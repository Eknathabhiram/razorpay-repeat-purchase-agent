"""Observed brand-wide outcomes. No fabricated causal lift or zero unknown costs."""
import uuid
from datetime import datetime,timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from . import schema as t,planning,execution
from .repositories import ScopedRepository
from .errors import ApplicationError
from .outcomes_models import OutcomeView
from .planning_models import PolicyChange,PolicyConfig

COST_FIELDS=('product_cost_minor','fulfillment_cost_minor','gateway_fee_minor','contact_cost_minor','agent_cost_minor','retained_tax_minor')

async def learn_reminder(session,scope,turn,voice,due_at):
    repo=ScopedRepository(session,scope);journey=await execution.scoped_one(session,repo,t.journeys,voice['journey_id'])
    await session.execute(insert(t.learning_records).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,customer_id=journey['customer_id'],variant_id=journey['variant_id'],turn_id=turn['id'],kind='confirmed_reminder',
        value={'due_at':due_at.isoformat(),'timezone':'Asia/Kolkata','channel':'whatsapp','permission_scope':'one_time'},
        provenance={'source_mode':'simulated','classification':'customer_confirmed','source_ref':str(turn['id']),'confirmed_at':datetime.now(timezone.utc).isoformat()}).on_conflict_do_nothing(index_elements=[t.learning_records.c.merchant_id,t.learning_records.c.workspace_id,t.learning_records.c.turn_id,t.learning_records.c.kind]))

async def accounting(session,scope,body,correlation):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace(lock=True)
    if workspace['environment']!='demo' or scope.role!='owner':raise ApplicationError(403,'DEMO_OWNER_REQUIRED','Only the Demo owner may review synthetic accounting costs.')
    purchase=await execution.scoped_one(session,repo,t.confirmed_purchases,body.purchase_id)
    records=[r for r in await planning.rows(session,repo,t.accounting_reviews) if r['purchase_id']==purchase['id']]
    revision=max((r['revision'] for r in records),default=0)
    if revision!=body.expected_revision:raise ApplicationError(409,'VERSION_CONFLICT','Review the current accounting revision.')
    if body.retained_tax_minor is not None and body.retained_tax_minor>purchase['total_minor']:raise ApplicationError(422,'TAX_INVALID','Retained tax cannot exceed original payable.')
    match=await execution.scoped_one(session,repo,t.payment_order_matches,purchase['match_id'])
    payment=await execution.scoped_one(session,repo,t.payments,match['payment_id'])
    if body.retained_tax_minor is not None and body.retained_tax_minor>purchase['total_minor']-payment['refunded_minor']:raise ApplicationError(422,'TAX_INVALID','Retained tax cannot exceed remaining payable after refunds.')
    await session.execute(t.accounting_reviews.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,purchase_id=purchase['id'],revision=revision+1,costs={**{k:getattr(body,k) for k in COST_FIELDS},'refund_minor_at_review':payment['refunded_minor']},returns_mature=body.confirmed_demo_return_maturity,actor_id=scope.user_id,source_mode='simulated'))
    await audit(session,scope,'accounting_review',purchase['id'],correlation)
    return await view(session,scope)

async def suggest(session,scope,correlation):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace(lock=True)
    if workspace['environment']!='demo':raise ApplicationError(422,'DEMO_ONLY','Learning suggestions currently use labelled Demo evidence.')
    policy=await planning.latest(session,repo,t.policies)
    if not policy:raise ApplicationError(422,'POLICY_REQUIRED','Review a policy first.')
    learning=await planning.rows(session,repo,t.learning_records)
    if learning and policy['config_json']['contact_cap']>1:
        diff={'contact_cap':1};evidence={'learning_refs':sorted(str(x['id']) for x in learning),'reason':'Confirmed requests for more time warrant reviewing a lower contact cap. This is a conservative proposal, not measured uplift.'}
        digest=planning.digest({'policy_id':str(policy['id']),'diff':diff,'evidence':evidence})
        await session.execute(insert(t.policy_suggestions).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,policy_id=policy['id'],kind='review_contact_cap',proposed_diff=diff,evidence=evidence,digest=digest).on_conflict_do_nothing(index_elements=[t.policy_suggestions.c.merchant_id,t.policy_suggestions.c.workspace_id,t.policy_suggestions.c.policy_id,t.policy_suggestions.c.kind,t.policy_suggestions.c.digest]))
    await audit(session,scope,'suggestion_review',scope.workspace_id,correlation)
    return await view(session,scope)

