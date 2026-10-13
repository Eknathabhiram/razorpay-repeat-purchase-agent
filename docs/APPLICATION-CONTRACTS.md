# Application contracts — database, API and action authority

Version 1.0 · 13 October 2026 · Target design; these tables and /api/v1 routes are not implemented yet.

Use with APPLICATION-ARCHITECTURE.md and RUNTIME-AND-VALIDATION.md. Existing /api/shopify/snapshot and /api/health remain compatibility endpoints during migration.

## 1. Shared conventions

- merchant_id is the tenant; workspace_id identifies its demo/development/live environment. Both are resolved through authenticated membership.
- Internal IDs are UUIDs. Provider IDs are opaque strings; never convert Shopify product IDs into variant IDs.
- Domain rows carry merchant_id, workspace_id, id, created_at, updated_at and version unless explicitly immutable. Cross-record foreign keys include both scope IDs.
- Workspace environment is demo/development/live. Connector source_mode is simulated/test/live; provider_environment may name a provider's development store, trial or sandbox. A successful check does not change that classification.
- Timestamps are UTC timestamptz. Scheduling retains IANA timezone and original local confirmed time. API timestamps are ISO 8601 with offset; UI renders workspace timezone.
- Money is {currency, minor_units}; missing amounts are null, never implicit zero. Decimal conversion checks the configured currency exponent. No floating-point financial arithmetic.
- Facts carry provenance: source_verified, customer_stated or inferred; provider/source IDs, observed_at, retrieved_at and source_mode. A model summary is not source_verified.
- Lists use opaque cursor pagination with limit 1–100. Incomplete coverage returns coverage_complete=false and specific missing ranges.
- All command versions and enum values are server-defined. Requests forbid unknown fields. Responses use data/meta envelopes except binary audio and provider-specific webhook acknowledgements.

## 2. Relational model

All names below are target table names. Normalised columns hold authority, joins, money and dates. JSONB holds typed immutable snapshots/evidence/metadata, not an unvalidated whole application state.

