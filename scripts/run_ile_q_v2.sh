#!/bin/bash
# PHASE 1 — extension q_v2 aux 23 communes (Saint-Paul = référence, non recalculée).
# Par taille croissante ; chunké/résumable (relancer ce script reprend où il en était).
set -u
cd /Users/openclaw/Desktop/labuse
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@127.0.0.1:5432/labuse"
LOG=/tmp/ile_run.log
BIN=.venv/bin/labuse

COMMUNES=(97417 97423 97402 97419 97403 97406 97424 97421 97401 97404 97407 97420 97405 97408 97418 97410 97409 97413 97412 97414 97411 97416 97422)

echo "════ RUN ÎLE q_v2 — $(date '+%F %T') ════" >> "$LOG"
for insee in "${COMMUNES[@]}"; do
  echo "━━━ $insee — evaluate $(date '+%T') ━━━" >> "$LOG"
  $BIN dryrun-evaluate --label q_v2 --commune "$insee" --chunk 2000 >> "$LOG" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then echo "✗ ÉCHEC evaluate $insee (rc=$rc) — ARRÊT" >> "$LOG"; exit $rc; fi
  echo "━━━ $insee — matrice ━━━" >> "$LOG"
  $BIN dryrun-matrice --label q_v2 --commune "$insee" >> "$LOG" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then echo "✗ ÉCHEC matrice $insee (rc=$rc) — ARRÊT" >> "$LOG"; exit $rc; fi
  echo "✓ $insee terminé $(date '+%T')" >> "$LOG"
done
echo "════ RUN ÎLE TERMINÉ — $(date '+%F %T') ════" >> "$LOG"
