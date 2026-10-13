import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('../..'),access=JSON.parse(await fs.readFile(path.join(root,'backend/.local/stage05-qa.json'),'utf8'));
const browser=await chromium.launch({channel:'msedge',headless:true}),context=await browser.newContext(),page=await context.newPage();
const checks=[];
try{
 await context.addInitScript(()=>{if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Synthetic permission denial','NotAllowedError');};});
 await page.goto('http://127.0.0.1:8766/app/');await page.getByLabel('Login',{exact:true}).fill(access.login);await page.getByLabel('Password',{exact:true}).fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#workspace-selector')).toBeVisible();
 const demo=await page.locator('#workspace-selector option').filter({hasText:/^Demo/}).getAttribute('value');await page.getByLabel('Active workspace').selectOption(demo);await page.goto('http://127.0.0.1:8766/app/#/intelligence');await expect(page.locator('#voice-customer')).toBeVisible();
 const rahul=await page.locator('#voice-customer option').filter({hasText:/Rahul Verma/}).first().getAttribute('value');await page.getByLabel('Test customer journey').selectOption(rahul);await page.getByRole('button',{name:'Start conversation test',exact:true}).click();await expect(page.getByRole('button',{name:'Interpret reviewed text',exact:true})).toBeVisible();
 await page.getByText('Optional browser voice · last priority',{exact:true}).click();await page.getByRole('button',{name:'Start microphone',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Synthetic permission denial');checks.push('Microphone denial shows a recoverable error without capturing audio');
 const restore=await page.request.post('http://127.0.0.1:8766/api/v1/auth/session',{headers:{Origin:'http://127.0.0.1:8766'}});const csrf=(await restore.json()).data.csrf_token,base='http://127.0.0.1:8766/api/v1/workspaces/'+demo;
 let data=(await (await page.request.get(base+'/intelligence')).json()).data;const active=data.sessions.find(s=>s.state==='active');
 const response=await page.request.post(base+'/voice-sessions/'+active.id+'/audio?sequence=1',{headers:{Origin:'http://127.0.0.1:8766','X-CSRF-Token':csrf,'Content-Type':'audio/wav'},data:await fs.readFile(path.join(root,'backend/.local/stage07-smoke.wav'))});
 if(response.status()!==200)throw new Error('Audio transcription HTTP '+response.status());await page.reload();await expect(page.getByRole('button',{name:'Confirm transcript & interpret',exact:true})).toBeVisible();checks.push('Real Together synthetic-audio transcript waits for explicit review');
 await page.getByRole('button',{name:'Confirm transcript & interpret',exact:true}).click();await expect(page.getByText('offer enquiry',{exact:true})).toBeVisible({timeout:45000});await expect(page.getByText('reminder',{exact:true})).toBeVisible();checks.push('Confirmed transcript uses the same compound-intent pipeline');
 const speech=page.waitForResponse(r=>r.url().endsWith('/speech')&&r.request().method()==='POST');await page.getByRole('button',{name:'Play Together reply',exact:true}).click();const audio=await speech;if(audio.status()!==200||!audio.headers()['content-type'].startsWith('audio/'))throw new Error('Speech reply failed');checks.push('Together reply audio is generated from the server-rendered text');
 await page.getByRole('button',{name:'Stop conversation test',exact:true}).click();await expect(page.getByRole('button',{name:'Interpret reviewed text',exact:true})).toHaveCount(0);checks.push('Stop closes the session and stops local capture/playback');
 console.log(JSON.stringify({checks},null,2));
}finally{await fs.writeFile(path.join(root,'docs/implementation-evidence/stage-07-voice-browser.json'),JSON.stringify({checks},null,2));await browser.close();}
