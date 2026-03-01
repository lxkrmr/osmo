---
name: skill-authoring
description: Guide for creating new devkit skills with consistent structure, safety rules, and validation quality.
---

# Skill Authoring Guide

_This skill follows `templates/SKILL.md` conventions._

Use this skill when someone wants to add a new skill to `pi-odoo-devkit`.

## Decide First: Skill vs Command

Keep root agent docs (`AGENTS.md` / `CLAUDE.md`) lean. Put workflow-specific rules into skills.

Create a **skill** when:

- workflow has multiple steps,
- safety/context matters,
- troubleshooting guidance is needed,
- team consistency is important.

Create a **command** when:

- action is atomic and repeatable,
- low context needed,
- mostly a convenience wrapper.

## Prerequisites

- Use the template: `templates/SKILL.md`
- Keep scope narrow (one clear workflow per skill)
- Confirm if the task is destructive/risky and add explicit guardrails

## Steps

1. Create skill scaffold:
   ```bash
   ./commands/dev new-skill <skill-name>
   ```
2. Fill frontmatter:
   - `name`
   - `description` (must explain why the skill is useful/needed)
3. Add a short "why this helps" sentence near the top of the skill body.
4. Replace placeholders in all sections.
5. Add concrete copy-paste commands.
6. Add/keep `Credential Hygiene` section.
7. If relevant, add dependencies (tools/scripts/skills) explicitly.
8. If skill depends on project-specific files/tools, add requirement rules to `skills/manifest.json`.
9. Run doctor/basic checks and review for path/secret safety.

## Quality Checklist

Before considering a skill done, verify:

- [ ] No hardcoded personal paths
- [ ] No real credentials/tokens
- [ ] Commands are copy-paste ready
- [ ] Safety notes cover destructive actions
- [ ] Validation section exists (user-run commands)
- [ ] Troubleshooting section exists
- [ ] Skill is narrow and non-overlapping with existing skills
- [ ] Dependencies are declared in `skills/manifest.json` when needed

## Validation (User-Run)

```bash
# scaffold a new skill
./commands/dev new-skill my-new-skill

# run devkit checks (recommended)
./commands/dev doctor
```

## Troubleshooting

- **Skill overlaps existing one**
  - Merge into existing skill or narrow scope.
- **Needs code tooling, not just docs**
  - Add/extend command in `commands/` and reference it in skill.
- **Unclear whether to add skill**
  - Start with command; promote to skill if workflow complexity grows.

## Notes / Risks

- Avoid creating “mega-skills” that mix unrelated workflows.
- Prefer iterative improvement over large first draft.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
