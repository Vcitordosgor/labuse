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

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import DataSourceStatus as S
from ..enums import ReliabilityLevel as R
from ..models import DataSource

# (name, category, provider, access_type, status, reliability_level, rate_limit, doc, endpoint, legal, technical)
SOURCES: list[dict] = [
    # ── Cœur MVP — flux live confirmés au SPIKE (2026-06) ──
    dict(name="Cadastre (API Carto PCI)", category="cadastre", provider="IGN / API Carto",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         rate_limit=None, documentation_url="https://apicarto.ign.fr/api/doc/cadastre",
         endpoint_url="https://apicarto.ign.fr/api/cadastre/parcelle",
         legal_notes="Parcellaire Express (PCI), MAJ semestrielle ; BD Parcellaire gelée depuis 2019.",
         technical_notes="✓ live (HTTP 200). Lookup unitaire (parcelle/section/geom). Ingestion EN MASSE via Cadastre Etalab (bulk), pas cette API en boucle (§4)."),
    dict(name="Cadastre Etalab (bulk DGFiP/Etalab)", category="cadastre", provider="DGFiP / Etalab",
         access_type="téléchargement/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://cadastre.data.gouv.fr/datasets/cadastre-etalab",
         endpoint_url="https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/974/97415/cadastre-97415-parcelles.json.gz",
         legal_notes=None,
         technical_notes="✓ live : parcelles 97415 = 5,36 Mo (.json.gz) ; dépt 974 = 54 Mo. Source d'ingestion EN MASSE des parcelles."),
    dict(name="Urbanisme PLU/GPU (API Carto)", category="urbanisme", provider="IGN / API Carto GPU",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/zone-urba",
         legal_notes=None,
         technical_notes="✓ live : Saint-Paul DÉMATÉRIALISÉE (partition DU_97415). zone-urba + assiette-sup-s (SUP) OK."),
    dict(name="Géorisques", category="risques", provider="BRGM / MTE",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1",
         legal_notes=None,
         technical_notes="✓ live : gaspar/risques, gaspar/catnat, gaspar/azi, rga, zonage_sismique (HTTP 200). ⚠ pas d'endpoint /ppr en v1 (404)."),
    dict(name="DEAL Réunion — PPR / aléas", category="risques", provider="DEAL Réunion (Lizmap)",
         access_type="WFS/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://deal974.lizmap.com/cartes/index.php/view/map?repository=02sprinr&project=01risque",
         endpoint_url="https://deal974.lizmap.com/cartes/index.php/lizmap/service?repository=02sprinr&project=01risque",
         legal_notes=None,
         technical_notes="✓ validé spike 2026-06 : PPR_APPROUVE (zonage rouge=INTERDICTION / bleu=PRESCRIPTION, MultiPolygon EPSG:2975, champs CODE_INSEE/RISQUE/DEGRE/CODE_DEGRE) ; ALEA_INONDATION (degre FAIBLE/MOYEN/FORT + RESIDUEL_*) ; ALEA_MOUVEMENT_TERRAIN. Filtre CODE_INSEE."),
    dict(name="DVF / valeurs foncières", category="marche", provider="DGFiP / Cerema · Région ODS",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/demande-de-valeurs-foncierespublic/records",
         legal_notes="R112 A-3 LPF : interdiction de réidentifier / d'indexer. Agréger, jamais nominatif.",
         technical_notes="✓ ingéré : Région ODS, géolocalisé par jointure l_idpar→parcelle (centroïde). Requête PAR RAYON, agrégée (§7bis). geo-DVF DGFiP exclut le 974."),
    dict(name="RGE ALTI (altimétrie)", category="topographie", provider="IGN / Géoplateforme",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="5 req/s",
         documentation_url="https://geoservices.ign.fr/services-geoplateforme-altimetrie",
         endpoint_url="https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json",
         legal_notes=None,
         technical_notes="✓ live (elevations:[6.43]). Batch commune : préférer raster RGE ALTI + pente PostGIS aux milliers d'appels."),
    # ── Spécificité réunionnaise (premier rang) ──
    dict(name="Parc National de La Réunion (INPN)", category="environnement", provider="INPN/MNHN · API Carto · Région ODS",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com/explore/dataset/pnrun_2021/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/pnrun_2021/records",
         legal_notes=None,
         technical_notes="✓ live : pnrun_2021 champ `type` = « Coeur du Parc national » (HARD_EXCLUDE) vs « Aire d'Adhésion » (SOFT_FLAG). Aussi apicarto/nature/pn. INPN direct en maintenance au 2026-06-07."),
    dict(name="Forêts publiques (ONF)", category="environnement", provider="ONF / IGN (BD TOPO)",
         access_type="WFS", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/bdtopo", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None,
         technical_notes="✓ intégré auto : BDTOPO_V3:foret_publique (Géoplateforme, régime forestier). toponyme « domaniale » → HARD_EXCLUDE, sinon flag fort."),
    dict(name="SAR Réunion (PEIGEO)", category="urbanisme", provider="Région Réunion / AGORAH",
         access_type="import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://peigeo.re", endpoint_url=None,
         legal_notes="SAR juridiquement SUPÉRIEUR au PLU.",
         technical_notes="INTROUVABLE EN PUBLIC (data.gouv vide, Région ODS vide, PEIGEO HTTP 503 sans OWS, DEAL injoignable). Reste UNKNOWN — listée au bandeau."),
    dict(name="Zonage SAFER (DAAF)", category="agricole", provider="DAAF (propre non public) · proxy RPG/IGN",
         access_type="WFS", status=S.PARTIEL, reliability_level=R.A_CONFIRMER,
         documentation_url="https://geoservices.ign.fr/services-geoplateforme-diffusion", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Droit de préemption SAFER.",
         technical_notes="Zonage SAFER/DAAF propre INTROUVABLE en public. ✓ proxy intégré : RPG.LATEST (parcelles agricoles déclarées, Géoplateforme) en flag agricole."),
    # ── Hubs ──
    dict(name="Région Réunion Open Data (Opendatasoft)", category="hub", provider="Région Réunion (Opendatasoft)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets",
         legal_notes=None,
         technical_notes="✓ live : 275 datasets. Clés : pnrun_2021 (Parc cœur/adhésion), potentiel-foncier, base PLU, permis de construire, DVF, ZNIEFF."),
    dict(name="PEIGEO (hub régional)", category="hub", provider="AGORAH",
         access_type="WMS/WFS", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://peigeo.re", endpoint_url=None,
         legal_notes=None, technical_notes="⚠ Hôte injoignable depuis l'infra (HTTP 000, 2026-06-07). Fallback Région ODS / import."),
    dict(name="DEAL Réunion (WMS/WFS)", category="hub", provider="DEAL Réunion",
         access_type="WMS/WFS", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.reunion.developpement-durable.gouv.fr", endpoint_url=None,
         legal_notes=None, technical_notes="⚠ carto.reunion.developpement-durable.gouv.fr injoignable (HTTP 000). Risques via Géorisques en proxy ; sinon import."),
    dict(name="Géoplateforme IGN", category="hub", provider="IGN",
         access_type="WFS/WMS/téléchargement", status=S.CONNECTE, reliability_level=R.VERIFIE,
         rate_limit="10 req/s (téléchargement)",
         documentation_url="https://geoservices.ign.fr", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None, technical_notes="✓ live : WFS GetFeature BDTOPO_V3:batiment (51 M features). BD TOPO/parcellaire ; OCS GE typename à confirmer."),
    dict(name="data.regionreunion.com — Potentiel foncier", category="potentiel", provider="Région Réunion (Opendatasoft)",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com/explore/dataset/potentiel-foncier/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier/records",
         legal_notes=None,
         technical_notes="✓ live : grain PARCELLE (section/parcelle/espacesar/zpu). Îlots > 500 m² (bâti) / 200 m² (vierge). BONUS (§1) + proxy SAR."),
    # ── Enrichissement ──
    dict(name="SITADEL (autorisations d'urbanisme)", category="dynamique", provider="SDES",
         access_type="import/CSV", status=S.PARTIEL, reliability_level=R.VERIFIE,
         documentation_url="https://www.statistiques.developpement-durable.gouv.fr", endpoint_url=None,
         legal_notes=None,
         technical_notes="MAJ mensuelle, DOM 974. ⚠ Sitadel3 depuis mars 2026. Appariement IDU §7bis. Alt. live : Région ODS « liste-des-permis-de-construire »."),
    dict(name="BD TOPO IGN", category="topographie", provider="IGN / Géoplateforme",
         access_type="WFS/téléchargement", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/bdtopo", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None, technical_notes="✓ live : BDTOPO_V3:batiment (bâti, voirie, hydrographie, équipements)."),
    dict(name="Base Adresse Nationale", category="acces", provider="DINUM / IGN",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://adresse.data.gouv.fr", endpoint_url="https://api-adresse.data.gouv.fr/search/",
         legal_notes=None, technical_notes="✓ live : géocodage + voie la plus proche."),
    dict(name="OpenStreetMap / Overpass", category="signal", provider="OSM",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://wiki.openstreetmap.org/wiki/Overpass_API", endpoint_url="https://overpass-api.de/api/interpreter",
         legal_notes="Signal complémentaire, JAMAIS vérité juridique.",
         technical_notes="✓ live (UA applicatif requis, sinon 406). Faux positifs géométriques (cemetery, pitch, parking, school). Cacher agressivement."),
    dict(name="BPE INSEE", category="attractivite", provider="INSEE",
         access_type="import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.insee.fr/fr/statistiques?theme=1&debut=0&categorie=3", endpoint_url=None,
         legal_notes=None, technical_notes="Base permanente des équipements (import millésime)."),
    dict(name="BODACC (procédures collectives)", category="economie", provider="DILA (Opendatasoft)",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE, rate_limit="throttle poli",
         documentation_url="https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/",
         endpoint_url="https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records",
         legal_notes="Licence Ouverte v2.0 — paternité DILA. RGPD : signal INTERNE de priorisation (personnes morales, open data), jamais un export nominatif de masse (règle d'archi #2).",
         technical_notes="✓ live 05/07/2026 (schéma vérifié, record A200902491993). Filtre familleavis='collective' (BODACC A). Interrogé par SIREN (registre[]), batché registre IN(...). Vague A1 : flag foncier_sous_pression (# TODO étage 2). last_sync_at posé à l'ingestion."),
    dict(name="SIRENE", category="economie", provider="INSEE / annuaire-entreprises",
         access_type="REST", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://recherche-entreprises.api.gouv.fr/docs", endpoint_url="https://recherche-entreprises.api.gouv.fr/search",
         legal_notes=None, technical_notes="✓ live : confirme une personne morale propriétaire en attendant les Fichiers fonciers."),
    dict(name="OCS GE (IGN)", category="occupation_sol", provider="IGN / Géoplateforme",
         access_type="WFS", status=S.PARTIEL, reliability_level=R.A_CONFIRMER,
         documentation_url="https://geoservices.ign.fr/ocsge", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None, technical_notes="OCS GE 974 non exposé en WFS geopf (OCSGE:occupation_du_sol → 400). Proxy actuel : BDCARTO_V5:occupation_du_sol (naturel/agricole/artificialisé). Signal non juridique."),
    dict(name="ZNIEFF (INPN / Région)", category="environnement", provider="INPN/MNHN · Région ODS",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com/explore/dataset/zones-naturelles-d-interet-ecologique-faunistique-et-floristique-a-la-reunion/",
         endpoint_url="https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/zones-naturelles-d-interet-ecologique-faunistique-et-floristique-a-la-reunion/records",
         legal_notes=None, technical_notes="✓ live : ZNIEFF I/II. Signal environnemental (non éliminatoire)."),
    # ── Spécifiques / accès restreint ──
    dict(name="ABF / Monuments historiques", category="patrimoine", provider="API Carto GPU (SUP) / Atlas patrimoine",
         access_type="REST/GeoJSON", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://apicarto.ign.fr/api/doc/gpu", endpoint_url="https://apicarto.ign.fr/api/gpu/assiette-sup-s",
         legal_notes=None, technical_notes="✓ live : SUP via assiette-sup-s (filtrer suptype AC1 = abords MH ; AC2 sites). Périmètres 500 m / délimités."),
    dict(name="ENS (Département)", category="environnement", provider="INPN/MNHN (espaces protégés) · ENS dép. non public",
         access_type="WFS", status=S.PARTIEL, reliability_level=R.A_CONFIRMER,
         documentation_url="https://inpn.mnhn.fr/", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes="Droit de préemption départemental.",
         technical_notes="ENS départemental propre INTROUVABLE en public. ✓ espaces protégés réglementaires intégrés (APB/RNN/réserve biologique/CEN/conservatoire littoral, patrinat Géoplateforme/INPN)."),
    dict(name="VRD / assainissement (SPANC)", category="reseaux", provider="EPCI",
         access_type="manuel", status=S.MANUEL, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None,
         legal_notes=None, technical_notes="Collectif vs non collectif : décisif. Souvent pas de donnée ouverte fine → lien EPCI + champ manuel."),
    dict(name="Fichiers fonciers (Cerema)", category="proprietaire", provider="DGFiP / Cerema",
         access_type="import", status=S.MANUEL, reliability_level=R.SOUS_CONVENTION,
         documentation_url="https://datafoncier.cerema.fr", endpoint_url=None,
         legal_notes="Accès sous convention. Version anonymisée : physiques masquées (_X_), morales complètes → RGPD-safe.",
         technical_notes="idprocpte / idprodroit → nb_droits_propriete = signal d'indivision. Champ manuel en attendant la convention."),
    dict(name="DEAL Réunion — trait de côte", category="risques", provider="Cerema / GéoLittoral",
         access_type="import/SHP", status=S.CONNECTE, reliability_level=R.VERIFIE,
         documentation_url="https://www.geolittoral.developpement-durable.gouv.fr/indicateur-national-de-l-erosion-cotiere-a1434.html",
         endpoint_url="https://geolittoral.din.developpement-durable.gouv.fr/telechargement/couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip",
         legal_notes=None,
         technical_notes="✓ intégré : SHP indicateur national d'érosion côtière (Réunion, EPSG:2975→4326). Champ `taux` (m/an) : recul fort ≤ -1 → exclude, recul modéré → flag."),
]


def seed(session: Session) -> int:
    """Upsert idempotent du catalogue. Renvoie le nombre de sources présentes."""
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
