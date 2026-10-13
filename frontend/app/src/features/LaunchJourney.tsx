import {useQuery} from '@tanstack/react-query';
import {useState,useEffect,useRef} from 'react';
import {useSearchParams} from 'react-router';
import {api} from '../api/client';
import type {Summary} from '../api/merchant';
import {number} from '../api/merchant';
import {Badge,Button,Loading,Panel} from '../components/shared';
import Planning from './Planning';
import Launch from './Launch';

type Scope={facts_version:number;counts:{eligible:number;total:number};policy:{config_json:{mode:string;conversation_automation?:boolean}}|null;draft:{selected_count:number;stale:boolean;revision:number}|null};
const steps=[['setup','Products & limits','Choose products and campaign limits'],['audience','Choose audience','Filter and save the eligible customer cohort'],['review','Review & launch','Approve the cohort, style and boundaries once'],['monitor','Conversations','Agent handles replies; you handle exceptions']] as const;
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
 const [stageDirty,setStageDirty]=useState(false);
 const [params]=useSearchParams(),step=['setup','audience','review'].includes(params.get('step')??'')?params.get('step')!:'setup';
 const query=useLaunchScope(workspace.id),data=query.data;
 const active=steps.findIndex(([id])=>id===step);
 const stageTitle=useRef<HTMLHeadingElement>(null);
 useEffect(()=>{stageTitle.current?.focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'});},[step,workspace.id]);
 return <div className="guided-launch avime-campaign"><div className="avime-page-title"><div><span className="eyebrow">NEW CAMPAIGN</span><h2 ref={stageTitle} tabIndex={-1}>{step==='setup'?'Products & limits':step==='audience'?'Choose your audience':'Review campaign'}</h2><p>{step==='setup'?'Choose what the agent can offer and how much it can spend.':step==='audience'?'Select customers and save the audience for this campaign.':'Review the audience, messages and limits before launching.'}</p></div><span className="avime-stage-count">Step {active+1} of 3</span></div>
 {workspace.environment==='development'&&data&&<div className="campaign-source-note"><strong>Connected Shopify store · {number(data.counts.total)} customer records</strong><p>{number(data.counts.eligible)} meet the current consent and purchase checks. For the scale walkthrough, choose <b>Avime Herbal · 200 customers</b> from the workspace menu.</p></div>}
 {step==='review'?<Launch workspace={workspace} go={path=>go(path==='planning'?'launch?step=audience':path)}/>:<Planning key={workspace.id+step} workspace={workspace} stage={step as 'setup'|'audience'} onDirty={setStageDirty} go={path=>go(path==='execution'?'launch?step=review':path)}/>}
 {query.isPending?<Loading label="Checking the saved launch stage…"/>:query.isError?<Panel title="Launch progress unavailable"><p role="alert">{query.error.message}</p></Panel>:step!=='review'&&<div className="launch-next-step"><p>{step==='setup'?!stageDirty&&data?.policy&&data.facts_version?'Settings saved. Choose your customer audience next.':'Save campaign settings to continue.':!stageDirty&&data?.draft&&!data.draft.stale?`${number(data.draft.selected_count)} selected journeys are saved for initial review.`:'Save your audience selection to continue.'}</p><div className="button-row">{step==='audience'&&<Button onClick={()=>go('launch?step=setup')}>Back to products & limits</Button>}<Button primary disabled={step==='setup'?stageDirty||!data?.policy||!data.facts_version:stageDirty||!data?.draft||data.draft.stale} onClick={()=>go('launch?step='+(step==='setup'?'audience':'review'))}>{step==='setup'?'Continue to audience':'Continue to review'}</Button></div></div>}
 </div>;
}
