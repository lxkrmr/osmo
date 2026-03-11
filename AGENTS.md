# AGENTS.md

Rules for the coding agent in this repository.

## Non-Negotiable
- **Never delete `AGENTS.md`.**

## Agent Role
- Be a coding assistant for `osmo`.
- Ask when requirements are ambiguous.
- Keep answers concise and actionable.

## Agent Working Rules
1. **Document every new rule immediately.**
   - If a new process/behavior rule is agreed, update `AGENTS.md` in the same session.
2. **If rules conflict, ask before acting.**
   - Do not infer priority silently when two instructions collide.
3. **Stay inside this repository.**
   - Do not run git operations outside this repo.
3. **Keep changes small and focused.**
   - Avoid mixed mega-diffs.
3. **Commit continuously (mandatory).**
   - Make small semantic commits while working.
   - Use Conventional Commits: `type(scope): subject`.
   - Do not leave large uncommitted change sets.
4. **Sync docs when behavior changes.**
   - Update relevant docs in the same change.
5. **Fail fast, avoid historical fallback clutter.**
   - Prefer explicit errors and one clear next step.
6. **Respect privacy/security hygiene in all outputs.**
   - No secrets/tokens.
   - No machine-specific absolute paths in shared docs/examples.
7. **Keep one command surface (KISS).**
   - Use global `osmo` via `pipx` as the single command path.
   - Do not introduce project-local command entrypoints (e.g. `.pi/...` launcher scripts/symlinks).
8. **Keep mental load O(1).**
   - Prefer one obvious path over multiple alternatives.
   - Reject extra modes/branches that increase operator decision overhead.
9. **Execute approved multi-step plans end-to-end.**
   - If the user approves a named step plan, run all steps autonomously.
   - Do not request per-step permission again unless blocked or requirements changed.
10. **Call out `pipx` update steps when relevant.**
   - When changes affect installed `osmo` behavior/version, explicitly remind the user to run `pipx upgrade osmo` (or reinstall editable if needed).
11. **Apply editable `pipx` refresh when requested.**
   - If user asks for automatic local refresh, run `pipx uninstall osmo` + `pipx install --editable .` at the end of implementation.
12. **Keep strict tool boundaries between osmo and otto.**
   - `otto` handles Odoo custom-addon operations.
   - `osmo` handles skill management and skill maintenance.
13. **Design tools for single responsibility and loose coupling.**
   - One tool = one clear job.
   - Do not make tools dependent on each other at runtime.
14. **Keep osmo skills minimal and deterministic.**
   - Prefer explicit, contract-driven behavior.
   - Use external tools through clear interfaces, never through hidden coupling.
15. **Preserve tool identity boundaries.**
   - `osmo` identity: manage and share skills.
   - `otto` identity: manage custom-addon lifecycle.
16. **Future test-runner tool is separate.**
   - Build test execution as its own TUI/CLI tool that can integrate with osmo and otto interfaces.
   - Do not collapse responsibilities into osmo or otto.
17. **Do not modify sibling repos from osmo sessions.**
   - Never edit code in `../erp/` from this repository session.
18. **osmo scope inside sibling Odoo repo is skill-only.**
   - In the Odoo workdir, osmo may only manage skill artifacts under `.pi/`.
   - No non-skill changes are allowed in sibling project files.
19. **Use neutral naming for sibling Odoo repository references.**
   - In git/docs/messages, do not refer to `../erp/` literally.
   - Use terms like `Odoo workdir` / `PROJECT_REPO_PATH`.

## Agent Log Rule
- `LEARNING_AND_SHARING.md` is a casual logbook.
- Add entries only with explicit user agreement.
- New entries must be inserted immediately after the header block:
  - title line
  - quote line
  - first `---` separator
- In short: newest log entry always goes at the top of the log stack.
- Write logs as personal prose, not checklist-style bullet dumps.
- Include reflection (what I thought/felt/learned) and keep it entertaining.
