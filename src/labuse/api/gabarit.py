"""Endpoint outil « Gabarit réglementaire » — GET /outils/gabarit/{idu}.

Le front n'affiche que ce que l'API sert (doctrine LABUSE : zéro recalcul au front).
Le calcul est porté par le moteur pur `labuse.gabarit.engine`.

- `/outils/gabarit/demo`  → démonstration sur la parcelle FICTIVE (CDC §9), calcul complet
  (conservée pour les tests ; le bouton de démo est retiré du front en GABARIT-2).
- `/outils/gabarit/{idu}` → raccordement RÉEL (GABARIT-2) : cadastre + PLU + classification
  des limites (BD TOPO) + PPR rouge. Calcul complet si tout est réuni ; sinon « Calcul
  incomplet » + motif métier (parcelle sans façade, limite non qualifiée, PLU non validé…).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..gabarit.builder import build_gabarit_input
from ..gabarit.contract import GabaritResult
from ..gabarit.engine import INCOMPLETE_MESSAGE, compute_gabarit
from ..gabarit.fixtures import demo_gabarit_input

router = APIRouter(prefix="/outils/gabarit", tags=["gabarit"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def _bati_existant(db: Session, idu: str) -> dict | None:
    """GABARIT-6 P4 — le bâti EXISTANT porté par la parcelle : emprise BD TOPO (`spatial_layers`
    kind='batiment') + hauteur LiDAR HD mesurée (`batiment_hauteur_lidar`, au faîtage, par parcelle)
    à défaut la hauteur BD TOPO du bâtiment. C'est un FAIT contextuel (l'outil montre où l'on PEUT
    construire ; ceci montre ce qui est DÉJÀ là) : aucun calcul réglementaire n'en dépend.

    On retient les bâtiments MAJORITAIREMENT sur la parcelle (≥ 50 % de leur emprise) ou d'emprise
    intersectée ≥ 20 m² — écarte les débords de voisins. Emprise entière servie (schéma fidèle).
    Renvoie une FeatureCollection (4326) ou None si la parcelle ne porte aucun bâti."""
    lid = db.execute(text(
        "SELECT faitage_m FROM batiment_hauteur_lidar WHERE idu = :i"), {"i": idu}).scalar()
    lidar_faitage = float(lid) if lid is not None else None
    rows = db.execute(text(
        "SELECT ST_AsGeoJSON(ST_Transform(s.geom_2975, 4326)) AS gj, "
        "       (s.attrs->>'hauteur')::float AS h_bdtopo "
        "FROM spatial_layers s JOIN parcels p ON p.idu = :i "
        "WHERE s.kind = 'batiment' AND ST_Intersects(s.geom_2975, p.geom_2975) "
        "  AND (ST_Area(ST_Intersection(s.geom_2975, p.geom_2975)) >= 0.5 * ST_Area(s.geom_2975) "
        "       OR ST_Area(ST_Intersection(s.geom_2975, p.geom_2975)) >= 20.0)"
    ), {"i": idu}).mappings().all()
    feats = []
    for r in rows:
        if not r["gj"]:
            continue
        h_bdtopo = float(r["h_bdtopo"]) if r["h_bdtopo"] is not None else None
        # hauteur mesurée LiDAR (au faîtage) prioritaire ; repli sur la hauteur BD TOPO du bâtiment
        hauteur = lidar_faitage if lidar_faitage is not None else h_bdtopo
        feats.append({
            "type": "Feature",
            "properties": {
                "hauteur_m": round(hauteur, 1) if hauteur is not None else None,
                "h_source": "lidar" if lidar_faitage is not None else ("bdtopo" if h_bdtopo is not None else None),
            },
            "geometry": json.loads(r["gj"]),
        })
    if not feats:
        return None
    return {"type": "FeatureCollection", "features": feats}


@router.get("/{idu}", response_model=GabaritResult)
def gabarit_detail(idu: str, db: Session = Depends(get_db)) -> GabaritResult:
    if idu == "demo":
        res = compute_gabarit(demo_gabarit_input())
        res.raccordement = {"mode": "fixtures",
                            "avertissement": "Données FICTIVES de démonstration (CDC §9)"}
        return res

    build = build_gabarit_input(db, idu)
    if build is None:
        raise HTTPException(404, f"Parcelle inconnue : {idu}")

    if build.blocking:
        # GABARIT-6 lot B : calcul incomplet, mais la parcelle reste VISIBLE. On sert le contour
        # cadastral + la référence/commune (via raccordement.parcelle) pour que la carte centre sur
        # la parcelle et que le panneau l'identifie AU-DESSUS du motif — jamais un écran vide.
        parcel = build.input.parcel if build.input else None
        return GabaritResult(status="incomplete", message=INCOMPLETE_MESSAGE,
                             validationErrors=build.blocking, raccordement=build.raccordement,
                             contourGeoJSON=parcel.geometry if parcel else None,
                             surfaceParcelleM2=parcel.areaM2 if parcel else None,
                             batiExistantGeoJSON=_bati_existant(db, idu))

    res = compute_gabarit(build.input)
    res.raccordement = build.raccordement
    # FRONT-CHIFFRES-2 (F57/F50) — % « à cheval » calculé ICI, une seule fois : round(portion / cadastre
    # × 100), même arithmétique que les deux sites front qui le recomputaient (GabaritLine + panneau).
    _rac = build.raccordement or {}
    _cad = (_rac.get("parcelle") or {}).get("surface_m2")
    if (_rac.get("zone") or {}).get("a_cheval") and _cad and res.surfaceParcelleM2 is not None:
        res.pctPortionZone = round(res.surfaceParcelleM2 / _cad * 100)
    res.batiExistantGeoJSON = _bati_existant(db, idu)
    return res
