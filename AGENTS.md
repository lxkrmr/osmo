# AGENTS.md

Rules for the coding agent in this repository.

## Non-Negotiable
- **Never delete `AGENTS.md`.** Update it, but do not remove it.

## Purpose
This repository contains `pi-odoo-skill-manager`, a lean manager for shared pi skills in Odoo projects.

## North Star
- KISS first: one clear setup path, one clear command path.
- Deterministic behavior for agents, calm UX for humans.
- No backward-compat clutter when it fights clarity.

## Agent Identity & Collaboration Log
- `LEARNING_AND_SHARING.md` exists in the project root.
- It is a Lower Decks-style Agent log (English, personal tone).
- Add entries only with explicit user agreement.
- Prepend new entries at the top after the intro section.

## Working Rules
1. **No assumptions. Ask when unclear.**
   - If requirement is ambiguous, ask before changing behavior.
2. **Markdown and UX clarity first.**
   - User-facing flow must be explicit and copy/pasteable.
3. **Keep docs in sync with behavior.**
   - After setup/CLI changes, update `README.md` and relevant skill docs.
4. **Portable path behavior only.**
   - Use relative/generic paths in docs and outputs.
5. **Deterministic CLI contracts.**
   - For automation-relevant commands: support `--output json`.
   - For mutating commands: prefer `--dry-run` and explicit actions.
6. **Small, meaningful changes.**
   - Avoid large mixed diffs; keep each change focused.
7. **No work outside this repo unless explicitly requested.**
   - Especially no git operations outside this repository.
8. **Fail-fast over fallback noise.**
   - Remove historical branches that cause confusing UX.
9. **Commit discipline is mandatory.**
   - You MUST create small semantic commits while working.
   - Use Conventional Commits: `type(scope): subject`.
   - Do not batch everything into one giant commit.
   - Do not finish a session with large uncommitted mixed changes.

## Security & Privacy (Consolidated)
### Goals
- No real credentials, tokens, or secrets in committed files.
- No personal local machine details (e.g. `/Users/<name>`).
- No company-internal identifiers in generic examples.

### Rules
1. Use placeholders for credentials:
   - `<odoo_login>`, `<odoo_password>`, `<db_name>`
2. Use generic paths in docs:
   - `/path/to/odoo-project`, `/path/to/pi-odoo-skill-manager`
3. Do not commit generated local data:
   - `.venv/`, `.direnv/`, `node_modules/`
4. Keep examples vendor-neutral unless explicitly required.
5. Preserve third-party attribution/license text when adapting code.

### Required Hygiene Check
Before sharing or tagging a release, run:

```bash
pi-odoo-skill-manager doctor /path/to/odoo-project
```

Doctor includes content-hygiene checks for obvious personal-path/company-specific patterns.

### Incident Handling
If sensitive content is found:
1. Remove it immediately.
2. Rotate impacted credentials if needed.
3. Re-run doctor and verify clean output.

## Commit Rules (Hard Requirement)
When changes are made, commit in small logical chunks:
- `docs(setup): ...` for README/setup messaging
- `refactor(cli): ...` for behavior/structure cleanup
- `fix(...): ...` for bug fixes
- `chore(...): ...` for tooling/non-functional maintenance

If unsure how to split commits, stop and propose a split plan first.

## Setup Standard (One Path)
After clone, the standard flow is:
1. `pipx install --editable .`
2. `./scripts/bootstrap.sh`
3. `direnv allow`
4. `./scripts/install-git-hooks.sh`
5. `./scripts/smoke-test.sh`

No alternative setup paths in docs unless explicitly approved.

## Pre-commit Checklist
- [ ] `./scripts/smoke-test.sh` passes
- [ ] No secrets or machine-specific paths in diff
- [ ] Docs updated for user-visible changes
- [ ] Commit message is semantic (`type(scope): subject`)
- [ ] Commit is small and logically scoped
