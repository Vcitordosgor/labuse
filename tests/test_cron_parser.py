"""RETOURS-8 (R4.1) — le parseur cron de l'Horloge comprend la grammaire réelle.

Avant : `_champ_match` faisait `int('7,37')` → ValueError sur le job `sante-endpoints` (« 7,37 * * * * »),
et l'Horloge plantait. Il supporte désormais listes (`,`), plages (`-`), pas (`/`) et `*`, combinés.
"""
from __future__ import annotations

from labuse.jobs import _champ_match, prochaine


def test_liste_virgule():
    # le cas qui plantait : « 7,37 » (minutes 7 et 37)
    assert _champ_match(7, "7,37") and _champ_match(37, "7,37")
    assert not _champ_match(8, "7,37")


def test_pas_sur_etoile():
    assert _champ_match(0, "*/15") and _champ_match(15, "*/15") and _champ_match(30, "*/15")
    assert not _champ_match(7, "*/15")


def test_plage():
    assert all(_champ_match(v, "1-5") for v in (1, 2, 3, 4, 5))
    assert not _champ_match(0, "1-5") and not _champ_match(6, "1-5")


def test_etoile_et_entier():
    assert _champ_match(23, "*") and _champ_match(5, "5")
    assert not _champ_match(6, "5")


def test_combine_et_pas_sur_plage():
    # liste de termes hétérogènes
    assert _champ_match(30, "1-5,30") and _champ_match(3, "1-5,30")
    assert not _champ_match(6, "1-5,30")
    # pas sur une plage : 0-30/10 → 0,10,20,30
    assert _champ_match(20, "0-30/10") and not _champ_match(25, "0-30/10")


def test_illisible_ne_matche_pas_et_ne_leve_pas():
    assert not _champ_match(1, "abc")       # jamais une exception qui casse l'Horloge


def test_prochaine_sur_liste_de_minutes():
    """La régression concrète : `prochaine` d'un cron à liste ne lève plus et tombe sur 7 ou 37."""
    t = prochaine("7,37 * * * *")
    assert t is not None and t.minute in (7, 37)
