## End-to-end delivery — 13 October 2026

The owner instructed completion through outcomes/release validation and made voice last priority. The text-first local hybrid application is ready for review at http://127.0.0.1:8766/app/#/dashboard. Read docs/RELEASE-HANDOVER.md and docs/implementation-evidence/STAGE-07.md, STAGE-08.md, STAGE-09.md. Schema is 0008_outcomes. Together AI is configured privately and verified with synthetic inputs. Planning, exact approval, protected replies, checkout, independent payment matching, refunds, cohorts, scoped learning and owner-reviewed policy changes form the persisted end-to-end pipeline. Optional browser voice was checked last. Real Storefront/Twilio/public deployment and production retention/coordination gates remain blocked; no customer outreach, new real payment, refund or deployment occurred. Preserve credentials/data and prior code. Earlier stage notes below are historical.
## Stage 06 implemented — 13 October 2026

Stage 05 was accepted for continuation by the owner's request for the next stage. Stage 06 is ready for review at http://127.0.0.1:8766/app/#/whatsapp. Read docs/implementation-evidence/STAGE-06.md and docs/implementation-evidence/STATUS.md. Schema is 0006_whatsapp. Official SDK signature checks, exact recipient review, inbound protection, contextual Demo conversations and monotonic delivery receipts are implemented. Twenty-four backend checks and eleven browser checks passed. Twilio credentials/test-send controls and actual callback delivery remain unavailable/unverified; no real message was sent. Preserve the correct historical join receipt and do not ask for another join. Stage 07 follows owner review and continuation. Earlier notes below are historical.
## Stage 05 implemented — 13 October 2026

Stage 04 was accepted for continuation by the owner's request for the next stage. Stage 05 is ready for review at http://127.0.0.1:8766/app/#/commerce. Read docs/implementation-evidence/STAGE-05.md and docs/implementation-evidence/STATUS.md. Schema is 0005_commerce. Demo checkout terms, separate link approval, independent payment evidence, reconciliation/refunds and approved offer controls are implemented. Read-only Development verification matched one Razorpay test payment to the full Shopify payable of INR 1,273.15. Fifty application tests, four compatibility tests and fourteen browser checks passed; four final source guards also passed. Real Storefront cart creation and callback delivery remain unconfigured. Preserve credentials/data and existing changes. Stage 06 follows owner review and continuation. Earlier stage notes below are historical.
# Merchant frontend

React/TypeScript application served at `/app/`, with same-origin `/api/v1` requests. The standalone merchant design reference is preserved separately. Application styles live in `src/styles`: `base.css` preserves the established shell, `app.css` provides journey components, and `production.css` defines the polished application layouts.

## Local commands

Use the locked dependencies with Node 22.18+ (Node 26.4 was verified) and pnpm.

```powershell
pnpm install --frozen-lockfile
pnpm dev
pnpm check
pnpm build
pnpm test:api
pnpm test:browser --workers=2
pnpm audit --prod
```

Development runs on loopback port 5173 and forwards API requests to the existing backend on 8766. The backend serves the compiled `dist` directory at `/app/`. `pnpm preview` previews the built assets; authenticated use still requires the same-origin API server or reverse proxy.

The production browser suite starts its own loopback server on 5174, uses installed Microsoft Edge, and intercepts all API requests with synthetic fixtures. It requires no merchant credentials and makes no provider calls. Existing stage browser scripts remain available for integration checks against the running authenticated backend; they are separate from this frontend suite. Screenshots/traces are saved under ignored `test-results/` and `playwright-report/`.

## Verified frontend behavior

- Responsive dashboard, audience planning, approvals, checkout, settings and connections at 320, 390, 768 and 1440 pixels; no document overflow or uncaught browser errors in the tested fixtures.
- Focus containment/restoration in customer drawers, visible drawer action footers, and keyboard/backdrop dismissal of mobile navigation.
- Recoverable session/service outages, session-expiry cache clearing, failed sign-out feedback, and unknown-page recovery.
- Last loaded workspace data stays visible after a polling failure, with approval controls blocked pending refresh.
- Timeouts, non-JSON proxy errors, uncertain write outcomes, cancellation, CSRF and idempotency headers covered by API-client tests. Mutations are never automatically retried.
- Automated WCAG A/AA checks on six key screens at desktop/mobile widths found no violations. This is automated coverage, not certification or complete assistive-technology validation.

## Release boundary

This branch contains a polished frontend and production build. It does not enable live outreach, production payments or unfinished backend stages. Demo remains explicitly simulated; Development capabilities remain separately labelled. The local backend was unavailable during this frontend verification, so authenticated integration checks were not rerun here.

For a hosted release, serve `/app/` and `/api/v1` under the same HTTPS origin, verify the backend's production session/cookie configuration, and apply hosting security headers. Serve `index.html` with revalidation and content-hashed assets with long immutable caching. Do not cache authenticated API responses. Preserve `/app/` as the asset base and the hash router's workspace URLs. Hosting and provider launch verification remain release prerequisites.

Visual evidence and the verified change summary are in `../../docs/implementation-evidence/FRONTEND-POLISH.md`.
