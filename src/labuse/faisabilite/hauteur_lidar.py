"""RECETTE-8 W23 — HAUTEURS MESURÉES au LiDAR HD (MNS − MNT), faîtage ET égout distingués.

Le bâti BD TOPO ne porte qu'UNE hauteur (souvent au faîtage, parfois à l'égout, incertaine) : c'est
la cause de fond de E1 (on comparait un faîtage à une règle d'égout). Le LiDAR HD MNS de l'IGN donne
la hauteur MESURÉE : sur l'emprise du bâtiment, hauteur au-dessus du sol = MNS − MNT ; le FAÎTAGE est
le haut de la distribution (p99, robuste au bruit), l'ÉGOUT le bord de toit (p25).

Validé sur 20 bâtiments de Saint-Denis (script `scripts/_recette8_w23_lidar_mns.py`) : écart médian
faîtage − BD TOPO +0,57 m, écart absolu médian 1,11 m — les chiffres TIENNENT l'estimation, et le
MNS distingue bien faîtage/égout (ce que BD TOPO ne fait pas). Coût mesuré : ~1 s de fetch WMS +
33 ms de calcul par bâtiment.

Servi PAR PARCELLE à la demande (comme l'exposition, W22) : une fenêtre MNS+MNT autour du bâtiment
principal, jamais une ingestion massive bloquante. L'ingestion précalculée de toute l'île (pour
remplacer BD TOPO partout : extrusion 3D, surélévation, Apporteur) reste un batch borné à lancer sous
le go de Vic (coût extrapolé : ~1 s/bâtiment).
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger("labuse.hauteur_lidar")

WMS = "https://data.geopf.fr/wms-r/wms"
MNS = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS"   # surface (bâti compris) — LiDAR HD
MNT = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"       # sol
SRID = 2975
RES = 0.5
MARGE_M = 6.0
P_FAITAGE = 99
P_EGOUT = 25


def _fetch(layer: str, xmin, ymin, xmax, ymax) -> bytes:
    import httpx
    w = int(round((xmax - xmin) / RES))
    h = int(round((ymax - ymin) / RES))
    p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
         "CRS": f"EPSG:{SRID}", "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
         "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/geotiff", "STYLES": ""}
    r = httpx.get(WMS, params=p, timeout=90.0)
    r.raise_for_status()
    return r.content


def _hauteurs(geojson: str, bbox: tuple[float, float, float, float]) -> dict | None:
    """Faîtage/égout mesurés (m au-dessus du sol) sur l'emprise, depuis MNS−MNT. None si trop peu
    de cellules valides sous le contour."""
    import numpy as np
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.io import MemoryFile
    xmin, ymin, xmax, ymax = bbox
    tif_s = _fetch(MNS, xmin - MARGE_M, ymin - MARGE_M, xmax + MARGE_M, ymax + MARGE_M)
    tif_t = _fetch(MNT, xmin - MARGE_M, ymin - MARGE_M, xmax + MARGE_M, ymax + MARGE_M)
    with MemoryFile(tif_s) as ms, ms.open() as ds, MemoryFile(tif_t) as mt, mt.open() as dt:
        mns = ds.read(1).astype("float64"); tr = ds.transform; nod_s = ds.nodata
        mnt = dt.read(1).astype("float64"); nod_t = dt.nodata
    mask = geometry_mask([json.loads(geojson)], out_shape=mns.shape, transform=tr, invert=True)
    haut = mns - mnt
    ok = mask.copy()
    if nod_s is not None:
        ok &= mns != nod_s
    if nod_t is not None:
        ok &= mnt != nod_t
    ok &= np.isfinite(haut)
    vals = haut[ok]
    if vals.size < 5:
        return None
    return {"faitage_m": round(float(np.percentile(vals, P_FAITAGE)), 1),
            "egout_m": round(float(np.percentile(vals, P_EGOUT)), 1),
            "n_cellules": int(vals.size)}


def hauteur_parcelle_lidar(db, parcel_id: int) -> dict | None:
    """Hauteurs LiDAR mesurées du bâtiment PRINCIPAL (le plus grand) de la parcelle : faîtage, égout,
    et l'écart au faîtage BD TOPO (fait déclaré). None si la parcelle n'a pas de bâti BD TOPO. En cas
    d'échec fetch/calcul : `{faitage_m: None, erreur}` — dit, jamais une fausse mesure."""
    from sqlalchemy import text
    row = db.execute(text(
        """SELECT b.id, ST_AsGeoJSON(b.geom_2975) gj,
                  NULLIF(b.attrs->>'hauteur','')::float AS h_bdtopo,
                  ST_XMin(b.geom_2975) x0, ST_YMin(b.geom_2975) y0,
                  ST_XMax(b.geom_2975) x1, ST_YMax(b.geom_2975) y1
           FROM spatial_layers b JOIN parcels p ON p.id = :p
           WHERE b.kind='batiment' AND b.geom_2975 IS NOT NULL
             AND ST_Intersects(b.geom_2975, p.geom_2975)
           ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1"""), {"p": parcel_id}).mappings().first()
    if not row:
        return None
    try:
        h = _hauteurs(row["gj"], (row["x0"], row["y0"], row["x1"], row["y1"]))
    except Exception as exc:  # noqa: BLE001 — échec DIT
        log.warning("hauteur_lidar parcelle %s : %s", parcel_id, exc)
        return {"parcel_id": parcel_id, "faitage_m": None, "erreur": str(exc)[:200]}
    if h is None:
        return {"parcel_id": parcel_id, "faitage_m": None, "erreur": "MNS/MNT indisponible sur l'emprise"}
    hb = row["h_bdtopo"]
    return {"parcel_id": parcel_id, "source": "LiDAR HD MNS (IGN) − MNT, mesuré",
            "hauteur_bdtopo_m": (round(float(hb), 1) if hb is not None else None),
            "ecart_faitage_bdtopo_m": (round(h["faitage_m"] - float(hb), 1) if hb is not None else None),
            **h}
