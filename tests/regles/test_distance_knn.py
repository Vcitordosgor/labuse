"""Témoin CIRCUIT-4 — distance KNN : recalcul indépendant via pyproj (EPSG:4326 → 2975, distance
euclidienne plane) + le drapeau « sous 800 m » de L151-36 (xfail tant que l'écart E1 tient)."""
from __future__ import annotations

import math

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_distance_euclidienne_temoin(engine):
    from pyproj import Transformer

    from labuse.registre.moteurs.parcelle import plus_proche
    p0 = (55.5000, -21.1000)
    proche = (55.5030, -21.1000)     # ~310 m à l'est
    loin = (55.5500, -21.1000)       # ~5 km
    with engine.begin() as c:
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'c4_arret_temoin'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinKnn-C4'"))
        c.execute(text(
            "INSERT INTO parcels (idu, commune, surface_m2, geom, geom_2975) VALUES "
            "('C4KNN0000000', 'TemoinKnn-C4', 10, ST_GeomFromText(:w, 4326),"
            " ST_Transform(ST_GeomFromText(:w, 4326), 2975))"), {"w": f"POINT({p0[0]} {p0[1]})"})
        for nom, (x, y) in (("Arrêt proche", proche), ("Arrêt loin", loin)):
            c.execute(text(
                "INSERT INTO spatial_layers (kind, name, geom, geom_2975) VALUES "
                "('c4_arret_temoin', :n, ST_GeomFromText(:w, 4326),"
                " ST_Transform(ST_GeomFromText(:w, 4326), 2975))"),
                {"n": nom, "w": f"POINT({x} {y})"})
        out = plus_proche(c, "C4KNN0000000", "c4_arret_temoin")
    # recalcul INDÉPENDANT : projection pyproj vers 2975 puis distance euclidienne plane
    tr = Transformer.from_crs(4326, 2975, always_xy=True)
    ax, ay = tr.transform(*p0)
    bx, by = tr.transform(*proche)
    attendu = round(math.hypot(bx - ax, by - ay))
    assert out["nom"] == "Arrêt proche"
    assert abs(out["distance_m"] - attendu) <= 1        # arrondi SQL ±1 m


@pytest.mark.xfail(reason="ÉCART E1 (REGLES-ECARTS) : le code pose d <= 800 (large) quand "
                          "L151-36 dit « à moins de 800 m » (strict) — corrigé au lot 6",
                   strict=True)
def test_drapeau_800_strict():
    """L151-36 : « situées à moins de huit cents mètres » — d = 800 exactement N'EST PAS
    « à moins de 800 m ». Le drapeau du code doit être strict."""
    import re
    src = open("src/labuse/api/app.py").read()
    m = re.search(r"proche = d (<=?) 800", src)
    assert m and m.group(1) == "<", f"opérateur du drapeau : {m.group(1)!r} (attendu '<')"
