import asyncio
import unittest
import uuid
from datetime import datetime,timedelta,timezone
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from app import schema as t,worker,execution,planning
from app.repositories import resolve_scope,ScopedRepository
import tests.test_foundation as foundation


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown

    def path(self,workspace=None):return '/api/v1/workspaces/'+(workspace or self.demo)['id']
    async def read(self):return (await self.client.get(self.path()+'/execution')).json()['data']
    async def post(self,suffix,body,key=None,workspace=None):
        return await self.client.post(self.path(workspace)+suffix,json=body,headers={**self.headers,'Idempotency-Key':key or str(uuid.uuid4())})
    async def command(self,action,subject=None,digest=None,**fields):
        data=await self.read();body={'action':action,'expected_version':data['version'],'subject_id':subject,'digest':digest,**fields}
        return await self.post('/execution/commands',body)
    async def prepare(self,mode='review',cap=2,budget=50000,customers=None):
        response=await self.post('/planning/facts',{'action':'seed_demo'});self.assertEqual(response.status_code,200,response.text)
        response=await self.post('/planning/policies',{'expected_revision':0,'config':{'variant_ids':['demo:laundry:1L'],'fallback_days':30,'contact_start':'00:00','contact_end':'23:59','mode':mode,'contact_cap':cap,'budget_minor':budget}})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()['data'];selected=[o['id'] for o in data['opportunities'] if o['eligible'] and (customers is None or o['evidence_json']['customer_alias'] in customers)]
        response=await self.post('/planning/drafts',{'expected_revision':0,'selected':selected});self.assertEqual(response.status_code,200,response.text)
        async with self.db.unit_of_work() as session:self.scope=await resolve_scope(session,self.owner_id,uuid.UUID(self.demo['id']),True)
        data=await self.read();review=data['plan_review']
        response=await self.command('approve_plan',review['id'],review['digest']);self.assertEqual(response.status_code,200,response.text)
        return response.json()['data']
    async def approve_actions(self):
        for action in (await self.read())['actions']:
            if action['state']=='awaiting_review':
                response=await self.command('approve_action',action['id'],action['digest']);self.assertEqual(response.status_code,200,response.text)

    async def test_first_plan_exact_message_approval_and_no_fabrication(self):
        data=await self.prepare()
        self.assertEqual(data['cohort_count'],3);self.assertEqual(len(data['actions']),3);self.assertEqual(data['receipts'],[])
        self.assertTrue(all(a['state']=='awaiting_review' for a in data['actions']))
        await worker.run_once(self.db,self.scope);self.assertEqual((await self.read())['receipts'],[])
        await self.approve_actions();await worker.run_once(self.db,self.scope)
        data=await self.read();self.assertEqual(len(data['receipts']),2)
        self.assertTrue(all(r['source_mode']=='simulated' and r['status']=='submitted' for r in data['receipts']))
        self.assertEqual(sum(j['state']=='ready' for j in data['jobs']),1) # confirmed reminder remains future
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.commerce_orders)),24)
            self.assertTrue(all(o['provider_order_id'].startswith('demo:') for o in await planning.rows(session,ScopedRepository(session,self.scope),t.commerce_orders)))

    async def test_stale_payload_policy_and_immutable_records(self):
        data=await self.prepare();action=data['actions'][0]
        self.assertEqual((await self.command('approve_action',action['id'],'0'*64)).status_code,409)
        async with self.db.unit_of_work() as session:policy=await planning.latest(session,ScopedRepository(session,self.scope),t.policies)
        await self.post('/planning/policies',{'expected_revision':1,'config':{**policy['config_json'],'contact_cap':3}})
        self.assertEqual((await self.command('approve_action',action['id'],action['digest'])).status_code,422)
        with self.assertRaises(DBAPIError):
            async with self.db.unit_of_work() as session:await session.execute(t.approvals.update().values(decision='reject'))
        with self.assertRaises(DBAPIError):
            async with self.db.unit_of_work() as session:await session.execute(t.proposed_actions.update().values(payload={'unsafe':True}))

    async def test_pause_optout_race_and_duplicate_events(self):
        data=await self.prepare('bounded',customers=['Ananya Rao'])
        claimed=await worker.claim(self.db,self.scope,datetime.now(timezone.utc));self.assertIsNotNone(claimed)
        await self.command('pause')
        self.assertIsNone(await worker.prepare(self.db,self.scope,claimed,datetime.now(timezone.utc)))
        await self.command('resume')
        journey=data['journeys'][0];event={'event_key':str(uuid.uuid4()),'journey_id':journey['id'],'kind':'opt_out'}
        first=await self.post('/execution/demo-events',event);self.assertEqual(first.status_code,200,first.text)
        await self.post('/execution/demo-events',event)
        await worker.run_once(self.db,self.scope)
        data=await self.read();self.assertEqual(data['receipts'],[]);self.assertEqual(data['journeys'][0]['state'],'opted_out')
        async with self.db.unit_of_work() as session:self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.event_inbox)),1)
        self.assertEqual((await self.post('/execution/demo-events',{**event,'kind':'support'})).status_code,409)

    async def test_takeover_reply_and_handback_guards(self):
        data=await self.prepare('bounded',customers=['Ananya Rao']);journey=data['journeys'][0]
        await self.command('takeover',journey['id']);await worker.run_once(self.db,self.scope)
        self.assertEqual((await self.read())['receipts'],[])
        response=await self.command('propose_reply',journey['id']);self.assertEqual(response.status_code,200,response.text)
        reply=next(a for a in response.json()['data']['actions'] if a['payload']['kind']=='human_acknowledgement')
        await self.command('approve_action',reply['id'],reply['digest']);await worker.run_once(self.db,self.scope)
        self.assertEqual(len((await self.read())['receipts']),1)
        response=await self.command('handback',journey['id']);self.assertEqual(response.status_code,200,response.text)
        self.assertIsNone(response.json()['data']['journeys'][0]['owner_id'])

    async def test_shared_budget_concurrency_with_barrier(self):
        await self.prepare('bounded',budget=25,customers=['Ananya Rao','Customer C003'])
        barrier=asyncio.Barrier(2)
        async def contender():
            claimed=await worker.claim(self.db,self.scope,datetime.now(timezone.utc));await barrier.wait()
            attempt=await worker.prepare(self.db,self.scope,claimed,datetime.now(timezone.utc))
            if attempt:await worker.finish(self.db,self.scope,attempt,await worker.demo_submit(self.db,self.scope,attempt,'accepted'))
        await asyncio.gather(contender(),contender())
        data=await self.read();self.assertEqual(len(data['receipts']),1)
        self.assertEqual(data['budgets'][0]['spent_minor'],25);self.assertEqual(data['budgets'][0]['reserved_minor'],0)
        self.assertTrue(any(j['blocked_reason']=='budget_cap' for j in data['jobs']))

    async def test_customer_cap_and_guard_concurrency(self):
        data=await self.prepare('bounded',cap=1,customers=['Ananya Rao']);journey=data['journeys'][0];original=data['actions'][0]
        async with self.db.unit_of_work() as session:
            policy=await planning.latest(session,ScopedRepository(session,self.scope),t.policies)
            await execution.create_action(session,self.scope,journey,policy,original['payload'],datetime.now(timezone.utc),planning.date(original['expires_at']),auto=True)
        barrier=asyncio.Barrier(2)
        async def contender():
            claimed=await worker.claim(self.db,self.scope,datetime.now(timezone.utc));await barrier.wait();return await worker.prepare(self.db,self.scope,claimed,datetime.now(timezone.utc))
        attempts=await asyncio.gather(contender(),contender());self.assertEqual(sum(a is not None for a in attempts),1)
        attempt=next(a for a in attempts if a);await worker.finish(self.db,self.scope,attempt,await worker.demo_submit(self.db,self.scope,attempt,'accepted'))
        self.assertEqual(len((await self.read())['receipts']),1)

    async def test_crash_before_submitting_and_lease_fencing(self):
        await self.prepare('bounded',customers=['Ananya Rao']);now=datetime.now(timezone.utc)
        claimed=await worker.claim(self.db,self.scope,now);await worker.recover(self.db,self.scope,now+timedelta(seconds=61))
        new=await worker.claim(self.db,self.scope,now+timedelta(seconds=61));self.assertNotEqual(new['lease_token'],claimed['lease_token'])
        self.assertIsNone(await worker.prepare(self.db,self.scope,claimed,now+timedelta(seconds=62)))
        attempt=await worker.prepare(self.db,self.scope,new,now+timedelta(seconds=62));self.assertIsNotNone(attempt)

    async def test_crash_after_submitting_holds_unknown_and_no_replay(self):
        await self.prepare('bounded',customers=['Ananya Rao']);now=datetime.now(timezone.utc)
        await worker.run_once(self.db,self.scope,now=now,crash='after_submitting')
        await worker.run_once(self.db,self.scope,now=now+timedelta(seconds=61))
        data=await self.read();self.assertEqual(data['receipts'][0]['status'],'unknown');self.assertEqual(data['budgets'][0]['reserved_minor'],25)
        self.assertEqual(data['journeys'][0]['owner_id'],str(self.scope.user_id))
        self.assertEqual((await self.command('handback',data['journeys'][0]['id'])).status_code,422)
        await worker.run_once(self.db,self.scope,now=now+timedelta(minutes=10))
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.dispatch_attempts)),1)
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.demo_transport)),0)

    async def test_crash_after_acceptance_recovers_while_paused(self):
        await self.prepare('bounded',customers=['Ananya Rao'])
        await worker.run_once(self.db,self.scope,crash='after_acceptance');await self.command('pause')
        await worker.run_once(self.db,self.scope)
        data=await self.read();self.assertTrue(data['paused']);self.assertEqual(len(data['receipts']),1)
        self.assertEqual(data['budgets'][0]['reserved_minor'],0);self.assertEqual(data['budgets'][0]['spent_minor'],25)
        await worker.run_once(self.db,self.scope)
        async with self.db.unit_of_work() as session:self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.demo_transport)),1)

    async def test_support_reminder_and_external_purchase_holds(self):
        data=await self.prepare('bounded');journey=next(j for j in data['journeys'] if j['customer_alias']=='Ananya Rao')
        event={'event_key':str(uuid.uuid4()),'journey_id':journey['id'],'kind':'support'}
        response=await self.post('/execution/demo-events',event);case=response.json()['data']['support_cases'][0]
        self.assertEqual((await self.command('handback',journey['id'])).status_code,403)
        await self.command('assign_support',case['id']);await self.command('resolve_support',case['id'])
        rahul=next(j for j in data['journeys'] if j['customer_alias']=='Rahul Verma')
        reminder={'event_key':str(uuid.uuid4()),'journey_id':rahul['id'],'kind':'reminder','due_at':(datetime.now(timezone.utc)+timedelta(days=3)).isoformat()}
        response=await self.post('/execution/demo-events',reminder);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(sum(r['state']=='scheduled' for r in response.json()['data']['reminders']),1)
        other=next(j for j in data['journeys'] if j['customer_alias']=='Customer C003')
        await self.post('/execution/demo-events',{'event_key':str(uuid.uuid4()),'journey_id':other['id'],'kind':'outside_purchase'})
        await worker.run_once(self.db,self.scope)
        data=await self.read();self.assertEqual(data['receipts'],[])
        self.assertEqual(data['cohort_count'],3)

    async def test_quiet_hours_and_scope_and_role_denial(self):
        data=await self.prepare('bounded',customers=['Ananya Rao'])
        async with self.db.unit_of_work() as session:
            policy=await planning.latest(session,ScopedRepository(session,self.scope),t.policies)
        # Change policy invalidates old action rather than silently changing approved mandate.
        await self.post('/planning/policies',{'expected_revision':1,'config':{**policy['config_json'],'contact_start':'10:00','contact_end':'18:00'}})
        await worker.run_once(self.db,self.scope);self.assertEqual((await self.read())['receipts'],[])
        self.assertEqual((await self.post('/execution/commands',{'action':'pause','expected_version':0},workspace=self.dev)).status_code,422)
        self.assertEqual((await self.post('/execution/demo-events',{'event_key':str(uuid.uuid4()),'journey_id':str(uuid.uuid4()),'kind':'opt_out'})).status_code,404)
        async with self.db.unit_of_work() as session:await session.execute(t.memberships.update().values(role='viewer'))
        self.assertEqual((await self.command('pause')).status_code,403)
        self.assertEqual((await self.post('/execution/run-due',{})).status_code,403)
