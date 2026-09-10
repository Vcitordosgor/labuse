"""RECETTE-11 A1 — ingestion LiDAR HD par DALLES pour TOUTE l'île (Saint-Denis compris).

Une seule méthode pour les 24 communes. Là où RECETTE-10 T9 mesurait parcelle par parcelle par
requête WMS distante (~0,5 s/parcelle → ~38 h l'île, WMS martelé), on télécharge la DALLE LiDAR HD
1 km une seule fois, on la lit EN LOCAL, on mesure toutes les parcelles bâties qu'elle couvre, puis
on la SUPPRIME. Plus aucune requête par parcelle.

La donnée : par dalle 1 km à 0,5 m (EPSG:2975 / RGR92 UTM40S), on télécharge les MÊMES couches que la
méthode par parcelle validée (RECETTE-8 W23) — MNS LiDAR HD (`…HIGHRES.MNS`) et MNT
(`…HIGHRES`) — on les soustrait, et p99 de la hauteur sur l'emprise = faîtage, p25 = égout. Ce choix
est délibéré : lire les mêmes couches garantit que la méthode par dalles REDONNE les valeurs déjà
servies (vérifié : 50/50 bâtiments de Saint-Denis à ±0,5 m, écart médian 0,10 m ; le reliquat vient
seulement de la grille native vs la grille recentrée du fetch par parcelle). Le produit MNH d'IGN
(hauteur toute prête, 1 seul téléchargement) DIVERGE de la méthode servie sur terrain pentu
(médian 0,4 m, extrêmes > 20 m) : rejeté pour ne pas changer les valeurs sous les pieds du client.

La grille des dalles (emprise + DATES DE SURVOL) vient du service IGN `IGNF_LIDAR-HD_METADONNEE:metadata`
(WFS Géoplateforme) — la date de survol est LUE, jamais supposée (`date_debut_acquisition` /
`date_fin_acquisition` par dalle ; sur la Réunion, mission unique 23LHDREUNION, août–septembre 2023).

Reprise : `lidar_dalle_grille` porte l'état par dalle (`fait_le`) ; relancer SAUTE les dalles finies.
Les mesures s'écrivent dans `batiment_hauteur_lidar` (idempotent `ON CONFLICT (idu)`), commune par
commune au fil des dalles. Un `pg_dump` de cette seule table suffit à porter les hauteurs sur le VPS.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET

log = logging.getLogger("labuse.hauteur_lidar_dalles")

WFS = "https://data.geopf.fr/wfs/ows"
TYPENAME = "IGNF_LIDAR-HD_METADONNEE:metadata"
# emprise Réunion (WGS84, axe lat,lon pour EPSG:4326 sur ce WFS)
BBOX_REUNION = "-21.40,55.20,-20.80,55.85"
# LES MÊMES couches que la méthode par parcelle (hauteur_lidar) : reproduction garantie.
WMS = "https://data.geopf.fr/wms-r/wms"
LAYER_MNS = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS"   # surface (bâti compris) — LiDAR HD
LAYER_MNT = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"       # sol
SRID = 2975
RES = 0.5
PX = 2000  # 1 km / 0,5 m
MARGE_M = 6.0
P_FAITAGE = 99
P_EGOUT = 25


# ── la grille des dalles (emprise + dates de survol + URL MNH) ───────────────────────────────────
_DDL_GRILLE = """
CREATE TABLE IF NOT EXISTS lidar_dalle_grille (
  cle             text PRIMARY KEY,
  x0 double precision, y0 double precision, x1 double precision, y1 double precision,
  code_mission    text,
  date_debut      date,
  date_fin        date,
  url_mnh         text,
  n_parcelles     int,
  n_mesurees      int,
  fait_le         timestamptz
);
"""


def ensure_grille(db) -> None:
    from sqlalchemy import text
    db.execute(text(_DDL_GRILLE))


def ensure_colonnes_survol(db) -> None:
    """RECETTE-11 A2/A3 — la mesure porte la date de survol de sa dalle (jamais supposée)."""
    from sqlalchemy import text
    from labuse.faisabilite.hauteur_lidar import ensure_table
    ensure_table(db)
    for col, typ in (("date_debut_survol", "date"), ("date_fin_survol", "date"),
                     ("code_mission", "text"), ("methode", "text")):
        db.execute(text(f"ALTER TABLE batiment_hauteur_lidar ADD COLUMN IF NOT EXISTS {col} {typ}"))


def _parse_bbox_2975(url: str) -> tuple[float, float, float, float] | None:
    """La dalle porte SON emprise EPSG:2975 dans le paramètre BBOX de l'URL WMS (grille 1 km IGN)."""
    m = re.search(r"BBOX=([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)", url)
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))


