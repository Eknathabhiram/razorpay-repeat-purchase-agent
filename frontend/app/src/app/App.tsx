import {lazy,Suspense,useEffect,useRef,useState,type FormEvent} from 'react';
import {Link,useLocation,useNavigate,useSearchParams} from 'react-router';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {api,clearSession,login,logout,restoreSession,ApiError,type Command,type DemoState,type Policy,type UIState} from '../api/client';
import {Badge,Button,Dialog,Empty,Icon,Loading,RefreshNotice,Panel,CommandErrorContext} from '../components/shared';
import {Dashboard,Activity,Plan,SettingsView,Outcomes,Studio,AgentDetail,Payments,type ViewsProps} from '../features/AgentViews';
import MyAgents from '../features/MyAgents';
import {people,fixtureBasis,type PersonKey} from '../features/fixtures';
const Connections=lazy(()=>import('../features/Connections'));
const Planning=lazy(()=>import('../features/Planning'));
const Execution=lazy(()=>import('../features/Execution'));
const Commerce=lazy(()=>import('../features/Commerce'));
const views=['dashboard','activity','settings','planning','execution','commerce','studio','agents','agent','connections','payments','transactions','customers','entry','plan','outcomes'];

function Login({onLogin,notice}:{onLogin:()=>Promise<unknown>;notice:string}) {
  const [error,setError]=useState(''),[pending,setPending]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();setError('');setPending(true);
    const form=event.currentTarget,values=new FormData(form);
    try{await login(String(values.get('login')),String(values.get('password')));form.reset();await onLogin();}
    catch(e){setError((e as Error).message);}finally{setPending(false);}
  }
  return <div className="auth-page"><header className="product-header"><span className="brand">Razorpay<span className="brand-mark">/</span></span><span className="product-switch">Agent workspace</span></header>
    <main className="auth-main"><div className="auth-intro"><Badge>Repeat Purchase Agent</Badge><h1>Welcome to your merchant workspace</h1><p>Review customer journeys and keep every action within your limits.</p></div>
      <section className="panel auth-card"><div className="panel-heading"><h2>Application owner sign-in</h2></div><form className="settings-body" onSubmit={submit}>
        <p className="field-help">Use your local application account. This form does not authenticate a Razorpay merchant account.</p>
        {notice&&<p className="notice warning" role="status">{notice}</p>}
        <div className="field"><label className="input-label" htmlFor="login">Login</label><input id="login" name="login" autoComplete="username" required autoCapitalize="none" spellCheck={false}/></div>
        <div className="field"><label className="input-label" htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required/></div>
        {error&&<p className="field-error" role="alert">{error}</p>}<Button type="submit" primary disabled={pending}>{pending?'Signing in…':'Sign in'}</Button>
      </form></section><p className="small muted">Separate Demo and Development workspaces. Source access and simulation are always labelled.</p>
    </main></div>;
}

