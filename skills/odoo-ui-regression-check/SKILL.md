---
name: odoo-ui-regression-check
description: Reusable checklist for quick Odoo UI regression spot-checks in local Odoo dev using browser-tools.
---

# Odoo UI Regression Spot-Check (Template)

_This skill follows `.pi/skills/_template/SKILL.md` conventions._

Use this as a lightweight, repeatable checklist when validating a UI change or bugfix in local Odoo.

## Scope

- Goal: catch obvious regressions quickly.
- Not a replacement for full E2E automation.
- Read-only by default; avoid side effects unless explicitly requested.

## Preconditions

- Local stack running: `docker compose up -d`
- Odoo reachable: `http://localhost:8069`
- Browser-tools deps installed: `./pi-odoo-devkit.sh wizard /path/to/odoo-project --yes --with-browser-tools`
- Browser CDP reachable: `curl -s http://localhost:9222/json/version`

## Step 1 — Define Check Matrix (before clicking)

Fill this quickly:

- **Ticket/Change:** `<id or short summary>`
- **Target view(s):** `<menu + model + view type>`
- **User context:** `<user>`
- **Company context:** `<company>`
- **Expected behavior:** `<what should happen>`
- **Out of scope:** `<what not to check now>`

## Step 2 — Baseline Context Validation

Confirm and report:

- Logged-in user is correct.
- Active company is correct.
- Correct DB/environment (local dev).
- Correct record/sample data used.

If any mismatch: stop and fix context first.

## Step 3 — Core Spot Checks

Run these checks in order:

1. **Navigation check**
   - Target menu/page opens without JS/server error dialogs.
2. **Visibility check**
   - Expected fields/buttons/columns visible.
   - Unexpected elements not shown.
3. **State check**
   - Required buttons enabled/disabled as expected.
   - Key labels/status tags match expectation.
4. **Interaction check (minimal)**
   - Perform only minimal required interaction (open form, toggle filter, switch tab).
   - Re-check resulting state via DOM.

## Step 4 — Multi-Context Spot Checks (only if relevant)

- Alternate company
- Alternate language
- Alternate access level/user
- Empty vs non-empty dataset

Only run contexts explicitly requested or clearly impacted by the change.

## Step 5 — Regression Guardrails

Quickly verify unrelated but nearby UI did not obviously break:

- list view loads
- form view opens
- no blocking modal/error toast appears
- no broken layout for key controls

## Step 6 — Evidence and Reporting

Provide concise output:

- **Checked page(s):**
- **Context used (user/company):**
- **Pass/Fail per check:**
- **Observed vs expected differences:**
- **Screenshot taken?** (only if user requested)
- **Need backend cross-check?** (`odoo-shell-debug` / `local-db`)

## Critical Notes

- UI-only confirmation is insufficient for computed/access-sensitive behavior.
- If results are ambiguous, escalate to ORM/DB checks and report uncertainty explicitly.
- One screenshot per user prompt; no autonomous screenshot loops.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
