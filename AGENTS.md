## Consolidated application - 13 October 2026

The owner requested gathering all frontend/backend work, merging latest branches, removing obsolete code and pushing to GitHub. Current code is frontend/app plus backend/app at schema 0008_outcomes. Read docs/CONSOLIDATION-2026-10-13.md and docs/RELEASE-HANDOVER.md. The superseded frontend/index.html, frontend/src/design-preview.fragment.html, frontend/design-tokens.css and unused Overview.tsx were removed; history remains in Git. Earlier references to preserving those files or absent backend implementation are historical. Preserve private configuration/data and the still-used v2 compatibility connector.

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
# Working instructions

## Current implementation — Stage 01

Stage 01 is implemented and ready for owner review. Read docs/implementation-evidence/STATUS.md and STAGE-01-RUNBOOK.md before continuing. The new FastAPI/PostgreSQL foundation runs on loopback port 8766; the existing 8765 Shopify connector and merchant preview remain preserved. Thirteen PostgreSQL tests and four original Shopify tests passed. Do not restart Stage 01 or overwrite existing credentials/data. Stage 02 follows owner review/continuation; current preview journey actions remain simulated.

## Latest architecture handoff — 13 October 2026

The owner requested a complete application architecture and implementation handover for GPT-6.1-sol with low reasoning effort. Start at docs/IMPLEMENTATION-HANDOFF.md; technical design is in docs/APPLICATION-ARCHITECTURE.md, docs/APPLICATION-CONTRACTS.md and docs/RUNTIME-AND-VALIDATION.md. These files define target architecture, not completed implementation. Python + FastAPI + PostgreSQL is owner-selected; other technical defaults are architecture recommendations. Preserve the existing working Shopify connector and merchant UI v2. Follow the owner's stage testing/review preference when implementation is requested.

Use the final dated entries in docs/integration-status.md for current provider evidence. Shopify customer/order reads now work and one Razorpay test payment was reconciled manually to a Shopify order. WhatsApp trial linking remains unresolved despite a verified correct join command. The small Shopify backend exists; the full application backend remains unimplemented. Older statements below about absent accounts/backend or design-only next work are historical and must not override this evidence or the latest owner request.

## Original project guidance

Read `HANDOFF.md` before choosing scope or implementation. Read `docs/product-specification.md` for behaviour, contracts and acceptance requirements. The current preview is a design reference, not a production architecture.

The latest user-provided 18-feature scope is preserved in `docs/user-feature-scope.txt`. `docs/PRD.md` was approved on 12 October 2026. The UI/UX implementation handoff is `docs/UIUX-HANDOFF.md`, supported by `frontend/design-handoff.html`, `frontend/design-tokens.css`, `docs/design-evidence.md` and `docs/design-qa.md`. Read these before design implementation; the five-screen handoff reference does not replace the full application journey. The original preview lives at `frontend/index.html` and its editable source at `frontend/src/design-preview.fragment.html`. `backend/` currently documents the proposed server boundary, not an implemented service. Preserve both folders. The confidential original assignment PDF is excluded from Git uploads.

## Next priority

The owner requires merchant-facing UI and copy with a production-quality presentation. Read `docs/MERCHANT-UI-V2.md` before design implementation. Use `frontend/merchant-preview.template.html`, `frontend/merchant-app.css` and `frontend/merchant-app.js`; rebuild the standalone `frontend/design-handoff.html` with `node frontend/build-preview.mjs`. V2 supersedes the v1 visual composition and copy. Keep all service modes honest; presentation quality does not establish integrated production readiness.

Improve UI/UX before adding integrations. Keep the observed Razorpay dashboard shell and installation pattern. Organise our agent around merchant decisions, not a catalogue of AI features. Use `docs/ux-next-pass.md` as the design brief.

## Product constraints

- Deliver the full agreed journey. Do not silently reduce it to an MVP or add cross-sell to current execution.
- Keep same-product scope, coordinated WhatsApp/voice, approved plans, review-first, takeover and pause.
- Preserve verified-source checks, customer consent, opt-out suppression, duplicate prevention and payment/order reconciliation.
- Never use a language model as the source of current price, stock, offer eligibility or payment truth.
- Distinguish sample, test and live sources. Never label disconnected accounts as connected.
- Keep observed outcomes separate from causal incremental lift. Sample metrics stay labelled; missing costs prevent contribution claims.

## Implementation boundaries

No real credentials, developer accounts, backend, database or provider integration are currently available in this package. Do not infer access to Razorpay's private Agent Studio APIs. Research current official provider documentation before integrating. Do not deploy, send customer outreach, charge money or publish this confidential brief merely because the preview has buttons for those concepts.

When accounts are available, keep credentials server-side in environment variables and out of source control. Browser login in the current preview is a simulation; it must not collect real Razorpay credentials.

## Design and validation

Use a consistent component system and spacing/type scale. Check desktop, narrow screens, keyboard/focus, overlay behaviour and empty/error/paused/disconnected states. Use WCAG 2.2 AA as a target and verify before claiming compliance. Inspect rendered screens; DOM interaction checks alone do not prove visual quality.

Show revised key screens and explain substantial design or architecture tradeoffs. Obtain the user's choice for consequential unresolved decisions; do not ask again for routine work already authorised. Report which integrations and tests actually work, and which remain simulated.
