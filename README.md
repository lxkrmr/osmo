# pi-odoo-devkit

Lean helper CLI for Odoo + pi.dev local workflows.

## Usage

```bash
./pi-odoo-devkit.py --help
```

Main commands:

```bash
./pi-odoo-devkit.py wizard [PROJECT_REPO_PATH]
./pi-odoo-devkit.py doctor [PROJECT_REPO_PATH]
./pi-odoo-devkit.py cleanup [PROJECT_REPO_PATH]
```

Path behavior is consistent for all three:
- pass `PROJECT_REPO_PATH`, or
- run interactively and enter it when prompted.

In non-interactive mode, the path is required.

## From your Odoo project

After `wizard`, use:

```bash
./.pi/devkit --help
./.pi/devkit components
./.pi/devkit up
./.pi/devkit db
./.pi/devkit shell
```

## Skills

This devkit exposes one Odoo UI browser skill:
- `odoo-ui-check`

Browser JS helpers used by that skill are in:
- `skills/browser-tools/browser-tools/`

Credit/source for those helpers is documented directly in `skills/odoo-ui-check/SKILL.md`.