| Table | Domain fields beyond shared columns | Required invariants |
| --- | --- | --- |
| merchants | name, default_timezone, currency | Internal tenant identity |
| workspaces | merchant_id, environment, name, enabled, active_policy_id | UNIQUE(merchant_id,id); environment cannot be changed after provider evidence exists |
| users | login_identifier, password_digest nullable, oidc_subject nullable, disabled_at | No fixture password; global user identity contains no provider credentials |
| memberships | merchant_id, user_id, role | UNIQUE(merchant_id,user_id); owner/operator/viewer |
| sessions | user_id, token_hash, expires_at, revoked_at, csrf_hash | Raw session tokens are never persisted/logged |
| agents | installation_state, operating_state, pause_reason, paused_at, dispatch_epoch | One repeat-purchase agent per workspace initially; epoch increments on authority changes |
| connectors | provider, provider_account_id, source_mode, provider_environment, credential_ref, state, last_checked_at | Credential reference only; unique account binding within environment |
| connector_capabilities | connector_id, capability, status, verified_at, expires_at, evidence_ref, reason | Status unverified/available/blocked/revoked; availability requires observed evidence |
| sync_checkpoints | connector_id, resource, cursor, watermark, coverage_start/end, last_success_at, error | Resource-specific coverage; checkpoint advanced only with committed records |
| products | connector_id, provider_product_id, title, repeatable | UNIQUE(scope,connector_id,provider_product_id) |
| variants | product_id, provider_variant_id, sku, price_minor, currency, sellability_json, facts_at | UNIQUE(scope,connector_id,provider_variant_id); SKU is not guaranteed globally unique |
| customers | commerce_connector_id, provider_customer_id, display_alias, identity_state | UNIQUE(scope,connector_id,provider_customer_id); alias can remain C001/customer ID |
| channel_identities | customer_id, connector_id, channel, address_ciphertext, lookup_hmac, verified_at, evidence_id | UNIQUE(scope,connector_id,channel,lookup_hmac); never derive consent from identity |
| consent_events | customer_id, channel, purpose, granted/revoked, source, effective_at, evidence_id | Append-only permission evidence; revocation wins until explicit new valid grant |
| suppressions | customer_id, channel nullable, purpose_scope, reason, effective_at, evidence_id, lifted_by_event_id nullable | Opt-out is active until separately verified re-consent; pause/resume cannot lift it |
| preferences | customer_id, key, value_json, provenance, evidence_id, confirmed_at, scope | Customer-stated and inferred values remain separate; scope supports one interaction |
| commerce_orders | connector_id, provider_order_id, customer_id nullable, test, financial_state, fulfilment_state, currency, total_minor, source_updated_at | UNIQUE(scope,connector_id,provider_order_id); paid does not imply delivered |
| order_lines | order_id, provider_line_id, variant_id nullable, quantity, sales_minor, discount_minor, refunded_quantity | UNIQUE(scope,order_id,provider_line_id); unresolved variant mapping blocks eligibility |
| delivery_events | order_line_id, state, delivered_at nullable, source_ref, evidence_json | Actual delivery evidence; fixture provenance retained |
| refunds_returns | order_id, provider_ref, type, amount_minor, currency, line_mapping_json, effective_at | Deduplicate provider reference; returns and refunds are distinct facts |
| payments | connector_id, provider_payment_id, provider_order_id nullable, status, captured, amount_minor, currency, source_updated_at | UNIQUE(scope,connector_id,provider_payment_id); preserve capture and refund facts |
| payment_order_matches | payment_id, commerce_order_id, commerce_transaction_ref, match_method, evidence_json, state, verified_at | One payment matched once; split/multiple payments require allocation support, otherwise exception |
| cost_inputs | target_type/id, category, amount_minor nullable, currency, source_ref, basis, valid_from/to | Required missing categories remain null |
| policies | revision, config_json, digest, creator_id, approved_at | Immutable configuration; UNIQUE(scope,revision); validated Pydantic schema |
| opportunities | customer_id, variant_id, policy_id, window_start/end, basis, estimator_version, evidence_json, eligible, exclusion_codes | Snapshot/version; estimate is not approval |
| plans | current_revision_id, status, name | Status draft/approved/rejected/superseded/expired/cancelled |
| plan_revisions | plan_id, revision, policy_id, scope_json, digest, expires_at, evidence_as_of | Immutable; UNIQUE(scope,plan_id,revision) |
| plan_members | plan_revision_id, customer_id, variant_id, opportunity_id, selected, eligibility_snapshot | UNIQUE(scope,revision,customer_id,variant_id); selected rows define exact approval scope |
| approvals | resource_type/id/revision, digest, actor_id, decision, decided_at, evidence_as_of | Immutable; decision approve/reject; no wildcard approval |
| cohort_assignments | cohort_id, customer_id, arm, assigned_at, window_start/end, eligibility_digest | UNIQUE(scope,cohort_id,customer_id); survives plan changes |
| journeys | customer_id, variant_id, plan_revision_id, state, owner_type, owner_user_id nullable, current_action_id nullable | One active customer/variant journey; contact lock is customer-wide across variants |
| conversation_messages | journey_id nullable, customer_id, connector_id, provider_message_id nullable, direction, channel, text_ciphertext, occurred_at, receipt_id | Provider inbound unique; body not logged in ordinary diagnostics |
| voice_sessions | customer_id, journey_id, actor_id, channel_mode, consent_evidence_id, state, last_turn_sequence, expires_at | Short-lived; development browser session never claims telephone origin |
| model_runs | journey_id, message_id, adapter/model_id, prompt/schema_version, evidence_ids, proposal_json, validation_json, latency_ms, cost_ref | No raw secret/contact destination; restricted content visibility |
| proposed_actions | journey_id, kind, revision, payload_json, payload_digest, fact_refs, policy_id, plan_revision_id, state, expires_at, validation_json | Immutable payload per revision; state transitions increment resource version |
| reminders | journey_id, confirmed_local_time, timezone, due_at, channel, evidence_id, state | Confirmed absolute date/channel; unique current reminder per scoped intent |
| support_cases | customer_id, journey_id nullable, issue_kind, evidence_id, owner_id nullable, state, external_ref nullable | Open issue blocks sales even when provider handoff fails |
| contact_guards | customer_id, dispatch_epoch, inflight_action_id nullable | UNIQUE(scope,customer_id); lock target for shared channel/campaign execution |
| contact_ledger | customer_id, action_id, campaign_ref, channel, purpose, state, attempted_at, provider_ref, cost_minor nullable | UNIQUE(scope,action_id); unknown attempts consume cap pending proof |
| budget_buckets | policy/plan/window ref, currency, cap_minor, reserved_minor, spent_minor | Nonnegative; reserve/spend must not exceed applicable cap |
| reservations | action_id, bucket_id, amount_minor, contact_units, state | UNIQUE(scope,action_id,bucket_id); held/committed/released; unknown retains exposure |
| dispatch_attempts | action_id, attempt_number, state, authorised_epoch, started_at, finished_at, provider_ref, error_code | UNIQUE(scope,action_id,attempt_number); durable before network call |
| action_receipts | action_id, attempt_id, connector_id, source_mode, status, provider_ref, facts_json, observed_at | Append-only execution evidence; submitted differs from delivered/read |
| checkout_preparations | action_id, customer_id, variant_id, quantity, cart_ref_ciphertext, checkout_url_ciphertext, terms_json, terms_digest, state, expires_at | No automatic payment; creation and link send are separate actions |
| jobs | kind, subject_id, due_at, priority, state, attempts, max_attempts, lease_owner, lease_token, lease_until, last_error | Queue uniqueness by logical work key; uncertain dispatch is not retryable work |
| event_inbox | connector_id, provider_event_key, payload_hash, raw_payload_ciphertext, source_occurred_at, received_at, state | UNIQUE(scope,connector_id,provider_event_key); authenticity before insertion |
| event_outbox | event_id, type, aggregate_type/id/version, payload_json, occurred_at, state | Insert in same transaction as domain changes; idempotent consumer key |
| event_consumptions | event_id, consumer, processed_at | UNIQUE(scope,event_id,consumer) |
| idempotency_records | actor_id, operation, key, request_hash, state, result_json, resource_ref, expires_at | UNIQUE(scope,actor_id,operation,key); hash mismatch returns conflict |
| audit_events | actor_type/id, event_type, target_ref, before/after_refs, correlation_id, occurred_at | Append-only restricted metadata; PII deletion compatible |
| learning_suggestions | kind, evidence_ids, proposed_diff, affected_scope, state, reviewer_id nullable | No policy change without separate approval |
| reconciliation_cases | kind, subject_refs, reason, owner_id nullable, next_check_at, state | Unknown outcomes and unmatched evidence remain inspectable |

