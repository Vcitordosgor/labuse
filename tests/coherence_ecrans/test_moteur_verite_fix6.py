"""MOTEUR-VERITE-FIX-6 — l'ordre des verdicts : un refus établi ne s'efface jamais.

Les refus réglementaires (habitat interdit, zone fermée, parcelle refusée par main faute
d'assiette utilisable) passent AVANT les gardes de taille / « capacité à vérifier ».
Base applicative réelle requise (marqueur `reel`).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.coherence, pytest.mark.reel]


def _res(app_session, idu: str):
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"{idu} absente de la base réelle")
    r = parcel_faisabilite(app_session, pid)
    assert r is not None
    _ctx, f = r
    return f


# LOT 1 — refus réglementaires/établis : la parcelle NE DOIT PAS ressortir « constructible ».
#   (idu, cause attendue approximative)
REFUS = [
    ("97418000AC1634", "habitat_interdit"),   # Sainte-Marie UEm, 20 m² : habitat interdit AVANT micro-garde
    ("97413000CG0875", "terrain_exigu"),      # Saint-Leu, 92 m², 0 m² net : refus établi, pas « à vérifier »
]


@pytest.mark.parametrize("idu,cause", REFUS)
def test_lot1_refus_etabli_preserve(app_session, idu, cause):
    f = _res(app_session, idu)
    assert f.constructible is False, f"{idu} : refus établi devenu constructible"
    assert (f.cause or "").startswith(cause.split(":")[0]), f"{idu} : cause {f.cause}, attendu {cause}"
