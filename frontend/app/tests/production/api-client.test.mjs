import {test,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {api,ApiError,login,clearSession} from '../../src/api/client.ts';

const originalFetch=globalThis.fetch;
afterEach(()=>{globalThis.fetch=originalFetch;clearSession();});
test('a proxy HTML error produces actionable copy',async()=>{
  globalThis.fetch=async()=>new Response('<h1>Bad gateway</h1>',{status:502});
  await assert.rejects(api('/test'),e=>e instanceof ApiError&&e.status===502&&e.message.includes('temporarily unavailable'));
});
test('successful malformed payloads are rejected',async()=>{
  globalThis.fetch=async()=>Response.json({unexpected:true});
  await assert.rejects(api('/test'),e=>e.code==='INVALID_RESPONSE');
});
test('network failures during writes explain uncertain outcomes and do not retry',async()=>{
  let calls=0;globalThis.fetch=async()=>{calls++;throw new TypeError('Failed to fetch');};
  await assert.rejects(api('/test','POST',{},'exact-command'),e=>e.code==='NETWORK_ERROR'&&e.message.includes('may have been saved'));
  assert.equal(calls,1);
});
test('request timeout provides recovery',async()=>{
  globalThis.fetch=async(_,options)=>new Promise((resolve,reject)=>{
    options.signal.addEventListener('abort',()=>reject(options.signal.reason),{once:true});
    setTimeout(resolve,30); // Keep the event loop alive until the short timeout aborts.
  });
  await assert.rejects(api('/test','GET',undefined,undefined,{timeoutMs:5}),e=>e.code==='TIMEOUT');
});
test('query cancellation stays a cancellation',async()=>{
  const controller=new AbortController();controller.abort();
  globalThis.fetch=async(_,options)=>{throw options.signal.reason;};
  await assert.rejects(api('/test','GET',undefined,undefined,{signal:controller.signal}),e=>e.name==='AbortError');
});
test('session CSRF and exact idempotency headers remain attached to writes',async()=>{
  globalThis.fetch=async()=>Response.json({data:{csrf_token:'session-token'}});await login('test','synthetic');
  globalThis.fetch=async(_,options)=>{
    assert.equal(options.headers['X-CSRF-Token'],'session-token');assert.equal(options.headers['Idempotency-Key'],'command-token');
    assert.equal(options.credentials,'same-origin');return new Response(null,{status:204});
  };
  assert.equal(await api('/test','POST',{},'command-token'),undefined);
});
