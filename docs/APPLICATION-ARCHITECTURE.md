# Repeat Purchase Agent — application architecture

Version 1.0 · 13 October 2026 · Architecture handoff for GPT-6.1-sol, low reasoning effort

This is the complete target application design requested by the owner. It builds on the approved 18-feature PRD and merchant UI v2. It is a design, not evidence that the target services have been implemented. The intended implementing model is a Codex setting; it is not the application's selected model provider.

## 1. Start here

Read [IMPLEMENTATION-HANDOFF.md](IMPLEMENTATION-HANDOFF.md) for the exact developer instructions and stage gates. Use this document for component ownership and decisions, [APPLICATION-CONTRACTS.md](APPLICATION-CONTRACTS.md) for schemas/APIs/state, and [RUNTIME-AND-VALIDATION.md](RUNTIME-AND-VALIDATION.md) for execution/recovery/test cases.

Authority, in order: latest owner instructions → approved PRD/product constraints → latest dated integration evidence → this architecture for technical defaults → merchant UI v2 for interface implementation → older specifications for requirements that remain compatible. Architecture does not reduce F01–F18. Existing UI handoff diagrams and screenshots remain useful; v1 composition is historical.

The design is a modular monolith: one FastAPI codebase, one PostgreSQL database, a web process and a durable worker process. Domain services control actions. A language model interprets and proposes. Provider adapters execute only an already validated command. The frontend renders server state and gathers explicit merchant decisions.

## 2. Verified starting point

These are recorded checks from the existing project, not new provider tests performed while authoring this design.

| Area | Existing evidence | Target work still required |
| --- | --- | --- |
| Requirements | F01–F18 approved on 12 October; same-product scope; all required demo journeys | Implement every acceptance condition |
| UI | Merchant v2 source/export, persisted synthetic interactions, desktop/mobile screenshots | Consolidate full entry/setup flow; replace local authority with server state |
| Shopify | Read-only FastAPI snapshot; 20 products, 4 customer IDs/order counts, 1 order, 10 drafts; protected-data purposes saved | Pagination, order lines/history/delivery, verified customer/channel mapping, production OAuth if multiple merchants |
| Razorpay | Test gateway active; one captured INR 127315 payment matched to Shopify #1001; credentials recorded as server-side | Durable automated mapping, signed webhooks, failure/refund tests and restart recovery |
| WhatsApp | Twilio trial account and Messaging API reads; exact join command received | Device linking, error 12300 diagnosis, purpose-specific test send, inbound/status callbacks, sender/template permissions |
| Backend | Small local connector and four recorded tests | Database, auth, domain engine, scheduling, model/speech adapters, outcome services |
| Purchase history | Three purpose-made test SKUs; paid test order remains unfulfilled | Qualifying delivered repeat histories with explicitly synthetic consent |
| Deployment | Private GitHub remote configured; newest integrations uncommitted | Reviewed commits, CI, host selection and owner-run deployment |

The current frontend only calls the Shopify snapshot. The manually verified Razorpay reconciliation is not an implemented payment adapter. Customer IDs/order counts do not supply verified phone mappings or consent. Generated draft orders do not qualify as purchases. Earlier notes about denied Shopify customer/order reads and an absent correct WhatsApp join command are superseded by the final entries in integration-status.md.

## 3. Technical decisions

The owner's stack choice is Python + FastAPI + PostgreSQL. The remaining choices below are architecture defaults, reviewable in this handoff. Do not ask the owner to choose routine folder names, ORM patterns or queue mechanics again.

