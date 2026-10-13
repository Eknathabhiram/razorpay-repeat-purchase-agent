"""Deterministic commerce evidence, repeat_window_v1 and immutable draft revisions."""
import hashlib
import json
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlalchemy as sa
from collections import defaultdict
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from . import schema as t
from .errors import ApplicationError
from .repositories import ScopedRepository
from .planning_models import PolicyConfig, PlanningView
from .shopify_facts import read_facts


def digest(value):
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def money(value, currency):
    if currency != "INR":
        raise ApplicationError(422, "CURRENCY_UNSUPPORTED", "This workspace requires INR amounts.")
    amount = Decimal(value) * 100
    if amount != amount.to_integral_value() or amount < 0:
        raise ApplicationError(422, "MONEY_INVALID", "Source amount has invalid minor units.")
    return int(amount)


def date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def estimate(history, fallback, reminder=None):
    """No quantity scaling; future/impossible dates must be excluded by caller."""
    if reminder:
        return reminder, reminder, "customer_confirmed_date"
    if not history:
        return None, None, "needs_history"
    history = sorted(history, key=lambda line: line["delivery_at"])
    quantity = history[-1]["quantity"]
    compatible = [line["delivery_at"] for line in history if line["quantity"] == quantity]
    # Consecutive purchases must all have compatible quantities. Do not skip an intervening different pack.
    if len(history) >= 3 and len(compatible) == len(history):
        intervals = [(b - a).total_seconds()/86400 for a, b in zip(compatible, compatible[1:])]
        if min(intervals) <= 0:
            return None, None, "invalid_history"
        median = statistics.median(intervals)
        spread = max(1, statistics.median(abs(i-median) for i in intervals))
        return compatible[-1] + timedelta(days=max(0, median-spread)), compatible[-1] + timedelta(days=median+spread), "same_variant_median"
    if fallback:
        last = history[-1]["delivery_at"]
        return last + timedelta(days=max(0, fallback-1)), last + timedelta(days=fallback+1), "merchant_product_fallback"
    return None, None, "needs_history"


async def rows(session, repo, table):
    return (await session.execute(sa.select(table).where(repo.where(table)))).mappings().all()


async def latest(session, repo, table):
    return (await session.execute(sa.select(table).where(repo.where(table)).order_by(table.c.revision.desc()).limit(1))).mappings().first()


async def put(session, scope, table, values, keys):
    statement = insert(table).values(merchant_id=scope.merchant_id, workspace_id=scope.workspace_id, **values)
    await session.execute(statement.on_conflict_do_update(index_elements=[table.c.merchant_id, table.c.workspace_id, *[table.c[k] for k in keys]],
        set_={k:v for k,v in values.items() if k not in keys and k != "id"}))
    query = sa.select(table).where(ScopedRepository(session, scope).where(table), *[table.c[k] == values[k] for k in keys])
    return (await session.execute(query)).mappings().one()


async def checkpoint(session, scope, complete, notes, mode):
    repo = ScopedRepository(session, scope)
    current = await rows(session, repo, t.sync_checkpoints)
    version = current[0]["facts_version"] + 1 if current else 1
    await put(session, scope, t.sync_checkpoints, dict(resource="commerce", cursor=None, facts_version=version,
        coverage_complete=complete, notes=notes, source_mode=mode, synced_at=datetime.now(timezone.utc)), ["resource"])
    return version


