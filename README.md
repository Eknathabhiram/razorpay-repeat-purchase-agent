# Repeat Purchase Agent

Consolidated frontend and backend, 13 October 2026.

Review the current application at http://127.0.0.1:8766/app/#/dashboard using the existing owner login. The root URL redirects to this React application.

The React/TypeScript frontend includes Avime Herbal catalogue and dashboard, campaign setup, audience filters, readable offer/settings approval, conversations, WhatsApp test controls, analytics, connections and supervision. The FastAPI/PostgreSQL backend includes authentication and workspace isolation, Shopify reads, deterministic planning, exact approvals, durable execution, protected replies, Together AI, checkout terms, independent payment reconciliation, refunds, outcomes and reviewed learning. Eight additive migrations define the persisted schema.

Start the backend with `./backend/run-foundation.ps1`. Build the frontend from `frontend/app` with `pnpm run build`. New installations follow `backend/scripts/setup-foundation.ps1 -InstallDependencies`; preserve existing ignored configuration and database data.

Read [the consolidation report](docs/CONSOLIDATION-2026-10-13.md) and [release handover](docs/RELEASE-HANDOVER.md) for verification and integration limits. The full local hybrid flow is implemented; production checkout, WhatsApp delivery, public callbacks and deployment remain gated.

The superseded v1 HTML preview, inline fragment, tokens and unused overview component were removed. The v2 reference builder and Shopify compatibility connector remain because existing references and compatibility behavior use them. Historical versions remain in Git.

Credentials, owner access, customer databases, local audio/backups, dependencies and generated builds are excluded from Git. The confidential original assignment is excluded.