| Decision | Target choice | Reason and boundary |
| --- | --- | --- |
| Backend structure | Modular FastAPI application with shared domain services | Keeps transactions and debugging within one codebase |
| Persistence | PostgreSQL 18 stable line; SQLAlchemy 2 async; psycopg 3; Alembic | Durable relational invariants, locks and migrations; resolve/pin compatible package versions at implementation |
| Background execution | PostgreSQL job/inbox/outbox tables; separate Python worker | Durable scheduling without adding Redis/Celery infrastructure initially |
| Frontend | React + TypeScript + Vite; React Router; TanStack Query | Typed contracts and server state; preserve v2 layout/CSS/copy during migration |
| Validation | Pydantic request/domain schemas plus DB constraints | Reject invalid model, browser and provider payloads before side effects |
| Public API | Same-origin REST under /api/v1; generated OpenAPI TypeScript types | One auth boundary; explicit commands and receipts |
| Updates | Poll active screens every 5 seconds initially; immediate cache invalidation after commands | Simple reliable initial delivery; add server events only if measured need justifies it |
| Checkout | Commerce-owned Shopify checkout with Razorpay gateway | Preserves commerce order creation and customer-reviewed total |
| AI runtime | Provider-neutral structured intent/proposal adapter; bounded orchestration | No provider credentials or vendor model names assumed |
| Voice | Browser, push-to-talk, turn-based STT → shared intent engine → TTS | Shares the text action engine and is straightforward to inspect; real telephony remains an additional verified adapter |
| Support | Durable internal case/owner workflow; optional external ticket adapter | Makes support functional even before an external system is selected |
| Authentication | Local owner bootstrap + server sessions for development; OIDC integration before external pilot | Separates app identity from the sample Razorpay login |
| Hosting | Portable containers/process commands; same-origin web/API + worker + managed PostgreSQL | Owner chooses host and deploys; no hosting account or public ingress assumed |

The existing FastAPI/httpx pins are the starting point, not a mandate to upgrade working packages. Generate dependency lock files after a compatibility smoke test. No microservices, vector database, unrestricted agents, long-lived browser provider secrets or extra workflow framework is needed for this scope.

React migration is deliberate implementation work in Stage 02. Keep the current inspectable previews operational until the replacement passes continuity checks. Do not install Blade solely because the shell is Razorpay-inspired; reuse the v2 semantic components and verify any future Blade adoption against actual package APIs.

## 4. System and trust boundaries

~~~mermaid
flowchart LR
    Merchant[Merchant browser] --> UI[React merchant workspace]
    Customer[WhatsApp customer] --> Twilio[Twilio adapter boundary]
    Voice[Browser voice test session] --> API[FastAPI authenticated API]
    UI --> API
    API --> Domain[Policies / plans / journeys / validator]
    Domain --> DB[(PostgreSQL)]
    Worker[Durable Python worker] --> Domain
    Worker --> AI[Structured model and speech adapters]
    Worker --> Commerce[Shopify commerce adapter]
    Worker --> Pay[Razorpay evidence adapter]
    Worker --> Twilio
    Commerce --> Shopify[Shopify checkout and orders]
    Pay --> Razorpay[Razorpay test gateway]
    Twilio --> Inbox[Authenticated webhook ingress]
    Shopify --> Inbox
    Razorpay --> Inbox
    Inbox --> DB
    DB --> Worker
~~~

All provider traffic is server-side. Browser voice sends audio only to the app's authorised session endpoint. Public webhook ingress verifies provider identity independently of merchant cookies and writes a durable inbox before acknowledging delivery. No model response reaches an external side-effecting adapter directly.

PostgreSQL is the source of truth for policies, approvals, consent, jobs, ownership and receipts. The React cache is a view. Browser storage may retain cosmetic UI preferences; it may not create consent, approve actions or confirm payments.

### Environment separation

Every workspace has an environment: demo, development or live. Every connector and receipt records its actual source mode: simulated, test or live. Do not collapse all providers into a single green global badge.

- Demo uses persistent deterministic adapters and an injectable clock, with no external sends.
- Development may read the real Shopify development store and Razorpay test account. A Twilio trial is a real communication service: test messaging still requires an explicitly authorised verified recipient.
- Live stays disabled until all live gates pass. The development payment adapter rejects live Razorpay keys.

Historical synthetic UI data are never silently imported into development as real source evidence. Use separate workspaces and environment-scoped provider identities. Production data access and deployment remain independent release decisions.

## 5. Module ownership

