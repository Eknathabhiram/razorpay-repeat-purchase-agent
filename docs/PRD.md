# Repeat Purchase Agent — Product Requirements Document

Version: 2.0 | Date: 12 October 2026 | Owner/approver: project owner

**Approval status: APPROVED — 12 October 2026.** The project owner approved proceeding after review of the PRD. Approval covers the product scope and requirements; it does not establish completed implementation. The owner's latest 18-feature list is the scope authority. Implementation choices explicitly marked pending remain undecided even if the product requirements are approved.

## 1. Product purpose

Build the full journey **identify → decide → act → learn** for a specialist Repeat Purchase Agent proposed for Razorpay Agent Studio. Help growth owners at Indian D2C brands generate profitable repeat purchases by adapting timing and conversations to individual readiness and reasons for waiting.

The agent identifies a likely reorder opportunity, proposes a merchant-approved plan, coordinates WhatsApp and voice, prepares a same-product checkout or a more appropriate next action, verifies outcomes and improves subsequent decisions. Merchant control and customer choice apply throughout.

The hypothesis is that relevant timing and adaptive outreach improve incremental net contribution while reducing manual retention work and discount waste. Merchant demand, predictive quality and business lift remain unvalidated hypotheses.

### Users and jobs

| User | Job | Authority |
| --- | --- | --- |
| Growth owner | Choose audiences, operating boundaries and offers; assess economics | Configure/install, approve plans and policy changes, supervise and pause |
| Merchant operator/support owner | Resolve reviews, conversation takeovers and customer issues | Assigned operational actions within server-enforced roles |
| Returning customer | Reorder when ready, defer, ask questions or stop | Confirms product, quantity, reminder date and purchase; controls contact preferences |

Roles are proposed logical permissions, not an assertion about private Razorpay platform roles. Map them to the selected authentication system before implementation.

## 2. Scope and outcome

All 18 features below are included. Build sequencing must not reduce this to an MVP or omit voice, learning, supervision or failure handling. Current execution supports **the same previously purchased SKU/variant**; a customer can confirm a different quantity of that same item.

Excluded execution: alternatives, pack recommendations, cross-sell, acquisition, subscriptions, autonomous pricing, automatic charges, refunds, cancellations and address changes. Alternatives/packs and broader cross-sell are roadmap concepts only.

### Success measures

| Measure | Definition and reporting rule |
| --- | --- |
| North star | Incremental net contribution per eligible customer assigned to agent vs comparable control |
| Fallback | Incremental net revenue per eligible assigned customer when reliable costs are unavailable |
| Supporting | Repeat-order rate and merchant time saved |
| Customer guardrails | Opt-outs and complaints per contacted customer |
| Execution guardrails | Prohibited action executions, duplicates, failed/blocked actions and reconciliation errors |
| Economic monitoring | Contact and discount spend, cost completeness and contribution per order |

A prototype displays observed synthetic/test outcomes and **incremental lift: not measured**. A valid rollout comparison is required for incremental claims; experiment administration is not a prototype screen. No invented percentage targets, sample sizes or validated accuracy claims.

## 3. Complete merchant and customer journeys

### Merchant journey

1. Enter through the Razorpay-style login/verification preview and payments dashboard; discover the agent in Agent Studio.
2. Inspect purpose, access, capabilities and limitations; install using Configure → Connectors → Review → Activate.
3. Connect actual available sources, inspect modes/permissions/health and set a versioned operating policy.
4. Review suggested opportunities, timing evidence, uncertainty and exclusions.
5. Edit the audience and schedule; approve or reject a concrete plan. Installation never authorises customer outreach by itself.
6. Monitor active journeys, approve actions in review-first mode, resolve exceptions, take over or pause.
7. Inspect verified orders, costs, customer preferences and learning suggestions; approve consequential policy changes.

### Customer journeys

