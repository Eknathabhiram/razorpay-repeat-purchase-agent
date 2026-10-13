# Stage 08 — observed outcomes, learning and reviewed accounting

13 October 2026. Implemented as part of the owner's request to finish everything end to end.

Migration 0008_outcomes adds immutable accounting revisions, scoped learning records, immutable policy suggestions and owner decisions. The application role cannot update/delete those records. Historical approved audience assignments remain independent of subsequent plans.

Outcomes aggregate every independently matched purchase in the workspace, including outside-link orders, grouped by currency. Gross payable, processed refunds and remaining payable are distinct; shipping/tax are not falsely labelled net merchandise revenue. Each purchase has at most one reporting cohort (earliest applicable customer/variant assignment), preventing plan renewal from double-counting it. Cohort repeat-purchase rate is observed unique purchasing customers / assigned customers; it is not causal lift or a randomized experiment.

Reviewed Demo accounting requires explicit product, fulfillment, gateway, communication, AI/agent and retained-tax inputs. Blank costs remain unknown. Return maturity must be explicitly reviewed. Contribution remains null if a required cost is missing, returns are immature or refund evidence changed since accounting review. Development accounting remains unverified; no synthetic cost fills a provider fact.

Confirmed customer date/channel learning is saved only after explicit reminder confirmation, scoped to the exact customer/variant/source turn. Permission is one-time; no permanent marketing consent or consumption interval is inferred. Learning creates an owner-review suggestion for a conservative contact cap. Acceptance creates a new policy version, recomputes opportunities and invalidates existing audience authority. Rejection and acceptance are immutable decisions.

Intervention timestamps and actor references are recorded; handling duration/time saved remain unmeasured. No contribution, incremental lift or agent attribution is fabricated from mere checkout correlation.

Three PostgreSQL Stage 08 cases passed in 50.173 seconds: outside-link purchase/refund/cost completeness, cohort renewal/deduplication and explicit learning/owner-reviewed policy change. Final agent-cost/refund safeguards and integrated workflow are covered by the Stage 09 evidence.

Dashboard now reads the same persisted Planning/Execution/Outcomes data. Activity uses durable Execution; Settings uses the actual Planning policy. Prior Stage 02 preview code remains as a historical design reference, not the source of operational counters.
