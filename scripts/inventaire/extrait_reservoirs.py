#!/usr/bin/env python3
"""CIRCUIT-0 Lot 1 — extraction des RÉSERVOIRS (lecture seule).

Produit docs/CIRCUIT/inventaire/reservoirs.csv : une ligne par source de data_sources
(77 lignes en base au 05/09/2026) + les sources VOULUES mais ABSENTES (ECLN, LOVAC).

Colonnes DB (psql, SELECT seul) : nom_affiche, producteur, famille, millesime_servi,
date_injection, cadence_declaree, sentinelle, methode_sonde, derniere_sonde,
dernier_millesime_publie_vu, url_producteur_connue, licence.
Colonnes CODE (surcouche OVERLAY ci-dessous, chaque entrée porte sa preuve fichier:ligne) :
id, tables_servies, mode_remplissage, job_ingestion, cron, absente_motif.
raison_non_surveillee : extraite par AST de src/labuse/sentinelle.py (RAISONS_NON_SURVEILLEES)
— telle qu'affichée au dashboard (sentinelle.raison_non_surveillee, défaut honnête sinon).

NOTE ÉNUM : le mandat prévoit job_sur_clic|cron_mensuel|depot_manuel|one_shot|derivee|absente.
Le terrain impose UNE valeur de plus : `en_direct` (source interrogée à la requête, aucun
réservoir en base — API Carto GPU, recherche-entreprises). Signalé au rapport.
"""
from __future__ import annotations

import ast
import csv
import io
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/CIRCUIT/inventaire/reservoirs.csv"
DB = "labuse"

SQL = """
SELECT d.id, d.name, coalesce(d.provider,'') AS provider, coalesce(d.category,'aucune') AS category,
       coalesce(d.source_millesime,'') AS millesime, coalesce(d.last_sync_at::date::text,'') AS last_sync,
       coalesce(d.source_cadence,'aucune') AS cadence, d.status,
       coalesce(d.endpoint_url, d.documentation_url, '') AS url,
       coalesce(d.legal_notes,'DOUTE') AS licence,
       coalesce(v.methode,'aucune') AS methode, coalesce(v.actif::text,'') AS actif,
       coalesce(v.dernier_passage_at::date::text,'') AS derniere_sonde,
       coalesce(v.dernier_vu,'') AS dernier_vu,
       left(coalesce(d.technical_notes,''),30) AS tn30
FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id
ORDER BY d.id
"""

#: vraies sondes (sentinelle.py:35 _SONDES) — 'rappel' n'est pas une surveillance amont.
SONDES = {"api", "page", "entete", "temoin"}

