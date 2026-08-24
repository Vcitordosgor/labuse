"""Ingestion CoSIA (Couverture du Sol par IA, IGN) — classe « Bâtiment ».

SOURCE OFFICIELLE : IGN Géoplateforme, CoSIA v1.0, département D974 La Réunion,
millésime **2025** (PVA juil.-août 2025, 20 cm). VECTEUR GPKG (polygones), livré en 37
tuiles, CRS **EPSG:2975 (RGR92 / UTM 40S)** — identique à `geom_2975` (aucune reprojection
de système, juste 2975→4326 pour la colonne `geom`). Licence Ouverte 2.0 (Etalab).
URL : data.geopf.fr/telechargement/download/COSIA/COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01/…

Matérialise les footprints de la classe « Bâtiment » (classe 1 des 15) dans
`spatial_layers kind='batiment_cosia'` (patron `dispositifs.py` / `layers_ingest`).
Idempotent (purge par kind avant réinsertion). `geom` en 4326 (le trigger pose `geom_2975`).
`commune` taguée par jointure spatiale aux frontières IGN (`communes974.geojson`).
Source + millésime portés au catalogue `data_sources` (radar de fraîcheur : cf. `fraicheur.py`).

Lecture GPKG en PUR PYTHON (`sqlite3`) : un GPKG = une base SQLite ; la géométrie est un BLOB
« GP » (en-tête GeoPackage) suivi du WKB standard. On strippe l'en-tête → WKB → `ST_GeomFromWKB`.
Aucune dépendance GDAL/fiona (la maison n'en a pas ; py7zr suffit pour l'archive .7z).

NB doublon : `p_model_bati_cosia` (emprise CoSIA PAR PARCELLE, sans géométrie) porte la MÊME
donnée amont dérivée à la parcelle. Cette ingestion-ci est la source GÉOMÉTRIQUE canonique ;
la redondance est documentée (docs/mandats/PAU_COSIA_PHASE2.md), remplacement hors périmètre PAU.
"""
from __future__ import annotations

import glob
import json
import sqlite3
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

KIND = "batiment_cosia"
CLASSE = "Bâtiment"
SOURCE_NAME = "CoSIA (couverture du sol IA, IGN)"
SOURCE_MILLESIME = "CoSIA 2025 (PVA juil.-août 2025, 20 cm)"
SOURCE_HORIZON = "2025-01-01"          # editionDate IGN du lot D974 (fait amont daté)
DOC_URL = "https://geoservices.ign.fr/cosia"
DL_URL = ("https://data.geopf.fr/telechargement/download/COSIA/"
          "COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01/"
          "COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01.7z")
LEGAL = ("Licence Ouverte 2.0 (Etalab) — attribution : « Source : IGN — CoSIA "
         "(Couverture du Sol par IA), D974 millésime 2025 ».")

# GPKG BLOB : magic 'GP'(2) + version(1) + flags(1) + srs_id(4) + envelope(E) + WKB.
# E = (flags>>1)&0x07 : 0→0, 1→32, 2/3→48, 4→64 octets d'enveloppe.
_ENV_BYTES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


def _gpkg_to_wkb(blob: bytes | None) -> bytes | None:
    """Strippe l'en-tête GeoPackage d'un BLOB géométrie → WKB standard (ou None si vide/invalide)."""
    if not blob or len(blob) < 8 or blob[:2] != b"GP":
        return None
    env = (blob[3] >> 1) & 0x07
    n = _ENV_BYTES.get(env)
    if n is None:
        return None
    return bytes(blob[8 + n:])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_extract_dir() -> Path:
    base = _repo_root() / "data" / "cosia" / "extract"
    subs = sorted(base.glob("COSIA_*"))
    if not subs:
        raise FileNotFoundError(
            f"Aucun lot CoSIA extrait sous {base}. Télécharger + extraire d'abord "
            "(cf. docs/mandats/PAU_COSIA_PHASE2_BLOCAGE.md).")
    return subs[-1]


