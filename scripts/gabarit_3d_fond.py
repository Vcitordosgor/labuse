"""GABARIT-3D-1 — construction du FOND D'ALTITUDES 1 m local (COG unique).

Pilote (CDC GABARIT-3D-1, étape 1). Source retenue : LiDAR HD MNT 1 m de l'IGN
(`IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S`), tiré par WMS en
GeoTIFF Float32. Justification (mesurée, cf. reports/) :
  - le RGE ALTI « HIGHRES » en DÉRIVE (écart moyen −0,09 m, p95 1,56 m sur BZ1065) ;
  - le RGE ALTI standard est le vieux 5 m rééchantillonné (écart-type 5 m, max 26 m) ;
  - le 1 m IGN est EXACTEMENT la moyenne 2×2 du 0,50 m natif (écart 0,000).
Référentiel : RGR92 / UTM 40 Sud (EPSG:2975) en planimétrie, REUN89 (= IGN 1989) en
altitude. Le WMS tague la sortie EPSG:32740 (WGS84 UTM40S) alors que la grille est en
coordonnées 2975 (origine = BBOX demandée au pixel près) : on la RÉ-ÉTIQUETTE 2975
(écart RGR92↔WGS84 < 1 m en planimétrie à La Réunion, produit natif RGR92).

Étendue : VOISINAGES DES PARCELLES TÉMOINS (décision pilote, disque à 13 GiB partagé).
Chaque fenêtre = bbox cadastrale de la parcelle élargie de PAD_M mètres (couvre le
voisinage ~150 m et la marge des coupes). Le fond est un COG unique (sparse) couvrant
l'union des fenêtres ; les lacunes (hors emprise LiDAR) restent des lacunes (−9999).

Sorties :
  data/mnt1m/fond_1m.tif        COG Float32, EPSG:2975, nodata −9999, 1 m
  data/mnt1m/fond_1m.meta.json  métadonnées (source, pas, référentiel, acquisition,
                                 fenêtres, lacunes) — lues par l'endpoint de scène.

Usage :  ../labuse/.venv/bin/python scripts/gabarit_3d_fond.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import rasterio
from rasterio.transform import from_origin
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "mnt1m"
COG = OUT_DIR / "fond_1m.tif"
META = OUT_DIR / "fond_1m.meta.json"
TMP = Path("/tmp/gabarit3d_fond")

WMS = "https://data.geopf.fr/wms-r"
LAYER = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S"
NODATA = -9999.0
PAD_M = 190  # élargissement de la bbox parcelle (voisinage ~150 m + marge coupes)

# Parcelles témoins du pilote (CDC). La « pente synthétique » est générée hors-fond
# (contrôle a) ; elle n'a pas de fenêtre réelle.
TEMOINS = [
    ("plate", "97415000CY0196"),       # plaine de Saint-Paul (étang)
    ("cotier", "97413000CA0057"),       # littoral Saint-Leu (falaise / lacune océan)
    ("alt760", "97415000CM1658"),       # 36 Rue des Jacarandas, Saint-Paul (~760 m)
    ("bz1065", "97411000BZ1065"),       # Saint-Denis — talus (CDC)
]

DB = os.environ.get("LABUSE_DATABASE_URL",
                    "postgresql+psycopg://openclaw@localhost:5432/labuse")


def _bbox(con, idu: str):
    r = con.execute(text(
        "SELECT ST_XMin(geom_2975), ST_YMin(geom_2975), "
        "ST_XMax(geom_2975), ST_YMax(geom_2975), commune "
        "FROM parcels WHERE idu=:i"), {"i": idu}).first()
    if not r:
        raise SystemExit(f"parcelle inconnue : {idu}")
    return float(r[0]), float(r[1]), float(r[2]), float(r[3]), r[4]


def _missions(con, minx, miny, maxx, maxy):
    """Missions LiDAR HD couvrant la fenêtre (date d'acquisition, pour les métadonnées)."""
    rows = con.execute(text(
        "SELECT DISTINCT code_mission, min(date_debut), max(date_fin) "
        "FROM lidar_dalle_grille WHERE x0 < :x1 AND x1 > :x0 AND y0 < :y1 AND y1 > :y0 "
        "GROUP BY code_mission"),
        {"x0": minx, "y0": miny, "x1": maxx, "y1": maxy}).all()
    return [{"mission": m, "debut": str(d0), "fin": str(d1)} for m, d0, d1 in rows]


def _fetch_window(label, minx, miny, maxx, maxy, client) -> Path:
    """Tire la fenêtre (1 m) en GeoTIFF, nettoie (sentinelles→nodata), ré-étiquette 2975."""
    minx, miny = int(np.floor(minx)), int(np.floor(miny))
    maxx, maxy = int(np.ceil(maxx)), int(np.ceil(maxy))
    w, h = maxx - minx, maxy - miny
    raw = TMP / f"{label}_raw.tif"
    r = client.get(WMS, params={
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "STYLES": "",
        "CRS": "EPSG:2975", "FORMAT": "image/geotiff", "WIDTH": w, "HEIGHT": h,
        "BBOX": f"{minx},{miny},{maxx},{maxy}", "LAYERS": LAYER})
    r.raise_for_status()
    raw.write_bytes(r.content)
    with rasterio.open(raw) as ds:
        a = ds.read(1).astype("float32")
    # sentinelles IGN (service renvoie des très-négatifs hors emprise) → nodata unique
    a[(a <= -1000) | ~np.isfinite(a)] = NODATA
    clean = TMP / f"{label}_1m.tif"
    tr = from_origin(minx, maxy, 1.0, 1.0)  # origine coin haut-gauche, pas 1 m
    with rasterio.open(clean, "w", driver="GTiff", height=h, width=w, count=1,
                       dtype="float32", crs="EPSG:2975", transform=tr,
                       nodata=NODATA, compress="deflate") as dst:
        dst.write(a, 1)
    n_lac = int((a == NODATA).sum())
    return clean, {"label": label, "bbox": [minx, miny, maxx, maxy], "px": [w, h],
                   "n_pixels": w * h, "n_lacune": n_lac,
                   "alt_min": None if (a != NODATA).sum() == 0 else round(float(a[a != NODATA].min()), 2),
                   "alt_max": None if (a != NODATA).sum() == 0 else round(float(a[a != NODATA].max()), 2)}


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    eng = create_engine(DB)
    tiles, wins = [], []
    with eng.connect() as con, httpx.Client(timeout=90, headers={"User-Agent": "labuse-gabarit3d/1.0"}) as client:
        for label, idu in TEMOINS:
            x0, y0, x1, y1, commune = _bbox(con, idu)
            minx, miny, maxx, maxy = x0 - PAD_M, y0 - PAD_M, x1 + PAD_M, y1 + PAD_M
            miss = _missions(con, minx, miny, maxx, maxy)
            t0 = time.time()
            tile, info = _fetch_window(label, minx, miny, maxx, maxy, client)
            info.update({"idu": idu, "commune": commune, "missions": miss})
            tiles.append(tile)
            wins.append(info)
            print(f"  {label} {idu} {commune}: {info['px']} px, "
                  f"{info['n_lacune']} lacune, alt {info['alt_min']}–{info['alt_max']} m "
                  f"({time.time()-t0:.1f}s)")

    # COG unique (sparse) sur l'union des fenêtres
    vrt = TMP / "fond.vrt"
    subprocess.run(["gdalbuildvrt", "-srcnodata", str(NODATA), "-vrtnodata", str(NODATA),
                    str(vrt), *[str(t) for t in tiles]], check=True)
    subprocess.run(["gdal_translate", "-of", "COG",
                    "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=3",
                    "-co", "BLOCKSIZE=512", "-co", "RESAMPLING=BILINEAR",
                    "-co", "SPARSE_OK=TRUE", "-co", "BIGTIFF=IF_SAFER",
                    "-a_nodata", str(NODATA), str(vrt), str(COG)], check=True)

    size = COG.stat().st_size
    px_tot = sum(w["n_pixels"] for w in wins)
    lac_tot = sum(w["n_lacune"] for w in wins)
    # octets/m² EFFECTIF (compressé) pour extrapoler
    octets_m2 = size / px_tot
    meta = {
        "produit": "LiDAR HD MNT 1 m (IGN)",
        "couche_wms": LAYER,
        "endpoint_wms": WMS,
        "resolution_m": 1.0,
        "referentiel_plani": "RGR92 / UTM 40 Sud (EPSG:2975)",
        "referentiel_alti": "REUN89 (IGN 1989)",
        "note_crs": "WMS tague EPSG:32740 ; grille ré-étiquetée EPSG:2975 (natif RGR92, écart <1 m).",
        "nodata": NODATA,
        "pad_m": PAD_M,
        "cog": str(COG.relative_to(REPO)),
        "taille_octets": size,
        "pixels_donnee": px_tot,
        "pixels_lacune": lac_tot,
        "octets_par_m2_compresse": round(octets_m2, 4),
        "fenetres": wins,
        "extrapolation": {
            "note": "taille = octets/m² compressé × surface (couverture 1 m pleine).",
            "3_communes_km2": {"saint_denis": 148, "saint_leu": 119, "saint_paul": 241},
            "estim_3_communes_octets": int(octets_m2 * (148 + 119 + 241) * 1e6),
            "estim_ile_octets": int(octets_m2 * 2512 * 1e6),
        },
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"\nCOG : {COG}  ({size/1e6:.2f} Mo, {px_tot/1e6:.2f} Mpx données, {lac_tot} lacune)")
    print(f"octets/m² compressé : {octets_m2:.3f}")
    print(f"→ extrapolation 3 communes (508 km²) : {meta['extrapolation']['estim_3_communes_octets']/1e9:.2f} Go")
    print(f"→ extrapolation île (2512 km²)       : {meta['extrapolation']['estim_ile_octets']/1e9:.2f} Go")
    print(f"meta : {META}")


if __name__ == "__main__":
    sys.exit(main())
