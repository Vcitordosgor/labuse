"""RECETTE-8 W23 (étapes 1-2) — LiDAR HD MNS : mesurer sur UNE commune, comparer à BD TOPO.

Étape 1 : pour un échantillon de bâtiments d'une commune, on télécharge le MNS LiDAR HD (WMS-r
IGN, couche ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS, GeoTIFF Float32) + le MNT (sol) sur la
même fenêtre, à 0,5 m. On MESURE le temps de téléchargement, le volume, le temps de calcul.

Étape 2 : hauteur au-dessus du sol = MNS − MNT, masquée au CONTOUR du bâtiment (rasterisé). Le
FAÎTAGE = haut percentile (p99, robuste au bruit) ; l'ÉGOUT = bas percentile (p25, bord de toit).
On compare le faîtage mesuré à la hauteur BD TOPO du bâtiment : écart médian, cas extrêmes.

Lecture seule. Aucune ingestion en base (fetch WMS par fenêtre — le coût mesuré ci-dessous décide
si l'on va sur l'île). `PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.
"""
import json
import statistics
import sys
import time

import httpx
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
from sqlalchemy import text

from labuse.db import session_scope

WMS = "https://data.geopf.fr/wms-r/wms"
MNS = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS"
MNT = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
SRID = 2975
RES = 0.5
MARGE = 6.0


def _fetch(layer: str, xmin, ymin, xmax, ymax) -> bytes:
    w = int(round((xmax - xmin) / RES))
    h = int(round((ymax - ymin) / RES))
    p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
         "CRS": f"EPSG:{SRID}", "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
         "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/geotiff", "STYLES": ""}
    r = httpx.get(WMS, params=p, timeout=90.0)
    r.raise_for_status()
    return r.content


def _arr(tif: bytes):
    with MemoryFile(tif) as mf, mf.open() as ds:
        return ds.read(1).astype("float64"), ds.transform, ds.nodata


def main(commune: str, n: int) -> None:
    dl_time = 0.0
    dl_bytes = 0
    calc_time = 0.0
    ecarts = []
    lignes = []
    with session_scope() as db:
        rows = db.execute(text(
            """SELECT b.id, ST_AsGeoJSON(b.geom_2975) gj,
                      NULLIF(b.attrs->>'hauteur','')::float AS h_bdtopo,
                      ST_XMin(b.geom_2975) x0, ST_YMin(b.geom_2975) y0,
                      ST_XMax(b.geom_2975) x1, ST_YMax(b.geom_2975) y1
               FROM spatial_layers b
               WHERE b.kind='batiment' AND b.geom_2975 IS NOT NULL
                 AND NULLIF(b.attrs->>'hauteur','') IS NOT NULL
                 AND ST_Area(b.geom_2975) BETWEEN 40 AND 2000
                 AND EXISTS (SELECT 1 FROM parcels p WHERE p.commune=:c
                             AND ST_Intersects(b.geom_2975, p.geom_2975))
               ORDER BY md5(b.id::text) LIMIT :n"""),
            {"c": commune, "n": n}).mappings().all()
        print(f"commune {commune} — {len(rows)} bâtiments échantillonnés (BD TOPO hauteur présente)\n")
        for r in rows:
            xmin, ymin = r["x0"] - MARGE, r["y0"] - MARGE
            xmax, ymax = r["x1"] + MARGE, r["y1"] + MARGE
            try:
                t = time.time()
                tif_s = _fetch(MNS, xmin, ymin, xmax, ymax)
                tif_t = _fetch(MNT, xmin, ymin, xmax, ymax)
                dl_time += time.time() - t
                dl_bytes += len(tif_s) + len(tif_t)
                t = time.time()
                mns, tr, nod_s = _arr(tif_s)
                mnt, _, nod_t = _arr(tif_t)
                geom = json.loads(r["gj"])
                mask = geometry_mask([geom], out_shape=mns.shape, transform=tr, invert=True)
                haut = mns - mnt
                ok = mask.copy()
                if nod_s is not None:
                    ok &= mns != nod_s
                if nod_t is not None:
                    ok &= mnt != nod_t
                ok &= np.isfinite(haut)
                calc_time += time.time() - t
                vals = haut[ok]
                if vals.size < 5:
                    continue
                faitage = float(np.percentile(vals, 99))
                egout = float(np.percentile(vals, 25))
                hb = float(r["h_bdtopo"])
                ecart = faitage - hb
                ecarts.append(ecart)
                lignes.append((r["id"], round(hb, 1), round(faitage, 1), round(egout, 1), round(ecart, 1)))
            except Exception as exc:  # noqa: BLE001
                print(f"  bât {r['id']} : échec {str(exc)[:80]}")
    print(f"{'bât_id':>10} | BD TOPO | faîtage | égout | écart(faît−BDT)")
    for l in lignes:
        print(f"{l[0]:>10} | {l[1]:>7} | {l[2]:>7} | {l[3]:>5} | {l[4]:>+6}")
    if ecarts:
        print(f"\nMESURES — {len(ecarts)} bâtiments comparés")
        print(f"  écart médian faîtage−BD TOPO : {statistics.median(ecarts):+.2f} m")
        print(f"  écart moyen : {statistics.mean(ecarts):+.2f} m | min {min(ecarts):+.1f} | max {max(ecarts):+.1f}")
        absmed = statistics.median([abs(e) for e in ecarts])
        print(f"  écart absolu médian : {absmed:.2f} m")
    print(f"\nCOÛT (WMS par fenêtre bâtiment, MNS+MNT @0,5 m) — {len(lignes)} bâtiments :")
    if lignes:
        print(f"  téléchargement total {dl_time:.1f}s ({dl_bytes/1e6:.1f} Mo) → {dl_time/len(lignes):.2f}s/bât, {dl_bytes/len(lignes)/1e3:.0f} ko/bât")
        print(f"  calcul total {calc_time:.2f}s → {calc_time/len(lignes)*1000:.0f} ms/bât")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Saint-Denis",
         int(sys.argv[2]) if len(sys.argv) > 2 else 20)