def _ensure_source(session: Session) -> int:
    """Upsert de la ligne catalogue `data_sources` (idempotent) → renvoie son id."""
    # FIX-SOURCES S2 — le statut PASSE par la garde d'enum (minuscule validée) : plus jamais un
    # 'CONNECTE' brut qui sortait CoSIA de la vitrine. `reliability_level` est posé (était NULL) :
    # source servie (réconciliation bâti BD TOPO/CoSIA) → vérifiée, comme le seed le déclare.
    from ..sources_catalog import normalize_status
    statut = normalize_status("connecte")
    row = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).first()
    if row is None:
        session.execute(text(
            """INSERT INTO data_sources (name, category, provider, access_type, status,
                   reliability_level, documentation_url, endpoint_url, source_millesime,
                   source_horizon_at, source_cadence, legal_notes, last_sync_at)
               VALUES (:n, 'occupation_sol', 'IGN / Géoplateforme', 'téléchargement/GPKG',
                   :st, 'verifie', :doc, :dl, :mil, CAST(:hz AS date), 'pluriannuelle', :legal, now())"""),
            {"n": SOURCE_NAME, "st": statut, "doc": DOC_URL, "dl": DL_URL, "mil": SOURCE_MILLESIME,
             "hz": SOURCE_HORIZON, "legal": LEGAL})
        row = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                              {"n": SOURCE_NAME}).first()
    else:
        session.execute(text(
            """UPDATE data_sources SET status = :st, source_millesime = :mil,
                   reliability_level = COALESCE(reliability_level, 'verifie'),
                   source_horizon_at = CAST(:hz AS date), last_sync_at = now(),
                   documentation_url = :doc, endpoint_url = :dl, legal_notes = :legal
               WHERE name = :n"""),
            {"n": SOURCE_NAME, "st": statut, "mil": SOURCE_MILLESIME, "hz": SOURCE_HORIZON,
             "doc": DOC_URL, "dl": DL_URL, "legal": LEGAL})
    return int(row[0])


_INS = text(
    """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id)
       VALUES ('batiment_cosia', 'Bâtiment', NULL,
               ST_Force2D(ST_MakeValid(ST_Transform(ST_GeomFromWKB(:wkb, 2975), 4326))),
               CAST(:a AS jsonb), :sid)""")


def _insert_tile(session: Session, gpkg: str, sid: int, attrs_json: str,
                 batch: int = 3000) -> int:
    """Lit une tuile GPKG (classe Bâtiment) et insère ses polygones. Renvoie le compte."""
    db = sqlite3.connect(gpkg)
    try:
        tbl = db.execute("SELECT table_name FROM gpkg_contents "
                         "WHERE data_type='features'").fetchone()[0]
        cur = db.execute(f'SELECT geom FROM "{tbl}" WHERE classe = ?', (CLASSE,))
        n = 0
        params: list[dict] = []
        for (blob,) in cur:
            wkb = _gpkg_to_wkb(blob)
            if wkb is None:
                continue
            params.append({"wkb": wkb, "a": attrs_json, "sid": sid})
            if len(params) >= batch:
                session.execute(_INS, params)
                n += len(params)
                params.clear()
        if params:
            session.execute(_INS, params)
            n += len(params)
        return n
    finally:
        db.close()


def _tag_commune(session: Session) -> int:
    """Tague `commune` par point-sur-surface dans les frontières IGN (communes974.geojson).
    Le `nom` du geojson matche EXACTEMENT parcels.commune / les entrées RNU (build_pau lit ce
    nom). Renvoie le nombre de polygones tagués."""
    geo = json.loads((_repo_root() / "frontend" / "public" / "communes974.geojson")
                     .read_text("utf-8"))
    session.execute(text(
        "CREATE TEMP TABLE _cb (nom text, g geometry(Geometry,2975)) ON COMMIT DROP"))
    for feat in geo["features"]:
        nom = feat["properties"].get("nom")
        if not nom:
            continue
        session.execute(text(
            "INSERT INTO _cb (nom, g) VALUES "
            "(:nom, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 2975))"),
            {"nom": nom, "g": json.dumps(feat["geometry"])})
    session.execute(text("CREATE INDEX ON _cb USING gist (g)"))
    return session.execute(text(
        """UPDATE spatial_layers b SET commune = cb.nom
           FROM _cb cb
           WHERE b.kind = 'batiment_cosia'
             AND ST_Contains(cb.g, ST_PointOnSurface(b.geom_2975))""")).rowcount


def build_cosia_batiment(session: Session, extract_dir: str | Path | None = None,
                         log=lambda *_: None) -> dict:
    """(Re)matérialise `spatial_layers kind='batiment_cosia'` depuis le lot CoSIA extrait.
    Idempotent. Renvoie {inserted, communes, tiles, source_millesime}."""
    d = Path(extract_dir) if extract_dir else _default_extract_dir()
    tiles = sorted(glob.glob(str(d / "*.gpkg")))
    if not tiles:
        raise FileNotFoundError(f"Aucune tuile .gpkg sous {d}")
    sid = _ensure_source(session)
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'batiment_cosia'"))
    attrs_json = json.dumps({"classe": CLASSE, "source_millesime": SOURCE_MILLESIME})
    total = 0
    for i, gpkg in enumerate(tiles, 1):
        n = _insert_tile(session, gpkg, sid, attrs_json)
        total += n
        log(f"cosia [{i}/{len(tiles)}] {Path(gpkg).name} : {n} bâtiments (cumul {total})")
    tagged = _tag_commune(session)
    log(f"cosia : {total} bâtiments insérés, {tagged} tagués commune")
    session.commit()
    return {"inserted": total, "communes_tagged": tagged, "tiles": len(tiles),
            "source_millesime": SOURCE_MILLESIME}
