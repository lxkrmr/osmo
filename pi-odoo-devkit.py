#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_script(devkit_root: Path, rel_script: str, args: list[str]) -> int:
    script = devkit_root / rel_script
    cmd = [sys.executable, str(script), *args]
    return subprocess.call(cmd)


def run_dev_command(devkit_root: Path, args: list[str]) -> int:
    dev_cmd = devkit_root / "commands" / "dev"
    cmd = [str(dev_cmd), *args]
    return subprocess.call(cmd)


def main() -> int:
    devkit_root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="pi-odoo-devkit",
        description="Pi Odoo Devkit toolbox (wizard, doctor, components, skill/command management).",
    )

    sub = parser.add_subparsers(dest="command")

    p_wizard = sub.add_parser("wizard", help="Run setup/reconfiguration wizard")
    p_wizard.add_argument("args", nargs=argparse.REMAINDER)

    p_doctor = sub.add_parser("doctor", help="Run health and hygiene checks")
    p_doctor.add_argument("args", nargs=argparse.REMAINDER)

    p_cleanup = sub.add_parser("cleanup", help="Run cleanup/uninstall flow")
    p_cleanup.add_argument("args", nargs=argparse.REMAINDER)

    p_components = sub.add_parser("components", help="Show available/enabled skills and commands")
    p_components.add_argument("args", nargs=argparse.REMAINDER)

    # Common developer actions (forward to commands/dev)
    p_up = sub.add_parser("up", help="Start docker services")
    p_up.add_argument("args", nargs=argparse.REMAINDER)

    p_db = sub.add_parser("db", help="Open psql using project DB config")
    p_db.add_argument("args", nargs=argparse.REMAINDER)

    p_shell = sub.add_parser("shell", help="Open Odoo shell (--no-http)")
    p_shell.add_argument("args", nargs=argparse.REMAINDER)

    p_test = sub.add_parser("test", help="Run project test wrapper")
    p_test.add_argument("args", nargs=argparse.REMAINDER)

    p_lint = sub.add_parser("lint", help="Run pre-commit wrapper")
    p_lint.add_argument("args", nargs=argparse.REMAINDER)

    p_enable_skill = sub.add_parser("enable-skill", help="Enable one skill")
    p_enable_skill.add_argument("name")

    p_disable_skill = sub.add_parser("disable-skill", help="Disable one skill")
    p_disable_skill.add_argument("name")

    p_enable_cmd = sub.add_parser("enable-command", help="Enable one command")
    p_enable_cmd.add_argument("name")

    p_disable_cmd = sub.add_parser("disable-command", help="Disable one command")
    p_disable_cmd.add_argument("name")

    p_new_skill = sub.add_parser("new-skill", help="Scaffold a new skill")
    p_new_skill.add_argument("name")

    args = parser.parse_args()

    if args.command in {None, "help"}:
        parser.print_help()
        return 0

    if args.command == "wizard":
        extra = args.args if hasattr(args, "args") else []
        return run_script(devkit_root, "bootstrap/install.py", extra)

    if args.command == "doctor":
        return run_script(devkit_root, "bootstrap/doctor.py", args.args)

    if args.command == "cleanup":
        extra = args.args if hasattr(args, "args") else []
        return run_script(devkit_root, "bootstrap/uninstall.py", extra)

    if args.command == "components":
        return run_dev_command(devkit_root, ["components", *args.args])

    if args.command in {"up", "db", "shell", "test", "lint"}:
        return run_dev_command(devkit_root, [args.command, *args.args])

    if args.command == "enable-skill":
        return run_dev_command(devkit_root, ["enable-skill", args.name])

    if args.command == "disable-skill":
        return run_dev_command(devkit_root, ["disable-skill", args.name])

    if args.command == "enable-command":
        return run_dev_command(devkit_root, ["enable-command", args.name])

    if args.command == "disable-command":
        return run_dev_command(devkit_root, ["disable-command", args.name])

    if args.command == "new-skill":
        return run_dev_command(devkit_root, ["new-skill", args.name])

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
