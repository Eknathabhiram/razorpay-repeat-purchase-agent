# Frontend

`app/` is the current React/TypeScript merchant application, served by FastAPI at `/app/`. It includes the latest Avime Herbal dashboard and campaign, offer, audience and conversation review work.

From `app/`, run `pnpm run check`, `pnpm run build`, `pnpm run test:api` and `pnpm run test:browser`. The Vite development server proxies `/api` to loopback port 8766.

`design-handoff.html`, `merchant-preview.template.html`, `merchant-app.css`, `merchant-app.js` and `build-preview.mjs` retain the v2 design/compatibility reference. They are not the application entry point. The obsolete v1 preview/source/tokens have been removed during consolidation.
