#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def resolve_project_dir(positional: str) -> Path:
    return Path(positional).expanduser()


def remove_local_exclude(project_dir: Path) -> str:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Uninstall Odoo devkit links from a project repo safely.")
    parser.add_argument("project_repo_path", help="Path to Odoo project repo")
    parser.add_argument(
        "--remove-local-exclude",
        action="store_true",
        help="Also remove '.pi/' from <project>/.git/info/exclude if present",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all devkit-managed links/files without interactive prompts",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive mode (accept defaults)",
    )
    args = parser.parse_args()

    project_dir = resolve_project_dir(args.project_repo_path).resolve()
    if not project_dir.exists():
        print(f"Project repo path does not exist: {project_dir}")
        return 1

    if not (project_dir / "docker-compose.yml").exists():
        print(f"Not an Odoo project repo (missing docker-compose.yml): {project_dir}")
        return 1

    interactive = sys.stdin.isatty() and not args.yes and not args.all

    actions: list[str] = []

    skills_dir = project_dir / ".pi" / "skills" / "shared-devkit"
    tools_dir = project_dir / ".pi" / "tools" / "shared-devkit"
    devkit_link = project_dir / ".pi" / "tools" / "devkit"
    notes = project_dir / ".pi" / "DEVKIT_AGENT_NOTES.md"

    remove_skills = True
    remove_commands = True
    remove_notes = True

    if interactive:
        remove_skills = prompt_yes_no("Remove installed devkit skills from project (.pi/skills/shared-devkit)?", True)
        remove_commands = prompt_yes_no("Remove installed devkit commands from project (.pi/tools/shared-devkit)?", True)
        remove_notes = prompt_yes_no("Remove local devkit notes file (.pi/DEVKIT_AGENT_NOTES.md)?", True)

    if remove_skills and skills_dir.exists():
        if skills_dir.is_dir() and not skills_dir.is_symlink():
            shutil.rmtree(skills_dir)
            actions.append(f"REMOVED dir: {skills_dir}")
        else:
            skills_dir.unlink()
            actions.append(f"REMOVED: {skills_dir}")
    else:
        actions.append(f"SKIP: {skills_dir}")

    if remove_commands and tools_dir.exists():
        if tools_dir.is_dir() and not tools_dir.is_symlink():
            shutil.rmtree(tools_dir)
            actions.append(f"REMOVED dir: {tools_dir}")
        else:
            tools_dir.unlink()
            actions.append(f"REMOVED: {tools_dir}")
    else:
        actions.append(f"SKIP: {tools_dir}")

    if remove_commands and devkit_link.is_symlink():
        devkit_link.unlink()
        actions.append(f"REMOVED: {devkit_link}")
    else:
        actions.append(f"SKIP: {devkit_link}")

    if remove_notes and notes.exists():
        text = notes.read_text(encoding="utf-8")
        if "managed-by: devkit installer" in text:
            notes.unlink()
            actions.append(f"REMOVED: {notes}")
        else:
            actions.append(f"SKIP: notes file not managed by installer (left untouched): {notes}")
    else:
        actions.append(f"SKIP: {notes}")

    remove_exclude = args.remove_local_exclude
    if interactive and not args.remove_local_exclude:
        remove_exclude = prompt_yes_no("Remove '.pi/' entry from local git exclude?", False)

    if remove_exclude:
        actions.append(remove_local_exclude(project_dir))

    print(f"Uninstall summary for project repo: {project_dir}")
    for line in actions:
        print(f"- {line}")

    print("\nNote: existing local .pi skills/tools you created manually remain untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