- Ready: confirm same SKU/variant and quantity → verify facts → prepare checkout → customer pays → payment/order reconciliation → outcome recorded.
- Waiting: clarify and confirm a date and permitted channel → save reminder → cancel overlapping outreach → recheck eligibility when due.
- Price concern/coupon enquiry: check existing authorised offer → explain verified eligibility/terms or absence → checkout only when requested and permitted.
- Voice: identify assistant and purpose → understand/confirm intent → browser audio for current demonstration → permitted WhatsApp checkout handoff when requested.
- Complaint/product dislike: stop sales progression → record support handoff and owner → unresolved issue suppresses purchase outreach.
- Refusal/opt-out: end current outreach or persist appropriate suppression → cancel queued jobs; suppression still processes during pause/outage.

## 4. Functional requirements and acceptance criteria

Requirement IDs F01–F18 correspond exactly to the latest feature list, rather than the older specification's different numbering. Every mutation must persist, return its state/receipt and produce an audit event. The following are acceptance requirements, not passed test results.

### F01 — Razorpay-style entry and navigation

Provide sample login/verification, payments-dashboard entry, Agent Studio discovery/detail, Home / My Agents / Connectors, and agent Dashboard / Activity / Settings. Preserve the public-reference shell and navigation patterns. Identify proposed screens and sample authentication honestly. Do not collect real Razorpay passwords or claim private production fidelity.

**Accept:** all navigation destinations work; installation and operating views are distinct; sample entry is labelled; page state is coherent after navigation/back and refresh. Merchant navigation has no demo playback controls mixed into primary actions.

### F02 — Agent installation

Use a modal with four vertical steps: Configure, Connectors, Review, Activate. Show capabilities, limits, required access, missing dependencies and activation consequences. Installation saves configuration and activates readiness; customer contact requires a separate approved audience/plan.

**Accept:** missing required sources prevent activation with specific repair guidance; completion persists; activation creates no outbound customer jobs; closing/reopening preserves the appropriate draft state; focus returns to the triggering control.

### F03 — Connections and integration health

Cover Shopify commerce, Razorpay payments, WhatsApp, voice, and support/delivery evidence. An adapter may serve more than one evidence role only when its capabilities are verified. Display permission scopes, disconnected/simulated/test/live mode, health, last successful sync, stale data and repair actions. Do not equate a saved credential or sample badge with a verified connection.

**Accept:** a disconnected service never displays connected; revoked permissions block dependent actions; real permission/sync checks produce receipts; mock sources remain labelled; connection state survives restart. Mode compatibility prevents test/live event mixing.

### F04 — Merchant operating policy

Save selected repeatable SKUs, channels, schedule and customer timezone handling, quiet hours, total/shared contact caps, spend caps, approved offers, required margin floors and execution mode. Offers default off until authorised. Policies have immutable versions and a reviewable change history. Validate missing/contradictory settings before activation or plan approval.

**Accept:** policy edits create versions; expanded scope requires fresh approval; restrictions apply immediately; budgets and counts are enforced by the server; missing required costs block incentives under a margin rule; UI explains invalid fields.

### F05 — Opportunity detection

Use qualifying delivered orders, exact SKU/variant, quantity, prior intervals, elapsed time and confirmed customer dates. Return a suggested repeat window, basis, data coverage, estimator version and uncertainty. Prefer customer-specific evidence where sufficient; otherwise use a merchant-approved product-level fallback. Confirmed dates override inferred timing within permitted scheduling boundaries.

**Accept:** every suggestion has inspectable evidence; sparse history shows fallback; undelivered orders do not establish depletion; no fabricated confidence score or consumption claim; the demo calls synthetic-history timing an estimate, not validated ML.

### F06 — Eligibility and suppression

Deterministically exclude newer relevant buyers, undelivered/returned qualifying orders, unresolved issues, uncertain customer identity, missing channel permission, explicit opt-outs and unavailable SKU stock. Record all reasons without double-counting customers. Run checks before selection and again immediately before execution.

**Accept:** excluded customers receive no outbound job; new orders or opt-outs after approval stop dispatch; stale/unknown facts block the affected action; immediate opt-out persists during pause; suppression and permission apply to all relevant channels.

### F07 — Audience and plan approval