async def seed_demo(session, scope):
    repo = ScopedRepository(session, scope)
    if (await repo.workspace())["environment"] != "demo":
        raise ApplicationError(422, "DEMO_ONLY", "Synthetic history can only be loaded in Demo.")
    if await rows(session, repo, t.sync_checkpoints):
        return
    now = datetime.now(timezone.utc)
    provenance = {"source_mode":"simulated", "classification":"source_verified", "source_ref":"stage03-fixture-v1", "retrieved_at":now.isoformat()}
    variant = await put(session, scope, t.variants, dict(provider_variant_id="demo:laundry:1L", provider_product_id="demo:laundry",
        title="Laundry liquid · 1 L", sku="DEMO-LAUNDRY-1L", price_minor=49900, currency="INR", stock=100,
        active=True, provenance=provenance), ["provider_variant_id"])
    for number, name, kind in [(1,"Ananya Rao","ready"),(2,"Rahul Verma","confirmed"),(3,"Customer C003","fallback"),
        (4,"Customer C004","undelivered"),(5,"Customer C005","opted_out"),(6,"Customer C006","support"),
        (7,"Meera Shah","recent"),(8,"Customer C008","no_consent"),(9,"Customer C009","returned")]:
        customer = await put(session, scope, t.customers, dict(provider_customer_id=f"demo:C{number:03}",
            display_alias=name, identity_state="synthetic"), ["provider_customer_id"])
        for event, value in [("consent",{"granted":kind != "no_consent", "channel":"whatsapp", "purpose":"replenishment"}),
                             ("suppression",{"active":kind == "opted_out"}), ("support",{"open":kind == "support"}),
                             ("campaign",{"blocked":False}),('location',{'city':['Mumbai','Bengaluru','Hyderabad'][number%3]})]:
            await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id, workspace_id=scope.workspace_id,
                customer_id=customer["id"], kind=event, value=value, effective_at=now, provenance=provenance))
        if kind == "confirmed":
            await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id, workspace_id=scope.workspace_id,
                customer_id=customer["id"], kind="reminder", value={"date":(now+timedelta(days=2)).isoformat(),"timezone":"Asia/Kolkata","channel":"whatsapp","variant_id":str(variant["id"])},
                effective_at=now, provenance={**provenance,"classification":"customer_stated"}))
        days = [90,60,30] if kind not in ("fallback","undelivered") else [30]
        if kind == "recent": days.append(2)
        for index, age in enumerate(days):
            order = await put(session, scope, t.commerce_orders, dict(provider_order_id=f"demo:C{number}:order{index}",
                customer_id=customer["id"], placed_at=now-timedelta(days=age+2), financial_state="PAID",
                fulfilment_state="UNFULFILLED" if kind == "undelivered" else "DELIVERED", total_minor=49900,
                currency="INR", provenance=provenance), ["provider_order_id"])
            await put(session, scope, t.order_lines, dict(order_id=order["id"], provider_line_id=f"demo:line:{number}:{index}",
                variant_id=variant["id"], quantity=1, refunded_quantity=1 if kind == "returned" else 0,
                delivery_at=None if kind == "undelivered" else now-timedelta(days=age),
                return_state="RETURNED" if kind == "returned" else "NONE", coverage_complete=True, provenance=provenance), ["order_id","provider_line_id"])
    await checkpoint(session, scope, True, ["Synthetic delivery, consent, suppression and support evidence; no Shopify orders were created."], "simulated")


