# Integration setup and verified identifiers

Updated: 13 October 2026. No secrets belong in this document.

## Delivery decisions

- Owner selected Python + FastAPI + PostgreSQL.
- Owner requires testing and reviewing every stage before moving forward. Latest request explicitly authorises connecting the frontend to Shopify through the small FastAPI server; full backend construction remains outside this stage.
- Shopify account/development store and replenishment products were reviewed; owner authorised moving to the next stage.
- Authenticated Shopify shop/product/inventory/location reads and frontend catalogue rendering are verified. Customer/order access, payment tests, messages and voice calls are not verified.

## Shopify account and store

- Partner organization: Repeat Purchase Agent; Partner dashboard organization ID: `5249995`.
- Developer Dashboard organization ID: `240407436` (distinct from Partner ID).
- Store name: Repeat Purchase Agent Test.
- Domain: `repeat-purchase-agent-test.myshopify.com`.
- Admin: https://admin.shopify.com/store/repeat-purchase-agent-test
- Store ID shown in Developer Dashboard login link: `78934507683`.
- Verified registry type: Dev; Basic feature tier. Generated test data selected at creation.
- Store currency changed from USD to INR before adding our fixtures. Original generated sample prices were not converted/repriced; do not use them as replenishment fixture prices.
- Store entity/address defaults to United States and timezone defaults to Eastern Time, as observed in General settings. INR does not establish Indian store/gateway compatibility; regional setup remains to verify before Razorpay checkout tests.
- Product list: 17 Shopify-generated products plus 3 project fixtures = 20 products, observed in admin.

## Project fixture products

| Product | Shopify product ID | SKU | Price (INR minor units) | Initial available stock |
| --- | --- | --- | ---: | ---: |
| Laundry Liquid - 1 L | `15430840615075` | `TEST-LAUNDRY-1L` | 49900 | 100 |
| Shampoo - 250 mL | `15430840877219` | `TEST-SHAMPOO-250ML` | 29900 | 100 |
| Hand Wash - 500 mL | `15430841106595` | `TEST-HANDWASH-500ML` | 19900 | 100 |

All three were saved and verified in Shopify admin; active, tracked inventory at Shop location, zero at My Custom Location, descriptions identify synthetic development/testing data. Continue selling when out of stock is off. Costs remain missing; do not infer margin or contribution. No real sales or shipments.

Product IDs are not variant IDs. Authenticated Admin GraphQL returned these variant IDs on 13 October 2026:

| SKU | Variant ID |
| --- | --- |
| TEST-LAUNDRY-1L | `gid://shopify/ProductVariant/67664059170979` |
| TEST-SHAMPOO-250ML | `gid://shopify/ProductVariant/67664059662499` |
| TEST-HANDWASH-500ML | `gid://shopify/ProductVariant/67664060219555` |

Do not substitute product IDs into Storefront cart merchandise inputs. Current catalogue returned INR prices 499.00 / 299.00 / 199.00 and stock 100 each. Scope remains the customer's previously purchased SKU/variant; these three products do not authorise cross-sell. Checkout/Storefront access and precise inventory locations must still be validated for execution.

## Pending evidence and connections

API test app created/released and installed after explicit owner approvals on 13 October 2026: `Repeat Purchase Agent API Test`, app ID `434636062721`, version `api-read-test-v1`, version ID `1164379029505`, client ID `e2b9a37eac2044803318007a712fb3e3`, standalone/non-embedded, official default app home `https://shopify.dev/apps/default-app-home`, API version `2026-10`. Scopes: `read_products,read_inventory,read_locations,read_customers,read_orders,read_draft_orders`. No write/payment/messaging scopes. Credentials reside only in ignored `backend/.env`; never copy the secret into this document. The server exchanges credentials for an in-memory expiring token using the same-organization grant.

