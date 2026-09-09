"""RECETTE-7 lot D (D1) — INGESTION du RGE ALTI 5 m (MNT, altitude) en PostGIS raster.

Vic a tranché : le RGE ALTI ouvre la vue mer, l'exposition et l'altitude. Le raster de PENTE
(`rgealti_pente_5m`, dérivé) était déjà en base ; il manquait le MNT d'ALTITUDE, indispensable au
viewshed (la pente ne suffit pas). On l'ingère par la MÊME source et la MÊME maille que la pente :
WMS-raster de la Géoplateforme IGN, couche `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`, format
`image/geotiff` (Float32, altitude en mètres, NoData −99999 = mer/hors emprise), CRS EPSG:2975.

VÉRIFIÉ le 09/09/2026 (RECETTE-7 lot D) : un GetMap 2 km × 2 km (400×400 px à 5 m) renvoie bien un
Float32 d'altitude (min ≈ 0, max ≈ 185 m sur la côte de Saint-Pierre) — la chaîne fetch → GeoTIFF →
gdal_viewshed tourne (0,46 s / fenêtre).

PIÈGE SRID (rappelé au mandat) : le raster est en **2975**, `parcels.geom` en **4326**. On ingère et
on interroge le raster en 2975 (les parcelles ont `geom_2975`) ; un `ST_Intersects` naïf 2975↔4326 a
déjà tourné 32 minutes pour rien. Le raster porte donc SRID 2975, comme `rgealti_pente_5m`.

REPRISE : l'ingestion est tuilée et REJOUABLE — `mnt_tiles.statut` (attendu|fait|erreur) est le point
de reprise ; on ne re-télécharge JAMAIS une tuile `fait`. `--force` re-télécharge tout.

STATUT (RECETTE-7) : le CODE est écrit et la chaîne prouvée sur une fenêtre ; l'ingestion de l'ÎLE
(2 793 tuiles, comme la pente) n'est PAS lancée dans la session d'audit (heures de téléchargement +
calcul). Elle se lance par `labuse ingest-rgealti-mnt` (à câbler au CLI) ; on borne d'abord aux
communes littorales (lot D4 : une commune, 10 témoins, validation Vic AVANT l'île).
"""
from __future__ import annotations

import io
import logging
import time

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.rgealti_mnt")

WMS = "https://data.geopf.fr/wms-r/wms"
COUCHE = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
SRID = 2975
RES_M = 5.0                     # 5 m (RGE ALTI)
TUILE_M = 2000.0               # côté d'une tuile d'ingestion (400 px à 5 m) — comme la fenêtre prouvée
NODATA = -99999.0

DDL = """
CREATE TABLE IF NOT EXISTS rgealti_mnt_5m (
  rid serial PRIMARY KEY,
  rast raster
);
CREATE TABLE IF NOT EXISTS mnt_tiles (
  id serial PRIMARY KEY,
  -- NB : jamais `xmin`/`xmax` (colonnes SYSTÈME Postgres) → x0/y0/x1/y1.
  x0 double precision NOT NULL, y0 double precision NOT NULL,
  x1 double precision NOT NULL, y1 double precision NOT NULL,
  statut varchar(12) NOT NULL DEFAULT 'attendu',   -- attendu | fait | erreur
  message text, updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (x0, y0)
);
"""


def ensure(db: Session) -> None:
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))


def _emprise_ile(db: Session) -> tuple[float, float, float, float]:
    """L'emprise 2975 à couvrir = celle des parcelles (jamais plus large que ce qu'on sert)."""
    r = db.execute(text(
        "SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM "
        "(SELECT ST_Extent(geom_2975) e FROM parcels) t")).first()
    return float(r[0]), float(r[1]), float(r[2]), float(r[3])


def planifier(db: Session, *, communes: list[str] | None = None) -> int:
    """Découpe l'emprise (île, ou communes littorales bornées — lot D4) en tuilage 2 km et remplit
    `mnt_tiles` (idempotent). Rend le nombre de tuiles ATTENDUES."""
    ensure(db)
    if communes:
        r = db.execute(text(
            "SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM "
            "(SELECT ST_Extent(geom_2975) e FROM parcels WHERE commune = ANY(:c)) t"),
            {"c": communes}).first()
        x0, y0, x1, y1 = (float(r[0]), float(r[1]), float(r[2]), float(r[3]))
    else:
        x0, y0, x1, y1 = _emprise_ile(db)
    n = 0
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            db.execute(text(
                "INSERT INTO mnt_tiles (x0, y0, x1, y1) VALUES (:a,:b,:c,:d) "
                "ON CONFLICT (x0, y0) DO NOTHING"),
                {"a": x, "b": y, "c": x + TUILE_M, "d": y + TUILE_M})
            n += 1
            x += TUILE_M
        y += TUILE_M
    return n


def _fetch_tuile(xmin: float, ymin: float, xmax: float, ymax: float) -> bytes:
    """Un GetMap GeoTIFF Float32 (altitude, m) pour la tuile — la chaîne prouvée en lot D."""
    w = h = int(round((xmax - xmin) / RES_M))
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": COUCHE,
        "CRS": f"EPSG:{SRID}", "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
        "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/geotiff", "STYLES": "",
    }
    resp = httpx.get(WMS, params=params, timeout=60.0)
    resp.raise_for_status()
    return resp.content


def _ingerer_tuile(db: Session, tif: bytes) -> None:
    """GeoTIFF → PostGIS raster (SRID 2975). `ST_FromGDALRaster` lit le GDAL en mémoire — mais
    PostGIS RESTREINT les drivers GDAL par défaut (`postgis.gdal_enabled_drivers` = 'DISABLE_ALL',
    sécurité) : sans autoriser GTiff, on obtient « Could not open bytea with GDAL ». On l'autorise
    au niveau session (jamais global — pas d'ALTER DATABASE)."""
    db.execute(text("SET LOCAL postgis.gdal_enabled_drivers = 'GTiff'"))
    db.execute(text(
        "INSERT INTO rgealti_mnt_5m (rast) VALUES (ST_SetSRID(ST_FromGDALRaster(:b), :srid))"),
        {"b": tif, "srid": SRID})


def ingerer(db: Session, *, force: bool = False, limite: int | None = None) -> dict:
    """Télécharge et ingère les tuiles ATTENDUES (ou toutes si `force`). Rejouable : reprend où le
    `statut` s'est arrêté. Rend {faites, erreurs, duree_s}."""
    ensure(db)
    where = "" if force else "WHERE statut <> 'fait'"
    rows = db.execute(text(
        f"SELECT id, x0, y0, x1, y1 FROM mnt_tiles {where} ORDER BY id"  # noqa: S608
        + (f" LIMIT {int(limite)}" if limite else ""))).all()
    t0 = time.monotonic()
    faites = erreurs = 0
    for tid, x0, y0, x1, y1 in rows:
        try:
            tif = _fetch_tuile(float(x0), float(y0), float(x1), float(y1))
            _ingerer_tuile(db, tif)
            db.execute(text("UPDATE mnt_tiles SET statut='fait', message=NULL, updated_at=now() WHERE id=:i"),
                       {"i": tid})
            faites += 1
        except Exception as exc:  # noqa: BLE001 — une tuile qui échoue est ÉTIQUETÉE, jamais muette
            db.rollback()
            db.execute(text("UPDATE mnt_tiles SET statut='erreur', message=:m, updated_at=now() WHERE id=:i"),
                       {"i": tid, "m": str(exc)[:400]})
            erreurs += 1
        db.commit()
    return {"faites": faites, "erreurs": erreurs, "duree_s": round(time.monotonic() - t0, 1)}
