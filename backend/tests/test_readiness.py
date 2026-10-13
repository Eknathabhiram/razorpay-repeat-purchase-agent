import json,unittest,uuid
from datetime import datetime,timezone
import sqlalchemy as sa
from app import schema as t
from app.payment_sources import RazorpayReadOnly
from app.together_provider import TogetherProvider
from app.whatsapp_transport import TwilioTransport
import tests.test_foundation as foundation
import tests.test_execution as helpers

class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown
    path=helpers.ExecutionTests.path
    post=helpers.ExecutionTests.post
    async def status(self,workspace=None):
        self.app.state.razorpay=RazorpayReadOnly(key='rzp_test_synthetic',secret='synthetic-secret')
        self.app.state.twilio=TwilioTransport(account='',token='',sender='')
        self.app.state.together=TogetherProvider(key='synthetic-together-key')
        response=await self.client.get(self.path(workspace)+'/merchant/readiness')
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()['data'];return data,{p['provider']:p for p in data['providers']}
    async def test_demo_is_a_functioning_synthetic_journey_not_disconnected_providers(self):
        data,providers=await self.status()
        self.assertEqual(providers['shopify']['status'],'setup')
        self.assertEqual(providers['twilio']['status'],'demo');self.assertEqual(providers['support']['status'],'ready')
        self.assertFalse(data['real_outreach_enabled']);self.assertFalse(data['real_checkout_enabled'])
        await self.post('/planning/facts',{'action':'seed_demo'})
        data,providers=await self.status();self.assertEqual(providers['shopify']['label'],'Demo data loaded')
        self.assertNotIn('synthetic-secret',json.dumps(data));self.assertNotIn('synthetic-together-key',json.dumps(data))
    async def test_credentials_are_separate_from_scoped_verified_reads(self):
        data,providers=await self.status(self.dev)
        self.assertEqual(providers['razorpay']['status'],'configured');self.assertEqual(providers['twilio']['status'],'blocked')
        self.assertEqual(providers['together']['status'],'configured')
        connectors=(await self.client.get(self.path(self.dev)+'/connectors')).json()['data'];shop=next(c for c in connectors if c['provider']=='shopify')
        response=await self.post('/connectors/'+shop['id']+'/check',{'expected_version':shop['version']},workspace=self.dev)
        self.assertEqual(response.status_code,200,response.text)
        data,providers=await self.status(self.dev);self.assertEqual(providers['shopify']['status'],'ready')
        gateway=next(c for c in connectors if c['provider']=='razorpay')
        async with self.db.unit_of_work() as session:
            await session.execute(t.connectors.update().where(t.connectors.c.id==uuid.UUID(gateway['id'])).values(state='healthy',provider_account_id=self.app.state.razorpay.account_ref,last_checked_at=datetime.now(timezone.utc)))
        data,providers=await self.status(self.dev);self.assertEqual(providers['razorpay']['status'],'ready')
        _,other=await self.status();self.assertEqual(other['razorpay']['status'],'demo')
    async def test_automatic_together_receipts_count_as_verified_only_in_their_workspace(self):
        await self.status()
        async with self.db.unit_of_work() as session:
            await session.execute(t.event_outbox.insert().values(merchant_id=uuid.UUID(self.demo['merchant_id']) if 'merchant_id' in self.demo else
                await session.scalar(sa.select(t.workspaces.c.merchant_id).where(t.workspaces.c.id==uuid.UUID(self.demo['id']))),workspace_id=uuid.UUID(self.demo['id']),event_type='conversation.interpreted',subject_id=uuid.uuid4(),details={'receipt':{'provider':'together','account_ref':self.app.state.together.account_ref},'source_mode':'simulated'}))
        _,providers=await self.status();self.assertEqual(providers['together']['status'],'ready')
        _,other=await self.status(self.dev);self.assertEqual(other['together']['status'],'configured')
        response=await self.client.get('/api/v1/workspaces/'+str(uuid.uuid4())+'/merchant/readiness');self.assertEqual(response.status_code,404)

if __name__=='__main__':unittest.main()
