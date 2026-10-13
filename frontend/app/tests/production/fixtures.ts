import {test as base, expect} from '@playwright/test';

export const state={scenario:'operating',installed:true,paused:false,plan_approved:true,plan_needs_review:false,
  selected:['ananya','rahul','meera'],assigned:['ananya','rahul','meera'],checkout_sent:false,order_confirmed:true,
  taken_over:false,support_assigned:false,disconnected:false,events:[],
  policy:{version:3,start:'10:00',end:'18:00',cap:2,budget:500,mode:'review'}};
export const workspaces=[{id:'demo',name:'Loop Essentials',environment:'demo',role:'owner',version:1},
  {id:'dev',name:'Development store',environment:'development',role:'owner',version:1}];
export const planning={environment:'demo',facts_version:3,coverage_complete:true,coverage_notes:[],synced_at:'2026-10-13T08:00:00Z',
  policy:{revision:1,digest:'demo-policy',config_json:{variant_ids:['variant-1'],fallback_days:30,recent_purchase_days:14,
    contact_start:'10:00',contact_end:'18:00',timezone:'Asia/Kolkata',contact_cap:2,budget_minor:50000,currency:'INR',mode:'review',offers_enabled:false}},
  variants:[{provider_variant_id:'variant-1',title:'Laundry liquid · 1 L'}],
  opportunities:[{id:'opportunity-1',eligible:true,exclusion_codes:[],basis:'Comparable delivered purchase intervals',
    window_start:'2026-10-12',window_end:'2026-10-19',evidence_json:{customer_alias:'Ananya Rao',variant_title:'Laundry liquid · 1 L',
      provider_variant_id:'variant-1',source_mode:'simulated',deliveries:[],estimator_version:'v1',checked_at:'2026-10-13T08:00:00Z'}}],
  draft:null,notice:'Synthetic purchase history. Audience approval is required before outreach.'};
export const execution={environment:'demo',version:1,paused:false,plan_review:null,journeys:[],actions:[],jobs:[],receipts:[],
  support_cases:[],reminders:[],budgets:[],cohort_count:0,notice:'Only exact approved messages may be dispatched. Transport is simulated.'};
export const commerce={environment:'demo',source_notice:'Simulated commerce. Payment capture and delivery are separate facts.',
  storefront_available:false,plan_requires_review:false,last_sync_at:null,mapping_version:'v1',
  journeys:[{id:'journey-1',customer_alias:'Ananya Rao',state:'active',current_plan:true}],preparations:[],payments:[],
  matches:[],purchases:[],cases:[],adjustments:[],offers:[],offer_policy:null};

export const test=base.extend<{mockApi:void}>({
  mockApi:[async ({page},use)=>{
    const demo=structuredClone(state);
    let version=1;
    await page.route('**/api/v1/**',async route=>{
      const pathname=new URL(route.request().url()).pathname;
      let data:unknown;
      if(pathname.endsWith('/auth/session')||pathname.endsWith('/auth/login')) data={csrf_token:'test-csrf'};
      else if(pathname.endsWith('/auth/logout')) data={};
      else if(pathname.endsWith('/me')) data={login:'owner',workspaces};
      else if(pathname.endsWith('/ui-state')) data={version,state:pathname.includes('/dev/')?null:demo,notice:'Separate synthetic workspace.'};
      else if(pathname.endsWith('/demo-commands')){
        const command=route.request().postDataJSON();
        if(command.action==='pause')demo.paused=true;
        if(command.action==='resume')demo.paused=false;
        if(command.action==='assign_support')demo.support_assigned=true;
        if(command.action==='takeover')demo.taken_over=true;
        if(command.action==='handback')demo.taken_over=false;
        data={version:++version,state:demo,notice:'Separate synthetic workspace.'};
      }
      else if(pathname.endsWith('/planning')) data=planning;
      else if(pathname.endsWith('/execution')) data=execution;
      else if(pathname.endsWith('/commerce')) data=commerce;
      else if(pathname.endsWith('/connectors'))data=['shopify','razorpay','twilio','voice','support'].map(provider=>({
        id:provider,provider,source_mode:'simulated',provider_environment:'demo',state:'unverified',last_checked_at:null,version:1,capabilities:[]}));
      else {await route.fulfill({status:501,json:{error:{message:'Test endpoint not configured.'}}});return;}
      await route.fulfill({json:{data}});
    });
    await use();
  },{auto:true}],
});
export {expect};
