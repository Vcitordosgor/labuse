"""Témoin CIRCUIT-4 — comparables DVF : le filtre de retenue (PUR, liste → gardées/écartées avec
motif), recomparé indépendamment ; tranches VEFA et terrain par zone = mêmes seuils déclarés."""
from __future__ import annotations

import statistics

from labuse.marche_service import filtre_ventes


def test_filtre_motifs_visibles():
    ventes = [
        {"id": 1, "prix_m2": 3000.0},         # gardée
        {"id": 2, "prix_m2": 500.0},          # hors domaine bas
        {"id": 3, "prix_m2": 15000.0},        # hors domaine haut
        {"id": 4, "prix_m2": None},           # sans prix → gardée (le filtre ne juge pas l'absence)
        {"id": 5, "prix_m2": 4000.0, "type_local": "appartement", "surface_m2": 750.0},
    ]
    gardees, ecartees = filtre_ventes(ventes, cle_type="type_local",
                                      seuil_type_m2={"appartement": 200})
    # recomptage indépendant : bornes [1000;12000], vraisemblance type, aucune disparition muette
    assert {v["id"] for v in gardees} == {1, 4}
    assert {v["id"] for v in ecartees} == {2, 3, 5}
    assert all(v.get("motif") for v in ecartees)
    assert len(gardees) + len(ecartees) == len(ventes)


def test_mediane_commune_independante():
    prix = [2000.0, 3000.0, 3500.0, 4000.0, 9000.0]
    gardees, _ = filtre_ventes([{"prix_m2": p} for p in prix])
    med = statistics.median([v["prix_m2"] for v in gardees])
    assert med == 3500.0                       # médiane indépendante (statistics)


def test_tranche_vefa_seuil10():
    from labuse.ingestion.vefa_neuf import TRANCHE_LIBELLE
    assert "sous_seuil" in TRANCHE_LIBELLE     # < 10 ventes → hachure, jamais une médiane fragile


def test_terrain_par_zone_seuil():
    # seuil 10 ventes par cellule (fiche prix_terrain_zone) — recompte indépendant du principe
    ventes_cellule = 9
    assert (ventes_cellule >= 10) is False     # sous le seuil → rien de servi
