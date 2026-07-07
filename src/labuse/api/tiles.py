"""Tuiles vectorielles MVT — la carte ÎLE ENTIÈRE (431k parcelles).

Le GeoJSON par commune (26 Mo à Saint-Paul) ne tient pas à l'échelle de l'île : on sert du
MVT depuis une table MATÉRIALISÉE `mvt_parcels` (statuts + propriétés de filtre pré-joints,
géométrie en 3857, GIST) reconstruite après chaque run de scoring (`labuse build-mvt`).
Doctrine perf : z<10 rien (l'île entière = communes colorées par les couches IGN), z10-12
uniquement les promues (chaude/à surveiller/à creuser), z≥13 tout — un tile reste < ~700 Ko.
Les propriétés portent EXACTEMENT les clés du GeoJSON commune (idu, status, q_score…) pour
que les expressions de filtre MapLibre soient IDENTIQUES sur les deux sources ; `flags` est
une chaîne CSV (le MVT ne porte pas de tableaux) — l'expression `['in', flag, ['get','flags']]`
fonctionne à l'identique sur chaîne et tableau.
"""
from __future__ import annotations

from collections import OrderedDict

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(tags=["tiles"])

RUN = "q_v2"
_PROMUES = ("chaude", "a_surveiller", "a_creuser")


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


def build_mvt_table(db: Session, run_label: str = RUN) -> int:
    """(Re)construit la table matérialisée servie en tuiles. À lancer APRÈS un run de scoring
    (le script d'extension île le fait) ; idempotent, ~1-2 min pour 431k parcelles."""
    db.execute(text("DROP TABLE IF EXISTS mvt_parcels"))
    db.execute(text("""
        CREATE TABLE mvt_parcels AS
        SELECT p.id, p.idu, p.commune, p.surface_m2,
               ST_Transform(p.geom, 3857) AS geom_3857,
               d.matrice_statut AS status, d.q_score, d.a_score, d.a_completude,
               d.completeness_score, r.sdp_residuelle_m2, r.sous_densite, vm.vue AS vue_mer,
               CASE WHEN ev.parcel_id IS NOT NULL THEN 'rouge' END AS evenement,
               COALESCE(fl.flags, '') AS flags
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN parcel_vue_mer vm ON vm.parcel_id = p.id
        LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                   WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
        LEFT JOIN (SELECT parcel_id, string_agg(DISTINCT layer_name, ',') AS flags
                   FROM dryrun_cascade_results
                   WHERE run_label = :run AND (result = 'SOFT_FLAG'
                         OR (layer_name = 'abf' AND result = 'UNKNOWN'))
                   GROUP BY parcel_id) fl ON fl.parcel_id = p.id
    """), {"run": run_label})
    db.execute(text("CREATE INDEX mvt_parcels_gix ON mvt_parcels USING GIST (geom_3857)"))
    db.execute(text("CREATE INDEX mvt_parcels_status ON mvt_parcels (status)"))
    db.execute(text("ANALYZE mvt_parcels"))
    n = db.execute(text("SELECT count(*) FROM mvt_parcels")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


# cache LRU en mémoire (les tuiles sont chères à générer et très re-demandées en navigation)
_CACHE: OrderedDict[tuple, bytes] = OrderedDict()
_CACHE_MAX = 4096


@router.get("/map/tiles/{z}/{x}/{y}.pbf")
def mvt_tile(z: int, x: int, y: int, db: Session = Depends(get_db)) -> Response:
    """Tuile MVT couche `parcels` — mêmes propriétés que le GeoJSON commune."""
    if z < 10 or z > 22:
        return Response(status_code=204)
    key = (z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf")
    exists = db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar()
    if not exists:
        return Response(status_code=204)  # table pas encore construite (run en cours)
    # z10-12 : promues seules (l'aperçu île = « où sont les cibles ») ; z13+ : tout (les
    # écartées à 0.04 d'opacité n'apportent rien sous ~10 km d'écran et triplent la tuile)
    statut_where = "" if z >= 13 else "AND m.status IN ('chaude','a_surveiller','a_creuser')"
    data = db.execute(text(f"""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),
        mvt AS (
          SELECT ST_AsMVTGeom(m.geom_3857, b.env, 4096, 64, true) AS geom,
                 m.idu, m.commune, m.surface_m2, m.status, m.q_score, m.a_score,
                 m.a_completude, m.completeness_score, m.sdp_residuelle_m2,
                 m.sous_densite, m.vue_mer, m.evenement, m.flags
          FROM mvt_parcels m, b
          WHERE m.geom_3857 && b.env {statut_where}
        )
        SELECT ST_AsMVT(mvt.*, 'parcels', 4096, 'geom') FROM mvt
    """), {"z": z, "x": x, "y": y}).scalar()
    body = bytes(data) if data else b""
    _CACHE[key] = body
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return Response(content=body, media_type="application/x-protobuf",
                    headers={"Cache-Control": "public, max-age=3600"})
