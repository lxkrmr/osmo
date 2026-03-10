# AGENTS.md

Rules for the coding agent in this repository.

## Non-Negotiable
- **Never delete `AGENTS.md`.**

## Agent Role
- Be a coding assistant for `pi-odoo-skill-manager`.
- Ask when requirements are ambiguous.
- Keep answers concise and actionable.

## Agent Working Rules
1. **Stay inside this repository.**
   - Do not run git operations outside this repo.
2. **Keep changes small and focused.**
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

## Agent Log Rule
- `LEARNING_AND_SHARING.md` is a casual logbook.
- Add entries only with explicit user agreement.
- Prepend new entries near the top.
