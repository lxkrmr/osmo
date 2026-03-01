---
name: odoo-ui-check
description: Check local Odoo UI in Chromium via Chrome DevTools Protocol (browser-tools), so the agent can inspect and validate UI behavior reliably.
---

# Odoo UI Check (Local Odoo)

Use this skill when you need to verify behavior in local Odoo UI (`http://localhost:8069`).

This skill uses the browser JS tooling adapted from Mario Zechner's `pi-skills` project:
https://github.com/badlogic/pi-skills

## Prerequisites

1. Start local stack:
   ```bash
   docker compose up -d
   ```
2. Ensure Odoo is reachable:
   - `http://localhost:8069`
3. Ensure browser-tools deps are installed (tooling lives in `skills/browser-tools/browser-tools`):
   ```bash
   ./pi-odoo-devkit.py wizard /path/to/odoo-project --yes --with-browser-tools
   ```
4. Ensure CDP is reachable:
   ```bash
   curl -s http://localhost:9222/json/version
   ```

## How browser access works

This skill opens Odoo in Chromium with Chrome DevTools Protocol (CDP) enabled on `:9222`.
That lets the browser JS helpers inspect and interact with the page deterministically.

Typical start commands (from `skills/browser-tools/browser-tools`):

```bash
./browser-start.js
./browser-nav.js http://localhost:8069
```

After Chromium is open, the user can:
- log in manually,
- navigate to the target menu/view,
- switch company/user context,
- ask for a concrete UI check.

Then the skill can run DOM checks (`browser-eval.js`), guided picker (`browser-pick.js`),
and screenshot (`browser-screenshot.js`) only when explicitly requested.

## Minimal Workflow

1. Open target Odoo page in Chromium.
2. Confirm context: correct user + company.
3. Check expected UI state (buttons/fields/labels/visibility).
4. Do minimal interaction needed.
5. Re-check expected result.
6. Report pass/fail and observed vs expected.

## Rules

- Prefer DOM checks over screenshots.
- Screenshots only on explicit user request.
- Avoid side effects (create/post/delete) unless requested.
- If UI result is ambiguous, cross-check with:
  - `odoo-shell-debug`
  - `local-db`

## Useful DOM snippets

### Page context

```javascript
(function () {
  return {
    title: document.title,
    breadcrumb: Array.from(document.querySelectorAll('.breadcrumb-item, .o_breadcrumb li')).map(e => e.textContent.trim()).filter(Boolean),
  };
})()
```

### Visible action buttons

```javascript
(function () {
  return Array.from(document.querySelectorAll('button, a.btn, .o_form_button_save, .o_list_button_add'))
    .map(e => ({
      text: (e.textContent || '').trim(),
      disabled: !!e.disabled || e.classList.contains('disabled'),
      visible: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length),
    }))
    .filter(b => b.text)
    .slice(0, 80);
})()
```

## Troubleshooting

- **CDP not reachable**
  - restart browser-tools Chrome and retry `curl` check.
- **Wrong user/company behavior**
  - re-login / switch company and re-run check.
- **Flaky selector**
  - use browser element picker.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
