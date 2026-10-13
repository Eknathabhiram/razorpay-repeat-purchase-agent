import {test,expect} from './fixtures';
import AxeBuilder from '@axe-core/playwright';

test('key screens pass automated WCAG AA checks at desktop and mobile widths',async ({page})=>{
  test.setTimeout(120000);
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:900});
    for(const view of ['dashboard','planning','launch','execution','commerce','connections','settings','whatsapp']){
      await page.goto('#/'+view);await expect(page.locator('#workspace')).toBeVisible();await expect(page.locator('.loading-view')).toHaveCount(0);
      const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
      expect(result.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))).toEqual([]);
    }
  }
});

test('desktop and mobile merchant views render without overflow or runtime errors',async ({page},testInfo)=>{
  test.setTimeout(180000);
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  for(const width of [1440,768,390,320]){
    await page.setViewportSize({width,height:1000});
    for(const view of ['dashboard','activity','settings','planning','execution','commerce','connections','studio','agents','plan','outcomes']){
      await page.goto('#/'+view+'?workspace=demo');
      await expect(page.locator('#workspace')).toBeVisible();
      await expect(page.locator('.loading-view')).toHaveCount(0);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
      if((width===1440||width===390)&&['dashboard','planning','execution','commerce','connections'].includes(view)){
        await page.screenshot({path:testInfo.outputPath(view+'-'+width+'.png'),fullPage:true,animations:'disabled'});
      }
    }
  }
  expect(errors).toEqual([]);
});

test('drawer traps focus, restores it and leaves the action footer visible',async ({page},testInfo)=>{
  await page.setViewportSize({width:390,height:650});await page.goto('#/dashboard');
  const trigger=page.getByRole('button',{name:'Pause agent',exact:true});await trigger.click();
  const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();
  await expect(page.getByRole('button',{name:'Close details'})).toBeFocused();
  for(let i=0;i<12;i++)await page.keyboard.press('Tab');
  expect(await page.evaluate(()=>!!document.activeElement?.closest('dialog'))).toBeTruthy();
  const approve=dialog.getByRole('button',{name:'Pause agent',exact:true});
  const box=await approve.boundingBox();expect(box!.y+box!.height).toBeLessThanOrEqual(650);
  await page.screenshot({path:testInfo.outputPath('drawer-390.png'),animations:'disabled'});
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);await expect(trigger).toBeFocused();
});

test('mobile navigation supports keyboard dismissal and backdrop',async ({page})=>{
  await page.setViewportSize({width:390,height:800});await page.goto('#/dashboard');
  const toggle=page.getByRole('button',{name:'Open navigation',exact:true});await toggle.click();
  await expect(page.getByRole('link',{name:'Home',exact:true})).toBeFocused();
  await page.keyboard.press('Shift+Tab');await expect(page.getByRole('button',{name:'Help & support',exact:true})).toBeFocused();
  await page.keyboard.press('Escape');await expect(toggle).toBeFocused();
  await toggle.click();await page.locator('.navigation-backdrop').click({position:{x:350,y:100}});
  await expect(toggle).toHaveAttribute('aria-expanded','false');
});

test('launch explains the stages and keeps data, audience and approval distinct',async ({page})=>{
 await page.goto('#/launch?step=setup');await expect(page.getByRole('heading',{name:'Step 1: Data & limits'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Operating limits & automation'})).toBeVisible();await expect(page.getByRole('heading',{name:/Opportunity audience/})).toHaveCount(0);
 await page.getByRole('button',{name:'Continue to audience',exact:true}).click();await expect(page.getByRole('heading',{name:'Step 2: Choose audience'})).toBeVisible();
 await expect(page.getByRole('heading',{name:/Opportunity audience/})).toBeVisible();await expect(page.getByRole('heading',{name:'Operating limits & automation'})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Continue to initial review',exact:true})).toBeDisabled();
});

test('session outage is recoverable and is distinguished from signed-out state',async ({page})=>{
  await page.route('**/api/v1/auth/session',route=>route.fulfill({status:503,body:'Service unavailable'}));
  await page.goto('');await expect(page.getByRole('heading',{name:'Unable to reach your workspace'})).toBeVisible();
  await expect(page.getByText('The service is temporarily unavailable.')).toBeVisible();
  await page.unroute('**/api/v1/auth/session');await page.getByRole('button',{name:'Try again'}).click();
  await expect(page.getByRole('heading',{name:'Needs your decision'})).toBeVisible();
});

test('expired session clears workspace data and requires sign-in',async ({page})=>{
  await page.goto('#/dashboard');await expect(page.locator('#workspace')).toBeVisible();
  await page.route('**/api/v1/workspaces/*/merchant/planning',route=>route.fulfill({status:401,json:{error:{message:'Session expired.'}}}));
  await page.getByRole('link',{name:'Settings',exact:true}).click();
  await expect(page.getByLabel('Password',{exact:true})).toBeVisible();
  await expect(page.getByText('Your session expired. Sign in to continue.')).toBeVisible();await expect(page.locator('#workspace')).toHaveCount(0);
});

test('failed logout keeps the session visible and explains recovery',async ({page})=>{
  await page.goto('#/dashboard');await page.route('**/api/v1/auth/logout',route=>route.fulfill({status:503,body:'Unavailable'}));
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await expect(page.locator('#workspace')).toBeVisible();await expect(page.getByRole('alert')).toContainText('temporarily unavailable');
});

test('unknown routes provide a clear recovery action',async ({page})=>{
  await page.goto('#/missing-page');await expect(page.getByRole('heading',{name:'Page not found'})).toBeVisible();
  await page.getByRole('button',{name:'Return to dashboard'}).click();await expect(page.getByRole('heading',{name:'Needs your decision'})).toBeVisible();
});

test('background refresh failure preserves data and blocks approvals',async ({page})=>{
  await page.goto('#/dashboard');await expect(page.getByRole('heading',{name:'Needs your decision'})).toBeVisible();
  await page.route('**/api/v1/workspaces/*/merchant/overview',route=>route.fulfill({status:503,body:'Unavailable'}));
  await expect(page.getByRole('alert')).toContainText('Showing the last loaded data',{timeout:25000});
  await expect(page.getByRole('heading',{name:'Needs your decision'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Pause agent',exact:true})).toBeDisabled();
});
