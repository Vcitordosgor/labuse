"""SOURCES-4 lot 2 — CoSIA TOUTES LES CLASSES par parcelle (couverture du sol IA, IGN).

L'ingestion `cosia.py` ne matérialise que la classe « Bâtiment » (1 des 15). Le mandat SOURCES-4
veut TOUTES les classes de couverture PAR PARCELLE. On calcule, pour chaque parcelle, la surface
(m²) de chaque classe CoSIA qui la recouvre → table `parcel_cosia_couverture (idu, classe, m2)`.

⚠ CALCUL UNIQUE, LOURD, NON RÉCURRENT (décision Vic) : l'intersection couvre toute l'île
(431 663 parcelles × ~14 classes × des millions de polygones 20 cm). On procède TUILE PAR TUILE
(37 tuiles GPKG) pour borner la mémoire et le disque : chaque tuile est chargée dans une table de
staging indexée (GIST), intersectée avec les parcelles, agrégée en (idu, classe, m²) puis cumulée
dans la table finale ; la staging est vidée avant la tuile suivante. Idempotent au niveau tuile
(la table finale est purgée une fois au début d'un run complet).

CRS : les géométries CoSIA sont en EPSG:2975 (RGR92/UTM40S) — identique à `parcels.geom_2975`,
aucune reprojection. Lecture GPKG en pur Python (`sqlite3`, cf. cosia.py) : BLOB « GP » → WKB.
"""
from __future__ import annotations

import glob
import sqlite3
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .cosia import _default_extract_dir, _gpkg_to_wkb

