"""RETOURS-13 R31 — PROTOTYPE toiture simple / double pente depuis le LiDAR HD IGN.

Constat de disponibilité (05/09/2026, vérifié LIVE) : la Géoplateforme diffuse les modèles
dérivés du LiDAR HD SUR LE 974 — couches WMS `IGNF_LIDAR-HD_MNS_...RGR92UTM40S` et
`IGNF_LIDAR-HD_MNH_...RGR92UTM40S` (EPSG:2975, GeoTIFF 32 bits, valeurs réelles mesurées
4-70 m sur Saint-Denis). Le MNH (hauteur au-dessus du sol, MNS−MNT déjà calculé par l'IGN)
est LA matière : pente + orientation par pixel sur l'emprise bâtie = les pans de toiture.

Méthode (20 bâtiments d'essai) :
  1. bâtiments BD TOPO (spatial_layers kind='batiment'), emprise ≥ 60 m² ;
  2. patch MNH 50 cm (WMS GeoTIFF, EPSG:2975) masqué à l'emprise ;
  3. pente/aspect par pixel (gradient) ; pixels pentus (8°-50°) → histogramme d'orientation
     en 8 secteurs ; lissage ; classification :
       plat (< 15 % de pixels pentus) · monopente (1 secteur dominant) ·
       double pente (2 secteurs opposés) · croupe/complexe (3+ secteurs) ;
  4. planche PNG par bâtiment : ortho | MNH | carte d'aspect + verdict — CONTRÔLE À L'ŒIL.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

import httpx
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import create_engine, text  # noqa: E402

ENG = create_engine(os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse"))
WMS = "https://data.geopf.fr/wms-r/wms"
MNH_LAYER = "IGNF_LIDAR-HD_MNH_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S"
ORTHO_WMS = "https://data.geopf.fr/wms-r/wms"
OUT = os.path.join(os.path.dirname(__file__), "toiture_planches")
os.makedirs(OUT, exist_ok=True)
RES = 0.5  # m/pixel


def fetch_geotiff(layer: str, bbox: tuple[float, float, float, float], fmt="image/geotiff") -> np.ndarray:
    w = int((bbox[2] - bbox[0]) / RES)
    h = int((bbox[3] - bbox[1]) / RES)
    r = httpx.get(WMS, params={
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
        "CRS": "EPSG:2975", "BBOX": ",".join(str(v) for v in bbox),
        "WIDTH": w, "HEIGHT": h, "FORMAT": fmt, "STYLES": ""}, timeout=120)
    r.raise_for_status()
    import rasterio
    from rasterio.io import MemoryFile
    with MemoryFile(r.content) as mf, mf.open() as ds:
        return ds.read(1).astype("float64")


def fetch_ortho(bbox) -> np.ndarray:
    w = int((bbox[2] - bbox[0]) / 0.2)
    h = int((bbox[3] - bbox[1]) / 0.2)
    r = httpx.get(ORTHO_WMS, params={
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": "HR.ORTHOIMAGERY.ORTHOPHOTOS", "CRS": "EPSG:2975",
        "BBOX": ",".join(str(v) for v in bbox), "WIDTH": w, "HEIGHT": h,
        "FORMAT": "image/png", "STYLES": ""}, timeout=120)
    r.raise_for_status()
    from PIL import Image
    return np.array(Image.open(io.BytesIO(r.content)).convert("RGB"))


def classify(mnh: np.ndarray, mask: np.ndarray) -> tuple[str, dict]:
    gy, gx = np.gradient(mnh, RES)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    aspect = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360   # 0=N
    core = mask.copy()
    # érosion 2 px (bords de toit = gradients parasites)
    from scipy.ndimage import binary_erosion
    core = binary_erosion(core, iterations=2)
    tot = int(core.sum())
    if tot < 40:
        return "indetermine", {"raison": "emprise trop petite après érosion"}
    pentu = core & (slope >= 8) & (slope <= 50)
    part_pentue = pentu.sum() / tot
    if part_pentue < 0.15:
        return "plat", {"part_pentue": round(float(part_pentue), 2)}
    # histogramme d'orientation en 16 secteurs, LISSÉ circulairement, puis PICS (un pan de
    # toiture étale son orientation sur 2 secteurs bruts : compter les secteurs sur-représentés
    # coupait un pan en deux — mesuré sur l'échantillon : double pente basse classée mono).
    sect = ((aspect[pentu] + 11.25) // 22.5).astype(int) % 16
    hist = np.bincount(sect, minlength=16).astype(float)
    hist /= hist.sum()
    liss = np.array([hist[(i - 1) % 16] * 0.25 + hist[i] * 0.5 + hist[(i + 1) % 16] * 0.25
                     for i in range(16)])
    pics = [i for i in range(16)
            if liss[i] >= 0.10 and liss[i] >= liss[(i - 1) % 16] and liss[i] > liss[(i + 1) % 16]]
    pics = sorted(pics, key=lambda i: -liss[i])[:4]
    meta = {"part_pentue": round(float(part_pentue), 2),
            "pics": [int(i * 22.5) for i in pics],
            "pente_mediane": round(float(np.median(slope[pentu])), 1)}
    if len(pics) <= 1:
        return "monopente", meta
    if len(pics) == 2:
        ecart = min((pics[0] - pics[1]) % 16, (pics[1] - pics[0]) % 16)   # 0..8
        if ecart >= 6:            # pans OPPOSÉS (135-180°) → double pente
            return "double_pente", meta
        if ecart <= 2:            # pics adjacents = un même pan étalé → monopente
            return "monopente", meta
        return "croupe_complexe", meta   # perpendiculaires (toit en L, croupe)
    return "croupe_complexe", meta


def main(n=20):
    with ENG.connect() as c:
        rows = c.execute(text("""
            SELECT sl.id, sl.commune, ST_XMin(g) x1, ST_YMin(g) y1, ST_XMax(g) x2, ST_YMax(g) y2,
                   ST_AsGeoJSON(ST_Transform(sl.geom, 2975)) gj, ST_Area(g) aire
            FROM spatial_layers sl,
                 LATERAL (SELECT ST_Transform(sl.geom, 2975) AS g) t
            WHERE sl.kind='batiment' AND ST_Area(g) BETWEEN 80 AND 600
              AND sl.commune IN ('Saint-Denis','Saint-Paul','Saint-Pierre','Sainte-Marie')
            ORDER BY sl.id LIMIT :n"""), {"n": n}).mappings().all()
    from PIL import Image, ImageDraw
    from rasterio.features import rasterize
    from shapely.geometry import shape
    verdicts = []
    for i, r in enumerate(rows):
        pad = 6.0
        bbox = (math.floor(r["x1"] - pad), math.floor(r["y1"] - pad),
                math.ceil(r["x2"] + pad), math.ceil(r["y2"] + pad))
        try:
            mnh = fetch_geotiff(MNH_LAYER, bbox)
        except Exception as e:
            print(i, "MNH KO", e); continue
        mnh[mnh < -100] = np.nan
        geom = shape(json.loads(r["gj"]))
        h, w = mnh.shape
        # rasterize emprise (transform: north-up, origin en haut-gauche)
        from rasterio.transform import from_bounds
        tr = from_bounds(*bbox, w, h)
        mask = rasterize([(geom, 1)], out_shape=(h, w), transform=tr, fill=0).astype(bool)
        mnh_f = np.nan_to_num(mnh, nan=0.0)
        verdict, meta = classify(mnh_f, mask)
        verdicts.append({"id": r["id"], "commune": r["commune"], "verdict": verdict, **meta})
        # planche : ortho | MNH | verdict
        try:
            ortho = fetch_ortho(bbox)
        except Exception:
            ortho = np.zeros((h, w, 3), dtype=np.uint8)
        mnh_img = mnh_f.copy(); mnh_img[~mask] *= 0.35
        mx = np.nanpercentile(mnh_img[mask], 98) if mask.sum() else 1
        mnh_vis = np.clip(mnh_img / max(mx, 1e-3), 0, 1)
        mnh_rgb = (np.stack([mnh_vis]*3, -1) * 255).astype(np.uint8)
        o = Image.fromarray(ortho).resize((w*3, h*3), Image.NEAREST)
        m = Image.fromarray(mnh_rgb).resize((w*3, h*3), Image.NEAREST)
        planche = Image.new("RGB", (w*6 + 12, h*3 + 34), (12, 16, 14))
        planche.paste(o, (0, 34)); planche.paste(m, (w*3 + 12, 34))
        d = ImageDraw.Draw(planche)
        d.text((6, 8), f"#{i:02d} bat {r['id']} {r['commune']} — {verdict} "
                       f"(pentu {meta.get('part_pentue','?')}, pente méd {meta.get('pente_mediane','—')}°)",
               fill=(120, 230, 170))
        planche.save(os.path.join(OUT, f"toit_{i:02d}_{verdict}.png"))
        print(i, r["commune"], verdict, meta)
    with open(os.path.join(OUT, "verdicts.json"), "w") as f:
        json.dump(verdicts, f, ensure_ascii=False, indent=1)
    print("planches →", OUT)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
