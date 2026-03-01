#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillMeta:
    name: str
    path: Path
    description: str


@dataclass
class CommandMeta:
    name: str
    path: Path
    description: str


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def resolve_project_dir(devkit_dir: Path, positional: str | None) -> Path | None:
    if positional:
        return Path(positional).expanduser()

    env_val = os.environ.get("ODOO_REPO_PATH")
    if env_val:
        return Path(env_val).expanduser()

    sibling = devkit_dir.parent / "erp"
    if sibling.exists():
        return sibling

    cwd = Path.cwd()
    if (cwd / "docker-compose.yml").exists():
        return cwd

    return None


def prompt_for_project_dir() -> Path:
    while True:
        raw = input("Enter path to your Odoo project repo (contains docker-compose.yml): ").strip()
        if not raw:
            print("Please enter a path.")
            continue
        p = Path(raw).expanduser().resolve()
        if not p.exists():
            print(f"Path does not exist: {p}")
            continue
        if not (p / "docker-compose.yml").exists():
            print(f"Not an Odoo project repo (missing docker-compose.yml): {p}")
            continue
        return p


def preflight_checks() -> list[str]:
    rows = []
    for tool, required in [("python3", True), ("docker", True), ("node", False), ("npm", False), ("direnv", False)]:
        ok = command_exists(tool)
        status = "OK" if ok else ("MISSING (required)" if required else "MISSING (optional)")
        rows.append(f"- {tool}: {status}")
    return rows


def load_skill_manifest(devkit_dir: Path) -> dict:
    manifest_path = devkit_dir / "skills" / "manifest.json"
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


def parse_skill_meta(skill_dir: Path) -> SkillMeta | None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None

    description = "No description provided."
    name = skill_dir.name
    try:
        text = skill_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            i = 1
            while i < len(lines) and lines[i].strip() != "---":
                line = lines[i]
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip() or name
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip() or description
                i += 1
    except Exception:
        pass

    return SkillMeta(name=name, path=skill_dir, description=description)


