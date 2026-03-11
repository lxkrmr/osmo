#!/usr/bin/env python3
from __future__ import annotations

import configparser
import curses
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import click


@dataclass
class SkillMeta:
    name: str
    path: Path
    description: str
    command: str = ""
    example: str = ""


@dataclass
class SkillStatus:
    meta: SkillMeta
    enabled: bool
    available: bool
    reason: str


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def devkit_root() -> Path:
    return Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path | None = None) -> int:
    return subprocess.call(cmd, cwd=str(cwd) if cwd else None)


def check_project_repo(project_dir: Path) -> None:
    if not project_dir.exists():
        raise click.ClickException(f"Project repo path does not exist: {project_dir}")
    if not (project_dir / "docker-compose.yml").exists():
        raise click.ClickException(f"Not an Odoo project repo (missing docker-compose.yml): {project_dir}")


def _envrc_local_path(root: Path) -> Path:
    return root / ".envrc.local"


def get_saved_project_path(root: Path) -> Path | None:
    env_val = os.environ.get("ODOO_REPO_PATH")
    if env_val:
        return Path(env_val).expanduser().resolve()

    envrc_local = _envrc_local_path(root)
    if not envrc_local.exists():
        return None

    try:
        text = envrc_local.read_text(encoding="utf-8")
    except Exception:
        return None

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r'^export\s+ODOO_REPO_PATH\s*=\s*"?(.*?)"?\s*$', s)
        if m and m.group(1).strip():
            return Path(m.group(1).strip()).expanduser().resolve()

    return None


def save_project_path(root: Path, project_dir: Path) -> None:
    envrc_local = _envrc_local_path(root)
    envrc_local.write_text(f'export ODOO_REPO_PATH="{project_dir}"\n', encoding="utf-8")


def clear_saved_project_path(root: Path) -> None:
    envrc_local = _envrc_local_path(root)
    if envrc_local.exists():
        envrc_local.unlink()


def prompt_project_repo_path(root: Path) -> Path:
    """Prompt for project path with TAB completion, and optional save/reset of default path."""

    saved = get_saved_project_path(root)
    if saved:
        try:
            check_project_repo(saved)
            click.echo(f"Saved project path: {saved}")
            if click.confirm("Use this path?", default=True):
                return saved
            if click.confirm("Reset saved path?", default=False):
                clear_saved_project_path(root)
        except click.ClickException:
            click.echo(f"Saved project path is invalid: {saved}")
            if click.confirm("Reset saved path?", default=True):
                clear_saved_project_path(root)

    readline = None
    try:
        import readline as _readline  # type: ignore

        readline = _readline
    except Exception:
        readline = None

    old_completer = None
    old_delims = None

    if readline is not None:
        old_completer = readline.get_completer()
        old_delims = readline.get_completer_delims()
        is_libedit = "libedit" in (getattr(readline, "__doc__", "") or "").lower()

        def _normalize_prefix(text: str) -> tuple[str, str]:
            raw = text or ""
            if raw.startswith("~"):
                return raw, os.path.expanduser(raw)
            return raw, raw

        def _complete(text: str, state: int) -> str | None:
            visible_prefix, fs_prefix = _normalize_prefix(text)
            matches = glob.glob(fs_prefix + "*")
            out: list[str] = []
            for m in sorted(matches):
                display = m
                if visible_prefix.startswith("~"):
                    home = os.path.expanduser("~")
                    if display.startswith(home):
                        display = "~" + display[len(home):]
                if os.path.isdir(m):
                    display += "/"
                out.append(display)
            if state < len(out):
                return out[state]
            return None

        readline.set_completer_delims("\t\n")
        if is_libedit:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
        readline.set_completer(_complete)

    try:
        while True:
            raw = input("Enter path to your Odoo project repo: ").strip()
            if not raw:
                click.echo("Please enter a path.")
                continue
            raw = raw.replace("\\ ", " ")
            p = Path(raw).expanduser().resolve()
            try:
                check_project_repo(p)
                if click.confirm("Save as default project path for next runs?", default=True):
                    save_project_path(root, p)
                return p
            except click.ClickException as e:
                click.echo(f"{e.format_message()}")
    finally:
        if readline is not None:
            readline.set_completer(old_completer)
            if old_delims is not None:
                readline.set_completer_delims(old_delims)


def resolve_runtime_project_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "docker-compose.yml").exists():
        return cwd

    cur = cwd
    while cur != cur.parent:
        if (cur / "docker-compose.yml").exists():
            return cur
        cur = cur.parent

    raise click.ClickException(
        "Could not resolve Odoo project repo root. Run from project repo or set cwd accordingly."
    )


def preflight_checks() -> list[str]:
    rows = []
    for tool, required in [
        ("python3", True),
        ("docker", True),
        ("node", False),
        ("npm", False),
        ("direnv", False),
    ]:
        ok = command_exists(tool)
        status = "OK" if ok else ("MISSING (required)" if required else "MISSING (optional)")
        rows.append(f"- {tool}: {status}")
    return rows


def _frontmatter_value(line: str, key: str) -> str | None:
    prefix = f"{key}:"
    if not line.startswith(prefix):
        return None
    value = line.split(":", 1)[1].strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value


def parse_skill_meta(skill_dir: Path) -> SkillMeta | None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None

    description = "No description provided."
    name = skill_dir.name
    command = ""
    example = ""
    try:
        text = skill_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            i = 1
            while i < len(lines) and lines[i].strip() != "---":
                line = lines[i]
                if (v := _frontmatter_value(line, "name")) is not None:
                    name = v or name
                elif (v := _frontmatter_value(line, "description")) is not None:
                    description = v or description
                elif (v := _frontmatter_value(line, "command")) is not None:
                    command = v
                elif (v := _frontmatter_value(line, "example")) is not None:
                    example = v
                i += 1
    except Exception:
        pass

    return SkillMeta(name=name, path=skill_dir, description=description, command=command, example=example)


