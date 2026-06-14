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


def test_socle_respecte_les_overrides_de_vic(db_session):
    """Un override saisi par Vic survit à une ré-injection du socle (ON CONFLICT DO NOTHING)."""
    bp.save(db_session, "*", "cout_construction_m2_sdp", 2400.0)   # Vic calibre
    cal.seed(db_session)                                           # ré-injection du socle
    r = bp.resolve(db_session, None)
    assert r["cout_construction_m2_sdp"]["value"] == 2400.0        # l'override prime, jamais écrasé
