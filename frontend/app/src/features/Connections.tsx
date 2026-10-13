import {useState} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {api,type Workspace,type Connector} from '../api/client';
import type {components} from '../api/generated';
import {Panel,Button,Badge,Empty} from '../components/shared';
type Store=components['schemas']['StoreView'];
export default function Connections({workspace,notify}:{workspace:Workspace;notify:(s:string)=>void}) {
  const client=useQueryClient(),[showAll,setShowAll]=useState(false),[checking,setChecking]=useState(false);
  const sources=useQuery({queryKey:['connectors',workspace.id],queryFn:()=>api<Connector[]>('/workspaces/'+workspace.id+'/connectors')});
  const shop=sources.data?.find(c=>c.provider==='shopify');
  const store=useQuery({queryKey:['store',workspace.id],queryFn:()=>api<Store>('/workspaces/'+workspace.id+'/connectors/'+shop!.id+'/store'),
    enabled:workspace.environment==='development'&&!!shop,retry:false});
  async function check(){
    if(!shop)return;setChecking(true);
    try {await api('/workspaces/'+workspace.id+'/connectors/'+shop.id+'/check','POST',{expected_version:shop.version});
      await client.invalidateQueries({queryKey:['connectors',workspace.id]});await store.refetch();notify('Shopify read capabilities checked.');}
    catch(e){notify((e as Error).message);}finally{setChecking(false);}
  }
  const money=(amount:string,currency:string)=>new Intl.NumberFormat('en-IN',{style:'currency',currency}).format(Number(amount));
  return <><div className="page-toolbar"><div><h2>Connections</h2><p className="description">Actual source modes, access and last successful checks.</p></div></div>
    {sources.isPending?<p role="status">Loading connection access…</p>:sources.isError?<p role="alert">{sources.error.message}</p>:
    <div className="connection-grid">{sources.data.map(c=><section className="connection-card" key={c.id}>
      <div className="provider-head"><span className="provider-logo">{c.provider.slice(0,1).toUpperCase()}</span><h3>{c.provider==='shopify'?'Shopify':c.provider==='twilio'?'WhatsApp':c.provider==='razorpay'?'Razorpay':c.provider==='voice'?'Browser voice':'Support'}</h3></div>
      <Badge tone={c.state==='healthy'||(c.provider==='shopify'&&store.data)?'teal':''}>{c.source_mode==='simulated'?'Simulated':c.provider==='shopify'&&store.isError?'Read check failed':c.provider==='shopify'&&store.data?(store.data.warnings.length?'Partial access':'Connected · development'):c.state==='healthy'?'Connected · test':c.state.replaceAll('_',' ')}</Badge>
      <p className="small muted section-space">{c.last_checked_at?'Checked '+new Date(c.last_checked_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST':'No capability verified in this workspace.'}</p>
      <details className="disclosure"><summary>Permissions and capabilities</summary>{c.capabilities.map(cap=><p key={cap.capability}><strong>{cap.capability.replaceAll('_',' ')}</strong> · {cap.status}<br/><span className="field-help">{cap.reason}</span></p>)}</details>
    </section>)}</div>}
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
  </>;
}
