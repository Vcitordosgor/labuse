"""GABARIT-3D-3 (LOT 2) — le SOL réellement mesuré : LiDAR HD MNT 0,5 m (IGN), par parcelle.

La coupe ET le maillage lisent le relief FIN de l'IGN (couche WMS `HIGHRES`, 0,5 m), demandé pour la
fenêtre de la parcelle À L'OUVERTURE. Chaque fenêtre obtenue est GARDÉE en copie locale
(`data/mnt_hr_cache/`) et resservie SANS appel extérieur ; le dossier est plafonné à 1 Go et les copies
les plus anciennes sont écartées (LRU sur l'horodatage d'accès). Délai d'appel COURT ; si le service ne
répond pas : repli sur la copie si elle existe, sinon sur le fond 1 m — et la vue le DIT en clair (meta).
Jamais d'écran cassé, jamais un relief inventé. Aucun secret ni clé dans l'appel (WMS public geopf.fr).

`appels_wms` compte les appels EXTÉRIEURS réellement émis (preuve : 2ᵉ ouverture = 0).
Réglages par env (jamais de secret) : `LABUSE_GAB_SOL_WMS` (base WMS — pour COUPER le service en recette),
`LABUSE_GAB_SOL_TIMEOUT_S` (défaut 4), `LABUSE_GAB_SOL_CACHE` (dossier), `LABUSE_GAB_SOL_CACHE_MAX` (octets).
"""
from __future__ import annotations

import math
import os
import time
from pathlib import Path

import numpy as np

WMS_DEFAUT = "https://data.geopf.fr/wms-r/wms"
HR_LAYER = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"   # MNT 0,5 m (sol LiDAR HD)
RES = 0.5
NODATA = -9999.0
_CACHE_MAX_DEFAUT = 1024 ** 3                          # 1 Go

appels_wms = {"n": 0}                                  # compteur d'appels EXTÉRIEURS (recette : 2e = 0)


def _repo_root() -> Path:
    from ..config import _repo_root as rr
    return rr()


def cache_dir() -> Path:
    d = Path(os.environ.get("LABUSE_GAB_SOL_CACHE", "data/mnt_hr_cache"))
    d = d if d.is_absolute() else _repo_root() / d
    d.mkdir(parents=True, exist_ok=True)
    return d


def _wms_base() -> str:
    return os.environ.get("LABUSE_GAB_SOL_WMS", WMS_DEFAUT)


def _timeout_s() -> float:
    return float(os.environ.get("LABUSE_GAB_SOL_TIMEOUT_S", "4"))


def _cache_max() -> int:
    return int(os.environ.get("LABUSE_GAB_SOL_CACHE_MAX", str(_CACHE_MAX_DEFAUT)))


def _fenetre(minx, miny, maxx, maxy, marge):
    """Fenêtre snappée sur des mètres entiers (clé de cache stable), largeur en pixels à 0,5 m."""
    x0, y0 = int(math.floor(minx - marge)), int(math.floor(miny - marge))
    x1, y1 = int(math.ceil(maxx + marge)), int(math.ceil(maxy + marge))
    return x0, y0, x1, y1


def _cle(x0, y0, x1, y1) -> str:
    return f"hr_{x0}_{y0}_{x1}_{y1}.tif"


def taille_cache() -> tuple[int, int]:
    """(octets, nb fichiers) du dossier de copies."""
    fichiers = list(cache_dir().glob("hr_*.tif"))
    return sum(f.stat().st_size for f in fichiers), len(fichiers)


def _evict_lru(cap: int) -> None:
    """Écarte les copies les PLUS ANCIENNES (dernier accès) tant que le dossier dépasse `cap`."""
    fichiers = list(cache_dir().glob("hr_*.tif"))
    total = sum(f.stat().st_size for f in fichiers)
    if total <= cap:
        return
    for f in sorted(fichiers, key=lambda p: p.stat().st_atime):   # le plus ancien accès d'abord
        if total <= cap:
            break
        try:
            total -= f.stat().st_size
            f.unlink()
        except OSError:
            pass


def _fetch_wms(x0, y0, x1, y1) -> bytes:
    """GetMap WMS (GeoTIFF Float32, 0,5 m) — AUCUNE clé ni secret. Lève sur échec/timeout."""
    import httpx
    w, h = (x1 - x0) * 2, (y1 - y0) * 2                 # 0,5 m
    params = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "STYLES": "",
              "CRS": "EPSG:2975", "FORMAT": "image/geotiff", "WIDTH": str(w), "HEIGHT": str(h),
              "BBOX": f"{x0},{y0},{x1},{y1}", "LAYERS": HR_LAYER}
    appels_wms["n"] += 1
    r = httpx.get(_wms_base(), params=params, timeout=_timeout_s())
    r.raise_for_status()
    return r.content


def obtenir_fenetre(minx, miny, maxx, maxy, marge):
    """Rend (chemin_tif, source) pour la fenêtre : source ∈ {'copie', 'lidar_05m'} ; (None, None) si le
    service ne répond pas ET qu'aucune copie n'existe (→ l'appelant replie sur le fond 1 m).

    Copie d'abord (0 appel extérieur) ; sinon appel WMS court, écriture en cache + éviction LRU."""
    x0, y0, x1, y1 = _fenetre(minx, miny, maxx, maxy, marge)
    f = cache_dir() / _cle(x0, y0, x1, y1)
    if f.exists():
        os.utime(f, None)                               # marque l'accès (LRU) → resservi sans appel
        return f, "copie"
    try:
        contenu = _fetch_wms(x0, y0, x1, y1)
    except Exception:  # noqa: BLE001 — service indisponible/timeout : pas d'écran cassé, l'appelant replie
        return None, None
    tmp = f.with_suffix(".tmp")
    tmp.write_bytes(contenu)
    os.replace(tmp, f)                                  # écriture atomique
    _evict_lru(_cache_max())
    return f, "lidar_05m"


def acquisition(db, minx, miny, maxx, maxy) -> str | None:
    """Date d'acquisition LiDAR HD lue DANS LA DONNÉE (grille des dalles/missions) pour la fenêtre."""
    try:
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT max(date_fin) FROM lidar_dalle_grille "
            "WHERE x0 < :x1 AND x1 > :x0 AND y0 < :y1 AND y1 > :y0"),
            {"x0": minx, "y0": miny, "x1": maxx, "y1": maxy}).scalar()
        return str(row) if row else None
    except Exception:  # noqa: BLE001 — table absente/base lente : date inconnue, pas d'erreur
        return None


def lire_tif(chemin: Path):
    """(array float, ox, oy, pas) d'un GeoTIFF en cache — lecture pixel-native."""
    import rasterio
    with rasterio.open(chemin) as ds:
        a = ds.read(1).astype("float64")
        tr = ds.transform
    a[(a <= -1000.0) | ~np.isfinite(a)] = np.nan
    return a, float(tr.c), float(tr.f), float(tr.a)
