# Repeat Purchase Agent — final UI/UX implementation handoff

Version 1.0 · 12 October 2026 · Intended implementer: GPT-6.1-sol, low reasoning effort

**Design direction: considerate replenishment.** A familiar Razorpay operating environment containing a specialist that understands when a customer is ready, knows when to wait, and leaves evidence for every action. Its identity comes from the way it makes decisions visible and respects customer timing.

This is the implementation-ready design specification, not a claim of production approval, usability research or completed integration. Product requirements are approved in `PRD.md`. This design handoff was requested by the owner; any subsequent owner feedback takes precedence. Do not begin integrations or resolve undecided providers/hosting as a side effect of UI work.

## 0. Read order and deliverables

1. `../AGENTS.md`, `../HANDOFF.md`, `PRD.md` and `user-feature-scope.txt`.
2. This document: final design decisions, behaviours and implementation gates.
3. `../frontend/design-handoff.html`: inspectable reference for five key desktop/mobile compositions and local demo interactions. All data/actions are synthetic. It is a design reference, not the final application.
4. `../frontend/design-tokens.css`: concrete proposed tokens, distinct from official Blade values.
5. `design-evidence.md`: evidence/provenance and limitations.
6. `design-qa.md`: actual reference checks and remaining application checks.

Existing `../frontend/index.html` and `../frontend/src/design-preview.fragment.html` retain the original journey. Refine their implementation after this handoff without removing entry, installation, supervision, analytics or failure states. Keep an editable source and standalone export coherent. Do not replace a working full journey with the five-screen reference alone.

## 1. Reference grounding and provenance

