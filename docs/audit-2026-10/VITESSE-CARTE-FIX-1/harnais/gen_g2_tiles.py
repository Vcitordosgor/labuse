"""VITESSE-CARTE-FIX-1 (G2) — génère, par (couche, z/x/y), les octets AVANT (ST_AsMVT SANS ORDER BY,
ordre non déterministe) et APRÈS (avec `ORDER BY mvt.geom` en fin d'arguments). Écrit les .pbf + un
plan JSON (niveaux/style par couche) pour le test de neutralité pixel `neutralite_g2.mjs`.

But : prouver que le seul effet du `ORDER BY` (requis pour rendre le cache byte-identique à la volée)
est l'ORDRE des features — jamais les pixels. On rend AVANT vs APRÈS avec le style réel du front.

  PYTHONPATH=src LABUSE_ENV=local LABUSE_DATABASE_URL=... python gen_g2_tiles.py <outdir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope
from labuse.api import couches_tuyau as ct

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "g2_tiles")
OUT.mkdir(parents=True, exist_ok=True)

# 5 couches lourdes (dont multi-sous-types : plu_gpu_zone, sup) × 3 zooms · tuiles St-Denis dense
COUCHES = ["ppr", "alea_mvt", "plu_gpu_zone", "sup", "ebc"]
TUILES = {9: (334, 286), 11: (1339, 1145), 13: (5357, 4582)}


def construire(db, c, z, x, y, *, ordonne: bool) -> bytes:
    """Reproduit _construire_tuile, avec/ sans ORDER BY — pour comparer AVANT/APRÈS."""
    params: dict = {"z": z, "x": x, "y": y, "layer": c.kind}
    if c.resolution:
        clauses = []
        for i, (k, subs) in enumerate(c.resolution):
            params[f"k{i}"] = k
            if subs:
                clauses.append(f"(m.kind = :k{i} AND m.subtype = ANY(:s{i}))")
                params[f"s{i}"] = list(subs)
            else:
                clauses.append(f"(m.kind = :k{i})")
        where = "(" + " OR ".join(clauses) + ")"
    else:
        where = c.where_sql or "TRUE"
    g_src = f"ST_SetSRID(m.{c.geom}, {c.srid})"
    g_3857 = g_src if c.srid == 3857 else f"ST_Transform({g_src}, 3857)"
    filtre = "b.env_marge" if c.srid == 3857 else f"ST_Transform(b.env_marge, {c.srid})"
    props_sql = "".join(f', {expr} AS "{nom}"' for nom, expr in c.props)
    order = " ORDER BY mvt.geom" if ordonne else ""
    sql = text(f"""
        WITH b AS (SELECT ST_TileEnvelope(:z,:x,:y) AS env,
                          ST_TileEnvelope(:z,:x,:y, margin=>0.125) AS env_marge),
        mvt AS (SELECT ST_AsMVTGeom({g_3857}, b.env, 4096, 64, true) AS geom{props_sql}
                FROM {c.table} m, b WHERE {where} AND {g_src} && {filtre})
        SELECT ST_AsMVT(mvt.*, :layer, 4096, 'geom'{order}) FROM mvt WHERE geom IS NOT NULL
    """)
    data = db.execute(sql, params).scalar()
    return bytes(data) if data else b""


def main() -> None:
    import hashlib
    plan = {}
    with session_scope() as db:
        reg = ct.registre()
        # le plan servi (niveaux/style/subdivise) pour le rendu fidèle côté front
        from labuse.registre.declarations import couches_carte
        decl = {d["kind"]: d for d in couches_carte()}
        lignes = ["couche,z,x,y,bytes_avant,bytes_apres,md5_avant,md5_apres,octets_egaux"]
        for kind in COUCHES:
            c = reg.get(kind)
            if c is None:
                print(f"⚠ {kind} absente du registre — ignorée")
                continue
            d = decl.get(kind, {})
            plan[kind] = {
                "niveaux": d.get("niveaux"),
                "style": d.get("style"),
                "geometrie": d.get("geometrie") or "polygone",
                "subdivise": reg[kind].table == "tuyau_subdivise",
            }
            for z, (x, y) in TUILES.items():
                av = construire(db, c, z, x, y, ordonne=False)
                ap = construire(db, c, z, x, y, ordonne=True)
                (OUT / f"{kind}_z{z}_avant.pbf").write_bytes(av)
                (OUT / f"{kind}_z{z}_apres.pbf").write_bytes(ap)
                lignes.append(f"{kind},{z},{x},{y},{len(av)},{len(ap)},"
                              f"{hashlib.md5(av).hexdigest()[:8]},{hashlib.md5(ap).hexdigest()[:8]},"
                              f"{av == ap}")
                print(f"{kind} z{z}: avant {len(av)} o / après {len(ap)} o "
                      f"(octets {'égaux' if av == ap else 'différents'})")
    (OUT / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "bytes.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("→", OUT / "plan.json")


if __name__ == "__main__":
    main()
