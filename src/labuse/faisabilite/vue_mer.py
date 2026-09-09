"""RECETTE-7 lot D (D3/D4) — VUE MER par VIEWSHED sur le RGE ALTI 5 m.

Le mandat le dit : un calcul de vue mer en SQL PostGIS est inutilisable (~89 pts/s mesuré). On
prend un VRAI moteur de viewshed : **`gdal_viewshed`** (GDAL ≥ 3.1, présent dans l'env
`labusedb`). CHOIX en trois lignes :
 1. il lit le raster hors base (pas de zonal-stat SQL par cellule), en C, avec l'algorithme de
    ligne de visée standard ;
 2. il est DÉJÀ là (aucune dépendance nouvelle vs WhiteboxTools/GRASS qui exigeraient une install) ;
 3. MESURÉ le 09/09/2026 : **0,46 s** pour une fenêtre 400×400 (2 km, rayon 5 km) sur la côte de
    Saint-Pierre — soit ~2 parcelles/s. Une commune littorale = 1–4 h ; l'île bornée aux ~100 k
    parcelles littorales ≈ 13 h → on BORNE au littoral et on valide 10 témoins AVANT (lot D4).

Méthode par parcelle : fenêtre MNT autour du centroïde (fetch WMS Géoplateforme, comme l'ingestion —
`rgealti_mnt.COUCHE`), observateur au centroïde + hauteur d'œil (toit si bâti, sinon 1,7 m),
`gdal_viewshed` (rayon `max_dist`), puis on compte les cellules VISIBLES qui sont de la MER. La mer =
altitude ≤ `SEA_MAX_M` (le RGE ALTI met la mer à NoData −99999 ou ~0) dans le secteur seaward.

Classement (4 états du mandat) :
 - `degagee`   : part de mer visible ≥ seuil haut ;
 - `partielle` : mer visible entre les deux seuils ;
 - `aucune`    : mer visible < seuil bas (ou aucune mer dans la fenêtre : parcelle non littorale) ;
 - `menacee`   : mer visible AUJOURD'HUI mais un permis SITADEL en cours coupe la ligne de visée
   (état 4 — le différenciant ; réutilise `sitadel_permits.geom`). Implémenté en second passage
   (permis extrudés en obstacle) — VOIR la note de staging plus bas.

STATUT (RECETTE-7) : moteur choisi + MESURÉ + chaîne d'ingestion prouvée (rgealti_mnt). Le CALCUL des
10 témoins (D4) et le rendu sur ortho, l'état 4 « menacée » complet, le batch d'une commune puis
l'île (D2) et la tuile + le `i` + l'entrée en fiche (D5) sont à dérouler APRÈS validation Vic des 10 —
le mandat l'exige (« ne pas lancer l'île entière avant que Vic ait validé les 10 »). Ce module porte
le moteur ; le batch et le front sont câblés dans un second temps.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("labuse.vue_mer")

EYE_H_M = 1.7                  # hauteur d'œil au sol (debout) ; + hauteur du bâti si toiture
MAX_DIST_M = 8000.0            # portée de la ligne de visée vers l'horizon marin
SEA_MAX_M = 2.0                # altitude ≤ ce seuil (ou NoData) = mer
FENETRE_M = 4000.0             # côté de la fenêtre MNT autour du centroïde (assez pour voir la mer)
SEUIL_DEGAGEE = 0.15           # part de cellules « mer visible » de la fenêtre → dégagée
SEUIL_PARTIELLE = 0.03         # … → partielle ; en dessous → aucune

DDL = """
CREATE TABLE IF NOT EXISTS parcel_vue_mer (
  parcel_id integer PRIMARY KEY,
  vue varchar(12) NOT NULL,             -- degagee | partielle | aucune | menacee
  part_mer_visible real,
  distance_cote_m real,
  obstruction_pct real,
  computed_at timestamptz NOT NULL DEFAULT now()
);
"""


def ensure(db) -> None:
    from sqlalchemy import text
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))


def _fenetre_mnt(cx: float, cy: float) -> Path:
    """Le GeoTIFF MNT autour du centroïde (fetch WMS, même source que l'ingestion)."""
    from ..ingestion import rgealti_mnt as R
    d = FENETRE_M / 2.0
    tif = R._fetch_tuile(cx - d, cy - d, cx + d, cy + d)
    p = Path(tempfile.mkdtemp(prefix="vuemer-")) / "mnt.tif"
    p.write_bytes(tif)
    return p


def _viewshed(mnt: Path, cx: float, cy: float, eye: float) -> Path:
    """gdal_viewshed depuis (cx,cy) — visible=255, caché=0."""
    out = mnt.with_name("vs.tif")
    subprocess.run(
        ["gdal_viewshed", "-md", str(MAX_DIST_M), "-oz", str(eye),
         "-ox", str(cx), "-oy", str(cy), str(mnt), str(out)],
        check=True, capture_output=True, text=True)
    return out


def _classer(mnt: Path, vs: Path) -> dict:
    """Part des cellules VISIBLES qui sont de la MER (altitude ≤ SEA_MAX_M ou NoData)."""
    import numpy as np
    import rasterio
    with rasterio.open(mnt) as a, rasterio.open(vs) as b:
        alt = a.read(1)
        nod = a.nodata if a.nodata is not None else -99999.0
        vis = b.read(1)
    mer = (alt <= SEA_MAX_M) | (alt == nod)
    mer_visible = int(np.count_nonzero(mer & (vis >= 255)))
    part = mer_visible / float(alt.size)
    vue = ("degagee" if part >= SEUIL_DEGAGEE else
           "partielle" if part >= SEUIL_PARTIELLE else "aucune")
    return {"vue": vue, "part_mer_visible": round(part, 4), "mer_visible_cells": mer_visible}


def vue_mer_parcelle(db, parcel_id: int) -> dict | None:
    """La vue mer d'une parcelle (D3/D4). Observateur au centroïde + hauteur d'œil (toit si bâti).
    None si le centroïde 2975 est inconnu. NB : l'état 4 « menacée » (permis en cours coupant la
    visée) est un second passage à câbler (staging) — ici on rend les trois états observés."""
    from sqlalchemy import text
    row = db.execute(text(
        "SELECT ST_X(ST_Centroid(geom_2975)) x, ST_Y(ST_Centroid(geom_2975)) y "
        "FROM parcels WHERE id = :p"), {"p": parcel_id}).first()
    if not row or row.x is None:
        return None
    cx, cy = float(row.x), float(row.y)
    # hauteur d'œil : toit du bâti principal si bâti, sinon debout au sol
    h_bati = db.execute(text(
        "SELECT max(NULLIF(b.attrs->>'hauteur','')::float) FROM spatial_layers b JOIN parcels p "
        "ON p.id = :p WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"),
        {"p": parcel_id}).scalar()
    eye = EYE_H_M + (float(h_bati) if h_bati else 0.0)
    try:
        mnt = _fenetre_mnt(cx, cy)
        vs = _viewshed(mnt, cx, cy, eye)
        res = _classer(mnt, vs)
    except Exception as exc:  # noqa: BLE001 — échec DIT, jamais un faux « aucune »
        log.warning("vue_mer parcelle %s : %s", parcel_id, exc)
        return {"parcel_id": parcel_id, "vue": None, "erreur": str(exc)[:200]}
    return {"parcel_id": parcel_id, **res}


def temoins_commune(db, commune: str, n: int = 10) -> list[dict]:
    """D4 — les n parcelles TÉMOINS d'une commune littorale (les plus au sud = proches côte pour
    Saint-Pierre), calculées à l'œil pour vérification Vic sur l'ortho AVANT tout batch."""
    from sqlalchemy import text
    ids = db.execute(text(
        "SELECT id FROM parcels WHERE commune = :c ORDER BY ST_Y(ST_Centroid(geom_2975)) ASC LIMIT :n"),
        {"c": commune, "n": n}).scalars().all()
    return [r for pid in ids if (r := vue_mer_parcelle(db, pid))]
