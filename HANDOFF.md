# Project handoff — 12 October 2026

## Workspace organisation and PRD review

The owner requested GitHub upload, separate frontend/backend folders and a detailed PRD for explicit approval. The current preview and source moved to `frontend/index.html` and `frontend/src/design-preview.fragment.html`; `backend/README.md` documents the server scaffold. The 18-feature list is preserved in `docs/user-feature-scope.txt`. The project owner approved `docs/PRD.md` on 12 October 2026 and requested design discussion next, before UI changes. This reorganisation does not implement integrations or select a framework.

The owner signed in to GitHub and authorised upload. Private repository: https://github.com/Eknathabhiram/razorpay-repeat-purchase-agent . Upload uses the authenticated browser because the CLI is signed out and the connector exposes no repositories. The confidential `docs/challenge-brief.pdf` remains excluded. Original references in the workspace's top-level `Docs/` are outside this project repository. The PRD scope and requirements are approved; unresolved provider, framework and hosting choices remain open.

## Immediate user request

The user wants to move this work to Codex and improve the UI/UX before coding integrations. The current merchant journey is functional but still feels assembled around agent features. Start by revising the design around merchant tasks and decision clarity. Do not treat the existing preview as a final visual design.

The latest request is a final UI/UX handoff for a senior developer using GPT-6.1-sol with low reasoning effort. `docs/UIUX-HANDOFF.md` specifies considerate replenishment, grounded in official Blade, RazorSense and Agent Studio principles, with explicit provenance limits for earlier walkthroughs. A five-screen inspectable reference and proposed tokens are in `frontend/design-handoff.html` and `frontend/design-tokens.css`. `docs/design-qa.md` records actual reference checks. Original application files remain intact; no separate developer/model task was started. Design implementation follows the handoff while preserving all 18 features and unresolved provider/hosting choices.

The owner subsequently rejected the v1 visual execution as generic and asked for merchant-facing polish and launch-quality copy. The current v2 workspace is `frontend/design-handoff.html`, assembled from the merchant template, CSS and JS with `frontend/build-preview.mjs`. `docs/MERCHANT-UI-V2.md` supersedes v1 composition/copy and records actual local checks. V2 uses normal Dashboard/Activity/Settings navigation, contextual customer/action drawers, concrete approval copy, policy versioning and persisted synthetic state. Test information is contained in Test mode and source details. Real authentication, backend/provider integrations and release verification remain incomplete; do not describe the service as ready for production launch.

## Product intent

Build a proposed specialist agent for Razorpay Agent Studio that helps the growth owner of an Indian D2C consumer brand generate profitable repeat purchases. The core pain is reorder journeys that cannot adapt to individual readiness or the customer's reason for waiting. Discount waste and manual retention work support that problem.

## Authoritative decisions

- Full agreed solution: identify opportunity, choose an appropriate action, execute within approval boundaries and learn from outcomes. The user rejected an MVP-first reduction of this scope.
- Any repeatedly purchased D2C consumer product; do not restrict the merchant segment to skincare or haircare.
- Current purchase scope: same previously purchased SKU or variant. Suitable alternatives, packs and broader cross-sell are future bets, not executable current features.
- Use qualifying delivered purchase history, prior intervals, quantity and customer-stated dates. Use a product-level fallback when customer history is sparse. Non-response is unknown readiness.
- Exclude recent relevant buyers, undelivered or returned orders, unresolved issues, missing contact permission and explicit opt-outs.
- WhatsApp and voice are part of the product. Coordinate them under one contact ledger and policy. Voice permission does not independently permit WhatsApp delivery.
- Merchant approves data access, customer audience, channels, timing, contact and spend caps, offers and required margin constraints. Review-first and bounded execution are supported. Pause and takeover remain visible.
- Conditional incentives come only from existing, approved, eligible offers for price concerns or explicit offer enquiries. Never invent discounts or pricing.
- Agent owns reorder outreach for the approved group. Other reorder campaigns exclude it; other campaigns need shared contact coordination. Failed coordination pauses affected outreach.
- Customer actions: same-SKU checkout, confirmed reminder, support handoff or suppression. Customer completes payment; the agent does not charge them automatically.
- Verified payment and commerce evidence confirms purchase. A checkout link is not an order; paid, fulfilled and delivered are separate states.
- North star: incremental net contribution per eligible customer, measured against a comparable control in rollout. If reliable costs are missing, use incremental net revenue. Include all assigned customers' brand orders, including those outside agent links, and allow returns to mature.
- Supporting outcomes: repeat-order rate and merchant time saved. Guardrails: opt-outs, complaints and execution errors. Do not fabricate lift or precision.
- Moonshots: suitable alternatives and packs, then broader next-product/cross-sell once evidence and permissions support expansion.

## Current design and status

The latest preview covers sample login and verification, a payments-home entry, Agent Studio discovery, agent detail, Configure / Connectors / Review / Activate, My Agents, Dashboard / Activity / Settings, plan approval, conversation and action-trace drawers, analytics, review-first action approval, pause and takeover.

The observed Razorpay shell is a black payments header, regular dashboard sidebar and Agent Studio Home / My Agents / Connectors navigation. Installation is a modal with a vertical four-step progress list. Public operations demos show an agent list and summary, Dashboard / Activity / Settings, and an activity detail drawer. Preserve these patterns while improving our agent-specific information architecture.

The login entry and Studio structure are grounded in public references. The verification screen, neutral payments-home content, repeat-purchase controls and analytics are proposed/sample additions. Do not call them an exact copy of the private production dashboard.

The fixture is a fictional household-goods brand using a laundry-liquid SKU. Three initially eligible customers demonstrate waiting, voice-to-checkout handoff and a brand order outside the agent link. Two excluded customers demonstrate undelivered status and opt-out. An inbound delivery issue can be routed to support without initiating sales outreach. These data are synthetic, not merchant validation.

## Implementation decisions and access

- The user has no Shopify, Razorpay, WhatsApp or voice developer accounts yet.
- Desired direction: use real provider APIs and developer/test accounts where possible, with clearly labelled simulation elsewhere.
- D02 commerce path: recommend native Shopify checkout with Razorpay test payments if the accounts can support it. This has not been independently connected or finally selected. A standalone payment link does not automatically create a Shopify order.
- D03 voice: browser microphone/audio is the practical demonstration direction. Actual telephone automation is an additional connection to verify, not an already-working feature.
- D04: code in GitHub; the user will deploy. No repository URL or AI/speech provider has been supplied. Do not assume GitHub selects the model provider.
- D05: use a Shopify development store with purpose-built synthetic repeat history where possible. Generic generated Shopify data are not validated replenishment data. The sample product remains configurable.
- Keep provider secrets on the server and in environment variables. Do not ask for secret keys in chat or commit them.

## How to work with the user

For consequential product or architecture decisions, provide two or three clear options, recommend one and explain the tradeoff. Avoid repeatedly asking for approval for already agreed scope or routine reversible edits. The immediate next work is design refinement, not account signup or deployment.

If the older specification's D01–D05 table differs from this handoff, use this handoff for the latest implementation discussion. Preserve the specification's behaviour and safety requirements unless the user explicitly changes them.
