# Stage 01 — owner review and local operation

13 October 2026. This stage implements the persistent backend foundation. The full agent engine and React migration belong to later stages.

## Review now

The application is running at http://127.0.0.1:8766/foundation. The existing connector/start command on port 8765 was preserved.

1. Privately open backend/.local/owner-access.json for the generated local owner login. Do not upload it or copy the password into chat.
2. Sign in on the foundation page. This is an application owner credential, independent of Razorpay/Shopify credentials.
3. Select Demo. Save a workspace name, refresh, and inspect its audit receipt.
4. Select Development. Its name/version are independent of Demo. Check Shopify reads and inspect capability/source details.
5. Open the preserved merchant preview from the page. Its agent actions and policy controls still use the prior simulation; only its Shopify read panel uses the connected source.
6. Sign out. Authenticated APIs must return 401. Signing in again retrieves the saved workspace state.

The review page is a small internal Stage 01 utility. It is not the Stage 02 React implementation or a production login experience. Its CSRF token stays in memory; reload requires sign-in before another command.

The test suite verifies a new application instance can use the same persisted session/workspace. For manual process restart, stop the foundation server, run the start command below and sign in again.

## Commands

From the repository root:

~~~powershell
./backend/run-foundation.ps1
~~~

The script discovers this machine's bundled Python, uses backend/.local/foundation and binds only 127.0.0.1:8766. It explicitly runs a Windows selector event loop for psycopg async compatibility. It does not replace the older run-local.ps1 connector.

To restart the project PostgreSQL runtime:

~~~powershell
. ./backend/scripts/foundation-env.ps1
& $FoundationPython backend/scripts/prepare_postgres.py --start
~~~

To perform a fresh setup on a compatible Windows machine:

~~~powershell
./backend/scripts/setup-foundation.ps1 -InstallDependencies
~~~

This installs the pinned dependencies into the ignored local folder, downloads official PostgreSQL 18 Windows binaries, initialises a loopback cluster, migrates the development database and prompts privately for the owner password. Choose 12–1024 characters. On repeat bootstrap, enter the existing password; it does not silently reset an existing owner.

To choose a replacement password on this already-prepared machine:

~~~powershell
. ./backend/scripts/foundation-env.ps1
Push-Location backend
try {
    & $FoundationPython -m app.cli owner-password
} finally { Pop-Location }
~~~

The prompt is hidden. Changing the owner password revokes all existing sessions. The earlier generated owner-access.json no longer contains the current password after replacement; keep the new password privately.

To run the tests:

~~~powershell
./backend/scripts/check-foundation.ps1
~~~

The integration suite upgrades/downgrades/re-upgrades and clears tables only in rpa_stage1_test. It explicitly rejects any other database name. It never resets rpa_development or changes Shopify records.

## Local configuration and stored data

| Location | Purpose |
| --- | --- |
| backend/.env | Existing provider credentials; preserved |
| backend/.env.foundation | Generated application/migration DB URLs and loopback origin settings |
| backend/.local/owner-access.json | Random initial local owner credential; private, ignored |
| backend/.local/postgres/auth.json | Generated database-role credentials; private, ignored |
| backend/.local/postgres/data | PostgreSQL data directory |
| backend/.local/postgres/server.log | Database operations log |
| backend/requirements-foundation.lock | Complete 30-package dependency lock for the tested Python 3.12 Windows environment |

There are separate rpa_admin, rpa_migrator and rpa_app database roles. The application role is not superuser and has no BYPASSRLS. Audit records cannot be updated/deleted by the app role. Scoped repository checks and composite workspace/connector foreign keys enforce the tested Stage 01 boundary; production FORCE RLS and external identity remain future pilot gates.

The PostgreSQL archive comes from EDB's official binary link reached through PostgreSQL's Windows download page. The local download.json records its source and computed SHA-256 for traceability; this is not a claim of an independently verified publisher checksum. No Windows service, global PostgreSQL installation or public listener was installed.

## Implemented API scope

- Login/logout, hashed expiring server sessions and persistent login throttling.
- Membership roles, workspace listing/read, independent demo/development scopes.
- Versioned/idempotent workspace rename and append-only audit receipt.
- Connector bindings/capabilities with honest modes and authenticated Shopify check.
- Compatibility snapshot shape through the new server, restricted to an authorised development-store member.
- Liveness/readiness, safe errors, request correlation, origin/CSRF/host checks and static-file boundaries.

Connector verification is a synchronous read-only check in Stage 01. Durable async connector operations, agent policies/plans/jobs and general action approval belong to later stages. The preserved standalone legacy server remains a loopback development connector; it has not gained the new server's authentication.

## Actual provider evidence

The authenticated Stage 01 smoke check returned HTTP 200, 20 products, four customer ID/order-count records, one order and ten drafts, with no Shopify warnings. These were real development-store reads; tests use explicitly synthetic adapter responses separately.

Razorpay, WhatsApp, voice, support and checkout execution are not implemented by this stage. Existing manually reconciled Razorpay evidence remains valid, but the new foundation does not claim automatic payment reconciliation. No message, charge, order creation or provider scope expansion was performed.

The structured smoke evidence is stage-01-smoke.json. Test evidence/report is recorded separately. Stage 02 begins after the owner reviews Stage 01 and instructs continuation.
