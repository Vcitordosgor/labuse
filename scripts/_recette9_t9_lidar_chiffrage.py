"""RECETTE-9 T9 — la question qui décide de l'ingestion complète : +0,57 m d'écart médian, c'est PEU.
La valeur du LiDAR est-elle (A) la PRÉCISION du faîtage, ou (B) la DISTINCTION faîtage/égout que
la BD TOPO ne donne pas du tout ? On CHIFFRE les deux sur la commune déjà mesurée (Saint-Denis).

Lecture seule (fetch WMS par fenêtre, aucune écriture en base).
Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python scripts/_recette9_t9_lidar_chiffrage.py [commune] [n]
"""
import json
import statistics
import sys
import time

import httpx
import numpy as np
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
from sqlalchemy import text

from labuse.db import session_scope

WMS = "https://data.geopf.fr/wms-r/wms"
MNS = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS"
MNT = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
SRID, RES, MARGE = 2975, 0.5, 6.0


def _fetch(layer, xmin, ymin, xmax, ymax):
    w = int(round((xmax - xmin) / RES)); h = int(round((ymax - ymin) / RES))
    r = httpx.get(WMS, params={"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": layer, "CRS": f"EPSG:{SRID}", "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
        "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/geotiff", "STYLES": ""}, timeout=90.0)
    r.raise_for_status(); return r.content


def _arr(tif):
    with MemoryFile(tif) as mf, mf.open() as ds:
        return ds.read(1).astype("float64"), ds.transform, ds.nodata


def main(commune, n):
    rows_out = []
    with session_scope() as db:
        rows = db.execute(text(
            """SELECT b.id, ST_AsGeoJSON(b.geom_2975) gj, NULLIF(b.attrs->>'hauteur','')::float h_bdtopo,
                      ST_XMin(b.geom_2975) x0, ST_YMin(b.geom_2975) y0,
                      ST_XMax(b.geom_2975) x1, ST_YMax(b.geom_2975) y1
               FROM spatial_layers b
               WHERE b.kind='batiment' AND b.geom_2975 IS NOT NULL
                 AND NULLIF(b.attrs->>'hauteur','') IS NOT NULL
                 AND ST_Area(b.geom_2975) BETWEEN 40 AND 2000
                 AND EXISTS (SELECT 1 FROM parcels p WHERE p.commune=:c
                             AND ST_Intersects(b.geom_2975, p.geom_2975))
               ORDER BY md5(b.id::text) LIMIT :n"""), {"c": commune, "n": n}).mappings().all()
        for r in rows:
            try:
                bb = (r["x0"] - MARGE, r["y0"] - MARGE, r["x1"] + MARGE, r["y1"] + MARGE)
                mns, tr, ns = _arr(_fetch(MNS, *bb)); mnt, _, nt = _arr(_fetch(MNT, *bb))
                mask = geometry_mask([json.loads(r["gj"])], out_shape=mns.shape, transform=tr, invert=True)
                haut = mns - mnt; ok = mask.copy()
                if ns is not None: ok &= mns != ns
                if nt is not None: ok &= mnt != nt
                ok &= np.isfinite(haut)
                vals = haut[ok]
                if vals.size < 5:
                    continue
                fait = float(np.percentile(vals, 99)); egout = float(np.percentile(vals, 25))
                rows_out.append((float(r["h_bdtopo"]), fait, egout))
            except Exception as exc:  # noqa: BLE001
                print(f"  bât {r['id']} : échec {str(exc)[:70]}", flush=True)
    if not rows_out:
        print("aucun bâtiment mesuré"); return
    bdt = [b for b, f, e in rows_out]; faits = [f for b, f, e in rows_out]; egs = [e for b, f, e in rows_out]
    ec_f = [f - b for b, f, e in rows_out]           # faîtage − BD TOPO
    ec_e = [b - e for b, f, e in rows_out]           # BD TOPO − égout
    spread = [f - e for b, f, e in rows_out]         # amplitude faîtage/égout (ce que BD TOPO écrase)
    med = statistics.median
    print(f"\n=== {commune} — {len(rows_out)} bâtiments mesurés (LiDAR HD MNS−MNT vs BD TOPO) ===\n")
    print("CHIFFRAGE A — la PRÉCISION du faîtage (LiDAR vs la hauteur BD TOPO déclarée) :")
    print(f"  écart médian faîtage−BD TOPO      : {med(ec_f):+.2f} m")
    print(f"  écart ABSOLU médian |faîtage−BDT| : {med([abs(x) for x in ec_f]):.2f} m")
    print(f"  part |écart| ≤ 1 m                : {100*sum(1 for x in ec_f if abs(x)<=1)/len(ec_f):.0f} %")
    print("  → si petit : la BD TOPO donne DÉJÀ un faîtage proche ; le LiDAR ajoute peu de précision.\n")
    print("CHIFFRAGE B — la DISTINCTION faîtage/égout (ce que BD TOPO ne donne PAS) :")
    print(f"  amplitude médiane faîtage−égout   : {med(spread):.2f} m   (BD TOPO l'écrase en UN nombre)")
    print(f"  amplitude moyenne                 : {statistics.mean(spread):.2f} m  (min {min(spread):.1f}, max {max(spread):.1f})")
    # BD TOPO est-elle un faîtage ou un égout ? distance à l'un vs l'autre
    plus_pres_faitage = sum(1 for b, f, e in rows_out if abs(b - f) < abs(b - e))
    print(f"  BD TOPO plus proche du FAÎTAGE    : {plus_pres_faitage}/{len(rows_out)} "
          f"({100*plus_pres_faitage/len(rows_out):.0f} %) — donc pas toujours un faîtage")
    print(f"  écart médian BD TOPO−égout        : {med(ec_e):+.2f} m  "
          "(hauteur constructible réelle = égout, pas faîtage)")
    print("  → l'égout (bord de toit) est LA hauteur qui décide de la surélévation (règle à l'égout,")
    print("    cause de fond de E1). BD TOPO ne le donne jamais ; le LiDAR, oui. C'est LÀ sa valeur.\n")
    print("VERDICT (chiffré) : A =", f"{med([abs(x) for x in ec_f]):.2f} m d'écart absolu médian sur le faîtage",
          "(précision modeste) ;")
    print("                    B =", f"{med(spread):.2f} m d'amplitude faîtage/égout que BD TOPO masque",
          "+ égout jamais fourni par BD TOPO.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Saint-Denis",
         int(sys.argv[2]) if len(sys.argv) > 2 else 40)
