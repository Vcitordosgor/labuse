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

from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)
_PROMUES = ("chaude", "a_surveiller", "a_creuser")


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


def build_parcel_zone_plu(db: Session) -> int:
    """M6.1 item 1 — table dérivée `parcel_zone_plu` (idu PK, zone_lib, zone_fam) : la zone
    PLU DOMINANTE par surface d'intersection (spatial_layers kind='plu_gpu_zone', dédoublonné
    M6-2b). `zone_lib` = CODE COURT de zone (« U1e », « 1AUc ») : le name GPU est hétérogène
    selon les communes (code nu, « Ud : libellé long », phrase entière sans code) — on garde le
    1er token quand il ressemble à un code de la famille, sinon la famille seule (honnête :
    jamais une phrase en étiquette carte). `zone_fam` = famille dérivée du typezone (AU* → AU,
    U* → U, A, N, sinon autre). Build one-shot ~20-40 min sous charge — appelée par
    build_mvt_table SI la table est absente, jointe ensuite en LEFT JOIN (une parcelle hors
    zonage GPU n'apparaît pas ici → colonnes NULL côté tuiles/geojson)."""
    db.execute(text("SET statement_timeout = 0"))
    db.execute(text("DROP TABLE IF EXISTS parcel_zone_plu"))
    # ST_MakeValid sur les 5 848 zones (une géométrie GPU invalide ferait échouer
    # ST_Intersection) ; la jointure s'appuie sur idx_parcels_geom_2975 (nested loop côté zones).
    db.execute(text("""
        CREATE TABLE parcel_zone_plu AS
        WITH z0 AS (
            SELECT name, subtype, ST_MakeValid(geom_2975) AS g,
                   rtrim(split_part(btrim(name), ' ', 1), ':') AS tok,
                   CASE WHEN subtype ILIKE 'AU%' THEN 'AU'
                        WHEN subtype ILIKE 'U%'  THEN 'U'
                        WHEN subtype = 'A'       THEN 'A'
                        WHEN subtype = 'N'       THEN 'N'
                        ELSE 'autre' END AS fam
            FROM spatial_layers WHERE kind = 'plu_gpu_zone'
        ), z AS (
            SELECT g, CAST(fam AS varchar) AS fam,
                   CAST(CASE WHEN name NOT LIKE '% %' THEN name
                             WHEN length(tok) BETWEEN 1 AND 10 AND (
                                  (fam = 'AU' AND tok ~* '^[0-9]{0,2}AU')
                               OR (fam = 'U'  AND tok ~* '^[0-9]{0,2}U')
                               OR (fam = 'A'  AND tok ~* '^A')
                               OR (fam = 'N'  AND tok ~* '^N'))
                             THEN tok ELSE fam END AS varchar) AS lib
            FROM z0
        )
        SELECT DISTINCT ON (p.idu)
               p.idu, z.lib AS zone_lib, z.fam AS zone_fam
        FROM parcels p
        JOIN z ON p.geom_2975 && z.g AND ST_Intersects(p.geom_2975, z.g)
        ORDER BY p.idu, ST_Area(ST_Intersection(p.geom_2975, z.g)) DESC
    """))
    db.execute(text("ALTER TABLE parcel_zone_plu ADD PRIMARY KEY (idu)"))
    db.execute(text("ANALYZE parcel_zone_plu"))
    n = db.execute(text("SELECT count(*) FROM parcel_zone_plu")).scalar() or 0
    db.commit()
    return int(n)


