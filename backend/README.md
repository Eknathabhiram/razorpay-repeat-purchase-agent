## End-to-end delivery — 13 October 2026

The owner instructed completion through outcomes/release validation and made voice last priority. The text-first local hybrid application is ready for review at http://127.0.0.1:8766/app/#/dashboard. Read docs/RELEASE-HANDOVER.md and docs/implementation-evidence/STAGE-07.md, STAGE-08.md, STAGE-09.md. Schema is 0008_outcomes. Together AI is configured privately and verified with synthetic inputs. Planning, exact approval, protected replies, checkout, independent payment matching, refunds, cohorts, scoped learning and owner-reviewed policy changes form the persisted end-to-end pipeline. Optional browser voice was checked last. Real Storefront/Twilio/public deployment and production retention/coordination gates remain blocked; no customer outreach, new real payment, refund or deployment occurred. Preserve credentials/data and prior code. Earlier stage notes below are historical.
## Stage 06 implemented — 13 October 2026

Stage 05 was accepted for continuation by the owner's request for the next stage. Stage 06 is ready for review at http://127.0.0.1:8766/app/#/whatsapp. Read docs/implementation-evidence/STAGE-06.md and docs/implementation-evidence/STATUS.md. Schema is 0006_whatsapp. Official SDK signature checks, exact recipient review, inbound protection, contextual Demo conversations and monotonic delivery receipts are implemented. Twenty-four backend checks and eleven browser checks passed. Twilio credentials/test-send controls and actual callback delivery remain unavailable/unverified; no real message was sent. Preserve the correct historical join receipt and do not ask for another join. Stage 07 follows owner review and continuation. Earlier notes below are historical.
## Stage 05 implemented — 13 October 2026

Stage 04 was accepted for continuation by the owner's request for the next stage. Stage 05 is ready for review at http://127.0.0.1:8766/app/#/commerce. Read docs/implementation-evidence/STAGE-05.md and docs/implementation-evidence/STATUS.md. Schema is 0005_commerce. Demo checkout terms, separate link approval, independent payment evidence, reconciliation/refunds and approved offer controls are implemented. Read-only Development verification matched one Razorpay test payment to the full Shopify payable of INR 1,273.15. Fifty application tests, four compatibility tests and fourteen browser checks passed; four final source guards also passed. Real Storefront cart creation and callback delivery remain unconfigured. Preserve credentials/data and existing changes. Stage 06 follows owner review and continuation. Earlier stage notes below are historical.
## Stage 04 implemented — 13 October 2026

The owner accepted Stage 03 and instructed implementation of Stage 04. Stage 04 is ready for review at http://127.0.0.1:8766/app/#/execution. Read docs/implementation-evidence/STAGE-04.md and STATUS.md from the repository root. Exact approvals, durable Demo dispatch, leased/fenced jobs, shared contact/budget guards, receipts, supervision, reminders/support and protective events are implemented. Current schema is 0004_execution. All external side effects remain simulated; Development execution stays blocked. Preserve credentials/data and earlier references. Stage 05 follows owner review and continuation. Earlier stage-status notes below are historical.
## Stage 03 implemented — 13 October 2026

Stage 02 was accepted for continuation by the owner's explicit continue. Stage 03 is ready for review at http://127.0.0.1:8766/app/#/planning. Read docs/implementation-evidence/STAGE-03.md and STATUS.md from the project root. Normalized commerce facts, immutable planning policies, deterministic eligibility and immutable audience drafts are implemented. Shopify sync preserves permitted facts and explicitly blocks eligibility where returns/history/consent are unverified. The paid, unfulfilled order is not delivered history. Existing journey screens remain Stage 02 simulation. Stage 04 follows owner review; do not treat draft creation as outreach approval. Older stage-status notes below are historical.
## Stage 02 implemented — 13 October 2026