Present exact customer IDs/count, selected products, timing, channels, contact/spend limits, permitted actions, offers and expiry. Show forecast contact costs as estimates with assumptions/missing inputs. Let merchants edit timing, exclude customers, approve or reject. Save approving identity, timestamp and immutable policy/audience snapshot.

**Accept:** no new customer silently joins an approved plan; audience or permission expansion invalidates approval; rejected/expired/superseded plans cannot execute; narrowed permissions constrain queued actions; costs are not described as predicted incremental revenue.

### F08 — WhatsApp automation

Interpret free text and shortcuts for reorder, waiting, price concern, coupon enquiry, complaint, refusal and opt-out. Resolve compound requests separately. Validate actual provider session/template conditions before outbound communication. Store inbound/outbound timestamps and provider delivery states; sent is not read.

**Accept:** ambiguous intent receives clarification; an unauthorised offer request cannot cause a discount; opt-out bypasses discretionary model dependencies; provider receipt determines delivery status; duplicate inbound events cause one mutation/action; simulator messages are labelled.

### F09 — Voice automation

Identify assistant and purpose. Confirm intent, ambiguous dates, same SKU and quantity; record transcript and outcome. Support requested checkout handoff through separately permitted WhatsApp. Browser microphone/audio is the recommended demonstration mode. Real telephone calls require a separately verified provider and permissions.

**Accept:** transcript-only replay is never labelled a call integration; unclear date creates no reminder before clarification; interruption and correction are handled in the supported mode; no WhatsApp send without its permission; denied microphone access shows a labelled fallback and recovery action.

### F10 — Shared channel coordination

One journey/contact ledger covers WhatsApp and voice. Use explicit preference, relevant response history, then approved merchant default. Enforce distinct permissions, combined caps, quiet hours and budget reservations. Responses, purchases, complaints, refusal and opt-out cancel incompatible queued contact. Silence means unknown readiness and does not independently authorise calling.

**Accept:** concurrent jobs cannot reserve/send competing outreach; each event updates the shared journey; a one-off handoff does not become a permanent preference; external reorder campaigns exclude the approved audience; failed verified campaign coordination pauses affected execution.

### F11 — Checkout and purchase verification

Fetch current stock, price, variant, quantity and commercial terms from authoritative commerce sources; confirm with customer; produce a valid same-product checkout. Customer reviews final charges and pays. Keep checkout created, payment pending/confirmed, order created, fulfilled and delivered separate. A standalone payment link is not proof of a commerce order.

**Accept:** browser success cannot confirm purchase; trusted payment and commerce identity/amount/currency/order mapping must reconcile; repeated events confirm once; unmatched payment becomes an owned exception; confirmed brand purchases cancel outreach even when made outside the agent link; changed terms require reconfirmation.

### F12 — Conditional approved offers

Only consider existing merchant-approved offers for price concerns or explicit enquiries. Validate scope, customer/SKU eligibility, expiry, redemption limits, remaining budget and required margin. No invented discounts, autonomous negotiation or incentives after silence. Merchant approval cannot bypass prohibited actions or invalid provider eligibility.

**Accept:** offers remain off by default; an expired/ineligible coupon is not promised; concurrent reservations cannot overspend; missing required cost blocks execution; audit captures validation inputs and result; no pressure or invented scarcity.

### F13 — Reminders, support and opt-out

Persist confirmed date/timezone/channel, confirm with customer and cancel superseded reminders. Recheck current eligibility when due. Complaints/product dislike suspend relevant purchase outreach and create a support handoff with owner and receipt. Explicit unsubscribe is processed immediately; do not interpret simple refusal as permission for escalating follow-up.

**Accept:** ambiguous date produces clarification; reminder survives restart; no contact after later reorder; support-source failure leaves a visible owned exception; pause does not defer opt-out; resume cannot remove suppression; no substitute-product recommendation.

### F14 — Supervision and action review

Bounded mode executes only approved routine actions; review-first holds outgoing messages, call starts and commerce actions for review. Show proposed actions, current facts, checks and consequences. Support approve/reject, valid edits, conversation takeover, queued-contact cancellation and pause/resume. Handback/resume requires current eligibility and approval checks.

