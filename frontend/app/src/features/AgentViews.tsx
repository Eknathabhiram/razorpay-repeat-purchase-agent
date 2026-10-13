import {useState} from 'react';
import {Link} from 'react-router';
import type {DemoState,Policy} from '../api/client';
import {Badge,Button,Empty,Panel} from '../components/shared';
import {audience,people,fixtureBasis,type PersonKey} from './fixtures';

export type ViewsProps={state:DemoState;pending:boolean;go:(path:string)=>void;open:(name:string)=>void;
  run:(action:string,fields?:Record<string,unknown>)=>Promise<void>; link:(path:string)=>string};
const money=(value:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(value);

export function Dashboard({state,open,go}:ViewsProps) {
  const assigned=state.assigned.length;
  const reviewNeeded=!state.plan_approved||state.plan_needs_review||
    (state.scenario==='operating'&&!state.checkout_sent);
  const decisions=Number(!state.support_assigned)+Number(reviewNeeded);
  return <>
    <div className="metrics-strip">
      {[['Assigned customers',String(assigned)],['Confirmed orders',state.order_confirmed?'1':'0'],
        ['Net revenue',state.order_confirmed?'₹499':'₹0'],['Net contribution','Not available']].map(([label,value])=>
        <div className="metric" key={label}><span className="metric-label">{label}</span><strong>{value}</strong><span className="metric-note">{label==='Net contribution'?'Cost data incomplete':'Demo cohort · 12–19 Oct'}</span></div>)}
    </div>
    <div className="dashboard-columns"><div>
      <Panel title="Needs your attention" action={<Badge>{decisions} {decisions===1?'decision':'decisions'}</Badge>}>
        {!state.installed?<div className="decision-item"><h3>Finish installing your agent</h3><p>Review products, connections and permitted actions.</p><Button primary onClick={()=>open('install')}>Continue installation</Button></div>:<>
        {!state.support_assigned&&<div className="decision-item"><div><Badge tone="amber">Customer issue</Badge><h3>A delivery issue needs an owner</h3><p>Priya's last order has not arrived. Reorder outreach is blocked.</p></div><Button onClick={()=>open('journey:support')}>Review issue</Button></div>}
        {reviewNeeded&&<div className="decision-item"><div><Badge>{state.plan_needs_review?'Plan changed':state.plan_approved?'Message review':'Audience review'}</Badge>
          <h3>{state.plan_needs_review?'Review your plan under the new policy':state.plan_approved?'Send Rahul his checkout link':'Review customers for your next plan'}</h3>
          <p>{state.plan_approved&&!state.plan_needs_review?'He confirmed the same bottle and requested WhatsApp checkout.':'Approval defines the exact customers and contact limits.'}</p></div>
          <Button primary onClick={()=>state.plan_approved&&!state.plan_needs_review?open('journey:rahul'):go('plan')}>{state.plan_approved&&!state.plan_needs_review?'Review message':'Review plan'}</Button></div>}
        {!decisions&&<Empty title="No actions waiting for approval">Existing journeys can continue within their approved limits.</Empty>}</>}
      </Panel>
      <div className="section-space"><Panel title="Customer activity" action={<button className="text-button" onClick={()=>go('activity')}>View all activity →</button>}>
        {!state.plan_approved&&!state.assigned.length?<Empty title="No outreach scheduled" action={<Button onClick={()=>go('plan')}>Review first plan</Button>}>Approve an audience before contacting customers.</Empty>:
          audience.filter(key=>state.assigned.includes(key)).map(key=><CustomerRow key={key} person={key} state={state} onClick={()=>open('journey:'+key)}/>)}
      </Panel></div>
      <div className="section-space"><Panel title="Verified outcomes" action={<button className="text-button" onClick={()=>go('outcomes')}>View outcomes →</button>}>
        <div className="settings-body"><p>{state.order_confirmed?'One synthetic brand order matched to payment, outside the agent link.':'No confirmed orders yet.'}</p><p className="muted small">Incremental lift: not measured. Contribution needs verified costs.</p></div>
      </Panel></div>
    </div><aside><PolicySummary state={state} onClick={()=>go('settings')}/>
      <div className="section-space"><Panel title="Connection health"><div className="settings-body"><Badge tone={state.disconnected?'amber':''}>{state.disconnected?'Demo commerce unavailable':'Simulated sources'}</Badge><p className="field-help">Inspect real provider access in Connections.</p><Button onClick={()=>go('connections')}>View connections</Button></div></Panel></div>
    </aside></div>
  </>;
}

export function CustomerRow({person,state,onClick}:{person:PersonKey;state:DemoState;onClick:()=>void}) {
  const p=people[person];
  const isAssigned=state.assigned.includes(person);
  const label=person==='support'||person==='opted'?p.status:!isAssigned?'Awaiting plan':
    state.scenario!=='operating'?'Scheduled':person==='meera'&&!state.order_confirmed?'Scheduled':
    person==='rahul'&&state.checkout_sent?'Checkout pending':p.status;
  return <button className="customer-row" onClick={onClick}>
    <span className="avatar light">{p.name.slice(0,1)}</span><span className="customer-main"><strong>{p.name}</strong><span>{p.channel} · Laundry liquid 1 L</span></span>
    <span className="customer-status"><Badge tone={person==='support'?'amber':person==='meera'?'teal':''}>{label}</Badge><span className="small muted">{p.date}</span></span><span className="customer-chevron" aria-hidden="true">›</span>
  </button>;
}

export function PolicySummary({state,onClick}:{state:DemoState;onClick:()=>void}) {
  return <Panel title="Operating policy" action={<span className="small muted">v{state.policy.version}</span>}><dl className="definition-list settings-body">
    <div><dt>Product scope</dt><dd>Laundry liquid · 1 L</dd></div><div><dt>Channels</dt><dd>WhatsApp & browser voice</dd></div>
    <div><dt>Contact hours</dt><dd>{state.policy.start}–{state.policy.end} IST</dd></div><div><dt>Contact cap</dt><dd>{state.policy.cap} per customer</dd></div>
    <div><dt>Spend limit</dt><dd>{money(state.policy.budget)}</dd></div><div><dt>Offers</dt><dd>Off</dd></div>
    <div><dt>Execution</dt><dd>{state.policy.mode==='review'?'Review-first':'Within limits'}</dd></div></dl>
    <div className="panel-bottom"><button className="text-button" onClick={onClick}>Manage limits →</button></div></Panel>;
}

export function Activity({state,open}:ViewsProps) {
  const [search,setSearch]=useState(''),[filter,setFilter]=useState('all');
  const keys=(Object.keys(people) as PersonKey[]).filter(key=>{
    if(!people[key].name.toLowerCase().includes(search.toLowerCase()))return false;
    return filter==='all'||(filter==='attention'&&['rahul','support'].includes(key))||(filter==='suppressed'&&key==='opted');
  });
  return <Panel title="Customer journeys"><div className="filter-bar"><label className="sr-only" htmlFor="activity-search">Search customer activity</label><input id="activity-search" type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search customers"/>
    <label className="sr-only" htmlFor="activity-filter">Filter activity</label><select id="activity-filter" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All states</option><option value="attention">Needs attention</option><option value="suppressed">Suppressed</option></select></div>
    {keys.length?keys.map(key=><CustomerRow key={key} person={key} state={state} onClick={()=>open('journey:'+key)}/>):<Empty title="No matching activity">Try a different customer or state filter.</Empty>}
  </Panel>;
}

export function Plan({state,pending,run,open}:ViewsProps) {
  const [selected,setSelected]=useState<string[]>(state.selected);
  const eligible=audience.filter(key=>!(state.order_confirmed&&key==='meera'));
  const selectedEligible=selected.filter(key=>eligible.includes(key as typeof audience[number]));
  return <><div className="page-toolbar"><div><h2>{state.plan_needs_review?'Renew plan approval':'Repeat purchase plan'}</h2><p className="description">Approval permits only these selected customers within the limits shown.</p></div><Badge>{state.plan_approved&&!state.plan_needs_review?'Approved':'Draft for review'}</Badge></div>
    <div className="plan-columns"><Panel title="Customers for review" action={<span className="small muted">{selectedEligible.length} selected</span>}>
      {eligible.map(key=><div className="audience-row" key={key}><input type="checkbox" id={'select-'+key} checked={selected.includes(key)} onChange={e=>setSelected(e.target.checked?[...selected,key]:selected.filter(k=>k!==key))}/>
        <label htmlFor={'select-'+key}><strong>{people[key].name}</strong><span className="small muted">{fixtureBasis(key,state.scenario==='operating')}</span><span className="small">Same purchased variant · one unit · channel permission in demo</span></label><Button onClick={()=>open('journey:'+key)}>Evidence</Button></div>)}
      <div className="panel-bottom"><button className="text-button" onClick={()=>open('exclusions')}>View excluded customers</button></div>
    </Panel><aside><PolicySummary state={state} onClick={()=>open('policy')}/><div className="panel settings-body section-space">
      <p className="field-help">Same SKU only. Offers off. The customer reviews checkout and pays. Installation alone permits no contact.</p>
      <div className="action-group"><Button disabled={pending} onClick={()=>void run('reject_plan')}>Reject plan</Button><Button primary disabled={pending||state.paused||state.disconnected||!selectedEligible.length}
        onClick={()=>void run('approve_plan',{selected:selectedEligible})}>{pending?'Checking…':'Approve '+selectedEligible.length+' customers'}</Button></div>
      {state.paused&&<p className="field-error">Resume outreach before approving the plan.</p>}
      {state.plan_approved&&!state.plan_needs_review&&<p className="receipt-note" role="status">Audience approval saved. No replies or purchases were fabricated.</p>}
    </div></aside></div></>;
}

export function SettingsView({state,pending,open,reviewPolicy}:ViewsProps&{reviewPolicy:(policy:Policy)=>void}) {
  const [draft,setDraft]=useState<Policy>(state.policy);
  return <Panel title="Operating policy" action={<Badge>Version {state.policy.version}</Badge>}><form className="settings-body" onSubmit={e=>{e.preventDefault();reviewPolicy(draft);}}>
    <h3>Products and contact schedule</h3><div className="field"><label className="input-label" htmlFor="product">Repeatable product</label><input id="product" readOnly value="Laundry liquid · 1 L · same purchased variant"/></div>
    <div className="field-grid"><div className="field"><label className="input-label" htmlFor="contact-start">Contact start · IST</label><input id="contact-start" type="time" required value={draft.start} onChange={e=>setDraft({...draft,start:e.target.value})}/></div>
      <div className="field"><label className="input-label" htmlFor="contact-end">Contact end · IST</label><input id="contact-end" type="time" required value={draft.end} onChange={e=>setDraft({...draft,end:e.target.value})}/></div></div>
    <h3 className="section-space">Channels and limits</h3><p className="field-help">WhatsApp and browser voice share one demo contact limit.</p>
    <div className="field-grid"><div className="field"><label className="input-label" htmlFor="contact-cap">Total contacts per customer</label><input id="contact-cap" type="number" min="1" max="10" required value={draft.cap} onChange={e=>setDraft({...draft,cap:Number(e.target.value)})}/></div>
      <div className="field"><label className="input-label" htmlFor="spend-cap">Contact spend limit · INR</label><input id="spend-cap" type="number" min="0" max="100000" required value={draft.budget} onChange={e=>setDraft({...draft,budget:Number(e.target.value)})}/></div></div>
    <div className="field"><label className="input-label" htmlFor="execution-mode">Execution mode</label><select id="execution-mode" value={draft.mode} onChange={e=>setDraft({...draft,mode:e.target.value as Policy['mode']})}><option value="review">Review-first</option><option value="bounded">Within approved limits</option></select></div>
    <div className="section-space"><h3>Offers and economics</h3><p className="field-help">Offers are off. Product and fulfilment costs are missing; contribution is unavailable.</p></div>
    <div className="form-footer"><Button onClick={()=>open('environment')}>Source details</Button><Button primary type="submit" disabled={pending}>Review policy changes</Button></div>
  </form></Panel>;
}

export function Outcomes({state,open}:ViewsProps) {
  return <><div className="page-toolbar"><div><h2>Outcomes and learning</h2><p className="description">Assigned demo cohort · 12–19 October 2026 · IST</p></div><Badge>Simulated evidence</Badge></div>
    <div className="metrics-strip">{[['Brand orders',state.order_confirmed?'1':'0'],['Net revenue',state.order_confirmed?'₹499':'₹0'],['Net contribution','Unavailable'],['Incremental lift','Not measured']].map(([label,value])=><div className="metric" key={label}><span className="metric-label">{label}</span><strong>{value}</strong></div>)}</div>
    <Panel title="Confirmed brand orders">{state.order_confirmed?<div className="settings-body"><h3>Meera Shah · LE-1048</h3><p>Same laundry liquid · one unit · ₹499 net item revenue.</p><p className="field-help">Outside agent link. Synthetic payment/order match. Returns have not matured.</p><Button onClick={()=>open('calculation')}>Inspect calculation</Button></div>:<Empty title="No confirmed orders yet">Creating a checkout or approving a message does not confirm payment.</Empty>}</Panel>
    <div className="section-space"><Panel title="Customer learning"><div className="settings-body"><p>{state.scenario==='operating'?'Ananya confirmed a later reminder; Rahul requested a one-time WhatsApp handoff.':'No customer-confirmed preferences yet.'}</p><p className="field-help">More history is needed for policy suggestions. A one-time handoff is not a permanent preference.</p></div></Panel></div>
  </>;
}

export function Studio({open,go,link}:ViewsProps) {
  return <><div className="page-toolbar"><div><h2>Explore agents</h2><p className="description">Specialists for your merchant operations.</p></div></div>
    <Panel title="Repeat Purchase Agent"><div className="settings-body"><div className="agent-identity"><div className="agent-symbol"><span/><span/></div><div><h3>Help customers reorder when they are ready</h3><p className="muted">Same purchased product. WhatsApp and voice. Merchant-approved plans.</p></div></div>
      <div className="section-space"><p>Identify opportunities, choose a considerate next step, act within your limits and learn from verified outcomes.</p></div><div className="action-group"><Link className="button primary" to={link('agent')}>View agent</Link><Button onClick={()=>go('dashboard')}>My agents</Button><Button onClick={()=>open('install')}>Install agent</Button></div></div></Panel></>;
}

export function AgentDetail({open}:ViewsProps) {
  return <Panel title="Repeat Purchase Agent"><div className="settings-body"><h3>Replenishment that respects customer timing</h3>
    <p className="section-space">Detect eligible customers from delivered purchase history. Coordinate WhatsApp and voice, preserve confirmed dates, and give merchants a clear review for each action.</p>
    <ul className="check-list"><li>Exact previously purchased variant; no cross-sell.</li><li>Approved plans, review-first, pause and takeover.</li><li>Current source facts and trusted payment/order evidence.</li><li>Consent, opt-outs, support issues and shared contact limits.</li></ul>
    <p className="field-help">The current operating demonstration uses synthetic journeys. Real source capabilities are shown separately in Connections.</p><Button primary onClick={()=>open('install')}>Install agent</Button></div></Panel>;
}

export function Payments({go}:ViewsProps) {
  return <Panel title="Payments workspace"><Empty title="Your merchant operations" action={<Button primary onClick={()=>go('studio')}>Explore Agent Studio</Button>}>Open your specialist agent to review customers, decisions and source connections.</Empty></Panel>;
}