Stage 01 was accepted for continuation when the owner requested Stage 02. Stage 02 is ready for review at http://127.0.0.1:8766/app/. Read docs/implementation-evidence/STAGE-02.md and STATUS.md (paths relative to the project root). The React/TypeScript application uses real owner sessions, workspace isolation and scoped Shopify reads. Agent journeys use explicitly labelled server-persisted simulation state; production policy, execution, messaging, AI and payment engines remain later-stage work. Preserve existing credentials, source references and provider data. Stage 03 follows owner review and instruction to continue. Older implementation statements below are historical.
# Local Shopify connector

## Stage 01 application foundation

The persistent FastAPI/PostgreSQL foundation is implemented separately from the preserved connector below. Start it with ./backend/run-foundation.ps1 and review http://127.0.0.1:8766/foundation. See ../docs/implementation-evidence/STAGE-01-RUNBOOK.md for owner login, migrations, tests and restart commands. Provider secrets remain in the existing ignored file.

The new server adds sessions, roles, independent workspaces, capability records, idempotent updates and audit evidence. Agent policies, approval/execution jobs, AI/speech and payment reconciliation remain later-stage work. The older port 8765 server retains its original local read-only boundary.

The original FastAPI server connects the v2 merchant frontend to our Shopify development store through authenticated, read-only GraphQL requests. This is a local connector. PostgreSQL and application owner sessions now exist in the separate Stage 01 server; persistent agent policies/approvals, checkout, scheduling, messaging and automated payment reconciliation remain unimplemented.

## Run locally

Use Python 3.12 or later. From the project root:

```powershell
python -m pip install --target backend/.local/python -r backend/requirements.txt
```

Create backend/.env from backend/.env.example only if it does not already exist. Enter the installed app client ID and secret in that local file, never in chat or source control. This session already configured the ignored file.

```powershell
./backend/run-local.ps1
```

If Python is not on PATH, pass its executable:

```powershell
./backend/run-local.ps1 -Python 'C:\path\to\python.exe'
```

Open http://127.0.0.1:8765/#connections. The server serves frontend/design-handoff.html and /api/shopify/snapshot from the same origin. Rebuild frontend changes with `node frontend/build-preview.mjs`.

## Behavior and limits

- Secrets load server-side from the ignored .env. Access tokens stay in memory and renew before expiry; neither credentials nor tokens are returned to the browser.
- Own-organization client credentials authentication requires the app and store to belong to the same organization, with the app installed. Other merchants require an appropriate OAuth flow later.
- Reads up to 50 products (20 variants each), 50 customers, 20 orders, 20 drafts and 10 locations. Pagination flags make snapshot limits visible. The UI initially shows TEST- project SKUs; all returned products can be shown.
- Customer/order queries are separate from catalogue queries. Protected-data denial produces partial access, not a fabricated empty list or loss of verified products.
- Customer/order reads initially failed protected-data checks. After the owner-approved development access declaration, the recorded snapshot returned four customer IDs/order counts, one order and ten drafts without warnings. Identity/contact/address fields remain unrequested; ID access is not marketing consent.
- Shopify financial/fulfilment states are source records, not proof of Razorpay reconciliation or delivery. Existing agent journeys and controls remain simulated.
- This is a single-owner loopback-only development server, with trusted-host and cross-origin checks. Only the frontend directory is exposed. It has no production authentication or tenant isolation and must not be exposed publicly.

## Checks

From backend, with the local dependency directory on PYTHONPATH:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) '.local/python'
python -m unittest test_shopify_app -v
```

Four tests cover token caching, partial access, authentication failure, host validation, cross-origin denial and private-file exclusion. Real API reads and visual frontend checks are separate. Exact IDs and results are recorded in ../docs/integration-status.md.

## Target application architecture

Read ../docs/IMPLEMENTATION-HANDOFF.md for the staged developer brief, supported by APPLICATION-ARCHITECTURE.md, APPLICATION-CONTRACTS.md and RUNTIME-AND-VALIDATION.md. The planned PostgreSQL-backed engine is not implemented by the current connector. One Razorpay test reconciliation was verified independently; this service does not yet automate payment matching.
