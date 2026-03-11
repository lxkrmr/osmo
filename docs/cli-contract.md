# osmo CLI Contract v1

Status: active
Version: v1

This document defines the stable automation contract for `osmo`.

## Scope

Automation contract commands:
- `wizard`
- `doctor`
- `cleanup`
- `components`
- `enable-skill`
- `disable-skill`
- `reset-project-path`

Non-contract human-ops commands (no JSON/describe guarantee):
- `ui`, `new-skill`, `up`, `db`, `shell`, `test`, `lint`

## Global contract rules

For automation commands:
- `--output json` is supported.
- `--describe` is supported.
- mutating commands support `--dry-run`.

Mutating commands:
- `wizard`, `cleanup`, `enable-skill`, `disable-skill`, `reset-project-path`

## JSON envelope

Success:
```json
{
  "ok": true,
  "command": "<command>",
  "data": { ... }
}
```

Error:
```json
{
  "ok": false,
  "command": "<command>",
  "error": {
    "code": "<error_code>",
    "message": "<human readable>"
  }
}
```

## Exit code contract

- `0`: success
- `1`: runtime failure / failing checks (e.g. `doctor` with FAIL checks)
- `2`: validation/usage error (`validation_error`, `missing_dependencies`, ...)

## Command-specific stable fields

### `components --output json`

Per entry in `data.skills[]`:
- `name`
- `enabled`
- `available`
- `reason`
- `reason_code`
- `requirement_failures[]`
- `description`

### `doctor --output json`

Top-level stable fields in `data`:
- `checks[]` (legacy)
- `checks_structured[]`
- `recommendations[]` (legacy)
- `recommendations_structured[]`

`checks_structured[]` fields:
- `name`
- `check_code`
- `category`
- `resource`
- `status`
- `severity`
- `message`

`recommendations_structured[]` fields:
- `code`
- `severity`
- `message`
- `next_command`

## Contract index command

Use this for machine discovery:
```bash
osmo help --output json
```

Relevant fields:
- `contract_version` (`v1`)
- `contract_spec` (`docs/cli-contract.md`)
- `automation_commands`
- `non_contract_commands`
- `details[].contract_scope`
- `details[].params[]`

`details[].params[]` stable fields:
- `kind` (`option` | `argument`)
- `name`
- `required`
- `opts` (for `option`)
- `nargs` (for `argument`)

## Contract evolution / migration policy

- Additive changes (new optional JSON fields) are allowed in `v1`.
- Renaming/removing existing stable fields requires a new contract version.
- For a breaking change:
  1. introduce `v2` in docs,
  2. update `help --output json` to expose new `contract_version`,
  3. keep compatibility fields for at least one release when practical,
  4. update golden snapshots and contract tests in the same change.
