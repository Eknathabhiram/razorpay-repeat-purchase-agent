# Repeat Purchase Agent — merchant experience design v3

13 October 2026 · Proposed design for owner review · Application implementation is pending design review.

**Latest owner feedback:** [D2C scale and WhatsApp interactions — revision 2](D2C-SCALE-AND-WHATSAPP.md) supersedes this document's tiny aggregate fixtures and three-tab navigation. The revised navigation is Dashboard / Activity / WhatsApp interactions / Settings, with grouped cohort operations and a merchant conversation workspace. Core approval, evidence and customer-control requirements below remain applicable.

The owner requested a senior UI/UX architecture and PM review grounded in Razorpay, then explicitly instructed: show design changes before coding. This deliverable contains visual concepts and a design specification. It changes no application or backend code. It preserves the approved full 18-feature journey.

## Design decision

Organise the product around the merchant's decisions: **what needs attention, what happened with customers, and what results can be trusted**. Keep the familiar payments/Agent Studio shell. Within the agent use Dashboard / Activity / Settings. Audience, messages, checkout, voice, learning and reconciliation remain full capabilities, opened from their relevant task instead of competing permanent module tabs.

The current implementation has grown around planning, execution, WhatsApp, intelligence, commerce and outcomes modules. Those are useful engineering boundaries. The proposed navigation connects them into one merchant journey.

## Concepts for review

All data, amounts, people, dates and checks in these images are synthetic design fixtures. The plan and message screens illustrate different journey moments; they are not one synchronized application state. These are raster design concepts, not evidence of implemented interaction, measured accessibility, private Razorpay dashboard fidelity or marketplace certification.

1. [Dashboard](dashboard-concept.png): decisions lead, customer activity follows, observed results sit below. Compact policy and source context stays alongside the task.
2. [Audience review](audience-review-concept.png): selected customers, reason, timing, exclusions and approval boundaries are visible together. One selection control per customer. Plan approval and message approval stay separate.
3. [Message review, desktop and mobile](message-review-concept.png): customer words precede the proposed message; commercial facts, permissions and operating checks are available before the pinned approval action.

Exact copy and behaviors below govern implementation. Raster concepts illustrate composition; their small labels are not an immutable copy specification.

## Grounding in official Razorpay material

