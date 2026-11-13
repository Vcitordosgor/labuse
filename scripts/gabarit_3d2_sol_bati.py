"""GABARIT-3D-2 LOT A (LECTURE SEULE) — le sol près du bâti sur BZ1065, coupe B.

On reconstruit la coupe B exactement comme l'app (build_scene), on localise la BOSSE (d∈[68,84],
z≈405,7 m « au bord du bâti »), puis :
A1 — valeurs BRUTES du MNT (LiDAR HD 1 m, data/mnt1m/fond_1m.tif) dans les 3 m autour de l'emprise
     bâtie : la bosse est-elle DANS la donnée IGN, ou créée par notre interpolation sous le bâti ?
A2 — au sommet de la bosse : MNT (sol, 1 m local + 0,5 m HR) vs MNS (surface, WMS LiDAR HD 0,5 m).

Aucune écriture en base, aucun code applicatif modifié.
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d2_sol_bati.py
"""
from __future__ import annotations

import statistics

import httpx
import rasterio
from rasterio.io import MemoryFile
from shapely import wkt
from shapely.geometry import Point
from shapely.ops import unary_union
from sqlalchemy import text

from labuse.config import get_settings
from labuse.db import session_scope
from labuse.gabarit.scene import build_scene

IDU = "97411000BZ1065"
WMS = "https://data.geopf.fr/wms-r/wms"
MNS_LAYER = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS"
MNT_HR_LAYER = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"   # MNT 0,5 m (sol)
SRID = 2975


def _fetch(layer, xmin, ymin, xmax, ymax, res=0.5):
    w, h = int(round((xmax - xmin) / res)), int(round((ymax - ymin) / res))
    p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
         "CRS": f"EPSG:{SRID}", "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
         "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/geotiff", "STYLES": ""}
    r = httpx.get(WMS, params=p, timeout=90.0)
    r.raise_for_status()
    return r.content


def _s(ds, a, x, y):
    col, row = ~ds.transform * (x, y)
    r, c = int(row), int(col)
    if 0 <= r < a.shape[0] and 0 <= c < a.shape[1]:
        v = float(a[r, c])
        if ds.nodata is None or v != ds.nodata:
            return v
    return None


