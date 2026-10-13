import {request} from '@playwright/test';
import fs from 'node:fs/promises';
const credentials=JSON.parse(await fs.readFile('../../../Razorpay_Repeat_Agent_Codex_UI/backend/.local/owner-access.json','utf8'));
const api=await request.newContext({baseURL:'http://127.0.0.1:8766',extraHTTPHeaders:{Origin:'http://127.0.0.1:8766'}});
try{const response=await api.post('/api/v1/auth/login',{data:credentials});if(!response.ok())throw Error('Local login failed: '+response.status());const p=await api.get('/api/v1/workspaces/4b9786d5-3244-4adf-99dc-6e11539f568b/merchant/planning');const data=(await p.json()).data;console.log(JSON.stringify({status:p.status(),variants:data.variants.map(v=>({id:v.provider_variant_id,title:v.title,price:v.price_minor})),customers:data.counts,facts_version:data.facts_version}));}finally{await api.dispose();}
