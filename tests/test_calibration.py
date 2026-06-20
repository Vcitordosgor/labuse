"""Calibration web du bilan — le socle sourcé lève le bandeau « non fiable » DUR ; les valeurs
ESTIMÉES restent signalées « à affiner ». Le socle respecte les overrides de Vic (idempotent).
"""
from __future__ import annotations

import pytest

from labuse.faisabilite import bilan_calibration as cal
from labuse.faisabilite import bilan_params as bp

pytestmark = pytest.mark.db


def test_socle_calibre_les_critiques_et_signale_les_estimes(db_session):
    r = bp.resolve(db_session, None)              # global '*' — socle injecté au boot (ensure_bilan_params)
    # Le coût de construction (critique) a une valeur → plus de bandeau « non fiable » DUR.
    assert r["cout_construction_m2_sdp"]["is_placeholder"] is False
    assert bp.uncalibrated_critical(r) == []
    # Prix neuf = SOURCÉ ; coût construction + marge = ESTIMÉS → sous-bandeau « à affiner ».
    assert r["prix_m2_neuf"]["provenance"] == "sourcee" and r["prix_m2_neuf"]["value"] == 4900.0
    aff = " ".join(bp.estimated_to_refine(r))
    assert "Coût de construction" in aff and "Marge cible promoteur" in aff


def test_prix_neuf_ventile_par_secteur(db_session):
    """Recette ventilation : chaque bassin utilise SON prix sourcé ; non couvert → socle commun."""
    sg = bp.resolve(db_session, "Saint-Gilles")["prix_m2_neuf"]
    assert sg["value"] == 5800.0 and sg["source"] == "secteur" and sg["provenance"] == "sourcee"
    gui = bp.resolve(db_session, "Le Guillaume")["prix_m2_neuf"]
    assert gui["value"] == 3900.0 and gui["provenance"] == "estimee"   # Hauts — fragile, signalé
    unc = bp.resolve(db_session, "Secteur Inexistant")["prix_m2_neuf"]
    assert unc["value"] == 4900.0 and unc["source"] == "global"        # fallback socle commun


def test_socle_respecte_les_overrides_de_vic(db_session):
    """Un override saisi par Vic survit à une ré-injection du socle (ON CONFLICT DO NOTHING)."""
    bp.save(db_session, "*", "cout_construction_m2_sdp", 2400.0)   # Vic calibre
    cal.seed(db_session)                                           # ré-injection du socle
    r = bp.resolve(db_session, None)
    assert r["cout_construction_m2_sdp"]["value"] == 2400.0        # l'override prime, jamais écrasé
