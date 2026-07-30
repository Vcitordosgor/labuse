"""Point de calcul unique de normalisation de zone (pt2.2, Vic).

Verrouille la règle CRITIQUE : la normalisation matche la FAMILLE mais ne perd JAMAIS le rang de
phasage — 1AU, 2AU, 3AU sont trois statuts d'ouverture distincts. Sans DB.
"""
from __future__ import annotations

from labuse.faisabilite.zone_norm import (
    normalize_key, famille_normalisee, zone_phasage, est_famille,
)


def test_normalize_key_casse_accents_separateurs():
    # casse, accents, espaces, tirets, apostrophes, points → même clé
    assert normalize_key("AUB") == normalize_key("AUb") == normalize_key("aub") == "aub"
    assert normalize_key("AU-b") == normalize_key("AU b") == normalize_key("AU.b") == "aub"
    assert normalize_key("Ûb") == "ub"


def test_normalize_key_conserve_le_phasage():
    # LE POINT CRITIQUE : le rang de phasage n'est JAMAIS perdu — clés distinctes.
    assert normalize_key("1AUb") == "1aub"
    assert normalize_key("2AUb") == "2aub"
    assert normalize_key("1AUb") != normalize_key("2AUb") != normalize_key("AUb")


def test_famille_retire_le_phasage():
    # pour la CASCADE : « 2AUc » se classe AU (phasage retiré), jamais « autre »
    assert famille_normalisee("2AUc") == "AUC"
    assert est_famille("2AUc", ("U", "AU")) is True
    assert est_famille("1AUst", ("U", "AU")) is True
    assert est_famille("Acu", ("A", "N")) is True
    assert est_famille("Uba", ("A", "N")) is False


def test_zone_phasage_expose_le_rang():
    assert zone_phasage("2AUc") == 2
    assert zone_phasage("1AUst") == 1
    assert zone_phasage("AUc") is None