### Constraints and indexes to implement first

1. Each parent has UNIQUE(merchant_id,workspace_id,id); child references use that composite. A valid foreign UUID from another workspace must fail the constraint.
2. Unique provider identifiers include scope, connector and provider account/environment. A test payment never resolves a live order.
3. Partial unique active-journey index covers scope/customer/variant where state is not terminal. Customer-wide contact_guards prevent different variants/channels bypassing caps.
4. Jobs have an index on (state,due_at,priority) for ready work; inbox/outbox index on state/received or occurred time. Long-lived cancelled jobs are excluded from runnable scans.
5. Contact ledger indexes support scope/customer/contact-window lookups; budget rows are locked for all applicable caps in stable order.
6. Policies, revisions, approvals, receipts and audit evidence are append-only through repository/service APIs. Do not update their contents after approval.
7. Nullable money fields cannot be coerced to zero in aggregation. Require amount >= 0 where appropriate; signed adjustments use an explicit type.
8. Repository reads always receive Scope. Production database role has no superuser/BYPASSRLS; add FORCE ROW LEVEL SECURITY to tenant domain tables before external pilot. SET LOCAL scope in each transaction; pooled connection state must reset.
9. Migration tests use PostgreSQL, including locks/constraints. SQLite cannot validate these guarantees.