**Accept:** approval validates the exact action version; edits invalidate prior approval where needed; takeover stops autonomous conversation actions; pause blocks new sends while trusted events/suppression continue; already submitted external actions are reconciled, not falsely described as recalled.

### F15 — Activity, audit and failure recovery

Show customer words, interpreted intent, source-verified facts, customer-stated facts, inferred estimates, concise reasons, checks, approvals, actions, execution receipts and results. Handle stale/missing data, ambiguity, provider failure, duplicate/unordered events and unknown execution. Status lookup precedes retry of a possibly completed action.

**Accept:** repeated event/action keys return existing result; timeout-after-send stays unknown until resolved; no blind retry; every block has reason and owner/recovery path; explanations never stand in for receipts; no hidden chain-of-thought is exposed.

### F16 — Learning from outcomes

Persist confirmed reminder dates/preferences, reply reasons and verified purchases within a merchant account. Timing updates use qualifying delivered purchases; a click or sent checkout does not become a repurchase. Record estimator/policy versions. Evidence-backed cohort suggestions can propose timing/channel/offer-policy changes for merchant review.

**Accept:** a one-off handoff does not create permanent preference; inference never overwrites explicit statements; policy suggestions show evidence/uncertainty/affected scope; no automatic cap, offer, permission or product-scope expansion; learning respects tenant isolation.

### F17 — Business analytics

Display assigned customers, journey states, verified brand orders, repeat-order rate, net revenue, known costs and provisional contribution. Include orders outside agent links. Show attribution, cost completeness, returns maturity, measurement window and calculation drilldown. Synthetic/test/live data and projections stay distinguishable.

**Accept:** missing cost is nullable, not zero; incomplete costs prevent a complete contribution claim; duplicate orders do not double-count; refunds update net sales when trusted evidence arrives; causal lift remains not measured without comparison; agent-link attribution is separate from incrementality.

### F18 — Usable, trustworthy interface

Design around: what needs my decision; what happened and can I trust it; did it improve business within my limits. Use consistent components/spacing/type, readable copy, one primary action per context, progressive disclosure and responsive layouts. Include first-use, empty, loading, disconnected, blocked, paused, uncertain and success states. Keep demo controls separate.

**Accept:** inspect key screens at roughly 1440, 1024, 768, 390 and 320 px, enlarged text and keyboard-only use; overlays manage focus/escape/return; statuses have text as well as colour; tables/transcripts remain usable. WCAG 2.2 AA is a design target requiring verification, not current compliance.

## 5. Screen and information architecture

| Surface | Main decision/information | Primary action |
| --- | --- | --- |
| Agent Studio Home/detail | Purpose, limits, access and installation status | Install or open agent |
| Install modal | Four steps, permission inventory, activation consequence | Continue/activate when valid |
| Connectors | Mode, health, scopes, freshness, dependency failures | Connect/repair |
| Agent Dashboard, first use | Missing setup and next decision | Finish setup/review first plan |
| Agent Dashboard, returning | Pending decisions, exceptions, running journeys, observed results | Resolve highest-priority decision |
| Opportunity/plan review | Readiness evidence, exclusions, audience and boundaries | Approve plan |
| Action review | Exact proposed action, policy/fact checks and consequence | Approve/reject |
| Activity/detail drawer | Conversation, evidence, receipts, state, owner | Take over/resolve as appropriate |
| Settings | Versioned policy and channel/offer/economic limits | Save policy changes |
| Analytics/learning | Verified outcomes, completeness and reviewable suggestions | Inspect result/review suggestion |

Preserve Razorpay-style header/sidebar, Studio Home/My Agents/Connectors, Dashboard/Activity/Settings, the four-step install modal and contextual activity drawers. Analytics placement within the operating experience can be refined during design without changing scope. Do not expose raw prompts or payloads by default.

## 6. Decision and execution contract

