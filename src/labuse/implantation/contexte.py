"""Contexte cartographique de la PLANCHE plan masse (façon archi) — tout en EPSG:2975.

Rassemble, autour de l'assiette, ce que l'archi dessine en fond de plan : parcelles VOISINES (avec
leur numéro), bâti voisin (BD TOPO, `spatial_layers kind='batiment'`), voies NOMMÉES (`kind='voirie'`),
et le terrain naturel (TN) échantillonné au LiDAR (`rgealti_mnt_5m`) aux angles de l'assiette.

Lecture seule, tolérante : chaque requête qui échoue (tuile absente, couche non ingérée) renvoie vide
→ la planche se dessine avec ce qui est disponible (dégradation gracieuse, comme la maquette).
"""
from __future__ import annotations

import math
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
    # DOCS-COHERENCE-1 (F1) — bâti EXISTANT SUR l'assiette (BD TOPO) : dessiné en gris pointillé
    # « supposé démoli » quand l'étude est menée terrain libéré. Même source que batis_voisins.
    batis_assiette: list[BaseGeometry] = field(default_factory=list)
    voies: list[Voie] = field(default_factory=list)
    tn_coins: list[dict] = field(default_factory=list)   # [{x, y, alt_m|None}] aux angles de la bbox
    # axe de coupe (perpendiculaire à la voie, passant par l'assiette) + profil TN le long de cet axe,
    # pour tracer la COUPE à travers le plan réel (bâtiment/parking à leur vraie position).
    axe: Optional[dict] = None                           # {ox, oy, ux, uy, L}
    tn_section: list[dict] = field(default_factory=list)  # [{d_m, alt_m|None}] le long de l'axe


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


def _wkts(rows) -> list[BaseGeometry]:
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


def _batis(session, aw_wkt: str) -> list[BaseGeometry]:
    return _wkts(_rows(session,
        "SELECT ST_AsText(geom_2975) AS wkt FROM spatial_layers "
        "WHERE kind='batiment' AND geom_2975 IS NOT NULL "
        "AND ST_DWithin(geom_2975, ST_GeomFromText(:g,2975), :r) "
        "AND NOT ST_Intersects(geom_2975, ST_GeomFromText(:g,2975)) LIMIT 400",
        {"g": aw_wkt, "r": _RAYON_VOISINS_M}))


def _batis_assiette(session, aw_wkt: str) -> list[BaseGeometry]:
    # DOCS-COHERENCE-1 (F1) — le bâti existant QUI TOUCHE l'assiette (= à démolir sur terrain libéré).
    return _wkts(_rows(session,
        "SELECT ST_AsText(ST_Intersection(geom_2975, ST_GeomFromText(:g,2975))) AS wkt FROM spatial_layers "
        "WHERE kind='batiment' AND geom_2975 IS NOT NULL "
        "AND ST_Intersects(geom_2975, ST_GeomFromText(:g,2975)) LIMIT 400",
        {"g": aw_wkt}))


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


def _axe_coupe(assiette: BaseGeometry, voie_edges) -> Optional[dict]:
    """Axe de coupe = PERPENDICULAIRE à la voie (sinon au grand côté du rectangle minimal), passant par
    le centroïde, orienté depuis la voie VERS l'intérieur. `O` = point de l'axe au bord « voie »,
    `u` = direction, `L` = longueur traversant l'assiette. Sert à projeter bâtiment/parking et à
    échantillonner le TN le long de la coupe."""
    if assiette is None or assiette.is_empty:
        return None
    c = assiette.centroid
    if voie_edges:
        ve = max(voie_edges, key=lambda g: g.length)
        co = list(ve.coords)
        vx, vy = co[-1][0] - co[0][0], co[-1][1] - co[0][1]
    else:
        mrr = list(assiette.minimum_rotated_rectangle.exterior.coords)[:4]
        s1 = (mrr[1][0] - mrr[0][0], mrr[1][1] - mrr[0][1])
        s2 = (mrr[2][0] - mrr[1][0], mrr[2][1] - mrr[1][1])
        vx, vy = s1 if (s1[0] ** 2 + s1[1] ** 2) >= (s2[0] ** 2 + s2[1] ** 2) else s2
    n = math.hypot(vx, vy) or 1.0
    vx, vy = vx / n, vy / n
    ux, uy = -vy, vx                                       # perpendiculaire à la voie
    ds = [((x - c.x) * ux + (y - c.y) * uy) for x, y in assiette.exterior.coords]
    dmin, dmax = min(ds), max(ds)
    if voie_edges:                                         # u doit pointer DE la voie VERS l'intérieur
        vm = max(voie_edges, key=lambda g: g.length).interpolate(0.5, normalized=True)
        if ((vm.x - c.x) * ux + (vm.y - c.y) * uy) > 0:    # voie du côté dmax → on inverse
            ux, uy, dmin, dmax = -ux, -uy, -dmax, -dmin
    ox, oy = c.x + ux * dmin, c.y + uy * dmin              # origine au bord « voie »
    return {"ox": ox, "oy": oy, "ux": ux, "uy": uy, "L": dmax - dmin}


def _tn_section(session, axe: dict, *, avec_ign: bool, n: int = 16) -> list[dict]:
    """Profil TN (LiDAR) le long de l'axe de coupe : n points [{d_m, alt_m|None}]."""
    if not axe:
        return []
    ox, oy, ux, uy, L = axe["ox"], axe["oy"], axe["ux"], axe["uy"], axe["L"]
    wkt = f"LINESTRING({ox} {oy}, {ox + ux * L} {oy + uy * L})"
    try:
        from labuse.faisabilite.profil_altimetrique import _echantillons
        pts = _echantillons(session, wkt, n)
    except Exception:
        return []
    if avec_ign and any(p["alt_m"] is None for p in pts):
        try:
            from labuse.faisabilite.profil_altimetrique import _completer_ign
            _completer_ign(pts)
        except Exception:
            pass
    return [{"d_m": round(p["dist_m"], 2), "alt_m": p["alt_m"]} for p in pts]


def charger_contexte(session, assiette: BaseGeometry, idus: list[str], *, avec_tn: bool = True,
                     voie_edges=None) -> Contexte:
    """Contexte complet autour de l'assiette (2975). Tolérant : tout ce qui manque = vide.
    `avec_tn=False` coupe l'appel réseau IGN du TN (tests / rendu rapide)."""
    if session is None or assiette is None or assiette.is_empty:
        return Contexte()
    aw = assiette.wkt
    axe = _axe_coupe(assiette, voie_edges)
    return Contexte(
        voisins=_voisins(session, aw, idus),
        batis_voisins=_batis(session, aw),
        batis_assiette=_batis_assiette(session, aw),
        voies=_voies(session, aw),
        tn_coins=_tn_coins(session, assiette, avec_ign=avec_tn),
        axe=axe,
        tn_section=_tn_section(session, axe, avec_ign=avec_tn) if axe else [],
    )