def _wfs_dalles(client) -> list[dict]:
    """Toutes les dalles LiDAR HD couvrant la Réunion, avec emprise 2975, dates de survol et URL MNH."""
    dalles: list[dict] = []
    start = 0
    while True:
        params = {
            "SERVICE": "WFS", "REQUEST": "GetFeature", "VERSION": "2.0.0",
            "TYPENAMES": TYPENAME, "SRSNAME": "EPSG:4326",
            "OUTPUTFORMAT": "application/json", "COUNT": "5000", "STARTINDEX": str(start),
            "PROPERTYNAME": "coordonnees_nw,code_mission,date_debut_acquisition,"
                            "date_fin_acquisition,url_mnh",
            "BBOX": BBOX_REUNION,
        }
        r = client.get(WFS, params=params, timeout=180.0)
        r.raise_for_status()
        feats = r.json().get("features", [])
        for f in feats:
            p = f.get("properties", {})
            url = p.get("url_mnh") or ""
            bbox = _parse_bbox_2975(url)
            if not bbox:
                continue
            xmin, ymin, xmax, ymax = bbox
            cle = p.get("coordonnees_nw") or f"{int(xmin/1000)}-{int(ymax/1000)}"
            dalles.append({
                "cle": cle, "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
                "code_mission": p.get("code_mission"),
                "date_debut": (p.get("date_debut_acquisition") or "")[:10] or None,
                "date_fin": (p.get("date_fin_acquisition") or "")[:10] or None,
                "url_mnh": url,
            })
        if len(feats) < 5000:
            break
        start += 5000
    return dalles


def charger_grille(db, client, refresh: bool = False) -> int:
    """Peuple `lidar_dalle_grille` depuis le WFS IGN (idempotent). Rend le nombre de dalles connues."""
    from sqlalchemy import text
    ensure_grille(db)
    n = db.execute(text("SELECT count(*) FROM lidar_dalle_grille")).scalar() or 0
    if n and not refresh:
        return int(n)
    dalles = _wfs_dalles(client)
    for d in dalles:
        db.execute(text(
            "INSERT INTO lidar_dalle_grille (cle, x0, y0, x1, y1, code_mission, date_debut, "
            "date_fin, url_mnh) VALUES (:cle,:x0,:y0,:x1,:y1,:cm,:dd,:df,:u) "
            "ON CONFLICT (cle) DO UPDATE SET url_mnh=EXCLUDED.url_mnh, date_debut=EXCLUDED.date_debut, "
            "date_fin=EXCLUDED.date_fin, code_mission=EXCLUDED.code_mission"),
            {"cle": d["cle"], "x0": d["xmin"], "y0": d["ymin"], "x1": d["xmax"],
             "y1": d["ymax"], "cm": d["code_mission"], "dd": d["date_debut"],
             "df": d["date_fin"], "u": d["url_mnh"]})
    db.commit()
    return db.execute(text("SELECT count(*) FROM lidar_dalle_grille")).scalar() or 0


