---
name: odoo-pr-review
description: Assist step-by-step PR reviews in CLI + IDE with an Odoo-focused checklist, optional Jira MHTML context, and explicit human-in-charge guardrails.
---

# Odoo PR Review (Assistive, CLI + IDE)

_This skill follows `templates/SKILL.md` conventions._

Use this skill when you want a structured PR review process where the developer stays in charge.

## Core Operating Rules (Mandatory)

1. **Human reviewer is in charge**
   - The reviewer owns decisions, responsibility, and final feedback.
2. **Assist, do not take over**
   - Provide commands, reasoning, findings, and draft feedback.
   - Do not act autonomously on review submission.
3. **Never submit review by default**
   - Do **not** run `gh pr review ...` unless the developer explicitly asks.
4. **Step-by-step only**
   - One small step at a time with explicit confirmation.
5. **Intent before judgment**
   - Understand ticket intent/constraints before evaluating code quality.
6. **Evidence must be explicit**
   - For every must-fix / should-fix finding, include a concrete code snippet in Markdown code fences.
   - Never rely on implicit references like “this logic” without showing the exact lines.
   - Prefer `path + snippet + issue + impact + suggestion` over prose-only findings.

## When to Use

- You were asked to review a GitHub PR end-to-end.
- You want balanced feedback: flaws/risks + positive notes.
- You need Odoo-specific review depth (inheritance, ORM, security, upgrade impact).

## Prerequisites

- In the target repository working directory.
- IDE available (PyCharm/VSCode) for deep file navigation and chain tracing.

### GH CLI Setup Quickstart

1. Check GitHub CLI is installed:
   ```bash
   gh --version
   ```
2. Authenticate (interactive):
   ```bash
   gh auth login
   ```
3. Verify active auth/account:
   ```bash
   gh auth status
   ```
4. If auth is wrong/broken, re-login:
   ```bash
   gh auth logout -h github.com
   gh auth login
   ```

Optional SSH verification (if using SSH for git operations):

```bash
ssh -T git@github.com
```

## Intake (Context First)

At review start, ask:

1. PR number/link
2. Optional ticket context file (MHTML)
3. Whether to do a quick scan first or deep review directly

### If ticket MHTML is not available, offer capture instructions

Chrome / Chromium / Edge:

1. Open the Jira issue page.
2. Expand sections/comments needed for context.
3. Open DevTools (`F12` / `Cmd+Option+I`).
4. Open Command Menu (`Cmd+Shift+P` / `Ctrl+Shift+P`).
5. Run **Capture snapshot**.
6. Use the downloaded `.mhtml` path as review context.

## Review Workflow (Assistive)

1. **Read PR metadata (CLI)**
   ```bash
   gh pr view <PR_NUMBER>
   ```
2. **Read changed files list (CLI)**
   ```bash
   gh pr diff <PR_NUMBER> --name-only
   ```
3. **Read full patch (CLI)**
   ```bash
   gh pr diff <PR_NUMBER>
   ```
4. **Open critical files in IDE**
   - Guide the reviewer to inspect risky paths first.
   - Trace inheritance/override chains where relevant.
5. **Build findings with evidence**
   - Separate facts, assumptions, and open questions.
   - Quote exact code snippets for each finding (and proposed snippet when suggesting a fix).
   - Include file paths with every snippet.
6. **Draft feedback**
   - Provide must-fix / should-fix / positive notes.
7. **Reviewer submits final decision**
   - Offer command options, but reviewer executes them.

## Odoo Review Checklist

### A) Odoo-ish implementation

- Follows Odoo conventions and module boundaries.
- Uses ORM patterns correctly (recordsets, domains, context, compute dependencies).
- Avoids non-idiomatic workarounds without rationale.

### B) Intent alignment

- Ticket intent (or MHTML context) matches implementation behavior.
- Acceptance criteria are clearly covered or gaps are called out.

### C) Inheritance chain impact (when relevant)

- Method overrides (`create`, `write`, `unlink`, computes, onchange) preserve chain expectations.
- `super()` usage and side effects are correct.
- View/model inheritance impact is understood and safe.

### D) Flaws and risks

- Security/ACL/record rules correctness.
- Upgrade/data impact (manifest bump, migration needs, data safety).
- Performance risks (N+1, expensive loops, domain/query choices).
- Reliability edge cases (cron/queue/retry/error paths).

### E) Positive feedback

- Explicitly highlight good decisions and clean patterns.
- Call out thoughtful trade-offs and maintainable design choices.

## Suggested Review Output

Use this structure when sharing findings with the reviewer:

1. **Intent Summary**
   - What the PR tries to achieve (validated against ticket context).
2. **Critical Findings (must-fix)**
   - For each finding, use:
     - **Path**
     - **Current code snippet**
     - **Issue**
     - **Impact**
     - **Suggested change** (include snippet when possible)
3. **Important Suggestions (should-fix)**
   - Same evidence format as must-fix findings.
4. **Positive Notes**
   - What is done well and should be kept.
5. **Open Questions**
   - What needs clarification from author/reviewer.
6. **Suggested Final Review Commands (reviewer-run)**
   - Provide options only.

### Finding Template (Markdown, explicit evidence)

````md
### <Short finding title>

**Path:** `path/to/file.py`

**Current code:**
```python
# exact relevant snippet
```

**Issue:**
<what is wrong or risky>

**Impact:**
<why this matters>

**Suggested change:**
```python
# concrete alternative (if applicable)
```
````

## Reviewer-Run Command Options

```bash
# approve
gh pr review <PR_NUMBER> --approve

# request changes
gh pr review <PR_NUMBER> --request-changes -b "<blocking feedback>"

# comment only
gh pr review <PR_NUMBER> --comment -b "<non-blocking feedback>"
```

## Closure and Cleanup

- Review support ends when the reviewer submits their decision.
- This is independent of merge (PR creator owns merge).
- If temporary notes were created, propose cleanup and wait for explicit developer confirmation before deleting.

## Notes

- Keep comments high-signal and actionable.
- Combine with `odoo-shell-debug` for ORM/runtime inspection.
- Combine with `local-db` for SQL/data verification.
- Combine with `odoo-ui-check` for UI-visible behavior.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
