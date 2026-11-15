"""CHIRURGICAL-FIX-1 — gardes UNITAIRES (sans base) des corrections de libellés.

· E105 — `estimer3._zone_code` ne prend plus un MOT (« Pas », « Zone ») pour un code de zone PLU :
  sur une commune au RNU (« Pas de PLU local… ») il rend None → plus de « (Pas) » dans Estimer ;
  les vrais codes (A, N, Ud, 1AU) restent extraits.
· E112a — `_cause_court` (Comparatif, écran + PDF) écrit une cause « code:ZONE » EN CLAIR
  (« habitat_interdit:UE » → « habitat interdit (zone UE) »), jamais le brut avec deux-points.
"""
from __future__ import annotations

import pytest

from labuse.exports.blocs.comparatif import _cause_court
from labuse.pige.estimer3 import _zone_code


@pytest.mark.parametrize("libelle", [
    "Pas de PLU local — zone non résolvable",   # commune au RNU
    "Pas de PLU local",
    "Zone non constructible",                    # tête « Zone » (mot, pas code)
    "Sans objet",
])
def test_zone_code_rejette_les_mots_non_codes(libelle):
    assert _zone_code(libelle) is None


@pytest.mark.parametrize("libelle,attendu", [
    ("Zone non constructible (A)", "A"),
    ("N - Naturelle", "N"),
    ("Ud", "Ud"),
    ("1AU — à urbaniser", "1AU"),
])
def test_zone_code_extrait_les_vrais_codes(libelle, attendu):
    assert _zone_code(libelle) == attendu


def test_cause_court_ecrit_la_cause_en_clair():
    # « code:ZONE » → libellé + zone entre parenthèses (plus jamais « habitat interdit:UE »).
    assert _cause_court("habitat_interdit:UE") == "habitat interdit (zone UE)"
    assert ":" not in (_cause_court("habitat_interdit:UE") or "")
    # sans suffixe de zone, le libellé court habituel est conservé.
    assert _cause_court("terrain_exigu") == "terrain exigu"
    assert _cause_court("zone_non_constructible_a") == "zone non constructible"
    assert _cause_court(None) is None
