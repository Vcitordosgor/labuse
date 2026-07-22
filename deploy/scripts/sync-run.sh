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
#   deploy/scripts/sync-run.sh --dry-run              # tout SAUF le restore (répétition)
#   deploy/scripts/sync-run.sh                        # bascule réelle
# Env requis pour l'étape 5 (golden) :
#   LABUSE_QA_TARGET, LABUSE_QA_BASIC, LABUSE_QA_PASSWORD (cf. M7_MISE_EN_LIGNE.md)
# ⚠ Ne JAMAIS lancer pendant le backup VPS de 3h (leçon M7 : verrous croisés).
# ⚠ Après une bascule de LABEL servi : mettre aussi à jour LABUSE_SERVED_RUN
#   (/etc/labuse/labuse.env) + rebuild front (VITE_RUN_LABEL) — rappelé en fin de script.
# =============================================================================
set -euo pipefail
HOST="${SYNC_HOST:-labuse-vps}"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
PG=${PG_BIN:-/Users/openclaw/miniforge3/envs/labusedb/bin}
LOCAL_DB="${LABUSE_LOCAL_DB:-postgresql://openclaw@localhost:5432/labuse}"
STAMP=$(date +%Y%m%d-%H%M%S)
DUMP=/tmp/labuse_runsync_${STAMP}.dump

# Les tables de la grande passe : runs + scores + badges/dérivés recalculés localement.
TABLES=(parcel_p_score_v2 p_score_v2_runs dryrun_cascade_results dryrun_parcel_evaluations
        parcel_evaluations pc_caducs defisc_fenetres score_e dvf_prix_sortie_neuf surface_d_events)

echo "── 1. dump ciblé (${#TABLES[@]} tables) depuis la base locale ──"
ARGS=(); for t in "${TABLES[@]}"; do ARGS+=(-t "$t"); done
"$PG/pg_dump" -Fc "${ARGS[@]}" -d "$LOCAL_DB" -f "$DUMP"
ls -lh "$DUMP" | awk '{print "   taille:", $5}'

echo "── 2. comptages locaux (la référence) ──"
for t in "${TABLES[@]}"; do
  printf "   %-28s %s\n" "$t" "$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t")"
done > /tmp/sync_counts_local.txt
cat /tmp/sync_counts_local.txt

echo "── 3. transfert ──"
rsync -a --partial "$DUMP" "$HOST":/tmp/labuse_runsync.dump
[ "$(md5 -q "$DUMP")" = "$(ssh -o BatchMode=yes "$HOST" md5sum /tmp/labuse_runsync.dump | cut -d' ' -f1)" ] \
  && echo "   checksum OK" || { echo "✗ checksum transfert"; exit 1; }

if [ "$DRY" = 1 ]; then
  echo "── DRY-RUN : arrêt avant restore. Le dump est sur le VPS (/tmp/labuse_runsync.dump). ──"
  echo "   Bascule réelle : relancer sans --dry-run."
  exit 0
fi

echo "── 4. bascule VPS (pg_restore --clean des tables ciblées) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u postgres pg_restore --clean --if-exists --no-owner --role=labuse \
  -d labuse -j 2 /tmp/labuse_runsync.dump 2>&1 | tail -2 ; sudo -u postgres psql -d labuse -c ANALYZE'

echo "── 5a. comptages VPS vs local (le moindre écart = arrêt) ──"
ok=1
while read -r line; do
  t=$(echo "$line" | awk '{print $1}'); n=$(echo "$line" | awk '{print $2}')
  nv=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -tAc 'SELECT count(*) FROM $t'")
  [ "$n" = "$nv" ] && printf "   ✓ %-28s %s\n" "$t" "$n" || { printf "   ✗ %-28s local=%s vps=%s\n" "$t" "$n" "$nv"; ok=0; }
done < /tmp/sync_counts_local.txt
[ "$ok" = 1 ] || { echo "✗ ÉCART DE COMPTAGE — diagnostic requis"; exit 1; }

echo "── 5b. tuiles (nouveau label) + golden distant ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "set -a; . /etc/labuse/labuse.env; set +a; cd /opt/labuse/app && /opt/labuse/venv/bin/labuse build-mvt 2>&1 | tail -1"'
python3 qa/golden_check.py --base-url "${LABUSE_QA_TARGET:?}" || { echo "✗ GOLDEN ROUGE — le run n'est PAS servi"; exit 1; }

echo "✓ SYNC-RUN terminé. Si le LABEL servi a changé : maj LABUSE_SERVED_RUN (/etc/labuse/labuse.env),"
echo "  rebuild front (VITE_RUN_LABEL, deploy_app.sh), restart labuse HORS fenêtre de backup."
