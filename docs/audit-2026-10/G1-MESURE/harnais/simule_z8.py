#!/usr/bin/env python3
"""G1-MESURE mesure 4 — SIMULATION : poids de parcels-ile si servie au dézoom complet (z8).
Méthode A (génération à la volée, SANS stockage) — préférée à l'extrapolation car la
simplification/quantification est non linéaire : extrapoler depuis z9 fausserait le chiffre.
On génère la tuile z8 de l'île (8/167/143) par le MÊME SQL que _parcel_tile_bytes, en deux
variantes : (a) code ACTUEL tel quel à z8 (simplify absent → 0, extent 1024, props maigres) ;
(b) palier z8 SENSÉ extrapolé (simplify 120 m, suite géométrique 60/30/15 → 120 en descendant).
Lecture seule : aucun INSERT, aucun cache touché."""
import gzip, os
os.environ.setdefault("LABUSE_DATABASE_URL","postgresql+psycopg://openclaw@localhost:5432/labuse")
from sqlalchemy import create_engine, text

eng = create_engine(os.environ["LABUSE_DATABASE_URL"])
Z,X,Y = 8,167,143

def gen(simplify, extent):
    buffer = max(extent//64, 8)
    geom = f"ST_SimplifyPreserveTopology(m.geom_3857, {simplify})" if simplify else "m.geom_3857"
    # props MAIGRES z<=11 (mêmes que _parcel_tile_bytes : tier_v2/etage0/zone_fam/commune)
    sql = f"""
      WITH b AS (SELECT ST_TileEnvelope(:z,:x,:y) AS env),
      mvt AS (
        SELECT ST_AsMVTGeom({geom}, b.env, {extent}, {buffer}, true) AS geom,
               m.tier_v2, m.etage0, m.zone_fam, m.commune
        FROM mvt_parcels m, b WHERE m.geom_3857 && b.env)
      SELECT ST_AsMVT(mvt.* ORDER BY mvt.geom, 'parcels', {extent}, 'geom') FROM mvt
    """
    with eng.connect() as c:
        c.execute(text("SET statement_timeout='120s'"))
        data = c.execute(text(sql), {"z":Z,"x":X,"y":Y}).scalar()
    raw = bytes(data) if data else b""
    return len(raw), len(gzip.compress(raw, 6))

for label, s, e in [("(a) code actuel z8 : simplify=0, extent 1024", 0, 1024),
                    ("(b) palier sensé z8 : simplify=120, extent 1024", 120, 1024)]:
    raw, gz = gen(s, e)
    print(f"{label}\n     raw={raw:9d}  gz={gz:9d}  ({raw/1048576:.2f} MB / gz {gz/1048576:.2f} MB)")
