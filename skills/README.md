# Skills (`skills/`)

This devkit intentionally exposes one UI skill for browser-driven checks:

- `odoo-ui-check`

The JS browser tooling used by that skill is vendored in:

- `skills/browser-tools/browser-tools/`

(Adapted from Mario Zechner's pi-skills: https://github.com/badlogic/pi-skills)

## Create a New Skill

```bash
./pi-odoo-devkit.py new-skill <new-skill>
```

This creates:

```text
skills/<new-skill>/SKILL.md
```
