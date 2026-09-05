#!/usr/bin/env python3
"""CIRCUIT-0 Lot 5 — le registre des CHIFFRES : une ligne par couple (robinet, chiffre).

Règle 5 du mandat : un chiffre = un id — le même id quand le même chiffre (même sens) sort
à plusieurs robinets, même par des chemins différents (c'est ce qui fait les fuites).
`fuites_candidates.csv` est DÉRIVÉ de ce fichier par groupby (chiffre_id servi par ≥ 2
robinets avec ≥ 2 `fichier_ligne` distincts).

Sources de chaque ligne : lecture du code (preuve = fichier_ligne) — les libellés viennent
des composants front cités, les producteurs du back. Les lignes incertaines portent DOUTE.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

INV = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire"
OUT = INV / "chiffres.csv"
OUT_FUITES = INV / "fuites_candidates.csv"

HEADER = ["robinet_id", "chiffre_id", "libelle_affiche", "unite", "niveau", "calcul",
          "fichier_ligne", "reservoirs_lus", "run_lu", "cache", "tampon", "definition_lue", "preuve"]

RUN = "q_v11_m137 (constante_unique)"

ROWS: list[dict] = []


def L(robinet: str, *chiffres) -> None:
    """chiffres = tuples (chiffre_id, libelle, unite, niveau, calcul, fichier_ligne,
    reservoirs, run_lu, cache, tampon, definition)."""
    for (cid, lib, unite, niveau, calc, fl, res, run, cache, tampon, defn) in chiffres:
        ROWS.append({"robinet_id": robinet, "chiffre_id": cid, "libelle_affiche": lib,
                     "unite": unite, "niveau": niveau, "calcul": calc, "fichier_ligne": fl,
                     "reservoirs_lus": res, "run_lu": run, "cache": cache, "tampon": tampon,
                     "definition_lue": defn, "preuve": fl})


# ── COUCHES (les couches qui portent une classe/tranche affichée) ─────────────────────
L("couche_verdict",
  ("tier_opportunite", "Verdict · Classement servi", "classe", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/cli.py (build-mvt) ; parcel_flags", "cosia,sitadel,dvf,filosofi_carreaux,bd_topo", RUN,
   "tuiles MVT (api/tiles.py, invalidé mvt_meta)", "run",
   "tier du run servi (brûlante→froide), reconstruit à la bascule"))
L("couche_zonage_plu",
  ("zone_plu_famille", "Zonage PLU (par type)", "classe", "parcelle", "passe_plat",
   "src/labuse/api/app.py:map_layers_geojson (parcel_zone_plu)", "gpu_plu_api_carto", "live",
   "aucun", "rien", "famille de zone (U/AU/A/N) portée par parcel_zone_plu, une zone par parcelle"))
L("couche_vefa",
  ("tranche_prix_vefa", "Prix du logement neuf (VEFA)", "tranche", "commune", "moteur:marche_communes",
   "src/labuse/ingestion/vefa_neuf.py:118", "dvf,sitadel", "live", "spatial_layers (précalcul couche)", "rien",
   "tranche de prix médian VEFA 36 mois glissants, ≥10 ventes avec prix sinon hachure"))
L("couche_densifier",
  ("classe_residuel", "Densifier l'existant", "classe", "parcelle", "moteur:residuel",
   "src/labuse/faisabilite/residuel.py:80", "cosia,bd_topo,cadastre_api_carto",
   "residuel_runs.is_served (pointeur propre)", "aucun", "rien",
   "classe de sous-densité issue de la vue parcel_residuel (run résiduel servi)"))

# ── OUTILS ────────────────────────────────────────────────────────────────────────────
L("outil_etudier_bien",
  ("tier_opportunite", "Verdict (tier)", "classe", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/api/modules.py:scoreur_adresse", "cosia,sitadel,dvf", RUN, "aucun", "rien",
   "tier lu de parcel_p_score_v2 au run servi"),
  ("surface_parcelle_m2", "Surface", "m²", "parcelle", "passe_plat",
   "src/labuse/api/modules.py:scoreur_adresse", "cadastre_api_carto", "live", "aucun", "rien",
   "surface cadastrale parcels.surface_m2"))
L("outil_faisabilite",
  ("capacite_logements", "Capacité (logements)", "logements", "parcelle", "moteur:residuel",
   "src/labuse/api/modules.py:faisabilite_sens1", "gpu_plu_api_carto,cosia,bd_topo",
   "residuel_runs.is_served", "aucun", "rien", "capacité estimée depuis SDP résiduelle / taille moyenne logement"),
  ("sdp_residuelle_m2", "SDP résiduelle", "m²", "parcelle", "moteur:residuel",
   "src/labuse/faisabilite/residuel.py:80", "gpu_plu_api_carto,cosia", "residuel_runs.is_served",
   "aucun", "rien", "max(0, SDP_max − SDP_existante)"),
  ("charge_fonciere_eur", "Charge foncière", "€", "parcelle", "moteur:bilan_promoteur",
   "src/labuse/faisabilite/bilan.py", "dvf,cadastre_api_carto", "live", "aucun", "rien",
   "prix de sortie × SDP − coûts − marge (bilan à rebours)"))
L("outil_taxe_amenagement",
  ("taxe_amenagement_eur", "Taxe d'aménagement", "€", "parcelle", "moteur:taxe_amenagement",
   "src/labuse/taxe_amenagement.py", "(barème config daté)", "live", "aucun", "date",
   "calcul ligne-à-ligne, taux communal SAISI obligatoire, jamais un défaut"))
L("outil_pieges",
  ("n_vigilances", "Vigilances", "nombre", "parcelle", "moteur:cascade",
   "src/labuse/api/modules.py:risques_audit", "georisques_api,deal_ppr,abf_merimee,znieff_inpn", RUN,
   "aucun", "rien", "compte des couches cascade en SOFT_FLAG/HARD_EXCLUDE"))
L("outil_plu",
  ("n_extraits_plu", "extraits (règlement)", "nombre", "commune", "sql_propre",
   "src/labuse/api/modules.py:1893-1952", "gpu_plu_api_carto,sudocuh", "live", "aucun", "rien",
   "extraits de règlement servis par commune (corpus)"),
  ("n_communes_rnu", "au RNU", "nombre", "global", "sql_propre",
   "src/labuse/api/modules.py:1942", "sudocuh", "live", "aucun", "rien",
   "communes au statut rnu du corpus (registre config/rnu_communes.yaml)"))
L("outil_plu_simuler",
  ("simulplu_resultat", "Simuler un changement (parcelles gagnées)", "nombre", "commune", "moteur:cascade",
   "src/labuse/api/moteurs.py:56-124", "gpu_plu_api_carto", RUN, "aucun", "rien",
   "re-verdict cascade sous zonage hypothétique (dryrun)"))
L("outil_comparer_parcelles",
  ("comparateur_composite", "Score composite", "nombre", "commune", "sql_propre",
   "src/labuse/api/comparateur.py:88-118", "dvf,sitadel,cosia", RUN, "mémoïsé (raw_rows)", "rien",
   "moyenne pondérée min-max des 6 axes présents, poids réglables"),
  ("stock_opportunites", "Stock d'opportunités (brûlantes + chaudes)", "nombre", "commune", "moteur:scoring_p_v2",
   "src/labuse/api/comparateur.py:47-50", "cosia,sitadel,dvf", RUN, "mémoïsé", "rien",
   "count tiers brûlante+chaude au run servi, par insee"),
  ("velocite_delai_median_mois", "Vélocité admin (délai médian dépôt→autorisation, mois)", "nombre", "commune", "sql_propre",
   "src/labuse/api/comparateur.py:51-53", "sitadel", "live", "mémoïsé", "rien",
   "percentile_cont(0.5) sur m10_permit_delais famille logements"),
  ("permis_5a_n", "Dynamisme permis (SITADEL, 5 ans)", "nombre", "commune", "sql_propre",
   "src/labuse/api/comparateur.py:54-56", "sitadel", "live", "mémoïsé", "rien",
   "count sitadel_permits date ≥ now−5 ans"),
  ("deficit_sru_pts", "Déficit SRU (objectif − taux LLS, points)", "nombre", "commune", "passe_plat",
   "src/labuse/api/comparateur.py:56", "sru_dhup", "live", "mémoïsé", "rien",
   "greatest(objectif_pct − taux_lls, 0) depuis commune_contexte_sru"),
  ("pression_zan_ha", "Pression ZAN (ENAF consommé 2021-2024, ha)", "nombre", "commune", "passe_plat",
   "src/labuse/api/comparateur.py:57", "(commune_conso_enaf — réservoir Cerema ENAF, hors catalogue)", "live",
   "mémoïsé", "rien", "conso_2021_2024_m2 / 10000"),
  ("prix_neuf_vefa_eur_m2", "Prix de sortie neuf VEFA (DVF, €/m²)", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/api/comparateur.py:139-141 (neuf_vefa_commune LIVE — RETOURS-11F M1)", "dvf", "live",
   "mémoïsé", "rien", "médiane VEFA live, MÊME moteur que fiche et carte (divergence précalc corrigée)"),
  ("prix_ancien_median_eur_m2", "€/m² ancien", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/api/moteurs.py:prix_ancien_communes (partagé PDF baromètre)", "dvf", "live", "mémoïsé", "rien",
   "médiane DVF ventes strictes, filtre de retenue du baromètre"))
L("outil_scan_patrimoine",
  ("n_parcelles_pm", "Parcelles détenues", "nombre", "proprietaire", "sql_propre",
   "src/labuse/api/modules.py:patrimoine", "dgfip_parcelles_pm", "live", "aucun", "millesime",
   "count parcelle_personne_morale par SIREN (millésime 2025)"))
L("outil_prospection_solaire",
  ("prod_spec_kwh_kwc", "Productible", "nombre", "parcelle", "moteur:solaire",
   "src/labuse/api/modules.py:prospection_solaire", "pvgis,bd_topo", "en_dur (millésime gelé)",
   "aucun", "millesime", "productible PVGIS SARAH3 gelé au run du builder (parcel_solar)"),
  ("azimut_bati_deg", "Azimut (Estimé)", "nombre", "parcelle", "moteur:solaire",
   "src/labuse/ingestion/solaire.py (ST_OrientedEnvelope)", "bd_topo", "en_dur", "aucun", "millesime",
   "azimut du bâti principal, Estimé"))
L("outil_solaire_piscines",
  ("n_piscines", "Piscines détectées", "nombre", "commune", "sql_propre",
   "src/labuse/api/modules.py:prospection_piscines", "bd_ortho", "live", "aucun", "millesime",
   "count parcel_equipements piscine (BD ORTHO 2025, ~90,7 %)"))
L("outil_communes_evolution",
  ("prix_ancien_median_eur_m2", "€/m² ancien (baromètre)", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/api/moteurs.py:barometres", "dvf", "live", "aucun", "rien",
   "même fonction prix_ancien_communes que comparateur et PDF"),
  ("mutations_12m_n", "Mutations 12 mois", "nombre", "commune", "sql_propre",
   "src/labuse/api/app.py:1934-1940", "dvf", "live", "aucun", "rien",
   "count dvf_mutations sur les 12 derniers mois DE DONNÉES (pas calendaire)"))
L("outil_communes_acquisitions",
  ("acquisitions_pm_n", "Acquisitions récentes (PM)", "nombre", "commune", "moteur:proprietaire_historique",
   "src/labuse/api/app.py:commune_acquisitions_pm", "dgfip_parcelles_pm", "live", "aucun", "millesime",
   "diff CONSTAT entre millésimes PM, maille commune"))
L("outil_permis",
  ("permis_12m_n", "Permis (12 mois)", "nombre", "commune", "sql_propre",
   "src/labuse/api/modules.py:permis", "sitadel", "live", "aucun", "rien",
   "count sitadel_permits fenêtre 12 mois"),
  ("velocite_delai_median_mois", "Délai médian", "nombre", "commune", "sql_propre",
   "src/labuse/api/modules.py:velocite", "sitadel", "live", "aucun", "rien",
   "même percentile m10_permit_delais (source unique velocite())"))
L("outil_permis_point_mort",
  ("point_mort_n", "Permis au point mort", "nombre", "commune", "sql_propre",
   "src/labuse/api/modules.py:promesses", "sitadel", "live", "aucun", "rien",
   "permis autorisés sans DOC/DAACT dans la fenêtre"))
L("outil_densifier",
  ("n_densifiables", "Parcelles densifiables", "nombre", "commune", "moteur:renouvellement",
   "src/labuse/api/modules.py:renouvellement", "(dérivé cascade)", RUN, "aucun", "run",
   "count parcel_renouvellement au run servi"),
  ("sdp_residuelle_m2", "SDP résiduelle (commune)", "m²", "commune", "moteur:residuel",
   "src/labuse/api/modules.py:renouvellement", "gpu_plu_api_carto,cosia", "residuel_runs.is_served",
   "aucun", "rien", "somme des SDP résiduelles des parcelles densifiables"))
L("outil_etude_zone",
  ("population_zone", "Habitants (zone)", "nombre", "zone", "moteur:zone",
   "src/labuse/zone.py (population_zone — point Filosofi UNIQUE)", "filosofi_carreaux", "live",
   "zone_isochrone_cache (sans TTL)", "rien", "somme carreaux Filosofi 200 m intersectant l'isochrone"),
  ("n_concurrents_zone", "Concurrents (NAF)", "nombre", "zone", "moteur:zone",
   "src/labuse/zone.py (comptages_zone)", "sirene_etablissements", "live", "aucun", "rien",
   "count sirene_etablissements du NAF choisi dans la zone, chacun avec son temps"),
  ("emplois_fourchette", "Emplois (fourchette)", "tranche", "zone", "moteur:zone",
   "src/labuse/zone.py", "sirene_etablissements", "live", "aucun", "rien",
   "somme des tranches d'effectifs SIRENE (jamais un point)"),
  ("revenu_approche_eur", "Revenu (valeur approchée)", "€", "zone", "moteur:zone",
   "src/labuse/zone.py", "filosofi_carreaux", "live", "aucun", "rien",
   "niveau de vie approché N/M carreaux couverts (i_est_200)"),
  ("trafic_mja", "Trafic (MJA)", "nombre", "zone", "passe_plat",
   "src/labuse/zone.py", "trafic_rn", "live", "aucun", "millesime",
   "comptage MJA du tronçon RN le plus proche, millésime porté par tronçon"))
L("outil_radar_marche",
  ("annonces_actives_n", "Biens en vente", "nombre", "commune", "moteur:marche_pige",
   "src/labuse/pige/marche.py:71-91", "radar_pige", "live", "aucun", "rien",
   "count pige_biens actifs a_qualifier=false ; n<5 → NULL insuffisant"),
  ("prix_demande_median_eur_m2", "Prix demandé (médiane)", "€/m²", "commune", "moteur:marche_pige",
   "src/labuse/pige/marche.py:71-91", "radar_pige", "live", "aucun", "rien",
   "médiane des prix affichés terrain/bâti, n<5 masqué"),
  ("delai_vente_median_j", "Délai médian", "nombre", "commune", "moteur:marche_pige",
   "src/labuse/pige/marche.py", "radar_pige", "live", "aucun", "rien",
   "médiane 1re vue → retrait/vente"),
  ("ecart_demande_acte_pct", "Écart demandé/acté", "%", "commune", "moteur:marche_pige",
   "src/labuse/api/fiche_commune.py:16-58 (comparable, partagé)", "radar_pige,dvf", "live", "aucun", "rien",
   "médiane demandé vs médiane DVF actée, servi dès SEUIL_N biens"))

# ── FICHE PARCELLE ────────────────────────────────────────────────────────────────────
L("fiche_parcelle_score",
  ("tier_opportunite", "Score d'opportunité (tier)", "classe", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/api/app.py:3283 (_q_v2_fiche)", "cosia,sitadel,dvf,filosofi_carreaux", RUN, "aucun", "rien",
   "tier + rang lus de parcel_p_score_v2 au run servi, jamais recalculés"),
  ("rang_tier", "Rang (dans le tier)", "nombre", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/api/app.py:3283", "(idem scoring)", RUN, "aucun", "rien", "rang au sein du tier"))
L("fiche_parcelle_constructibilite",
  ("capacite_logements", "Capacité (logements)", "logements", "parcelle", "moteur:residuel",
   "src/labuse/api/app.py:3283", "gpu_plu_api_carto,cosia", "residuel_runs.is_served", "aucun", "rien",
   "fourchette de capacité depuis le résiduel servi"),
  ("sdp_residuelle_m2", "SDP résiduelle", "m²", "parcelle", "moteur:residuel",
   "src/labuse/api/app.py:3283", "gpu_plu_api_carto,cosia", "residuel_runs.is_served", "aucun", "rien",
   "même valeur que l'outil Faisabilité (vue parcel_residuel)"),
  ("charge_fonciere_eur", "Calculette de charge foncière", "€", "parcelle", "front",
   "frontend/src/components/fiche/constructibilite.tsx:19-93", "dvf", "live", "aucun", "rien",
   "CALCULÉE AU FRONT depuis prix de sortie serveur + curseurs utilisateur (Q5.4)"))
L("fiche_parcelle_risques",
  ("n_vigilances", "Vigilances", "nombre", "parcelle", "front",
   "frontend/src/components/fiche/risques.tsx:16-30", "georisques_api,deal_ppr", RUN, "aucun", "rien",
   "COMPTAGE AU FRONT des lignes cascade SOFT_FLAG/HARD_EXCLUDE (Q5.4)"))
L("fiche_parcelle_marche",
  ("prix_terrain_secteur_eur_m2", "Terrain nu secteur", "€/m²", "parcelle", "moteur:sector_price",
   "src/labuse/faisabilite/bilan.py (sector_price)", "dvf,cadastre_api_carto", "live", "aucun", "rien",
   "médiane DVF rayon adaptatif 500→1500 m, trim 5 %, min 8 ventes, indice fiabilité"),
  ("prix_sortie_bati_eur_m2", "Prix de sortie — bâti secteur", "€/m²", "parcelle", "moteur:sector_price",
   "frontend/src/components/fiche/marche.tsx:19-90", "dvf", "live", "aucun", "rien",
   "médiane bâti secteur + tendance calculées côté front sur ventes serveur (Q5.4)"),
  ("prix_neuf_vefa_eur_m2", "Neuf (VEFA) — commune", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/api/app.py:3283 (neuf_vefa_commune)", "dvf", "live", "aucun", "rien",
   "même moteur live que comparateur/carte (RETOURS-11F M1)"),
  ("ventes_100m_n", "Ventes à moins de 100 m", "nombre", "parcelle", "sql_propre",
   "src/labuse/api/app.py:3283 (dvf_parcelle)", "dvf", "live", "aucun", "rien",
   "count mutations à <100 m + médiane"))
L("fiche_parcelle_reseaux",
  ("pente_deg", "Pente", "nombre", "parcelle", "passe_plat",
   "src/labuse/api/app.py:3283 (viabilisation)", "rge_alti", "live", "aucun", "rien",
   "pente moyenne parcelle (RGE ALTI), flag terrassement"),
  ("piscine_m2", "Piscine ~m²", "m²", "parcelle", "passe_plat",
   "src/labuse/api/app.py:3283", "bd_ortho", "live", "aucun", "millesime",
   "surface détectée parcel_equipements (BD ORTHO 2025)"),
  ("distance_arret_m", "Transport public — au plus proche", "m", "parcelle", "sql_propre",
   "src/labuse/api/app.py:3283 (proximites)", "gtfs_pan,osm_transport", "live", "aucun", "rien",
   "plus proche arrêt/pôle (distance en m)"))
L("fiche_parcelle_autour",
  ("population_zone", "Habitants (autour)", "nombre", "zone", "moteur:zone",
   "src/labuse/api/app.py:4265 (parcel_zone)", "filosofi_carreaux", "live",
   "zone_isochrone_cache", "rien", "même point Filosofi unique que l'Étude de zone"),
  ("n_permis_proximite", "Permis à proximité", "nombre", "parcelle", "sql_propre",
   "src/labuse/api/app.py:3283", "sitadel", "live", "aucun", "rien",
   "permis Sitadel dans le rayon, avec distance et date"),
  ("depots_secteur_n", "Déposés/autorisés (Sitadel)", "nombre", "zone", "sql_propre",
   "src/labuse/api/app.py:3283", "sitadel", "live", "aucun", "rien",
   "activité de dépôt par année dans le secteur"))
L("fiche_parcelle_proprietaire",
  ("type_proprietaire", "Propriétaire (type)", "classe", "proprietaire", "passe_plat",
   "src/labuse/api/app.py:3283 (proprietaire_moral)", "dgfip_parcelles_pm", "live", "aucun", "millesime",
   "personne morale (dénomination) / personne physique non recensée — millésime 2025"))
L("fiche_parcelle_confiance",
  ("verdict_icd", "Confiance données", "verdict", "parcelle", "moteur:cascade",
   "src/labuse/api/app.py:3283 (bloc icd)", "(couverture des couches)", RUN, "aucun", "rien",
   "verdict de complétude des couches + liste des manquants"))
L("fiche_parcelle_solaire",
  ("prod_spec_kwh_kwc", "Productible (fiche)", "nombre", "parcelle", "moteur:solaire",
   "table parcel_solar (14 col)", "pvgis", "en_dur", "aucun", "millesime",
   "même valeur gelée que l'outil Prospection solaire"))
L("fiche_parcelle_division",
  ("divisible_classe", "Division (candidate)", "classe", "parcelle", "moteur:division_or",
   "src/labuse/api/app.py:2692-2696", "cadastre_api_carto,cosia,gpu_plu_api_carto",
   "q_v10_m129 (EN RETARD, lu sans filtre de run)", "aucun", "rien",
   "présence dans division_or_candidates — run figé q_v10, workflow de revue"))

# ── FICHE COMMUNE (cartes) ────────────────────────────────────────────────────────────
L("fiche_commune_regles_urbanisme",
  ("statut_plu", "Règles d'urbanisme (statut)", "classe", "commune", "moteur:plu_destinations",
   "src/labuse/api/fiche_commune.py:137-144", "sudocuh,gpu_plu_api_carto", "live",
   "fiche-commune-cache (nocturne)", "date", "RNU (registre) l'emporte ; sinon statut du registre veille_plu"))
L("fiche_commune_zan",
  ("zan_reste_ha", "Enveloppe ZAN (reste)", "nombre", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py (rarete)", "(commune_conso_enaf)", "live", "fiche-commune-cache", "date",
   "enveloppe restante estimée depuis conso ENAF"))
L("fiche_commune_sru",
  ("taux_lls_pct", "Taux LLS", "%", "commune", "passe_plat",
   "src/labuse/api/fiche_commune.py (commune_contexte_sru)", "sru_dhup", "live", "fiche-commune-cache", "date",
   "taux LLS de l'inventaire SRU"),
  ("deficit_sru_pts", "Déficit SRU", "nombre", "commune", "passe_plat",
   "src/labuse/api/fiche_commune.py", "sru_dhup", "live", "fiche-commune-cache", "date",
   "même définition que le comparateur (objectif − taux)"))
L("fiche_commune_permis",
  ("permis_12m_n", "Permis 12 mois", "nombre", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py (permis_bloc)", "sitadel", "live", "fiche-commune-cache", "date",
   "count Sitadel 12 mois — partagé via raw_rows avec le comparateur"),
  ("velocite_delai_median_mois", "Délai médian (mois)", "nombre", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py", "sitadel", "live", "fiche-commune-cache", "date",
   "même velocite() que l'outil Permis"),
  ("point_mort_n", "Point mort", "nombre", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py", "sitadel", "live", "fiche-commune-cache", "date",
   "même définition que l'outil Permis au point mort"))
L("fiche_commune_plh",
  ("plh_objectif_logements_an", "Objectif logements/an", "logements", "commune", "passe_plat",
   "src/labuse/api/fiche_commune.py (plh_epci)", "plh_epci", "live", "fiche-commune-cache", "date",
   "objectif PLH, chaque chiffre porte sa référence doc+page"))
L("fiche_commune_prix",
  ("prix_ancien_median_eur_m2", "Ancien médian", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/api/fiche_commune.py:16-58 (comparable → raw_rows)", "dvf", "live", "fiche-commune-cache", "date",
   "MÊME source que comparateur et baromètre (prix_ancien_communes)"),
  ("prix_neuf_vefa_eur_m2", "Neuf", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/api/fiche_commune.py:16-58", "dvf", "live", "fiche-commune-cache", "date",
   "même moteur live neuf_vefa_commune"),
  ("mutations_12m_n", "Mutations 12 m", "nombre", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py", "dvf", "live", "fiche-commune-cache", "date",
   "même fenêtre 12 mois de données que _foncier_commune"))
L("fiche_commune_terrain_nu",
  ("prix_terrain_zone_eur_m2", "Terrain nu (zone U / AU)", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/faisabilite/marche_commune.py (ligne2_terrain_zone)", "dvf,gpu_plu_api_carto", "live",
   "fiche-commune-cache", "date", "médiane DVF terrain nu par famille de zone, seuil 10 ventes"))
L("fiche_commune_annonces",
  ("annonces_actives_n", "Biens en vente (Radar)", "nombre", "commune", "moteur:marche_pige",
   "src/labuse/api/fiche_commune.py (marche_annonces → pige.marche.stats)", "radar_pige", "live",
   "fiche-commune-cache", "date", "même stats() que l'onglet Marché Radar"),
  ("prix_demande_median_eur_m2", "Prix demandé médian", "€/m²", "commune", "moteur:marche_pige",
   "src/labuse/api/fiche_commune.py", "radar_pige", "live", "fiche-commune-cache", "date", "même stats()"),
  ("ecart_demande_acte_pct", "Écart demandé/acté", "%", "commune", "moteur:marche_pige",
   "src/labuse/api/fiche_commune.py:16-58", "radar_pige,dvf", "live", "fiche-commune-cache", "date",
   "défini une fois dans comparable(), servi fiche + comparateur"))
L("fiche_commune_loyers",
  ("loyer_median_eur_m2", "Loyer médian", "€/m²", "commune", "moteur:loyers",
   "src/labuse/api/fiche_commune.py (loyer)", "DOUTE (entrées loyers.py)", "live", "fiche-commune-cache", "date",
   "estimation locative loyers.py — entrées à confirmer (DOUTE)"))
L("fiche_commune_foncier",
  ("n_parcelles_commune", "N parcelles", "nombre", "commune", "sql_propre",
   "src/labuse/api/app.py:1905", "cadastre_api_carto", "live", "fiche-commune-cache", "date",
   "count parcels par commune"),
  ("stock_opportunites", "Stock opportunités", "nombre", "commune", "moteur:scoring_p_v2",
   "src/labuse/api/app.py:1944-1948", "cosia,sitadel,dvf", RUN, "fiche-commune-cache", "date",
   "MÊME définition et même run que la colonne stock du comparateur (commentaire OUTILS-6 C2)"),
  ("n_densifiables", "Densifiables", "nombre", "commune", "moteur:renouvellement",
   "src/labuse/api/fiche_commune.py", "(dérivé cascade)", RUN, "fiche-commune-cache", "date",
   "même compte que l'outil Densifier"))
L("fiche_commune_zonage",
  ("part_zone_U_pct", "Zonage — U", "%", "commune", "sql_propre",
   "src/labuse/api/app.py:1908-1955 (_foncier_commune, PART DE SURFACE)", "gpu_plu_api_carto,cadastre_api_carto",
   "live", "fiche-commune-cache", "date", "surface cadastrée U / surface zonée totale (somme=100 %)"),
  ("part_zone_AU_pct", "Zonage — AU", "%", "commune", "sql_propre",
   "src/labuse/api/app.py:1908-1955", "gpu_plu_api_carto,cadastre_api_carto", "live", "fiche-commune-cache",
   "date", "surface AU / surface zonée"),
  ("part_zone_A_pct", "Zonage — A", "%", "commune", "sql_propre",
   "src/labuse/api/app.py:1908-1955", "gpu_plu_api_carto,cadastre_api_carto", "live", "fiche-commune-cache",
   "date", "surface A / surface zonée (Saint-Paul : 35,8 % — la part en PARCELLES vaut 17,8 %)"),
  ("part_zone_N_pct", "Zonage — N", "%", "commune", "sql_propre",
   "src/labuse/api/app.py:1908-1955", "gpu_plu_api_carto,cadastre_api_carto", "live", "fiche-commune-cache",
   "date", "surface N / surface zonée (Saint-Paul : 47,2 % — la part en PARCELLES vaut 6,8 %)"))
L("fiche_commune_risques",
  ("ppr_pct", "PPR (part des parcelles)", "%", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py:66-88 (_pct_layer)", "deal_ppr", "live", "fiche-commune-cache", "date",
   "part des parcelles de la commune intersectant la couche ppr"),
  ("catnat_n", "Arrêtés CatNat", "nombre", "commune", "passe_plat",
   "src/labuse/api/fiche_commune.py", "(catnat_arretes)", "live", "fiche-commune-cache", "date",
   "count catnat_arretes"))
L("fiche_commune_population",
  ("habitants_n", "Habitants", "nombre", "commune", "passe_plat",
   "src/labuse/api/fiche_commune.py:123 (population)", "filosofi_carreaux,insee_rp_logement", "live",
   "fiche-commune-cache", "date", "population INSEE/Filosofi commune"),
  ("vacance_pct", "Vacance", "%", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py:123", "insee_rp_logement", "live", "fiche-commune-cache", "date",
   "100 × vacants / logements (RP)"))
L("fiche_commune_qpv",
  ("qpv_n", "QPV", "nombre", "commune", "sql_propre",
   "src/labuse/api/fiche_commune.py", "qpv_2024", "live", "fiche-commune-cache", "date",
   "count QPV intersectant la commune"))

# ── AUTRES FICHES ─────────────────────────────────────────────────────────────────────
L("fiche_annonce",
  ("prix_demande_eur", "Prix demandé", "€", "annonce", "passe_plat",
   "src/labuse/pige/client.py", "radar_pige", "live", "aucun", "date",
   "fait déclaré de l'annonce (pige_faits), jamais le texte"),
  ("prix_demande_median_eur_m2", "Prix demandé €/m² (contexte)", "€/m²", "commune", "moteur:marche_pige",
   "src/labuse/pige/client.py", "radar_pige", "live", "aucun", "rien", "contexte marché de la fiche bien"))
L("fiche_proprietaire",
  ("n_parcelles_pm", "Parcelles détenues (timeline)", "nombre", "proprietaire", "moteur:proprietaire_historique",
   "src/labuse/proprietaire_historique.py", "dgfip_parcelles_pm", "live", "aucun", "millesime",
   "timeline versionné∪servi, anti-doublon NOT EXISTS"))
L("fiche_soleil",
  ("prod_spec_kwh_kwc", "Productible (fiche soleil)", "nombre", "parcelle", "moteur:solaire",
   "table parcel_solar + toiture_lidar", "pvgis,lidar_hd_mnh", "en_dur", "aucun", "millesime",
   "même valeur gelée, rosace + photo du toit"))

# ── COPILOTE ─────────────────────────────────────────────────────────────────────────
L("copilote_compter_parcelles",
  ("copilote_compte_parcelles", "Compte de parcelles (réponse)", "nombre", "global", "sql_propre",
   "src/labuse/copilote_v2/outils.py:130-219", "cadastre_api_carto", RUN, "aucun", "rien",
   "MÊME facette canonique que le filtre écran (égalité verrouillée)"))
L("copilote_compter_permis",
  ("permis_12m_n", "Nombre de permis accordés", "nombre", "commune", "sql_propre",
   "src/labuse/copilote_v2/outils.py:550-567", "sitadel", "live", "aucun", "rien",
   "même endpoint permis() que l'outil (fenêtre 24 mois par défaut)"))
L("copilote_parcelles_entreprise",
  ("n_parcelles_pm", "Parcelles détenues par une personne morale", "nombre", "proprietaire", "sql_propre",
   "src/labuse/copilote_v2/outils.py:279-325", "dgfip_parcelles_pm", "live", "aucun", "millesime",
   "même patrimoine() que Scan patrimoine"))
L("copilote_fiche_parcelle",
  ("surface_parcelle_m2", "Surface (réponse)", "m²", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/copilote_v2/outils.py:333-345", "cadastre_api_carto", RUN, "aucun", "rien",
   "_q_v2_fiche LU du run servi, jamais recalculé"))
L("copilote_stats_commune",
  ("taux_lls_pct", "Taux LLS (réponse)", "%", "commune", "sql_propre",
   "src/labuse/copilote_v2/outils.py:350-365", "sru_dhup,insee_rp_logement", "live", "aucun", "rien",
   "même commune_contexte() que la fiche commune"))
L("copilote_delais_instruction",
  ("velocite_delai_median_mois", "Délai médian d'instruction (réponse)", "nombre", "commune", "sql_propre",
   "src/labuse/copilote_v2/outils.py:370-389", "sitadel", "live", "aucun", "rien",
   "même velocite(), réserve Sitadel citée mot pour mot"))
L("copilote_marche",
  ("prix_ancien_median_eur_m2", "Marché d'une commune (réponse)", "€/m²", "commune", "moteur:marche_communes",
   "src/labuse/copilote_v2/outils.py:395-418", "dvf", "live", "aucun", "rien",
   "build_marche_commune — point de calcul unique"))
L("copilote_compter_piscines",
  ("n_piscines", "Piscines détectées (réponse)", "nombre", "commune", "sql_propre",
   "src/labuse/copilote_v2/outils.py:529-545", "bd_ortho", "live", "aucun", "millesime",
   "même prospection_piscines() que l'outil"))
L("copilote_destination_zone",
  ("destination_statut", "Peut-on ouvrir une activité ? (verdict)", "verdict", "parcelle", "moteur:plu_destinations",
   "src/labuse/copilote_v2/outils.py:573-599", "gpu_plu_api_carto,sudocuh", "live", "aucun", "rien",
   "MÊME moteur plu.destinations que fiche et étude de zone"))

# ── VEILLE / PROJETS / CRM ───────────────────────────────────────────────────────────
L("veille_evaluations",
  ("n_veilles", "Veilles actives", "nombre", "global", "sql_propre",
   "src/labuse/copilote_v2/veilles.py:82-88", "(veilles)", "live", "aucun", "rien", "count veilles du compte"))
L("projets_liste",
  ("projet_cadrage_n", "Parcelles (cadrage)", "nombre", "global", "sql_propre",
   "src/labuse/api/projets.py:606-640", "(projet_parcelles)", RUN, "aucun", "rien",
   "count parcelles du projet"),
  ("projet_retenues_n", "Retenues", "nombre", "global", "sql_propre",
   "src/labuse/api/projets.py:606-640", "(projet_parcelles)", RUN, "aucun", "rien", "count retenues"))
L("projets_compteur",
  ("projet_cadrage_n", "Compteur projet (bandeau)", "nombre", "global", "sql_propre",
   "src/labuse/api/projets.py:488-510", "(projet_parcelles)", RUN, "_COMPTEUR_CACHE 600 s", "rien",
   "mêmes comptes, cache mémoire 600 s"))
L("crm_kanban",
  ("crm_cartes_n", "Cartes par colonne", "nombre", "global", "sql_propre",
   "src/labuse/api/crm_columns.py:34", "(pipeline_entries)", "live", "aucun", "rien", "count par colonne"))

# ── NOTIFICATIONS ────────────────────────────────────────────────────────────────────
L("notif_cloche",
  ("n_notifications", "Notifications non lues", "nombre", "global", "sql_propre",
   "src/labuse/api/events.py:696", "(event_log)", "live", "aucun", "rien", "count event_log non lus du compte"))
L("notif_brief_matin",
  ("n_bascules_7j", "Bascules (7 jours)", "nombre", "global", "sql_propre",
   "src/labuse/api/events.py:1086-1153", "(event_log)", RUN, "aucun", "rien",
   "bascules de tier détectées vs run précédent"))
L("notif_digest_quotidien",
  ("n_biens_du_jour", "Biens du jour (digest)", "nombre", "global", "moteur:marche_pige",
   "src/labuse/api/events.py:1160-1216", "radar_pige", "live", "dédup event_log", "date",
   "biens validés du jour, cartes HTML plafond 10 + « et N autres »"))
L("notif_radar_digest",
  ("n_biens_du_jour", "NB_BIENS (Brevo 12)", "nombre", "global", "moteur:marche_pige",
   "src/labuse/pige/digests.py:278-296", "radar_pige", "live", "dédup event_log", "date",
   "len(biens) du jour — paramètre nommé du template, aucun calcul dans Brevo"))
L("notif_radar_alerte",
  ("n_biens_veille", "NB_BIENS (Brevo 13)", "nombre", "global", "moteur:marche_pige",
   "src/labuse/pige/digests.py:303-313", "radar_pige", "live", "dédup event_log", "date",
   "len(matches) de LA veille — un mail par veille"))

# ── PDF ──────────────────────────────────────────────────────────────────────────────
L("pdf_flash",
  ("tier_opportunite", "Verdict (Flash)", "classe", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/flash/data.py (collect_report_data)", "cosia,sitadel,dvf", RUN, "aucun", "run",
   "verdict lu du run servi, TEMPLATE_VERSION 1.4, section Sources datée"),
  ("prix_terrain_secteur_eur_m2", "Prix secteur (Flash)", "€/m²", "parcelle", "moteur:sector_price",
   "src/labuse/flash/data.py", "dvf", "live", "aucun", "millesime", "même sector_price que la fiche"),
  ("population_zone", "Autour de cette parcelle (Flash)", "nombre", "zone", "moteur:zone",
   "src/labuse/flash/data.py::_zone (consomme zone.etude_de_zone)", "filosofi_carreaux,sirene_etablissements",
   "live", "zone_isochrone_cache", "millesime", "AUCUNE recopie : consomme le moteur zone (F2)"))
L("pdf_dossier_expert",
  ("tier_opportunite", "Verdict (Dossier)", "classe", "parcelle", "moteur:scoring_p_v2",
   "src/labuse/api/dossier.py:65 (réutilise flash/report.py)", "cosia,sitadel,dvf", RUN, "aucun", "run",
   "même builder que Flash, quota mensuel"))
L("pdf_banquier",
  ("charge_fonciere_eur", "Bilan (banquier)", "€", "parcelle", "moteur:bilan_promoteur",
   "src/labuse/api/banquier.py:283 (briques_pdf)", "dvf", "live", "aucun", "rien",
   "11 étapes de faisabilité + bilan, synthèse IA strict_numbers"),
  ("prix_terrain_secteur_eur_m2", "Comparables (banquier)", "€/m²", "parcelle", "moteur:sector_price",
   "src/labuse/api/banquier.py:283", "dvf", "live", "aucun", "rien", "même sector_price"))
L("pdf_pre_dossier_pc",
  ("zone_plu_famille", "Règles de zonage (CERFA)", "classe", "parcelle", "passe_plat",
   "src/labuse/api/pre_dossier.py:732", "gpu_plu_api_carto", "live", "aucun", "date",
   "zone + servitudes telles que servies, CERFA 13406*17"))
L("pdf_lettre_zonage",
  ("zone_plu_famille", "Zone (lettre)", "classe", "parcelle", "passe_plat",
   "src/labuse/api/lettre_zonage.py", "gpu_plu_api_carto", "live", "aucun", "date",
   "zone exacte + références (lettre_zonage_refs)"))
L("pdf_argumentaire",
  ("prix_terrain_secteur_eur_m2", "Prix (argumentaire)", "€/m²", "parcelle", "moteur:sector_price",
   "src/labuse/api/argumentaire.py", "dvf", "live", "aucun", "rien", "faits chiffrés sourcés"))

# ── PAGES CLIENT ─────────────────────────────────────────────────────────────────────
L("page_accueil_chiffres",
  ("n_parcelles_ile", "Parcelles (accueil)", "nombre", "global", "sql_propre",
   "src/labuse/api/accueil.py:57", "cadastre_api_carto", "live", "cache 1 h", "rien",
   "count parcels mesuré, jamais en dur"),
  ("n_sources", "Sources (accueil)", "nombre", "global", "sql_propre",
   "src/labuse/api/accueil.py:57 (WHERE_AFFICHEES)", "(data_sources)", "live", "cache 1 h", "rien",
   "count des sources AFFICHÉES (66 au 05/09)"),
  ("run_label_servi", "Run servi (pied)", "classe", "global", "constante",
   "src/labuse/api/accueil.py:57", "(config/served_run.txt)", RUN, "cache 1 h", "run", "label du run servi"))
L("page_accueil_semaine",
  ("n_bascules_7j", "Bascules (cette semaine)", "nombre", "global", "sql_propre",
   "src/labuse/api/accueil.py:116", "(event_log)", RUN, "aucun", "rien",
   "même compte de bascules que le brief"))
L("page_sources_client",
  ("n_sources", "Sources (page client)", "nombre", "global", "sql_propre",
   "src/labuse/api/app.py:919-924 (WHERE_AFFICHEES)", "(data_sources)", "live", "aucun", "millesime",
   "66 affichées — chaque ligne porte millésime amont + ingéré le"))
L("page_flash_publique",
  ("prix_flash_eur", "Rapport Flash — 79 €", "€", "global", "constante",
   "src/labuse/offres.py (source unique des prix)", "(config)", "live", "aucun", "rien",
   "prix de l'offre Flash, source unique offres.py"))

# ── ADMIN ────────────────────────────────────────────────────────────────────────────
L("admin_pilotage",
  ("n_a_faire", "À faire (pilotage)", "nombre", "global", "sql_propre",
   "src/labuse/api/dashboard.py:250", "(etats_sources + crons)", "live", "aucun", "rien",
   "gestes attendus : nouvelle_version + a_rafraichir (arbitre unique etats_sources)"))
L("admin_catalogue_sources",
  ("n_sources", "Catalogue (compte par état)", "nombre", "global", "sql_propre",
   "src/labuse/api/dashboard.py:893-894 (est_affichee — sans affichage_desactive)", "(data_sources)",
   "live", "aucun", "rien", "66 affichées, ventilées par les 5 états"))
L("admin_flux_circuit",
  ("n_sources", "Sources (écran Circuit)", "nombre", "global", "sql_propre",
   "src/labuse/flux.py:198 (count(*) SANS WHERE_AFFICHEES)", "(data_sources)", "live", "aucun", "rien",
   "77 = compte BRUT — c'est la FUITE du « 77 dont 49 » vu par Vic"),
  ("n_sources_surveillees", "sous veille (écran Circuit)", "nombre", "global", "sql_propre",
   "src/labuse/flux.py:199-201", "(source_veille)", "live", "aucun", "rien",
   "49 = lignes source_veille actives à vraie sonde, compte brut"),
  ("run_label_servi", "Run courant (Circuit)", "classe", "global", "constante",
   "src/labuse/api/dashboard.py:1231", "(config/served_run.txt)", RUN, "aucun", "run", "runs.current()"))
L("admin_mise_a_jour",
  ("ecart_candidat_pct", "Écart candidat vs servi", "%", "global", "sql_propre",
   "src/labuse/golden_ops.py:33-60 (_DISTRIB_CACHE)", "(parcel_p_score_v2)", "parametre", "dict mémoire", "run",
   "comparaison distribution tiers candidat/servi"))
L("admin_ia",
  ("ia_cout_eur", "Conso IA (€)", "€", "global", "sql_propre",
   "src/labuse/api/dashboard.py:721", "(ia_log)", "live", "aucun", "rien",
   "somme cout par modèle/surface 30 j (ledger ia_log)"))
L("admin_radar",
  ("n_depots_a_verifier", "Dépôts à vérifier", "nombre", "global", "sql_propre",
   "src/labuse/pige/api.py (a_verifier)", "radar_pige", "live", "aucun", "rien",
   "count pige_depots en attente de validation"))
L("admin_destinations",
  ("n_communes_rnu", "RNU (règlement national)", "nombre", "global", "sql_propre",
   "frontend/src/components/admin/Destinations.tsx:45 (d.compte.rnu)", "sudocuh", "live", "aucun", "rien",
   "compteur de communes RNU de la calibration destinations"))
L("admin_licences",
  ("n_comptes_actifs", "Comptes actifs", "nombre", "global", "sql_propre",
   "src/labuse/api/dashboard.py:462", "(comptes)", "live", "aucun", "rien", "count comptes par statut"))


def main() -> None:
    INV.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(ROWS)

    # ── fuites candidates : chiffre_id sur ≥2 robinets avec ≥2 chemins (fichier_ligne) ──
    par_chiffre: dict[str, list[dict]] = defaultdict(list)
    for r in ROWS:
        par_chiffre[r["chiffre_id"]].append(r)
    fuites = []
    for cid, rs in sorted(par_chiffre.items()):
        robs = sorted({r["robinet_id"] for r in rs})
        chemins = sorted({r["fichier_ligne"] for r in rs})
        if len(robs) >= 2 and len(chemins) >= 2:
            fuites.append({"chiffre_id": cid, "n_robinets": len(robs), "n_chemins": len(chemins),
                           "robinets": ",".join(robs), "chemins": " || ".join(chemins),
                           "preuve": "dérivé de chiffres.csv (groupby chiffre_id)"})
    # la fuite mandatée (part de zonage) est ajoutée même si le 2e chemin (app.py:2436, comptes
    # par famille) n'est pas un robinet client listé : les DEUX chemins existent dans le code.
    fuites.append({"chiffre_id": "part_zone_A_pct", "n_robinets": 2, "n_chemins": 2,
                   "robinets": "fiche_commune_zonage,(filtres /zones-plu)",
                   "chemins": "src/labuse/api/app.py:1908-1955 (PART DE SURFACE) || src/labuse/api/app.py:2436 (comptes de PARCELLES par famille)",
                   "preuve": "mesuré Saint-Paul 05/09 : A 35,8 % surface vs 17,8 % parcelles"})
    fuites.append({"chiffre_id": "part_zone_N_pct", "n_robinets": 2, "n_chemins": 2,
                   "robinets": "fiche_commune_zonage,(filtres /zones-plu)",
                   "chemins": "src/labuse/api/app.py:1908-1955 || src/labuse/api/app.py:2436",
                   "preuve": "mesuré Saint-Paul 05/09 : N 47,2 % surface vs 6,8 % parcelles"})
    with OUT_FUITES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["chiffre_id", "n_robinets", "n_chemins", "robinets", "chemins", "preuve"],
                           delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(fuites)

    calc = Counter(r["calcul"].split(":")[0] for r in ROWS)
    print(f"chiffres.csv : {len(ROWS)} lignes ; chiffre_id distincts : {len(par_chiffre)}")
    print("par calcul :", dict(sorted(calc.items())))
    print("avec tampon ≠ rien :", sum(1 for r in ROWS if r["tampon"] != "rien"))
    print("DOUTE :", sum(1 for r in ROWS if "DOUTE" in ";".join(r.values())))
    print(f"fuites candidates : {len(fuites)}")


if __name__ == "__main__":
    main()
