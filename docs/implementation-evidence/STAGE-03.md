# Stage 03 — commerce facts, policy and planning

13 October 2026 · ready_for_review

Open [Planning](http://127.0.0.1:8766/app/#/planning) and use the existing owner account. Select Demo, load synthetic history, review/save a planning policy, inspect eligible/excluded customer evidence and save an audience draft. Removing the fallback shows how sparse history becomes excluded; changing policy makes the previous draft require review. Select Development to sync permitted Shopify facts and inspect explicit missing evidence.

## Implemented

Migration 0003_planning adds scoped variants, customers, orders, exact order lines, customer evidence, sync checkpoints, immutable policies, opportunity snapshots, draft revisions and members. Composite scope foreign keys prevent cross-workspace references. The application role cannot update/delete policies, opportunities, evidence or draft records. Migration DDL is frozen independently of future metadata edits.

The read-only adapter scans catalogue/customers/orders with cursors, plus variant, order-line, fulfillment-line, refund-line and return pagination. Invalid/repeated cursors and bounded scan limits fail without advancing committed checkpoints. Sync commits normalized facts and its coverage generation atomically; failures preserve previous evidence. This stage uses bounded full scans and a commerce checkpoint, not an incremental background scheduler or cross-request cursor resume.

Delivery requires source delivery timestamps and sufficient quantities for the exact line; payment/fulfillment status alone does not establish delivery. Return/refund evidence and unknown coverage remain distinct. Customer identities stay provider IDs in Development. Consent, suppression, support, campaign and confirmed-date evidence is seeded only in Demo; no generated store customer is contacted.

repeat_window_v1 uses positive same-variant intervals from at least three comparable delivered purchases, median and median absolute deviation. Mixed quantities are not scaled; configured product fallback applies when history is insufficient. Customer-confirmed date takes precedence. Missing basis, consent, coverage, stock, delivery or protection evidence produces named exclusions. New relevant purchases and returns suppress eligibility. Draft creation re-evaluates current facts so stale opportunity IDs cannot bypass changed stock or consent.

Planning policies have reviewed differences, impact counts, exact variant scope, minor-unit INR budgets and immutable revisions. Draft edits create new immutable revisions with exact selected/excluded membership, digest, policy/evidence generation and 24-hour expiry. Saving does not approve outreach or create jobs. The Planning tab exposes source coverage, policy review, exclusions, date/quantity evidence and exact draft counts. Stage 02 Dashboard/Activity/Settings remain their labelled journey simulation; they do not become production execution authority through this stage.

## Actual checks

- Full application suite: 26 tests passed in 152.599 seconds, including foundation and UI compatibility. See stage-03-tests.txt.
- After the source-access adjustment, all nine Stage 03 tests passed in 44.480 seconds. This includes an additional denied-return test: 27 distinct application cases are covered across the saved runs. See stage-03-planning-tests.txt. Estimator/pagination cases were also rerun after final error wrapping.
- Four original Shopify compatibility tests passed.
- Strict TypeScript check, generated API types and production Vite build passed.
- Nine browser checks passed: synthetic eligibility (3 eligible/6 excluded), editable exact draft, provenance drawer, policy impact/stale draft/reload, and layouts at 1440/1024/768/390/320 pixels. See stage-03-browser.json, stage-03-browser-log.txt and stage03-screens/. Screens were rendered and inspected. This does not establish full accessibility certification.
- Real authenticated Shopify sync persisted 29 variants, four customers, one order and one exact line. There are zero confirmed deliveries and one paid/unfulfilled order. Zero Development customers qualified. See stage-03-source.json. No provider writes occurred.

The existing Shopify access denies returns and does not include all historical orders. Independent catalogue/order facts are retained while coverage remains incomplete and returns remain unverified. No permissions were expanded. Consent, contact mappings, support and campaign evidence are also unverified in Development. This is a verified partial read, not verified production eligibility. Field semantics were checked against [Shopify Fulfillment documentation](https://shopify.dev/docs/api/admin-graphql/latest/objects/Fulfillment).

## Operate and continue

Start ./backend/run-foundation.ps1; restart PostgreSQL using the Stage 01 runbook if needed. Apply migrations from the configured backend environment with python -m alembic upgrade head. Preserve the existing database/credentials. Rebuild frontend/app with pnpm run types, pnpm run check and pnpm run build after exporting the actual OpenAPI schema using backend/scripts/export_openapi.py.

Tests run on the guarded disposable database using backend/scripts/check-foundation.ps1. Target Stage 03 with python -m unittest tests.test_planning -v. The headless UI check is frontend/app/tests/planning-check.mjs. The real read-only check is backend/scripts/stage03_source_check.py and uses the isolated local QA tenant. These checks do not reset owner accounts or create Shopify history.

Stage 02 was accepted for continuation by the owner's explicit “continue”. Stage 03 awaits review. Stage 04 adds exact approvals, durable execution, contact/budget guards and supervision. The current draft is deliberately separate from Stage 02 simulated approvals. Live execution, automatic gateway reconciliation, messaging, AI/voice, deployment and production RLS remain later-stage work.
