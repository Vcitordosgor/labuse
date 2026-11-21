-- VERITE-TERRAIN-3 — « ce que le client voit aujourd'hui » par parcelle (classement servi).
-- Reproduit le gate de faisabilite/potentiel_batir.py (_sql_gate) : cause résiduelle OU
-- constructibilité déclassée (zone fermée / non constructible) OU AU différée.
-- Exécuter depuis le dossier cohortes/ (où _idus.txt liste un idu par ligne) :
--   grep -ohE '974[0-9]{2}000?[A-Z0-9]{6,7}' H.csv R.csv T.csv | sort -u > _idus.txt   # cf. note
--   psql -U openclaw -d labuse -f ../scripts/servi_parcelle.sql

\set ON_ERROR_STOP on

CREATE TEMP TABLE t_idus (idu text PRIMARY KEY);
\copy t_idus FROM '_idus.txt'

CREATE TEMP TABLE t_servi AS
SELECT i.idu,
       p.id IS NOT NULL                                   AS existe,
       r.sdp_residuelle_m2, r.cause                        AS resid_cause,
       pc.label                                            AS constr_label,
       au.classe                                           AS au_classe,
       zp.zone_fam, zp.zone_lib,
       (r.cause IS NOT NULL
        OR COALESCE(pc.label IN ('declasse_zone_fermee','declasse_non_constructible'), false)
        OR COALESCE(au.classe IN ('declasse_au_fermee','declasse_au_statut_inconnu','générique'), false))
                                                           AS gate_ferme,
       CASE WHEN (r.cause IS NOT NULL
        OR COALESCE(pc.label IN ('declasse_zone_fermee','declasse_non_constructible'), false)
        OR COALESCE(au.classe IN ('declasse_au_fermee','declasse_au_statut_inconnu','générique'), false))
            THEN 0 ELSE COALESCE(r.sdp_residuelle_m2, 0) END AS sdp_restante_servie
FROM t_idus i
LEFT JOIN parcels p ON p.idu = i.idu
LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
LEFT JOIN parcel_constructibilite pc ON pc.parcel_id = p.id
LEFT JOIN parcel_au_statut au ON au.parcel_id = p.id
LEFT JOIN parcel_zone_plu zp ON zp.idu = i.idu
ORDER BY i.idu;

\copy t_servi TO 'SERVI.csv' CSV HEADER
