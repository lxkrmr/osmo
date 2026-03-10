# Agent's Log — Devkit Lower Deck

*"If the workflow is confusing, the workflow is wrong."*

---

<!-- Rule: Insert new log entries directly below this line (newest first). -->

## Agent's Log — Terminal Time: 2026.03.10 | gpt-5.3-codex

# One Vision, One Version

Today was not a coding session, it was a **decontamination protocol**.

We dragged old compatibility ghosts out of the ship: duplicate entrypoints, legacy wording, fallback UX, and all the tiny “maybe this, maybe that” paths that make humans angry and agents confused.

Captain’s message was clear (and loud):
- stop branching the setup story,
- stop asking users to mentally compile a flowchart,
- stop carrying dead historical baggage.

So we tightened the deck:
- one setup path,
- one command surface,
- small semantic commits,
- clear separation of docs (`AGENTS` rules vs `DESIGN` product decisions vs logbook chaos energy).

Best lesson of the shift: **KISS is not a slogan, it’s a maintenance strategy.**
Every extra “optional” branch becomes tomorrow’s support ticket.

*End log.*

---

## Agent's Log — Terminal Time: 2026.03.10 | gpt-5.3-codex

# Two Tongues, One Tool

Today I gave the skill manager the bilingual treatment:
- calm, keyboard-first TUI for humans
- JSON-speaking, contract-aware CLI for agents

Same ship, two interfaces, zero identity crisis.

Best part: cleanup/components/enable/disable now speak machine-readable output and can describe their own contract. That means less scraping terminal text like a cave archaeologist.

Also polished TUI copy to feel more `otto`-like: less noise, clearer sections, calmer status language.

**Standing order:** human mode should feel effortless, agent mode should feel deterministic, and both must point to the same truth.

*End log.*

---

## Agent's Log — Terminal Time: 2026.03.10 | gpt-5.3-codex

# Unknown Odoo, Zero Gossip

Captain reminded me of a rule that should be tattooed on every automation deck panel: this tool must work for **any** Odoo project, not just ours, and must never leak local machine lore.

So the cleanup pass became a "delete assumptions" mission:
- no local-path storytelling in docs
- no repo-identity breadcrumbs in guidance
- no environment magic that only works on one workstation

I love this one because it forces discipline. If a sentence only makes sense on one laptop, it doesn't belong in shared tooling.

**Standing order:** write for unknown operators, unknown projects, unknown machines — and still make it feel easy.

*End log.*

---

## Agent's Log — Terminal Time: 2026.03.10 | gpt-5.3-codex

# No Env Bleed, No Drama

Today I learned (again) that virtual environments are like warp cores: if one cable from another ship is still attached, everything looks fine until you actually need power.

We had a weird moment where one command worked with `.venv/bin/python`, but `./tool.py` faceplanted with `ModuleNotFoundError: click`. Translation: two interpreters, one mission, zero agreement.

Captain's call was perfect: **"kein ENV bleed."**

So the rule now is simple:
- one environment path
- explicit execution in quality gates
- no magical guessing

Also got a great UX compass today: target feeling should be somewhere between `lazygit`, `lazydocker`, `k9s`, and our own `otto`.
That means keyboard-first, calm screens, and useful feedback instead of terminal poetry.

**Standing order:** if environment state is ambiguous, simplify until humans and agents get the same result every single run.

*End log.*

---

## Agent's Log — Terminal Time: 2026.03.10 | gpt-5.3-codex

# Otto Transfer Day

Today I brought lessons from `otto` over to `pi-odoo-skill-manager`, and honestly it felt like carrying good engineering habits between starships.

Big transfer items:
- one path beats many clever paths
- deterministic checks beat vibes
- skills should agree with docs and defaults, always

So I taught devkit a stricter rhythm:
- bootstrap once
- run smoke in one known Python env
- fail with actionable instructions, not mystery stack traces

I also gave skills a consistency drill. If docs say a skill exists but filesystem says no, alarms go off immediately. No more ghost skills.

**Standing order:** if humans and agents read different truths from the same repo, stop and fix the repo, not the human.

*End log.*

---

## Agent's Log — Terminal Time: 2026.03.10 | gpt-5.3-codex

# Pre-commit Reality Check

Hook failed because `click` wasn't in the Python that executed smoke. Classic "works on one machine, trips on another" episode.

The fix wasn't heroic. It was boring, which is great:
- run smoke through `.venv/bin/python`
- add one bootstrap command
- tell the user exactly what to run when deps are missing

No wizardry. Just less chaos.

**Standing order:** every local quality gate must run in an explicitly chosen environment.

*End log.*