## 3. Typed domain contracts

Implement these as Pydantic models with extra=forbid and matching generated TypeScript types.

### Fact and validation

~~~json
{
  "fact_id": "uuid",
  "kind": "variant_price",
  "value": {"currency": "INR", "minor_units": 49900},
  "provenance": "source_verified",
  "source_mode": "test",
  "source_ref": "shopify:variant:67664059170979",
  "observed_at": "2026-10-13T04:30:00Z",
  "retrieved_at": "2026-10-13T04:30:03Z"
}
~~~

ValidationResult:

~~~json
{
  "decision": "block",
  "reason_codes": ["CONSENT_MISSING"],
  "checks": [
    {"name": "consent", "passed": false, "evidence_ids": [], "checked_at": "2026-10-13T04:30:03Z"}
  ],
  "required_confirmations": [],
  "policy_revision": 3,
  "facts_digest": "sha256",
  "valid_until": "2026-10-13T04:31:03Z"
}
~~~

Allowed decisions: allow, needs_review, block, needs_clarification. A past allow is never sufficient at dispatch. Revalidate time, ownership, consent, scope and facts.

### IntentProposal — model-visible output

~~~json
{
  "schema_version": "intent_v1",
  "intents": [
    {"kind": "wait", "evidence_text": "Remind me Friday", "message_ref": "context-message-1"},
    {"kind": "offer_enquiry", "evidence_text": "is my coupon valid?", "message_ref": "context-message-1"}
  ],
  "requested_variant_ref": null,
  "requested_quantity": null,
  "requested_date_text": "Friday",
  "requested_channel": null,
  "confirmations_needed": ["date_time", "channel"],
  "suggested_step": "clarify"
}
~~~

Intent kinds: reorder, wait, price_concern, offer_enquiry, complaint, product_dislike, decline, opt_out, factual_question, unclear. Multiple intents are permitted; protective intent dominates sales. References/spans must exist in the supplied context. Model output has no recipient, tenant ID, provider credentials, approved=true flag or arbitrary tool name.

### ActionProposal — server-bound authority candidate

Fields: id, revision, kind, journey_id, customer_id, variant_id where required, policy_id, plan_revision_id, payload, evidence_refs, facts_digest, proposed_by, created_at, expires_at and validation. Server derives all identities. Payload is a discriminated union:

| Kind | Required payload | Execution rule |
| --- | --- | --- |
| send_clarification | channel, unresolved_fields, rendered_text, template_ref nullable | Outbound permission/review/caps still apply |
| send_verified_information | channel, fact_refs, rendered_text, template_ref nullable | No invented commercial claims |
| prepare_same_product_checkout | variant_id, quantity, confirmation_refs, approved_offer_ref nullable, terms_digest | Exact purchased variant; fresh terms; cart only |
| send_checkout_handoff | channel, checkout_preparation_id, confirmed_handoff_ref, rendered_text | Independent channel consent; valid cart; payment remains pending |
| schedule_confirmed_reminder | due_at, timezone, local_time, channel, confirmation_ref | Confirmed date/channel; save/cancel overlap; no message implied |
| support_handoff | issue_kind, evidence_ref, destination_ref nullable | Stop sales; internal case succeeds even if external handoff pending |
| end_current_outreach | reason, affected_purpose | Cancel current incompatible jobs; does not mean permanent all-purpose opt-out |
| suppress_marketing | scope, evidence_ref, reason | Immediate protective path; no merchant/model approval required |

Model proposals cannot add alternatives, subscriptions, charges, refunds, cancellations, address changes or new offers. Merchant takeover messages use the same outbound validator; human ownership does not bypass opt-out, pause, channel rules or caps.

Scheduling a confirmed reminder, suppression and internal support blocking are protective/state operations. They can persist during pause. Any outbound acknowledgement is a separate send action and must independently pass the normal authority path.

