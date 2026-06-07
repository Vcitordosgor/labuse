"""Moteur de cascade d'exclusion — le cœur de LA BUSE (brief §2).

Importer ce paquet enregistre toutes les couches dans le registry.
"""
from .base import REGISTRY, Layer, Verdict, register  # noqa: F401
from . import layers  # noqa: F401  (effet de bord : enregistre les couches)
from .engine import run_cascade  # noqa: F401
from .pipeline import evaluate_parcels  # noqa: F401
