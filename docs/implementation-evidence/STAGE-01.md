# Stage 01 evidence report

13 October 2026 · ready_for_review

## Implemented behaviour

Added a modular FastAPI foundation with PostgreSQL persistence, Alembic migration, separate owner/application identity, hashed expiring sessions, login throttling, CSRF/origin/host checks, membership roles, independent demo/development workspaces, scoped connector capabilities, immutable audit permissions and versioned/idempotent workspace updates.

The new server preserves the merchant reference and successful Shopify snapshot shape; it adds membership authentication to that snapshot on port 8766. The original connector/startup path remains intact on port 8765.

Provided a project-local PostgreSQL runtime, distinct administrative/migration/application roles, Windows-compatible async entry points, owner bootstrap/password replacement, a 30-package dependency lock and PowerShell setup/run/check scripts. Generated credentials are private ignored files; no provider secret was copied into source.

## Changed paths

- backend/app/: settings, schema, database unit of work, repositories, security, services, API/main, CLI and Windows-compatible runtime/server.
- backend/migrations/ and alembic.ini: frozen ten-table initial migration, downgrade and grants.
- backend/tests/test_foundation.py: real PostgreSQL acceptance suite with an enforced disposable database.
- backend/scripts/: local PostgreSQL preparation, owner preparation, environment/setup/check helpers.
- backend/run-foundation.ps1, requirements-foundation.in/.lock and .env.foundation.example.
- backend/review/index.html: minimal Stage 01 internal review utility.
- Project README/AGENTS/HANDOFF pointers and docs/implementation-evidence.
- .gitignore: allow the non-secret foundation example while preserving ignored credentials/dependencies/data.

No existing frontend source, Shopify provider implementation or original test was changed by Stage 01.

## Checks actually run

| Check | Result |
| --- | --- |
| PostgreSQL migration upgrade → downgrade → upgrade, disposable database | Passed |
| Final python -m unittest discover -s tests -v | 13 passed in 50.643 seconds |
| Original python -m unittest test_shopify_app -v | 4 passed |
| Targeted concurrency/idempotency/restart regression rerun | 3 passed in 18.503 seconds |
| Development database migration and random owner/bootstrap workspaces | Completed |
| Running HTTP readiness + review page | 200; revision 0001_foundation |
| Running owner login → workspace reads → logout | Passed; authenticated read after logout 401 |
| Real authenticated Shopify capability check | 200; 20 products, 4 customer records, 1 order, 10 drafts; no warnings |
| Compatibility snapshot through new authenticated server | Passed; development/read_only shape retained |
| PowerShell script parse | Passed |
| Git whitespace and credential-ignore checks | Passed |

The first full run found a concurrency failure: competing commands inserted idempotency rows that acquired workspace foreign-key KEY SHARE locks, then tried to upgrade both to FOR UPDATE. The workspace update lock now uses FOR NO KEY UPDATE, compatible with those foreign-key locks while still serialising name/version updates. Targeted and final full suites passed after the fix.

Windows initially rejected psycopg async connections on the default Proactor loop. Application/CLI/migration entry points now explicitly use a selector loop; the Python 3.12 unittest runner uses its Windows selector policy.

## How to review

See [STAGE-01-RUNBOOK.md](STAGE-01-RUNBOOK.md). The review server is running at http://127.0.0.1:8766/foundation. Privately read backend/.local/owner-access.json for the generated owner credential, or use the hidden local password replacement command. No password is included in this report.

## Limits

This is a loopback development foundation. Production OIDC, FORCE RLS, live retention/pilot controls, the React migration and the complete agent engine remain future stages. The internal review page was HTTP/functionally checked; no full visual/accessibility compliance is claimed.

Connector checks are synchronous read-only verification in this stage. Policies/plans, general command jobs/outbox, consent/customer execution, AI/audio, WhatsApp and automatic Razorpay reconciliation are not yet implemented.

The existing provider accounts and earlier payment evidence were preserved. No external write, send, charge, new data grant or public deployment occurred. Owner Stage 01 review remains pending; Stage 02 has not started.
