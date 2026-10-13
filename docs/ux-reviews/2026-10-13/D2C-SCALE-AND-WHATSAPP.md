# D2C scale and WhatsApp interactions — design revision 2

13 October 2026 · Proposed design only · Application code remains outside this design revision.

The owner liked the visual direction and requested two changes: represent a D2C brand's substantial customer volume, and add a WhatsApp interactions tab showing actual message choices before free-flow conversation. The owner confirmed the merchant conversation workspace: inbox on the left, selected message thread on the right.

This revision supersedes the original three-tab navigation and tiny aggregate counts. The previous customer-detail concept remains relevant: one selected customer's context and exact-message review are still individual tasks within a large operation.

## Revised screens

- [D2C dashboard](revision-2/dashboard-scale.png)
- [Audience review at scale](revision-2/audience-scale.png)
- [WhatsApp merchant workspace](revision-2/whatsapp-interactions.png)

All volumes, names, dates, replies, checks and commercial amounts are synthetic examples. The images are raster design proposals, not implemented interactions or proof of backend capacity. A few visible rows represent a larger paginated dataset.

## Navigation

**Dashboard / Activity / WhatsApp interactions / Settings**.

Dashboard prioritizes grouped operational decisions and cohort state. Activity records the complete customer journey across channels, commercial evidence and receipts. WhatsApp interactions provides a focused conversation inbox and message/choice history, using the same customer identity, permissions, ownership and contact ledger. Settings controls products, channels, hours, contact limits, approved offers, budgets and versioned policies. Connections remains shared Studio navigation.

## Large-volume operation

Separate the total historical customer base, current eligible candidates and the exact selected/approved cohort. The illustrative design uses 128,400 historical customers, 12,480 eligible candidates and an approved cohort of 9,600. Eligibility is never inferred from total customer count.

The illustrative cohort's mutually exclusive current states are:

| State | Customers |
| --- | ---: |
| Scheduled | 3,799 |
| Awaiting reply | 3,860 |
| Confirmed reminders | 940 |
| Checkout pending | 460 |
| Needs message review | 184 |
| On hold | 45 |
| Matched orders | 312 |
| Total | 9,600 |

The 45 held journeys comprise 36 support issues and 9 uncertain dispatch outcomes. Those 45 decisions plus 184 message reviews make 229 items awaiting attention. Candidate exclusions are a separate population: 910 missing permission + 720 recent purchase + 286 support holds + 160 unavailable stock = 2,076 excluded candidates. Candidate exclusion counts and holds within an already assigned cohort have different denominators; the coded UI must label their scope.

The inbox illustration uses 5,801 conversations, the cohort excluding 3,799 scheduled customers who have not yet entered a conversation. Real counters must use backend-defined scopes; suppressed/historical threads remain searchable and must not be silently lost when current eligibility changes.

### Interaction requirements

- Group work by plan, product, message and exception reason. Aggregate counts lead; representative customer rows are drilldowns.
- Search by customer, order or SKU; filter by state, plan and evidence reason; use backend pagination. Rendering 25 rows does not mean the brand has 25 customers.
- Distinguish **Select this page** from selecting across all eligible results. Keep selected count visible when navigating or filtering. An immutable review binds the selected IDs, facts, timing and limits across all pages.
- Grouped review is an inspection convenience. It never authorizes unseen expanded scope or bypasses exact-message review in review-first mode. If batch approvals are supported later, every recipient, rendered message and approval revision must remain inspectable and individually bound.
- A plan approval for 9,600 people does not submit 9,600 provider requests at once. Rate limits, contact windows, current facts, customer responses, suppression, provider capacity and budget guards govern dispatch.
- No fabricated revenue, contribution or uplift is derived from customer volume. In the mockup, net revenue remains unavailable and incremental lift remains unmeasured.
- Support large data without sacrificing keyboard/focus behavior. Use stable selection and explicit loading/stale/error states; avoid giant client-side lists or aggressive polling of entire cohorts.

## Meaning of the ₹25,000 cap

**₹25,000 was introduced only as an illustrative maximum outreach budget. It is not an owner-approved or changed application setting.** The conceptual budget covers contact costs for the reviewed plan, such as WhatsApp delivery and permitted voice usage. Approved-offer discount exposure is separate and remains off in these examples.

The authoritative policy must define the amount, currency, period and included costs. Prefer the visible label **Outreach budget · per plan**, with the actual merchant-configured value. The image's shorter “spend ceiling” label is provisional. New contact reservations must remain within the applicable budget; an uncertain attempt keeps its exposure held until reconciled. A cap is neither actual spend nor a guarantee of provider billing. Missing or unverified costs cannot be silently treated as zero.

## WhatsApp merchant workspace

The left pane contains searchable, paginated customer conversations, latest actual message/event, timestamp, ownership and state. Filters include message review and on-hold journeys. Selecting one customer opens the same cross-channel journey used by Activity.

The right pane leads with customer identity, product, owner, source mode and service-window state. It displays sent business text, the button choices that accompanied it, actual received button/text replies, and receipt status. A proposed response appears in a distinct **Not sent** review surface, never as a sent bubble with delivery ticks.

