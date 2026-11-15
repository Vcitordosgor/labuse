-- VERITE-TERRAIN-3 — LOT 5 : ventes DVF « terrains a bâtir » (2021-2025, sans local bâti dans la
-- mutation sur la parcelle) × verdict SERVI (gate potentiel_batir). INDICE, pas preuve :
-- la vente peut précéder les règles actuelles, et le marché peut se tromper.
-- Exécuter depuis cohortes/ : psql -U openclaw -d labuse -f ../scripts/lot5_tab.sql

\set ON_ERROR_STOP on

CREATE TEMP TABLE t_tab AS
SELECT DISTINCT dp.id_parcelle AS idu, dp.id_mutation, dp.date_mutation::date AS d,
       dp.valeur_fonciere, dp.surface_terrain
FROM dvf_mutations_parcelle dp
WHERE dp.nature_culture='terrains a bâtir'
  AND NOT EXISTS (SELECT 1 FROM dvf_mutations_parcelle b
                  WHERE b.id_mutation=dp.id_mutation AND b.id_parcelle=dp.id_parcelle
                    AND b.type_local IN ('Maison','Appartement','Immeuble',
                                         'Local industriel. commercial ou assimilé'));

CREATE TEMP TABLE t_tab_servi AS
SELECT t.*, p.id IS NOT NULL AS existe, p.commune,
       (r.cause IS NOT NULL
        OR COALESCE(pc.label IN ('declasse_zone_fermee','declasse_non_constructible'), false)
        OR COALESCE(au.classe IN ('declasse_au_fermee','declasse_au_statut_inconnu','générique'), false)) AS gate_ferme,
       r.cause AS resid_cause, pc.label AS constr_label, au.classe AS au_classe,
       zp.zone_fam, zp.zone_lib
FROM t_tab t
LEFT JOIN parcels p ON p.idu=t.idu AND p.cadastre_disparue_le IS NULL
LEFT JOIN parcel_residuel r ON r.parcel_id=p.id
LEFT JOIN parcel_constructibilite pc ON pc.parcel_id=p.id
LEFT JOIN parcel_au_statut au ON au.parcel_id=p.id
LEFT JOIN parcel_zone_plu zp ON zp.idu=t.idu;

SELECT 'ventes TAB total' AS ligne, count(*) FROM t_tab_servi
UNION ALL SELECT 'parcelle au cadastre actuel', count(*) FROM t_tab_servi WHERE existe
UNION ALL SELECT 'gate FERMÉ au servi', count(*) FROM t_tab_servi WHERE existe AND gate_ferme;

SELECT split_part(COALESCE(resid_cause, constr_label, au_classe, '?'), ':', 1) AS cause,
       zone_fam, count(*)
FROM t_tab_servi WHERE existe AND gate_ferme
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 25;

\copy (SELECT * FROM t_tab_servi WHERE existe AND gate_ferme ORDER BY valeur_fonciere DESC NULLS LAST) TO 'LOT5-TAB-FERMEES.csv' CSV HEADER