async def decide(session,scope,suggestion_id,body,correlation):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
    if scope.role!='owner':raise ApplicationError(403,'OWNER_REQUIRED','Only the owner may change the approved policy boundary.')
    suggestion=await execution.scoped_one(session,repo,t.policy_suggestions,suggestion_id)
    existing=(await session.execute(sa.select(t.suggestion_decisions).where(repo.where(t.suggestion_decisions),t.suggestion_decisions.c.suggestion_id==suggestion_id))).mappings().first()
    if existing:raise ApplicationError(409,'ALREADY_DECIDED','This suggestion already has an immutable decision.')
    policy=await planning.latest(session,repo,t.policies)
    if not policy or policy['id']!=suggestion['policy_id'] or policy['revision']!=body.expected_policy_revision:raise ApplicationError(409,'POLICY_STALE','Review the current policy before deciding.')
    result_id=None
    if body.decision=='accept':
        config=PolicyConfig.model_validate({**policy['config_json'],**suggestion['proposed_diff']})
        await planning.command(session,scope,'policy',PolicyChange(expected_revision=policy['revision'],config=config),uuid.uuid4(),correlation)
        result_id=(await planning.latest(session,repo,t.policies))['id']
    await session.execute(t.suggestion_decisions.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,suggestion_id=suggestion_id,decision=body.decision,actor_id=scope.user_id,result_policy_id=result_id))
    await audit(session,scope,'suggestion_'+body.decision,suggestion_id,correlation)
    return await view(session,scope)

async def audit(session,scope,action,target,correlation):
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,event_type='outcomes.'+action,target_id=target,correlation_id=correlation,details={'source':'owner_review','measured_time_saved':None}))

