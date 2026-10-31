#!/usr/bin/env bash
# =============================================================================
# COHERENCE-HOOK-1 — lance la SUITE DE COHÉRENCE sur la base locale, ou le dit EN ROUGE.
# -----------------------------------------------------------------------------
# Point d'entrée UNIQUE partagé par le hook pre-push ET le banc de nuit : sonde la base applicative
# réelle (le run servi) ; si elle répond → joue `pytest -m coherence tests/coherence/` avec
# LABUSE_COHERENCE_REQUIRE_DB=1 (un skip silencieux devient alors un ÉCHEC) ; si elle ne répond pas →
# écrit un message ROUGE explicite (jamais un silence).
#
# Codes de sortie :   0 = tout vert · 1 = au moins un test de cohérence ROUGE · 2 = base injoignable
# Usage           :   scripts/ci/coherence_run.sh
# Env (optionnel) :   LABUSE_APP_DATABASE_URL / LABUSE_DATABASE_URL (sinon lus dans .env)
# =============================================================================
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$ROOT" ] && ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 2
RED=$'\033[31m'; GRN=$'\033[32m'; NC=$'\033[0m'

# --- Python porteur de pytest : .venv du worktree, puis .venv du dépôt principal, puis PATH. ---
common="$(git rev-parse --git-common-dir 2>/dev/null)"
PY=""
for cand in "$ROOT/.venv/bin/python" "${common%/.git}/.venv/bin/python" "$common/../.venv/bin/python" python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import pytest" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then printf '%s✗ aucun Python avec pytest — cohérence non jouable.%s\n' "$RED" "$NC"; exit 2; fi

# --- URL de la base APPLICATIVE réelle (run servi) : env, sinon .env, sinon défaut local. ---
APP_URL="${LABUSE_APP_DATABASE_URL:-${LABUSE_DATABASE_URL:-}}"
if [ -z "$APP_URL" ] && [ -f "$ROOT/.env" ]; then
  APP_URL="$(grep -E '^LABUSE_APP_DATABASE_URL=' "$ROOT/.env" | tail -1 | cut -d= -f2-)"
  [ -z "$APP_URL" ] && APP_URL="$(grep -E '^LABUSE_DATABASE_URL=' "$ROOT/.env" | tail -1 | cut -d= -f2-)"
fi
APP_URL="${APP_URL:-postgresql+psycopg://openclaw@localhost:5432/labuse}"
export LABUSE_APP_DATABASE_URL="$APP_URL"

# --- Sonde LECTURE SEULE : la base répond-elle ET porte-t-elle un run résiduel servi ? ---
probe="$("$PY" - "$APP_URL" <<'PYEOF' 2>/dev/null
import sys
from sqlalchemy import create_engine, text
url = sys.argv[1]
try:
    eng = create_engine(url, future=True)
    with eng.connect() as c:
        c.execute(text("SET default_transaction_read_only = on"))
        seq = c.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    print(f"OK:{seq}" if seq else "NORUN:")
except Exception as exc:  # noqa: BLE001
    print("DOWN:" + type(exc).__name__)
PYEOF
)"

case "$probe" in
  OK:*)
    printf '%s✓ base locale OK (run résiduel servi = %s) — suite de cohérence lancée…%s\n' \
           "$GRN" "${probe#OK:}" "$NC"
    LABUSE_COHERENCE_REQUIRE_DB=1 PYTHONPATH=src "$PY" -m pytest tests/coherence/ -m coherence \
      -q -p no:cacheprovider -o addopts=""
    rc=$?
    if [ "$rc" -eq 0 ]; then printf '%s✓ cohérence : aucun écart (1 €/1 m²) sur les témoins.%s\n' "$GRN" "$NC"; exit 0
    else printf '%s✗ COHÉRENCE ROUGE — un fait est servi à plusieurs valeurs (détail ci-dessus).%s\n' "$RED" "$NC"; exit 1; fi
    ;;
  *)
    reason="${probe#*:}"; [ "${probe%%:*}" = "NORUN" ] && reason="aucun run résiduel servi"
    printf '%s✗ BASE LOCALE INJOIGNABLE — suite de cohérence NON EXÉCUTÉE (%s).%s\n' "$RED" "${reason:-injoignable}" "$NC"
    printf '  (démarre PostgreSQL + la base « labuse » pour jouer le filet de cohérence au push.)\n'
    exit 2
    ;;
esac
