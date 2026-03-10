# Skills (`skills/`)

This devkit currently exposes shared Odoo development skills, including:

- `semantic-commit-message`
- `dev-workbench`
- `local-db`
- `odoo-otto`
- `odoo-shell-debug`
- `odoo-ui-check`
- `odoo-log-debug`
- `odoo-pr-review`
- `skill-authoring`
- `web-lookup`

The JS browser tooling used by the UI skill is vendored in:

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
