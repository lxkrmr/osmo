# Skills (`skills/`)

This devkit currently exposes shared Odoo development skills, including:

- `dev-workbench`
- `local-db`
- `odoo-addon-lifecycle`
- `odoo-shell-debug`
- `odoo-translate`
- `odoo-ui-check`
- `odoo-log-debug`
- `skill-authoring`

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
