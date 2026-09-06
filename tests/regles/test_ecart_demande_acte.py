"""Témoin CIRCUIT-4 — écart demandé/acté : formule et seuils recalculés indépendamment."""
from __future__ import annotations

from labuse.pige import signaux


def test_ecart_formule_et_seuils():
    # seuils du code = ceux de la fiche (5 / 30 / 8 / −15 / 0,5)
    assert signaux.SEUIL_N == 5
    assert signaux.SEUIL_REF_TYPE == 30
    assert signaux.SEUIL_REF_LOCAL == 8
    assert signaux.SEUIL_SOUS_MARCHE_PCT == -15.0
    assert signaux.SEUIL_PART_FONCIERE == 0.5

    # formule : ecart = 100 × (demandé − acté) ÷ acté — recalcul indépendant
    out = signaux._ecart(5000.0, 10, {"eur_m2": 4000.0, "n": 12, "millesime": "2026"})
    assert out["calculable"] and out["ecart_pct"] == round(100.0 * (5000.0 - 4000.0) / 4000.0, 1)
    # un côté sous le seuil → PAS d'écart servi
    out2 = signaux._ecart(5000.0, 4, {"eur_m2": 4000.0, "n": 12, "millesime": "2026"})
    assert out2["calculable"] is False
