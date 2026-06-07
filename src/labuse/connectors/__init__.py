"""Connecteurs de sources externes (REST/WFS).

⚠ Réseau restreint dans cet environnement : les appels live sont bloqués par
l'allowlist. Les connecteurs sont écrits d'après les formats documentés
`[✓ vérifié]` du brief §6 et testés contre des FIXTURES (tests/test_connectors.py).
`test_connection()` tente l'appel réel et rapporte honnêtement le résultat —
c'est le moteur du bouton « tester la connexion » de la page Sources.
"""
from __future__ import annotations

from .base import ConnectionTestResult, Connector
from .cadastre import CadastreConnector
from .georisques import GeorisquesConnector
from .gpu import GpuConnector
from .wfs import WfsConnector

# data_sources.name -> connecteur (pour la page Sources / bouton test).
REGISTRY: dict[str, Connector] = {
    "Cadastre (API Carto PCI)": CadastreConnector(),
    "Urbanisme PLU/GPU (API Carto)": GpuConnector(),
    "Géorisques": GeorisquesConnector(),
}


def get_connector(source_name: str) -> Connector | None:
    return REGISTRY.get(source_name)


__all__ = [
    "ConnectionTestResult", "Connector", "CadastreConnector", "GpuConnector",
    "GeorisquesConnector", "WfsConnector", "REGISTRY", "get_connector",
]
