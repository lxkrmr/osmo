# Security & Privacy Guidelines

This devkit is intended to be generic and safe to share.

## Goals

- No real credentials, tokens, or secrets in committed files.
- No personal local machine details (e.g. `/Users/<name>`, home-directory-specific examples).
- No company-internal identifiers in generic examples.

## Rules

1. Use placeholders for credentials:
   - `<odoo_login>`, `<odoo_password>`, `<db_name>`
2. Use generic paths in docs:
   - `/path/to/odoo-project`, `/path/to/pi-odoo-devkit`
3. Do not commit generated local data:
   - `.venv/`, `.direnv/`, `node_modules/`
4. Keep examples vendor-neutral unless explicitly required.
5. Preserve third-party attribution/license text when adapting code.

## Recommended Checks

Run doctor before sharing or tagging releases:

```bash
./pi-odoo-devkit.sh doctor /path/to/odoo-project
```

Doctor includes a content-hygiene check for obvious personal-path/company-specific patterns.

## Reporting

If you spot sensitive content, remove it immediately and rotate impacted credentials if needed.
