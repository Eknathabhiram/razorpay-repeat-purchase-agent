"""Same-variant checkout, bounded offers and independent payment reconciliation."""
import asyncio
import uuid
from datetime import datetime,timedelta,timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from . import schema as t,planning,execution
from .errors import ApplicationError
from .repositories import ScopedRepository
from .commerce_models import CommerceView
from .payment_sources import shopify_transactions

MAPPING="shopify_payment_id_to_razorpay_receipt_v1"


async def require_demo(session,scope):
    if (await ScopedRepository(session,scope).workspace())["environment"]!="demo":
        raise ApplicationError(422,"STOREFRONT_UNVERIFIED","Development checkout creation remains blocked; Storefront access and buyer context are unverified.")


async def quote(session,scope,request):
    await require_demo(session,scope)
    repo=ScopedRepository(session,scope)
    journey=await execution.scoped_one(session,repo,t.journeys,request.journey_id)
    policy=await planning.latest(session,repo,t.policies)
    draft=await planning.latest(session,repo,t.plan_revisions)
    now=datetime.now(timezone.utc)
    if not policy or not draft or draft["id"]!=journey["plan_revision_id"] or draft["policy_id"]!=policy["id"] or draft["expires_at"]<=now:
        raise ApplicationError(422,"PLAN_STALE","A current approved same-product plan is required.")
    approved=await execution.existing_approval(session,repo,"plan",draft["id"])
    agent=await execution.agent(session,scope)
    if not approved or approved["decision"]!="approve" or not agent or agent["paused"]:
        raise ApplicationError(422,"CHECKOUT_BLOCKED","Approve the current plan and resolve pause before preparing checkout.")
    if journey["owner_id"] and journey["owner_id"]!=scope.user_id:raise ApplicationError(403,"OWNER_REQUIRED","The current conversation owner must prepare this checkout.")
    if journey["state"] in ("support","opted_out","purchased","unknown_outcome","refused","purchase_under_review"):raise ApplicationError(422,"CUSTOMER_HELD","Resolve the customer protection hold first.")
    inflight=await session.scalar(sa.select(t.contact_guards.c.inflight_action_id).where(repo.where(t.contact_guards),t.contact_guards.c.customer_id==journey["customer_id"]))
    if inflight:raise ApplicationError(422,"CONTACT_UNKNOWN","Resolve an in-flight or unknown contact before preparing another checkout.")
    fresh=await planning.compute(session,scope,customer_id=journey['customer_id'])
    item=next((i for i in fresh if i["customer_id"]==str(journey["customer_id"]) and i["variant_id"]==str(journey["variant_id"])),None)
    if not item or not item["eligible"]:raise ApplicationError(422,"FACTS_CHANGED","Current purchase, consent, stock or support evidence blocks checkout.")
    variant=await execution.scoped_one(session,repo,t.variants,journey["variant_id"])
    if variant["stock"] is None or variant["stock"]<request.quantity:raise ApplicationError(422,"STOCK_INSUFFICIENT","Current stock cannot support the confirmed quantity.")
    discount=0;offer_revision=0;expires=now+timedelta(minutes=15);offer=None
    if request.offer_ref:
        if not policy["config_json"].get("offers_enabled") or request.offer_ref not in policy["config_json"].get("approved_offer_refs",[]):
            raise ApplicationError(422,"OFFERS_OFF","The approved plan mandate does not permit this offer.")
        offer_policy=await planning.latest(session,repo,t.offer_policies)
        if not offer_policy or not offer_policy["config_json"]["enabled"]:raise ApplicationError(422,"OFFERS_OFF","Offers remain off until a reviewed offer policy is configured.")
        config=offer_policy["config_json"]
        offer=next((o for o in await planning.rows(session,repo,t.approved_offers) if o["provider_ref"]==request.offer_ref),None)
        if not offer or config["approved_offer_ref"]!=request.offer_ref or offer["variant_id"]!=variant["id"]:
            raise ApplicationError(422,"OFFER_INELIGIBLE","Only the configured approved offer for this exact variant is allowed.")
        if offer["expires_at"]<=now:raise ApplicationError(422,"OFFER_EXPIRED","The approved offer expired.")
        if config["unit_cost_minor"] is None or config["fulfillment_cost_minor"] is None:
            raise ApplicationError(422,"COSTS_MISSING","Verified product and fulfillment costs are required for an offer.")
        discount=offer["discount_minor"]
        margin=variant["price_minor"]*request.quantity-discount-config["unit_cost_minor"]*request.quantity-config["fulfillment_cost_minor"]
        if discount>=variant["price_minor"]*request.quantity or margin<config["minimum_margin_minor"]:
            raise ApplicationError(422,"MARGIN_FLOOR","The approved offer fails the required contribution floor.")
        bucket=next((b for b in await planning.rows(session,repo,t.budget_buckets) if b["policy_id"]==policy["id"]),None)
        if not bucket or bucket["spent_minor"]+bucket["reserved_minor"]+discount+25>bucket["cap_minor"]:
            raise ApplicationError(422,"OFFER_BUDGET","Conservative offer and contact exposure exceeds the approved budget.")
        offer_revision=offer_policy["revision"];expires=min(expires,offer["expires_at"])
    terms={"variant_id":str(variant["id"]),"provider_variant_id":variant["provider_variant_id"],"title":variant["title"],"quantity":request.quantity,
        "unit_price_minor":variant["price_minor"],"item_subtotal_minor":variant["price_minor"]*request.quantity,"discount_minor":discount,
        "shipping_estimate_minor":4000,"tax_estimate_minor":0,"total_estimate_minor":variant["price_minor"]*request.quantity-discount+4000,
        "currency":"INR","stock":variant["stock"],"offer_ref":request.offer_ref,"offer_revision":offer_revision,"policy_id":str(policy["id"]),
        "source_mode":"simulated","buyer_confirmation":{"same_product":True,"quantity":request.quantity,"whatsapp_handoff":True},
        "charges_basis":"Synthetic estimates. Customer reviews final checkout charges and completes payment."}
    return {"terms":terms,"digest":planning.digest(terms),"expires_at":min(expires,draft["expires_at"])}


