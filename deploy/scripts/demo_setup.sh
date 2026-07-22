#!/usr/bin/env bash
# BLOC B — prépare LE projet de démo (idempotent : dédup douce côté API).
# Usage : BASE=http://127.0.0.1:8020 [CURL_ARGS="-u user:pass -b jar"] bash demo_setup.sh
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8020}"
C="curl -s ${CURL_ARGS:-}"
PID=$($C -X POST "$BASE/projets" -H "Content-Type: application/json" -d '{
  "nom": "Démo — 40 logements · Saint-Paul",
  "fiche": {"type_programme": "logements", "ampleur": {"logements": 40},
            "perimetre": {"mode": "communes", "communes": ["Saint-Paul"]},
            "contraintes": ["eviter_ppr"], "budget_foncier_eur": 1500000}}' | python3 -c "import json,sys; d=json.load(sys.stdin); print((d.get('projet') or d).get('id'))")
echo "projet #$PID"
$C -X POST "$BASE/projets/$PID/proposer" -H "Content-Type: application/json" -d '{"limit": 24}' -o /dev/null
# un tri qui raconte une histoire : 3 retenues, 1 à analyser, 1 écartée
IDUS=$($C "$BASE/projets/$PID/parcelles" | python3 -c "
import json,sys
d = json.load(sys.stdin)
p = [x['idu'] for x in d.get('proposees', [])]
print(' '.join(p[:5]))")
i=0
for idu in $IDUS; do
  case $i in
    0|1|2) st=retenue;; 3) st=a_analyser;; *) st=ecartee;;
  esac
  $C -X PATCH "$BASE/projets/$PID/parcelle/$idu" -H "Content-Type: application/json" -d "{\"statut\": \"$st\"}" -o /dev/null
  echo "  $idu → $st"
  i=$((i+1))
done
echo "démo prête (projet #$PID : 3 retenues → CRM, 1 à analyser, 1 écartée récupérable)"
