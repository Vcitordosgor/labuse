#!/bin/bash
# DEPLOY-GROUPE-3 — RECALCUL PARTIEL de q_v23 après fix/exigu-fix-1 (déploiement 2).
# Cible = parcelles cause='terrain_exigu' du run candidat seq 18 (= le set emprise<seuil du ré-examen,
# le reste du code est inchangé octet-pour-octet → recalcul partiel valide ; preuve par q23_exigu_proof.py).
# Recalcule : résiduel (--into-run 18) + cache parcel_constructibilite + Score LABUSE. Les scénarios V2
# sont ensuite ENRICHIS EN PLEIN (île, séparément). Ne refait NI cascade NI build_all NI Signal NI l'île.
# À lancer en `labuse` sur le VPS, APRÈS déploiement 2 (exigu-fix compris) et hors 01-05.
set -euo pipefail
set -a; . /etc/labuse/labuse.env; set +a
export LABUSE_RESIDUEL_RUN_SEQ=18
cd /opt/labuse/app
PY=/opt/labuse/venv/bin/python
PG="sudo -u postgres psql -d labuse -At"
RS=18

echo "== 0. disque avant =="; df -h / | tail -1
echo "== 1. cible = terrain_exigu du run candidat (seq $RS) =="
$PG -c "SELECT parcel_id FROM parcel_residuel_runs WHERE run_seq=$RS AND cause='terrain_exigu' ORDER BY parcel_id" > /tmp/q23_exigu_ids.txt
N=$(wc -l < /tmp/q23_exigu_ids.txt); echo "   N = $N parcelles"
split -n l/4 /tmp/q23_exigu_ids.txt /tmp/q23_exigu_shard_

echo "== 2. RÉSIDUEL delta (--into-run $RS --parcelles-fichier, 4 shards) =="
t0=$(date +%s)
for f in /tmp/q23_exigu_shard_*; do
  setsid nohup $PY -u -m labuse.cli compute-residuel --into-run $RS --parcelles-fichier "$f" \
    > "/tmp/q23_exigu_resid_$(basename "$f").log" 2>&1 < /dev/null &
done
wait
echo "   résiduel delta fini en $(( $(date +%s)-t0 ))s"; df -h / | tail -1

echo "== 3. cache parcel_constructibilite delta (--parcelles-fichier) =="
t0=$(date +%s)
$PY -u -m labuse.cli compute-constructibilite --parcelles-fichier /tmp/q23_exigu_ids.txt
echo "   constructibilité delta fini en $(( $(date +%s)-t0 ))s"; df -h / | tail -1

echo "== 4. SCORE LABUSE delta (--parcelles-fichier, lit résiduel seq $RS) =="
$PY -u -m labuse.cli score-labuse --run q_v23 --parcelles-fichier /tmp/q23_exigu_ids.txt \
  --cascade-label q_v23 --signal-run q_v23 --residuel-run-seq $RS

echo "== 5. sous-ensemble CORRIGÉ (cause n'est plus terrain_exigu) — info =="
$PG -c "SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=$RS AND parcel_id IN (SELECT parcel_id FROM parcel_residuel_runs WHERE run_seq=$RS AND cause='terrain_exigu')" >/dev/null 2>&1 || true
NC=$($PG -c "WITH cible AS (SELECT line::int pid FROM regexp_split_to_table(pg_read_file('/tmp/q23_exigu_ids.txt'),E'\n') line WHERE line<>'') SELECT count(*) FROM cible c JOIN parcel_residuel_runs r ON r.parcel_id=c.pid AND r.run_seq=$RS WHERE r.cause IS DISTINCT FROM 'terrain_exigu'" 2>/dev/null || echo "?")
echo "   $NC parcelles ne sont plus terrain_exigu (régain ou assiette_a_verifier)"
echo "== FAIT (résiduel + constructibilité + Score). SUITE : enrich scénarios V2 île + 7 contrôles + preuve. =="
