#!/usr/bin/env bash
# =============================================================================
# LA BUSE — SYNC-RUN : le pont « le Mac CALCULE → le VPS SERT » (post-M7 · J5)
# -----------------------------------------------------------------------------
# Après une GRANDE PASSE locale (gel-cascade, retrain, nouveau run servi) :
#   1. dump ciblé des TABLES DE RUN + dérivés depuis la base LOCALE ;
#   2. transfert (rsync, checksum) ;
#   3. bascule sur le VPS (pg_restore --clean des tables ciblées) ;
#   4. build-mvt sur le VPS (tuiles au nouveau label) ;
#   5. VÉRIFICATION : comptages local vs VPS + GOLDEN DISTANT — le nouveau run
#      n'est « servi » qu'après ces deux verts.
#
# Usage :
#   deploy/scripts/sync-run.sh --dry-run                     # tout SAUF le restore (répétition)
#   deploy/scripts/sync-run.sh                               # bascule réelle (toutes les lignes)
#   deploy/scripts/sync-run.sh --run-label q_v15            # SCORING-6 lot F : dump FILTRÉ par run_label
#   deploy/scripts/sync-run.sh --dry-run --run-label q_v15  # répétition du dump filtré
#
# --run-label LABEL (SCORING-5-RETOUR §5.5) : ne transfère QUE les lignes de ce run pour les tables
#   versionnées (au lieu des ~80 M lignes tous labels de dryrun_cascade_results). Le restore MET À
#   JOUR ces seules lignes (DELETE WHERE label + COPY), les tables NON versionnées restent entières.
#
# Env requis pour l'étape 5 (golden) : LABUSE_QA_TARGET, LABUSE_QA_BASIC, LABUSE_QA_PASSWORD.
# ⚠ Ne JAMAIS lancer pendant le backup VPS de 3h (leçon M7 : verrous croisés).
# ⚠ Après une bascule de LABEL servi : maj LABUSE_SERVED_RUN + rebuild front (VITE_RUN_LABEL).
# =============================================================================
set -euo pipefail
HOST="${SYNC_HOST:-labuse-vps}"
DRY=0; RUN_LABEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --run-label) RUN_LABEL="${2:?--run-label attend un libellé}"; shift ;;
    *) echo "argument inconnu : $1" >&2; exit 2 ;;
  esac; shift
done
PG=${PG_BIN:-/Users/openclaw/miniforge3/envs/labusedb/bin}
LOCAL_DB="${LABUSE_LOCAL_DB:-postgresql://openclaw@localhost:5432/labuse}"
STAMP=$(date +%Y%m%d-%H%M%S)
DUMP=/tmp/labuse_runsync_${STAMP}.dump
COPYDIR=/tmp/labuse_runsync_${STAMP}_filtered

# Tables NON versionnées (dérivés recalculés) — toujours transférées entières.
TABLES=(parcel_evaluations pc_caducs defisc_fenetres score_e dvf_prix_sortie_neuf surface_d_events)
# Tables VERSIONNÉES → colonne de filtre par run (SCORING-6 : + score_labuse).
declare -a RUN_TABLES=(parcel_p_score_v2 p_score_v2_runs dryrun_cascade_results
                       dryrun_parcel_evaluations score_labuse score_labuse_runs)
declare -A RUN_COL=( [parcel_p_score_v2]=run_id [p_score_v2_runs]=run_id
                     [dryrun_cascade_results]=run_label [dryrun_parcel_evaluations]=run_label
                     [score_labuse]=run_label [score_labuse_runs]=run_label )

if [ -z "$RUN_LABEL" ]; then
  # ── chemin HISTORIQUE : tables entières (versionnées + dérivés) ──
  ALL=("${RUN_TABLES[@]}" "${TABLES[@]}")
  echo "── 1. dump ciblé (${#ALL[@]} tables, TOUS labels) depuis la base locale ──"
  ARGS=(); for t in "${ALL[@]}"; do ARGS+=(-t "$t"); done
  "$PG/pg_dump" -Fc "${ARGS[@]}" -d "$LOCAL_DB" -f "$DUMP"
  ls -lh "$DUMP" | awk '{print "   taille:", $5}'
  echo "── 2. comptages locaux (la référence) ──"
  : > /tmp/sync_counts_local.txt
  for t in "${ALL[@]}"; do
    printf "   %-28s %s\n" "$t" "$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t")"
  done | tee /tmp/sync_counts_local.txt
