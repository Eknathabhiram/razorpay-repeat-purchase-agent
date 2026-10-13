"""Scoped, bounded merchant read models. No fabricated cohort counts or send authority."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import sqlalchemy as sa
from fastapi.encoders import jsonable_encoder
from . import schema as t, planning, execution
from .repositories import ScopedRepository


def current_opportunities(repo, policy, point):
    ranked = sa.select(t.opportunities, sa.func.row_number().over(
        partition_by=(t.opportunities.c.customer_id, t.opportunities.c.variant_id),
        order_by=(t.opportunities.c.created_at.desc(), t.opportunities.c.id.desc())).label('rank')).where(
        repo.where(t.opportunities), t.opportunities.c.policy_id == (policy['id'] if policy else None),
        t.opportunities.c.facts_version == (point['facts_version'] if point else -1)).subquery()
    return sa.select(ranked).where(ranked.c.rank == 1).subquery()


async def planning_context(session, scope):
    repo = ScopedRepository(session, scope)
    policy = await planning.latest(session, repo, t.policies)
    point = (await session.execute(sa.select(t.sync_checkpoints).where(repo.where(t.sync_checkpoints),
        t.sync_checkpoints.c.resource == 'commerce'))).mappings().first()
    draft = await planning.latest(session, repo, t.plan_revisions)
    stale = bool(draft and (not policy or not point or draft['policy_id'] != policy['id'] or
        draft['facts_version'] != point['facts_version'] or draft['expires_at'] <= datetime.now(timezone.utc)))
    return repo, policy, point, draft, stale, current_opportunities(repo, policy, point)


async def approved_plan(session, repo):
    return (await session.execute(sa.select(t.plan_revisions).join(t.approvals,
        sa.and_(t.approvals.c.resource_id == t.plan_revisions.c.id,
            t.approvals.c.resource_type == 'plan', t.approvals.c.decision == 'approve')).where(
        repo.where(t.plan_revisions), repo.where(t.approvals)).order_by(t.plan_revisions.c.revision.desc()).limit(1))).mappings().first()


def search_clause(search, *columns):
    # Literal substring search; '%' and '_' from the user are not wildcard authority.
    escaped = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return sa.or_(*(column.ilike('%' + escaped + '%', escape='\\') for column in columns))

def date_bounds(query,column,date_from=None,date_to=None):
    if date_from:query=query.where(column>=datetime.combine(date_from,datetime.min.time(),ZoneInfo('Asia/Kolkata')))
    if date_to:query=query.where(column<datetime.combine(date_to+timedelta(days=1),datetime.min.time(),ZoneInfo('Asia/Kolkata')))
    return query

def opportunity_filters(query,items,search='',city='',date_from=None,date_to=None):
    query=query.where(search_clause(search,items.c.evidence_json['customer_alias'].astext,items.c.evidence_json['variant_title'].astext,items.c.evidence_json['provider_variant_id'].astext))
    value=items.c.evidence_json['city'].astext
    if city:query=query.where(sa.func.coalesce(value,'')=='' if city=='__unknown__' else sa.func.lower(value)==city.lower())
    return date_bounds(query,items.c.window_start,date_from,date_to)

def customer_city(repo,customer_id):
    return sa.select(t.customer_evidence.c.value['city'].astext).where(repo.where(t.customer_evidence),t.customer_evidence.c.customer_id==customer_id,t.customer_evidence.c.kind=='location',t.customer_evidence.c.effective_at<=datetime.now(timezone.utc)).order_by(t.customer_evidence.c.effective_at.desc(),t.customer_evidence.c.id.desc()).limit(1).scalar_subquery()


async def planning_summary(session, scope):
    repo, policy, point, draft, stale, items = await planning_context(session, scope)
    counts = (await session.execute(sa.select(sa.func.count().label('total'),
        sa.func.count().filter(items.c.eligible).label('eligible'),
        sa.func.count().filter(~items.c.eligible).label('excluded')).select_from(items))).mappings().one()
    selected = await session.scalar(sa.select(sa.func.count()).select_from(t.plan_members).where(
        repo.where(t.plan_members), t.plan_members.c.plan_revision_id == (draft['id'] if draft else None), t.plan_members.c.selected))
    return jsonable_encoder({'policy': dict(policy) if policy else None,
        'facts_version': point['facts_version'] if point else 0,
        'coverage_complete': bool(point and point['coverage_complete']),
        'coverage_notes': point['notes'] if point else ['Source facts have not been loaded.'],
        'synced_at': point['synced_at'] if point else None, 'counts': dict(counts),
        'variants': [dict(v) for v in await planning.rows(session, repo, t.variants)],
        'draft': {**dict(draft), 'selected_count': selected, 'stale': stale} if draft else None})

async def filters(session,scope):
    repo=ScopedRepository(session,scope)
    city=customer_city(repo,t.customers.c.id)
    locations=sa.select(city.label('city')).where(repo.where(t.customers)).subquery()
    values=(await session.execute(sa.select(locations.c.city,sa.func.count().label('count')).group_by(locations.c.city).order_by(locations.c.city).limit(501))).mappings().all()
    return {'cities':[dict(row) for row in values[:500]],'truncated':len(values)>500,'date_timezone':'Asia/Kolkata'}

async def launch(session,scope,page=1,page_size=25):
    repo=ScopedRepository(session,scope);agent=await execution.agent(session,scope)
    review=await execution.manifest(session,scope)
    policy=await planning.latest(session,repo,t.policies)
    draft=await planning.latest(session,repo,t.plan_revisions)
    if review:
        decision=await execution.existing_approval(session,repo,'plan',draft['id'])
        review={**review,'decision':decision['decision'] if decision else None,'messages':review['messages'][(page-1)*page_size:page*page_size],
            'page':page,'page_size':page_size,'total':review['selected_count'],'mandate':policy['config_json'] if policy else {},'audience_filters':draft['scope_json'].get('audience_filters')}
    return {'version':agent['version'] if agent else 0,'paused':bool(agent and agent['paused']),'plan_review':review}


async def opportunity_page(session, scope, page=1, page_size=25, search='', eligibility='all',city='',date_from=None,date_to=None):
    repo, policy, point, draft, stale, items = await planning_context(session, scope)
    selected = sa.exists(sa.select(t.plan_members.c.id).where(repo.where(t.plan_members),
        t.plan_members.c.plan_revision_id == (draft['id'] if draft and not stale else None),
        t.plan_members.c.opportunity_id == items.c.id, t.plan_members.c.selected))
    query=opportunity_filters(sa.select(items,selected.label('selected')),items,search,city,date_from,date_to)
    eligible_total=await session.scalar(sa.select(sa.func.count()).select_from(query.where(items.c.eligible).subquery()))
    if eligibility != 'all': query = query.where(items.c.eligible == (eligibility == 'eligible'))
    total = await session.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
    records = (await session.execute(query.order_by(items.c.eligible.desc(),
        items.c.evidence_json['customer_alias'].astext, items.c.id).limit(page_size).offset((page-1)*page_size))).mappings().all()
    return jsonable_encoder({'items': [dict(row) for row in records], 'total': total,
        'page': page, 'page_size': page_size, 'facts_version': point['facts_version'] if point else 0,
        'policy_id': policy['id'] if policy else None,'eligible_total':eligible_total})


async def summary(session, scope):
    repo, policy, point, draft, stale, items = await planning_context(session, scope)
    workspace = await repo.workspace()
    plan = await approved_plan(session, repo)
    agent = await execution.agent(session, scope)
    cohort = sa.and_(repo.where(t.journeys), t.journeys.c.plan_revision_id == (plan['id'] if plan else None))
    distribution = dict((await session.execute(sa.select(t.journeys.c.state, sa.func.count()).where(cohort)
        .group_by(t.journeys.c.state))).all())
    pending = await session.scalar(sa.select(sa.func.count()).select_from(t.proposed_actions).join(t.journeys,
        t.journeys.c.id == t.proposed_actions.c.journey_id).where(repo.where(t.proposed_actions), cohort,
        t.proposed_actions.c.state == 'awaiting_review'))
    support = await session.scalar(sa.select(sa.func.count()).select_from(t.support_cases).join(t.journeys,
        t.journeys.c.id == t.support_cases.c.journey_id).where(repo.where(t.support_cases), cohort,
        t.support_cases.c.state != 'resolved'))
    bucket = (await session.execute(sa.select(t.budget_buckets).where(repo.where(t.budget_buckets),
        t.budget_buckets.c.policy_id == (policy['id'] if policy else None)))).mappings().first()
    return jsonable_encoder({'environment': workspace['environment'], 'paused': bool(agent and agent['paused']),
        'approval_current':bool(plan and draft and policy and plan['id']==draft['id'] and plan['policy_id']==policy['id'] and plan['expires_at']>datetime.now(timezone.utc)),
        'version': agent['version'] if agent else 0, 'policy': dict(policy) if policy else None,
        'plan': dict(plan) if plan else None, 'synced_at': point['synced_at'] if point else None,
        'coverage_complete': bool(point and point['coverage_complete']),
        'customer_base': await session.scalar(sa.select(sa.func.count()).select_from(t.customers).where(repo.where(t.customers))),
        'eligible_customers': await session.scalar(sa.select(sa.func.count(sa.distinct(items.c.customer_id))).where(items.c.eligible)),
        'approved_customers': await session.scalar(sa.select(sa.func.count(sa.distinct(t.journeys.c.customer_id))).where(cohort)),
        'journey_count': sum(distribution.values()), 'distribution': distribution,
        'pending_messages': pending, 'support_issues': support,
        'unknown_outcomes': distribution.get('unknown_outcome', 0),
        'other_exceptions':distribution.get('reply_review',0),
        'matched_purchases': await session.scalar(sa.select(sa.func.count()).select_from(t.confirmed_purchases).where(repo.where(t.confirmed_purchases))),
        'budget': {'cap_minor': bucket['cap_minor'] if bucket else policy['config_json']['budget_minor'] if policy else None,
            'spent_minor': bucket['spent_minor'] if bucket else 0, 'reserved_minor': bucket['reserved_minor'] if bucket else 0,
            'scope': 'policy_version', 'policy_revision': policy['revision'] if policy else None}})


async def journey_page(session, scope, page=1, page_size=25, search='', state='all', inbox=False,city='',date_from=None,date_to=None):
    repo = ScopedRepository(session, scope)
    # One newest journey per customer/variant; older plans remain available in immutable audit views.
    ranked = sa.select(t.journeys, sa.func.row_number().over(partition_by=(t.journeys.c.customer_id,
        t.journeys.c.variant_id), order_by=(t.journeys.c.created_at.desc(), t.journeys.c.id.desc())).label('rank')).where(repo.where(t.journeys)).subquery()
    latest_event = sa.select(t.whatsapp_events.c.text).where(repo.where(t.whatsapp_events),
        t.whatsapp_events.c.customer_id == ranked.c.customer_id, t.whatsapp_events.c.kind == 'inbound').order_by(
            t.whatsapp_events.c.created_at.desc(), t.whatsapp_events.c.id.desc()).limit(1).scalar_subquery()
    pending = sa.select(sa.func.count()).where(repo.where(t.proposed_actions),
        t.proposed_actions.c.journey_id == ranked.c.id, t.proposed_actions.c.state == 'awaiting_review').scalar_subquery()
    location=customer_city(repo,ranked.c.customer_id)
    query = sa.select(ranked.c.id, ranked.c.customer_id, ranked.c.state, ranked.c.owner_id,location.label('city'),
        ranked.c.variant_id, ranked.c.created_at, ranked.c.updated_at,
        t.customers.c.display_alias.label('customer_alias'), t.variants.c.title.label('variant_title'),
        t.variants.c.sku, latest_event.label('latest_reply'), pending.label('pending_count')).join(t.customers,
            t.customers.c.id == ranked.c.customer_id).join(t.variants, t.variants.c.id == ranked.c.variant_id).where(
                ranked.c.rank == 1, repo.where(t.customers), repo.where(t.variants),
                search_clause(search, t.customers.c.display_alias, t.customers.c.provider_customer_id, t.variants.c.title,
                    sa.func.coalesce(t.variants.c.sku, '')))
    if state == 'review': query = query.where(pending > 0)
    elif state == 'held': query = query.where(ranked.c.state.in_(('support','unknown_outcome','reply_review','opted_out','refused','purchase_under_review')))
    elif state=='contacted':query=query.where(ranked.c.state.in_(('contacted','awaiting_reply','checkout_pending','reminder_scheduled')))
    elif state != 'all': query = query.where(ranked.c.state == state)
    if city:query=query.where(sa.func.coalesce(location,'')=='' if city=='__unknown__' else sa.func.lower(location)==city.lower())
    query=date_bounds(query,ranked.c.updated_at,date_from,date_to)
    if inbox:
        outgoing = sa.exists(sa.select(t.action_receipts.c.id).join(t.dispatch_attempts,
            t.dispatch_attempts.c.id == t.action_receipts.c.attempt_id).join(t.proposed_actions,
                t.proposed_actions.c.id == t.dispatch_attempts.c.action_id).where(repo.where(t.action_receipts),
                    repo.where(t.dispatch_attempts), repo.where(t.proposed_actions), t.proposed_actions.c.journey_id == ranked.c.id))
        query = query.where(sa.or_(latest_event.is_not(None), outgoing, pending > 0))
    total = await session.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
    records = (await session.execute(query.order_by(ranked.c.updated_at.desc(), ranked.c.id).limit(page_size)
        .offset((page-1)*page_size))).mappings().all()
    return jsonable_encoder({'items': [dict(row) for row in records], 'page': page, 'page_size': page_size, 'total': total})


async def thread(session, scope, journey_id):
    repo = ScopedRepository(session, scope)
    journey = await execution.scoped_one(session, repo, t.journeys, journey_id)
    customer = await execution.scoped_one(session, repo, t.customers, journey['customer_id'])
    variant = await execution.scoped_one(session, repo, t.variants, journey['variant_id'])
    actions = (await session.execute(sa.select(t.proposed_actions).where(repo.where(t.proposed_actions),
        t.proposed_actions.c.journey_id == journey_id).order_by(t.proposed_actions.c.created_at.desc()).limit(100))).mappings().all()
    action_ids = [a['id'] for a in actions]
    receipt_rows = (await session.execute(sa.select(t.action_receipts, t.dispatch_attempts.c.action_id,
        t.whatsapp_deliveries.c.status.label('delivery_status')).join(t.dispatch_attempts,
            t.dispatch_attempts.c.id == t.action_receipts.c.attempt_id).outerjoin(t.whatsapp_deliveries,
                sa.and_(t.whatsapp_deliveries.c.receipt_id == t.action_receipts.c.id, repo.where(t.whatsapp_deliveries))).where(
                    repo.where(t.action_receipts), repo.where(t.dispatch_attempts), t.dispatch_attempts.c.action_id.in_(action_ids),t.action_receipts.c.status=='submitted').order_by(t.action_receipts.c.created_at))).mappings().all()
    receipts = {r['action_id']: r for r in receipt_rows}
    events = (await session.execute(sa.select(t.whatsapp_events).where(repo.where(t.whatsapp_events),
        t.whatsapp_events.c.customer_id == journey['customer_id'], t.whatsapp_events.c.kind == 'inbound').order_by(
            t.whatsapp_events.c.created_at.desc(), t.whatsapp_events.c.id.desc()).limit(100))).mappings().all()
    choices = (await session.execute(sa.select(t.event_outbox.c.details).where(repo.where(t.event_outbox),
        t.event_outbox.c.event_type == 'whatsapp.choice', t.event_outbox.c.subject_id == journey['customer_id']).order_by(
            t.event_outbox.c.created_at.desc()).limit(100))).scalars().all()
    choice_by_ref = {c['message_ref']: c for c in choices}
    timeline = []
    for action in actions:
        receipt = receipts.get(action['id'])
        if receipt and receipt['status'] == 'submitted':
            timeline.append({'id': str(action['id']), 'direction':'outbound', 'text': action['payload']['text'],
                'buttons':action['payload'].get('reply_buttons', []), 'status': receipt['delivery_status'] or 'submitted',
                'source_mode': receipt['source_mode'], 'at': receipt['created_at']})
    for event in events:
        timeline.append({'id':str(event['id']), 'direction':'inbound', 'text':event['text'],
            'buttons':[], 'status':event['classification'], 'source_mode':event['source_mode'],
            'at':event['created_at'], 'choice':choice_by_ref.get(event['message_ref'])})
    last_inbound = max((e['created_at'] for e in events), default=None)
    window_end = last_inbound + timedelta(hours=24) if last_inbound else None
    agent = await execution.agent(session, scope)
    exceptions=(await session.execute(sa.select(t.event_outbox.c.details).where(repo.where(t.event_outbox),t.event_outbox.c.event_type=='conversation.exception',t.event_outbox.c.subject_id==journey_id).order_by(t.event_outbox.c.created_at.desc()).limit(1))).scalars().first()
    return jsonable_encoder({'journey': {**dict(journey), 'customer_alias':customer['display_alias'], 'variant_title':variant['title']},
        'timeline':sorted(timeline, key=lambda e:(e['at'], e['direction'], e['id'])),
        'history_limited':len(events) == 100 or len(actions) == 100,
        'proposals':[dict(a) for a in actions if a['state'] == 'awaiting_review'],
        'window_end':window_end, 'window_open':bool(window_end and window_end > datetime.now(timezone.utc)),
        'paused':bool(agent and agent['paused']), 'version':agent['version'] if agent else 0,
        'exception':exceptions,'environment':(await repo.workspace())['environment']})