1. Read merchant/customer-scoped facts and identify freshness and provenance.
2. Interpret intent and propose a typed action or clarification. Model output has no execution authority.
3. Deterministic validation checks consent, suppression, exact SKU, approval/policy version, mode, schedule, caps, budget, costs, provider rules and current eligibility.
4. Review-first holds the action for the merchant. Bounded execution proceeds only if authorised.
5. Atomically reserve contact/budget and action identity; recheck before provider dispatch.
6. Execute through a scoped adapter, persist receipt and reconcile uncertain results.
7. Update journey, cancel conflicting jobs, publish audit/outcome/learning events.

Allowed action types: clarify, provide verified information, prepare same-product checkout, send permitted checkout handoff, schedule confirmed reminder, support handoff, end current outreach and suppress. Prohibited actions cannot be enabled by a conversational request or manual review bypass.

## 7. Proposed frontend/backend boundaries

The repository has `frontend/`, `backend/` and `docs/`. The current frontend is an HTML design simulation; backend is a documented scaffold. The framework/database/provider selections below are proposals awaiting selection.

Frontend renders verified server state, collects explicit decisions, manages accessible navigation and shows mode/receipt/error detail. It does not store provider secrets, authorise actions, calculate payment truth or call privileged provider APIs directly.

Backend owns authentication/roles, tenant isolation, connectors, policy/versioning, opportunities, approvals, persistence, deterministic validation, contact ledger/scheduler, model tools, adapters, webhook processing, reconciliation, analytics and audit.

A modular backend is the initial architecture recommendation: keep domain modules and adapters explicit without introducing independent services before operational need exists. Durable background work and transactionally safe reservations are required whatever stack is selected.

### Proposed API responsibilities (design contract; not implemented endpoints)

| Area | Operations | Required semantics |
| --- | --- | --- |
| Connectors | List, authorise, verify, sync, revoke | Server credentials, mode/scopes, freshness and dependency checks |
| Policy | Read, validate draft, save version, view diff | Immutable versions; optimistic concurrency |
| Opportunities | List/filter, inspect evidence, refresh, exclude/edit schedule | Deterministic eligibility and estimator provenance |
| Plans | Create/edit draft, approve/reject, expire/cancel | Approval binds exact version, audience and policy |
| Journeys | Inspect, pause/resume, takeover/handback, cancel queued action | Immediate ownership/dispatch checks |
| Reviews | List, inspect, approve/reject exact action | Revalidate stale facts and action version |
| Conversations | Inbound provider events, browser audio session, transcript/outcome | Identity/permission checks; coordinated state |
| Commerce/payments | Prepare checkout, ingest verified events, reconcile | Same SKU, idempotency, payment/order mapping |
| Outcomes/learning | Read aggregates/calculation, inspect/approve suggestion | Tenant scope, costs/maturity, no false lift |

Mutating requests carry tenant-scoped identity, expected version and idempotency key. Responses return resulting state/version, correlation ID and receipt or actionable error. Webhooks use provider-specific authenticity validation and event IDs. Final route names/schemas follow stack selection.

## 8. Minimum data model

| Entity | Minimum fields/invariants |
| --- | --- |
| Merchant and role | Tenant ID, timezone, currency, operator identity and permissions |
| Connector | Provider, evidence roles, mode, verified scopes, health, sync time, server credential reference |
| Product/variant | Commerce IDs, repeatable flag, verified availability/price, source timestamp |
| Customer | Tenant/commerce identity, verified channel mappings, permission evidence, explicit preferences |
| Order/payment/delivery | Provider IDs, line items, amount/currency, independent statuses, delivery/refund evidence and mapping |
| Policy version | Selected SKUs/actions/channels, timing/caps/budgets/offers/margin constraints, creator/time |
| Opportunity | Customer/SKU, history references, estimated window, basis/version/coverage, eligibility reasons |
| Plan/approval | Version, immutable audience, policy reference, schedule/expiry, offers/boundaries, approver/time |
| Journey | Customer/SKU, plan, state, owner, confirmed reminder, last event, version |
| Contact ledger/job | Channel, due time/timezone, reservation, attempts, approval, cancellation, provider receipt |
| Proposed action/review | Typed arguments, fact/policy references, validation result, version, reviewer/result |
| Event/receipt/audit | Deduplication key, source/time, correlation, mode, actor, before/after state, execution status |
| Offer/budget | Authorised provider offer ID, eligibility/expiry, reservations/redemptions, limits and cost inputs |
| Support case | Issue, owner, provider reference, status and blocked journey |
| Learning suggestion | Evidence, proposed change, uncertainty, scope, status and approval |
| Outcome | Verified order/customer assignment, costs/completeness, returns maturity and measurement window |

