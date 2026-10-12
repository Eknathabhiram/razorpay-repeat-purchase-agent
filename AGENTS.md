# Working instructions

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
