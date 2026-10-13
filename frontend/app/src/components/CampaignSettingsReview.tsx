import {money,number} from '../api/merchant';
import type {ScopeProduct} from './ProductScope';
type Settings={variant_ids:string[];budget_minor:number;contact_cap:number;contact_start:string;contact_end:string;fallback_days:number|null;recent_purchase_days:number;offers_enabled:boolean;approved_offer_refs?:string[]};
export default function CampaignSettingsReview({settings,previous,products,eligible,excluded}:{settings:Settings;previous:Settings|null;products:ScopeProduct[];eligible:number;excluded:number}){
 const names=settings.variant_ids.map(id=>products.find(p=>p.provider_variant_id===id)?.title??'Selected product');
 const rows=[['Products',names.join(', ')],['Campaign spend limit',money(settings.budget_minor)],['Weekly contacts per customer',String(settings.contact_cap)],['Sending hours',settings.contact_start+'–'+settings.contact_end],['Offers',settings.offers_enabled?number(settings.approved_offer_refs?.length??0)+' approved offer':'No discount'],['Routine conversations','Handled automatically by the agent'],['Merchant queue','Support requests, opt-outs and exceptions']];
 const changes=previous?[
  previous.budget_minor!==settings.budget_minor?['Campaign spend limit',money(previous.budget_minor),money(settings.budget_minor)]:null,
  previous.contact_cap!==settings.contact_cap?['Weekly contacts',String(previous.contact_cap),String(settings.contact_cap)]:null,
  previous.contact_start!==settings.contact_start||previous.contact_end!==settings.contact_end?['Sending hours',previous.contact_start+'–'+previous.contact_end,settings.contact_start+'–'+settings.contact_end]:null,
  JSON.stringify(previous.variant_ids)!==JSON.stringify(settings.variant_ids)?['Product selection',number(previous.variant_ids.length)+' products',number(settings.variant_ids.length)+' products']:null,
  previous.offers_enabled!==settings.offers_enabled?['Offers',previous.offers_enabled?'Enabled':'No discount',settings.offers_enabled?'Enabled':'No discount']:null,
 ].filter((v):v is string[]=>!!v):[];
 return <div className="campaign-settings-review"><p className="review-lead">{previous?'Confirm your campaign settings.':'Confirm the settings for your first campaign.'}</p><dl className="campaign-review-summary">{rows.map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl><div className="review-audience-note"><strong>{number(eligible)} eligible customers</strong><span>{number(excluded)} excluded by consent, purchase or support checks.</span></div>{changes.length>0&&<details className="review-changes"><summary>{changes.length} settings changed</summary>{changes.map(([name,before,after])=><div key={name}><span>{name}</span><span><s>{before}</s> → <strong>{after}</strong></span></div>)}</details>}<p className="field-help section-space">Saving authorizes the agent to interpret customer replies using limited product and conversation context. Customer outreach starts only after you approve the campaign audience.</p></div>;
}
