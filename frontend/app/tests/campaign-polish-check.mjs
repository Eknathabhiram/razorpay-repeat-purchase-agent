import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),access=JSON.parse(await fs.readFile(path.join(root,'backend/.local/merchant-qa.json'),'utf8'));
const output=path.join(root,'docs/ux-reviews/2026-10-13/campaign-polish');await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),context=await browser.newContext({viewport:{width:1440,height:1050},reducedMotion:'reduce'}),page=await context.newPage();
const errors=[],checks=[],accessibility=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:8766/app/');await page.getByLabel('Login',{exact:true}).fill(access.login);await page.getByLabel('Password',{exact:true}).fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#workspace-selector')).toBeVisible();
 const demo=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).first().getAttribute('value');
 const url=view=>'http://127.0.0.1:8766/app/#/'+view+(view.includes('?')?'&':'?')+'workspace='+demo;
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1050});
  for(const view of ['dashboard','analytics','launch?step=setup']){
   await page.goto(url(view));await expect(page.locator('#workspace')).toBeVisible();await expect(page.locator('.loading-view')).toHaveCount(0);
   if(view==='analytics')await expect(page.getByRole('heading',{name:'Campaign analytics',exact:true})).toBeVisible();
   if(view.startsWith('launch'))await expect(page.getByRole('group',{name:'Choose products',exact:true})).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),view+' '+width+' overflow').toBeTruthy();
   const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();accessibility.push({view,width,violations:result.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))});
   await page.screenshot({path:path.join(output,view.split('?')[0]+'-'+width+'.png'),fullPage:true});
  }
 }
 checks.push('Dashboard, campaign setup and separate analytics render at 1440, 390 and 320 px without horizontal overflow');
 await page.setViewportSize({width:1440,height:1050});await page.goto(url('launch?step=setup'));await expect(page.getByLabel('Search product catalogue',{exact:true})).toBeVisible();await page.getByLabel('Search product catalogue',{exact:true}).fill('no-match-unique-2099');await expect(page.getByText('No products match this search.',{exact:true})).toBeVisible();await page.getByLabel('Search product catalogue',{exact:true}).fill('');await expect(page.locator('.product-option').first()).toBeVisible();checks.push('Searchable product catalogue shows a recoverable no-results state');
 await page.getByRole('button',{name:'Select shown',exact:true}).click();await page.getByRole('button',{name:'Clear',exact:true}).click();await expect(page.getByRole('button',{name:'Review planning policy',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Continue to audience',exact:true})).toBeDisabled();checks.push('Clearing product scope blocks policy review and continuation; no persistent changes or outreach performed');
 await page.goto(url('dashboard'));await page.getByRole('link',{name:'Analytics',exact:true}).click();await expect(page.getByRole('heading',{name:'Campaign analytics',exact:true})).toBeVisible();checks.push('Analytics is reachable directly from merchant navigation');
 expect(errors).toEqual([]);expect(accessibility.flatMap(x=>x.violations)).toEqual([]);
 await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({checks,errors,accessibility},null,2));console.log(JSON.stringify({checks,errors,accessibility},null,2));
}finally{await browser.close();}
