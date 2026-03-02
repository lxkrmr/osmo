---
name: skill-authoring
description: Guide for adding or updating a devkit skill in a consistent, lean, and safe way.
---

# Skill Authoring

Use this skill when someone asks to create or modify a skill in this devkit.

## Workflow

1. Scaffold a skill:
   ```bash
   ./pi-odoo-devkit.py new-skill <skill-name>
   ```
2. Fill frontmatter:
   - `name` (must match folder)
   - `description` (clear and specific)
   - optional `command` (shortcut, e.g. `/skill:<name>`)
   - optional `example` (one-line usage)
3. Replace placeholders with concrete steps and commands.
4. Keep it lean (one skill = one workflow).
5. If project-specific prerequisites are needed, add them to `skills/manifest.json`.

## Quality Rules

- No personal machine paths
- No real credentials or tokens
- Commands must be copy-paste ready
- Add safety notes for destructive actions
- Keep language direct and practical
- Define clear defaults and explicit override behavior (user instruction wins unless safety-critical)
- Define a precise output contract (what the agent returns by default)
- Prefer deterministic automation over ad-hoc prompt work:
  - if a step is repetitive/deterministic, recommend adding a script/helper/octolib command
  - avoid re-solving the same deterministic workflow manually in each run (saves tokens and context)

## Validation

```bash
./scripts/smoke-test.sh
./pi-odoo-devkit.py doctor /path/to/odoo-project
```

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
