"""Capability-specific connection status; configuration never means a verified live service."""
import sqlalchemy as sa
from . import schema as t, planning
from .repositories import ScopedRepository

async def view(session,scope,shopify,razorpay,twilio,together):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace();demo=workspace['environment']=='demo'
    connectors={row['provider']:row for row in await planning.rows(session,repo,t.connectors)}
    point=(await session.execute(sa.select(t.sync_checkpoints).where(repo.where(t.sync_checkpoints),t.sync_checkpoints.c.resource=='commerce'))).mappings().first()
    rows=[]
    def add(provider,label,status,detail,action=None,checked_at=None):
        rows.append({'provider':provider,'label':label,'status':status,'detail':detail,'action':action,'checked_at':checked_at})
    shop=connectors.get('shopify');shop_configured=bool(shopify.client_id and shopify.secret and shopify.shop)
    if demo:
        add('shopify','Demo data loaded' if point else 'Demo data needed','ready' if point else 'setup',
            'Synthetic catalogue and purchase history for this Demo. Connected Shopify reads are in Development.', 'audience')
        add('razorpay','Demo payment evidence','demo','Synthetic payment/order matching is available. No real charge or refund is created.','outcomes')
        add('twilio','Demo conversations','demo','Button replies, automatic journeys and delivery simulations are available after initial launch approval. Real WhatsApp sending is disabled.','whatsapp')
    else:
        shop_bound=bool(shop and shop['source_mode']=='test' and shop['provider_account_id']==shopify.shop)
        checked=bool(shop_bound and shop['last_checked_at'] and shop['state'] in ('healthy','degraded'))
        add('shopify','Connected · development' if checked else 'Configured · check needed' if shop_configured and shop_bound else 'Setup required',
            'ready' if checked else 'configured' if shop_configured and shop_bound else 'setup',
            'Catalogue, customer and order reads. Checkout, delivery/returns and marketing consent are separate capabilities.',
            'check_shopify' if shop_configured and shop_bound else 'setup',shop['last_checked_at'] if shop else None)
        gateway=connectors.get('razorpay');key_ok=bool(razorpay.key.startswith('rzp_test_') and razorpay.secret)
        bound=bool(gateway and gateway['source_mode']=='test' and gateway['provider_account_id'] in (None,razorpay.account_ref))
        payment_count=await session.scalar(sa.select(sa.func.count()).select_from(t.payments).where(repo.where(t.payments),t.payments.c.source_mode=='test',t.payments.c.account_ref==razorpay.account_ref))
        verified=bool(key_ok and bound and gateway['last_checked_at'] and gateway['state']=='healthy')
        add('razorpay','Verified test reads' if verified else 'Test keys configured · check needed' if key_ok and bound else 'Setup required',
            'ready' if verified else 'configured' if key_ok and bound else 'setup',
            f'{payment_count} test payment records in this workspace. Payment reads and reconciliation are available; live charges and refunds are disabled.',
            'check_payments' if key_ok and bound else 'setup',gateway['last_checked_at'] if gateway else None)
        add('twilio','Real sending unavailable','blocked',
            'WhatsApp credentials and sender are missing. Approved content and HTTPS callbacks are also required.' if not twilio.configured else
            'Credentials are configured. Recipient/template authority and public callbacks remain unverified; real sending is disabled.', 'setup')
    voice_verified=await session.scalar(sa.select(sa.exists(sa.select(t.intelligence_turns.c.id).where(repo.where(t.intelligence_turns),t.intelligence_turns.c.state=='completed',t.intelligence_turns.c.receipt['provider'].astext=='together',t.intelligence_turns.c.receipt['account_ref'].astext==together.account_ref)))) if together.configured else False
    auto_verified=await session.scalar(sa.select(sa.exists(sa.select(t.event_outbox.c.id).where(repo.where(t.event_outbox),t.event_outbox.c.event_type=='conversation.interpreted',t.event_outbox.c.details['receipt']['provider'].astext=='together',t.event_outbox.c.details['receipt']['account_ref'].astext==together.account_ref)))) if together.configured else False
    add('together','Verified in this workspace' if voice_verified or auto_verified else 'Configured · processing available' if together.configured else 'Setup required',
        'ready' if voice_verified or auto_verified else 'configured' if together.configured else 'setup',
        'Contextual interpretation uses server-side credentials and the approved processing boundary. Prices, stock and payment facts remain backend authority.', 'policy' if together.configured else 'setup')
    add('support','Internal support ready','ready','Support cases and merchant ownership work in the application database. An external helpdesk is not connected.','whatsapp')
    add('voice','Optional browser voice' if together.configured else 'Voice setup required','configured' if together.configured else 'setup',
        'Browser conversation testing is available with explicit microphone/processing permission. Telephone calls are not enabled.', 'intelligence' if together.configured and demo else 'setup')
    return {'environment':workspace['environment'],'providers':rows,'real_outreach_enabled':False,'real_checkout_enabled':False,
        'notice':'Demo runs the merchant journey with synthetic customers. Switch to Development to inspect real connected test-source reads.' if demo else
        'Development supports connected test-source reads. Real customer outreach and Storefront checkout are not enabled.'}
