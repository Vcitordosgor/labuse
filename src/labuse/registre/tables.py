"""CIRCUIT-5 lot 1.1 — LA CARTE TABLE → RÉSERVOIR.

Chaque réservoir du catalogue (`data_sources`, slugs de `reservoirs.csv` /
`circuit_etats.NOM_VERS_SLUG`) déclare ICI la ou les tables qu'il sert (tables, vues,
matérialisations, tuilages — et pour `spatial_layers`, ses `kind`), et le millésime servi.
Une table qui n'appartient ni à cette carte, ni aux fabrications de la pompe
(`TABLES_FABRIQUEES`), ni aux tables d'exploitation (`TABLES_EXPLOITATION`) est ORPHELINE :
aucun moteur n'a le droit de la lire (verrou V1, `circuit_verrous.py`), et elle est listée
dans `docs/CIRCUIT/TABLES-ORPHELINES.md` pour le geste de Vic (`labuse tables purger`).

Les orphelines ne sont JAMAIS énumérées en dur : elles sont CALCULÉES (le schéma moins la
carte) — seule l'action proposée pour chacune est curée (`ACTIONS_PROPOSEES`).

Le code est LA vérité (comme donnees.py/robinets.py) ; `reservoirs.csv` (CIRCUIT-0) en fut
la source d'inventaire, les DOUTE y ont été résolus ici (voir COMPTE-RENDU-CIRCUIT-5).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReservoirTables:
    """Ce qu'un réservoir sert physiquement en base."""
    tables: tuple[str, ...] = ()          # relations lues (tables, vues, matérialisations)
    couches: tuple[str, ...] = ()         # kind dans spatial_layers (si spatial_layers ∈ tables)
    millesime: str = ""                   # millésime servi (texte, tel qu'affiché/inventorié)
    note: str | None = None               # hors vitrine, alias, API directe… (raison lisible)


Rt = ReservoirTables

