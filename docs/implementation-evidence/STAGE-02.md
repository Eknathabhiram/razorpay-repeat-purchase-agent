# Stage 02 — application UI handover

13 October 2026 · ready_for_review

Review [the application](http://127.0.0.1:8766/app/) using the existing Stage 01 owner login. The ignored backend/.local/owner-access.json contains local owner access details. Do not commit credentials. The original /foundation review and merchant design references remain available.

## Implemented scope

React, TypeScript and Vite application in frontend/app, preserving merchant UI v2 styling. Entry, verification, Payments, Agent Studio, My Agents, installation, Dashboard, Activity, Settings, Plan, Outcomes and Connections are implemented. Contextual drawers support plan review, policy differences, pause/resume, takeover/handback and simulated checkout review.

Owner login, session restoration, workspace selection and connector access use the actual scoped backend. Cookie sessions and CSRF survive reload without browser storage becoming authoritative. Generated OpenAPI types describe the UI API. Viewer controls disable mutation; backend authorization independently enforces roles.

Demo commands use PostgreSQL-backed, versioned, idempotent simulation state and audit records. Policy changes invalidate plans. Paused/disconnected states block relevant commands. First-plan scenarios do not fabricate replies, payments or orders. Development mode shows actual read-only Shopify data and keeps agent execution unavailable.

## Validation

- 18 PostgreSQL/application tests passed, including the original 13 foundation tests. See stage-02-tests.txt.
- All four preserved Shopify connector tests passed. See stage-02-compatibility-tests.txt.
- Strict TypeScript check and production Vite build passed.
- Main browser suite passed 17 recorded checks, covering six principal screens at 1440, 1024, 768, 390 and 320 pixels, session reload, keyboard dialog containment, Escape/focus return, policy invalidation, pause, installation, source separation and logout. See stage-02-browser.json and stage02-screens/.
- Five supplemental browser checks passed: takeover/handback, persistent policy validation error with retained draft, disconnected approval prevention, provider error/retry UI, and viewer controls. See stage-02-browser-edge-cases.json. Viewer UI projection is mocked in that check; backend role enforcement is tested separately.
- Rendered desktop/mobile screens and doubled-text layouts were inspected. Text enlargement is not a claim of actual browser zoom or full accessibility certification.

## Run and rebuild

Start the backend from the project root with ./backend/run-foundation.ps1. The installed database schema is 0002_demo_ui. Existing Stage 01 database/migration commands are in STAGE-01-RUNBOOK.md. Do not reset owner credentials or databases when restarting.

From frontend/app, use pnpm install --frozen-lockfile, pnpm run check and pnpm run build. The backend serves the generated dist at /app/. Regenerate the API schema with backend/scripts/export_openapi.py in the configured backend environment, then pnpm run types before building after API changes. The dependency lock and explicit esbuild build permission are checked in. Build output and node_modules are ignored.

Browser tests are frontend/app/tests/browser-check.mjs and browser-edge-cases.mjs. They use an isolated local QA tenant prepared by backend/scripts/prepare_stage02_qa.py; its private access file is ignored. They require the local database/backend and a supported Edge installation. The Vite development proxy is configured, but a separate-origin development session needs matching backend allowed-origin configuration; the reviewed build is served from the backend origin.

## Boundaries and next stage

The demo state is a UI simulation contract, not the production opportunity/policy/execution engine. Its policy budget preview uses whole INR values; production money contracts require explicit currency and minor units. Fixture copy never establishes provider facts. Shopify reads are projections, not persisted normalized commerce facts.

Stage 03 implements normalized facts, eligibility, production policy versions and opportunities after owner review. Messaging, browser voice/AI, scheduled execution, support case processing, checkout creation and automated payment reconciliation remain later stages. No external messages, charges or deployment occurred in Stage 02. Full screen-reader, contrast and actual browser-zoom certification remain open.
