import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),access=JSON.parse(await fs.readFile(path.join(root,'backend/.local/stage05-qa.json'),'utf8')),output=path.join(root,'docs/implementation-evidence/stage09-screens');
const browser=await chromium.launch({channel:'msedge',headless:true}),context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),checks=[],accessibility=[];
try{
 await page.goto('http://127.0.0.1:8766/app/');await page.getByLabel('Login',{exact:true}).fill(access.login);await page.getByLabel('Password',{exact:true}).fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#workspace-selector')).toBeVisible();
 const demo=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');await page.getByLabel('Active workspace').selectOption(demo);
 for(const [route,title] of [['dashboard','Repeat Purchase Agent · operational overview'],['intelligence','AI & customer replies'],['outcomes','Observed outcomes & learning'],['connections','Together AI · conversation interpretation']]){
  await page.goto('http://127.0.0.1:8766/app/#/'+route);await expect(page.getByText(title,{exact:true})).toBeVisible();
  for(const width of [1440,1024,768,390,320]){await page.setViewportSize({width,height:1000});await page.screenshot({path:path.join(output,route+'-'+width+'.jpg'),type:'jpeg',quality:78,fullPage:true});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('Overflow '+route+' '+width);checks.push(route+' final layout '+width);}
  await page.setViewportSize({width:1440,height:1000});const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();accessibility.push({route,violations:result.violations.map(v=>({id:v.id,impact:v.impact}))});if(result.violations.length)throw new Error('Accessibility violations '+route);
 }
 await page.goto('http://127.0.0.1:8766/app/#/outcomes');await page.getByRole('button',{name:'Review Demo accounting',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('button',{name:'Review Demo accounting',exact:true})).toBeFocused();checks.push('Accounting dialog Escape and return focus');
 await page.evaluate(()=>document.documentElement.style.zoom='2');if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('200% CSS zoom overflow');checks.push('Outcomes observed at 200% CSS zoom without horizontal overflow');await page.evaluate(()=>document.documentElement.style.zoom='1');
 console.log(JSON.stringify({checks,accessibility},null,2));
}finally{await fs.writeFile(path.join(root,'docs/implementation-evidence/stage-09-final-visual.json'),JSON.stringify({checks,accessibility},null,2));await browser.close();}
