# Consolidation - 13 October 2026

## Gathered work

The complete uncommitted backend/application implementation was committed on frontend/merchant-campaign-polish. The latest campaign-review checkout changes, tests and screenshots were committed on frontend/merchant-campaign-review. integration/latest-2026-10-13 merges both; frontend/production-ready is already an ancestor. GitHub origin/main contained the older published prototype under a separate history. That history was joined while retaining the newer application tree and existing reference assets, without rewriting published commits.

Frontend: Avime Herbal catalogue/dashboard, campaign settings, readable offer review, filtered/paginated audience, initial launch approval, conversation supervision, WhatsApp testing, analytics and connections. Backend: owner sessions, workspace/role isolation, Shopify facts, eligibility/policies, exact audience approvals, durable jobs, coordinated protection, approved offers/checkout terms, Together AI/audio, payment reconciliation/refunds, outcomes and reviewed learning. Database schema: 0008_outcomes.

## Cleanup

Removed superseded v1 HTML preview, editable fragment, unused design tokens and replaced Overview.tsx. Git retains historical versions. The main server redirects `/` to the current React application at `/app/`. README files identify current entry points. The v2 reference and original Shopify connector remain because compatibility paths still use them. Credentials, local databases, owner access, generated dependencies/builds and confidential assignment remain excluded.

## WhatsApp check (limited to two minutes)

The current adapter targets Twilio. Existing evidence records a correct trial join but unresolved provider linking/test controls and no configured transport credentials/public callbacks. No new message was sent. Meta developer testing is an alternative through its official WhatsApp Cloud API collection, requiring an app/account setup, sender/phone-number ID, access token and a verified test recipient; inbound integration requires webhook setup. No Meta adapter or configured account credentials were found in this project. Switching providers is additional implementation, so consolidation proceeded after the bounded check.

Official provider reference: https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api . Direct Meta documentation returned HTTP 429 during this check.

## Review

Open http://127.0.0.1:8766/app/#/dashboard using existing owner credentials. Review catalogue, launch settings/offer approval, audience, conversations and analytics. See RELEASE-HANDOVER.md for the full persisted demonstration and live-integration blockers. This is a local hybrid application; production delivery is not claimed.

Final results are recorded below.

## Final validation

- Strict TypeScript and Vite production build passed (111 modules); API types regenerated from the merged FastAPI schema.
- Six API/session/network recovery tests passed.
- Twenty-one backend tests passed: merchant cohort/offer automation, protections/reminders, provider readiness, test conversations, WhatsApp signatures/authority/unknown outcomes and original Shopify compatibility.
- Initial browser run: seven passed; five selectors still expected superseded labels. Updated those selectors while preserving launch-dirty, session-recovery and failed-refresh behavior assertions; All five passed after updating the saved-policy/count fixture; together with the original seven passing cases, all twelve browser checks pass.
- Private credential-value scan passed before capture; Final merged-tree scan also passed. Published main history and all three local feature branches are ancestors of the integrated branch.

- Final merged credential scan: 423 tracked files, eight private values checked, no leaks. Local review server refreshed to load consolidated code.