def link_text(preparation):
    terms=preparation["terms_json"]
    return f"Review your same-product checkout for {terms['title']} · quantity {terms['quantity']}. Confirm final charges and complete payment yourself. Simulated checkout: {preparation['checkout_url']}"


async def validate_link(session,scope,action,now):
    repo=ScopedRepository(session,scope)
    try:preparation=await execution.scoped_one(session,repo,t.checkout_preparations,uuid.UUID(action["payload"]["preparation_id"]))
    except (ApplicationError,ValueError,KeyError):return "checkout_missing"
    if preparation["journey_id"]!=action["journey_id"] or preparation["digest"]!=action["payload"].get("terms_digest"):return "checkout_scope_changed"
    if preparation["expires_at"]<=now or preparation["state"] not in ("prepared","link_proposed"):return "checkout_expired_or_closed"
    if action["payload"].get("text")!=link_text(preparation):return "checkout_content_changed"
    from .commerce_models import CartRequest
    try:
        current=await quote(session,scope,CartRequest(journey_id=action["journey_id"],quantity=preparation["terms_json"]["quantity"],
            confirmed_same_product=True,confirmed_whatsapp_handoff=True,offer_ref=preparation["terms_json"]["offer_ref"]))
    except ApplicationError as error:return error.code.lower()
    if current["digest"]!=preparation["digest"]:return "checkout_terms_changed"
    if action["payload"]["cost_minor"]!=25+preparation["terms_json"]["discount_minor"]:return "checkout_exposure_changed"
    return None


async def case(session,scope,subject,reason):
    await planning.put(session,scope,t.reconciliation_cases,dict(subject_ref=subject,reason=reason,state="open",owner_id=scope.user_id),["subject_ref","reason"])


