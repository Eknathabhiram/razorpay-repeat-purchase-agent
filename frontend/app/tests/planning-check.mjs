import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),privateLogin=JSON.parse(await fs.readFile(path.join(root,'backend/.local/stage02-qa.json'),'utf8'));
const output=path.join(root,'docs/implementation-evidence/stage03-screens');await fs.mkdir(output,{recursive:true});
const checks=[],errors=[];
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
page.on('pageerror',error=>errors.push(error.message));
try{
 await page.goto('http://127.0.0.1:8766/app/');
 await page.getByLabel('Login',{exact:true}).fill(privateLogin.login);await page.getByLabel('Password',{exact:true}).fill(privateLogin.password);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.locator('#workspace-selector')).toBeVisible();
 const demo=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');await page.getByLabel('Active workspace').selectOption(demo);
 await page.getByRole('link',{name:'Planning',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Commerce planning',exact:true})).toBeVisible();
 if(await page.getByRole('button',{name:'Load synthetic history',exact:true}).count())await page.getByRole('button',{name:'Load synthetic history',exact:true}).click();
 await expect(page.getByText('Laundry liquid · 1 L',{exact:true}).first()).toBeVisible();
 await page.locator('#fallback-days').fill('30');await page.getByRole('button',{name:'Review planning policy',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('3 eligible');await page.getByRole('button',{name:'Save planning policy',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('heading',{name:'Opportunity audience · 3 eligible, 6 excluded',exact:true})).toBeVisible();
 checks.push('Persisted synthetic evidence produces three eligible and six excluded opportunities');
 await page.getByRole('checkbox',{name:'Select Rahul Verma',exact:true}).uncheck();await page.getByRole('button',{name:'Save draft revision',exact:true}).click();
 await expect(page.getByText(/Draft revision .* · 2 selected/)).toBeVisible();checks.push('Editable selection saves exact immutable two-customer draft');
 await page.locator('.planning-person').filter({hasText:'Ananya Rao'}).getByRole('button',{name:'Review evidence'}).click();
 await expect(page.getByRole('dialog')).toContainText('same variant median');await expect(page.getByRole('dialog')).toContainText('repeat_window_v1');
 await page.screenshot({path:path.join(output,'evidence-1440.jpg'),type:'jpeg',quality:82});await page.keyboard.press('Escape');checks.push('Evidence drawer shows exact variant, delivery dates and estimator provenance');
 await page.locator('#fallback-days').fill('');await page.getByRole('button',{name:'Review planning policy',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('2 eligible');await expect(page.getByRole('dialog')).toContainText('Existing draft requires a new revision');
 await page.screenshot({path:path.join(output,'policy-diff-1440.jpg'),type:'jpeg',quality:82});await page.getByRole('button',{name:'Save planning policy',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByText('Facts or policy changed. Create a fresh revision.',{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByText('Facts or policy changed. Create a fresh revision.',{exact:true})).toBeVisible();checks.push('Policy impact preview excludes sparse history and stale draft survives reload');
 for(const width of [1440,1024,768,390,320]){
   await page.setViewportSize({width,height:1000});await page.screenshot({path:path.join(output,'planning-'+width+'.jpg'),type:'jpeg',quality:78,fullPage:true});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);if(overflow)throw new Error('Horizontal overflow at '+width);checks.push('Planning reflows at '+width+'px');
 }
 if(errors.length)throw new Error(errors.join('\n'));
 console.log(JSON.stringify({checks,errors},null,2));
}finally{await fs.writeFile(path.join(root,'docs/implementation-evidence/stage-03-browser.json'),JSON.stringify({checks,errors},null,2));await browser.close();}
