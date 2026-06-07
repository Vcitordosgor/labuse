"""Connecteurs de sources externes (REST/WFS/ODS).

Accès réseau COMPLET (SPIKE 2026-06) : les sources confirmées live sont câblées
dans REGISTRY et testables via `test_connection()` (bouton « tester la connexion »
de la page Sources). Les sources sans flux ouvert (PEIGEO/DEAL injoignables, ONF,
SAFER, ENS, Fichiers fonciers) restent en import/manuel — pas de connecteur live.
Le parsing reste couvert par des fixtures (tests/test_connectors.py).
"""
from __future__ import annotations

from .base import ConnectionTestResult, Connector, GenericGetConnector
from .cadastre import CadastreConnector
from .georisques import GeorisquesConnector
from .gpu import GpuConnector
from .wfs import WfsConnector

# Petit polygone de test sur le centre de Saint-Paul (97415) pour les endpoints `geom`.
_SAINT_PAUL_TOWN = (
    '{"type":"Polygon","coordinates":[[[55.284,-21.012],[55.290,-21.012],'
    '[55.290,-21.006],[55.284,-21.006],[55.284,-21.012]]]}'
)
_GEOPF_WFS_BDTOPO = {
    "service": "WFS", "version": "2.0.0", "request": "GetFeature",
    "typeNames": "BDTOPO_V3:batiment", "outputFormat": "application/json", "count": 1,
}
_ODS = "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets"

# data_sources.name -> connecteur (pour la page Sources / bouton test).
# Sources confirmées live au SPIKE réseau (2026-06) → testables. Les noms DOIVENT
# matcher data_sources.name (ingestion/seed_sources.py).
REGISTRY: dict[str, Connector] = {
    # Connecteurs spécialisés (méthodes de fetch dédiées).
    "Cadastre (API Carto PCI)": CadastreConnector(),
    "Urbanisme PLU/GPU (API Carto)": GpuConnector(),
    "Géorisques": GeorisquesConnector(),
    # Connecteurs de test génériques (GET simple, succès = HTTP 200).
    "Cadastre Etalab (bulk DGFiP/Etalab)": GenericGetConnector(
        "Cadastre Etalab (bulk DGFiP/Etalab)",
        "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/974/97415/",
    ),
    "RGE ALTI (altimétrie)": GenericGetConnector(
        "RGE ALTI (altimétrie)",
        "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json",
        {"lon": "55.27", "lat": "-21.01", "resource": "ign_rge_alti_wld", "zonly": "true"},
    ),
    "Géoplateforme IGN": GenericGetConnector(
        "Géoplateforme IGN", "https://data.geopf.fr/wfs/ows", dict(_GEOPF_WFS_BDTOPO),
    ),
    "BD TOPO IGN": GenericGetConnector(
        "BD TOPO IGN", "https://data.geopf.fr/wfs/ows", dict(_GEOPF_WFS_BDTOPO),
    ),
    "Base Adresse Nationale": GenericGetConnector(
        "Base Adresse Nationale", "https://api-adresse.data.gouv.fr/search/",
        {"q": "saint-paul reunion", "limit": 1},
    ),
    "OpenStreetMap / Overpass": GenericGetConnector(
        "OpenStreetMap / Overpass", "https://overpass-api.de/api/interpreter",
        {"data": '[out:json][timeout:20];node["amenity"="townhall"](around:3000,-21.009,55.286);out 1;'},
    ),
    "SIRENE": GenericGetConnector(
        "SIRENE", "https://recherche-entreprises.api.gouv.fr/search",
        {"q": "mairie saint-paul", "departement": "974", "per_page": 1},
    ),
    "Parc National de La Réunion (INPN)": GenericGetConnector(
        "Parc National de La Réunion (INPN)", f"{_ODS}/pnrun_2021/records", {"limit": 1},
    ),
    "data.regionreunion.com — Potentiel foncier": GenericGetConnector(
        "data.regionreunion.com — Potentiel foncier", f"{_ODS}/potentiel-foncier/records", {"limit": 1},
    ),
    "Région Réunion Open Data (Opendatasoft)": GenericGetConnector(
        "Région Réunion Open Data (Opendatasoft)", _ODS, {"limit": 1},
    ),
    "ZNIEFF (INPN / Région)": GenericGetConnector(
        "ZNIEFF (INPN / Région)",
        f"{_ODS}/zones-naturelles-d-interet-ecologique-faunistique-et-floristique-a-la-reunion/records",
        {"limit": 1},
    ),
    "ABF / Monuments historiques": GenericGetConnector(
        "ABF / Monuments historiques", "https://apicarto.ign.fr/api/gpu/assiette-sup-s",
        {"geom": _SAINT_PAUL_TOWN},
    ),
}


def get_connector(source_name: str) -> Connector | None:
    return REGISTRY.get(source_name)


__all__ = [
    "ConnectionTestResult", "Connector", "GenericGetConnector", "CadastreConnector",
    "GpuConnector", "GeorisquesConnector", "WfsConnector", "REGISTRY", "get_connector",
]