#: slug réservoir (reservoirs.csv / NOM_VERS_SLUG) → tables servies.
#: Les réservoirs SANS table (API interrogée en direct, règles portées par le code, saisie
#: manuelle) le déclarent avec une note — jamais un oubli silencieux.
RESERVOIR_TABLES: dict[str, ReservoirTables] = {
    # ── cadastre / foncier ──────────────────────────────────────────────────────────
    "cadastre_api_carto": Rt(("parcels",), millesime="PCI Parcellaire Express (DGFiP) — « latest » ingérée"),
    "cadastre_etalab_bulk": Rt(("parcels",), millesime="Etalab cadastre — « latest » (DGFiP)",
                               note="DOUBLON (canal bulk du même réservoir que cadastre_api_carto)"),
    "cadastre_epoque": Rt(("cadastre_historique",),
                          millesime="PCI vecteur Etalab — millésimes 2019→2025 (cadastre d'époque)"),
    "dgfip_parcelles_pm": Rt(("parcelle_personne_morale", "pm_proprietaires_millesimes"),
                             millesime="Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)"),
    "fichiers_fonciers_cerema": Rt((), note="manuel — convention DGFiP non instruite, aucune table"),
    # ── urbanisme ───────────────────────────────────────────────────────────────────
    "gpu_plu_api_carto": Rt(("spatial_layers", "plu_reglement_extrait"),
                            couches=("plu_gpu_zone", "plu_gpu_prescription"),
                            millesime="GPU/PLU par commune (révisions — détail en fiche)"),
    "sup_gpu": Rt(("spatial_layers",), couches=("sup",),
                  millesime="assiettes SUP GPU (API Carto) — inventaire catégoriel 974 sondé "
                            "(9 en vigueur ; T5/PT1/PT2 restreintes ; AS1 non publiée)"),
    # ── SOURCES-1 lot 1 — droit des sols ────────────────────────────────────────────
    "gpu_prescriptions_er": Rt(("spatial_layers",), couches=("plu_gpu_prescription",),
                               millesime="GPU — prescriptions typepsc 05 (idurba par commune)",
                               note="réservoir LOGIQUE sur la famille ER du kind plu_gpu_prescription "
                                    "(typepsc 05 + rescue libellé — même canal que gpu_plu_api_carto)"),
    "gpu_prescriptions_ebc": Rt(("spatial_layers",), couches=("plu_gpu_prescription",),
                                millesime="GPU — prescriptions typepsc 01 (idurba par commune)",
                                note="réservoir LOGIQUE sur les EBC (typepsc 01) du kind "
                                     "plu_gpu_prescription — même canal que gpu_plu_api_carto"),
    "dpu_perimetres": Rt(("spatial_layers",), couches=("dpu",),
                         millesime="GPU typeinf 04 — 4/24 communes publiées (06/09/2026)"),
    "peb_dgac": Rt(("spatial_layers",), couches=("peb",),
                   millesime="Roland-Garros A/B/C/D (annexes GPU) ; Pierrefonds non publié"),
    "zonage_abc_dhup": Rt(("commune_zonage_abc",),
                          millesime="arrêté 23/06/2026 en vigueur 26/06 — 24/24 (4 A, 20 B1)"),
    "zppa_culture": Rt((), note="aucune donnée — Atlas des patrimoines injoignable au 06/09/2026, "
                                "rappel sentinelle 180 j (SOURCES-1 lot 1)"),
    # ── SOURCES-1 lot 2 — la nature et l'eau ────────────────────────────────────────
    "deal_dpf_dpe": Rt(("spatial_layers",), couches=("dpf",),
                       millesime="DPF arrêté 06-3077 du 21/08/2006 — 275 tronçons + 6 plans",
                       note="le DPE (domaine privé de l'État) n'est pas diffusé — demande DEAL (lot 7)"),
    "deal_zones_humides": Rt(("spatial_layers",), couches=("zone_humide",),
                             millesime="inventaires DEAL 2003/2009/2011/2019 par secteurs"),
    "enp_complements_deal": Rt(("spatial_layers",), couches=("ens",),
                               millesime="Ramsar 1 · sites classés/inscrits 7 · RN 3 (Carmen 07/09/2026)",
                               note="complète le kind ens de l'INPN (subtypes ramsar/site_classe/"
                                    "site_inscrit/reserve_naturelle — purge par subtype)"),
    "georisques_azi_tri": Rt(("azi_communes",),
                             millesime="GASPAR azi+tri par commune (07/09/2026)"),
    "sudocuh": Rt(("sudocuh_procedures",), millesime="Sudocuh — état au 31/12/2024"),
    "sitadel": Rt(("sitadel_permits", "via_permits_geo"), millesime="2026-07"),
    "qpv_2024": Rt(("spatial_layers",), couches=("qpv",), millesime="génération 2024"),
    "npnru": Rt(("anru_quartiers", "spatial_layers"), couches=("anru",)),
    "sru_dhup": Rt(("commune_contexte_sru",), millesime="inventaire LLS — CSV v2 du 18/12/2025"),
    "plh_epci": Rt(("plh_epci",), millesime="extraction documentaire 07/07/2026"),
    "cinquante_pas_deal": Rt(("spatial_layers",), couches=("cinquante_pas",),
                             millesime="cadastre 1877 (géoréf. 2012/1950)"),
    "gpu_zonage_assainissement": Rt(("spatial_layers", "parcel_anc"), couches=("zonage_assainissement",),
                                    millesime="GPU — idurba par commune ; SIG 4/24 au 11/07/2026"),
    "gpu_assainissement_infosurf": Rt((), note="DOUBLON (canal info-surf de gpu_zonage_assainissement)"),
    "rtaa_dom": Rt((), note="règles portées par le code (aucune table)"),
    "zfang": Rt(("spatial_layers", "territoire_fiscal_commune"), couches=("zfang", "tva_primo"),
                millesime="Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18)"),
    "frr_ex_zrr": Rt(("spatial_layers", "territoire_fiscal_commune"), couches=("frr",),
                     millesime="ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017"),
    "taxe_amenagement": Rt(("taxe_amenagement_taux",),
                           note="a_faire — mécanisme CIRCUIT-3 lot 6.2, taux communaux à saisir"),
    # ── risques / environnement ─────────────────────────────────────────────────────
    "georisques_api": Rt(("spatial_layers",), couches=("georisque_alea",)),
    "catnat_gaspar": Rt(("catnat_arretes",), millesime="GASPAR — 426 arrêtés sur 24 communes"),
    "deal_ppr": Rt(("spatial_layers",), couches=("ppr",),
                   millesime="PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)"),
    "georisques_ssp": Rt(("spatial_layers",), couches=("sol_pollue",)),
    "georisques_cavites": Rt(("spatial_layers",), couches=("cavite",)),
    "georisques_icpe": Rt(("spatial_layers",), couches=("icpe",)),
    "georisques_mvt": Rt(("spatial_layers",), couches=("mvt",)),
    "cartofriches": Rt(("spatial_layers",), couches=("friche",)),
    "abf_merimee": Rt(("spatial_layers",), couches=("abf",),
                      millesime="Monuments historiques Mérimée (POP) — périmètres ABF"),
    "erosion_cotiere_geolittoral": Rt(("spatial_layers",), couches=("trait_de_cote",), millesime="millésime 2018"),
    "bruit_itt_cerema": Rt(("spatial_layers",), couches=("bruit_route",), millesime="arrêtés déc. 2023"),
    "parc_national_inpn": Rt(("spatial_layers",), couches=("parc_national",), millesime="millésime 2021"),
    "forets_onf_bdtopo": Rt(("spatial_layers",), couches=("foret_publique",),
                            millesime="BD TOPO® V3 — forêt publique (IGN)"),
    "inpn_espaces_proteges": Rt(("spatial_layers",), couches=("ens",),
                                millesime="INPN/patrinat espaces protégés — passe 05/07/2026"),
    "znieff_inpn": Rt(("spatial_layers",), couches=("znieff",), millesime="INPN, mise à jour 29/08/2025"),
    "znieff_region_ods": Rt((), note="canal Région non branché (0 donnée) — canonique : znieff_inpn"),
    # ── marché / valeurs ────────────────────────────────────────────────────────────
    "dvf": Rt(("dvf_mutations", "dvf_mutations_parcelle", "dvf_mutations_histo",
               "dvf_secteur_medianes", "dvf_prix_sortie_neuf", "spatial_layers"),
              couches=("vefa_neuf",),
              millesime="géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020"),
    "dpe_ademe": Rt(("dpe_records",)),
    "radar_pige": Rt(("pige_annonces", "pige_biens", "pige_faits", "pige_depots", "pige_captures",
                      "pige_clics", "pige_prix_historique", "pige_interets_agence", "radar_releves"),
                     millesime="collecte manuelle — biens en vente (faits + lien)"),
    # ── entreprises / propriétaires ────────────────────────────────────────────────
    "sirene_recherche_entreprises": Rt((), note="API INSEE interrogée à la requête (aucune table)"),
    "sirene_etablissements": Rt(("sirene_etablissements",),
                                millesime="SIRENE géolocalisé — publication mensuelle INSEE"),
    "recherche_entreprises_dinum": Rt(("owner_denom_lookup", "owner_enrichment"),
                                      millesime="Sirene INSEE / RNE INPI (api.gouv.fr) — courant"),
    "inpi_rne": Rt(("pm_dirigeants", "pm_dirigeant_gigogne")),
    "bodacc": Rt(("bodacc_sondages", "bodacc_procedures", "bodacc_annonces_owner", "annonces")),
    # ── territoire / statistique ────────────────────────────────────────────────────
    "insee_rp_logement": Rt(("commune_insee_logement",)),
    "insee_rp2022_egoul": Rt(("anc_maille_taux",), millesime="RP2022 — fichier détail Logements (16/10/2025)"),
    "filosofi_carreaux": Rt(("filosofi_carreaux_200m", "p_model_filo"), millesime="millésime 2021"),
    "mobpro": Rt(("mobpro_commune",), millesime="MOBPRO INSEE — fichier détail (millésime RP)",
                 note="RETIRÉ 06/09/2026 (CIRCUIT-5b) — abandonné par ZONE-DONNÉES ; lecteur "
                      "zone.emplois_communes sans appelant (code mort). Table conservée, plus lue."),
    "bpe_insee": Rt(("spatial_layers",), couches=("amenite_bpe",),
                    millesime="millésime 2025 (géographie au 01/01/2025)"),
    "contours_iris": Rt(("spatial_layers",), couches=("iris_insee",),
                        millesime="Contours IRIS — géographie 2024 (IGN/INSEE)"),
    "office_eau_chroniques": Rt(("anc_office_eau_commune",), millesime="Chronique n°149 — données 2023"),
    "spanc_epci": Rt((), note="manuel — collectif/non collectif saisi, aucune table dédiée"),
    "annuaire_service_public": Rt(("mairies",),
                                  millesime="annuaire service-public.fr — 24 mairies (OUTILS K2)"),
    "rnic_anah": Rt(("rnic_coproprietes",), millesime="RNIC (ANAH) — registre des copropriétés"),
    "rpls_sdes": Rt(("rpls_commune",), millesime="RPLS — millésime 01/01/2025 (SDES)"),
    "enaf_cerema": Rt(("commune_conso_enaf",),
                      millesime="conso ENAF 2021-2024 (portail artificialisation, Cerema)"),
    # ── géographie physique / imagerie ─────────────────────────────────────────────
    "bd_topo": Rt(("spatial_layers",), couches=("batiment", "voirie", "water", "ravine"),
                  millesime="BD TOPO® V3 (IGN)"),
    "rge_alti": Rt(("rgealti_pente_5m", "spatial_layers"), couches=("pente",), millesime="RGE ALTI® (IGN)"),
    "rge_alti_5m": Rt(("rgealti_pente_5m",), note="DOUBLON (même réservoir que rge_alti)"),
    "bd_carto_ocs": Rt(("spatial_layers",), couches=("ocs_ge",),
                       millesime="BD CARTO® V5 — occupation du sol (IGN, proxy)"),
    "bd_ortho": Rt(("ortho_tiles", "ortho_detections", "parcel_equipements"),
                   millesime="BD ORTHO IGN 974 — millésime 2025"),
    "bd_ortho_irc": Rt(("ortho_detections", "parcel_vegetation", "vegetation_zonal_acc")),
    "cosia": Rt(("spatial_layers", "p_model_bati_cosia", "qa_cosia_bati"), couches=("batiment_cosia",),
                millesime="CoSIA 2025 (PVA juil.-août 2025, 20 cm)"),
    "lidar_hd_mnh": Rt(("toiture_lidar",), millesime="LiDAR HD MNH — dalles publiées 25/06/2025 (IGN)"),
    "pvgis": Rt(("solar_grid", "parcel_solar"), millesime="PVGIS v5.3 · modèle SARAH3"),
    # ── occupation / potentiel ──────────────────────────────────────────────────────
    "potentiel_foncier_region": Rt(("spatial_layers",), couches=("potentiel_foncier", "sar")),
    "potentiel_foncier_ods": Rt(("spatial_layers",), couches=("potentiel_foncier",)),
    "rpg_proxy_ign": Rt(("spatial_layers",), couches=("safer",),
                        millesime="proxy RPG (IGN) — RPG.LATEST, année non pinnée",
                        note="SOURCES-1 lot 2 : code_cultu servi (CSA canne 12 464/38 460) — "
                             "couche carte « Cultures déclarées » + cascade zone A/canne"),
    # ── adresses / réseaux / transport ─────────────────────────────────────────────
    "ban": Rt(("adresses", "adresse_parcelles")),
    "osm_overpass": Rt(("parcel_amenites", "spatial_layers"), couches=("amenite", "osm_faux_positif"),
                       millesime="extraction Overpass (base OSM vivante, ODbL)"),
    "osm_transport": Rt(("spatial_layers",), couches=("telepherique", "pole_echange"),
                        millesime="extraction Overpass (base OSM vivante, ODbL)"),
    "gtfs_pan": Rt(("spatial_layers",),
                   couches=("transport_arret", "transport_ligne", "pole_echange", "axe_structurant"),
                   millesime="7 jeux PAN, màj 2025-12-29 → 2026-08-17"),
    "tcsp_osm": Rt(("spatial_layers",), couches=("tcsp_troncon", "tcsp_station", "tcsp_zone"),
                   millesime="extraction Overpass (OSM, ODbL) — voies bus 974"),
    "trafic_rn": Rt(("trafic_rn",), millesime="Trafic RN Région — millésime porté par tronçon"),
    "edf_hta": Rt(("spatial_layers",), couches=("ligne_mt", "ligne_ht"),
                  millesime="EDF géométrie ~02/2020 · publié 16/10/2025"),
    "parkings_osm_aper": Rt(("parkings_aper",)),
    # ── hubs et retirées (hors vitrine — déclarées pour que rien ne soit un oubli) ──
    "region_ods_hub": Rt((), note="hub de catalogue (jamais un réservoir)"),
    "peigeo_hub": Rt((), note="hub AGORAH (jamais un réservoir)"),
    "geoplateforme_hub": Rt((), note="hub IGN (jamais un réservoir)"),
    "deal_wms_wfs": Rt((), note="canal servi par proxys — les tables sont portées par qpv_2024/npnru"),
    "edf_sei_opendata": Rt((), note="RETIRÉ — amont 410 Gone"),
    "odre_registre_installations": Rt((), note="RETIRÉ — jamais branché"),
    "bdnb": Rt((), note="amont métropole seule — 974 absent (constat mesuré)"),
    "reunion_express_cndp": Rt((), note="hypothèses de tracé au débat public — rien d'ingéré"),
    "ecln": Rt((), note="métropole seule, N/A DOM"),
    "lovac": Rt((), note="convention dédiée non instruite"),
}