| Module | Owns | Must not own |
| --- | --- | --- |
| identity | Sessions, memberships, roles, active workspace | Razorpay merchant passwords |
| connectors | Credential references, capabilities, sync checkpoints, health, mode | Inferring capabilities from account existence |
| commerce | Variants, order lines, delivery/return evidence, checkout preparations | Marketing consent or model-generated stock |
| customers | Scoped identities, channel mappings, explicit consent/preferences/suppression | Fuzzy cross-tenant matching |
| policy | Immutable operating-policy versions, active version, changes | Provider requests |
| opportunities | Deterministic eligibility, repeat windows, exclusions and evidence | Dispatch permission |
| plans | Drafts, immutable audience/scope revisions, approvals/expiry | Sending outreach during activation |
| journeys | Customer/SKU progression, owner, support/reminder transitions | Replacing payment/channel states with one status |
| agent | Minimal context assembly, model calls, validated intent proposals, evaluations | Approval authority, raw credentials or money arithmetic |
| execution | Action validator, reservations, dispatch attempts, reconciliation and caps | Invented provider idempotency |
| communications | Message templates, channel sessions, transcripts, provider statuses | Independent channel schedulers |
| support | Owned cases, sales blocking, optional ticket receipt | Automatic sales resumption after ticket creation |
| outcomes | Order/payment matching, costs, cohort metrics and learning proposals | Causal lift from observed orders |
| events | Webhook inbox, domain outbox, typed event routing, audit | Calling models in webhook acknowledgement |
| operations | Health/readiness, job backlog, failed/unknown work, diagnostics | Resetting safety state as a recovery shortcut |

Routers call application services. Services open a unit of work and call repositories. Domain functions implement pure decisions. Adapters translate provider-specific requests/responses into typed application contracts. Tests can replace adapters and the clock without changing domain logic.

## 6. Full merchant journey

| Surface | Target server responsibility | Interaction and completion |
| --- | --- | --- |
| Sample entry/payments home/Studio | Demo-only reference route; real app session is separate | Preserve full approved entry experience without collecting real Razorpay credentials |
| Agent detail/My Agents | Agent installation and mode/capability read model | Install/open with clear same-product scope |
| Configure → Connectors → Review → Activate | Saved installation draft, policy, capability preflight and installation record | Activation alone creates no contact job; unavailable required roles block that environment's execution |
| Connections | Actual provider capabilities, permissions, source age, sync/repair result | Existing Shopify data stay reviewable; each unavailable action has a specific blocker |
| Dashboard | Decision queue, exclusive journey counts, policy, health, verified outcomes | Safety/support/unknown execution outrank routine approvals |
| Opportunity/plan review | Candidate evidence, exclusions, selected IDs, immutable version | Exact audience/limits/timezone; approval revalidates; stale scope returns a review diff |
| Activity/customer drawer | Customer words, interpreted intent, next step, chronological messages, evidence/receipts | Approve action, takeover, support assignment or status check in context |
| Settings | Policy diff and immutable version creation | Affected approvals/jobs invalidated; show review required |
| Outcomes/learning | Cohort/window, verified orders, calculation completeness and proposals | Include outside-link orders; no lift/profit claim without supporting data |
| Test mode | Scenario selection/reset in demo workspace only | Never erase development provider records or provider receipts |

One shared app shell and accessible Dialog/Drawer/Field/Button/Status/Receipt/Evidence components support all surfaces. Preserve merchant v2 hierarchy. Avoid a second generic chatbot page. Contextual questions use scoped read-only evidence and show a link to the underlying plan/journey.

### Server read models

Dashboard and journey endpoints aggregate domain data for the UI; do not require the browser to join raw payment, contact and consent tables. Each response includes workspace environment, source modes, generated_at, resource version and available commands with blocked reason codes. Allowed-command hints improve copy but do not replace server validation.

Optimistic UI is allowed for expansion, search and selection. Approval, sending, pause, takeover and payment states use server-confirmed results. Pending requests disable duplicate submission. Errors preserve draft inputs. A receipt remains inspectable after a toast disappears.

## 7. Opportunity and policy design

Opportunity identification is deterministic in the first complete implementation. The model is useful for natural/compound replies and grounded explanations, not for guessing which paid order was delivered.

