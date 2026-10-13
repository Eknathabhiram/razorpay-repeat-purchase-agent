import {test,expect} from './fixtures';
import AxeBuilder from '@axe-core/playwright';
test('test tab reads catalogue, distinguishes phone sending and stays accessible',async({page})=>{
 await page.route('**/api/v1/workspaces/*/test-conversations/catalogue',route=>route.fulfill({json:{data:{shop_name:'Connected test store',domain:'test.myshopify.com',checked_at:'2026-10-13T08:00:00Z',agent_configured:true,whatsapp_enabled:false,whatsapp_blockers:['Interactive content and callbacks are not verified.'],products:[{variant_id:'shopify:1',title:'Laundry Liquid - 1 L',sku:'TEST-LAUNDRY',price:'499.00',currency:'INR',stock:99}]}}}));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('#/whatsapp-test');
  await expect(page.getByRole('heading',{name:'WhatsApp test',exact:true})).toBeVisible();
  await expect(page.getByRole('radio',{name:/Laundry Liquid/})).toBeVisible();
  await expect(page.getByRole('button',{name:'Send to my WhatsApp · unavailable',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Start browser preview',exact:true})).toBeDisabled();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();expect(results.violations.map(v=>v.id)).toEqual([]);
 }
});
