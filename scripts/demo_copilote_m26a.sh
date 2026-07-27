#!/usr/bin/env bash
# M26-A · Point d'arrêt B — démo par curl (pas d'UI).
#
# Lance un run « collectif 6 logements Saint-Paul, 480 k€, hors PPR rouge », suit le fil
# SSE (rejeu + streaming), puis montre l'état final + les retenues/écartées EN BASE.
#
# Prérequis : l'API lancée sur la base APPLICATIVE (le serveur crée les tables copilote
# au boot), une clé ANTHROPIC_API_KEY dans l'environnement du serveur (interpréteur) :
#   .venv/bin/uvicorn labuse.api.app:app --port ${PORT:-8016}
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8016}"
DB_URL="${LABUSE_DEMO_DB:-postgresql://openclaw@localhost:5432/labuse}"
BRIEF="collectif 6 logements Saint-Paul, 480 k€, hors PPR rouge"

echo "── 1. POST /api/copilote/runs ──────────────────────────────────────────"
RUN_ID=$(curl -sf -X POST "$BASE/api/copilote/runs" \
  -H 'Content-Type: application/json' \
  -d "{\"mission\": \"instruire\", \"brief_raw\": \"$BRIEF\"}" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
echo "run_id = $RUN_ID"

echo
echo "── 2. SSE /runs/$RUN_ID/events (rejeu + live, coupé à la fin du run) ──"
curl -sN "$BASE/api/copilote/runs/$RUN_ID/events" | tee /tmp/m26a_sse_1.txt | sed -n '1,200p'

echo
echo "── 3. Reconnexion SSE avec after_seq=3 (reprise sans doublon) ─────────"
curl -sN "$BASE/api/copilote/runs/$RUN_ID/events?after_seq=3" | head -40

echo
echo "── 4. GET /runs/$RUN_ID (état dérivé de l'event log) ──────────────────"
curl -sf "$BASE/api/copilote/runs/$RUN_ID" | python3 -m json.tool | head -50

echo
echo "── 5. Retenues / écartées EN BASE (agent_run_parcels) ─────────────────"
psql "$DB_URL" -c "SELECT verdict, count(*) FROM agent_run_parcels
                   WHERE run_id = '$RUN_ID' GROUP BY verdict ORDER BY verdict;"
psql "$DB_URL" -c "SELECT parcel_idu, verdict, left(coalesce(motif,''), 60) AS motif
                   FROM agent_run_parcels WHERE run_id = '$RUN_ID'
                   ORDER BY verdict DESC, parcel_idu LIMIT 15;"

echo
echo "── 6. Event log brut (source de vérité) ───────────────────────────────"
psql "$DB_URL" -c "SELECT seq, kind, left(payload::text, 100) AS payload
                   FROM agent_events WHERE run_id = '$RUN_ID' ORDER BY seq;"
