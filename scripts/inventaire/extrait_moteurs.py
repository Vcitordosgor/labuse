#!/usr/bin/env python3
"""CIRCUIT-0 Lot 2 — inventaire des MOTEURS (pompes). Lecture seule.

Chaque ligne est un moteur : un calcul défini une fois qui produit des chiffres servis.
`entrees` = tables lues → ids de réservoirs (reservoirs.csv). `run_lu` :
constante_unique = config/served_run.txt via runs.current() (src/labuse/runs.py:49-61) ;
parametre = run passé en argument (défaut souvent la constante) ; en_dur = valeur figée ;
live = calcul à la lecture, aucun run ; pointeur_propre = pointeur séparé (résiduel).
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire/moteurs.csv"

HEADER = ["id", "nom", "fichier", "fonctions", "entrees", "versionne_par_run", "run_lu", "cache", "preuve"]

M = [
 dict(id="scoring_p_v2", nom="Scoring Potentiel v2 (tiers brûlante→froide)",
      fichier="src/labuse/scoring/p_v2/pipeline.py",
      fonctions="run_score_v2, verify_artifact, rebuild_features",
      entrees="p_model_* → cosia, sitadel, dvf, filosofi_carreaux, bd_topo ; parcel_v_score → bodacc, sirene_etablissements ; dryrun_parcel_evaluations ; parcel_residuel",
      versionne_par_run="oui", run_lu="parametre",
      cache="aucun (artifact gelé sha256, recalage par run)",
      preuve="src/labuse/scoring/p_v2/pipeline.py:78-170 ; tables parcel_p_score_v2 + p_score_v2_runs (9 runs, SELECT 05/09)"),
 dict(id="cascade", nom="Cascade d'exclusion (17 couches, verdict par étage)",
      fichier="src/labuse/cascade/engine.py",
      fonctions="evaluate_parcels, run_cascade",
      entrees="spatial_layers (tous kinds) + parcels → gpu_plu_api_carto, deal_ppr, georisques_*, abf_merimee, znieff_inpn, cinquante_pas_deal, bd_topo, cosia, qpv_2024…",
      versionne_par_run="oui", run_lu="parametre",
      cache="aucun (contexte à la requête)",
      preuve="src/labuse/cascade/__init__.py ; dryrun_cascade_results/dryrun_parcel_evaluations.run_label ; src/labuse/cli.py:534-602"),
 dict(id="residuel", nom="Résiduel de faisabilité (SDP résiduelle, emprise)",
      fichier="src/labuse/faisabilite/residuel.py",
      fonctions="compute_residuel",
      entrees="parcel_bati_revele, spatial_layers(batiment), parcels → cosia, bd_topo, cadastre_api_carto",
      versionne_par_run="oui", run_lu="pointeur_propre (residuel_runs.is_served, run_seq — PAS la constante unique)",
      cache="aucun ; garde anti-écriture au run servi (ServedRunWriteError)",
      preuve="src/labuse/faisabilite/residuel.py:28-80 ; src/labuse/faisabilite/residuel_runs.py:87-117 ; SELECT residuel_runs 05/09 (run_seq 2 « m135-run2-ile » is_served)"),
 dict(id="sector_price", nom="Prix de secteur (DVF fiabilisée €/m²)",
      fichier="src/labuse/faisabilite/bilan.py",
      fonctions="sector_price",
      entrees="dvf_mutations_parcelle, parcels → dvf, cadastre_api_carto",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/faisabilite/bilan.py (MIN_N_SECTEUR=8, rayons 500/1000/1500 m, trim 5 %, indice fiable/fragile/insuffisant)"),
 dict(id="zone", nom="Étude de zone (isochrone + agrégats)",
      fichier="src/labuse/zone.py",
      fonctions="isochrone, population_zone, comptages_zone, etude_de_zone",
      entrees="sirene_etablissements, filosofi_carreaux_200m, dvf_mutations_parcelle, spatial_layers, trafic_rn, pige_biens → sirene_etablissements, filosofi_carreaux, dvf, trafic_rn, bpe_insee, radar_pige",
      versionne_par_run="non", run_lu="live",
      cache="zone_isochrone_cache (table spatiale, clé mode|minutes|lon|lat, sans TTL)",
      preuve="src/labuse/zone.py:1-100 (dégradé honnête : jamais un cercle)"),
 dict(id="marche_pige", nom="Marché Radar (annonces : prix affiché, délais)",
      fichier="src/labuse/pige/marche.py",
      fonctions="stats",
      entrees="pige_biens, pige_faits → radar_pige",
      versionne_par_run="non", run_lu="live",
      cache="aucun (n<5 → NULL + insuffisant=true)",
      preuve="src/labuse/pige/marche.py:15,47-50,71-91"),
 dict(id="rattachement_pige", nom="Rattachement bien→parcelle (GPS→BAN→DPE→morpho)",
      fichier="src/labuse/pige/rattachement.py",
      fonctions="rattacher",
      entrees="parcels, dpe_records, p_model_bati, parcel_equipements → cadastre_api_carto, ban, dpe_ademe, bd_ortho",
      versionne_par_run="non", run_lu="live",
      cache="aucun (MAX_CANDIDATES_ESTIME=3)",
      preuve="src/labuse/pige/rattachement.py:19,70+"),
 dict(id="solaire", nom="Potentiel solaire toiture (PVGIS + azimut bâti)",
      fichier="src/labuse/ingestion/solaire.py",
      fonctions="build_grid, build_solar",
      entrees="solar_grid, spatial_layers(batiment), parcel_vegetation, filosofi_carreaux_200m → pvgis, bd_topo, bd_ortho_irc, filosofi_carreaux",
      versionne_par_run="non", run_lu="en_dur (millésime gelé porté en base, bandeau lu du champ)",
      cache="solar_api_cache (table)",
      preuve="src/labuse/ingestion/solaire.py:18-45 ; table parcel_solar (14 col)"),
 dict(id="score_e", nom="Marge promoteur (score E)",
      fichier="src/labuse/ingestion/score_e.py",
      fonctions="build (CLI score-e)",
      entrees="parcel_p_score_v2, parcel_residuel, dvf_prix_sortie_neuf, dvf_secteur_medianes → dvf, cadastre_api_carto",
      versionne_par_run="oui", run_lu="parametre",
      cache="aucun",
      preuve="src/labuse/ingestion/score_e.py:59 ; src/labuse/cli.py:3494 ; score_e.run_label=q_v11_m137 (SELECT 05/09)"),
 dict(id="renouvellement", nom="Signaux de renouvellement urbain",
      fichier="src/labuse/renouvellement.py",
      fonctions="agrégation des verdicts cascade",
      entrees="dryrun_cascade_results, parcels → (dérivé de cascade)",
      versionne_par_run="oui", run_lu="constante_unique (reconstruit par build-mvt à la bascule)",
      cache="aucun",
      preuve="src/labuse/renouvellement.py ; parcel_renouvellement.run_label=q_v11_m137 (SELECT 05/09) ; dashboard.py:1428-1443"),
 dict(id="division_or", nom="Divisibilité (division d'or)",
      fichier="src/labuse/ingestion/division_or.py",
      fonctions="build (CLI division-or), revue par commune",
      entrees="parcels, bâti (CoSIA), PLU → cadastre_api_carto, cosia, gpu_plu_api_carto",
      versionne_par_run="oui", run_lu="EN RETARD : lignes q_v10_m129 (SELECT 05/09) lues SANS filtre de run (app.py:1573,2696) — workflow de revue toléré par la garde",
      cache="aucun",
      preuve="src/labuse/ingestion/division_or.py:24-30 ; src/labuse/api/app.py:1573,2692-2696 ; src/labuse/bascule_gardes.py:663-665"),
 dict(id="flags", nom="Drapeaux parcelle (tuiles + filtres)",
      fichier="src/labuse/cli.py (build-mvt)",
      fonctions="build_mvt",
      entrees="dryrun_*, spatial_layers, parcel_p_score_v2 → (dérivé cascade + scoring)",
      versionne_par_run="oui", run_lu="constante_unique (reconstruit détaché à la bascule)",
      cache="tuiles MVT (api/tiles.py _CACHE, invalidé par mvt_meta)",
      preuve="src/labuse/api/dashboard.py:1428-1443 ; parcel_flags.run_label=q_v11_m137 ; mvt_meta run_label=q_v11_m137 (SELECT 05/09)"),
 dict(id="plu_destinations", nom="Destinations PLU par zone",
      fichier="src/labuse/plu/destinations.py",
      fonctions="lecture du règlement calibré",
      entrees="parcel_zone_plu, config/plu_*.yaml → gpu_plu_api_carto, sudocuh",
      versionne_par_run="non", run_lu="live",
      cache="lru_cache YAML (config.py:313-326)",
      preuve="src/labuse/plu/destinations.py ; src/labuse/api/moteurs.py:56-124"),
 dict(id="taxe_amenagement", nom="Calculette taxe d'aménagement",
      fichier="src/labuse/taxe_amenagement.py",
      fonctions="calcul ligne-à-ligne (taux communal SAISI, jamais un défaut)",
      entrees="config/taxe_amenagement.yaml (daté) → (constantes réglementaires)",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/taxe_amenagement.py ; config/taxe_amenagement.yaml"),
 dict(id="v_score", nom="Événements propriétaire (score V)",
      fichier="src/labuse/ingestion/score_v_fetch.py",
      fonctions="fetch + build signaux datés",
      entrees="bodacc_*, sirene_etablissements, dvf_mutations → bodacc, sirene_etablissements, dvf",
      versionne_par_run="non", run_lu="live (signaux datés consommés par scoring_p_v2)",
      cache="aucun",
      preuve="src/labuse/ingestion/score_v_fetch.py ; src/labuse/cli.py:2502 ; parcel_v_score"),
 dict(id="marche_communes", nom="Évolution du marché (outil Communes)",
      fichier="src/labuse/marche_service.py",
      fonctions="stats par commune",
      entrees="dvf_mutations_parcelle, dvf_secteur_medianes → dvf",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/marche_service.py"),
 dict(id="bilan_promoteur", nom="Bilan promoteur (faisabilité)",
      fichier="src/labuse/faisabilite/bilan.py",
      fonctions="compute (charge foncière, marge)",
      entrees="sector_price, parcel_residuel, taxe_amenagement → dvf, cadastre_api_carto",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/faisabilite/bilan.py"),
 dict(id="proprietaire_historique", nom="Timeline propriétaire PM (versionné∪servi)",
      fichier="src/labuse/proprietaire_historique.py",
      fonctions="timeline, diff CONSTAT",
      entrees="pm_proprietaires_millesimes, parcelle_personne_morale → dgfip_parcelles_pm",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/proprietaire_historique.py (NOT EXISTS anti-doublon, servi jamais écrasé)"),
 dict(id="cycle_pige", nom="Cycle de vie d'une annonce Radar",
      fichier="src/labuse/pige/cycle.py",
      fonctions="en_vente_longue, a_reverifier, vendue (DVF Sourcé seul), retiree_sans_vente",
      entrees="pige_biens, dvf_mutations_parcelle → radar_pige, dvf",
      versionne_par_run="non", run_lu="live (cron radar-cycle quotidien)",
      cache="aucun",
      preuve="src/labuse/pige/cycle.py ; deploy/cron.d-labuse (30 2 * * *)"),
 dict(id="contexte_parcelle", nom="Contexte de fiche (risques, réseaux, mairie…)",
      fichier="src/labuse/cascade/context.py",
      fonctions="assemblage contexte fiche",
      entrees="spatial_layers (géorisques, ppr, bruit…), mairies, data_sources → georisques_*, deal_ppr, bruit_itt_cerema",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/cascade/context.py:525"),
 dict(id="loyers", nom="Loyers (estimation locative)",
      fichier="src/labuse/loyers.py",
      fonctions="estimation",
      entrees="DOUTE (tables lues à confirmer)",
      versionne_par_run="non", run_lu="live",
      cache="aucun",
      preuve="src/labuse/loyers.py (DOUTE sur les entrées exactes)"),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(M)
    v = Counter(m["versionne_par_run"] for m in M)
    print(f"moteurs: {len(M)} | versionnés par run: {v['oui']} | live: {v['non']}")
    print("DOUTE:", sum(1 for m in M if "DOUTE" in ";".join(m.values())))


if __name__ == "__main__":
    main()