Verified `/api/shopify/snapshot` reads shop `gid://shopify/Shop/78934507683`, INR, all 20 products and inventory. Shopify returns protected-customer-data errors for customers and orders/drafts; the frontend reports partial access and unavailable data rather than empty lists. The app's Partners distribution/protected-data setup route currently prompts for user account selection; authentication handoff is pending. Four local tests passed; real API catalogue response and frontend rendering were separately verified. The local UI is http://127.0.0.1:8765/#connections. App credentials are not embedded in the frontend.

- Inspect Shopify-generated customers and draft/completed orders; build purpose-made synthetic delivered repeat history for our fixtures only after reviewing the next stage.
- Shopify app creation/release, six read scopes, installation, server credential storage, token exchange and catalogue API validation are done. Protected customer/order data setup and reads remain pending. Credentials must remain server-side.
- Razorpay, Twilio, Meta and AI/speech account completion is not verified. Signup forms were prepared earlier; do not claim connected adapters.
- Native Shopify checkout with Razorpay test mode is documented but needs store-region/account/plugin and payment-to-order mapping tests.
- WhatsApp trial/sandbox is limited; custom proactive reorder templates need separate verification.
- Browser voice is the demonstration direction; telephone calling in India is separately conditional.
- Support provider and external campaign coordination remain unselected.
- Native custom deployment into Razorpay Agent Studio has no verified public developer contract/access.

## Next test stage

Customer/order inspection completed in Shopify admin on 13 October 2026:

| Generated customer | Shopify customer ID | Completed orders observed | Email subscription |
| --- | --- | ---: | --- |
| Ayumu Hirano | `31288934432931` | 0 | Not subscribed |
| Russell Winfield | `31288934400163` | 0 | Not subscribed |
| Karine Ruby | `31288934367395` | 0 | Not subscribed |

Orders page was empty. Drafts page contained ten open generated drafts, `#D1`–`#D10`, denominated in USD. Drafts and their totals are not paid/delivered evidence and must not feed repeat eligibility or verified revenue. The three project products have no verified purchase histories. Email subscription is not WhatsApp or voice permission.

Latest owner request supersedes the earlier no-code setup phase: connect the frontend to Shopify. The small read-only server and Connections panel now do so for shop/catalogue data, while protected customer/order configuration remains pending. The full backend, historical write permissions and live outreach remain outside this stage. Controlled historical fixtures are still only planned in `shopify-test-data-plan.md`.

Frontend validation: automatic check after reload succeeded; all three test products rendered with exact variant IDs, INR prices and stock. Show-all/project-only product toggles passed. Partial-access warnings and unavailable customer/order states are visible. Screenshot: `frontend-shopify-connected.jpg` in this chat's local visualization output directory. The server remains running on loopback port 8765 for owner review.

## Next integration: Razorpay — 13 October 2026

Owner reviewed the Shopify catalogue connection and requested checking the next integration. The protected Shopify customer/order prerequisite remains outstanding; this is not a waiver of that requirement.

Observed Shopify Payments settings: development stores can only process test payments; Test payment gateway is configured. Search by provider returned `01 Cards, UPI, NB, Wallets by Razorpay`. Its setup page is https://admin.shopify.com/store/repeat-purchase-agent-test/settings/payments/alternative-providers/1058839 and offers Install. No provider installation, activation or payment was performed. The listing's automatic payment-capture behavior was observed; actual test checkout support is still unverified. The current US store entity and INR currency do not independently prove account/region compatibility.

Razorpay account page https://accounts.razorpay.com/auth/ was opened and the owner-authorised email was prefilled. It remains at signup/login; no authenticated dashboard, completed account, API keys or test-mode access has been verified. Authentication/terms completion needs owner input.

Official integration documentation confirms a Shopify Razorpay Secure test path, separate Shopify test-mode toggle, and test transactions that deduct no money: https://razorpay.com/docs/payments/payment-gateway/ecommerce-plugins/shopify-razorpay-secure/integration-steps/ . Documentation states test mode can be used while KYC is incomplete; actual account availability must be checked, and documentation also lists account activation in installation steps. Do not promise account eligibility before observing it.

