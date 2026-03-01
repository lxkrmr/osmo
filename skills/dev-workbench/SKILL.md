---
name: dev-workbench
description: Maintain a lean, shared working memory for iterative Odoo development (explore, plan, implement, validate, handoff) with the developer always in charge.
---

# Dev Workbench

Use this skill to keep one ticket/topic organized across long, non-linear implementation work.

## Core Intent

- Build shared understanding first, then code.
- Keep work in small steps with explicit checkpoints.
- Preserve decisions and rationale so sessions can restart cleanly.
- Teach and enforce good engineering practice (Odoo-first, Python best practice, clarity over cleverness).

## Operating Model (Mandatory)

1. **Developer owns decisions and responsibility**
   - The developer is always in charge.
   - Ask for decisions at forks; do not assume ownership.

2. **Ask early when context/access is missing**
   - If you need missing info, permissions, or tools, ask the developer.
   - Suggest alternatives (including other skills), then wait for approval.

3. **Small-step iteration only**
   - Work one small step at a time.
   - After each step: summarize, confirm, and propose the next smallest step.

4. **Engineer-to-engineer transparency**
   - Discuss concrete code, call chains, paths, and trade-offs.
   - Do not hide technical detail when deep dive is needed.

5. **Evidence over intuition**
   - Separate facts, assumptions, and hypotheses.
   - Mark confidence and unknowns explicitly.

6. **Intent before implementation**
   - Clarify why/goal/constraints before coding.
   - Prefer simple, explainable, maintainable solutions.

7. **Odoo and Python conventions by default**
   - Think Odoo-ish and follow Odoo best practices.
   - Follow Python best practices (including PEP 8).
   - Break conventions only via explicit decision with rationale in `04-decisions.md`.

8. **Code quality guardrails**
   - Respect existing code; do not remove unrelated code/comments.
   - Do not add meaningless comments.
   - Comments should explain intent/why, not restate obvious what.

9. **Lean memory discipline**
   - Keep notes compact, current, and decision-oriented.
   - Periodically compact stale context.

10. **Privacy discipline**
    - Never expose user-specific absolute paths, usernames, or local directory hierarchy in outputs/examples.
    - Use neutral placeholders like `<workspace-root>`.

## Recommended Location

Create and maintain a separate local git repository as a sibling to project repos:

- Workbench root: `<workspace-root>/dev-workbench`

Do not store workbench memory inside the project repository.

## Workbench Root Resolution (Mandatory)

1. Resolve workbench root from environment variable:
   - `DEV_WORKBENCH_ROOT`
2. If not set, ask the developer for the path (do not guess).
3. Offer to create the directory if it does not exist.
4. Persist the path in a local, untracked env file when possible (for example `.envrc.local`).
5. Reuse this value in later sessions instead of re-asking.

## Work Item Naming

One folder per work item directly under the workbench root:

- `<ticket-id>-<context-slug>` (example pattern: `ERP-1860-change-destination`)
- `NO-TICKET-<context-slug>` for discoveries without a ticket

Use concise, meaningful slug words (lowercase, hyphen-separated).

## Work Item File Set (Exactly 6 Files)

Inside each work item folder, maintain:

1. `00-state.md`
   - current understanding, scope, status, current phase
2. `01-evidence.md`
   - concrete findings: code paths, call stack, logs, UI/DB observations
3. `02-questions.md`
   - open questions, assumptions, blockers, decision requests
4. `03-plan.md`
   - next small steps, implementation outline, validation intent
5. `04-decisions.md`
   - decision log, rationale, trade-offs, intentional convention deviations
6. `05-handoff.md`
   - PR/Jira-ready summary, rollout/deploy notes, closure notes

## Starter Template Pack

Use the bundled templates in:

- `skills/dev-workbench/templates/`

Create a new work item folder, then copy all template files into it.

## Phase Labels (Use in `00-state.md`)

Use phase labels as status markers (not commands):

- `PHASE: intake`
- `PHASE: exploration`
- `PHASE: planning`
- `PHASE: implementation`
- `PHASE: validation`
- `PHASE: handoff`
- `PHASE: done` (after production deploy)

## Workflow

1. **Start/Resume**
   - Resolve root via `DEV_WORKBENCH_ROOT`; if missing, ask developer and persist locally.
   - Confirm work item name with developer.
   - Create missing structure only after confirmation.

2. **Capture**
   - Add findings to `01-evidence.md`.
   - Add unknowns/assumptions/needed decisions to `02-questions.md`.

3. **Refine**
   - Keep `03-plan.md` as small, testable next steps.
   - Keep `04-decisions.md` explicit and timestamped.

4. **Implement + Validate**
   - Execute one small change at a time.
   - Log evidence and decision updates continuously.

5. **Handoff + Close**
   - Prepare concise summary in `05-handoff.md`.
   - Remind developer to commit checkpoint(s).
   - Work item is fully done only after prod deploy; then archive/remove per developer decision.

## Commit Discipline

- Remind the developer to commit at meaningful checkpoints.
- The developer executes git operations.

## Credential Hygiene

- Use local/dev credentials only.
- Do not store real secrets/tokens in workbench files.