async def purchase_hold(session,scope,order):
    if not order["customer_id"]:return
    repo=ScopedRepository(session,scope)
    if not any(e["kind"]=="purchase_hold" and e["provenance"].get("source_ref")==str(order["id"]) for e in await planning.rows(session,repo,t.customer_evidence)):
        now=datetime.now(timezone.utc)
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,customer_id=order["customer_id"],kind="purchase_hold",value={"active":True},effective_at=now,
            provenance={"source_mode":order["provenance"]["source_mode"],"classification":"source_verified","source_ref":str(order["id"]),"retrieved_at":now.isoformat()}))
    await execution.hold_customer(session,scope,order["customer_id"],"new_commerce_order",cancel=True)
    await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.customer_id==order["customer_id"],t.journeys.c.state.not_in(("opted_out","support"))).values(state="purchase_under_review"))
    journey_ids=[j["id"] for j in await planning.rows(session,repo,t.journeys) if j["customer_id"]==order["customer_id"]]
    await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.journey_id.in_(journey_ids),t.reminders.c.state=="scheduled").values(state="cancelled"))


async def reconcile(session,scope):
    repo=ScopedRepository(session,scope)
    orders=await planning.rows(session,repo,t.commerce_orders);payments=await planning.rows(session,repo,t.payments)
    transactions=await planning.rows(session,repo,t.commerce_transactions)
    for order in orders:
        txs=[tx for tx in transactions if tx["order_id"]==order["id"] and "razorpay" in tx["gateway"].lower() and tx["kind"] in ("SALE","CAPTURE") and tx["status"]=="SUCCESS"]
        if not txs:continue
        await purchase_hold(session,scope,order)
        subject="order:"+str(order["id"])
        if len(txs)!=1:await case(session,scope,subject,"unsupported_split_transactions");continue
        tx=txs[0]
        candidates=[p for p in payments if p["order_receipt"] and p["order_receipt"]==tx["payment_ref"]]
        if len(candidates)!=1:await case(session,scope,subject,"mapping_missing_or_ambiguous");continue
        payment=candidates[0]
        if len([p for p in payments if p["provider_order_id"]==payment["provider_order_id"]])!=1:
            await case(session,scope,subject,"unsupported_split_payments");continue
        expected=order["provenance"]["source_mode"]
        if payment["source_mode"]!=expected or not tx["test"]:
            await case(session,scope,subject,"account_or_mode_mismatch");continue
        if not payment["captured"] or payment["status"] not in ("captured","refunded") or not payment["provider_order_paid"]:
            await case(session,scope,subject,"payment_not_captured");continue
        if len({order["currency"],payment["currency"],tx["currency"]})!=1 or order["total_minor"]!=payment["amount_minor"] or tx["amount_minor"]!=payment["amount_minor"]:
            await case(session,scope,subject,"payable_total_or_currency_mismatch");continue
        existing=next((m for m in await planning.rows(session,repo,t.payment_order_matches) if m["order_id"]==order["id"] or m["payment_id"]==payment["id"]),None)
        if existing and (existing["order_id"]!=order["id"] or existing["payment_id"]!=payment["id"]):
            await case(session,scope,subject,"mapping_conflict");continue
        match_id=existing["id"] if existing else uuid.uuid4()
        if not existing:
            await session.execute(t.payment_order_matches.insert().values(id=match_id,merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,payment_id=payment["id"],order_id=order["id"],transaction_id=tx["id"],mapping_version=MAPPING,
                evidence={"transaction_ref":tx["provider_transaction_id"],"payment_ref":payment["provider_payment_id"],"source_mode":expected,"amount_minor":payment["amount_minor"],"currency":payment["currency"]}))
            await session.execute(t.confirmed_purchases.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,order_id=order["id"],match_id=match_id,source_mode=expected,total_minor=order["total_minor"],currency=order["currency"]))
            await execution.emit(session,scope,"commerce.purchase_matched",order["id"],{"source_mode":expected,"mapping_version":MAPPING})
        await session.execute(t.reconciliation_cases.update().where(repo.where(t.reconciliation_cases),t.reconciliation_cases.c.subject_ref==subject).values(state="resolved"))
        if order["customer_id"]:
            customer_journeys=[j for j in await planning.rows(session,repo,t.journeys) if j["customer_id"]==order["customer_id"]]
            for journey in customer_journeys:
                if journey["state"] not in ("support","opted_out"):await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey["id"]).values(state="purchased"))
                await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.journey_id==journey["id"],t.checkout_preparations.c.state.in_(("prepared","link_proposed","link_submitted"))).values(state="closed_by_outside_purchase"))
                if tx["preparation_id"]:
                    await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.id==tx["preparation_id"],t.checkout_preparations.c.journey_id==journey["id"]).values(state="payment_matched"))
    matched={m["payment_id"] for m in await planning.rows(session,repo,t.payment_order_matches)}
    for payment in payments:
        if payment["captured"] and payment["id"] not in matched:await case(session,scope,"payment:"+str(payment["id"]),"commerce_order_unmatched")
        elif payment["id"] in matched:
            await session.execute(t.reconciliation_cases.update().where(repo.where(t.reconciliation_cases),t.reconciliation_cases.c.subject_ref=="payment:"+str(payment["id"])).values(state="resolved"))