#: Tables FABRIQUÉES par la pompe (cascade, scoring, builders) : produits du calcul dérivés
#: des réservoirs, changés au run/à la bascule — pas des réservoirs, pas de l'exploitation.
#: valeur = qui les fabrique (lisible).
TABLES_FABRIQUEES: dict[str, str] = {
    "cascade_results": "cascade (run complet)",
    "dryrun_cascade_results": "cascade (dryrun candidat)",
    "dryrun_parcel_evaluations": "évaluation (dryrun candidat)",
    "parcel_evaluations": "évaluation (run servi)",
    "parcel_p_score_v2": "scoring P v2",
    "p_score_v2_runs": "scoring P v2 (registre des runs)",
    "parcel_flags": "build-mvt (drapeaux servis)",
    "score_e": "score É (ingestion/score_e.py)",
    "score_snapshot_parcelles": "score V (photos)",
    "score_snapshots": "score V (photos)",
    "parcel_v_score": "score V",
    "parcel_residuel": "vue résiduel (faisabilite)",
    "parcel_residuel_bati": "résiduel bâti (builder)",
    "parcel_residuel_runs": "résiduel (registre des runs)",
    "parcel_residuel_base_legacy": "LEGACY — lecteur faisabilite/residuel_runs.py (à rattacher ou purger, CIRCUIT-0)",
    "residuel_runs": "résiduel (manifeste)",
    "mvt_parcels": "build-mvt (tuiles parcelles)",
    "mvt_overlays": "build-mvt (tuiles couches)",
    "mvt_meta": "build-mvt (pointeurs)",
    "p_model_bati": "modèle P (features bâti)",
    "p_model_candidates": "modèle P (candidats)",
    "p_model_dataset": "modèle P (dataset v1)",
    "p_model_dataset_v2": "modèle P (dataset v2)",
    "p_model_dataset_v2bis": "modèle P (dataset v2bis)",
    "p_model_ext_copro": "modèle P ext (copropriétés)",
    "p_model_ext_dataset": "modèle P ext (dataset)",
    "p_model_ext_dvf": "modèle P ext (DVF)",
    "p_model_ext_mut_all": "modèle P ext (mutations)",
    "p_model_ext_mut_l2": "modèle P ext (mutations L2)",
    "p_model_frame": "modèle P (trame)",
    "p_model_geo": "modèle P (géo)",
    "p_model_layers_sub": "modèle P (couches sous-échantillonnées)",
    "p_model_mut_all": "modèle P (mutations)",
    "p_model_mut_l2": "modèle P (mutations L2)",
    "p_model_permits": "modèle P (permis)",
    "p_model_static": "modèle P (statique)",
    "module_division": "module division",
    "division_or_candidates": "division (candidats or)",
    "division_or_revue_snapshot": "division (photo de revue)",
    "parcel_au_statut": "statut AU (builder)",
    "parcel_zone_plu": "zonage parcelle (builder GPU)",
    "parcel_terrain": "terrain (pente/ortho builders)",
    "parcel_geometrie": "géométrie parcelle (builder)",
    "parcel_bati_revele": "bâti révélé (builder)",
    "parcel_constructibilite": "constructibilité (builder)",
    "parcel_filtre_bati": "filtre bâti (scoring)",
    "parcel_acquerabilite": "lignée/tête (scoring)",
    "parcel_entree_tete": "lignée/tête (scoring)",
    "parcel_adresse": "rattachement adresses (builder BAN)",
    "parcel_enrichment": "enrichissement fiche (builder)",
    "parcel_signals": "signaux parcelle (builder)",
    "parcel_signaux_vie": "signaux de vie (builder)",
    "parcel_veille_succession": "veille succession (score V)",
    "parcel_renouvellement": "renouvellement (builder)",
    "parcel_viabilisation": "viabilisation (builder)",
    "parcel_pau": "PAU — parties actuellement urbanisées (rnu.py)",
    "commune_pau": "PAU commune (rnu.py)",
    "parcel_source_results": "résultats par source (cascade)",
    "spatial_layers_sub": "couches sous-échantillonnées (cascade)",
    "m10_permit_delais": "délais permis (builder Sitadel)",
    "pc_caducs": "PC caducs (builder)",
    "defisc_fenetres": "fenêtres défisc (builder)",
    "surface_d_events": "surface D (événements)",
    "grid_capacity": "capacité réseau (viabilisation)",
    "matching_review_queue": "file de revue matching (score V)",
    "entonnoir_motifs": "entonnoir des motifs (scoring)",
    "zone_isochrone_cache": "cache isochrones (étude de zone)",
    "commune_contexte_cache": "cache fiche commune",
    "v_foncier_propension_vendre": "vue (score V)",
    "v_foncier_sous_pression": "vue (score V)",
    "v_parcel_dvf_last": "vue (DVF dernier passage)",
    "v_parcelle_contact_compte": "vue (CRM)",
    "v_passoire_thermique": "vue (DPE)",
    "v_pm_propension_vendre": "vue (score V)",
}

