"""SOURCES-4 lot 2 — DVF+ : adresse / pièces / Carrez / lots (table latérale, additive).

La table `dvf_mutation_detail` est LATÉRALE : elle ne nourrit NI le scoring NI le marché servi —
elle est jointe à la liste des ventes de la fiche. On garde ici que l'agrégat Carrez (somme des
lots) et l'entier sont corrects, et que la table est déclarée au réservoir dvf (V1c).
"""
from __future__ import annotations

from labuse.ingestion.dvf_detail import _carrez, _int, TABLE


def test_carrez_somme_des_lots():
    assert _carrez({"lot1_surface_carrez": "45,5", "lot2_surface_carrez": "12.5"}) == 58.0
    assert _carrez({"lot1_surface_carrez": "", "lot2_surface_carrez": ""}) is None   # aucun → None
    assert _carrez({}) is None


def test_int_tolerant():
    assert _int("4") == 4 and _int("4.0") == 4
    assert _int("") is None and _int(None) is None and _int("x") is None


def test_dvf_detail_declaree_au_reservoir():
    from labuse.registre import tables
    assert TABLE in tables.RESERVOIR_TABLES["dvf"].tables
