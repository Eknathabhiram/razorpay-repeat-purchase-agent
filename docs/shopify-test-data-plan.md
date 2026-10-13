# Shopify replenishment test-data plan

Prepared: 13 October 2026. Plan only; these customer histories have not been created in Shopify.

The generated store has three customers, ten open USD draft orders, and zero completed orders. These do not establish the qualifying delivered same-SKU history required by the product. Keep generated snowboarding data outside the agent's selected product scope.

## Proposed controlled cases

Use `TEST-LAUNDRY-1L` first, corresponding to product `15430840615075`; resolve its actual variant ID before any API order creation. All names and histories below are synthetic. Logical fixture IDs match the frontend reference and are not Shopify customer IDs.

| Fixture | Synthetic case | Required evidence | Expected behaviour |
| --- | --- | --- | --- |
| C001 / Ananya Sharma | Delivered repeat history; customer confirms a later reminder | Multiple delivered same-SKU purchases; explicit date/time/channel confirmation | Explain timing basis, save confirmed reminder, cancel competing outreach |
| C002 / Rahul Mehta | Delivered history; voice reorder and WhatsApp handoff requested | Exact SKU/quantity confirmation; independent synthetic channel permission evidence | Review-first checkout/handoff; no payment confirmation from checkout creation |
| C003 / Meera Shah | Qualifying history followed by a new brand purchase outside agent link | New commerce order and matched trusted test payment | Exclude/cancel future contact; count the order once only after reconciliation |
| C004 / Undelivered customer | Prior order fulfilled but not delivered | Separate fulfilment and delivery states | Exclude; fulfilled is insufficient |
| C005 / Opted-out customer | Delivered history plus explicit opt-out | Suppression event even while agent paused | Exclude and cancel both channels; resume cannot remove suppression |
| C006 / Priya Nair | Unresolved delivery issue | Undelivered order and owned support case | Support handoff; no sales outreach |

## Creation and review requirements

1. Create clearly tagged synthetic customer profiles without real recipient phone numbers or emails. Use reserved `.test` email addresses if addresses are necessary. Never assume a random phone number is fictional or subscribe an actual recipient.
2. Validate authorised Shopify app access and required scopes before deciding how to seed past orders. Historical order/delivery timestamps must be supported and verified through the selected API; current admin-created orders cannot be described as historical delivered purchases.
3. Keep manually completed synthetic orders distinct from Razorpay-backed test transactions. Marking a draft paid is not evidence of a Razorpay payment.
4. Keep synthetic permission and support fixtures labelled in their own source mode. An email subscription flag is not WhatsApp or telephone consent; real contact requires separately verified permission and a authorised test recipient.
5. Persist a mapping from logical fixture ID to actual Shopify customer, order, product, variant and inventory IDs. Use exact variant IDs for same-product checkout.
6. Review customer/product/order mappings and the eligible/excluded cases with the owner before connecting them to application behaviour. Missing permission still blocks outbound execution even if purchase history qualifies.

## Acceptance for this data stage

The owner can inspect the saved synthetic records; paid, fulfilled and delivered are separate; qualifying history and exclusions are reproducible; all fixtures are distinguishable from generated data and live evidence. Product costs remain unknown, and incremental lift remains unmeasured.
