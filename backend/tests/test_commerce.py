import json
import unittest
import uuid
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
import httpx
import sqlalchemy as sa
from app import schema as t,worker,commerce
from app.payment_sources import RazorpayReadOnly,StorefrontCartAdapter
from app.commerce_callbacks import signature_valid
import tests.test_foundation as foundation
import tests.test_execution as execution_tests


class CommerceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown
    path=execution_tests.ExecutionTests.path
    read=execution_tests.ExecutionTests.read
    post=execution_tests.ExecutionTests.post
    command=execution_tests.ExecutionTests.command
    prepare=execution_tests.ExecutionTests.prepare

    async def commerce(self):return (await self.client.get(self.path()+'/commerce')).json()['data']
    async def cart(self,quantity=1,offer=None):
        data=await self.read();journey=next(j for j in data['journeys'] if j['customer_alias']=='Ananya Rao' and j['plan_revision_id']==data['plan_review']['id'])
        body={'journey_id':journey['id'],'quantity':quantity,'confirmed_same_product':True,'confirmed_whatsapp_handoff':True,'offer_ref':offer}
        response=await self.post('/commerce/quote',body)
        self.assertEqual(response.status_code,200,response.text)
        body['quote_digest']=response.json()['data']['digest']
        response=await self.post('/commerce/commands',{'action':'prepare','cart':body})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['data']['preparations'][-1],body
    async def evidence(self,prepared,scenario,key=None):
        return await self.post('/commerce/demo-evidence',{'event_key':key or str(uuid.uuid4()),'journey_id':prepared['journey_id'],'preparation_id':prepared['id'],'scenario':scenario})

    async def test_checkout_prepare_is_not_payment_and_link_needs_approval(self):
        await self.prepare(customers=['Ananya Rao']);prepared,body=await self.cart(2)
        self.assertEqual(prepared['terms_json']['total_estimate_minor'],103800)
        self.assertEqual((await self.commerce())['payments'],[])
        self.assertTrue(all(a['state']=='cancelled' for a in (await self.read())['actions']))
        response=await self.post('/commerce/commands',{'action':'propose_link','preparation_id':prepared['id']})
        self.assertEqual(response.status_code,200,response.text)
        action=next(a for a in (await self.read())['actions'] if a['payload']['kind']=='checkout_link')
        self.assertEqual(action['state'],'awaiting_review');await worker.run_once(self.db,self.scope)
        self.assertEqual((await self.read())['receipts'],[])
        response=await self.command('approve_action',action['id'],action['digest']);self.assertEqual(response.status_code,200,response.text)
        await worker.run_once(self.db,self.scope)
        data=await self.commerce();self.assertEqual(data['preparations'][0]['state'],'link_submitted');self.assertEqual(data['purchases'],[])

    async def test_stale_terms_quantity_scope_and_idempotency(self):
        await self.prepare(customers=['Ananya Rao']);prepared,body=await self.cart()
        key=str(uuid.uuid4());first=await self.post('/commerce/commands',{'action':'prepare','cart':body},key=key)
        replay=await self.post('/commerce/commands',{'action':'prepare','cart':body},key=key)
        self.assertEqual(first.json()['data'],replay.json()['data'])
        self.assertEqual((await self.post('/commerce/commands',{'action':'prepare','cart':{**body,'quantity':2}},key=key)).status_code,409)
        async with self.db.unit_of_work() as session:await session.execute(t.variants.update().values(price_minor=59900))
        self.assertEqual((await self.post('/commerce/commands',{'action':'prepare','cart':body})).status_code,409)
        self.assertEqual((await self.post('/commerce/quote',{**body,'quantity':0})).status_code,422)
        self.assertEqual((await self.post('/commerce/quote',{**body,'confirmed_same_product':False})).status_code,422)
        self.assertEqual((await self.post('/commerce/quote',body,workspace=self.dev)).status_code,422)

    async def test_independent_evidence_matches_full_total_once_and_refunds(self):
        await self.prepare(customers=['Ananya Rao']);prepared,_=await self.cart()
        key=str(uuid.uuid4());response=await self.evidence(prepared,'captured',key)
        self.assertEqual(response.status_code,200,response.text);data=response.json()['data'];self.assertEqual(len(data['matches']),1)
        self.assertEqual(data['purchases'][0]['total_minor'],53900);self.assertFalse(data['purchases'][0]['delivery_verified'])
        await self.evidence(prepared,'captured',key);self.assertEqual(len((await self.commerce())['purchases']),1)
        response=await self.evidence(prepared,'refunded');data=response.json()['data'];self.assertEqual(len(data['matches']),1)
        self.assertEqual(data['purchases'][0]['net_payable_minor'],0);self.assertEqual(len(data['adjustments']),1)
        await self.evidence(prepared,'refunded');self.assertEqual(len((await self.commerce())['adjustments']),1)
        self.assertEqual((await self.evidence(prepared,'authorized',key)).status_code,409)

    async def test_mismatch_and_unmatched_cannot_confirm_or_fake_browser_success(self):
        await self.prepare(customers=['Ananya Rao']);prepared,_=await self.cart()
        response=await self.evidence(prepared,'amount_mismatch');self.assertEqual(response.status_code,200,response.text)
        data=response.json()['data'];self.assertEqual(data['purchases'],[])
        self.assertIn('payable_total_or_currency_mismatch',[c['reason'] for c in data['cases']])
        response=await self.post('/commerce/demo-evidence',{'event_key':str(uuid.uuid4()),'journey_id':prepared['journey_id'],'scenario':'browser_success'})
        self.assertEqual(response.status_code,422)
        await worker.run_once(self.db,self.scope);self.assertEqual((await self.read())['receipts'],[])

    async def test_offers_disabled_missing_cost_margin_and_valid_explicit_offer(self):
        await self.prepare(customers=['Ananya Rao']);data=await self.read();journey=data['journeys'][0]
        request={'journey_id':journey['id'],'quantity':1,'confirmed_same_product':True,'confirmed_whatsapp_handoff':True,'offer_ref':'DEMO-REORDER-25'}
        self.assertEqual((await self.post('/commerce/quote',request)).json()['error']['code'],'OFFERS_OFF')
        await self.post('/commerce/commands',{'action':'seed_offer'})
        await self.post('/commerce/offer-policy',{'expected_revision':0,'enabled':True,'approved_offer_ref':'DEMO-REORDER-25'})
        self.assertEqual((await self.post('/commerce/quote',request)).json()['error']['code'],'PLAN_STALE')
        current=(await self.client.get(self.path()+'/planning')).json()['data']
        await self.post('/planning/drafts',{'expected_revision':1,'selected':[o['id'] for o in current['opportunities'] if o['eligible'] and o['evidence_json']['customer_alias']=='Ananya Rao']})
        review=(await self.read())['plan_review'];await self.command('approve_plan',review['id'],review['digest'])
        request['journey_id']=next(j['id'] for j in (await self.commerce())['journeys'] if j['current_plan'])
        self.assertEqual((await self.post('/commerce/quote',request)).json()['error']['code'],'COSTS_MISSING')
        await self.post('/commerce/offer-policy',{'expected_revision':1,'enabled':True,'approved_offer_ref':'DEMO-REORDER-25','unit_cost_minor':48000,'fulfillment_cost_minor':5000})
        self.assertEqual((await self.post('/commerce/quote',request)).json()['error']['code'],'MARGIN_FLOOR')
        await self.post('/commerce/offer-policy',{'expected_revision':2,'enabled':True,'approved_offer_ref':'DEMO-REORDER-25','unit_cost_minor':20000,'fulfillment_cost_minor':5000})
        prepared,_=await self.cart(offer='DEMO-REORDER-25');self.assertEqual(prepared['terms_json']['discount_minor'],2500)
        self.assertEqual(prepared['terms_json']['total_estimate_minor'],51400)

    async def test_callbacks_authenticate_bind_and_only_queue_refetch(self):
        import hashlib,hmac
        connectors=(await self.client.get(self.path(self.dev)+'/connectors')).json()['data'];gateway=next(c for c in connectors if c['provider']=='razorpay')
        async with self.db.unit_of_work() as session:await session.execute(t.connectors.update().where(t.connectors.c.id==uuid.UUID(gateway['id'])).values(provider_account_id='test-key:fixture'))
        raw=json.dumps({'account_id':'acc_demo','event':'payment.captured','payload':{'payment':{'entity':{'id':'pay_fixture'}}}}).encode()
        signature=hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest();url='/api/v1/providers/razorpay/'+self.dev['id']+'/'+gateway['id']+'/events'
        with patch.dict('os.environ',{'RAZORPAY_WEBHOOK_SECRET':'fixture-secret','RAZORPAY_WEBHOOK_ACCOUNT_ID':'acc_demo'}):
            self.assertEqual((await self.client.post(url,content=raw,headers={'X-Razorpay-Signature':'wrong'})).status_code,401)
            first=await self.client.post(url,content=raw,headers={'X-Razorpay-Signature':signature});self.assertEqual(first.status_code,200,first.text)
            await self.client.post(url,content=raw,headers={'X-Razorpay-Signature':signature,'X-Razorpay-Event-Id':'different'})
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.provider_notifications)),1)
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.confirmed_purchases)),0)

    async def test_unmatched_authorized_and_mode_mismatch_remain_exceptions(self):
        await self.prepare(customers=['Ananya Rao']);prepared,_=await self.cart()
        response=await self.evidence(prepared,'unmatched');self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['data']['purchases'],[])
        self.assertIn('mapping_missing_or_ambiguous',[c['reason'] for c in response.json()['data']['cases']])
        async with self.db.unit_of_work() as session:
            # Source fixture mutation is confined to the disposable database.
            await session.execute(t.payments.update().values(order_receipt='demo:receipt:'+prepared['id'],source_mode='test'))
            await commerce.reconcile(session,self.scope)
        self.assertEqual((await self.commerce())['purchases'],[])
        self.assertIn('account_or_mode_mismatch',[c['reason'] for c in (await self.commerce())['cases']])

    async def test_expiry_and_out_of_order_payment_status(self):
        await self.prepare(customers=['Ananya Rao']);prepared,_=await self.cart()
        await self.evidence(prepared,'captured')
        await self.evidence(prepared,'authorized')
        data=await self.commerce();self.assertTrue(data['payments'][0]['captured']);self.assertEqual(data['payments'][0]['status'],'captured');self.assertEqual(len(data['purchases']),1)
        async with self.owner_db.unit_of_work() as session:
            await session.execute(t.checkout_preparations.update().values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1),state='prepared'))
        self.assertEqual((await self.post('/commerce/commands',{'action':'propose_link','preparation_id':prepared['id']})).status_code,422)

    async def test_scope_viewer_and_changed_stock_blocks_link(self):
        await self.prepare(customers=['Ananya Rao']);prepared,_=await self.cart()
        await self.post('/commerce/commands',{'action':'propose_link','preparation_id':prepared['id']})
        action=next(a for a in (await self.read())['actions'] if a['payload']['kind']=='checkout_link')
        await self.command('approve_action',action['id'],action['digest'])
        async with self.db.unit_of_work() as session:await session.execute(t.variants.update().values(stock=0))
        await worker.run_once(self.db,self.scope);self.assertEqual((await self.read())['receipts'],[])
        async with self.db.unit_of_work() as session:await session.execute(t.memberships.update().values(role='viewer'))
        self.assertEqual((await self.post('/commerce/commands',{'action':'seed_offer'})).status_code,403)


class SourceContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_keys_rejected_and_http_adapter_read_only_redacted(self):
        with self.assertRaises(Exception):await RazorpayReadOnly('rzp_live_fixture','secret').snapshot()
        calls=[]
        def respond(request):
            calls.append(request.method)
            if request.url.path.endswith('/payments'):return httpx.Response(200,json={'items':[{'id':'pay_fixture','order_id':'order_fixture','amount':127315,'currency':'INR','status':'captured','captured':True,'amount_refunded':0,'contact':'DO_NOT_PERSIST'}]})
            if '/orders/' in request.url.path:return httpx.Response(200,json={'id':'order_fixture','receipt':'join-ref','amount':127315,'amount_paid':127315,'currency':'INR','status':'paid'})
            return httpx.Response(200,json={'items':[]})
        source=RazorpayReadOnly('rzp_test_fixture','synthetic',httpx.MockTransport(respond));data=await source.snapshot()
        self.assertTrue(all(c=='GET' for c in calls));self.assertNotIn('DO_NOT_PERSIST',json.dumps(data));self.assertEqual(data['payments'][0]['amount'],127315)

    async def test_storefront_contract_exact_variant_and_disabled_mutation(self):
        disabled=StorefrontCartAdapter('test.myshopify.com','2026-10','')
        self.assertFalse((await disabled.verify())['available'])
        with self.assertRaises(Exception):await disabled.prepare('gid://shopify/ProductVariant/1',1,uuid.uuid4())
        def respond(request):
            data=json.loads(request.content);line=data['variables']['input']['lines'][0]
            return httpx.Response(200,json={'data':{'cartCreate':{'userErrors':[],'cart':{'id':'cart_fixture','checkoutUrl':'https://test.myshopify.com/cart/c/fixture','cost':{'totalAmount':{'amount':'499.00','currencyCode':'INR'}},'lines':{'nodes':[{'quantity':line['quantity'],'merchandise':{'id':line['merchandiseId']}}]}}}}})
        adapter=StorefrontCartAdapter('test.myshopify.com','2026-10','synthetic',httpx.MockTransport(respond),allow_creation=True)
        self.assertEqual((await adapter.prepare('gid://shopify/ProductVariant/1',2,uuid.uuid4()))['lines']['nodes'][0]['quantity'],2)
        with self.assertRaises(Exception):await adapter.prepare('gid://shopify/Product/1',1,uuid.uuid4())

    async def test_signatures_use_raw_bytes_and_correct_provider_encoding(self):
        import hmac,hashlib,base64
        raw=b'{"test":true}';secret='synthetic'
        value=hmac.new(secret.encode(),raw,hashlib.sha256).digest()
        self.assertTrue(signature_valid('razorpay',raw,value.hex(),secret));self.assertTrue(signature_valid('shopify',raw,base64.b64encode(value).decode(),secret))
        self.assertFalse(signature_valid('razorpay',raw+b' ',value.hex(),secret))
