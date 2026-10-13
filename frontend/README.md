## Stage 04 implemented — 13 October 2026

The owner accepted Stage 03 and instructed implementation of Stage 04. Stage 04 is ready for review at http://127.0.0.1:8766/app/#/execution. Read docs/implementation-evidence/STAGE-04.md and STATUS.md from the repository root. Exact approvals, durable Demo dispatch, leased/fenced jobs, shared contact/budget guards, receipts, supervision, reminders/support and protective events are implemented. Current schema is 0004_execution. All external side effects remain simulated; Development execution stays blocked. Preserve credentials/data and earlier references. Stage 05 follows owner review and continuation. Earlier stage-status notes below are historical.
## Stage 03 implemented — 13 October 2026

Stage 02 was accepted for continuation by the owner's explicit continue. Stage 03 is ready for review at http://127.0.0.1:8766/app/#/planning. Read docs/implementation-evidence/STAGE-03.md and STATUS.md from the project root. Normalized commerce facts, immutable planning policies, deterministic eligibility and immutable audience drafts are implemented. Shopify sync preserves permitted facts and explicitly blocks eligibility where returns/history/consent are unverified. The paid, unfulfilled order is not delivered history. Existing journey screens remain Stage 02 simulation. Stage 04 follows owner review; do not treat draft creation as outreach approval. Older stage-status notes below are historical.
## Stage 02 implemented — 13 October 2026

Stage 01 was accepted for continuation when the owner requested Stage 02. Stage 02 is ready for review at http://127.0.0.1:8766/app/. Read docs/implementation-evidence/STAGE-02.md and STATUS.md (paths relative to the project root). The React/TypeScript application uses real owner sessions, workspace isolation and scoped Shopify reads. Agent journeys use explicitly labelled server-persisted simulation state; production policy, execution, messaging, AI and payment engines remain later-stage work. Preserve existing credentials, source references and provider data. Stage 03 follows owner review and instruction to continue. Older implementation statements below are historical.
# Frontend

- `index.html`: standalone generated export of the current interactive design.
- `src/design-preview.fragment.html`: editable design source.

Open `index.html` in a browser for the existing simulation. External fonts/icons may need internet. It currently has no backend connection or real authentication. Never enter real Razorpay credentials into its sample login.

After source edits, regenerate the standalone export; the fragment and export are not automatically synchronised. There is currently no build script or dependency manifest.

The future application will render merchant setup, opportunities, plan/action review, activity, supervision, analytics and settings using backend-authorised state. Framework selection remains pending; this reorganisation does not convert the preview into a production application.
