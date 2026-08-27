"""E1 (parcours d'entrée) — source de vérité UNIQUE des offres + anti-régression.

Deux offres seulement : Intégral 349 €/mois (engagement 12 mois), Flash 79 € paiement unique.
L'ancienne offre fantôme « Illimité 499 € » n'existe plus. Aucun prix d'offre en dur dans le front.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from labuse import comptes, quota
from labuse.offres import offre_flash, offre_integral, offres_publiques

_FRONT = Path(__file__).resolve().parents[1] / "frontend" / "src"


def test_offre_integral_valeurs():
    o = offre_integral()
    assert o["label"] == "Intégral"
    assert o["eur_mois"] == 349
    assert o["engagement_mois"] == 12
    assert o["periodicite"] == "mois"


def test_offre_flash_valeurs():
    o = offre_flash()
    assert o["label"] == "Flash"
    assert o["eur"] == 79
    assert o["periodicite"] == "unique"


def test_offres_publiques_deux_offres_seulement():
    assert set(offres_publiques()) == {"integral", "flash"}


def test_plans_ne_contient_plus_l_offre_fantome():
    """PLANS ne connaît que 'integral' (commercial) et 'interne' (admin/système, sans prix).
    Ni 'illimite', ni 'Illimité', ni 499 nulle part."""
    assert comptes.PLANS["integral"]["eur_mois"] == 349
    assert comptes.PLANS["interne"]["eur_mois"] is None
    with pytest.raises(KeyError):
        comptes.PLANS["illimite"]


def test_message_quota_sans_offre_fantome():
    m = quota.message_depassement("integral", 30)
    assert "Illimité" not in m and "499" not in m
    assert "Intégral" in m and "Flash" in m


def test_source_verite_unique_prix_suit_la_config(monkeypatch):
    """Changer le prix se fait à UN endroit (config) — offres.py le reflète immédiatement."""
    from labuse import config
    monkeypatch.setenv("LABUSE_INTEGRAL_PRIX_EUR_MOIS", "399")
    config.get_settings.cache_clear()
    try:
        assert offre_integral()["eur_mois"] == 399
        assert comptes.PLANS["integral"]["eur_mois"] == 399
    finally:
        monkeypatch.delenv("LABUSE_INTEGRAL_PRIX_EUR_MOIS", raising=False)
        config.get_settings.cache_clear()


# ── ANTI-RÉGRESSION FRONT : aucun montant d'offre écrit en dur dans le JSX ──
# Le front lit /api/offres (getOffres) ; un prix littéral adjacent à « € » est INTERDIT
# (une interpolation `${x} €/mois` n'a pas de chiffre littéral avant €, donc ne matche pas).
_MONTANT_EN_DUR = re.compile(r"(?<![.\w])(349|499|199|249|149|97|79|39|29)\s*€")


def test_aucun_prix_offre_en_dur_dans_le_front():
    coupables = []
    for f in _FRONT.rglob("*.ts*"):
        for i, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if _MONTANT_EN_DUR.search(ligne) or "Illimité" in ligne:
                coupables.append(f"{f.relative_to(_FRONT.parent.parent)}:{i}: {ligne.strip()[:100]}")
    assert not coupables, "Prix d'offre en dur dans le front (doit venir de /api/offres) :\n" + "\n".join(coupables)
