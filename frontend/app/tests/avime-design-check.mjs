import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),output=path.join(root,'docs/ux-reviews/2026-10-13/avime');await fs.mkdir(output,{recursive:true});
const access=JSON.parse(await fs.readFile('../../../Razorpay_Repeat_Agent_Codex_UI/backend/.local/owner-access.json','utf8'));
const browser=await chromium.launch({channel:'msedge',headless:true}),context=await browser.newContext({viewport:{width:1440,height:1050},reducedMotion:'reduce'}),page=await context.newPage();
const errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));const workspace='4b9786d5-3244-4adf-99dc-6e11539f568b';const url=view=>'http://127.0.0.1:8766/app/#/'+view+(view.includes('?')?'&':'?')+'workspace='+workspace;
try{
 await page.goto(url('agents'));await page.getByLabel('Login',{exact:true}).fill(access.login);await page.getByLabel('Password',{exact:true}).fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#workspace-selector')).toBeVisible();
 for(const width of [1440,1024,768,390,320]){await page.setViewportSize({width,height:1050});for(const view of ['agents']){await page.goto(url(view));await expect(page.locator('.loading-view')).toHaveCount(0);await expect(page.locator('#workspace')).toBeVisible();if(view.startsWith('launch'))await expect(page.locator('.avime-product-card')).toHaveCount(9);if(view==='dashboard')await expect(page.locator('.avime-metric')).toHaveCount(4);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),view+' '+width+' overflow').toBeTruthy();const text=await page.locator('body').innerText();expect(text).not.toMatch(/synthetic|demo|all times in ist/i);expect(text).toContain('Avime Herbal');const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();expect(axe.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})),view+' '+width).toEqual([]);checks.push({view,width,overflow:false,accessibility_violations:0});if([1440,390].includes(width))await page.screenshot({path:path.join(output,view.split('?')[0]+'-'+width+'.png'),fullPage:true});}}
 expect(errors).toEqual([]);await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({checks,errors,page:'My agents'},null,2));console.log(JSON.stringify({screens:checks.length,errors,checks:'My agents: desktop, tablet, mobile, copy and accessibility checks passed'},null,2));
}finally{await browser.close();}
