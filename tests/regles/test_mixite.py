"""Témoin CIRCUIT-4 — clause de mixité : seuils LUS du règlement calibré (jamais des constantes
nationales), déclenchement (logique OU du texte) vérifié indépendamment."""
from __future__ import annotations

from labuse.faisabilite.bilan import _clause_mixite
from labuse.faisabilite.engine import Hypotheses


def test_seuils_du_reglement():
    hyp = Hypotheses.charger("Saint-Paul")
    s_sdp = float(hyp.mixite_sdp_seuil_m2)
    assert s_sdp == 1500.0                 # « SDP ≥ 1 500 m² » (YAML calibré Saint-Paul)
    petit = {"sdp_max_m2": 100.0, "logements_estimes": 1.0, "terrain_m2": 100.0}
    au_seuil = {"sdp_max_m2": s_sdp, "logements_estimes": 1.0, "terrain_m2": 100.0}
    # recalcul indépendant de la logique OU : SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil
    assert _clause_mixite(au_seuil, hyp)["declenchee"] is (s_sdp >= s_sdp)          # ≥ au seuil
    attendu_petit = (100.0 >= s_sdp or 1.0 >= float(hyp.mixite_logements_seuil)
                     or 100.0 > float(hyp.mixite_terrain_seuil_m2))
    assert _clause_mixite(petit, hyp)["declenchee"] is attendu_petit