async def import_payments(session,scope,snapshot,mode):
    repo=ScopedRepository(session,scope);now=datetime.now(timezone.utc)
    for payment in snapshot["payments"]:
        original=next((p for p in await planning.rows(session,repo,t.payments) if p["account_ref"]==snapshot["account_ref"] and p["provider_payment_id"]==payment["id"]),None)
        order=snapshot["orders"].get(payment.get("order_id")) or {}
        if type(payment.get("captured")) is not bool or type(payment.get("amount_refunded")) is not int:
            raise ApplicationError(502,"PAYMENT_FACTS_MISSING","Capture and refund facts must be explicit; missing amounts cannot become zero.")
        captured=payment["captured"];refunded=payment["amount_refunded"]
        if original:
            if original["amount_minor"]!=payment["amount"] or original["currency"]!=payment["currency"]:
                await case(session,scope,"payment:"+str(original["id"]),"immutable_payment_terms_conflict");continue
            captured=captured or original["captured"];refunded=max(refunded,original["refunded_minor"])
            if original["provider_order_id"]!=payment.get("order_id") or original["order_receipt"] and order.get("receipt") and original["order_receipt"]!=order["receipt"]:
                await case(session,scope,"payment:"+str(original["id"]),"provider_reference_conflict");continue
        if not isinstance(payment["amount"],int) or payment["amount"]<0 or refunded>payment["amount"]:raise ApplicationError(422,"PAYMENT_AMOUNT_INVALID","Payment/refund minor-unit values are invalid.")
        status="refunded" if refunded==payment["amount"] and refunded else "captured" if captured else payment["status"]
        await planning.put(session,scope,t.payments,dict(provider_payment_id=payment["id"],provider_order_id=payment.get("order_id"),account_ref=snapshot["account_ref"],source_mode=mode,
            status=status,captured=captured,amount_minor=payment["amount"],refunded_minor=refunded,currency=payment["currency"],order_receipt=order.get("receipt"),
            provider_order_paid=bool(original and original["provider_order_paid"]) or order.get("status")=="paid" and order.get("amount")==order.get("amount_paid")==payment["amount"] and order.get("currency")==payment["currency"],observed_at=now),["account_ref","provider_payment_id"])
    for refund in snapshot["refunds"]:
        payment=next((p for p in await planning.rows(session,repo,t.payments) if p["provider_payment_id"]==refund["payment_id"]),None)
        if not payment or refund["status"]!="processed":continue
        if refund["currency"]!=payment["currency"] or not isinstance(refund["amount"],int) or not 0<=refund["amount"]<=payment["amount_minor"]:
            await case(session,scope,"payment:"+str(payment["id"]),"refund_terms_invalid");continue
        match=next((m for m in await planning.rows(session,repo,t.payment_order_matches) if m["payment_id"]==payment["id"]),None)
        await planning.put(session,scope,t.commerce_adjustments,dict(provider_ref=snapshot["account_ref"]+":"+refund["id"],payment_id=payment["id"],order_id=match["order_id"] if match else None,
            kind="refund",amount_minor=refund["amount"],currency=refund["currency"],evidence={"source_mode":mode,"status":"processed","source_ref":refund["id"]}),["provider_ref"])


