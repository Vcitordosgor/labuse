"""CONTENANCE-1 (garde-fou SYMÉTRIQUE) — contenance qui s'écarte d'un facteur > 2 du dessin, dans
un sens OU l'autre (contenance < dessin/2, ou contenance > 2×dessin) ⇒ « Analyse incomplète ».

Quand le plan et le cadastre se contredisent trop (dessin > 2×contenance, OU contenance > 2×dessin
— p.ex. erreur d'unité ×10 000 comme BP2028), la parcelle n'est
calculée NI sur la contenance NI sur le dessin : faisabilité « Analyse incomplète », cause
`surface_incertaine` (IGNORANCE → bande NC au scoring), SDP ∅, aucune capacité. Les deux chiffres
restent affichés par la fiche (payload). Les autres parcelles restent sur la contenance.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse import surface as S
from labuse.faisabilite import engine as E
from labuse.faisabilite.db import ParcelContext
from labuse.scoring.score_labuse import ScoreEntrees, _cause_nc, charger_bareme, score_parcelle


# ───────────────────────── pur : prédicat + helpers ─────────────────────────

@pytest.mark.parametrize("dessin,cont,attendu", [
    (117505, 1, True),       # DV0285 — port de Saint-Pierre (borne basse)
    (966633, 9657, True),    # BH0010 (borne basse)
    (2138, 2142, False),     # écart minime (contenance ≈ dessin)
    (664, 694, False),       # contenance > dessin mais facteur ≈ 1,05 → sous la borne haute
    (4000, 2000, False),     # pile la moitié → PAS strictement inférieur
    (4000, 1999, True),      # juste sous la moitié (borne basse)
    (100, None, False),      # pas de contenance → repli dessin, jamais incertain
    # ── borne HAUTE symétrique (contenance > 2×dessin) ──
    (813, 8130000, True),    # BP2028 — contenance ×10 000 (erreur d'unité) → incertaine
    (1000, 2000, False),     # pile le double → PAS strictement supérieur
    (1000, 2001, True),      # juste au-dessus du double
])
def test_predicat_surface_incertaine(dessin, cont, attendu):
    assert S.surface_incertaine(dessin, cont) is attendu


def test_faisabilite_surface_incertaine_est_analyse_incomplete():
    fa = E.faisabilite_surface_incertaine("U2")
    assert fa.cause == "surface_incertaine"
    assert fa.constructible is False
    # SDP ∅ : la fourchette ne porte PAS de surface_plancher_m2 (jamais un 0).
    assert "surface_plancher_m2" not in fa.fourchette
    assert "surface incertaine" in fa.verdict
    # cause d'IGNORANCE (pas certaine) → le scoring en fera une bande NC.
    assert E.cause_certaine("surface_incertaine") is False
    assert E.cause_libelle("surface_incertaine").startswith("Analyse incomplète — surface incertaine")


def test_ctx_surface_incertaine_property():
    inc = ParcelContext(1, "x", "Saint-Pierre", 1.0, "U", None, surface_dessin_m2=117505.0)
    assert inc.surface_incertaine is True
    # borne HAUTE : BP2028 — surface_m2 = contenance (8 130 000) ≫ 2×dessin (813)
    haut = ParcelContext(1, "97422000BP2028", "Le Tampon", 8130000.0, "U", None,
                         surface_dessin_m2=813.0)
    assert haut.surface_incertaine is True
    ok = ParcelContext(1, "x", "Saint-Paul", 2142.0, "U", None, surface_dessin_m2=2138.0)
    assert ok.surface_incertaine is False
    sans_cont = ParcelContext(1, "x", "Y", 500.0, "U", None, surface_dessin_m2=500.0)
    assert sans_cont.surface_incertaine is False


def _entree(cause, sdp):
    return ScoreEntrees(parcel_id=1, idu="97416000DV0285", commune="Saint-Pierre",
                        residuel_present=True, sdp_residuelle_m2=sdp, taux_emprise_pct=0.0,
                        cause=cause, capacite_estimee=False, pente_moy_deg=2.0, aire_m2=117505.0,
                        perimetre_m=1400.0, faitage_m=None, au_classe=None, acces="POSITIVE")


def test_scoring_surface_incertaine_est_NC():
    # SDP concrète 0 MAIS cause d'ignorance → NC (jamais bande « 0 »).
    assert _cause_nc(_entree("surface_incertaine", 0.0)) is not None
    # SDP ∅ (None) → NC aussi.
    assert _cause_nc(_entree("surface_incertaine", None)) is not None
    # témoin : parcelle calculée (pas de cause, SDP réelle) n'est PAS NC.
    assert _cause_nc(_entree(None, 1200.0)) is None
    bareme, version = charger_bareme()
    sl = score_parcelle(_entree("surface_incertaine", 0.0), bareme, version, "test")
    assert sl.bande == "NC" and sl.non_calculable is True


# ───────────────────────── base APP : parcelles réelles ─────────────────────────

INCERTAINES = ["97416000DV0285", "97419000BH0010", "97415000AO0009"]


def _app_session() -> Session | None:
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        return None
    try:
        s = Session(create_engine(url))
        s.execute(text("SELECT 1"))
        return s
    except Exception:  # noqa: BLE001
        return None


@pytest.mark.parametrize("idu", INCERTAINES)
def test_app_parcelles_incertaines_sans_capacite(idu: str):
    db = _app_session()
    if db is None:
        pytest.skip("base APP injoignable — garde rejouée en recette")
    try:
        from labuse.faisabilite.db import parcel_faisabilite
        row = db.execute(text("SELECT id, round(surface_m2) d, contenance_m2 c FROM parcels WHERE idu=:i"),
                         {"i": idu}).mappings().first()
        if not row or row["c"] is None:
            pytest.skip(f"{idu} absent / sans contenance")
        assert row["c"] < row["d"] / 2.0, (idu, row["d"], row["c"])   # bien dans le périmètre du garde-fou
        ctx, fa = parcel_faisabilite(db, row["id"])
        assert ctx.surface_incertaine is True
        assert fa.cause == "surface_incertaine" and fa.constructible is False
        assert (fa.fourchette or {}).get("surface_plancher_m2") is None
    finally:
        db.close()


def test_app_parcelle_normale_reste_sur_contenance():
    db = _app_session()
    if db is None:
        pytest.skip("base APP injoignable")
    try:
        from labuse.faisabilite.db import parcel_faisabilite
        row = db.execute(text("SELECT id, contenance_m2 c FROM parcels WHERE idu='97404000AX0047'"),
                         ).mappings().first()
        if not row or row["c"] is None:
            pytest.skip("AX0047 absent")
        ctx, fa = parcel_faisabilite(db, row["id"])
        assert ctx.surface_incertaine is False
        assert round(ctx.surface_m2) == round(row["c"])        # calculée sur la contenance
        assert fa.cause != "surface_incertaine"
    finally:
        db.close()
