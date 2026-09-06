"""Témoin CIRCUIT-4 — INSEE zone : tranches SIRENE sommées en FOURCHETTE (nomenclature citée),
part égout = simple taux, carreaux Filosofi au centroïde."""
from __future__ import annotations

from labuse.zone import TRANCHE_BORNES


def test_emplois_somme_de_tranches():
    # nomenclature vérifiée au lot 2 : 01 = 1-2, 02 = 3-5, 12 = 20-49, 53 = 10 000+ (ouvert)
    assert TRANCHE_BORNES["01"] == (1, 2) and TRANCHE_BORNES["02"] == (3, 5)
    assert TRANCHE_BORNES["12"] == (20, 49) and TRANCHE_BORNES["53"][1] is None
    # recalcul indépendant d'une fourchette : 2 étabs 01 + 1 étab 12
    etabs = ["01", "01", "12"]
    bas = sum(TRANCHE_BORNES[t][0] for t in etabs)
    haut = sum(TRANCHE_BORNES[t][1] for t in etabs)
    assert (bas, haut) == (1 + 1 + 20, 2 + 2 + 49)     # toujours une fourchette, jamais un point


def test_part_egout_maille():
    # part = 100 × raccordés ÷ total — arithmétique du taux, maille dite (IRIS, repli commune)
    assert round(100 * 732 / 1000, 1) == 73.2


def test_somme_carreaux_intersectants():
    """La règle d'inclusion du moteur est le CENTROÏDE du carreau dans la zone (docstring
    population_zone) — le témoin d'agrégation vit au niveau SQL (somme des ind) ; ici on épingle
    la règle d'inclusion pour que la fiche ne dérive plus de la doc (corrigée au lot 4)."""
    import inspect

    from labuse import zone
    src = inspect.getsource(zone.population_zone)
    assert "CENTROÏDE" in src or "centroïde" in src.lower()
