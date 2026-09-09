"""RECETTE-8 W14 — la règle d'accord singulier/pluriel des équipements de proximité.

Le bug : « 1 bu » (le « s » de « bus », invariable, était mangé par un rstrip('s') naïf).
On teste chaque catégorie servie (api.app._PROX_EQUIP) à 0, 1 et 2.
"""
from __future__ import annotations

import pytest

from labuse.exports.blocs.autour import _EQUIP_ACCORD, _accord

CATS = ["École", "Commerces", "Santé", "Bus"]


@pytest.mark.parametrize("cat", CATS)
def test_categorie_connue_du_registre_daccord(cat):
    assert cat in _EQUIP_ACCORD, f"{cat} n'a pas de forme singulier/pluriel déclarée"


@pytest.mark.parametrize("cat", CATS)
@pytest.mark.parametrize("n", [0, 1, 2])
def test_accord_a_0_1_2(cat, n):
    sing, plur = _EQUIP_ACCORD[cat]
    attendu = f"{n} {sing if n <= 1 else plur}"
    assert _accord(cat, n) == attendu


def test_bus_ne_perd_jamais_son_s():
    # le bug historique : « 1 bu ». « bus » est invariable.
    assert _accord("Bus", 1) == "1 arrêt de bus"
    assert _accord("Bus", 2) == "2 arrêts de bus"
    assert "bu " not in _accord("Bus", 1) + " " and _accord("Bus", 1).split()[1].startswith("arrêt")


def test_commerces_singularise_bien():
    assert _accord("Commerces", 1) == "1 commerce"
    assert _accord("Commerces", 3) == "3 commerces"
