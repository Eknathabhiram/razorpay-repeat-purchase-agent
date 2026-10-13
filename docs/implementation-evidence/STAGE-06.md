# Stage 06 — WhatsApp transport and inbound protection

13 October 2026 · ready_for_review · account-backed messaging remains blocked

Review [WhatsApp](http://127.0.0.1:8766/app/#/whatsapp) with the existing owner account. Demo uses the same persisted Planning/Execution journeys, approvals, dispatch receipts, contact guards and checkout pipeline. No external message was sent, callback registered, public endpoint deployed or paid sender activated.

## Implemented

Migration 0006_whatsapp adds account-bound recipient identities, delivery projections and immutable inbound/status evidence with composite workspace foreign keys. Application grants permit only delivery status/error updates; identities and events are append-only.

Inbound callbacks validate the complete form using the official Twilio 9.12.0 RequestValidator, configured public URL, primary auth token, account, connector source mode and exact sender/recipient. No forwarded host is trusted. Query strings, duplicate form fields, oversized bodies and unsupported encodings are rejected. Missing credentials/public URL or SDK fail closed. Replay keys include account-scoped MessageSid and event type; conflicting content cannot silently replace evidence. Unmapped identities are quarantined without retaining their message body or granting consent.

Owner-reviewed recipient mapping requires an authenticated read of an exact inbound MessageSid from the specified WhatsApp address to the configured sender, plus explicit customer-identity confirmation. This proves sender control and records the owner's mapping decision; it does not create marketing consent or permit generated Shopify customers to be contacted. This path is covered with mocked provider reads, not a real account-backed verification.

Every mapped reply cancels competing unsent work across the customer's journeys and scheduled reminders. Opt-out and refusal create durable suppression. Support opens an owner-assigned case. Purchase interest, reminder requests and unclear language enter human review; no date, consent, checkout, payment or purchase is inferred. Late replies cannot erase existing opt-out, support or purchase protection. An explicitly owned, separately approved acknowledgement/checkout link can use the existing human workflow; ordinary agent work remains blocked. This is deterministic conservative routing; language-model interpretation is Stage 07.

Demo delivery projections are attached to existing immutable submission receipts. Read evidence survives delayed sent/delivered updates. Contradictory success/failure evidence requests authoritative refetch and holds competing work, rather than changing purchase truth or replaying a submission. TwilioTransport.read_message supplies the account-bound read adapter for reconciliation. Automated public delivery and reconciliation scheduling remain release work because real transport is disabled here.

The template adapter supports only explicit recipient/template authority, a ContentSid and the configured origin for an optional status callback. It sends no free-form Body or unverified trial variables. Timeout, HTTP 5xx or an ambiguous response produces unknown with retry disabled. No application API/UI invokes real send_template: Development/live dispatch remains blocked behind unverified transport, consent, facts, policy and exact message capabilities. All adapter outbound tests use MockTransport.

## Provider evidence and limitations

The previously verified correct join receipt remains valid historical evidence; do not ask the owner to repeat it. The existing standard provider auto-reply is not an application test send. Earlier inbound error 12300 indicates invalid response Content-Type; its precise provider-side configuration cause has not been established.

Current backend/.env contains Shopify and Razorpay fields, but no Twilio credentials. The new trial last showed a device-link screen without test-send controls. Its provided templates/custom reorder capability and public callback delivery remain unverified. No account-backed MessageSid was newly obtained in this stage.

New trial documentation explicitly excludes direct TwiML XML responses. Our ingress returns an empty JSON acknowledgement and sends no auto-reply. This local handler is tested; acceptance by the actual new trial is not claimed. A deployed callback and actual authorized tester evidence are needed before declaring transport verified.

Server-side configuration, after provider/deployment review: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM and TWILIO_CALLBACK_BASE_URL. Never substitute an API key secret for the primary webhook auth token. Do not expose values in frontend files. Identity review is POST /api/v1/workspaces/{id}/whatsapp/identity-review. Callbacks are POST /api/v1/providers/twilio/{workspace}/{connector}/inbound or /status.

Official references: [signature validation](https://www.twilio.com/docs/usage/security), [new WhatsApp trial constraints](https://www.twilio.com/docs/usage/trials/try-out-whatsapp), [error 12300](https://www.twilio.com/docs/api/errors/12300). Trial and legacy Sandbox behaviors must not be combined.

## Actual validation

- Seven initial Stage 06 cases plus all eleven shared execution regressions: 18 passed in 197.482 seconds, stage-06-tests.txt.
- Exact reviewed identity routing/no marketing consent, checkout-link regression and all four original Shopify compatibility checks: six passed in 40.222 seconds, stage-06-final-tests.txt.
- The signature test uses Twilio's published known vector and checks changed URL/invalid signature. Callback tests cover authenticated ingress, account mismatch, duplicate messages, unmapped quarantine, bad encoding and tampering.
- Adapter contract checks cover exact template authority and timeout with no automatic retry. PostgreSQL tests cover shared reply cancellation, duplicate/conflicting event keys, Development separation, support/opt-out protection, delivery ordering and contradiction holds.
- Actual OpenAPI export, generated TypeScript and Vite production build passed (97 modules, lazy WhatsApp chunk).
- Eleven browser checks passed with no page errors: contextual messages, read ordering, purchase-interest review, opt-out/shared journey updates, Development separation, and widths 1440/1024/768/390/320. See stage-06-browser.json and stage06-screens/. The rendered 390px view was inspected; accessibility certification is not claimed.

The first SDK download failed due to DNS; the retry installed the official SDK successfully. No custom cryptographic fallback is used. Setup installs the pinned application lock with --no-deps; the Twilio dependency is used only for its standalone RequestValidator and HTTP uses existing httpx.

## Run and next stage

Use backend/run-foundation.ps1; schema is 0006_whatsapp. Preserve the owner account and private provider configuration. Run python -m unittest tests.test_whatsapp tests.test_execution -v in the configured foundation environment. frontend/app/tests/whatsapp-check.mjs uses an isolated private QA tenant prepared by backend/scripts/prepare_stage05_qa.py; it never resets the owner's workspace.

Stage 05 was accepted for continuation by the owner's “next stage too”. Stage 06 is ready for review with explicit account-backed transport limitations. Stage 07 adds AI interpretation and browser voice after owner review and continuation.
