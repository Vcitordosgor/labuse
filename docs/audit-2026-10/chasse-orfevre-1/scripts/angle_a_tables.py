#!/usr/bin/env python
"""CHASSE-ORFEVRE-1 — Angle A : contrôles table par table (doublons, orphelins,
NULL obligatoires, valeurs impossibles, encodages, géométries).

STRICTEMENT READ-ONLY : la session force default_transaction_read_only=on.
Rejouable : chaque contrôle est un SELECT idempotent, imprimé en texte.

Usage :
    PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python \
        docs/audit-2026-10/chasse-orfevre-1/scripts/angle_a_tables.py [--grep motif]

DSN : variable LABUSE_DATABASE_URL (chargée depuis .env si absente de l'env).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Luhn inline (SQL pur, sans fonction temporaire : le rôle est read-only).
# s = colonne 9 ou 14 chiffres ; la sous-requête vaut true si la clé est bonne.
# ---------------------------------------------------------------------------
def _luhn_ko(col: str, length: int) -> str:
    return (
        f"{col} ~ '^[0-9]{{{length}}}$' AND "
        f"(SELECT sum(CASE WHEN ({length}-i+1) % 2 = 0 "
        f" THEN CASE WHEN 2*substr({col},i,1)::int > 9 THEN 2*substr({col},i,1)::int - 9 "
        f"      ELSE 2*substr({col},i,1)::int END "
        f" ELSE substr({col},i,1)::int END) % 10 <> 0 "
        f" FROM generate_series(1,{length}) i)"
    )


INSEE_OK = "between '97401' and '97424'"  # les 24 communes de La Réunion
BBOX = "(lat not between -21.5 and -20.8 or lon not between 55.2 and 55.9)"

# (section, titre, sql)
CHECKS: list[tuple[str, str, str]] = [
    # ----------------------------------------------------------- inventaire
    ("inventaire", "tables public + volumes estimés", """
        select c.relname, c.reltuples::bigint est_rows, pg_total_relation_size(c.oid)/1024/1024 mb
        from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relkind='r' order by c.reltuples desc limit 60"""),

    # -------------------------------------------------------------- parcels
    ("parcels", "total / doublons idu / idu null", """
        select count(*) total, count(*)-count(distinct idu) dup_idu,
               count(*) filter (where idu is null) idu_null from parcels"""),
    ("parcels", "nom commune hors référentiel", """
        select commune, count(*) from parcels
        where commune not in (select nom from communes_referentiel) group by 1"""),
    ("parcels", "insee (préfixe idu) hors 97401-97424", f"""
        select substring(idu,1,5) ins, count(*) from parcels
        where substring(idu,1,5) not {INSEE_OK} group by 1"""),
    ("parcels", "incohérence nom commune vs idu", """
        select count(*) from parcels p join communes_referentiel r on r.nom=p.commune
        where substring(p.idu,1,5) <> r.insee"""),
    ("parcels", "surfaces (null / <=0 / >10 Mm2)", """
        select count(*) filter (where surface_m2 is null) s_null,
               count(*) filter (where surface_m2 <= 0) s_nonpos,
               count(*) filter (where surface_m2 > 10000000) s_huge from parcels"""),
    ("parcels", "écarts surface géométrique vs contenance fiscale (x2 / /2)", """
        select count(*) from parcels where contenance_m2 > 0
          and (surface_m2/contenance_m2 > 2 or surface_m2/contenance_m2 < 0.5)"""),
    ("parcels", "exemples pires écarts surface/contenance", """
        select idu, commune, round(surface_m2::numeric) s_geom, contenance_m2 from parcels
        where contenance_m2 > 0 and (surface_m2/contenance_m2 > 2 or surface_m2/contenance_m2 < 0.5)
        order by abs(surface_m2-contenance_m2) desc limit 5"""),
    ("parcels", "contenance null / zéro ; disparues ; disparues futures", """
        select count(*) filter (where contenance_m2 is null) c_null,
               count(*) filter (where contenance_m2 = 0) c_zero,
               count(*) filter (where cadastre_disparue_le is not null) disparues,
               count(*) filter (where cadastre_disparue_le > current_date) disp_futur from parcels"""),
    ("parcels", "géométries null / invalides / vides (geom_2975)", """
        select count(*) filter (where geom is null) g_null,
               count(*) filter (where geom_2975 is null) g2975_null,
               count(*) filter (where centroid is null) c_null,
               count(*) filter (where not ST_IsValid(geom_2975)) invalid,
               count(*) filter (where ST_IsEmpty(geom_2975)) vide from parcels"""),

    # -------------------------------------- satellites parcelle (clé idu)
    ("satellites_idu", "orphelins idu -> parcels", """
        select 'parcel_zone_plu' t, count(*) n from parcel_zone_plu x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_viabilisation', count(*) from parcel_viabilisation x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_terrain', count(*) from parcel_terrain x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_solar', count(*) from parcel_solar x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_vegetation', count(*) from parcel_vegetation x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_filtre_bati', count(*) from parcel_filtre_bati x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_residuel_bati', count(*) from parcel_residuel_bati x left join parcels p using(idu) where p.idu is null
        union all select 'batiment_hauteur_lidar', count(*) from batiment_hauteur_lidar x left join parcels p using(idu) where p.idu is null
        union all select 'adresse_parcelles', count(*) from adresse_parcelles x left join parcels p using(idu) where p.idu is null
        union all select 'etablissement_parcelle', count(*) from etablissement_parcelle x left join parcels p using(idu) where p.idu is null
        union all select 'parcelle_personne_morale', count(*) from parcelle_personne_morale x left join parcels p using(idu) where p.idu is null
        union all select 'piscines', count(*) from piscines x left join parcels p using(idu) where p.idu is null
        union all select 'mvt_parcels', count(*) from mvt_parcels x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_geometrie', count(*) from parcel_geometrie x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_anc', count(*) from parcel_anc x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_adresse', count(*) from parcel_adresse x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_equipements', count(*) from parcel_equipements x left join parcels p using(idu) where p.idu is null
        union all select 'parcel_pau', count(*) from parcel_pau x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'parcel_acquerabilite', count(*) from parcel_acquerabilite x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'parcel_entree_tete', count(*) from parcel_entree_tete x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'parcel_signaux_vie', count(*) from parcel_signaux_vie x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'pc_caducs', count(*) from pc_caducs x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'parcel_renouvellement', count(*) from parcel_renouvellement x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'parcel_veille_succession', count(*) from parcel_veille_succession x where not exists (select 1 from parcels p where p.idu=x.parcelle_id)
        union all select 'rnic_coproprietes', count(*) from rnic_coproprietes x where parcelle_idu is not null and not exists (select 1 from parcels p where p.idu=x.parcelle_idu)
        union all select 'dpe_records', count(*) from dpe_records x where parcelle_idu is not null and not exists (select 1 from parcels p where p.idu=x.parcelle_idu)
        union all select 'score_e', count(*) from score_e x where not exists (select 1 from parcels p where p.idu=x.idu)
        union all select 'parcel_v_score', count(*) from parcel_v_score x where not exists (select 1 from parcels p where p.idu=x.parcelle_id)
        order by 2 desc"""),
    ("satellites_idu", "doublons idu dans les tables 1-ligne-par-parcelle", """
        select 'parcel_zone_plu' t, count(*)-count(distinct idu) d from parcel_zone_plu
        union all select 'parcel_viabilisation', count(*)-count(distinct idu) from parcel_viabilisation
        union all select 'parcel_terrain', count(*)-count(distinct idu) from parcel_terrain
        union all select 'parcel_solar', count(*)-count(distinct idu) from parcel_solar
        union all select 'parcel_vegetation', count(*)-count(distinct idu) from parcel_vegetation
        union all select 'parcel_filtre_bati', count(*)-count(distinct idu) from parcel_filtre_bati
        union all select 'mvt_parcels', count(*)-count(distinct idu) from mvt_parcels
        union all select 'parcel_geometrie', count(*)-count(distinct idu) from parcel_geometrie
        union all select 'parcel_v_score', count(*)-count(distinct parcelle_id) from parcel_v_score
        union all select 'batiment_hauteur_lidar', count(*)-count(distinct idu) from batiment_hauteur_lidar
        union all select 'parcel_residuel_bati', count(*)-count(distinct idu) from parcel_residuel_bati
        union all select 'parcel_anc', count(*)-count(distinct idu) from parcel_anc
        union all select 'parcel_adresse', count(*)-count(distinct idu) from parcel_adresse
        union all select 'parcel_equipements', count(*)-count(distinct idu) from parcel_equipements
        union all select 'score_e', count(*)-count(distinct (idu,run_label)) from score_e
        order by 2 desc"""),
    ("satellites_idu", "parcel_signaux_vie : exemples orphelins", """
        select idu, signal, updated_at::date from parcel_signaux_vie x
        where not exists (select 1 from parcels p where p.idu=x.idu) limit 5"""),
    ("satellites_idu", "parcelle_personne_morale : exemples orphelins", """
        select idu, siren, denomination, millesime from parcelle_personne_morale x
        where not exists (select 1 from parcels p where p.idu=x.idu) limit 5"""),

    # ---------------------------------- satellites parcelle (clé parcel_id)
    ("satellites_pid", "orphelins parcel_id -> parcels.id", """
        select 'parcel_residuel_runs' t, count(*) n from parcel_residuel_runs x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'score_labuse', count(*) from score_labuse x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'parcel_au_statut', count(*) from parcel_au_statut x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'pipeline_entries', count(*) from pipeline_entries x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'projet_parcelles', count(*) from projet_parcelles x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'alertes', count(*) from alertes x left join parcels p on p.id=x.parcel_id where x.parcel_id is not null and p.id is null
        union all select 'parcel_amenites', count(*) from parcel_amenites x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'parcel_constructibilite', count(*) from parcel_constructibilite x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'parcel_signals', count(*) from parcel_signals x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'parcel_bati_revele', count(*) from parcel_bati_revele x left join parcels p on p.id=x.parcel_id where p.id is null
        union all select 'parcel_bloc_membres', count(*) from parcel_bloc_membres x left join parcels p on p.id=x.parcel_id where p.id is null
        order by 2 desc"""),

    # ------------------------------------------------------- runs & scores
    ("runs", "références de run (orphelins)", """
        select 'parcel_residuel_runs.run_seq' t, count(*) n from parcel_residuel_runs x
          where not exists (select 1 from residuel_runs r where r.run_seq=x.run_seq)
        union all select 'score_labuse.run_label', count(*) from score_labuse x
          where not exists (select 1 from score_labuse_runs r where r.run_label=x.run_label)
        union all select 'parcel_bloc_membres.bloc_id', count(*) from parcel_bloc_membres x
          where not exists (select 1 from parcel_blocs b where b.id=x.bloc_id)"""),
    ("runs", "score_labuse : lignes réelles vs score_labuse_runs.n_parcelles", """
        select r.run_label, r.n_parcelles meta, (select count(*) from score_labuse s
               where s.run_label=r.run_label) reel from score_labuse_runs r order by r.computed_at"""),
    ("runs", "score_labuse : score/bande/couverture", """
        select run_label, count(*) n, min(score) smin, max(score) smax,
               count(*) filter (where score is null and not non_calculable) score_null_hors_nc,
               count(*) filter (where bande is null) bande_null,
               count(*) filter (where couverture_pct not between 0 and 100) couv_hors
        from score_labuse group by 1 order by 1"""),
    ("runs", "parcel_residuel_runs : bornes par run", """
        select run_seq, count(*) n,
               count(*) filter (where sdp_residuelle_m2 < 0) sdp_neg,
               count(*) filter (where taux_emprise_pct not between 0 and 100) taux_hors,
               max(taux_emprise_pct) taux_max,
               count(*) filter (where pct_potentiel not between 0 and 100) pct_hors,
               max(pct_potentiel) pct_max,
               count(*) filter (where surface_terrain_m2 <= 0) st_nonpos
        from parcel_residuel_runs group by 1 order by 1"""),
    ("runs", "run servi : exemples taux_emprise_pct > 100", """
        select p.idu, x.taux_emprise_pct, x.pct_potentiel, x.sdp_residuelle_m2
        from parcel_residuel_runs x join parcels p on p.id=x.parcel_id
        where x.run_seq = (select run_seq from residuel_runs where is_served limit 1)
          and x.taux_emprise_pct > 100 order by x.taux_emprise_pct desc limit 5"""),

    # ------------------------------------------------------------ lidar/dpe (connus)
    ("lidar_dpe", "batiment_hauteur_lidar : aberrations (CONNU, borné à la lecture)", """
        select count(*) filter (where faitage_m <= 0) f_nonpos,
               count(*) filter (where faitage_m > 60) f_gt60, max(faitage_m) f_max,
               count(*) filter (where egout_m <= 0) e_nonpos, max(egout_m) e_max,
               count(*) filter (where egout_m > faitage_m) egout_gt_faitage
        from batiment_hauteur_lidar"""),
    ("lidar_dpe", "dpe_records : années/coords/doublons (année 1761 CONNUE)", f"""
        select count(*) filter (where annee_construction < 1800) a_lt1800,
               count(*) filter (where annee_construction > extract(year from current_date)+1) a_futur,
               min(annee_construction) amin, max(annee_construction) amax,
               count(*) filter (where lat is not null and {BBOX}) coord_hors,
               count(*) filter (where date_etablissement > current_date) de_futur,
               count(*)-count(distinct numero_dpe) dup_num from dpe_records"""),
    ("lidar_dpe", "parcel_filtre_bati : années aberrantes (héritées DPE)", """
        select count(*) filter (where annee_construction < 1800) lt1800,
               count(*) filter (where annee_construction > extract(year from current_date)+1) futur,
               min(annee_construction) amin, max(annee_construction) amax from parcel_filtre_bati"""),

    # ------------------------------------------------------------------ dvf
    ("dvf", "dvf_mutations_parcelle : groupes de doublons exacts métier", """
        select count(*) from (select 1 from dvf_mutations_parcelle
          group by id_mutation, id_parcelle, date_mutation, valeur_fonciere, type_local,
                   surface_reelle_bati, surface_terrain, nature_culture having count(*)>1) z"""),
    ("dvf", "dvf_mutations_parcelle : valeurs/dates/coords/orphelins", f"""
        select count(*) filter (where valeur_fonciere is null) vf_null,
               count(*) filter (where valeur_fonciere <= 1) vf_le1,
               count(*) filter (where date_mutation < '1800-01-01' or date_mutation > current_date) d_hors,
               count(*) filter (where latitude is not null and
                 (latitude not between -21.5 and -20.8 or longitude not between 55.2 and 55.9)) coord_hors,
               count(*) filter (where id_parcelle is null) idp_null,
               count(*) filter (where not exists (select 1 from parcels p where p.idu=id_parcelle)) orphelins
        from dvf_mutations_parcelle"""),
    ("dvf", "dvf_mutations_parcelle : exemples orphelins id_parcelle", """
        select id, id_mutation, id_parcelle, date_mutation, valeur_fonciere from dvf_mutations_parcelle x
        where not exists (select 1 from parcels p where p.idu=x.id_parcelle)
        order by date_mutation desc limit 5"""),
    ("dvf", "dvf_mutations (géolocalisées) : doublons/valeurs", """
        select count(*)-count(distinct mutation_id) dup_mutation_id,
               count(*) filter (where valeur_fonciere <= 1) vf_le1,
               count(*) filter (where date_mutation > current_date or date_mutation < '1800-01-01') d_hors,
               count(*) filter (where geom is null) g_null from dvf_mutations"""),
    ("dvf", "dvf_mutation_detail : orphelins vers dvf_mutations_parcelle", """
        select count(*) from dvf_mutation_detail d
        where not exists (select 1 from dvf_mutations_parcelle m where m.id_mutation=d.id_mutation)"""),
    ("dvf", "dvf_mutations_histo : valeurs/dates + recouvrement avec parcelle", """
        select count(*) filter (where valeur_fonciere <= 1) vf_le1,
               count(*) filter (where date_mutation > current_date or date_mutation < '1800-01-01') d_hors,
               (select count(*) from (select id_mutation, id_parcelle from dvf_mutations_parcelle
                 intersect select id_mutation, id_parcelle from dvf_mutations_histo) z) recouvrement
        from dvf_mutations_histo"""),
    ("dvf", "dvf_secteur_medianes : bornes", """
        select count(*) filter (where n_ventes <= 0) nv_nonpos,
               count(*) filter (where mediane_valeur <= 0) mv_nonpos,
               count(*) filter (where mediane_prix_m2 <= 0) mp_nonpos,
               count(*) filter (where mediane_prix_m2 > 20000) mp_enorme from dvf_secteur_medianes"""),

    # --------------------------------------------------------- siren/siret
    ("siren", "sirene_etablissements : format + Luhn + cohérence", f"""
        select count(*) filter (where siret !~ '^[0-9]{{14}}$') siret_format,
               count(*) filter (where {_luhn_ko('siret', 14)} and siren <> '356000000') siret_luhn_ko,
               count(*) filter (where siren !~ '^[0-9]{{9}}$') siren_format,
               count(*) filter (where {_luhn_ko('siren', 9)}) siren_luhn_ko,
               count(*) filter (where siren <> substr(siret,1,9)) siren_mismatch,
               count(*)-count(distinct siret) siret_dup,
               count(*) filter (where insee not {INSEE_OK}) insee_hors,
               count(*) filter (where date_creation > current_date) dc_futur,
               count(*) filter (where date_creation < '1800-01-01') dc_lt1800
        from sirene_etablissements"""),
    ("siren", "sirene : exemples dates création aberrantes", """
        select siret, denomination, date_creation from sirene_etablissements
        where date_creation > current_date or date_creation < '1800-01-01'
        order by date_creation limit 10"""),
    ("siren", "parcelle_personne_morale : siren non numériques (MAJIC 'U…') + Luhn", f"""
        select count(*) filter (where siren is null) s_null,
               count(*) filter (where siren !~ '^[0-9]{{9}}$') s_format,
               count(*) filter (where {_luhn_ko('siren', 9)}) s_luhn_ko
        from parcelle_personne_morale"""),
    ("siren", "parcelle_personne_morale : doublons (idu,siren,millesime)", """
        select count(*) from (select 1 from parcelle_personne_morale
          group by idu, siren, millesime having count(*)>1) z"""),
    ("siren", "pm_dirigeants : siren + dates", f"""
        select count(*) filter (where siren !~ '^[0-9]{{9}}$') s_format,
               count(*) filter (where {_luhn_ko('siren', 9)}) s_luhn_ko,
               count(*) filter (where date_prise_fonction > current_date) dpf_futur from pm_dirigeants"""),
    ("siren", "etablissement_parcelle : Luhn + orphelins sirene", f"""
        select count(*) filter (where {_luhn_ko('siret', 14)} and substr(siret,1,9) <> '356000000') luhn_ko,
               count(*) filter (where not exists
                 (select 1 from sirene_etablissements s where s.siret=etablissement_parcelle.siret)) orphelin
        from etablissement_parcelle"""),
    ("siren", "parcel_blocs : siren non numériques + bornes + cohérence membres", """
        select count(*) filter (where siren !~ '^[0-9]{9}$') siren_format,
               count(*) filter (where sdp_residuelle_m2 < 0) sdp_neg,
               count(*) filter (where surface_totale_m2 <= 0) s_nonpos,
               (select count(*) from parcel_blocs b where n_parcelles <>
                  (select count(*) from parcel_bloc_membres m where m.bloc_id=b.id)) n_incoherent
        from parcel_blocs"""),
    ("siren", "bodacc_depots : format siren", """
        select count(*) filter (where siren !~ '^[0-9]{9}$') fmt from bodacc_depots"""),
    ("siren", "owner_enrichment : siren absents de parcelle_personne_morale", """
        select count(*) from owner_enrichment oe where siren ~ '^[0-9]{9}$'
          and not exists (select 1 from parcelle_personne_morale p where p.siren=oe.siren)"""),

    # ------------------------------------------------------------- piscines
    ("piscines", "piscines : idu null / commune vide / surfaces", """
        select count(*) filter (where idu is null) idu_null,
               count(*) filter (where idu is null and statut='servie') idu_null_servies,
               count(*) filter (where commune is null or commune='') commune_vide,
               count(*) filter (where statut='servie' and (commune is null or commune='')) servie_commune_vide,
               count(*) filter (where surface_m2 <= 0) s_nonpos,
               count(*) filter (where confiance < 0 or confiance > 1) conf_hors from piscines"""),

    # -------------------------------------------------------------- permis
    ("permis", "sitadel_permits : doublons/dates/geom", """
        select count(*)-count(distinct permit_id) dup,
               count(*) filter (where date_depot > current_date) futur,
               count(*) filter (where date_depot < '1900-01-01') ancien,
               count(*) filter (where geom is null and geom_approx is null) sans_geom,
               count(*) filter (where geom is null and geom_approx is null
                 and (idu_codes is null or idu_codes='[]'::jsonb)) sans_geom_ni_idu
        from sitadel_permits"""),
    ("permis", "m10_permit_delais : délais négatifs / dates incohérentes", """
        select count(*) filter (where delai_mois < 0) delai_neg,
               min(delai_mois) delai_min,
               count(*) filter (where date_autorisation < date_depot) autor_avant_depot,
               count(*) filter (where valide and date_autorisation < date_depot) dont_valide,
               count(*) filter (where valide and delai_mois < 0) valide_delai_neg,
               count(*) filter (where date_depot > current_date) depot_futur from m10_permit_delais"""),
    ("permis", "m10 : exemples délais négatifs", """
        select permit_id, commune, date_depot, date_autorisation, delai_mois, valide
        from m10_permit_delais where delai_mois < 0 order by delai_mois limit 5"""),

    # ----------------------------------------------- comptes & utilisateurs
    ("comptes", "utilisateurs : doublons email (casse) / format / orphelins / hash", """
        select count(*)-count(distinct lower(email)) dup_email_ci,
               count(*) filter (where email <> lower(email)) email_maj,
               count(*) filter (where email !~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$') email_format,
               count(*) filter (where not exists (select 1 from comptes c where c.id=compte_id)) orphelin,
               count(*) filter (where (hash is null or hash='') and statut='actif') actif_sans_hash
        from utilisateurs"""),
    ("comptes", "utilisateurs actifs sans hash (détail)", """
        select id, compte_id, email, statut, role, created_at::date from utilisateurs
        where (hash is null or hash='') and statut='actif'"""),
    ("comptes", "comptes : doublons de nom (insensible casse)", """
        select lower(nom) nom_ci, count(*) n, array_agg(id) ids, array_agg(statut) statuts
        from comptes group by 1 having count(*)>1"""),
    ("comptes", "comptes : stripe ids dupliqués", """
        select count(stripe_customer_id)-count(distinct stripe_customer_id) dup_cust,
               count(stripe_subscription_id)-count(distinct stripe_subscription_id) dup_sub from comptes"""),
    ("comptes", "sessions_auth : orphelins / expirées", """
        select count(*) total,
               count(*) filter (where not exists (select 1 from utilisateurs u where u.id=utilisateur_id)) orphelin,
               count(*) filter (where expire_at < now()) expiree from sessions_auth"""),

    # ----------------------------------------------------- mails & journal
    ("mails", "mail_queue : états / orphelins compte", """
        select etat, count(*) n,
               count(*) filter (where compte_id is not null and not exists
                 (select 1 from comptes c where c.id=compte_id)) orphelins_compte
        from mail_queue group by 1"""),
    ("mails", "mail_queue : détail a_rejouer", """
        select id, compte_id, mail_key, tentatives, left(coalesce(erreur,''),60) erreur, cree_at::date
        from mail_queue where etat='a_rejouer' order by cree_at limit 12"""),
    ("mails", "evenements_compte : orphelins compte/utilisateur", """
        select count(*) filter (where compte_id is not null and not exists
                 (select 1 from comptes c where c.id=compte_id)) orph_compte,
               count(*) filter (where utilisateur_id is not null and not exists
                 (select 1 from utilisateurs u where u.id=utilisateur_id)) orph_utilisateur
        from evenements_compte"""),
    ("mails", "stripe_events : doublons / futur", """
        select count(*)-count(distinct event_id) dup, count(*) filter (where recu_at > now()) futur
        from stripe_events"""),

    # -------------------------------------------------- pipeline & courrier
    ("pipeline", "pipeline_entries : GB-TEST (connu) + orphelins", """
        select count(*) total, count(*) filter (where notes like '%[GB-TEST]%') gbtest,
               count(*) filter (where compte_id is not null and not exists
                 (select 1 from comptes c where c.id=compte_id)) orph_compte,
               count(*) filter (where projet_id is not null and not exists
                 (select 1 from projets pj where pj.id=projet_id)) orph_projet from pipeline_entries"""),
    ("pipeline", "projets / projet_parcelles / courrier_demandes : orphelins", """
        select 'projets.compte_id' t, count(*) n from projets
          where compte_id is not null and not exists (select 1 from comptes c where c.id=compte_id)
        union all select 'projet_parcelles.projet_id', count(*) from projet_parcelles
          where not exists (select 1 from projets pj where pj.id=projet_id)
        union all select 'courrier_demandes.compte_id', count(*) from courrier_demandes
          where compte_id is not null and not exists (select 1 from comptes c where c.id=compte_id)
        union all select 'courrier_demandes.pipeline_entry_id', count(*) from courrier_demandes
          where pipeline_entry_id is not null and not exists
            (select 1 from pipeline_entries pe where pe.id=pipeline_entry_id)
        union all select 'alertes.compte_id', count(*) from alertes
          where compte_id is not null and not exists (select 1 from comptes c where c.id=compte_id)
        union all select 'alertes.zone_id', count(*) from alertes
          where zone_id is not null and not exists (select 1 from watch_zones z where z.id=zone_id)
        union all select 'usage_events.compte_id', count(*) from usage_events
          where compte_id is not null and not exists (select 1 from comptes c where c.id=compte_id)
        union all select 'share_links.idu', count(*) from share_links
          where not exists (select 1 from parcels p where p.idu=share_links.idu)"""),
    ("pipeline", "consultation_log : idu orphelins (dont idu de test)", """
        select count(*) from consultation_log x where idu is not null
          and not exists (select 1 from parcels p where p.idu=x.idu)"""),

    # --------------------------------------------------- référentiels divers
    ("referentiels", "tables commune : exactement 24 lignes attendues", """
        select 'rpls_commune' t, count(*) n from rpls_commune
        union all select 'commune_contexte_sru', count(*) from commune_contexte_sru
        union all select 'commune_conso_enaf', count(*) from commune_conso_enaf
        union all select 'commune_insee_logement', count(*) from commune_insee_logement
        union all select 'commune_rei', count(*) from commune_rei
        union all select 'commune_zonage_abc', count(*) from commune_zonage_abc
        union all select 'population_legale', count(*) from population_legale
        union all select 'territoire_fiscal_commune', count(*) from territoire_fiscal_commune
        union all select 'mvt_communes', count(*) from mvt_communes
        union all select 'grid_capacity', count(*) from grid_capacity
        union all select 'rp_logement_commune', count(*) from rp_logement_commune
        union all select 'mairies', count(*) from mairies
        union all select 'communes_referentiel', count(*) from communes_referentiel
        union all select 'commune_contexte_cache', count(*) from commune_contexte_cache"""),
    ("referentiels", "mairies : emails/téléphones manquants ou invalides", """
        select count(*) filter (where email is null or email='') email_vide,
               count(*) filter (where email is not null and email <> ''
                 and email !~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$') email_format,
               count(*) filter (where telephone is null or telephone='') tel_vide from mairies"""),
    ("referentiels", "commune_contexte_cache : fraîcheur", """
        select min(computed_at)::date age_min, max(computed_at)::date age_max,
               count(*) filter (where payload is null) p_null from commune_contexte_cache"""),
    ("referentiels", "plu_reglement_extrait : pages/insee/verbatim/doublons", f"""
        select count(*) filter (where page_pdf <= 0) page_nonpos,
               count(*) filter (where insee not {INSEE_OK}) insee_hors,
               count(*) filter (where texte_verbatim is null or texte_verbatim='') verbatim_vide,
               (select count(*) from (select 1 from plu_reglement_extrait
                  group by insee, zone, article_ref, page_pdf, texte_verbatim having count(*)>1) z) dup
        from plu_reglement_extrait"""),
    ("referentiels", "catnat_arretes : dates/insee/doublons", f"""
        select count(*) filter (where date_arrete > current_date) futur,
               count(*) filter (where date_fin < date_debut) fin_avant_debut,
               count(*) filter (where insee not {INSEE_OK}) insee_hors,
               (select count(*) from (select 1 from catnat_arretes
                  group by insee, type_peril, date_arrete, date_debut, date_fin having count(*)>1) z) dup
        from catnat_arretes"""),
    ("referentiels", "rnic_coproprietes : insee/siret/lots/doublons", f"""
        select count(*) filter (where insee not {INSEE_OK}) insee_hors,
               count(*) filter (where syndic_siret is not null and syndic_siret !~ '^[0-9]{{14}}$') siret_format,
               count(*) filter (where nb_lots_habitation > nb_lots_total) lots_incoh,
               count(*)-count(distinct numero_immatriculation) dup from rnic_coproprietes"""),
    ("referentiels", "cadastre_historique : orphelins (ATTENDU : parcelles disparues)", """
        select count(*) total, count(*) filter (where not exists
          (select 1 from parcels p where p.idu=cadastre_historique.idu)) orphelins,
          count(*)-count(distinct (idu,millesime)) dup from cadastre_historique"""),

    # ---------------------------------------------------- adresses & bâti
    ("adresses", "adresses : geom/insee/encodage/doublons", f"""
        select count(*) filter (where geom is null) g_null,
               count(*) filter (where insee not {INSEE_OK}) insee_hors,
               count(*) filter (where voie like '%Ã%') enc_voie,
               count(*) filter (where voie ~ '[\\n\\r]') nl_voie,
               count(*) filter (where voie like '%'||chr(160)||'%') nbsp_voie,
               count(*)-count(distinct id_ban) dup_ban from adresses"""),
    ("adresses", "adresse_parcelles : doublons (id_ban,idu) + orphelins BAN", """
        select (select count(*) from (select 1 from adresse_parcelles
                  group by id_ban, idu having count(*)>1) z) dup,
               (select count(*) from adresse_parcelles ap where not exists
                  (select 1 from adresses a where a.id_ban=ap.id_ban)) orphelin_ban"""),
    ("adresses", "rnb_batiments : geom/insee/doublons", f"""
        select count(*) filter (where shape is null and point is null) sans_geom,
               count(*) filter (where insee not {INSEE_OK}) insee_hors,
               count(*)-count(distinct rnb_id) dup from rnb_batiments"""),
    ("adresses", "mvt_parcels : surfaces/geom", """
        select count(*) filter (where surface_m2 <= 0) s_nonpos,
               count(*) filter (where sdp_residuelle_m2 < 0) sdp_neg,
               count(*) filter (where geom_3857 is null) g_null from mvt_parcels"""),

    # -------------------------------------------------- bornes numériques
    ("bornes", "parcel_vegetation / terrain / solar / viabilisation / renouvellement", """
        select 'vegetation.canopee_pct' t, count(*) n from parcel_vegetation where canopee_pct not between 0 and 100
        union all select 'vegetation.ndvi', count(*) from parcel_vegetation where ndvi_moyen not between -1 and 1
        union all select 'terrain.pente_moy', count(*) from parcel_terrain where pente_moy_deg not between 0 and 90
        union all select 'terrain.pente_max<moy', count(*) from parcel_terrain where pente_max_deg < pente_moy_deg
        union all select 'solar.score', count(*) from parcel_solar where score_solaire not between 0 and 100
        union all select 'solar.proba_occupant', count(*) from parcel_solar where proba_proprio_occupant not between 0 and 100
        union all select 'solar.ghi<=0', count(*) from parcel_solar where ghi_kwh_m2_an <= 0
        union all select 'viabilisation.score', count(*) from parcel_viabilisation where score not between 0 and 100
        union all select 'renouvellement.score', count(*) from parcel_renouvellement where renouv_score not between 0 and 100
        union all select 'renouvellement.contrainte_pct', count(*) from parcel_renouvellement where contrainte_pct not between 0 and 100
        union all select 'residuel_bati.hauteur>60', count(*) from parcel_residuel_bati where hauteur_bati_m > 60
        union all select 'residuel_bati.emprise<0', count(*) from parcel_residuel_bati where emprise_residuelle_m2 < 0
        union all select 'veille_succession.age_hors_18_110', count(*) from parcel_veille_succession where dirigeant_age < 18 or dirigeant_age > 110
        union all select 'score_e.prix<=0', count(*) from score_e where prix_probable <= 0
        order by 2 desc"""),

    # ------------------------------------------------------------ encodage
    ("encodage", "mojibake 'Ã' / retours ligne dans les champs texte", """
        select 'sirene.denomination' t, count(*) n from sirene_etablissements where denomination like '%Ã%' or denomination ~ '[\\n\\r]'
        union all select 'sirene.adresse', count(*) from sirene_etablissements where adresse like '%Ã%' or adresse ~ '[\\n\\r]'
        union all select 'ppm.denomination', count(*) from parcelle_personne_morale where denomination like '%Ã%' or denomination ~ '[\\n\\r]'
        union all select 'pm_dirigeants.nom_prenoms', count(*) from pm_dirigeants where nom like '%Ã%' or prenoms like '%Ã%' or nom ~ '[\\n\\r]'
        union all select 'mairies.nom_adresse', count(*) from mairies where nom like '%Ã%' or adresse like '%Ã%' or commune like '%Ã%'
        union all select 'rnic.nom_adresse', count(*) from rnic_coproprietes where nom_usage like '%Ã%' or adresse like '%Ã%'
        union all select 'dvf_detail.adresse', count(*) from dvf_mutation_detail where adresse like '%Ã%'
        union all select 'adresses.voie_nbsp', count(*) from adresses where voie like '%'||chr(160)||'%'
        order by 2 desc"""),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Angle A — contrôles read-only table par table")
    ap.add_argument("--grep", help="ne joue que les contrôles dont la section ou le titre contient ce motif")
    args = ap.parse_args()

    dsn = os.environ.get("LABUSE_DATABASE_URL")
    if not dsn:
        env = Path(__file__).resolve().parents[4] / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("LABUSE_DATABASE_URL="):
                    dsn = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not dsn:
        print("LABUSE_DATABASE_URL introuvable (env ou .env)", file=sys.stderr)
        return 2

    engine = create_engine(dsn)
    failures = 0
    with engine.connect() as conn:
        conn.execute(text("SET default_transaction_read_only = on"))
        conn.execute(text("SET statement_timeout = '120s'"))
        for section, titre, sql in CHECKS:
            if args.grep and args.grep.lower() not in (section + " " + titre).lower():
                continue
            print(f"\n== [{section}] {titre} ==")
            t0 = time.time()
            try:
                res = conn.execute(text(sql))
                cols = list(res.keys())
                rows = res.fetchall()
                print("  " + " | ".join(cols))
                for r in rows[:40]:
                    print("  " + " | ".join("" if v is None else str(v) for v in r))
                if len(rows) > 40:
                    print(f"  … ({len(rows)} lignes au total)")
                print(f"  -- {time.time()-t0:.1f}s")
            except Exception as e:  # noqa: BLE001 — on continue, audit best-effort
                failures += 1
                conn.rollback()
                print(f"  !! ERREUR: {e}")
    print(f"\nTerminé — {failures} contrôle(s) en erreur.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
