import {useQuery} from '@tanstack/react-query';
import {useState} from 'react';
import {useSearchParams} from 'react-router';
import {api} from '../api/client';
import type {Summary} from '../api/merchant';
import {number} from '../api/merchant';
import {Badge,Button,Loading,Panel} from '../components/shared';
import Planning from './Planning';
import Launch from './Launch';

type Scope={facts_version:number;counts:{eligible:number};policy:{config_json:{mode:string;conversation_automation?:boolean}}|null;draft:{selected_count:number;stale:boolean;revision:number}|null};
const steps=[['setup','Data & limits','Choose the product and what the agent may do'],['audience','Choose audience','Filter and save the eligible customer cohort'],['review','Review & launch','Approve the cohort, style and boundaries once'],['monitor','Conversations','Agent handles replies; you handle exceptions']] as const;
function useLaunchScope(workspace:string){return useQuery({queryKey:['merchant-planning',workspace],queryFn:({signal})=>api<Scope>('/workspaces/'+workspace+'/merchant/planning','GET',undefined,undefined,{signal})});}
export function LaunchPath({workspace,summary,go}:{workspace:string;summary:Summary;go:(path:string)=>void}){
 const scope=useLaunchScope(workspace),data=scope.data;
 if(!data)return null;
 const automatic=!!data.policy&&data.policy.config_json.mode==='bounded'&&data.policy.config_json.conversation_automation;
 const next=!data.facts_version||!data.policy||!automatic?'setup':!data.draft||data.draft.stale?'audience':!summary.approval_current?'review':'monitor';
 const active=steps.findIndex(([id])=>id===next);
 return <section className="launch-path" aria-label="Your launch progress"><div className="launch-path-heading"><div><h2>{next==='monitor'?'Your cohort is running':'Your next step: '+steps[active][1]}</h2><p>{summary.paused?'The agent is paused. Incoming replies and customer protections still update.':!automatic&&data.policy?'This workspace has the older message-review policy. Choose initial review, then automatic, and approve a new cohort to use the requested flow.':next==='review'?`${number(data.draft?.selected_count??0)} selected journeys are ready for one initial review. No outreach is authorized yet.`:next==='monitor'?'The agent confirms items, sends checkout and saves customer-confirmed reminders. Open the inbox for exceptions.':'Complete these steps once for your customer cohort.'}</p></div><Button primary onClick={()=>go(next==='monitor'?'whatsapp':'launch?step='+next)}>{next==='monitor'?'Open conversations':'Continue '+steps[active][1].toLowerCase()}</Button></div><ol className="launch-step-list">{steps.map(([id,title,detail],index)=><li key={id} className={index===active?'current':index<active?'complete':''}><button type="button" onClick={()=>go(id==='monitor'?'whatsapp':'launch?step='+id)} aria-current={index===active?'step':undefined}><span className="step-number">{index<active?'✓':index+1}</span><span><strong>{title}</strong><small>{detail}</small></span></button></li>)}</ol></section>;
}
export default function LaunchJourney({workspace,go}:{workspace:{id:string;environment:string;role:string};go:(path:string)=>void}){
 const [setupDirty,setSetupDirty]=useState(false);
 const [params]=useSearchParams(),step=['setup','audience','review'].includes(params.get('step')??'')?params.get('step')!:'setup';
 const query=useLaunchScope(workspace.id),data=query.data;
 const active=steps.findIndex(([id])=>id===step);
 return <div className="guided-launch"><div className="page-toolbar"><div><h2>Launch a customer cohort</h2><p className="description">Review once. The agent manages the conversation; you handle exceptions.</p></div><Badge>{workspace.environment==='demo'?'Demo launch · synthetic customers':'Connected source review · real sending disabled'}</Badge></div>
 <ol className="launch-step-list" aria-label="Launch steps">{steps.map(([id,title,detail],index)=><li key={id} className={index===active?'current':index<active?'complete':''}><button type="button" onClick={()=>go(id==='monitor'?'whatsapp':'launch?step='+id)} aria-current={index===active?'step':undefined}><span className="step-number">{index+1}</span><span><strong>{title}</strong><small>{detail}</small></span></button></li>)}</ol>
 <div className="launch-stage-intro"><h3>Step {active+1}: {steps[active][1]}</h3><p>{step==='setup'?'Load or check the customer data. Save the product, contact/spend limits and the initial-review automation policy. Saving these settings does not launch outreach.':step==='audience'?'Choose customers using eligibility, city and date filters. Save the cohort so its exact scope can be reviewed.':'Review the selected cohort and the full automation mandate. Approve once to start; the customer still confirms checkout and completes payment.'}</p>{workspace.environment!=='demo'&&<p className="field-error">Shopify and test payment reads work in Development. Use Demo to review the complete launch and conversation flow while real WhatsApp and checkout remain unavailable.</p>}</div>
 {step==='review'?<Launch workspace={workspace} go={path=>go(path==='planning'?'launch?step=audience':path)}/>:<Planning workspace={workspace} stage={step as 'setup'|'audience'} onDirty={setSetupDirty} go={path=>go(path==='execution'?'launch?step=review':path)}/>}
 {query.isPending?<Loading label="Checking the saved launch stage…"/>:query.isError?<Panel title="Launch progress unavailable"><p role="alert">{query.error.message}</p></Panel>:step!=='review'&&<div className="launch-next-step"><p>{step==='setup'?!setupDirty&&data?.policy&&data.facts_version?'Data and policy are saved. Continue to select your audience.':'Save source data and a policy before continuing.':data?.draft&&!data.draft.stale?`${number(data.draft.selected_count)} selected journeys are saved for initial review.`:'Save a current audience draft before continuing.'}</p><div className="button-row">{step==='audience'&&<Button onClick={()=>go('launch?step=setup')}>Back to data & limits</Button>}<Button primary disabled={step==='setup'?setupDirty||!data?.policy||!data.facts_version:!data?.draft||data.draft.stale} onClick={()=>go('launch?step='+(step==='setup'?'audience':'review'))}>{step==='setup'?'Continue to audience':'Continue to initial review'}</Button></div></div>}
 </div>;
}
