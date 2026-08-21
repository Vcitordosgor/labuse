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
         access_type="import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.insee.fr/fr/statistiques?theme=1&debut=0&categorie=3", endpoint_url=None,
         legal_notes="Licence Ouverte / Etalab 2.0 — attribution : « Source : Insee, Base permanente des équipements ».",
         technical_notes="Base permanente des équipements (import millésime)."),
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
    dict(name="ZNIEFF (INPN / Région)", category="environnement", provider="INPN/MNHN · Région ODS",
         access_type="REST/GeoJSON", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://data.regionreunion.com/explore/dataset/zones-naturelles-d-interet-ecologique-faunistique-et-floristique-a-la-reunion/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/zones-naturelles-d-interet-ecologique-faunistique-et-floristique-a-la-reunion/records",
         legal_notes="Licence à confirmer (jeu servi par la Région Réunion ODS — audit M6 §1.11 R8) ; producteur : INPN/MNHN.",
         technical_notes="M71 (audit M66/M66-B) : endpoint vivant mais 0 donnée ingérée, 0 usage — "
                         "repassé a_faire. Signal environnemental (non éliminatoire) à ingérer."),
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
    dict(name="DGFiP — parcelles des personnes morales", category="proprietaire", provider="DGFiP",
         source_millesime="Parcelles des PM — situation 2025 (DGFiP)",   # M125-1bis : endpoint ..._situation_2025_...
         access_type="téléchargement/CSV", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.economie.gouv.fr/explore/dataset/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/",
         endpoint_url="https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_parcelles_situation_2025_dpts_57_a_976_zip",
         legal_notes="Licence Ouverte v2 — attribution : « Source : DGFiP — parcelles des personnes morales ». "
                     "RGPD-safe : personnes MORALES uniquement (commune/État/SEM/bailleur/SCI), aucune personne physique.",
         technical_notes="M74 A : source AJOUTÉE au catalogue (elle alimentait le produit sans y figurer — audit "
                         "M74 C bis). Fichier DGFiP annuel (ZIP départemental, CSV PM_25_NB_974.csv), millésime 2025 : "
                         "82 701 parcelles de personnes morales → parcelle_personne_morale (owner_type/owner_name), lu "
                         "par la fiche (bloc Propriétaire) + recoupé avec BODACC/INPI. C'est la source réelle du "
                         "propriétaire moral, distincte des Fichiers fonciers Cerema conventionnés."),
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


def seed(session: Session) -> int:
    """Upsert idempotent du catalogue. Renvoie le nombre de sources présentes."""
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
    return session.query(DataSource).count()
