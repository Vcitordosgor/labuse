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


# LOT 2 — un seul jeu de règles pour le repli : niveau par niveau + test rouge∩PLU.
def test_lot2_repli_niveau_par_niveau(app_session):
    """AD0173 (Sainte-Marie UA, zone autorisée) servie par le REPLI : le retrait relatif se
    calcule niveau par niveau (R+1, 3,75 m) comme le gabarit, plus un retrait uniforme de 9 m
    qui vidait l'assiette à tort (363 → 0 « trop exigu »). Baisse, pas refus ferme."""
    f = _res(app_session, "97418000AD0173")
    sdp = (f.fourchette or {}).get("surface_plancher_m2")
    assert f.constructible is True and sdp is not None, "AD0173 : refus ferme injustifié"
    assert 60 <= sdp <= 363, f"AD0173 : {sdp} m² hors de la fourchette R+1 attendue"


def test_lot2_repli_rouge_et_plu(app_session):
    """Le repli applique le test conjoint zone rouge ∩ PLU : la partie hors rouge doit être
    exploitable (≥ 200 m² ∩ U/AU, accès voie). AW1235/BM0158/BO0383 servaient un chiffre que
    la cascade excluait — ils ferment désormais."""
    for idu in ("97405000AW1235", "97410000BM0158", "97409000BO0383"):
        f = _res(app_session, idu)
        assert f.constructible is False, f"{idu} : repli sert encore un chiffre exclu par la cascade"
