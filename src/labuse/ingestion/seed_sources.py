"""Catalogue des sources de données (brief §6).

Alimente la table `data_sources` — qui incarne la promesse « tout relié au même
endroit ». Statuts HONNÊTES : dans cet environnement le réseau sortant est
restreint (allowlist), donc les connecteurs REST/WFS live sont `a_faire`
(écrits mais non vérifiés en ligne) et les couches du jeu de démo sont `mock`.

Les `name` ci-dessous sont les identifiants canoniques référencés par les couches
de la cascade (cascade/layers/*.py) et par le jeu de démo.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import DataSourceStatus as S
from ..enums import ReliabilityLevel as R
from ..models import DataSource

# (name, category, provider, access_type, status, reliability, rate_limit, doc, endpoint, legal, technical)
SOURCES: list[dict] = [
    # ── Cœur MVP — endpoints confirmés ──
    dict(name="Cadastre (API Carto PCI)", category="cadastre", provider="IGN / API Carto",
         access_type="REST/GeoJSON", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         rate_limit=None, documentation_url="https://apicarto.ign.fr/api/doc/cadastre",
         endpoint_url="https://apicarto.ign.fr/api/cadastre/parcelle",
         legal_notes="Parcellaire Express (PCI), MAJ semestrielle ; BD Parcellaire gelée depuis 2019.",
         technical_notes="Connecteur écrit (connectors/cadastre.py). Appel live BLOQUÉ par l'allowlist ici."),
    dict(name="Urbanisme PLU/GPU (API Carto)", category="urbanisme", provider="IGN / API Carto GPU",
         access_type="REST/GeoJSON", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://apicarto.ign.fr/api/doc/gpu",
         endpoint_url="https://apicarto.ign.fr/api/gpu/zone-urba",
         legal_notes=None,
         technical_notes="Couverture dépend de la dématérialisation locale ; fallback import PLU si absent."),
    dict(name="Géorisques", category="risques", provider="BRGM / MTE",
         access_type="REST", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://www.georisques.gouv.fr/doc-api",
         endpoint_url="https://www.georisques.gouv.fr/api/v1",
         legal_notes=None, technical_notes="catnat, azi, ppr, sismique, argiles, radon, cavités, BASIAS/BASOL."),
    dict(name="DVF / valeurs foncières", category="marche", provider="DGFiP / Cerema (DVF+)",
         access_type="import/CSV/GeoJSON", status=S.PARTIEL, reliability_level=R.VERIFIE,
         documentation_url="https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/",
         endpoint_url=None,
         legal_notes="R112 A-3 LPF : interdiction de réidentifier / d'indexer. Agréger, jamais nominatif.",
         technical_notes="Modèle : télécharger + ingérer dans PostGIS, requête PAR RAYON (§7bis). Démo = échantillon synthétique."),
    dict(name="RGE ALTI (altimétrie)", category="topographie", provider="IGN / Géoplateforme",
         access_type="REST", status=S.A_FAIRE, reliability_level=R.VERIFIE, rate_limit="5 req/s",
         documentation_url="https://geoservices.ign.fr/services-geoplateforme-altimetrie",
         endpoint_url="https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json",
         legal_notes=None,
         technical_notes="Batch commune : préférer ingestion raster + pente PostGIS/rasterio aux milliers d'appels."),
    # ── Spécificité réunionnaise (premier rang) ──
    dict(name="Parc National de La Réunion (INPN)", category="environnement", provider="INPN / MNHN",
         access_type="WFS/import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://inpn.mnhn.fr/", endpoint_url=None,
         legal_notes=None, technical_notes="Distinguer cœur (éliminatoire) et aire d'adhésion (flag). ~42 % de l'île."),
    dict(name="Forêts publiques (ONF)", category="environnement", provider="ONF",
         access_type="import/WFS", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None, legal_notes=None,
         technical_notes="Tester Feature Service / téléchargement ; sinon import SHP."),
    dict(name="SAR Réunion (PEIGEO)", category="urbanisme", provider="Région Réunion / AGORAH",
         access_type="WFS/import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://peigeo.re", endpoint_url=None,
         legal_notes="SAR juridiquement SUPÉRIEUR au PLU.",
         technical_notes="Espaces naturels/agricoles, coupures d'urbanisation. Import GeoJSON/SHP probable."),
    dict(name="Zonage SAFER (DAAF)", category="agricole", provider="DAAF Réunion",
         access_type="import", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url=None, endpoint_url=None,
         legal_notes="Droit de préemption SAFER.", technical_notes="« Zonage des terres agricoles selon la SAFER » (millésime 2023 constaté)."),
    # ── Hubs ──
    dict(name="PEIGEO (hub régional)", category="hub", provider="AGORAH",
         access_type="WMS/WFS", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://peigeo.re", endpoint_url=None,
         legal_notes=None, technical_notes="Hub n°1 local : occupation du sol, conso d'espace, PPR, SAR."),
    dict(name="DEAL Réunion (WMS/WFS)", category="hub", provider="DEAL Réunion",
         access_type="WMS/WFS", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://www.reunion.developpement-durable.gouv.fr", endpoint_url=None,
         legal_notes=None, technical_notes="PPRN, risques, trait de côte. Connecteur WFS générique (config/wfs_layers.yaml)."),
    dict(name="Géoplateforme IGN", category="hub", provider="IGN",
         access_type="WFS/WMS/téléchargement", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         rate_limit="10 req/s (téléchargement)",
         documentation_url="https://geoservices.ign.fr", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None, technical_notes="BD TOPO, OCS GE, parcellaire."),
    dict(name="data.regionreunion.com — Potentiel foncier", category="potentiel", provider="Région Réunion (Opendatasoft)",
         access_type="REST/GeoJSON", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://data.regionreunion.com", endpoint_url=None,
         legal_notes=None, technical_notes="Îlots > 500 m² (bâti) / 200 m² (vierge) hors tissu urbain. Utilisé en BONUS (§1)."),
    # ── Enrichissement ──
    dict(name="SITADEL (autorisations d'urbanisme)", category="dynamique", provider="SDES",
         access_type="import/CSV", status=S.PARTIEL, reliability_level=R.VERIFIE,
         documentation_url="https://www.statistiques.developpement-durable.gouv.fr", endpoint_url=None,
         legal_notes=None,
         technical_notes="MAJ mensuelle, DOM 974 couvert. ⚠ Sitadel3 depuis mars 2026. Appariement IDU vs signal de zone (§7bis)."),
    dict(name="BD TOPO IGN", category="topographie", provider="IGN / Géoplateforme",
         access_type="WFS/téléchargement", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/bdtopo", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None, technical_notes="Bâti, voirie, hydrographie, équipements. Démo = couches mock."),
    dict(name="Base Adresse Nationale", category="acces", provider="DINUM / IGN",
         access_type="REST", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://adresse.data.gouv.fr", endpoint_url="https://api-adresse.data.gouv.fr/search/",
         legal_notes=None, technical_notes="Géocodage + voie la plus proche."),
    dict(name="OpenStreetMap / Overpass", category="signal", provider="OSM",
         access_type="REST", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://wiki.openstreetmap.org/wiki/Overpass_API", endpoint_url="https://overpass-api.de/api/interpreter",
         legal_notes="Signal complémentaire, JAMAIS vérité juridique.",
         technical_notes="Faux positifs géométriques (cemetery, pitch, parking, school). Cacher agressivement (ban)."),
    dict(name="BPE INSEE", category="attractivite", provider="INSEE",
         access_type="import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://www.insee.fr/fr/statistiques?theme=1&debut=0&categorie=3", endpoint_url=None,
         legal_notes=None, technical_notes="Base permanente des équipements (millésime à confirmer)."),
    dict(name="SIRENE", category="economie", provider="INSEE",
         access_type="REST", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://www.sirene.fr", endpoint_url="https://recherche-entreprises.api.gouv.fr",
         legal_notes=None, technical_notes="Peut confirmer une personne morale propriétaire en attendant les Fichiers fonciers."),
    dict(name="OCS GE (IGN)", category="occupation_sol", provider="IGN / Géoplateforme",
         access_type="WFS/téléchargement", status=S.A_FAIRE, reliability_level=R.VERIFIE,
         documentation_url="https://geoservices.ign.fr/ocsge", endpoint_url="https://data.geopf.fr/wfs/ows",
         legal_notes=None, technical_notes="Artificialisé vs non (logique ZAN). Signal non juridique."),
    # ── Spécifiques / accès restreint ──
    dict(name="ABF / Monuments historiques", category="patrimoine", provider="Ministère Culture / Atlas patrimoine",
         access_type="import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url="https://atlas.patrimoines.culture.fr", endpoint_url=None,
         legal_notes=None, technical_notes="Périmètres 500 m."),
    dict(name="ENS (Département)", category="environnement", provider="Département de La Réunion",
         access_type="import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None,
         legal_notes="Droit de préemption départemental.", technical_notes="Source Département/PEIGEO."),
    dict(name="VRD / assainissement (SPANC)", category="reseaux", provider="EPCI",
         access_type="manuel", status=S.MANUEL, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None,
         legal_notes=None, technical_notes="Collectif vs non collectif : décisif. Souvent pas de donnée ouverte fine → lien EPCI + champ manuel."),
    dict(name="Fichiers fonciers (Cerema)", category="proprietaire", provider="DGFiP / Cerema",
         access_type="import", status=S.MANUEL, reliability_level=R.SOUS_CONVENTION,
         documentation_url="https://datafoncier.cerema.fr", endpoint_url=None,
         legal_notes="Accès sous convention. Version anonymisée : physiques masquées (_X_), morales complètes → RGPD-safe.",
         technical_notes="idprocpte / idprodroit → nb_droits_propriete = signal d'indivision. Champ manuel en attendant la convention."),
    dict(name="DEAL Réunion — trait de côte", category="risques", provider="DEAL Réunion",
         access_type="WFS/import", status=S.A_FAIRE, reliability_level=R.A_CONFIRMER,
         documentation_url=None, endpoint_url=None, legal_notes=None,
         technical_notes="Bandes de recul du trait de côte."),
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
