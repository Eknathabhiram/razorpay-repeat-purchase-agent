import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..');
const credentials=JSON.parse(await fs.readFile(path.join(root,'backend/.local/stage02-qa.json'),'utf8'));
const results=[];
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();
const output=path.join(root,'docs/implementation-evidence/stage02-screens');
async function nav(route){
  const id=await page.locator('#workspace-selector').inputValue();
  await page.goto('http://127.0.0.1:8766/app/#/'+route+'?workspace='+id);
}
async function reset(name){
  await page.getByRole('button',{name:'Demo mode',exact:true}).click();
  await page.getByRole('button',{name:'Manage demo scenarios',exact:true}).click();
  await page.locator('dialog .service-row').filter({hasText:name}).getByRole('button',{name:'Load',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
}
try{
  await page.goto('http://127.0.0.1:8766/app/');
  await page.getByLabel('Login',{exact:true}).fill(credentials.login);
  await page.getByLabel('Password',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Needs your attention',exact:true})).toBeVisible();
  await reset('Active plan');await nav('agents');
  await expect(page.getByRole('heading',{name:'My agents',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Open agent',exact:true}).click();
  await page.getByRole('button',{name:'Review message',exact:true}).click();
  await page.getByRole('button',{name:'Take over',exact:true}).click();
  await page.getByRole('button',{name:'Review message',exact:true}).click();
  await expect(page.getByText('You control this conversation.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Hand back',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  results.push('My Agents opens operating view; takeover survives drawer close and explicit handback');
  await page.getByRole('link',{name:'Settings',exact:true}).click();
  await expect(page.locator('#contact-end')).toBeVisible();
  await page.locator('#contact-end').fill('09:00');
  await page.getByRole('button',{name:'Review policy changes',exact:true}).click();
  await page.getByRole('button',{name:'Save policy',exact:true}).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('later than start time');
  await page.waitForTimeout(6500);
  await expect(page.getByRole('dialog').getByRole('alert')).toBeVisible();
  await page.screenshot({path:path.join(output,'policy-error-1440.jpg'),type:'jpeg',quality:82});
  await page.keyboard.press('Escape');
  await expect(page.locator('#contact-end')).toHaveValue('09:00');
  results.push('Invalid policy has persistent inline error and preserves unsaved draft');
  await reset('Disconnected commerce');await nav('plan');
  await expect(page.getByRole('button',{name:'Approve 3 customers',exact:true})).toBeDisabled();
  results.push('Disconnected source blocks plan approval');
  const developmentId=await page.locator('#workspace-selector option').filter({hasText:/^Development/}).getAttribute('value');
  await page.getByLabel('Active workspace').selectOption(developmentId);
  await page.route('**/api/v1/workspaces/*/connectors/*/store',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'TEST_UNAVAILABLE',message:'Test source unavailable.'}})}));
  await nav('connections');
  await expect(page.getByRole('heading',{name:'Store data unavailable',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Try again',exact:true})).toBeVisible();
  await page.screenshot({path:path.join(output,'connection-error-1440.jpg'),type:'jpeg',quality:82,fullPage:true});
  results.push('Provider read failure offers recovery without fabricated empty records');
  await page.unroute('**/api/v1/workspaces/*/connectors/*/store');
  await page.route('**/api/v1/me',async route=>{
    const response=await route.fetch(),body=await response.json();
    body.data.workspaces.forEach(w=>w.role='viewer');
    await route.fulfill({response,json:body});
  });
  const demoId=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');
  await page.getByLabel('Active workspace').selectOption(demoId);
  await nav('settings');await page.reload();
  await expect(page.getByRole('button',{name:'Review policy changes',exact:true})).toBeDisabled();
  results.push('Viewer membership projection disables policy mutation controls');
  console.log(JSON.stringify(results,null,2));
}finally{
  await fs.writeFile(path.join(root,'docs/implementation-evidence/stage-02-browser-edge-cases.json'),JSON.stringify(results,null,2));
  await browser.close();
}
