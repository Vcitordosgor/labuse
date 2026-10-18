"""Contexte cartographique de la PLANCHE plan masse (façon archi) — tout en EPSG:2975.

Rassemble, autour de l'assiette, ce que l'archi dessine en fond de plan : parcelles VOISINES (avec
leur numéro), bâti voisin (BD TOPO, `spatial_layers kind='batiment'`), voies NOMMÉES (`kind='voirie'`),
et le terrain naturel (TN) échantillonné au LiDAR (`rgealti_mnt_5m`) aux angles de l'assiette.

Lecture seule, tolérante : chaque requête qui échoue (tuile absente, couche non ingérée) renvoie vide
→ la planche se dessine avec ce qui est disponible (dégradation gracieuse, comme la maquette).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from shapely import wkt as shp_wkt
from shapely.geometry.base import BaseGeometry

_RAYON_VOISINS_M = 40.0      # parcelles + bâti voisins dessinés jusqu'à 40 m de l'assiette
_RAYON_VOIES_M = 30.0        # voies nommées jusqu'à 30 m


@dataclass
class Voisin:
    numero: str
    geom_2975: BaseGeometry


@dataclass
class Voie:
    nom: str
    geom_2975: BaseGeometry


@dataclass
class Contexte:
    voisins: list[Voisin] = field(default_factory=list)
    batis_voisins: list[BaseGeometry] = field(default_factory=list)
    voies: list[Voie] = field(default_factory=list)
    tn_coins: list[dict] = field(default_factory=list)   # [{x, y, alt_m|None}] aux angles de la bbox


def _rows(session, sql: str, params: dict):
    from sqlalchemy import text
    try:
        return session.execute(text(sql), params).fetchall()
    except Exception:
        return []


def _voisins(session, aw_wkt: str, idus: list[str]) -> list[Voisin]:
    rows = _rows(session,
        "SELECT numero, ST_AsText(geom_2975) AS wkt FROM parcels "
        "WHERE geom_2975 IS NOT NULL AND idu <> ALL(:idus) "
        "AND ST_DWithin(geom_2975, ST_GeomFromText(:g,2975), :r) "
        "AND NOT ST_Contains(ST_GeomFromText(:g,2975), geom_2975) "
        "ORDER BY numero LIMIT 60",
        {"idus": idus, "g": aw_wkt, "r": _RAYON_VOISINS_M})
    out = []
    for numero, w in rows:
        if not w:
            continue
        try:
            out.append(Voisin(str(numero or "").strip(), shp_wkt.loads(w)))
        except Exception:
            continue
    return out


def _batis(session, aw_wkt: str) -> list[BaseGeometry]:
    rows = _rows(session,
        "SELECT ST_AsText(geom_2975) AS wkt FROM spatial_layers "
        "WHERE kind='batiment' AND geom_2975 IS NOT NULL "
        "AND ST_DWithin(geom_2975, ST_GeomFromText(:g,2975), :r) "
        "AND NOT ST_Intersects(geom_2975, ST_GeomFromText(:g,2975)) LIMIT 400",
        {"g": aw_wkt, "r": _RAYON_VOISINS_M})
    out = []
    for (w,) in rows:
        if not w:
            continue
        try:
            g = shp_wkt.loads(w)
            if not g.is_empty:
                out.append(g)
        except Exception:
            continue
    return out


def _voies(session, aw_wkt: str) -> list[Voie]:
    """Voies NOMMÉES près de l'assiette. Géométrie = lignes `voirie` (BD TOPO) ; le NOM = toponyme de
    l'adresse (BAN) la plus proche (`adresses.voie` = « Avenue Raymond Barre »…), car `voirie.name` ne
    porte que la NATURE (« Route à 1 chaussée »). On replie sur la nature si aucune adresse à proximité."""
    rows = _rows(session,
        "SELECT v.name, "
        "  (SELECT a.voie FROM adresses a WHERE a.geom_2975 IS NOT NULL "
        "     AND a.voie IS NOT NULL AND a.voie <> '' "
        "   ORDER BY a.geom_2975 <-> v.geom_2975 LIMIT 1) AS toponyme, "
        "  ST_AsText(ST_Intersection(v.geom_2975, ST_Buffer(ST_GeomFromText(:g,2975), :r))) AS wkt "
        "FROM spatial_layers v WHERE v.kind='voirie' "
        "AND ST_DWithin(v.geom_2975, ST_GeomFromText(:g,2975), :r) LIMIT 80",
        {"g": aw_wkt, "r": _RAYON_VOIES_M})
    out = []
    for nature, toponyme, w in rows:
        if not w:
            continue
        try:
            g = shp_wkt.loads(w)
            if g.is_empty:
                continue
            nom = (str(toponyme).strip() if toponyme else "") or (str(nature).strip() if nature else "voie")
            out.append(Voie(nom, g))
        except Exception:
            continue
    return out


def _tn_coins(session, assiette: BaseGeometry, *, avec_ign: bool) -> list[dict]:
    """Altitude LiDAR (TN) aux 4 angles de la bbox de l'assiette. Raster RGE ALTI 5 m EN BASE d'abord
    (rapide) ; là où la tuile manque, complétée au service IGN (même source) si `avec_ign` — comme la
    pente du terrain. Tolérant : altitude None = angle dessiné sans cote (relief non disponible)."""
    from labuse.geo import to_4326
    from shapely.geometry import Point

    minx, miny, maxx, maxy = assiette.bounds
    coins = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)]
    out = []
    for x, y in coins:
        rows = _rows(session,
            "SELECT ST_Value(r.rast, ST_SetSRID(ST_Point(:x,:y),2975)) FROM rgealti_mnt_5m r "
            "WHERE ST_Intersects(r.rast, ST_SetSRID(ST_Point(:x,:y),2975)) LIMIT 1", {"x": x, "y": y})
        alt = None
        if rows and rows[0][0] is not None:
            try:
                alt = round(float(rows[0][0]), 1)
            except Exception:
                alt = None
        p4326 = to_4326(Point(x, y))
        out.append({"x": x, "y": y, "lon": p4326.x, "lat": p4326.y, "alt_m": alt})
    if avec_ign and any(c["alt_m"] is None for c in out):
        try:
            from labuse.faisabilite.profil_altimetrique import _completer_ign
            _completer_ign(out)
        except Exception:
            pass
    for c in out:
        if c["alt_m"] is not None:
            c["alt_m"] = round(float(c["alt_m"]), 1)
    return out


def charger_contexte(session, assiette: BaseGeometry, idus: list[str], *, avec_tn: bool = True) -> Contexte:
    """Contexte complet autour de l'assiette (2975). Tolérant : tout ce qui manque = vide.
    `avec_tn=False` coupe l'appel réseau IGN du TN (tests / rendu rapide)."""
    if session is None or assiette is None or assiette.is_empty:
        return Contexte()
    aw = assiette.wkt
    return Contexte(
        voisins=_voisins(session, aw, idus),
        batis_voisins=_batis(session, aw),
        voies=_voies(session, aw),
        tn_coins=_tn_coins(session, assiette, avec_ign=avec_tn),
    )