Store money using currency-aware integer minor units and deterministic calculations. Missing costs are nullable. Use timezone-aware timestamps and explicit scheduling timezone. Every record is tenant-scoped; provider identities are not globally trusted customer matches.

## 9. State transitions and concurrency

Agent states: setup_required, ready, running, paused, degraded, stopped. Plan states: draft, approved, superseded, expired, cancelled. Channel delivery, journey and commerce/payment states remain independent.

| Event | Result | Required side effect |
| --- | --- | --- |
| Eligibility fails | Excluded/blocked | Save reasons; no outbound job |
| Plan approved | Scheduled | Store immutable approval; queue permitted jobs |
| Dispatch preflight passes | Contacting/awaiting reply | Reserve ledger/budget; persist receipt |
| Waiting date confirmed | Reminder scheduled | Save date/channel; cancel incompatible jobs |
| Same-product reorder confirmed | Checkout ready | Fresh commercial checks and checkout receipt |
| Trusted payment/order match | Order confirmed | Record once; cancel competing reorder contact |
| Paid but unmatched order | Reconciliation required | Owned exception; no purchase-confirmed metric |
| Complaint/product dislike | Support handoff | Stop sales progression; record owner/receipt |
| Refusal | Declined | Cancel current incompatible follow-up |
| Opt-out | Suppressed | Persist immediately; cancel relevant marketing jobs |
| Pause/takeover/revocation | Execution blocked | Preserve pending state; continue trusted events/suppression |
| Resume/handback | Eligible scheduled state or blocked | Recheck permissions, facts, approval, ownership and budget |

Customer-level locking and atomic reservations prevent simultaneous channel dispatch and overspend. Approval and execution use version checks. Event handling must tolerate duplicates and out-of-order delivery without regressing newer facts. An unknown provider result is resolved by status enquiry or operator review before any repeat submission.

## 10. Safety, privacy and reliability requirements

- Enforce authentication, tenant scope and roles on every server read/write; a disabled button is insufficient.
- Keep secrets server-side and out of source control; sample login never collects real credentials.
- Minimise model-visible personal data; restrict transcripts/recordings to authorised purpose and access.
- Separate source-verified, customer-stated and inferred facts. Model output cannot establish price, stock, eligibility, payment or delivery truth.
- Validate inbound authenticity, deduplicate events and log actionable failures without secret leakage.
- Continue suppression and trusted event processing during model outage or merchant pause; pause discretionary generation.
- Treat customer instructions and transcripts as untrusted inputs to tools; enforce action allowlists and schema validation.
- Define recording/transcript consent, retention, deletion and access policies before any live pilot; values remain pending, not invented.
- Persist policies, approvals, preferences, queued work and receipts across reload/restart. Recovery cannot silently resend.
- Never claim inherited Razorpay infrastructure certifications or production platform access.

No live rollout is authorised by PRD approval alone. Account access, provider-specific requirements and actual integration tests remain prerequisites.

## 11. Failure and recovery matrix

| Failure | Behaviour | Merchant evidence/recovery |
| --- | --- | --- |
| Stale stock/price or changed terms | Refresh/block and reconfirm | Source time, changed terms, refresh action |
| New purchase after approval | Cancel affected outreach | Order evidence and exclusion |
| Missing consent/revoked connector | Block dependent action | Specific missing permission; reconnect/review |
| Missing margin costs/ineligible offer | Withhold incentive | Missing inputs or provider reason |
| Ambiguous reply/date or poor transcript | Clarify | Customer wording and unresolved field |
| Provider definite failure | Persist failure; safe bounded retry only when allowed | Receipt/error and retry eligibility |
| Provider timeout/unknown send | Status lookup; no blind repeat | Unknown state and reconciliation owner |
| Duplicate/unordered event | Idempotent processing; preserve valid newer state | Duplicate receipt/correlation |
| Campaign coordination unavailable | Pause affected outbound | Dependency failure and repair |
| Unmatched payment/order | Reconcile; do not count purchase | Both references and exception owner |
| Model outage | Continue deterministic safety/events; pause discretionary work | Degraded mode and recoverable queue |
| Support provider unavailable | Keep sales blocked and own exception | Handoff pending, owner and next step |

