# Pi Odoo Devkit (repository: `pi-odoo-devkit`)

A toolbox for **agentic coding in Odoo with pi.dev**.

It provides Pi-oriented skills, setup wizards, health checks, and component management to keep local Odoo development workflows consistent and low-friction.

## Main entrypoint

Use the toolbox command:

```bash
./pi-odoo-devkit.sh --help
```

Primary subcommands:

- `wizard` — guided setup/reconfiguration
- `doctor` — health + dependency + hygiene checks
- `components` — show available/enabled skills and commands
- `enable-skill` / `disable-skill`
- `enable-command` / `disable-command`
- `new-skill` — scaffold new skill from template
- `cleanup` — guided uninstall/cleanup

## Repository layout

- `skills/` — reusable skills (for Pi users)
  - includes `skills/manifest.json` for dependency-based availability rules
- `commands/` — helper command implementation
- `templates/` — templates for creating new skills
- `bootstrap/install.py` — wizard implementation backend
- `bootstrap/doctor.py` — diagnostics backend
- `bootstrap/uninstall.py` — cleanup backend
- `THIRD_PARTY.md` + `LICENSES/` — attribution and license texts
- `SECURITY.md` — security/privacy authoring rules

## Recommended setup (direnv + .venv)

The wizard can set up a local Python environment managed by `direnv`:

- `.envrc` at devkit root
- `.venv` for Python tooling isolation
- optional `.envrc.local` (stores `ODOO_REPO_PATH`)

## Install / Reconfigure (wizard)

```bash
# interactive wizard (recommended for newcomers)
./pi-odoo-devkit.sh wizard /path/to/odoo-project
```

Wizard mode guides users through:
- dependency checks,
- project path confirmation,
- skill selection (with descriptions and availability checks),
- command selection,
- optional browser-tools dependencies,
- optional local git exclude,
- optional local env setup.

Non-interactive example:

```bash
./pi-odoo-devkit.sh wizard /path/to/odoo-project --yes --with-browser-tools --add-local-exclude --set-project-env
```

Or using environment variable:

```bash
ODOO_REPO_PATH=/path/to/odoo-project ./pi-odoo-devkit.sh wizard
```

## What wizard sets up

Links in project repo:

- `.pi/skills/shared-devkit/` (selected skills as symlinks)
- `.pi/tools/shared-devkit/` (selected commands as symlinks)
- `.pi/tools/devkit` → main devkit entrypoint (`pi-odoo-devkit.sh`)

Additional local support file:

- `.pi/DEVKIT_AGENT_NOTES.md`

Installer is non-invasive and does **not** edit `AGENTS.md` / `CLAUDE.md` automatically.

Recommendation: keep `AGENTS.md` / `CLAUDE.md` lean and put workflow-specific rules into skills.

## Component management after setup

From project repo:

```bash
./.pi/tools/devkit components
./.pi/tools/devkit enable-skill browser-tools
./.pi/tools/devkit disable-skill odoo-translate
```

## Doctor checks

```bash
./pi-odoo-devkit.sh doctor /path/to/odoo-project
```

Doctor checks:
- tool availability,
- enabled skill dependency requirements,
- runtime reachability hints (`:8069`, `:9222`),
- content hygiene for obvious secret/path leakage.

## Cleanup

```bash
# guided cleanup
./pi-odoo-devkit.sh cleanup /path/to/odoo-project

# full cleanup
./pi-odoo-devkit.sh cleanup /path/to/odoo-project --all --remove-local-exclude
```

Cleanup removes only devkit-managed links/files; existing custom local `.pi` files remain untouched.

## Credits

- Built for **pi.dev** agentic coding workflows.
- Browser tooling is adapted from Mario Zechner's `pi-skills` project.

See `THIRD_PARTY.md` and `LICENSES/`.
