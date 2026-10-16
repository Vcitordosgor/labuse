"""Terrain : assiette fusionnée, limites classées, zone d'implantation réglementaire, contraintes.

Tout en EPSG:2975 (métrique, La Réunion). Réutilise :
  - `ST_Union(geom_2975)` pour fusionner les parcelles (patron assemblage.py) ;
  - `gabarit.limites.classify_parcel_limits(sub_geom_wkt=...)` pour la classification voie/séparative ;
  - shapely buffer/difference pour la zone d'implantation (patron gabarit/engine.py).

IMPLANTATION-1BIS : PPR rouge (interdiction) DÉDUITE de la zone d'implantation ; PPR bleue
(prescription) conservée pour tester si elle touche le bâti proposé. Dénivelé LiDAR reporté
(fait contextuel), non pris en compte dans le volume.
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
    assiette: Polygon
    contenance_totale_m2: float
    aire_dessin_m2: float
    zone_implantation: Polygon            # 2975, après reculs ET déduction PPR rouge
    aire_zone_m2: float
    voie_edges: list[LineString]
    autres_edges: list[LineString]
    has_voie: bool
    note_limites: Optional[str]
    contraintes: dict[str, int] = field(default_factory=dict)
    ppr_rouge: Optional[BaseGeometry] = None      # interdiction, déduite de la zone
    ppr_bleue: Optional[BaseGeometry] = None       # prescription, signalée
    ppr_rouge_m2: float = 0.0
    ppr_bleue_m2: float = 0.0
    pente: Optional[dict] = None                   # dénivelé LiDAR (fait contextuel)

    @property
    def ecart_contenance_dessin_m2(self) -> float:
        return self.contenance_totale_m2 - self.aire_dessin_m2

    @property
    def contraintes_presentes(self) -> list[str]:
        return [k for k, n in self.contraintes.items() if n > 0]


def _plus_grand_polygone(geom: BaseGeometry) -> Polygon:
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    return geom


def _ppr_par_couleur(session, aw: str):
    """(geom_rouge, geom_bleue) sur l'assiette. rouge = interdiction, bleue = prescription."""
    from sqlalchemy import text
    rows = session.execute(text(
        "SELECT subtype, ST_AsText(ST_Intersection(geom_2975, ST_GeomFromText(:g,2975))) AS wkt "
        "FROM spatial_layers WHERE kind='ppr' AND ST_Intersects(geom_2975, ST_GeomFromText(:g,2975))"
    ), {"g": aw}).fetchall()
    rouges, bleues = [], []
    for sub, wkt in rows:
        if not wkt:
            continue
        g = shp_wkt.loads(wkt)
        s = (sub or "").lower()
        if "interdict" in s or "rouge" in s:
            rouges.append(g)
        elif "prescript" in s or "bleu" in s:
            bleues.append(g)
    rouge = unary_union(rouges) if rouges else None
    bleue = unary_union(bleues) if bleues else None
    return rouge, bleue


def _pente_lidar(session, parcelles: list[Parcelle]) -> Optional[dict]:
    """Dénivelé/pente via le profil altimétrique LiDAR (RGE ALTI). Réseau requis ; None si indisponible."""
    try:
        from labuse.faisabilite.profil_altimetrique import profil_parcelle
    except Exception:
        return None
    idu = max(parcelles, key=lambda p: p.aire_dessin_m2).idu
    try:
        prof = profil_parcelle(session, idu)
    except Exception:
        return None
    if not prof or not prof.get("disponible"):
        return {"disponible": False, "motif": (prof or {}).get("motif")}
    return {"disponible": True, "source": prof.get("source"),
            "denivele_m": round(prof.get("denivele_positif_m", 0.0) + prof.get("denivele_negatif_m", 0.0), 1),
            "pente_moyenne_pct": prof.get("pente_moyenne_pct"), "pente_max_pct": prof.get("pente_max_pct")}


def charger(session, idus: list[str], *, recul_voie_m: float, recul_separative_m: float,
            inset_m: float = 0.0, avec_pente: bool = True) -> Terrain:
    from sqlalchemy import text
    from labuse.gabarit.limites import classify_parcel_limits

    rows = session.execute(text(
        "SELECT id, idu, numero, commune, contenance_m2, ST_Area(geom_2975) AS aire, "
        "ST_AsText(geom_2975) AS wkt FROM parcels WHERE idu = ANY(:i) ORDER BY numero"
    ), {"i": idus}).mappings().all()
    if len(rows) != len(idus):
        trouves = {r["idu"] for r in rows}
        raise ValueError(f"parcelles introuvables : {[i for i in idus if i not in trouves]}")

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

    res = classify_parcel_limits(session, ids[0], sub_geom_wkt=aw)
    voie_edges, autres_edges = [], []
    for e in (res.edges if res else []):
        (voie_edges if e.type == "voie" else autres_edges).append(e.geom)
    has_voie = bool(res and res.has_voie)
    note = None
    if res and res.non_classees:
        note = ("arêtes non qualifiées (ni voie ni voisin cadastré ≤ 0,5 m), traitées en recul "
                "séparatif : " + " ; ".join(res.non_classees))

    # zone = assiette − reculs (voie 4 m, séparative 3 m sur tout le reste) − PPR rouge
    bufs = [g.buffer(recul_voie_m) for g in voie_edges] + \
           [g.buffer(recul_separative_m) for g in autres_edges]
    zone = assiette.difference(unary_union(bufs)) if bufs else assiette

    ppr_rouge, ppr_bleue = _ppr_par_couleur(session, aw)
    if ppr_rouge is not None and not ppr_rouge.is_empty:
        zone = zone.difference(ppr_rouge)
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
    contraintes["ppr_rouge"] = 1 if (ppr_rouge is not None and not ppr_rouge.is_empty) else 0
    contraintes["ppr_bleue"] = 1 if (ppr_bleue is not None and not ppr_bleue.is_empty) else 0

    pente = _pente_lidar(session, parcelles) if avec_pente else None

    return Terrain(
        insee=insee, commune=commune, parcelles=parcelles,
        assiette=assiette, contenance_totale_m2=contenance_totale, aire_dessin_m2=aire_dessin,
        zone_implantation=zone, aire_zone_m2=float(zone.area),
        voie_edges=voie_edges, autres_edges=autres_edges, has_voie=has_voie, note_limites=note,
        contraintes=contraintes,
        ppr_rouge=ppr_rouge, ppr_bleue=ppr_bleue,
        ppr_rouge_m2=round(ppr_rouge.area, 1) if (ppr_rouge is not None and not ppr_rouge.is_empty) else 0.0,
        ppr_bleue_m2=round(ppr_bleue.area, 1) if (ppr_bleue is not None and not ppr_bleue.is_empty) else 0.0,
        pente=pente,
    )