| Foundation | Evidence | Application | Evidence limit |
| --- | --- | --- | --- |
| Blade | Official [repository](https://github.com/razorpay/blade) identifies Razorpay's design system | Consistent fields, buttons, tabs, drawers, tables, semantic states and spacing; use verified Blade components if the eventual stack supports them | Package APIs/tokens must be checked at implementation; proposed CSS below is not official Blade |
| Agent Studio | [Public platform page](https://razorpay.com/agent-studio/) | Specialist-agent discovery, connected sources and visible merchant control | Marketing page, not private UI or SDK contract |
| Agent authority | [Principles and guardrails](https://razorpay.com/blog/razorpay-agent-studio-principles-guardrails-and-merchant-control/) | Explicit boundaries, reviewable actions, current source facts, audit receipts and pause | Do not inherit platform access/security claims into our prototype |
| RazorSense | [Design language](https://razorpay.com/razorsense/) | Distinct calm, pending, caution and completion states; purposeful response/motion | Public philosophy/examples, not a complete product token specification |
| RAY | [Conversational dashboard](https://razorpay.com/blog/razorpay-agentic-dashboard-your-dashboard-just-conversational-with-ray/) | Contextual questions reveal an evidence/action object in place | Inspiration; no dependency on RAY or claim our agent runs on it |
| Prior walkthroughs | LinkedIn URLs in `references.md` and previous handoff observations | Black payments header, dashboard sidebar, Home/My Agents/Connectors, four-step install modal, Dashboard/Activity/Settings, activity drawer | Prior-session observation. Videos could not be retrieved on 12 October; pixel values and current private layouts are unverified |

Existing specialist patterns inspire functions, not copied layouts: cart recovery connects context to an action; subscription recovery uses conversation at a relevant moment; dispute response makes the evidence/draft reviewable. Our contribution is customer readiness, respectful deferral, cross-channel continuity and honest profitability evidence. Existing agents' marketing performance numbers must never appear in our metrics.

The public page describes review-first broadly while the principles article describes it as configurable. Our PRD supports review-first and bounded execution; expose both as **our proposed execution modes**. Do not assert actual Razorpay platform support for bounded mode until verified.

## 2. Final design decisions

| Decision | Final choice | Reason |
| --- | --- | --- |
| Overall experience | Decision-led operating dashboard with contextual AI assistance | Merchant can scan pending work and retain direct controls |
| AI surface | Embedded explanations and a constrained “Ask about this” panel | Questions stay attached to the plan/journey/evidence being discussed |
| First screen after setup | Needs your decision → customer journeys → verified outcomes | Moves attention from feature inventory to merchant work |
| Default execution mode for first setup | Review-first preselected; bounded mode is an explicit choice | Builds confidence; preserves both approved product modes |
| Visual character | Neutral surfaces, disciplined blue actions, teal emphasis for customer timing | Familiar payment-tool clarity with a distinctive replenishment language |
| Installation | Keep four-step modal and vertical step list | Preserve prior observed Studio pattern |
| Top navigation | Keep Home/My Agents/Connectors; operating tabs Dashboard/Activity/Settings | Avoid adding competing permanent navigation |
| Analytics | Dashboard link/section opens an Outcomes view inside the agent | Existing product area; no extra global navigation |
| Opportunity authoring | Review a concrete plan, not an agent-feature wizard | Approval has a clear scope and consequence |
| Changes | Show before/after diff, invalidate stale approval and require review | Agent adaptability stays legible and bounded |
| Distinctiveness | Repeat window, customer-word-led explanation, adaptive journey timeline | Original interaction grammar grounded in the approved product |

Alternatives considered: a chat-first dashboard would hide the audience and approval scope; a dense KPI dashboard would underplay pending decisions; a separate canvas of autonomous agents would introduce a second mental model. Use none of these as the primary composition.

## 3. What makes this AI-native

### A. An evolving plan with evidence

Each plan connects a suggested action to a customer reason, source freshness and operating boundary. Before approval show a concrete audience, schedule and offers. When the merchant changes timing or excludes someone, show the effect on scope and schedule rather than a generic saved toast.

Example: “Move contact to Friday” produces “12 Oct, 10:00 → 16 Oct, 10:00 IST” and “Previous approval no longer applies.” A model never executes a natural-language command directly. The deterministic form and review object remain the source of authorisation.

### B. A repeat window, not a propensity badge

For a due customer, show a compact time range: last delivered purchase → suggested repeat window → today or confirmed customer date. Pair it with “Based on two previous intervals” or “Product-level estimate; limited customer history.” A window communicates uncertainty; do not add an invented percentage score or assert product depletion.

On mobile, replace the graphic with a two-line dated statement. Window marks must carry accessible dates and basis. A requested reminder is shown as a distinct customer-confirmed date, not merged into the estimate.

### C. Customer words → understanding → action → receipt

In each journey, lead with the customer's words and show the concise interpreted request. Follow with verified facts, the proposed/completed action and its real receipt. This explains adaptation without exposing hidden model reasoning. A voice conversation and WhatsApp handoff occupy one chronological journey.

### D. Useful questions in context

“Why this customer?”, “What changed?” and “What is blocking this?” open deterministic evidence views first. Optional natural-language follow-up may summarise existing facts, but must carry scope/source links and a missing-evidence state. Editing/approving still uses the structured review object. Do not make a general merchant chatbot, conversational analytics engine or RAY integration a new delivery dependency.

### E. Learning that asks permission

Customer-confirmed dates/preferences update the journey visibly. Broader policy suggestions show evidence, proposed change and impact, with Review change. A one-off checkout handoff is not a permanent channel preference. No silent cap/offer/permission expansion.

## 4. Information architecture and routing contract

Logical view names are implementation-neutral; preserve them in URL/hash state where practical.

| View ID | Entry | Contains |
| --- | --- | --- |
| entry | Sample login/verification | Clearly simulated authentication and route to payments home |
| payments-home | Existing dashboard shell | Discover Agent Studio |
| studio-home | Home | Agent catalogue and Repeat Purchase detail |
| studio-my-agents | My Agents | Installed agent state and Open agent |
| studio-connectors | Connectors | Shared connectors with actual permissions/mode/health |
| install | Agent detail / Install | Four-step modal and connector permission subview |
| agent-dashboard | Open agent / Dashboard | Setup or operating overview, decision queue, journey summary, outcomes link |
| plan-review | Review plan | Concrete audience, evidence and schedule/limit changes |
| agent-activity | Activity | Filterable event/journey list and contextual drawer |
| journey-detail | Journey row | Transcript, evidence, approval, receipt, takeover |
| agent-outcomes | View outcomes | Observed brand orders, costs, maturity and learning |
| agent-settings | Settings | Versioned operating policy, execution mode and permissions |

The ask panel is a contextual overlay inside these views, not a new product destination. Analytics Back returns to Dashboard with prior context. Closing plan review restores its originating decision row. Persist filter/sort/selected plan state where helpful; browser Back closes the current route-level overlay before leaving the agent.

## 5. Layout and visual system

These are **proposed product values**, not extracted official Razorpay tokens. If a verified Blade equivalent differs slightly, use it consistently and document the mapping. Preserve information hierarchy and state meaning.

### Geometry

- Payments header: 56 px high. Product/sidebar: 208 px at ≥1024. Content padding 32 px desktop, 24 px tablet, 16 px narrow.
- Agent header: breadcrumb, title 28/36, one-line mandate, execution status/mode and visible Pause. Operating tabs below, separated by a neutral rule.
- At ≥1200: main content 2fr/1fr, 24 px gap. First decision spans the main column; a concise operating-boundary panel occupies the secondary column. Journey rows and outcomes follow.
- At 1024: keep shell, stack secondary panel under primary when the main area falls below 720 px. At 768: collapsible global navigation, one content column. At ≤480: 16 px gutters, full-width decision surfaces and overlays.
- Content maximum width 1280 px; align left inside available shell. Avoid stretching paragraphs beyond 65–75 characters.
- Card padding 24; rows 16 vertical; primary controls 40 px minimum desktop, 44 px narrow. Corner radii 8 control / 12 panel. Use at most one prominent outlined decision container per viewport; other content uses whitespace and dividers.
- Install modal width up to 960 px and max-height calc(100dvh - 48px), steps 200 px, footer persistent. At ≤767, step header above content, full-height panel and safe-area footer. Plan review can be a full content view; customer evidence opens a drawer without losing the plan.

### Type and colour

- System sans as offline fallback; use verified product font if available. Body/control 14/22; readable secondary 13/20; minimum labels 12/18; page title 28/36; section 18/26; metric 26/34. Weights 400/500/600. Tabular numerals for money/time/counts.
- Background #F6F8FB; surface #FFFFFF; ink #172B4D; secondary #52637A; border #DCE3EC; action #145CFF. Customer-timing teal #087F83, soft teal #EAF7F5; pending blue #EDF3FF.
- Success #146C43 on #EAF6EF; caution #7A4B00 on #FFF4DC; blocked #A32432 on #FFF0F1. Distinguish text roles from surface tokens. Verify final contrast rather than relying on these pairings as a compliance claim.
- Teal identifies confirmed customer timing/learning across views; blue identifies merchant decision/action. Colour always has a text label. A verified sample result remains labelled synthetic.
- Use one consistent icon set. Avoid emoji in merchant chrome, purple AI gradients, decorative sparkle badges, an invented Razorpay sub-brand or mimicry of RazorSense's proprietary glyph/flutes.

### Motion

Use 120–180 ms for focus/selection, 180–240 ms for drawer transition, and short finite state changes after confirmed events. With prefers-reduced-motion, remove translation and use immediate state updates. Processing state says what operation is pending; no fake token-streaming, endless decorative pulse or success before a receipt. Do not animate stationary lists continually.

## 6. Screen specifications

### S01 — First use and installation

Agent detail explains “Help returning customers reorder at the right time” and “Same previously purchased product. WhatsApp and voice. Merchant-approved plans.” Primary: Install agent. Display capability/access overview and mode limitations; do not display unsupported pricing/trial promises.

Configure groups essential choices first: repeatable products, review-first/bounded mode, permitted channels and contact schedule. Advanced offer/margin/budget inputs expand only when relevant. Show a sample-safe policy summary; do not invent permission defaults.

Connectors displays commerce, payments, WhatsApp, browser voice and support/delivery roles. For every source show actual mode/scopes/freshness. Connect opens the access subview, returning to the same step. Missing support/delivery evidence is a specific blocker even if another connector provides that role.

Review displays capabilities and access, policy values, unresolved dependencies and activation consequences. Activate produces installed/ready state. Final copy: “Agent installed. Review an audience before contacting customers.” Primary becomes Review opportunities. No contact jobs are created by activation.

Never nest two modal dialogs. Connector permission detail replaces the current step body and Back restores it. All modal exit paths handle unsaved state consistently.

### S02 — Operating Dashboard

Top area: title, status, execution mode and Pause. Sample mode is visible independently of agent status. A one-line update has count/source/time provenance; omit it when data are unavailable.

**Priority 1: Needs your decision.** Rank unresolved customer safety/support and unknown execution ahead of routine approvals, then ready-to-review plans. One leading item shows what requires a decision, why it matters, what approval authorises and one primary action. Secondary queue is compact rows, not equally prominent cards. Never hide urgent exceptions behind a new-plan card.

**Priority 2: Customer journeys.** Show customers grouped by meaningful state: awaiting reply, reminder confirmed, checkout pending, order confirmed, needs attention, suppressed. Mutually exclusive journey counts use a declared cohort; channel counts remain separate. Empty states explain the reason and next step.

**Priority 3: Verified outcomes.** Compact observed orders/net revenue/cost completeness and View outcomes. No synthetic incremental uplift chart. Keep experiment setup out of this screen.

Secondary operating-boundary panel: products, permitted channels, next permitted contact window, contact/spend caps, offers setting and policy version. It is concise, with View policy. Health summary shows only attention or freshness needed for decisions.

When no approval/exception exists: “No decisions waiting” and the next scheduled action. Do not create fake activity. When paused: persistent text identifies paused time/reason and explains new outreach is stopped while trusted events and opt-outs still process. Resume has a preflight result, not an instant green state.

### S03 — Opportunity and plan review

Header: plan name, draft/review state, concrete audience size, exact product scope. Lead copy states “Approval allows these customers to be contacted within these limits.” Distinguish plan approval from installation and individual action review.

Left main: selected customer rows showing alias/ID, last delivered order, repeat window or confirmed date, evidence basis and eligibility. Row selects the evidence drawer. Excluded count opens reasoned rows; do not include them in approve totals. Default sort: due/overdue, then explicit reminder priority, with reasons visible and no false urgency.

Right/stacked: schedule, channels, total contact cap, spend cap, offers off/approved IDs, mode, expiry and missing cost inputs. Schedule edit changes draft. Show before/after if the plan had approval. Primary “Approve plan for 3 customers” in the reference; actual count comes from eligible selected IDs. Secondary Edit timing and Reject plan. Revalidate server facts at approval and dispatch.

Approving shows saving/checking then receipt. Disable repeated submission while pending. If version/facts changed, show the affected customers/limits and require review of the refreshed plan. Bulk select selects only eligible rows and announces selected/total counts. Never expose “force include” for an opt-out.

### S04 — Activity and journey detail

Activity defaults to a concise table/list: customer, product, latest decision/outcome, channel, event time and attention flag. Useful filters: state, channel and plan. Event timestamps specify timezone. Distinguish historical transcript from an active interaction.

Journey drawer width 640 px desktop, up to 88vw tablet, full viewport mobile. Header: alias/ID, same SKU, current state, owner. Primary contextual action is Approve action if required, Take over if autonomous and eligible, or Resolve exception if blocked. Pause agent remains accessible in global chrome; suppress/stop is a clearly labelled contextual action with scope explanation.

Content order: latest customer words → concise intent → current next step/confirmed date → chronological conversation → evidence and receipts. Show voice transcript and subsequent WhatsApp handoff in one timeline. Optional Facts/Receipts sections reveal source times/provider references; not another permanent sub-navigation system.

For Ananya: “I still have enough. Remind me Friday.” → confirmed 16 Oct, 10:00 IST → WhatsApp reminder saved → voice overlap cancelled. Treat waiting as a successful customer outcome, not lost conversion.

For Rahul: voice confirms same bottle/one unit and asks for checkout on WhatsApp → separate channel permission/fact checks → checkout prepared → payment not confirmed. Audio simulation uses an explicit mode tag. Real browser audio states: requesting permission, listening, processing, speaking, permission denied, disconnected; controls labelled Start/Stop/Mute/Replay as applicable.

For unknown send result: show “Delivery result unknown”, actual last attempt and Check delivery status; no resend shortcut. For support: owner/handoff receipt or pending failure and sales paused. For opt-out: “Suppressed” with no marketing approval button.

Takeover displays “You control this conversation” and disables autonomous proposals. Hand back checks current facts/policy; avoid silently returning control on drawer close.

### S05 — Outcomes and learning

Header includes cohort/window and source modes. First row: verified brand orders, net revenue, cost completeness. Contribution is provisional when calculable and returns immature; if required costs missing, show Unavailable plus missing categories. Incremental lift remains Not measured. No growth arrow that suggests causality.

Order rows include origin: agent checkout or outside agent link; payment/order reconciliation status, return maturity and included/excluded accounting reason. Drilldown opens calculation, component costs and source references. Customer-assigned denominator/window accompanies rates.

Learning follows outcome evidence: customer-confirmed date/preferences already saved; broader suggestion has evidence, proposed diff, affected scope and Review change. The fixture's three customers do not justify a cohort recommendation; show “More history needed for policy suggestions.” Do not invent a lesson to fill a panel.

### S06 — Settings, connectors and entry continuation

Preserve existing sample login, verification, payments home and Studio discovery. Keep them clear and restrained; concentrate bespoke design on the agent's operating experience. Settings uses grouped forms (products/schedule; channels/contact limits; offers/economics; execution/review). Save produces a policy diff/version and approval implications. Revoking a connector shows the affected active jobs and blocks dependent execution. UI permissions mirror server state; they do not replace server authorisation.

## 7. Component inventory and contracts

Use composable components in whatever frontend stack is eventually selected. Names are proposed local names, not Blade API names.

| Component | Required data/behaviour | Key variants |
| --- | --- | --- |
| AgentHeader | title, mode, status, pause, policy | ready/running/paused/degraded |
| SourceMode | real adapter mode; text plus optional icon | disconnected/simulated/test/live |
| DecisionItem | required decision, consequence, owner, due context, primary action | plan/action/exception |
| PolicySummary | approved version, exact boundaries | complete/missing/revoked |
| RepeatWindow | dated evidence/estimate, basis, confirmed date, accessible text | personal/fallback/customer-confirmed |
| PlanReview | immutable/edited version, audience, policy diff, approval receipt | draft/invalidated/pending/approved/rejected |
| JourneyRow | current journey state, latest event and channel | awaiting/reminder/checkout/order/blocked/suppressed |
| EvidenceSection | facts by provenance and source timestamp | fresh/stale/missing |
| ActionReceipt | exact action ID, provider reference, result, timestamp, mode | held/submitted/confirmed/failed/unknown |
| ContextQuestion | scope-bound explanations/follow-up | evidence available/no evidence/loading/error |
| ConversationOwner | agent/human ownership and change receipt | autonomous/taken over/handback blocked |
| OutcomeValue | value, cohort/window, completeness, maturity | verified/provisional/unavailable/not measured |
| LearningDiff | evidence, exact proposed policy changes, review | enough evidence/insufficient/reviewed |

Do not invent component-library props. Verify official APIs when installing Blade. For the existing plain HTML stage, implement equivalent semantic controls using proposed tokens. Do not install a framework solely to execute this design handoff.

## 8. Interaction and state rules

| Trigger/state | UI response | Persistence/execution requirement |
| --- | --- | --- |
| Plan/action approval | Explicit scope/count; checking state; receipt | Bind exact version; error retains review state |
| Edited approved plan | Before/after diff and Approval required | Prior approval cannot execute expanded scope |
| Pause | Stop-new-outreach confirmation and pending/confirmed state | Real pause receipt; no false recall of submitted sends |
| Resume | Preflight list; running or blocked result | Current consent/orders/policy/ownership checks |
| Takeover | Visible human owner and Hand back | Closing drawer does not transfer ownership |
| Customer later date | Confirmed date, new reminder, overlap cancellation | Explicit date/channel; dispatch preflight later |
| Opt-out during pause | Suppressed immediately | Process independently of discretionary agent state |
| Checkout created | Checkout pending, current terms/receipt | Does not set payment/order confirmed |
| Outside-link order | Verified order origin and updated journey | Trusted evidence, deduplication, cancelled jobs |
| Missing source/cost | Specific blocked action and repair | No fallback fabricated fact/cost |
| Unknown provider result | Unknown + Check status | No blind resend |
| Data refresh | Preserve context, timestamp and stale distinction | Never silently remove merchant draft edits |
| Empty queue/history | Cause plus useful next step | No seeded success presented as real |

Toast is acknowledgement, not the only receipt. Critical error/pause/unknown states remain inline until resolved. Form validation is next to the field and summarised on submit with focus on the first error. Destructive/prohibited marketing actions do not gain an override button.

## 9. Exact copy patterns

| Context | Approved pattern |
| --- | --- |
| Dashboard title/subtitle | Repeat Purchase Agent / Help customers reorder when they are ready. |
| Sample status | Design reference · synthetic data · local actions only |
| Pending plan | 3 customers are ready for your review. / Review timing and contact limits before outreach. |
| Timing | Suggested repeat window: 11–14 Oct. / Based on two previous delivered-purchase intervals. |
| Sparse history | Product-level estimate. Limited customer history. |
| Waiting customer | Reminder confirmed for 16 Oct, 10:00 IST. |
| Plan scope | Same purchased SKU only. Offers off. Customer completes payment. |
| Activation | Installed. No customer contact is authorised yet. |
| Approve action | Approve this action / [channel, customer, terms and limits shown above] |
| Missing evidence | Cannot verify current stock. Refresh commerce data before preparing checkout. |
| Unknown execution | Delivery result unknown. Check provider status before retrying. |
| Pause | New outreach paused. Order updates and opt-outs still process. |
| Costs | Contribution unavailable. Product and fulfilment costs are missing. |
| Lift | Incremental lift: not measured. A valid comparison is required. |

Avoid “AI magic”, “autopilot profits”, “high-confidence buyer”, “customer is running out”, “revenue recovered” before verified payment/order evidence, and causal language for observed orders. Do not call an inactive provider connected or an illustrative transcript live.

## 10. Synthetic reference fixture and coherence

Reference date: 12 Oct 2026, IST. Reference merchant: Loop Essentials; product: laundry liquid 1 L, same variant. Three approved/eligible example customers: Ananya C001 (waiting), Rahul C002 (voice-to-checkout), Meera C003 (order outside agent link). Excluded rows: C004 (undelivered) and C005 (opt-out). Inbound support case C006 is outside the outbound audience.

Approved reference policy: 10:00–18:00 IST, 2 total contacts/customer across permitted channels, ₹500 contact-spend cap, offers off. These are synthetic design values, not merchant authorisation. Voice/WhatsApp permissions are per customer; Rahul's handoff requires both. Three customers → three independent journey states; do not add support/opt-out cases into assigned audience totals.

Observed synthetic order: Meera, one unit, ₹499 net revenue, outside agent link, reconciled payment/order. Product/fulfilment costs missing; contribution unavailable; returns immature; incremental lift unmeasured. Ananya's reminder and Rahul's checkout are not orders. Actual application fixtures may differ, but screenshots and calculations must agree.

The reference begins with a draft plan. Approve in the reference advances to labelled illustrative journeys and a single observed synthetic order; this is local demonstration playback, not actual send/payment execution. Reset applies only to this reference fixture.

## 11. Accessibility and responsive acceptance

- Real semantic landmarks/headings/buttons, labelled controls, visible 2 px focus ring with adequate contrast. No essential hover-only disclosure.
- Tabs: roving focus, Left/Right/Home/End navigation, matching selected panel and role/ID relationships. Native links for route navigation.
- Modal/drawer: aria-modal/label, initial focus, focus trap, Escape, inert underlying application and focus return. Confirm unsaved edits only when needed; never stack inaccessible overlays.
- Live regions announce saved/failed/paused states without interrupting typing. Do not stream every generated word to screen readers.
- Use text equivalents for date windows, channels, colours and progress. Provider state is named explicitly.
- Test ≥200% zoom/text enlargement, keyboard-only, screen-reader labels and focus order. Reflow at 320 px; no clipped controls. Tables may scroll within a labelled region; primary actions remain reachable.
- Mobile plan fields precede sticky approval footer; respect safe areas. A mobile drawer is a full-height view with visible Back/Close. Audio controls remain labelled and reachable.
- Target WCAG 2.2 AA; implementation requires actual verification. Do not mark the whole prototype compliant from visual checks alone.

## 12. Feature traceability and developer build order

| PRD features | UI ownership |
| --- | --- |
| F01–F02 | Existing entry/discovery + S01 install and activation |
| F03–F04 | Connectors/Settings + PolicySummary and source states |
| F05–F07 | S03 opportunity evidence, eligibility and plan approval |
| F08–F10 | S04 contextual conversations, voice and shared journey |
| F11–F13 | S04 receipts, checkout/payment distinctions, reminder/support/suppression |
| F14–F15 | Global pause, action reviews, takeover, audit/failure recovery |
| F16–F17 | S05 customer learning, suggestions, truthful analytics |
| F18 | Shared tokens, responsive composition, focus and every state |

Build order: tokens/shared controls → shell and entry continuity → installation/settings/connectors → operating dashboard → plan review/evidence → activity/journey → outcomes/learning → responsive/accessibility/state QA. Deliver the entire approved journey. Priority is order, not feature removal.

## 13. Execution brief for GPT-6.1-sol low

Copy this brief into the developer task when implementation is requested:

> Implement the approved Repeat Purchase Agent UI/UX using `docs/UIUX-HANDOFF.md`, `frontend/design-handoff.html`, `frontend/design-tokens.css`, the approved `docs/PRD.md` and `AGENTS.md`. Read `docs/design-evidence.md` and `docs/design-qa.md` before claiming fidelity or validation. Preserve the Razorpay-style shell, all entry/install views and the full 18-feature journey. Implement considerate replenishment through decision-led hierarchy, repeat-window evidence, versioned plan review and customer-words-to-receipt journey detail. Keep all unavailable integrations clearly labelled and keep server/provider decisions open. Work in the existing editable frontend source and keep its standalone export current; the new handoff reference is not a replacement for the full application. Use deterministic, coherent local fixtures until authorised backend work exists. Implement every specified empty/error/paused/disconnected/unknown state and responsive/focus behaviour. Validate visually at 1440, 1024, 768, 390 and 320 px, with enlarged text and keyboard operation. Report actual checks, defects and simulation limits. Do not publish, initiate real outreach or move money. Do not ask routine questions answered by the handoff; ask only for consequential unresolved choices after making a concrete reviewable proposal.

Expected developer outputs: refined editable UI/export, reusable tokens/components, working local full-journey controls, state inventory, screenshot evidence and concise change/validation report. No new task or model session has been launched by preparing this handoff.

## 14. Definition of design implementation done

All key views and the 18-feature traceability exist; states/metrics agree; no dead critical controls; approval scope/version visible; pause/takeover/suppression behave correctly; payment/order truth remains distinct; every source mode is honest; layout and focus checks pass or material defects are explicitly reported. The desktop design can be recognised as Razorpay-compatible, while customer readiness, deferral and traceable adaptation make the Repeat Purchase Agent distinctive.
