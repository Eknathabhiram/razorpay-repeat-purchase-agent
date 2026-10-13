"""Signed notifications request authoritative polling; they never confirm browser success."""
import base64
import hashlib
import hmac
import json
import os
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from . import schema as t,planning
from .errors import ApplicationError


def signature_valid(provider,raw,signature,secret):
    if not secret or not signature:return False
    value=hmac.new(secret.encode(),raw,hashlib.sha256).digest()
    expected=base64.b64encode(value).decode() if provider=="shopify" else value.hex()
    try:return hmac.compare_digest(expected.encode("ascii"),signature.encode("ascii"))
    except (UnicodeError,AttributeError):return False


async def receive(request,session,provider,workspace_id,connector_id):
    secret=os.getenv("SHOPIFY_WEBHOOK_SECRET" if provider=="shopify" else "RAZORPAY_WEBHOOK_SECRET","")
    account=os.getenv("RAZORPAY_WEBHOOK_ACCOUNT_ID","") if provider=="razorpay" else None
    if not secret or provider=="razorpay" and not account:raise ApplicationError(503,"CALLBACK_UNCONFIGURED","A verified callback secret/account binding has not been configured.")
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>1048576:raise ApplicationError(413,"EVENT_TOO_LARGE","Callback exceeds its size limit.")
    signature=request.headers.get("x-shopify-hmac-sha256" if provider=="shopify" else "x-razorpay-signature")
    if not signature_valid(provider,bytes(raw),signature,secret):raise ApplicationError(401,"SIGNATURE_INVALID","Callback signature is invalid.")
    try:body=json.loads(raw)
    except (ValueError,TypeError):raise ApplicationError(422,"EVENT_INVALID","Callback must contain a valid JSON object.") from None
    if not isinstance(body,dict):raise ApplicationError(422,"EVENT_INVALID","Callback must contain a valid JSON object.")
    row=(await session.execute(sa.select(t.connectors).where(t.connectors.c.id==connector_id,t.connectors.c.workspace_id==workspace_id,t.connectors.c.provider==provider,t.connectors.c.source_mode=="test"))).mappings().first()
    if not row:raise ApplicationError(404,"NOT_FOUND","Callback connector not found.")
    if provider=="shopify":
        if request.headers.get("x-shopify-shop-domain")!=row["provider_account_id"]:raise ApplicationError(403,"ACCOUNT_MISMATCH","Callback store does not match the bound account.")
        event_type=request.headers.get("x-shopify-topic","")
        if event_type not in ("orders/create","orders/paid","orders/updated","refunds/create","returns/create"):raise ApplicationError(422,"EVENT_UNSUPPORTED","Unsupported commerce callback.")
    else:
        if body.get("account_id")!=account or not row["provider_account_id"]:raise ApplicationError(403,"ACCOUNT_MISMATCH","Callback payment account is not bound.")
        event_type=body.get("event","")
        if event_type not in ("payment.captured","payment.authorized","payment.failed","refund.processed","order.paid"):raise ApplicationError(422,"EVENT_UNSUPPORTED","Unsupported payment callback.")
    # Canonical body hash prevents changing an unsigned event-ID header to replay the same evidence.
    hash_value=planning.digest(body)
    await session.execute(insert(t.provider_notifications).values(merchant_id=row["merchant_id"],workspace_id=workspace_id,connector_id=connector_id,event_key=provider+":"+hash_value,
        payload_hash=hash_value,event_type=event_type,state="pending").on_conflict_do_nothing(index_elements=[t.provider_notifications.c.merchant_id,t.provider_notifications.c.workspace_id,t.provider_notifications.c.connector_id,t.provider_notifications.c.event_key]))
    return {"accepted":True,"requires_authoritative_refetch":True}