async def sync_shopify(session, scope, adapter):
    repo = ScopedRepository(session, scope)
    workspace = await repo.workspace()
    if workspace["environment"] != "development":
        raise ApplicationError(422,"DEVELOPMENT_ONLY","This adapter is bound only to Development.")
    connectors = await rows(session, repo, t.connectors)
    bound = next((c for c in connectors if c["provider"] == "shopify"), None)
    if not bound or bound["provider_account_id"] != adapter.shop or bound["source_mode"] != "test":
        raise ApplicationError(422,"ACCOUNT_UNBOUND","No matching test store is bound.")
    snapshot = await read_facts(adapter)
    now = datetime.now(timezone.utc)
    provenance = {"source_mode":"test", "classification":"source_verified", "source_ref":adapter.shop,
                  "retrieved_at":now.isoformat()}
    await session.execute(t.variants.update().where(repo.where(t.variants)).values(active=False))
    variant_map, customer_map = {}, {}
    for product in snapshot["products"]:
        for variant in product["variants"]["nodes"]:
            row = await put(session, scope, t.variants, dict(provider_variant_id=variant["id"], provider_product_id=product["id"],
                title=product["title"]+" · "+variant["title"], sku=variant.get("sku"), price_minor=money(variant["price"],snapshot["currency"]),
                currency=snapshot["currency"], stock=variant.get("inventoryQuantity"), active=product["status"]=="ACTIVE",
                provenance=provenance), ["provider_variant_id"])
            variant_map[variant["id"]] = row["id"]
    for customer in snapshot["customers"]:
        row = await put(session, scope, t.customers, dict(provider_customer_id=customer["id"],
            display_alias="Customer "+customer["id"].rsplit("/",1)[-1], identity_state="provider_id_only"), ["provider_customer_id"])
        customer_map[customer["id"]] = row["id"]
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            customer_id=row['id'],kind='location',value={'city':(customer.get('defaultAddress') or {}).get('city')},
            effective_at=now,provenance=provenance))
    for order in snapshot["orders"]:
        total = order["totalPriceSet"]["shopMoney"]
        row = await put(session, scope, t.commerce_orders, dict(provider_order_id=order["id"],
            customer_id=customer_map.get((order.get("customer") or {}).get("id")), placed_at=date(order["createdAt"]),
            financial_state=order["displayFinancialStatus"], fulfilment_state=order["displayFulfillmentStatus"],
            total_minor=money(total["amount"],total["currencyCode"]), currency=total["currencyCode"],
            provenance={**provenance,"observed_at":order["updatedAt"]}), ["provider_order_id"])
        await session.execute(t.order_lines.delete().where(repo.where(t.order_lines),t.order_lines.c.order_id==row["id"]))
        for line in order["lineItems"]["nodes"]:
            delivered = [(f["deliveredAt"],item["quantity"]) for f in order["fulfillments"] if f.get("deliveredAt")
                for item in f["fulfillmentLineItems"]["nodes"] if item["lineItem"]["id"] == line["id"]]
            delivery_at = max((date(d) for d,q in delivered),default=None) if sum(q for d,q in delivered)>=line["quantity"] else None
            refunded = sum(item["quantity"] for refund in order["refunds"] for item in refund["refundLineItems"]["nodes"] if item["lineItem"]["id"]==line["id"])
            returned = any(r["status"] != "CANCELED" for r in order["returns"]["nodes"])
            await put(session,scope,t.order_lines,dict(order_id=row["id"],provider_line_id=line["id"],
                variant_id=variant_map.get((line.get("variant") or {}).get("id")),quantity=line["quantity"],refunded_quantity=refunded,
                delivery_at=delivery_at,return_state="UNVERIFIED" if order["returns"].get("verified") is False else "RETURN_REVIEW" if returned else "NONE",coverage_complete=order["returns"].get("verified") is not False,
                provenance={**provenance,"source_ref":line["id"],"delivery_refs":[f["id"] for f in order["fulfillments"]]}),["order_id","provider_line_id"])
    return await checkpoint(session, scope, snapshot["complete"], snapshot["notes"], "test")


