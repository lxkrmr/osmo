#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"


def discover_skill_dirs() -> set[str]:
    names: set[str] = set()
    for p in SKILLS_DIR.iterdir():
        if not p.is_dir() or p.name.startswith("_"):
            continue
        if (p / "SKILL.md").exists():
            names.add(p.name)
    return names


def load_manifest_keys() -> set[str]:
    path = SKILLS_DIR / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.keys())


def extract_skill_list(md_path: Path, marker: str) -> set[str]:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    collecting = False
    names: set[str] = set()

    for line in lines:
        if not collecting and line.strip() == marker:
            collecting = True
            continue

        if not collecting:
            continue

        if line.startswith("## "):
            break

        stripped = line.strip()
        if not stripped:
            continue

        match = re.match(r"^- `([^`]+)`$", stripped)
        if match:
            names.add(match.group(1))
            continue

        if names:
            break

    return names


def extract_recommended_defaults(py_path: Path) -> set[str]:
    text = py_path.read_text(encoding="utf-8")
    match = re.search(r"recommended\s*=\s*\{(?P<body>.*?)\}\n\s*return", text, re.DOTALL)
    if not match:
        return set()

    names = set(re.findall(r'"([a-z0-9\-]+)"', match.group("body")))
    return names


def main() -> int:
    errors: list[str] = []

    discovered = discover_skill_dirs()
    manifest = load_manifest_keys()

    stale_manifest = manifest - discovered
    if stale_manifest:
        errors.append(f"manifest has non-existing skills: {sorted(stale_manifest)}")

    root_readme = extract_skill_list(ROOT / "README.md", "Current shared skills in this skill manager:")
    skills_readme = extract_skill_list(SKILLS_DIR / "README.md", "This skill manager currently exposes shared Odoo development skills, including:")

    if root_readme != discovered:
        errors.append(
            "README.md skill list mismatch: "
            f"expected {sorted(discovered)} got {sorted(root_readme)}"
        )

    if skills_readme != discovered:
        errors.append(
            "skills/README.md skill list mismatch: "
            f"expected {sorted(discovered)} got {sorted(skills_readme)}"
        )

    defaults = extract_recommended_defaults(ROOT / "pi-odoo-skill-manager.py")
    stale_defaults = defaults - discovered
    if stale_defaults:
        errors.append(f"default skill selection contains missing skills: {sorted(stale_defaults)}")

    if errors:
        print("Skill consistency check failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("Skill consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