An evidence bundle contains exact variant, qualifying delivered line items, quantities, delivery dates, returns, newest relevant order, channel consent, open issues, stock, contact history and source timestamps. Any required missing source produces a named exclusion/block, rather than a guessed empty history.

Estimator version repeat_window_v1:

1. Explicit customer-confirmed reminder date takes precedence over estimates. Preserve its exact timezone and channel.
2. Use at least two positive intervals from three qualifying delivered same-variant purchases with compatible quantities. Compute median interval and median absolute deviation. Proposed window: last delivery + median ± max(1 day, MAD), with a non-negative start. Save evidence references and algorithm version.
3. Different quantities remain visible; do not silently scale consumption by quantity. Insufficient comparable history uses a merchant-configured product-level repeat window, with its provenance shown.
4. If neither history nor a product fallback exists, return needs_history. Do not fabricate a timing score or automatically schedule.
5. Reject impossible dates/intervals as data exceptions. Window estimates are planning aids, not calibrated probabilities.

These estimator rules are proposed transparent defaults to validate with fixtures; they are not demonstrated predictive accuracy. Production product defaults require merchant configuration and review. Model-based timing can be evaluated later against this baseline without weakening eligibility.

Eligibility checks exact same variant, delivered qualifying purchase, no newer relevant purchase, no unresolved return/issue, applicable channel permission, no opt-out, product scope/stock, source coverage and shared campaign coordination. The plan records selected and excluded rows with reasons; dispatch checks these again.

Policies are immutable versions with products, permitted action types/channels, timezone, contact hours/quiet hours, contact-window/cap, spend limits, offer allowlist, margin requirements, review mode and expiry rules. Fixture defaults are synthetic settings only. Required unset limits block actual dispatch. A new policy invalidates affected queued actions; it does not erase historical orders or preferences.

## 8. AI application design

Use one bounded intent interpreter and deterministic orchestrator. Avoid a network of agents for this product.

### Input and output

The interpreter receives the latest customer utterance, a bounded chronological context, unresolved confirmation fields, policy summary and a reference-addressable facts bundle. Mask or omit names, contact destinations, addresses and unnecessary order details. Tenant/customer/plan identity is supplied by the server and never taken from model output.

Output is a strict IntentProposal: one or more recognised intents, direct evidence spans, requested SKU/quantity/date/channel where stated, missing confirmations and a proposed semantic next step. Unsupported fields fail schema validation. The server binds all referenced facts to the current context and generates a typed ActionProposal. The model never outputs an authorised provider call.

Use a fixed system instruction, versioned task prompt and JSON-schema contract. Customer content and provider notes are data. Never inject them into system instructions. No arbitrary HTTP, SQL, filesystem, shell, recipient selection, discount creation or billing tools are exposed.

### Protective routing and ambiguity

Explicit opt-out, refusal and complaint/product-dislike paths are handled ahead of sales. High-certainty configured opt-out tokens run without a model. A model-recognised opt-out invokes deterministic suppression; ambiguity conservatively holds sales and requests review/clarification. Do not reject protective action because an unrelated checkout field is missing.

Compound replies preserve independent intentions: “remind me Friday; is my coupon valid?” becomes a date-confirmation task and a verified-offer enquiry. Confirm vague dates using workspace timezone and actual event time. No reminder is scheduled from an ambiguous voice transcript.

Read-only factual answers come from current facts and templates. Render monetary values/links through code using verified references. Model-authored language must not introduce prices, discounts, stock promises, shipping guarantees or urgency absent from those facts.

### Bounded execution

Per inbound turn: one interpretation, at most one repair attempt for invalid structured output, and at most two rounds of scoped read-only fact retrieval. These are engineering limits, configurable per provider and measured in tests. Side effects run separately through execution. A timeout or repeated schema failure leaves the journey held with an actionable exception.

Log provider/model ID, prompt/schema version, context fact IDs, latency, token/cost receipt if available, parsed proposal and validation result. Record concise reasons, not hidden reasoning. Store no secrets in traces. No model is selected until the owner reviews capability/cost/latency evidence; deterministic adapters allow other stages to proceed.

