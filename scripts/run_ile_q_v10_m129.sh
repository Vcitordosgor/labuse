#!/bin/bash
# RE-RUN q_v10_m129 — les 24 communes, --no-resume (réécriture complète).
set -u
cd /Users/openclaw/Desktop/labuse
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@127.0.0.1:5432/labuse"
LOG=/tmp/rerun_q_v10_m129.log
BIN=.venv/bin/labuse
LABEL=q_v10_m129

COMMUNES=(97415 97417 97423 97402 97419 97403 97406 97424 97421 97401 97404 97407 97420 97405 97408 97418 97410 97409 97413 97412 97414 97411 97416 97422)

echo "════ RE-RUN ÎLE $LABEL — $(date '+%F %T') ════" >> "$LOG"
for insee in "${COMMUNES[@]}"; do
  echo "━━━ $insee — $(date '+%T') ━━━" >> "$LOG"
  $BIN dryrun-evaluate --label $LABEL --commune "$insee" --chunk 2000 --no-resume >> "$LOG" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then echo "✗ ÉCHEC $insee (rc=$rc) — ARRÊT" >> "$LOG"; exit $rc; fi
  echo "✓ $insee terminé $(date '+%T')" >> "$LOG"
done
echo "════ RE-RUN TERMINÉ — $(date '+%F %T') ════" >> "$LOG"
