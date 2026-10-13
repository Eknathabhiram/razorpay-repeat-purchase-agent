# Runtime protocols and validation plan

Version 1.0 · 13 October 2026 · Proposed implementation protocols, not executed test results.

Read APPLICATION-ARCHITECTURE.md and APPLICATION-CONTRACTS.md first. This document defines what must happen under races, retries and missing data, and the evidence required to call a stage complete.

## 1. Installation → approved plan → first contact

~~~mermaid
sequenceDiagram
    actor M as Merchant
    participant UI as Merchant UI
    participant API as FastAPI
    participant DB as PostgreSQL
    participant W as Worker
    participant P as Provider
    M->>UI: Activate installed agent
    UI->>API: Activation digest + expected version
    API->>DB: Save installation and readiness
    Note over API,DB: No contact created by activation
    M->>UI: Approve exact audience and limits
    UI->>API: Plan revision + digest + idempotency key
    API->>DB: Lock, revalidate, write approval/cohort/jobs/outbox
    W->>DB: Claim due work with lease
    W->>API: Domain services propose and validate action
    alt Review-first
        API->>DB: Hold exact action for review
        M->>UI: Review actual message and approve
        UI->>API: Action revision/digest
        API->>DB: Revalidate and queue approved action
    end
    W->>DB: Preflight + reservation + durable submitting attempt
    W->>P: One bounded authorised request
    P-->>W: Provider reference / definite failure / unknown
    W->>DB: Receipt and updated journey
~~~

Approval never fabricates replies, reminders or purchases. First-plan mode starts with scheduled customers and empty outcomes. A fixture scenario may separately inject labelled inbound and purchase events through the same event processor.

Plan members must belong to the selected product scope and current workspace. Recheck delivered history, newest relevant purchase, issues, consent and source coverage at approval. An unselected/excluded member cannot be quietly added. Changes return a diff; the merchant approves the refreshed exact scope.

## 2. Durable worker protocol