async def compute(session, scope, config=None, persist=False, customer_id=None):
    repo = ScopedRepository(session,scope)
    policy = await latest(session,repo,t.policies)
    if not config and not policy: return []
    config = config or PolicyConfig.model_validate(policy["config_json"])
    points = await rows(session,repo,t.sync_checkpoints)
    point = points[0] if points else None
    now = datetime.now(timezone.utc)
    if customer_id is None:
        customers, variants, orders, lines, events = [await rows(session,repo,table) for table in
            (t.customers,t.variants,t.commerce_orders,t.order_lines,t.customer_evidence)]
    else:
        customers=list((await session.execute(sa.select(t.customers).where(repo.where(t.customers),t.customers.c.id==customer_id))).mappings())
        variants=await rows(session,repo,t.variants)
        orders=list((await session.execute(sa.select(t.commerce_orders).where(repo.where(t.commerce_orders),t.commerce_orders.c.customer_id==customer_id))).mappings())
        lines=list((await session.execute(sa.select(t.order_lines).where(repo.where(t.order_lines),t.order_lines.c.order_id.in_([o['id'] for o in orders])))).mappings())
        events=list((await session.execute(sa.select(t.customer_evidence).where(repo.where(t.customer_evidence),t.customer_evidence.c.customer_id==customer_id))).mappings())
    result = []
    # Index once instead of scanning every customer's complete workspace history.
    evidence_by_customer = defaultdict(dict)
    orders_by_customer = defaultdict(dict)
    lines_by_order = defaultdict(list)
    reminders_by_customer=defaultdict(list)
    for event in sorted(events,key=lambda e:(e['effective_at'],str(e['id']))):
        if event['effective_at'] <= now: evidence_by_customer[event['customer_id']][event['kind']] = event
        if event['kind']=='reminder' and event['effective_at']<=now:reminders_by_customer[event['customer_id']].append(event)
    for order in orders: orders_by_customer[order['customer_id']][order['id']] = order
    for line in lines: lines_by_order[line['order_id']].append(line)
    for customer in customers:
        evidence = evidence_by_customer[customer['id']]
        relevant_orders = orders_by_customer[customer['id']]
        customer_lines = [line for order_id in relevant_orders for line in lines_by_order[order_id]]
        for variant in variants:
            if variant["provider_variant_id"] not in config.variant_ids: continue
            relevant = [line for line in customer_lines if line['variant_id'] == variant['id']]
            history = [line for line in relevant if line["delivery_at"] and not line["refunded_quantity"] and line["return_state"]=="NONE"
                       and relevant_orders[line["order_id"]]["financial_state"]=="PAID"]
            reasons=[]
            if not point or not point["coverage_complete"]: reasons.append("coverage_incomplete")
            if not point or now-point["synced_at"]>timedelta(hours=24): reasons.append("facts_stale")
            if any(line['variant_id'] is None for line in customer_lines): reasons.append('variant_unmapped')
            if not variant["active"] or variant["stock"] is None or variant["stock"]<=0: reasons.append("stock_unavailable")
            if variant["price_minor"] is None: reasons.append("price_missing")
            consent=evidence.get("consent",{}).get("value",{})
            if not consent.get("granted") or consent.get("channel")!="whatsapp" or consent.get("purpose")!="replenishment": reasons.append("consent_missing")
            if "suppression" not in evidence: reasons.append("suppression_unverified")
            elif evidence["suppression"]["value"].get("active"): reasons.append("opted_out")
            if "support" not in evidence: reasons.append("support_unverified")
            elif evidence["support"]["value"].get("open"): reasons.append("open_issue")
            if "campaign" not in evidence: reasons.append("campaign_unverified")
            elif evidence["campaign"]["value"].get("blocked"): reasons.append("campaign_conflict")
            if evidence.get("purchase_hold",{}).get("value",{}).get("active"): reasons.append("new_relevant_purchase")
            if not history: reasons.append("delivery_unverified")
            if any(line["return_state"] not in ("NONE","UNVERIFIED") or line["refunded_quantity"] for line in relevant): reasons.append("return_or_refund")
            if any(line["return_state"]=="UNVERIFIED" for line in relevant): reasons.append("returns_unverified")
            if any(not line["coverage_complete"] for line in relevant): reasons.append("line_coverage_incomplete")
            if any(line["quantity"]<=0 or line["delivery_at"]>now or line["delivery_at"]<relevant_orders[line["order_id"]]["placed_at"] for line in history): reasons.append("invalid_history")
            newest = max((line["delivery_at"] for line in history),default=None)
            if any(relevant_orders[line["order_id"]]["placed_at"]>now-timedelta(days=config.recent_purchase_days) or
                (newest and relevant_orders[line["order_id"]]["placed_at"]>newest) for line in relevant): reasons.append("new_relevant_purchase")
            scoped_reminders=[e for e in reminders_by_customer[customer['id']] if
                (e["value"].get("variant_id")==str(variant["id"]) or not e["value"].get("variant_id") and len(config.variant_ids)==1)]
            confirmed=max(scoped_reminders,key=lambda e:e["effective_at"]) if scoped_reminders else None
            reminder=date(confirmed["value"].get("date")) if confirmed else None
            start,end,basis=estimate(history,config.fallback_days,reminder)
            if basis in ("needs_history","invalid_history"): reasons.append(basis)
            if start and start>now+timedelta(days=7): reasons.append("not_due")
            item=dict(customer_id=customer["id"],variant_id=variant["id"],policy_id=policy["id"] if policy else None,
                facts_version=point["facts_version"] if point else 0,eligible=not reasons,exclusion_codes=list(dict.fromkeys(reasons)),
                window_start=start,window_end=end,basis=basis,evidence_json={"estimator_version":"repeat_window_v1",
                    "line_ids":[str(line["id"]) for line in history],"deliveries":[jsonable_encoder({"date":line["delivery_at"],"quantity":line["quantity"],"provenance":line["provenance"]}) for line in history],
                    "customer_evidence_ids":[str(e["id"]) for e in evidence.values()],"source_mode":point["source_mode"] if point else "unavailable",
                    "checked_at":now.isoformat(),"customer_alias":customer["display_alias"],"city":evidence.get('location',{}).get('value',{}).get('city'),"variant_title":variant["title"],"provider_variant_id":variant["provider_variant_id"]})
            if persist:
                item["id"]=uuid.uuid4()
                await session.execute(t.opportunities.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,**item))
            result.append(item)
    return jsonable_encoder(result)