# ── mesure d'une dalle ───────────────────────────────────────────────────────────────────────────
def parcelles_de_dalle(db, xmin, ymin, xmax, ymax) -> list[dict]:
    """Parcelles bâties AFFECTÉES à cette dalle : celles dont le CENTROÏDE du bâtiment principal (le
    plus grand intersectant la parcelle) tombe dans l'emprise de la dalle → chaque parcelle mesurée
    par UNE seule dalle (pas de double comptage aux bords)."""
    from sqlalchemy import text
    sql = text(
        """WITH box AS (SELECT ST_MakeEnvelope(:xmin,:ymin,:xmax,:ymax, 2975) g)
           SELECT p.idu,
                  ST_AsGeoJSON(pb.geom) gj,
                  NULLIF(pb.attrs->>'hauteur','')::float h_bdtopo,
                  ST_XMin(pb.geom) x0, ST_YMin(pb.geom) y0,
                  ST_XMax(pb.geom) x1, ST_YMax(pb.geom) y1
           FROM parcels p
           JOIN LATERAL (
                SELECT b.geom_2975 AS geom, b.attrs
                FROM spatial_layers b
                WHERE b.kind='batiment' AND b.geom_2975 IS NOT NULL
                  AND ST_Intersects(b.geom_2975, p.geom_2975)
                ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1) pb ON true
           WHERE p.geom_2975 && (SELECT g FROM box)
             AND ST_Contains((SELECT g FROM box), ST_Centroid(pb.geom))""")
    return [dict(r) for r in db.execute(
        sql, {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax}).mappings().all()]


def _url_dalle(layer: str, x0, y0, x1, y1) -> str:
    return (f"{WMS}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={layer}&CRS=EPSG:{SRID}"
            f"&BBOX={x0},{y0},{x1},{y1}&WIDTH={PX}&HEIGHT={PX}&FORMAT=image/geotiff&STYLES=")


def _telecharger_tif(client, url: str) -> str:
    """Télécharge un GeoTIFF de dalle dans un fichier temporaire. Rend le chemin (à supprimer)."""
    r = client.get(url, timeout=180.0)
    r.raise_for_status()
    fd, path = tempfile.mkstemp(suffix=".tif", prefix="lhd_")
    os.write(fd, r.content)
    os.close(fd)
    return path


def hauteur_dalle(client, x0, y0, x1, y1):
    """Télécharge MNS + MNT de la dalle EN LOCAL, rend (hauteur=MNS−MNT, transform), et SUPPRIME les
    deux fichiers. NaN là où l'une des deux couches est nodata."""
    import numpy as np
    import rasterio
    p_s = _telecharger_tif(client, _url_dalle(LAYER_MNS, x0, y0, x1, y1))
    try:
        p_t = _telecharger_tif(client, _url_dalle(LAYER_MNT, x0, y0, x1, y1))
        try:
            with rasterio.open(p_s) as ds:
                mns = ds.read(1).astype("float64"); transform = ds.transform; nod_s = ds.nodata
            with rasterio.open(p_t) as dt:
                mnt = dt.read(1).astype("float64"); nod_t = dt.nodata
        finally:
            try:
                os.remove(p_t)
            except OSError:
                pass
    finally:
        try:
            os.remove(p_s)
        except OSError:
            pass
    haut = mns - mnt
    bad = ~np.isfinite(haut)
    if nod_s is not None:
        bad |= mns == nod_s
    if nod_t is not None:
        bad |= mnt == nod_t
    haut[bad] = np.nan
    return haut, transform


def _hauteurs_locales(mnh, transform, nodata, geojson: str, bbox: tuple) -> dict | None:
    """Faîtage (p99) / égout (p25) sur l'emprise du bâtiment, lus DANS le tableau MNH de la dalle
    (fenêtre locale + marge, jamais de fetch). None si < 5 cellules valides sous le contour."""
    import numpy as np
    from rasterio.features import geometry_mask
    from rasterio.windows import from_bounds
    from rasterio.transform import array_bounds
    x0, y0, x1, y1 = bbox
    win = from_bounds(x0 - MARGE_M, y0 - MARGE_M, x1 + MARGE_M, y1 + MARGE_M, transform)
    r0 = max(0, int(np.floor(win.row_off)))
    c0 = max(0, int(np.floor(win.col_off)))
    r1 = min(mnh.shape[0], int(np.ceil(win.row_off + win.height)))
    c1 = min(mnh.shape[1], int(np.ceil(win.col_off + win.width)))
    if r1 <= r0 or c1 <= c0:
        return None
    sub = mnh[r0:r1, c0:c1]
    sub_tr = transform * transform.identity().translation(c0, r0)
    mask = geometry_mask([json.loads(geojson)], out_shape=sub.shape, transform=sub_tr, invert=True)
    ok = mask & np.isfinite(sub)
    if nodata is not None:
        ok &= sub != nodata
    vals = sub[ok]
    if vals.size < 5:
        return None
    return {"faitage_m": round(float(np.percentile(vals, P_FAITAGE)), 1),
            "egout_m": round(float(np.percentile(vals, P_EGOUT)), 1),
            "n_cellules": int(vals.size)}


