# Stage 09 — integrated local delivery and release evidence

13 October 2026 · ready_for_review · production gates remain explicit

The owner instructed completion end to end with voice last. Stages 07–09 were completed in one integrated delivery. Start at [Dashboard](http://127.0.0.1:8766/app/#/dashboard); deployment/rollback/configuration and exact provider limits are in [RELEASE-HANDOVER.md](../RELEASE-HANDOVER.md). No public deployment, push, live charge, new real checkout or customer outreach occurred.

## Actual checks

- Full application regression: 70 cases ran in 995.044 seconds. 69 passed; one setup database connection timeout occurred in first-plan approval. Original evidence is preserved in stage-09-all-tests.txt.
- The timeout case passed on retry. All final AI/provider, exact checkout-consent, outcomes/learning/accounting and four preserved Shopify checks passed together: 18 tests, 140.406 seconds, stage-09-final-tests.txt. This resolves the failing case; the original whole-run log is not rewritten as green.
- Four focused schema/intent-validation checks passed, stage-07-final-provider-tests.txt. Six frontend API/session/network-error checks passed, stage-09-api-client-tests.txt.
- Fifteen end-to-end browser checks passed with no JavaScript errors. The uninterrupted path covered verified facts, exact audience approval, real Together interpretation of synthetic customer text, independent product/quantity/channel confirmation, checkout terms of INR 1,038.00, separate exact-link approval, durable simulated submission, independent capture/match, refunds, compound intentions, confirmed date learning and owner-reviewed policy renewal.
- Automated WCAG-tagged axe scans returned zero violations on Dashboard, AI & Replies, Outcomes and Connections in that run. Final layout polish receives a separate visual report; no full accessibility certification is claimed.
- Voice was checked after the text-to-outcomes journey: five browser checks passed for recoverable microphone denial, real synthetic-audio transcription with explicit review, compound interpretation, Together reply audio and stop. No physical microphone recording or telephone call was performed.
- Actual OpenAPI/type generation and strict TypeScript/Vite build passed: 100 modules, lazy feature chunks.
- Private PostgreSQL backup restored successfully to a newly created disposable probe database at schema 0008_outcomes; five persisted-table counts matched. Probe was removed, development database unchanged. stage-09-backup.json.
- Additive upgrade/downgrade-to-base/upgrade rehearsals ran on the guarded rpa_stage1_test DB through the application suites. Prior execution tests exercise barriers, fencing, reservations, restart/recovery and unknown outcomes without blind resend.

## Acceptance coverage and practical limits

| Requirements | Actual coverage | Remaining live proof |
| --- | --- | --- |
| T01/T22 scope, auth, webhook security | PostgreSQL workspace/FK isolation, sessions/CSRF/roles, signed account-bound callbacks and replay tests | Public ingress/TLS/provider delivery and production identity review |
| T02/T20 entry/setup/full UI | Preserved Stage 02 entry/installation references; persisted operational surfaces and end-to-end customer flow | Native private Agent Studio installation is not available |
| T03/T04 eligibility/estimation | Source provenance, exact variant, consent/stock/delivery/returns exclusions and fallback tests | Actual older history/returns/consent coverage remains incomplete |
| T05/T06/T07 authority/checkout/offers | Immutable approvals/terms, market rechecks, exact quantity/channel confirmation, configured offers and cost guards | Real Storefront/buyer context, approved real templates/offers |
| T08/T10 compound/protection | Real Together evidence plus deterministic preservation; explicit dates; outage-safe opt-out/support/refusal | Broader adjudicated language/transcript coverage |
| T09/T11/T16/T25 coordination | Internal customer-wide caps, budgets, ownership/pause, stale-fact fencing and unsent cancellation | External campaign coordinator is unverified; dependent real execution stays blocked |
| T12/T13/T14/T15 events/payment/unknown | Deduplication, delivery ordering, independent full-total matching, outside-link cases and no uncertain resend | Live callbacks/unknown external send resolution not account-backed |
| T17/T18 learning/accounting | Explicit scoped learning, owner policy decisions, cohort renewal, refunds, nullable costs/returns and separate lift labels | Real costs/return maturity, randomized comparison, measured handling duration |
| T19/T26 persistence/recovery | Multiple process restarts, persisted DB, migration rehearsal, restored backup counts and worker recovery tests | Production retention/export/deletion procedures remain a release gate |
| T21 interface | 320–1440px layouts, dialog behavior, keyboard checks and four-screen automated accessibility scans | Full assistive-technology/production accessibility certification |
| T24 voice | Tested last: denial, transcript confirmation, compound processing, stop, duplicate turn and channel handoff | Physical-device microphone, actual customer voice consent; no telephone automation |

F01–F18 remain represented across the preserved entry/reference and persisted domain surfaces. Missing live capabilities are not silently supplied by Demo data. The local hybrid demonstration is reviewable; production readiness is not claimed.

## Reviewable source

backend/app/together_provider.py, intelligence.py and outcomes.py own bounded provider contracts and deterministic authority. Migrations 0007_intelligence and 0008_outcomes are frozen additive DDL. frontend/app/src/features/Intelligence.tsx is text-first with optional voice collapsed; Overview.tsx and Outcomes.tsx read persisted evidence. Connections exposes server-side Together configuration/verification without returning credentials.

Source/evidence credential scanning and git diff --check are part of final handover checks. The supplied Together key stays in ignored backend/.env. Audio verification fixtures, owner/QA access and backup dumps remain ignored in backend/.local.

Final delivery checks: seven final same-variant reminder/coordination and provider-contract tests passed in 47.035 seconds (stage-09-learning-scope-tests.txt). Twenty-two final visual checks passed, including five widths on each of four screens, accounting-dialog Escape/return focus and observed 200% CSS zoom. Final axe scans returned zero violations on the same four screens. Updated Outcomes at 1024px and AI & Replies layouts were visually inspected. The final credential scan checked 207 source/evidence files, including the Together key, with no leaks; private key/audio/backup exclusions were verified. See stage-09-final-visual.json and stage-09-credential-scan.json.
