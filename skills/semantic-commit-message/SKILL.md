---
name: semantic-commit-message
description: Propose a semantic commit message from staged git changes. By default stay guidance-only; execute repo mutations only on explicit user request.
command: /skill:semantic-commit-message
example: /skill:semantic-commit-message
---

# Semantic Commit Message

Use this skill to generate a semantic commit message based on currently staged changes.

## Scope of This Skill

- This skill primarily proposes commit messages.
- Default behavior is guidance-only.
- Prefer no repo mutations unless explicitly requested by the developer.
- If a user request conflicts with defaults, explicit user instruction wins.

## Default Guardrails

- By default, do **not** run `git commit`, `git push`, or hook runners.
- By default, do **not** run branch-modifying commands (merge, rebase, reset, cherry-pick, etc.).
- If the developer explicitly asks for such actions, first confirm intent, then proceed.

## Commit Message Format

`<type>(<scope>): <subject>`

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Scope:** brief area affected (for example: `sales`, `inventory`, `webshop`)
- **Subject:** concise imperative summary, max 50 characters

If scope is unknown or not useful, allow:

`<type>: <subject>`

### Examples

- `feat(sales): add discount to sales orders`
- `fix(inventory): correct stock level rounding`
- `docs: update README setup steps`
- `refactor(accounting): simplify invoice batching`
- `test: add payment reconciliation tests`
- `chore: bump development dependencies`

## Agent Hint: Efficient Git Inspection

Use a minimal, read-only command sequence and stop when enough context is available:

1. `git diff --cached --name-status` (quick file-level intent)
2. `git diff --cached --stat` (size/shape overview)
3. `git diff --cached` (full patch only if needed)

Guidance:
- Prefer staged diff commands (`--cached`) only.
- Avoid duplicate commands that provide the same information.
- If staged changes are empty, do not inspect unstaged changes; ask the user to stage files first.

## Workflow

1. Inspect staged changes with the efficient sequence above.
2. If nothing is staged, tell the user no reliable commit message can be proposed yet and ask them to stage files first.
3. Analyze staged changes and propose:
   - one **primary** commit message
   - up to two **alternatives** when ambiguity exists
4. Ask the user to confirm or modify the message.
5. By default, return the final commit message text only.
6. If the developer explicitly asks for git write actions, confirm first, then execute only the requested commands.

## Safety Rules

- Always show the proposed message before commit-related actions.
- Keep actions read-only by default.
- If the developer explicitly requests write actions, confirm and then execute only what was asked.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