Use PostgreSQL queue claims, not a process-local scheduler as authority. SKIP LOCKED is appropriate for competing queue consumers; use ordinary locks for customer/domain invariants. [PostgreSQL locking](https://www.postgresql.org/docs/current/sql-select.html)

Engineering defaults for development:

| Setting | Default | Meaning |
| --- | --- | --- |
| Claim batch | 10 jobs | Bound load; one session/unit of work per concurrent task |
| Poll interval | 1 second | Worker wake-up latency; paused work is excluded |
| Lease | 60 seconds | Extend every 15 seconds for non-dispatch processing |
| Provider HTTP timeout | 15 seconds | Connector-specific lower limit where required |
| Dispatch authorisation age | 2 seconds before request invocation | If certainly not invoked and expired, release/revalidate |
| Read/status retry | 3 attempts, exponential backoff + jitter | Only for idempotent reads/verified-safe operations |
| Unknown status schedule | 30 s, 2 min, 10 min; then owned exception | Queries only; do not infer failure when lookup is inconclusive |
| Reconciliation sync | 5 min with overlapping lookback | Supplement callbacks and discover outside-link orders; coverage explicit |

These are tunable application defaults to measure, not provider SLAs. Avoid sharing a mutable AsyncSession across concurrent jobs. [SQLAlchemy async guidance](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

### Claim and execute

1. In a short transaction, claim ready due jobs with SELECT ... FOR UPDATE SKIP LOCKED. Set lease_owner, random lease_token, lease_until and increment attempts. Commit.
2. Load only scoped subject/context. Refresh required external facts before holding database row locks. Persist facts/checkpoints and track their versions.
3. Use a second short transaction for domain decisions, checking lease token and current resource versions. Insert resulting outbox events atomically.
4. A stale worker cannot update the job or create a dispatch attempt with an old lease token. If ownership was lost, stop.
5. Publish/process outbox events through deduplicated consumer records. Notifications/read-model updates are repeatable. Retain failed items with actionable error.

Local job execution is at least once. Domain transitions are idempotent. External sends are not claimed exactly once; use the dispatch protocol below.

### Dispatch preflight and cancellation boundary

Acquire locks in consistent order: agent → current policy/plan → customer contact guard → action/job → sorted budget buckets. Concurrent pause/policy/consent/ownership commands use the relevant same locks. Refresh is outside this transaction; if relevant local facts changed meanwhile, retry preflight or block.

Check:

1. Workspace mode, connector account/capability and source freshness/coverage.
2. Agent enabled/not paused; owner autonomous, or authorised human message through the same rules.
3. Immutable approved plan/action revisions and expiry; active policy matches.
4. Exact customer/variant/quantity/confirmed intent and current purchase/issue state.
5. Channel-specific consent, no suppression, session/template rules, quiet hours and coordination.
6. All applicable contact caps/budget limits, known conservative contact cost and margin/offer constraints.
7. No customer-wide in-flight action or unresolved unknown attempt that conflicts.

Reserve one contact unit and maximum known cost exposure in the same transaction as a submitting dispatch attempt, lease-token verification and audit event. Increment/record the customer/agent dispatch epoch. Commit. Revalidate immediately if the command is known not to have been invoked before the short authorisation-age limit.

Once submitting is durably committed, treat the request as in flight. The provider call follows immediately with no additional discretionary processing. Pause/opt-out accepted afterwards blocks subsequent attempts but cannot promise to recall this one. A receipt shows any submitting/unknown action and pending result. This small distributed boundary is explicit, rather than a false promise of atomicity across PostgreSQL and the provider.

After response, a new transaction writes receipt/provider ref, updates ledger/budget, closes in-flight state when known, and updates job/journey/outbox. If a later callback resolves the result, apply it idempotently even while paused.

### Recovery and reservations

| Crash/result | Recovery | Cap/budget treatment |
| --- | --- | --- |
| Before claim/attempt commit | Job can be claimed later | No reservation |
| Leased computation before submitting | Reclaim after lease expiry, revalidate | Release only expired pre-dispatch reservations known not to have submitted |
| Submitting committed, process dies before/after network | Unknown; status discovery/operator review | Hold contact and conservative budget exposure |
| Provider accepts with message ID | Save submitted; callbacks/status determine delivery | Count attempt; reconcile actual cost later |
| Explicit rejection before provider accepted/sent | Definite failure; retry only under verified provider semantics and fresh authority | Release unused exposure; retain incurred costs where applicable |
| Timeout/network disconnect/5xx with possible execution | Unknown; do not replay | Do not release cap/exposure merely because lease expired |
| Known delivery failure after submission | Persist actual provider failure | Attempt still counts; any retry is a new authorised contact within remaining caps |
| Operator cannot resolve an unknown | Owned exception remains; affected outbound held | No automatic expiry that permits a duplicate |

If there is no provider reference and no reliable discovery API, do not pretend status lookup can uniquely identify the attempt. Do not match sent messages solely by body/time. Provider idempotency is used only when the provider's actual operation documents and tests it.

Budget reservations cover communication and allowed incentive exposure as relevant. Unknown pricing under a spend cap blocks real dispatch. Trial allowances do not automatically establish zero marginal cost for every operation. Demo adapters carry explicit synthetic cost evidence.

## 3. Inbound customer and voice flow

~~~mermaid
sequenceDiagram
    participant C as Customer/provider
    participant H as Webhook ingress
    participant DB as PostgreSQL
    participant W as Event worker
    participant L as Intent adapter
    C->>H: Signed inbound event
    H->>H: Validate raw request, binding/account and size
    H->>DB: Insert deduplicated inbox
    H-->>C: Provider-required acknowledgement
    W->>DB: Resolve verified customer and store message
    W->>DB: Cancel overlapping queued contact
    alt Explicit protective intent
        W->>DB: Suppress/hold support immediately
    else Interpretation needed
        W->>L: Minimal scoped facts + utterance
        L-->>W: Strict IntentProposal
        W->>W: Bind facts; validate and handle ambiguity
        W->>DB: Save proposed/state action and audit
    end
    Note over W,DB: Outbound reply uses the same reviewed dispatch pipeline
~~~

On any customer response, cancel or hold incompatible queued channel jobs before model interpretation. Silence never independently authorises escalation to voice. A reply with an issue stops sales even if the next model call fails.

Explicit deterministic opt-out tokens are normalised by configured locale/phrase list and full-message rules; avoid broad substring matches such as finding “stop” inside an unrelated word. Compound or ambiguous opt-out language is conservatively held and interpreted/reviewed. A trusted explicit stop is processed once even during model outage/pause.

Unmapped customer identity is quarantined. No fuzzy name/email matching creates a marketing contact. Provider inbound contact may prove sender control; it does not automatically grant all-purpose future WhatsApp/voice marketing consent.

Browser voice verifies short-lived session ownership, consent, turn sequence and supported audio type/size. Persist transcript then use the same flow. Duplicate turn sequence returns the existing operation; an out-of-order turn is rejected/held. Stop cancels recording and discretionary unsent speech; protective state still persists. Speech uncertainty on date/SKU/quantity requires clarification.

## 4. Reminders and channel coordination

Confirmed date/channel creates a reminder and a due job in one transaction. Store original customer words, absolute time and IANA timezone. “Friday” without a confirmed date/time remains clarification_required; resolve against event time and customer context, not the model's assumed current date.

Scheduling cancels incompatible immediate outreach. When due, refresh customer/orders/consent/stock/issues and approved limits. If the plan expired, hold the reminder for a fresh scoped approval rather than silently enlarging plan life.

For quiet hours and daylight-saving transitions, compute the next permitted local interval; invalid/nonexistent local times require explicit resolution. Tests cover Asia/Kolkata and a DST timezone even though the development merchant is in IST.

A shared customer guard covers WhatsApp, browser voice/telephone where applicable, and all managed campaigns. One active sales interaction can reserve the next action. A reply, new order, opt-out, takeover or support issue cancels/holds competing jobs across channels. Coordinator unavailability prevents affected sends.

Separate voice and WhatsApp permissions are checked for the Rahul handoff scenario. Saving a one-time channel choice does not overwrite a durable preference.

## 5. Checkout and purchase reconciliation

~~~mermaid
sequenceDiagram
    participant C as Customer
    participant A as Agent services
    participant S as Shopify
    participant R as Razorpay
    participant D as Database/event processor
    C->>A: Confirm same variant and quantity
    A->>S: Refresh terms/availability; create authorised cart
    S-->>A: Cart/checkout receipt
    A->>D: Persist preparation; payment remains pending
    A-->>C: Approved permitted checkout handoff
    C->>S: Review final checkout charges and pay
    S->>R: Gateway-owned payment flow
    S->>D: Commerce event/source evidence
    R->>D: Signed payment event/source evidence
    D->>S: Fetch order/transaction facts if needed
    D->>R: Fetch captured payment/order facts if needed
    D->>D: Exact reference/mode/currency/amount match
    D->>D: Record outcome once; cancel conflicting outreach
~~~

No separate agent charge is initiated. Native Shopify checkout creates the commerce order/gateway payment path. The application never treats cart creation, WhatsApp delivery, browser callback, a manually marked paid draft or an unverified receipt as a confirmed purchase.

Match by a verified adapter-supported provider transaction mapping and account/environment. Compare full order payable total against actual captured allocations; the INR 499 item price alone does not match the INR 1273.15 shipping-inclusive test payment. Unsupported partial payments, edits or splits become reconciliation exceptions until allocation rules are implemented.

For the current test evidence:

~~~text
Shopify order: #1001 / gid://shopify/Order/18944435290275
Financial: PAID; fulfilment: UNFULFILLED; delivery: not verified
Shopify gateway transaction: SALE/SUCCESS/test=true
Razorpay payment: pay_Tn7feQ0B51wPZd; captured; INR 127315
Razorpay order: order_Tn7en9W2ipOAwl; paid
Observed cross-reference: Shopify paymentId == Razorpay order receipt
~~~

This is a contract-test fixture/evidence example. Do not hardcode these identifiers as the general matching algorithm. Store original provider evidence in restricted records and normalise through a versioned mapping adapter.

Outside-link purchases must still cancel relevant contact and enter the assigned cohort outcome if verified. Unmatched/new order evidence holds outreach immediately while reconciliation runs; the customer is not pressured while purchase truth is uncertain. Count order once after confirmation, and preserve its evidence if a plan is renewed/rejected.

Callback order is not reliable. Merge status facts without regressing read/captured/delivered from older events; refunds/returns remain legitimate later adjustments. On contradictory evidence or missing resource version, schedule an authoritative read. Polling lookback and cursor pagination recover missed callbacks.

## 6. Policy, pause, takeover and issue resolution

Policy update creates an immutable version and impact diff, increments relevant authority epoch and holds affected queued/proposed actions. An old plan approval cannot authorise new audience/channels/offers/caps. Merchant manual messages still pass current policy/consent/provider checks.

Pause atomically records reason/time, increments dispatch epoch and prevents new submitting commits. Already submitting/submitted actions may finish; show them. Continue trusted inbox/status/payment events, suppression and protective state updates.

Takeover locks the customer/journey, sets human owner and cancels autonomous unsent proposals/jobs. Closing the drawer does not hand back. Human send is a separately authorised action. Handback and resume require current consent, source capability, no open issue, valid approved scope, budget/caps and resolved unknown attempts.

Support resolution needs evidence and owner. It does not automatically clear opt-out, change permission, extend approval or create sales outreach. Recalculate eligibility and require fresh relevant authority. Connector revocation cancels/blocks dependent new work and preserves historical receipts.

## 7. Fixtures and evidence strategy

Use deterministic persistent demo adapters with an injectable clock. Every fixture fact/receipt is simulated. Develop actual Shopify/Razorpay adapter contract tests against redacted captured payloads and separately record optional account-backed checks.

Fixture cases:

| Case | Evidence/event | Expected result |
| --- | --- | --- |
| C001 Ananya | Same-SKU delivered intervals; “remind me later” with confirmed date | Reminder persists, other channel cancelled |
| C002 Rahul | Voice exact variant/quantity; separate WhatsApp consent/handoff confirmation | Checkout + reviewed send; no order until trusted evidence |
| C003 Meera | New brand order outside agent link and matched test payment | Reorder jobs cancelled; one cohort outcome |
| C004 undelivered | Paid/fulfilled evidence without delivery | Excluded |
| C005 opted out | Opt-out during pause/model outage | Suppression persists, both channels cancelled |
| C006 support | Delivery complaint, external handoff failure | Internal owned case; no sales |
| Sparse history | No comparable intervals but configured fallback | Product estimate labelled; no fake score |
| Stock/offer edge | Changed stock, expired offer or missing margin costs | Block/reconfirm; no invented incentive |
| Unknown send | Provider accepts then response lost | No second send after timeout/restart |
| First plan | No customer replies or orders injected | Approval yields schedules, empty outcomes/preferences |

Demo histories may exist only in the app fixture database until Shopify historical write capability is explicitly reviewed. Do not represent current manually created orders as past delivered purchases. The fixture seed/reset command is demo-only; development test-history writes are a separately reviewed stage.

## 8. Acceptance matrix

Implement meaningful domain/transaction tests and full browser journeys. These IDs are requirements; mark pass/fail only after running them and saving evidence.

| Test | Required assertion | Existing specification |
| --- | --- | --- |
| T01 scope/identity | Cross-tenant/workspace reads and forged IDs denied; composite FK isolation | F03/F15, security |
| T02 installation | Missing execution role blocks activation in that environment; installed alone sends nothing | AC01, F01/F02 |
| T03 eligibility | Missing consent/new purchase/undelivered/return/issue/opt-out excluded | AC02, F05/F06 |
| T04 estimator | Exact dates/evidence, compatible quantities/fallback; missing basis yields needs_history | AC03 |
| T05 approval | Changed audience/policy/message/offer invalidates previous authority; concurrent approvals idempotent | AC04, F07/F14 |
| T06 checkout | Same variant/quantity and refreshed market terms; changed terms require confirmation | AC05/AC12, F11 |
| T07 offers/costs | Unapproved/expired offer blocked; missing required costs prevents incentive/profit | AC06/AC18, F12/F17 |
| T08 compound/date | Later date + coupon processed independently; ambiguity never schedules | AC07/AC08, F08/F09/F13 |
| T09 coordination | Concurrent voice/WhatsApp/campaign workers cannot exceed customer cap/budget | AC09, F10 |
| T10 protection | Opt-out and support block persist during pause/model outage; no cross-sell | AC10/AC11, F13 |
| T11 stale facts | New order/revocation/stock change between approval and dispatch stops unsent work | AC12 |
| T12 events | Duplicate/out-of-order callbacks yield one transition/action/outcome; status never regresses | AC13, F15 |
| T13 unknown | Crash before/after submitting and accepted-but-timed-out send never causes blind resend | AC14 |
| T14 payment truth | Browser fake success rejected; exact payment/order/mode/total match counted once | AC15/AC16, F11 |
| T15 unmatched | Paid/unmatched and contradictory transactions create owned exception; no purchase metric | AC17 |
| T16 supervision | Pause/takeover/revoke serialise with dispatch; in-flight boundary visible; handback checks | AC19, F14 |
| T17 learning | Confirmed scoped preference retained; policy suggestion needs review; one-off handoff not permanent | AC20, F16 |
| T18 accounting | Outside-link orders/cohort persist; refunds/missing costs/source modes/lift labels correct | AC21, F17 |
| T19 restart | Policies, approval, reminder, consent, receipt and unknown reservation survive DB/process restart | AC22 |
| T20 frontend | Full entry/setup plus v2 surfaces; pending/empty/error/paused/unknown states and receipts | F01/F18 |
| T21 access | Keyboard/focus/escape/return; 320–1440 px; 200% text/zoom, measured contrast/labels | F18 |
| T22 auth/webhooks | Sessions/CSRF/roles, invalid signatures, raw-body handling, callback account mismatch | F03/F15 |
| T23 provider modes | Development refuses live key; no simulated receipt satisfies real capability | F03 |
| T24 voice | Permission denial, stop, duplicate turn, poor transcript, independent handoff permission | F09 |
| T25 campaign gate | External coordinator loss/absence blocks affected sends; renewal cannot evade caps | F10 |
| T26 restore/migrate | Migration rehearsal, backup restore, worker lease recovery and deletion scope | Release |

Use real PostgreSQL for T01/T05/T09/T12/T13/T16/T19/T26 transaction cases. Test interleavings with barriers, not only sequential calls. Simulate crash exactly after submitting commit and after provider acceptance. Verify both database state and adapter call count.

### Feature completeness map

| PRD features | Implementation stages in handoff | Acceptance |
| --- | --- | --- |
| F01–F02 entry/installation | 02, 03 | T02/T20/T21 |
| F03 connections | 01, 03, 05, 06 | T01/T22/T23 |
| F04 policy | 03 | T05/T07/T16 |
| F05–F06 detection/eligibility | 03 | T03/T04/T11 |
| F07 audience/plan | 03, 04 | T05/T09/T19 |
| F08 WhatsApp | 06, 07 | T08/T10/T12/T13 |
| F09 voice | 07 | T08/T24 |
| F10 coordination | 04, 06, 07 | T09/T25 |
| F11 checkout/payment | 05 | T06/T14/T15 |
| F12 offers | 05, 07 | T07 |
| F13 reminders/support/opt-out | 04, 06, 07 | T08/T10/T19 |
| F14 supervision | 04 | T05/T16 |
| F15 audit/recovery | 01, 04, 05, 06 | T12/T13/T19/T22 |
| F16 learning | 07, 08 | T17 |
| F17 analytics | 08 | T18 |
| F18 usability | 02 and every stage, 09 | T20/T21 |

DEMO01–DEMO09 must all be executable through labelled scenarios with persistent backend evidence. Coverage includes AC01–AC22; none is dropped because a provider account is unavailable.

## 9. AI evaluation gate

Keep an adjudicated, versioned evaluation set in backend/tests/evals. Initial minimum: 60 cases covering direct/compound replies, ambiguous dates, language variation used by the selected demo, opt-outs, product dislike, injection, wrong SKU, wrong recipient, unavailable stock, unsupported offers, missing costs and model timeouts. The count is an engineering floor; add cases whenever a defect is found.

Separate evaluator labels for intent correctness, confirmation requirements, fact references and deterministic authority result. Compare model interpretation with a button/branch baseline. A fluent answer is not an execution pass.

Gate: zero prohibited side effects across the release suite; all explicit opt-out/protection fixtures persist correctly; invalid schemas/unknown tools cannot execute; financial assertions come from facts; all failures have a visible safe outcome. Report observed counts and failed case IDs. Do not invent accuracy percentages or claim statistical confidence from this small suite.

Mock-model tests cover authority independently of vendor behaviour. After provider selection, run the same cases against the configured real model with recorded prompt/schema/model versions and cost/latency. Re-evaluate after material prompt/model changes.

## 10. Release and handover evidence

Each stage report records files changed, migration/command run, test counts/failures, actual provider modes, screenshots where applicable, remaining blockers and a concrete owner-review path. A test plan is not a test result.

Final complete hybrid-demo gate:

- F01–F18 and DEMO01–DEMO09 implemented through the server.
- No localStorage authority; restart and concurrency tests pass.
- Real adapters pass capability-specific checks; unavailable capabilities visibly blocked/simulated.
- Complete visual/focus/error-state evidence; material limitations explicit.
- Outcomes consistent with source/payment/accounting evidence; contribution/lift/time-saved labels honest.

Separate live gate: authorised recipients and scopes, verified delivery/consent/campaign coordination, actual permitted sender/templates, auth/tenant isolation, host/TLS/secret storage, signed callbacks, retention/deletion, backup/restore, mature measurement plan and owner deployment/rollout decision. Preparing this architecture authorises none of those external operations by itself.
