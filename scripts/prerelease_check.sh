#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEEL="$(ls -t "$ROOT"/dist/cohzen-*-py3-none-any.whl 2>/dev/null | head -1)"
if [ -z "$WHEEL" ]; then
  echo "Error: No wheel found in $ROOT/dist. Run 'uv build' first."
  exit 1
fi
echo "Testing wheel: $WHEEL"

UV_BIN="${UV_BIN:-/Users/aarora/.local/bin/uv}"

for PY_SPEC in 3.10 3.11 3.12 3.13; do
  PY_BIN=""
  if command -v "python$PY_SPEC" >/dev/null 2>&1; then
    PY_BIN="python$PY_SPEC"
  elif command -v "$UV_BIN" >/dev/null 2>&1 && "$UV_BIN" python find "$PY_SPEC" >/dev/null 2>&1; then
    PY_BIN="$("$UV_BIN" python find "$PY_SPEC")"
  fi

  if [ -z "$PY_BIN" ]; then
    echo "=== Skipping Python $PY_SPEC (not installed) ==="
    continue
  fi

  echo "=== Running stranger check on Python $PY_SPEC ($PY_BIN) ==="
  TMP="$(mktemp -d)"
  VENV_DIR="$TMP/venv"
  "$PY_BIN" -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"

  pip install -q --upgrade pip
  pip install -q "${WHEEL}[runtime]"

  # 1. CLI help matches expectations
  cz --help >/dev/null

  # 2. Static scan
  cz scan "$ROOT/examples/langgraph-basic" >/dev/null

  # 3. Always-on project capture test
  mkdir -p "$TMP/proj"
  cp -R "$ROOT/examples/langgraph-basic/." "$TMP/proj/"
  (
    cd "$TMP/proj"
    echo y | cz init
    python app.py
    python - <<'EOF'
import sqlite3
conn = sqlite3.connect(".cohzen/executions.db")
count = conn.execute("select count(*) from executions").fetchone()[0]
assert count > 0, f"Expected captured runs, got {count}"
print(f"Captured {count} run(s) successfully in SQLite.")
EOF
    cz runs >/dev/null
  )

  # 4. Scenario A: Test cz deinit cleanly removes hook and .cohzen
  mkdir -p "$TMP/deinit_test"
  cp -R "$ROOT/examples/langgraph-basic/." "$TMP/deinit_test/"
  (
    cd "$TMP/deinit_test"
    echo y | cz init
    cz deinit --yes
    [ ! -d ".cohzen" ] || { echo "FAIL: .cohzen directory was not removed by deinit"; exit 1; }
  )

  # 5. Scenario B: Uninstall WITHOUT cz deinit -> Python must still start silently (stdout + stderr)
  pip uninstall -y -q cohzen
  OUT="$(python -c "print('ok')" 2>&1)"
  [ "$OUT" = "ok" ] || { echo "FAIL: noise after uninstall on $PY_SPEC: $OUT"; exit 1; }

  deactivate
  rm -rf "$TMP"
  echo "=== Python $PY_SPEC passed ==="
done

echo "All stranger checks passed!"
