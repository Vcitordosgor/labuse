"""Tuiles d'altitude de la carte 3D, dans la même maille IGN que la scène parcellaire."""
from functools import lru_cache
from io import BytesIO
from math import pi
import re

import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling

from ..config import get_settings
from . import sol


def sources(titre):
    """Les abords sont lus dans le fond régional, la fenêtre parcellaire dans le MNT sélectionné."""
    cfg = get_settings()
    fonds = {"regional": cfg.mnt5m_file, "local": cfg.mnt1m_cog_file}
    if titre in fonds:
        choisi = fonds[titre]
    elif re.fullmatch(r"lidarhd05_\d+_\d+_\d+_\d+", titre):
        choisi = sol.cache_dir() / f"{titre}.tif"
    else:
        raise ValueError("Source de relief inconnue")
    if not choisi.is_file():
        raise FileNotFoundError(choisi)
    chemins = [cfg.mnt5m_file, choisi] if choisi != cfg.mnt5m_file and cfg.mnt5m_file.is_file() else [choisi]
    return tuple((p, p.stat().st_mtime_ns) for p in chemins)


@lru_cache(maxsize=192)
def tuile(fonds, z, x, y):
    """Reprojection sur les nœuds du maillage XYZ de MapLibre puis encodage Terrarium, en mètres REUN89."""
    if not (10 <= z <= 19 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise ValueError("Tuile hors grille")
    demi = pi * 6378137
    cote = 2 * demi / 2**z
    gauche, haut = -demi + x * cote, demi - y * cote
    taille = 512 if 15 <= z <= 19 else 256
    # À la vue parcellaire (zoom 18), MapLibre échantillonne le DEM parent z17.
    # Une tuile fine à ce niveau conserve les crêtes du LiDAR 0,5 m. En z18,
    # 512 pixels donnent déjà le même pas au sol.
    if z == 17 and fonds[-1][0].stem.startswith("lidarhd05_"):
        taille = 1024
    # MapLibre interpole DEM[i,j] à la coordonnée entière (i,j) de la tuile.
    # GDAL centre les échantillons à (i+0,5,j+0,5). Aligner les deux grilles.
    demi_pixel = cote / (2 * taille)
    gauche -= demi_pixel
    haut += demi_pixel
    tr = from_bounds(gauche, haut - cote, gauche + cote, haut, taille, taille)
    sol_m = np.zeros((taille, taille), dtype="float32")
    for path, _ in fonds:
        with rasterio.open(path) as ds:
            grille = np.empty_like(sol_m)
            reproject(rasterio.band(ds, 1), grille, dst_transform=tr, dst_crs="EPSG:3857",
                      dst_nodata=np.nan, resampling=Resampling.bilinear)
        valide = np.isfinite(grille) & (grille > -1000)
        sol_m[valide] = grille[valide]
    code = np.rint((32768 + sol_m) * 256).astype("uint32")
    rgb = np.stack((code >> 16, code >> 8, code), axis=-1).astype("uint8")
    buf = BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return buf.getvalue()
