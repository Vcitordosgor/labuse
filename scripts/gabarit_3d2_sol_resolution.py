"""GABARIT-3D-2 LOT A (SOL, lecture seule) — lire le sol à 0,5 m plutôt que 1 m ?

Q3 : sur les 3 cas « élément couvert » (surélevé ≥1,5 m) + BZ1065, le sol 0,5 m HR efface-t-il la bosse ?
Q4 : coût — poids disque + temps de lecture d'une coupe et d'un maillage à 1 m vs 0,5 m.

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d2_sol_resolution.py
"""
from __future__ import annotations

import math
import statistics
import time

import httpx
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from shapely import wkt
from shapely.geometry import Point
from shapely.ops import unary_union
from sqlalchemy import text

import labuse.gabarit.scene as scene_mod
from labuse.db import session_scope

WMS = "https://data.geopf.fr/wms-r"
WMS2 = "https://data.geopf.fr/wms-r/wms"
L_1M = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S"   # notre fond 1 m
L_HR = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"                        # MNT 0,5 m (sol propre)
_cli = httpx.Client(timeout=90.0)

# Q3 : BZ1065 + les 3 parcelles « surélevées ≥1,5 m » repérées en A4
CAS = ["97411000BZ1065", "97415000DX0049", "97403000AP1634", "97404000AI2092"]


def _fetch(layer, x0, y0, x1, y1, res, endpoint=WMS2):
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "STYLES": "", "CRS": "EPSG:2975",
         "FORMAT": "image/geotiff", "WIDTH": w, "HEIGHT": h, "BBOX": f"{x0},{y0},{x1},{y1}", "LAYERS": layer}
    r = _cli.get(endpoint, params=p); r.raise_for_status()
    return r.content


def _samp(tif, x, y):
    with MemoryFile(tif) as mf, mf.open() as ds:
        a = ds.read(1).astype("float64"); a[(a <= -1000) | ~np.isfinite(a)] = np.nan
        col, row = ~ds.transform * (x, y); rr, cc = int(row), int(col)
        if 0 <= rr < a.shape[0] and 0 <= cc < a.shape[1] and np.isfinite(a[rr, cc]):
            return float(a[rr, cc])
    return None


def q3():
    print("── Q3 — le sol 0,5 m HR efface-t-il la bosse des 3 cas (+ BZ1065) ? ──")
    efface = 0
    with session_scope() as db:
        for idu in CAS:
            pw = db.execute(text("SELECT ST_AsText(geom_2975) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            bw = db.execute(text("SELECT ST_AsText(b.geom_2975) FROM spatial_layers b JOIN parcels p ON p.idu=:i "
                                 "WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,p.geom_2975)"), {"i": idu}).scalars().all()
            if not pw or not bw:
                print(f"  {idu} : données absentes"); continue
            emp = unary_union([wkt.loads(w) for w in bw])
            minx, miny, maxx, maxy = emp.bounds
            # MNT 1 m sur l'emprise → point le plus haut SOUS le bâti = la bosse
            t1 = _fetch(L_1M, int(minx) - 3, int(miny) - 3, int(maxx) + 3, int(maxy) + 3, 1.0, endpoint=WMS)
            with MemoryFile(t1) as mf, mf.open() as ds:
                a = ds.read(1).astype("float64"); a[(a <= -1000) | ~np.isfinite(a)] = np.nan
                bestv, bx, by = -1e9, None, None
                for rr in range(a.shape[0]):
                    for cc in range(a.shape[1]):
                        if not np.isfinite(a[rr, cc]):
                            continue
                        x, y = ds.transform * (cc + 0.5, rr + 0.5)
                        if emp.contains(Point(x, y)) and a[rr, cc] > bestv:
                            bestv, bx, by = float(a[rr, cc]), x, y
            if bx is None:
                print(f"  {idu} : pas de pixel sous l'emprise"); continue
            # sol voisin (anneau 0–3 m hors emprise, MNT 1 m)
            ann = emp.buffer(3).difference(emp); vois = []
            with MemoryFile(t1) as mf, mf.open() as ds:
                a = ds.read(1).astype("float64"); a[(a <= -1000) | ~np.isfinite(a)] = np.nan
                for rr in range(a.shape[0]):
                    for cc in range(a.shape[1]):
                        if not np.isfinite(a[rr, cc]):
                            continue
                        x, y = ds.transform * (cc + 0.5, rr + 0.5)
                        if ann.contains(Point(x, y)):
                            vois.append(float(a[rr, cc]))
            solv = statistics.median(sorted(vois)[:max(1, int(len(vois) * 0.6))]) if vois else float("nan")
            # 0,5 m HR au même point
            hr = _fetch(L_HR, bx - 6, by - 6, bx + 6, by + 6, 0.5)
            z05 = _samp(hr, bx, by)
            sur1 = bestv - solv
            sur05 = (z05 - solv) if z05 is not None else None
            disparu = (sur05 is not None and sur05 < 1.5)
            efface += 1 if disparu else 0
            print(f"  {idu[-6:]} bosse 1 m={bestv:.2f} (+{sur1:.1f} m) | 0,5 m HR={None if z05 is None else round(z05,2)} "
                  f"(+{'?' if sur05 is None else round(sur05,1)} m) → bosse {'EFFACÉE' if disparu else 'persiste'}")
    print(f"  => {efface} / {len(CAS)} cas où la bosse disparaît à 0,5 m")