async def sync(session,scope,razorpay,shopify):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace()
    if workspace["environment"]!="development":raise ApplicationError(422,"DEVELOPMENT_ONLY","Real payment polling is available only in Development.")
    snapshots=await asyncio.gather(razorpay.snapshot(),shopify_transactions(shopify))
    await repo.workspace(lock=True)
    connectors=await planning.rows(session,repo,t.connectors)
    shop=next(c for c in connectors if c["provider"]=="shopify");gateway=next(c for c in connectors if c["provider"]=="razorpay")
    if shop["provider_account_id"]!=shopify.shop or gateway["source_mode"]!="test" or gateway["provider_account_id"] not in (None,razorpay.account_ref):
        raise ApplicationError(409,"ACCOUNT_MISMATCH","Configured payment/store accounts do not match the workspace binding.")
    customer_map={c["provider_customer_id"]:c["id"] for c in await planning.rows(session,repo,t.customers)}
    for source in snapshots[1]:
        if not source["test"]:continue
        total=source["totalPriceSet"]["shopMoney"]
        order=await planning.put(session,scope,t.commerce_orders,dict(provider_order_id=source["id"],customer_id=customer_map.get((source.get("customer") or {}).get("id")),placed_at=planning.date(source["createdAt"]),
            financial_state=source["displayFinancialStatus"],fulfilment_state=source["displayFulfillmentStatus"],total_minor=planning.money(total["amount"],total["currencyCode"]),currency=total["currencyCode"],
            provenance={"source_mode":"test","classification":"source_verified","source_ref":shopify.shop,"observed_at":source["updatedAt"],"retrieved_at":datetime.now(timezone.utc).isoformat()}),["provider_order_id"])
        for tx in source["transactions"]:
            money=tx["amountSet"]["shopMoney"]
            await planning.put(session,scope,t.commerce_transactions,dict(order_id=order["id"],provider_transaction_id=tx["id"],payment_ref=tx.get("paymentId"),gateway=tx["gateway"],kind=tx["kind"],status=tx["status"],test=tx["test"],
                amount_minor=planning.money(money["amount"],money["currencyCode"]),currency=money["currencyCode"],mapping_version=MAPPING,preparation_id=None),["provider_transaction_id"])
    await import_payments(session,scope,snapshots[0],"test");await reconcile(session,scope)
    # Reimport refund allocation after newly established matches; upsert is deterministic.
    await import_payments(session,scope,snapshots[0],"test")
    now=datetime.now(timezone.utc)
    await session.execute(t.connectors.update().where(repo.where(t.connectors),t.connectors.c.id==gateway["id"]).values(provider_account_id=razorpay.account_ref,state="healthy",last_checked_at=now,version=gateway["version"]+1))
    for capability in ("read_payment_evidence","reconcile_payment"):
        available=capability=="read_payment_evidence" or bool(await planning.rows(session,repo,t.payment_order_matches))
        await session.execute(t.capabilities.update().where(repo.where(t.capabilities),t.capabilities.c.connector_id==gateway["id"],t.capabilities.c.capability==capability).values(status="available" if available else "unverified",verified_at=now,evidence_ref=MAPPING,reason=None if available else "No exact match verified."))
    await session.execute(t.provider_notifications.update().where(repo.where(t.provider_notifications),t.provider_notifications.c.state=="pending").values(state="refetched"))