#: Tables d'EXPLOITATION : la machine elle-même (comptes, journal, registre, filtres,
#: événements, sessions, IA, CRM, paiement…). valeur = rôle (lisible).
TABLES_EXPLOITATION: dict[str, str] = {
    "data_sources": "catalogue des sources",
    "communes_referentiel": "référentiel des 24 communes (cible des clés étrangères, CIRCUIT-5 lot 4)",
    "ingestion_runs": "journal d'ingestion",
    "source_veille": "sentinelle des sources",
    "source_checks": "contrôles de sources",
    "source_radar": "radar de sources",
    "registre_chiffres": "miroir du registre (données)",
    "registre_robinets": "miroir du registre (robinets)",
    "registre_aretes": "miroir du registre (arêtes)",
    "circuit_journal": "journal du circuit",
    "circuit_ecarts": "sonde — fuites",
    "circuit_eau_ancienne": "sonde — eau ancienne",
    "circuit_controles": "sonde — passages",
    "filtre_resultats": "filtres — résultats",
    "filtre_versions": "filtres — versions",
    "run_bascule_journal": "journal des bascules",
    "served_run_exceptions": "exceptions du run servi",
    "comptes": "comptes clients",
    "utilisateurs": "utilisateurs",
    "sessions_auth": "sessions",
    "totp_2fa": "2FA",
    "totp_secours": "2FA (codes de secours)",
    "api_keys": "clés API partenaires",
    "acces_gels": "gels d'accès",
    "abuse_scores": "protection anti-abus",
    "admin_alertes": "alertes admin",
    "consultation_log": "journal des consultations",
    "export_fingerprints": "empreintes d'export",
    "evenements_compte": "événements de compte",
    "event_log": "journal d'événements",
    "event_seen": "événements vus",
    "usage_events": "usage (événements)",
    "usage_compteurs": "usage (compteurs)",
    "alertes": "alertes clients",
    "veilles": "veilles",
    "veille_reprise": "reprise de veille",
    "watch_zones": "zones surveillées",
    "watch_zone_zonage_snap": "photos zonage des zones surveillées",
    "watch_snapshots": "photos de veille",
    "watched_parcels": "parcelles suivies",
    "saved_filters": "filtres enregistrés",
    "saved_searches": "recherches enregistrées",
    "notif_canaux": "canaux de notification",
    "notif_prefs": "préférences de notification",
    "suggestions": "suggestions",
    "retours": "retours utilisateurs",
    "signalements": "signalements",
    "parcel_feedback": "retours parcelle",
    "pipeline_entries": "CRM — pipeline",
    "crm_columns": "CRM — colonnes",
    "contact_etiquette_log": "CRM — étiquettes",
    "commune_contacts": "contacts communes",
    "projets": "projets clients",
    "projet_parcelles": "projets — parcelles",
    "programmes": "programmes (promo)",
    "match_profiles": "profils de matching partenaires",
    "share_links": "liens de partage",
    "courrier_demandes": "courrier — demandes",
    "courrier_envois": "courrier — envois",
    "flash_commandes": "commandes Flash",
    "stripe_events": "paiement Stripe",
    "licence_mails": "licences (mails)",
    "copilote_conversations": "Copilote — conversations",
    "copilote_messages": "Copilote — messages",
    "copilote_faits": "Copilote — faits",
    "copilote_telemetrie": "Copilote — télémétrie",
    "agent_runs": "Copilote — runs d'agents",
    "agent_run_parcels": "Copilote — parcelles d'agents",
    "agent_events": "Copilote — événements d'agents",
    "ia_log": "IA — grand livre",
    "ia_cache": "IA — cache",
    "ia_ask_quota": "IA — quotas",
    "nl_query_log": "IA — requêtes NL",
    "app_reglages": "réglages applicatifs",
    "bilan_params": "paramètres de bilan",
    "entite_acronyme": "référentiel des acronymes",
    "lettre_zonage_refs": "références lettre de zonage",
    "piscine_corrections": "curation humaine (piscines)",
    # CIRCUIT-5b lot 1 — rpls_commune (→ rpls_sdes) et commune_conso_enaf (→ enaf_cerema) sont
    # désormais des RÉSERVOIRS de première classe (voir RESERVOIR_TABLES), plus des tables
    # d'exploitation « servies sans réservoir » : une source = une ligne data_sources.
}

