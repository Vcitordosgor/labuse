#!/usr/bin/env bash
# =============================================================================
# SOLIDITE-1 (Lot 3.4) — MÉNAGE DISQUE : runs morts + reliquats (DRY-RUN PAR DÉFAUT).
# -----------------------------------------------------------------------------
# Regagne de la place SANS JAMAIS toucher au run servi, au précédent, ni à un secours.
# Par défaut : n'exécute RIEN — il LISTE ce qu'il ferait et la place regagnée estimée.
# `--execute` déclenche réellement (DELETE + VACUUM FULL, TRUNCATE, DROP SCHEMA, rm) —
# à faire UNIQUEMENT après revue de Vic (cf. docs/audit-2026-10/solidite-1/INVENTAIRE-DISQUE.md).
#
# Garde dure : garder au moins SERVI + PRÉCÉDENT + SECOURS. La liste est EXPLICITE (KEEP_RUNS),
# jamais devinée. Le servi est lu de served_run.txt ; le reste est paramétrable.
#
# Usage :
#   deploy/scripts/menage_disque.sh                 # dry-run (par défaut)
#   deploy/scripts/menage_disque.sh --execute       # exécute (après accord Vic)
#   KEEP_RUNS="q_v18,q_v16,q_v11_m137" ... --execute
#   --drop-schema  : DROP SCHEMA sauvegarde_20261006 (10 Mo, reliquat) — en plus
#   --rm-vieux-app : rm -rf /opt/labuse/app-avant-0610 (4,2 Go, ancienne version) — en plus
# =============================================================================
set -euo pipefail

EXECUTE=0; DROP_SCHEMA=0; RM_VIEUX_APP=0
for a in "$@"; do case "$a" in
  --execute) EXECUTE=1 ;; --drop-schema) DROP_SCHEMA=1 ;; --rm-vieux-app) RM_VIEUX_APP=1 ;;
  *) echo "option inconnue : $a" >&2; exit 2 ;;
esac; done

DB="${LABUSE_DB_NAME:-labuse}"
PSQL=(sudo -u postgres psql -At -d "$DB")
SERVED_FILE="${LABUSE_SERVED_FILE:-/opt/labuse/app/config/served_run.txt}"
SERVI="$(grep -vE '^\s*#' "$SERVED_FILE" 2>/dev/null | grep -vE '^\s*$' | head -1 || echo q_v18)"
# SERVI + PRÉCÉDENT + SECOURS (modifiable) — pour les tables à run_label/run_id de scoring.
KEEP_RUNS="${KEEP_RUNS:-${SERVI},q_v16,q_v11_m137}"
# pour la cascade, les labels diffèrent (…_sources) — garder le servi + les keepers DISQUE-VPS-1.
KEEP_CASCADE="${KEEP_CASCADE:-${SERVI}_sources,q_v13_sources1,q_v11_m137}"

mode() { [ "$EXECUTE" = 1 ] && echo "EXÉCUTE" || echo "DRY-RUN"; }
echo "── MÉNAGE DISQUE ($(mode)) — servi=$SERVI ──"
echo "   garder (scoring) : $KEEP_RUNS"
echo "   garder (cascade) : $KEEP_CASCADE"
echo

_in_list() { local IFS=,; printf "'%s'," $1 | sed "s/,$//"; }   # "a,b" -> 'a','b'

# ── 1. runs morts dans les tables de scoring (run_id) et de score (run_label) ──
nettoyer_runs() {
  local table="$1" col="$2" keep="$3"
  local liste; liste="$(_in_list "$keep")"
  echo "▸ $table ($col) — runs présents :"
  "${PSQL[@]}" -c "SELECT '    '||$col||'  '||count(*) FROM $table GROUP BY $col ORDER BY count(*) DESC" || true
  local morts; morts="$("${PSQL[@]}" -c "SELECT count(*) FROM $table WHERE $col NOT IN ($liste)" 2>/dev/null || echo 0)"
  echo "    → lignes hors keep : ${morts:-0}"
  if [ "${morts:-0}" != "0" ]; then
    if [ "$EXECUTE" = 1 ]; then
      echo "    DELETE…"; "${PSQL[@]}" -c "DELETE FROM $table WHERE $col NOT IN ($liste)"
      echo "    VACUUM FULL $table…"; "${PSQL[@]}" -c "VACUUM (FULL) $table"
    else
      echo "    (dry-run : DELETE FROM $table WHERE $col NOT IN ($liste) ; puis VACUUM FULL)"
    fi
  fi
  echo
}
nettoyer_runs parcel_p_score_v2 run_id "$KEEP_RUNS"
nettoyer_runs score_labuse run_label "$KEEP_RUNS"
nettoyer_runs dryrun_cascade_results run_label "$KEEP_CASCADE"

# ── 2. datasets d'entraînement (NON servis) — TRUNCATE. JAMAIS p_model_ext_dataset (lu par l'API). ──
echo "▸ datasets d'entraînement (TRUNCATE p_model_dataset / _v2 / _v2bis ; _ext_ GARDÉ) :"
for t in p_model_dataset p_model_dataset_v2 p_model_dataset_v2bis; do
  n="$("${PSQL[@]}" -c "SELECT count(*) FROM $t" 2>/dev/null || echo '?')"
  echo "    $t : $n lignes"
  if [ "$EXECUTE" = 1 ]; then "${PSQL[@]}" -c "TRUNCATE $t"; else echo "    (dry-run : TRUNCATE $t)"; fi
done
echo

# ── 3. schéma reliquat (optionnel) ──
if [ "$DROP_SCHEMA" = 1 ]; then
  echo "▸ DROP SCHEMA sauvegarde_20261006 CASCADE"
  [ "$EXECUTE" = 1 ] && "${PSQL[@]}" -c "DROP SCHEMA IF EXISTS sauvegarde_20261006 CASCADE" || echo "    (dry-run)"
  echo
fi

# ── 4. ancienne version de l'app (optionnel) ──
if [ "$RM_VIEUX_APP" = 1 ]; then
  echo "▸ rm -rf /opt/labuse/app-avant-0610"
  [ "$EXECUTE" = 1 ] && sudo rm -rf /opt/labuse/app-avant-0610 || echo "    (dry-run)"
  echo
fi

echo "── fin ($(mode)) ──"
[ "$EXECUTE" = 1 ] || echo "Rien touché. Relancer avec --execute (après accord) pour appliquer."
