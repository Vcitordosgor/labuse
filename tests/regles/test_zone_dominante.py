"""Témoin CIRCUIT-4 — zone servie : la DOMINANTE PAR SURFACE, recomparée à un calcul d'aires
indépendant (géométries seedées 60/40)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_dominante_par_surface(engine):
    from labuse.db import session_scope
    from labuse.faisabilite.zone_servie import zone_dominante
    with engine.begin() as c:
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'plu_gpu_zone'"
                       " AND name IN ('U1 c4', 'N c4')"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinZone-C4'"))
        # parcelle rectangulaire en 4326 (les triggers dérivent geom_2975) ; U1 couvre 60 % de
        # la largeur, N les 40 % restants (split à 55.5006)
        c.execute(text(
            "INSERT INTO parcels (idu, commune, surface_m2, geom, geom_2975) VALUES "
            "('C4ZON0000000', 'TemoinZone-C4', 10000, ST_GeomFromText(:w, 4326),"
            " ST_Transform(ST_GeomFromText(:w, 4326), 2975))"),
            {"w": "POLYGON((55.5 -21.1, 55.501 -21.1, 55.501 -21.099, 55.5 -21.099, 55.5 -21.1))"})
        pid = c.execute(text("SELECT id FROM parcels WHERE idu = 'C4ZON0000000'")).scalar()
        for nom, st, lib, wkt in (
            ("U1 c4", "U", "U1",
             "POLYGON((55.5 -21.1, 55.5006 -21.1, 55.5006 -21.099, 55.5 -21.099, 55.5 -21.1))"),
            ("N c4", "N", "N",
             "POLYGON((55.5006 -21.1, 55.501 -21.1, 55.501 -21.099, 55.5006 -21.099, 55.5006 -21.1))")):
            c.execute(text(
                "INSERT INTO spatial_layers (kind, name, subtype, attrs, geom, geom_2975) VALUES "
                "('plu_gpu_zone', :n, :st, :a, ST_GeomFromText(:w, 4326),"
                " ST_Transform(ST_GeomFromText(:w, 4326), 2975))"),
                {"n": nom, "st": st, "a": '{"libelle": "%s"}' % lib, "w": wkt})
    with session_scope() as s:
        z = zone_dominante(s, pid)
    with engine.begin() as c:   # nettoyage : aucun legs (zones fantômes) dans la base partagée
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'plu_gpu_zone'"
                       " AND name IN ('U1 c4', 'N c4')"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinZone-C4'"))
    # recalcul indépendant : la coupe 4326 à 60 % de la largeur → parts ~60/40 (projection
    # localement conforme, tolérance 1 pt d'arrondi)
    assert z.zone == "U1" and z.zone_fam == "U"
    parts = {p["zone"]: p["pct"] for p in z.parts}
    assert abs(parts["U1"] - 60.0) <= 1.0 and abs(parts["N"] - 40.0) <= 1.0
    assert abs(parts["U1"] + parts["N"] - 100.0) <= 0.3
    assert z.a_cheval is True                   # dominante < seuil 90 % → à cheval, parts servies
    assert abs(z.pct_constructible - parts["U1"]) < 0.01   # somme des parts U/AU