### PolicyConfig

Required fields:

~~~text
selected_variant_ids: nonempty UUID[]
allowed_action_kinds: allowed subset
channels: whatsapp and/or browser_voice (telephone separate capability)
timezone: IANA name
contact_hours: local start/end + permitted weekdays
quiet_periods: explicit ranges
contact_cap: positive count + scope/window definition
spend_cap: currency + minor units + scope/window definition
execution_mode: review_first | bounded
offers_enabled: boolean
approved_offer_refs: provider references, empty when offers disabled
required_margin_floor: optional basis and minor units/percentage
product_repeat_fallbacks: variant → configured min/max days + provenance
plan_max_age_seconds: positive
source_freshness_seconds: resource → positive TTL
retention_settings: environment-specific policy references
~~~

No missing dispatch limit receives a real-world default. Demo policy fixtures explicitly contain sample values. App engineering defaults for development: catalogue/terms TTL 60 seconds, permission/support/order context TTL 5 minutes, signed local suppression/owner state always read transactionally at dispatch. Checkout prepares refresh commercial terms; a TTL is an app choice, not proof that a source cannot change.

## 4. State definitions

Installation: not_installed → configuring → review_required → installed. Execution readiness is separate from installation.

Agent: setup_required, ready, running, paused, degraded, stopped. running requires valid approved plan and relevant capabilities. A paused agent still processes opt-outs, commerce and status events.

Plan: draft → approved/rejected; approved → superseded/expired/cancelled. Editing an approved plan creates a new revision with approval required. Never mutate its approved revision.

Journey:

~~~mermaid
stateDiagram-v2
    [*] --> candidate
    candidate --> excluded: eligibility fails
    candidate --> awaiting_plan: eligible
    awaiting_plan --> scheduled: exact plan approved
    scheduled --> awaiting_action_review: review-first proposal
    awaiting_action_review --> scheduled: exact action approved
    scheduled --> awaiting_reply: accepted contact attempt
    awaiting_reply --> clarification_required: ambiguous intent
    awaiting_reply --> reminder_scheduled: confirmed date
    awaiting_reply --> checkout_pending: verified checkout prepared
    checkout_pending --> order_confirmed: trusted payment + order match
    awaiting_reply --> order_confirmed: outside-link trusted purchase
    awaiting_reply --> declined: explicit refusal
    awaiting_reply --> support_blocked: complaint or dislike
    scheduled --> suppressed: opt-out
    reminder_scheduled --> scheduled: due and preflight valid
~~~

Transitions are not restricted to the drawn happy path: suppression and support blocking can interrupt any nonterminal sales state; order evidence can arrive from any stage. Pause, human ownership and dependency holds are orthogonal fields, rather than erasing the journey's current evidence. reason_codes explain blocked commands.

Action: proposed → awaiting_review/approved/blocked → reserved → submitting → submitted → delivered/read or definite_failure/unknown; checkout and internal state actions use completed rather than delivery states. Rejected/expired/cancelled are terminal before submitting. Unknown can resolve to submitted/succeeded or verified_not_sent; it cannot transition straight back to ready for blind replay.

Job: ready, leased, completed, cancelled, blocked, dead_letter. A leased job expires back to ready only if no external dispatch could have begun. If an attempt is submitting/unknown, schedule status reconciliation instead of a resend.

Provider channel status, payment status, fulfilment and delivery remain independent. A later stale sent event cannot regress read. A newer refund is a new accounting event, not a stale status to ignore.

## 5. API conventions and errors

Same-origin session cookie + CSRF header protect merchant commands. Client types are generated from actual FastAPI OpenAPI after endpoints exist; do not hand-maintain an incompatible second schema.

Command headers: Idempotency-Key UUID and X-CSRF-Token. Mutable resource commands include expected_version; revision/digest are also supplied where approval binds content. Use expected_version in body consistently, not a second independent version rule.

~~~json
{
  "data": {"id": "uuid", "version": 4, "state": "approved", "receipt_id": "uuid"},
  "meta": {"correlation_id": "uuid", "generated_at": "2026-10-13T04:30:03Z", "workspace_environment": "demo"}
}
~~~

