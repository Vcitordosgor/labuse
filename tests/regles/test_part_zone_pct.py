"""Témoin CIRCUIT-4 — parts de zonage (surface) : recompte indépendant sur lignes seedées."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.fixture
def seed_zonage(engine):
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS parcel_zone_plu"
                       " (idu varchar(14) PRIMARY KEY, zone_lib text, zone_fam text, zone_filtre text)"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'Temoin-C4'"))
        c.execute(text("DELETE FROM parcel_zone_plu WHERE idu LIKE 'C4%'"))
        rows = [("C4U1", "U", 1000.0), ("C4U2", "U", 3000.0), ("C4AU1", "AU", 2000.0),
                ("C4A1", "A", 10000.0), ("C4N1", "N", 4000.0)]
        for idu, fam, m2 in rows:
            c.execute(text(
                "INSERT INTO parcels (idu, commune, surface_m2, geom)"
                " VALUES (:i, 'Temoin-C4', :m, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"),
                {"i": idu, "m": m2})
            c.execute(text(
                "INSERT INTO parcel_zone_plu (idu, zone_fam, zone_filtre) VALUES (:i, :f, :f2)"
                " ON CONFLICT (idu) DO UPDATE SET zone_fam = EXCLUDED.zone_fam"),
                {"i": idu, "f": fam, "f2": fam})
    return rows


@pytest.mark.db
def test_parts_zonage_surface_temoin(engine, seed_zonage):
    from labuse.registre.moteurs.zonage import parts_zonage_surface
    with engine.begin() as c:
        out = parts_zonage_surface(c, "Temoin-C4")
    # recompte indépendant : U = 4000, AU = 2000, A = 10000, N = 4000, total = 20000
    total = 20000.0
    assert out["familles"]["U"]["pct"] == round(100 * 4000 / total, 1) == 20.0
    assert out["familles"]["AU"]["pct"] == 10.0
    assert out["familles"]["A"]["pct"] == 50.0
    assert out["familles"]["N"]["pct"] == 20.0
    somme = sum(out["familles"][f]["pct"] for f in ("U", "AU", "A", "N"))
    assert abs(somme - 100.0) < 0.3            # les parts somment à 100 (arrondi 0,1)


@pytest.mark.db
def test_parcelles_par_zone_temoin(engine, seed_zonage):
    from labuse.registre.moteurs.zonage import parcelles_par_zone
    with engine.begin() as c:
        out = parcelles_par_zone(c, communes=["Temoin-C4"])
    par_fam = {f["fam"]: f["n"] for f in out["familles"]}
    assert par_fam == {"U": 2, "AU": 1, "A": 1, "N": 1}   # recompte à la main
