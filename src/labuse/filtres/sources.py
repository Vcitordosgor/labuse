"""CIRCUIT-3 lot 2 — LES FILTRES PAR SOURCE (contrôles propres).

Chaque source qui pèse déclare ici son `Filtre` avec ses contrôles PROPRES, en plus des
universels hérités du cadre. Les seuils sont écrits AVEC la mesure qui les a fixés (la valeur
observée au 05/09/2026 sur la base servie `labuse`). Un seuil non mesuré reste `avertissant`.

Ce module est rempli lot par lot ; `filtres/__init__.py` fusionne `FILTRES_RICHES` avec les
filtres par défaut de toutes les sources à job (sources_ingestion.yaml, test 1.5).
"""
from __future__ import annotations

from .cadre import Filtre

# Rempli au lot 2 : source_key -> Filtre riche.
FILTRES_RICHES: dict[str, Filtre] = {}