## 12. Analytics and measurement definitions

Net sales = sales after discounts and refunds, with a consistent merchant-defined tax treatment. Net contribution = net sales − product − fulfilment − payment − communication − agent costs. State the accounting basis; avoid subtracting an already netted discount twice.

Repeat-order rate uses a declared assigned customer cohort, qualifying subsequent brand orders and a declared measurement window. Journey-stage conversion and same-SKU outcomes can be supporting drilldowns; they do not replace brand-wide outcome measurement. Show denominator and window for every rate.

Incremental contribution/customer = average contribution of eligible customers assigned to agent − average contribution of eligible customers assigned to comparison. Include all assigned customers and their brand orders, including orders outside agent links. Use a common eligibility pool, comparable/randomised assignment where feasible, coordinated campaigns, multiple relevant repeat cycles and matured returns. Record policy/model changes and report uncertainty.

Merchant time saved requires measured intervention time and a comparable baseline; otherwise report observed intervention time and mark savings unmeasured. Complaints/opt-outs use distinct customer counts; failure metrics distinguish blocked prevention from executed errors. Contact/discount costs are tied to receipts and accounting inputs.

## 13. Demonstration dataset and required scenarios

Use the existing fictional household-goods merchant and laundry-liquid SKU unless changed by the owner. Fixtures use synthetic identities, delivered purchase histories, sparse history, permitted channels, opt-outs, unresolved issues and stock/offer edge cases. Stable timezone-aware scenario dates and reset controls apply only to synthetic data.

| ID | Demonstration | Evidence required |
| --- | --- | --- |
| DEMO01 | Customer requests a later reminder | Natural reply, clarified date/channel, persisted reminder, cancelled overlap |
| DEMO02 | Voice customer confirms same product and requests checkout | Labelled audio mode, transcript, confirmed SKU/quantity, permitted handoff, valid checkout |
| DEMO03 | Purchase detected outside agent link | Trusted brand order/payment evidence, cancelled outreach, outcome counted once |
| DEMO04 | Support issue | Sales stopped, support receipt or owned failure, no substitute sales |
| DEMO05 | Opt-out | Immediate persisted suppression and cancelled queued work, including while paused |
| DEMO06 | Review-first | Action held, reviewed exact version, receipt only after approval |
| DEMO07 | Pause and takeover | Blocked new dispatch, visible owner/state, safe resume/handback |
| DEMO08 | Blocked action | Unauthorised offer or missing required facts/costs, reason and recovery |
| DEMO09 | Purchase updates activity, learning and analytics | Shared verified evidence, persistence and consistent calculations |

Each demo must declare which parts are simulated, test or live. A complete labelled hybrid demonstration is different from an entirely live integration; both inventory and limitations must be explicit.

## 14. Validation and release gates

Before calling the implementation complete, verify every F01–F18 acceptance condition, all required demo scenarios and the older specification's AC01–AC22 safety matrix. Validate exact action approval, concurrency, provider timeout recovery, duplicate/unordered events, revoked permissions, missing costs, browser false-success claims, restart persistence and tenant isolation.

Evaluate intent/action correctness with adjudicated compound replies, ambiguous dates, opt-outs, complaints, product dislike and prompt injection. Compare with a deterministic branch baseline. **Zero prohibited action execution in the release evaluation is a gate**; an average language-quality score cannot compensate for an unsafe write.