async def view(session,scope):
    repo=ScopedRepository(session,scope)
    workspace=await repo.workspace()
    points=await rows(session,repo,t.sync_checkpoints)
    point=points[0] if points else None
    policy=await latest(session,repo,t.policies)
    draft=await latest(session,repo,t.plan_revisions)
    items=await rows(session,repo,t.opportunities)
    current=[]
    if policy and point:
        for item in items:
            if item["policy_id"]==policy["id"] and item["facts_version"]==point["facts_version"]:
                current.append(dict(item))
        # Refreshes append immutable snapshots; newest per customer/variant is current.
        unique={}
        for item in sorted(current,key=lambda i:i["created_at"]): unique[(item["customer_id"],item["variant_id"])]=item
        current=list(unique.values())
    draft_data=None
    if draft:
        members=[dict(m) for m in await rows(session,repo,t.plan_members) if m["plan_revision_id"]==draft["id"]]
        stale=not policy or not point or draft["policy_id"]!=policy["id"] or draft["facts_version"]!=point["facts_version"] or draft["expires_at"]<=datetime.now(timezone.utc)
        draft_data={**dict(draft),"members":members,"selected_count":sum(m["selected"] for m in members),"stale":stale,"status":"needs_review" if stale else "draft"}
    return PlanningView(environment=workspace["environment"],facts_version=point["facts_version"] if point else 0,
        fact_counts={"variants":len(await rows(session,repo,t.variants)),"customers":len(await rows(session,repo,t.customers)),
                     "orders":len(await rows(session,repo,t.commerce_orders)),"order_lines":len(await rows(session,repo,t.order_lines)),
                     "confirmed_deliveries":sum(line["delivery_at"] is not None for line in await rows(session,repo,t.order_lines)),
                     "paid_unfulfilled_orders":sum(order["financial_state"]=="PAID" and order["fulfilment_state"]=="UNFULFILLED" for order in await rows(session,repo,t.commerce_orders))},
        coverage_complete=point["coverage_complete"] if point else False,coverage_notes=point["notes"] if point else ["Commerce facts have not been synchronized."],
        synced_at=point["synced_at"] if point else None,policy=dict(policy) if policy else None,variants=jsonable_encoder([dict(v) for v in await rows(session,repo,t.variants)]),opportunities=jsonable_encoder(current),
        draft=jsonable_encoder(draft_data),notice="Draft edits require fresh audience approval. Review exact messages in Execution; no checkout is created here.")


