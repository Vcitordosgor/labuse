"""RECETTE-8 W22 — L'EXPOSITION de la parcelle, à la place de la vue mer.

Vic a tranché : on arrête la vue mer (55 h de calcul pour une donnée dont l'affirmation la plus
vendeuse — « vue dégagée » — est la moins fiable). L'exposition prend sa place : elle se calcule
LOCALEMENT sur le MNT (RGE ALTI, la même source que le viewshed abandonné), SANS ligne de vue —
juste l'orientation du versant et sa pente moyenne autour de la parcelle.

Méthode : une petite fenêtre MNT (200 m) autour du centroïde → `gdaldem aspect` (orientation du
plus grand pente, 0°=N horaire) + `gdaldem slope` (pente en degrés). On fait la MOYENNE VECTORIELLE
des orientations, PONDÉRÉE par la pente (une cellule plate n'a pas d'orientation défendable), pour
obtenir l'octant dominant (Nord, Nord-Est, …) et la pente moyenne. Terrain quasi plat → « plat »
(aucune exposition marquée), jamais une orientation inventée sur du bruit.

Aucun ray-casting, aucune fenêtre de 4 km : c'est ~100× moins cher que le viewshed (mesuré au
rapport). Le code de viewshed (faisabilite/vue_mer.py) n'est plus servi ; il reste en historique.
"""
from __future__ import annotations

import logging
import math
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("labuse.exposition")

FENETRE_M = 200.0          # côté de la fenêtre MNT autour du centroïde (le versant immédiat)
PENTE_PLATE_DEG = 3.0      # sous ce seuil de pente MOYENNE, le terrain est « plat » (pas d'expo marquée)
PENTE_MIN_CELL_DEG = 2.0   # une cellule sous ce seuil ne pèse pas dans la moyenne d'orientation

#: les 8 octants (bornes en degrés, 0°=Nord, sens horaire) → libellé humain.
_OCTANTS = [
    (22.5, "Nord"), (67.5, "Nord-Est"), (112.5, "Est"), (157.5, "Sud-Est"),
    (202.5, "Sud"), (247.5, "Sud-Ouest"), (292.5, "Ouest"), (337.5, "Nord-Ouest"), (360.0, "Nord"),
]


def _octant(deg: float) -> str:
    d = deg % 360.0
    for borne, lib in _OCTANTS:
        if d < borne:
            return lib
    return "Nord"


def _fenetre_mnt(cx: float, cy: float) -> Path:
    """Le GeoTIFF MNT (RGE ALTI) autour du centroïde — même fetch que l'ingestion/viewshed, mais
    une PETITE fenêtre (l'exposition ne regarde que le versant immédiat, pas l'horizon)."""
    from ..ingestion import rgealti_mnt as R
    d = FENETRE_M / 2.0
    tif = R._fetch_tuile(cx - d, cy - d, cx + d, cy + d)
    p = Path(tempfile.mkdtemp(prefix="expo-")) / "mnt.tif"
    p.write_bytes(tif)
    return p


def _gdaldem(mnt: Path, mode: str) -> Path:
    out = mnt.with_name(f"{mode}.tif")
    subprocess.run(["gdaldem", mode, str(mnt), str(out), "-compute_edges"],
                   check=True, capture_output=True, text=True)
    return out


def _calculer(mnt: Path) -> dict | None:
    """Orientation dominante (moyenne vectorielle pondérée pente) + pente moyenne, depuis le MNT."""
    import numpy as np
    import rasterio
    asp_p = _gdaldem(mnt, "aspect")
    slp_p = _gdaldem(mnt, "slope")
    with rasterio.open(asp_p) as a, rasterio.open(slp_p) as s:
        aspect = a.read(1).astype("float64")
        asp_nod = a.nodata
        slope = s.read(1).astype("float64")
        slp_nod = s.nodata
    ok = np.ones(aspect.shape, dtype=bool)
    if asp_nod is not None:
        ok &= aspect != asp_nod
    if slp_nod is not None:
        ok &= slope != slp_nod
    # gdaldem met aspect = -9999 pour les cellules plates : on les exclut de l'orientation.
    ok &= aspect >= 0
    pente_moy = float(np.mean(slope[ok])) if ok.any() else 0.0
    porteuses = ok & (slope >= PENTE_MIN_CELL_DEG)
    if not porteuses.any():
        return {"orientation": "plat", "aspect_deg": None, "pente_moyenne_deg": round(pente_moy, 1)}
    # moyenne VECTORIELLE des orientations (aspect 0°=N horaire), pondérée par la pente.
    rad = np.deg2rad(aspect[porteuses])
    w = slope[porteuses]
    vx = float(np.sum(w * np.sin(rad)))   # composante Est
    vy = float(np.sum(w * np.cos(rad)))   # composante Nord
    aspect_moy = (math.degrees(math.atan2(vx, vy))) % 360.0
    plat = pente_moy < PENTE_PLATE_DEG
    return {
        "orientation": "plat" if plat else _octant(aspect_moy),
        "aspect_deg": None if plat else round(aspect_moy, 1),
        "pente_moyenne_deg": round(pente_moy, 1),
    }


def exposition_parcelle(db, parcel_id: int) -> dict | None:
    """L'exposition d'une parcelle (W22). None si le centroïde 2975 est inconnu. En cas d'échec de
    fetch/gdaldem : `{orientation: None, erreur}` — dit, jamais un faux « plat »."""
    from sqlalchemy import text
    row = db.execute(text(
        "SELECT ST_X(ST_Centroid(geom_2975)) x, ST_Y(ST_Centroid(geom_2975)) y "
        "FROM parcels WHERE id = :p"), {"p": parcel_id}).first()
    if not row or row.x is None:
        return None
    try:
        mnt = _fenetre_mnt(float(row.x), float(row.y))
        res = _calculer(mnt)
    except Exception as exc:  # noqa: BLE001 — échec DIT
        log.warning("exposition parcelle %s : %s", parcel_id, exc)
        return {"parcel_id": parcel_id, "orientation": None, "erreur": str(exc)[:200]}
    return {"parcel_id": parcel_id, **(res or {})}
