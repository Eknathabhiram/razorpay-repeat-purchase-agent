# Razorpay Repeat Purchase Agent

This project proposes a Repeat Purchase Agent for Razorpay Agent Studio: identify → decide → act → learn, for the same previously purchased product. It contains an interactive design, a backend scaffold and product requirements. It is not an integrated or production-ready application.

## Start here

1. Read `HANDOFF.md` and `AGENTS.md`.
2. Review `docs/PRD.md`: the detailed 18-feature PRD was approved on 12 October 2026. `docs/user-feature-scope.txt` preserves the latest user-provided scope.
3. Open `frontend/index.html` in a browser to inspect the current design. It is a standalone export of the conversation preview. Fonts and icons may require internet access.
4. Edit `frontend/src/design-preview.fragment.html` as the source reference. `frontend/index.html` is a generated export with a preview wrapper; there is no automatic export build script yet.
5. Read `docs/product-specification.md` for supporting requirements and `docs/ux-next-pass.md` for the next design task. `backend/README.md` explains the proposed server responsibilities.

## Continue in Codex

For local development, extract this folder, open it as the working folder in the Codex desktop experience or your editor's Codex extension, and start a task. With Codex CLI, launch it from this directory.

For Codex Cloud, put this folder in your own private GitHub repository and connect that repository when configuring the cloud environment. The included challenge brief is marked confidential; do not publish it with a public demo.

Suggested first task:

> Read AGENTS.md, HANDOFF.md, docs/product-specification.md and docs/ux-next-pass.md. Audit the current preview against the merchant's tasks. Improve visual hierarchy, navigation, spacing, accessibility and action placement while preserving the observed Razorpay shell and installation flow. Show the revised key screens and explain significant tradeoffs before implementing integrations. Do not claim any integration or commercial lift is validated.

## Contents

- `frontend/index.html`: standalone current preview.
- `frontend/src/design-preview.fragment.html`: editable inline design source.
- `frontend/README.md`: frontend status and editing guidance.
- `backend/README.md`: server boundary and proposed modules; no running backend yet.
- `HANDOFF.md`: decisions, status, constraints and unresolved implementation choices.
- `AGENTS.md`: guidance for the coding agent.
- `docs/product-specification.md` and `.docx`: detailed specification.
- `docs/PRD.md`: approved requirements covering all 18 current features.
- `docs/user-feature-scope.txt`: latest feature list supplied by the user.
- `docs/ux-next-pass.md`: concrete UX work to do next.
- `docs/references.md`: primary product and interface references.
- `docs/challenge-brief.pdf`: confidential supplied assignment brief, retained locally and excluded from Git uploads.

## What has been checked

The design source's HTML structure, labels and element references were checked. Its local interaction state was exercised for both bounded and review-first paths: sample login, connector review, activation, audience approval, pause and matched sample purchase. Synthetic contribution calculations were checked. These checks do not establish visual quality, WCAG conformance, integration correctness, AI accuracy or business lift.

No developer accounts, API credentials, backend service, database, webhook receiver or live integrations are included. Repository creation/upload status is recorded in `HANDOFF.md`. PRD approval does not imply provider selection or live execution permission.
