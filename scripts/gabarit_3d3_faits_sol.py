"""GABARIT-3D-3 (LOT 2 FIX) — LES FAITS. Sur la MÊME fenêtre (BZ1065), on lit les DEUX couches WMS IGN à la
même résolution demandée (0,5 m) et on mesure : nombre de valeurs distinctes + longueur du plus long palier
plat le long d'une ligne. On interroge aussi GetCapabilities (titre + résolution annoncée) de chaque couche.
Conclusion attendue : HIGHRES (RGE ALTI) est GROSSIER (marches ~5 m) ; LiDAR HD est fin (0,5 m natif).

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d3_faits_sol.py
"""
from __future__ import annotations

import io
import re

import httpx
import numpy as np
import rasterio
from sqlalchemy import text

from labuse.db import session_scope

WMS = "https://data.geopf.fr/wms-r/wms"
HIGHRES = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
LIDARHD = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S"
IDU = "97411000BZ1065"
_c = httpx.Client(timeout=90.0)


def _fenetre_bz():
    with session_scope() as db:
        b = db.execute(text("SELECT ST_XMin(g),ST_YMin(g),ST_XMax(g),ST_YMax(g) FROM "
                            "(SELECT geom_2975 g FROM parcels WHERE idu=:i) q"), {"i": IDU}).one()
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return cx - 25, cy - 25, cx + 25, cy + 25           # 50 m × 50 m


def _lire(layer, x0, y0, x1, y1, res=0.5):
    w, h = int((x1 - x0) / res), int((y1 - y0) / res)
    r = _c.get(WMS, params={"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
                            "CRS": "EPSG:2975", "BBOX": f"{x0},{y0},{x1},{y1}", "WIDTH": w, "HEIGHT": h,
                            "FORMAT": "image/geotiff", "STYLES": ""})
    r.raise_for_status()
    with rasterio.open(io.BytesIO(r.content)) as ds:
        a = ds.read(1).astype("float64")
    a[(a <= -1000) | ~np.isfinite(a)] = np.nan
    return a


def _palier_ligne(a):
    """Plus long palier (cellules consécutives à ±1 cm) sur la ligne centrale → en mètres (cellule = 0,5 m)."""
    ligne = a[a.shape[0] // 2]
    best = run = 0
    prev = None
    for v in ligne:
        if np.isnan(v):
            prev, run = None, 0
            continue
        if prev is None or abs(v - prev) > 0.01:
            prev, run = v, 1
        else:
            run += 1
            best = max(best, run)
    return best * 0.5


def _distinctes(a):
    v = a[np.isfinite(a)]
    return len(np.unique(np.round(v, 2)))


def _capabilities(layer):
    r = _c.get(WMS, params={"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetCapabilities"})
    xml = r.text
    i = xml.find(f"<Name>{layer}</Name>")
    if i < 0:
        return "(couche absente des capabilities)"
    # dans un <Layer>, le <Title> précède en général le <Name> — on prend le DERNIER Title avant le Name.
    titres = re.findall(r"<Title>([^<]*)</Title>", xml[max(0, i - 1500):i])
    return titres[-1] if titres else "(titre non trouvé)"


def main():
    x0, y0, x1, y1 = _fenetre_bz()
    print(f"\n════ FAITS — fenêtre 50 m sur {IDU}, deux couches lues à 0,5 m demandé ════\n")
    for nom, layer in (("HIGHRES (RGE ALTI)", HIGHRES), ("LiDAR HD RGR92UTM40S", LIDARHD)):
        try:
            a = _lire(layer, x0, y0, x1, y1)
            print(f"{nom}")
            print(f"    couche        : {layer}")
            print(f"    GetCapabilities titre : {_capabilities(layer)}")
            print(f"    valeurs distinctes sur 100×100 px : {_distinctes(a)}")
            print(f"    plus long palier plat (ligne centrale) : {_palier_ligne(a):.1f} m\n")
        except Exception as e:  # noqa: BLE001
            print(f"{nom} : lecture impossible — {e}\n")
    print("Lecture : un palier long + peu de valeurs distinctes = donnée grossière suréchantillonnée (marches).")


if __name__ == "__main__":
    main()
