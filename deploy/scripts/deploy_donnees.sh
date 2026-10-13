#!/usr/bin/env bash
# =============================================================================
# SOLIDITE-1 (Lot 4.1) — LE CHEMIN UNIQUE « envoyer des données du Mac vers la prod ».
# -----------------------------------------------------------------------------
# UNE routine, TOUJOURS les mêmes gardes, dans CET ordre — s'arrête au PREMIER écart :
#   1. sauvegarde prod vérifiée (dump frais + lisible pg_restore --list) ;
#   2. place disque prod suffisante (sinon STOP — cf. incident disque 94 %) ;
#   3. copie + restore en --no-owner --no-acl (propriétaire labuse) — délégués à sync-run.sh,
#      qui vérifie DÉJÀ : checksum du transfert + comptages Mac == prod par table ;
#   4. intersections FRAÎCHES (parcel_couche_intersection) AVANT toute bascule ;
#   5. BASCULE EN DERNIER (scoring + résiduel + tuiles) — jamais avant les vérifs ;
#   6. contrôle du MANIFESTE prod (le run servi est bien celui qu'on voulait) ;
#   7. /readyz == 200 ;
#   8. BANC (les 25 gardes chasse + cohérence) sur la prod.
#
# Les gestes de bascule (étape 5) ne partent QUE si tout le reste est vert. `--no-bascule`
# s'arrête après l'étape 3 (données posées, pointeurs inchangés — répétition / pré-pose).
#
# Usage :
#   deploy/scripts/deploy_donnees.sh --run-label q_v19 --residuel-seq 16 [--cascade-label q_v19_sources]
#   deploy/scripts/deploy_donnees.sh --run-label q_v19 --no-bascule     # pose sans basculer
#   deploy/scripts/deploy_donnees.sh --dry-run --run-label q_v19        # répétition (sync-run dry-run)
# =============================================================================
set -euo pipefail
HOST="${SYNC_HOST:-labuse-vps}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
MIN_FREE_GB="${LABUSE_DEPLOY_MIN_FREE_GB:-12}"
HEALTH_PORT="${LABUSE_HEALTH_PORT:-8000}"

RUN_LABEL=""; RESIDUEL_SEQ=""; CASCADE_LABEL=""; NO_BASCULE=0; DRY=0
PASS=()                                    # arguments passés tels quels à sync-run.sh
while [ $# -gt 0 ]; do
  case "$1" in
    --run-label) RUN_LABEL="${2:?}"; PASS+=(--run-label "$2"); shift ;;
    --residuel-seq) RESIDUEL_SEQ="${2:?}"; PASS+=(--residuel-seq "$2"); shift ;;
    --cascade-label) CASCADE_LABEL="${2:?}"; PASS+=(--cascade-label "$2"); shift ;;
    --no-bascule) NO_BASCULE=1 ;;
    --dry-run) DRY=1; NO_BASCULE=1; PASS+=(--dry-run) ;;
    *) echo "argument inconnu : $1" >&2; exit 2 ;;
  esac; shift
done
[ -n "$RUN_LABEL" ] || { echo "✗ --run-label obligatoire" >&2; exit 2; }
stop() { echo "✗ ARRÊT (garde $1) : $2" >&2; exit 1; }

echo "════ deploy_donnees → $HOST · run=$RUN_LABEL · bascule=$([ $NO_BASCULE = 1 ] && echo non || echo oui) ════"

echo "── GARDE 1/8 — sauvegarde prod fraîche et lisible ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash /opt/labuse/app/deploy/scripts/backup_postgres.sh' \
  || stop 1 "le backup prod a échoué — on ne déploie pas sans filet"
DERNIER=$(ssh -o BatchMode=yes "$HOST" 'ls -1t /var/backups/labuse/labuse-labuse-*.dump 2>/dev/null | head -1')
[ -n "$DERNIER" ] || stop 1 "aucun dump prod localisé après backup"
ssh -o BatchMode=yes "$HOST" "sudo -u postgres pg_restore --list '$DERNIER' >/dev/null" \
  || stop 1 "dump prod illisible (pg_restore --list)"
echo "   ✓ sauvegarde : $DERNIER"

echo "── GARDE 2/8 — place disque prod (≥ ${MIN_FREE_GB} Go) ──"
FREE_GB=$(ssh -o BatchMode=yes "$HOST" "df -BG --output=avail /var/lib/postgresql | tail -1 | tr -dc '0-9'")
echo "   libre : ${FREE_GB} Go"
[ "${FREE_GB:-0}" -ge "$MIN_FREE_GB" ] || stop 2 "disque prod trop plein (${FREE_GB} Go < ${MIN_FREE_GB} Go) — faire le ménage / agrandir avant (Lot 3)"

echo "── GARDE 3/8 — copie + restore --no-owner + comptages Mac==prod (sync-run) ──"
bash "$REPO/deploy/scripts/sync-run.sh" "${PASS[@]}" || stop 3 "sync-run a signalé un écart (checksum ou comptage)"

if [ "$NO_BASCULE" = 1 ]; then
  echo "✓ données posées, pointeurs INCHANGÉS (--no-bascule / --dry-run). Rien basculé."
  exit 0
fi

echo "── GARDE 4/8 — intersections fraîches AVANT bascule ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse /opt/labuse/venv/bin/labuse build-intersections' \
  || stop 4 "reconstruction des intersections (parcel_couche_intersection) en échec"

echo "── GARDE 5/8 — BASCULE EN DERNIER (scoring + résiduel + tuiles) ──"
ssh -o BatchMode=yes "$HOST" "sudo -u labuse /opt/labuse/venv/bin/labuse golden promote '$RUN_LABEL'" \
  || stop 5 "golden promote $RUN_LABEL en échec"
if [ -n "$RESIDUEL_SEQ" ]; then
  ssh -o BatchMode=yes "$HOST" "sudo -u labuse /opt/labuse/venv/bin/labuse residuel-serve '$RESIDUEL_SEQ'" \
    || stop 5 "residuel-serve $RESIDUEL_SEQ en échec"
fi
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse /opt/labuse/venv/bin/labuse build-mvt' \
  || stop 5 "build-mvt (tuiles) en échec"

echo "── GARDE 6/8 — contrôle du manifeste prod (served_run.txt = pointeur de vérité) ──"
MANIF=$(ssh -o BatchMode=yes "$HOST" "grep -vE '^[[:space:]]*#' /opt/labuse/app/config/served_run.txt 2>/dev/null | grep -vE '^[[:space:]]*\$' | head -1")
echo "   servi prod = ${MANIF:-?} (voulu $RUN_LABEL)"
[ "$MANIF" = "$RUN_LABEL" ] || stop 6 "le manifeste prod (${MANIF:-vide}) ne sert pas $RUN_LABEL"

echo "── GARDE 7/8 — /readyz ──"
ssh -o BatchMode=yes "$HOST" "curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:${HEALTH_PORT}/readyz | grep -q 200" \
  || stop 7 "/readyz != 200 après bascule"

echo "── GARDE 8/8 — banc (chasse + cohérence) sur la prod ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse /opt/labuse/venv/bin/labuse jobs run coherence-banc' \
  || stop 8 "le banc a signalé un problème — vérifier les incidents (labuse ops incidents)"

echo "✓✓ DÉPLOIEMENT DONNÉES COMPLET — $RUN_LABEL servi, manifeste OK, /readyz 200, banc joué."
