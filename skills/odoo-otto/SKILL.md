---
name: odoo-otto
description: Unified otto workflow for addon lifecycle and translations with agent-friendly, deterministic CLI usage.
---

# Odoo + otto (Unified Skill)

Use this skill for Odoo addon lifecycle and translation workflows through `otto`.

## Core Rules

- Use `otto` as the single interface for addon operations.
- Prefer deterministic agent usage:
  - `--output json` for machine-readable results
  - `--dry-run` before mutating commands
- Keep workflow simple and explicit (KISS).

## Prerequisites

- `otto` command is available in shell (`pipx` install recommended).
- Odoo instance is reachable.
- otto setup is completed once:

```bash
otto setup
```

## Fast Health Check

```bash
otto doctor --output json
```

If this fails, fix config/connectivity first.

## Lifecycle Workflows

### List addons

```bash
otto list --output json
otto list --not-installed --output json
```

### Install addon

```bash
otto install --dry-run <addon_name> --output json
otto install <addon_name> --output json
```

### Upgrade addon

```bash
otto upgrade --dry-run <addon_name> --output json
otto upgrade <addon_name> --output json
```

### Uninstall addon (destructive)

Only run with explicit confirmation.

```bash
otto uninstall --dry-run <addon_name> --output json
otto uninstall <addon_name> --output json
```

## Translation Workflows

### Export addon translation (`de.po`)

```bash
otto translate <addon_name> --output json
```

Notes:
- `translate` is export-only.
- Addon must be installed for export.

### Refresh language terms in Odoo (`de_DE`)

```bash
otto load-language-terms --dry-run --output json
otto load-language-terms --output json
```

## Review Guidance for `de.po`

After export, review untranslated entries in:
- `<custom_addons_path>/<addon_name>/i18n/de.po`

When proposing `msgstr` values:
1. Search existing addon translations for prior wording.
2. If multiple variants exist for same `msgid`, report the variants and ask for explicit choice.
3. Apply only confirmed wording.

## Troubleshooting

- `custom_addons_path is not set` / invalid path
  - Run `otto setup` and correct path.
- Odoo auth/connectivity issues
  - Verify host/port/database/user/password in setup config.
- Addon not found
  - Ensure addon is present in configured custom addons path.

## Credential Hygiene

- Use local/dev credentials only.
- Never commit credential values.
