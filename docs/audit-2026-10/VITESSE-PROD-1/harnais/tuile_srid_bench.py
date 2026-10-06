"""VITESSE-PROD-1 — banc AVANT/APRÈS des tuiles overlay (prédicat SRID + ordre déterministe).

AVANT = requête historique : prédicat `ST_SetSRID(m.geom, srid) && env` (l'index GiST ne matche
pas → seq scan par tuile) + `ORDER BY mvt.geom` seul (égalités départagées par l'ordre de scan →
octets INSTABLES sur les couches à boîtes égales — mesuré : 3 calculs = 3 md5 sur amenite_bpe,
batiment, trait_de_cote).
APRÈS = `_construire_tuile` courant : colonne nue dans le WHERE (index) + départage `mvt::text`.

Invariants prouvés, par couche × tuile témoin :
  1. CONTENU identique : md5 du MULTISET des lignes (geom MVT + toutes propriétés) entrant dans
     ST_AsMVT, pour l'ancien et le nouveau WHERE → mêmes entités, mêmes propriétés, mêmes pixels.
  2. DÉTERMINISME APRÈS : 2 calculs consécutifs → même md5 d'octets (l'AVANT ne le tenait pas).
  3. VITESSE : ms AVANT vs APRÈS (médiane de 3, à cache Postgres chaud).

Sortie CSV : couche,z,x,y,ms_avant,ms_apres,octets,contenu_identique,deterministe_apres
Usage : PYTHONPATH=src python docs/audit-2026-10/VITESSE-PROD-1/harnais/tuile_srid_bench.py
"""
from __future__ import annotations

import hashlib
import statistics
import sys
import time

from sqlalchemy import text

from labuse.api.couches_tuyau import _construire_tuile, _table_manquante, registre
from labuse.db import session_scope

# tuiles témoins : vue île (z9-11, pré-chauffées en prod) + zooms de travail z12-z15 (Saint-Paul,
# Saint-Pierre — zones habitées, tuiles réellement demandées par la carte).
TUILES = [
    (9, 334, 286), (10, 669, 573), (11, 1339, 1146),
    (12, 2679, 2293),            # ouest (Saint-Paul)
    (13, 5357, 4587),            # Saint-Paul (tuile mesurée 4 s à froid AVANT, bout en bout)
    (13, 5359, 4592),            # sud (Saint-Pierre)
    (14, 10714, 9174),           # Saint-Paul z14
    (15, 21429, 18349),          # Saint-Paul z15
]


def _sql_parts(c) -> tuple[str, dict]:
    params: dict = {"layer": c.kind}
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
    return where, params


def _cte(c, where: str, predicat_nu: bool) -> str:
    g_src = f"ST_SetSRID(m.{c.geom}, {c.srid})"
    g_3857 = g_src if c.srid == 3857 else f"ST_Transform({g_src}, 3857)"
    filtre = "b.env_marge" if c.srid == 3857 else f"ST_Transform(b.env_marge, {c.srid})"
    g_filtre = f"m.{c.geom}" if predicat_nu else g_src
    props_sql = "".join(f', {expr} AS "{nom}"' for nom, expr in c.props)
    return f"""
        WITH b AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS env,
                   ST_TileEnvelope(:z, :x, :y, margin => 0.125) AS env_marge
        ),
        mvt AS (
            SELECT ST_AsMVTGeom({g_3857}, b.env, 4096, 64, true) AS geom{props_sql}
            FROM {c.table} m, b
            WHERE {where}
              AND {g_filtre} && {filtre}
        )"""


def tuile_avant(db, c, z, x, y) -> bytes:
    """Requête AVANT VITESSE-PROD-1 : prédicat ST_SetSRID + ORDER BY mvt.geom seul."""
    where, params = _sql_parts(c)
    params.update({"z": z, "x": x, "y": y})
    sql = text(_cte(c, where, predicat_nu=False) + """
        SELECT ST_AsMVT(mvt.*, :layer, 4096, 'geom' ORDER BY mvt.geom) FROM mvt WHERE geom IS NOT NULL
    """)
    data = db.execute(sql, params).scalar()
    return bytes(data) if data else b""


def multiset_md5(db, c, z, x, y, predicat_nu: bool) -> str:
    """md5 du MULTISET des lignes (geom MVT + props) entrant dans ST_AsMVT — indépendant de l'ordre."""
    where, params = _sql_parts(c)
    params.update({"z": z, "x": x, "y": y})
    params.pop("layer")
    sql = text(_cte(c, where, predicat_nu) + """
        SELECT md5(coalesce(string_agg(t, '' ORDER BY t), '')) FROM
          (SELECT mvt::text AS t FROM mvt WHERE geom IS NOT NULL) s
    """)
    return db.execute(sql, params).scalar()


def mediane_ms(fn, n=3) -> tuple[float, object]:
    ts, out = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts), out


def main() -> None:
    print("couche,z,x,y,ms_avant,ms_apres,octets,contenu_identique,deterministe_apres")
    ko_contenu = ko_det = 0
    with session_scope() as db:
        reg = registre()
        for kind in sorted(reg):
            c = reg[kind]
            if _table_manquante(db, c.table):
                continue
            for z, x, y in TUILES:
                ms_avant, _ = mediane_ms(lambda: tuile_avant(db, c, z, x, y))
                ms_apres, b1 = mediane_ms(lambda: _construire_tuile(db, c, z, x, y))
                b2 = _construire_tuile(db, c, z, x, y)
                det = hashlib.md5(b1).hexdigest() == hashlib.md5(b2).hexdigest()
                contenu = multiset_md5(db, c, z, x, y, False) == multiset_md5(db, c, z, x, y, True)
                ko_det += 0 if det else 1
                ko_contenu += 0 if contenu else 1
                print(f"{kind},{z},{x},{y},{ms_avant:.1f},{ms_apres:.1f},{len(b1)},"
                      f"{'OUI' if contenu else 'NON'},{'OUI' if det else 'NON'}", flush=True)
    if ko_contenu or ko_det:
        print(f"ÉCHEC : {ko_contenu} contenus ≠, {ko_det} non déterministes", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