async def command(session,scope,body,key,correlation,razorpay=None,shopify=None):
    repo=ScopedRepository(session,scope)
    if body.action=="sync":
        await sync(session,scope,razorpay,shopify)
        return await view(session,scope)
    await repo.workspace(lock=True);await require_demo(session,scope)
    hash_value=planning.digest(body)
    await session.execute(insert(t.idempotency).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,operation="commerce.command",key=key,request_hash=hash_value,expires_at=datetime.now(timezone.utc)+timedelta(days=7)).on_conflict_do_nothing(
        index_elements=[t.idempotency.c.merchant_id,t.idempotency.c.workspace_id,t.idempotency.c.actor_id,t.idempotency.c.operation,t.idempotency.c.key]))
    record=(await session.execute(sa.select(t.idempotency).where(repo.where(t.idempotency),t.idempotency.c.actor_id==scope.user_id,t.idempotency.c.operation=="commerce.command",t.idempotency.c.key==key).with_for_update())).mappings().one()
    if record["request_hash"]!=hash_value:raise ApplicationError(409,"IDEMPOTENCY_CONFLICT","Commerce request key was used for different content.")
    if record["result_json"] is not None:return record["result_json"]
    if body.action=="prepare":
        if not body.cart:raise ApplicationError(422,"CONFIRMATION_REQUIRED","Confirm the exact variant, quantity and handoff channel.")
        quoted=await quote(session,scope,body.cart)
        if body.cart.quote_digest!=quoted["digest"]:raise ApplicationError(409,"TERMS_CHANGED","Review the current exact checkout terms before preparing.")
        journey=await execution.scoped_one(session,repo,t.journeys,body.cart.journey_id)
        await execution.hold_customer(session,scope,journey["customer_id"],"checkout_requested",cancel=True)
        await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.journey_id==journey["id"],t.reminders.c.state=="scheduled").values(state="cancelled"))
        await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey["id"]).values(state="checkout_pending"))
        await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.journey_id==body.cart.journey_id,t.checkout_preparations.c.state.in_(("prepared","link_proposed"))).values(state="superseded"))
        identifier=uuid.uuid4()
        await session.execute(t.checkout_preparations.insert().values(id=identifier,merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,journey_id=body.cart.journey_id,terms_json=quoted["terms"],digest=quoted["digest"],
            checkout_url="/app/#/commerce?cart="+str(identifier),expires_at=quoted["expires_at"],state="prepared"))
        await execution.emit(session,scope,"checkout.prepared",identifier,{"source_mode":"simulated","payment_state":"pending"})
    elif body.action=="propose_link":
        prepared=await execution.scoped_one(session,repo,t.checkout_preparations,body.preparation_id)
        if prepared["state"]!="prepared" or prepared["link_action_id"] or prepared["expires_at"]<=datetime.now(timezone.utc):raise ApplicationError(422,"CHECKOUT_CLOSED","A fresh prepared checkout is required.")
        journey=await execution.scoped_one(session,repo,t.journeys,prepared["journey_id"])
        policy=await planning.latest(session,repo,t.policies)
        payload={"customer_id":str(journey["customer_id"]),"variant_id":prepared["terms_json"]["variant_id"],"provider_variant_id":prepared["terms_json"]["provider_variant_id"],
            "customer_alias":(await execution.scoped_one(session,repo,t.customers,journey["customer_id"]))["display_alias"],"variant_title":prepared["terms_json"]["title"],"kind":"checkout_link","channel":"whatsapp","text":link_text(prepared),
            "cost_minor":25+prepared["terms_json"]["discount_minor"],"currency":"INR","source_mode":"simulated","preparation_id":str(prepared["id"]),"terms_digest":prepared["digest"],"plan_revision_id":str(journey["plan_revision_id"]),"policy_id":str(policy["id"])}
        if journey["owner_id"]:payload["actor_id"]=str(scope.user_id)
        identifier=await execution.create_action(session,scope,journey,policy,payload,datetime.now(timezone.utc),prepared["expires_at"],auto=False)
        await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.id==prepared["id"]).values(link_action_id=identifier,state="link_proposed"))
    elif body.action=="seed_offer":
        variant=next((v for v in await planning.rows(session,repo,t.variants) if v["provider_variant_id"]=="demo:laundry:1L"),None)
        if not variant:raise ApplicationError(422,"FACTS_REQUIRED","Load Demo commerce history first.")
        await session.execute(insert(t.approved_offers).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,provider_ref="DEMO-REORDER-25",variant_id=variant["id"],discount_minor=2500,expires_at=datetime.now(timezone.utc)+timedelta(days=1),evidence={"source_mode":"simulated","provider_approved":True,"eligibility":"same-variant confirmed customer","discount_basis":"one cart, not per unit"}).on_conflict_do_nothing(index_elements=[t.approved_offers.c.merchant_id,t.approved_offers.c.workspace_id,t.approved_offers.c.provider_ref]))
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,event_type="commerce."+body.action,target_id=body.preparation_id or scope.workspace_id,correlation_id=correlation,details={"source_mode":"simulated"}))
    result=jsonable_encoder(await view(session,scope))
    await session.execute(t.idempotency.update().where(t.idempotency.c.id==record["id"]).values(result_json=result))
    return result