def main() -> None:
    with session_scope() as db:
        scene = build_scene(db, IDU)
        pwkt = db.execute(text("SELECT ST_AsText(geom_2975) FROM parcels WHERE idu=:i"), {"i": IDU}).scalar()
        bwkts = db.execute(text(
            "SELECT ST_AsText(b.geom_2975) FROM spatial_layers b JOIN parcels p ON p.idu=:i "
            "WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"), {"i": IDU}).scalars().all()
    d = scene.to_dict()
    coupe_b = next(c for c in d["coupes"] if c["label"] == "B")
    ox, oy = coupe_b["origine_2975"]
    ux, uy = coupe_b["direction"]
    profil = [p for p in coupe_b["profil"] if p["z"] is not None]
    batis_d = [(b["d0"], b["d1"]) for b in coupe_b["batiments"]]

    # ─── localiser la BOSSE (le mandat : entre 68 et 84 m, monte à ~405,7) ───
    fen = [p for p in profil if 60 <= p["d"] <= 90]
    print(f"coupe B — profil entre 60 et 90 m (d : z) :")
    for p in fen:
        dans_bati = any(a - 1e-6 <= p["d"] <= b + 1e-6 for a, b in batis_d)
        print(f"  d={p['d']:6.2f}  z={p['z']:7.2f}{'   [sous bâti]' if dans_bati else ''}")
    sommet = max(fen, key=lambda p: p["z"])
    sx, sy = ox + ux * sommet["d"], oy + uy * sommet["d"]
    sous_bati = any(a - 1e-6 <= sommet["d"] <= b + 1e-6 for a, b in batis_d)
    print(f"\nSOMMET de la bosse : d={sommet['d']:.2f} m  z={sommet['z']:.2f} m  "
          f"@ ({sx:.1f}, {sy:.1f})  {'SOUS le bâti' if sous_bati else 'hors bâti'}")

    # ─── A1 : MNT BRUT dans l'anneau 0–3 m autour de l'emprise bâtie ───
    emprise = unary_union([wkt.loads(w) for w in bwkts])
    cog = get_settings().mnt1m_cog_file
    with rasterio.open(cog) as ds:
        arr = ds.read(1)
        nod = ds.nodata
        anneau = emprise.buffer(3.0).difference(emprise)
        minx, miny, maxx, maxy = emprise.bounds
        c0, r0 = ~ds.transform * (minx - 4, maxy + 4)
        c1, r1 = ~ds.transform * (maxx + 4, miny - 4)
        ring, sous = [], []
        for row in range(int(min(r0, r1)), int(max(r0, r1)) + 1):
            for col in range(int(min(c0, c1)), int(max(c0, c1)) + 1):
                if not (0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]):
                    continue
                v = arr[row, col]
                if nod is not None and v == nod:
                    continue
                x, y = ds.transform * (col + 0.5, row + 0.5)
                pt = Point(x, y)
                if emprise.contains(pt):
                    sous.append(float(v))
                elif anneau.contains(pt):
                    ring.append((float(v), x, y))
        mnt_local_sommet = _s(ds, arr, sx, sy)

    rv = [v for v, _, _ in ring]
    print("\n── A1 — MNT BRUT (IGN LiDAR HD 1 m, data local) ──")
    print(f"anneau 0–3 m autour du bâti : n={len(rv)}  min={min(rv):.2f}  méd={statistics.median(rv):.2f}  max={max(rv):.2f}")
    bas = sorted(rv)[: max(1, int(len(rv) * 0.6))]
    print(f"sol voisin (bas 60 % anneau) : méd={statistics.median(bas):.2f} m")
    print(f"MNT sous l'emprise : n={len(sous)}  min={min(sous):.2f}  méd={statistics.median(sous):.2f}  max={max(sous):.2f}")
    print(f"MNT LOCAL au sommet de la bosse ({sx:.0f},{sy:.0f}) = {mnt_local_sommet} m  "
          f"(profil app : {sommet['z']:.2f})")

    # ─── A2 : MNT vs MNS au sommet (WMS LiDAR HD 0,5 m) ───
    print("\n── A2 — MNT vs MNS au SOMMET de la bosse (WMS LiDAR HD 0,5 m) ──")
    pad = 10.0
    try:
        mns_b = _fetch(MNS_LAYER, sx - pad, sy - pad, sx + pad, sy + pad)
        mnt_b = _fetch(MNT_HR_LAYER, sx - pad, sy - pad, sx + pad, sy + pad)
        with MemoryFile(mns_b) as m1, m1.open() as d1, MemoryFile(mnt_b) as m2, m2.open() as d2:
            a1, a2 = d1.read(1).astype("float64"), d2.read(1).astype("float64")
            mns = _s(d1, a1, sx, sy)
            mnt_hr = _s(d2, a2, sx, sy)
        print(f"au sommet : MNT(1m)={sommet['z']:.2f}  MNT_HR(0,5m)={None if mnt_hr is None else round(mnt_hr,2)}  "
              f"MNS(0,5m)={None if mns is None else round(mns,2)}")
        if mns is not None and mnt_hr is not None:
            print(f"MNS − MNT_HR = {mns - mnt_hr:+.2f} m")
        if mns is not None:
            print(f"MNS − sol voisin({statistics.median(bas):.2f}) = {mns - statistics.median(bas):+.2f} m")
        print(f"MNT(1m) − sol voisin = {sommet['z'] - statistics.median(bas):+.2f} m")
    except Exception as exc:  # noqa: BLE001
        print(f"WMS indisponible : {exc}")


if __name__ == "__main__":
    main()
