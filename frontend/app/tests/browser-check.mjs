import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..');
const credentials=JSON.parse(await fs.readFile(path.join(root,'backend/.local/stage02-qa.json'),'utf8'));
const output=path.join(root,'docs/implementation-evidence/stage02-screens');
await fs.mkdir(output,{recursive:true});
const results={checks:[],screens:[],consoleErrors:[]};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();
page.on('pageerror',error=>results.consoleErrors.push(error.message));
function record(name){results.checks.push(name);console.log('PASS '+name);}
async function nav(route){
  const workspaceId=await page.locator('#workspace-selector').inputValue().catch(()=>null);
  await page.goto('http://127.0.0.1:8766/app/#/'+route+(workspaceId?'?workspace='+workspaceId:''));
  await expect(page.locator('#workspace')).toBeVisible();
  const headings={dashboard:'Needs your attention',activity:'Customer journeys',settings:'Operating policy',
    plan:'Repeat purchase plan',outcomes:'Outcomes and learning',connections:'Connections'};
  if(route==='dashboard'&&(await page.locator('#workspace-selector option:checked').textContent()).startsWith('Development'))
    await expect(page.getByRole('heading',{name:'The agent engine is not connected here',exact:true})).toBeVisible();
  else if(route==='plan')await expect(page.getByRole('heading',{name:/^(Repeat purchase plan|Renew plan approval)$/})).toBeVisible();
  else if(headings[route])
    await expect(page.getByRole('heading',{name:headings[route],exact:true}).first()).toBeVisible();
}
async function scenario(name){
  await page.getByRole('button',{name:'Demo mode',exact:true}).click();
  await page.getByRole('button',{name:'Manage demo scenarios',exact:true}).click();
  await page.locator('dialog .service-row').filter({hasText:name}).getByRole('button',{name:'Load',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
}
async function shot(name){
  await page.screenshot({path:path.join(output,name+'.jpg'),type:'jpeg',quality:82,fullPage:!(await page.getByRole('dialog').count()),animations:'disabled'});
  results.screens.push(name+'.jpg');
}
try{
  await page.goto('http://127.0.0.1:8766/app/');
  await page.getByLabel('Login',{exact:true}).fill(credentials.login);
  await page.getByLabel('Password',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Repeat Purchase Agent',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Needs your attention',exact:true})).toBeVisible();
  record('Real owner session and typed demo read model');
  await scenario('Active plan');
  await page.reload();
  await expect(page.getByRole('heading',{name:'Needs your attention',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>Object.keys(localStorage))).toEqual([]);
  record('Reload restores session without localStorage authority');

  for(const width of [1440,1024,768,390,320]){
    await page.setViewportSize({width,height:1000});
    for(const route of ['dashboard','activity','settings','plan','outcomes','connections']){
      await nav(route);
      await expect(page.getByRole('status').filter({hasText:'Loading your workspace'})).toHaveCount(0);
      const size=await page.evaluate(()=>({content:document.documentElement.scrollWidth,viewport:innerWidth}));
      expect(size.content,'Horizontal overflow: '+route+' '+width).toBeLessThanOrEqual(size.viewport);
      await shot(route+'-'+width);
    }
    record('Six key screens reflow at '+width+'px');
  }
  await page.setViewportSize({width:1440,height:1000});
  await nav('dashboard');
  const review=page.getByRole('button',{name:'Review message',exact:true});
  await review.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('button',{name:'Close details',exact:true})).toBeFocused();
  for(let index=0;index<8;index++)await page.keyboard.press('Tab');
  expect(await page.evaluate(()=>!!document.activeElement?.closest('dialog'))).toBe(true);
  await shot('checkout-drawer-1440');
  await page.keyboard.press('Escape');
  await expect(review).toBeFocused();
  record('Drawer initial focus, keyboard containment, Escape and focus return');

  await page.getByRole('button',{name:'Pause agent',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Pause agent',exact:true}).click();
  await expect(page.getByText('Outreach is paused',{exact:true})).toBeVisible();
  await review.click();
  await expect(page.getByRole('button',{name:'Approve & send',exact:true})).toBeDisabled();
  await page.setViewportSize({width:390,height:844});await shot('checkout-paused-390');
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Resume',exact:true}).first().click();
  await page.getByRole('button',{name:'Resume agent',exact:true}).click();
  record('Pause blocks sending; responsive paused drawer; safe resume');

  await page.setViewportSize({width:1440,height:1000});await nav('settings');
  await page.getByLabel('Total contacts per customer').fill('3');
  await page.getByRole('button',{name:'Review policy changes',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('2 → 3');
  await page.getByRole('button',{name:'Save policy',exact:true}).click();
  await expect(page.getByText('Your policy changed.',{exact:false})).toBeVisible();
  await nav('plan');
  await expect(page.getByLabel('Meera Shah',{exact:false})).toHaveCount(0);
  await page.getByRole('button',{name:'Approve 2 customers',exact:true}).click();
  await nav('outcomes');
  await expect(page.getByText('Meera Shah · LE-1048',{exact:true})).toBeVisible();
  record('Policy diff invalidates plan; new buyer excluded; prior order retained');

  await nav('dashboard');await review.click();
  await page.getByRole('button',{name:'Approve & send',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.reload();await expect(page.getByRole('heading',{name:'Customer activity'})).toBeVisible();
  await page.locator('.customer-row').filter({hasText:'Rahul Mehta'}).click();
  await expect(page.getByRole('button',{name:'Checkout pending',exact:true})).toBeDisabled();
  await expect(page.getByText('Simulated message receipt saved. Payment remains pending.',{exact:true})).toBeVisible();
  await page.keyboard.press('Escape');
  record('Reviewed checkout message persists; no payment fabricated');

  await scenario('First plan');await nav('plan');
  await page.getByLabel('Meera Shah',{exact:false}).uncheck();
  await page.getByRole('button',{name:'Approve 2 customers',exact:true}).click();
  await nav('outcomes');await expect(page.getByRole('heading',{name:'No confirmed orders yet',exact:true})).toBeVisible();
  await nav('activity');await page.locator('.customer-row').filter({hasText:'Rahul Mehta'}).click();
  await expect(page.getByText('No customer reply has been received in this scenario.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Approve & send',exact:true})).toBeDisabled();
  await page.keyboard.press('Escape');
  record('First plan schedules only; no invented reply, checkout or purchase');

  await scenario('New installation');await nav('agent');
  await page.getByRole('button',{name:'Install agent',exact:true}).click();
  await page.getByLabel('Approval mode',{exact:true}).selectOption('bounded');
  await page.getByRole('button',{name:'Continue',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('Review source access');
  await page.getByRole('button',{name:'Continue',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('Installation alone');
  await page.getByRole('button',{name:'Activate demo agent',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('No customer contact is authorised yet.');
  await shot('installation-1440');
  await page.getByRole('button',{name:'Review first audience',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Repeat purchase plan',exact:true})).toBeVisible();
  record('Configure / Connectors / Review / Activate and audience separation');

  await nav('entry');
  await page.getByRole('button',{name:'Continue to verification',exact:true}).click();
  await page.getByRole('button',{name:'Continue with simulated verification',exact:true}).click();
  await page.getByRole('button',{name:'Open payments home',exact:true}).click();
  await page.getByRole('button',{name:'Explore Agent Studio',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Agent Studio',exact:true})).toBeVisible();
  record('Separate entry / verification / payments / Studio discovery continuity');

  const developmentId=await page.locator('#workspace-selector option').filter({hasText:/^Development/}).getAttribute('value');
  await page.getByLabel('Active workspace').selectOption(developmentId);
  await nav('dashboard');
  await expect(page.getByRole('heading',{name:'The agent engine is not connected here',exact:true})).toBeVisible();
  await nav('connections');
  await expect(page.getByRole('cell',{name:'TEST-LAUNDRY-1L',exact:true})).toBeVisible({timeout:60000});
  await expect(page.getByText('4 customer IDs/order counts read.',{exact:false})).toBeVisible();
  await shot('development-connections-1440');
  await page.setViewportSize({width:390,height:844});await shot('development-connections-390');
  record('Development has actual scoped Shopify reads; agent execution blocked');

  const demoId=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');
  await page.getByLabel('Active workspace').selectOption(demoId);
  await nav('dashboard');
  await page.setViewportSize({width:1440,height:1000});
  await page.evaluate(()=>{
    const sizes=[...document.querySelectorAll('body *')].map(el=>[el,parseFloat(getComputedStyle(el).fontSize),parseFloat(getComputedStyle(el).lineHeight)]);
    for(const [el,size,line] of sizes){el.style.fontSize=(size*2)+'px';if(Number.isFinite(line))el.style.lineHeight=(line*2)+'px';}
  });
  await shot('dashboard-enlarged-1440');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.reload();await expect(page.getByRole('heading',{name:'Needs your attention',exact:true})).toBeVisible();
  record('200% text enlargement remains within viewport');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Application owner sign-in',exact:true})).toBeVisible();
  record('Logout clears authenticated application state');
  expect(results.consoleErrors).toEqual([]);
}catch(error){results.failure=error.message;await shot('failure');throw error;}
finally{
  await fs.writeFile(path.join(root,'docs/implementation-evidence/stage-02-browser.json'),JSON.stringify(results,null,2));
  await browser.close();
}
