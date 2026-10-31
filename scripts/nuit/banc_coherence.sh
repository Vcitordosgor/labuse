#!/usr/bin/env bash
# =============================================================================
# COHERENCE-HOOK-1 — BANC DE NUIT : la suite COMPLÈTE avec base, chaque soir à 22 h 30 HEURE RÉUNION.
# -----------------------------------------------------------------------------
# Rejoue TOUTE la suite de tests qui touche la base (db + reel + local + coherence, hors réseau) sur la
# base APPLICATIVE réelle (run servi), avec LABUSE_COHERENCE_REQUIRE_DB=1 (une base muette devient un
# ÉCHEC, jamais un skip). Écrit un RAPPORT DATÉ dans ~/labuse-nuit/ et, SI UN SEUL TEST EST ROUGE, lève
# une NOTIFICATION macOS (osascript). But du mandat : la dérive ne peut plus passer des jours inaperçue.
#
# Ancrage HEURE RÉUNION (robuste au changement d'heure de Paris, doctrine RADAR-COUVERTURE-1) : le job
# launchd amorce ce script à 19:30 ET 20:30 Paris (qui encadrent 22:30 Réunion été comme hiver) ; le
# script ne s'exécute QUE dans la fenêtre [22:15, 23:45] Réunion, et au plus UNE fois par jour (verrou).
#
# Usage :   banc_coherence.sh [REPO_PATH]      # REPO_PATH défaut = $LABUSE_REPO ou le dépôt courant
#           banc_coherence.sh --force [REPO]   # ignore la fenêtre + le verrou (run manuel / recette)
# =============================================================================
set -uo pipefail

FORCE=0; [ "${1:-}" = "--force" ] && { FORCE=1; shift; }
REPO="${1:-${LABUSE_REPO:-}}"
if [ -z "$REPO" ]; then REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"; fi
if [ -z "$REPO" ] || [ ! -d "$REPO/tests/coherence" ]; then
  echo "✗ dépôt LA BUSE introuvable (REPO='$REPO') — passer le chemin en argument ou poser LABUSE_REPO." >&2
  exit 2
fi
cd "$REPO" || exit 2

NUIT="$HOME/labuse-nuit"
mkdir -p "$NUIT"
JOUR="$(TZ='Indian/Reunion' date +%Y-%m-%d)"
HM="$(TZ='Indian/Reunion' date +%H%M)"
RAPPORT="$NUIT/coherence-$JOUR.log"
VERROU="$NUIT/.ran-$JOUR"

# --- Fenêtre Réunion + verrou quotidien (sautés avec --force) ---
if [ "$FORCE" -ne 1 ]; then
  if [ "$HM" \< "2215" ] || [ "$HM" \> "2345" ]; then
    exit 0   # hors fenêtre 22:30 Réunion : amorçage launchd de l'autre créneau — on ne fait rien
  fi
  if [ -f "$VERROU" ]; then exit 0; fi   # déjà joué aujourd'hui
fi
: > "$VERROU"

# --- Python porteur de pytest ---
common="$(git rev-parse --git-common-dir 2>/dev/null)"
PY=""
for cand in "$REPO/.venv/bin/python" "${common%/.git}/.venv/bin/python" "$common/../.venv/bin/python" python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import pytest" >/dev/null 2>&1; then PY="$cand"; break; fi
done

notifier() {  # titre, message (best-effort : osascript absent = silencieux)
  command -v osascript >/dev/null 2>&1 && \
    osascript -e "display notification \"$2\" with title \"$1\" sound name \"Basso\"" >/dev/null 2>&1 || true
}

# --- Base applicative : URL + sonde (muette = ROUGE, jamais silence) ---
APP_URL="${LABUSE_APP_DATABASE_URL:-${LABUSE_DATABASE_URL:-}}"
if [ -z "$APP_URL" ] && [ -f "$REPO/.env" ]; then
  APP_URL="$(grep -E '^LABUSE_APP_DATABASE_URL=' "$REPO/.env" | tail -1 | cut -d= -f2-)"
  [ -z "$APP_URL" ] && APP_URL="$(grep -E '^LABUSE_DATABASE_URL=' "$REPO/.env" | tail -1 | cut -d= -f2-)"
fi
APP_URL="${APP_URL:-postgresql+psycopg://openclaw@localhost:5432/labuse}"
export LABUSE_APP_DATABASE_URL="$APP_URL"
export LABUSE_COHERENCE_REQUIRE_DB=1

{
  echo "===== BANC DE NUIT COHÉRENCE — $JOUR $(TZ='Indian/Reunion' date +%H:%M) (heure Réunion) ====="
  echo "dépôt    : $REPO ($(git rev-parse --short HEAD 2>/dev/null))"
  echo "base     : $APP_URL"
} > "$RAPPORT"

if [ -z "$PY" ]; then
  echo "✗ aucun Python avec pytest — suite NON jouée." >> "$RAPPORT"
  notifier "LA BUSE — banc de nuit ROUGE" "pytest introuvable : suite non jouée (voir $RAPPORT)"
  exit 2
fi

seq="$("$PY" - "$APP_URL" <<'PYEOF' 2>>"$RAPPORT"
import sys
from sqlalchemy import create_engine, text
try:
    with create_engine(sys.argv[1], future=True).connect() as c:
        print(c.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar() or "")
except Exception as exc:  # noqa: BLE001
    print("DOWN")
PYEOF
)"
echo "run servi: $seq" >> "$RAPPORT"
if [ "$seq" = "DOWN" ] || [ -z "$seq" ]; then
  echo "✗ BASE INJOIGNABLE OU SANS RUN SERVI — suite de nuit NON exécutée (ROUGE, jamais silence)." >> "$RAPPORT"
  notifier "LA BUSE — banc de nuit ROUGE" "base locale injoignable : suite non jouée (voir $RAPPORT)"
  exit 2
fi

# Sélection pytest : COMPLÈTE par défaut (db + reel + local + coherence, hors réseau). Surchargée par
# LABUSE_NUIT_SELECTION pour une recette ciblée (ex. un seul test) — jamais en exploitation.
SEL="${LABUSE_NUIT_SELECTION:--m not network}"
echo "----- pytest $SEL -----" >> "$RAPPORT"
# shellcheck disable=SC2086
PYTHONPATH=src "$PY" -m pytest $SEL -q -p no:cacheprovider -o addopts="" -rfE >> "$RAPPORT" 2>&1
rc=$?

resume="$(grep -E '^(=+ .*(passed|failed|error).*=+|[0-9]+ (passed|failed))' "$RAPPORT" | tail -1)"
echo "===== FIN (code $rc) — $resume =====" >> "$RAPPORT"

if [ "$rc" -eq 0 ]; then
  echo "✓ banc de nuit VERT — aucun test rouge." >> "$RAPPORT"
  exit 0
else
  notifier "LA BUSE — banc de nuit ROUGE" "${resume:-au moins un test a échoué} — $RAPPORT"
  exit 1
fi
