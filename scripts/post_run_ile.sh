#!/bin/bash
# POST-RUN ÎLE — à lancer quand run_ile_q_v2.sh est terminé :
# 1. invariants (0 commune vide, gardes étage 0 par commune, chaudes hors SP, traçabilité)
# 2. mvt_parcels reconstruite (les tuiles servent le nouveau run)
# 3. M01 division pré-calculé pour les 24 communes
# 4. tops HTML par commune + top 50 île
set -u
cd /Users/openclaw/Desktop/labuse
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@127.0.0.1:5432/labuse"
DB="postgresql://openclaw@127.0.0.1:5432/labuse"
LOG=/tmp/ile_postrun.log
: > "$LOG"

echo "════ INVARIANTS ════" | tee -a "$LOG"
psql "$DB" -P pager=off -c "
SELECT p.commune,
  count(*) AS evaluees,
  count(*) FILTER (WHERE d.matrice_statut='chaude')       AS chaudes,
  count(*) FILTER (WHERE d.matrice_statut='a_surveiller') AS surv,
  count(*) FILTER (WHERE d.matrice_statut='a_creuser')    AS creuser,
  count(*) FILTER (WHERE d.matrice_statut='ecartee')      AS ecartees
FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
WHERE d.run_label='q_v2' GROUP BY 1 ORDER BY 3 DESC" | tee -a "$LOG"

echo "── gardes franc étage 0 (compte par garde par commune, HARD_EXCLUDE) ──" | tee -a "$LOG"
psql "$DB" -P pager=off -c "
SELECT p.commune,
  count(*) FILTER (WHERE c.layer_name='surface')          AS g_surface,
  count(*) FILTER (WHERE c.layer_name='pente')            AS g_pente,
  count(*) FILTER (WHERE c.layer_name='osm_faux_positif') AS g_osm,
  count(*) FILTER (WHERE c.layer_name='bati')             AS g_bati,
  count(*) FILTER (WHERE c.layer_name='zonage_plu_gpu')   AS g_zonage,
  count(*) FILTER (WHERE c.layer_name='risques')          AS g_ppr
FROM dryrun_cascade_results c JOIN parcels p ON p.id=c.parcel_id
WHERE c.run_label='q_v2' AND c.result='HARD_EXCLUDE' GROUP BY 1 ORDER BY 1" | tee -a "$LOG"

echo "── bascule événementielle hors Saint-Paul ──" | tee -a "$LOG"
psql "$DB" -P pager=off -c "
SELECT p.commune, count(DISTINCT c.parcel_id) AS parcelles_evenement_rouge
FROM dryrun_cascade_results c JOIN parcels p ON p.id=c.parcel_id
WHERE c.run_label='q_v2' AND c.evenement='rouge' GROUP BY 1 ORDER BY 2 DESC" | tee -a "$LOG"

echo "── traçabilité : 5 parcelles/commune, base+Σ=Q (clamp 1..100 admis) ──" | tee -a "$LOG"
psql "$DB" -P pager=off -c "
WITH sample AS (
  SELECT d.parcel_id, p.commune, d.q_score,
         row_number() OVER (PARTITION BY p.commune ORDER BY md5(p.idu)) AS rn
  FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
  WHERE d.run_label='q_v2' AND d.matrice_statut <> 'ecartee'),
calc AS (
  SELECT s.commune, s.parcel_id, s.q_score,
         GREATEST(1, LEAST(100, 50 + COALESCE((SELECT sum(c.weight_applied) FROM dryrun_cascade_results c
            WHERE c.run_label='q_v2' AND c.parcel_id=s.parcel_id
              AND c.layer_name NOT IN ('proprietaire','age_dirigeant','bodacc','dpe_passoire')
              AND c.weight_applied IS NOT NULL), 0)))::int AS recompute
  FROM sample s WHERE s.rn <= 5)
SELECT commune, count(*) AS testees, count(*) FILTER (WHERE q_score = recompute) AS ok
FROM calc GROUP BY 1 ORDER BY 1" | tee -a "$LOG"

echo "════ MVT ════" | tee -a "$LOG"
.venv/bin/labuse build-mvt --label q_v2 2>&1 | tee -a "$LOG"

echo "════ M01 DIVISION × 24 ════" | tee -a "$LOG"
for c in "Les Avirons" "Bras-Panon" "Entre-Deux" "L'Étang-Salé" "Petite-Île" \
         "La Plaine-des-Palmistes" "Le Port" "La Possession" "Saint-André" "Saint-Benoît" \
         "Saint-Denis" "Saint-Joseph" "Saint-Leu" "Saint-Louis" "Saint-Pierre" \
         "Saint-Philippe" "Sainte-Marie" "Sainte-Rose" "Sainte-Suzanne" "Salazie" \
         "Le Tampon" "Les Trois-Bassins" "Cilaos"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:8010/modules/division/compute?commune=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$c")")
  echo "  division $c → HTTP $code" | tee -a "$LOG"
done

echo "════ TOPS HTML ════" | tee -a "$LOG"
.venv/bin/python scripts/gen_tops_ile.py 2>&1 | tee -a "$LOG"
echo "════ POST-RUN TERMINÉ ════" | tee -a "$LOG"
