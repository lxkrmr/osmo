# CLI Contract Matrix

Date: 2026-03-11
Status: active

Reference spec: `docs/cli-contract.md` (v1)

## Scope
Automation-relevant commands should expose deterministic behavior:
- `--output json`
- `--describe`
- `--dry-run` for mutating commands

## Matrix

| Command | Mutates state | `--output json` | `--describe` | `--dry-run` |
|---|---:|---:|---:|---:|
| `wizard` | yes | yes | yes | yes |
| `doctor` | no | yes | yes | n/a |
| `cleanup` | yes | yes | yes | yes |
| `components` | no | yes | yes | n/a |
| `enable-skill` | yes | yes | yes | yes |
| `disable-skill` | yes | yes | yes | yes |
| `reset-project-path` | yes | yes | yes | yes |

## Non-contract commands (explicit)
Outside automation contract by design:
- `ui`, `new-skill`, `up`, `db`, `shell`, `test`, `lint`

## Notes
- `wizard --dry-run` returns a plan and does not write files.
- `reset-project-path --dry-run` reports whether `.envrc.local` would be removed.
- `components --output json` exposes stable machine fields: `reason_code` and `requirement_failures[]`.
- `doctor --output json` exposes `checks_structured[]` with `check_code`, `category`, `resource`, `status`, `severity`, `message`.
- `doctor --output json` exposes `recommendations_structured[]` with `code`, `severity`, `message`, `next_command` (while keeping legacy `recommendations[]`).
- Command metadata is exposed via `--describe` and reflected by `osmo help --output json` (`contract_version`, `contract_spec`, `automation_commands`, `non_contract_commands`, `details[].contract_scope`, `details[].params[]`).