def build_parcel_adresse(db: Session) -> int:
    """M6.2 perf — table dérivée `parcel_adresse` (idu PK, ban_voie/ban_cp/ban_commune) : la
    MEILLEURE adresse BAN par parcelle, matérialisée une fois. Élimine le LATERAL par parcelle
    (regexp + tri, ~5,4 s pour 21k parcelles en mode commune) qui pesait sur geojson/liste/CSV.
    Sélection STRICTEMENT identique au lateral (_BAN_ORDER) via DISTINCT ON → mêmes adresses.
    Rebuild rapide (~1,5 s pour 257k) ; à relancer si la BAN est ré-ingérée (build-mvt le fait)."""
    if not db.execute(text("SELECT to_regclass('adresse_parcelles') IS NOT NULL"
                           " AND to_regclass('adresses') IS NOT NULL")).scalar():
        return 0
    db.execute(text("DROP TABLE IF EXISTS parcel_adresse"))
    db.execute(text(r"""
        CREATE TABLE parcel_adresse AS
        SELECT DISTINCT ON (ap.idu) ap.idu,
               trim(concat_ws(' ', a.numero, a.rep, a.voie)) AS ban_voie,
               a.code_postal AS ban_cp, a.commune AS ban_commune
        FROM adresse_parcelles ap JOIN adresses a ON a.id_ban = ap.id_ban
        ORDER BY ap.idu, (ap.source = 'principal') DESC, (a.numero IS NULL),
                 NULLIF(regexp_replace(a.numero, '\D', '', 'g'), '')::int NULLS LAST, a.id_ban
    """))
    db.execute(text("ALTER TABLE parcel_adresse ADD PRIMARY KEY (idu)"))
    db.execute(text("ANALYZE parcel_adresse"))
    n = db.execute(text("SELECT count(*) FROM parcel_adresse")).scalar() or 0
    db.commit()
    return int(n)


def build_mvt_table(db: Session, run_label: str = RUN) -> int:
    """(Re)construit la table matérialisée servie en tuiles. À lancer APRÈS un run de scoring
    (le script d'extension île le fait) ; idempotent, ~1-2 min pour 431k parcelles."""
    # M6.1 : le zonage PLU par parcelle est un prérequis des tuiles — construit une seule fois
    # (long) puis réutilisé tel quel à chaque rebuild (le zonage ne bouge pas avec les runs).
    if not db.execute(text("SELECT to_regclass('parcel_zone_plu')")).scalar():
        build_parcel_zone_plu(db)
    # M6.2 : adresse BAN matérialisée (rapide) — reconstruite à chaque build-mvt (suit la BAN).
    build_parcel_adresse(db)
    db.execute(text("DROP TABLE IF EXISTS mvt_parcels"))
    # correctif M5 (verdict) : tier v2 embarqué dans les tuiles — la carte colore par le
    # verdict effectif (tier v2 quand un run existe, étage 0 du run servi prime).
    v2run = db.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar() \
        if db.execute(text("SELECT to_regclass('p_score_v2_runs')")).scalar() else None
    db.execute(text("""
        CREATE TABLE mvt_parcels AS
        SELECT p.id, p.idu, p.commune, p.surface_m2,
               ST_Transform(p.geom, 3857) AS geom_3857,
               d.matrice_statut AS status, d.q_score, d.a_score, d.a_completude,
               s2.tier AS tier_v2, s2.rang AS rang_v2, s2.mult_base AS mult_v2,
               (d.status IN ('exclue', 'faux_positif_probable'))::int AS etage0,
               d.completeness_score, r.sdp_residuelle_m2, r.sous_densite,
               CASE WHEN ev.parcel_id IS NOT NULL THEN 'rouge' END AS evenement,
               COALESCE(fl.flags, '') AS flags,
               zp.zone_lib, zp.zone_fam
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                   WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
        LEFT JOIN (SELECT parcel_id, string_agg(DISTINCT layer_name, ',') AS flags
                   FROM dryrun_cascade_results
                   WHERE run_label = :run AND (result = 'SOFT_FLAG'
                         OR (layer_name = 'abf' AND result = 'UNKNOWN'))
                   GROUP BY parcel_id) fl ON fl.parcel_id = p.id
    """), {"run": run_label, "v2run": v2run})
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
# M6.2 perf : cache navigateur des tuiles (le contenu ne change qu'au build-mvt). Appliqué
# AUSSI au chemin servi depuis le cache LRU serveur — il l'omettait, donc le navigateur
# re-téléchargeait les tuiles CHAUDES à chaque navigation.
_TILE_HEADERS = {"Cache-Control": "public, max-age=3600"}


