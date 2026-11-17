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


# ─────────────── LOT 2 — zone rouge : la perte du chiffre se fonde sur l'effet mesuré ───────────────
@pytest.mark.reel
def test_lot2_rouge_sur_assiette(app_session):
    """La surface rouge du terrain entier déclenche le contrôle mais ne le tranche pas : le chiffre
    n'est retiré que si le rouge recoupe l'ASSIETTE du scénario. AT2046 (3,40 m² de rouge sur la
    parcelle, 0 m² sur l'assiette testée) garde son chiffre, avec la mention de la zone rouge. AD0423
    (rouge recoupant l'assiette, part hors rouge sous le seuil) reste « à vérifier ». DR0615 (rouge
    couvrant l'assiette) reste un refus."""
    _ctx, f = _res(app_session, "97408000AT2046")
    assert f.constructible is True and (f.fourchette or {}).get("surface_plancher_m2") is not None, \
        "AT2046 : chiffre retiré alors que le rouge ne recoupe pas l'assiette testée"
    assert any("hors de l'assiette" in a.lower() for a in (_ctx.contraintes.libelles or [])), \
        "AT2046 : mention « zone rouge hors de l'assiette » absente"
    _ctx, f = _res(app_session, "97418000AD0423")
    assert f.constructible is True and (f.fourchette or {}).get("surface_plancher_m2") is None, \
        "AD0423 : rouge recoupant l'assiette → doit rester « à vérifier »"
    _ctx, f = _res(app_session, "97415000DR0615")
    assert f.constructible is False and f.cause == "terrain_exigu", "DR0615 : rouge couvrant → refus"


@pytest.mark.reel
def test_lot2_panne_mesure_rouge_ni_chiffre_ni_refus(app_session, monkeypatch):
    """Une panne de la mesure de la zone rouge sur l'assiette ne doit rendre NI un chiffre NI un
    refus : capacité inconnue → « capacité à vérifier »."""
    from sqlalchemy import text as _t
    import labuse.faisabilite.db as _db
    # FIX-10 — la mesure rouge gabarit passe par `_ROUGE_SUR_GEOM` ; on patche les deux mesures.
    monkeypatch.setattr(_db, "_ROUGE_SUR_GEOM", _t("SELECT 1/0 AS rouge_assiette_m2"))
    monkeypatch.setattr(_db, "_ROUGE_SUR_ASSIETTE", _t("SELECT 1/0 AS rouge_assiette_m2"))
    _ctx, f = _res(app_session, "97408000AT2046")
    assert f.constructible is True, "panne rouge : ne doit pas refuser"
    assert (f.fourchette or {}).get("surface_plancher_m2") is None, "panne rouge : ne doit pas chiffrer"
    assert "indisponible" in (f.verdict or "").lower()


# ─────────────── LOT 3 — tracer le calcul qui a réellement servi ───────────────
@pytest.mark.reel
def test_lot3_recul_non_arrondi_et_chemin_servant(app_session):
    """Le détail par côté n'arrondit pas (AS1086 : 8,25 m, pas 8,2) ; et la trace décrit le chemin
    qui SERT le chiffre : BL0314 est servie par le repli uniforme à 3 m — on n'affiche PAS le fond à
    8 m du gabarit. AO0308 (gabarit) : 6 m retenu, côté par côté."""
    _ctx, f = _res(app_session, "97418000AS1086")
    assert "8.25" in (_ctx.recul_par_cote or ""), f"AS1086 : recul arrondi — {_ctx.recul_par_cote}"
    assert abs((_ctx.recul_servi_m or 0) - 8.25) < 0.01
    _ctx, f = _res(app_session, "97408000AO0308")
    assert "latérale 6 m" in (_ctx.recul_par_cote or "")
    # BL0314 : chiffre du repli uniforme (3 m) — pas le détail par côté du gabarit
    _ctx, f = _res(app_session, "97408000BL0314")
    assert _ctx.assiette_source != "gabarit", "BL0314 : servie par le repli, pas le gabarit"
    assert _ctx.recul_par_cote is None, f"BL0314 : détail gabarit affiché à tort — {_ctx.recul_par_cote}"
    assert abs((_ctx.recul_servi_m or 0) - 3.0) < 0.5, f"BL0314 : recul servi {_ctx.recul_servi_m} ≠ 3 m (repli)"


# ─────── FIX-10 — rouge mesuré sur la GÉOMÉTRIE EXACTE du scénario retenu (gabarit per-côté) ───────
@pytest.mark.reel
def test_fix10_rouge_sur_assiette_exacte_du_scenario(app_session):
    """Sur le chemin gabarit, le rouge se mesure sur la zone d'implantation RÉELLE (per-côté), pas
    sur un inset uniforme qui diffère. AB0752 / AB0823 (Bras-Panon) servaient 21 / 12 m² après une
    mesure de 0 m² à l'inset uniforme 5,50 m, alors que le rouge recoupe leur assiette réelle
    (21,04 / 17,63 m²) : ils repassent « à vérifier ». AT2046, AM0577, AW1235, EW0458 gardent leur
    chiffre (rouge sous le seuil sur leur assiette réelle)."""
    for idu in ("97402000AB0752", "97402000AB0823"):
        _ctx, f = _res(app_session, idu)
        assert f.constructible is True and (f.fourchette or {}).get("surface_plancher_m2") is None, \
            f"{idu} : le rouge recoupe l'assiette réelle → « à vérifier » attendu, obtenu {f.verdict!r}"
    for idu in ("97408000AT2046", "97406000AM0577", "97415000AW1235", "97416000EW0458"):
        _ctx, f = _res(app_session, idu)
        assert f.constructible is True and (f.fourchette or {}).get("surface_plancher_m2") is not None, \
            f"{idu} : chiffre perdu alors que le rouge reste sous le seuil sur l'assiette réelle"
