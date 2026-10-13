import unittest,uuid
from datetime import datetime,timedelta,timezone
import sqlalchemy as sa
from app import schema as t
import tests.test_foundation as foundation
import tests.test_execution as execution_tests
import tests.test_commerce as commerce_tests

class OutcomesTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown
    path=execution_tests.ExecutionTests.path
    read=execution_tests.ExecutionTests.read
    post=execution_tests.ExecutionTests.post
    command=execution_tests.ExecutionTests.command
    prepare=execution_tests.ExecutionTests.prepare
    cart=commerce_tests.CommerceTests.cart
    evidence=commerce_tests.CommerceTests.evidence
    commerce=commerce_tests.CommerceTests.commerce
    async def outcomes(self):return (await self.client.get(self.path()+'/outcomes')).json()['data']
    async def test_reminder_learning_does_not_apply_to_other_variant(self):
        from app import planning
        from app.planning_models import PolicyConfig
        await self.prepare(customers=['Rahul Verma'])
        async with self.db.unit_of_work() as session:
            other_id=uuid.uuid4()
            await session.execute(t.variants.insert().values(id=other_id,merchant_id=self.scope.merchant_id,workspace_id=self.scope.workspace_id,provider_variant_id='demo:other',provider_product_id='demo:other-product',title='Other product',sku='OTHER',price_minor=49900,currency='INR',stock=10,active=True,provenance={'source_mode':'simulated'}))
            opportunities=await planning.compute(session,self.scope,PolicyConfig(variant_ids=['demo:laundry:1L','demo:other'],fallback_days=30))
            other=next(o for o in opportunities if o['variant_id']==str(other_id) and o['evidence_json']['customer_alias']=='Rahul Verma')
            self.assertNotEqual(other['basis'],'customer_confirmed_date')
    async def test_outside_purchase_refunds_and_unknown_costs(self):
        await self.prepare(customers=['Ananya Rao']);cart,_=await self.cart()
        key=str(uuid.uuid4());await self.evidence(cart,'outside_link',key);await self.evidence(cart,'outside_link',key)
        data=await self.outcomes();self.assertEqual(data['totals'][0]['purchase_count'],1);self.assertEqual(data['totals'][0]['outside_link_count'],1)
        purchase=data['purchases'][0];self.assertIsNone(purchase['contribution_minor']);self.assertEqual(purchase['net_payable_minor'],53900)
        costs={'purchase_id':purchase['id'],'expected_revision':0,'product_cost_minor':10000,'fulfillment_cost_minor':4000,'gateway_fee_minor':100,'contact_cost_minor':25,'agent_cost_minor':0,'retained_tax_minor':0,'confirmed_demo_return_maturity':False}
        response=await self.post('/outcomes/accounting',costs);self.assertEqual(response.status_code,200,response.text)
        self.assertIsNone(response.json()['data']['purchases'][0]['contribution_minor'])
        response=await self.post('/outcomes/accounting',{**costs,'expected_revision':1,'confirmed_demo_return_maturity':True})
        self.assertEqual(response.json()['data']['purchases'][0]['contribution_minor'],39775)
        await self.evidence(cart,'refunded');data=await self.outcomes()
        self.assertEqual(data['totals'][0]['refund_minor'],53900);self.assertEqual(data['totals'][0]['purchase_count'],1)
        self.assertIsNone(data['totals'][0]['contribution_minor']);self.assertIn('refund_accounting_review_required',data['purchases'][0]['missing_costs'])
        self.assertEqual((await self.post('/outcomes/accounting',costs,workspace=self.dev)).status_code,403)
    async def test_cohort_survives_plan_renewal_without_double_counting(self):
        await self.prepare(customers=['Ananya Rao','Rahul Verma']);cart,_=await self.cart()
        await self.evidence(cart,'captured')
        before=await self.outcomes();self.assertEqual(len(before['cohorts']),1)
        plan=(await self.client.get(self.path()+'/planning')).json()['data']
        selected=[o['id'] for o in plan['opportunities'] if o['eligible'] and o['evidence_json']['customer_alias']=='Rahul Verma']
        response=await self.post('/planning/drafts',{'expected_revision':plan['draft']['revision'],'selected':selected})
        self.assertEqual(response.status_code,200,response.text)
        review=(await self.read())['plan_review'];response=await self.command('approve_plan',review['id'],review['digest']);self.assertEqual(response.status_code,200,response.text)
        after=await self.outcomes();self.assertEqual(len(after['cohorts']),2);self.assertEqual(after['totals'][0]['purchase_count'],1)
        self.assertEqual(sum(c['observed_purchases'] for c in after['cohorts']),1)
        self.assertTrue(all(c['incremental_lift'] is None for c in after['cohorts']))
    async def test_confirmed_learning_suggestion_requires_owner_decision(self):
        await self.prepare(customers=['Ananya Rao']);journey=(await self.read())['journeys'][0]
        voice=(await self.post('/voice-sessions',{'journey_id':journey['id'],'confirmed_browser_test_consent':True})).json()['data']
        response=await self.post('/voice-sessions/'+voice['id']+'/turns',{'sequence':1,'text':'remind me Friday and is my coupon valid'})
        turn=response.json()['data']['turns'][0]
        self.assertEqual((await self.outcomes())['learning'],[])
        response=await self.post('/intelligence/turns/'+turn['id']+'/reminder',{'due_at':(datetime.now(timezone.utc)+timedelta(days=3)).isoformat(),'confirmed_date_and_whatsapp':True})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(len((await self.outcomes())['learning']),1)
        response=await self.post('/outcomes/suggestions',{});self.assertEqual(response.status_code,200,response.text)
        suggestion=response.json()['data']['suggestions'][0]
        policy=(await self.client.get(self.path()+'/planning')).json()['data']['policy']
        self.assertEqual(policy['config_json']['contact_cap'],2)
        response=await self.post('/outcomes/suggestions/'+suggestion['id']+'/decision',{'decision':'accept','expected_policy_revision':policy['revision']})
        self.assertEqual(response.status_code,200,response.text)
        new=(await self.client.get(self.path()+'/planning')).json()['data']['policy']
        self.assertEqual(new['config_json']['contact_cap'],1);self.assertTrue((await self.read())['plan_review']['stale'])
        self.assertEqual((await self.post('/outcomes/suggestions/'+suggestion['id']+'/decision',{'decision':'accept','expected_policy_revision':new['revision']})).status_code,409)
