# Next design pass

The user approved the direction and reference fidelity but says the experience still feels like an AI-agent assembly without sufficient UI/UX discipline. Improve how a merchant completes the job; preserve product scope.

## Design around three merchant questions

1. What needs my decision now?
2. What did the agent do, and can I trust the outcome?
3. Did this improve the business, within my limits?

## Concrete changes to explore

- Reduce competing cards, borders, status badges and explanatory copy. Put the most important pending decision and its consequence first.
- Keep one clear primary action per decision context. Distinguish installation, permission approval, audience approval and individual action review.
- Make first-use and returning-use layouts different. Before activation, show setup progress; during operation, show attention items, journey state and observed results.
- Use a coherent typography and spacing scale. Supporting copy must remain readable, including inside connector cards, tables and drawers.
- Separate product navigation from demonstration controls. Sample playback must be identifiable but must not define the intended merchant workflow.
- Keep opportunities compact. Show enough evidence to make a decision; reveal order history, eligibility checks and freshness on demand.
- Let merchants review and edit timing, audience and permitted actions before approval. Changed scope must invalidate the corresponding approval.
- Use progressive disclosure in setup. Keep essential controls visible, with advanced offer and margin controls available when the necessary data are connected.
- Review modal and drawer dimensions, keyboard focus, closing behaviour and smaller-screen adaptation. Preserve context when an overlay closes.
- Keep Activity as a decision/outcome record: customer words, intent, verified facts, action, execution receipt and exception owner. Show concise reasons rather than hidden model reasoning.
- Make Analytics decision-oriented. Prioritise verified group purchases, cost completeness, provisional contribution and guardrail breaches. Avoid decorating an unvalidated hypothesis with fabricated uplift charts.
- Include missing-cost reporting, stale source, unknown execution result, opt-out, issue handoff and pause states. Tell the merchant what is blocked and what repairs it.
- Preserve learning evidence: explicitly stated dates, confirmed preferences and verified purchases. Do not infer permanent preferences from a one-off channel handoff.

## Reviewable output before integrations

Produce a revised setup screen, operator overview, opportunity/plan review, conversation/action detail and analytics view. Explain the information hierarchy and significant alternatives. Check them at approximately 1440, 1024, 768, 390 and 320 px, at increased text size, and with keyboard-only use. Record actual checks and unresolved problems.

The full product scope remains the target. Do not use this design pass as a reason to remove voice, approval controls, failure handling, learning or outcome measurement.