async def configure_offer(session,scope,body,correlation):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True);await require_demo(session,scope)
    previous=await planning.latest(session,repo,t.offer_policies)
    if (previous["revision"] if previous else 0)!=body.expected_revision:raise ApplicationError(409,"VERSION_CONFLICT","Offer policy changed; review the current revision.")
    if body.enabled and (not body.approved_offer_ref or not any(o["provider_ref"]==body.approved_offer_ref for o in await planning.rows(session,repo,t.approved_offers))):
        raise ApplicationError(422,"OFFER_REQUIRED","Select existing approved offer evidence; new discounts cannot be invented.")
    await session.execute(t.offer_policies.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,revision=body.expected_revision+1,config_json=body.model_dump(mode="json"),digest=planning.digest(body)))
    policy=await planning.latest(session,repo,t.policies)
    if policy:
        refs=[body.approved_offer_ref] if body.enabled else []
        if bool(policy["config_json"].get("offers_enabled"))!=body.enabled or policy["config_json"].get("approved_offer_refs",[])!=refs:
            from .planning_models import PolicyConfig
            config=PolicyConfig.model_validate({**policy["config_json"],"offers_enabled":body.enabled,"approved_offer_refs":refs})
            await session.execute(t.policies.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,revision=policy["revision"]+1,config_json=config.model_dump(mode="json"),digest=planning.digest(config),creator_id=scope.user_id))
            await planning.compute(session,scope,persist=True)
    await execution.emit(session,scope,"offer.policy_changed",scope.workspace_id,{"revision":body.expected_revision+1,"enabled":body.enabled})
    return await view(session,scope)


async def demo_purchase(session,scope,body,correlation):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True);await require_demo(session,scope)
    journey=await execution.scoped_one(session,repo,t.journeys,body.journey_id)
    connector=next(c for c in await planning.rows(session,repo,t.connectors) if c["provider"]=="razorpay")
    existing=(await session.execute(sa.select(t.provider_notifications).where(repo.where(t.provider_notifications),t.provider_notifications.c.connector_id==connector["id"],t.provider_notifications.c.event_key==str(body.event_key)))).mappings().first()
    if existing:
        if existing["payload_hash"]!=planning.digest(body):raise ApplicationError(409,"EVENT_CONFLICT","Event key was used for different fixture evidence.")
        return await view(session,scope)
    preparation=None
    if body.preparation_id:
        preparation=await execution.scoped_one(session,repo,t.checkout_preparations,body.preparation_id)
        if preparation["journey_id"]!=journey["id"]:raise ApplicationError(422,"CART_SCOPE","Checkout and customer journey do not match.")
    variant=await execution.scoped_one(session,repo,t.variants,journey["variant_id"])
    identifier=str(preparation["id"]) if preparation else str(body.event_key)
    payable=preparation["terms_json"]["total_estimate_minor"] if preparation else variant["price_minor"]+4000
    quantity=preparation["terms_json"]["quantity"] if preparation else 1
    now=datetime.now(timezone.utc)
    order=await planning.put(session,scope,t.commerce_orders,dict(provider_order_id="demo:commerce:"+identifier,customer_id=journey["customer_id"],placed_at=now,
        financial_state="PENDING" if body.scenario=="authorized" else "REFUNDED" if body.scenario=="refunded" else "PAID",fulfilment_state="UNFULFILLED",total_minor=payable,currency="INR",
        provenance={"source_mode":"simulated","classification":"source_verified","source_ref":"stage05-payment-fixture","retrieved_at":now.isoformat()}),["provider_order_id"])
    await planning.put(session,scope,t.order_lines,dict(order_id=order["id"],provider_line_id="demo:line:"+identifier,variant_id=variant["id"],quantity=quantity,refunded_quantity=quantity if body.scenario=="refunded" else 0,
        delivery_at=None,return_state="NONE",coverage_complete=True,provenance=order["provenance"]),["order_id","provider_line_id"])
    receipt="demo:receipt:"+identifier
    await planning.put(session,scope,t.commerce_transactions,dict(order_id=order["id"],provider_transaction_id="demo:tx:"+identifier,payment_ref=receipt,gateway="Razorpay demo",kind="SALE",status="SUCCESS",test=True,
        amount_minor=payable,currency="INR",mapping_version=MAPPING,preparation_id=preparation["id"] if preparation and body.scenario!="outside_link" else None),["provider_transaction_id"])
    amount=variant["price_minor"] if body.scenario=="amount_mismatch" else payable
    captured=body.scenario!="authorized"
    snapshot={"account_ref":"demo:"+str(scope.workspace_id),"payments":[{"id":"demo:pay:"+identifier,"order_id":"demo:gateway:"+identifier,"amount":amount,"currency":"INR","captured":captured,
        "status":"refunded" if body.scenario=="refunded" else "captured" if captured else "authorized","amount_refunded":amount if body.scenario=="refunded" else 0}],
        "orders":{"demo:gateway:"+identifier:{"receipt":"different:"+receipt if body.scenario=="unmatched" else receipt,"status":"paid" if captured else "attempted","amount":amount,"amount_paid":amount if captured else 0,"currency":"INR"}},
        "refunds":[{"id":"demo:refund:"+identifier,"payment_id":"demo:pay:"+identifier,"amount":amount,"currency":"INR","status":"processed"}] if body.scenario=="refunded" else []}
    await import_payments(session,scope,snapshot,"simulated");await reconcile(session,scope);await import_payments(session,scope,snapshot,"simulated")
    await session.execute(t.provider_notifications.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,connector_id=connector["id"],event_key=str(body.event_key),payload_hash=planning.digest(body),event_type="demo."+body.scenario,state="processed"))
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,event_type="commerce.demo_evidence",target_id=order["id"],correlation_id=correlation,details={"source_mode":"simulated","scenario":body.scenario}))
    return await view(session,scope)


