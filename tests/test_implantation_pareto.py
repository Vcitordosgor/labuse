"""IMPLANTATION-4 (scénarios dominés) — le filtre de Pareto (unitaire, sans base).

Critères : logements, surface habitable, simplicité (moins de bâtiments). Les places NE comptent pas.
Dominé = ≤ sur les trois ET < sur au moins un → disparaît. Métriques identiques → on garde le premier
(ordre d'entrée = ordre de l'objectif). Un seul survivant = un seul scénario.
"""
from types import SimpleNamespace as NS

from labuse.implantation.moteur import _domine, _n_batiments, _pareto


def _scene(n_bat, n_place=10):
    return NS(objets=[NS(kind="batiment_emprise")] * n_bat + [NS(kind="place")] * n_place)


def _item(logts, shab, n_bat, forme="barre"):
    cap = NS(logements=logts, shab_estimee_m2=shab)
    return (None, (_scene(n_bat), cap), forme, 3, 1.0)   # (clef, paquet=(scene,cap), forme, niveaux, frac)


def test_n_batiments_compte_les_emprises():
    assert _n_batiments(_scene(2)) == 2
    assert _n_batiments(_scene(1)) == 1


def test_domine_sur_les_trois():
    # a ≥ b sur (logts, shab) et ≤ sur n_bat, strict quelque part → a domine b
    assert _domine((28, 1312.0, 1), (26, 1300.0, 2)) is True
    assert _domine((28, 1312.0, 1), (28, 1312.0, 2)) is True      # strict sur n_bat seulement
    assert _domine((28, 1312.0, 1), (28, 1312.0, 1)) is False     # identiques → pas de domination
    assert _domine((28, 1312.0, 2), (28, 1312.0, 1)) is False     # a a PLUS de bâtiments → ne domine pas


def test_deux_barres_dominees_par_la_barre_disparait():
    # barre 28/1312/1 bâtiment domine deux_barres 26/1300/2 → un seul affiché
    survivants = _pareto([_item(28, 1312, 1, "barre"), _item(26, 1300, 2, "deux_barres")])
    assert len(survivants) == 1
    assert survivants[0][2] == "barre"


def test_front_de_pareto_garde_les_non_domines():
    # la barre est plus simple ; les deux barres font plus de logements+shab → aucun ne domine l'autre
    survivants = _pareto([_item(28, 1312, 1, "barre"), _item(32, 1500, 2, "deux_barres")])
    assert len(survivants) == 2


def test_metriques_identiques_garde_le_premier():
    # même (logts, shab, n_bat) → un seul gardé, le premier (meilleur par l'objectif)
    survivants = _pareto([_item(28, 1312, 1, "barre"), _item(28, 1312, 1, "L")])
    assert len(survivants) == 1
    assert survivants[0][2] == "barre"


def test_les_places_ne_sont_pas_un_critere():
    # deux candidats égaux sur logts/shab/n_bat mais places différentes → un seul gardé (places ignorées)
    a = _item(20, 900, 1); b = _item(20, 900, 1)
    a[1][0].objets += [NS(kind="place")] * 40    # a a beaucoup plus de places : sans effet
    assert len(_pareto([a, b])) == 1
