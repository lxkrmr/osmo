---
name: odoo-translate
description: Export and update German translations (de.po) for Odoo addons. Use when asked to update/add translations for an addon.
---

# Odoo Translation Workflow

_This skill follows `templates/SKILL.md` conventions._

## Prerequisites

- Local Odoo is running and reachable by `tools/octo`.
- Addon is installed in Odoo (required for export).
- German language `de_DE` is installed in Odoo.
- Translation terms for `de_DE` are loaded/updated (especially after fresh DB/init).

If auth/DB is not detected correctly, set env vars explicitly before running `tools/octo`:

```bash
export DATABASE=<db_name>
export DB_USER=<odoo_login>
export DB_PASSWORD=<odoo_password>
```


## Steps

### 0. Fresh instance only: update German translation terms first (mandatory)

After a new local DB/init, refresh terms once before the first export.

UI path (fresh DB, recommended):

- Settings → **Manage Languages**
- Open language: **German (de_DE)**
- Click **Update**

This is the key step that repopulates terms so existing translations are preserved in later `de.po` exports.

CLI fallback (equivalent term refresh for installed modules):

```bash
docker compose exec -T odoo odoo shell --no-http -d postgres <<'PY'
mods = env['ir.module.module'].search([('state', '=', 'installed')])
mods._update_translations(['de_DE'], overwrite=False)
print(f"Updated de_DE terms for {len(mods)} installed modules")
PY
```

If this step is skipped, `translation download` may produce a very incomplete `de.po` on fresh DBs.

### 1. Download translations from Odoo

```bash
tools/octo translation download <addon_name>
```

This exports to:

- `addons/custom/<addon_name>/i18n/de.po`

### 2. Preview auto-fill from existing translations (dry run)

```bash
tools/octo translation from-existing <addon_name> --dry-run
```

### 3. Apply auto-fill from existing translations

Use `--no-backup` by default in this repo (Git already provides restore/history):

```bash
tools/octo translation from-existing <addon_name> --no-backup
```

### 4. Review remaining untranslated entries manually

For each empty `msgstr` in `addons/custom/<addon_name>/i18n/de.po`:

- **Identical in EN/DE** (e.g., "Material", "Status") → leave `msgstr ""` empty
- **Needs translation** → provide German translation

Notes:

- `from-existing` reuses known translations; it does **not** invent new domain-specific wording.
- After fresh DB exports, custom business labels can still remain empty and must be translated manually.

When editing, verify placeholders and formatting are preserved:

- `%s`, `%d`, `%(name)s`
- HTML/XML tags
- line breaks / punctuation

### 5. Summarize changes

Report:

- auto-filled count,
- manual translations added,
- entries intentionally left empty,
- entries still untranslated.

## Troubleshooting

- **Addon not found / not installed**
  - Ensure addon exists and is installed in target DB.
- **`de_DE` missing**
  - Install German language in Odoo first.
- **Exported file misses expected translations / many empty `msgstr` on fresh DB**
  - Run Step 0 first (Manage Languages → German → Update, or CLI fallback), then export again.
  - Run `from-existing` afterwards to recover known terms.
  - Manually translate remaining business-specific labels.
  - Avoid importing/updating translations from a `de.po` that already contains empty `msgstr` for your target labels, otherwise DB terms can be overwritten with blanks.
- **Connection/auth errors**
  - Ensure Odoo is running and env vars (`DATABASE`, `DB_USER`, `DB_PASSWORD`) are correct.

## Octolib improvement idea

- This fresh-DB language-update prerequisite should ideally be automated in octolib.
- Suggested enhancement: before `translation download`, detect whether `de_DE` terms are populated and, if needed, trigger a safe term refresh (or prompt with a guided command).
- Goal: avoid exporting `de.po` files with unintended empty `msgstr` values and reduce manual UI dependency.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