#: Relations système PostGIS — jamais orphelines, jamais purgées.
POSTGIS: frozenset[str] = frozenset({
    "spatial_ref_sys", "geometry_columns", "geography_columns", "raster_columns", "raster_overviews",
})

#: Tables SERVIES par un écran mais sans ligne `data_sources` (ou sans slug réservoir) — la
#: question est pour Vic : créer la ligne au catalogue, ou rattacher à une ligne existante.
#: Elles apparaissent au Résumé sous « à décider » (lot 1.4) — PAS des orphelines.
#: CIRCUIT-5b lot 1 — les quatre « à rattacher » de CIRCUIT-5 sont TRANCHÉS : ce sont des
#: sources, entrées au catalogue (data_sources), au pont (NOM_VERS_SLUG) et à la carte
#: (RESERVOIR_TABLES : annuaire_service_public, rnic_anah, rpls_sdes, enaf_cerema). Plus aucun
#: rattachement en attente — le dict reste (le Résumé le lit) mais vide.
RATTACHEMENTS_A_DECIDER: dict[str, str] = {}

#: Action proposée pour les orphelines CONNUES (curation CIRCUIT-5 — la purge reste le geste
#: de Vic, `labuse tables purger --apply`). Une orpheline hors de ce dict = « à décider ».
ACTIONS_PROPOSEES: dict[str, str] = {
    "_lota_grave_parcels": "purger (photo de travail LOT A)",
    "algo2_prop_features": "purger (features d'essai algo2)",
    "backup_sp_ppr_avant_littoral": "purger (backup PPR avant littoral — Saint-Pierre)",
    "backup_spaul_ppr_avant_littoral": "purger (backup PPR avant littoral — Saint-Paul)",
    "cascade_ext_avant": "purger (photo avant cascade ext — plus aucun lecteur)",
    "conso_baseline_commune": "archiver (baseline conso — plus aucun lecteur)",
    "m50_marker": "purger (marqueur de migration M50)",
    "m6_a02_backup_plu_dup": "purger (backup M6 doublons PLU)",
    "m6_p103_backup_dvf_surfaces": "purger (backup M6 surfaces DVF)",
    "m6_snapshot_mvt_post2a": "purger (photo M6 tuiles)",
    "m6_snapshot_mvt_post2b": "purger (photo M6 tuiles)",
    "mv_toitures_tertiaires": "archiver (matérialisation toitures tertiaires — plus aucun lecteur)",
    "ortho_verdicts_quarantaine": "archiver (quarantaine ortho historique)",
    "p_model_bati_features": "purger (features d'essai modèle P)",
    "p_model_scores_2026": "archiver (scores modèle P 2026 — photo)",
    "p_model_static_pre_v8": "archiver (photo pré-v8 — débranchée de bascule_gardes, CIRCUIT-5b lot 4 ; orpheline ordinaire, purge au geste de Vic)",
    "parcel_adjacence": "archiver (adjacence — plus aucun lecteur)",
    "parcel_au_statut_pre_m32": "purger (photo pré-M32, CIRCUIT-0)",
    "parcel_au_statut_prebascule": "purger (photo pré-bascule)",
    "parcel_residuel_pre_v8": "archiver (photo pré-v8 — débranchée de bascule_gardes, CIRCUIT-5b lot 4 ; orpheline ordinaire, purge au geste de Vic)",
    "parcel_residuel_rerun": "purger (rerun d'essai)",
    "parcel_vue_mer": "archiver (vue mer — plus aucun lecteur)",
    "parcel_zone_plu_prebascule": "purger (photo pré-bascule)",
    "pv_registry": "archiver (registre PV — plus aucun lecteur)",
    "qa_cadastre_bati": "archiver (QA bâti cadastre — passe historique)",
    "repli_pcov": "purger (repli de migration)",
    "repli_sp_residuel": "purger (repli de migration)",
    "segment_presets": "archiver (presets de segments — plus aucun lecteur)",
    "segment_preset_counts": "archiver (compteurs de presets — plus aucun lecteur)",
    "solar_api_cache": "purger (cache API solaire mort)",
    "tdl_faisa": "purger (table de travail faisa)",
    "zone_cat_p": "archiver (catégories de zone P — plus aucun lecteur)",
}


def tables_reservoirs() -> set[str]:
    """Toutes les relations déclarées servies par un réservoir."""
    return {t for rt in RESERVOIR_TABLES.values() for t in rt.tables}


def tables_carte() -> set[str]:
    """La carte complète : tout ce qu'un moteur a le droit de lire."""
    return tables_reservoirs() | set(TABLES_FABRIQUEES) | set(TABLES_EXPLOITATION) | set(POSTGIS)


def reservoirs_de(table: str) -> tuple[str, ...]:
    """Les réservoirs qui servent cette table (une table peut être partagée : ortho/IRC…)."""
    return tuple(sorted(slug for slug, rt in RESERVOIR_TABLES.items() if table in rt.tables))


def orphelines(relations: set[str]) -> set[str]:
    """Les orphelines : relations du schéma hors carte. CALCULÉ, jamais énuméré en dur."""
    return set(relations) - tables_carte()
