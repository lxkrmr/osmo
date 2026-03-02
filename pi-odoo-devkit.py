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
from datetime import datetime
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


def evaluate_skill_requirements(skill_name: str, project_dir: Path, manifest: dict) -> tuple[bool, str]:
    entry = manifest.get(skill_name, {})
    req = entry.get("requirements", {}) if isinstance(entry, dict) else {}

    reasons: list[str] = []
    for rel in req.get("project_files", []):
        if not (project_dir / rel).exists():
            reasons.append(f"missing file: {rel}")
    for rel in req.get("project_dirs", []):
        p = project_dir / rel
        if not p.exists() or not p.is_dir():
            reasons.append(f"missing directory: {rel}")
    for cmd in req.get("commands", []):
        if not command_exists(cmd):
            reasons.append(f"missing command: {cmd}")

    if reasons:
        return False, "; ".join(reasons)
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

    envrc_content = """# Odoo Devkit recommended environment (direnv + venv)
export ODOO_DEVKIT_ROOT=\"$(pwd)\"

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
    content = """# Odoo Devkit Local Notes

<!-- managed-by: devkit installer -->

This file is generated by `pi-odoo-devkit.py`.

## Shared Devkit Links

- Skills: `.pi/skills/shared-devkit`
- Dev command: `.pi/devkit`

## Quick Commands

```bash
./.pi/devkit --help
./.pi/devkit up
./.pi/devkit db
./.pi/devkit shell
```

## Browser Skill Dependency

If using `odoo-ui-check`, ensure browser-tools deps are installed:

