# Cohort launch and merchant conversations

Implemented on `frontend/production-ready`, following the owner's approved visual direction and subsequent initial-review-only mandate. The local app is served at http://127.0.0.1:8766/app/. Existing owner workspaces, credentials and prior backend stages are preserved.

## Merchant experience

- Dashboard / Activity / WhatsApp interactions / Settings are the primary navigation. Audience selection and launch review are contextual tasks. Detailed execution receipts remain available at `#/receipts`.
- Dashboard separates the actual customer base, eligible candidates and approved cohort. Counts come from scoped PostgreSQL queries, with current cohort states, merchant exceptions, observed purchases and the saved policy's shared spend allowance. No ₹25,000 amount or large illustrative metric is used as a live setting.
- Audience selection uses server search and pagination, city and reorder-window-start date filters, and selection across pages. “Select all filtered eligible” freezes those filter criteria. Changing the view afterward preserves the selection. Selected IDs and the facts generation are checked again when saving and approving.
- Launch review summarizes the entire selected cohort, reply style, provider-processing authority, permitted offers, checkout/reminder authority, contact hours, weekly contact cap, shared policy budget and expiry. Exact initial messages and reply choices remain inspectable through pages and are bound to the approval digest.
- WhatsApp shows a searchable conversation inbox and selected customer's actual sent/received history. City and activity-date filters sit in an expandable filter section. Sent choices are read-only evidence. Explicit Demo customer controls replay submitted buttons or typed messages; they never contact a real customer. The thread follows new messages while allowing the merchant to read earlier history.
- Desktop and narrow-screen layouts retain pause, takeover, readable message threads and recoverable loading/error states. Lists scroll within bounded surfaces rather than extending through hundreds of rows.

## Automation authority

`bounded` mode plus the immutable `conversation_automation` flag enables background Demo processing after initial plan approval. Existing policies are not silently upgraded. The initial review authorizes clear, concise, helpful replies and the displayed limits; individual internal action records still preserve exact payload digests and approval/audit evidence.

The agent asks for the same product and quantity, automatically prepares and sends a fresh checkout after the customer confirms them, checks approved offer evidence and contribution limits, and asks for an exact date/time followed by customer confirmation before saving a reminder. The customer completes payment. Sending a link never marks an order as purchased.

Contextual interpretation uses Together AI only when both contextual replies and provider processing are authorized by the policy. Typed intent proposals never supply prices, stock, discounts, recipients or payment truth. Responses render from allowlisted structures and current backend facts. A plain price question cannot become an invented offer because of a model classification.

Support issues, missing facts, uncertain delivery and requests outside approved limits become merchant exceptions. Opt-outs, refusals, missing consent and limit breaches stop competing work. Pause and human ownership remain authoritative. Customer replies take dispatch priority over a bulk launch, and durable event consumption and leased/fenced dispatch prevent routine replay.

The existing 24-hour plan expiry and fresh-fact requirements remain visible and enforced. Reminders beyond that authority require renewal; there is no silent extension. Weekly caps include conversation attempts. Spend is shared across a policy version, including conservative approved-offer exposure; a new cohort does not reset that allowance.

## Source and provider boundaries

The 200-customer scale sample is available only in an empty Demo workspace. It contains 160 eligible customers, 40 exclusions and five synthetic cities. Loading it cannot overwrite an existing source dataset. Current Shopify reads retain only the customer's default-address city for this filter; missing or inaccessible cities stay unknown. See [Shopify Customer documentation](https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer).

Interactive examples use at most three quick replies with short titles. Customer free text remains available. Actual transport must also satisfy the WhatsApp service window and approved-template requirements described in [Twilio quick replies](https://www.twilio.com/docs/content/twilio-quick-reply) and [WhatsApp concepts](https://www.twilio.com/docs/whatsapp/key-concepts). This implementation preserves the existing block on real sends, real Storefront checkout and public deployment. Razorpay-style merchant authority is grounded in [Razorpay's published guardrail principles](https://razorpay.com/blog/razorpay-agent-studio-principles-guardrails-and-merchant-control/); it does not claim private Agent Studio API access or certification.

## Verification

The production build, generated API types and six API-client checks passed. The nine frontend regression tests passed, including keyboard/focus, recovery and automated WCAG AA checks. Thirty-six affected backend checks passed for planning, commerce, interpretation and merchant flows. A final 26-test run passed for automatic price/offer behavior, merchant flows, worker priority, execution and WhatsApp safeguards. These suite totals overlap and should not be added as unique test counts.

The integrated browser exercised a 160-journey launch from the 200-customer sample, same-item confirmation, checkout without routine approval, and real Together interpretation of a synthetic price question. The final visual recheck passed all 15 screen/width combinations at 1440, 390 and 320 pixels, with no runtime errors, page overflow or automated WCAG AA violations. It also checked mobile back navigation and city filtering. A keyboard-scrollability issue found in the read-only transcript was repaired before this final run.

One additional PostgreSQL test passed for the “Not now” button: it stops the current journey without inventing a persistent opt-out or merchant exception, while a subsequent customer-initiated reorder can resume inside the mandate. Explicit STOP remains a suppression event. The header now distinguishes an initial review requirement from a current approved mandate.

Integrated browser evidence is saved in `implemented/`: desktop/mobile screenshots and `verification.json`. The browser uses a fresh isolated synthetic QA tenant and the actual local API/database. Review screenshots are application renders, separate from the earlier ImageGen design concepts. Automated accessibility checks are supporting evidence, not a WCAG certification or production-launch claim.

## Connection status and guided launch follow-up

The original owner Demo contained nine customers and an older per-message review policy. That explained why the owner's screen differed from the separate QA sample. A separate **D2C review · 200 customers** workspace is now accessible through the existing owner login, with 160 eligible customers and an unapproved draft. Existing owner workspaces, credentials and approvals remain intact. Its all-day contact window and ₹500 shared budget are explicit synthetic walkthrough settings, editable before initial approval.

Launch now follows four visible stages: Data & limits → Choose audience → Review & launch → Conversations. Source/policy setup and audience selection have separate screens. Unsaved policy or audience changes block forward navigation; edited selection must be saved before review. Each stage has one Continue action, and stage navigation restores the page top and announces the new stage through keyboard focus. The initial approval remains with the merchant.

`GET /merchant/readiness` reports capability-specific, workspace-scoped status. Demo availability, configured credentials, recorded verification and unavailable real sending are distinct. The owner's Development Shopify source returns 20 products, four customer records, one test order and ten drafts. The new **Check test payment reads** action completed a read-only sync and recorded one Razorpay test payment; no charge or refund was created. Real WhatsApp credentials/sender/callback requirements remain incomplete. Together processing is configured and verification follows scoped provider receipts.

The API contract export and final production build passed. Three backend readiness tests passed. Nine frontend regressions passed in the initial run; its obsolete mobile-navigation expectation was updated for the removed preview link and the mobile focus test passed on rerun. Both guided-stage tests and the desktop/mobile automated accessibility scan passed after the audience-save fix; the two affected flow tests passed again after adding stage focus and forward-step protection. Actual owner review was checked at 1440 and 390 pixels with no page overflow. Screenshots are in `connection-flow/`. The owner cohort was not approved during verification.

The authorized coordination chat's Analytics and ProductScope changes are preserved. Both chats were editing the same physical checkout, now on `frontend/merchant-campaign-polish`; a branch switch in that checkout does not isolate uncommitted changes. This follow-up did not stage or commit the shared changes.
