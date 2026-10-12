# UI/UX reference QA — 12 October 2026

Scope: `frontend/design-handoff.html` and proposed tokens. This is a five-screen composition reference with synthetic data, not the complete application or integrated backend.

## Actual checks

- Rendered dashboard, plan review, activity/journey detail, outcomes and installation-review compositions in the in-app browser.
- Checked all five views at 1440, 1024, 768, 390 and 320 px: 25 view/width combinations. Document scroll width stayed within the viewport in every combination. Saved desktop/mobile screenshots in `design-screens/`.
- Visually inspected desktop dashboard/plan/journey/installation and tablet/narrow dashboard plus full narrow plan/journey. Remaining screenshot captures support developer inspection; a DOM width check alone does not prove every detail is visually flawless.
- Corrected tablet navigation collapse and stale draft-plan count after local approval. Corrected the repeat-window marks to represent the displayed dates.
- Pause disables local plan approval and displays the persistent pause explanation. Resume restores the local control. This reference does not implement a server preflight.
- Schedule editing reveals a changed-schedule notice and approval requirement. Plan approval runs explicitly labelled local playback, updating observed synthetic order count and net revenue once.
- Rahul's evidence retains checkout pending/payment unconfirmed. Customer selection shows support case C006 outside the audience, and C005 suppression has no takeover/marketing override.
- Takeover and handback update local owner text. Modal opens with focus on Close; Escape closes it and returns focus to the triggering contextual question.
- No AI, commerce, payment, messaging, microphone or telephone provider is connected. Source modes and illustrative receipts are labelled. One observed synthetic order does not establish causal lift.

## Reference limitations and developer requirements

The reference uses local ephemeral state and fixed fixture customers. It is not a database-backed approval, event processor, fully implemented four-step installation modal or production responsive navigation. Its five screen-switch buttons are reference navigation; the application retains Dashboard/Activity/Settings as specified. Server concurrency/idempotency, real permissions and every application empty/error/unknown state still require implementation.

Full WCAG 2.2 AA compliance, screen-reader operation, complete focus trapping, 200% text/zoom, contrast measurement and reduced-motion system preference were not fully evaluated. These remain explicit developer gates. Verify persistence, full entry/setup flow, audio permission/error states, mobile sticky approval footer, disclosure focus and all release criteria in `UIUX-HANDOFF.md` and `PRD.md`.

This QA record distinguishes checks actually run from design requirements. No merchant usability study, predictive validation or commercial lift has been performed.
