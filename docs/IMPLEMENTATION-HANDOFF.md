# Developer handoff — GPT-6.1-sol low

Version 1.0 · 13 October 2026 · Complete application implementation brief

The owner requested an application architecture designed for a smooth handover to GPT-6.1-sol with low reasoning effort. This package makes routine implementation decisions explicit and preserves the full approved scope. It does not launch another chat, select the app's model provider or start backend implementation.

## 1. Read order

1. AGENTS.md and the newest sections of HANDOFF.md.
2. This file for scope, sequence, stage gates and the ready-to-use prompt.
3. APPLICATION-ARCHITECTURE.md for architecture and ownership.
4. APPLICATION-CONTRACTS.md for tables/types/routes/authority.
5. RUNTIME-AND-VALIDATION.md for races/recovery/tests.
6. PRD.md and user-feature-scope.txt for all F01–F18; product-specification.md for AC01–AC22.
7. MERCHANT-UI-V2.md and actual merchant-app.css/template/JS for visual implementation; UIUX-HANDOFF.md/design-evidence.md for continuity and provenance.
8. The final entries of integration-status.md for provider evidence; earlier notes in that file are chronological and may be superseded.

Do not treat frontend/index.html as the latest visual composition. The latest v2 export is frontend/design-handoff.html. Keep both references until the new app demonstrates every journey.

## 2. Fixed decisions and constraints

| Item | Instruction |
| --- | --- |
| Full scope | Deliver all 18 approved features and all nine demo journeys; stages define order, not feature removal |
| Product | Same previously purchased variant; no cross-sell, new discounts or automatic charges |
| Backend | Python + FastAPI + PostgreSQL; modular application, not independent services |
| Persistence | SQLAlchemy async + psycopg + Alembic; PostgreSQL jobs/inbox/outbox and immutable approvals |
| Frontend default | React/TypeScript/Vite in frontend/app; preserve merchant UI v2 layout/copy |
| AI | Strict intent proposal and bounded context; deterministic validator owns authority |
| Voice | Browser turn-based audio first; same text engine; telephone connection separate |
| Checkout | Shopify-owned checkout + configured Razorpay test gateway; no second agent gateway order |
| Status | Actual per-capability simulated/test/live; account existence is not a working adapter |
| Security | Server credentials, session/role/tenant checks, signed callbacks, no real Razorpay login in preview |
| Review | Owner requires testing and reviewing each stage before advancement |
| External operations | Honour specific existing authorisations; do not infer new recipient contact, write scopes, live charges or deployment from UI/PRD approval |

No implementation changes were made by this architecture package. Existing uncommitted integrations belong to previous project work; inspect the diff before editing and preserve it.

## 3. Work method

Implement one stage as a cohesive vertical slice. Keep every changed path and acceptance condition linked to that stage. Reuse existing working connectors and v2 UI instead of rewriting them before their replacement is reviewable.

Within a stage, progress autonomously through ordinary code, migrations, fixtures, local checks and fixes already authorised. Do not stop to ask about names, route conventions, lock mechanics or routine dependencies specified here.

At the stage boundary, show the running/reviewable result, tests and any material limitation. Stop advancement for the owner's stage review because that is their recorded delivery preference. Do not describe that review as a skill-imposed permission requirement. An explicit instruction to continue satisfies the next stage gate; do not request it again.

If a provider capability is blocked, finish the independent code/demo path and record exactly what remains unverifiable. Do not mark the stage's real-provider checks passed. Prepare a concrete account/permission proposal before asking for a consequential choice.

Maintain docs/implementation-evidence/STATUS.md with stage state (not_started/in_progress/ready_for_review/accepted/blocked), last completed test evidence, next permitted stage and provider capability inventory. Update it after actual work; do not prefill passes or owner acceptance.

## 4. Stage plan

### Stage 01 — durable backend foundation

Deliver:

- Preserve the current loopback UI and Shopify snapshot compatibility.
- Add backend/app, settings, scoped repositories, transactional unit of work, structured errors/logs and migrations.
- Add merchant/workspace, identity/session/membership, connectors/capabilities, audit and idempotency foundations.
- Configure PostgreSQL and owner bootstrap without embedding credentials. Provide explicit Windows run/check scripts and reproducible dependency locks.
- Seed a separate demo workspace and retain a development workspace binding to the existing account. Demo data cannot overwrite development records.
- Keep the server loopback by default; public deployment is separate.

Validate: migration upgrade on a disposable database, login/logout/CSRF/roles, cross-workspace denial, idempotent command, secret/static-file exclusion, existing Shopify snapshot/test compatibility. Use real PostgreSQL for relational isolation.

Owner review: log in, inspect actual connection modes and restart the app to verify persistent workspace/session policy. No real send/payment is needed.

Database-runtime absence is a setup blocker, not permission to substitute SQLite and claim PostgreSQL tests passed. Prepare the configuration and runnable code while resolving the local runtime.

### Stage 02 — application shell and full UI continuity

Deliver:

