"""Catalogue des sources de données (brief §6).

Alimente la table `data_sources` — qui incarne la promesse « tout relié au même
endroit ». Statuts confirmés par appels RÉELS (SPIKE réseau, accès complet,
2026-06) : `connecte` = flux live vérifié (HTTP 200), `partiel`/`a_faire` =
import requis (flux ouvert indisponible), `manuel`/`sous convention` = hors
automatisation. Le bouton « tester la connexion » s'appuie sur
`connectors/*.test_connection()` (REGISTRY).

Les `name` ci-dessous sont les identifiants canoniques référencés par les couches
de la cascade (cascade/layers/*.py) et par le jeu de démo — NE PAS renommer.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..enums import DataSourceStatus as S
from ..enums import ReliabilityLevel as R
from ..models import DataSource

# (name, category, provider, access_type, status, reliability_level, rate_limit, doc, endpoint, legal, technical)
SOURCES: list[dict] = [
    # ── Cœur MVP — flux live confirmés au SPIKE (2026-06) ──
    dict(name="Cadastre (API Carto PCI)", category="cadastre", provider="IGN / API Carto",
         source_millesime="PCI Parcellaire Express (DGFiP) — « latest » ingérée",   # M125-1bis : note licence PCI
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         rate_limit=None, documentation_url="https://apicarto.ign.fr/api/doc/cadastre",
         endpoint_url="https://apicarto.ign.fr/api/cadastre/parcelle",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : DGFiP — Plan Cadastral Informatisé, via API Carto (IGN) ». Parcellaire Express (PCI), MAJ semestrielle ; BD Parcellaire gelée depuis 2019.",
         technical_notes="✓ live (HTTP 200). Lookup unitaire (parcelle/section/geom). Ingestion EN MASSE via Cadastre Etalab (bulk), pas cette API en boucle (§4)."),
    dict(name="Cadastre Etalab (bulk DGFiP/Etalab)", category="cadastre", provider="DGFiP / Etalab",
         source_millesime="Etalab cadastre — « latest » ingérée (DGFiP)",   # M125-1bis : endpoint /latest/
         access_type="téléchargement/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://cadastre.data.gouv.fr/datasets/cadastre-etalab",
         endpoint_url="https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/974/97415/cadastre-97415-parcelles.json.gz",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : DGFiP/Etalab — Plan Cadastral Informatisé ».",
         technical_notes="DOUBLON de « Cadastre (API Carto PCI) » (M71 : même donnée, canal bulk — ne compte "
                         "pas dans le bandeau Sources). ✓ live : parcelles 97415 = 5,36 Mo (.json.gz) ; "
                         "dépt 974 = 54 Mo. Source d'ingestion EN MASSE des parcelles."),
    dict(name="Urbanisme PLU/GPU (API Carto)", category="urbanisme", provider="IGN / API Carto GPU",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/zone-urba",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN), documents d'urbanisme des collectivités ».",
         technical_notes="✓ live : Saint-Paul DÉMATÉRIALISÉE (partition DU_97415). zone-urba + assiette-sup-s (SUP) OK."),
    # M-H — source des zonages d'assainissement (couches d'information CNIG typeinf 19) : distincte
    # du zonage d'urbanisme (zone-urba) bien que servie par le même Géoportail. Consommée par anc.py.
    dict(name="GPU — zonages d'assainissement", category="urbanisme", provider="IGN / Géoportail de l'urbanisme",
         source_millesime="GPU — idurba par commune ; SIG 4/24 au 11/07/2026",   # M125-1bis : layers_ingest millesime=idurba
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/municipality/document/info-surf",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN), annexes d'assainissement des collectivités ».",
         technical_notes="✓ couches d'information surfaciques typeinf=19 (« zonage d'assainissement » CNIG). Couverture SIG partielle (4/24 communes au 11/07/2026) ; ailleurs, taux de non-raccordement du secteur (INSEE RP2022), jamais une proba parcellaire (M88)."),
    # M-H — contours IRIS (maille infra-communale IGN/INSEE) : support des taux d'assainissement
    # agrégés (RP2022 EGOUL). Consommé par anc.py (ingest_iris_contours).
    dict(name="Contours IRIS (IGN/INSEE)", category="attractivite", provider="IGN / INSEE",
         access_type="WFS/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/contoursiris",
         endpoint_url="https://data.geopf.fr/wfs/ows",
         source_millesime="Contours IRIS — géographie 2024 (IGN/INSEE)",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Contours IRIS © IGN/INSEE ».",
         # M88 — maille du FAIT de secteur servi (taux RP2022 par IRIS), plus une estimation probabiliste.
         technical_notes="✓ WFS Géoplateforme, filtre code_insee 974 (330 IRIS). Maille la plus fine diffusée : support du taux de non-raccordement servi à la fiche (Sourcé secteur)."),
    dict(name="Géorisques", category="risques", provider="BRGM / MTE",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) ».",
         technical_notes="✓ live : gaspar/risques, gaspar/catnat, gaspar/azi, rga, zonage_sismique (HTTP 200). ⚠ pas d'endpoint /ppr en v1 (404)."),
    # CIRCUIT-3 lot 6.1 — CatNat au registre : arrêtés de catastrophe naturelle GASPAR, PAGINÉS
    # (répare `catnat_n`, tronqué à 10/commune). Ingestion `labuse ingest-catnat`, refresh mensuel.
    dict(name="CatNat (arrêtés GASPAR / Géorisques)", category="risques", provider="BRGM / Géorisques (GASPAR)",
         source_millesime="GASPAR — arrêtés CatNat 974 (paginés, 06/09/2026)",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~1000 req/min/IP",
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/gaspar/catnat",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) — GASPAR ».",
         technical_notes="✓ live 974 : 426 arrêtés sur 24 communes (paginé PAGE_SIZE=100). Avant CIRCUIT-3 : 239 (tronqué à 10/commune, ingestion retirée)."),
    # CIRCUIT-3 lot 6.2 — taux communaux de taxe d'aménagement (source publique : délibérations /
    # base DGFiP). Table seedée VIDE (doctrine « aucun taux inventé ») ; les taux viennent de la
    # source officielle. La calculette utilise le taux public dès qu'il existe (n'exige plus le saisi).
    dict(name="Taxe d'aménagement — taux communaux (délibérations)", category="fiscalite",
         provider="Communes / DGFiP", access_type="délibérations / CSV",
         status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         source_millesime="taux à ingérer de la source officielle — 0/24 (06/09/2026)",
         documentation_url="https://www.collectivites-locales.gouv.fr/finances-locales/taxe-damenagement",
         endpoint_url="https://www.collectivites-locales.gouv.fr/finances-locales/taxe-damenagement",
         legal_notes="Délibérations communales / base publique DGFiP — taux communaux de la part locale de la TA.",
         technical_notes="CIRCUIT-3 lot 6.2 : table taxe_amenagement_taux prête (mécanisme livré). Rates À VALIDER — aucun taux inventé."),
    dict(name="Géorisques — sites et sols pollués", category="risques", provider="BRGM / Géorisques",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~1000 req/min/IP",
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/ssp",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) ».",
         technical_notes="PÉRIMÈTRE TRANCHÉ (M74 B) : /ssp expose 4 sous-collections, LABUSE ingère les 3 "
                         "site-centrées — casias (ex-BASIAS, inventaire) + instructions (ex-BASOL, gestion) + "
                         "conclusions_sis (SIS, périmètres réglementaires L.125-6 CE) — et EXCLUT conclusions_sup "
                         "(servitude déjà portée par la couche SUP id 44, éviter le doublon). spatial_layers "
                         "kind='sol_pollue'. Vague B. last_sync_at à l'ingestion."),
    dict(name="Géorisques — cavités souterraines", category="risques", provider="BRGM / Géorisques",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~1000 req/min/IP",
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/cavites",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) ».",
         technical_notes="✓ live 05/07/2026 : /cavites (naturelle/carrière/ouvrage), lon-lat → Point. spatial_layers kind='cavite'. Vague B (# TODO étage 1)."),
    dict(name="Géorisques — mouvements de terrain", category="risques", provider="BRGM / Géorisques",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~1000 req/min/IP",
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/mvt",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) ».",
         technical_notes="✓ live 05/07/2026 : /mvt (coulée/glissement/éboulement, fiabilité), lon-lat → Point. spatial_layers kind='mvt'. Saint-Paul 160 objets. Vague C2 bonus (# TODO étage 1)."),
    dict(name="Géorisques — ICPE", category="risques", provider="BRGM / Géorisques",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~1000 req/min/IP",
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/installations_classees",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) ».",
         technical_notes="✓ live 05/07/2026 : /installations_classees (régime, statut Seveso, NAF), lon-lat → Point. spatial_layers kind='icpe'. Vague B (# TODO étage 1)."),
    dict(name="DEAL Réunion — PPR / aléas", category="risques", provider="DEAL Réunion (Lizmap)",
         source_millesime="PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)",   # M125-1bis : attrs.approbation min/max sur 164 zonages en base
         access_type="WFS/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://deal974.lizmap.com/cartes/index.php/view/map?repository=02sprinr&project=01risque",
         endpoint_url="https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=02sprinr&project=01risque",
         legal_notes="Données État — Licence Ouverte ; attribution : « Source : DEAL Réunion, PPR / aléas ». Les documents PPR sont des actes réglementaires (libres).",
         technical_notes="✓ validé spike 2026-06 : PPR_APPROUVE (zonage rouge=INTERDICTION / bleu=PRESCRIPTION, MultiPolygon EPSG:2975, champs CODE_INSEE/RISQUE/DEGRE/CODE_DEGRE) ; ALEA_INONDATION (degre FAIBLE/MOYEN/FORT + RESIDUEL_*) ; ALEA_MOUVEMENT_TERRAIN. Filtre CODE_INSEE."),
    dict(name="DVF / valeurs foncières", category="marche", provider="DGFiP / Etalab — géo-DVF",
         access_type="téléchargement/CSV", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/",
         endpoint_url="https://files.data.gouv.fr/geo-dvf/latest/csv/",
         legal_notes="Licence Ouverte + art. L.112 A LPF : interdiction de réidentifier / d'indexer — agréger, jamais nominatif. Attribution : « Source : DGFiP, Demandes de valeurs foncières (DVF) géolocalisées, via files.data.gouv.fr (géo-DVF Etalab) ».",
         technical_notes="✓ ingéré : géo-DVF Etalab (files.data.gouv.fr), CSV par département — le 974 EST couvert (dep=974, millésimes 2021–2025). Géolocalisé par id_mutation, agrégé par mutation réelle (layers_ingest.fetch_geo_dvf, fraicheur.refresh_dvf). M124 — PROFONDEUR 2014-2020 : archives brutes DGFiP (miroir data.cquest.org/dgfip_dvf, Licence Ouverte, URL exacte par ligne) → dvf_mutations_histo (dvf_histo.py, M3.5) ; frontière 2020/2021 sans recouvrement (garde ≥2021 refusée)."),
    dict(name="RGE ALTI (altimétrie)", category="topographie", provider="IGN / Géoplateforme",
         source_millesime="RGE ALTI® (IGN) — édition non enregistrée",   # M125-1bis : API alti Géoplateforme
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="5 req/s",
         documentation_url="https://geoservices.ign.fr/services-geoplateforme-altimetrie",
         endpoint_url="https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « © IGN — RGE ALTI ».",
         technical_notes="✓ live (elevations:[6.43]). Batch commune : préférer raster RGE ALTI + pente PostGIS aux milliers d'appels."),
    # ── Spécificité réunionnaise (premier rang) ──
    dict(name="Parc National de La Réunion (INPN)", category="environnement", provider="INPN/MNHN · API Carto · Région ODS",
         source_millesime="millésime 2021",   # M86 — millésime centralisé (plus de date en dur au front)
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com/explore/dataset/pnrun_2021/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/pnrun_2021/records",
         legal_notes="Licence à confirmer — jeu pnrun_2021 servi par la Région Réunion (ODS), licence du jeu à consigner (audit M6 §1.11 R8).",
         technical_notes="✓ live : pnrun_2021 champ `type` = « Coeur du Parc national » (HARD_EXCLUDE) vs « Aire d'Adhésion » (SOFT_FLAG). Aussi apicarto/nature/pn. INPN direct en maintenance au 2026-06-07."),
    dict(name="Forêts publiques (ONF)", category="environnement", provider="ONF / IGN (BD TOPO)",
         source_millesime="BD TOPO® V3 — forêt publique (IGN)",   # M125-1bis : typename BDTOPO_V3:foret_publique
         access_type="WFS", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/bdtopo", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « © IGN — BD TOPO, forêt publique ».",
         technical_notes="MESURÉ MAXIMUM (M74 C) : 65 géométries distinctes en base = 65 emprises au WFS "
                         "BDTOPO_V3:foret_publique sur l'emprise 974 (numberMatched=65). ⚠ 227 LIGNES en base = "
                         "162 doublons d'ingestion par bbox commune (features à cheval sur 2 communes comptés 2×) — "
                         "dedup à passer (dette BACKLOG). ✓ intégré auto : régime forestier ; toponyme « domaniale » "
                         "→ HARD_EXCLUDE, sinon flag fort."),
    dict(name="Potentiel foncier Région (Région ODS)", category="urbanisme", provider="Région Réunion / AGORAH",
         access_type="import", status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://peigeo.re", endpoint_url=None,
         legal_notes="Licence à confirmer (jeu Région ODS « potentiel foncier » — audit M6 §1.11 R8). Proxy de vocation INDICATIF ; ce n'est pas le zonage régional officiel (introuvable en open data), aucune portée réglementaire ni hiérarchie sur le PLU.",
         technical_notes="PROXY : le zonage SAR officiel PEIGEO est INTROUVABLE en public (data.gouv/ODS vides, "
                         "PEIGEO 503, DEAL injoignable). La vocation SAR est servie via le jeu Potentiel foncier "
                         "de la Région — 2 453 emprises intégrées (spatial_layers kind='sar'), verdicts réels sur "
                         "431 663 parcelles (couche cascade 'sar' = proxy indicatif, jamais une interdiction). "
                         "M74 A : requalifiée connecte (mesurée, intégrée) — l'ancienne note « UNKNOWN » était périmée."),
    dict(name="RPG — déclarations agricoles (IGN/ASP)", category="agricole", provider="DAAF (propre non public) · proxy RPG/IGN",
         source_millesime="proxy RPG (IGN) — RPG.LATEST, année non pinnée",   # M125-1bis : attrs.src=RPG.LATEST (38 460)
         access_type="WFS", status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://geoservices.ign.fr/services-geoplateforme-diffusion", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence à confirmer (proxy RPG servi par la Géoplateforme — non tranché à l'audit M6 §1.11). Parcelle DÉCLARÉE agricole au RPG (déclarations PAC) — usage indicatif, aucune portée réglementaire.",
         technical_notes="PROXY : le zonage SAFER/DAAF officiel est INTROUVABLE en open data. ✓ proxy intégré : "
                         "RPG.LATEST (38 460 parcelles agricoles déclarées, Géoplateforme) en flag agricole du scoring. "
                         "M74 A : requalifiée connecte (mesurée, intégrée) — le proxy est le maximum publiable, jamais présenté comme la source officielle."),
    # ── Hubs ──
    dict(name="Région Réunion Open Data (Opendatasoft)", category="hub", provider="Région Réunion (Opendatasoft)",
         access_type="REST/GeoJSON", status=S.HUB, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets",
         legal_notes="Licence à confirmer PAR JEU de données (portail Région Réunion ODS — audit M6 §1.11 R8).",
         technical_notes="✓ live : 275 datasets. Clés : pnrun_2021 (Parc cœur/adhésion), potentiel-foncier, base PLU, permis de construire, DVF, ZNIEFF."),
    dict(name="PEIGEO (hub régional)", category="hub", provider="AGORAH",
         access_type="WMS/WFS", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://peigeo.re", endpoint_url=None,
         legal_notes="Licence à confirmer par jeu (AGORAH/PEIGEO — audit M6 §1.11 R8).",
         technical_notes="⚠ Hôte injoignable depuis l'infra (HTTP 000, 2026-06-07). Fallback Région ODS / import."),
    dict(name="DEAL Réunion (WMS/WFS)", category="urbanisme", provider="DEAL Réunion",
         source_millesime="NPNRU — QP génération 2024 (DEAL/ANCT)",   # M125-1bis : anru attrs code_qp_2024 (8 quartiers)
         access_type="WMS/WFS", status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.reunion.developpement-durable.gouv.fr", endpoint_url=None,
         legal_notes="Données État — Licence Ouverte ; attribution : « Source : DEAL Réunion ». Licence à consigner couche par couche (audit M6 §1.11 R8).",
         technical_notes="SERVI PAR PROXYS : l'hôte carto DEAL (carto.reunion.developpement-durable.gouv.fr) est "
                         "INJOIGNABLE (HTTP 000). Les couches sont servies via proxys — 8 emprises ANRU intégrées "
                         "(spatial_layers kind='anru'), lues par la fiche (contexte commune). M74 A : requalifiée "
                         "connecte (mesurée, servie par proxys) — catégorie hub→urbanisme (une source, pas un portail)."),
    dict(name="Géoplateforme IGN", category="hub", provider="IGN",
         access_type="WFS/WMS/téléchargement", status=S.HUB, reliability_level=R.VERIFIE,
         rate_limit="10 req/s (téléchargement)",
         documentation_url="https://geoservices.ign.fr", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence Ouverte 2.0 (Etalab) — ouverture totale des données publiques IGN au 01/01/2021 (hors SCAN) ; attribution : « © IGN ».",
         technical_notes="✓ live : WFS GetFeature BDTOPO_V3:batiment (51 M features). BD TOPO/parcellaire ; OCS GE typename à confirmer."),
    dict(name="data.regionreunion.com — Potentiel foncier", category="potentiel", provider="Région Réunion (Opendatasoft)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com/explore/dataset/potentiel-foncier/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier/records",
         legal_notes="Licence à confirmer (jeu potentiel-foncier, Région Réunion ODS — audit M6 §1.11 R8).",
         technical_notes="MESURÉ MAXIMUM (M74 C) : base 2 453 ≈ amont 2 458 (ODS total_count, 99,8 %) — écart de "
                         "5 = filtrage géométrie. ✓ live : grain PARCELLE (section/parcelle/espacesar/zpu). Îlots "
                         "> 500 m² (bâti) / 200 m² (vierge). BONUS (§1) + porte le proxy SAR (2 453 emprises kind='sar')."),
    # ── Enrichissement ──
    dict(name="SITADEL (autorisations d'urbanisme)", category="dynamique", provider="SDES (Dido)",
         access_type="REST/CSV", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="4 exports CSV/run",
         documentation_url="https://www.statistiques.developpement-durable.gouv.fr/donnees-des-permis-de-construire-et-autres-autorisations-durbanisme",
         endpoint_url="https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles/{rid}/csv",
         legal_notes="Licence Ouverte — attribution : « Source : SDES, Sitadel ». Pétitionnaires personnes MORALES seulement (physiques anonymisées à la source).",
         technical_notes="✓ live 10/07/2026 (Wave Sitadel3). Flux national Dido (dataset 6513f0189d7d312c80ec5b5b), 4 datafiles (logements/locaux/PA/PD), filtre serveur DEP_CODE=eq:974, delta DATE_REELLE_AUTORISATION=gte:. MAJ mensuelle, historique 2013+. Ingestion : permits_sdes.py (upsert permit_id, refresh cron). ⚠ voie Région ODS morte 2023-09 (permits.py legacy). last_sync_at posé à l'ingestion."),
    dict(name="BD TOPO IGN", category="topographie", provider="IGN / Géoplateforme",
         source_millesime="BD TOPO® V3 (IGN) — édition non enregistrée",   # M125-1bis : typename BDTOPO_V3 (config wfs_layers)
         access_type="WFS/téléchargement", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/bdtopo", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « © IGN — BD TOPO ».",
         technical_notes="✓ live : BDTOPO_V3:batiment (bâti, voirie, hydrographie, équipements)."),
    dict(name="Base Adresse Nationale", category="acces", provider="DINUM / IGN",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://adresse.data.gouv.fr", endpoint_url="https://api-adresse.data.gouv.fr/search/",
         legal_notes="Licence Ouverte depuis le 01/01/2020 (fin de l'ODbL ; ne pas confondre avec BANO, qui reste ODbL) — attribution : « Source : Base Adresse Nationale (DINUM/IGN) ».",
         technical_notes="✓ live : géocodage + voie la plus proche."),
    dict(name="OpenStreetMap / Overpass", category="signal", provider="OSM",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://wiki.openstreetmap.org/wiki/Overpass_API", endpoint_url="https://overpass-api.de/api/interpreter",
         legal_notes="ODbL 1.0 — attribution : « © les contributeurs d'OpenStreetMap — données disponibles sous ODbL (openstreetmap.org/copyright) ». Couches dérivées d'OSM (aménités, faux positifs) = bases dérivées : disponibles sous ODbL sur demande (share-alike, ODbL §4.4-4.6). Signal complémentaire, JAMAIS vérité juridique.",
         technical_notes="✓ live (UA applicatif requis, sinon 406). Faux positifs géométriques (cemetery, pitch, parking, school). Cacher agressivement."),
    dict(name="BPE INSEE", category="attractivite", provider="INSEE",
         access_type="import", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="millésime 2025 (géographie au 01/01/2025)",
         documentation_url="https://www.insee.fr/fr/statistiques/8217525",
         endpoint_url="https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.zip",
         legal_notes="Licence Ouverte / Etalab 2.0 — attribution : « Source : Insee, Base permanente des équipements ».",
         technical_notes="M137-U : ingéré → spatial_layers kind='amenite_bpe' (fichier national géolocalisé, "
                         "filtre DEP=974, 36 821 équipements, subtype = domaine A..G). Couche ÉQUIPEMENTS "
                         "DISTINCTE d'OSM (kind 'amenite') — deux items par source, jamais fusionnés. Le "
                         "modèle (acces_equipements) lit toujours OSM."),
    dict(name="Filosofi INSEE (carreaux 200 m)", category="attractivite", provider="INSEE",
         source_millesime="millésime 2021",   # M86 — millésime centralisé (plus de date en dur au front)
         access_type="import GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.insee.fr/fr/statistiques/8735162?sommaire=8735243", endpoint_url=None,
         legal_notes="Licence Ouverte — attribution : « Source : Insee, Filosofi 2021 ».",
         technical_notes="Table filosofi_carreaux_200m : 14 773 carreaux 200 m (974, EPSG:2975), millésime 2021 "
                         "(dernier millésime carroyé publié — vérifié M5.1 FRAICHEUR). Alimente le score P v2 "
                         "(niveau de vie, pauvreté, part propriétaires, densité) "
                         "(proprio-occupant). Ligne ajoutée à l'audit M6 §1.11 R7 (source exploitée mais absente du catalogue)."),
    dict(name="BODACC (procédures collectives)", category="economie", provider="DILA (Opendatasoft)",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="throttle poli",
         documentation_url="https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/",
         endpoint_url="https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records",
         legal_notes="Licence Ouverte v2.0 — attribution : « Source : DILA — BODACC ». RGPD : signal INTERNE de priorisation (personnes morales, open data), jamais un export nominatif de masse (règle d'archi #2).",
         technical_notes="✓ live 05/07/2026 (schéma vérifié, record A200902491993). Filtre familleavis='collective' (BODACC A). Interrogé par SIREN (registre[]), batché registre IN(...). Vague A1 : flag foncier_sous_pression (# TODO étage 2). last_sync_at posé à l'ingestion."),
    dict(name="INPI RNE (dirigeants)", category="economie", provider="INPI (Registre National des Entreprises)",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="throttle poli (1 req/SIREN, token JWT)",
         documentation_url="https://www.inpi.fr/ressources/propriete-intellectuelle/acces-aux-api-et-ftp",
         endpoint_url="https://registre-national-entreprises.inpi.fr/api/companies/{siren}",
         legal_notes="Licence INPI RNE 2024 (licence spécifique homologuée, art. L. 323-2 CRPA) : réutilisation, y compris commerciale, autorisée (art. 2.1) ; attribution exigée (art. 2.4, source + date de dernière mise à jour) : « Source : INPI — Registre national des entreprises, données du [date de dernière synchronisation] », sans suggérer une caution de l'INPI ; restrictions de recherche art. A.123-69 c. com. (art. 2.5). RGPD : personnes morales en open data complet ; données d'une personne PHYSIQUE conservées seulement si l'entreprise est diffusible. Signal INTERNE de priorisation, jamais un export nominatif de masse (règle d'archi #2). Naissance au MOIS.",
         technical_notes="✓ login live 05/07/2026 (schéma vérifié, siren 913037362 SCI ALOE). Auth POST /api/sso/login (compte portail, identifiants en env INPI_API_*, JAMAIS en dur ; SFTP abandonné = firewall IP). GET /api/companies/{siren}. Champs : composition.pouvoirs[].individu.descriptionPersonne.dateDeNaissance (AAAA-MM). ⚠ pas de procédures collectives dans cet endpoint (restent BODACC A1). Vague A3 : signal propension_vendre / âge dirigeant (# TODO étage 2). last_sync_at posé à l'ingestion."),
    dict(name="50 pas géométriques — limite haute (DEAL)", category="reglement", provider="DEAL Réunion (Lizmap)",
         source_millesime="cadastre 1877 (géoréf. 2012/1950)",   # M86 — millésime centralisé
         access_type="WFS/GeoJSON", status=S.CONNECTE, reliability_level=R.A_CONFIRMER, rate_limit="1 requête",
         documentation_url="https://deal974.lizmap.com/cartes/",
         endpoint_url="https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=00cartogenerale&project=deal_reunion",
         legal_notes="Données État — Licence Ouverte ; attribution : « Source : DEAL Réunion, 50 pas géométriques (limite haute) ». Limite numérisée du cadastre 1877 (géoréf. orthos 2012/1950) — indicative, la bande polygonale officielle n'est pas diffusée.",
         technical_notes="✓ live 10/07/2026 (LOT 6 data-gap) : couche LIMITE_HA, 163 tronçons (~184 km). CORRIDOR ±90 m matérialisé (approximation documentée) → kind='cinquante_pas', flag « au contact » Stage 1 faible. 16 099 parcelles touchées."),
    dict(name="Classement sonore ITT (Cerema)", category="reglement", provider="Cerema (Cartagène)",
         source_millesime="arrêtés déc. 2023",   # M86 — millésime centralisé
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="1 requête (export intégral)",
         documentation_url="https://cartagene.cerema.fr",
         endpoint_url="https://cartagene.cerema.fr/server/rest/services/Hosted/Routes_classement_sonore_La_Reunion_V2/FeatureServer/0/query",
         legal_notes="Licence Ouverte 2.0 (open data Cerema) — attribution : « Source : Cerema, classement sonore ITT ». Classement en vigueur : arrêtés préfectoraux 14-15/12/2023.",
         technical_notes="✓ live 10/07/2026 (LOT 3 data-gap) : 1 004 tronçons, catégories 1-5 + sect_bruit (largeur du secteur affecté). Bandes MATÉRIALISÉES par buffer 2975 → spatial_layers kind='bruit_route'. Couche cascade : cat 1-2 moyen, 3-5 faible (R.571-32 CE). ⚠ PEB aérodromes BLOQUÉ (PDF préfecture uniquement, pas de SIG open data 974)."),
    dict(name="SUP — assiettes GPU (API Carto)", category="reglement", provider="IGN (Géoportail de l'urbanisme)",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="1 req/commune/géométrie",
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/assiette-sup-s",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN) ». Assiettes telles que téléversées par les gestionnaires — exhaustivité variable par catégorie.",
         technical_notes="✓ live 10/07/2026 (LOT 4 data-gap, Le Port : pm1/pm2/ac2/ac3/el10). Endpoints assiette-sup-s/l/p par bbox de commune → spatial_layers kind='sup' (subtype=suptype). Couche cascade `sup` : malus par catégorie (t5 fort ; t4/t7/i4/i1/i3 moyen ; défaut faible ; pm*/ac1-2/el10 info ×0 anti-double-compte). Plafond 1000 features/réponse loggé."),
    dict(name="Recherche d'entreprises (DINUM)", category="economie", provider="DINUM (api.gouv.fr)",
         source_millesime="Sirene INSEE / RNE INPI (api.gouv.fr) — courant",   # M125-1bis : note seed
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~7 req/s (throttle 5 req/s)",
         documentation_url="https://recherche-entreprises.api.gouv.fr/docs/",
         endpoint_url="https://recherche-entreprises.api.gouv.fr/search",
         legal_notes="Licence Ouverte (open data DINUM, agrégat INSEE/RNE) — attribution : « Source : Insee (Sirene) / INPI (RNE), via recherche-entreprises.api.gouv.fr ». RGPD : personnes morales ; signal INTERNE de priorisation (Score V), jamais un export nominatif de masse (règle d'archi #2).",
         technical_notes="✓ live 10/07/2026 (schéma vérifié, SHLMR 310895172). Sans clé. Score V : enrichissement propriétaire PAR SIREN (état administratif A/C, siège, NAF, catégorie juridique, dirigeants naissance AAAA-MM) → cache owner_enrichment ; fallback matching PAR DÉNOMINATION (§4.2) → owner_denom_lookup. Complète le RNE (état administratif absent de la vague A3)."),
    dict(name="QPV 2024 (ANCT)", category="fiscal", provider="ANCT (Agence nationale cohésion des territoires)",
         source_millesime="génération 2024",   # M86 — millésime centralisé
         access_type="téléchargement/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.data.gouv.fr/datasets/quartiers-prioritaires-de-la-politique-de-la-ville-qpv",
         endpoint_url="https://static.data.gouv.fr/resources/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/20260115-204323/qpv-2024-geojson.zip",
         legal_notes="Licence Ouverte — attribution : « Source : ANCT, quartiers prioritaires de la politique de la ville, génération 2024 ». Décret 2023-1314 (en vigueur 01/01/2024).",
         technical_notes="✓ live 05/07/2026 : zip GeoJSON national, fichier ...Outre_Mer_WGS84, filtre insee_dep=974 → 57 QPV / 13 communes (MultiPolygon WGS84). spatial_layers kind='qpv'. Sert le BILAN PROMOTEUR (dispositifs/TVA en QPV), PAS le score (# TODO bilan). TVA 2,1% DOM = règle globale (pas un zonage). NPNRU absent open data. VEFA/ECLN = N/A DOM (métropole only)."),
    dict(name="DPE ADEME (logements existants)", category="energie", provider="ADEME",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="~1200 req/min (authentifié) / moins anonyme",
         documentation_url="https://data.ademe.fr/datasets/dpe03existant",
         endpoint_url="https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines",
         legal_notes="Licence Ouverte — attribution : « Source : ADEME, base DPE ». RGPD : diagnostic du bien, pas nominatif.",
         technical_notes="✓ live 05/07/2026 : jeu dpe03existant (3CL réformée). 974 = 910 DPE, Saint-Paul 168. ⚠ REPRÉSENTATIVITÉ : DPE obligatoire en DROM seulement depuis le 01/07/2024 → base JEUNE en croissance, couvre les biens diagnostiqués depuis 2021, PAS tout le parc — signal « positif quand présent », jamais exhaustif. ⚠ _geopoint ADEME FAUX au 974 (100% hors Réunion) → re-géocodage BAN (citycode). Table dpe_records, signal passoire_thermique (# TODO étage 2)."),
    dict(name="Cartofriches (Cerema)", category="foncier", provider="Cerema / DGALN",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="non exposé (throttle prudent)",
         documentation_url="https://schema.data.gouv.fr/cnigfr/schema-friches",
         endpoint_url="https://apidf-preprod.cerema.fr/cartofriches/geofriches/",
         legal_notes="Licence Ouverte 2.0 — attribution : « Source : Cerema, Cartofriches ». MAJ trimestrielle.",
         technical_notes="✓ live 05/07/2026 (INSEE 97415) : host apidf-preprod.cerema.fr (apidf.cerema.fr ne résout pas), sans clé. /geofriches (GeoJSON MultiPolygon + unite_fonciere_refcad = IDU exacts), /friches/{id} (78 champs). Couverture 974 = 373 friches. spatial_layers kind='friche', rattachement EXACT via refcad. Vague C1 (# TODO étage 1/2). last_sync_at à l'ingestion."),
    dict(name="SIRENE", category="economie", provider="INSEE / annuaire-entreprises",
         source_millesime="Sirene INSEE — état courant (non versionné)",   # M125-1bis : note seed
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://recherche-entreprises.api.gouv.fr/docs", endpoint_url="https://recherche-entreprises.api.gouv.fr/search",
         legal_notes="Licence Ouverte — attribution : « Source : Insee, Sirene, via recherche-entreprises (DINUM) ».",
         technical_notes="✓ live : confirme une personne morale propriétaire en attendant les Fichiers fonciers."),
    # ÉTUDE DE ZONE Z1 — SIRENE établissements ADRESSÉS/GÉOCODÉS (annuaire pour la chalandise). DISTINCT
    # de « SIRENE » ci-dessus (qui enrichit le propriétaire par SIREN). Fichier géolocalisé volumineux →
    # ingestion par CLI (labuse ingest-sirene-etab --file …). Statut de diffusion INSEE respecté.
    dict(name="SIRENE établissements géolocalisés", category="economie", provider="INSEE / data.gouv",
         source_millesime="SIRENE géolocalisé — publication mensuelle INSEE",
         access_type="parquet (data.gouv)", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.data.gouv.fr/fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/",
         legal_notes="Licence Ouverte 2.0 — attribution : « Source : Insee, Sirene ». Statut de diffusion respecté : les établissements en diffusion partielle (personnes physiques opposées) n'ont ni nom ni adresse stockés/affichés (obligation légale).",
         technical_notes="Table dédiée `sirene_etablissements`. CADENCE MENSUELLE (cron Réunion, CLI ingest-sirene-etab) : fichier INSEE de géolocalisation (x_longitude/y_latitude GPS + qualite_xy + plg_iris/plg_qp24) JOINT à StockEtablissement (NAF fin, tranche d'effectif, état, diffusion) sur le SIRET, via DuckDB en lecture parquet distante, filtre 974 ACTIFS. Position ingérée en lon/lat direct (aucune reprojection). Millésime = date de publication du fichier géo (source_millesime mis à jour à chaque run)."),
    # ÉTUDE DE ZONE Z1 — MOBPRO (mobilités domicile-travail) : emplois au lieu de travail par commune.
    dict(name="MOBPRO (mobilités domicile-travail, INSEE)", category="economie", provider="INSEE (RP)",
         source_millesime="MOBPRO INSEE — fichier détail (millésime RP)",
         access_type="import CSV", status=S.MANUEL, reliability_level=R.VERIFIE,
         documentation_url="https://www.insee.fr/fr/statistiques/7630376",
         legal_notes="Licence Ouverte — attribution : « Source : Insee, MOBPRO ».",
         technical_notes="Table `mobpro_commune` (emplois au lieu de travail agrégés par commune, pondérés IPONDI). ABANDONNÉ pour l'Étude de zone (ZONE-DONNÉES LOT 2 : l'emploi au lieu de travail n'est pas traité à une maille infracommunale — les emplois de zone viennent des tranches d'effectif SIRENE). Table conservée, non supprimée."),
    # ZONE-DONNÉES LOT 5 — trafic moyen journalier annuel sur les routes nationales (Région Réunion).
    dict(name="Trafic RN (Région Réunion — SIR)", category="economie", provider="Région Réunion (Système d'Information Routier)",
         source_millesime="Trafic RN Région — comptages (millésime porté par tronçon)",
         access_type="ODS (open data)", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com/explore/dataset/trafic-mja-rn-lareunion/",
         legal_notes="Licence Ouverte — attribution : « Source : Région Réunion ».",
         technical_notes="Table `trafic_rn` (tronçons LineString, route/annee/tmja véhicules-jour). CLI ingest-trafic-rn. Sert le trafic VÉHICULES des ROUTES NATIONALES traversant/bordant la zone (Étude de zone) — jamais un flux piéton, jamais le réseau départemental/communal (non ouvert)."),
    dict(name="IGN BD CARTO V5 — occupation du sol", category="occupation_sol", provider="IGN / Géoplateforme",
         source_millesime="BD CARTO® V5 — occupation du sol (IGN, proxy)",   # M125-1bis : attrs.src=BDCARTO_V5 (1 643 objets)
         access_type="WFS", status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://geoservices.ign.fr/ocsge", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « © IGN — BD CARTO (proxy OCS GE) ».",
         technical_notes="PROXY : OCS GE 974 natif non exposé en WFS geopf (OCSGE:occupation_du_sol → 400). Proxy "
                         "intégré : BDCARTO_V5:occupation_du_sol (naturel/agricole/artificialisé), lu par le scoring. "
                         "Signal non juridique. MESURÉ MAXIMUM vs proxy (M74 C) : 1 643 géométries distinctes en base = "
                         "1 643 au WFS BDCARTO 974 (numberMatched). ⚠ 3 250 LIGNES = 1 607 doublons d'ingestion par bbox "
                         "commune (dedup à passer, dette BACKLOG). Le proxy BDCARTO n'est PAS le plafond de l'OCS GE natif "
                         "(plus fin) — la couverture OCS GE réelle reste non mesurable sans exposition WFS. M74 A : connecte."),
    # M137-U — UNE seule ligne ZNIEFF, pointée sur la source COMPLÈTE (INPN via Géoplateforme WFS).
    # L'ancien jeu Région Réunion ODS est un DOUBLON AMPUTÉ (type II seul) → écarté (dit ci-dessous),
    # pas une 2e ligne. L'ancien nom « ZNIEFF (INPN / Région) » est purgé par la CLI znieff-build.
    dict(name="ZNIEFF (INPN/MNHN)", category="environnement", provider="INPN/MNHN · PatriNat",
         access_type="WFS/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="INPN, mise à jour 29/08/2025",
         documentation_url="https://www.data.gouv.fr/datasets/inventaire-des-zones-naturelles-dinteret-ecologique-faunistique-et-floristique-znieff",
         endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence Ouverte / Etalab — attribution : « Source : INPN/MNHN (PatriNat) ».",
         technical_notes="M137-U : ingéré → spatial_layers kind='znieff' via Géoplateforme WFS "
                         "(patrinat_znieff1/znieff2). CONTINENTAL type I (134) + type II (28) = 162. "
                         "MARINES EXCLUES (znieff*_mer) : en mer, aucune intersection avec des parcelles "
                         "constructibles. CONTRAINTE hors cascade (études d'impact, risque de recours). Le jeu "
                         "Région Réunion ODS est un doublon amputé (28 = type II seul, sans champ type) → écarté."),
    # ── Spécifiques / accès restreint ──
    dict(name="ABF / Monuments historiques", category="patrimoine", provider="Base Mérimée (Ministère Culture)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.culture.gouv.fr/explore/dataset/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/",
         endpoint_url="https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/records",
         legal_notes="Licence Ouverte (POP open data) — attribution : « Source : Ministère de la Culture, base Mérimée ».",
         technical_notes="MESURÉ MAXIMUM (M74 C) sur les MONUMENTS : 200 tampons en base ≈ 200 immeubles MH 974 "
                         "(amont data.gouv, dataset national). ⚠ la couche 'abf' compte des TAMPONS ~500 m autour des "
                         "MH, PAS les périmètres ABF/SPR réglementaires (PDA + covisibilité) qui sont un objet distinct "
                         "non mesuré. ⚠ ENDPOINT MORT : data.culture.gouv.fr (ODS) décommissionné (301→SPA, plus d'API) "
                         "— re-ingestion à re-sourcer via le dump data.gouv ; les 200 en base datent du dernier run "
                         "OK (05/07/2026). FLAG QUALITÉ étage 1, PAS exclusion étage 0 ; « covisibilité à instruire »."),
    dict(name="INPN / patrinat — espaces protégés", category="environnement", provider="INPN/MNHN (espaces protégés) · ENS dép. non public",
         source_millesime="INPN/patrinat espaces protégés — passe 05/07/2026",   # M125-1bis : note seed (proxy)
         access_type="WFS", status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://inpn.mnhn.fr/", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Licence à confirmer (couches espaces protégés INPN/patrinat — non tranché à l'audit M6 §1.11). Espaces protégés réglementaires (INPN) ; ce n'est PAS le zonage ENS départemental (introuvable en open data), aucun droit de préemption départemental déduit.",
         technical_notes="PROXY (M74 A : requalifiée connecte, mesurée). ENS départemental propre INTROUVABLE en public. ✓ espaces protégés réglementaires intégrés (APB/RNN/réserve biologique/CEN/conservatoire littoral, patrinat Géoplateforme/INPN) — 73 emprises, 21/24 communes. Les 3 restantes (Le Port, Saint-André, Sainte-Suzanne) : « vérifié N/A 05/07/2026 » — passe INPN a tourné (parc national + forêt présents) mais 0 espace protégé de ces types (port urbain / plaines côtières agricoles). Couche ENS départementale officielle À DEMANDER au mail AGORAH/DEAL en attente. Ne rien inventer."),
    dict(name="VRD / assainissement (SPANC)", category="reseaux", provider="EPCI",
         access_type="manuel", status=S.MANUEL, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None,
         legal_notes="Licence à confirmer (données EPCI, champ manuel — non tranché à l'audit M6 §1.11).",
         technical_notes="Collectif vs non collectif : décisif. Souvent pas de donnée ouverte fine → lien EPCI + champ manuel."),
    # M74 A — LA VRAIE SOURCE PROPRIÉTAIRE, absente du catalogue (surfacée par l'audit) : le fichier
    # DGFiP « parcelles des personnes morales » (open data Licence Ouverte v2) porte les 82 701 liens
    # parcelle↔PM lus par la fiche (bloc Propriétaire) — à ne pas confondre avec « Fichiers fonciers
    # (Cerema) » (conventionné, non branché, 100 % UNKNOWN). Ingérée par ingestion/personnes_morales.py.
    # RADAR (pige) · P456 D4 — la collecte HUMAINE d'annonces au registre. Fraîcheur = date de dernière
    # COLLECTE (max(date_saisie) de pige_annonces), JAMAIS une date de run. Cadence quotidienne (rituel Vic).
    dict(name="Radar (pige d'annonces)", category="marche", provider="LABUSE — collecte humaine",
         source_millesime="Collecte manuelle — biens en vente (faits + lien)",
         source_cadence="quotidien", access_type="saisie admin (100% humaine)",
         status=S.MANUEL, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None,
         legal_notes="Faits extraits d'annonces PUBLIQUES + lien de redirection vers la source ; captures "
                     "conservées en interne, aucune coordonnée vendeur, aucune republication (doctrine RADAR §2). "
                     "Collecte 100 % HUMAINE : aucun code ne requête un portail.",
         technical_notes="Fraîcheur = max(date_saisie) de pige_annonces (dernière collecte), posée par "
                         "`pige.enregistrer_fraicheur()`. Hors scoring. Tables pige_* isolées. Le rituel quotidien "
                         "de Vic est décrit dans docs/EXPLOITATION.md."),
    dict(name="DGFiP — parcelles des personnes morales", category="proprietaire", provider="DGFiP",
         source_millesime="Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)",   # KF-2 L1/L3
         source_cadence="annuelle", source_horizon_at=date(2025, 1, 1),   # KF-2 L3 : cadence + dernière situation
         access_type="téléchargement/CSV", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.economie.gouv.fr/explore/dataset/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/",
         endpoint_url="https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_parcelles_situation_2025_dpts_57_a_976_zip",
         legal_notes="Licence Ouverte v2 — attribution : « Source : DGFiP — parcelles des personnes morales ». "
                     "RGPD-safe : personnes MORALES uniquement (commune/État/SEM/bailleur/SCI), aucune personne physique.",
         technical_notes="M74 A : source AJOUTÉE au catalogue (elle alimentait le produit sans y figurer). KF-2 L1 : "
                         "PANEL MILLÉSIMES exploité — pm_proprietaires_millesimes (461 570 lignes 2019→2024, 24/24 "
                         "communes, siren+dénom 100 %, ingestion/pm_millesimes.py) UNI au millésime 2025 servi "
                         "(parcelle_personne_morale, 82 701, JAMAIS écrasé). Fiche : timeline propriétaire PM + DIFF "
                         "annuel CONSTATÉ (proprietaire_historique.py, hors scoring). Cadence ANNUELLE (situation au "
                         "1ᵉʳ janvier) ; rafraîchissement : `labuse ingest-pm-millesimes` (cf. EXPLOITATION-CRON.md). "
                         "⚠ 2025 versionné disponible en amont, non ré-ingéré (servi via l'union) ; pic 2019→2020 = "
                         "discontinuité de complétude SIREN, pas des ventes (KF-102). Distincte des Fichiers fonciers Cerema."),
    dict(name="Fichiers fonciers (Cerema)", category="proprietaire", provider="DGFiP / Cerema",
         access_type="import", status=S.MANUEL, reliability_level=R.SOUS_CONVENTION,
         documentation_url="https://datafoncier.cerema.fr", endpoint_url=None,
         legal_notes="NON INTÉGRÉ — aucune donnée ingérée. Acte d'engagement DGALN/DGFiP/Cerema : usage limité aux finalités déclarées, DÉMARCHAGE COMMERCIAL INTERDIT, rediffusion interdite → incompatible avec la prospection LABUSE (audit M6 §1.11 R1 : à trancher AVANT toute signature de convention). Version anonymisée : physiques masquées (_X_), morales complètes → RGPD-safe.",
         technical_notes="M74 A : RESTE manuel (mesuré, PAS requalifiée). La couche cascade 'proprietaire' qui la "
                         "cite renvoie 100 % UNKNOWN (parcel_source_results VIDE — convention non branchée). Les "
                         "82 701 liens parcelle↔personne morale du produit viennent en réalité de « DGFiP — parcelles "
                         "des personnes morales » (open data, ligne distincte), PAS de cette source conventionnée. "
                         "idprocpte / idprodroit → nb_droits_propriete = signal d'indivision, en attente de convention."),
    dict(name="Cerema / GéoLittoral — indicateur d'érosion côtière", category="risques", provider="Cerema / GéoLittoral",
         source_millesime="millésime 2018",   # M86 — millésime centralisé
         access_type="import/SHP", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.geolittoral.developpement-durable.gouv.fr/indicateur-national-de-l-erosion-cotiere-a1434.html",
         endpoint_url="https://geolittoral.din.developpement-durable.gouv.fr/telechargement/couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip",
         legal_notes="Licence Ouverte 2.0 (open data Cerema/GéoLittoral) — attribution : « Source : Cerema / GéoLittoral, indicateur national de l'érosion côtière ».",
         technical_notes="✓ intégré : SHP indicateur national d'érosion côtière (Réunion, EPSG:2975→4326). Champ `taux` (m/an) : recul fort ≤ -1 → exclude, recul modéré → flag."),
    # ── Mandat Wave Détection Ortho ──
    dict(name="BD ORTHO 20 cm (IGN)", category="imagerie", provider="IGN / Géoplateforme",
         access_type="WMS", status=S.CONNECTE, reliability_level=R.VERIFIE,
         rate_limit="gratuit sans clé ; 4 requêtes simultanées (politesse)",
         documentation_url="https://geoservices.ign.fr/bdortho",
         endpoint_url="https://data.geopf.fr/wms-r (ORTHOIMAGERY.ORTHOPHOTOS)",
         legal_notes="Licence Ouverte Etalab — usage commercial OK, attribution IGN obligatoire (UI).",
         technical_notes="✓ live 11/07/2026. MILLÉSIME 974 = 2025 (fiche IGN dates de prises de vues) "
                         "— l'âge de l'image = l'âge de la vérité terrain. Mode retenu : WMS EPSG:2975 "
                         "natif 2560×2560 px (512 m à 20 cm), 5 041 tuiles ciblées (bâti ∪ parkings) "
                         "≈ 6 Go de cache temporaire vs ~50-80 Go de dalles JP2. Re-survol ~3-4 ans "
                         "→ pas de cron, commande --refresh (Lot 7)."),
    dict(name="RGE ALTI 5 m (IGN)", category="terrain", provider="IGN / Géoplateforme",
         source_millesime="RGE ALTI® 5 m (IGN) — édition non enregistrée",   # M125-1bis : raster 5 m Géoplateforme
         access_type="import raster", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/rgealti",
         endpoint_url=None,
         legal_notes="Licence Ouverte Etalab.",
         technical_notes="DOUBLON de « RGE ALTI (altimétrie) » (M71 : même référentiel IGN, résolution 5 m — "
                         "ne compte pas dans le bandeau Sources). Déjà ingéré au data-gap : raster de PENTE dérivé conservé "
                         "(rgealti_pente_5m, PostGIS raster SRID 2975, 2 793 dalles) — réutilisé "
                         "tel quel par wave-ortho Lot 1 (pente non bâtie), aucun re-téléchargement."),
    # ── Mandat Wave ANC & Végétation ──
    dict(name="INSEE RP2022 — fichier détail Logements (EGOUL)", category="assainissement",
         provider="INSEE", access_type="import CSV/zip", status=S.CONNECTE,
         reliability_level=R.VERIFIE,
         documentation_url="https://www.insee.fr/fr/statistiques/8647099",
         endpoint_url="https://www.insee.fr/fr/statistiques/fichier/8647099/RP2022_logemt.zip",
         source_millesime="RP2022 — fichier détail Logements, publié le 16/10/2025 (INSEE)",
         legal_notes="Licence Ouverte Etalab — attribution INSEE obligatoire (UI).",
         # M88 — sert le FAIT de secteur (taux de non-raccordement, Sourcé secteur), jamais une proba
         # parcellaire. Variable EGOUL agrégée par IRIS/commune ; le taux BRUT est servi tel quel.
         technical_notes="✓ Variable EGOUL (mode d'évacuation des eaux usées, "
                         "DOM uniquement : 1=égout, 2=fosse, 3=puisard, 4=sol), pondérée IPONDL, "
                         "diffusée à l'IRIS (330 IRIS 974). Agrégé → anc_maille_taux (iris + commune) : "
                         "taux de non-raccordement du SECTEUR servi à la fiche. 148 307 rés. principales 974."),
    dict(name="GPU — zonages d'assainissement (info-surf typeinf 19)", category="assainissement",
         source_millesime="GPU — idurba par commune ; SIG 4/24 au 11/07/2026",   # M125-1bis (doublon info-surf)
         provider="IGN / Géoportail de l'urbanisme", access_type="REST/GeoJSON",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/info-surf",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN), zonages d'assainissement des collectivités ».",
         technical_notes="DOUBLON de « GPU — zonages d'assainissement » (M71 : même couche GPU, canal info-surf — "
                         "ne compte pas dans le bandeau Sources). Constat 11/07/2026 : 4 communes/24 en SIG (L'Étang-Salé, Le Port, "
                         "Saint-Denis, Saint-Paul) → spatial_layers kind='zonage_assainissement'. "
                         "Les 20 autres : PDF d'enquête publique au mieux (intercos) — noté, passé. "
                         "Classification des libellés en config (anc_vegetation.yaml)."),
    dict(name="Office de l'eau Réunion — Chroniques de l'eau", category="assainissement",
         provider="Office de l'eau Réunion", access_type="seed CSV (PDF)", status=S.CONNECTE,
         reliability_level=R.A_CONFIRMER,
         documentation_url="https://eaureunion.fr/fileadmin/user_upload/Chroniques/2025/"
                           "25.12.17_CHRONIQUES_de_L_EAU_149.pdf",
         endpoint_url=None,
         legal_notes="Licence à confirmer (publication Office de l'eau Réunion — non tranché à l'audit M6 §1.11).",
         technical_notes="SERVIE à la fiche depuis M95 (démasquée M97, audit M96 G1) : source du classement "
                         "« Sourcé · commune » des 3 communes intégralement en ANC — Salazie, La Plaine des "
                         "Palmistes, Petite-Île (anc_office_eau_commune, branche source_commune d'anc_service). "
                         "Chronique n°149 (déc. 2025, données 2023), chiffres par commune du texte p. 13 → seed "
                         "versionné data/anc/office_eau_chronique_149_2023.csv (pas de scraping du PDF). "
                         "Second usage : calage/contrôle croisé INSEE (calage_office_eau, QA)."),
    dict(name="BD ORTHO IRC (IGN)", category="imagerie", provider="IGN / Géoplateforme",
         access_type="WMS", status=S.CONNECTE, reliability_level=R.VERIFIE,
         rate_limit="gratuit sans clé ; 4 requêtes simultanées (politesse)",
         documentation_url="https://geoservices.ign.fr/bdortho",
         endpoint_url="https://data.geopf.fr/wms-r (ORTHOIMAGERY.ORTHOPHOTOS.IRC)",
         legal_notes="Licence Ouverte Etalab — attribution IGN obligatoire (UI).",
         technical_notes="✓ live 11/07/2026 (couverture 974 constatée). Infrarouge fausses "
                         "couleurs : PIR=canal R, rouge=canal G → pseudo-NDVI. Même grille "
                         "ortho_tiles (512 m), 0,4 m/px suffit (cache data/ortho_irc ≈ 2 Go)."),
    dict(name="LiDAR HD — MNH 50 cm (IGN)", category="terrain", provider="IGN / Géoplateforme",
         source_millesime="LiDAR HD MNH — dalles publiées 25/06/2025 (IGN)",   # M125-1bis : note seed (2 665 dalles)
         access_type="WMS GeoTIFF", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://diffusion-lidarhd.ign.fr/mnx/",
         endpoint_url="https://data.geopf.fr/wms-r "
                      "(IGNF_LIDAR-HD_MNH_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S)",
         legal_notes="Licence Ouverte Etalab — attribution IGN obligatoire (UI).",
         technical_notes="✓ constaté 11/07/2026 : couverture 974 COMPLÈTE (2 665 dalles MNH "
                         "publiées 25/06/2025 — 1er DROM couvert). Streamé par tuile à 1 m/px "
                         "en GeoTIFF float32, jamais stocké. MNH inclut le sursol bâti → croisé "
                         "NDVI. Fallbacks MNS Corrélé/texture du mandat : non nécessaires."),
    dict(name="Parkings OSM (loi APER)", category="energie", provider="OpenStreetMap",
         access_type="Overpass/GeoJSON", status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dparking",
         endpoint_url="https://overpass-api.de/api/interpreter",
         legal_notes="ODbL 1.0 — attribution : « © les contributeurs d'OpenStreetMap — données disponibles sous ODbL (openstreetmap.org/copyright) ». parkings_aper = base dérivée d'OSM : disponible sous ODbL sur demande (share-alike).",
         technical_notes="M75 : EXPLOITÉ — obligation APER en information sur la fiche (tiroir Urbanisme) + "
                         "exports. Donnée refiltrée au SEUIL LÉGAL 1 500 m² (loi 2023-175 art. 40, décret "
                         "2024-1023 ; scripts/m75_refiltre_parkings_aper_1500.sql) : 450 parkings soumis "
                         "(426 en 1 500-10 000 m² éch. 2028, 24 > 10 000 m² éch. 2026), 451 sous le seuil. "
                         "amenity=parking (polygones) → parkings_aper, surface = ST_Area OSM. Complétude "
                         "déclarative OSM : volumétrie = plancher, pas un recensement (« potentiellement concerné »)."),
    # M106 P3 — dispositifs fiscaux TERRITORIAUX servis comme attributs de commune (patron M95,
    # seed data/fiscal/territoire_fiscal.csv, service territoire_fiscal.attributs_commune).
    # INTERDIT ABSOLU du mandat : aucun chiffre fiscal servi (ni taux, ni plafond, ni calcul) —
    # LABUSE sert le fait territorial sourcé/daté, le fiscaliste tranche. Le radar sonde les
    # pages Légifrance (repli HEAD automatique sur endpoint_url).
    # M106 P4 — transport public + téléphérique + lignes HT (arbitrage Vic 17/08/2026).
    dict(name="Transport public — GTFS (PAN, 7 réseaux)", category="acces",
         provider="AOM Réunion (Région, CINOR, TCO, CIVIS, CIREST, CASUD) via transport.data.gouv.fr",
         access_type="GTFS (zip)", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://transport.data.gouv.fr/datasets/region/04?format=GTFS",
         # sonde radar : l'API data.gouv du jeu Citalis (le plus vivant) = CANARI des 7 —
         # les URLs static.data.gouv sont horodatées et périment, on ne les sonde jamais.
         endpoint_url="https://www.data.gouv.fr/api/1/datasets/horaire-du-reseau-citalis/",
         legal_notes="Licence Ouverte v2.0 (les 7 jeux). Attribution : « Source : Point d'Accès "
                     "National transport.data.gouv.fr — AOM de La Réunion ».",
         technical_notes="Car Jaune, Citalis, Papang, Kar'Ouest, Alternéo, Carsud, Estival — "
                         "300 lignes, ~9 900 quais (recouvrements inter-réseaux non dédoublonnés). "
                         "kinds transport_arret/transport_ligne + pole_echange subtype='gtfs' "
                         "(DÉRIVÉ : ≥ seuil lignes, config/transport.yaml, statut Estimé). "
                         "Résolution des URLs à CHAQUE ingestion via la liste API du PAN "
                         "(transport_reseaux._pan_urls). Papang sans shapes.txt (tracé = OSM)."),
    dict(name="OSM — transport (pôles d'échange & téléphérique)", category="acces",
         provider="OpenStreetMap", access_type="Overpass/GeoJSON", status=S.CONNECTE,
         reliability_level=R.A_CONFIRMER,
         documentation_url="https://wiki.openstreetmap.org/wiki/Key:public_transport",
         endpoint_url="https://overpass-api.de/api/interpreter",
         legal_notes="ODbL 1.0 — attribution : « © les contributeurs d'OpenStreetMap — données "
                     "disponibles sous ODbL (openstreetmap.org/copyright) ». Usage assumé par "
                     "arbitrage Vic M106 (cohérent parkings APER/aménités) ; portée share-alike "
                     "à faire trancher avant le premier client (note hors mandat).",
         technical_notes="pole_echange subtype='osm' (stations + gares routières, Sourcé — "
                         "concordance avec le dérivé GTFS mesurée et DITE : confirme/osm_seul/"
                         "gtfs_seul) ; telepherique = le Papang EN SERVICE seul (gondola + "
                         "stations) — la ligne 2 « Zèl La Montagne » (2029) est EXCLUE : aucun "
                         "tracé publié, l'OSM proposed est une anticipation de contributeur."),
    # RETOURS-13 R4 — la MOYENNE TENSION (HTA) retrouvée sur le portail EDF Réunion refondu
    # (Koumoul/data-fair — l'ancien portail ODS répond 404/410, d'où le constat erroné de C1
    # « couches retirées »). Les POSTES SOURCES, eux, sont bien VIDÉS (0 enregistrement,
    # 24/12/2025, « sécurité publique ») : pas de couche postes, l'absence est dite.
    dict(name="EDF Réunion — lignes moyenne tension HTA (open data)", category="acces",
         provider="EDF SEI — open data La Réunion (portail Koumoul)",
         access_type="CSV data-fair (GeoJSON)", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://opendata-reunion.edf.fr/datasets/lignes-haute-tension-hta-aerien-run",
         endpoint_url="https://opendata-reunion.edf.fr/datasets/lignes-haute-tension-hta-aerien-run",
         source_millesime="EDF géométrie ~02/2020 · publié 16/10/2025",
         legal_notes="Licence Ouverte v2.0 — attribution : « Source : EDF, open data La Réunion ». "
                     "Données publiées « à titre purement indicatif », contenu réduit pour raison "
                     "de sécurité publique (mention du portail).",
         technical_notes="kind='ligne_mt' (subtype aérien 4 211 / souterrain 15 269 tronçons). "
                         "HTA = MOYENNE tension de distribution (15-20 kV) dans le vocabulaire "
                         "EDF — distinct de la HTB (ligne_ht, BD TOPO). Champs servis : statut + "
                         "géométrie SEULS (ni tension exacte ni nom de départ). Tracé indicatif : "
                         "ne remplace pas une DT-DICT. Postes sources : jeu VIDÉ au 24/12/2025."),
    # RETOURS-13 R5 — TCSP « en service » : OSM (voies bus), faute de toute source SIG publique
    # (recherche du 05/09/2026 : PEIGEO 0, Région 0, EPCI 0, transecoexpress.re injoignable).
    dict(name="TCSP — voies bus en site propre (OSM)", category="acces",
         provider="OpenStreetMap", access_type="Overpass/GeoJSON", status=S.CONNECTE,
         reliability_level=R.A_CONFIRMER,
         documentation_url="https://wiki.openstreetmap.org/wiki/Tag:highway%3Dbusway",
         endpoint_url="https://overpass-api.de/api/interpreter",
         legal_notes="ODbL 1.0 — attribution : « © les contributeurs d'OpenStreetMap ».",
         technical_notes="kind='tcsp_troncon' : subtype='site_propre' (highway=busway, chaussée "
                         "dédiée) vs 'couloir' (busway=lane, lanes:psv — PAS un site propre "
                         "L151-36, jamais de drapeau stationnement). kind='tcsp_station' (Dérivé) : "
                         "grappes d'arrêts GTFS à ≤ 60 m d'un tronçon en site propre — le drapeau "
                         "fiche < 800 m (art. L151-36, loi 2025-1129 du 26/11/2025) se mesure à la "
                         "STATION à vol d'oiseau (CE 2022), jamais au tracé. EN TRAVAUX (Rico "
                         "Carpaye, ESTI+) et EN PROJET (Réunion Express, débat public 19/08→"
                         "26/11/2026) : aucune géométrie publique — dits au « i », jamais dessinés."),
    # RETOURS-14 S5 — cadastre D'ÉPOQUE : archives figées (millésimes trimestriels Etalab depuis
    # 2017-07 + PCI vecteur DGFiP depuis 2017-02) servant à retrouver la parcelle d'origine des
    # permis dont la parcelle a disparu (division/remembrement). Archives IMMUABLES → pas de
    # sonde sentinelle (rien n'y change jamais).
    dict(name="Cadastre d'époque (Etalab / PCI vecteur DGFiP)", category="topographie",
         provider="Etalab / DGFiP via cadastre.data.gouv.fr",
         access_type="GeoJSON + EDIGEO (archives)", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://cadastre.data.gouv.fr/datasets/cadastre-etalab",
         endpoint_url="https://cadastre.data.gouv.fr/data/etalab-cadastre/",
         source_millesime="archives 2017-02 (PCI) et 2017-07→2026-06 (Etalab)",
         legal_notes="Licence Ouverte 2.0 — attribution : « Etalab / DGFiP, cadastre.data.gouv.fr ».",
         technical_notes="Table cadastre_historique (référence + géométrie SEULEMENT — mandat "
                         "RETOURS-14 S5) : parcelles d'ORIGINE des permis Sitadel orphelins, "
                         "rattachées par la géométrie aux parcelles actuelles (> 50 % → une seule ; "
                         "à cheval → toutes, « origine redécoupée »). Une parcelle disparue avant "
                         "2017-02 est irrécupérable (aucune archive ouverte plus ancienne) — "
                         "compté et dit, jamais contourné. CLI : python -m "
                         "labuse.ingestion.cadastre_historique"),
    # RETOURS-13 R5 — le tracé du RÉUNION EXPRESS n'existe qu'en carte interactive de débat
    # public (aucun export SIG) : source « à venir », suivie par la sentinelle — le tracé
    # bougera après le débat (clôture 26/11/2026).
    dict(name="Réunion Express — hypothèses de tracé (débat public CNDP)", category="acces",
         provider="Région Réunion / CNDP", access_type="carte interactive (pas de SIG)",
         status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.debatpublic.fr/projet-train-reunion-express",
         endpoint_url="https://www.debatpublic.fr/projet-train-reunion-express",
         legal_notes="Hypothèses de tracé et zones de variantes présentées au débat public "
                     "(19/08 → 26/11/2026) — document d'intention, pas une donnée opposable.",
         technical_notes="Tram-train ~140 km, 25 gares, Saint-Benoît → Saint-Joseph ; phase 1 "
                         "Saint-Benoît–Saint-Paul visée 2035. Carte interactive : "
                         "client.landweb3d.com/cr-reunion/Reunion-Express_PC (viewer 3D, pas de "
                         "données téléchargeables). RIEN N'EST INGÉRÉ (on ne numérise pas une "
                         "image) ; à ré-ouvrir après le débat si la Région publie un SIG."),
    dict(name="ZFANG — zone franche d'activité nouvelle génération (Légifrance)", category="fiscal",
         provider="Légifrance / DGOM", access_type="seed CSV (texte réglementaire)", status=S.CONNECTE,
         reliability_level=R.VERIFIE,
         documentation_url="https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054153903",
         endpoint_url="https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054153903",
         legal_notes="Texte réglementaire (Légifrance, réutilisation libre). Attribution : "
                     "« Source : décret n° 2026-421 du 29 mai 2026 (Légifrance) ».",
         technical_notes="Attribut de COMMUNE (jamais parcellaire) : régime standard (plein droit DOM, "
                         "art. 44 quaterdecies CGI) ou RENFORCÉ pour 6 communes de l'Est (Bras-Panon, "
                         "La Plaine-des-Palmistes, Saint-André, Saint-Benoît, Sainte-Rose, Salazie — "
                         "décret n° 2026-421 du 29/05/2026, critère taux de pauvreté EPCI). Dispositif "
                         "modifié deux fois en 2026 (février puis mai) → radar sur la page du décret."),
    dict(name="FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)", category="fiscal",
         provider="Légifrance / Région Réunion", access_type="seed CSV (texte réglementaire)",
         status=S.CONNECTE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049746820",
         endpoint_url="https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049746820",
         legal_notes="Texte réglementaire (Légifrance) ; référence infra-communale : jeu « ZRR 2017 » "
                     "du portail open data Région Réunion (Licence Ouverte).",
         technical_notes="Attribut de COMMUNE en 3 états MESURÉS (jeu Région ZRR 2017, ZSAR décret "
                         "n° 78-690 les Hauts, FRR au 01/07/2024 art. 44 quindecies A) : EN TOTALITÉ "
                         "(Cilaos, Salazie, La Plaine-des-Palmistes) / EN PARTIE (20 communes — "
                         "délimitation infra-communale, on ne conclut JAMAIS à la parcelle) / HORS "
                         "(Le Port). À CONFIRMER : liste FRR 2024+ par commune entière (annexe de "
                         "l'arrêté du 19/06/2024, section 974 non consultable en ligne)."),
    # PAU-CoSIA — footprints bâti vectorisés (IGN Géoplateforme). Source GÉOMÉTRIQUE canonique
    # de la couche spatial_layers kind='batiment_cosia' (ingestion/cosia.py). Millésime porté ici
    # (fait amont statique) ; last_sync_at est posé À L'INGESTION (jamais dans le seed).
    dict(name="CoSIA (couverture du sol IA, IGN)", category="occupation_sol",
         provider="IGN / Géoplateforme", access_type="téléchargement/GPKG",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="CoSIA 2025 (PVA juil.-août 2025, 20 cm)",
         documentation_url="https://geoservices.ign.fr/cosia",
         endpoint_url=("https://data.geopf.fr/telechargement/download/COSIA/"
                       "COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01/"
                       "COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01.7z"),
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : IGN — CoSIA "
                     "(Couverture du Sol par IA), D974 millésime 2025 ».",
         technical_notes="Occupation du sol par IA (segmentation d'ortho 20 cm) VECTORISÉE, 15 classes ; "
                         "on n'ingère QUE la classe « Bâtiment » (1/15) en footprints polygones. Lot D974 "
                         "RGR92/UTM40S (EPSG:2975), 37 tuiles, ~494 Mio .7z, 445 190 bâtiments. Sert le "
                         "recalcul PAU (RNU) en complément de BD TOPO. Doublon connu : p_model_bati_cosia "
                         "(emprise MÊME donnée agrégée à la parcelle, sans géométrie)."),
    # SOLAIRE M1 — PVGIS REQUALIFIÉE « servie » : le builder reconstruit parcel_solar (le catalogue
    # disait « DORMANT / non servi » depuis le spin-off Plein Sud ; il est de nouveau alimenté ici).
    dict(name="PVGIS (Commission européenne)", category="energie", provider="CE / JRC",
         access_type="REST/JSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="PVGIS v5.3 · modèle SARAH3 (relevé au run du builder solaire)",
         endpoint_url="https://re.jrc.ec.europa.eu/api/v5_3/PVcalc",
         legal_notes="CC BY 4.0 (décision 2011/833/UE) — attribution : « Source : Commission européenne, "
                     "Joint Research Centre — PVGIS », modifications indiquées (calculs dérivés LABUSE). "
                     "Gratuit, sans clé.",
         technical_notes="✓ SERVI (SOLAIRE M1) : builder ingestion/solaire.py reconstruit parcel_solar — "
                         "productible mensuel (12 E_m) + annuel + GHI, grille ST_SquareGrid 400 m "
                         "(~15 680 points) → IDW 4-NN, aspect 180° (plein nord, hémisphère sud), "
                         "usehorizon=1 (horizon topo intégré). ~10 req/s, résumable (`labuse solaire-build`)."),
    # SCORING-3 (L3) — BDNB : année de construction, classe DPE, surfaces, usage PAR BÂTIMENT —
    # le dernier proxy accessible de l'âge du propriétaire et de l'état du bien (plan v2 §2.4).
    dict(name="BDNB", category="proprietaire", provider="CSTB",
         access_type="import", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         source_millesime="2026-02-a (métropole seule — 974 absent)",
         source_cadence="trimestrielle",
         documentation_url="https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-batiments",
         endpoint_url="https://www.data.gouv.fr/api/1/datasets/base-de-donnees-nationale-des-batiments/",
         legal_notes="Licence Ouverte / Etalab 2.0 — attribution : « CSTB — Base de données nationale "
                     "des bâtiments ».",
         technical_notes="SCORING-3 L3 — CONSTAT MESURÉ 03/09/2026 : l'export « France » 2026-02-a "
                         "(seule distribution, csv.tar.gz 39 Go) couvre la MÉTROPOLE SEULE — 96 "
                         "départements, 0 ligne 974 sur 22,3 M vérifiées ligne à ligne "
                         "(batiment_groupe_ffo_bat). L'ingestion est PRÊTE (ingestion/bdnb.py : stream "
                         "gunzip→tar→filtre 974, `labuse ingest-bdnb`, CRON trimestriel qui re-SONDE la "
                         "couverture avant tout téléchargement) ; les variables candidates (année de "
                         "construction, DPE F/G, écart surface) et leur banc K0 (l3_bdnb.py) attendent "
                         "un millésime couvrant La Réunion. La sentinelle surveille (api data.gouv, "
                         "last_update) ; le CRON calcule ; Vic promeut. AUCUNE variable au modèle sans "
                         "banc K0 (L3.2)."),
    # ── CIRCUIT-5b lot 1 — les quatre « à rattacher » de CIRCUIT-5 entrent au catalogue ──
    # Tables déjà servies (mairies, rnic_coproprietes, rpls_commune, commune_conso_enaf), slug déjà
    # à la carte (RESERVOIR_TABLES) et lues par le registre ; il ne leur manquait que leur ligne
    # data_sources. Chacune : producteur, mode d'accès, mode+cadence (MODE_ET_CADENCE) et une raison
    # de non-surveillance (RAISONS_NON_SURVEILLEES) — millésimes annuels/mensuels sans témoin amont
    # à empreinte stable, suivis par le rappel de cadence et la page Circuit.
    dict(name="Annuaire de l'administration (service-public.fr / DILA)", category="acces",
         provider="DILA (service-public.fr)", access_type="API/JSON",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="annuaire service-public.fr — 24 mairies (OUTILS K2)",
         documentation_url="https://api-lannuaire.service-public.fr/",
         endpoint_url="https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/api-lannuaire-administration/records",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : DILA — Annuaire de l'administration (service-public.fr) ».",
         technical_notes="OUTILS K2 : 24 mairies (adresse, téléphone, courriel, horaires, service urbanisme) ingérées depuis l'annuaire de l'administration. Table `mairies`, bloc MAIRIE du ContextePanel — un champ manquant reste ABSENT, jamais inventé. Cadence mensuelle."),
    dict(name="RNIC — registre national des copropriétés (Anah)", category="logement",
         provider="Anah (registre national d'immatriculation des copropriétés)", access_type="téléchargement/CSV",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="RNIC (ANAH) — registre des copropriétés (extraction annuelle)",
         documentation_url="https://www.data.gouv.fr/fr/datasets/registre-national-dimmatriculation-des-coproprietes/",
         legal_notes="Licence Ouverte — attribution : « Source : Anah — Registre national d'immatriculation des copropriétés (RNIC) ».",
         technical_notes="Table `rnic_coproprietes`. Copropriétés immatriculées rattachées à la parcelle (lots, syndic), servies à la fiche parcelle. Extraction annuelle data.gouv, filtre 974."),
    dict(name="RPLS — répertoire des logements locatifs sociaux (SDES)", category="logement",
         provider="SDES (répertoire des logements locatifs des bailleurs sociaux)", access_type="téléchargement/CSV",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="RPLS — millésime 01/01/2025 (SDES)",
         documentation_url="https://www.statistiques.developpement-durable.gouv.fr/le-repertoire-des-logements-locatifs-des-bailleurs-sociaux-rpls",
         legal_notes="Licence Ouverte — attribution : « Source : SDES — Répertoire des logements locatifs des bailleurs sociaux (RPLS) ».",
         technical_notes="Table `rpls_commune` (parc social par commune : nb_logements, construction médiane). Servi au contexte marché de la fiche commune, au Flash et au PDF premium. `pct_qpv` NON servi (valeur non discriminante — 100 % pour les 24 communes, RETOURS-11F). Millésime 01/01/2025."),
    dict(name="Consommation d'espaces NAF (Cerema — portail de l'artificialisation)", category="urbanisme",
         provider="Cerema (portail national de l'artificialisation des sols)", access_type="téléchargement/CSV",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="conso ENAF 2021-2024 (portail artificialisation, Cerema)",
         documentation_url="https://artificialisation.developpement-durable.gouv.fr/les-donnees/donnees-de-consommation-despaces",
         legal_notes="Licence Ouverte — attribution : « Source : Cerema — portail national de l'artificialisation des sols ».",
         technical_notes="Table `commune_conso_enaf` (consommation d'espaces NAF par commune, période 2021-2024). Lue par la pression ZAN et l'enveloppe ZAN restante (fiche commune, comparateur). Millésime annuel."),
    # ── SOURCES-1 lot 1 — les prescriptions et périmètres du droit des sols ──
    # Deux réservoirs LOGIQUES sur la même table servie par le canal GPU existant (API Carto
    # prescriptions, réservoir gpu_plu_api_carto) : les codes CNIG typepsc VÉRIFIÉS dans les
    # données des 24 communes (06/09/2026) sont 05 = emplacement réservé (2 250 + 6 ER réels
    # codés « 02 » à Saint-Louis, rescue M8a) et 01 = espace boisé classé (1 782).
    dict(name="GPU — emplacements réservés (prescriptions CNIG)", category="urbanisme",
         provider="IGN / Géoportail de l'urbanisme (prescriptions des PLU)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="GPU — prescriptions typepsc 05 (idurba par commune)",
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/prescription-surf",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN), prescriptions des documents d'urbanisme ».",
         technical_notes="SOURCES-1 lot 1 — réservoir gpu_prescriptions_er sur spatial_layers "
                         "kind='plu_gpu_prescription' (famille ER : typepsc 05 + rescue/veto libellé, "
                         "source unique cascade_rules.yaml). Rempli par le canal GPU existant "
                         "(prescriptions par commune). Cascade : VIGILANCE, RÉDHIBITOIRE ≥ 50 % "
                         "(seuil regles/), surface ER déduite de l'emprise (pré-faisabilité)."),
    dict(name="GPU — espaces boisés classés (prescriptions CNIG)", category="urbanisme",
         provider="IGN / Géoportail de l'urbanisme (prescriptions des PLU)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="GPU — prescriptions typepsc 01 (idurba par commune)",
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/prescription-surf",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN), prescriptions des documents d'urbanisme ».",
         technical_notes="SOURCES-1 lot 1 — réservoir gpu_prescriptions_ebc sur spatial_layers "
                         "kind='plu_gpu_prescription' (typepsc 01, Art. L113-1 CU). Rempli par le "
                         "canal GPU existant. Cascade : VIGILANCE dès non nul, RÉDHIBITOIRE ≥ 80 % "
                         "(seuil regles/), part EBC SOUSTRAITE de l'assiette du bloc potentiel."),
    dict(name="GPU — droit de préemption urbain (info-surf)", category="urbanisme",
         provider="IGN / Géoportail de l'urbanisme (informations des PLU)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="GPU typeinf 04 — partiel, non-publiées listées",
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/info-surf",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : Géoportail de l'urbanisme (IGN), informations des documents d'urbanisme ».",
         technical_notes="SOURCES-1 lot 1 — réservoir dpu_perimetres : spatial_layers kind='dpu' "
                         "(typeinf CNIG 04, subtype dpu/dpu_renforce), attribution stricte par "
                         "partition DU_<insee>. `labuse ingest-gpu-infos`. Une commune sans typeinf 04 "
                         "n'a PAS publié son DPU au GPU (état « non publié », listée au rapport "
                         "d'ingestion pour la demande de Vic aux communes/SIG communaux). Cascade : "
                         "VIGILANCE (la préemption pèse sur la transaction, pas sur la constructibilité)."),
    dict(name="PEB — plans d'exposition au bruit (DGAC via annexes GPU)", category="risques",
         provider="DGAC / DEAL (PEB approuvés) — republication annexes GPU",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="Roland-Garros B/C/D (GPU) ; Pierrefonds non publié",
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/info-surf",
         legal_notes="Licence Ouverte (GPU) — attribution : « Source : DGAC (plans d'exposition au bruit), via le Géoportail de l'urbanisme ». Référence : art. L112-10 du code de l'urbanisme.",
         technical_notes="SOURCES-1 lot 1 — réservoir peb_dgac : spatial_layers kind='peb' "
                         "(typeinf CNIG 27, zone A/B/C/D dans txt, dédoublonné à l'île). VÉRIFIÉ "
                         "06/09/2026 : Roland-Garros servi en B/C/D par les annexes GPU des communes "
                         "concernées ; Pierrefonds ABSENT du GPU (0 typeinf 27 sur la bbox de "
                         "Saint-Pierre) — couverture partielle DITE, aucune géométrie inventée. "
                         "`labuse ingest-gpu-infos`. Cascade : zones A/B RÉDHIBITOIRES, C/D VIGILANCE "
                         "(L112-10 CU)."),
    dict(name="Zonage ABC des communes (DHUP)", category="logement",
         provider="DHUP / Ministère de la Transition écologique (arrêté national)",
         access_type="téléchargement/CSV", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="arrêté 23/06/2026 en vigueur 26/06 — 24/24 (4 A, 20 B1)",
         documentation_url="https://www.data.gouv.fr/datasets/liste-des-communes-selon-le-zonage-abc",
         endpoint_url="https://static.data.gouv.fr/resources/liste-des-communes-selon-le-zonage-abc/20260703-091314/liste-ensemble-des-communes-zonage-abc-en-vigueur-26-juin-2026.csv",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : DHUP — zonage ABC (arrêté du 1er août 2014 modifié, art. D. 304-1 CCH) ».",
         technical_notes="SOURCES-1 lot 1 — réservoir zonage_abc_dhup : table commune_zonage_abc "
                         "(classe par commune, passe-plat de l'arrêté). VÉRIFIÉ 06/09/2026 : 24/24 "
                         "communes (A : Les Avirons, L'Étang-Salé, Saint-Leu, Saint-Paul ; B1 : les "
                         "20 autres). `labuse ingest-zonage-abc`. Pas de couche carte, pas de cascade "
                         "(régime d'aides, pas de constructibilité)."),
    # ── SOURCES-1 lot 2 — la nature et l'eau ──
    dict(name="Ravines — domaine public fluvial (DEAL Carmen)", category="risques",
         provider="DEAL Réunion (Carmen, nœud 29 — DEAL_REUNION_2020)",
         access_type="WFS/GML", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="DPF arrêté 06-3077 du 21/08/2006 — 275 tronçons + 6 plans",
         documentation_url="https://www.reunion.developpement-durable.gouv.fr/domaine-public-fluvial-dpf-et-domaine-prive-de-l-a285.html",
         endpoint_url="http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020",
         legal_notes="Licence Ouverte — attribution : « Source : DEAL Réunion — domaine public fluvial (arrêté préfectoral n°06-3077/SG/DRCTV du 21/08/2006) ».",
         technical_notes="SOURCES-1 lot 2 — réservoir deal_dpf_dpe : spatial_layers kind='dpf' "
                         "(cours_eau 275, plan_eau 6), couches Cours_d_eau_DPF + Plan_d_eau_DPF du "
                         "WFS Carmen 29 (GML EPSG:2975 → ogr2ogr, vérifié live 07/09/2026 — la "
                         "fiche Sextant du rapport n'offre AUCUNE distribution, WMS de "
                         "visualisation seul). `labuse ingest-deal-carmen`. Cascade : marchepied "
                         "3,25 m RÉDHIBITOIRE (L2131-2 CGPPP), bande 10 m = vigilance (portée par "
                         "la couche ravine BD TOPO, anti-double-compte). Le DPE (domaine privé de "
                         "l'État, ~1 700 km) n'est PAS diffusé sur ce WFS — demande DEAL (lot 7)."),
    dict(name="Zones humides — inventaires DEAL (Carmen)", category="environnement",
         provider="DEAL Réunion (Carmen, nœud 29 — DEAL_REUNION_2020)",
         access_type="WFS/GML", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="inventaires 2003/2009/2011/2019 par secteurs (partiels)",
         documentation_url="https://www.reunion.developpement-durable.gouv.fr/les-cartographies-d-habitats-a320.html",
         endpoint_url="http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020",
         legal_notes="Licence Ouverte — attribution : « Source : DEAL Réunion — inventaires des zones humides ».",
         technical_notes="SOURCES-1 lot 2 — réservoir deal_zones_humides : spatial_layers "
                         "kind='zone_humide' (habitats_2011 1 507 · inventaire_2009 187 · "
                         "espace_fonctionnel_2009 30 · inventaire_2003 49 · basse_altitude_2019 "
                         "1 349 — vérifié live 07/09/2026). Couverture PAR SECTEURS dite, jamais "
                         "une preuve d'absence (habitats ≠ zones humides réglementaires). "
                         "`labuse ingest-deal-carmen`. Cascade : VIGILANCE forte (loi sur l'eau, "
                         "séquence ERC)."),
    dict(name="Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)",
         category="environnement",
         provider="DEAL Réunion (Carmen, nœud 29 — DEAL_REUNION_2020)",
         access_type="WFS/GML", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="Ramsar 1 · sites classés/inscrits 7 · RN 3 (07/09/2026)",
         documentation_url="https://www.reunion.developpement-durable.gouv.fr/informations-geographiques-r104.html",
         endpoint_url="http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020",
         legal_notes="Licence Ouverte — attribution : « Source : DEAL Réunion (Carmen) — Ramsar, sites classés et inscrits, réserves naturelles ».",
         technical_notes="SOURCES-1 lot 2 — complète l'ENP INPN (kind='ens') avec les types "
                         "absents du jeu INPN local : ramsar (Étang Saint-Paul), site_classe/"
                         "site_inscrit (7, attribut Type), reserve_naturelle (RNN zonée A/B + "
                         "RÉSERVE MARINE, absente du jeu INPN local — chevauche l'entité RNN INPN "
                         "sur l'Étang, dit). Purge par SUBTYPE seulement, les subtypes INPN "
                         "restent. Forêts de protection = SUP A7 : NON publiée pour le 974 "
                         "(inventaire GPU sondé, lot 1). Cascade : réserves/APB RÉDHIBITOIRES, "
                         "sites = info ×0 (anti-double-compte SUP AC2), ramsar = vigilance."),
    dict(name="AZI / TRI — inondation (Géorisques GASPAR)", category="risques",
         provider="BRGM / Géorisques (GASPAR)",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="GASPAR azi+tri par commune (07/09/2026)",
         rate_limit="~1000 req/min/IP",
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/gaspar/azi",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) — GASPAR ».",
         technical_notes="SOURCES-1 lot 2 — réservoir georisques_azi_tri : table azi_communes "
                         "(FAIT documentaire par commune — ex. 97411 : AZI « La Montagne » 2004, "
                         "TRI Saint-Denis/Sainte-Marie 2013, vérifié live 07/09/2026). La "
                         "GÉOMÉTRIE d'aléa inondation n'est PAS ré-ingérée : l'ALEA_INONDATION "
                         "Carmen (75) est un doublon vérifié de georisque_alea/inondation (76, "
                         "DEAL Lizmap) déjà servi par la couche cascade risques. "
                         "`labuse ingest-azi-tri`."),
    dict(name="ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)",
         category="patrimoine", provider="Ministère de la Culture / DAC de La Réunion",
         access_type="WFS/shp", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         source_millesime="aucune donnée — Atlas injoignable (06/09/2026)",
         documentation_url="https://www.culture.gouv.fr/regions/dac-de-la-reunion/la-direction-des-affaires-culturelles-de-la-reunion/patrimoine-architecture-environnement/archeologie/Zones-de-presomption-de-prescription-archeologique-ZPPA",
         endpoint_url="https://atlas.patrimoines.culture.fr/",
         legal_notes="Licence : libre sous mention de la source et de la date (Atlas des patrimoines). Une ZPPA n'est PAS une servitude — indication (saisine préfet, diagnostic archéologique).",
         technical_notes="SOURCES-1 lot 1 — réservoir zppa_culture ATTENDU : atlas.patrimoines."
                         "culture.fr injoignable au test du 06/09/2026 (timeout, aucune réponse HTTP) "
                         "et aucun jeu national/974 sur data.gouv (recherche du 06/09/2026 : couches "
                         "locales hors 974 seulement). Couverture 974 à confirmer AU TÉLÉCHARGEMENT "
                         "quand l'Atlas répond — la sentinelle surveille la page DAC. Rien d'ingéré, "
                         "rien d'inventé ; couche + fiche + VIGILANCE brancheront à la première "
                         "version réelle."),
    # ── SOURCES-1 lot 3 — les sols et le bruit ──
    # SIS et CASIAS : réservoirs LOGIQUES sur le kind sol_pollue (subtypes sis/casias), déjà
    # rempli par le canal Géorisques SSP existant (/api/v1/ssp groupe sis+casias+instructions,
    # ingest-georisques) — pas de table dupliquée, l'anti-doublon est la doctrine (cf. ER/EBC).
    dict(name="Géorisques — secteurs d'information sur les sols (SIS)", category="risques",
         provider="BRGM / MTE (Géorisques — infosols)", access_type="REST",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="4 SIS 974 (MultiPolygon) — canal SSP, vu 07/09/2026",
         documentation_url="https://www.georisques.gouv.fr/donnees/bases-de-donnees/secteurs-dinformations-sur-les-sols-sis",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/ssp",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) — SIS ». "
                     "Obligation d'information de l'acquéreur/locataire : art. L125-7 du code de l'environnement.",
         technical_notes="SOURCES-1 lot 3 — réservoir georisques_sis : spatial_layers "
                         "kind='sol_pollue' subtype='sis' (périmètres réglementaires MultiPolygon, "
                         "4 au 974 : Le Port, Saint-Benoît, Saint-Louis, Sainte-Marie). Rempli par "
                         "le canal SSP existant (labuse ingest-georisques). Cascade : VIGILANCE "
                         "FORTE (étude de sols au changement d'usage L556-2, information de "
                         "l'acheteur L125-7 — motifs cités). Couche carte kind virtuel 'sis'."),
    dict(name="Géorisques — CASIAS (anciens sites industriels)", category="risques",
         provider="BRGM / MTE (Géorisques — CASIAS, ex-BASIAS)", access_type="REST",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="453 sites 974 (435 points, 18 emprises) — canal SSP, 07/09/2026",
         documentation_url="https://www.georisques.gouv.fr/donnees/bases-de-donnees/inventaire-historique-de-sites-industriels-et-activites-de-service",
         endpoint_url="https://www.georisques.gouv.fr/api/v1/ssp",
         legal_notes="Licence Ouverte 2.0 (Etalab) — attribution : « Source : Géorisques (BRGM/MTE) — CASIAS ». "
                     "Un site CASIAS est un INVENTAIRE HISTORIQUE, pas une pollution avérée.",
         technical_notes="SOURCES-1 lot 3 — réservoir georisques_casias : spatial_layers "
                         "kind='sol_pollue' subtypes 'casias' (453) + 'instruction' (56), rempli "
                         "par le canal SSP existant. Cascade : VIGILANCE (faible, ≤ 100 m) — le "
                         "motif dit « inventaire historique, pas une pollution avérée ». Couche "
                         "carte kind virtuel 'casias'."),
    dict(name="DEAL — cartes de bruit stratégiques (CBS)", category="risques",
         provider="DEAL Réunion (directive 2002/49/CE, échéance 4)", access_type="WFS/GML",
         status=S.CONNECTE, reliability_level=R.VERIFIE,
         source_millesime="CBS 2022 — 6 zones de dépassement Lden/Ln (RN/RD/VC)",
         documentation_url="https://www.reunion.developpement-durable.gouv.fr/8-consultation-des-donnees-a62.html",
         endpoint_url="http://ws.carmen.developpement-durable.gouv.fr/WFS/29/Cartes_bruit_strategiques",
         legal_notes="Licence Ouverte — attribution : « Source : DEAL Réunion — cartes de bruit stratégiques ».",
         technical_notes="SOURCES-1 lot 3 — réservoir deal_bruit_cartes : spatial_layers "
                         "kind='bruit_carte' (type c = dépassements des valeurs limites Lden 68 / "
                         "Ln 62 dB(A), 6 entités). ≠ classement sonore réglementaire (kind "
                         "bruit_route, arrêtés 14-15/12/2023) — les type b (secteurs affectés) ne "
                         "sont PAS ingérés (doublon vérifié des bandes sect_bruit Cerema), les "
                         "type a (isophones) écartés (exposition, pas d'effet réglementaire). "
                         "`labuse ingest-bruit-cartes`."),
]


# M125-1ter — RENOMMAGES de sources (faux constat de NOM). `seed()` clé par nom → un simple
# changement de nom dans SOURCES créerait un DOUBLON (nouvelle ligne) et laisserait les résultats
# cascade existants pointés sur l'ANCIEN nom (donc le faux nom s'afficherait encore). On renomme
# donc EN PLACE avant l'upsert. Idempotent : si le nouveau nom existe déjà (ré-exécution), on
# repointe les liens de l'orphelin puis on le supprime.
_RENAMES = {
    "SAR Réunion (PEIGEO)": "Potentiel foncier Région (Région ODS)",
    "Zonage SAFER (DAAF)": "RPG — déclarations agricoles (IGN/ASP)",
    "OCS GE (IGN)": "IGN BD CARTO V5 — occupation du sol",
    "ENS (Département)": "INPN / patrinat — espaces protégés",
    "DEAL Réunion — trait de côte": "Cerema / GéoLittoral — indicateur d'érosion côtière",
}


def _migrer_renommages(session: Session) -> None:
    """M125-1ter — renomme les sources EN PLACE (avant l'upsert clé-par-nom). Renommage seul
    (`UPDATE name`) : l'id est conservé, toutes les FK (spatial_layers, cascade_results…) restent
    valides, et les résultats cascade existants affichent le NOUVEAU nom sans re-run. Idempotent :
    si le nouveau nom existe déjà, on n'écrase rien (le renommage a déjà eu lieu)."""
    for old, new in _RENAMES.items():
        has_old = session.execute(text("SELECT 1 FROM data_sources WHERE name = :n"), {"n": old}).first()
        has_new = session.execute(text("SELECT 1 FROM data_sources WHERE name = :n"), {"n": new}).first()
        if has_old and not has_new:
            session.execute(text("UPDATE data_sources SET name = :new WHERE name = :old"),
                            {"new": new, "old": old})
    # M125-C6 — la couche « proprietaire » ne doit plus CITER « Fichiers fonciers (Cerema) » (source
    # NON branchée, retirée en M125-1ter → SRC_FF = DGFiP). Repointe les résultats cascade STOCKÉS de
    # l'ancienne source vers DGFiP (la génération le fait déjà pour les runs futurs). Idempotent.
    _ff = session.execute(text("SELECT id FROM data_sources WHERE name = 'Fichiers fonciers (Cerema)'")).first()
    _dg = session.execute(text(
        "SELECT id FROM data_sources WHERE name = 'DGFiP — parcelles des personnes morales'")).first()
    if _ff and _dg:
        for _tbl in ("cascade_results", "dryrun_cascade_results"):
            session.execute(text(f"UPDATE {_tbl} SET data_source_id = :dg WHERE data_source_id = :ff"),
                            {"dg": _dg[0], "ff": _ff[0]})
    session.flush()


def verifier_catalogue(rows: list[dict] | None = None) -> list[str]:
    """CIRCUIT-5 lot 2.3 — une source ne peut plus ENTRER qu'avec un id (name), un producteur,
    un mode d'accès, un mode de remplissage + une cadence (MODE_ET_CADENCE), et une sonde OU la
    raison de son absence (RAISONS_NON_SURVEILLEES, ou une URL amont que la sentinelle sait
    sonder). Rend la liste des problèmes — `seed()` REFUSE si elle n'est pas vide."""
    from ..sentinelle import RAISONS_NON_SURVEILLEES
    pbs: list[str] = []
    for row in (SOURCES if rows is None else rows):
        nom = row.get("name") or "(sans nom)"
        if not row.get("name"):
            pbs.append("source sans name (id de catalogue)")
        if not row.get("provider"):
            pbs.append(f"{nom} : sans producteur (provider)")
        if not row.get("access_type"):
            pbs.append(f"{nom} : sans mode d'accès (access_type)")
        if row.get("name") and nom not in MODE_ET_CADENCE:
            pbs.append(f"{nom} : sans mode de remplissage ni cadence (MODE_ET_CADENCE)")
        sondable = bool(row.get("endpoint_url") or row.get("documentation_url"))
        if row.get("name") and not sondable and nom not in RAISONS_NON_SURVEILLEES:
            pbs.append(f"{nom} : sans sonde (aucune URL amont) ni raison d'absence "
                       "(RAISONS_NON_SURVEILLEES)")
    return pbs


#: CIRCUIT-5 lot 2.1 — les statuts de première classe posés sur les lignes HORS VITRINE
#: (le préfixe de technical_notes reste en ceinture, le statut fait foi). Par NOM (les ids
#: peuvent varier d'une base à l'autre). Doublon → alias de la ligne canonique ; morte ou
#: essai → retiree (date + raison) ; hub → hub. Les a_faire légitimes (chantier nommé dans
#: la note : BDNB, Réunion Express, taxe d'aménagement) restent a_faire.
ALIAS_CANONIQUES: dict[str, str] = {
    "Cadastre Etalab (bulk DGFiP/Etalab)": "Cadastre (API Carto PCI)",
    "RGE ALTI 5 m (IGN)": "RGE ALTI (altimétrie)",
    "GPU — zonages d'assainissement (info-surf typeinf 19)": "GPU — zonages d'assainissement",
}

RETRAITS: dict[str, str] = {
    "EDF SEI Réunion — open data":
        "amont 410 Gone — jeu retiré par EDF SEI (~2026), plus rien à sonder",
    "Registre national des installations (ODRÉ)":
        "jamais branché, aucun usage identifié (audit M66/M71)",
    "ZNIEFF (INPN / Région)":
        "canal Région jamais alimenté (endpoint vivant, 0 donnée) — canonique : ZNIEFF (INPN/MNHN)",
    # CIRCUIT-5b lot 2 — MOBPRO abandonné par ZONE-DONNÉES (emplois de zone servis par les tranches
    # SIRENE) ; son unique lecteur, zone.emplois_communes, n'a plus aucun appelant (code mort vérifié
    # par grep). Table mobpro_commune conservée (aucun DROP) ; réservoir marqué RETIRÉ dans la carte.
    "MOBPRO (mobilités domicile-travail, INSEE)":
        "abandonnée par ZONE-DONNÉES (emplois de zone = tranches d'effectif SIRENE) ; lecteur "
        "zone.emplois_communes sans appelant (code mort) — table conservée, plus rien de servi",
}

HUBS: tuple[str, ...] = (
    "Région Réunion Open Data (Opendatasoft)", "PEIGEO (hub régional)", "Géoplateforme IGN",
)


def appliquer_statuts_circuit(session: Session) -> None:
    """Pose (idempotent) les colonnes CIRCUIT-5 (`alias_de`, `retiree_le`, `retiree_raison`)
    et les statuts de première classe. `retiree_le` n'est posé qu'une fois (premier passage) —
    la date du retrait ne bouge plus ensuite. RIEN n'est effacé : les notes restent."""
    for ddl in (
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS alias_de integer REFERENCES data_sources(id)",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS retiree_le date",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS retiree_raison text",
    ):
        session.execute(text(ddl))
    for nom, canonique in ALIAS_CANONIQUES.items():
        session.execute(text(
            "UPDATE data_sources SET status = 'alias',"
            " alias_de = (SELECT id FROM data_sources WHERE name = :canonique)"
            " WHERE name = :nom"), {"nom": nom, "canonique": canonique})
    for nom, raison in RETRAITS.items():
        session.execute(text(
            "UPDATE data_sources SET status = 'retiree', retiree_raison = :raison,"
            " retiree_le = COALESCE(retiree_le, CURRENT_DATE) WHERE name = :nom"),
            {"nom": nom, "raison": raison})
    for nom in HUBS:
        session.execute(text("UPDATE data_sources SET status = 'hub' WHERE name = :nom"),
                        {"nom": nom})


def seed(session: Session) -> int:
    """Upsert idempotent du catalogue. Renvoie le nombre de sources présentes.
    CIRCUIT-5 lot 2.3 : REFUSE un catalogue incomplet (id, producteur, mode, cadence, sonde)."""
    pbs = verifier_catalogue()
    if pbs:
        raise ValueError("seed refusé (CIRCUIT-5 lot 2.3) : " + " ; ".join(pbs))
    _migrer_renommages(session)   # M125-1ter — rename EN PLACE avant l'upsert (sinon doublon)
    existing = {name for (name,) in session.execute(select(DataSource.name)).all()}
    for row in SOURCES:
        if row["name"] in existing:
            ds = session.execute(select(DataSource).where(DataSource.name == row["name"])).scalar_one()
            for k, v in row.items():
                setattr(ds, k, v)
        else:
            session.add(DataSource(**row))
    session.flush()
    appliquer_modes_cadences(session)   # CIRCUIT-1 lot 1.7 — modes + cadences déclarés
    appliquer_statuts_circuit(session)  # CIRCUIT-5 lot 2.1 — alias/retiree/hub de première classe
    return session.query(DataSource).count()


# ═══════════════ CIRCUIT-1 lot 1.7 — mode de remplissage + cadence attendue DÉCLARÉS ═══════════════
# Énum des modes (CIRCUIT-0) : job_sur_clic · cron_mensuel · depot_manuel · one_shot · en_direct ·
# absente. `cadence_attendue_jours` : déclarée quand le producteur publie à cadence connue
# (`declaree`), PROPOSÉE sinon (`proposee` — règle : mensuel pour un flux, 365 j pour un millésime,
# spécifiques BAN 35 j / BODACC 3 j / Radar 7 j) ; `sans_objet` pour l'interrogé en direct et
# l'absent. La liste des propositions est livrée dans docs/CIRCUIT/CADENCES-PROPOSEES.md — Vic les
# corrige depuis la page Circuit, pas dans ce fichier.
MODE_ET_CADENCE: dict[str, tuple[str, int | None, str]] = {
    "Cadastre (API Carto PCI)": ("one_shot", 365, "proposee"),
    "Cadastre Etalab (bulk DGFiP/Etalab)": ("one_shot", 365, "proposee"),
    "Urbanisme PLU/GPU (API Carto)": ("en_direct", None, "sans_objet"),
    "Géorisques": ("one_shot", 365, "proposee"),
    "DVF / valeurs foncières": ("job_sur_clic", 190, "declaree"),
    "RGE ALTI (altimétrie)": ("one_shot", 365, "proposee"),
    "Parc National de La Réunion (INPN)": ("one_shot", 365, "proposee"),
    "Forêts publiques (ONF)": ("one_shot", 365, "proposee"),
    "Potentiel foncier Région (Région ODS)": ("one_shot", 365, "proposee"),
    "RPG — déclarations agricoles (IGN/ASP)": ("en_direct", None, "sans_objet"),
    "Région Réunion Open Data (Opendatasoft)": ("absente", None, "sans_objet"),
    "PEIGEO (hub régional)": ("absente", None, "sans_objet"),
    "DEAL Réunion (WMS/WFS)": ("one_shot", 365, "proposee"),
    "Géoplateforme IGN": ("absente", None, "sans_objet"),
    "data.regionreunion.com — Potentiel foncier": ("one_shot", 365, "proposee"),
    "SITADEL (autorisations d'urbanisme)": ("cron_mensuel", 35, "declaree"),
    "BD TOPO IGN": ("one_shot", 365, "proposee"),
    "Base Adresse Nationale": ("job_sur_clic", 35, "declaree"),
    "OpenStreetMap / Overpass": ("one_shot", 365, "proposee"),
    "BPE INSEE": ("one_shot", 365, "proposee"),
    "SIRENE": ("en_direct", None, "sans_objet"),
    "IGN BD CARTO V5 — occupation du sol": ("one_shot", 365, "proposee"),
    "ABF / Monuments historiques": ("one_shot", 365, "proposee"),
    "INPN / patrinat — espaces protégés": ("one_shot", 365, "proposee"),
    "VRD / assainissement (SPANC)": ("depot_manuel", 365, "proposee"),
    "Fichiers fonciers (Cerema)": ("absente", None, "sans_objet"),
    "Cerema / GéoLittoral — indicateur d'érosion côtière": ("one_shot", 365, "proposee"),
    "BODACC (procédures collectives)": ("job_sur_clic", 3, "proposee"),
    "DEAL Réunion — PPR / aléas": ("one_shot", 365, "proposee"),
    "INPI RNE (dirigeants)": ("one_shot", 365, "proposee"),
    "Géorisques — sites et sols pollués": ("one_shot", 365, "proposee"),
    "Géorisques — cavités souterraines": ("one_shot", 365, "proposee"),
    "Géorisques — ICPE": ("one_shot", 365, "proposee"),
    "Cartofriches (Cerema)": ("one_shot", 365, "proposee"),
    "Géorisques — mouvements de terrain": ("one_shot", 365, "proposee"),
    "DPE ADEME (logements existants)": ("cron_mensuel", 9, "declaree"),
    "QPV 2024 (ANCT)": ("one_shot", 365, "proposee"),
    "Inventaire SRU (DHUP)": ("one_shot", 365, "proposee"),
    "NPNRU (DEAL Réunion / ANCT)": ("one_shot", 365, "proposee"),
    "INSEE RP Logement 2023": ("one_shot", 365, "proposee"),
    "PLH des 5 EPCI (extraction documentaire)": ("depot_manuel", 365, "proposee"),
    "RTAA DOM (textes réglementaires)": ("one_shot", 365, "proposee"),
    "SUP — assiettes GPU (API Carto)": ("cron_mensuel", 35, "proposee"),
    "Recherche d'entreprises (DINUM)": ("en_direct", None, "sans_objet"),
    "Classement sonore ITT (Cerema)": ("one_shot", 365, "proposee"),
    "50 pas géométriques — limite haute (DEAL)": ("one_shot", 365, "proposee"),
    "PVGIS (Commission européenne)": ("one_shot", 365, "proposee"),
    "EDF SEI Réunion — open data": ("absente", None, "sans_objet"),
    "Registre national des installations (ODRÉ)": ("absente", None, "sans_objet"),
    "Parkings OSM (loi APER)": ("one_shot", 365, "proposee"),
    "Filosofi INSEE (carreaux 200 m)": ("one_shot", 365, "proposee"),
    "BD ORTHO 20 cm (IGN)": ("one_shot", 365, "proposee"),
    "Sudocuh (procédures d'urbanisme)": ("depot_manuel", 365, "proposee"),
    "GPU — zonages d'assainissement": ("one_shot", 365, "proposee"),
    "Contours IRIS (IGN/INSEE)": ("one_shot", 365, "proposee"),
    "RGE ALTI 5 m (IGN)": ("one_shot", 365, "proposee"),
    "INSEE RP2022 — fichier détail Logements (EGOUL)": ("one_shot", 365, "proposee"),
    "GPU — zonages d'assainissement (info-surf typeinf 19)": ("one_shot", 365, "proposee"),
    "Office de l'eau Réunion — Chroniques de l'eau": ("depot_manuel", 365, "proposee"),
    "BD ORTHO IRC (IGN)": ("one_shot", 365, "proposee"),
    "LiDAR HD — MNH 50 cm (IGN)": ("one_shot", 365, "proposee"),
    "DGFiP — parcelles des personnes morales": ("one_shot", 400, "declaree"),
    "ZFANG — zone franche d'activité nouvelle génération (Légifrance)": ("one_shot", 365, "proposee"),
    "FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)": ("one_shot", 365, "proposee"),
    "Transport public — GTFS (PAN, 7 réseaux)": ("one_shot", 365, "proposee"),
    "OSM — transport (pôles d'échange & téléphérique)": ("one_shot", 365, "proposee"),
    "ZNIEFF (INPN/MNHN)": ("one_shot", 365, "proposee"),
    "ZNIEFF (INPN / Région)": ("absente", None, "sans_objet"),
    "CoSIA (couverture du sol IA, IGN)": ("one_shot", 800, "declaree"),
    "Radar (pige d'annonces)": ("depot_manuel", 3, "declaree"),
    "SIRENE établissements géolocalisés": ("cron_mensuel", 35, "proposee"),
    "MOBPRO (mobilités domicile-travail, INSEE)": ("one_shot", 365, "proposee"),
    "Trafic RN (Région Réunion — SIR)": ("one_shot", 365, "proposee"),
    "BDNB": ("absente", 100, "declaree"),
    "EDF Réunion — lignes moyenne tension HTA (open data)": ("one_shot", 365, "proposee"),
    "TCSP — voies bus en site propre (OSM)": ("one_shot", 365, "proposee"),
    "Réunion Express — hypothèses de tracé (débat public CNDP)": ("absente", None, "sans_objet"),
    # CIRCUIT-5 lot 2.3 — attrapées par verifier_catalogue() (entrées sans mode ni cadence) :
    "CatNat (arrêtés GASPAR / Géorisques)": ("job_sur_clic", 190, "proposee"),
    "Taxe d'aménagement — taux communaux (délibérations)": ("depot_manuel", 365, "proposee"),
    "Cadastre d'époque (Etalab / PCI vecteur DGFiP)": ("one_shot", 365, "proposee"),
    # CIRCUIT-5b lot 1 — les quatre « à rattacher » entrent au catalogue avec leur cadence :
    "Annuaire de l'administration (service-public.fr / DILA)": ("cron_mensuel", 35, "proposee"),
    "RNIC — registre national des copropriétés (Anah)": ("one_shot", 365, "proposee"),
    "RPLS — répertoire des logements locatifs sociaux (SDES)": ("one_shot", 365, "proposee"),
    "Consommation d'espaces NAF (Cerema — portail de l'artificialisation)": ("one_shot", 365, "proposee"),
    # ── SOURCES-1 lot 1 — droit des sols ──
    "GPU — emplacements réservés (prescriptions CNIG)": ("en_direct", None, "sans_objet"),
    "GPU — espaces boisés classés (prescriptions CNIG)": ("en_direct", None, "sans_objet"),
    "GPU — droit de préemption urbain (info-surf)": ("job_sur_clic", 190, "proposee"),
    "PEB — plans d'exposition au bruit (DGAC via annexes GPU)": ("job_sur_clic", 365, "proposee"),
    "Zonage ABC des communes (DHUP)": ("job_sur_clic", 365, "declaree"),
    "ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)":
        ("absente", None, "sans_objet"),
    # ── SOURCES-1 lot 2 — nature et eau ──
    "Ravines — domaine public fluvial (DEAL Carmen)": ("job_sur_clic", 365, "proposee"),
    "Zones humides — inventaires DEAL (Carmen)": ("job_sur_clic", 365, "proposee"),
    "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)":
        ("job_sur_clic", 365, "proposee"),
    "AZI / TRI — inondation (Géorisques GASPAR)": ("job_sur_clic", 365, "proposee"),
    # ── SOURCES-1 lot 3 — sols et bruit ──
    "Géorisques — secteurs d'information sur les sols (SIS)": ("en_direct", None, "sans_objet"),
    "Géorisques — CASIAS (anciens sites industriels)": ("en_direct", None, "sans_objet"),
    "DEAL — cartes de bruit stratégiques (CBS)": ("job_sur_clic", 365, "proposee"),
}


def appliquer_modes_cadences(session: Session) -> int:
    """Pose (idempotent) les trois colonnes déclarées sur data_sources et les remplit depuis
    MODE_ET_CADENCE. Appelée par seed() ; ne touche jamais une autre colonne."""
    for ddl in (
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS mode_remplissage varchar(16)",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS cadence_attendue_jours integer",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS cadence_statut varchar(12)",
    ):
        session.execute(text(ddl))
    n = 0
    for nom, (mode, jours, statut) in MODE_ET_CADENCE.items():
        n += session.execute(text(
            "UPDATE data_sources SET mode_remplissage = :m, cadence_attendue_jours = :j,"
            " cadence_statut = :s WHERE name = :n"),
            {"m": mode, "j": jours, "s": statut, "n": nom}).rowcount
    if hasattr(session, "flush"):     # Session ORM ; une Connection brute (tests) n'a pas flush
        session.flush()
    return n