| Official source | Principle used | Design consequence |
| --- | --- | --- |
| [Agent Studio principles and guardrails](https://razorpay.com/blog/razorpay-agent-studio-principles-guardrails-and-merchant-control/) | Merchant boundaries, explicit authority, validated facts, consent, permitted offers and action traceability | Show what approval permits; keep pause/takeover visible; attach price, stock, permission and receipt evidence to actions |
| [Agent Studio product page](https://razorpay.com/agent-studio/) | Specialist agents within merchant operations, review and connected sources | Preserve discovery/install/operating journeys and recognizable Studio context |
| [Blade official repository](https://github.com/razorpay/blade) and [component documentation](https://blade.razorpay.com/) | Razorpay's component system, accessible semantics, documented design decisions | Use consistent buttons, fields, navigation, review surfaces and disclosure; map to supported Blade components during implementation |
| [RazorSense](https://razorpay.com/razorsense/) | Purposeful state expression and contextual feedback | Give pending, paused, blocked and confirmed states distinct text and restrained emphasis; motion follows real state changes |

Public marketing copy and the principles article describe review-first differently. Use review-first as the proposed default; bounded execution remains an explicit approved product policy. Do not infer private platform capabilities from those pages. The visual tokens here are proposed, not verified official Blade token values. Prior shell observations are preserved references, not proof of today's private dashboard layout.

Razorpay's statements about its infrastructure, certifications and data residency do not establish those properties for this independent application. In particular, an external Together AI integration requires its own truthful source/access disclosure. No interface should imply Razorpay certification or that all data stay inside Razorpay merely because the shell is familiar.

## Product architecture

| Merchant area | Main job | Contextual destinations |
| --- | --- | --- |
| Dashboard | Resolve the next decision and understand current operation | Review audience; review message; assign issue; resolve uncertain attempt; open observed outcomes |
| Activity | Follow one customer across channels, receipts and commercial evidence | Customer detail; transcript; takeover; reminder; support; suppression; checkout/payment timeline |
| Settings | Define authority and operating limits | Product scope; channels and permissions; hours/caps; budget; approved offers/cost requirements; execution mode; version comparison |
| Shared Connections | Understand source readiness and recover access | Actual source mode; scope; last successful verification; missing capabilities; recovery |
| Agent detail / installation | Decide whether to install and configure access | Configure → Connectors → Review → Activate; activation does not approve outreach |

Customer records are the organizing object. WhatsApp, voice and model interpretation are events/capabilities within that journey. Customer-facing history does not become a separate transcript silo for every provider.

## Dashboard hierarchy

1. Show actual workspace mode and agent state independently. An agent may be paused in Demo or Development; mode is not health.
2. Lead with a ranked decision queue: customer safety/suppression and uncertain provider outcomes; unresolved source/approval blockers; ready messages; new audiences; suggested policy learning. Rank by consequence, not invented urgency.
3. Promote one leading decision. Remaining decisions are compact rows with reason, consequence and one contextual action. An unknown delivery attempt offers inspect/reconcile rather than a blind resend.
4. Follow with customer journeys: customer words or evidence basis, current state, relevant timestamp and the next action. No unverified propensity scores or percent confidence.
5. Show observed orders, revenue basis and cost completeness below operational work. Contribution stays unavailable when costs are missing. Incremental lift stays unmeasured until an appropriate comparison exists.
6. Keep operating limits concise: product, permitted hours, shared contact cap, spending ceiling, offers and policy version. Source readiness shows actual capability exceptions rather than a decorative all-green connector grid.

First use has setup progress, missing capabilities and a next setup action. Returning use has decisions and actual journeys. An empty returning dashboard says no decisions are waiting and shows the next confirmed scheduled work, when such work exists; it does not fabricate activity.

## Audience approval

Display selected eligible customers, exact variant, evidence reason and proposed contact time. A customer-confirmed date is distinct from a historical estimate. Exclusions remain visible with reasons, and opted-out/missing-permission records have no force-include action.

The boundary summary contains product/channel scope, quiet hours, shared contact cap, spend ceiling, offers, policy version, expiry and execution mode. The reviewed backend object binds the exact revision and selected IDs. Changing products, timing, selection, offers or other authority invalidates the affected approval.

The primary label is **Approve plan for N customers**. Zero selected disables it. In review-first, approval prepares proposed contact; outgoing messages still require exact-message approval. In bounded execution, the interface must explicitly describe the exact approved actions that can run within limits. Installation alone never authorises either.

At approval, recheck the facts and display changed/removed customers or limits when the review became stale. Preserve draft edits through an error. Never show success until the authoritative receipt is available.

## Customer detail and exact-message review

Order information by decision value:

1. Alias, journey state, owner, product and source mode.
2. Actual customer words with channel/time and an inspectable transcript.
3. The exact proposed message and its destination/channel.
4. Same variant, quantity, current stock and full payable terms. Distinguish charges verified now from those not yet available.
5. Current channel permission, contact/budget state, current plan and approval expiry.
6. Receipt/history details, revealed on demand.
7. A pinned footer with the primary contextual action; secondary takeover/rejection as appropriate.

**Approve & send message** authorises the displayed content only. Before approval, the check copy is **Plan approval is current**, not “message approval current.” The message remains awaiting the merchant's decision. If the journey is paused, suppressed, owned by someone else, stale, out of stock or beyond limits, replace or disable the send action and state the precise recovery route.

Takeover assigns control and prevents competing agent actions; closing the drawer does not hand it back. Handback requires current source/permission checks. Message acceptance, delivery, read, customer response, checkout, captured payment, matched order, fulfillment and delivery remain separate states.

## Commercial and communication rules

- Same previously purchased variant remains the execution scope. Quantity changes require customer confirmation and freshly checked terms.
- Current prices, stock, payable amount and payment truth come from authoritative sources. Model-generated interpretation never supplies those facts.
- Approved offers are off unless enabled; show the existing offer reference, eligibility and limits when used. Silence never triggers an incentive or a voice escalation.
- Voice consent and WhatsApp permission are independent. Customer confirmation of a WhatsApp handoff is tied to its specific use, not permanent marketing permission.
- Resolve ambiguous dates, quantities or compound intents through a specific confirmation step. An unresolved complaint blocks sales progression.
- Opt-outs suppress marketing promptly and cancel competing queued work, including while the agent is paused. No recovery path overrides an opt-out.
- A payment link is not payment. Financial views identify the accounting basis, refunds, delivery status, return maturity and unknown costs.

## Visual system and responsive behavior

Use the established dark payments header, neutral white sidebar and quiet gray canvas. Blue is reserved for merchant action/selection, teal for customer-confirmed timing and positive receipts, amber for attention, red for a genuine block/error. Every state includes text; color never carries the meaning alone. Avoid decorative AI sparkles, proprietary RazorSense glyph imitation and invented sub-brands.

Proposed spacing uses 4/8/12/16/24/32 px steps; desktop page gutters 24–32 px. Body text is 14–16 px and secondary operational copy is at least 12 px. A 24–28 px page title, 16–18 px section titles and consistent 400/500/600 weights create hierarchy without promotional headlines. Use tabular figures for aligned money/time values.

Wide desktop: one primary work column and a smaller contextual boundary column. Tablet: stack the boundary summary; retain normal reading order. Mobile: keep essential actions visible, make customer rows self-contained, and use a full-screen detail surface with independently scrolling content and a fixed action footer. Primary control targets are at least 44 px. Primary navigation must remain operable with keyboard, visible focus and an accessible mobile menu.

Map these roles to verified current Blade components/tokens during implementation, after checking React compatibility. A custom CSS imitation is not a claim of native Blade usage. Contrast, 200% zoom, screen-reader operation, reduced motion and mobile keyboard/viewport behavior must be tested on the coded design before any accessibility claim.

## Failure and empty states

| State | Merchant explanation | Available next action |
| --- | --- | --- |
| Missing source or consent | Name the specific fact/capability that prevents this action | Review source evidence; affected outreach stays blocked |
| Stale plan or message | State what changed and why prior approval no longer applies | Review the refreshed version |
| Offline or failed refresh | Identify last loaded data and unavailable updates | Refresh; preserve edits and prevent stale approvals |
| Unknown transport outcome | Explain uncertainty without claiming failure/delivery | Inspect/reconcile receipt; do not offer blind retry |
| Paused | New outreach stops; protective events and receipts still update | Review resume checks |
| No eligible audience | Show reasoned exclusions and missing evidence | Resolve permissible source gaps; never override opt-out |
| No matched purchase | A checkout exists, but no trusted payment/order match exists | Inspect evidence; do not invent revenue |
| Missing costs or immature returns | Name unknown inputs and provisional basis | Inspect source/accounting details |
| Viewer access | Explain read-only role at the attempted action | Authorized owner/operator handles the change |

## Full feature coverage

| Approved feature | Proposed home |
| --- | --- |
| F01 entry/navigation | Payments shell and Studio discovery; local application auth stays honest |
| F02 installation | Four-step Configure / Connectors / Review / Activate |
| F03 connections | Shared Connections and contextual source exceptions |
| F04 policy | Settings and approval-boundary summaries |
| F05 repeat opportunity | Contextual audience review and evidence drawer |
| F06 eligibility/suppression | Audience exclusions and customer/action guard checks |
| F07 plan approval | Dedicated audience review |
| F08 WhatsApp | Cross-channel Activity/customer detail |
| F09 voice | Customer transcript/audio and explicit intent confirmation |
| F10 shared coordination | One journey, shared limits and visible ownership |
| F11 checkout/purchase verification | Message review and commercial evidence timeline |
| F12 approved offers | Conditional commercial review and Settings |
| F13 reminders/support/opt-out | Customer detail and protective decision queue |
| F14 supervision | Persistent pause; contextual review/takeover/handback |
| F15 audit/recovery | Detail receipt/source disclosure and blocked-action queue |
| F16 outcomes/economics | Dashboard observed summary → Outcomes drilldown |
| F17 learning | Customer-confirmed preferences and explicit policy-change review |
| F18 future evolution | Roadmap context only; no executable alternatives/cross-sell |

## PM acceptance before implementation completion

Review the screen concepts first. On implementation, evaluate whether merchants can: identify the most consequential decision; describe exactly what a plan/message approval permits; distinguish a confirmed reminder from an estimate; distinguish a sent link from a purchase; explain why an opted-out customer cannot be included; find pause and takeover without learning engineering modules.

Proposed usability gate: representative growth owners and operators complete those tasks without coaching. Record completion, misinterpretations, recovery difficulty and time to complete; establish benchmarks from observation instead of inventing performance targets. An authority or payment-state misunderstanding is a release blocker. Merchant time saved and business lift need independent evidence, not visual-design claims.

After design approval, implement in a separate worktree with stable contracts, preserve the complete current pipeline, keep demo controls outside the normal operating flow, and validate first-use/active/paused/empty/disconnected/stale/unknown-outcome states. This review does not authorise live customer outreach, provider writes or deployment.

## Generation provenance and final prompt set

Visuals were produced with the built-in ImageGen tool. The existing dashboard screenshot was a shell/style reference; no official private dashboard screenshot was supplied.

- **Dashboard:** high-fidelity flat Razorpay-style merchant shell; three operating tabs; ranked two-item decision queue before activity/results; truthful Demo sources; compact operating limits; no fabricated uplift or certification.
- **Audience:** same shell/style; selected customers with evidence and confirmed/estimated timing; two selected/two excluded; exact policy limits; separate plan/message authority. Final edit: one left-side checkbox per row, remove the duplicate Selected column, and schedule Rahul for 14 Oct at 10 am IST.
- **Message review:** desktop contextual drawer and mobile full-screen counterpart; customer words, exact message, synthetic commercial terms, current checks and a pinned action footer. Final edit: say Plan approval is current; the message itself remains awaiting approval.

These prompts and the specification define a coherent direction. The next deliverable is implementation only after the owner reviews this design.
