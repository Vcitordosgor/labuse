"""COHERENCE-FIX-1 (lot B) — densité consommée : plus de « 999 % », plus de zéro-pour-absence.

- le moteur ne plafonne plus (la valeur est la vérité arithmétique) et sert None — jamais 0 —
  quand le dénominateur manque ;
- l'affichage partagé (`fmt_pct_consomme`, miroir front format.ts) : exact ≤ 300, « > 300 »
  au-delà, None si absent.
"""
from __future__ import annotations

from labuse.faisabilite.residuel import (
    SEUIL_PCT_AFFICHAGE, TAUX_EMPRISE_SATURE, _libelle, fmt_pct_consomme, fmt_taux_emprise,
)


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


# CHASSE-INVARIANTS-FIX-1 (Lot 1, E-01) — la règle d'affichage du TAUX D'OCCUPATION DU GABARIT a
# changé : au-delà de 100 % on n'affiche plus jamais un % brut (ni même « > 300 ») mais le message
# « Saturé … » unique. `_libelle` (texte de la fiche) suit cette règle ; `fmt_pct_consomme` (SDP
# consommée, une AUTRE notion) garde son « > 300 » et n'est pas touché.
def test_libelle_au_dela_de_100_dit_sature_sans_pourcentage():
    for taux in (140.0, 1240.0, 19569.0):
        lib = _libelle(taux, 0.0, True)
        assert "Saturé" in lib
        assert str(int(taux)) not in lib and "> 300" not in lib and "~" not in lib.split("·")[0]


def test_fmt_taux_emprise_rendu_unique():
    assert fmt_taux_emprise(None) is None
    assert fmt_taux_emprise(45) == "45 %"
    assert fmt_taux_emprise(100) == "100 %"
    assert fmt_taux_emprise(100.4) == "100 %"      # arrondi à 100 → encore un %
    assert fmt_taux_emprise(101) == TAUX_EMPRISE_SATURE
    assert fmt_taux_emprise(19569) == TAUX_EMPRISE_SATURE
    assert "%" not in fmt_taux_emprise(19569)      # jamais un pourcentage brut au-delà de 100