def mesurer_dalle(db, dalle: dict, client) -> dict:
    """Télécharge la dalle (MNS+MNT), mesure toutes ses parcelles bâties, écrit dans
    `batiment_hauteur_lidar` (avec la date de survol de la dalle), SUPPRIME les fichiers.
    Rend {n_parcelles, ok, vide}."""
    from sqlalchemy import text
    parcelles = parcelles_de_dalle(db, dalle["x0"], dalle["y0"], dalle["x1"], dalle["y1"])
    if not parcelles:
        return {"n_parcelles": 0, "ok": 0, "vide": 0}
    haut, transform = hauteur_dalle(client, dalle["x0"], dalle["y0"], dalle["x1"], dalle["y1"])
    ok = vide = 0
    for r in parcelles:
        h = _hauteurs_locales(haut, transform, None, r["gj"],
                              (r["x0"], r["y0"], r["x1"], r["y1"]))
        if h is None:
            vide += 1
            continue
        hb = r["h_bdtopo"]
        db.execute(text(
            "INSERT INTO batiment_hauteur_lidar (idu, faitage_m, egout_m, hauteur_bdtopo_m, "
            "ecart_faitage_bdtopo_m, n_cellules, mesure_le, date_debut_survol, date_fin_survol, "
            "code_mission, methode) VALUES (:i,:f,:e,:b,:ec,:n, now(), :dd, :df, :cm, 'dalle') "
            "ON CONFLICT (idu) DO UPDATE SET faitage_m=EXCLUDED.faitage_m, egout_m=EXCLUDED.egout_m, "
            "hauteur_bdtopo_m=EXCLUDED.hauteur_bdtopo_m, "
            "ecart_faitage_bdtopo_m=EXCLUDED.ecart_faitage_bdtopo_m, n_cellules=EXCLUDED.n_cellules, "
            "mesure_le=now(), date_debut_survol=EXCLUDED.date_debut_survol, "
            "date_fin_survol=EXCLUDED.date_fin_survol, code_mission=EXCLUDED.code_mission, "
            "methode='dalle'"),
            {"i": r["idu"], "f": h["faitage_m"], "e": h["egout_m"],
             "b": (round(float(hb), 1) if hb is not None else None),
             "ec": (round(h["faitage_m"] - float(hb), 1) if hb is not None else None),
             "n": h["n_cellules"], "dd": dalle["date_debut"], "df": dalle["date_fin"],
             "cm": dalle["code_mission"]})
        ok += 1
    return {"n_parcelles": len(parcelles), "ok": ok, "vide": vide}


def backfill_dates(db) -> int:
    """RECETTE-11 A3 (garantie non-merge) — pose la date de survol sur les mesures déjà présentes
    (méthode par parcelle de RECETTE-10) sans la dalle : jointure spatiale au centroïde du bâtiment
    principal contre la grille. Aucune mesure LiDAR ne peut s'afficher sans date."""
    from sqlalchemy import text
    ensure_grille(db)
    ensure_colonnes_survol(db)
    res = db.execute(text(
        """WITH cible AS (
             SELECT hl.idu, ST_Centroid(pb.geom) c
             FROM batiment_hauteur_lidar hl
             JOIN parcels p ON p.idu = hl.idu
             JOIN LATERAL (
                  SELECT b.geom_2975 AS geom FROM spatial_layers b
                  WHERE b.kind='batiment' AND b.geom_2975 IS NOT NULL
                    AND ST_Intersects(b.geom_2975, p.geom_2975)
                  ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1) pb ON true
             WHERE hl.date_fin_survol IS NULL)
           UPDATE batiment_hauteur_lidar hl
           SET date_debut_survol=g.date_debut, date_fin_survol=g.date_fin, code_mission=g.code_mission
           FROM cible, lidar_dalle_grille g
           WHERE hl.idu = cible.idu
             AND ST_Contains(ST_MakeEnvelope(g.x0,g.y0,g.x1,g.y1,2975), cible.c)"""))
    db.commit()
    return res.rowcount or 0
