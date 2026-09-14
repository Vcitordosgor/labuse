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
    """Charge TOUTES les classes d'une tuile GPKG dans la table temporaire `_cosia_tile`
    (classe text, g geometry(Geometry,2975)). Renvoie le nombre de polygones chargés."""
    session.execute(text("DROP TABLE IF EXISTS _cosia_tile"))
    session.execute(text(
        "CREATE TEMP TABLE _cosia_tile (classe text, g geometry(Geometry, 2975))"))
    ins = text("INSERT INTO _cosia_tile (classe, g) VALUES "
               "(:c, ST_MakeValid(ST_GeomFromWKB(:wkb, 2975)))")
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
