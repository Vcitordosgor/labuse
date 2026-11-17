"""MOTEUR-VERITE-FIX-9 — le relecteur confirme le décompte FIX-8, reste sa liste fermée de trois points.

LOT 1 — littoral : découper l'assiette NETTE (après toutes les contraintes), plus de prorata ;
        panne de mesure → « capacité à vérifier » (ni chiffre ni refus).
LOT 2 — zone rouge : le chiffre n'est retiré que si le rouge recoupe l'assiette du scénario (ou sa
        desserte) ; la surface rouge du terrain entier déclenche mais ne tranche pas.
LOT 3 — tracer le calcul qui a réellement servi (recul non arrondi, chemin servant, rejeu sans
        chiffre vs absent, refus levés vs déjà incertains).

Base applicative réelle (marqueur `reel`) pour les cas parcelle.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.coherence]


def _res(app_session, idu: str):
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"{idu} absente de la base réelle")
    r = parcel_faisabilite(app_session, pid)
    assert r is not None
    _ctx, f = r
    return _ctx, f


# ─────────────── LOT 1 — littoral : découper l'assiette NETTE ───────────────
@pytest.mark.reel
def test_lot1_littoral_decoupe_assiette_nette(app_session):
    """La bande découpe l'assiette NETTE (après ER/EBC/PPR rouge/PEB/DPF/ravine/50 pas), pas en
    prorata de l'assiette brute. AO0648 (Saint-Benoît, ravine dans la bande) sortait à 4 475 m² en
    prorata ; la découpe réelle de l'assiette nette donne 5 857 m² (la contrainte est DANS la bande,
    le net est donc plus hors bande). C'est le cas « bande ∩ autre contrainte »."""
    _ctx, f = _res(app_session, "97410000AO0648")
    sdp = (f.fourchette or {}).get("surface_plancher_m2")
    assert sdp is not None and abs(sdp - 5857) <= 3, f"AO0648 : {sdp} m² ≠ 5 857 (découpe nette)"
    # BL0045 n'est PAS préservée intégralement : son assiette nette hors bande ≈ 642 m² (sur ~1 750).
    _ctx2, _f2 = _res(app_session, "97408000BL0045")
    _lib = " ".join(_ctx2.contraintes.libelles or [])
    assert "hors bande" in _lib.lower() and "642" in _lib, \
        f"BL0045 : assiette nette hors bande (~642 m²) non tracée — {_lib[:160]}"


@pytest.mark.reel
def test_lot1_panne_mesure_littorale_ni_chiffre_ni_refus(app_session, monkeypatch):
    """Une panne de la mesure littorale ne doit rendre NI un chiffre NI un refus : capacité inconnue
    → « capacité à vérifier ». Aujourd'hui la panne ressert l'assiette entière (BL0308 : 716 m²)."""
    from sqlalchemy import text as _t
    import labuse.faisabilite.db as _db
    _panne = _t("SELECT 1/0 AS assiette_m2, 1/0 AS hors_bande_m2")
    monkeypatch.setattr(_db, "_LITTORAL_SUR_INSET", _panne)
    monkeypatch.setattr(_db, "_LITTORAL_SUR_GJ", _panne)
    _ctx, f = _res(app_session, "97408000BL0040")   # parcelle littorale normalement chiffrée
    assert f.constructible is True, "panne littorale : ne doit pas refuser"
    assert (f.fourchette or {}).get("surface_plancher_m2") is None, "panne littorale : ne doit pas chiffrer"
    assert "indisponible" in (f.verdict or "").lower()
