# Avime Herbal page-by-page review

Current review page: My agents. Open http://127.0.0.1:8766/app/#/agents?workspace=4b9786d5-3244-4adf-99dc-6e11539f568b and hard refresh.

Renamed the presentation to Avime Herbal, removed demo and timezone footer copy from the merchant shell, corrected the breadcrumb and removed the duplicate page heading. The agent card has one primary Open agent action, readable capabilities and a secondary Create campaign action. Source/transport details remain in Connections; no live-source capability was implied or enabled.

TypeScript and production build pass. My agents passed render, no-overflow, no-demo-copy, branding and automated WCAG AA checks at 1440, 1024, 768, 390 and 320 px. Desktop and mobile screenshots were visually inspected. Evidence: docs/ux-reviews/2026-10-13/avime/verification.json.

Dashboard and product/settings layouts have draft code prepared and await the next page review. The linked local synthetic workspace had one product. Eight illustrative herbal review products were added with simulated provenance, retaining existing product history and approvals. The fixture helper makes no provider calls and explicitly refuses non-demo workspaces. These are review catalogue entries, not actual Shopify inventory or verified merchant prices.

Source remains isolated on frontend/merchant-campaign-review. The original source checkout is preserved; only compiled preview assets were refreshed for the user's local URL. Do not rebuild the original frontend and accidentally replace this review preview. No merge, push, campaign launch or customer contact occurred.