TABLE = "parcel_cosia_couverture"

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    idu     varchar(14) NOT NULL,
    classe  text        NOT NULL,
    m2      double precision NOT NULL,
    source_millesime text,
    computed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (idu, classe)
)
"""


def ensure_table(session: Session) -> None:
    session.execute(text(DDL))


def _charger_staging(session: Session, gpkg: str, batch: int = 3000) -> int:
    """Charge TOUTES les classes d'une tuile GPKG dans `_cosia_tile` (classe, g), en SUBDIVISANT les
    polygones (`ST_Subdivide`, ≤128 sommets) : les grands objets (forêt, broussaille) sont éclatés
    en petits morceaux → le filtre GIST `&&` devient TRÈS sélectif et chaque `ST_Intersection` porte
    sur une pièce minuscule (le tuilage lourd des tuiles urbaines denses tombe de ~heures à minutes).
    Renvoie le nombre de polygones bruts chargés."""
    session.execute(text("DROP TABLE IF EXISTS _cosia_raw, _cosia_tile"))
    session.execute(text(
        "CREATE TEMP TABLE _cosia_raw (classe text, g geometry(Geometry, 2975))"))
    ins = text("INSERT INTO _cosia_raw (classe, g) VALUES "
               "(:c, ST_CollectionExtract(ST_MakeValid(ST_GeomFromWKB(:wkb, 2975)), 3))")
    db = sqlite3.connect(gpkg)
    try:
        tbl = db.execute("SELECT table_name FROM gpkg_contents "
                         "WHERE data_type='features'").fetchone()[0]
        cur = db.execute(f'SELECT classe, geom FROM "{tbl}"')
        n = 0
        params: list[dict] = []
        for classe, blob in cur:
            wkb = _gpkg_to_wkb(blob)
            if wkb is None or not classe:
                continue
            params.append({"c": str(classe), "wkb": wkb})
            if len(params) >= batch:
                session.execute(ins, params)
                n += len(params)
                params.clear()
        if params:
            session.execute(ins, params)
            n += len(params)
    finally:
        db.close()
    # subdivision : petits morceaux → index efficace ; on écarte les géométries vides/nulles.
    session.execute(text(
        "CREATE TEMP TABLE _cosia_tile AS "
        "SELECT classe, ST_Subdivide(g, 128) AS g FROM _cosia_raw "
        "WHERE g IS NOT NULL AND NOT ST_IsEmpty(g)"))
    session.execute(text("DROP TABLE _cosia_raw"))
    session.execute(text("CREATE INDEX ON _cosia_tile USING gist (g)"))
    session.execute(text("ANALYZE _cosia_tile"))
    return n


def _agreger_tuile(session: Session, millesime: str) -> int:
    """Intersecte la staging `_cosia_tile` avec les parcelles, agrège la surface par (idu, classe)
    et CUMULE dans la table finale (une parcelle peut chevaucher plusieurs tuiles). Renvoie le
    nombre de couples (idu, classe) touchés par cette tuile."""
    res = session.execute(text(f"""
        INSERT INTO {TABLE} (idu, classe, m2, source_millesime)
        SELECT p.idu, t.classe,
               SUM(ST_Area(ST_Intersection(p.geom_2975, t.g))) AS m2,
               :mil
          FROM parcels p
          JOIN _cosia_tile t
            ON p.geom_2975 && t.g AND ST_Intersects(p.geom_2975, t.g)
         GROUP BY p.idu, t.classe
        ON CONFLICT (idu, classe) DO UPDATE
           SET m2 = {TABLE}.m2 + EXCLUDED.m2, computed_at = now()
    """), {"mil": millesime})
    return res.rowcount


def build_couverture(session: Session, extract_dir: str | Path | None = None,
                     tiles: list[str] | None = None, purge: bool = True,
                     log=lambda *_: None) -> dict:
    """Construit `parcel_cosia_couverture` depuis le lot CoSIA extrait. `tiles` : sous-liste (test).
    ⚠ appels lourds. Commit APRÈS CHAQUE TUILE (reprise possible)."""
    ensure_table(session)
    from .cosia import SOURCE_MILLESIME
    if tiles is None:
        d = Path(extract_dir) if extract_dir else _default_extract_dir()
        tiles = sorted(glob.glob(str(d / "*.gpkg")))
    if not tiles:
        raise FileNotFoundError("Aucune tuile .gpkg CoSIA")
    if purge:
        session.execute(text(f"TRUNCATE {TABLE}"))
        session.commit()
    total_poly = 0
    t0 = time.time()
    for i, gpkg in enumerate(tiles, 1):
        n = _charger_staging(session, gpkg)
        touches = _agreger_tuile(session, SOURCE_MILLESIME)
        session.commit()
        total_poly += n
        log(f"cosia-couv [{i}/{len(tiles)}] {Path(gpkg).name} : {n} polys, "
            f"{touches} couples (cumul {total_poly} polys, {time.time()-t0:.0f}s)")
    couples = session.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar()
    classes = session.execute(text(f"SELECT count(DISTINCT classe) FROM {TABLE}")).scalar()
    return {"polys": total_poly, "couples": int(couples or 0), "classes": int(classes or 0),
            "tiles": len(tiles), "secondes": round(time.time() - t0)}


# ── Couche Piscines (polygones individuels, mappables + rattachés parcelle/commune) ──────────────
PISCINE_KIND = "piscine_cosia"

_INS_PISCINE = text(
    """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id)
       VALUES (:k, 'Piscine', NULL,
               ST_Force2D(ST_MakeValid(ST_Transform(ST_GeomFromWKB(:wkb, 2975), 4326))),
               CAST(:a AS jsonb), :sid)""")


def build_cosia_piscines(session: Session, extract_dir: str | Path | None = None,
                         tiles: list[str] | None = None, log=lambda *_: None) -> dict:
    """SOURCES-4 lot 2 — matérialise CHAQUE piscine détectée par CoSIA (classe « Piscine ») en
    polygone dans `spatial_layers kind='piscine_cosia'`, avec sa surface (m²), la commune (point sur
    surface dans les frontières IGN) et la parcelle qui la contient. Croisable propriétaire (piste
    piscines non déclarées). Idempotent (purge du kind). Détection IA 20 cm 2025 — pas un cadastre."""
    import glob as _glob
    import json as _json
    from .cosia import _ensure_source, SOURCE_MILLESIME, _repo_root
    if tiles is None:
        d = Path(extract_dir) if extract_dir else _default_extract_dir()
        tiles = sorted(_glob.glob(str(d / "*.gpkg")))
    if not tiles:
        raise FileNotFoundError("Aucune tuile .gpkg CoSIA")
    sid = _ensure_source(session)
    session.execute(text("DELETE FROM spatial_layers WHERE kind = :k"), {"k": PISCINE_KIND})
    attrs = _json.dumps({"classe": "Piscine", "source_millesime": SOURCE_MILLESIME})
    total = 0
    for i, gpkg in enumerate(tiles, 1):
        db = sqlite3.connect(gpkg)
        try:
            tbl = db.execute("SELECT table_name FROM gpkg_contents "
                             "WHERE data_type='features'").fetchone()[0]
            cur = db.execute(f"SELECT geom FROM \"{tbl}\" WHERE classe = 'Piscine'")
            params, n = [], 0
            for (blob,) in cur:
                wkb = _gpkg_to_wkb(blob)
                if wkb is None:
                    continue
                params.append({"k": PISCINE_KIND, "wkb": wkb, "a": attrs, "sid": sid})
                if len(params) >= 2000:
                    session.execute(_INS_PISCINE, params); n += len(params); params.clear()
            if params:
                session.execute(_INS_PISCINE, params); n += len(params)
            total += n
            log(f"piscines [{i}/{len(tiles)}] {Path(gpkg).name} : {n} (cumul {total})")
        finally:
            db.close()
    session.flush()
    # surface m² (2975) dans les attrs, tag commune (frontières IGN), rattachement parcelle.
    session.execute(text(
        "UPDATE spatial_layers SET attrs = attrs || jsonb_build_object('surface_m2', "
        "round(ST_Area(geom_2975)::numeric, 1)) WHERE kind = :k"), {"k": PISCINE_KIND})
    geo = _json.loads((_repo_root() / "frontend" / "public" / "communes974.geojson").read_text("utf-8"))
    session.execute(text("CREATE TEMP TABLE _cb (nom text, g geometry(Geometry,2975)) ON COMMIT DROP"))
    for feat in geo["features"]:
        if feat["properties"].get("nom"):
            session.execute(text(
                "INSERT INTO _cb (nom, g) VALUES (:nom, "
                "ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 2975))"),
                {"nom": feat["properties"]["nom"], "g": _json.dumps(feat["geometry"])})
    session.execute(text("CREATE INDEX ON _cb USING gist (g)"))
    tag = session.execute(text(
        "UPDATE spatial_layers b SET commune = cb.nom FROM _cb cb WHERE b.kind = :k "
        "AND ST_Contains(cb.g, ST_PointOnSurface(b.geom_2975))"), {"k": PISCINE_KIND}).rowcount
    # rattachement parcelle : la parcelle qui contient le centre de la piscine (idu dans attrs).
    ratt = session.execute(text(
        "UPDATE spatial_layers b SET attrs = b.attrs || jsonb_build_object('parcelle_idu', p.idu) "
        "FROM parcels p WHERE b.kind = :k "
        "AND p.geom_2975 && b.geom_2975 AND ST_Contains(p.geom_2975, ST_PointOnSurface(b.geom_2975))"),
        {"k": PISCINE_KIND}).rowcount
    session.commit()
    return {"piscines": total, "communes_taguees": tag, "rattachees_parcelle": ratt,
            "source_millesime": SOURCE_MILLESIME}