async def view(session,scope):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace()
    orders={o['id']:o for o in await planning.rows(session,repo,t.commerce_orders)}
    matches={m['id']:m for m in await planning.rows(session,repo,t.payment_order_matches)}
    payments={p['id']:p for p in await planning.rows(session,repo,t.payments)}
    transactions={x['id']:x for x in await planning.rows(session,repo,t.commerce_transactions)}
    accounting=await planning.rows(session,repo,t.accounting_reviews);assignments=await planning.rows(session,repo,t.cohort_assignments);lines=await planning.rows(session,repo,t.order_lines)
    customers={c['id']:c['display_alias'] for c in await planning.rows(session,repo,t.customers)}
    totals={};purchases=[]
    for purchase in await planning.rows(session,repo,t.confirmed_purchases):
        order=orders[purchase['order_id']];match=matches[purchase['match_id']];payment=payments[match['payment_id']];tx=transactions[match['transaction_id']]
        records=[a for a in accounting if a['purchase_id']==purchase['id']];review=max(records,key=lambda a:a['revision']) if records else None
        costs={k:review['costs'].get(k) for k in COST_FIELDS} if review else {k:None for k in COST_FIELDS}
        missing=[k for k in COST_FIELDS if costs[k] is None];refund=payment['refunded_minor'];net=purchase['total_minor']-refund
        current_accounting=bool(review and review['costs'].get('refund_minor_at_review')==refund)
        if review and not current_accounting:missing.append('refund_accounting_review_required')
        mature=bool(review and review['returns_mature'] and current_accounting);contribution=net-sum(costs.values()) if not missing and mature else None
        purchase_variants={l['variant_id'] for l in lines if l['order_id']==order['id']}
        eligible_cohorts=[a for a in assignments if a['customer_id']==order['customer_id'] and a['variant_id'] in purchase_variants and a['created_at']<=order['placed_at']]
        # Exclusive reporting assignment is earliest enrolled customer/variant; later plans
        # preserve their records but cannot double-count a purchase across cohorts.
        cohort=min(eligible_cohorts,key=lambda a:(a['created_at'],str(a['id']))) if eligible_cohorts else None
        item={'id':purchase['id'],'order_id':order['id'],'customer_alias':customers.get(order['customer_id'],'Unassigned customer'),'currency':purchase['currency'],'gross_payable_minor':purchase['total_minor'],'refund_minor':refund,'net_payable_minor':net,'contribution_minor':contribution,'missing_costs':missing,'returns_mature':mature,'source_mode':purchase['source_mode'],'outside_link':tx['preparation_id'] is None,'cohort_plan_id':str(cohort['plan_revision_id']) if cohort else None,'accounting_revision':review['revision'] if review else 0,'costs':costs}
        purchases.append(item)
        total=totals.setdefault(purchase['currency'],{'currency':purchase['currency'],'purchase_count':0,'gross_payable_minor':0,'refund_minor':0,'net_payable_minor':0,'contribution_minor':0,'contribution_complete':True,'outside_link_count':0})
        for field in ('gross_payable_minor','refund_minor','net_payable_minor'):total[field]+=item[field]
        total['purchase_count']+=1;total['outside_link_count']+=int(item['outside_link'])
        if contribution is None:total['contribution_complete']=False
        else:total['contribution_minor']+=contribution
    for total in totals.values():
        if not total['contribution_complete']:total['contribution_minor']=None
    plans={p['id']:p for p in await planning.rows(session,repo,t.plan_revisions)};cohorts=[]
    for plan_id in {a['plan_revision_id'] for a in assignments}:
        members=[a for a in assignments if a['plan_revision_id']==plan_id]
        assigned_customers={a['customer_id'] for a in members}
        observed_customers={orders[p['order_id']]['customer_id'] for p in purchases if p['cohort_plan_id']==str(plan_id)}
        cohorts.append({'plan_id':str(plan_id),'revision':plans[plan_id]['revision'],'assigned_pairs':len(members),'assigned_customers':len(assigned_customers),'observed_purchases':sum(p['cohort_plan_id']==str(plan_id) for p in purchases),'observed_repeat_purchase_rate':len(observed_customers)/len(assigned_customers) if assigned_customers else None,'assignment_kind':'approved_audience','treatment_control_verified':False,'incremental_lift':None})
    policy=await planning.latest(session,repo,t.policies);decisions={d['suggestion_id']:d for d in await planning.rows(session,repo,t.suggestion_decisions)}
    suggestions=[{**dict(s),'policy_revision':next(p['revision'] for p in await planning.rows(session,repo,t.policies) if p['id']==s['policy_id']),'stale':not policy or policy['id']!=s['policy_id'],'decision':decisions[s['id']]['decision'] if s['id'] in decisions else None} for s in await planning.rows(session,repo,t.policy_suggestions)]
    learning=[{**dict(l),'customer_alias':customers.get(l['customer_id'],'Customer')} for l in await planning.rows(session,repo,t.learning_records)]
    interventions=[{'id':a['id'],'event_type':a['event_type'],'at':a['created_at'],'actor_id':a['actor_id'],'time_saved_seconds':None} for a in await planning.rows(session,repo,t.audit_events) if a['event_type'].startswith(('execution.','outcomes.'))]
    return OutcomeView(environment=workspace['environment'],totals=jsonable_encoder(list(totals.values())),purchases=jsonable_encoder(purchases),cohorts=jsonable_encoder(cohorts),learning=jsonable_encoder(learning),suggestions=jsonable_encoder(suggestions),interventions=jsonable_encoder(interventions[-100:]),
        notice='Observed, independently matched brand-wide purchases include purchases outside agent links. Demo figures are synthetic; Development uses test-provider facts. Payable includes shipping/tax and is not net merchandise revenue.',
        evidence_limits=['Incremental lift and time saved are not measured.','Approved audience cohorts are not randomized treatment/control groups.','Unknown costs or immature returns prevent contribution claims.','Development delivery/physical returns and accounting costs remain unverified.'])