## 9. Provider integration plan

### Shopify

Refactor the working read-only connector into a ShopifyAdminAdapter while preserving the existing snapshot endpoint as a compatibility facade. Keep same-organisation authentication for the current owned development store. Multi-merchant installation needs a verified OAuth contract and tenant credential isolation before external use.

Add paginated sync checkpoints and explicit coverage. Required execution facts include order lines, customer mapping, financial/fulfilment/delivery/return evidence and variant sellability for the appropriate market/location. Do not infer delivery from PAID or FULFILLED.

Use a separate ShopifyStorefrontAdapter for cart creation and checkout URL retrieval. Existing Admin read scopes do not establish Storefront cart capability. Until access is verified, the development checkout command returns CAPABILITY_UNVERIFIED; the demo adapter still demonstrates the full flow. Cart IDs and checkout URLs contain sensitive tokens: keep them scoped, redact logs, avoid query-string exposure and do not attach names/phones in cart correlation metadata.

Shopify cart estimates can change at checkout; the customer reviews final charges there. Use exact variant IDs, confirmed quantity and opaque journey/action correlation attributes if their cart-to-order propagation is verified. The current browser-tested cart permalink is evidence of a test path, not a complete automated cart contract. [Shopify cart guide](https://shopify.dev/docs/storefronts/headless/building-with-the-storefront-api/cart/manage)

### Razorpay and reconciliation

Implement a server-only read/evidence adapter for the development account. Native Shopify checkout owns the gateway order; the agent does not create a second Razorpay order for that checkout. The standalone INR 499 test order in earlier evidence is unrelated to Shopify #1001.

Purchase confirmation requires commerce order, exact provider account/mode, captured payment, matching currency/amount and a verified cross-system transaction/order reference. Do not match on email, total or approximate time alone. The recorded test matched Shopify transaction paymentId to the Razorpay order receipt; this is useful evidence but requires a versioned adapter contract test before reuse. No durable mapping is assumed from undocumented receipt JSON.

Unknown payment/order links become owned reconciliation exceptions; relevant outreach is held while evidence is refreshed. Refunds/returns update accounting rather than erase purchase history. Webhook duplicates and delayed authorised events cannot regress a captured status. [Razorpay webhook validation](https://razorpay.com/docs/webhooks/validate-test/)

### WhatsApp

Continue with Twilio as the account already set up. Capabilities are granular: read_records, trial_template_send, receive_inbound, receive_status, session_free_text, approved_reorder_template. An authenticated account does not imply all are available.

The new trial flow allows provided ContentSid templates to verified recipients and does not support direct TwiML response. Keep this provider restriction distinct from app approval. A generic trial template proves transport only; it does not prove proactive replenishment or a free-text agent conversation. [Twilio trial guide](https://www.twilio.com/docs/usage/trials/try-out-whatsapp)

Do not ask the owner to resend the correct joining command again: its receipt is verified. Diagnose trial linking, sender/tester association and inbound response configuration. Error 12300 identifies invalid content type; it does not prove a specific root cause. [Twilio error 12300](https://www.twilio.com/docs/api/errors/12300)

Map verified inbound account/sender/recipient to one tenant/customer; unmapped senders are quarantined. Apply the actual session/template rules for the selected sender. No custom template or proactive customer send proceeds merely because a plan is approved.

### Voice and support

Browser voice is a separate consented test session, not a telephone call. Start/stop/mute/replay controls have requesting_permission, recording, processing, speaking, stopped and error states. Speech adapters return transcript/evidence; both text and voice use the same interpreter, validator and contact ledger.

Use short recorded turns first. Default development limits: 60 seconds/turn and 10 MiB upload, configurable engineering limits with visible error copy. Restrict supported MIME types; record only while the control is active. Raw audio is transient and deleted after processing by default. Persistent recordings require explicit retention/consent selection before live use. No uncontrolled background microphone.

Internal support cases retain owner, issue, receipt and unresolved state. If an external provider fails, keep sales held and expose an owned exception. Ticket creation is not issue resolution.

### Campaign coordination

In demo, the shared ledger owns all synthetic campaigns. In development, no autonomous outbound campaign runs unless the owner declares that all outreach for those explicitly authorised test recipients passes through this ledger.

For a real merchant, require campaign cohort exclusion and contact/reservation exchange with external campaigns. Lost coordination blocks affected dispatch. Importing historical messages is not equivalent to coordinating future sends.

## 10. Security, data and operations

Every authenticated read/write resolves workspace membership from the server session. User-supplied tenant IDs are never authority. Data uses environment-scoped composite foreign keys and unique provider identifiers. See APPLICATION-CONTRACTS.md.

Development auth bootstraps one owner via a local CLI/env-backed credential, stores a password digest and issues a random hashed server session with HttpOnly/SameSite cookie. There is no password in source or seeded fixture. CSRF protection and origin checks cover mutations. Production sessions require TLS/Secure cookies; rate limit authentication. OIDC provider selection and account lifecycle are gates before external pilot. A loopback bootstrap cannot be publicly deployed unchanged.

Webhook signatures are provider-specific: verify Shopify/Razorpay raw bytes and use Twilio SDK request validation with the configured external callback URL and all received parameters. Trust forwarded headers only from configured ingress proxies. Invalid signatures are rejected; database failure produces retryable failure, not a false acknowledgement. [Shopify verification](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries), [Twilio security](https://www.twilio.com/docs/usage/security)

Keep provider credentials in the existing ignored server file for local development, then in deployment secret storage. Credential references are stored in DB, secrets are not. Never expose .env or backend folders through static hosting. Add secret scanning and log redaction. Encrypt sensitive channel identifiers/transcripts at rest with a configured key and restrict payload access.

Retention is configurable per workspace/data type. Development raw audio is transient; demo resets erase only demo records. Live transcript, message, webhook-payload and audit retention/deletion policies require owner selection before live pilot. Implement deletion/export and de-identification with minimal non-PII deduplication tombstones; do not promise indefinite immutable personal data.

Operational views show worker heartbeat, oldest due job, inbox/outbox backlog, pending/unknown attempts, connector freshness and reconciliation age. Emit structured logs with correlation/action/event IDs and masked destinations. Measurements include response/model/dispatch latency, blocked reasons, delivery failures, cost completeness and guardrails. Missing model costs block profit completeness, not deterministic opt-out processing.

Run migrations as a separate one-shot operation; API and worker verify schema readiness at startup. API liveness checks process status; readiness checks DB/schema and required configuration. Worker failure leaves durable jobs recoverable. Backup/restore, rollback and failed migration rehearsal are release gates.

Portable deployment topology: static frontend served at the same origin as the API, private worker, managed PostgreSQL, TLS ingress for authenticated APIs and signed callbacks. No public access to the current loopback connector. Polling with sync lookback can support local development before public webhook configuration; mark freshness/coverage and do not call it real-time.

## 11. Outcomes and learning

Record original order lines/discounts/taxes/shipping/refunds and separate cost components. Money uses currency-aware integer minor units with Decimal conversion at provider boundaries. Never compare different currencies or treat missing costs as zero.

Net revenue follows an explicit merchant accounting basis: item sales after discounts/refunds, stated tax treatment, shipping revenue shown separately if included. Net contribution subtracts product, fulfilment, gateway, communication and model/agent costs once. Return-maturity and allocation assumptions are visible; unavailable required inputs yield contribution unavailable.

Cohort assignment is immutable and exists separately from current plan state. Count each qualifying subsequent brand order once within its declared window, including orders outside agent links. Same-SKU outcomes are a drilldown. Declines, waiting and support cases remain valid journey states, not invented failed conversions.

Confirmed dates/preferences are saved as customer-stated evidence. One-off WhatsApp checkout handoff does not establish a permanent channel preference. Broader timing/offer/policy suggestions show evidence and a proposed diff and require merchant review.

Future rollout measurement uses a comparable eligibility pool with immutable treatment/control assignment, campaign coordination and matured returns. Persist assignment even when a customer is suppressed or never contacts the agent. Incremental contribution is difference in average contribution per assigned eligible customer; use net revenue fallback when reliable costs are absent. Until a valid comparison exists, incremental lift and merchant time saved remain not measured.

## 12. Proposed repository structure

~~~text
frontend/
  index.html, src/design-preview.fragment.html   # preserved original reference
  merchant-preview.template.html
  merchant-app.css, merchant-app.js
  design-handoff.html, build-preview.mjs         # preserved v2 reference
  app/                                         # new application, Stage 02
    src/app/                                   # routes, auth boundary, shell
    src/components/                            # semantic shared controls
    src/features/                              # domain surfaces
    src/api/                                   # generated types, typed client, queries
    src/styles/                                # migrated v2 CSS
    tests/                                     # meaningful journey/focus tests
backend/
  shopify_app.py, test_shopify_app.py            # compatibility during migration
  app/
    main.py, settings.py
    api/                                       # routers, dependencies, error envelope
    domain/                                    # pure rules/types
    services/                                  # transactional use cases
    repositories/                              # scoped database access
    adapters/                                  # Shopify, Razorpay, Twilio, speech, model, demo
    jobs/                                      # worker, scheduler, inbox/outbox, reconciliation
    security/                                  # sessions, CSRF, signature validation
    observability/                             # structured log/health diagnostics
  migrations/
  tests/unit/, tests/integration/, tests/contracts/
  tests/evals/                                 # labelled input/proposal/authority cases
  scripts/                                     # bootstrap, fixture, run, check
docs/
  APPLICATION-ARCHITECTURE.md
  APPLICATION-CONTRACTS.md
  RUNTIME-AND-VALIDATION.md
  IMPLEMENTATION-HANDOFF.md
  implementation-evidence/                      # later stage reports/screenshots
~~~

Use feature/domain names consistently across API, database and UI. Avoid placing all services in one large router or all components in one render file. Existing source folders remain preserved until replacement coverage is demonstrated.

## 13. Unresolved choices and implementation defaults

| Choice | Default while unresolved | Resolve before |
| --- | --- | --- |
| Model/STT/TTS provider | Deterministic test adapters and provider-neutral contracts | Real model/audio stage |
| Storefront access/cart-to-order mapping | Demo checkout; development capability explicitly blocked | Automated Shopify checkout |
| WhatsApp trial/custom sender/template | Transport diagnostics; synthetic full agent conversation | Purpose-specific real messaging |
| Delivery source | Labelled fixtures; paid/unfulfilled test order remains ineligible | Real opportunity calculation |
| Production login/hosting | Loopback owner session and portable topology | External pilot/deployment |
| Support provider | Real internal owned case workflow | External ticket promises |
| Live contact/economic/retention policy | Unset required fields block live execution | Live mode |
| Campaign coordination integration | Sole-owner test-recipient declaration only | Real merchant outbound |
| Agent Studio private deployment | Standalone Razorpay-inspired application | Claiming native installation/access |

No consequential choice is hidden behind a simulated success badge. Account or permission gaps block that adapter capability; they do not delete the corresponding product feature.

## 14. Primary technical references

Checked while authoring on 13 October 2026. These references inform the proposed design; they do not verify account capability. Recheck versions and provider access when implementing.

- [FastAPI modular applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) — router/module organisation.
- [SQLAlchemy async sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — isolate sessions per concurrent task.
- [PostgreSQL SELECT locking](https://www.postgresql.org/docs/current/sql-select.html) — queue claims using SKIP LOCKED; domain rows use ordinary locking.
- [React application setup](https://react.dev/learn/creating-a-react-app), [Vite guide](https://vite.dev/guide/), [React Router installation](https://reactrouter.com/start/declarative/installation), [TanStack Query overview](https://tanstack.com/query/latest/docs/framework/react/overview) — proposed client build and server-state tools.
- [Shopify webhook structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure) — delivery identity and event correlation.

All uncited application rules, TTLs, folder layouts and engineering limits are project design choices, not provider guarantees.
