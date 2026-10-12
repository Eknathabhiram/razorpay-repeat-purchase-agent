# Primary references

## Assignment

`challenge-brief.pdf` is the user-supplied Razorpay AI PM build challenge. Follow Track 2's signal, AI necessity, decision/action, merchant control, learning, trust/failure and business-outcome requirements.

## Razorpay interface and behaviour

- Installation walkthrough supplied by the user: https://www.linkedin.com/posts/razorpay-agentstudio-ugcPost-7492897180425322496-1dMB/
- Corresponding public post: https://www.linkedin.com/posts/razorpay_razorpay-agentstudio-activity-7492897315595177985-tLWY/
- My Agents / Activity / Connectors walkthrough: https://www.linkedin.com/posts/razorpay_razorpay-agentstudio-activity-7493894174287654913-QgjR/
- Public Agent Studio page: https://razorpay.com/agent-studio/
- Merchant control and guardrails: https://razorpay.com/blog/razorpay-agent-studio-principles-guardrails-and-merchant-control/
- Public login entry inspected during design: https://dashboard.razorpay.com/?country_code=IN&next=app&screen=sign_in
- Blade design system: https://github.com/razorpay/blade
- RazorSense design language: https://razorpay.com/razorsense/
- Accessibility requirements: https://www.w3.org/WAI/WCAG22/quickref/

Public video frames were inspected to ground the Studio shell, installation modal and operational layout. There was no private dashboard access. Recheck current documentation and behaviour during implementation; a public demo is not an SDK contract or proof of account availability.

## Integration starting points

- Shopify dev stores: https://shopify.dev/docs/apps/build/stores/development-stores
- Shopify generated test data: https://shopify.dev/docs/apps/build/stores/generated-test-data
- Shopify cart creation: https://shopify.dev/docs/api/storefront/latest/mutations/cartCreate
- Razorpay Shopify integration: https://razorpay.com/docs/payments/payment-gateway/ecommerce-plugins/shopify-razorpay-secure/integration-steps/
- Razorpay test/live modes: https://razorpay.com/docs/payments/dashboard/test-live-modes/
- Razorpay webhook verification: https://razorpay.com/docs/webhooks/validate-test/
- WhatsApp developer resources: https://whatsappbusiness.com/developers/developer-hub/
- Twilio WhatsApp sandbox: https://www.twilio.com/docs/whatsapp/sandbox
- Twilio voice trial restrictions: https://www.twilio.com/docs/usage/trials/try-out-voice

These references support investigation, not a claim that the integrations are complete. Provider account restrictions, OAuth permissions, templates, test checkout compatibility and voice streaming support must be verified with the actual accounts.
