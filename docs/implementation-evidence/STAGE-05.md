# Stage 05 — checkout, payment evidence and approved offers

13 October 2026 · ready_for_review

Open [Commerce](http://127.0.0.1:8766/app/#/commerce) with the existing owner account. In Demo, save and approve a current audience, confirm the customer's same product/quantity/WhatsApp handoff, review checkout terms and prepare a simulated cart. Prepare its link for separate message approval in Execution. Sending a link leaves payment pending. Inject separately labelled commerce/gateway evidence to inspect capture, unmatched references, amount mismatch, authorization, refunds and outside-link purchases.

In Development, Refresh Shopify & Razorpay evidence performs only authenticated provider reads. Storefront creation stays blocked because no token/cart capability or buyer context is configured. The real test checkout is not repeated.

## Implemented behavior

Migration 0005_commerce adds scoped checkout receipts, payment facts, commerce transaction mapping, immutable payment/order matches and purchases, owned reconciliation cases, refund adjustments, immutable approved offers/offer policies and deduplicated provider notifications. Checkout terms and their digest are immutable to the app role; only receipt state/link association can change. All migration DDL is frozen.

Checkout preparation infers the exact prior variant from the approved scoped journey, requires explicit same-product/quantity/channel confirmation, verifies current stock/consent/protection/plan and freezes minor-unit terms. Cart preparation cancels incompatible unsent contact. The Demo receipt expires within 15 minutes and the approved plan boundary. The separate link action always requires exact content approval, including in bounded mode. Dispatch rechecks terms, offer revision, price/stock, expiry, ownership, pause, shared caps and conservative exposure. Preparing/sending a link creates no payment or purchase.

The typed Storefront adapter verifies exact variant/quantity/checkout origin and exposes no mutation by default. Its contract is tested with mocked transport. No real Storefront token exists here; live/development cart creation, private checkout-token storage and full buyer-context handling remain blocked release work. No additional agent gateway order or automatic charge is created.

Razorpay adapter rejects live keys and exposes only GET payment/order/refund reads, with bounded pagination and redacted evidence projection. Shopify transaction reads are paginated and use existing scopes. A versioned mapping adapter joins Shopify transaction paymentId to the Razorpay order receipt, requiring a unique account/mode-compatible captured payment, paid provider order, currency and full payable total. Item price alone is insufficient. Ambiguous references, splits, missing capture or inconsistent terms become owned cases. Matches/purchases deduplicate independently of plans and browser state. Older authorization facts cannot regress known capture/refund evidence.

New commerce evidence immediately holds relevant outreach while purchase truth is reconciled. Matched outside-link purchases are included without claiming agent attribution. Exact cart correlation marks only the associated cart paid; other open carts close because a purchase occurred. Original purchase evidence survives refunds; processed refund adjustments and remaining payable are shown separately. Delivery, physical returns, costs and causal profit/lift remain independent facts. Current Shopify return access is still unavailable.

## Offers and authority

Offers default off. Demo can load an existing, explicitly synthetic approved reference (DEMO-REORDER-25), then review an immutable economics policy. The validator checks reference/variant eligibility, expiry, quantity, current price/stock, product and fulfillment costs, contribution floor and conservative discount/contact exposure. Missing costs do not become zero. New discounts or arbitrary codes cannot be invented through this API.

Enabling/disabling offers creates a new main policy version and requires a fresh audience draft/approval. Cost-policy changes invalidate old checkout terms. The link is still separately reviewed. Budget booking conservatively includes discount exposure; it is not proof of redemption or measured profit. Real offers remain blocked until real provider evidence, costs and policy authority are configured.

## Callbacks and polling

Shopify HMAC base64 and Razorpay HMAC hex are verified over the raw bounded body with constant-time comparison and account/store binding. Canonical body hashes prevent replay via changed event-ID headers. Signed notifications queue authoritative refetch; callback/browser fields never directly create purchase truth. Current signing secrets/account bindings and public registrations are absent, so account-backed callback delivery is unverified. No webhook or public endpoint was registered or deployed.

Configure signing fields only after separate provider/deployment review: SHOPIFY_WEBHOOK_SECRET, RAZORPAY_WEBHOOK_SECRET and RAZORPAY_WEBHOOK_ACCOUNT_ID. API credentials are not substituted for callback secrets. The current Razorpay connector binding is a fingerprint of the authenticated test key, not a claim that a merchant-ID API has been verified.

The local read-only fallback is python -m app.payment_poll --workspace <Development-workspace-UUID> --once in the configured backend environment. Without --once it refreshes every five minutes. It scans bounded visible provider history; Shopify's older-history permission remains unavailable. The UI refresh and CLI are explicit starts, not an automatically registered scheduler or real-time callback claim. Failures retain previously committed evidence/freshness.

## Actual evidence

- Full application regression suite: 50 tests passed in 395.709 seconds, stage-05-all-tests.txt.
- Final twelve commerce tests passed in 93.209 seconds, stage-05-final-tests.txt. Checkout/offer coordination plus all eleven execution cases passed again (13 tests, 150.217 seconds), stage-05-guard-tests.txt.
- Four preserved Shopify compatibility tests passed, stage-05-compatibility-tests.txt.
- Actual OpenAPI export/generated types, strict TypeScript and Vite production build passed.
- Fourteen browser checks passed: reviewed terms, separate link approval, pending payment after send, independent full-total match, refund preservation, mismatch exception, renewed offer authority/cost guards, five viewport widths (1440/1024/768/390/320) and Development separation. See stage-05-browser.json, stage-05-browser-log.txt and stage05-screens/. Rendered layouts were inspected; full accessibility certification is not claimed.
- Read-only real check verified one test payment, one exact match and one purchase at INR 127315 minor units. No open reconciliation case or provider write occurred. See stage-05-source.json. This matches existing Shopify #1001 despite the earlier browser callback failure; it remains unfulfilled with no verified delivery. Credentials and contact/card fields were not printed or persisted in evidence.

Reference semantics were checked against [Shopify cart documentation](https://shopify.dev/docs/storefronts/headless/building-with-the-storefront-api/cart/manage), [OrderTransaction](https://shopify.dev/docs/api/admin-graphql/latest/objects/OrderTransaction), [Razorpay payment reads](https://razorpay.com/docs/api/payments/fetch-all-payments/) and [webhook validation](https://razorpay.com/docs/webhooks/validate-test/).

## Run, review and next stage

Start ./backend/run-foundation.ps1. Schema is 0005_commerce; preserve the existing database, owner account and ignored backend/.env. Use the Stage 01 database restart runbook if needed. Re-export backend/scripts/export_openapi.py before pnpm run types/check/build in frontend/app after API changes.

Run backend/scripts/check-foundation.ps1 for all guarded disposable-database tests, or python -m unittest tests.test_commerce -v for this stage. The browser check is frontend/app/tests/commerce-check.mjs with private isolated QA prepared by backend/scripts/prepare_stage05_qa.py. Account-backed source verification is backend/scripts/stage05_source_check.py. QA does not reset owner data or write provider records.

Stage 04 was accepted by the owner's “next stage”. Stage 05 awaits review. Stage 06 adds WhatsApp transport/inbound/status protection, retaining the already verified correct Twilio join receipt. Production checkout, live charges, real offers, callback deployment, expanded scopes and customer outreach are not authorized by this stage's review readiness.