def _mvt_has_zone(db: Session) -> bool:
    """La table mvt_parcels SERVIE porte-t-elle zone_lib/zone_fam (build post-M6.1) ?"""
    return bool(db.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'mvt_parcels' AND column_name = 'zone_fam'")).scalar())


@router.get("/map/tiles/meta")
def mvt_tiles_meta(db: Session = Depends(get_db)) -> dict:
    """Capacités des tuiles servies — le front grise la couche « Zonage PLU (parcelles) »
    en mode île tant que mvt_parcels n'embarque pas zone_fam (prochain build-mvt)."""
    run = None
    if db.execute(text("SELECT to_regclass('mvt_meta')")).scalar():
        run = db.execute(text("SELECT value FROM mvt_meta WHERE key = 'run_label'")).scalar()
    return {"run_label": run,
            "zonage_parcelle": _mvt_has_zone(db)
            if db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar() else False}


@router.get("/map/tiles/{z}/{x}/{y}.pbf")
def mvt_tile(z: int, x: int, y: int, db: Session = Depends(get_db)) -> Response:
    """Tuile MVT couche `parcels` — mêmes propriétés que le GeoJSON commune."""
    if z < 9 or z > 22:
        return Response(status_code=204)
    key = (z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf", headers=_TILE_HEADERS)
    exists = db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar()
    if not exists:
        return Response(status_code=204)  # table pas encore construite (run en cours)
    # table d'avant le correctif M5 (sans tier_v2) : repli legacy jusqu'au `labuse build-mvt`
    has_v2 = db.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'mvt_parcels' AND column_name = 'tier_v2'")).scalar()
    # M6.1 : table d'avant l'item 1 (sans zone_lib/zone_fam) : repli — les tuiles embarqueront
    # le zonage au prochain `labuse build-mvt` (bascule q_v5), RIEN ne casse d'ici là.
    has_zone = _mvt_has_zone(db)
    # R1 (revue Vic n°2 : le cadastre d'abord) — TOUTES les parcelles dès z9, simplification
    # par palier pour tenir les poids (mesurés : z9 « tout » 10 m ≈ 3,4 Mo, z10 5 m ≈ 3,5 Mo,
    # z12+ brut ≈ 850 Ko max). L'ouverture cadre l'île entière : la trame est là d'emblée.
    simplify = {9: 10, 10: 5, 11: 2}.get(z, 0)
    geom_expr = (f"ST_SimplifyPreserveTopology(m.geom_3857, {simplify})" if simplify
                 else "m.geom_3857")
    # z ≤ 11 : tuiles MAIGRES (status + commune seulement — 24 et 4 valeurs distinctes,
    # dédupliquées par l'encodage MVT). Les 13 propriétés complètes (idu unique en tête)
    # pesaient 15 Mo/tuile à z9 ; le clic passe par /parcels/at, le ping vole à z16.
    # tier_v2/etage0 dans les tuiles maigres aussi : c'est la couleur (verdict effectif)
    v2_props = "m.tier_v2, m.etage0, " if has_v2 else ""
    v2_props_full = "m.tier_v2, m.rang_v2, m.mult_v2, m.etage0, " if has_v2 else ""
    # zone_fam dans les tuiles maigres aussi (5 valeurs distinctes, dédupliquées par le MVT) :
    # c'est la COULEUR de la couche « Zonage PLU (parcelles) », visible dès z9 en mode île.
    zone_props = "m.zone_fam, " if has_zone else ""
    zone_props_full = "m.zone_lib, m.zone_fam, " if has_zone else ""
    props = (f"m.status, {v2_props}{zone_props}m.commune" if z <= 11 else
             "m.idu, m.commune, m.surface_m2, m.status, m.q_score, m.a_score, "
             f"{v2_props_full}{zone_props_full}"
             "m.a_completude, m.completeness_score, m.sdp_residuelle_m2, "
             "m.sous_densite, m.evenement, m.flags")
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
    return Response(content=body, media_type="application/x-protobuf", headers=_TILE_HEADERS)


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
        return Response(content=_CACHE[key], media_type="application/x-protobuf", headers=_TILE_HEADERS)
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
    return Response(content=body, media_type="application/x-protobuf", headers=_TILE_HEADERS)
