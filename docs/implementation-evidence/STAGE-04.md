# Stage 04 — approvals, durable demo execution and supervision

13 October 2026 · ready_for_review

Review [Execution](http://127.0.0.1:8766/app/#/execution) with the existing owner account. In Demo, save a current audience in Planning, then review its exact audience and proposed messages in Execution. Plan approval creates durable assignments and proposed actions; review-first mode still requires message approval. Run due demo jobs to inspect simulated receipts. Pause, take over a conversation, or inject an explicitly synthetic opt-out/support/reminder/purchase signal to inspect protective behavior. Development execution remains blocked.

## Implemented authority and persistence

Migration 0004_execution adds agents/epochs, immutable approvals and audience assignments, journeys, immutable action payloads, leased jobs, customer-wide contact guards/ledger, budget buckets/reservations, attempts/receipts, simulated transport evidence, reminders/support and deduplicated inbox/outbox records. Composite foreign keys retain workspace scope. The app role cannot update/delete approvals, assignments, receipts, transport evidence or event records; action UPDATE permission covers state/timestamp only. Migration DDL and the due-job index are frozen.

Plan approval binds the current draft to the exact rendered message manifest, selected audience, policy and expiry. It re-evaluates current eligibility. Action approval binds the content digest. Changed audience, policy, evidence generation, expiry, variant or content stops unsent work. Bounded mode authorizes deterministic messages within the reviewed mandate; review-first mode requires individual action review. The renderer currently permits reorder checks, confirmed reminders and a fixed human acknowledgement; unrestricted human text and AI interpretation are later work.

Audience assignments survive policy/draft changes. A first plan creates no customer replies, purchases or payment confirmations. The simulated purchase signal creates a protective hold, not a Shopify order or payment record. Confirmed reminder evidence persists as an absolute time with Asia/Kolkata and WhatsApp channel; non-response creates no reminder. Renewal cancels incompatible unsent work while retaining historical assignments and receipts.

## Worker and safety behavior

The PostgreSQL worker claims bounded due jobs with SKIP LOCKED and random 60-second leases. Preflight uses the same workspace lock as policy/fact/supervision commands, then scoped customer/budget locks. Broad workspace serialization is intentional for this local implementation. Lease token/expiry fencing prevents stale claims from authorizing an attempt. Before dispatch, it checks current approvals, facts, consent/suppression/issues/purchases, ownership, quiet hours, customer-wide seven-day contact cap, conservative cost and policy budget.

Contact and cost reservations commit with a durable submitting attempt before the simulated adapter is invoked. The adapter writes separate durable Demo transport evidence; it makes no provider request. Submitted is separate from delivered/read/replied/paid. A definite rejection releases unused exposure. Unknown/submitting crashes retain contact and budget exposure and are not resent. Status recovery uses the exact simulated attempt reference; absence of proof leaves an owned exception. Recovery can record a known result while paused without weakening opt-out or support state. There is no force-success or blind retry operation.

Pause blocks new attempts but cannot promise to recall a durably submitting attempt. Takeover blocks autonomous contact across the customer; a reviewed human acknowledgement uses the same guards. Handback cannot clear unresolved in-flight/unknown protection. Support issues immediately cancel unsent sales and create an internal case, even without an external support provider. Case resolution requires assignment and does not automatically restore old sales authority. Opt-outs remain active across pause, renewal and support resolution.

Inbox event keys bind exact content and duplicate processing is suppressed. Outbox evidence is committed with domain transitions and consumed by a deduplicated local read-model consumer. No external publication or provider callback authenticity is claimed.

## Validation evidence

- Full PostgreSQL regression suite: 38 tests passed in 697.653 seconds. See stage-04-all-tests.txt. A Windows process lookup/runtime slowdown increased elapsed time.
- All eleven execution tests passed again after content/unknown ownership tightening in 126.573 seconds. See stage-04-final-tests.txt. Initial failure was an incorrect fixture-order count in the test (24 actual versus 25 expected), corrected before these passes.
- Final ownership/handback assertions passed: two tests in 28.983 seconds, stage-04-ownership-tests.txt. Unresolved outcomes retain an owner and cannot be handed back; ordinary resolved handoff still works.
- Budget/contact concurrency uses barriers; recovery tests cover expired claims, stale tokens, crash after submitting, crash after simulated acceptance, pause/opt-out and duplicate inbox events. Immutable record privileges and viewer/scope denial are tested.
- Four preserved Shopify compatibility tests passed: stage-04-compatibility-tests.txt.
- Actual OpenAPI export/types, strict TypeScript and Vite production build passed.
- Twelve browser checks passed: exact plan/message approvals, pause/resume and receipt separation, persisted takeover/reminder, opt-out, assigned support, and reflow at 1440/1024/768/390/320 pixels. See stage-04-browser.json, stage-04-browser-log.txt and stage04-screens/. Desktop/mobile approval and execution renders were inspected. This is not full accessibility certification.

## Run and handover

Start ./backend/run-foundation.ps1 and preserve the existing PostgreSQL database and owner credentials. Current schema: 0004_execution. The owner account/password is unchanged. The Execution UI's Run due demo jobs button runs a bounded worker batch; no worker is silently started on application login.

For a separate persistent local Demo worker, load backend/scripts/foundation-env.ps1, enter backend, and run:

~~~powershell
python -m app.worker --workspace <Demo-workspace-UUID> --once
~~~

Use the configured bundled Python from the environment script, rather than an unrelated system interpreter. Remove --once to poll every second; stop with Ctrl+C. This worker is explicitly restricted to Demo. Restart does not recreate authority from browser state. Leased computation is reclaimable after expiry; submitting uncertainty is retained for status discovery/owned review.

Tests: backend/scripts/check-foundation.ps1; targeted execution cases: python -m unittest tests.test_execution -v. Browser check: frontend/app/tests/execution-check.mjs with a fresh isolated QA tenant from backend/scripts/prepare_stage04_qa.py. Its private credential file is ignored. No owner data is reset by QA. Frontend API export/build commands remain in the Stage 03 handover.

Stage 03 was accepted for continuation by the owner's “okay” and “do it”. Stage 04 awaits review. Stage 05 adds checkout preparation, payment evidence/reconciliation and offer validation. WhatsApp/voice transports, real-provider status retries, live dispatch authorization-age measurements, external callback signatures, deployment and production RLS remain separate later-stage gates. Current quiet-hour configuration supports IST; broader timezone/DST and live transport timing need their release validation.