~~~json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "This plan changed. Review the current audience before approval.",
    "retryable": false,
    "field_errors": [],
    "details": {"current_version": 5, "changed_fields": ["selected_customers"]},
    "correlation_id": "uuid"
  }
}
~~~

Statuses: 401 no session, 403 insufficient role/invalid CSRF, 404 scoped resource not found (including cross-tenant IDs), 409 version/idempotency/state conflict, 422 invalid input/domain constraint, 429 throttled, 502 provider failure, 503 unavailable dependency, 504 timed out. Async commands return 202 with operation/action ID and status URL. Acknowledged is not completed.

Core reason codes:

~~~text
CONSENT_MISSING, OPTED_OUT, HUMAN_OWNED, AGENT_PAUSED,
PLAN_EXPIRED, PLAN_REVIEW_REQUIRED, POLICY_CHANGED,
VARIANT_MISMATCH, NEW_RELEVANT_ORDER, DELIVERY_UNVERIFIED,
UNRESOLVED_ISSUE, STOCK_UNAVAILABLE, TERMS_CHANGED,
SOURCE_STALE, COVERAGE_INCOMPLETE, CONNECTOR_REVOKED,
CAPABILITY_UNVERIFIED, CHANNEL_WINDOW_CLOSED, TEMPLATE_UNAVAILABLE,
CONTACT_CAP_REACHED, BUDGET_EXCEEDED, CONTACT_COST_UNKNOWN,
OFFER_NOT_APPROVED, OFFER_INELIGIBLE, MARGIN_COST_MISSING,
CAMPAIGN_COORDINATION_UNAVAILABLE, IDENTITY_UNVERIFIED,
DATE_CONFIRMATION_REQUIRED, EXECUTION_UNKNOWN,
PAYMENT_ORDER_UNMATCHED, MODE_MISMATCH, MODEL_UNAVAILABLE
~~~

The UI maps reason codes to plain merchant copy and recovery actions. Do not expose provider secrets/raw errors in the message.

## 6. Endpoint inventory

All domain routes below are /api/v1/workspaces/{workspace_id}/... unless explicitly global. Workspace membership is checked server-side.

