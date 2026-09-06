"""Témoin CIRCUIT-4 — surélévation : marge = hé − hauteur bâtie (égout prioritaire), recomparée
indépendamment ; hauteur du bâti = max des bâtiments intersectants (seedé)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


class _Rules:
    def __init__(self, he=None, hf=None):
        self.he_m, self.hf_m = he, hf


class _Ctx:
    zone, commune = "Utest", "Saint-Paul"


@pytest.mark.db
def test_hauteur_max_batiments(engine):
    from labuse.faisabilite.potentiel import _hauteur_bati_m
    from labuse.db import session_scope
    with engine.begin() as c:
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'batiment'"
                       " AND name LIKE 'c4-bat%'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinSur-C4'"))
        c.execute(text(
            "INSERT INTO parcels (idu, commune, surface_m2, geom, geom_2975) VALUES "
            "('C4SUR0000000', 'TemoinSur-C4', 100, ST_GeomFromText('POINT(55.5 -21.1)', 4326),"
            " ST_GeomFromText('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))', 2975))"))
        pid = c.execute(text("SELECT id FROM parcels WHERE idu = 'C4SUR0000000'")).scalar()
        for nom, h in (("c4-bat1", 4.5), ("c4-bat2", 7.0)):
            c.execute(text(
                "INSERT INTO spatial_layers (kind, name, attrs, geom, geom_2975) VALUES "
                "('batiment', :n, :a, ST_GeomFromText('POINT(55.5 -21.1)', 4326),"
                " ST_GeomFromText('POLYGON((1 1, 3 1, 3 3, 1 3, 1 1))', 2975))"),
                {"n": nom, "a": f'{{"hauteur": "{h}"}}'})
    with session_scope() as s:
        h = _hauteur_bati_m(s, pid)
    with engine.begin() as c:   # nettoyage : aucun legs (bâtiments fantômes)
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'batiment' AND name LIKE 'c4-bat%'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinSur-C4'"))
    assert h == 7.0                             # max(4,5 ; 7,0) — recompté à la main


@pytest.mark.db
def test_marge_egout_prioritaire(engine, monkeypatch):
    from labuse.faisabilite import potentiel
    from labuse.db import session_scope
    monkeypatch.setattr(potentiel, "_hauteur_bati_m", lambda s, p: 6.0)
    with session_scope() as s:
        # hé ET hf présents → l'ÉGOUT prime : marge = 12 − 6 = 6 m (recalcul indépendant)
        out = potentiel.surelevation(s, 1, rules=_Rules(he=12.0, hf=16.0), ctx=_Ctx())
        assert out["base"] == "égout" and out["marge_m"] == 12.0 - 6.0
        assert out["possible"] is (out["marge_m"] >= 2.8)
        # hé absent → repli faîtage AVEC avertissement
        out2 = potentiel.surelevation(s, 1, rules=_Rules(he=None, hf=9.0), ctx=_Ctx())
        assert out2["base"].startswith("faîtage") and out2["avertissement"]
        # aucune hauteur → possible=None (jamais un faux « non »)
        out3 = potentiel.surelevation(s, 1, rules=_Rules(), ctx=_Ctx())
        assert out3["possible"] is None
