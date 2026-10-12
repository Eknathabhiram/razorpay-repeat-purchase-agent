# Repeat Purchase Agent — merchant UI v2

12 October 2026. This revision responds to the owner's feedback that the first design looked generic and its copy read like an annotated prototype. **This document and the v2 source supersede the v1 visual composition and copy where they differ.** The approved 18-feature PRD, product boundaries and original reference evidence remain authoritative.

## Delivery standard

Write for a merchant making a decision, not for someone reviewing an AI demonstration. The main workspace contains operational content only. Put simulation details in Test mode and connection/source details; never imply simulated services are live. The interface is a merchant-facing design implementation. It is not yet a launch-ready integrated service: real authentication, persistent server state, provider connections, consent checks, receipts and release verification remain required.

## What changed

- Replaced the five-screen presentation navigator with Dashboard / Activity / Settings. Plan review, outcomes, support and installation open through the relevant task.
- Replaced the oversized promotional plan card with a compact approval queue, coherent customer activity and a readable operating-policy summary.
- Removed presentation notes, repeated sample disclaimers and generic “AI” headings from normal product content.
- Introduced customer/action drawers with conversation context, proposed message, commercial facts, checks, receipt details and a persistent action footer.
- Moved setup into a four-step installation dialog. Shared connections have clear mode/access information.
- Added real local interactions: audience selection, approval counts, policy diff/versioning, pause/resume, takeover, support assignment, activity search/filter and saved test state.
- Mobile journeys use stacked customer rows, not squeezed desktop tables. Drawers occupy the narrow viewport; footers preserve the next action.

## Copy rules

| Context | Merchant copy | Consequence made clear |
| --- | --- | --- |
| Queue | Needs your attention | Pending operational work |
| Delivery issue | A delivery issue needs an owner | Reorder outreach is blocked |
| Customer checkout | Send Rahul his checkout link | Same item requested; payment still pending |
| Message review | Review message → Approve & send | Merchant approves the actual outgoing message |
| Support | Assign to me | Merchant owns the follow-up; sales stay blocked |
| Audience | Approve 2 customers | Exact selected audience, not installation permission |
| Pause | Pause outreach? | Stop new messages/calls; preserve reminders and process orders/opt-outs |
| Policy | Review policy changes → Save policy | New version; affected plan needs review |
| Empty approvals | No actions waiting for approval | Existing work can continue within current authority |
| No purchases | No confirmed orders yet | Trusted order/payment evidence is required |
| Costs | Not available / Cost data incomplete | Revenue is not claimed as profit |
| Incremental impact | Not measured | Observed orders do not establish lift |
| Unconnected source | Disconnected / Simulated | No implied live account access |

Use human-readable dates and specific actions. Do not expose developer file names, synthetic receipt IDs or implementation caveats in ordinary headings. Source/receipt details may show references on demand. Avoid placeholder link text, invented commercial promises, generic motivational messages and “AI magic”. For checkout conversations distinguish item price from final charges; final tax/delivery details come from the commerce checkout.

## Design system and layout

Use `frontend/merchant-app.css` as the concrete v2 styling source. These are proposed application values, not official Blade tokens. Default body 14 px; merchant controls and data 12–14 px; secondary metadata 10–12 px; title 24 px. Maintain contrast and verify final accessibility before compliance claims.

The 56 px dark product header and 212 px sidebar carry the Razorpay-compatible shell. The workspace uses aligned tabs, a compact metrics strip, a decision/activity column and a narrower policy column. No gradient hero, decorative AI badge, oversized empty-value card or repeated feature catalogue. On tablet, collapse global navigation; on mobile, stack the main columns and activity rows. Customer context stays in a right drawer, with fixed header/footer and scrolling body.

The distinct agent experience comes from contextual action proposals, confirmed customer timing, a shared WhatsApp/voice journey, exact approval scope, and honest outcomes. Customer intent is visible before the proposed action; waiting and support remain valid outcomes. A separate generic chatbot is not required.

