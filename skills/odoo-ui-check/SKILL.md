---
name: odoo-ui-check
description: Check local Odoo UI behavior in Odoo dev using browser-tools with a safe, repeatable workflow (read-only by default).
---

# Odoo UI Check (Local Odoo)

_This skill follows `.pi/skills/_template/SKILL.md` conventions._

Use this skill when asked to verify behavior in the local Odoo web UI (`http://localhost:8069`) instead of only DB/ORM inspection.

This skill builds on `browser-tools` and is focused on Odoo-specific checks.

## When This Skill Is Appropriate

- Verify what is actually visible/clickable in Odoo UI.
- Confirm view state differences (list/form/kanban), buttons, labels, domain effects.
- Validate company/context-dependent UI behavior.

## Critical Limits (Read Before Use)

- UI checks can be flaky if session/company context is wrong.
- DOM checks do **not** replace business-logic validation (use `odoo-shell-debug` for that).
- Do not infer DB truth from UI alone (cross-check with `local-db` when needed).
- Avoid side-effect actions (create/post/validate/send/delete) unless explicitly requested.

## Prerequisites

1. Start local services:
   ```bash
   docker compose up -d
   ```
2. Ensure Odoo is reachable:
   - `http://localhost:8069`
3. Ensure browser-tools dependencies are installed (from devkit root):
   ```bash
   ./pi-odoo-devkit.sh wizard /path/to/odoo-project --yes --with-browser-tools
   ```
4. Ensure browser-tools CDP is reachable:
   ```bash
   curl -s http://localhost:9222/json/version
   ```

## Session Strategy

- Default: start browser with fresh profile.
- Use profile mode only when login/session persistence is needed.
- Before checking behavior, confirm:
  - logged-in user,
  - active company,
  - target database/environment (local dev only).

## Standard Verification Workflow

1. Open target page in Odoo UI.
2. Confirm context (user + active company).
3. Inspect DOM state (labels, buttons, values, row counts, visibility).
4. Perform minimal navigation/interactions required by request.
5. Re-check expected state.
6. Screenshot only on explicit request.

## Odoo-Oriented DOM Checks (Examples)

Use browser-tools eval to extract reliable state in one call.

### Basic page context

```javascript
(function () {
  return {
    title: document.title,
    breadcrumb: Array.from(document.querySelectorAll('.breadcrumb-item, .o_breadcrumb li')).map(e => e.textContent.trim()).filter(Boolean),
    hasModal: !!document.querySelector('.modal.show, .o_dialog_container .modal'),
  };
})()
```

### Active company (top bar heuristic)

```javascript
(function () {
  const candidates = Array.from(document.querySelectorAll('[data-menu], .o_switch_company_menu, .dropdown-toggle, .o_navbar *'))
    .map(e => e.textContent?.trim())
    .filter(Boolean)
    .slice(0, 40);
  return { candidates };
})()
```

(Company selector markup varies by Odoo/enterprise theme; verify with visible UI text.)

### Visible primary actions/buttons

```javascript
(function () {
  return Array.from(document.querySelectorAll('button, a.btn, .o_form_button_save, .o_list_button_add'))
    .map(e => ({
      text: (e.textContent || '').trim(),
      classes: e.className,
      disabled: !!e.disabled || e.classList.contains('disabled'),
      visible: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length),
    }))
    .filter(b => b.text)
    .slice(0, 80);
})()
```

## Determinism Rules

- Prefer DOM assertions over visual interpretation.
- Batch reads in single eval calls.
- After clicks/navigation, wait briefly and re-check expected selectors.
- If state is inconsistent, reload page and re-run checks once before concluding.

## Escalation Path (Important)

If UI and backend seem inconsistent:

1. Re-check UI context (company/user/session).
2. Verify via `odoo-shell-debug` (ORM state).
3. Verify via `local-db` (raw persisted state).
4. Report mismatch explicitly instead of guessing.

## Troubleshooting

- **Login loop / unexpected user**
  - Restart browser with fresh profile; log in again.
- **Wrong company behavior**
  - Switch company in UI and re-run checks.
- **CDP not reachable**
  - Restart browser-tools Chrome and verify `:9222`.
- **Selectors unstable**
  - Use browser element picker and avoid brittle deep selectors.

## Reporting Checklist

When finishing UI checks, report:

- exact page/menu visited,
- user/company context used,
- what was observed,
- what was expected,
- whether cross-check with shell/DB was performed.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
