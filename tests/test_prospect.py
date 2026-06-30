"""Hauteur prospect (Ud/Uu) — largeur de façade + plancher 10 m. Mock session, ZÉRO base/réseau."""
from __future__ import annotations

from labuse.faisabilite.db import _facade_largeur, _prospect_hauteur


class _FakeSession:
    """Session minimale : .execute(...).all() renvoie les lignes (largeur, nature) fournies."""
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *a, **k):
        rows = self._rows

        class _R:
            def all(self):
                return rows
        return _R()


def _largeur(rows):
    return _facade_largeur(_FakeSession(rows), 1, "Saint-Denis")


# ── _prospect_hauteur : plancher 10 m ─────────────────────────────────────────
def test_prospect_hauteur_plancher():
    assert _prospect_hauteur(4.0) == 10.0      # chaussée étroite → plancher
    assert _prospect_hauteur(14.0) == 14.0     # avenue large → largeur réelle
    assert _prospect_hauteur(None) == 10.0     # aucune voie → plancher
    assert _prospect_hauteur(0.0) == 10.0      # largeur dégénérée → plancher


# ── _facade_largeur : réel / classe / dégénéré / aucune / multi-façades ───────
def test_facade_largeur_reel():
    assert _largeur([(5.5, "Route à 1 chaussée")]) == (5.5, "reel")


def test_facade_largeur_fallback_classe():
    # largeur NULL → défaut par nature
    assert _largeur([(None, "Chemin")]) == (4.0, "classe")
    assert _largeur([(None, "Route à 2 chaussées")]) == (14.0, "classe")


def test_facade_largeur_zero_degenere_va_en_fallback():
    # largeur 0 = dégénérée → PAS 'reel', on retombe sur la classe.
    assert _largeur([(0.0, "Route à 1 chaussée")]) == (6.0, "classe")


def test_facade_largeur_aucune():
    assert _largeur([]) == (None, "aucune")                     # aucune voie ≤ 25 m
    assert _largeur([(None, "Sentier")]) == (None, "aucune")    # sentier = pas une desserte


def test_facade_largeur_multi_facades_prend_la_plus_large():
    rows = [(4.0, "Route à 1 chaussée"), (12.0, "Route à 2 chaussées")]
    assert _largeur(rows) == (12.0, "reel")                     # la plus large
    # mix réel/classe : on compare les largeurs effectives
    rows2 = [(None, "Chemin"), (None, "Route à 2 chaussées")]
    assert _largeur(rows2) == (14.0, "classe")