def q4():
    print("\n── Q4 — coût : temps de lecture d'un maillage + d'une coupe, 1 m vs 0,5 m (BZ1065) ──")
    idu = "97411000BZ1065"
    with session_scope() as db:
        bbox = db.execute(text("SELECT ST_XMin(g),ST_YMin(g),ST_XMax(g),ST_YMax(g) FROM "
                               "(SELECT geom_2975 g FROM parcels WHERE idu=:i) q"), {"i": idu}).one()
        minx, miny, maxx, maxy = bbox
        orig = scene_mod.charger_surface

        def surf_res(res):
            x0, y0 = int(math.floor(minx - 45)), int(math.floor(miny - 45))
            x1, y1 = int(math.ceil(maxx + 45)), int(math.ceil(maxy + 45))
            layer, ep = (L_1M, WMS) if res == 1.0 else (L_HR, WMS2)
            t = _fetch(layer, x0, y0, x1, y1, res, endpoint=ep)
            with MemoryFile(t) as mf, mf.open() as ds:
                a = ds.read(1).astype("float64")
            a[(a <= -1000) | ~np.isfinite(a)] = np.nan
            return scene_mod._Surface(a, float(x0), float(y1), res), a.shape

        # warm-up (JIT/imports) : un build jeté AVANT de chronométrer, sinon le 1ᵉʳ res paie l'init
        s0, _ = surf_res(1.0)
        scene_mod.charger_surface = lambda a, b, c, d, marge=170.0, _s=s0: _s
        try:
            scene_mod.build_scene(db, idu, use_cache=False)
        finally:
            scene_mod.charger_surface = orig

        for res in (1.0, 0.5):
            surf, shp = surf_res(res)

            def _patched(aa, bb, cc, dd, marge=170.0, _s=surf):
                return _s
            scene_mod.charger_surface = _patched
            try:
                best = 1e9
                for _ in range(3):
                    t0 = time.perf_counter()
                    scene = scene_mod.build_scene(db, idu, use_cache=False)
                    best = min(best, time.perf_counter() - t0)
                dt = best
                d = scene.to_dict()
                npts = sum(len(c["profil"]) for c in d.get("coupes", []))
                nverts = len((d.get("terrain") or {}).get("sommets") or []) or "?"
            finally:
                scene_mod.charger_surface = orig
            print(f"  {res:>4} m : maillage {shp[0]}×{shp[1]} px · build_scene (maillage+2 coupes) {dt*1000:.0f} ms · "
                  f"points de profil (2 coupes) {npts} · sommets {nverts}")


if __name__ == "__main__":
    q3()
    q4()
