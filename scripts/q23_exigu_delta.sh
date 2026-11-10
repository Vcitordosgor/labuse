#!/bin/bash
# DEPLOY-GROUPE-3 — RECALCUL PARTIEL de q_v23 après le correctif fix/exigu-fix-1.
# Ne recalcule QUE les parcelles dont la cause résiduel (seq 18) est 'terrain_exigu'.
# Ne refait NI l'île, NI la cascade, NI build_all, NI le Signal (exigu-fix = résiduel/capacité seul).
# À lancer SUR LE VPS, en `labuse`, APRÈS déploiement d'origin/main (exigu-fix compris).
#   sudo -u labuse bash /opt/labuse/app/scripts/q23_exigu_delta.sh
set -euo pipefail
set -a; . /etc/labuse/labuse.env; set +a
export LABUSE_RESIDUEL_RUN_SEQ=18            # Score/scénarios lisent le run candidat seq 18
cd /opt/labuse/app
PY=/opt/labuse/venv/bin/python
PG="sudo -u postgres psql -d labuse -At"
RS=18

echo "== 0. PRÉ-REQUIS : exigu-fix déployé ? (diff limité à la règle terrain_exigu — sinon STOP) =="
echo "   disque avant :"; df -h / | tail -1

echo "== 1. cible = parcelles terrain_exigu du run candidat (seq $RS) =="
$PG -c "SELECT parcel_id FROM parcel_residuel_runs WHERE run_seq=$RS AND cause='terrain_exigu' ORDER BY parcel_id" > /tmp/q23_exigu_ids.txt
N=$(wc -l < /tmp/q23_exigu_ids.txt); echo "   N = $N parcelles"
# snapshot AVANT (pour isoler les parcelles CORRIGÉES ensuite) — table scratch, pas une table de run
$PG -c "DROP TABLE IF EXISTS _q23_exigu_cible; CREATE TABLE _q23_exigu_cible(pid int PRIMARY KEY);"
sudo -u postgres psql -d labuse -c "\copy _q23_exigu_cible(pid) FROM '/tmp/q23_exigu_ids.txt'"
split -n l/4 /tmp/q23_exigu_ids.txt /tmp/q23_exigu_shard_

echo "== 2. RÉSIDUEL delta : compute-residuel --into-run $RS --parcelles-fichier (4 shards) =="
t0=$(date +%s)
for f in /tmp/q23_exigu_shard_*; do
  setsid nohup $PY -u -m labuse.cli compute-residuel --into-run $RS --parcelles-fichier "$f" \
    > "/tmp/q23_exigu_resid_$(basename "$f").log" 2>&1 < /dev/null &
done
wait
echo "   résiduel delta fini en $(( $(date +%s)-t0 ))s"; df -h / | tail -1

echo "== 3. sous-ensemble CORRIGÉ (cause n'est plus terrain_exigu) =="
$PG -c "SELECT c.pid FROM _q23_exigu_cible c JOIN parcel_residuel_runs r ON r.parcel_id=c.pid AND r.run_seq=$RS WHERE r.cause IS DISTINCT FROM 'terrain_exigu' ORDER BY c.pid" > /tmp/q23_exigu_corrigees.txt
NC=$(wc -l < /tmp/q23_exigu_corrigees.txt); echo "   $NC parcelles reclassées (ne sont plus terrain_exigu)"

echo "== 4. SCORE LABUSE delta (sur TOUTES les cibles — déterministe, ~rapide) =="
$PY -u -m labuse.cli score-labuse --run q_v23 --parcelles-fichier /tmp/q23_exigu_ids.txt \
  --cascade-label q_v23 --signal-run q_v23 --residuel-run-seq $RS

echo "== 5. SCÉNARIOS V2 delta (enrich, sur les CORRIGÉES seulement) =="
$PY -u - <<PYEOF
import os
from labuse.db import session_scope
from labuse.scoring import scenarios_v2_persist as P
ids = [int(l) for l in open("/tmp/q23_exigu_corrigees.txt") if l.strip()]
print(f"scénarios V2 enrich sur {len(ids)} parcelles corrigées")
with session_scope() as s:
    b = P.compute_scenarios_v2_batch(s, ids, run_label="q_v23", enrich=True, log=lambda m: None)
    print("bilan:", b)
PYEOF

echo "== 6. ménage + disque après =="
$PG -c "DROP TABLE IF EXISTS _q23_exigu_cible;"
df -h / | tail -1
echo "== FAIT. Rejouer ensuite les 7 contrôles : python scripts/q23_gate.py =="
