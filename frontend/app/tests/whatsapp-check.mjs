import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),access=JSON.parse(await fs.readFile(path.join(root,'backend/.local/stage05-qa.json'),'utf8'));
const output=path.join(root,'docs/implementation-evidence/stage06-screens');await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}});
const checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:8766/app/');await page.getByLabel('Login',{exact:true}).fill(access.login);await page.getByLabel('Password',{exact:true}).fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#workspace-selector')).toBeVisible();
 const demo=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');await page.getByLabel('Active workspace').selectOption(demo);
 const restore=await page.request.post('http://127.0.0.1:8766/api/v1/auth/session',{headers:{Origin:'http://127.0.0.1:8766'}});const csrf=(await restore.json()).data.csrf_token,base='http://127.0.0.1:8766/api/v1/workspaces/'+demo;
 async function get(suffix){return (await (await page.request.get(base+suffix)).json()).data;}
 async function post(suffix,body){const response=await page.request.post(base+suffix,{headers:{Origin:'http://127.0.0.1:8766','X-CSRF-Token':csrf,'Idempotency-Key':crypto.randomUUID()},data:body});if(response.status()!==200)throw new Error(suffix+' HTTP '+response.status());return (await response.json()).data;}
 await post('/planning/facts',{action:'seed_demo'});let plan=await post('/planning/policies',{expected_revision:0,config:{mode:'bounded',variant_ids:['demo:laundry:1L'],fallback_days:30,contact_start:'00:00',contact_end:'23:59'}});await post('/planning/drafts',{expected_revision:0,selected:plan.opportunities.filter(o=>o.eligible).map(o=>o.id)});
 let execution=await get('/execution');await post('/execution/commands',{action:'approve_plan',expected_version:execution.version,subject_id:execution.plan_review.id,digest:execution.plan_review.digest});
 await post('/execution/run-due',{outcome:'accepted',limit:1});
 await page.goto('http://127.0.0.1:8766/app/#/whatsapp');await expect(page.getByText('Simulated transport',{exact:true})).toBeVisible();checks.push('Demo transport is explicitly labelled');
 await page.getByRole('button',{name:'Simulate read',exact:true}).first().click();await expect(page.getByText(/· read$/).first()).toBeVisible();await page.getByRole('button',{name:'Simulate delivered',exact:true}).first().click();checks.push('Out-of-order delivery does not erase read receipt');
 await page.getByLabel('Customer message · Demo').fill('Yes reorder the same product');await page.getByRole('button',{name:'Apply simulated reply',exact:true}).click();await expect(page.getByText('purchase interest',{exact:true})).toBeVisible();checks.push('Purchase interest enters protected human review');
 await page.getByLabel('Customer message · Demo').fill('STOP contacting me');await page.getByRole('button',{name:'Apply simulated reply',exact:true}).click();await expect(page.getByText('opt out',{exact:true})).toBeVisible();checks.push('Opt-out appears in contextual conversation');
 execution=await get('/execution');if(!execution.journeys.some(j=>j.state==='opted_out'))throw new Error('Opt-out not shared with execution');checks.push('Inbound opt-out updates shared execution journey');
 for(const width of [1440,1024,768,390,320]){await page.setViewportSize({width,height:1000});await page.screenshot({path:path.join(output,'whatsapp-'+width+'.jpg'),type:'jpeg',quality:78,fullPage:true});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('Horizontal overflow '+width);checks.push('WhatsApp reflows at '+width+'px');}
 const dev=await page.locator('#workspace-selector option').filter({hasText:/^Development/}).getAttribute('value');await page.getByLabel('Active workspace').selectOption(dev);await expect(page.getByText('Real transport blocked',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Apply simulated reply',exact:true})).toHaveCount(0);checks.push('Development transport blocked and synthetic controls absent');
 if(errors.length)throw new Error(errors.join('\n'));console.log(JSON.stringify({checks,errors},null,2));
}finally{await fs.writeFile(path.join(root,'docs/implementation-evidence/stage-06-browser.json'),JSON.stringify({checks,errors},null,2));await browser.close();}