The default merchant view has no empty unrestricted composer. Its next action is **Review & approve** for a pending exact message. **Take over** enables an authorized human composer, subject to pause, channel permission, provider window/template, contact and spend checks. Closing a thread does not hand it back to the agent.

Customer buttons are represented as read-only message evidence in the merchant workspace. Clicking a preview there must never fabricate an inbound customer reply. Explicit Demo replay belongs to separately labelled simulation controls.

## Customer message patterns

Buttons are the preferred path; customers can still ask questions or state intent in ordinary WhatsApp text. The native customer's composer remains available. No interaction should reject a genuine typed request merely because a button existed.

| Moment | Proposed customer message | Reply choices | Result |
| --- | --- | --- | --- |
| First reorder invitation | “Hi Rahul, would you like to reorder your laundry liquid, 1 L? Choose below, or type a question. Reply STOP to stop reorder updates.” | Reorder / Remind me later / Get help | Record the selected intent and apply the corresponding journey checks |
| Same-item confirmation | “Would you like the same variant and quantity? Laundry liquid · 1 L · quantity 1.” | Same item × 1 / Change quantity / Not now | Confirm the exact item/quantity; changes require a fresh customer confirmation and commercial quote |
| Reminder date | “When would you like a reminder? You can choose a date below or tell us another date.” | Fri, 16 Oct / Tue, 20 Oct / Choose a date | Confirm the complete date, year, time, timezone and permitted channel before saving |
| Typed price question | Customer: “Does the price include delivery?” Proposed response: “For this checkout, the item is ₹499 and delivery is ₹40. Total ₹539; taxes included.” | Get checkout / Remind me later / Get help | Use fresh authoritative terms; these amounts are synthetic examples, not standing prices |
| Offer enquiry | “I can check existing approved offers for this item. I won’t change the price or create a discount.” | Check offers / Reorder / Not now | Return only eligible approved evidence; no pressure after silence |
| Support route | “What do you need help with?” | Delivery issue / Product issue / Other help | Capture the issue, stop sales progression and route to an owner |
| Clarification | “I want to make sure I understood. Did you mean another bottle of the same item?” | Same item / Something else / Get help | Resolve ambiguity; unsupported alternatives are not silently substituted |
| Opt-out | Customer: “STOP.” A permitted acknowledgement may say: “You won’t receive reorder updates. Scheduled reorder outreach has been stopped.” | No sales reply buttons | Apply suppression promptly; no further reorder persuasion |

All interactive examples use no more than three quick replies per message and titles shorter than 20 characters. Choices that propose different dates must be followed by explicit date/time confirmation. “Not now” ends the current reorder progression; STOP and equivalent explicit opt-outs have their appropriate persistent suppression scope. Silence triggers neither an invented reminder nor automatic voice escalation.

Free text remains part of the full experience: price/offer questions, complaints, changed quantity, alternative dates and compound requests. Preserve all material intents. Protective requests are processed before proposing another sales action; ambiguity is clarified rather than guessed. A button click is not permission to widen marketing scope.

## Provider grounding

[Twilio quick-reply documentation](https://www.twilio.com/docs/content/twilio-quick-reply) supports button responses and distinguishes three-button in-session messages from larger approved-template configurations. Titles are text; do not implement decorative icon drawings as unsupported native button controls. Preserve the provider's signed inbound button payload and message context, rather than treating a browser click as a customer event.

[Twilio WhatsApp concepts](https://www.twilio.com/docs/whatsapp/key-concepts) define the 24-hour window from the last inbound customer message and require approved templates outside that window. Reorder outreach must use the appropriate approved category and consent; an initial promotional reorder message cannot be relabelled utility simply to avoid requirements. Exact provider template/button capabilities and costs must be verified for the connected account during implementation.

The window status, template status, opt-in, ownership, source facts, limits and receipts must be factual. The concept's green/blue states do not establish a live provider connection. Checkout messages retain separate approval, and a sent link never establishes a captured payment or matched order.

## Mobile behavior

Show the inbox first and open the selected thread as a full-screen surface with an accessible Back control. Keep the next review/takeover action pinned while the conversation scrolls. Customer button choices remain readable, transcripts retain chronology, and the Not sent draft remains visibly separate. Large cohort selection uses the same explicit cross-page scope and a fixed selected-count summary.

## Acceptance before coding

Review these revised concepts before implementation. Verify that a merchant can distinguish historical base/eligible/selected cohorts; review cross-page selection without losing authority scope; understand button responses and free text; identify an unsent draft; find the reason for a blocked send; take over without bypassing guardrails; and explain the configured budget period and included costs.

Built-in ImageGen produced the concepts. Final prompt set: preserve the accepted Razorpay-style visual direction; replace tiny aggregate fixtures with distinct high-volume cohort scopes; add the fourth WhatsApp interactions tab; display a merchant inbox and real message/quick-reply history; keep optional free text and human takeover; remove decorative native-button icons; correct inbox scale and preserve unsent-message status. Application implementation remains pending design review.
# Implementation update

The owner's later decision supersedes routine per-message approval in the conceptual examples below: approve the audience, reply style and limits once, then automate routine conversations, confirmed checkout and reminders within that authority. Merchant involvement is limited to exceptions. The implemented Demo uses the owner's requested 200-customer dataset, city/date filters and actual backend counts. See [the implementation and verification notes](IMPLEMENTED.md).