- Scaffold frontend/app with the specified client stack and generated API types.
- Port v2 shell, semantic shared controls, Dashboard/Activity/Settings, contextual dialogs/drawers and source detail.
- Consolidate full entry/Studio discovery/agent detail/install journey from the preserved original preview.
- Separate demo entry/verification from actual application authentication.
- Bind authentication, workspace/mode and connector views to Stage 01; other features can use explicitly simulated server read models until their stages arrive.
- Preserve focus, responsive CSS and concrete merchant copy; remove authority from browser storage.

Validate: build/type check, full navigation/entry/setup continuity, keyboard/overlay focus, 1440/1024/768/390/320 px and 200% enlargement on key views. Capture screenshots; inspect actual render.

Owner review: compare current v2 against the replacement, including mobile, setup and connection source detail. Keep the old preview accessible throughout.

### Stage 03 — facts, policy, opportunities and plan drafts

Deliver:

- Refactor Shopify adapter with paginated catalogue/customer/order coverage and checkpoints.
- Persist exact variant/order-line/delivery/return facts; development identities remain IDs until authorised fields/mappings are available.
- Add explicit consent/suppression/support fixture evidence in demo only.
- Implement immutable policies, review diff, active version and impact preview.
- Implement repeat_window_v1, eligibility/exclusion reasons and fact provenance.
- Create editable immutable plan draft revisions with selected audience, scope/digest/expiry.
- Render policy settings, opportunity evidence, excluded rows and exact plan counts.

Validate: T03/T04/T05/T11 plus scope and restart; pending required facts are blocked. Review synthetic history against shopify-test-data-plan.md without writing historical store orders unless separately authorised.

Owner review: inspect eligible/excluded customers, timing basis, policy diff and draft approval scope. The real paid/unfulfilled order must not qualify as delivered history.

### Stage 04 — approval, execution engine and supervision

Deliver:

- Plan/action approvals bound to exact revision/digest, cohort assignment and durable schedules.
- Contact guards/ledger, budget reservations, inbox/outbox, leased jobs/fencing and dispatch protocols.
- Deterministic validator and demo side-effect adapters through the same path.
- Pause/resume, takeover/handback, internal support cases, immediate opt-out and confirmed reminders.
- Receipts and owned exceptions; status checks for unknowns, no blind retry.
- UI decision queue and customer action review with exact rendered outgoing content.

Validate: concurrent channel/cap/budget tests; crash before/after submitting; duplicate command/event; pause/opt-out race; restart of reminders/unknown reservations. A first plan produces zero fabricated customer replies/orders.

Owner review: review-first approval, bounded demo dispatch, pause, takeover and a prevented stale/unknown action. Everything in this stage's side effects is explicitly simulated.

### Stage 05 — commerce checkout, payment evidence and offers

Deliver:

- Shopify Storefront capability verification and typed cart preparation where authorised.
- Read-only Razorpay evidence adapter, versioned cross-system mapping and automated reconciliation cases.
- Signed payment/commerce callback handlers; local polling fallback with honest freshness until public callback setup is available.
- Checkout receipt, independent link-send approval and payment/order distinction.
- Approved-offer validation with price/expiry/eligibility/budget/margin guards; offers remain off until configured.
- Refund/return accounting facts and outside-link purchase cancellation.

Validate: T06/T07/T12/T14/T15/T23, including mode/account mismatch, total vs item price, fake browser success and duplicate/out-of-order callbacks. Use current #1001 as redacted mapping evidence, not a hardcoded algorithm. Re-run any account-backed test only within actual authorisation.

Owner review: same-product checkout preparation and matched test evidence, plus a failure/unmatched path. If Storefront access is missing, development stays explicitly blocked while the full demo checkout works.

### Stage 06 — WhatsApp transport and inbound protection

Deliver:

- Diagnose current Twilio trial linkage/error 12300; use the already verified correct join receipt.
- Add capability-specific Twilio adapter, authentic inbound/status ingress and verified recipient mapping.
- Verify authorised test transport with actual provider MessageSid/status evidence if account capability allows.
- Implement shared journey updates, channel rules, opt-out/support/refusal routing and cancellation of conflicting work.
- Keep full contextual conversation in demo when trial templates cannot carry replenishment text.

Validate: signatures/account mismatch, inbound duplicates, delivered/read ordering, no trial-TwiML assumption, template/channel restrictions and unknown timeout handling.

Owner review: one explicitly authorised test recipient's transport receipts and inbound/status processing. Mark transport verification separately from approved custom reorder messaging.

Do not ask the owner to resend the correct join command. Do not contact generated Shopify customers. Do not silently upgrade a paid plan/sender or request new data scopes.

### Stage 07 — AI interpretation and browser voice

Deliver:

- Present a concrete provider choice based on available authorised account, structured-output capability, speech support, cost and measured latency; preserve provider-neutral contracts.
- Add bounded intent interpretation, schema validation, prompt/version records and evidence binding.
- Implement compound intents, clarifications and fact-rendered responses through Stage 04 authority.
- Add browser push-to-talk, transcript/reply/audio, consent controls and stop/error states.
- Voice checkout handoff checks exact SKU/quantity and independent WhatsApp consent.

