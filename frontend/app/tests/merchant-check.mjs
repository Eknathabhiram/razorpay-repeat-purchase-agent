import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),access=JSON.parse(await fs.readFile(path.join(root,'backend/.local/merchant-qa.json'),'utf8'));
const output=path.join(root,'docs/ux-reviews/2026-10-13/implemented');await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),context=await browser.newContext({viewport:{width:1440,height:1050},reducedMotion:'reduce'}),page=await context.newPage();
const checks=[],errors=[],accessibility=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:8766/app/');await page.getByLabel('Login',{exact:true}).fill(access.login);await page.getByLabel('Password',{exact:true}).fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#workspace-selector')).toBeVisible();
 const demo=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');await page.getByLabel('Active workspace').selectOption(demo);
 const auth=await page.request.post('http://127.0.0.1:8766/api/v1/auth/session',{headers:{Origin:'http://127.0.0.1:8766'}});const csrf=(await auth.json()).data.csrf_token,base='http://127.0.0.1:8766/api/v1/workspaces/'+demo;
 async function get(suffix){const r=await page.request.get(base+suffix);expect(r.status()).toBe(200);return (await r.json()).data;}
 async function post(suffix,body){const r=await page.request.post(base+suffix,{headers:{Origin:'http://127.0.0.1:8766','X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},data:body});const result=await r.json();expect(r.status(),suffix+' '+JSON.stringify(result.error??{})).toBe(200);return result.data;}
 const url=view=>'http://127.0.0.1:8766/app/#/'+view+'?workspace='+demo;
 let customer;
 if(!process.argv.includes('--visual-only')){
 await post('/planning/facts',{action:'seed_scale_demo'});
 await post('/planning/policies',{expected_revision:0,config:{variant_ids:['demo:laundry:1L'],fallback_days:30,contact_start:'00:00',contact_end:'23:59',contact_cap:10,budget_minor:500000,mode:'bounded',conversation_automation:true,contextual_replies:true,provider_processing:true}});
 await page.reload();
 await page.goto(url('planning'));await expect(page.getByText('160 selected across all pages',{exact:true})).toBeVisible();
 await page.getByLabel('Customer city',{exact:true}).selectOption('Mumbai');await expect(page.getByText('1–25 of 40',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Select all filtered eligible',exact:true}).click();await expect(page.getByText('40 selected across all pages',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('26–40 of 40',{exact:true})).toBeVisible();await page.getByRole('checkbox',{name:/Select Customer/}).first().uncheck();await expect(page.getByText('39 selected across all pages',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear filters',exact:true}).click();await expect(page.getByText('39 selected across all pages',{exact:true})).toBeVisible();await expect(page.getByText('1–25 of 200',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Select all filtered eligible',exact:true}).click();await expect(page.getByText('160 selected across all pages',{exact:true})).toBeVisible();
 await page.getByLabel('Reorder window · from',{exact:true}).fill('2099-01-01');await expect(page.getByText('No matching opportunities.',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Clear filters',exact:true}).click();await expect(page.getByText('1–25 of 200',{exact:true})).toBeVisible();
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(output,'audience-1440.png'),fullPage:true});checks.push('200 customers; city/date filters; selection persists across pages and view filters');
 await page.getByRole('button',{name:'Save cohort for review',exact:true}).click();await expect(page.getByText('Draft revision 1 · 160 selected',{exact:true})).toBeVisible();
 await page.goto(url('execution'));await expect(page.getByText('Initial review, then automatic conversations',{exact:true})).toBeVisible();await expect(page.getByText('1–25 of 160',{exact:true})).toBeVisible();await page.screenshot({path:path.join(output,'launch-1440.png'),fullPage:true});
 await page.getByRole('button',{name:'Review launch approval',exact:true}).click();await page.getByRole('button',{name:'Approve & launch Demo cohort',exact:true}).click();await expect(page.getByRole('button',{name:'Open conversations',exact:true})).toBeVisible();checks.push('Single initial approval launches 160 same-product journeys');
 customer=(await get('/merchant/journeys?search=Customer%2000001')).items[0];
 await expect.poll(async()=>{const d=await get('/merchant/threads/'+customer.id);return d.timeline.filter(i=>i.direction==='outbound').length;},{timeout:120000,intervals:[2000]}).toBeGreaterThan(0);
 await page.goto(url('whatsapp')+'&journey='+customer.id);await expect(page.locator('.thread-heading h3')).toHaveText('Customer 00001');await page.getByRole('button',{name:'Demo customer preview',exact:true}).click();await page.locator('.demo-customer-preview').getByRole('button',{name:'Reorder',exact:true}).click();
 await expect(page.locator('.chat-bubble').filter({hasText:'Would you like the same variant and quantity?'})).toBeVisible({timeout:120000});await expect(page.locator('.pending-message')).toHaveCount(0);
 await page.locator('.demo-customer-preview').getByRole('button',{name:'Same item × 1',exact:true}).click();await expect(page.locator('.chat-bubble').filter({hasText:'Simulated checkout:'})).toBeVisible({timeout:120000});checks.push('Automatic button-led confirmation and checkout; no routine message approvals');
 await page.getByLabel('Or type a customer question · Demo',{exact:true}).fill('What is the price of this product?');await page.getByRole('button',{name:'Apply simulated customer message',exact:true}).click();await expect(page.locator('.chat-bubble').filter({hasText:'The current item price is INR 499.00'})).toBeVisible({timeout:120000});checks.push('Real Together intent interpretation of synthetic free text; deterministic verified price response');
 await page.getByRole('button',{name:'Close customer preview',exact:true}).click();await page.screenshot({path:path.join(output,'whatsapp-1440.png'),fullPage:true});
 await fs.writeFile(path.join(output,'workflow-verification.json'),JSON.stringify({checks,errors},null,2));
 }else{customer=(await get('/merchant/journeys?search=Customer%2000001')).items[0];checks.push('Visual recheck of the existing isolated 200-customer cohort and recorded automatic conversation');}
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:950});
  for(const view of ['dashboard','planning','execution','activity','whatsapp']){
   await page.goto(url(view)+(view==='whatsapp'?'&journey='+customer.id:''));await expect(page.locator('.loading-view')).toHaveCount(0);await expect(page.locator('#workspace')).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),view+' '+width).toBeTruthy();
   const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();accessibility.push({view,width,violations:result.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))});
   await page.evaluate(()=>window.scrollTo(0,0));if(width===1440||width===390)await page.screenshot({path:path.join(output,view+'-'+width+'.png'),fullPage:true});
  }
 }
 await page.goto(url('whatsapp')+'&journey='+customer.id);await page.getByRole('button',{name:'← Inbox',exact:true}).click();await expect(page.locator('.conversation-inbox')).toBeVisible();await page.locator('.conversation-filter-options summary').click();await page.getByLabel('Customer city',{exact:true}).selectOption('Mumbai');await expect.poll(async()=>(await get('/merchant/journeys?inbox=true&city=Mumbai')).total,{timeout:120000,intervals:[2000]}).toBe(40);await expect(page.getByText('1–25 of 40',{exact:true})).toBeVisible();checks.push('Mobile inbox back navigation and city filtering');
 expect(errors).toEqual([]);expect(accessibility.flatMap(a=>a.violations)).toEqual([]);checks.push('No runtime errors, horizontal overflow or automated WCAG AA violations at 1440/390/320');
 await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({checks,accessibility,errors},null,2));console.log(JSON.stringify({checks,accessibility,errors},null,2));
}finally{await browser.close();}