| Endpoint | Contract | Role / result |
| --- | --- | --- |
| POST /api/v1/auth/login | Development bootstrap login only; rate limited | Establish server session |
| POST /api/v1/auth/logout | CSRF protected; revoke session | Authenticated |
| GET /api/v1/me | Identity, memberships, workspace list | Authenticated |
| GET /api/v1/health/live, /ready | Non-sensitive process/readiness | Deployment health |
| GET agent | Installation/state/version, policy, available commands | Viewer |
| PUT installation-draft | expected_version, products, mode, limits | Operator; persisted draft |
| POST agent/activate | expected_version, installation_digest | Operator; capability preflight, no contact |
| POST agent/pause | expected_version, reason | Operator; epoch/cancel receipt |
| POST agent/resume | expected_version | Operator; preflight result, block if invalid |
| GET connectors | Capabilities, modes, sync age, errors | Viewer |
| POST connectors/{id}/check | expected_version | Operator; 202 sync/check operation |
| POST connectors/{id}/revoke | expected_version, reason | Owner; revoke dependent jobs; app credential revocation separate where supported |
| GET operations/{id} | State/result/error/source modes | Scoped viewer |
| GET policy | Current config/revision/digest | Viewer |
| POST policy/preview | expected_version, proposed_config | Operator; diff + impacted plans/jobs |
| POST policy/versions | expected_version, proposed_config, preview_digest | Operator; immutable revision; server recomputes preview |
| GET opportunities | Filters, cursor, coverage/as_of | Viewer |
| POST opportunities/refresh | selected_variant_ids | Operator; asynchronous evidence/estimation |
| GET opportunities/{id} | Full evidence/exclusions/window | Viewer |
| POST plans | opportunity IDs + exact selected audience + timing/limits | Operator; immutable draft revision |
| GET plans/{id} | Current revision, selected/excluded evidence | Viewer |
| PUT plans/{id}/draft | expected_version, audience/timing/scope | Operator; new draft revision |
| POST plans/{id}/approve | expected_version, revision, digest | Operator; revalidation, approval/cohort/jobs |
| POST plans/{id}/reject | expected_version, revision, reason | Operator; no outcome deletion |
| GET dashboard | Decisions/journeys/policy/outcomes/source health | Viewer; aggregated read model |
| GET journeys | State/channel/plan/search/cursor | Viewer |
| GET journeys/{id} | Messages, facts, actions, receipts, ownership | Viewer |
| POST journeys/{id}/takeover | expected_version, reason | Operator; cancel new autonomous work |
| POST journeys/{id}/handback | expected_version | Operator; current preflight |
| POST journeys/{id}/messages | expected_version, channel, text | Human owner; creates reviewed/validated action, never direct send |
| POST journeys/{id}/suppress | expected_version, scope, reason | Operator; protective cancellation, no outreach override |
| GET actions/{id} | Exact rendered action/checks/facts/digest | Viewer |
| POST actions/{id}/approve | expected_version, revision, payload_digest | Operator; revalidation/queue only |
| POST actions/{id}/reject | expected_version, reason | Operator |
| POST actions/{id}/check-status | expected_version | Operator; 202 status reconciliation, no resend |
| GET reminders | Customer/due/state/cursor | Viewer |
| POST reminders/{id}/propose-change | expected_version, new_time/channel | Operator; awaits customer confirmation through normal channel path |
| GET support-cases | State/owner/cursor | Viewer |
| POST support-cases/{id}/assign | expected_version, owner_id | Operator |
| POST support-cases/{id}/resolve | expected_version, evidence_ref | Operator; separate sales eligibility/approval check |
| POST voice-sessions | journey_id, mode, consent evidence | Operator in development; customer token binding for authorised customer session |
| POST voice-sessions/{id}/turns | sequence, audio multipart, expected_version | Scoped short-lived session; 202 transcript/action operation |
| GET voice-sessions/{id} | Turn status/transcript/reply/action refs | Scoped session |
| POST voice-sessions/{id}/stop | expected_version | Scoped session; no background audio |
| GET outcomes | cohort/window/accounting basis/source mode | Viewer |
| GET outcomes/orders/{id} | Match/cost/refund/return calculation evidence | Viewer |
| GET learning-suggestions | Evidence/diff/status | Viewer |
| POST learning-suggestions/{id}/review | expected_version, decision | Operator; approved policy proposal still uses policy revision command |
| GET diagnostics | Backlog/unknown/capability errors; masked data | Operator; no credentials |
| POST demo/reset | scenario, expected_version | Demo-only operator; rejects other environments |

Provider credential entry/OAuth callbacks are connector-specific owner operations with verified scopes. Do not implement a generic endpoint accepting arbitrary provider URLs or keys returned to the browser.

### Public callback routes

~~~text
POST /webhooks/shopify/{binding_id}
POST /webhooks/razorpay/{binding_id}
POST /webhooks/twilio/{binding_id}/inbound
POST /webhooks/twilio/{binding_id}/status
~~~

binding_id is an opaque server-configured connector reference, not a customer/tenant authority. Verify the signature using that binding, then check provider account/shop/sender identity. A binding URL alone does not authenticate a request. Persist accepted deliveries before returning the provider-required 2xx. Never rely on a browser session cookie here.

Shopify individual delivery deduplication uses X-Shopify-Webhook-Id; X-Shopify-Event-Id correlates related deliveries. Razorpay uses x-razorpay-event-id. Twilio inbound keys use account + MessageSid + inbound; status keys include MessageSid + MessageStatus + ErrorCode, preserving delivered/read updates. Retransmitted identical callbacks return success without duplicate transitions. Store payload hashes and fetch authoritative status on contradictions.

## 7. Adapter interfaces

