"""Tuiles vectorielles MVT — la carte ÎLE ENTIÈRE (431k parcelles).

Le GeoJSON par commune (26 Mo à Saint-Paul) ne tient pas à l'échelle de l'île : on sert du
MVT depuis une table MATÉRIALISÉE `mvt_parcels` (statuts + propriétés de filtre pré-joints,
géométrie en 3857, GIST) reconstruite après chaque run de scoring (`labuse build-mvt`).
Doctrine perf (R1, revue Vic n°2) : TOUT dès z9 — simplification par palier (z9 : 10 m ≈
3,4 Mo/tuile · z10 : 5 m · z11 : 2 m · z12+ : brut ≈ 850 Ko max), cache LRU + navigateur.
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
    if z < 9 or z > 22:
        return Response(status_code=204)
    key = (z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf")
    exists = db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar()
    if not exists:
        return Response(status_code=204)  # table pas encore construite (run en cours)
    # R1 (revue Vic n°2 : le cadastre d'abord) — TOUTES les parcelles dès z9, simplification
    # par palier pour tenir les poids (mesurés : z9 « tout » 10 m ≈ 3,4 Mo, z10 5 m ≈ 3,5 Mo,
    # z12+ brut ≈ 850 Ko max). L'ouverture cadre l'île entière : la trame est là d'emblée.
    simplify = {9: 10, 10: 5, 11: 2}.get(z, 0)
    geom_expr = (f"ST_SimplifyPreserveTopology(m.geom_3857, {simplify})" if simplify
                 else "m.geom_3857")
    # z ≤ 11 : tuiles MAIGRES (status + commune seulement — 24 et 4 valeurs distinctes,
    # dédupliquées par l'encodage MVT). Les 13 propriétés complètes (idu unique en tête)
    # pesaient 15 Mo/tuile à z9 ; le clic passe par /parcels/at, le ping vole à z16.
    props = ("m.status, m.commune" if z <= 11 else
             "m.idu, m.commune, m.surface_m2, m.status, m.q_score, m.a_score, "
             "m.a_completude, m.completeness_score, m.sdp_residuelle_m2, "
             "m.sous_densite, m.vue_mer, m.evenement, m.flags")
    data = db.execute(text(f"""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),
        mvt AS (
          SELECT ST_AsMVTGeom({geom_expr}, b.env, 4096, 64, true) AS geom,
                 {props}
          FROM mvt_parcels m, b
          WHERE m.geom_3857 && b.env
        )
        SELECT ST_AsMVT(mvt.*, 'parcels', 4096, 'geom') FROM mvt
    """), {"z": z, "x": x, "y": y}).scalar()
    body = bytes(data) if data else b""
    _CACHE[key] = body
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return Response(content=body, media_type="application/x-protobuf",
                    headers={"Cache-Control": "public, max-age=3600"})


# ═══════════ OVERLAYS MVT (R6, revue Vic n°2) — zonage PLU + PPR île entière ═══════════
# 6 306 zones (29 Mo) + 164 PPR (88 Mo, mégapolygones 320k pts) : le GeoJSON île ne tient
# pas → même mécanique matérialisée que mvt_parcels. Reconstruit par `labuse build-mvt`.

OVERLAY_KINDS = ("plu_gpu_zone", "ppr")


def build_overlay_mvt(db: Session) -> int:
    db.execute(text("DROP TABLE IF EXISTS mvt_overlays"))
    db.execute(text("""
        CREATE TABLE mvt_overlays AS
        SELECT id, kind, subtype, name, commune, ST_Transform(geom, 3857) AS geom_3857
        FROM spatial_layers WHERE kind IN ('plu_gpu_zone', 'ppr')"""))
    db.execute(text("CREATE INDEX mvt_overlays_gix ON mvt_overlays USING GIST (geom_3857)"))
    db.execute(text("CREATE INDEX mvt_overlays_kind ON mvt_overlays (kind)"))
    db.execute(text("ANALYZE mvt_overlays"))
    n = db.execute(text("SELECT count(*) FROM mvt_overlays")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


@router.get("/map/tiles/ov/{kind}/{z}/{x}/{y}.pbf")
def mvt_overlay_tile(kind: str, z: int, x: int, y: int, db: Session = Depends(get_db)) -> Response:
    """Tuile MVT d'une couche overlay (couche = `kind`) — mode île."""
    if kind not in OVERLAY_KINDS or z < 8 or z > 22:
        return Response(status_code=204)
    key = ("ov", kind, z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf")
    if not db.execute(text("SELECT to_regclass('mvt_overlays')")).scalar():
        return Response(status_code=204)
    data = db.execute(text("""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),
        mvt AS (
          SELECT ST_AsMVTGeom(m.geom_3857, b.env, 4096, 64, true) AS geom,
                 m.subtype, m.name, m.commune
          FROM mvt_overlays m, b
          WHERE m.kind = :k AND m.geom_3857 && b.env)
        SELECT ST_AsMVT(mvt.*, :k, 4096, 'geom') FROM mvt"""),
        {"z": z, "x": x, "y": y, "k": kind}).scalar()
    body = bytes(data) if data else b""
    _CACHE[key] = body
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return Response(content=body, media_type="application/x-protobuf",
                    headers={"Cache-Control": "public, max-age=3600"})