Visually inspect revised setup, operator overview, plan review, conversation/action detail and analytics. Record actual viewport/keyboard/text-size checks and unresolved defects. Proposed responsiveness targets: visible local-action feedback within one second; useful text response or actionable failure within ten seconds. These are to be measured; voice targets await provider/mode selection.

An integration is complete only after real adapter capability, permissions, receipts and failure behaviour are verified in its declared mode. Fixture outputs and static badges cannot satisfy provider integration acceptance.

## 15. Delivery sequence

1. Approve PRD scope and resolve consequential open decisions. Keep current preview reviewable in frontend and backend boundary explicit.
2. Refine merchant UX and inspect the required screens/states.
3. Build authentication/persistence, fixtures, connector contracts, policy versioning and deterministic action validator.
4. Build opportunities, audience/plan approval, durable scheduling and shared contact coordination.
5. Implement commerce/payment verification and support/suppression, with declared available modes.
6. Add contextual WhatsApp and browser voice using the same validated action tools.
7. Finish supervision, audit/recovery, learning and analytics; run the release matrix and demonstrate all journeys.

This is delivery order for the complete scope. No dates or cost estimates are committed until access/stack choices are made. The owner deploys; publishing, customer outreach and real money movement require their specific authorisation.

## 16. Decision register for approval

| ID | Decision | Recommendation | Status/dependency |
| --- | --- | --- | --- |
| D01 | Integration depth | Hybrid: real persistent agent/test adapters where available, clearly labelled simulations elsewhere | Pending account access; do not remove full journey |
| D02 | Commerce/payment path | Native Shopify checkout with Razorpay test payments if compatible | Pending store/gateway verification; labelled prototype commerce fallback requires owner selection |
| D03 | Voice demonstration | Browser microphone/audio with transcript | Recommended by latest scope; AI/speech provider pending; phone provider separate |
| D04 | AI/speech provider | Provider-neutral domain tools; select after capability/cost/latency checks | Pending selection; no credentials available |
| D05 | App framework/database | Frontend and modular backend with durable transactional state | Specific stack pending; folder split makes no framework commitment |
| D06 | Hosting | Select after stack/provider/access decision | Pending; owner deploys |
| D07 | Live permissions/retention | Explicit scopes, consent and merchant-authorised transcript/recording policies | Pending before live pilot |
| D08 | Economic/contact limits | Merchant-configured values and verified accounting inputs | Pending fixture/pilot values; no invented defaults imply approval |
| D09 | Repository | Private project repository in owner's GitHub account | Creation/upload depends on authentication/access; no public brief publication |

PRD approval can approve F01–F18 and the acceptance requirements while leaving D01–D09 unresolved. Implementation must not silently interpret PRD approval as a provider/hosting choice or live-action authorisation.

## 17. Risks and dependencies

Shopify/Razorpay checkout compatibility and account availability may limit test execution. Voice audio, telephone automation and WhatsApp business conditions have separate dependencies. Delivery/support evidence and external campaign coordination may require additional adapters. Incomplete costs restrict contribution reporting. Sparse histories limit timing precision. Real causal lift needs sufficient pilot evidence and a valid comparator.

Verify current official provider documentation before integration; this PRD defines desired behaviour and does not assert that provider-specific APIs or private Agent Studio capabilities are available. Existing references are research starting points, not newly verified compatibility evidence.

## 18. Approval record and source precedence

| Field | Value |
| --- | --- |
| Version submitted | 2.0, 12 October 2026 |
| Scope requested | Full 18 features and required demos, same-product current execution |
| Approval requested | Scope, behaviour, UX requirements, acceptance/release criteria and proposed boundaries |
| User decision | Approved to proceed; discuss design next |
| Approved by/date | Project owner, 12 October 2026 |
| Changes requested | None at approval; design discussion follows |

Sources, in precedence order: latest user-supplied feature list in `user-feature-scope.txt`, latest explicit owner decisions, this PRD once approved, `HANDOFF.md`, then `product-specification.md` for supporting detail. `ux-next-pass.md` guides design refinement; `references.md` holds earlier public references. The original v1 specification is retained for traceability, including its acceptance matrix, rather than overwritten.