def discover_skills(devkit_dir: Path) -> list[SkillMeta]:
    skills_root = devkit_dir / "skills"
    if not skills_root.exists():
        return []
    skills: list[SkillMeta] = []
    for d in sorted(skills_root.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        meta = parse_skill_meta(d)
        if meta:
            skills.append(meta)
    return skills


def discover_commands(devkit_dir: Path) -> list[CommandMeta]:
    cmds_root = devkit_dir / "commands"
    if not cmds_root.exists():
        return []
    metas: list[CommandMeta] = []
    description_map = {
        "dev": "Main helper command (up/db/shell/test/lint/doctor/components/enable/disable/new-skill).",
    }
    for p in sorted(cmds_root.iterdir(), key=lambda x: x.name):
        if not p.is_file() or p.name == "README.md":
            continue
        if not os.access(p, os.X_OK):
            continue
        metas.append(CommandMeta(name=p.name, path=p, description=description_map.get(p.name, "Helper command.")))
    return metas


def ensure_container_dir(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def sync_symlink_set(target_dir: Path, selected: dict[str, Path]) -> list[str]:
    messages: list[str] = []
    ensure_container_dir(target_dir)

    # Remove stale links/files in target dir
    for existing in target_dir.iterdir():
        if existing.name not in selected:
            if existing.is_symlink() or existing.is_file():
                existing.unlink()
                messages.append(f"Removed: {existing}")
            elif existing.is_dir():
                shutil.rmtree(existing)
                messages.append(f"Removed dir: {existing}")

    # Ensure selected links
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


def ensure_envrc(devkit_dir: Path) -> list[str]:
    messages: list[str] = []
    envrc = devkit_dir / ".envrc"
    gitignore = devkit_dir / ".gitignore"
    venv_dir = devkit_dir / ".venv"

    envrc_content = """# Odoo Devkit recommended environment (direnv + venv)
export ODOO_DEVKIT_ROOT=\"$(pwd)\"

if [ -f .envrc.local ]; then
  source .envrc.local
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
export PATH=\"$ODOO_DEVKIT_ROOT/commands:$PATH\"
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


def ensure_project_env_local(devkit_dir: Path, project_dir: Path) -> str:
    env_local = devkit_dir / ".envrc.local"
    content = f'export ODOO_REPO_PATH="{project_dir}"\n'
    env_local.write_text(content, encoding="utf-8")
    return f"Wrote {env_local} (ODOO_REPO_PATH={project_dir})"


def install_browser_tools(devkit_dir: Path) -> list[str]:
    messages: list[str] = []
    bt_dir = devkit_dir / "skills" / "browser-tools" / "browser-tools"

    if not bt_dir.exists():
        return [f"Browser tools directory missing: {bt_dir}"]

    missing = [tool for tool in ("node", "npm") if not command_exists(tool)]
    if missing:
        return [f"Browser tools setup skipped: missing dependencies: {', '.join(missing)}"]

    messages.append(f"Running npm install in {bt_dir} ...")
    subprocess.run(["npm", "install"], cwd=bt_dir, check=True)
    messages.append("Browser tools npm dependencies installed.")

    chromium_path = Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
    if not chromium_path.exists():
        messages.append(
            "Note: Chromium app not found at /Applications/Chromium.app/Contents/MacOS/Chromium. "
            "Update browser-start.js or install Chromium there."
        )

    return messages


def write_local_agent_notes(project_dir: Path, devkit_dir: Path) -> Path:
    notes_path = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"
    content = f"""# Odoo Devkit Local Notes

<!-- managed-by: devkit installer -->

This file is generated by `bootstrap/install.py`.

## Shared Devkit Links

- Skills: `.pi/skills/shared-devkit`
- Commands: `.pi/tools/shared-devkit`
- Dev command: `.pi/tools/devkit`

## Quick Commands

```bash
./.pi/tools/devkit --help
./.pi/tools/devkit up
./.pi/tools/devkit db
./.pi/tools/devkit shell
```

## Browser Skill Dependency

If using browser-based skills (`browser-tools`, `odoo-ui-check`, `odoo-ui-regression-check`), ensure browser-tools deps are installed:

```bash
{devkit_dir}/pi-odoo-devkit.sh wizard {project_dir} --with-browser-tools --yes
```

## Notes

- This file is local support material; it does not modify `AGENTS.md`/`CLAUDE.md` automatically.
- If you want to reference it, add a short line in your preferred agent doc.
"""
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")
    return notes_path


def print_agent_doc_guidance(project_dir: Path, notes_path: Path) -> None:
    print("\n[agent docs]")
    print(f"- Wrote local include notes: {notes_path}")

    existing = [p for p in (project_dir / "AGENTS.md", project_dir / "CLAUDE.md") if p.exists()]
    if existing:
        print("- Existing agent docs detected:")
        for p in existing:
            print(f"  - {p}")
        print("- No automatic edits were applied (non-invasive by design).")
    else:
        print("- No AGENTS.md/CLAUDE.md found at repo root. That's okay.")

    print("- Optional copy/paste snippet:")
    print("""
## Local Devkit Notes (optional)
For local helper workflows, see `.pi/DEVKIT_AGENT_NOTES.md`.
""".strip())


def prompt_yes_no(question: str, default_yes: bool = True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    while True:
        ans = input(f"{question} [{default}] ").strip().lower()
        if not ans:
            return default_yes
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def current_enabled_names(target_dir: Path) -> set[str]:
    if not target_dir.exists():
        return set()
    names: set[str] = set()
    for p in target_dir.iterdir():
        if p.is_symlink() or p.exists():
            names.add(p.name)
    return names


def default_selection(
    all_skills: list[SkillMeta],
    all_commands: list[CommandMeta],
    available_skill_names: set[str],
) -> tuple[set[str], set[str]]:
    skill_names = {s.name for s in all_skills}
    cmd_names = {c.name for c in all_commands}

    recommended = {
        "local-db",
        "odoo-shell-debug",
        "odoo-addon-lifecycle",
        "odoo-translate",
        "odoo-ui-check",
        "odoo-ui-regression-check",
        "skill-authoring",
    }

    selected_skills = (recommended & skill_names) & available_skill_names
    selected_commands = ({"dev"} & cmd_names) or cmd_names
    return selected_skills, selected_commands


def interactive_select(
    all_skills: list[SkillMeta],
    all_commands: list[CommandMeta],
    current_skills: set[str],
    current_commands: set[str],
    availability: dict[str, tuple[bool, str]],
) -> tuple[set[str], set[str]]:
    selected_skills, selected_commands = default_selection(
        all_skills,
        all_commands,
        {name for name, (ok, _) in availability.items() if ok},
    )

    # keep current as default if already configured (but only for available skills)
    if current_skills:
        selected_skills = {n for n in current_skills if availability.get(n, (False, ""))[0]}
    if current_commands:
        selected_commands = set(current_commands)

    print("\n[skills selection]")
    for s in all_skills:
        ok, reason = availability.get(s.name, (True, ""))
        if not ok:
            selected_skills.discard(s.name)
            print(f"  ⛔ {s.name} unavailable — {reason}")
            continue

        default = s.name in selected_skills
        enabled = prompt_yes_no(f"Use skill '{s.name}'? — {s.description}", default_yes=default)
        if enabled:
            selected_skills.add(s.name)
        else:
            selected_skills.discard(s.name)

    print("\n[commands selection]")
    for c in all_commands:
        default = c.name in selected_commands or c.name == "dev"
        enabled = prompt_yes_no(f"Use command '{c.name}'? — {c.description}", default_yes=default)
        if enabled:
            selected_commands.add(c.name)
        else:
            selected_commands.discard(c.name)

    return selected_skills, selected_commands


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install Odoo devkit links and optional batteries-included setup."
    )
    parser.add_argument("project_repo_path", nargs="?", help="Path to Odoo project repo")
    parser.add_argument(
        "--add-local-exclude",
        action="store_true",
        help="Add '.pi/' to <project>/.git/info/exclude (local-only). In interactive mode, you'll be asked if omitted.",
    )
    parser.add_argument(
        "--with-browser-tools",
        action="store_true",
        help="Install browser-tools npm dependencies",
    )
    parser.add_argument(
        "--without-browser-tools",
        action="store_true",
        help="Skip browser-tools npm dependencies",
    )
    parser.add_argument(
        "--without-envrc",
        action="store_true",
        help="Skip recommended .envrc/.venv bootstrap",
    )
    parser.add_argument(
        "--set-project-env",
        action="store_true",
        help="Write ODOO_REPO_PATH to devkit .envrc.local",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive mode (use sensible defaults)",
    )

    args = parser.parse_args()

    if args.with_browser_tools and args.without_browser_tools:
        print("Cannot combine --with-browser-tools and --without-browser-tools", file=sys.stderr)
        return 2

    interactive = sys.stdin.isatty() and not args.yes

    if interactive:
        print("Welcome to the Odoo Devkit setup wizard 👋")
        print("We'll go step by step:")
        print("  1) Check dependencies")
        print("  2) Confirm your Odoo project path")
        print("  3) Choose skills (with short descriptions)")
        print("  4) Choose commands")
        print("  5) Optional local environment setup (direnv + .venv)")
        print("  6) Optional browser-tools dependency setup")
        print("  7) Optional local git exclude")
        print("  8) Final summary + confirmation")
        print("No changes are written until the final confirmation step.")
        print()

    print("[preflight]")
    for row in preflight_checks():
        print(row)
    print()

    missing_required = [tool for tool in ("python3", "docker") if not command_exists(tool)]
    if missing_required:
        print(f"Missing required tools: {', '.join(missing_required)}", file=sys.stderr)
        print("Please install required tools first, then re-run setup.", file=sys.stderr)
        return 1

    devkit_dir = Path(__file__).resolve().parent.parent
    project_dir_raw = resolve_project_dir(devkit_dir, args.project_repo_path)
    if not project_dir_raw and interactive:
        print("I couldn't auto-detect your Odoo project path.")
        project_dir_raw = prompt_for_project_dir()

    if not project_dir_raw:
        print("Could not resolve Odoo project repo path.", file=sys.stderr)
        parser.print_help()
        return 1

    project_dir = project_dir_raw.expanduser().resolve()
    if not project_dir.exists():
        print(f"Project repo path does not exist: {project_dir}", file=sys.stderr)
        return 1
    if not (project_dir / "docker-compose.yml").exists():
        print(f"Not an Odoo project repo (missing docker-compose.yml): {project_dir}", file=sys.stderr)
        return 1

    all_skills = discover_skills(devkit_dir)
    all_commands = discover_commands(devkit_dir)

    manifest = load_skill_manifest(devkit_dir)
    skill_availability: dict[str, tuple[bool, str]] = {}
    for s in all_skills:
        skill_availability[s.name] = evaluate_skill_requirements(s.name, project_dir, manifest)

    shared_skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
    shared_cmds_dir = project_dir / ".pi" / "tools" / "shared-devkit"
    current_skills = current_enabled_names(shared_skills_dir)
    current_commands = current_enabled_names(shared_cmds_dir)

    if interactive:
        if current_skills or current_commands:
            print(f"Current setup detected: {len(current_skills)} skills, {len(current_commands)} commands enabled.")
            print("You can adjust these selections now.")
        else:
            print("No existing devkit setup detected yet. We'll configure from scratch.")
        print()

    if interactive:
        selected_skills, selected_commands = interactive_select(
            all_skills,
            all_commands,
            current_skills,
            current_commands,
            skill_availability,
        )
    else:
        selected_skills, selected_commands = default_selection(
            all_skills,
            all_commands,
            {name for name, (ok, _) in skill_availability.items() if ok},
        )

    if args.with_browser_tools:
        enable_browser_tools = True
    elif args.without_browser_tools:
        enable_browser_tools = False
    elif interactive:
        enable_browser_tools = prompt_yes_no("Install browser-tools dependencies now? (needed for browser-based skills)", default_yes=True)
    else:
        enable_browser_tools = "browser-tools" in selected_skills

    if args.without_envrc:
        enable_envrc = False
    elif interactive:
        enable_envrc = prompt_yes_no("Set up recommended local environment (direnv + .venv)?", default_yes=True)
    else:
        enable_envrc = True

    if args.add_local_exclude:
        enable_local_exclude = True
    elif interactive:
        enable_local_exclude = prompt_yes_no("Hide local .pi files from git status on this machine?", default_yes=True)
    else:
        enable_local_exclude = False

    if args.set_project_env:
        set_project_env = True
    elif interactive:
        set_project_env = prompt_yes_no("Remember this project path for future runs? (.envrc.local)", default_yes=True)
    else:
        set_project_env = False

    if interactive:
        print("\n[summary]")
        print(f"- Project: {project_dir}")
        print(f"- Skills to enable ({len(selected_skills)}): {', '.join(sorted(selected_skills)) if selected_skills else '(none)'}")
        unavailable = {n: r for n, (ok, r) in skill_availability.items() if not ok}
        if unavailable:
            print("- Skills currently unavailable:")
            for n, r in sorted(unavailable.items()):
                print(f"    - {n}: {r}")
        print(f"- Commands to enable ({len(selected_commands)}): {', '.join(sorted(selected_commands)) if selected_commands else '(none)'}")
        print(f"- Setup env (.envrc/.venv): {'yes' if enable_envrc else 'no'}")
        print(f"- Install browser-tools deps: {'yes' if enable_browser_tools else 'no'}")
        print(f"- Add local git exclude (.pi/): {'yes' if enable_local_exclude else 'no'}")
        print(f"- Store project path in .envrc.local: {'yes' if set_project_env else 'no'}")

        if not prompt_yes_no("Apply these changes now?", default_yes=True):
            print("Cancelled. No changes were applied.")
            return 0

    # Ensure .pi containers
    (project_dir / ".pi" / "skills").mkdir(parents=True, exist_ok=True)
    (project_dir / ".pi" / "tools").mkdir(parents=True, exist_ok=True)

    # Map selections to source paths
    skill_map = {
        s.name: s.path
        for s in all_skills
        if s.name in selected_skills and skill_availability.get(s.name, (True, ""))[0]
    }
    cmd_map = {c.name: c.path for c in all_commands if c.name in selected_commands}

    skill_msgs = sync_symlink_set(shared_skills_dir, skill_map)
    cmd_msgs = sync_symlink_set(shared_cmds_dir, cmd_map)

    # Main convenience entrypoint
    devkit_cmd_link = project_dir / ".pi" / "tools" / "devkit"
    main_target = devkit_dir / "pi-odoo-devkit.sh"
    if devkit_cmd_link.exists() or devkit_cmd_link.is_symlink():
        if devkit_cmd_link.is_symlink() and devkit_cmd_link.resolve() == main_target.resolve():
            pass
        else:
            devkit_cmd_link.unlink()
            devkit_cmd_link.symlink_to(main_target)
    else:
        devkit_cmd_link.symlink_to(main_target)

    notes_path = write_local_agent_notes(project_dir, devkit_dir)

    print(f"Installed devkit setup into: {project_dir}")
    print("\n[skills]")
    print(f"- Enabled: {', '.join(sorted(skill_map.keys())) if skill_map else '(none)'}")
    for m in skill_msgs:
        print(f"- {m}")

    print("\n[commands]")
    print(f"- Enabled: {', '.join(sorted(cmd_map.keys())) if cmd_map else '(none)'}")
    for m in cmd_msgs:
        print(f"- {m}")
    if devkit_cmd_link.is_symlink():
        print(f"- Convenience link: {devkit_cmd_link} -> {devkit_cmd_link.resolve()}")

    if enable_local_exclude:
        print(ensure_local_exclude(project_dir))
    else:
        print("Tip: rerun with --add-local-exclude to hide .pi from git status (local-only).")

    if set_project_env:
        print(ensure_project_env_local(devkit_dir, project_dir))

    # Recommended env setup
    if enable_envrc:
        print("\n[env setup]")
        for m in ensure_envrc(devkit_dir):
            print(f"- {m}")
    else:
        print("\n[env setup] skipped (--without-envrc)")

    # Optional browser-tools batteries
    if enable_browser_tools:
        print("\n[browser-tools]")
        try:
            for m in install_browser_tools(devkit_dir):
                print(f"- {m}")
        except subprocess.CalledProcessError as e:
            print(f"- Browser tools setup failed with exit code {e.returncode}", file=sys.stderr)
            return e.returncode
    else:
        print("\n[browser-tools] skipped")

    print_agent_doc_guidance(project_dir, notes_path)

    # Core dependency summary
    print("\n[dependency check]")
    for tool, required in [
        ("python3", True),
        ("docker", True),
        ("node", False),
        ("npm", False),
        ("direnv", False),
    ]:
        ok = command_exists(tool)
        status = "OK" if ok else ("MISSING (required)" if required else "MISSING (optional)")
        print(f"- {tool}: {status}")

    print("\nNext steps:")
    step = 1
    if enable_envrc and command_exists("direnv"):
        print(f"{step}) cd {devkit_dir} && direnv allow")
        step += 1
    print(f"{step}) {project_dir}/.pi/tools/devkit --help")
    step += 1
    print(f"{step}) {project_dir}/.pi/tools/devkit doctor")
    step += 1
    print(f"{step}) If using browser skill: run browser-start.js via the skill instructions")
    step += 1
    print(f"{step}) For cleanup later: {devkit_dir}/pi-odoo-devkit.sh cleanup {project_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