Next checks after account access: verify test dashboard/API key availability; review provider installation permissions; verify both systems' test modes; perform success/failure test checkout; match Shopify order to Razorpay captured payment; verify server-side evidence and duplicate handling before updating frontend payment truth. Never use live credentials or browser success alone to confirm purchase.

Owner completed Razorpay sign-in. Onboarding exposed Test Mode and Get test keys controls; opening Test Mode reached https://dashboard.razorpay.com/app/dashboard . Dashboard content explicitly says `You are in test mode` and that test experience is available while live onboarding remains incomplete. An updated Razorpay Terms and Conditions modal currently blocks further interaction, with an `Okay, Got it` button and https://razorpay.com/terms/ link. Owner approval/acknowledgement is pending before dismissing it. No test keys were generated or retrieved, provider installed, payment submitted, or personal KYC information persisted to project files.

Owner subsequently approved the terms step; modal was already absent on the next observation. Dashboard menu Test Mode switch was observed enabled. Selected Shopify in the dashboard's web-builder integration helper, which displayed the official Shopify guide. Navigated Account & Settings → API keys to https://dashboard.razorpay.com/app/website-app-settings/business-website-details . Generate Key is available; website/app submission is disabled pending live KYC, while the page explicitly allows test API keys in test mode. No key generation was clicked. Await owner action-time approval before generating test credentials; store secrets server-side only. A Razorpay API key itself may permit more than read operations; the local connector must enforce its own read-only endpoints and reject live keys during this stage.

Owner then said `done` and requested moving to the next integration. On observation, Razorpay still displayed Generate Key; no key/secret was captured or stored. Record the owner-reported completion separately from verified evidence: test-mode account access is verified, API key generation is unverified, and API connectivity/Shopify gateway/payment reconciliation remain untested. Owner authorised proceeding to WhatsApp rather than continuing this step.

## WhatsApp account setup — 13 October 2026

Opened Twilio's official trial signup, with owner-authorised email and name prefilled. Password, terms and email/phone verification require owner completion. No Twilio account or WhatsApp sender is verified yet, no credentials stored, no device enrolled and no message sent.

Current official trial path is Messaging → WhatsApp → Try out WhatsApp in the new Twilio Console. Legacy Console also has a WhatsApp sandbox. Trial outbound messages use provided templates and verified recipients; custom proactive replenishment templates are not proven by the trial. After sign-in, determine the actual available console and test capabilities before writing adapters or promising custom outreach. First authorised test target should be the owner's own verified device, with inbound/outbound/status evidence inspected before advancing. Do not contact generated Shopify customers.

Owner completed Twilio signup. Verified signed-in account SID `AC3950f89724c60f05509de4194bf714bb`, named My First Twilio Account, in the new console. Completed non-binding onboarding preferences Messaging + Conversational AI + With code, and selected Limited trial (no credit card) rather than the default Full access. Trial console shows 30 days remaining, 100 free WhatsApp messages, 100 SMS, and 75 voice minutes; these are observed allowances, not proof any of those services has been tested.

Opened the WhatsApp trial launcher. `Activate your sandbox` modal requires acknowledging third-party WhatsApp/Meta business terms before Continue. Await explicit action-time acceptance before checking that agreement or continuing. No sandbox activation, phone enrollment, test send, webhook setup, delivery receipt, API authentication check or frontend adapter is yet verified. Auth token remains masked; it was not copied, revealed or stored. No paid upgrade was selected.

Owner then authorised activation. On observation, the agreement modal was already gone and Try out WhatsApp → Connect to testing environment was open, with one verified tester selected. Current console instruction: send `join twilio-trial` using the selected tester's WhatsApp device to Twilio trial number `+17372508034`, or scan the displayed QR code. Do not replace this with the legacy sandbox default number or code from documentation. Device join confirmation is pending; no test send/reply/status receipt is verified. Native phone access is unavailable, so owner must send this joining message from their own device. No recipient phone number or auth token is stored in project files.