#: surcouche par data_sources.id — tables lues par les moteurs, mode, job, cron, preuve.
#: preuve DB = « SELECT kind,count FROM spatial_layers GROUP BY kind » exécuté le 05/09/2026.
O = {
 1: dict(slug="cadastre_api_carto", tables="parcels", mode="one_shot",
        job="labuse ingest-real / ingest-island (cadastre_ingest.py)", cron="aucun",
        preuve="src/labuse/ingestion/cadastre_ingest.py:36 ; src/labuse/cli.py:394"),
 2: dict(slug="cadastre_etalab_bulk", tables="parcels", mode="one_shot",
        job="cadastre_bulk.py (canal bulk du même réservoir)", cron="aucun",
        preuve="src/labuse/ingestion/cadastre_bulk.py ; technical_notes DOUBLON (hors vitrine, sources_catalog.py:36)"),
 3: dict(slug="gpu_plu_api_carto", tables="spatial_layers(plu_gpu_zone,plu_gpu_prescription), plu_reglement_extrait", mode="en_direct",
        job="layers_ingest.py via ingest-real ; interrogée EN DIRECT par géométrie", cron="aucun",
        preuve="src/labuse/ingestion/layers_ingest.py:178 ; src/labuse/sentinelle.py:501"),
 4: dict(slug="georisques_api", tables="spatial_layers(georisque_alea)", mode="one_shot",
        job="labuse ingest-georisques", cron="aucun", preuve="src/labuse/cli.py:1093"),
 5: dict(slug="dvf", tables="dvf_mutations, dvf_mutations_parcelle, dvf_mutations_histo, dvf_secteur_medianes, dvf_prix_sortie_neuf", mode="job_sur_clic",
        job="labuse refresh-dvf (bouton Injecter)", cron="aucun (healthz attend 10 j — ops.py:23-41)",
        preuve="config/sources_ingestion.yaml:16-18 ; src/labuse/ingestion/dvf_histo.py:16"),
 6: dict(slug="rge_alti", tables="rgealti_pente_5m, spatial_layers(pente)", mode="one_shot",
        job="DOUTE (ortho_pente.py compute-only, pas de CLI trouvée)", cron="aucun",
        preuve="table rgealti_pente_5m (SELECT information_schema 05/09) ; src/labuse/ingestion/ortho_pente.py"),
 7: dict(slug="parc_national_inpn", tables="spatial_layers(parc_national)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="src/labuse/ingestion/layers_ingest.py:178 ; kind parc_national=3"),
 8: dict(slug="forets_onf_bdtopo", tables="spatial_layers(foret_publique)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="kind foret_publique=65"),
 9: dict(slug="potentiel_foncier_region", tables="spatial_layers(potentiel_foncier,sar)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="kind potentiel_foncier=2453, sar=2453"),
 10: dict(slug="rpg_proxy_ign", tables="DOUTE (aucun kind 'rpg' en spatial_layers — usage cascade à confirmer)", mode="en_direct",
        job="DOUTE", cron="aucun", preuve="SELECT kind FROM spatial_layers : pas de kind rpg (05/09)"),
 11: dict(slug="region_ods_hub", tables="aucune (hub de catalogue)", mode="absente",
        job="aucun", cron="aucun", motif="hub (status=hub), hors vitrine — les jeux servis sont des lignes propres",
        preuve="data_sources.status='hub' ; sources_catalog.py:36"),
 12: dict(slug="peigeo_hub", tables="aucune (hub)", mode="absente", job="aucun", cron="aucun",
        motif="hub AGORAH, status=a_faire, hors vitrine", preuve="data_sources.status='a_faire' ; sentinelle.py:512"),
 13: dict(slug="deal_wms_wfs", tables="DOUTE (QP NPNRU couvert par la ligne QPV/NPNRU)", mode="one_shot",
        job="DOUTE", cron="aucun", preuve="sentinelle.py:513 (couche QP déjà couverte par « QPV 2024 (ANCT) »)"),
 14: dict(slug="geoplateforme_hub", tables="aucune (hub)", mode="absente", job="aucun", cron="aucun",
        motif="hub IGN (status=hub), hors vitrine — produits surveillés individuellement", preuve="sentinelle.py:515"),
 15: dict(slug="potentiel_foncier_ods", tables="spatial_layers(potentiel_foncier)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="même jeu que id 9 (endpoint_url identique)"),
 16: dict(slug="sitadel", tables="sitadel_permits, via_permits_geo, ingestion_runs", mode="cron_mensuel",
        job="labuse ingest-permits (permits_sdes.py, delta 3 mois + upsert)", cron="ingest-sitadel · 30 0 10 * * UTC (04:30 Réunion le 10)",
        preuve="src/labuse/cli.py:930 ; src/labuse/ingestion/permits_sdes.py:177-236 ; deploy/cron.d-labuse"),
 17: dict(slug="bd_topo", tables="spatial_layers(batiment,voirie,water,ravine)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="kind batiment=817506, voirie=235643"),
 18: dict(slug="ban", tables="adresses, adresse_parcelles", mode="job_sur_clic",
        job="labuse ingest-ban --download", cron="aucun posé (healthz attend 35 j — ops.py:23-41)",
        preuve="config/sources_ingestion.yaml:22-23 ; src/labuse/cli.py:2636"),
 19: dict(slug="osm_overpass", tables="parcel_amenites", mode="one_shot",
        job="labuse ingest-amenites", cron="aucun", preuve="src/labuse/ingestion/amenites.py:84 ; src/labuse/cli.py:1312"),
 20: dict(slug="bpe_insee", tables="spatial_layers(amenite_bpe)", mode="one_shot",
        job="labuse bpe-build", cron="aucun", preuve="src/labuse/ingestion/bpe.py:99 ; src/labuse/cli.py:236"),
 21: dict(slug="sirene_recherche_entreprises", tables="aucune (API interrogée à la requête)", mode="en_direct",
        job="deposants-actifs (lecture API)", cron="aucun", preuve="src/labuse/ingestion/deposants_actifs.py ; src/labuse/cli.py:3309"),
 22: dict(slug="bd_carto_ocs", tables="spatial_layers(ocs_ge)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="kind ocs_ge=1643"),
 24: dict(slug="abf_merimee", tables="spatial_layers(abf)", mode="one_shot",
        job="labuse ingest-abf", cron="aucun", preuve="src/labuse/ingestion/abf_merimee.py:22,29 ; src/labuse/cli.py:1405"),
 25: dict(slug="inpn_espaces_proteges", tables="spatial_layers(ens) DOUTE (kind exact à confirmer)", mode="one_shot",
        job="layers_ingest.py", cron="aucun", preuve="kind ens=73 ; sentinelle.py:510"),
 26: dict(slug="spanc_epci", tables="DOUTE (champ manuel — aucune table dédiée trouvée)", mode="depot_manuel",
        job="saisie manuelle (rappel 365 j)", cron="aucun", preuve="sentinelle.py:521,535-540 (RAPPELS_MANUELS)"),
 27: dict(slug="fichiers_fonciers_cerema", tables="aucune", mode="absente", job="aucun", cron="aucun",
        motif="NON INTÉGRÉ — convention DGFiP/Cerema, aucune donnée ingérée (rappel 365 j posé)",
        preuve="data_sources.legal_notes id 27 ; sentinelle.py:522,538"),
 28: dict(slug="erosion_cotiere_geolittoral", tables="spatial_layers(trait_de_cote)", mode="one_shot",
        job="layers_ingest.py", cron="aucun", preuve="kind trait_de_cote=24168"),
 29: dict(slug="bodacc", tables="bodacc_sondages, bodacc_procedures, bodacc_annonces_owner", mode="job_sur_clic",
        job="labuse ingest-bodacc", cron="aucun posé (healthz attend 2 j — ops.py:23-41 : écart)",
        preuve="src/labuse/cli.py:2938 ; config/sources_ingestion.yaml:13-15"),
 30: dict(slug="deal_ppr", tables="spatial_layers(ppr)", mode="one_shot",
        job="layers_ingest.py via ingest-real", cron="aucun", preuve="kind ppr=164"),
 31: dict(slug="inpi_rne", tables="pm_dirigeants, pm_dirigeant_gigogne", mode="one_shot",
        job="labuse ingest-inpi-rne / ingest-inpi-gigogne", cron="aucun", preuve="src/labuse/cli.py:971,1024"),
 32: dict(slug="georisques_ssp", tables="spatial_layers(sol_pollue)", mode="one_shot",
        job="labuse ingest-georisques", cron="aucun", preuve="kind sol_pollue=513 ; src/labuse/cli.py:1093"),
 33: dict(slug="georisques_cavites", tables="spatial_layers(cavite)", mode="one_shot",
        job="labuse ingest-georisques", cron="aucun", preuve="kind cavite=151"),
 34: dict(slug="georisques_icpe", tables="spatial_layers(icpe)", mode="one_shot",
        job="labuse ingest-georisques", cron="aucun", preuve="kind icpe=1261"),
 35: dict(slug="cartofriches", tables="spatial_layers(friche)", mode="one_shot",
        job="labuse ingest-cartofriches", cron="aucun", preuve="src/labuse/cli.py:1154 ; kind friche=372"),
 36: dict(slug="georisques_mvt", tables="spatial_layers(mvt)", mode="one_shot",
        job="labuse ingest-georisques", cron="aucun", preuve="kind mvt=3085"),
 37: dict(slug="dpe_ademe", tables="dpe_records", mode="cron_mensuel",
        job="labuse ingest-dpe (SAUTE les communes déjà peuplées sans --force)",
        cron="ingest-dpe · 0 0 12 * * UTC (04:00 Réunion le 12)",
        preuve="src/labuse/cli.py:1218 (saut) ; src/labuse/ingestion/dpe.py:86 ; deploy/cron.d-labuse"),
 38: dict(slug="qpv_2024", tables="spatial_layers(qpv)", mode="one_shot",
        job="labuse ingest-qpv", cron="aucun", preuve="src/labuse/ingestion/qpv.py:55 ; src/labuse/cli.py:1298"),
 39: dict(slug="sru_dhup", tables="commune_contexte_sru", mode="one_shot",
        job="DOUTE (script d'import à identifier)", cron="aucun", preuve="table commune_contexte_sru (information_schema 05/09)"),
 40: dict(slug="npnru", tables="anru_quartiers, spatial_layers(anru)", mode="one_shot",
        job="scripts/ingest_npnru.py", cron="aucun", preuve="scripts/ingest_npnru.py ; kind anru=8"),
 41: dict(slug="insee_rp_logement", tables="commune_insee_logement", mode="one_shot",
        job="scripts/ingest_insee_logement.py", cron="aucun", preuve="scripts/ingest_insee_logement.py"),
 42: dict(slug="plh_epci", tables="plh_epci", mode="depot_manuel",
        job="extraction documentaire (src/labuse/plh.py)", cron="aucun", preuve="src/labuse/plh.py ; legal_notes id 42 (chiffre → plh_epci.refs)"),
 43: dict(slug="rtaa_dom", tables="aucune (règles portées par le code)", mode="one_shot",
        job="aucun", cron="aucun", preuve="data_sources id 43 (textes réglementaires, catalogue)"),
 44: dict(slug="sup_gpu", tables="spatial_layers(sup)", mode="cron_mensuel",
        job="labuse ingest-sup (sup_gpu.py, purge par commune)", cron="sync-gpu · 0 0 15 * * UTC (04:00 Réunion le 15)",
        preuve="src/labuse/cli.py:2557 ; src/labuse/ingestion/sup_gpu.py:55-56 ; deploy/cron.d-labuse"),
 45: dict(slug="recherche_entreprises_dinum", tables="aucune (API interrogée à la requête)", mode="en_direct",
        job="aucun", cron="aucun", preuve="sentinelle.py:505 (agrégat en direct, couvert par veille SIRENE)"),
 46: dict(slug="bruit_itt_cerema", tables="spatial_layers(bruit_route)", mode="one_shot",
        job="labuse ingest-bruit-route", cron="aucun", preuve="src/labuse/cli.py:2580 ; kind bruit_route=1004"),
 47: dict(slug="cinquante_pas_deal", tables="spatial_layers(cinquante_pas)", mode="one_shot",
        job="labuse ingest-cinquante-pas", cron="aucun", preuve="src/labuse/cli.py:2592 ; kind cinquante_pas=163"),
 48: dict(slug="pvgis", tables="solar_grid, parcel_solar", mode="one_shot",
        job="labuse solaire-build (run gelé — productible PVGIS)", cron="aucun",
        preuve="src/labuse/cli.py:2759 ; src/labuse/ingestion/solaire.py"),
 49: dict(slug="edf_sei_opendata", tables="aucune", mode="absente", job="aucun", cron="aucun",
        motif="RETIRÉ — amont 410 Gone (jeu retiré par le producteur)", preuve="data_sources.technical_notes id 49"),
 50: dict(slug="odre_registre_installations", tables="aucune", mode="absente", job="aucun", cron="aucun",
        motif="RETIRÉ — jamais branché, aucun usage identifié", preuve="data_sources.technical_notes id 50"),
 51: dict(slug="parkings_osm_aper", tables="parkings_aper", mode="one_shot",
        job="DOUTE (CLI à identifier)", cron="aucun", preuve="table parkings_aper (information_schema 05/09)"),
 52: dict(slug="filosofi_carreaux", tables="filosofi_carreaux_200m, p_model_filo", mode="one_shot",
        job="DOUTE (CLI à identifier)", cron="aucun", preuve="table filosofi_carreaux_200m (information_schema 05/09)"),
 61: dict(slug="bd_ortho", tables="ortho_tiles, ortho_detections, parcel_equipements", mode="one_shot",
        job="labuse ortho-detect-pv (détections dérivées — cf. Q1.2)", cron="aucun",
        preuve="src/labuse/ingestion/ortho_tiles.py:28 ; src/labuse/cli.py:2788"),
 62: dict(slug="sudocuh", tables="sudocuh_procedures + config/veille_plu.yaml (registre curaté servi)", mode="depot_manuel",
        job="curation manuelle (squelette Sudocuh)", cron="aucun", preuve="src/labuse/sources_catalog.py:96-100"),
 63: dict(slug="gpu_zonage_assainissement", tables="spatial_layers(zonage_assainissement), parcel_anc", mode="one_shot",
        job="labuse anc (anc.py)", cron="aucun", preuve="src/labuse/ingestion/anc.py:45,54 ; src/labuse/cli.py:3540 ; kind zonage_assainissement=258"),
 64: dict(slug="contours_iris", tables="spatial_layers(iris_insee)", mode="one_shot",
        job="layers_ingest.py", cron="aucun", preuve="kind iris_insee=344"),
 65: dict(slug="rge_alti_5m", tables="rgealti_pente_5m", mode="one_shot",
        job="DOUTE (même réservoir que id 6)", cron="aucun", preuve="technical_notes DOUBLON id 65"),
 66: dict(slug="insee_rp2022_egoul", tables="anc_maille_taux", mode="one_shot",
        job="labuse anc", cron="aucun", preuve="src/labuse/ingestion/anc.py:45 ; src/labuse/cli.py:3540"),
 67: dict(slug="gpu_assainissement_infosurf", tables="(canal DOUBLON de gpu_zonage_assainissement)", mode="one_shot",
        job="aucun", cron="aucun", preuve="technical_notes DOUBLON id 67"),
 68: dict(slug="office_eau_chroniques", tables="anc_office_eau_commune", mode="depot_manuel",
        job="seed CSV extrait à la main d'un PDF (rappel 365 j)", cron="aucun",
        preuve="src/labuse/sentinelle.py:524,539 ; src/labuse/ingestion/anc.py"),
 69: dict(slug="bd_ortho_irc", tables="ortho_detections(vegetation), parcel_vegetation", mode="one_shot",
        job="labuse vegetation-irc / vegetation", cron="aucun", preuve="src/labuse/cli.py:3566,3579"),
 70: dict(slug="lidar_hd_mnh", tables="toiture_lidar", mode="one_shot",
        job="DOUTE (WMS consommé au build toiture)", cron="aucun", preuve="table toiture_lidar (information_schema 05/09)"),
 71: dict(slug="dgfip_parcelles_pm", tables="parcelle_personne_morale, pm_proprietaires_millesimes", mode="one_shot",
        job="labuse ingest-personnes-morales + ingest-pm-millesimes (cadence annuelle documentée)", cron="aucun (EXPLOITATION-CRON : à poser annuel)",
        preuve="src/labuse/cli.py:956,3031"),
 72: dict(slug="zfang", tables="spatial_layers(zfang,tva_primo)", mode="one_shot",
        job="labuse dispositifs-build (dérivé des textes)", cron="aucun", preuve="src/labuse/ingestion/dispositifs.py:106,133,148 ; kind zfang=24"),
 73: dict(slug="frr_ex_zrr", tables="spatial_layers(frr)", mode="one_shot",
        job="labuse dispositifs-build", cron="aucun", preuve="kind frr=23"),
 74: dict(slug="gtfs_pan", tables="spatial_layers(transport_arret,transport_ligne,pole_echange,axe_structurant)", mode="one_shot",
        job="labuse transport-reseaux", cron="aucun", preuve="src/labuse/cli.py:156 ; kind transport_arret=9956"),
 75: dict(slug="osm_transport", tables="spatial_layers(telepherique,pole_echange)", mode="one_shot",
        job="labuse transport-reseaux", cron="aucun", preuve="kind telepherique=7"),
 76: dict(slug="znieff_inpn", tables="spatial_layers(znieff)", mode="one_shot",
        job="labuse znieff-build", cron="aucun", preuve="src/labuse/cli.py:216 ; kind znieff=162"),
 80: dict(slug="znieff_region_ods", tables="aucune", mode="absente", job="aucun", cron="aucun",
        motif="canal Région non branché (status=a_faire), même donnée que znieff_inpn", preuve="data_sources.technical_notes id 80"),
 83: dict(slug="cosia", tables="spatial_layers(batiment_cosia), p_model_bati_cosia, qa_cosia_bati", mode="one_shot",
        job="labuse ingest-cosia", cron="aucun", preuve="src/labuse/ingestion/cosia.py:119 ; src/labuse/cli.py:202"),
 84: dict(slug="radar_pige", tables="pige_annonces, pige_biens, pige_faits, pige_depots, pige_captures, pige_clics, pige_prix_historique, radar_releves", mode="depot_manuel",
        job="dépôt humain /admin/radar (collecte 100 % humaine, rappel 7 j)", cron="radar-cycle 30 2 * * * ; radar-digests 0 14 * * * ; radar-releves 0 13 * * * (exploitation, pas remplissage)",
        preuve="src/labuse/pige/ ; sentinelle.py:520,536 ; deploy/cron.d-labuse"),
 86: dict(slug="sirene_etablissements", tables="sirene_etablissements", mode="cron_mensuel",
        job="labuse ingest-sirene-etab (purge complète + réinsertion DuckDB)", cron="ingest-sirene · 0 0 7 * * UTC (04:00 Réunion le 7)",
        preuve="src/labuse/cli.py:264 ; src/labuse/ingestion/sirene_etablissements.py:143 ; deploy/cron.d-labuse"),
 87: dict(slug="mobpro", tables="mobpro_commune", mode="one_shot",
        job="labuse ingest-mobpro (import abandonné pour l'étude de zone)", cron="aucun",
        preuve="src/labuse/cli.py:285 ; sentinelle.py:523"),
 88: dict(slug="trafic_rn", tables="trafic_rn", mode="one_shot",
        job="labuse ingest-trafic-rn", cron="aucun", preuve="src/labuse/cli.py:252"),
 89: dict(slug="bdnb", tables="aucune (amont ne couvre pas le 974)", mode="absente",
        job="labuse ingest-bdnb (job défini, hors crontab)", cron="ingest-bdnb défini trimestriel · ABSENT de deploy/cron.d-labuse",
        motif="SCORING-3 L3 : constat mesuré 03/09/2026 — BDNB 2026-02-a métropole seule, 974 absent",
        preuve="src/labuse/cli.py:1203 ; src/labuse/jobs.py:263-318 ; data_sources.technical_notes id 89"),
 93: dict(slug="edf_hta", tables="spatial_layers(ligne_mt,ligne_ht)", mode="one_shot",
        job="RETOURS-13 Lot 1 (commit 44443736, branche fix/retours-12 NON mergée dans main)", cron="aucun",
        preuve="kind ligne_mt=19480, ligne_ht=48 (DB locale) ; git branch --contains 44443736 → fix/retours-12 seule"),
 94: dict(slug="tcsp_osm", tables="spatial_layers(tcsp_troncon,tcsp_station,tcsp_zone)", mode="one_shot",
        job="RETOURS-13 Lot 1 (code NON mergé dans main)", cron="aucun",
        preuve="kind tcsp_troncon=142 (DB locale) ; git branch --contains 44443736"),
 95: dict(slug="reunion_express_cndp", tables="aucune trouvée (status=a_faire)", mode="absente",
        job="aucun", cron="aucun", motif="hypothèses de tracé au débat public CNDP (19/08→26/11/2026) — non branché",
        preuve="data_sources id 95 (status a_faire, créé 05/09/2026)"),
}

#: sources VOULUES mais ABSENTES de data_sources (lignes ajoutées, mode=absente).
ABSENTES = [
    dict(slug="ecln", nom="ECLN (commercialisation des logements neufs, SDES)", producteur="SDES",
         motif="métropole seule, N/A DOM — aucun stock/écoulement servi, jamais extrapolé",
         preuve="src/labuse/ingestion/vefa_neuf.py:8"),
    dict(slug="lovac", nom="LOVAC (logements vacants)", producteur="DGFiP / Cerema",
         motif="convention dédiée non instruite — prédicteur vacance absent du scoring",
         preuve="docs/audit-2026-09/SCORING-RAPPORT.md:241"),
]


def _psql(sql: str) -> list[dict]:
    out = subprocess.run(["psql", "-d", DB, "--csv", "-c", sql], capture_output=True, text=True, check=True)
    return list(csv.DictReader(io.StringIO(out.stdout)))


def _raisons() -> dict[str, str]:
    """RAISONS_NON_SURVEILLEES extrait par AST (aucun import de l'app, aucune dépendance)."""
    src = (REPO / "src/labuse/sentinelle.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "RAISONS_NON_SURVEILLEES":
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "RAISONS_NON_SURVEILLEES" for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


DEFAUT_RAISON = "Pas d'URL amont à millésime stable identifiée (endpoint de requête, import manuel ou hub)."

HEADER = ["id", "nom_affiche", "producteur", "famille", "tables_servies", "millesime_servi",
          "date_injection", "cadence_declaree", "mode_remplissage", "job_ingestion", "cron",
          "sentinelle", "methode_sonde", "derniere_sonde", "dernier_millesime_publie_vu",
          "raison_non_surveillee", "url_producteur_connue", "licence", "absente_motif", "preuve"]


def main() -> None:
    raisons = _raisons()
    rows = []
    for r in _psql(SQL):
        i = int(r["id"])
        o = O.get(i)
        if o is None:
            print(f"!! source id {i} ({r['name']}) sans surcouche — ligne DOUTE", file=sys.stderr)
            o = dict(slug=f"source_{i}", tables="DOUTE", mode="DOUTE", job="DOUTE", cron="DOUTE", preuve="DOUTE")
        surveillee = r["methode"] in SONDES and r["actif"] != "false"
        licence = r["licence"]
        if "à confirmer" in licence.lower():
            licence = "DOUTE — " + licence
        rows.append({
            "id": o["slug"], "nom_affiche": r["name"], "producteur": r["provider"],
            "famille": r["category"] or "aucune",
            "tables_servies": o["tables"], "millesime_servi": r["millesime"],
            "date_injection": r["last_sync"], "cadence_declaree": r["cadence"] or "aucune",
            "mode_remplissage": o["mode"], "job_ingestion": o["job"], "cron": o["cron"],
            "sentinelle": "oui" if surveillee else "non",
            "methode_sonde": r["methode"] if r["methode"] != "aucune" else ("rappel" if r["methode"] == "rappel" else "aucune"),
            "derniere_sonde": r["derniere_sonde"], "dernier_millesime_publie_vu": r["dernier_vu"],
            "raison_non_surveillee": ("" if surveillee or r["methode"] == "rappel"
                                       else raisons.get(r["name"], DEFAUT_RAISON)),
            "url_producteur_connue": r["url"], "licence": licence,
            "absente_motif": o.get("motif", ""),
            "preuve": (f"data_sources id={i} (SELECT du 05/09/2026) ; " + o["preuve"]
                       + (f" ; hors vitrine ({r['tn30'].strip()}…, sources_catalog.py:36)"
                          if r["status"].lower() not in ("connecte", "manuel")
                          or r["tn30"].startswith(("DOUBLON", "RETIRÉ", "DORMANT")) else "")),
        })
    for a in ABSENTES:
        rows.append({
            "id": a["slug"], "nom_affiche": a["nom"], "producteur": a["producteur"], "famille": "aucune",
            "tables_servies": "aucune", "millesime_servi": "", "date_injection": "",
            "cadence_declaree": "aucune", "mode_remplissage": "absente", "job_ingestion": "aucun",
            "cron": "aucun", "sentinelle": "non", "methode_sonde": "aucune", "derniere_sonde": "",
            "dernier_millesime_publie_vu": "", "raison_non_surveillee": "",
            "url_producteur_connue": "", "licence": "DOUTE", "absente_motif": a["motif"], "preuve": a["preuve"],
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    # Compteurs (règle 2 : comptés depuis le fichier livré).
    modes = Counter(x["mode_remplissage"] for x in rows)
    print(f"lignes: {len(rows)}")
    print("par mode:", dict(sorted(modes.items())))
    print("surveillées (vraie sonde):", sum(1 for x in rows if x["sentinelle"] == "oui"),
          "/ non:", sum(1 for x in rows if x["sentinelle"] == "non"))
    print("sans cadence déclarée:", sum(1 for x in rows if x["cadence_declaree"] == "aucune"))
    print("absentes:", modes.get("absente", 0))
    print("avec URL producteur:", sum(1 for x in rows if x["url_producteur_connue"]))
    print("lignes portant DOUTE:", sum(1 for x in rows if "DOUTE" in ";".join(str(v) for v in x.values())))


if __name__ == "__main__":
    main()