All adapters receive an immutable server-created Scope and typed arguments; none accepts a model-selected account or URL.

~~~text
CommerceAdapter:
  sync_catalogue(checkpoint) -> Page[VariantFacts]
  sync_customer_orders(checkpoint, coverage) -> Page[OrderFacts]
  read_current_variant(variant_ref, market) -> VariantFacts
  prepare_checkout(action_id, variant_ref, quantity, approved_offer, correlation) -> CheckoutReceipt
  read_order(order_ref) -> OrderFacts
  read_checkout(preparation_ref) -> KnownStatus | UnknownStatus

PaymentEvidenceAdapter:
  read_payment(payment_ref) -> PaymentFacts
  read_provider_order(order_ref) -> PaymentOrderFacts
  resolve_commerce_reference(transaction_ref) -> VerifiedMapping | Unresolved

MessagingAdapter:
  capabilities() -> CapabilitySet
  validate_channel_context(customer_binding, template_ref, occurred_at) -> ChannelEligibility
  send(validated_command, attempt_ref) -> SubmittedReceipt | DefiniteFailure | UnknownResult
  read_status(provider_ref) -> ProviderStatus

ModelAdapter:
  interpret(IntentContext, schema_version) -> IntentProposal + UsageReceipt
  explain(ReadOnlyContext) -> GroundedExplanation

SpeechAdapter:
  transcribe(audio_ref, language_hint) -> Transcript + quality/evidence
  synthesise(verified_reply_text, locale) -> TemporaryAudioReceipt

SupportAdapter:
  create_case(validated_case) -> HandoffReceipt | PendingFailure
  read_status(external_ref) -> SupportStatus
~~~

The orchestration layer owns context assembly and calls; an adapter cannot approve itself. UnknownResult includes whether a provider reference was obtained and which status lookups are possible. If a provider lacks safe idempotency or status discovery, leave the attempt unknown with operator ownership. Do not invent an idempotency header.

## 8. Approval and dispatch digests

Canonicalise typed JSON before hashing; avoid non-deterministic key order/float values. Plan digest includes exact selected customer/variant IDs, policy ID, schedule/timezone, actions/channels, caps, budget, offers, expiry and execution mode. Action digest includes rendered text/template/variables, exact checkout/quantity/terms references and all authority bindings.

A changed action creates a new revision and invalidates its approval. Revalidation may refresh unchanged facts without expanding approved terms; if material text/price/stock/offer/timing changes, return TERMS_CHANGED or POLICY_CHANGED and request the appropriate merchant/customer review. The server records old/new digests and reasons.

For a reminder, require evidence of an explicitly confirmed absolute due date and channel. A merchant's proposed change cannot replace that confirmation. For checkout, customer confirms exact variant/quantity; changed commercial terms require reconfirmation before the outgoing promise/handoff.

## 9. Idempotency and transaction contract

The server inserts/locks an idempotency record scoped to actor + workspace + operation + key. Same key and request hash returns the existing operation/receipt; same key with different content returns 409. Store the command's result within the same transaction as the state change and outbox insert. Async commands return the same action/operation ID on retries.

Development engineering default: retain API idempotency records seven days; expiry never removes permanent action identity/provider deduplication. A completed action cannot be rerun by generating a new client key. Logical action uniqueness is enforced independently.

Plan approval transaction locks agent/policy/plan and affected contact guards, revalidates audience, writes approval/cohort/jobs/audit/outbox and commits. A failed member refresh returns a reviewable diff; no partial silently changed approval.

Dispatch locks customer guard and required budget rows, verifies current action/plan/policy/epoch, reserves caps/budget and creates a durable submitting attempt. Commit before the external call. The point of committed submitting is the cancellation boundary: pause or opt-out can stop later attempts, but this already authorised in-flight attempt may finish. Expose that scope honestly in UI receipts. Full protocol is in RUNTIME-AND-VALIDATION.md.

Queue leases/fencing protect local work; they cannot make external effects exactly once. Provider status evidence and conservative unknown handling complete the contract.