Owner reported joining and explicitly confirmed receiving the WhatsApp joining acknowledgement. However, the new-console trial drawer still displays the device-link/QR screen for its selected tester, with no test-send controls; Logs was empty even after Reload logs, and reopening after page reload did not change the linkage view. Remaining allowance observed as 98; do not infer a successful test send from the allowance change. Asked whether the join originated from the same verified tester selected in Twilio; response is pending. No agent-originated message was sent, no provider Message SID/delivery receipt inspected, and no WhatsApp frontend/server adapter is connected yet.

Owner confirmed joining from the selected verified tester ending 7767. Read-only API verification succeeded using the existing primary auth token on the US1 Auth tokens page (home-page copied token returned HTTP 401/code 20003). No credentials were saved; token was concealed again and clipboard cleared. GET Messages returned HTTP 200: inbound WhatsApp SM33d67e4e84c0a89dde4a38c32cf07288, status received, error 12300; outbound WhatsApp SM35e4a4023ec851fa51f691c116a0fa59, status read, error null. Both match the confirmed tester. These are pre-existing records, not a new agent test send; inbound body did not exactly match the displayed join command. Account message access and an outbound read receipt are verified; trial UI linkage, purpose-specific outbound test, inbound webhook handling (including error 12300), frontend adapter, and production templates remain pending. No agent-originated message was sent.

## Outstanding integration completion — 13 October 2026

Owner authorised completing remaining integration checks before deciding backend stages. Partner dashboard still displays Verify your business email address; owner asked to complete email verification. Razorpay test-key-created dialog observed, but both individual copies and Copy CSV returned no usable clipboard content and automated Download key timed out. Owner approved generation/private backend/.env storage, but no usable Razorpay credentials have been saved or API calls verified. Keep the one-time dialog open; owner asked for downloaded file path. Shopify Razorpay provider installation review requests store-owner name/email/phone/address plus editing payment gateways and payment sessions; final grant awaits owner approval.

Twilio message body inspection resolved the joining discrepancy: inbound body was `Join twilio-trail`, not `join twilio-trial`; outbound read record is Twilio's standard auto-reply, not a join acknowledgement or app-originated test message. Owner asked to resend the exact correct join command from tester ending 7767. Error 12300 denotes Invalid Content-Type per https://www.twilio.com/docs/api/errors/12300 ; root webhook configuration remains unverified. New trial supports only provided ContentSid templates and no direct TwiML response per https://www.twilio.com/docs/usage/trials/try-out-whatsapp . Content API listing returned 401/code 20003 despite successful Messaging API reads; do not assume it supplies trial templates. No new message sent, no webhook changed, no full backend built.

Owner approved Razorpay provider installation. On next observation Shopify permission grant had already advanced to Razorpay's current-account confirmation for MID Tn6qsNrRyUlq0E; confirmed intended account and verified Installed. Enabled Test mode before Activate. Final Shopify page explicitly shows Active, Test mode is on, all transactions simulated, and activation success notification. Gateway is configured for test-only automatic capture; this is not a successful payment or reconciliation result. Opened same-SKU Laundry cart permalink /cart/67664059170979:1; storefront redirected to password gate. No checkout/customer data submitted, no test payment created. Screenshots razorpay-provider-access.jpg and razorpay-shopify-test-active.jpg saved in chat visualization folder. API keys still not saved; awaiting owner download path and Shopify email verification. Corrected WhatsApp join not yet visible in API records.

## Continued checks — 13 October 2026

Located owner-downloaded C:\Users\eknat\Downloads\rzp-test-key.csv. Valid unmasked test credentials saved, with owner approval, in ignored backend/.env as RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET. No values printed. Authenticated GET /v1/payments returned HTTP 200/count 0. POST /v1/orders created order_Tn7cVpZZ1OdODA for INR 499.00, synthetic TEST-LAUNDRY-1L integration check; independent GET verified created, amount_paid 0. This is a standalone Razorpay test order, not a Shopify order or confirmed purchase.

