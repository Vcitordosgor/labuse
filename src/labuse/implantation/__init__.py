"""IMPLANTATION-1 — premier moteur d'implantation collectif.

Un terrain (assiette de parcelles fusionnées), une zone d'implantation réglementaire, un
scénario : le moteur dessine une géométrie (bâtiments, modules, noyaux, coursives, places,
allées, accès, espaces libres) en EPSG:2975, puis en TIRE le tableau de capacité et les
contrôles. Déterministe, sans IA, aucun calcul au front.

Entrée unique : `moteur.etudier(...)`. Voir `docs/audit-2026-10/implantation-1/`.
"""
from __future__ import annotations

__all__ = ["etudier"]


def etudier(*args, **kwargs):  # import paresseux (shapely/DB) — garde le package léger
    from .moteur import etudier as _etudier
    return _etudier(*args, **kwargs)
