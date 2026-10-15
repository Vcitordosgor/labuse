"""Terrain : assiette fusionnée, limites classées, zone d'implantation réglementaire, contraintes.

Tout en EPSG:2975 (métrique, La Réunion). Réutilise :
  - `ST_Union(geom_2975)` pour fusionner les parcelles (patron assemblage.py) ;
  - `gabarit.limites.classify_parcel_limits(sub_geom_wkt=...)` pour la classification voie/séparative ;
  - shapely buffer/difference pour la zone d'implantation (patron gabarit/engine.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from shapely import wkt as shp_wkt
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

# contraintes cartographiques cherchées sur l'assiette (kind dans spatial_layers)
_CONTRAINTES = ("ppr", "emplacement_reserve", "ebc", "sup", "servitude")


@dataclass
class Parcelle:
    idu: str
    numero: str
    contenance_m2: Optional[float]
    aire_dessin_m2: float
    geom_2975: Optional[Polygon] = None


@dataclass
class Terrain:
    insee: str
    commune: str
    parcelles: list[Parcelle]
    assiette: Polygon                 # 2975
    contenance_totale_m2: float       # somme des contenances cadastrales (fait foi)
    aire_dessin_m2: float             # aire du dessin fusionné
    zone_implantation: Polygon        # 2975, après reculs
    aire_zone_m2: float
    voie_edges: list[LineString]      # arêtes classées « voie » (2975)
    autres_edges: list[LineString]    # side / rear / nonclass
    has_voie: bool
    note_limites: Optional[str]       # réserve (ex. arête nonclass), non bloquante
    contraintes: dict[str, int] = field(default_factory=dict)  # kind -> nb d'objets intersectant

    @property
    def contraintes_presentes(self) -> list[str]:
        return [k for k, n in self.contraintes.items() if n > 0]


def _plus_grand_polygone(geom: BaseGeometry) -> Polygon:
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    return geom


def charger(session, idus: list[str], *, recul_voie_m: float, recul_separative_m: float,
            inset_m: float = 0.0) -> Terrain:
    from sqlalchemy import text
    from labuse.gabarit.limites import classify_parcel_limits

    rows = session.execute(text(
        "SELECT id, idu, numero, commune, contenance_m2, ST_Area(geom_2975) AS aire, "
        "ST_AsText(geom_2975) AS wkt FROM parcels WHERE idu = ANY(:i) ORDER BY numero"
    ), {"i": idus}).mappings().all()
    if len(rows) != len(idus):
        trouves = {r["idu"] for r in rows}
        manquantes = [i for i in idus if i not in trouves]
        raise ValueError(f"parcelles introuvables : {manquantes}")

    ids = [r["id"] for r in rows]
    commune = rows[0]["commune"]
    insee = idus[0][:5]
    parcelles = [Parcelle(idu=r["idu"], numero=r["numero"],
                          contenance_m2=float(r["contenance_m2"]) if r["contenance_m2"] is not None else None,
                          aire_dessin_m2=float(r["aire"]),
                          geom_2975=shp_wkt.loads(r["wkt"]) if r["wkt"] else None) for r in rows]

    aw = session.execute(text("SELECT ST_AsText(ST_Union(geom_2975)) FROM parcels WHERE id = ANY(:i)"),
                         {"i": ids}).scalar()
    assiette = _plus_grand_polygone(shp_wkt.loads(aw))
    aire_dessin = float(assiette.area)
    contenance_totale = sum((p.contenance_m2 or p.aire_dessin_m2) for p in parcelles)

    # classification des limites sur l'assiette fusionnée
    res = classify_parcel_limits(session, ids[0], sub_geom_wkt=aw)
    voie_edges, autres_edges = [], []
    for e in (res.edges if res else []):
        (voie_edges if e.type == "voie" else autres_edges).append(e.geom)
    has_voie = bool(res and res.has_voie)
    # l'arête nonclass est signalée mais NON bloquante : traitée en recul séparatif (prudent)
    note = None
    if res and res.non_classees:
        note = ("arêtes non qualifiées (ni voie ni voisin cadastré ≤ 0,5 m), traitées en recul "
                "séparatif : " + " ; ".join(res.non_classees))

    # zone d'implantation = assiette − reculs (voie 4 m, séparative 3 m sur tout le reste)
    bufs = [g.buffer(recul_voie_m) for g in voie_edges] + \
           [g.buffer(recul_separative_m) for g in autres_edges]
    zone = assiette.difference(unary_union(bufs)) if bufs else assiette
    zone = _plus_grand_polygone(zone)
    if inset_m > 0 and not zone.is_empty:
        zone = _plus_grand_polygone(zone.buffer(-inset_m))

    contraintes = {}
    for kind in _CONTRAINTES:
        n = session.execute(text(
            "SELECT count(*) FROM spatial_layers WHERE kind = :k "
            "AND ST_Intersects(geom_2975, ST_GeomFromText(:g, 2975))"
        ), {"k": kind, "g": aw}).scalar()
        contraintes[kind] = int(n or 0)

    return Terrain(
        insee=insee, commune=commune, parcelles=parcelles,
        assiette=assiette, contenance_totale_m2=contenance_totale, aire_dessin_m2=aire_dessin,
        zone_implantation=zone, aire_zone_m2=float(zone.area),
        voie_edges=voie_edges, autres_edges=autres_edges, has_voie=has_voie, note_limites=note,
        contraintes=contraintes,
    )