def discover_skills(root: Path) -> list[SkillMeta]:
    skills_root = root / "skills"
    if not skills_root.exists():
        return []
    out: list[SkillMeta] = []
    for d in sorted(skills_root.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        meta = parse_skill_meta(d)
        if meta:
            out.append(meta)
    return out


def load_skill_manifest(root: Path) -> dict:
    manifest_path = root / "skills" / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def evaluate_skill_requirements_detailed(skill_name: str, project_dir: Path, manifest: dict) -> list[dict[str, str]]:
    entry = manifest.get(skill_name, {})
    req = entry.get("requirements", {}) if isinstance(entry, dict) else {}

    failures: list[dict[str, str]] = []

    for rel in req.get("project_files", []):
        if not (project_dir / rel).exists():
            failures.append(
                {
                    "code": "missing_project_file",
                    "path": rel,
                    "message": f"missing file: {rel}",
                }
            )

    for rel in req.get("project_dirs", []):
        p = project_dir / rel
        if not p.exists() or not p.is_dir():
            failures.append(
                {
                    "code": "missing_project_dir",
                    "path": rel,
                    "message": f"missing directory: {rel}",
                }
            )

    for cmd in req.get("commands", []):
        if not command_exists(cmd):
            failures.append(
                {
                    "code": "missing_command",
                    "command": cmd,
                    "message": f"missing command: {cmd}",
                }
            )

    return failures


def evaluate_skill_requirements(skill_name: str, project_dir: Path, manifest: dict) -> tuple[bool, str]:
    failures = evaluate_skill_requirements_detailed(skill_name, project_dir, manifest)
    if failures:
        return False, "; ".join(item["message"] for item in failures)
    return True, ""


def ensure_container_dir(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def sync_symlink_set(target_dir: Path, selected: dict[str, Path]) -> list[str]:
    messages: list[str] = []
    ensure_container_dir(target_dir)

    for existing in target_dir.iterdir():
        if existing.name not in selected:
            if existing.is_symlink() or existing.is_file():
                existing.unlink()
                messages.append(f"Removed: {existing}")
            elif existing.is_dir():
                shutil.rmtree(existing)
                messages.append(f"Removed dir: {existing}")

    for name, src in selected.items():
        dst = target_dir / name
        if dst.is_symlink() and dst.resolve() == src.resolve():
            continue
        if dst.exists() or dst.is_symlink():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.symlink_to(src)
        messages.append(f"Linked: {dst} -> {src}")

    return messages


def ensure_local_exclude(project_dir: Path) -> str:
    exclude_file = project_dir / ".git" / "info" / "exclude"
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
    if any(line.strip() == ".pi/" for line in existing.splitlines()):
        return f"Local git exclude already contains '.pi/': {exclude_file}"
    with exclude_file.open("a", encoding="utf-8") as f:
        f.write("\n# local pi files\n.pi/\n")
    return f"Added local git exclude '.pi/' to: {exclude_file}"


def remove_local_exclude_entry(project_dir: Path) -> str:
    exclude_file = project_dir / ".git" / "info" / "exclude"
    if not exclude_file.exists():
        return f"SKIP: no local exclude file: {exclude_file}"

    lines = exclude_file.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    removed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == ".pi/":
            removed = True
            if new_lines and new_lines[-1].strip() == "# local pi files":
                new_lines.pop()
            i += 1
            continue
        new_lines.append(line)
        i += 1

    if not removed:
        return f"SKIP: '.pi/' not present in {exclude_file}"

    content = "\n".join(new_lines).rstrip() + "\n"
    exclude_file.write_text(content, encoding="utf-8")
    return f"UPDATED: removed '.pi/' from {exclude_file}"


def ensure_envrc(root: Path) -> list[str]:
    messages: list[str] = []
    envrc = root / ".envrc"
    gitignore = root / ".gitignore"
    venv_dir = root / ".venv"

    envrc_content = """# Odoo Skill Manager recommended environment (direnv + venv)

if [ -f .envrc.local ]; then
  source .envrc.local
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
"""

    if not envrc.exists():
        envrc.write_text(envrc_content, encoding="utf-8")
        messages.append(f"Created {envrc}")
    else:
        messages.append(f"Kept existing {envrc}")

    ignore_lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    changed = False
    for line in [".venv/", ".direnv/", ".envrc.local"]:
        if line not in ignore_lines:
            ignore_lines.append(line)
            changed = True
    if changed or not gitignore.exists():
        gitignore.write_text("\n".join(ignore_lines).strip() + "\n", encoding="utf-8")
        messages.append(f"Updated {gitignore} with .venv/.direnv ignores")

    if not venv_dir.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        messages.append(f"Created virtualenv: {venv_dir}")
    else:
        messages.append(f"Virtualenv already present: {venv_dir}")

    if command_exists("direnv"):
        messages.append("direnv detected. Run: direnv allow")
    else:
        messages.append("direnv not found. Install direnv for recommended setup, then run: direnv allow")

    return messages


def install_browser_tools(root: Path) -> list[str]:
    messages: list[str] = []
    bt_dir = root / "skills" / "browser-tools" / "browser-tools"
    if not bt_dir.exists():
        return [f"Browser tools directory missing: {bt_dir}"]

    missing = [tool for tool in ("node", "npm") if not command_exists(tool)]
    if missing:
        return [f"Browser tools setup skipped: missing dependencies: {', '.join(missing)}"]

    messages.append(f"Running npm install in {bt_dir} ...")
    subprocess.run(["npm", "install"], cwd=bt_dir, check=True)
    messages.append("Browser tools npm dependencies installed.")
    return messages


def write_local_agent_notes(project_dir: Path) -> Path:
    notes_path = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"
    content = """# Odoo Skill Manager Local Notes

<!-- managed-by: osmo installer -->

This file is generated by `osmo`.

## Shared Skill Links

- Skills: `.pi/skills/shared-osmo`

## Quick Commands

```bash
osmo --help
osmo wizard /path/to/odoo-project --yes
osmo doctor /path/to/odoo-project
```

## Browser Skill Dependency

If using `odoo-ui-check`, ensure browser-tools deps are installed:

```bash
cd /path/to/osmo
osmo wizard /path/to/odoo-project --yes
```

## Notes

- This file is local support material; it does not modify `AGENTS.md`/`CLAUDE.md` automatically.
- If you want to reference it, add a short line in your preferred agent doc.
"""
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")
    return notes_path


def current_enabled_names(target_dir: Path) -> set[str]:
    if not target_dir.exists():
        return set()
    names: set[str] = set()
    for p in target_dir.iterdir():
        if p.is_symlink() or p.exists():
            names.add(p.name)
    return names


def default_selection(all_skills: list[SkillMeta], available_skill_names: set[str]) -> set[str]:
    skill_names = {s.name for s in all_skills}
    recommended = {
        "dev-workbench",
        "local-db",
        "odoo-shell-debug",
        "odoo-otto",
        "odoo-ui-check",
        "skill-authoring",
    }
    return (recommended & skill_names) & available_skill_names


def sanitize_project_skills(project_dir: Path, managed_skills: set[str]) -> list[str]:
    actions: list[str] = []
    skills_root = project_dir / ".pi" / "skills"
    if not skills_root.exists():
        return actions

    for invalid_name in ["README.md", "_template"]:
        p = skills_root / invalid_name
        if p.exists() or p.is_symlink():
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
                actions.append(f"Removed invalid skill artifact dir: {p}")
            else:
                p.unlink()
                actions.append(f"Removed invalid skill artifact: {p}")

    for skill_name in sorted(managed_skills):
        p = skills_root / skill_name
        if not p.exists() and not p.is_symlink():
            continue
        if p.is_symlink():
            continue
        if p.is_dir():
            shutil.rmtree(p)
            actions.append(f"Removed colliding local skill dir: {p}")
        else:
            p.unlink()
            actions.append(f"Removed colliding local skill file: {p}")

    return actions


def print_agent_doc_guidance(project_dir: Path, notes_path: Path) -> None:
    click.echo("\n[agent docs]")
    click.echo(f"- Wrote local include notes: {notes_path}")

    existing = [p for p in (project_dir / "AGENTS.md", project_dir / "CLAUDE.md") if p.exists()]
    if existing:
        click.echo("- Existing agent docs detected:")
        for p in existing:
            click.echo(f"  - {p}")
        click.echo("- No automatic edits were applied (non-invasive by design).")
    else:
        click.echo("- No AGENTS.md/CLAUDE.md found at repo root. That's okay.")


def load_pg_env(project_dir: Path) -> dict[str, str]:
    cfg = configparser.ConfigParser()
    paths = [
        project_dir / "docker" / "odoo_base.conf",
        project_dir / "docker" / "odoo_local.conf",
    ]
    cfg.read([str(p) for p in paths if p.exists()])
    opt = cfg["options"] if cfg.has_section("options") else {}

    vals = {
        "PGHOST": str(opt.get("db_host", "localhost")),
        "PGPORT": str(opt.get("db_port", "5432")),
        "PGDATABASE": str(opt.get("db_name", "postgres")),
        "PGUSER": str(opt.get("db_user", "odoo")),
        "PGPASSWORD": str(opt.get("db_password", "odoo")),
    }
    if vals["PGHOST"] in {"postgres", "db"}:
        vals["PGHOST"] = "localhost"
    return vals


def check_http(url: str, name: str) -> tuple[str, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            if 200 <= r.status < 400:
                return (name, "PASS", f"reachable: {url} (HTTP {r.status})")
            return (name, "WARN", f"unexpected HTTP status {r.status}: {url}")
    except urllib.error.URLError as e:
        return (name, "WARN", f"not reachable: {url} ({e})")


def scan_content_hygiene(root: Path) -> tuple[str, str, str]:
    exclude_dirs = {".git", "node_modules", ".venv", ".direnv"}
    patterns = [
        (re.compile(r"/Users/[A-Za-z0-9._-]+"), "hardcoded macOS user path"),
        (re.compile(r"/home/[A-Za-z0-9._-]+"), "hardcoded Linux home path"),
        (re.compile(r"~/workspace/"), "hardcoded workspace home shortcut"),
        (re.compile(r"\bexample-company\b", re.IGNORECASE), "company-specific identifier placeholder"),
    ]

    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in exclude_dirs for part in path.parts):
            continue
        if path.suffix in {".lock", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}:
            continue
        if path.name == ".envrc.local":
            continue
        if path.name == "osmo.py":
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        for idx, line in enumerate(text.splitlines(), start=1):
            for rx, label in patterns:
                if rx.search(line):
                    rel = path.relative_to(root)
                    hits.append(f"{rel}:{idx} ({label})")
                    if len(hits) >= 10:
                        break
            if len(hits) >= 10:
                break
        if len(hits) >= 10:
            break

    if hits:
        preview = "; ".join(hits[:3])
        more = "" if len(hits) <= 3 else f" (+{len(hits)-3} more)"
        return ("content-hygiene", "WARN", f"Potentially non-generic content found: {preview}{more}")

    return ("content-hygiene", "PASS", "No obvious personal paths/company-specific identifiers found")


def doctor_recommendations_structured(results: list[tuple[str, str, str]], project_dir: Path) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(code: str, severity: str, message: str, next_command: str = "") -> None:
        key = (code, message, next_command)
        if key in seen:
            return
        seen.add(key)
        item = {
            "code": code,
            "severity": severity,
            "message": message,
            "next_command": next_command,
        }
        recs.append(item)

    for name, status, message in results:
        if status == "PASS":
            continue

        severity = "error" if status == "FAIL" else "warning"

        if name == "tool:python3":
            add("install_python3", severity, "Install python3 and rerun doctor.")
        elif name == "tool:docker":
            add("install_or_start_docker", severity, "Install/start Docker, then rerun doctor.")
        elif name in {"tool:node", "tool:npm"}:
            add("install_node_npm", severity, "Install Node.js + npm if you use odoo-ui-check/browser-tools.")
        elif name == "skills:shared-osmo":
            add("run_wizard_setup", severity, "Run setup wizard to install shared skills.", f"osmo wizard \"{project_dir}\"")
        elif name == "skills:collisions":
            add(
                "cleanup_skill_collisions",
                severity,
                "Clean colliding entries in .pi/skills and rerun setup.",
                f"osmo cleanup \"{project_dir}\" --all",
            )
        elif name == "skills:invalid-artifacts":
            add(
                "archive_invalid_skill_artifacts",
                severity,
                "Archive invalid .pi/skills artifacts via setup flow.",
                f"osmo wizard \"{project_dir}\"",
            )
        elif name.startswith("skill:") and name.endswith(":deps"):
            skill_name = name.split(":")[1]
            add(
                "fix_skill_prerequisites",
                severity,
                f"Fix prerequisites for skill '{skill_name}': {message}",
            )
        elif name == "odoo:web":
            add("start_odoo_services", severity, "Start Odoo services and retry.", "docker compose up -d")
        elif name == "browser:cdp":
            add(
                "start_chrome_cdp",
                severity,
                "Start Chrome with remote debugging on :9222 if you need UI/browser skills.",
            )
        elif name == "content-hygiene":
            add(
                "review_content_hygiene",
                severity,
                "Review flagged files and replace personal/company-specific hardcoded content.",
            )

    return recs


def doctor_recommendations(results: list[tuple[str, str, str]], project_dir: Path) -> list[str]:
    recs: list[str] = []
    for item in doctor_recommendations_structured(results, project_dir):
        if item["next_command"]:
            recs.append(f"{item['message']} Next: {item['next_command']}")
        else:
            recs.append(item["message"])
    return recs


def build_agent_user_mirror(fail_count: int, warn_count: int, recs: list[str]) -> dict[str, object]:
    status = "healthy" if fail_count == 0 and warn_count == 0 else "action-needed"

    if status == "healthy":
        summary = "Doctor passed: no FAIL and no WARN."
        user_lines = ["Everything looks good. No action needed."]
    else:
        summary = f"Doctor found issues: FAIL={fail_count}, WARN={warn_count}."
        user_lines = [summary]
        for rec in recs[:5]:
            user_lines.append(f"- {rec}")

    return {
        "status": status,
        "summary": summary,
        "mirror_to_user": "\n".join(user_lines),
    }


def collect_skill_statuses(root: Path, project_dir: Path) -> list[SkillStatus]:
    all_skills = discover_skills(root)
    manifest = load_skill_manifest(root)
    enabled = current_enabled_names(project_dir / ".pi" / "skills" / "shared-osmo")

    out: list[SkillStatus] = []
    for s in all_skills:
        ok, reason = evaluate_skill_requirements(s.name, project_dir, manifest)
        out.append(SkillStatus(meta=s, enabled=s.name in enabled, available=ok, reason=reason))
    return out


def enable_skill_for_project(root: Path, project_dir: Path, name: str) -> list[str]:
    src = root / "skills" / name
    marker = src / "SKILL.md"
    if not marker.exists():
        return [f"Skill not found: {name}"]

    manifest = load_skill_manifest(root)
    ok, reason = evaluate_skill_requirements(name, project_dir, manifest)
    if not ok:
        return [f"Cannot enable {name}: {reason}"]

    dst = project_dir / ".pi" / "skills" / "shared-osmo" / name
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    dst.symlink_to(src)
    messages = [f"Enabled skill: {name}"]
    messages.extend(sanitize_project_skills(project_dir, {name}))
    return messages


def disable_skill_for_project(project_dir: Path, name: str) -> list[str]:
    dst = project_dir / ".pi" / "skills" / "shared-osmo" / name
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
        return [f"Disabled skill: {name}"]
    return [f"Skill already disabled: {name}"]


def setup_project_quick(root: Path, project_dir: Path) -> list[str]:
    messages: list[str] = []

    all_skills = discover_skills(root)
    manifest = load_skill_manifest(root)
    availability: dict[str, tuple[bool, str]] = {}
    for s in all_skills:
        availability[s.name] = evaluate_skill_requirements(s.name, project_dir, manifest)

    shared_skills_dir = project_dir / ".pi" / "skills" / "shared-osmo"
    current_skills = current_enabled_names(shared_skills_dir)
    available_skill_names = {n for n, (ok, _) in availability.items() if ok}

    if current_skills:
        selected_skills = {n for n in current_skills if availability.get(n, (False, ""))[0]}
        messages.append("Keeping current enabled skills.")
    else:
        selected_skills = default_selection(all_skills, available_skill_names)
        messages.append("No skills enabled yet: applying recommended defaults.")

    (project_dir / ".pi" / "skills").mkdir(parents=True, exist_ok=True)

    skill_map = {
        s.name: s.path
        for s in all_skills
        if s.name in selected_skills and availability.get(s.name, (True, ""))[0]
    }
    messages.extend(sync_symlink_set(shared_skills_dir, skill_map))

    messages.extend(sanitize_project_skills(project_dir, set(skill_map.keys())))
    notes_path = write_local_agent_notes(project_dir)
    messages.append(f"Updated local notes: {notes_path}")
    messages.append(ensure_local_exclude(project_dir))

    if "odoo-ui-check" in selected_skills:
        messages.extend(install_browser_tools(root))

    return messages


def cleanup_project_all(project_dir: Path, remove_local_exclude: bool = False) -> list[str]:
    skills_dir = project_dir / ".pi" / "skills" / "shared-osmo"
    notes = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"

    actions: list[str] = []

    if skills_dir.exists():
        if skills_dir.is_dir() and not skills_dir.is_symlink():
            shutil.rmtree(skills_dir)
            actions.append(f"Removed dir: {skills_dir}")
        else:
            skills_dir.unlink()
            actions.append(f"Removed: {skills_dir}")

    if notes.exists():
        text = notes.read_text(encoding="utf-8")
        if "managed-by: osmo installer" in text:
            notes.unlink()
            actions.append(f"Removed: {notes}")

    if remove_local_exclude:
        actions.append(remove_local_exclude_entry(project_dir))

    if not actions:
        actions.append("Nothing to remove (project already clean).")

    return actions


def _project_path_for_ui(root: Path, project_repo_path: Path | None) -> Path:
    if project_repo_path is not None:
        project_dir = project_repo_path.expanduser().resolve()
        check_project_repo(project_dir)
        return project_dir

    saved = get_saved_project_path(root)
    if saved:
        try:
            check_project_repo(saved)
            return saved
        except click.ClickException:
            pass

    return prompt_project_repo_path(root)


def run_tui(root: Path, project_dir: Path) -> None:
    def _app(stdscr: curses.window) -> None:
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)   # title
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # enabled
        curses.init_pair(3, curses.COLOR_YELLOW, -1) # available
        curses.init_pair(4, curses.COLOR_RED, -1)    # unavailable
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # selection
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # accent

        selected_idx = 0
        scroll = 0
        messages = ["Ready."]

        def log(msgs: list[str] | str) -> None:
            nonlocal messages
            if isinstance(msgs, str):
                msgs = [msgs]

            normalized: list[str] = []
            for msg in msgs:
                s = msg.strip()
                if not s:
                    continue
                if s.lower().startswith(("cannot", "missing", "error", "failed")):
                    normalized.append(f"WARN: {s}")
                elif s.lower().startswith(("enabled", "disabled", "created", "updated", "linked", "installed", "added", "removed")):
                    normalized.append(f"OK: {s}")
                else:
                    normalized.append(s)

            messages.extend(normalized)
            messages = messages[-12:]

        while True:
            statuses = collect_skill_statuses(root, project_dir)
            if statuses:
                selected_idx = max(0, min(selected_idx, len(statuses) - 1))
            else:
                selected_idx = 0

            stdscr.erase()
            h, w = stdscr.getmaxyx()

            if h < 18 or w < 72:
                stdscr.addstr(1, 2, "osmo")
                stdscr.addstr(3, 2, f"Terminal too small ({w}x{h}).")
                stdscr.addstr(4, 2, "Please resize to at least 72x18.")
                stdscr.addstr(6, 2, "Press q to quit or r to retry.")
                stdscr.refresh()
                key = stdscr.getch()
                if key in (ord("q"), 27):
                    return
                continue

            def put(y: int, x: int, text: str, attr: int = 0) -> None:
                if y < 0 or y >= h or x < 0 or x >= w:
                    return
                width = max(0, w - x - 1)
                if width <= 0:
                    return
                try:
                    stdscr.addnstr(y, x, text, width, attr)
                except curses.error:
                    pass

            def hline(y: int, x: int, width: int) -> None:
                if width <= 0:
                    return
                put(y, x, "─" * width, curses.color_pair(1))

            def box(y: int, x: int, bh: int, bw: int, title: str = "") -> None:
                if bh < 3 or bw < 4:
                    return
                put(y, x, "┌" + ("─" * (bw - 2)) + "┐", curses.color_pair(1))
                for yy in range(y + 1, y + bh - 1):
                    put(yy, x, "│", curses.color_pair(1))
                    put(yy, x + bw - 1, "│", curses.color_pair(1))
                put(y + bh - 1, x, "└" + ("─" * (bw - 2)) + "┘", curses.color_pair(1))
                if title:
                    put(y, x + 2, f" {title} ", curses.color_pair(6) | curses.A_BOLD)

            total = len(statuses)
            enabled_count = sum(1 for s in statuses if s.enabled)
            available_count = sum(1 for s in statuses if s.available)
            unavailable_count = total - available_count

            title = "osmo"
            stats = f"enabled {enabled_count}/{total} · available {available_count} · unavailable {unavailable_count}"
            legend = "● enabled   ○ available   ✕ unavailable"
            mode = "tui"
            put(0, 2, title, curses.color_pair(1) | curses.A_BOLD)
            put(0, 24, f"[{mode}]", curses.color_pair(6) | curses.A_BOLD)
            put(0, max(2, w - len(stats) - 2), stats, curses.color_pair(1))
            put(1, 2, f"project: {project_dir}")
            put(1, max(2, w - len(legend) - 2), legend, curses.color_pair(6))
            hline(2, 1, max(0, w - 2))

            body_top = 3
            panel_x = 1
            panel_w = max(10, w - 2)

            # Layout: Skills (top), Details (middle), Activity (bottom)
            activity_h = max(6, min(10, h // 4))
            activity_top = h - activity_h - 1
            action_y = activity_top - 1

            skills_h = min(max(8, total + 3), 12)
            details_top = body_top + skills_h
            details_h = action_y - details_top

            if details_h < 6:
                shrink = 6 - details_h
                skills_h = max(6, skills_h - shrink)
                details_top = body_top + skills_h
                details_h = max(4, action_y - details_top)

            position = f"{selected_idx + 1}/{total}" if total else "0/0"
            box(body_top, panel_x, skills_h, panel_w, f"skills {position}")

            list_top = body_top + 1
            list_height = max(3, skills_h - 2)
            if total > list_height:
                put(body_top, panel_x + panel_w - 6, "↕", curses.color_pair(6) | curses.A_BOLD)

            if statuses:
                if selected_idx < scroll:
                    scroll = selected_idx
                if selected_idx >= scroll + list_height:
                    scroll = selected_idx - list_height + 1

                visible = statuses[scroll : scroll + list_height]
                for row_i, st in enumerate(visible):
                    idx = scroll + row_i
                    y = list_top + row_i

                    if st.enabled:
                        icon, color = "●", curses.color_pair(2)
                    elif st.available:
                        icon, color = "○", curses.color_pair(3)
                    else:
                        icon, color = "✕", curses.color_pair(4)

                    label = f" {icon} {st.meta.name}"
                    attr = (curses.color_pair(5) | curses.A_BOLD) if idx == selected_idx else color
                    put(y, panel_x + 1, label, attr)
            else:
                put(list_top, panel_x + 1, "No skills found.")

            box(details_top, panel_x, details_h, panel_w, "selected skill")
            if statuses:
                selected = statuses[selected_idx]
                y = details_top + 1
                content_x = panel_x + 2
                content_w = max(20, panel_w - 4)
                put(y, content_x, f"Skill: {selected.meta.name}", curses.A_BOLD)
                y += 1

                state = "enabled" if selected.enabled else ("available" if selected.available else "unavailable")
                state_color = curses.color_pair(2) if selected.enabled else (curses.color_pair(3) if selected.available else curses.color_pair(4))
                put(y, content_x, f"State: {state}", state_color | curses.A_BOLD)
                y += 1
                put(y, content_x, f"Path: skills/{selected.meta.name}")
                y += 2

                if selected.meta.command and y < details_top + details_h - 1:
                    put(y, content_x, "Quick command:", curses.A_BOLD)
                    y += 1
                    for line in textwrap.wrap(selected.meta.command, width=content_w):
                        if y >= details_top + details_h - 1:
                            break
                        put(y, content_x, line, curses.color_pair(6) | curses.A_BOLD)
                        y += 1
                    if y < details_top + details_h - 1:
                        y += 1

                if selected.meta.example and y < details_top + details_h - 1:
                    put(y, content_x, "Example:", curses.A_BOLD)
                    y += 1
                    for line in textwrap.wrap(selected.meta.example, width=content_w):
                        if y >= details_top + details_h - 1:
                            break
                        put(y, content_x, line)
                        y += 1
                    if y < details_top + details_h - 1:
                        y += 1

                put(y, content_x, "Description:", curses.A_BOLD)
                y += 1
                for line in textwrap.wrap(selected.meta.description, width=content_w):
                    if y >= details_top + details_h - 1:
                        break
                    put(y, content_x, line)
                    y += 1

                if (not selected.available) and selected.reason and y < details_top + details_h - 1:
                    y += 1
                    put(y, content_x, "Why unavailable:", curses.color_pair(4) | curses.A_BOLD)
                    y += 1
                    for line in textwrap.wrap(selected.reason, width=content_w):
                        if y >= details_top + details_h - 1:
                            break
                        put(y, content_x, line, curses.color_pair(4))
                        y += 1

            put(action_y - 1, 2, "navigation: [j/k] move  [Enter] toggle  [r] refresh  [q] quit", curses.color_pair(6))
            put(action_y, 2, "actions: [e] enable  [d] disable  [s] setup  [c] cleanup  [x] doctor  [X] full report", curses.color_pair(6))

            box(activity_top, 1, activity_h, max(10, w - 2), "activity log")
            recent_lines = messages[-max(1, activity_h - 2):]
            for i, line in enumerate(recent_lines):
                put(activity_top + 1 + i, 2, f"• {line}")

            stdscr.refresh()
            key = stdscr.getch()

            if key in (ord("q"), 27):
                return
            if key in (curses.KEY_UP, ord("k")):
                selected_idx = max(0, selected_idx - 1)
                continue
            if key in (curses.KEY_DOWN, ord("j")):
                selected_idx = min(len(statuses) - 1 if statuses else 0, selected_idx + 1)
                continue
            if key in (ord("g"),):
                selected_idx = 0
                continue
            if key in (ord("G"),):
                selected_idx = max(0, len(statuses) - 1)
                continue
            if key in (ord("r"),):
                log("View refreshed.")
                continue

            if not statuses:
                continue

            selected = statuses[selected_idx]

            if key in (ord("\n"), curses.KEY_ENTER, ord(" ")):
                if selected.enabled:
                    log(disable_skill_for_project(project_dir, selected.meta.name))
                else:
                    log(enable_skill_for_project(root, project_dir, selected.meta.name))
            elif key == ord("e"):
                log(enable_skill_for_project(root, project_dir, selected.meta.name))
            elif key == ord("d"):
                log(disable_skill_for_project(project_dir, selected.meta.name))
            elif key == ord("s"):
                log(setup_project_quick(root, project_dir))
            elif key == ord("c"):
                put(h - 1, 2, "Cleanup osmo-managed project artifacts? [y/N]")
                stdscr.refresh()
                confirm = stdscr.getch()
                if confirm in (ord("y"), ord("Y")):
                    log(cleanup_project_all(project_dir))
                else:
                    log("Cleanup cancelled.")
            elif key == ord("x"):
                results, fail_count, warn_count = run_doctor_checks(root, project_dir)
                if fail_count == 0 and warn_count == 0:
                    log("✓ Doctor: all checks passed.")
                else:
                    log(f"⚠ Doctor: FAIL {fail_count}, WARN {warn_count}")
                    recs = doctor_recommendations(results, project_dir)
                    for rec in recs[:3]:
                        log(f"→ {rec}")
                    if len(recs) > 3:
                        log(f"… {len(recs) - 3} more suggestions (press X for full report)")
            elif key == ord("X"):
                curses.def_prog_mode()
                curses.endwin()
                try:
                    subprocess.call([sys.executable, str(root / "osmo.py"), "doctor", str(project_dir)])
                    input("\nPress Enter to return to skill manager UI...")
                finally:
                    curses.reset_prog_mode()
                    stdscr.refresh()

    curses.wrapper(_app)


OUTPUT_TEXT = "text"
OUTPUT_JSON = "json"

COMMAND_SPECS = {
    "wizard": {
        "supports_dry_run": True,
        "automation_relevant": True,
    },
    "doctor": {
        "supports_dry_run": False,
        "automation_relevant": True,
    },
    "cleanup": {
        "supports_dry_run": True,
        "automation_relevant": True,
    },
    "components": {
        "supports_dry_run": False,
        "automation_relevant": True,
    },
    "enable-skill": {
        "supports_dry_run": True,
        "automation_relevant": True,
    },
    "disable-skill": {
        "supports_dry_run": True,
        "automation_relevant": True,
    },
    "reset-project-path": {
        "supports_dry_run": True,
        "automation_relevant": True,
    },
}

NON_CONTRACT_COMMANDS = [
    "ui",
    "new-skill",
    "up",
    "db",
    "shell",
    "test",
    "lint",
]


def emit_json(payload: dict) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False))


def success_payload(command: str, data: dict | None = None) -> dict:
    return {"ok": True, "command": command, "data": data or {}}


def error_payload(command: str, code: str, message: str) -> dict:
    return {"ok": False, "command": command, "error": {"code": code, "message": message}}


def _emit_success(command: str, output_mode: str, data: dict | None = None, text_lines: list[str] | None = None) -> None:
    if output_mode == OUTPUT_JSON:
        emit_json(success_payload(command, data))
        return
    for line in text_lines or []:
        click.echo(line)


def _emit_error(command: str, output_mode: str, error: Exception, code: str = "runtime_error", exit_code: int = 1) -> None:
    if output_mode == OUTPUT_JSON:
        emit_json(error_payload(command, code, str(error)))
    else:
        click.echo(str(error), err=True)
    raise SystemExit(exit_code)


def _emit_describe(command: str, output_mode: str) -> None:
    spec = COMMAND_SPECS.get(command, {})
    if output_mode == OUTPUT_JSON:
        _emit_success(command, output_mode, data={"describe": spec})
        return
    click.echo(f"Command: {command}")
    click.echo(f"  supports_dry_run: {'yes' if spec.get('supports_dry_run') else 'no'}")
    click.echo(f"  automation_relevant: {'yes' if spec.get('automation_relevant') else 'no'}")


def _maybe_describe(command: str, describe: bool, output_mode: str) -> bool:
    if not describe:
        return False
    _emit_describe(command, output_mode)
    return True


OUTPUT_OPTION = click.option(
    "--output",
    "output_mode",
    type=click.Choice([OUTPUT_TEXT, OUTPUT_JSON]),
    default=OUTPUT_TEXT,
    show_default=True,
    help="Output mode.",
)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Pi Odoo Skill Manager CLI."""


@cli.command("help")
@OUTPUT_OPTION
def help_cmd(output_mode: str) -> None:
    """Show CLI command overview (supports JSON output)."""
    command = "help"
    commands = sorted(cli.commands.keys())

    details: list[dict[str, object]] = []
    for name in commands:
        cmd = cli.commands[name]
        params: list[dict[str, object]] = []
        for p in cmd.params:
            if isinstance(p, click.Option):
                params.append(
                    {
                        "kind": "option",
                        "name": p.name,
                        "opts": list(p.opts),
                        "required": p.required,
                    }
                )
            elif isinstance(p, click.Argument):
                params.append(
                    {
                        "kind": "argument",
                        "name": p.name,
                        "required": p.required,
                        "nargs": p.nargs,
                    }
                )

        contract_scope = "automation" if name in COMMAND_SPECS else ("human-ops" if name in NON_CONTRACT_COMMANDS else "general")
        details.append(
            {
                "name": name,
                "summary": (cmd.help or "").strip().splitlines()[0] if cmd.help else "",
                "contract_scope": contract_scope,
                "automation_relevant": bool(COMMAND_SPECS.get(name, {}).get("automation_relevant", False)),
                "supports_dry_run": bool(COMMAND_SPECS.get(name, {}).get("supports_dry_run", False)),
                "params": params,
            }
        )

    data = {
        "commands": commands,
        "automation_commands": sorted(COMMAND_SPECS.keys()),
        "non_contract_commands": NON_CONTRACT_COMMANDS,
        "details": details,
    }
    text_lines = ["Available commands:", *(f"- {name}" for name in commands)]
    _emit_success(command, output_mode, data=data, text_lines=text_lines)


@cli.command("ui")
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
def ui_cmd(project_repo_path: Path | None) -> None:
    """Launch interactive skill manager TUI."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise click.ClickException("TUI requires an interactive terminal.")

    root = devkit_root()
    project_dir = _project_path_for_ui(root, project_repo_path)
    run_tui(root, project_dir)


@cli.command()
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
@click.option("--add-local-exclude", is_flag=True, help="Add '.pi/' to <project>/.git/info/exclude (local-only).")
@click.option("--yes", is_flag=True, help="Non-interactive mode (use sensible defaults)")
@click.option("--dry-run", is_flag=True, help="Show planned setup actions without modifying files")
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def wizard(
    project_repo_path: Path | None,
    add_local_exclude: bool,
    yes: bool,
    dry_run: bool,
    describe: bool,
    output_mode: str,
) -> None:
    """Run setup/reconfiguration wizard."""
    command = "wizard"
    if _maybe_describe(command, describe, output_mode):
        return

    try:
        root = devkit_root()
        interactive = sys.stdin.isatty() and not yes and not dry_run and output_mode == OUTPUT_TEXT

        if project_repo_path is None:
            if not interactive:
                raise click.ClickException("PROJECT_REPO_PATH is required in non-interactive mode.")
            project_repo_path = prompt_project_repo_path(root)

        project_dir = project_repo_path.expanduser().resolve()
        check_project_repo(project_dir)
    except click.ClickException as error:
        _emit_error(command, output_mode, error, code="validation_error", exit_code=2)

    if interactive:
        click.echo("Welcome to the Odoo Skill Manager setup wizard 👋")
        click.echo("This setup configures shared skills in your project.")
        click.echo("No changes are written until final confirmation.")
        click.echo()

    preflight = preflight_checks()
    if output_mode == OUTPUT_TEXT:
        click.echo("[preflight]")
        for row in preflight:
            click.echo(row)
        click.echo()

    missing_required = [tool for tool in ("python3", "docker") if not command_exists(tool)]
    if missing_required:
        _emit_error(
            command,
            output_mode,
            click.ClickException(f"Missing required tools: {', '.join(missing_required)}"),
            code="missing_dependencies",
            exit_code=2,
        )

    all_skills = discover_skills(root)
    manifest = load_skill_manifest(root)
    availability: dict[str, tuple[bool, str]] = {}
    for s in all_skills:
        availability[s.name] = evaluate_skill_requirements(s.name, project_dir, manifest)

    shared_skills_dir = project_dir / ".pi" / "skills" / "shared-osmo"
    current_skills = current_enabled_names(shared_skills_dir)

    available_skill_names = {n for n, (ok, _) in availability.items() if ok}
    recommended_available = default_selection(all_skills, available_skill_names)

    if current_skills:
        selected_skills = {n for n in current_skills if availability.get(n, (False, ""))[0]}
    else:
        selected_skills = set(recommended_available)

    if interactive:
        click.echo("[skills selection]")
        term_width = shutil.get_terminal_size(fallback=(100, 24)).columns
        wrap_width = max(50, term_width - 8)

        if current_skills:
            missing_recommended = sorted(recommended_available - current_skills)
            if missing_recommended:
                click.echo("  New recommended skills available (currently disabled):")
                for name in missing_recommended:
                    click.echo(f"    • {name}")
                click.echo("  You can enable them below.")

        for s in all_skills:
            ok, reason = availability.get(s.name, (True, ""))
            click.echo(f"\n  {'⛔' if not ok else '•'} {s.name}")
            desc = textwrap.fill(
                s.description,
                width=wrap_width,
                initial_indent="      ",
                subsequent_indent="      ",
            )
            click.echo(desc)

            if not ok:
                selected_skills.discard(s.name)
                why = textwrap.fill(
                    f"Unavailable: {reason}",
                    width=wrap_width,
                    initial_indent="      ",
                    subsequent_indent="      ",
                )
                click.echo(why)
                continue

            default = s.name in selected_skills
            use = click.confirm(f"      Enable {s.name}?", default=default)
            if use:
                selected_skills.add(s.name)
            else:
                selected_skills.discard(s.name)

    odoo_ui_enabled = "odoo-ui-check" in selected_skills
    enable_browser = odoo_ui_enabled

    enable_envrc = True
    enable_local_exclude = add_local_exclude or (
        click.confirm("Hide local .pi files from git status on this machine?", default=True) if interactive else False
    )

    if interactive:
        click.echo("\n[summary]")
        click.echo(f"  Project\n    {project_dir}")

        click.echo("\n  Skills to enable")
        if selected_skills:
            for name in sorted(selected_skills):
                click.echo(f"    • {name}")
        else:
            click.echo("    (none)")

        click.echo("\n  Options")
        click.echo(f"    Setup env (.envrc/.venv):     {'yes' if enable_envrc else 'no'}")
        browser_note = "yes (required by odoo-ui-check)" if enable_browser else "no (odoo-ui-check not enabled)"
        click.echo(f"    Install browser-tools deps:   {browser_note}")
        click.echo(f"    Add local git exclude (.pi/): {'yes' if enable_local_exclude else 'no'}")

        if not click.confirm("\nApply these changes now?", default=True):
            if output_mode == OUTPUT_JSON:
                _emit_success(command, output_mode, data={"project": str(project_dir), "cancelled": True})
            else:
                click.echo("Cancelled. No changes were applied.")
            return

    skill_map = {
        s.name: s.path
        for s in all_skills
        if s.name in selected_skills and availability.get(s.name, (True, ""))[0]
    }

    planned_enable = sorted(set(skill_map.keys()) - current_skills)
    planned_disable = sorted(current_skills - set(skill_map.keys()))
    unchanged = sorted(current_skills & set(skill_map.keys()))

    plan_data = {
        "project": str(project_dir),
        "dry_run": dry_run,
        "preflight": preflight,
        "selected_skills": sorted(skill_map.keys()),
        "skill_changes": {
            "enable": planned_enable,
            "disable": planned_disable,
            "unchanged": unchanged,
        },
        "options": {
            "setup_env": enable_envrc,
            "install_browser_tools": enable_browser,
            "add_local_exclude": enable_local_exclude,
        },
    }

    if dry_run:
        text_lines = [
            f"Plan for project: {project_dir}",
            f"- Enable skills: {', '.join(planned_enable) if planned_enable else '(none)'}",
            f"- Disable skills: {', '.join(planned_disable) if planned_disable else '(none)'}",
            f"- Keep skills: {', '.join(unchanged) if unchanged else '(none)'}",
            f"- Setup env: {'yes' if enable_envrc else 'no'}",
            f"- Install browser-tools deps: {'yes' if enable_browser else 'no'}",
            f"- Add local git exclude (.pi/): {'yes' if enable_local_exclude else 'no'}",
            "No files were modified (--dry-run).",
        ]
        _emit_success(command, output_mode, data=plan_data, text_lines=text_lines)
        return

    (project_dir / ".pi" / "skills").mkdir(parents=True, exist_ok=True)

    skill_msgs = sync_symlink_set(shared_skills_dir, skill_map)
    hygiene_msgs = sanitize_project_skills(project_dir, set(skill_map.keys()))
    notes_path = write_local_agent_notes(project_dir)

    local_exclude_msg = ""
    if enable_local_exclude:
        local_exclude_msg = ensure_local_exclude(project_dir)

    env_msgs: list[str] = []
    if enable_envrc:
        env_msgs = ensure_envrc(root)

    browser_msgs: list[str] = []
    if enable_browser:
        browser_msgs = install_browser_tools(root)

    if output_mode == OUTPUT_JSON:
        _emit_success(
            command,
            output_mode,
            data={
                **plan_data,
                "agent_notes": str(notes_path),
                "results": {
                    "skill_sync": skill_msgs,
                    "hygiene": hygiene_msgs,
                    "local_exclude": local_exclude_msg,
                    "env_setup": env_msgs,
                    "browser_setup": browser_msgs,
                },
            },
        )
        return

    click.echo(f"Installed skill manager into: {project_dir}")
    click.echo("\n[skills]")
    click.echo(f"- Enabled: {', '.join(sorted(skill_map.keys())) if skill_map else '(none)'}")
    for msg in skill_msgs:
        click.echo(f"- {msg}")

    if hygiene_msgs:
        click.echo("\n[pi skill hygiene]")
        for msg in hygiene_msgs:
            click.echo(f"- {msg}")

    if local_exclude_msg:
        click.echo(local_exclude_msg)

    if env_msgs:
        click.echo("\n[env setup]")
        for msg in env_msgs:
            click.echo(f"- {msg}")

    if browser_msgs:
        click.echo("\n[browser-tools]")
        for msg in browser_msgs:
            click.echo(f"- {msg}")

    print_agent_doc_guidance(project_dir, notes_path)


def run_doctor_checks(root: Path, project_dir: Path) -> tuple[list[tuple[str, str, str]], int, int]:
    results: list[tuple[str, str, str]] = []

    for tool, required in [
        ("python3", True),
        ("docker", True),
        ("node", False),
        ("npm", False),
        ("direnv", False),
    ]:
        ok = command_exists(tool)
        if ok:
            results.append((f"tool:{tool}", "PASS", "installed"))
        elif required:
            results.append((f"tool:{tool}", "FAIL", "missing required tool"))
        else:
            results.append((f"tool:{tool}", "WARN", "missing optional tool"))

    skills_dir = project_dir / ".pi" / "skills" / "shared-osmo"
    if not skills_dir.exists():
        results.append(("skills:shared-osmo", "FAIL", f"missing: {skills_dir}"))
    else:
        entries = list(skills_dir.iterdir()) if skills_dir.is_dir() else []
        results.append(("skills:shared-osmo", "PASS", f"{len(entries)} entries"))

    root_skills = project_dir / ".pi" / "skills"
    if root_skills.exists():
        collisions = []
        if skills_dir.exists() and skills_dir.is_dir():
            for s in skills_dir.iterdir():
                direct = root_skills / s.name
                if direct.exists() and not direct.is_symlink():
                    collisions.append(s.name)
        if collisions:
            results.append(("skills:collisions", "WARN", f"colliding names in .pi/skills: {', '.join(sorted(collisions))}"))
        else:
            results.append(("skills:collisions", "PASS", "no skill name collisions detected"))

        invalid = []
        for name in ["README.md", "_template"]:
            p = root_skills / name
            if p.exists() or p.is_symlink():
                invalid.append(name)
        if invalid:
            results.append(("skills:invalid-artifacts", "WARN", f"invalid entries in .pi/skills: {', '.join(invalid)}"))
        else:
            results.append(("skills:invalid-artifacts", "PASS", "none"))

    manifest = load_skill_manifest(root)
    if skills_dir.exists() and skills_dir.is_dir():
        for p in sorted(skills_dir.iterdir(), key=lambda x: x.name):
            ok, reason = evaluate_skill_requirements(p.name, project_dir, manifest)
            if ok:
                results.append((f"skill:{p.name}:deps", "PASS", "requirements satisfied"))
            else:
                results.append((f"skill:{p.name}:deps", "WARN", reason))

    results.append(check_http("http://localhost:8069", "odoo:web"))
    results.append(check_http("http://localhost:9222/json/version", "browser:cdp"))
    results.append(scan_content_hygiene(root))

    fail_count = sum(1 for _, status, _ in results if status == "FAIL")
    warn_count = sum(1 for _, status, _ in results if status == "WARN")
    return results, fail_count, warn_count


@cli.command()
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def doctor(project_repo_path: Path | None, describe: bool, output_mode: str) -> None:
    """Run health and hygiene checks."""
    command = "doctor"
    if _maybe_describe(command, describe, output_mode):
        return

    try:
        root = devkit_root()

        interactive = sys.stdin.isatty()
        if project_repo_path is None:
            if not interactive:
                raise click.ClickException("PROJECT_REPO_PATH is required in non-interactive mode.")
            project_repo_path = prompt_project_repo_path(root)

        project_dir = project_repo_path.expanduser().resolve()
        check_project_repo(project_dir)

        results, fail_count, warn_count = run_doctor_checks(root, project_dir)
        recommendations_structured = doctor_recommendations_structured(results, project_dir)
        recs = doctor_recommendations(results, project_dir)
        agent_guidance = build_agent_user_mirror(fail_count, warn_count, recs)

        if output_mode == OUTPUT_JSON:
            data = {
                "skill_manager_root": str(root),
                "project": str(project_dir),
                "fail_count": fail_count,
                "warn_count": warn_count,
                "checks": [
                    {"name": name, "status": status, "message": message}
                    for name, status, message in results
                ],
                "recommendations": recs,
                "recommendations_structured": recommendations_structured,
                "agent_guidance": agent_guidance,
            }
            _emit_success(command, output_mode, data=data)
        else:
            click.echo(f"Odoo skill manager doctor report\n- skill-manager: {root}\n- project: {project_dir}\n")

            for name, status, message in results:
                icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
                click.echo(f"{icon} [{status}] {name}: {message}")

            click.echo("\nSummary:")
            click.echo(f"- FAIL: {fail_count}")
            click.echo(f"- WARN: {warn_count}")

            if recs:
                click.echo("\nWhat to do next:")
                for i, rec in enumerate(recs, start=1):
                    click.echo(f"{i}. {rec}")

            if agent_guidance["status"] != "healthy":
                click.echo("\nAgent mirror text (copy to user):")
                click.echo(agent_guidance["mirror_to_user"])

        if fail_count:
            raise SystemExit(1)
    except click.ClickException as error:
        _emit_error(command, output_mode, error, code="validation_error", exit_code=2)


@cli.command(name="cleanup")
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
@click.option("--remove-local-exclude", is_flag=True, help="Remove '.pi/' from <project>/.git/info/exclude if present")
@click.option("--all", "remove_all", is_flag=True, help="Remove all osmo-managed links/files without interactive prompts")
@click.option("--yes", is_flag=True, help="Non-interactive mode (accept defaults)")
@click.option("--dry-run", is_flag=True, help="Show planned cleanup actions without modifying files")
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def cleanup_cmd(
    project_repo_path: Path | None,
    remove_local_exclude: bool,
    remove_all: bool,
    yes: bool,
    dry_run: bool,
    describe: bool,
    output_mode: str,
) -> None:
    """Run cleanup/uninstall flow."""
    command = "cleanup"
    if _maybe_describe(command, describe, output_mode):
        return

    try:
        root = devkit_root()
        interactive = sys.stdin.isatty() and not yes and not remove_all and not dry_run

        if project_repo_path is None:
            if not interactive:
                raise click.ClickException("PROJECT_REPO_PATH is required in non-interactive mode.")
            project_repo_path = prompt_project_repo_path(root)

        project_dir = project_repo_path.expanduser().resolve()
        check_project_repo(project_dir)
    except click.ClickException as error:
        _emit_error(command, output_mode, error, code="validation_error", exit_code=2)

    skills_dir = project_dir / ".pi" / "skills" / "shared-osmo"
    notes = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"

    remove_skills = True
    remove_notes = True

    if interactive:
        remove_skills = click.confirm("Remove installed shared skills from project (.pi/skills/shared-osmo)?", default=True)
        remove_notes = click.confirm("Remove local skill-manager notes file (.pi/DEVKIT_AGENT_NOTES.md)?", default=True)
        if not remove_local_exclude:
            remove_local_exclude = click.confirm("Remove '.pi/' entry from local git exclude?", default=False)

    actions: list[str] = []

    def _record_or_apply(path: Path, remove_enabled: bool, is_dir_remove: bool = False) -> None:
        if not remove_enabled:
            actions.append(f"SKIP: {path}")
            return

        exists = path.exists() or path.is_symlink()
        if not exists:
            actions.append(f"SKIP: {path}")
            return

        if dry_run:
            kind = "dir" if (path.is_dir() and not path.is_symlink()) or is_dir_remove else "entry"
            actions.append(f"PLAN: remove {kind}: {path}")
            return

        if (path.is_dir() and not path.is_symlink()) or is_dir_remove:
            shutil.rmtree(path)
            actions.append(f"REMOVED dir: {path}")
        else:
            path.unlink()
            actions.append(f"REMOVED: {path}")

    _record_or_apply(skills_dir, remove_skills)

    if remove_notes and notes.exists():
        text = notes.read_text(encoding="utf-8")
        if "managed-by: osmo installer" in text:
            _record_or_apply(notes, True)
        else:
            actions.append(f"SKIP: notes file not managed by installer: {notes}")
    else:
        actions.append(f"SKIP: {notes}")

    if remove_local_exclude:
        if dry_run:
            actions.append("PLAN: remove '.pi/' from local git exclude")
        else:
            actions.append(remove_local_exclude_entry(project_dir))

    visible = [line for line in actions if not line.startswith("SKIP:")]
    skipped = len(actions) - len(visible)

    if output_mode == OUTPUT_JSON:
        _emit_success(
            command,
            output_mode,
            data={
                "project": str(project_dir),
                "dry_run": dry_run,
                "actions": actions,
                "applied": visible,
                "skipped_count": skipped,
            },
        )
        return

    click.echo(f"Cleanup summary for project repo: {project_dir}")
    if visible:
        for line in visible:
            click.echo(f"- {line}")
    else:
        click.echo("- Nothing to remove (project already clean).")

    if skipped:
        click.echo(f"- Skipped unchanged entries: {skipped}")


@cli.command("reset-project-path")
@click.option("--dry-run", is_flag=True, help="Show if a saved project path would be removed")
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def reset_project_path(dry_run: bool, describe: bool, output_mode: str) -> None:
    """Forget saved default Odoo project path (.envrc.local)."""
    command = "reset-project-path"
    if _maybe_describe(command, describe, output_mode):
        return

    root = devkit_root()
    envrc_local = _envrc_local_path(root)
    exists = envrc_local.exists()

    if dry_run:
        _emit_success(
            command,
            output_mode,
            data={
                "dry_run": True,
                "path": str(envrc_local),
                "exists": exists,
                "would_remove": exists,
            },
            text_lines=[
                f"Dry-run: {'would remove' if exists else 'nothing to remove'} saved project path file: {envrc_local}"
            ],
        )
        return

    if exists:
        envrc_local.unlink()
        _emit_success(
            command,
            output_mode,
            data={"dry_run": False, "path": str(envrc_local), "removed": True},
            text_lines=[f"Removed saved project path file: {envrc_local}"],
        )
    else:
        _emit_success(
            command,
            output_mode,
            data={"dry_run": False, "path": str(envrc_local), "removed": False},
            text_lines=["No saved project path found."],
        )


@cli.command()
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def components(describe: bool, output_mode: str) -> None:
    """Show available/enabled skills from current project."""
    command = "components"
    if _maybe_describe(command, describe, output_mode):
        return

    try:
        root = devkit_root()
        project = resolve_runtime_project_root()
        skills = discover_skills(root)
        manifest = load_skill_manifest(root)

        enabled_dir = project / ".pi" / "skills" / "shared-osmo"
        enabled = {p.name for p in enabled_dir.iterdir()} if enabled_dir.exists() and enabled_dir.is_dir() else set()

        if output_mode == OUTPUT_JSON:
            data = {
                "project": str(project),
                "skill_manager_root": str(root),
                "skills": [],
            }
            for s in skills:
                failures = evaluate_skill_requirements_detailed(s.name, project, manifest)
                ok = not failures
                reason = "; ".join(item["message"] for item in failures)
                reason_code = ""
                if failures:
                    reason_code = failures[0]["code"] if len(failures) == 1 else "multiple_requirements"

                data["skills"].append(
                    {
                        "name": s.name,
                        "enabled": s.name in enabled,
                        "available": ok,
                        "reason": reason,
                        "reason_code": reason_code,
                        "requirement_failures": failures,
                        "description": s.description,
                    }
                )
            _emit_success(command, output_mode, data=data)
            return

        click.echo("\n🧰 Pi Odoo Skill Manager Components")
        click.echo(f"Project: {project}")
        click.echo(f"Skill manager: {root}\n")

        click.echo("Skills:")
        if not skills:
            click.echo("  (none)")
    except click.ClickException as error:
        _emit_error(command, output_mode, error, code="validation_error", exit_code=2)

    term_width = shutil.get_terminal_size(fallback=(100, 24)).columns
    wrap_width = max(50, term_width - 8)

    for s in skills:
        ok, reason = evaluate_skill_requirements(s.name, project, manifest)
        if ok:
            mark = "✅" if s.name in enabled else "⬜"
            click.echo(f"  {mark} {s.name}")
            wrapped = textwrap.fill(s.description, width=wrap_width, initial_indent="      ", subsequent_indent="      ")
            click.echo(wrapped)
            if s.command:
                cmd = textwrap.fill(f"Command: {s.command}", width=wrap_width, initial_indent="      ", subsequent_indent="      ")
                click.echo(cmd)
            if s.example:
                ex = textwrap.fill(f"Example: {s.example}", width=wrap_width, initial_indent="      ", subsequent_indent="      ")
                click.echo(ex)
        else:
            click.echo(f"  ⛔ {s.name}")
            wrapped = textwrap.fill(s.description, width=wrap_width, initial_indent="      ", subsequent_indent="      ")
            click.echo(wrapped)
            if s.command:
                cmd = textwrap.fill(f"Command: {s.command}", width=wrap_width, initial_indent="      ", subsequent_indent="      ")
                click.echo(cmd)
            if s.example:
                ex = textwrap.fill(f"Example: {s.example}", width=wrap_width, initial_indent="      ", subsequent_indent="      ")
                click.echo(ex)
            why = textwrap.fill(
                f"Unavailable: {reason}",
                width=wrap_width,
                initial_indent="      ",
                subsequent_indent="      ",
            )
            click.echo(why)


@cli.command("enable-skill")
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Validate skill enable without writing symlink")
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def enable_skill(name: str, dry_run: bool, describe: bool, output_mode: str) -> None:
    """Enable one skill in current project."""
    command = "enable-skill"
    if _maybe_describe(command, describe, output_mode):
        return

    try:
        root = devkit_root()
        project = resolve_runtime_project_root()
        src = root / "skills" / name
        marker = src / "SKILL.md"
        dst = project / ".pi" / "skills" / "shared-osmo" / name

        if not marker.exists():
            raise click.ClickException(f"Skill not found in skill manager: {name}")

        manifest = load_skill_manifest(root)
        ok, reason = evaluate_skill_requirements(name, project, manifest)
        if not ok:
            raise click.ClickException(f"Cannot enable skill '{name}' ({reason})")

        if dry_run:
            _emit_success(
                command,
                output_mode,
                data={"skill": name, "dry_run": True, "target": str(dst), "source": str(src)},
                text_lines=[f"OK: dry-run enable-skill '{name}' -> {dst}"],
            )
            return

        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.symlink_to(src)

        hygiene_msgs = sanitize_project_skills(project, {name})
        _emit_success(
            command,
            output_mode,
            data={"skill": name, "target": str(dst), "hygiene": hygiene_msgs},
            text_lines=[*(f"- {msg}" for msg in hygiene_msgs), f"✅ Enabled skill: {name}"],
        )
    except click.ClickException as error:
        _emit_error(command, output_mode, error, code="validation_error", exit_code=2)


@cli.command("disable-skill")
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Validate skill disable without removing symlink")
@click.option("--describe", is_flag=True, help="Describe command contract")
@OUTPUT_OPTION
def disable_skill(name: str, dry_run: bool, describe: bool, output_mode: str) -> None:
    """Disable one skill in current project."""
    command = "disable-skill"
    if _maybe_describe(command, describe, output_mode):
        return

    try:
        project = resolve_runtime_project_root()
        dst = project / ".pi" / "skills" / "shared-osmo" / name

        if dry_run:
            exists = dst.exists() or dst.is_symlink()
            _emit_success(
                command,
                output_mode,
                data={"skill": name, "dry_run": True, "target": str(dst), "exists": exists},
                text_lines=[f"OK: dry-run disable-skill '{name}' ({'will remove' if exists else 'already absent'})"],
            )
            return

        if dst.exists() or dst.is_symlink():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
            _emit_success(
                command,
                output_mode,
                data={"skill": name, "removed": True, "target": str(dst)},
                text_lines=[f"✅ Disabled skill: {name}"],
            )
        else:
            _emit_success(
                command,
                output_mode,
                data={"skill": name, "removed": False, "target": str(dst)},
                text_lines=[f"Skill already disabled: {name}"],
            )
    except click.ClickException as error:
        _emit_error(command, output_mode, error, code="validation_error", exit_code=2)


@cli.command("new-skill")
@click.argument("name")
def new_skill(name: str) -> None:
    """Scaffold a new skill."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise click.ClickException(f"Invalid skill name '{name}'. Use lowercase letters, numbers, and dashes.")

    root = devkit_root()
    template = root / "templates" / "SKILL.md"
    target_dir = root / "skills" / name
    target_file = target_dir / "SKILL.md"

    if not template.exists():
        raise click.ClickException(f"Template not found: {template}")
    if target_file.exists():
        raise click.ClickException(f"Skill already exists: {target_file}")

    target_dir.mkdir(parents=True, exist_ok=True)
    text = template.read_text(encoding="utf-8")
    text = text.replace("<skill-name>", name)
    text = text.replace("<one-line purpose>", f"Describe the purpose of {name}.")
    text = text.replace("<Skill Title>", name.replace("-", " ").title())
    target_file.write_text(text, encoding="utf-8")

    click.echo(f"Created skill scaffold: {target_file}")


@cli.command()
@click.argument("services", nargs=-1)
def up(services: tuple[str, ...]) -> None:
    """Start docker services (docker compose up -d)."""
    project = resolve_runtime_project_root()
    code = run(["docker", "compose", "up", "-d", *services], cwd=project)
    raise SystemExit(code)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def db(ctx: click.Context) -> None:
    """Open psql using project DB config."""
    project = resolve_runtime_project_root()
    env = os.environ.copy()
    env.update(load_pg_env(project))
    args = ctx.args

    if command_exists("psql"):
        code = subprocess.call(["psql", *args], cwd=project, env=env)
    else:
        click.echo("psql not found locally; using postgres container psql")
        code = subprocess.call(
            [
                "docker",
                "compose",
                "exec",
                "postgres",
                "psql",
                "-U",
                env["PGUSER"],
                "-d",
                env["PGDATABASE"],
                *args,
            ],
            cwd=project,
            env=env,
        )
    raise SystemExit(code)


@cli.command()
@click.argument("db_name", required=False)
def shell(db_name: str | None) -> None:
    """Open Odoo shell (--no-http)."""
    project = resolve_runtime_project_root()
    env = load_pg_env(project)
    db = db_name or os.environ.get("DATABASE") or env["PGDATABASE"]
    code = run(["docker", "compose", "exec", "odoo", "odoo", "shell", "--no-http", "-d", db], cwd=project)
    raise SystemExit(code)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def test(ctx: click.Context) -> None:
    """Run project test wrapper."""
    project = resolve_runtime_project_root()
    code = run(["./run-tests.sh", *ctx.args], cwd=project)
    raise SystemExit(code)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def lint(ctx: click.Context) -> None:
    """Run pre-commit wrapper."""
    project = resolve_runtime_project_root()
    args = ctx.args or ["run", "--all-files"]
    code = run(["pre-commit", *args], cwd=project)
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv

    if not args and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            root = devkit_root()
            project_dir = _project_path_for_ui(root, None)
            run_tui(root, project_dir)
        except click.ClickException as e:
            click.echo(e.format_message(), err=True)
            raise SystemExit(1)
        return

    cli.main(args=args, prog_name="osmo", standalone_mode=True)


if __name__ == "__main__":
    main()
