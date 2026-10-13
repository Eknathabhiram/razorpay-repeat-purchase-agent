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
# Razorpay Repeat Purchase Agent

## Stage 01 implemented

The persistent FastAPI/PostgreSQL foundation is ready for review at http://127.0.0.1:8766/foundation. Run ./backend/run-foundation.ps1 to restart it. [Owner review/runbook](docs/implementation-evidence/STAGE-01-RUNBOOK.md), [actual evidence](docs/implementation-evidence/STAGE-01.md) and [stage status](docs/implementation-evidence/STATUS.md) describe the implemented scope and next gate. The complete agent engine remains later-stage work.

## Application architecture and developer handover

The complete architecture package was prepared on 13 October 2026 for GPT-6.1-sol with low reasoning effort. Start at [Developer handoff](docs/IMPLEMENTATION-HANDOFF.md); it includes the copyable Stage 01 prompt and nine build stages. Read [Architecture](docs/APPLICATION-ARCHITECTURE.md), [Data/API contracts](docs/APPLICATION-CONTRACTS.md) and [Runtime/validation](docs/RUNTIME-AND-VALIDATION.md) for the full design. These are target designs, not implemented services.

Current provider evidence: Shopify catalogue/customer/order reads work; one Razorpay test payment was manually reconciled to a paid, unfulfilled Shopify order; WhatsApp trial linking remains unresolved. The latest entries in [Integration status](docs/integration-status.md) supersede older pending-access statements. Customer journeys elsewhere remain simulated.

This project proposes a Repeat Purchase Agent for Razorpay Agent Studio: identify → decide → act → learn, for the same previously purchased product. It contains an interactive design, a local read-only Shopify connector and product requirements. It is not a production-ready application.

The owner authorised connecting the frontend to Shopify on 13 October 2026. Run the local FastAPI server using `backend/README.md`, then open http://127.0.0.1:8765/#connections. Actual Shopify development-store products/prices/stock appear there; customer/order reads are pending protected-data setup. Other agent journeys remain simulated. Exact IDs and evidence are recorded in `docs/integration-status.md`.

## Start here

1. Read `HANDOFF.md` and `AGENTS.md`.
2. Review `docs/PRD.md`: the detailed 18-feature PRD was approved on 12 October 2026. `docs/user-feature-scope.txt` preserves the latest user-provided scope.
3. Open `frontend/index.html` in a browser to inspect the current design. It is a standalone export of the conversation preview. Fonts and icons may require internet access.
4. Edit `frontend/src/design-preview.fragment.html` as the source reference. `frontend/index.html` is a generated export with a preview wrapper; there is no automatic export build script yet.
5. Read `docs/product-specification.md` for supporting requirements and `docs/ux-next-pass.md` for the next design task. `backend/README.md` explains the proposed server responsibilities.
6. For the design implementation, read `docs/UIUX-HANDOFF.md` and open `frontend/design-handoff.html`. The current reference uses merchant-facing navigation, contextual action drawers and clearly separated test data. `docs/design-evidence.md` explains the Razorpay grounding; `docs/design-qa.md` records actual checks and remaining gates. The original full preview is preserved separately.
7. The current merchant-facing revision is documented in `docs/MERCHANT-UI-V2.md`. It supersedes the v1 five-screen composition. Edit the merchant template/CSS/JS and run `node frontend/build-preview.mjs` to refresh `frontend/design-handoff.html`. Revised screenshots are in `docs/merchant-ui-screens/`. The local adapter contains synthetic data only; live integrations are still pending.

## Continue in Codex

For local development, extract this folder, open it as the working folder in the Codex desktop experience or your editor's Codex extension, and start a task. With Codex CLI, launch it from this directory.

For Codex Cloud, put this folder in your own private GitHub repository and connect that repository when configuring the cloud environment. The included challenge brief is marked confidential; do not publish it with a public demo.

Suggested first task:

> Read AGENTS.md, HANDOFF.md, docs/product-specification.md and docs/ux-next-pass.md. Audit the current preview against the merchant's tasks. Improve visual hierarchy, navigation, spacing, accessibility and action placement while preserving the observed Razorpay shell and installation flow. Show the revised key screens and explain significant tradeoffs before implementing integrations. Do not claim any integration or commercial lift is validated.

## Contents

- `frontend/index.html`: standalone current preview.
- `frontend/src/design-preview.fragment.html`: editable inline design source.
- `frontend/README.md`: frontend status and editing guidance.
- `backend/README.md`: local Shopify connector setup, checks and remaining backend boundaries.
- `HANDOFF.md`: decisions, status, constraints and unresolved implementation choices.
- `AGENTS.md`: guidance for the coding agent.
- `docs/product-specification.md` and `.docx`: detailed specification.
- `docs/PRD.md`: approved requirements covering all 18 current features.
- `docs/user-feature-scope.txt`: latest feature list supplied by the user.
- `docs/ux-next-pass.md`: concrete UX work to do next.
- `docs/references.md`: primary product and interface references.
- `docs/challenge-brief.pdf`: confidential supplied assignment brief, retained locally and excluded from Git uploads.

## What has been checked

The design source's HTML structure, labels and element references were checked. Its local interaction state was exercised for both bounded and review-first paths: sample login, connector review, activation, audience approval, pause and matched sample purchase. Synthetic contribution calculations were checked. These checks do not establish visual quality, WCAG conformance, integration correctness, AI accuracy or business lift.

Shopify app creation/installation and authenticated catalogue reads are verified; the local connector uses credentials stored only in an ignored server file. No database, webhook receiver, live payments or outreach are implemented. Repository/upload and integration status are recorded in `HANDOFF.md` and `docs/integration-status.md`. PRD approval does not imply live execution permission.
