#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
CLI="$ROOT/osmo.py"

if [ ! -x "$PY" ]; then
  echo "Missing $PY" >&2
  echo "Run: ./scripts/bootstrap.sh" >&2
  exit 1
fi

OUT="$(mktemp)"
TMP_PROJECT=""
cleanup() {
  rm -f "$OUT"
  if [ -n "$TMP_PROJECT" ] && [ -d "$TMP_PROJECT" ]; then
    rm -rf "$TMP_PROJECT"
  fi
}
trap cleanup EXIT

assert_json_error() {
  local cmd="$1"
  local expected_code="$2"
  set +e
  eval "$cmd" >"$OUT" 2>/dev/null
  local rc=$?
  set -e
  if [ "$rc" -ne 2 ]; then
    echo "Expected exit code 2, got $rc for: $cmd" >&2
    exit 1
  fi
  "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["ok"] is False; assert d["error"]["code"]==sys.argv[2]' "$OUT" "$expected_code"
}

echo "[contract] validation errors"
assert_json_error "\"$PY\" \"$CLI\" wizard --yes --output json" "validation_error"
assert_json_error "\"$PY\" \"$CLI\" cleanup --yes --output json" "validation_error"


echo "[contract] dry-run must not mutate"
TMP_PROJECT="$(mktemp -d)"
cat >"$TMP_PROJECT/docker-compose.yml" <<'YAML'
services: {}
YAML
mkdir -p "$TMP_PROJECT/.pi/skills/shared-osmo"
mkdir -p "$TMP_PROJECT/.pi"
printf "managed-by: osmo installer\n" >"$TMP_PROJECT/.pi/DEVKIT_AGENT_NOTES.md"

"$PY" "$CLI" cleanup "$TMP_PROJECT" --dry-run --output json >"$OUT"
"$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["ok"]; assert d["data"]["dry_run"] is True; assert any("PLAN:" in a for a in d["data"]["actions"])' "$OUT"

if [ ! -d "$TMP_PROJECT/.pi/skills/shared-osmo" ]; then
  echo "cleanup --dry-run removed skills dir" >&2
  exit 1
fi
if [ ! -f "$TMP_PROJECT/.pi/DEVKIT_AGENT_NOTES.md" ]; then
  echo "cleanup --dry-run removed notes file" >&2
  exit 1
fi


echo "[contract] components reason codes"
(
  cd "$TMP_PROJECT"
  "$PY" "$CLI" components --output json >"$OUT"
)
"$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["ok"]; skills=d["data"]["skills"]; assert isinstance(skills,list) and skills; required={"name","enabled","available","reason","reason_code","requirement_failures","description"}; assert required.issubset(skills[0].keys())' "$OUT"

echo "[contract] doctor structured recommendations"
TMP_DOCTOR="$(mktemp -d)"
cat >"$TMP_DOCTOR/docker-compose.yml" <<'YAML'
services: {}
YAML
set +e
"$PY" "$CLI" doctor "$TMP_DOCTOR" --output json >"$OUT"
DOCTOR_RC=$?
set -e
rm -rf "$TMP_DOCTOR"
if [ "$DOCTOR_RC" -ne 1 ]; then
  echo "Expected doctor exit code 1 on failing checks, got $DOCTOR_RC" >&2
  exit 1
fi
"$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["ok"]; rs=d["data"]["recommendations_structured"]; assert isinstance(rs,list) and rs; req={"code","severity","message","next_command"}; assert req.issubset(rs[0].keys()); assert any(r["code"] for r in rs); cs=d["data"]["checks_structured"]; assert isinstance(cs,list) and cs; req2={"name","check_code","category","resource","status","severity","message"}; assert req2.issubset(cs[0].keys()); assert any(c["check_code"]=="shared_skills_installed" for c in cs)' "$OUT"

echo "[contract] done"
