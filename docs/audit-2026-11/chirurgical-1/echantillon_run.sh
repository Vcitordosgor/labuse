#!/bin/bash
# CHIRURGICAL-1 — exécution par groupe (chaque requête autonome et rapide).
# Reproductible : ordre déterministe md5(idu||':'||sel). Assemble echantillon.csv (dédoublon C>B>A).
set -e
cd "$(dirname "$0")/../../.."
DBURL=$(grep '^LABUSE_DATABASE_URL=' .env | cut -d= -f2- | sed 's|postgresql+psycopg|postgresql|')
Q(){ psql "$DBURL" -t -A -F',' -v ON_ERROR_STOP=1 -c "SET statement_timeout='120s'; SET max_parallel_workers_per_gather=0;" -c "$1"; }
OUT=docs/audit-2026-11/chirurgical-1/_groups.csv
: > "$OUT"

echo "[A] constructible/commune"; Q "
WITH e AS (
  SELECT p.idu,p.commune,p.surface_m2,z.zone_fam FROM parcels p
  LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
  LEFT JOIN parcel_constructibilite c ON c.parcel_id=p.id
  WHERE c.parcel_id IS NULL AND p.surface_m2 IS NOT NULL
    AND ((p.commune<>'Saint-Philippe' AND z.zone_fam IN ('U','AU')
          AND NOT EXISTS(SELECT 1 FROM cascade_results cr WHERE cr.parcel_id=p.id AND cr.layer_name='risques' AND cr.detail ILIKE '%zone rouge%'))
      OR (p.commune='Saint-Philippe' AND z.zone_fam IS NULL AND p.surface_m2>300))),
r AS (SELECT *,row_number() OVER(PARTITION BY commune ORDER BY md5(idu||':A-c1-20261114')) rn FROM e)
SELECT idu,commune,surface_m2,zone_fam,'A','A_constructible_commune' FROM r WHERE rn=1;" >> "$OUT"

echo "[B1] agricole/naturelle"; Q "
SELECT p.idu,p.commune,p.surface_m2,z.zone_fam,'B','B1_agricole_naturelle'
FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE z.zone_fam IN ('A','N') AND p.surface_m2 IS NOT NULL
ORDER BY md5(p.idu||':B1-c1-20261114') LIMIT 2;" >> "$OUT"

echo "[B2] a cheval (spatial, pool 4000)"; Q "
WITH pool AS (SELECT id,idu,commune,surface_m2,geom_2975 FROM parcels WHERE surface_m2>500 AND geom_2975 IS NOT NULL ORDER BY md5(idu||':B2pool-c1-20261114') LIMIT 4000),
inter AS (SELECT po.id,po.idu,po.commune,po.surface_m2, CASE WHEN sl.subtype LIKE 'AU%' THEN 'AU' ELSE sl.subtype END fam, ST_Area(ST_Intersection(po.geom_2975,sl.geom_2975)) a FROM pool po JOIN spatial_layers sl ON sl.kind='plu_gpu_zone' AND ST_Intersects(po.geom_2975,sl.geom_2975)),
fam AS (SELECT id,idu,commune,surface_m2,fam,sum(a) fa FROM inter GROUP BY 1,2,3,4,5),
cheval AS (SELECT id,idu,commune,surface_m2 FROM fam WHERE fa>0.05*surface_m2 GROUP BY 1,2,3,4 HAVING count(*)>=2)
SELECT c.idu,c.commune,c.surface_m2,z.zone_fam,'B','B2_a_cheval' FROM cheval c LEFT JOIN parcel_zone_plu z ON z.idu=c.idu
ORDER BY md5(c.idu||':B2pick-c1-20261114') LIMIT 2;" >> "$OUT"

echo "[B3] zone rouge partielle"; Q "
WITH red AS (SELECT DISTINCT parcel_id FROM cascade_results WHERE layer_name='risques' AND detail LIKE 'PPR zone rouge sur %')
SELECT p.idu,p.commune,p.surface_m2,z.zone_fam,'B','B3_zone_rouge_partielle'
FROM red JOIN parcels p ON p.id=red.parcel_id LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
ORDER BY md5(p.idu||':B3-c1-20261114') LIMIT 2;" >> "$OUT"

echo "[B4] >2ha urbain"; Q "
SELECT p.idu,p.commune,p.surface_m2,z.zone_fam,'B','B4_grande_zone_urbaine'
FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.surface_m2>20000 AND z.zone_fam IN ('U','AU')
ORDER BY md5(p.idu||':B4-c1-20261114') LIMIT 2;" >> "$OUT"

echo "[B5] copropriete (depuis rnic)"; Q "
WITH co AS (
  SELECT DISTINCT parcelle_idu AS idu FROM rnic_coproprietes WHERE parcelle_idu IS NOT NULL
  UNION
  SELECT DISTINCT jsonb_array_elements_text(idu_codes) AS idu FROM rnic_coproprietes WHERE jsonb_typeof(idu_codes)='array')
SELECT p.idu,p.commune,p.surface_m2,z.zone_fam,'B','B5_copropriete'
FROM co JOIN parcels p ON p.idu=co.idu LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.surface_m2 IS NOT NULL
ORDER BY md5(p.idu||':B5-c1-20261114') LIMIT 2;" >> "$OUT"

echo "[B6] proprietaire public"; Q "
WITH pub AS (SELECT DISTINCT idu FROM pm_proprietaires_millesimes WHERE millesime=2024 AND forme_juridique IN ('COM','DEPT','ETAT','REGION','COLL'))
SELECT p.idu,p.commune,p.surface_m2,z.zone_fam,'B','B6_proprietaire_public'
FROM pub JOIN parcels p ON p.idu=pub.idu LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.surface_m2 IS NOT NULL
ORDER BY md5(p.idu||':B6-c1-20261114') LIMIT 2;" >> "$OUT"

echo "[C] canaris"; Q "
SELECT p.idu,p.commune,p.surface_m2,z.zone_fam,'C','C_canari'
FROM parcels p LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.idu IN ('97422000AD0887','97416000HT0538');" >> "$OUT"

# Dédoublonnage C>B>A via awk (prio: C=1,B=2,A=3) en gardant la 1re occurrence par idu
echo "idu,commune,surface_m2,zone_fam,groupe,famille" > docs/audit-2026-11/chirurgical-1/echantillon.csv
awk -F',' '{prio=($5=="C"?1:($5=="B"?2:3)); if(!(($1) in best)||prio<best[$1]){best[$1]=prio; line[$1]=$0}} END{for(k in line) print line[k]}' "$OUT" \
  | sort -t',' -k5,5 -k6,6 -k2,2 >> docs/audit-2026-11/chirurgical-1/echantillon.csv
echo "TOTAL distinct: $(($(wc -l < docs/audit-2026-11/chirurgical-1/echantillon.csv)-1))"
