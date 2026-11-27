"""Tuiles Terrarium du terrain IGN de La Réunion, dans la grille XYZ de MapLibre."""
from __future__ import annotations

import io
from time import monotonic
from functools import lru_cache

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, Response
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from shapely.geometry import box

from ..config import get_settings
from ..gabarit import sol
from .ortho_proxy import _ile, _tuile_bounds

router = APIRouter(tags=["map-tiles"])
SIZE = 512


def _lire(chemin, transform, size=SIZE):
    with rasterio.open(chemin) as ds, WarpedVRT(
        ds, crs="EPSG:3857", transform=transform, width=size, height=size,
        resampling=Resampling.bilinear, dtype="float32", nodata=np.nan,
    ) as vrt:
        a = vrt.read(1)
        a[a <= -1000] = np.nan
        return a


def _terrarium(a):
    code = np.rint((a + 32768) * 256).astype("uint32")
    rgb = np.stack((code >> 16, code >> 8, code), axis=-1).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return buf.getvalue()


@lru_cache(maxsize=96)
def _tuile(z, x, y, cache_hour):
    bounds = _tuile_bounds(z, x, y)
    transform = from_bounds(*bounds, SIZE, SIZE)
    a = np.full((SIZE, SIZE), np.nan, dtype="float32")
    ile = _ile()
    if ile is not None and not ile.intersects(box(*bounds)):
        return _terrarium(np.zeros_like(a)), "mer"

    sources = []
    settings = get_settings()
    if z >= 17:
        # Marge pour interpoler aux bords depuis les mêmes pixels que la tuile voisine.
        terrain = transform_bounds("EPSG:3857", "EPSG:2975", *bounds)
        chemin, _ = sol.obtenir_fenetre(*terrain, marge=2)
        if chemin is not None:
            sources.append((chemin, "lidar-0.5m"))
        sources.append((settings.mnt1m_cog_file, "fond-1m"))
    sources.append((settings.mnt5m_file, "rge-5m"))
    utilisees = []
    for chemin, label in sources:
        if not chemin.is_file():
            continue
        try:
            grille = _lire(chemin, transform)
        except rasterio.errors.RasterioIOError:
            continue
        masque = ~np.isfinite(a) & np.isfinite(grille)
        if masque.any():
            a[masque] = grille[masque]
            utilisees.append(label)
        if np.isfinite(a).all():
            break
    if not utilisees:
        raise HTTPException(503, "Relief IGN indisponible")
    if not np.isfinite(a).all():
        # Le Terrarium n'a pas de NoData. Seule la mer peut prendre la cote zéro.
        from rasterio.features import geometry_mask
        if ile is None or ile.contains(box(*bounds)):
            raise HTTPException(503, "Couverture du relief incomplète")
        interieur = ile.buffer(-max(6.0, transform.a))
        terre = geometry_mask([interieur], out_shape=a.shape, transform=transform, invert=True)
        manquants = ~np.isfinite(a)
        if np.any(terre & manquants):
            # Le trait de côte vectoriel peut dépasser de quelques cellules le MNT.
            # Limiter le raccord au littoral et à deux cellules du RGE ALTI 5 m
            # (12 m en Web Mercator à La Réunion). Lire aussi la tuile voisine.
            from affine import Affine
            from scipy.ndimage import distance_transform_edt

            coeur = geometry_mask([ile.buffer(-max(35.0, transform.a))],
                                  out_shape=a.shape, transform=transform, invert=True)
            if np.any(coeur & manquants) or not settings.mnt5m_file.is_file():
                raise HTTPException(503, "Couverture du relief incomplète")
            marge = int(np.ceil(12.0 / transform.a))
            fenetre = transform * Affine.translation(-marge, -marge)
            try:
                fond = _lire(settings.mnt5m_file, fenetre, SIZE + 2 * marge)
            except rasterio.errors.RasterioIOError as exc:
                raise HTTPException(503, "Relief IGN indisponible") from exc
            if not np.isfinite(fond).any():
                raise HTTPException(503, "Couverture du relief incomplète")
            distances, indices = distance_transform_edt(~np.isfinite(fond), return_indices=True)
            centre = np.s_[marge:marge + SIZE, marge:marge + SIZE]
            proche = distances[centre] * transform.a <= 12.0
            if np.any(terre & manquants & ~proche):
                raise HTTPException(503, "Couverture du relief incomplète")
            littoral = geometry_mask([ile], out_shape=a.shape, transform=transform, invert=True)
            raccord = littoral & manquants & proche
            a[raccord] = fond[indices[0][centre][raccord], indices[1][centre][raccord]]
            if "rge-5m" not in utilisees:
                utilisees.append("rge-5m")
        a[~np.isfinite(a)] = 0
    return _terrarium(a), "+".join(utilisees)


@router.get("/map/tiles/relief/{z}/{x}/{y}.png")
def relief(z: int, x: int, y: int):
    if not (8 <= z <= 19 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(404)
    contenu, source = _tuile(z, x, y, int(monotonic() // 3600))
    return Response(contenu, media_type="image/png", headers={
        "Cache-Control": "public, max-age=3600", "X-Relief-Source": source,
    })
