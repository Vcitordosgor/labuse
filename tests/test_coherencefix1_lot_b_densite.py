"""COHERENCE-FIX-1 (lot B) — densité consommée : plus de « 999 % », plus de zéro-pour-absence.

- le moteur ne plafonne plus (la valeur est la vérité arithmétique) et sert None — jamais 0 —
  quand le dénominateur manque ;
- l'affichage partagé (`fmt_pct_consomme`, miroir front format.ts) : exact ≤ 300, « > 300 »
  au-delà, None si absent.
"""
from __future__ import annotations

from labuse.faisabilite.residuel import SEUIL_PCT_AFFICHAGE, _libelle, fmt_pct_consomme


def test_fmt_exact_sous_le_seuil():
    assert fmt_pct_consomme(0) == "0"
    assert fmt_pct_consomme(83) == "83"
    assert fmt_pct_consomme(299.6) == "300"


def test_fmt_au_dela_du_seuil():
    assert SEUIL_PCT_AFFICHAGE == 300
    assert fmt_pct_consomme(301) == "> 300"
    assert fmt_pct_consomme(999) == "> 300", "le 999 historique ne se lit plus jamais tel quel"
    assert fmt_pct_consomme(15000) == "> 300"


def test_fmt_absence_est_none_jamais_zero():
    assert fmt_pct_consomme(None) is None


def test_libelle_taux_none_dit_l_absence():
    lib = _libelle(None, 120.0, True)
    assert "non calculable" in lib and "0" not in lib.split("·")[0]


def test_libelle_au_dela_de_300_dit_plus_de_300():
    lib = _libelle(1240.0, 0.0, True)
    assert "> 300" in lib and "1240" not in lib


def test_libelle_entre_100_et_300_reste_exact():
    lib = _libelle(140.0, 0.0, True)
    assert "~140" in lib