```bash
cd /path/to/pi-odoo-devkit
./pi-odoo-devkit.py wizard /path/to/odoo-project --with-browser-tools --yes
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
        "odoo-addon-lifecycle",
        "odoo-translate",
        "odoo-ui-check",
        "skill-authoring",
    }
    return (recommended & skill_names) & available_skill_names


def archive_path(base_dir: Path, name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return base_dir / f"{name}.{stamp}"


def _devkit_skills_backup_root(project_dir: Path) -> Path:
    return project_dir / ".pi" / "_devkit-backups" / "skills"


def sanitize_project_skills(project_dir: Path, managed_skills: set[str]) -> list[str]:
    actions: list[str] = []
    skills_root = project_dir / ".pi" / "skills"
    if not skills_root.exists():
        return actions

    # Migrate old backup location that was inside .pi/skills (pi discovers it and warns)
    old_backup_root = skills_root / "_disabled-by-devkit"
    backup_root = _devkit_skills_backup_root(project_dir)
    backup_root.mkdir(parents=True, exist_ok=True)

    if old_backup_root.exists():
        migrated_target = archive_path(backup_root, "legacy-disabled-skills")
        shutil.move(str(old_backup_root), str(migrated_target))
        actions.append(f"Moved legacy backup out of .pi/skills: {old_backup_root} -> {migrated_target}")

    for invalid_name in ["README.md", "_template"]:
        p = skills_root / invalid_name
        if p.exists() or p.is_symlink():
            dest = archive_path(backup_root, invalid_name)
            shutil.move(str(p), str(dest))
            actions.append(f"Archived invalid skill artifact: {p} -> {dest}")

    for skill_name in sorted(managed_skills):
        p = skills_root / skill_name
        if not p.exists() and not p.is_symlink():
            continue
        if p.is_symlink():
            continue
        dest = archive_path(backup_root, skill_name)
        shutil.move(str(p), str(dest))
        actions.append(f"Archived colliding local skill: {p} -> {dest}")

    return actions


def migrate_legacy_tools(project_dir: Path) -> list[str]:
    actions: list[str] = []
    tools_dir = project_dir / ".pi" / "tools"
    if not tools_dir.exists():
        return actions

    backup = project_dir / ".pi" / "_legacy-tools-disabled"
    target = archive_path(backup, "tools")
    backup.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tools_dir), str(target))
    actions.append(f"Archived legacy .pi/tools directory: {tools_dir} -> {target}")
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
        (re.compile(r"\bphiloro\b", re.IGNORECASE), "company-specific identifier"),
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
        if path.name == "pi-odoo-devkit.py":
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


def doctor_recommendations(results: list[tuple[str, str, str]], project_dir: Path) -> list[str]:
    recs: list[str] = []
    seen: set[str] = set()

    def add(msg: str) -> None:
        if msg not in seen:
            seen.add(msg)
            recs.append(msg)

    for name, status, message in results:
        if status == "PASS":
            continue

        if name == "tool:python3":
            add("Install python3 and rerun doctor.")
        elif name == "tool:docker":
            add("Install/start Docker, then rerun doctor.")
        elif name in {"tool:node", "tool:npm"}:
            add("Install Node.js + npm if you use odoo-ui-check/browser-tools.")
        elif name == "skills:shared-devkit":
            add(f"Run setup: ./pi-odoo-devkit.py wizard \"{project_dir}\"")
        elif name == "link:.pi/devkit":
            add(f"Recreate project entrypoint: ./pi-odoo-devkit.py wizard \"{project_dir}\"")
        elif name == "pi:legacy-tools":
            add(f"Remove legacy artifacts: ./pi-odoo-devkit.py cleanup \"{project_dir}\" --all")
        elif name == "skills:collisions":
            add(f"Clean collisions: ./pi-odoo-devkit.py cleanup \"{project_dir}\" --all, then rerun setup.")
        elif name == "skills:invalid-artifacts":
            add(f"Archive invalid artifacts via setup: ./pi-odoo-devkit.py wizard \"{project_dir}\"")
        elif name.startswith("skill:") and name.endswith(":deps"):
            add(f"Fix skill prerequisites for {name.split(':')[1]}: {message}")
        elif name == "odoo:web":
            add("Start Odoo services (e.g. docker compose up -d) and retry.")
        elif name == "browser:cdp":
            add("Start Chrome with remote debugging on :9222 if you need UI/browser skills.")
        elif name == "content-hygiene":
            add("Review flagged files and replace personal/company-specific hardcoded content.")

    return recs


def collect_skill_statuses(root: Path, project_dir: Path) -> list[SkillStatus]:
    all_skills = discover_skills(root)
    manifest = load_skill_manifest(root)
    enabled = current_enabled_names(project_dir / ".pi" / "skills" / "shared-devkit")

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

    dst = project_dir / ".pi" / "skills" / "shared-devkit" / name
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
    dst = project_dir / ".pi" / "skills" / "shared-devkit" / name
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

    shared_skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
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

    local_devkit_link = project_dir / ".pi" / "devkit"
    target = root / "pi-odoo-devkit.py"
    if local_devkit_link.exists() or local_devkit_link.is_symlink():
        if not (local_devkit_link.is_symlink() and local_devkit_link.resolve() == target.resolve()):
            local_devkit_link.unlink()
            local_devkit_link.symlink_to(target)
            messages.append(f"Updated project entrypoint: {local_devkit_link}")
    else:
        local_devkit_link.symlink_to(target)
        messages.append(f"Created project entrypoint: {local_devkit_link}")

    messages.extend(sanitize_project_skills(project_dir, set(skill_map.keys())))
    messages.extend(migrate_legacy_tools(project_dir))
    notes_path = write_local_agent_notes(project_dir)
    messages.append(f"Updated local notes: {notes_path}")
    messages.append(ensure_local_exclude(project_dir))

    if "odoo-ui-check" in selected_skills:
        messages.extend(install_browser_tools(root))

    return messages


def cleanup_project_all(project_dir: Path, remove_local_exclude: bool = False) -> list[str]:
    skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
    local_devkit = project_dir / ".pi" / "devkit"
    notes = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"
    legacy_tools = project_dir / ".pi" / "tools"
    legacy_skill_backup = project_dir / ".pi" / "skills" / "_disabled-by-devkit"
    devkit_backups = project_dir / ".pi" / "_devkit-backups"
    legacy_tools_backup = project_dir / ".pi" / "_legacy-tools-disabled"

    actions: list[str] = []

    if skills_dir.exists():
        if skills_dir.is_dir() and not skills_dir.is_symlink():
            shutil.rmtree(skills_dir)
            actions.append(f"Removed dir: {skills_dir}")
        else:
            skills_dir.unlink()
            actions.append(f"Removed: {skills_dir}")

    if local_devkit.exists() or local_devkit.is_symlink():
        local_devkit.unlink()
        actions.append(f"Removed: {local_devkit}")

    if notes.exists():
        text = notes.read_text(encoding="utf-8")
        if "managed-by: devkit installer" in text:
            notes.unlink()
            actions.append(f"Removed: {notes}")

    if legacy_tools.exists():
        shutil.rmtree(legacy_tools)
        actions.append(f"Removed dir: {legacy_tools}")

    for p in [legacy_skill_backup, devkit_backups, legacy_tools_backup]:
        if p.exists():
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
                actions.append(f"Removed dir: {p}")
            else:
                p.unlink()
                actions.append(f"Removed: {p}")

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
        messages = ["Ready. Use ↑/↓ and Enter."]

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
                    normalized.append(f"⚠ {s}")
                elif s.lower().startswith(("enabled", "disabled", "created", "updated", "linked", "installed", "added", "removed")):
                    normalized.append(f"✓ {s}")
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
                stdscr.addstr(1, 2, "pi-odoo-devkit")
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

            title = "🧰 pi-odoo-devkit"
            stats = f"enabled {enabled_count}/{total}  available {available_count}  unavailable {unavailable_count}"
            legend = "● enabled   ○ available   ✕ unavailable"
            mode = "STACK"
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
            box(body_top, panel_x, skills_h, panel_w, f"Skills {position}")

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

            box(details_top, panel_x, details_h, panel_w, "Details")
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

            put(action_y, 2, "[Enter] toggle  [e] enable  [d] disable  [s] setup  [c] cleanup  [x] doctor  [X] full doctor  [r] refresh  [q] quit", curses.color_pair(6))

            box(activity_top, 1, activity_h, max(10, w - 2), "Activity")
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
                log("Refreshed.")
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
                put(h - 1, 2, "Cleanup project devkit artifacts? [y/N]")
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
                    subprocess.call([sys.executable, str(root / "pi-odoo-devkit.py"), "doctor", str(project_dir)])
                    input("\nPress Enter to return to devkit UI...")
                finally:
                    curses.reset_prog_mode()
                    stdscr.refresh()

    curses.wrapper(_app)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Pi Odoo Devkit CLI."""


@cli.command("ui")
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
def ui_cmd(project_repo_path: Path | None) -> None:
    """Launch interactive devkit TUI."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise click.ClickException("TUI requires an interactive terminal.")

    root = devkit_root()
    project_dir = _project_path_for_ui(root, project_repo_path)
    run_tui(root, project_dir)


@cli.command()
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
@click.option("--add-local-exclude", is_flag=True, help="Add '.pi/' to <project>/.git/info/exclude (local-only).")
@click.option("--with-browser-tools", is_flag=True, help="Install browser-tools npm dependencies")
@click.option("--without-browser-tools", is_flag=True, help="Skip browser-tools npm dependencies")
@click.option("--without-envrc", is_flag=True, help="Skip recommended .envrc/.venv bootstrap")
@click.option("--yes", is_flag=True, help="Non-interactive mode (use sensible defaults)")
def wizard(
    project_repo_path: Path | None,
    add_local_exclude: bool,
    with_browser_tools: bool,
    without_browser_tools: bool,
    without_envrc: bool,
    yes: bool,
) -> None:
    """Run setup/reconfiguration wizard."""
    if with_browser_tools and without_browser_tools:
        raise click.ClickException("Cannot combine --with-browser-tools and --without-browser-tools")

    root = devkit_root()
    interactive = sys.stdin.isatty() and not yes

    if project_repo_path is None:
        if not interactive:
            raise click.ClickException("PROJECT_REPO_PATH is required in non-interactive mode.")
        project_repo_path = prompt_project_repo_path(root)

    project_dir = project_repo_path.expanduser().resolve()
    check_project_repo(project_dir)

    if interactive:
        click.echo("Welcome to the Odoo Devkit setup wizard 👋")
        click.echo("This setup will create a project command at .pi/devkit.")
        click.echo("No changes are written until final confirmation.")
        click.echo()

    click.echo("[preflight]")
    for row in preflight_checks():
        click.echo(row)
    click.echo()

    missing_required = [tool for tool in ("python3", "docker") if not command_exists(tool)]
    if missing_required:
        raise click.ClickException(f"Missing required tools: {', '.join(missing_required)}")

    all_skills = discover_skills(root)
    manifest = load_skill_manifest(root)
    availability: dict[str, tuple[bool, str]] = {}
    for s in all_skills:
        availability[s.name] = evaluate_skill_requirements(s.name, project_dir, manifest)

    shared_skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
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

    # Keep behavior deterministic:
    # - if odoo-ui-check is enabled, browser-tools deps are installed
    # - if odoo-ui-check is not enabled, browser-tools deps are not installed
    if odoo_ui_enabled and without_browser_tools:
        raise click.ClickException("odoo-ui-check requires browser-tools dependencies; remove --without-browser-tools.")
    if (not odoo_ui_enabled) and with_browser_tools:
        raise click.ClickException("--with-browser-tools is only valid when odoo-ui-check is enabled.")

    enable_browser = odoo_ui_enabled

    enable_envrc = False if without_envrc else (click.confirm("Set up recommended local environment (direnv + .venv)?", default=True) if interactive else True)
    enable_local_exclude = add_local_exclude or (click.confirm("Hide local .pi files from git status on this machine?", default=True) if interactive else False)
    migrate_tools = True

    if interactive:
        click.echo("\n[summary]")
        click.echo(f"  Project\n    {project_dir}")

        click.echo("\n  Skills to enable")
        if selected_skills:
            for name in sorted(selected_skills):
                click.echo(f"    • {name}")
        else:
            click.echo("    (none)")

        click.echo("\n  Project command")
        click.echo("    • Creates .pi/devkit (symlink to this devkit CLI)")

        click.echo("\n  Options")
        click.echo(f"    Setup env (.envrc/.venv):     {'yes' if enable_envrc else 'no'}")
        browser_note = "yes (required by odoo-ui-check)" if enable_browser else "no (odoo-ui-check not enabled)"
        click.echo(f"    Install browser-tools deps:   {browser_note}")
        click.echo(f"    Add local git exclude (.pi/): {'yes' if enable_local_exclude else 'no'}")
        click.echo("    Legacy .pi/tools handling:    automatic")

        if not click.confirm("\nApply these changes now?", default=True):
            click.echo("Cancelled. No changes were applied.")
            return

    (project_dir / ".pi" / "skills").mkdir(parents=True, exist_ok=True)

    skill_map = {
        s.name: s.path
        for s in all_skills
        if s.name in selected_skills and availability.get(s.name, (True, ""))[0]
    }
    skill_msgs = sync_symlink_set(shared_skills_dir, skill_map)

    # Main convenience entrypoint in project
    local_devkit_link = project_dir / ".pi" / "devkit"
    target = root / "pi-odoo-devkit.py"
    if local_devkit_link.exists() or local_devkit_link.is_symlink():
        if local_devkit_link.is_symlink() and local_devkit_link.resolve() == target.resolve():
            pass
        else:
            local_devkit_link.unlink()
            local_devkit_link.symlink_to(target)
    else:
        local_devkit_link.symlink_to(target)

    hygiene_msgs = sanitize_project_skills(project_dir, set(skill_map.keys()))
    tools_msgs = migrate_legacy_tools(project_dir) if migrate_tools else []
    notes_path = write_local_agent_notes(project_dir)

    click.echo(f"Installed devkit setup into: {project_dir}")
    click.echo("\n[skills]")
    click.echo(f"- Enabled: {', '.join(sorted(skill_map.keys())) if skill_map else '(none)'}")
    for msg in skill_msgs:
        click.echo(f"- {msg}")

    click.echo("\n[project links]")
    click.echo(f"- Convenience link: {local_devkit_link} -> {local_devkit_link.resolve()}")

    if hygiene_msgs:
        click.echo("\n[pi skill hygiene]")
        for msg in hygiene_msgs:
            click.echo(f"- {msg}")

    if tools_msgs:
        click.echo("\n[pi tools migration]")
        for msg in tools_msgs:
            click.echo(f"- {msg}")

    if enable_local_exclude:
        click.echo(ensure_local_exclude(project_dir))

    if enable_envrc:
        click.echo("\n[env setup]")
        for msg in ensure_envrc(root):
            click.echo(f"- {msg}")

    if enable_browser:
        click.echo("\n[browser-tools]")
        for msg in install_browser_tools(root):
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

    skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
    if not skills_dir.exists():
        results.append(("skills:shared-devkit", "FAIL", f"missing: {skills_dir}"))
    else:
        entries = list(skills_dir.iterdir()) if skills_dir.is_dir() else []
        results.append(("skills:shared-devkit", "PASS", f"{len(entries)} entries"))

    local_devkit = project_dir / ".pi" / "devkit"
    if local_devkit.is_symlink():
        results.append(("link:.pi/devkit", "PASS", f"ok -> {local_devkit.resolve()}"))
    elif local_devkit.exists():
        results.append(("link:.pi/devkit", "WARN", "exists but not a symlink"))
    else:
        results.append(("link:.pi/devkit", "WARN", "missing"))

    legacy_tools = project_dir / ".pi" / "tools"
    if legacy_tools.exists():
        results.append(("pi:legacy-tools", "WARN", "project has .pi/tools (pi will warn; migrate/remove it)"))
    else:
        results.append(("pi:legacy-tools", "PASS", "no legacy .pi/tools directory"))

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
        for name in ["README.md", "_template", "_disabled-by-devkit"]:
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
def doctor(project_repo_path: Path | None) -> None:
    """Run health and hygiene checks."""
    root = devkit_root()

    interactive = sys.stdin.isatty()
    if project_repo_path is None:
        if not interactive:
            raise click.ClickException("PROJECT_REPO_PATH is required in non-interactive mode.")
        project_repo_path = prompt_project_repo_path(root)

    project_dir = project_repo_path.expanduser().resolve()
    check_project_repo(project_dir)

    results, fail_count, warn_count = run_doctor_checks(root, project_dir)

    click.echo(f"Odoo devkit doctor report\n- devkit: {root}\n- project: {project_dir}\n")

    for name, status, message in results:
        icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
        click.echo(f"{icon} [{status}] {name}: {message}")

    click.echo("\nSummary:")
    click.echo(f"- FAIL: {fail_count}")
    click.echo(f"- WARN: {warn_count}")

    recs = doctor_recommendations(results, project_dir)
    if recs:
        click.echo("\nWhat to do next:")
        for i, rec in enumerate(recs, start=1):
            click.echo(f"{i}. {rec}")

    if fail_count:
        raise SystemExit(1)


@cli.command(name="cleanup")
@click.argument("project_repo_path", required=False, type=click.Path(path_type=Path))
@click.option("--remove-local-exclude", is_flag=True, help="Remove '.pi/' from <project>/.git/info/exclude if present")
@click.option("--all", "remove_all", is_flag=True, help="Remove all devkit-managed links/files without interactive prompts")
@click.option("--yes", is_flag=True, help="Non-interactive mode (accept defaults)")
def cleanup_cmd(project_repo_path: Path | None, remove_local_exclude: bool, remove_all: bool, yes: bool) -> None:
    """Run cleanup/uninstall flow."""
    root = devkit_root()
    interactive = sys.stdin.isatty() and not yes and not remove_all

    if project_repo_path is None:
        if not interactive:
            raise click.ClickException("PROJECT_REPO_PATH is required in non-interactive mode.")
        project_repo_path = prompt_project_repo_path(root)

    project_dir = project_repo_path.expanduser().resolve()
    check_project_repo(project_dir)

    skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
    local_devkit = project_dir / ".pi" / "devkit"
    notes = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"
    legacy_tools = project_dir / ".pi" / "tools"
    legacy_skill_backup = project_dir / ".pi" / "skills" / "_disabled-by-devkit"
    devkit_backups = project_dir / ".pi" / "_devkit-backups"
    legacy_tools_backup = project_dir / ".pi" / "_legacy-tools-disabled"

    remove_skills = True
    remove_devkit_link = True
    remove_notes = True
    remove_legacy_tools = True
    remove_devkit_backups = True

    if interactive:
        remove_skills = click.confirm("Remove installed devkit skills from project (.pi/skills/shared-devkit)?", default=True)
        remove_devkit_link = click.confirm("Remove project devkit entrypoint (.pi/devkit)?", default=True)
        remove_notes = click.confirm("Remove local devkit notes file (.pi/DEVKIT_AGENT_NOTES.md)?", default=True)
        remove_legacy_tools = click.confirm("Remove legacy .pi/tools directory if present?", default=True)
        remove_devkit_backups = click.confirm("Remove devkit backup archives (.pi/_devkit-backups, .pi/_legacy-tools-disabled, old .pi/skills/_disabled-by-devkit)?", default=True)
        if not remove_local_exclude:
            remove_local_exclude = click.confirm("Remove '.pi/' entry from local git exclude?", default=False)

    actions: list[str] = []

    if remove_skills and skills_dir.exists():
        if skills_dir.is_dir() and not skills_dir.is_symlink():
            shutil.rmtree(skills_dir)
            actions.append(f"REMOVED dir: {skills_dir}")
        else:
            skills_dir.unlink()
            actions.append(f"REMOVED: {skills_dir}")
    else:
        actions.append(f"SKIP: {skills_dir}")

    if remove_devkit_link and (local_devkit.exists() or local_devkit.is_symlink()):
        local_devkit.unlink()
        actions.append(f"REMOVED: {local_devkit}")
    else:
        actions.append(f"SKIP: {local_devkit}")

    if remove_notes and notes.exists():
        text = notes.read_text(encoding="utf-8")
        if "managed-by: devkit installer" in text:
            notes.unlink()
            actions.append(f"REMOVED: {notes}")
        else:
            actions.append(f"SKIP: notes file not managed by installer: {notes}")
    else:
        actions.append(f"SKIP: {notes}")

    if remove_legacy_tools and legacy_tools.exists():
        shutil.rmtree(legacy_tools)
        actions.append(f"REMOVED dir: {legacy_tools}")
    else:
        actions.append(f"SKIP: {legacy_tools}")

    if remove_devkit_backups:
        for p in [legacy_skill_backup, devkit_backups, legacy_tools_backup]:
            if p.exists():
                if p.is_dir() and not p.is_symlink():
                    shutil.rmtree(p)
                    actions.append(f"REMOVED dir: {p}")
                else:
                    p.unlink()
                    actions.append(f"REMOVED: {p}")
            else:
                actions.append(f"SKIP: {p}")

    if remove_local_exclude:
        actions.append(remove_local_exclude_entry(project_dir))

    click.echo(f"Uninstall summary for project repo: {project_dir}")
    visible = [line for line in actions if not line.startswith("SKIP:")]
    skipped = len(actions) - len(visible)

    if visible:
        for line in visible:
            click.echo(f"- {line}")
    else:
        click.echo("- Nothing to remove (project already clean).")

    if skipped:
        click.echo(f"- Skipped unchanged entries: {skipped}")


@cli.command("reset-project-path")
def reset_project_path() -> None:
    """Forget saved default Odoo project path (.envrc.local)."""
    root = devkit_root()
    envrc_local = _envrc_local_path(root)
    if envrc_local.exists():
        envrc_local.unlink()
        click.echo(f"Removed saved project path file: {envrc_local}")
    else:
        click.echo("No saved project path found.")


@cli.command()
def components() -> None:
    """Show available/enabled skills from current project."""
    root = devkit_root()
    project = resolve_runtime_project_root()
    skills = discover_skills(root)
    manifest = load_skill_manifest(root)

    enabled_dir = project / ".pi" / "skills" / "shared-devkit"
    enabled = {p.name for p in enabled_dir.iterdir()} if enabled_dir.exists() and enabled_dir.is_dir() else set()

    click.echo("\n🧰 Pi Odoo Devkit Components")
    click.echo(f"Project: {project}")
    click.echo(f"Devkit:  {root}\n")

    click.echo("Skills:")
    if not skills:
        click.echo("  (none)")

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
def enable_skill(name: str) -> None:
    """Enable one skill in current project."""
    root = devkit_root()
    project = resolve_runtime_project_root()
    src = root / "skills" / name
    marker = src / "SKILL.md"
    dst = project / ".pi" / "skills" / "shared-devkit" / name

    if not marker.exists():
        raise click.ClickException(f"Skill not found in devkit: {name}")

    manifest = load_skill_manifest(root)
    ok, reason = evaluate_skill_requirements(name, project, manifest)
    if not ok:
        raise click.ClickException(f"Cannot enable skill '{name}' ({reason})")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.symlink_to(src)

    for msg in sanitize_project_skills(project, {name}):
        click.echo(f"- {msg}")
    click.echo(f"✅ Enabled skill: {name}")


@cli.command("disable-skill")
@click.argument("name")
def disable_skill(name: str) -> None:
    """Disable one skill in current project."""
    project = resolve_runtime_project_root()
    dst = project / ".pi" / "skills" / "shared-devkit" / name
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
        click.echo(f"✅ Disabled skill: {name}")
    else:
        click.echo(f"Skill already disabled: {name}")


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


if __name__ == "__main__":
    if len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            root = devkit_root()
            project_dir = _project_path_for_ui(root, None)
            run_tui(root, project_dir)
        except click.ClickException as e:
            click.echo(e.format_message(), err=True)
            raise SystemExit(1)
    else:
        cli()
