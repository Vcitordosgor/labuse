-- NU4-D — dossier promoteur par parcelle, run servi q_v20 (cascade q_v19_sources)
-- :sample = 'top' (100 mieux classées par rang) | 'bas' (100 au sort déterministe dans ecartee)
WITH sel AS (
  SELECT s.* FROM parcel_p_score_v2 s
  WHERE s.run_id='q_v20'
    AND ( (:'sample'='top' AND s.rang IS NOT NULL)
       OR (:'sample'='bas' AND s.tier='ecartee') )
), ech AS (
  SELECT * FROM sel
  ORDER BY CASE WHEN :'sample'='top' THEN rang END ASC,
           CASE WHEN :'sample'='bas' THEN md5(parcelle_id) END
  LIMIT 100
)
SELECT e.parcelle_id AS idu, e.tier, e.rang, round(e.p_raw::numeric,4) AS p_raw,
       e.copro, e.event_date, round(e.mult_base::numeric,2) AS mult_base,
       e.potentiel_sdp_m2, round(e.prix_commune_eur_m2::numeric,0) AS prix_commune_m2,
       round(e.valeur_creee_eur::numeric,0) AS valeur_creee, e.indice_opportunite,
       e.acces_pm_siren, e.acces_courrier, p.commune,
       round(p.surface_m2::numeric,0) AS surface_dessin,
       round(p.contenance_m2::numeric,0) AS contenance,
       zp.zone_fam, zp.zone_lib, zp.zone_filtre,
       r.sdp_residuelle_m2 AS sdp_resid, round(r.taux_emprise_pct::numeric,1) AS taux_emprise,
       r.sous_densite, r.cause AS resid_cause, round(r.pct_potentiel::numeric,2) AS pct_potentiel,
       pc.label AS constr_label, pc.motif AS constr_motif,
       au.classe AS au_classe, br.bande AS bati_revele,
       fb.decision AS filtre_bati, fb.ratio_pct AS bati_ratio,
       round(t.pente_moy_deg::numeric,1) AS pente_moy, t.flag_terrassement_lourd AS pente_lourde,
       (SELECT string_agg(DISTINCT d.layer_name, '|') FROM dryrun_cascade_results d
        WHERE d.run_label='q_v19_sources' AND d.parcel_id=p.id AND d.result='HARD_EXCLUDE') AS exclu_layers
FROM ech e JOIN parcels p ON p.idu=e.parcelle_id
LEFT JOIN parcel_zone_plu zp ON zp.idu=e.parcelle_id
LEFT JOIN parcel_residuel r ON r.parcel_id=p.id
LEFT JOIN parcel_constructibilite pc ON pc.parcel_id=p.id
LEFT JOIN parcel_au_statut au ON au.parcel_id=p.id
LEFT JOIN parcel_bati_revele br ON br.parcel_id=p.id
LEFT JOIN parcel_filtre_bati fb ON fb.parcel_id=p.id
LEFT JOIN parcel_terrain t ON t.idu=e.parcelle_id
ORDER BY e.rang ASC NULLS LAST, e.parcelle_id;