export default function App() {
  const client=useQueryClient(),navigate=useNavigate(),location=useLocation();
  const [params,setParams]=useSearchParams();
  const [modal,setModal]=useState<string|null>(null),[toast,setToast]=useState(''),[menu,setMenu]=useState(false);
  const [policyDraft,setPolicyDraft]=useState<Policy|null>(null),[installStep,setInstallStep]=useState(0),[installMode,setInstallMode]=useState<Policy['mode']>('review');
  const [entryStep,setEntryStep]=useState(0);
  const [commandError,setCommandError]=useState('');
  const [sessionNotice,setSessionNotice]=useState(''),[online,setOnline]=useState(navigator.onLine),[signingOut,setSigningOut]=useState(false);
  const navigationToggle=useRef<HTMLButtonElement>(null);
  useEffect(()=>{
    function expired(){clearSession();client.clear();client.setQueryData(['session'],null);setSessionNotice('Your session expired. Sign in to continue.');setModal(null);}
    function connected(){setOnline(true);} function disconnected(){setOnline(false);}
    window.addEventListener('session-expired',expired);window.addEventListener('online',connected);window.addEventListener('offline',disconnected);
    return ()=>{window.removeEventListener('session-expired',expired);window.removeEventListener('online',connected);window.removeEventListener('offline',disconnected);};
  },[client]);
  const session=useQuery({queryKey:['session'],queryFn:restoreSession,retry:false,staleTime:Infinity});
  const workspace=session.data?.workspaces.find(w=>w.id===params.get('workspace'))??session.data?.workspaces[0];
  const ui=useQuery({queryKey:['ui',workspace?.id],queryFn:({signal})=>api<UIState>('/workspaces/'+workspace!.id+'/ui-state','GET',undefined,undefined,{signal}),
    enabled:!!workspace,refetchInterval:5000});
  const state=ui.data?.state as DemoState|null|undefined;
  const view=location.pathname.replace(/^\//,'')||'dashboard';
  const link=(path:string)=>'/'+path+(workspace?'?workspace='+workspace.id:'');
  function go(path:string){setModal(null);setMenu(false);navigate(link(path));}
  function notify(message:string){setToast(message);}
  useEffect(()=>{if(!toast)return;const id=window.setTimeout(()=>setToast(''),6000);return()=>clearTimeout(id);},[toast]);
  useEffect(()=>{setModal(null);setPolicyDraft(null);setMenu(false);},[workspace?.id]);
  useEffect(()=>{setCommandError('');},[modal,workspace?.id]);
  useEffect(()=>{document.getElementById('workspace')?.focus();},[location.pathname]);
  useEffect(()=>{document.title=(view.charAt(0).toUpperCase()+view.slice(1))+' · Repeat Purchase Agent';setModal(null);setMenu(false);},[view]);
  useEffect(()=>{
    if(!menu)return;
    const sidebar=document.getElementById('sidebar'),main=document.getElementById('workspace'),headerRight=document.querySelector<HTMLElement>('.header-right');
    const previousOverflow=document.body.style.overflow;
    const media=window.matchMedia('(max-width:1023px)');
    if(!media.matches){setMenu(false);return;}
    const controls=()=>Array.from(sidebar?.querySelectorAll<HTMLElement>('a,button')??[]);
    main?.setAttribute('inert','');headerRight?.setAttribute('inert','');document.body.style.overflow='hidden';controls()[0]?.focus();
    function keydown(event:KeyboardEvent){
      if(event.key==='Escape'){event.preventDefault();setMenu(false);}
      if(event.key==='Tab'){
        const items=controls(),index=items.indexOf(document.activeElement as HTMLElement);
        if(event.shiftKey&&index<=0){event.preventDefault();items.at(-1)?.focus();}
        else if(!event.shiftKey&&index===items.length-1){event.preventDefault();items[0]?.focus();}
      }
    }
    function resize(){if(!media.matches)setMenu(false);}
    window.addEventListener('keydown',keydown);media.addEventListener('change',resize);
    return ()=>{main?.removeAttribute('inert');headerRight?.removeAttribute('inert');document.body.style.overflow=previousOverflow;window.removeEventListener('keydown',keydown);media.removeEventListener('change',resize);navigationToggle.current?.focus();};
  },[menu]);
  const mutation=useMutation({mutationFn:(fields:Record<string,unknown>)=>api<UIState>(
    '/workspaces/'+workspace!.id+'/demo-commands','POST',
    {expected_version:ui.data!.version,...fields},crypto.randomUUID()),
    onSuccess:data=>client.setQueryData(['ui',workspace!.id],data),
    onError:async(error)=>{setCommandError(error.message);notify(error.message);if(error instanceof ApiError&&error.status===409)await ui.refetch();}});
  async function run(action:string,fields:Record<string,unknown>={}) {
    setCommandError('');
    try{await mutation.mutateAsync({action:action as Command['action'],...fields});notify('Demo change saved. No provider action was executed.');setModal(action==='install'?'installed':null);}
    catch{/* Actionable error stays visible; unsaved draft remains available. */}
  }
  async function signOut(){setSigningOut(true);try{await logout();client.clear();client.setQueryData(['session'],null);setModal(null);navigate('/dashboard');setSessionNotice('');}catch(error){setCommandError((error as Error).message);}finally{setSigningOut(false);}}
  if(session.isPending)return <main className="recovery-page"><Loading label="Restoring your session…"/></main>;
  if(session.isError&&(!(session.error instanceof ApiError)||session.error.status!==401))return <main className="recovery-page"><Empty title="Unable to reach your workspace" action={<Button primary onClick={()=>void session.refetch()}>Try again</Button>}>{session.error.message}</Empty></main>;
  if(!session.data)return <Login notice={sessionNotice} onLogin={()=>client.invalidateQueries({queryKey:['session']})}/>;
  if(!workspace)return <main><Empty title="No workspace access">Ask the account owner to grant workspace membership.</Empty></main>;
  const busy=mutation.isPending||workspace.role==='viewer'||!online||ui.isError;
  const globalView=['studio','agents','agent','connections','payments','transactions','customers','entry'].includes(view);
  const props:ViewsProps={state:state!,pending:busy,go,open:name=>{setModal(name);if(name==='install'){setInstallStep(0);setInstallMode(state?.policy.mode??'review');}},run,link};
  const playback=state?.scenario==='operating';
  const person=modal?.startsWith('journey:')?modal.split(':')[1] as PersonKey:null;
  const p=person?people[person]:null;
  const hasConversation=playback||person==='support'||person==='opted';
  function reviewPolicy(draft:Policy){setPolicyDraft(draft);setModal('policy');}
  function switchDemo(){const demo=session.data!.workspaces.find(w=>w.environment==='demo');if(demo){setParams({workspace:demo.id});setModal(null);}}

  return <CommandErrorContext.Provider value={commandError}><a className="skip-link" href="#workspace" onClick={e=>{e.preventDefault();document.getElementById('workspace')?.focus();}}>Skip to workspace</a>
    <header className="product-header"><button ref={navigationToggle} className="icon-button mobile-toggle" aria-label={menu?'Close navigation':'Open navigation'} aria-expanded={menu} aria-controls="sidebar" onClick={()=>setMenu(!menu)}><Icon name="menu"/></button>
      <Link className="brand" to={link('payments')}>Razorpay<span className="brand-mark">/</span></Link><span className="product-switch">Payments</span>
      <div className="header-right"><button className="mode-button" onClick={()=>setModal('environment')}><span className="mode-dot"/>{workspace.environment==='demo'?'Demo mode':workspace.environment==='development'?'Development':'Live'}</button>
        <label className="sr-only" htmlFor="workspace-selector">Active workspace</label><select id="workspace-selector" className="workspace-select" value={workspace.id} onChange={e=>setParams({workspace:e.target.value})}>
          {session.data.workspaces.map(w=><option key={w.id} value={w.id}>{w.environment==='demo'?'Demo':'Development'} · {w.name}</option>)}</select>
        <button className="text-button header-signout" disabled={signingOut} onClick={()=>void signOut()}>{signingOut?'Signing out…':'Sign out'}</button>
      </div></header>
    {menu&&<button className="navigation-backdrop" aria-label="Close navigation" tabIndex={-1} onClick={()=>setMenu(false)}/>}
    <div className="app-layout"><aside id="sidebar" className={'sidebar '+(menu?'open':'')} aria-label="Main navigation">
      <div className="sidebar-label">WORKSPACE</div><nav className="primary-nav" aria-label="Payments">
        {[['payments','Home','home'],['transactions','Transactions','activity'],['customers','Customers','grid']].map(([path,title,icon])=><Link key={path} to={link(path)} onClick={()=>setMenu(false)} className={view===path?'selected':''}><Icon name={icon}/>{title}</Link>)}
      </nav><div className="sidebar-label studio-label">AGENT STUDIO</div><nav className="primary-nav" aria-label="Agent Studio">
        {[['studio','Explore agents','grid'],['agents','My agents','activity'],['connections','Connections','link']].map(([path,title,icon])=><Link key={path} to={link(path)} onClick={()=>setMenu(false)} className={view===path||(path==='agents'&&!globalView)?'selected':''}><Icon name={icon}/>{title}</Link>)}
      </nav><div className="sidebar-bottom"><button className="nav-button" onClick={()=>setModal('help')}><Icon name="settings"/>Help & support</button>
        <Link className="nav-button" to={link('entry')}>Entry journey preview</Link><div className="account-row"><span className="avatar light">LE</span><div><strong>Loop Essentials</strong><span>{workspace.environment} workspace</span></div></div></div>
    </aside><main id="workspace" tabIndex={-1}>
      {!online&&<div className="notice warning" role="alert"><p>You’re offline. Reconnect and refresh before approving or saving changes.</p></div>}
      {workspace.role==='viewer'&&<div className="access-note"><Icon name="box"/><span>View-only access. An owner or operator can approve and save changes.</span></div>}
      <div className="breadcrumb"><Link to={link('studio')}>Agent Studio</Link><span>/</span><Link to={link('agents')}>My agents</Link><span>/</span><span>Repeat Purchase</span></div>
      <div className="agent-heading"><div className="agent-identity"><div className="agent-symbol"><span/><span/></div><div><h1>{globalView?'Agent Studio':'Repeat Purchase Agent'}</h1><p>{globalView?'Specialists for your merchant operations.':'Customer reorders, managed within your limits.'}</p></div></div>
        {!globalView&&!['planning','execution','commerce'].includes(view)&&<div className="agent-controls"><span className={'status '+(state?.paused?'paused':'')}><span className="status-dot"/>{state?(state.paused?'Paused':state.installed?'Demo active':'Setup required'):'Engine pending'}</span>
          <Button disabled={!state||busy} onClick={()=>setModal('pause')}><Icon name="pause"/>{state?.paused?'Resume':'Pause agent'}</Button></div>}</div>
      {!globalView&&<nav className="agent-tabs" aria-label="Repeat Purchase Agent">{['dashboard','activity','settings','planning','execution','commerce'].map(path=><Link key={path} to={link(path)} className={view===path?'selected':''} aria-current={view===path?'page':undefined}>{path.charAt(0).toUpperCase()+path.slice(1)}</Link>)}</nav>}
      {state?.paused&&!['planning','execution','commerce'].includes(view)&&<div className="notice warning"><div><strong>Outreach is paused</strong><p>New messages and calls are on hold. Orders and opt-outs continue to update.</p></div><Button onClick={()=>setModal('pause')}>Resume</Button></div>}
      {state?.plan_needs_review&&!['planning','execution','commerce'].includes(view)&&<div className="notice warning"><p>Your policy changed. Review the plan before further demo outreach.</p><Button onClick={()=>go('plan')}>Review plan</Button></div>}
      {commandError&&!modal&&<div className="notice warning" role="alert"><p>{commandError}</p><Button onClick={()=>setCommandError('')}>Dismiss</Button></div>}
      <RefreshNotice failed={ui.isError&&!!ui.data} onRetry={()=>void ui.refetch()}/>
      <Suspense fallback={<Loading/>}>
      {ui.isPending?<Loading/>:ui.isError&&!ui.data?<Panel title="Workspace unavailable"><div className="settings-body" role="alert"><p>{ui.error.message}</p><Button onClick={()=>void ui.refetch()}>Try again</Button><Button onClick={()=>void signOut()}>Sign in again</Button></div></Panel>:
       !views.includes(view)?<Panel title="Page not found"><Empty title="This page is unavailable" action={<Button primary onClick={()=>go('dashboard')}>Return to dashboard</Button>}>Use the workspace navigation to find customers, approvals and settings.</Empty></Panel>:
       view==='commerce'?<Commerce key={workspace.id} workspace={workspace} go={go}/>:
       view==='execution'?<Execution key={workspace.id} workspace={workspace} go={go}/>:
       view==='planning'?<Planning key={workspace.id} workspace={workspace} go={go}/>:
       view==='connections'?<Connections key={workspace.id} workspace={workspace} notify={notify}/>:
       view==='entry'?<Panel title="Razorpay-style entry preview"><div className="settings-body"><Badge>Simulated entry</Badge><h3 className="section-space">{entryStep===0?'Sign-in preview':entryStep===1?'Verification preview':'Payments home entry'}</h3>
         <p className="field-help">This illustrates the agreed entry journey. No Razorpay credentials or verification code are collected.</p><div className="field"><label className="input-label" htmlFor="sample-merchant">Sample merchant</label><input id="sample-merchant" value="Loop Essentials" readOnly/></div>
         <Button primary onClick={()=>entryStep<2?setEntryStep(entryStep+1):go('payments')}>{entryStep===0?'Continue to verification':entryStep===1?'Continue with simulated verification':'Open payments home'}</Button></div></Panel>:
       view==='studio'?<Studio {...props}/>:view==='agents'?<MyAgents {...props}/>:view==='agent'?<AgentDetail {...props}/>:view==='payments'?<Payments {...props}/>:
       view==='transactions'||view==='customers'?<Panel title={view==='transactions'?'Transactions':'Customers'}><Empty title="Use source records in Connections" action={<Button onClick={()=>go('connections')}>View Shopify records</Button>}>These dashboard areas are entry references; no separate live merchant dashboard is connected.</Empty></Panel>:
       !state?<Panel title="Agent execution setup"><Empty title="The agent engine is not connected here" action={<><Button primary onClick={()=>go('connections')}>Review source connections</Button><Button onClick={switchDemo}>Open Demo workspace</Button></>}>{ui.data?.notice}</Empty></Panel>:
       view==='activity'?<Activity {...props}/>:view==='settings'?<SettingsView key={workspace.id+state.policy.version} {...props} reviewPolicy={reviewPolicy}/>:
       view==='plan'?<Plan key={workspace.id+state.scenario} {...props}/>:view==='outcomes'?<Outcomes {...props}/>:<Dashboard {...props}/>}
      </Suspense>
      <footer className="workspace-footer"><span>All times in IST</span><span>{workspace.environment==='demo'?'Synthetic journeys · server-persisted demo actions':'Development source reads · agent execution pending'}</span></footer>
    </main></div>
    {modal==='environment'&&<Dialog title="Workspace source mode" onClose={()=>setModal(null)} footer={<Button onClick={()=>state?setModal('scenarios'):switchDemo()}>{state?'Manage demo scenarios':'Open Demo workspace'}</Button>}>
      <p>{ui.data?.notice}</p><div className="section-space"><h3>Separate environments</h3><p className="field-help">Demo commands are persisted on the server and cannot change Development provider records. Actual source capabilities appear in Connections.</p></div><Button onClick={()=>go('connections')}>Review connections</Button></Dialog>}
    {modal==='scenarios'&&state&&<Dialog title="Demo scenarios" onClose={()=>setModal(null)}>
      <p>Choose a synthetic scenario. Reset changes only this demo's UI state.</p>{[['operating','Active plan','Reminders, message approval and an outside-link order.'],['first-plan','First plan','Audience review before any reply or purchase.'],['setup','New installation','Four-step setup journey.'],['disconnected','Disconnected commerce','Blocked actions and source recovery.']].map(([value,title,description])=><div className="service-row" key={value}><div><strong>{title}</strong><small>{description}</small></div><Button disabled={busy} onClick={()=>void run('reset',{scenario:value})}>Load</Button></div>)}</Dialog>}
    {modal==='pause'&&state&&<Dialog title={state.paused?'Resume outreach?':'Pause outreach?'} onClose={()=>setModal(null)} footer={<><Button onClick={()=>setModal(null)}>Keep {state.paused?'paused':'active'}</Button><Button primary disabled={busy||(state.paused&&(state.disconnected||state.plan_needs_review))} onClick={()=>void run(state.paused?'resume':'pause')}>{state.paused?'Resume agent':'Pause agent'}</Button></>}>
      <p>{state.paused?'Current connection and plan checks must pass before resuming.':'New messages and calls stop. Reminders remain saved; order updates and opt-outs still process.'}</p>
      {(state.disconnected||state.plan_needs_review)&&<p className="field-error">Resolve the connection or review the changed plan first.</p>}</Dialog>}
    {modal==='policy'&&policyDraft&&state&&<Dialog title="Review policy changes" onClose={()=>setModal(null)} footer={<><Button onClick={()=>setModal(null)}>Keep editing</Button><Button primary disabled={busy} onClick={()=>void run('save_policy',{policy:policyDraft})}>Save policy</Button></>}>
      <p>Saving creates policy version {state.policy.version+1}. An affected plan needs fresh approval.</p><dl className="definition-list">
        <div><dt>Contact hours</dt><dd>{state.policy.start}–{state.policy.end} → {policyDraft.start}–{policyDraft.end}</dd></div><div><dt>Contact cap</dt><dd>{state.policy.cap} → {policyDraft.cap}</dd></div><div><dt>Spend limit</dt><dd>₹{state.policy.budget} → ₹{policyDraft.budget}</dd></div><div><dt>Execution</dt><dd>{state.policy.mode} → {policyDraft.mode}</dd></div></dl></Dialog>}
    {modal==='install'&&<Dialog title="Install Repeat Purchase Agent" onClose={()=>setModal(null)} footer={<>
      {installStep>0&&<Button onClick={()=>setInstallStep(installStep-1)}>Back</Button>}
      <Button primary disabled={busy||(!state&&installStep===2)} onClick={()=>installStep<2?setInstallStep(installStep+1):void run('install',{policy:{...state!.policy,mode:installMode}})}>{installStep<2?'Continue':'Activate demo agent'}</Button></>}>
      <div className="installation-layout"><ol className="install-progress">{['Configure','Connectors','Review','Activate'].map((label,index)=><li key={label} className={installStep===index?'current':''}>{index+1}. {label}</li>)}</ol><div className="installation-body">
      {installStep===0?<><h3>Choose the agent's mandate</h3><div className="field"><label className="input-label" htmlFor="install-product">Product scope</label><input id="install-product" readOnly value="Same previously purchased laundry liquid · 1 L"/></div><div className="field"><label className="input-label" htmlFor="install-mode">Approval mode</label><select id="install-mode" value={installMode} onChange={e=>setInstallMode(e.target.value as Policy['mode'])}><option value="review">Review-first</option><option value="bounded">Within approved limits</option></select></div></>:
       installStep===1?<><h3>Review source access</h3><p className="field-help">{state?'This installation uses explicit synthetic sources.':'Development execution is blocked until its required capabilities are implemented.'}</p>{['Commerce','Payments','WhatsApp','Browser voice','Support'].map(label=><div className="service-row" key={label}><strong>{label}</strong><Badge>{state?'Simulated':'Unverified for execution'}</Badge></div>)}<Button onClick={()=>go('connections')}>Inspect actual connections</Button></>:
       <><h3>Review activation</h3><p>Same purchased variant. Offers off. Customer completes payment. {installMode==='review'?'Individual actions require review.':'Actions stay within approved limits.'}</p><p className="field-help">Installation alone does not approve an audience or send any customer contact.</p>{!state&&<p className="field-error">Real activation is unavailable at this stage. Select Demo to inspect the full setup flow.</p>}</>}</div></div>
    </Dialog>}
    {modal==='installed'&&<Dialog title="Agent installed" onClose={()=>setModal(null)} footer={<Button primary onClick={()=>go('plan')}>Review first audience</Button>}><ol className="install-progress">{['Configure','Connectors','Review','Activate'].map(label=><li key={label}>{label} ✓</li>)}</ol><p>No customer contact is authorised yet. Review an audience before outreach.</p></Dialog>}
    {modal==='exclusions'&&<Dialog title="Excluded customers" onClose={()=>setModal(null)}><div className="service-row"><strong>Customer C004</strong><span>Delivery unverified</span></div><div className="service-row"><strong>Customer C005</strong><span>Opted out</span></div>{state?.order_confirmed&&<div className="service-row"><strong>Meera Shah</strong><span>New purchase; no repeat outreach</span></div>}<p className="field-help">There is no override for an opt-out or missing consent.</p></Dialog>}
    {person&&p&&state&&<Dialog title={p.name} drawer onClose={()=>setModal(null)} footer={
      person==='support'?<Button primary disabled={busy||state.support_assigned} onClick={()=>void run('assign_support')}>{state.support_assigned?'Assigned to you':'Assign to me'}</Button>:
      person==='opted'?<Badge>Marketing suppressed</Badge>:
      <><Button disabled={busy} onClick={()=>void run(state.taken_over?'handback':'takeover')}>{state.taken_over?'Hand back':'Take over'}</Button>
        {person==='rahul'&&<Button primary disabled={!hasConversation||busy||state.checkout_sent||state.paused||state.disconnected||state.plan_needs_review||!state.plan_approved} onClick={()=>void run('approve_checkout')}>{state.checkout_sent?'Checkout pending':'Approve & send'}</Button>}</>}>
      <div className="detail-summary"><Badge>{p.id}</Badge><Badge>{p.channel}</Badge><Badge>Simulated journey</Badge></div>
      <section className="detail-section"><h3>Latest customer context</h3><p className="customer-words">{hasConversation?p.words:'No customer reply has been received in this scenario.'}</p><p className="field-help">{fixtureBasis(person!,!!playback)}</p></section>
      {person==='rahul'&&hasConversation&&<section className="detail-section"><h3>Proposed checkout message</h3><div className="bubble agent">Here is checkout for the same laundry liquid, 1 L × 1. Item price ₹499; final delivery and tax charges are shown at checkout.</div><p className="field-help">Verified facts and separate channel permissions are simulated here. Approval updates message state; it does not confirm payment.</p>
        {state.paused&&<p className="field-error">Agent paused. This action cannot be sent.</p>}{state.plan_needs_review&&<p className="field-error">The plan needs approval under the current policy.</p>}{state.checkout_sent&&<p className="receipt-note" role="status">Simulated message receipt saved. Payment remains pending.</p>}</section>}
      <section className="detail-section"><h3>Conversation and receipts</h3>{hasConversation?p.timeline.map(text=><div className="timeline-item" key={text}>{text}</div>):<p className="field-help">Plan approval schedules contact only. No replies, reminders or payments have been fabricated.</p>}</section>
      {person==='support'&&<p className="notice warning">Sales stay blocked until this issue is resolved. Assignment is not resolution.</p>}
      <details className="disclosure"><summary>Facts and source evidence</summary><p>Same variant · TEST-LAUNDRY-1L. {fixtureBasis(person!,!!playback)}</p><p>Fixture date: 12 October 2026, IST. State persisted in this demo workspace.</p></details>
      {state.taken_over&&person!=='opted'&&person!=='support'&&<p className="notice">You control this conversation. Closing this drawer does not hand it back.</p>}
    </Dialog>}
    {modal==='calculation'&&<Dialog title="Order calculation" drawer onClose={()=>setModal(null)}><dl className="definition-list"><div><dt>Net item revenue</dt><dd>₹499</dd></div><div><dt>Discount/refund recorded</dt><dd>₹0</dd></div><div><dt>Product and fulfilment costs</dt><dd>Missing</dd></div><div><dt>Gateway, communication and agent costs</dt><dd>Unverified</dd></div><div><dt>Net contribution</dt><dd>Unavailable</dd></div><div><dt>Incremental lift</dt><dd>Not measured</dd></div></dl><p className="field-help">Synthetic outside-link order. Returns immature; missing costs are not zero.</p></Dialog>}
    {modal==='help'&&<Dialog title="Help & support" onClose={()=>setModal(null)}><div className="service-row"><div><strong>Source access</strong><small>Inspect mode, permissions and freshness.</small></div><Button onClick={()=>go('connections')}>Connections</Button></div><div className="service-row"><div><strong>Customer issue</strong><small>Review the demo delivery case.</small></div><Button disabled={!state} onClick={()=>setModal('journey:support')}>Open issue</Button></div></Dialog>}
    {toast&&<div className="toast" role="status" aria-live="polite">{toast}</div>}
  </CommandErrorContext.Provider>;
}
