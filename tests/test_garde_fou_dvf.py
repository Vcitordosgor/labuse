"""MANDAT_DVF-B — le garde-fou du 2× : annote (jamais bloque/masque) ; ne se déclenche pas si un terme
manque (écart non mesurable ≠ écart) et le DIT ; formulation qui n'invite pas à l'achat."""
from __future__ import annotations

from labuse.marche_service import garde_fou_signal


def test_declenche_au_dela_du_facteur():
    s = garde_fou_signal(5000, 2000)          # ×2,5 > 2 → information manquante
    assert s["declenche"] is True and s["mesurable"] is True
    low = s["note"].lower()
    assert "à vérifier" in low and "incomplète" in low
    assert "opportunité" not in low or "pas une opportunité" in low   # n'invite pas à l'achat


def test_silencieux_sous_le_facteur():
    s = garde_fou_signal(2400, 2000)          # ×1,2 < 2 → rien
    assert s["declenche"] is False and s["mesurable"] is True and s["note"] is None


def test_non_mesurable_sans_reference_le_dit():
    s = garde_fou_signal(5000, None)
    assert s["declenche"] is False and s["mesurable"] is False
    assert "non mesurable" in s["note"].lower()


def test_non_mesurable_effectif_insuffisant():
    s = garde_fou_signal(5000, 2000, effectif=2, seuil_effectif=8)
    assert s["declenche"] is False and s["mesurable"] is False
    assert "insuffisant" in s["note"].lower()
