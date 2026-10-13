#!/usr/bin/env bash
# =============================================================================
# SOLIDITE-1 (Lot 3.4) — MÉNAGE DISQUE : runs morts + reliquats (DRY-RUN PAR DÉFAUT).
# -----------------------------------------------------------------------------
# Regagne de la place SANS JAMAIS toucher au run servi, au précédent, ni à un secours.
# Par défaut : n'exécute RIEN — il LISTE ce qu'il ferait, AVEC LES TAILLES et la place regagnée estimée.
# `--execute` déclenche réellement — à faire UNIQUEMENT après revue de Vic.
#
# ORDRE (important sur disque plein) : on LIBÈRE D'ABORD sans espace temporaire (TRUNCATE, rm, DROP)
# PUIS on compacte (DELETE + VACUUM FULL, qui a besoin de place pour réécrire la table).
#
# Garde dure : garder au moins SERVI + PRÉCÉDENT + SECOURS. Liste EXPLICITE (KEEP_RUNS), jamais devinée.
#
# Usage :
#   deploy/scripts/menage_disque.sh                 # dry-run (par défaut) — liste + tailles
#   deploy/scripts/menage_disque.sh --execute       # exécute (après accord Vic)
#   KEEP_RUNS="q_v18,q_v16,q_v11_m137" ... --execute
#   --rm-vieux-app : rm -rf /opt/labuse/app-avant-0610 (ancienne version) — en plus
#   --drop-schema  : DROP SCHEMA sauvegarde_20261006 (reliquat) — en plus
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
SERVI="$(grep -vE '^[[:space:]]*#' "$SERVED_FILE" 2>/dev/null | grep -vE '^[[:space:]]*$' | head -1 || echo q_v18)"
KEEP_RUNS="${KEEP_RUNS:-${SERVI},q_v16,q_v11_m137}"
KEEP_CASCADE="${KEEP_CASCADE:-${SERVI}_sources,q_v13_sources1,q_v11_m137}"

mode() { [ "$EXECUTE" = 1 ] && echo "EXÉCUTE" || echo "DRY-RUN"; }
libre() { df -BG --output=avail /var/lib/postgresql 2>/dev/null | tail -1 | tr -dc '0-9'; }
echo "── MÉNAGE DISQUE ($(mode)) — servi=$SERVI · libre=$(libre) Go ──"
echo "   garder (scoring) : $KEEP_RUNS"
echo "   garder (cascade) : $KEEP_CASCADE"
echo
_in_list() { local IFS=,; printf "'%s'," $1 | sed "s/,$//"; }

# ── 1. LIBÉRER sans espace temporaire : datasets d'entraînement (TRUNCATE). JAMAIS p_model_ext_dataset. ──
echo "▸ datasets d'entraînement (TRUNCATE p_model_dataset / _v2 / _v2bis ; _ext_ GARDÉ) :"
for t in p_model_dataset p_model_dataset_v2 p_model_dataset_v2bis; do
  taille="$("${PSQL[@]}" -c "SELECT pg_size_pretty(pg_total_relation_size('$t'))" 2>/dev/null || echo '?')"
  n="$("${PSQL[@]}" -c "SELECT count(*) FROM $t" 2>/dev/null || echo '?')"
  echo "    $t : $n lignes · $taille  → TRUNCATE (gain ≈ $taille)"
  [ "$EXECUTE" = 1 ] && "${PSQL[@]}" -c "TRUNCATE $t" && echo "      tronqué."
done
echo

# ── 2. ancienne version de l'app (optionnel) ──
if [ "$RM_VIEUX_APP" = 1 ]; then
  t="$(sudo du -sh /opt/labuse/app-avant-0610 2>/dev/null | cut -f1)"
  echo "▸ rm -rf /opt/labuse/app-avant-0610  (gain ≈ ${t:-?})"
  [ "$EXECUTE" = 1 ] && sudo rm -rf /opt/labuse/app-avant-0610 && echo "    supprimé."
  echo
fi

# ── 3. schéma reliquat (optionnel) ──
if [ "$DROP_SCHEMA" = 1 ]; then
  echo "▸ DROP SCHEMA sauvegarde_20261006 CASCADE"
  [ "$EXECUTE" = 1 ] && "${PSQL[@]}" -c "DROP SCHEMA IF EXISTS sauvegarde_20261006 CASCADE" && echo "    supprimé."
  echo
fi

# ── 4. COMPACTER : runs morts (DELETE + VACUUM FULL) — a besoin de place, donc APRÈS les libérations ──
nettoyer_runs() {
  local table="$1" col="$2" keep="$3" liste total morts taille gain
  liste="$(_in_list "$keep")"
  taille="$("${PSQL[@]}" -c "SELECT pg_size_pretty(pg_total_relation_size('$table'))" 2>/dev/null || echo '?')"
  echo "▸ $table ($col · $taille) — runs présents :"
  "${PSQL[@]}" -c "SELECT '    '||$col||'  '||count(*) FROM $table GROUP BY $col ORDER BY count(*) DESC" || true
  total="$("${PSQL[@]}" -c "SELECT count(*) FROM $table" 2>/dev/null || echo 0)"
  morts="$("${PSQL[@]}" -c "SELECT count(*) FROM $table WHERE $col NOT IN ($liste)" 2>/dev/null || echo 0)"
  echo "    → lignes hors keep : ${morts:-0} / ${total:-0}"
  if [ "${morts:-0}" != "0" ] && [ "${total:-0}" != "0" ]; then
    gain="$("${PSQL[@]}" -c "SELECT pg_size_pretty((pg_total_relation_size('$table')::numeric * $morts / $total)::bigint)" 2>/dev/null || echo '?')"
    echo "    → gain estimé ≈ $gain"
    if [ "$EXECUTE" = 1 ]; then
      echo "    DELETE…"; "${PSQL[@]}" -c "DELETE FROM $table WHERE $col NOT IN ($liste)"
      echo "    VACUUM FULL $table (libre avant : $(libre) Go)…"; "${PSQL[@]}" -c "VACUUM (FULL) $table"
      echo "    fait (libre après : $(libre) Go)."
    else
      echo "    (dry-run : DELETE FROM $table WHERE $col NOT IN ($liste) ; puis VACUUM FULL)"
    fi
  fi
  echo
}
nettoyer_runs score_labuse run_label "$KEEP_RUNS"
nettoyer_runs parcel_p_score_v2 run_id "$KEEP_RUNS"
nettoyer_runs dryrun_cascade_results run_label "$KEEP_CASCADE"

echo "── fin ($(mode)) — libre=$(libre) Go ──"
[ "$EXECUTE" = 1 ] || echo "Rien touché. Relancer avec --execute (après accord) pour appliquer."
