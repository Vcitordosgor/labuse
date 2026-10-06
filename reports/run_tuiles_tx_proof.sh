#!/usr/bin/env bash
# TUILES-TX-1 — lance la preuve locale (venv principal + src du worktree + base labuse).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$HOME/Desktop/labuse/.venv/bin/python"
export PYTHONPATH="$PWD/src"
export LABUSE_DATABASE_URL="${LABUSE_DATABASE_URL:-postgresql+psycopg://labuse@localhost:5432/labuse}"
export PROOF_PG_DSN="${PROOF_PG_DSN:-dbname=labuse}"
export PROOF_PORT="${PROOF_PORT:-8791}"
exec "$PY" reports/tuiles_tx_proof.py
