#!/usr/bin/env bash
# PROPRETE-1 — mesures rejouables d'une commande (lecture seule).
# Usage: bash scripts/proprete/run_all.sh   (ou `make proprete`)
# Les outils tournent en éphémère (uvx / npx) — RIEN n'est installé durablement
# ni committé. Sorties brutes dans scripts/proprete/raw/.
set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
RAW="$ROOT/scripts/proprete/raw"
mkdir -p "$RAW"
VENV="${LABUSE_VENV:-$HOME/Desktop/labuse/.venv}"
PY="$VENV/bin/python"
PGURL="${LABUSE_AUDIT_PGURL:-postgresql://openclaw@localhost:5432/labuse}"

say(){ echo -e "\n\033[1m== $* ==\033[0m"; }

say "0. Inventaire"
python3 scripts/proprete/inventory.py | tee "$RAW/inventory.txt"

say "1. Dépôt — secrets (gitleaks)"
gitleaks detect --no-banner --redact -r "$RAW/gitleaks.json" 2>&1 | tee "$RAW/gitleaks.txt" || true
say "1. Dépôt — artefacts & branches"
git ls-files | grep -vE 'node_modules/' | xargs -I{} stat -f "%z {}" {} 2>/dev/null | awk '$1>1048576' | sort -rn > "$RAW/git_big_files.txt"
git branch -r --merged origin/main | grep -vE 'HEAD|origin/main' > "$RAW/git_merged_branches.txt"

say "2. Python — ruff / format / vulture / radon / bandit / deptry / pip-audit"
uvx ruff@latest check src/labuse scripts --select E,F,W,I,B,UP,SIM,C4,PL --statistics 2>&1 | tee "$RAW/py_ruff.txt" || true
uvx ruff@latest format --check src/labuse scripts 2>&1 | tee "$RAW/py_format.txt" || true
vulture src/labuse scripts --min-confidence 80 2>&1 | tee "$RAW/py_vulture.txt" || true
uvx radon cc src/labuse scripts -s -a 2>&1 | tee "$RAW/py_radon.txt" || true
uvx bandit -ll -r src/labuse -f txt 2>&1 | tee "$RAW/py_bandit.txt" || true
uvx deptry . 2>&1 | tee "$RAW/py_deptry.txt" || true
uvx pip-audit 2>&1 | tee "$RAW/py_pipaudit.txt" || true
find src/labuse scripts -name '*.py' -exec wc -l {} + | sort -rn | awk '$1>800' > "$RAW/py_big_files.txt"

say "3. TypeScript — tsc / knip / madge / npm audit / build"
( cd frontend && npx tsc --noEmit 2>&1 | tee "$RAW/ts_tsc.txt" || true
  npx knip --no-exit-code 2>&1 | tee "$RAW/ts_knip.txt" || true
  npx madge --circular --extensions ts,tsx src 2>&1 | tee "$RAW/ts_madge.txt" || true
  npm audit 2>&1 | tee "$RAW/ts_npmaudit.txt" || true )

say "4. Tests — pytest coverage (cœur) / vitest"
( cd "$ROOT" && PYTHONPATH=src timeout 900 "$PY" -m pytest tests --cov=src/labuse \
    --cov-report=term-missing:skip-covered -p no:cacheprovider -q 2>&1 | tee "$RAW/tests_cov.txt" || true )

say "5. Base — tailles / dryrun / index inutilisés / réglages"
psql "$PGURL" -P pager=off -f scripts/proprete/db_mesures.sql 2>&1 | tee "$RAW/db_mesures.txt" || true

echo -e "\nTerminé. Sorties brutes : $RAW"
