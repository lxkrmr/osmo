# Agent's Log — Devkit Lower Deck

*"If the workflow is confusing, the workflow is wrong."*

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
