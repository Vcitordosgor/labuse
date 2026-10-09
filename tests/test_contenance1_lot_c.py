"""CONTENANCE-1 (Lot C/D) — les ratios lisent la contenance ; la règle C3 borne les aires.

D1 : (a) le facteur de ré-échelle C3 `terrain_sur_dessin` ; (b) propriété : toute aire ≤ dessin,
ramenée à l'échelle contenance, ne dépasse JAMAIS la contenance ; (c) sur la base APP, la surface
servie à la faisabilité = contenance (C1) et aucune aire d'emprise/zone d'implantation ne dépasse
la contenance (C3). Monotonicité : les 30 témoins du scoring restent inchangés tant qu'aucun run
n'a tourné (données servies intactes) — couvert par test_scoring6_* (golden), cité au rapport.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.db import ParcelContext


# ───────────────────────── pur : facteur + propriété C3 ─────────────────────────

def _ctx(surface_terrain, dessin) -> ParcelContext:
    return ParcelContext(1, "x", "Saint-Paul", float(surface_terrain), None, None,
                         surface_dessin_m2=float(dessin))


def test_facteur_terrain_sur_dessin():
    # contenance < dessin (CW0658) → facteur < 1
    assert _ctx(25633, 27156).terrain_sur_dessin == pytest.approx(25633 / 27156)
    # contenance > dessin (AS0772) → facteur > 1
    assert _ctx(694, 664).terrain_sur_dessin == pytest.approx(694 / 664)
    # repli : pas de dessin → 1.0 (aucune ré-échelle)
    assert _ctx(1000, 0).terrain_sur_dessin == 1.0


@pytest.mark.parametrize("dessin,cont", [(27156, 25633), (664, 694), (1000, 1000)])
@pytest.mark.parametrize("part", [0.0, 0.25, 0.5, 0.9, 1.0])
def test_c3_aucune_aire_du_dessin_ne_depasse_la_contenance(dessin, cont, part):
    """Toute aire géométrique ≤ dessin (ex. zone d'implantation, part `part` du dessin), ramenée à
    l'échelle contenance, reste ≤ contenance — le cœur de la règle C3 (« rien ne dépasse »)."""
    k = _ctx(cont, dessin).terrain_sur_dessin
    aire_dessin = part * dessin            # une aire quelconque tirée du dessin (≤ dessin)
    aire_rescaled = aire_dessin * k
    assert aire_rescaled <= cont + 1e-6


# ───────────────────────── base APP : C1 + C3 sur parcelles réelles ─────────────────────────

CIBLES = ["97415000CW0658", "97404000AX0047", "97411000CP0427", "97406000AM0664"]


def _app_session() -> Session | None:
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        return None
    try:
        s = Session(create_engine(url))
        s.execute(text("SELECT 1"))
        return s
    except Exception:  # noqa: BLE001 — base APP absente (CI) → skip
        return None


@pytest.mark.parametrize("idu", CIBLES)
def test_c1_surface_servie_est_la_contenance_et_c3_borne_les_aires(idu: str):
    db = _app_session()
    if db is None:
        pytest.skip("base APP injoignable (CI sur labuse_test) — garde rejouée en recette")
    try:
        from labuse.faisabilite.db import parcel_faisabilite
        row = db.execute(text(
            "SELECT id, contenance_m2 FROM parcels WHERE idu=:i"), {"i": idu}).mappings().first()
        if not row or row["contenance_m2"] is None:
            pytest.skip(f"{idu} absent / sans contenance sur cette base")
        cont = float(row["contenance_m2"])
        res = parcel_faisabilite(db, row["id"])
        if res is None:
            pytest.skip(f"{idu} : pas de faisabilité (zone non constructible / non calibrée)")
        ctx, fa = res
        # C1 : la surface servant aux ratios = la contenance (au m² près).
        assert round(ctx.surface_m2) == round(cont), (idu, ctx.surface_m2, cont)
        # C3 : aucune aire d'emprise / zone d'implantation affichée ne dépasse la contenance.
        f = fa.fourchette or {}
        for cle in ("zone_implantation_m2", "emprise_constructible_m2", "emprise_sol_max_m2"):
            v = f.get(cle)
            if v is not None:
                assert v <= cont + 1.0, (idu, cle, v, cont)
    finally:
        db.close()