async def command(session,scope,operation,body,key,correlation,adapter=None):
    repo=ScopedRepository(session,scope)
    await repo.workspace(lock=True)
    hash_value=digest(body)
    await session.execute(insert(t.idempotency).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,
        operation="planning."+operation,key=key,request_hash=hash_value,expires_at=datetime.now(timezone.utc)+timedelta(days=7)).on_conflict_do_nothing(
            index_elements=[t.idempotency.c.merchant_id,t.idempotency.c.workspace_id,t.idempotency.c.actor_id,t.idempotency.c.operation,t.idempotency.c.key]))
    record=(await session.execute(sa.select(t.idempotency).where(repo.where(t.idempotency),t.idempotency.c.actor_id==scope.user_id,
        t.idempotency.c.operation=="planning."+operation,t.idempotency.c.key==key).with_for_update())).mappings().one()
    if record["request_hash"]!=hash_value: raise ApplicationError(409,"IDEMPOTENCY_CONFLICT","Request key was used for different planning content.")
    if record["result_json"] is not None: return record["result_json"]
    if operation=="facts":
        if body.action=="seed_demo": await seed_demo(session,scope)
        elif body.action=='seed_scale_demo':
            from .scale_demo import seed
            await seed(session,scope)
        elif body.action=="sync": await sync_shopify(session,scope,adapter)
        elif body.action=="refresh":
            points=await rows(session,repo,t.sync_checkpoints)
            if points:
                point=points[0]
                # Advance evidence generation without pretending recomputation refreshed provider data.
                await session.execute(t.sync_checkpoints.update().where(repo.where(t.sync_checkpoints)).values(facts_version=point["facts_version"]+1))
        await compute(session,scope,persist=True)
    elif operation=="policy":
        previous=await latest(session,repo,t.policies)
        revision=previous["revision"] if previous else 0
        if revision!=body.expected_revision: raise ApplicationError(409,"VERSION_CONFLICT","Policy changed. Review the current revision.")
        variants=await rows(session,repo,t.variants)
        if not set(body.config.variant_ids).issubset({v["provider_variant_id"] for v in variants}):
            raise ApplicationError(422,"SCOPE_INVALID","Policy scope must use exact variants from this workspace.")
        if body.config.offers_enabled:
            offer_policy=await latest(session,repo,t.offer_policies)
            approved={offer["provider_ref"] for offer in await rows(session,repo,t.approved_offers)}
            if not offer_policy or not offer_policy["config_json"]["enabled"] or not set(body.config.approved_offer_refs).issubset(approved):
                raise ApplicationError(422,"OFFER_POLICY_REQUIRED","Configure reviewed approved-offer evidence before enabling it in a plan policy.")
        await session.execute(t.policies.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,revision=revision+1,
            config_json=body.config.model_dump(mode="json"),digest=digest(body.config),creator_id=scope.user_id))
        await compute(session,scope,persist=True)
    elif operation=="draft":
        previous=await latest(session,repo,t.plan_revisions)
        revision=previous["revision"] if previous else 0
        if revision!=body.expected_revision: raise ApplicationError(409,"VERSION_CONFLICT","Draft changed. Review its current revision.")
        current=await view(session,scope)
        if not current.policy: raise ApplicationError(422,"POLICY_REQUIRED","Save a policy before drafting a plan.")
        selected=set(map(str,body.selected))
        if len(selected)!=len(body.selected): raise ApplicationError(422,"AUDIENCE_DUPLICATE","Select each opportunity only once.")
        eligible={str(item["id"]) for item in current.opportunities if item["eligible"]}
        if not selected or not selected.issubset(eligible): raise ApplicationError(422,"AUDIENCE_INVALID","Only current eligible opportunities can be selected.")
        # Re-evaluate facts at command time; stale UI cannot bypass new purchase/stock/consent evidence.
        fresh=await compute(session,scope)
        fresh_pairs={(item["customer_id"],item["variant_id"]) for item in fresh if item["eligible"]}
        if any((item["customer_id"],item["variant_id"]) not in fresh_pairs for item in current.opportunities if str(item["id"]) in selected):
            raise ApplicationError(409,"FACTS_CHANGED","Facts changed. Refresh opportunities before drafting.")
        scope_json={"selected":sorted(selected),"policy_digest":current.policy["digest"],"facts_version":current.facts_version,
                    "same_variant_only":True,"offers_enabled":current.policy["config_json"].get("offers_enabled",False),"approved_offer_refs":current.policy["config_json"].get("approved_offer_refs",[]),"execution":"none"}
        if body.audience_filters:scope_json['audience_filters']=body.audience_filters.model_dump(mode='json')
        plan_id=uuid.uuid4()
        await session.execute(t.plan_revisions.insert().values(id=plan_id,merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            revision=revision+1,policy_id=current.policy["id"],facts_version=current.facts_version,scope_json=scope_json,digest=digest(scope_json),
            expires_at=datetime.now(timezone.utc)+timedelta(hours=24)))
        members=[dict(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            plan_revision_id=plan_id,opportunity_id=item['id'],selected=str(item['id']) in selected) for item in current.opportunities]
        for start in range(0,len(members),500):
            await session.execute(t.plan_members.insert(),members[start:start+500])
    result=jsonable_encoder(await view(session,scope))
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,
        event_type="planning."+operation,target_id=scope.workspace_id,correlation_id=correlation,details={"facts_version":result["facts_version"],"operation":operation}))
    await session.execute(t.idempotency.update().where(t.idempotency.c.id==record["id"]).values(result_json=result))
    return result