Validate: adjudicated evaluation set, deterministic baseline comparison, injection/wrong-recipient/unsupported-offer tests, all protective cases and real configured model latency/cost evidence. Audio denial/poor transcript/duplicate turn must safely recover.

Owner review: “later reminder + coupon enquiry”, voice same-product request, ambiguous date and opt-out while the model fails. No telephone automation is claimed from browser audio.

Provider selection is not implied by the Codex implementation model name. Without a selected provider, deterministic/mock evaluations may run but real AI/audio capability stays unverified.

### Stage 08 — outcomes, customer learning and accounting

Deliver:

- Persist assigned cohorts independently of plans and aggregate verified brand-wide outcomes.
- Show outside-link order inclusion, refunds/tax/shipping basis, missing costs and return maturity.
- Save confirmed customer dates/preferences with scope/provenance.
- Add reviewable policy suggestions with evidence and proposed diff; no autonomous boundary change.
- Record intervention time and future treatment/control assignment contracts without adding prototype experiment-management screens.

Validate: T17/T18, order deduplication, plan-renewal persistence, null cost arithmetic and consistent dashboard/outcome drilldowns. Incremental lift/time saved remain not measured without valid comparison.

Owner review: one outside-link order calculation, reminder learning and a suggestion review without fabricated profit or causal impact.

### Stage 09 — full journey, release and deployment handover

Deliver:

- Run all F01–F18, AC01–AC22, DEMO01–DEMO09 and T01–T26.
- Complete rendered state/accessibility checks and fix material failures.
- Rehearse migrations/backup restore, durable queue recovery and tenant/privacy/deletion boundaries.
- Produce actual provider capability/mode matrix, deployment runbook, rollback steps, configuration inventory and release limitations.
- Prepare reviewed code/commit/package as requested; owner deploys. Preserve confidential documents/secrets exclusions.

Owner review: uninterrupted identify → decide → act → learn demonstration, required failure paths and exact remaining simulated components.

A complete hybrid demo can include declared simulations. Production readiness requires the separate live gate in RUNTIME-AND-VALIDATION.md. Do not claim a native Agent Studio plugin, verified merchant lift or full WCAG compliance without actual evidence.

## 5. Ready-to-use initial prompt

Copy the following into the implementing chat configured as GPT-6.1-sol with low reasoning effort. No separate chat has been created by this handoff.

~~~text
Implement the Repeat Purchase Agent using the architecture package in docs.

Read AGENTS.md, the latest HANDOFF.md sections, docs/IMPLEMENTATION-HANDOFF.md,
docs/APPLICATION-ARCHITECTURE.md, docs/APPLICATION-CONTRACTS.md,
docs/RUNTIME-AND-VALIDATION.md, the approved docs/PRD.md and final entries of
docs/integration-status.md. Use docs/MERCHANT-UI-V2.md and the current merchant
template/CSS/JS as the visual reference. Preserve the original preview and
working Shopify connection.

Start with Stage 01 only. Inspect current uncommitted changes and preserve
them. Implement the complete Stage 01 vertical slice with real PostgreSQL
validation, safe owner bootstrap/session auth, scoped persistence, migrations,
idempotency/audit foundations and Shopify snapshot compatibility. Use the
technical defaults and contracts supplied; resolve routine choices yourself.
Keep credentials server-side and never print their values.

Create docs/implementation-evidence/STATUS.md and a Stage 01 evidence report
containing actual commands/results, a review path and remaining blockers.
Do not claim tests ran when only a test plan exists. If local DB/runtime
access is blocked, complete independent work and state the exact missing
prerequisite without substituting SQLite as proof of PostgreSQL correctness.

Preserve all F01–F18 for subsequent stages. Do not implement Stage 02 until
the owner has reviewed Stage 01 and instructed continuation. Do not infer
new external sends, expanded provider permissions, paid upgrades, live
payments or deployment from this implementation request. Honour specific
authorisations already recorded.

End with a concise outcome: files/behaviour changed, checks actually passed,
how the owner can review the result, and any material limitation. Avoid
routine questions already answered by the handoff.
~~~

## 6. Continuation prompt

~~~text
Continue from the accepted stage recorded in docs/implementation-evidence/STATUS.md.
Read its evidence and the latest owner instructions first. Implement the next
stage in docs/IMPLEMENTATION-HANDOFF.md using the architecture/contracts/runtime
package. Preserve working paths, run the stage's meaningful checks, update
actual evidence, and present the reviewable result before advancing again.
~~~

## 7. Developer report format

Keep stage reports short but evidential:

~~~text
Stage:
Scope and implemented behaviour:
Changed files/migrations:
How to run and review:
Checks run (command, result, case IDs):
Provider capabilities verified (mode and receipt/evidence reference):
Capabilities still simulated/blocked:
Material limitations and exact next prerequisite:
Owner review status:
~~~

Do not mark accepted until the owner actually accepts/proceeds. Existing four Shopify tests and UI QA are historical baseline evidence; new architecture code needs its own checks.