## Source and build contract

- `frontend/merchant-preview.template.html`: semantic shell and dialog containers.
- `frontend/merchant-app.css`: v2 styles and responsive layout.
- `frontend/merchant-app.js`: local synthetic data adapter, routing, state and interactions.
- `frontend/build-preview.mjs`: bundles the template/CSS/JS into `frontend/design-handoff.html`.
- Run `node frontend/build-preview.mjs` after editing source files. The export is dependency-free and can be opened locally.
- `frontend/design-tokens.css` remains a v1 reference; it is not loaded by v2. `frontend/index.html` and its original editable fragment retain the earlier full-journey export pending application consolidation.

Do not use browser localStorage as production authority. V2 stores only synthetic workspace state there. Replace it with server-authorised state, immutable approvals and real integration receipts before launch. A “sent” state in this Test mode is a simulated receipt, not provider verification.

## Developer behaviour requirements

1. Approval must display the selected customer count and bind the exact plan/policy/action version. Zero selected customers disables approval.
2. Saving policy changes shows the before/after values and holds affected plan execution for review. A new relevant buyer is excluded from renewed outreach.
3. Historical purchases survive plan rejection/renewal; cohort assignment and order evidence must not be erased by current-plan state changes.
4. Approving a checkout message changes message state, not payment/order state. New purchases require trusted commerce/payment matching.
5. Pause blocks new outgoing actions, including merchant messages from a paused conversation. Resume/handback rechecks current source and plan state.
6. Support ownership and sales suppression are independent of the reorder audience. There is no marketing override for an opt-out.
7. A proposed change to a customer-confirmed reminder date is held for confirmation; it does not silently overwrite the confirmed date.
8. First-plan approval schedules outreach without fabricating replies, reminders or purchases. Empty outcomes/preferences remain empty.
9. Real scheduler, contact-cap/budget reservations, concurrency and provider retry rules remain backend requirements. Frontend guards are not sufficient authorisation.
10. Use native semantic navigation and dialogs, labelled inputs, focus return, keyboard-accessible actions and visible text states. Verify all accessibility gates in the PRD and original handoff.

## Checks performed on v2

- Validated source JavaScript and the exported bundle; inspected rendered desktop dashboard and checkout-review drawer.
- Checked Dashboard, Activity, Settings, Connections, Plan and Outcomes at 1440, 1024, 768, 390 and 320 px. Initial dashboard overflow at narrow widths was found and corrected; narrow dashboard was rechecked.
- Visually inspected mobile dashboard and checkout drawer and refined stacked customer rows.
- Exercised local checkout approval and reload persistence; payment remained pending and order count did not increase.
- Exercised pause and attempted manual send; the send was blocked. Escape closed the drawer and returned focus to its originating customer action.
- Saved a policy change, confirmed the review diff/version, observed the stale action held, renewed the plan with the new buyer excluded, and verified the previous order remained in outcomes.
- Changed the first-plan audience and verified the approval count. Its approval created scheduled rows with zero fabricated purchases/reminders.

Real integrations, full screen-reader/contrast/200% zoom verification, latency/availability, server persistence and real merchant usability validation are not complete. These are release gates, not implied by the polished UI. Revised screenshots are in `docs/merchant-ui-screens/`.

## Brief for GPT-6.1-sol low

Implement against this v2 merchant UI, the approved PRD and `UIUX-HANDOFF.md`'s product constraints/evidence. Preserve the full identify → decide → act → learn journey. Use merchant copy from the implemented views and this document. Do not restore v1 presentation annotations or its five-screen navigator. Keep Test mode and every integration status truthful. Consolidate the full entry/setup/operating journey without losing the original features. Replace the local adapter only when backend work is explicitly requested and provider/hosting decisions are resolved. Do not claim production launch readiness until the release gates actually pass.
