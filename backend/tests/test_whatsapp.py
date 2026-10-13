import base64, hashlib, hmac, unittest, uuid
from datetime import datetime, timezone
import httpx
import sqlalchemy as sa
from app import schema as t, whatsapp, worker
from app.whatsapp_transport import TwilioTransport, validate_signature
from app.errors import ApplicationError
import tests.test_foundation as foundation
import tests.test_execution as execution_tests

def sign(url,params,token):
    return base64.b64encode(hmac.new(token.encode(),(url+''.join(k+params[k] for k in sorted(params))).encode(),hashlib.sha1).digest()).decode()

class TransportTests(unittest.IsolatedAsyncioTestCase):
    def test_published_signature_vector_and_tampering(self):
        url='https://example.com/myapp.php?foo=1&bar=2'
        params={'CallSid':'CA1234567890ABCDE','Caller':'+14158675310','Digits':'1234','From':'+14158675310','To':'+18005551212'}
        self.assertTrue(validate_signature(url,params,'L/OH5YylLD5NRKLltdqwSvS0BnU=','12345'))
        self.assertFalse(validate_signature(url+'x',params,'L/OH5YylLD5NRKLltdqwSvS0BnU=','12345'))
        self.assertFalse(validate_signature(url,params,'非ASCII','12345'))
    async def test_template_authority_and_unknown_timeout_no_retry(self):
        calls=[]
        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout('synthetic',request=request)
        adapter=TwilioTransport(account='AC'+'a'*32,token='synthetic-token',sender='whatsapp:+15550001111',transport=httpx.MockTransport(handler))
        with self.assertRaises(ApplicationError): await adapter.send_template('whatsapp:+15550002222','HX'+'b'*32,{})
        self.assertEqual(calls,[])
        result=await adapter.send_template('whatsapp:+15550002222','HX'+'b'*32,{},authorized=True,verified_recipient=True,approved_content=True)
        self.assertEqual(result['status'],'unknown');self.assertFalse(result['retry_allowed']);self.assertEqual(len(calls),1)
    def test_priority_and_no_purchase_or_consent_inference(self):
        self.assertEqual(whatsapp.classify('Yes but STOP contacting me'),'opt_out')
        self.assertEqual(whatsapp.classify('Yes my bottle is damaged'),'support')
        self.assertEqual(whatsapp.classify('No thanks'),'refusal')
        self.assertEqual(whatsapp.classify('Remind me next week'),'reminder_request')
        self.assertEqual(whatsapp.classify('I have paid'),'needs_review')

class WhatsAppTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls): foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown
    path=execution_tests.ExecutionTests.path
    read=execution_tests.ExecutionTests.read
    post=execution_tests.ExecutionTests.post
    command=execution_tests.ExecutionTests.command
    prepare=execution_tests.ExecutionTests.prepare
    async def inbound(self,journey,text,key=None,workspace=None):
        return await self.post('/whatsapp/demo-inbound',{'journey_id':journey['id'],'event_key':key or str(uuid.uuid4()),'text':text},workspace=workspace)
    async def test_reply_cancels_customer_work_duplicates_and_scope(self):
        await self.prepare(customers=['Ananya Rao'])
        journey=(await self.read())['journeys'][0];key=str(uuid.uuid4())
        response=await self.inbound(journey,'Yes reorder same product',key)
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()['data'];self.assertEqual(data['journeys'][0]['state'],'reply_review')
        self.assertIsNotNone(data['journeys'][0]['owner_id'])
        await self.inbound(journey,'Yes reorder same product',key)
        self.assertEqual((await self.client.get(self.path()+'/whatsapp')).json()['data']['events'].__len__(),1)
        self.assertEqual((await self.inbound(journey,'STOP',key)).status_code,409)
        self.assertEqual((await self.inbound(journey,'STOP',workspace=self.dev)).status_code,422)
        await worker.run_once(self.db,self.scope);self.assertEqual((await self.read())['receipts'],[])
        self.assertEqual((await self.command('handback',journey['id'])).status_code,422)
    async def test_optout_and_support_remain_protected(self):
        await self.prepare(customers=['Ananya Rao','Rahul Verma'])
        journeys=(await self.read())['journeys'];first=journeys[0];second=journeys[1]
        await self.inbound(first,'STOP');await self.inbound(first,'Yes please')
        await self.inbound(second,'My product arrived damaged, refund please')
        data=await self.read()
        self.assertEqual(next(j for j in data['journeys'] if j['id']==first['id'])['state'],'opted_out')
        self.assertEqual(next(j for j in data['journeys'] if j['id']==second['id'])['state'],'support')
        self.assertEqual(len(data['support_cases']),1)
        await worker.run_once(self.db,self.scope);self.assertEqual((await self.read())['receipts'],[])
    async def test_delivery_read_ordering_and_conflict(self):
        await self.prepare(customers=['Ananya Rao'],mode='bounded')
        await worker.run_once(self.db,self.scope)
        receipts=(await self.read())['receipts'];self.assertEqual(len(receipts),1)
        for status in ['read','delivered','queued','read','failed']:
            response=await self.post('/whatsapp/demo-status',{'event_key':str(uuid.uuid4()),'receipt_id':receipts[0]['id'],'status':status})
            self.assertEqual(response.status_code,200,response.text)
        data=response.json()['data'];self.assertEqual(data['messages'][0]['status'],'read')
        self.assertEqual(len(data['events']),4)
        self.assertIn('requires_authoritative_refetch',[e['state'] for e in data['events']])
    async def test_signed_callbacks_account_binding_unmapped_quarantine(self):
        adapter=TwilioTransport(account='AC'+'a'*32,token='synthetic-token',sender='whatsapp:+15550001111',callback_base='https://callbacks.example')
        self.app.state.twilio=adapter
        async with self.db.unit_of_work() as session:
            conn=(await session.execute(sa.select(t.connectors).where(t.connectors.c.workspace_id==uuid.UUID(self.dev['id']),t.connectors.c.provider=='twilio'))).mappings().one()
            await session.execute(t.connectors.update().where(t.connectors.c.id==conn['id']).values(provider_account_id=adapter.account))
        path='/api/v1/providers/twilio/'+self.dev['id']+'/'+str(conn['id'])+'/inbound'
        params={'AccountSid':adapter.account,'MessageSid':'SM'+'b'*32,'From':'whatsapp:+15550002222','To':adapter.sender,'Body':'STOP'}
        headers={'X-Twilio-Signature':sign(adapter.callback_base+path,params,adapter.token)}
        response=await self.client.post(path,data=params,headers=headers)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.headers['content-type'],'application/json')
        await self.client.post(path,data=params,headers=headers)
        data=(await self.client.get(self.path(self.dev)+'/whatsapp')).json()['data']
        self.assertEqual(len(data['events']),1);self.assertEqual(data['events'][0]['state'],'quarantined');self.assertIsNone(data['events'][0]['text'])
        self.assertEqual((await self.client.post(path,data={**params,'Body':'changed'},headers=headers)).status_code,401)
        wrong={**params,'AccountSid':'AC'+'c'*32}
        self.assertEqual((await self.client.post(path,data=wrong,headers={'X-Twilio-Signature':sign(adapter.callback_base+path,wrong,adapter.token)})).status_code,403)
        self.assertEqual((await self.client.post(path,json=params,headers=headers)).status_code,415)

    async def test_reviewed_identity_routes_exact_sender_without_marketing_consent(self):
        customer_id=uuid.uuid4();sid='SM'+'d'*32;account='AC'+'a'*32;sender='whatsapp:+15550001111';address='whatsapp:+15550002222'
        def handler(request):
            return httpx.Response(200,json={'account_sid':account,'sid':sid,'from':address,'to':sender,'direction':'inbound','status':'received','error_code':None})
        adapter=TwilioTransport(account=account,token='synthetic-token',sender=sender,callback_base='https://callbacks.example',transport=httpx.MockTransport(handler))
        self.app.state.twilio=adapter
        async with self.db.unit_of_work() as session:
            await session.execute(t.customers.insert().values(id=customer_id,merchant_id=uuid.UUID(self.dev['merchant_id']) if 'merchant_id' in self.dev else (await session.scalar(sa.select(t.workspaces.c.merchant_id).where(t.workspaces.c.id==uuid.UUID(self.dev['id'])))),workspace_id=uuid.UUID(self.dev['id']),provider_customer_id='synthetic-dev-customer',display_alias='Reviewed test recipient',identity_state='verified'))
        response=await self.post('/whatsapp/identity-review',{'customer_id':str(customer_id),'address':address,'message_sid':sid,'confirmed_customer_identity':True},workspace=self.dev)
        self.assertEqual(response.status_code,200,response.text)
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.customer_evidence)),0)
            conn=(await session.execute(sa.select(t.connectors).where(t.connectors.c.workspace_id==uuid.UUID(self.dev['id']),t.connectors.c.provider=='twilio'))).mappings().one()
        path='/api/v1/providers/twilio/'+self.dev['id']+'/'+str(conn['id'])+'/inbound'
        params={'AccountSid':account,'MessageSid':sid,'From':address,'To':sender,'Body':'STOP'}
        response=await self.client.post(path,data=params,headers={'X-Twilio-Signature':sign(adapter.callback_base+path,params,adapter.token)})
        self.assertEqual(response.status_code,200,response.text)
        async with self.db.unit_of_work() as session:
            evidence=(await session.execute(sa.select(t.customer_evidence).where(t.customer_evidence.c.customer_id==customer_id))).mappings().one()
            self.assertEqual(evidence['kind'],'suppression');self.assertTrue(evidence['value']['active'])
