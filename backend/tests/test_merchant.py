"""Cohort filtering and automatic conversations use actual scoped PostgreSQL state."""
import uuid
import unittest
from datetime import datetime,timedelta,timezone
import sqlalchemy as sa
from app import schema as t,worker,automation
from app.repositories import resolve_scope
from app.together_provider import TogetherProvider
from app.intelligence_models import IntentProposal,IntentItem
import tests.test_foundation as foundation
import tests.test_execution as execution_tests

class MerchantTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown
    path=execution_tests.ExecutionTests.path
    read=execution_tests.ExecutionTests.read
    post=execution_tests.ExecutionTests.post
    command=execution_tests.ExecutionTests.command

    async def get(self,suffix):
        response=await self.client.get(self.path()+suffix)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['data']
    async def prepare(self,scale=False,cap=10,contextual=False):
        response=await self.post('/planning/facts',{'action':'seed_scale_demo' if scale else 'seed_demo'})
        self.assertEqual(response.status_code,200,response.text)
        response=await self.post('/planning/policies',{'expected_revision':0,'config':{'variant_ids':['demo:laundry:1L'],'fallback_days':30,'contact_start':'00:00','contact_end':'23:59','mode':'bounded','contact_cap':cap,'budget_minor':500000,'conversation_automation':True,'contextual_replies':contextual,'provider_processing':contextual}})
        self.assertEqual(response.status_code,200,response.text)
        async with self.db.unit_of_work() as session:self.scope=await resolve_scope(session,self.owner_id,uuid.UUID(self.demo['id']),True)
        return await self.get('/merchant/planning')
    async def draft(self,data,filters=None,selected=None,excluded=None):
        body={'expected_revision':data['draft']['revision'] if data['draft'] else 0,'facts_version':data['facts_version'],'policy_id':data['policy']['id'],'mode':'explicit' if selected else 'eligible','filters':filters or {},'selected':selected or [],'excluded':excluded or []}
        response=await self.post('/merchant/audience',body)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['data'],body
    async def approve(self):
        data=await self.get('/merchant/launch');review=data['plan_review']
        response=await self.post('/merchant/commands',{'action':'approve_plan','expected_version':data['version'],'subject_id':review['id'],'digest':review['digest']})
        self.assertEqual(response.status_code,200,response.text)
    async def choice(self,action,button,key=None):
        response=await self.post('/merchant/whatsapp/demo-choice',{'action_id':action,'button_id':button,'event_key':key or str(uuid.uuid4())})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['data']
    async def text(self,journey,text):
        response=await self.post('/whatsapp/demo-inbound',{'journey_id':journey,'text':text,'event_key':str(uuid.uuid4())})
        self.assertEqual(response.status_code,200,response.text)
    async def drain(self,provider=None):
        await automation.run_conversations(self.db,self.scope,provider or TogetherProvider(key=''))
        await worker.run_once(self.db,self.scope)
    async def one(self,cap=10,contextual=False):
        data=await self.prepare(cap=cap,contextual=contextual);items=await self.get('/merchant/opportunities?search=Ananya')
        await self.draft(data,selected=[items['items'][0]['id']]);await self.approve()
        await worker.run_once(self.db,self.scope)
        data=await self.read();return data['journeys'][0]['id'],data['actions'][0]['id']

    async def test_200_cohort_city_date_selection_and_paginated_launch(self):
        data=await self.prepare(scale=True)
        self.assertEqual(data['counts'],{'total':200,'eligible':160,'excluded':40})
        overview=await self.get('/merchant/overview');self.assertEqual(overview['customer_base'],200)
        options=await self.get('/merchant/filters');self.assertEqual(len(options['cities']),5);self.assertTrue(all(city['count']==40 for city in options['cities']))
        first=await self.get('/merchant/opportunities?city=Mumbai&page_size=25')
        self.assertEqual(first['total'],40);self.assertEqual(first['eligible_total'],40)
        second=await self.get('/merchant/opportunities?city=Mumbai&page=2&page_size=25')
        self.assertEqual(len(second['items']),15)
        self.assertFalse({i['id'] for i in first['items']}&{i['id'] for i in second['items']})
        data,body=await self.draft(data,{'city':'Mumbai'},excluded=[second['items'][-1]['id']])
        self.assertEqual(data['draft']['selected_count'],39)
        review=await self.get('/merchant/launch?page_size=10&page=2')
        self.assertEqual(len(review['plan_review']['messages']),10);self.assertEqual(review['plan_review']['total'],39)
        self.assertEqual(review['plan_review']['audience_filters']['city'],'Mumbai')
        self.assertEqual((await self.get('/merchant/opportunities?date_from=2099-01-01'))['total'],0)
        self.assertEqual((await self.client.get(self.path()+'/merchant/opportunities?date_from=2026-11-02&date_to=2026-11-01')).status_code,422)
        self.assertEqual((await self.client.get(self.path()+'/merchant/opportunities?page_size=200')).status_code,422)
        body['facts_version']=999;self.assertEqual((await self.post('/merchant/audience',body)).status_code,409)
        await self.approve();journeys=await self.get('/merchant/journeys?city=Mumbai&page_size=10')
        self.assertEqual(journeys['total'],39);self.assertEqual(len(journeys['items']),10)
        other=await self.client.get(self.path(self.dev)+'/merchant/threads/'+journeys['items'][0]['id']);self.assertEqual(other.status_code,404)
        self.assertEqual((await self.post('/planning/facts',{'action':'seed_scale_demo'})).status_code,409)

    async def test_one_review_to_checkout_without_routine_merchant_approval(self):
        journey,initial=await self.one();key=str(uuid.uuid4())
        await self.choice(initial,'reorder',key);await self.choice(initial,'reorder',key)
        await self.drain();data=await self.get('/merchant/threads/'+journey)
        self.assertIsNone(data['journey']['owner_id']);self.assertEqual(data['proposals'],[])
        followup=[i for i in data['timeline'] if i['direction']=='outbound'][-1]
        self.assertIn('quantity 1',followup['text']);self.assertEqual(followup['buttons'][0]['id'],'same_item')
        await self.choice(followup['id'],'same_item');await self.drain()
        data=await self.get('/merchant/threads/'+journey)
        self.assertIn('Simulated checkout:',data['timeline'][-1]['text']);self.assertEqual(data['proposals'],[])
        self.assertIsNone(data['journey']['owner_id']);self.assertNotEqual(data['journey']['state'],'purchased')
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.checkout_preparations)),1)
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.confirmed_purchases)),0)
        await self.choice(initial,'reorder');await self.drain()
        self.assertEqual((await self.get('/merchant/threads/'+journey))['exception']['reason'],'stale_customer_choice')

    async def test_confirmed_reminder_and_free_text_quantity(self):
        journey,initial=await self.one()
        await self.choice(initial,'reorder')
        await self.drain();data=await self.get('/merchant/threads/'+journey);last=[i for i in data['timeline'] if i['direction']=='outbound'][-1]
        await self.choice(last['id'],'change_quantity');await self.drain();await self.text(journey,'2 please');await self.drain()
        last=(await self.get('/merchant/threads/'+journey))['timeline'][-1];self.assertIn('quantity 2',last['text'])
        await self.text(journey,'Remind me next week');await self.drain()
        last=(await self.get('/merchant/threads/'+journey))['timeline'][-1];self.assertIn('exact date and time',last['text'])
        due=datetime.now(timezone.utc)+timedelta(hours=2)
        await self.text(journey,'Remind me '+due.strftime('%Y-%m-%d %H:%M')+'Z');await self.drain()
        data=await self.get('/merchant/threads/'+journey);last=data['timeline'][-1]
        self.assertEqual(last['buttons'][0]['id'],'confirm_reminder')
        async with self.db.unit_of_work() as session:self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.reminders)),0)
        await self.choice(last['id'],'confirm_reminder');await self.drain()
        async with self.db.unit_of_work() as session:self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.reminders)),1)
        self.assertIn('saved for',(await self.get('/merchant/threads/'+journey))['timeline'][-1]['text'])

    async def test_caps_pause_support_and_unsent_choices(self):
        journey,initial=await self.one(cap=2)
        await self.command('pause');await self.choice(initial,'reorder');await self.drain()
        self.assertEqual(len((await self.get('/merchant/threads/'+journey))['timeline']),2)
        await self.command('resume');await self.drain()
        last=(await self.get('/merchant/threads/'+journey))['timeline'][-1]
        await self.choice(last['id'],'same_item');await self.drain()
        data=await self.get('/merchant/threads/'+journey);self.assertEqual(data['exception']['reason'],'weekly_contact_cap');self.assertIsNotNone(data['journey']['owner_id'])
        await self.text(journey,'STOP and refund please');await self.drain()
        data=await self.get('/merchant/threads/'+journey);self.assertEqual(data['journey']['state'],'opted_out')

    async def test_unsent_choice_and_provider_authority(self):
        data=await self.prepare();items=await self.get('/merchant/opportunities?search=Ananya');await self.draft(data,selected=[items['items'][0]['id']]);await self.approve()
        action=(await self.read())['actions'][0]
        response=await self.post('/merchant/whatsapp/demo-choice',{'action_id':action['id'],'button_id':'reorder','event_key':str(uuid.uuid4())})
        self.assertEqual(response.status_code,422)
        bad={**data['policy']['config_json'],'contextual_replies':True,'provider_processing':False}
        response=await self.post('/planning/policies',{'expected_revision':1,'config':bad});self.assertEqual(response.status_code,422)

    async def test_price_question_does_not_become_a_model_invented_offer(self):
        class PriceProvider:
            async def interpret(self,text,context):
                return IntentProposal(intents=[IntentItem(kind='offer_enquiry',evidence='price')],quantity=None,requested_product='this product',date_text=None,confidence=1.0),{'provider':'test','cost_usd':0}
        journey,initial=await self.one(contextual=True)
        await self.text(journey,'What is the price of this product?');await self.drain(PriceProvider())
        data=await self.get('/merchant/threads/'+journey)
        self.assertIsNone(data['journey']['owner_id']);self.assertIn('INR 499.00',data['timeline'][-1]['text']);self.assertEqual(data['proposals'],[])

    async def test_not_now_stops_progression_without_inventing_an_opt_out(self):
        journey,initial=await self.one();await self.choice(initial,'reorder');await self.drain()
        last=(await self.get('/merchant/threads/'+journey))['timeline'][-1]
        await self.choice(last['id'],'not_now');await self.drain()
        data=await self.get('/merchant/threads/'+journey)
        self.assertEqual(data['journey']['state'],'refused');self.assertIsNone(data['journey']['owner_id'])
        async with self.db.unit_of_work() as session:
            suppression=(await session.execute(sa.select(t.customer_evidence.c.value).where(t.customer_evidence.c.kind=='suppression').order_by(t.customer_evidence.c.effective_at.desc()).limit(1))).scalar_one()
            self.assertFalse(suppression['active'])
        await self.text(journey,'Yes reorder the same item');await self.drain()
        self.assertIn('quantity 1',(await self.get('/merchant/threads/'+journey))['timeline'][-1]['text'])

    async def test_approved_offer_is_quoted_confirmed_and_sent_automatically(self):
        await self.prepare()
        response=await self.post('/commerce/commands',{'action':'seed_offer'});self.assertEqual(response.status_code,200,response.text)
        response=await self.post('/commerce/offer-policy',{'expected_revision':0,'enabled':True,'approved_offer_ref':'DEMO-REORDER-25','unit_cost_minor':30000,'fulfillment_cost_minor':1000,'minimum_margin_minor':10000});self.assertEqual(response.status_code,200,response.text)
        data=await self.get('/merchant/planning');items=await self.get('/merchant/opportunities?search=Ananya');await self.draft(data,selected=[items['items'][0]['id']]);await self.approve();await worker.run_once(self.db,self.scope)
        journey=(await self.read())['journeys'][0]['id']
        await self.text(journey,'Is my DEMO-REORDER-25 coupon valid?');await self.drain()
        data=await self.get('/merchant/threads/'+journey);last=data['timeline'][-1]
        self.assertIn('INR 25.00 off this cart',last['text']);self.assertIsNone(data['journey']['owner_id'])
        await self.choice(last['id'],'same_item');await self.drain()
        async with self.db.unit_of_work() as session:
            prepared=(await session.execute(sa.select(t.checkout_preparations))).mappings().one()
            self.assertEqual(prepared['terms_json']['discount_minor'],2500);self.assertEqual(prepared['terms_json']['total_estimate_minor'],51400)
        self.assertIn('Simulated checkout:',(await self.get('/merchant/threads/'+journey))['timeline'][-1]['text'])

if __name__=='__main__':unittest.main()
