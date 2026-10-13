import {useId,useState} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {api} from '../api/client';
import type {Summary,ReplyButton,Page} from '../api/merchant';
import {number} from '../api/merchant';
import {Badge,Button,Dialog,Icon,useOnline} from './shared';

export type AudienceFilters={search:string;city:string;date_from:string;date_to:string};
export function CityDateFilters({workspace,value,onChange,dateLabel='Activity date'}:{workspace:string;value:{city:string;date_from:string;date_to:string};onChange:(value:{city:string;date_from:string;date_to:string})=>void;dateLabel?:string}){
 const id=useId(),options=useQuery({queryKey:['merchant-filters',workspace],queryFn:({signal})=>api<{cities:{city:string|null;count:number}[]}>('/workspaces/'+workspace+'/merchant/filters','GET',undefined,undefined,{signal}),staleTime:60000});
 return <div className="city-date-filters"><label htmlFor={id+'city'}>Customer city<select aria-label="Customer city" id={id+'city'} value={value.city} onChange={e=>onChange({...value,city:e.target.value})}><option value="">All cities</option>{options.data?.cities.filter(item=>item.city).map(item=><option key={item.city!} value={item.city!}>{item.city} · {number(item.count)}</option>)}<option value="__unknown__">Unknown city</option></select></label><label htmlFor={id+'from'}>{dateLabel} · from<input id={id+'from'} type="date" value={value.date_from} max={value.date_to||undefined} onChange={e=>onChange({...value,date_from:e.target.value})}/></label><label htmlFor={id+'to'}>To · inclusive, IST<input id={id+'to'} type="date" value={value.date_to} min={value.date_from||undefined} onChange={e=>onChange({...value,date_to:e.target.value})}/></label>{(value.city||value.date_from||value.date_to)&&<Button onClick={()=>onChange({city:'',date_from:'',date_to:''})}>Clear filters</Button>}{options.isError&&<span className="field-error">City options unavailable. <button className="text-button" onClick={()=>void options.refetch()}>Retry</button></span>}</div>;
}

export function Pagination({data,page,setPage,pageSize,setPageSize}:{data:Pick<Page<unknown>,'total'>|undefined;page:number;setPage:(value:number)=>void;pageSize:number;setPageSize:(value:number)=>void}){
 const pages=Math.max(1,Math.ceil((data?.total??0)/pageSize));
 return <div className="pagination"><span>{data?.total?`${number((page-1)*pageSize+1)}–${number(Math.min(page*pageSize,data.total))} of ${number(data.total)}`:'No matching records'}</span><div><label>Rows per page <select value={pageSize} onChange={e=>{setPageSize(Number(e.target.value));setPage(1);}}><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label><Button disabled={page<=1} onClick={()=>setPage(page-1)}>Previous</Button><span>Page {page} of {number(pages)}</span><Button disabled={page>=pages} onClick={()=>setPage(page+1)}>Next</Button></div></div>;
}
export function ReplyChoices({buttons,onChoose,disabled=false}:{buttons:ReplyButton[];onChoose?:(button:ReplyButton)=>void;disabled?:boolean}){
 if(!buttons.length)return null;
 return <div className="reply-choices" aria-label={onChoose?'Demo customer reply choices':'Reply choices shown to customer'}>{buttons.map(button=>onChoose?<button key={button.id} disabled={disabled} type="button" onClick={()=>onChoose(button)}>{button.title}</button>:<span key={button.id}>{button.title}</span>)}</div>;
}
export function MerchantControls({workspace}:{workspace:{id:string;role:string}}){
 const client=useQueryClient(),online=useOnline(),[open,setOpen]=useState(false),[error,setError]=useState('');
 const query=useQuery({queryKey:['merchant-overview',workspace.id],queryFn:({signal})=>api<Summary>('/workspaces/'+workspace.id+'/merchant/overview','GET',undefined,undefined,{signal}),refetchInterval:10000});
 const change=useMutation({mutationFn:()=>api('/workspaces/'+workspace.id+'/merchant/commands','POST',{action:query.data?.paused?'resume':'pause',expected_version:query.data?.version??0},crypto.randomUUID()),onSuccess:()=>{setOpen(false);void client.invalidateQueries({queryKey:['merchant-overview',workspace.id]});void client.invalidateQueries({queryKey:['merchant-thread',workspace.id]});void client.invalidateQueries({queryKey:['execution',workspace.id]});},onError:e=>{setError(e.message);void query.refetch();}});
 const paused=query.data?.paused;
 return <div className="agent-controls"><span className={'status '+(paused?'paused':'')}><span className="status-dot"/>{query.data?(paused?'Outreach paused':!(query.data.approval_current??(query.data.plan&&new Date(query.data.plan.expires_at)>new Date()))?'Initial review required':query.data.policy?.config_json.mode==='bounded'?'Within approved limits':'Review-first'):'Checking state'}</span><Button disabled={!query.data||query.isError||change.isPending||!online||workspace.role==='viewer'} onClick={()=>{setError('');setOpen(true);}}><Icon name="pause"/>{paused?'Resume agent':'Pause agent'}</Button>{open&&<Dialog title={paused?'Resume approved outreach?':'Pause new outreach?'} onClose={()=>setOpen(false)} footer={<><Button onClick={()=>setOpen(false)}>Cancel</Button><Button primary disabled={change.isPending} onClick={()=>change.mutate()}>{paused?'Resume approved work':'Pause agent'}</Button></>}><p>{paused?'The backend rechecks current plans, facts, ownership and customer protections.':'New dispatches stop. In-flight receipts and opt-outs still update, and saved reminders remain.'}</p>{error&&<p className="field-error" role="alert">{error}</p>}</Dialog>}</div>;
}
export function ModeNotice({environment}:{environment:string}){return null;}
