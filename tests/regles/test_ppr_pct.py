"""Témoin CIRCUIT-4 — part des parcelles intersectant une couche : recompte indépendant (shapely)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_part_intersection_temoin(engine):
    from labuse.registre.moteurs.commune import pct_parcelles_couche
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinPPR-C4'"))
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'c4_ppr_temoin'"))
        # 4 parcelles ponctuelles en 4326 : 3 dans le carré [55;56]×[−22;−21], 1 dehors
        # (geom_2975 est dérivée de geom par l'app — on ne la force pas)
        pts = [(55.5, -21.5), (55.2, -21.8), (55.9, -21.1), (57.0, -20.0)]
        for i, (x, y) in enumerate(pts):
            c.execute(text(
                "INSERT INTO parcels (idu, commune, surface_m2, geom, geom_2975) VALUES "
                "(:i, 'TemoinPPR-C4', 100, ST_GeomFromText(:wkt, 4326),"
                " ST_Transform(ST_GeomFromText(:wkt, 4326), 2975))"),
                {"i": f"C4PPR{i}", "wkt": f"POINT({x} {y})"})
        c.execute(text(
            "INSERT INTO spatial_layers (kind, geom, geom_2975) VALUES ('c4_ppr_temoin',"
            " ST_GeomFromText('POLYGON((55 -22, 56 -22, 56 -21, 55 -21, 55 -22))', 4326),"
            " ST_Transform(ST_GeomFromText('POLYGON((55 -22, 56 -22, 56 -21, 55 -21, 55 -22))', 4326), 2975))"))
        pct = pct_parcelles_couche(c, "TemoinPPR-C4", "c4_ppr_temoin", total_parcelles=4)
    # recompte indépendant : 3 points sur 4 dans le polygone → 75,0 %
    dedans = sum(1 for (x, y) in pts if 55 <= x <= 56 and -22 <= y <= -21)
    assert pct == round(100.0 * dedans / 4, 1) == 75.0
