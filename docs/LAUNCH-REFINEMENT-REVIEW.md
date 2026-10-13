# Launch and audience refinement — 13 October 2026

The user-linked workspace 269b2016-1dba-44f0-9b90-d93d07cfbdef is the connected Shopify Development source: 29 variants, four customer records, zero eligible under current delivery/consent evidence and no approved offer records. No extra real customers or offers were fabricated.

The owner's existing scale review workspace c3e7bba6-8e00-40f5-bf74-328af45872c7 contains 200 synthetic customer records, 160 eligible. The workspace selector now clearly names Avime Herbal · Shopify store, Avime Herbal · 200 customers and Avime Herbal · Design review. Default entry prefers the scale workspace; explicit workspace URLs remain respected.

- Approved offers are rendered as selectable cards with amount, expiry, approval and margin-readiness status. Empty state is explicit; manage-offer navigation remains available.
- AI checkbox and per-message review selector removed. Saving campaign settings uses bounded conversations, contextual interpretation and limited provider processing. The readable review explains the authority; campaign launch still requires exact audience approval.
- Review dialog shows selected settings with product names and rupee values. Changes show saved before/after values only; no Unset, raw JSON or internal keys.
- Audience filters are framed, labelled and responsive. Existing server pagination, all-filtered selection and unsaved-audience guards are preserved.
- Merchant dashboard defaults to the exception/opt-out queue. All customers remain inspectable. Support cases and blocked actions remain backend protected.
- Separate WhatsApp test source/style/route preserved from the other chat; its transport distinction was not changed.

Validation: TypeScript and Vite build passed. Browser checks passed for desktop/mobile review and audience layouts, automated WCAG AA, no page overflow, 200-row pagination, 160-eligible and 40-city bulk selection, dirty-state guards, merchant-queue default, preserved test tab, and approved-offer card interaction using a browser fixture. Zero runtime errors. No campaign, contact, offer approval or provider action was saved during checks.

Build assets updated the existing local preview; source remains on frontend/merchant-campaign-review. No merge or push.
