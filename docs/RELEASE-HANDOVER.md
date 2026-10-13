# End-to-end application handover

13 October 2026 · local hybrid application ready for review · production release blocked

Open [Dashboard](http://127.0.0.1:8766/app/#/dashboard). Use the existing owner credentials. Current schema is 0008_outcomes. The owner requested completion through outcomes/release validation and moved browser voice to last priority.

## Review the complete journey

1. Select Demo and open Planning. Load synthetic facts, review product/contact policy, create the exact audience draft.
2. Open Execution and approve the audience. Review-first messages require exact approval; bounded authority remains subject to the same guards.
3. Inspect WhatsApp synthetic inbound/status handling, or open AI & Replies to start a consented synthetic conversation using Together.
4. Interpret a compound reply or same-product request. Confirm an absolute date/channel for reminders. Confirm exact product, quantity and independent WhatsApp handoff before reviewing checkout terms.
5. Prepare the Demo checkout, propose its link in Commerce, then approve that exact message in Execution. Submission does not create a purchase.
6. Inject independently labelled commerce/gateway evidence in Commerce. Inspect capture, amount mismatch, outside-link matching or refunds.
7. Open Outcomes. Inspect full payable/refunds, unknown costs, original cohort and confirmed learning. Review a suggested policy change; accepting requires a fresh audience approval.
8. Optional browser voice is last: allow processing, record a short turn, review/correct its transcript, interpret and play the server-rendered reply. Stop ends capture/playback/session.

The automated end-to-end proof used a fresh isolated QA tenant and the real Together API with synthetic inputs. It did not reset the owner account or contact real customers.

## Actual capability matrix

| Capability | Current proof | Release boundary |
| --- | --- | --- |
| PostgreSQL auth/workspace/CSRF/roles | Real local DB and scoped tests | Loopback only; deploy requires TLS/secure cookies and production secret management |
| Shopify catalogue/customer/order reads | Real authenticated development reads | Returns/older-history access remains incomplete; eligibility fails closed |
| Shopify checkout | Full Demo receipts and adapter contract | No Storefront token/buyer context; real cart creation blocked |
| Razorpay reconciliation | One real test payment matched full INR 1,273.15 payable | Test-only reads; no live key/charge/refund request |
| WhatsApp ingress/status | Official SDK signature/account/replay tests, complete Demo flow | No configured credentials/public callbacks/template authority; real sends blocked |
| Together interpretation | Real structured requests, usage/latency, integrated browser proof | Synthetic consented operator test; raw model imperfect, deterministic guards required |
| Together transcription/speech | Real synthetic-audio smoke checks and optional browser controls | Physical microphone/production customer consent and retention are separate release checks |
| Outcomes/learning | Real DB, immutable reviews and end-to-end Demo | Contribution/returns/costs in Development unknown; lift/time saved unmeasured |
| Campaign coordination | Durable internal contact caps, budgets, holds and fencing | No verified external campaign coordinator; production dependent sends blocked |
| Agent Studio/hosting | Preserved Razorpay-style local reference | No native private Agent Studio API integration or public deployment claimed |

## Run and configuration

From the repository, run backend/run-foundation.ps1. For setup, backend/scripts/setup-foundation.ps1 -InstallDependencies installs the pinned private runtime and applies migrations. frontend/app uses pnpm run types/check/build; actual OpenAPI is exported with backend/scripts/export_openapi.py. Preserve backend/.env, backend/.env.foundation, backend/.local and existing owner access.

| Server-side configuration | Purpose |
| --- | --- |
| APP_DATABASE_URL / MIGRATION_DATABASE_URL | Separate app/migration roles |
| APP_ALLOWED_HOSTS / APP_ALLOWED_ORIGINS / APP_COOKIE_SECURE | Loopback defaults; explicit TLS configuration for deployment |
| SHOPIFY_SHOP / CLIENT_ID / CLIENT_SECRET / API_VERSION | Current read-only development connector |
| RAZORPAY_KEY_ID / KEY_SECRET | Existing test-only payment reads |
| TOGETHER_API_KEY / CHAT_MODEL / STT_MODEL / TTS_MODEL / TTS_VOICE | Together interpretation/audio; never exposed client-side |
| TWILIO_ACCOUNT_SID / AUTH_TOKEN / WHATSAPP_FROM / CALLBACK_BASE_URL | Missing: account-bound messaging and SDK callback validation |
| SHOPIFY_WEBHOOK_SECRET / RAZORPAY_WEBHOOK_SECRET / RAZORPAY_WEBHOOK_ACCOUNT_ID | Missing: signed commerce callbacks |
| Shopify Storefront token and buyer-context review | Missing: account-backed checkout mutation capability |

The developer database listener is loopback:55432; the app is loopback:8766 and the preserved connector is :8765. Do not broaden hosts/permissions, activate live payment mode, register callbacks or expose this confidential workspace without the release gate.

## Backup, rollback and recovery

backend/scripts/rehearse_backup.py writes a private custom PostgreSQL dump, restores only to a newly named rpa_restore_probe_* database, checks schema/counts and removes that probe. The real rehearsal passed at 0008_outcomes without modifying development data. The private dump remains in ignored backend/.local/release-rehearsal.dump.

Before a reviewed deployment, stop new dispatch, preserve in-flight/unknown attempts, take a verified backup and pin an app/schema version. Forward fixes are preferred after new ledger records exist. Downgrade scripts were rehearsed against the guarded disposable test DB; they are not authorization to erase development/production tables. Restore into a new database and validate it before changing the app connection.

Worker recovery does not replay an unknown external submission. Pause/opt-out/support/purchase holds remain effective. Resolve an authoritative provider receipt or an owned unknown outcome first. Optional payment polling is explicit read-only app.payment_poll; no automatic public scheduler is registered.

Retention/export/deletion procedures and actual provider-side retention must be reviewed before handling live customer data. App roles cannot delete immutable accounting/identity/approval evidence. No unreviewed customer-data purge or production deletion endpoint is shipped.

## Delivery limits

The full local hybrid flow is implemented. Production blockers are real checkout access, Twilio test/template/sender and public callback proof, complete commerce history/returns/consent, real accounting costs/return maturity, external campaign coordination, production identity/deletion/retention controls, TLS/hosting and final authorized live tests. Those capabilities cannot be replaced by a Demo receipt.

No commit, push, public deployment, scope expansion, real customer message, new payment or refund was performed in this delivery. Keep the confidential assignment and all credentials excluded from any code package. See docs/implementation-evidence/STAGE-09.md for actual acceptance evidence.
