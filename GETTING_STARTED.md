# Getting Started (Clone → Wizard → Start)

This guide is for new team members.

## 1) Clone repositories

```bash
cd /path/to/workspace
git clone <odoo-project-repo-url> odoo-project
git clone <pi-odoo-devkit-repo-url> pi-odoo-devkit
```

(Directory names can differ. Use explicit paths in commands.)

## 2) Run setup wizard

```bash
cd /path/to/pi-odoo-devkit
./pi-odoo-devkit.sh wizard /path/to/odoo-project
```

The wizard will guide you step by step.
No changes are written until final confirmation.

## 3) (Recommended) allow direnv

```bash
cd /path/to/pi-odoo-devkit
direnv allow
```

## 4) Run doctor

```bash
./pi-odoo-devkit.sh doctor /path/to/odoo-project
```

Fix FAIL items first.

## 5) Start using devkit from project repo

```bash
cd /path/to/odoo-project
./.pi/tools/devkit --help
./.pi/tools/devkit components
./.pi/tools/devkit up
```

If using browser skills, start Chromium/CDP as described in `skills/browser-tools/SKILL.md`.

---

## If you already have `AGENTS.md` / `CLAUDE.md`

Wizard does not modify those files automatically.

Check:
- `/path/to/odoo-project/.pi/DEVKIT_AGENT_NOTES.md`

Copy the suggested include note manually if you want.

---

## Reconfigure later

```bash
cd /path/to/pi-odoo-devkit
./pi-odoo-devkit.sh wizard /path/to/odoo-project
```

You can also toggle individual items quickly:

```bash
cd /path/to/odoo-project
./.pi/tools/devkit enable-skill browser-tools
./.pi/tools/devkit disable-skill odoo-translate
```

---

## Cleanup

```bash
cd /path/to/pi-odoo-devkit
./pi-odoo-devkit.sh cleanup /path/to/odoo-project

# full cleanup
./pi-odoo-devkit.sh cleanup /path/to/odoo-project --all --remove-local-exclude
```