Read existing storefront access password in Shopify Preferences and entered it into the same development storefront; protection was not changed. Added one exact Laundry Liquid variant through storefront WebMCP, then prepared Shopify checkout using synthetic integration-test@example.com and fictional US address. Standard shipping INR 774.15 gave total INR 1273.15. Selected Razorpay Secure (external gateway selection absent from WebMCP schema), advanced authorised test-only checkout via complete_checkout, and observed Razorpay hosted Test Mode. Used reserved fictional US contact 202-555-0100, selected mock IDBI netbanking. Subsequent express.razorpay.com callback failed with ERR_NETWORK_CHANGED and browser URL policy blocked its generated error page; did not bypass this restriction. GET payments still count 0. Success/failure outcome, Shopify order creation and reconciliation remain unverified.

Twilio latest two records: inbound SM98bdde533b75528c767d25c6229982b2 again contains `Join twilio-trail` with error 12300; outbound SM90fe3e13dfb6dc9708f8a2889f2082ac is standard auto-reply, read, no error. Correct `join twilio-trial` is still absent. No agent-originated WhatsApp message sent. Partner email verification screen remains present. No full backend architecture selected or built during this stage.

Shopify owner clarified email was already verified. Refreshed Partner tab and resumed existing account session; dashboard now accessible and verification gate gone. Earlier email-blocker statement was stale. Reached app API access requests -> Protected customer data access. Page explicitly permits development data access after selecting Step 1 purposes without App Store review. Preparing Analytics and Marketing/advertising purposes was rejected by automatic approval review as persistent protected-data access expansion without explicit authorisation. No purposes selected/saved; requested owner approval for the specific declaration, leaving optional identity/contact/address fields unselected initially. Gmail connector is available but no mailbox read was necessary after refresh resolved verification.

Owner approved development protected-data declaration. Saved Analytics + Marketing/advertising; page lists those purposes. No optional name/email/phone/address fields requested and no App Store data-protection claims submitted. Removed unnecessary displayName from customer GraphQL query and its frontend table column. Restarted local connector (session 25084/PID 44648). Real snapshot now has no warnings: 20 products, 4 customer IDs/order counts, 1 order, 10 drafts. Frontend explicitly shows Connected - development and rendered source records. Four existing async tests passed when run with the bundled runtime outside the sandbox; initial sandbox test run stalled and was terminated. JavaScript syntax and standalone rebuild passed.

New source evidence supersedes previous no-payment observation: Shopify #1001 / gid://shopify/Order/18944435290275 is a test order, PAID, UNFULFILLED, INR 1273.15, Laundry stock 99. Read-only transaction query returned SALE/SUCCESS/test=true for Razorpay gateway, transaction gid://shopify/OrderTransaction/20825991807139 and paymentId rHrnscnzUQfV2GL6zm3osAWp3. Razorpay GET payments returned pay_Tn7feQ0B51wPZd, captured=true/status captured, INR 127315 minor units, order_Tn7en9W2ipOAwl. GET that provider order returned paid/amount_paid 127315 and receipt rHrnscnzUQfV2GL6zm3osAWp3, exactly matching Shopify transaction paymentId. This independently verifies one test payment/order reconciliation despite the earlier browser callback failure. Do not parse gateway receiptJson as a durable production contract; production link handling/deduplication/webhooks still unbuilt. Failure-flow testing remains pending. No fulfillment or delivery evidence exists. Screenshot shopify-customer-order-connected.jpg saved. Gmail connector available, but email reads unnecessary because refreshing Shopify resolved owner verification.

Corrected WhatsApp evidence: read-only provider records now include exact `join twilio-trial` at 13 Oct 2026 01:47:05 IST, inbound SM6c118bccc29d3f6e86aced10cce24b13, received/error 12300. Response SM243da3670891f61dbbb5c35698845a5c is standard auto-reply/read. Later doubled-command record also exists. Correct-command receipt is verified; earlier statements that the owner had not sent it were based on older records and are superseded. Refreshed/reopened new trial UI still shows device-link screen, no outbound test controls, selected tester ending 7767, allowance 92. Do not ask owner to resend again; diagnose trial linking/provider state or inbound handler. No custom webhook or agent send verified.
