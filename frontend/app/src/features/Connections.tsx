import {useState} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {api,type Workspace,type Connector} from '../api/client';
import type {components} from '../api/generated';
import {Panel,Button,Badge,Empty,Dialog,RefreshNotice,useOnline} from '../components/shared';
type Readiness={environment:string;notice:string;providers:{provider:string;label:string;status:string;detail:string;action:string|null;checked_at:string|null}[]};
const providerNames:Record<string,string>={shopify:'Shopify',twilio:'WhatsApp',razorpay:'Razorpay',voice:'Browser voice',together:'Together AI',support:'Support'};
type Store=components['schemas']['StoreView'];
export default function Connections({workspace,notify,go,openDevelopment}:{workspace:Workspace;notify:(s:string)=>void;go:(path:string)=>void;openDevelopment:()=>void}) {
  const client=useQueryClient(),online=useOnline(),[showAll,setShowAll]=useState(false),[checking,setChecking]=useState(false),[error,setError]=useState(''),[setup,setSetup]=useState<string|null>(null);
  const readiness=useQuery({queryKey:['merchant-readiness',workspace.id],queryFn:({signal})=>api<Readiness>('/workspaces/'+workspace.id+'/merchant/readiness','GET',undefined,undefined,{signal})});
  const sources=useQuery({queryKey:['connectors',workspace.id],queryFn:()=>api<Connector[]>('/workspaces/'+workspace.id+'/connectors')});
  const shop=sources.data?.find(c=>c.provider==='shopify');
  const store=useQuery({queryKey:['store',workspace.id],queryFn:()=>api<Store>('/workspaces/'+workspace.id+'/connectors/'+shop!.id+'/store'),
    enabled:workspace.environment==='development'&&!!shop,retry:false});
  async function check(){
    if(!shop)return;setChecking(true);
    setError('');
    try {await api('/workspaces/'+workspace.id+'/connectors/'+shop.id+'/check','POST',{expected_version:shop.version});
      await client.invalidateQueries({queryKey:['connectors',workspace.id]});await store.refetch();await readiness.refetch();notify('Shopify read capabilities checked.');}
    catch(e){setError((e as Error).message);}finally{setChecking(false);}
  }
  async function checkPayments(){setChecking(true);setError('');try{await api('/workspaces/'+workspace.id+'/commerce/commands','POST',{action:'sync'},crypto.randomUUID(),{timeoutMs:60000});await readiness.refetch();void client.invalidateQueries({queryKey:['connectors',workspace.id]});void client.invalidateQueries({queryKey:['commerce',workspace.id]});notify('Test payment reads and reconciliation checked. No charge or refund was created.');}catch(e){setError((e as Error).message);}finally{setChecking(false);}}
  const money=(amount:string,currency:string)=>new Intl.NumberFormat('en-IN',{style:'currency',currency}).format(Number(amount));
  return <><div className="page-toolbar"><div><h2>Connections</h2><p className="description">Actual source modes, access and last successful checks.</p></div></div>
    <div className="notice connection-mode"><div><strong>{workspace.environment==='demo'?'You are reviewing the Demo journey':'You are inspecting connected test sources'}</strong><p>{readiness.data?.notice??(workspace.environment==='demo'?'Demo uses synthetic customers and services. Real Shopify and payment reads are available in Development.':'Provider status is being checked for this workspace.')}</p><div className="button-row">{workspace.environment==='demo'&&<Button onClick={openDevelopment}>View connected Development data</Button>}<Button primary={workspace.environment==='demo'} onClick={()=>go('launch')}>{workspace.environment==='demo'?'Start a Demo launch':'View launch steps'}</Button></div></div></div>
    <RefreshNotice failed={readiness.isError} onRetry={()=>void readiness.refetch()}/>{error&&<p className="notice warning" role="alert">{error}</p>}
    {readiness.isPending?<p role="status">Checking connection capabilities…</p>:readiness.isError&&!readiness.data?<Empty title="Connection status unavailable" action={<Button onClick={()=>void readiness.refetch()}>Try again</Button>}>{readiness.error.message}</Empty>:
    <div className="connection-grid">{readiness.data!.providers.map(item=>{const c=sources.data?.find(source=>source.provider===item.provider);return <section className="connection-card" key={item.provider}>
      <div className="provider-head"><span className="provider-logo">{item.provider.slice(0,1).toUpperCase()}</span><h3>{providerNames[item.provider]??item.provider}</h3></div>
      <Badge tone={item.status==='ready'?'teal':item.status==='blocked'||item.status==='demo'?'amber':''}>{item.provider==='shopify'&&store.isError?'Current read failed':item.provider==='shopify'&&store.data?(store.data.warnings.length?'Partial read access':'Connected · development'):item.label}</Badge>
      <p className="small section-space">{item.detail}</p>{item.checked_at&&<p className="field-help">Last verified {new Date(item.checked_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})} IST</p>}
      <div className="button-row section-space">{item.action==='check_shopify'?<Button disabled={checking||!online||workspace.role==='viewer'} onClick={()=>void check()}>{checking?'Checking…':'Check Shopify reads'}</Button>:item.action==='check_payments'?<Button disabled={checking||!online||workspace.role==='viewer'} onClick={()=>void checkPayments()}>{checking?'Checking…':'Check test payment reads'}</Button>:item.action==='setup'?<Button onClick={()=>setSetup(item.provider)}>View setup requirements</Button>:item.action&&<Button onClick={()=>go(item.action==='audience'?'launch?step=setup':item.action==='policy'?'settings':item.action!)}>{item.action==='audience'?'Review Demo data':item.action==='policy'?'Review processing policy':item.action==='whatsapp'?'Open conversations':item.action==='outcomes'?'View payment evidence':'Open conversation test'}</Button>}</div>
      {c&&<details className="disclosure"><summary>Recorded provider checks</summary><p className="field-help">These checks are scoped to this workspace. Missing verification is different from missing credentials.</p>{c.capabilities.map(cap=><p key={cap.capability}><strong>{cap.capability.replaceAll('_',' ')}</strong> · {cap.status}<br/><span className="field-help">{cap.reason}</span></p>)}</details>}
    </section>;})}</div>}
    <div className="section-space"><Panel title="Shopify store data" action={workspace.environment==='development'?<Button primary disabled={checking||!shop||workspace.role==='viewer'} onClick={()=>void check()}>{checking?'Checking…':'Refresh Shopify'}</Button>:undefined}>
      {workspace.environment!=='development'?<Empty title="Select Development for connected store reads">Demo uses separate synthetic journeys; it does not read customer records into the demo.</Empty>:
      store.isPending?<div className="settings-body" role="status">Reading development-store data…</div>:
      store.isError?<div className="settings-body" role="alert"><h3>Store data unavailable</h3><p>{store.error.message}</p><Button onClick={()=>void store.refetch()}>Try again</Button></div>:
      store.data&&<div className="settings-body"><p><strong>{store.data.shop_name}</strong> · {store.data.domain}</p>
        <p className="field-help">Read-only development source · {store.data.product_count} products · checked {new Date(store.data.checked_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})} IST.</p>
        {store.data.warnings.map(w=><p className="notice warning" key={w}>{w}</p>)}
        {!store.data.coverage_complete&&<p className="field-help">Snapshot coverage is partial; do not infer absent history.</p>}
        <div className="page-toolbar section-space"><h3>Products and variants</h3><Button onClick={()=>setShowAll(!showAll)}>{showAll?'Project products only':'Show all products'}</Button></div>
        <div className="table-scroll" role="region" aria-label="Shopify variants" tabIndex={0}><table><thead><tr><th>Product</th><th>SKU</th><th>Price</th><th>Stock</th></tr></thead><tbody>
          {store.data.products.filter(p=>showAll||p.sku.startsWith('TEST-')).map(p=><tr key={p.variant_id}><td>{p.title}<details><summary>Variant reference</summary>{p.variant_id}</details></td><td>{p.sku||'—'}</td><td>{money(p.price,p.currency)}</td><td>{p.stock??'Unknown'}</td></tr>)}
        </tbody></table></div>
        <h3 className="section-space">Customer source records</h3>{store.data.customers===null?<p>Customer access unavailable.</p>:<p>{store.data.customers.length} customer IDs/order counts read. Identity/contact fields and channel permission are not inferred.</p>}
        <h3 className="section-space">Orders</h3>{store.data.orders===null?<p>Order access unavailable.</p>:store.data.orders.length?store.data.orders.map(o=><div className="service-row" key={o.id}><div><strong>{o.name} · {money(o.total,o.currency)}</strong><small>{o.financial_status} · {o.fulfilment_status} · {o.test?'Test order':'Source order'}</small></div><Badge>{o.fulfilment_status==='UNFULFILLED'?'Delivery unverified':o.fulfilment_status}</Badge></div>):<p>No source orders returned.</p>}
        <h3 className="section-space">Draft orders</h3><p>{store.data.drafts===null?'Draft access unavailable.':store.data.drafts.length+' drafts. Draft totals do not establish paid or delivered purchases.'}</p>
        <p className="field-help section-space">Shopify financial and fulfilment states remain separate. This screen does not automate Razorpay reconciliation.</p>
      </div>}
    </Panel></div>
    {setup&&<Dialog title="Connection setup requirements" onClose={()=>setSetup(null)}><p>{setup==='twilio'?'Real WhatsApp needs server-side account credentials, a verified sender/recipient, approved message content and verified public callbacks. Those requirements are incomplete; Demo conversations are available now.':setup==='voice'?'Browser voice is optional. It requires the speech provider and explicit browser microphone/processing permission; it does not enable telephone calls.':'Configure and verify this provider on the server. Credentials are never collected by this merchant screen.'}</p><p className="field-help">A configured key does not authorize customer outreach or live checkout.</p><div className="button-row"><Button primary onClick={()=>{setSetup(null);go('launch');}}>Review the Demo journey</Button><Button onClick={()=>setSetup(null)}>Close</Button></div></Dialog>}
  </>;
}
