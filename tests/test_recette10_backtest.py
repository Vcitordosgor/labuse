"""RECETTE-10 T11 — la phrase « ce que le score apporte » : chiffrée, datée, et SEULEMENT quand le
modèle bat nettement le filtre (jamais un score nu vanté sans preuve)."""
from __future__ import annotations

from labuse.scoring.backtest import phrase_client


def _bt(lift_a_suivre, base=0.4, filtre_realiste_lift=3.17):
    # la comparaison de référence est le filtre RÉALISTE (pas la règle naïve « terrain nu »)
    return {
        "fenetre_fin": "2026-08-10", "base_pct": base,
        "paliers": [{"tier": "chaude", "label": "À suivre", "n": 1367, "mutees": 70,
                     "taux_pct": round(base * lift_a_suivre, 3), "lift": lift_a_suivre}],
        "filtres": {"realiste": {"libelle": "Ciblage manuel réaliste",
                                 "n": 30516, "mutees": 374,
                                 "taux_pct": round(base * filtre_realiste_lift, 3), "lift": filtre_realiste_lift}},
    }


def test_phrase_compare_au_filtre_realiste_pas_au_strawman():
    p = phrase_client(_bt(13.26))
    assert p is not None
    assert "12 mois" in p and "2026-08-10" in p        # chiffrée ET datée
    assert "À suivre" in p
    assert "ciblage manuel réaliste" in p              # comparé au filtre RÉALISTE
    assert "terrain nu" not in p                       # jamais l'homme de paille dans la phrase client


def test_pas_de_phrase_si_le_modele_ne_bat_pas_le_filtre_realiste():
    # le modèle doit battre le filtre RÉALISTE d'au moins 2× — sinon rien (pas de fausse promesse)
    assert phrase_client(_bt(5.0, filtre_realiste_lift=3.17)) is None   # 5/3,17 = 1,6× < 2×
    assert phrase_client(_bt(13.26, filtre_realiste_lift=3.17)) is not None  # 13,3/3,17 = 4,2× ≥ 2×
    assert phrase_client({"paliers": [], "filtres": {}}) is None
