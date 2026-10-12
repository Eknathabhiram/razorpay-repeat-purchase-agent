# Backend

This folder reserves the server-side application boundary. No backend service or live integration exists yet. Implementation follows approval of `../docs/PRD.md` and selection of the unresolved technology/provider choices.

## Responsibilities

- Authenticate merchants and enforce tenant isolation and roles.
- Persist connector permissions, policies, approvals, journeys and audit records.
- Estimate repeat windows and apply deterministic eligibility checks.
- Schedule work and coordinate WhatsApp/voice through one contact ledger.
- Validate every proposed action against current facts, consent and approved scope.
- Run commerce/payment, messaging, voice and support adapters with server-side secrets.
- Verify webhook authenticity, deduplicate events and reconcile uncertain execution.
- Calculate observed outcomes and propose evidence-backed learning changes.

## Proposed modules, subject to PRD approval

`identity`, `connectors`, `policies`, `opportunities`, `plans`, `journeys`, `scheduler`, `action-validator`, `conversations`, `commerce`, `reconciliation`, `support`, `analytics`, `learning`, `audit`.

Adapters must declare disconnected, simulated, test or live mode. The language model proposes intent/actions; deterministic server checks authorise execution. Mock/test results never become live evidence.

No programming framework, database, model provider or hosting service has been selected. See PRD section 16 for the decision register.
