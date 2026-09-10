"""RECETTE-10 T11 — la phrase « ce que le score apporte » : chiffrée, datée, et SEULEMENT quand le
modèle bat nettement le filtre (jamais un score nu vanté sans preuve)."""
from __future__ import annotations

from labuse.scoring.backtest import phrase_client


def _bt(lift_a_suivre, base=0.4, filtre_lift=0.3):
    return {
        "fenetre_fin": "2026-08-10", "base_pct": base,
        "paliers": [{"tier": "chaude", "label": "À suivre", "n": 1367, "mutees": 70,
                     "taux_pct": round(base * lift_a_suivre, 3), "lift": lift_a_suivre}],
        "filtres": {"terrain_nu_zone_u": {"libelle": "Terrain nu constructible en zone U",
                                          "n": 25281, "mutees": 27, "taux_pct": 0.107, "lift": filtre_lift}},
    }


def test_phrase_quand_le_modele_bat_le_filtre():
    p = phrase_client(_bt(13.26))
    assert p is not None
    assert "12 mois" in p and "2026-08-10" in p        # chiffrée ET datée
    assert "13.26" in p or "13,26" in p or "13" in p
    assert "À suivre" in p
    assert "filtre simple" in p                         # la comparaison au filtre est dite


def test_pas_de_phrase_si_le_modele_ne_bat_pas():
    # lift < 2 → pas de fausse promesse : on n'affiche rien plutôt qu'un score nu vanté
    assert phrase_client(_bt(1.4)) is None
    assert phrase_client({"paliers": [], "filtres": {}}) is None
