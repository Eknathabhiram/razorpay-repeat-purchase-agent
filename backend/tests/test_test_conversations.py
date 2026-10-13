import uuid,unittest,json
from app.intelligence_models import IntentProposal,IntentItem
import tests.test_foundation as foundation
class FakeAI:
    configured=True
    async def interpret(self,text,context):
        assert 'phone' not in json.dumps(context).lower()
        return IntentProposal(intents=[IntentItem(kind='clarification',evidence=text)],quantity=None,requested_product=None,date_text=None,confidence=1.0),{'provider':'together','model':'test-model','latency_ms':1,'attempts':1}
class TestConversations(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown
    async def start(self,mode='preview',key=None):
        self.app.state.together=FakeAI()
        original=self.app.state.shopify.snapshot
        if not getattr(self,'catalogue_mock',False):
            async def snapshot():
                data=await original();data['products']=[{'id':'synthetic-product','title':'Synthetic laundry','variants':{'nodes':[{'id':'synthetic-variant','price':'499.00','sku':'TEST-LAUNDRY','inventoryQuantity':10}]}}];return data
            self.app.state.shopify.snapshot=snapshot;self.catalogue_mock=True
        self.base='/api/v1/workspaces/'+self.demo['id']+'/test-conversations'
        catalogue=await self.client.get(self.base+'/catalogue');self.assertEqual(catalogue.status_code,200,catalogue.text)
        variant=catalogue.json()['data']['products'][0]['variant_id']
        return await self.client.post(self.base,headers={**self.headers,'Idempotency-Key':key or str(uuid.uuid4())},json={'phone':'+919000000001','variant_id':variant,'confirmed_own_number':True,'confirmed_provider_processing':True,'mode':mode})
    async def respond(self,data,**reply):
        return await self.client.post(self.base+'/'+data['id']+'/reply',headers={**self.headers,'Idempotency-Key':str(uuid.uuid4())},json={'expected_version':data['version'],**reply})
    async def test_no_shows_reasons_and_price_comes_from_shopify(self):
        response=await self.start();self.assertEqual(response.status_code,200,response.text);data=response.json()['data']
        self.assertFalse(data['sent_to_phone']);self.assertNotIn('+919000000001',response.text)
        response=await self.respond(data,choice='no');self.assertEqual(response.status_code,200,response.text);data=response.json()['data']
        self.assertEqual([b['id'] for b in data['timeline'][-1]['buttons']],['price','later','support'])
        response=await self.respond(data,choice='price');self.assertEqual(response.status_code,200,response.text)
        self.assertIn('No discount is approved',response.json()['data']['timeline'][-1]['text'])
        wrong=await self.client.get('/api/v1/workspaces/'+self.dev['id']+'/test-conversations/'+data['id']);self.assertEqual(wrong.status_code,404)
    async def test_actual_send_is_blocked_and_start_is_idempotent(self):
        response=await self.start('whatsapp');self.assertEqual(response.status_code,503,response.text)
        key=str(uuid.uuid4());first=await self.start(key=key);second=await self.start(key=key)
        self.assertEqual(first.status_code,200,first.text);self.assertEqual(first.json()['data'],second.json()['data'])
    async def test_stop_blocks_further_replies_and_stale_version_cannot_replay(self):
        response=await self.start();self.assertEqual(response.status_code,200,response.text);data=response.json()['data']
        changed=await self.respond(data,choice='yes');self.assertEqual(changed.status_code,200,changed.text)
        stale=await self.respond(data,choice='no');self.assertEqual(stale.status_code,409)
        stopped=await self.respond(changed.json()['data'],text='STOP');self.assertEqual(stopped.status_code,200,stopped.text)
        self.assertEqual(stopped.json()['data']['state'],'opted_out')
        held=await self.respond(stopped.json()['data'],text='yes');self.assertEqual(held.status_code,422)
if __name__=='__main__':unittest.main()
