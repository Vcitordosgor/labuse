"""Témoin CIRCUIT-4 — clause de mixité : seuils LUS du règlement calibré (jamais des constantes
nationales), déclenchement (logique OU du texte) vérifié indépendamment."""
from __future__ import annotations

from labuse.faisabilite.bilan import _clause_mixite
from labuse.faisabilite.engine import Hypotheses


def test_seuils_du_reglement():
    """OUTIL-ASSEMBLAGE-FIX-1 (LOT 3) — Saint-Paul : RÉGIME À BANDES, déclenchement sur le PROGRAMME
    chiffré (`sdp_programme_m2`), pas le gabarit. Seuils lus du YAML calibré."""
    hyp = Hypotheses.charger("Saint-Paul")
    assert float(hyp.mixite_sdp_seuil_m2) == 1500.0          # « SDP ≥ 1 500 m² » (bande basse)
    assert float(hyp.mixite_sdp_seuil_haut_m2) == 1800.0     # seuil HAUT du plein régime
    # Le gabarit élevé et le compte de logements du silo ne déclenchent PLUS à eux seuls : c'est le
    # programme chiffré qui pilote (le critère terrain > 6 000 m² reste un déclencheur réglementaire).
    gab = {"sdp_max_m2": 5000.0, "logements_estimes": 30.0, "terrain_m2": 3000.0}
    assert _clause_mixite({**gab, "sdp_programme_m2": 2000.0}, hyp)["regime"] == "plein"
    assert _clause_mixite({**gab, "sdp_programme_m2": 1582.0}, hyp)["regime"] == "intermediaire"
    assert _clause_mixite({**gab, "sdp_programme_m2": 1200.0}, hyp)["declenchee"] is False
    assert _clause_mixite({**gab, "sdp_programme_m2": 100.0, "terrain_m2": 7000.0}, hyp)["regime"] == "plein"


def test_seuils_du_reglement_commune_sans_bande_ou():
    """Une commune SANS seuil haut (ex. Saint-Denis) garde la logique OU HISTORIQUE sur le gabarit —
    la correction du régime à bandes est bornée à Saint-Paul (décision 24/11)."""
    hyp = Hypotheses.charger("Saint-Denis")
    assert float(getattr(hyp, "mixite_sdp_seuil_haut_m2", 0.0)) == 0.0
    s_sdp = float(hyp.mixite_sdp_seuil_m2)
    au_seuil = {"sdp_max_m2": s_sdp, "logements_estimes": 1.0, "terrain_m2": 100.0}
    petit = {"sdp_max_m2": 100.0, "logements_estimes": 1.0, "terrain_m2": 100.0}
    assert _clause_mixite(au_seuil, hyp)["declenchee"] is True        # gabarit ≥ seuil → déclenchée
    attendu_petit = (100.0 >= s_sdp or 1.0 >= float(hyp.mixite_logements_seuil)
                     or 100.0 > float(hyp.mixite_terrain_seuil_m2))
    assert _clause_mixite(petit, hyp)["declenchee"] is attendu_petit
