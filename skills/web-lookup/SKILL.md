---
name: web-lookup
description: Find citation-grade web evidence (official docs, GitHub, forum) and return exact links + quotes for tickets/PRs.
example: "Use web-lookup to find official Odoo statements about credit notes and payment_state=reversed."
---

# Web Lookup (Citation-Grade)

Use this skill when you need **proof with links and verbatim quotes**, not guesses.

## When to Use

- You need an official statement for Jira/PR review.
- You must confirm whether behavior is standard Odoo or custom.
- You need supporting public discussion (forum/GitHub) with sources.

## Source Priority (Mandatory)

1. Official vendor docs (e.g. `odoo.com/documentation/...`)
2. Official source code/tests (`github.com/odoo/odoo`)
3. Vendor/community forum threads
4. Third-party blogs (only if no better source exists; mark as non-authoritative)

## Safety / Quality Rules

- Always separate **facts** from interpretation.
- Quote exact text; do not paraphrase when citing.
- Include direct URL per quote.
- Avoid AI-generated search summaries as evidence.
- If a source is weak/outdated, mark confidence as low.

## Primary Command (Preferred)

Use the helper script from devkit root:

```bash
python scripts/web_lookup.py --help
```

### Common usage

#### A) Official docs quote candidates

```bash
python scripts/web_lookup.py docs \
  "https://www.odoo.com/documentation/16.0/applications/finance/accounting/customer_invoices/credit_notes.html" \
  --keywords "legal way" "reconciles it with the related invoice" "reverse entry" \
  --mode any
```

#### B) GitHub evidence (issues/PRs)

```bash
python scripts/web_lookup.py github \
  "repo:odoo/odoo reversed payment_state" \
  --limit 10
```

#### C) Odoo forum-focused search

```bash
python scripts/web_lookup.py forum "payment_state reversed" --limit 8
```

#### D) Quote exact phrase from a URL

```bash
python scripts/web_lookup.py quote \
  "https://www.odoo.com/documentation/16.0/applications/finance/accounting/customer_invoices/credit_notes.html" \
  --contains "only legal way|reconciles it with the related invoice|reverse entry"
```

## Fallback (No helper script)

If needed, use direct inline Python snippets with `requests + bs4`.

## Output Contract (Default)

Return:

1. **Conclusion** (2-4 bullets)
2. **Evidence table** with columns:
   - Source type
   - URL
   - Exact quote
   - Why it matters
   - Confidence (high/medium/low)
3. **Gaps / unknowns**
4. **Optional follow-up search terms**

## Optional Tooling Upgrades (Ask before install)

If we want faster/cleaner extraction later, prefer:

- `trafilatura` (high-quality article/doc extraction)
- `htmlq` (fast CSS-selector extraction in shell)
- `ddgr` (terminal DDG helper)

Keep current script as baseline; add optional acceleration only with explicit install approval.

## Troubleshooting

- **Search page blocks JS/content extraction**
  - Use official API (e.g. GitHub API) or alternate HTML endpoint.
- **No exact quote found**
  - Narrow query by page and phrase, then quote source code/tests instead.
- **Conflicting sources**
  - Prefer official docs + official code/tests, and explicitly note conflicts.

## Credential Hygiene

- Use local/dev credentials only.
- Do not commit real credential values into docs, scripts, or checklists.