else
  # ── chemin FILTRÉ par run_label (lot F) : dérivés entiers + versionnées filtrées ──
  echo "── 1. dump FILTRÉ run_label='$RUN_LABEL' ──"
  mkdir -p "$COPYDIR"
  ARGS=(); for t in "${TABLES[@]}"; do ARGS+=(-t "$t"); done
  "$PG/pg_dump" -Fc "${ARGS[@]}" -d "$LOCAL_DB" -f "$DUMP"     # dérivés non versionnés = entiers
  : > /tmp/sync_counts_local.txt
  for t in "${RUN_TABLES[@]}"; do
    col="${RUN_COL[$t]}"
    "$PG/psql" "$LOCAL_DB" -tAc \
      "\copy (SELECT * FROM $t WHERE $col = '$RUN_LABEL') TO '$COPYDIR/$t.csv' CSV"
    n=$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t WHERE $col = '$RUN_LABEL'")
    printf "   %-28s %s (filtré)\n" "$t" "$n" | tee -a /tmp/sync_counts_local.txt
  done
  for t in "${TABLES[@]}"; do
    printf "   %-28s %s\n" "$t" "$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t")" \
      | tee -a /tmp/sync_counts_local.txt
  done
fi

echo "── 3. transfert ──"
rsync -a --partial "$DUMP" "$HOST":/tmp/labuse_runsync.dump
[ "$(md5 -q "$DUMP")" = "$(ssh -o BatchMode=yes "$HOST" md5sum /tmp/labuse_runsync.dump | cut -d' ' -f1)" ] \
  && echo "   checksum OK" || { echo "✗ checksum transfert"; exit 1; }
[ -n "$RUN_LABEL" ] && rsync -a --partial "$COPYDIR"/ "$HOST":/tmp/labuse_runsync_filtered/

if [ "$DRY" = 1 ]; then
  echo "── DRY-RUN : arrêt avant restore. Dump(s) sur le VPS. ──"
  echo "   Bascule réelle : relancer sans --dry-run."
  exit 0
fi

echo "── 4. bascule VPS (pg_restore des dérivés ; DELETE+COPY des versionnées si filtré) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u postgres pg_restore --clean --if-exists --no-owner --role=labuse \
  -d labuse -j 2 /tmp/labuse_runsync.dump 2>&1 | tail -2'
if [ -n "$RUN_LABEL" ]; then
  for t in "${RUN_TABLES[@]}"; do
    col="${RUN_COL[$t]}"
    ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -c \
      \"DELETE FROM $t WHERE $col = '$RUN_LABEL'\" -c \
      \"\\copy $t FROM '/tmp/labuse_runsync_filtered/$t.csv' CSV\""
  done
fi
ssh -o BatchMode=yes "$HOST" 'sudo -u postgres psql -d labuse -c ANALYZE'

echo "── 5a. comptages VPS vs local (le moindre écart = arrêt) ──"
ok=1
while read -r line; do
  t=$(echo "$line" | awk '{print $1}'); n=$(echo "$line" | awk '{print $2}')
  if [ -n "$RUN_LABEL" ] && [ -n "${RUN_COL[$t]:-}" ]; then
    nv=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -tAc \"SELECT count(*) FROM $t WHERE ${RUN_COL[$t]} = '$RUN_LABEL'\"")
  else
    nv=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -tAc 'SELECT count(*) FROM $t'")
  fi
  [ "$n" = "$nv" ] && printf "   ✓ %-28s %s\n" "$t" "$n" || { printf "   ✗ %-28s local=%s vps=%s\n" "$t" "$n" "$nv"; ok=0; }
done < /tmp/sync_counts_local.txt
[ "$ok" = 1 ] || { echo "✗ ÉCART DE COMPTAGE — diagnostic requis"; exit 1; }

echo "── 5b. tuiles (nouveau label) + golden distant ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "set -a; . /etc/labuse/labuse.env; set +a; cd /opt/labuse/app && /opt/labuse/venv/bin/labuse build-mvt 2>&1 | tail -1"'
python3 qa/golden_check.py --base-url "${LABUSE_QA_TARGET:?}" || { echo "✗ GOLDEN ROUGE — le run n'est PAS servi"; exit 1; }

echo "✓ SYNC-RUN terminé. Si le LABEL servi a changé : maj LABUSE_SERVED_RUN (/etc/labuse/labuse.env),"
echo "  rebuild front (VITE_RUN_LABEL, deploy_app.sh), restart labuse HORS fenêtre de backup."
