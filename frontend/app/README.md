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