async def view(session,scope):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace()
    customers={c["id"]:c["display_alias"] for c in await planning.rows(session,repo,t.customers)}
    draft=await planning.latest(session,repo,t.plan_revisions)
    journeys=[{**dict(j),"customer_alias":customers.get(j["customer_id"],"Unknown"),"current_plan":bool(draft and j["plan_revision_id"]==draft["id"])} for j in await planning.rows(session,repo,t.journeys)]
    gateway=next((c for c in await planning.rows(session,repo,t.connectors) if c["provider"]=="razorpay"),None)
    policy=await planning.latest(session,repo,t.offer_policies);payments=await planning.rows(session,repo,t.payments);matches=await planning.rows(session,repo,t.payment_order_matches)
    mandate=await planning.latest(session,repo,t.policies)
    purchases=[]
    for purchase in await planning.rows(session,repo,t.confirmed_purchases):
        match=next(m for m in matches if m["id"]==purchase["match_id"]);payment=next(p for p in payments if p["id"]==match["payment_id"])
        purchases.append({**dict(purchase),"refund_minor":payment["refunded_minor"],"net_payable_minor":purchase["total_minor"]-payment["refunded_minor"],"delivery_verified":False,"attribution":"Observed purchase; incremental lift not measured."})
    return CommerceView(environment=workspace["environment"],source_notice="Demo checkout and payment events are simulated." if workspace["environment"]=="demo" else "Read-only test payment evidence. Storefront creation is not configured; delivery/returns remain independently unverified.",
        storefront_available=False,plan_requires_review=bool(draft and (not mandate or draft["policy_id"]!=mandate["id"] or draft["expires_at"]<=datetime.now(timezone.utc))),last_sync_at=gateway["last_checked_at"] if gateway else None,mapping_version=MAPPING,journeys=jsonable_encoder(journeys),
        preparations=jsonable_encoder([dict(c) for c in await planning.rows(session,repo,t.checkout_preparations)]),payments=jsonable_encoder([dict(p) for p in payments]),matches=jsonable_encoder([dict(m) for m in matches]),purchases=jsonable_encoder(purchases),
        cases=jsonable_encoder([dict(c) for c in await planning.rows(session,repo,t.reconciliation_cases)]),adjustments=jsonable_encoder([dict(a) for a in await planning.rows(session,repo,t.commerce_adjustments)]),offers=jsonable_encoder([dict(o) for o in await planning.rows(session,repo,t.approved_offers)]),offer_policy=dict(policy) if policy else None)
