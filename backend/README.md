# Backend

The current application is FastAPI + PostgreSQL in `app/`, with eight additive Alembic migrations. Run `./run-foundation.ps1` from the repository backend directory, or `./backend/run-foundation.ps1` from the repository root. It serves the current React build at http://127.0.0.1:8766/app/ and redirects `/` there.

`app/` owns authentication, isolated workspaces, source reads, planning, policy/offer approval, durable execution, customer protection, Together interpretation/audio, checkout terms, payment evidence, refunds, outcomes and reviewed learning. `shopify_app.py` and `run-local.ps1` retain the original read-only development connector for compatibility.

`./scripts/setup-foundation.ps1 -InstallDependencies` prepares a new local runtime/database and applies migrations. Existing installations must preserve `.env`, `.env.foundation`, `.local`, owner access and data. Configuration templates contain no real credentials.

`./scripts/check-foundation.ps1` runs PostgreSQL acceptance and Shopify compatibility tests. Database tests enforce the disposable `rpa_stage1_test` database. Export OpenAPI using `scripts/export_openapi.py` with the configured foundation runtime.

See `../docs/RELEASE-HANDOVER.md` and `../docs/CONSOLIDATION-2026-10-13.md` for actual capabilities and release limits. Real WhatsApp transport/callback delivery and Storefront checkout remain unverified and gated.
