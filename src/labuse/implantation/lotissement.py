"""ETUDE-V6 (Lot D) — LOTISSEMENT : division foncière d'UNE assiette en lots à bâtir, à la demande
(jamais le batch île). On réutilise l'assiette constructible du moteur (terrain.charger : zone U/AU,
PPR rouge retiré) ; on en retire l'EBC ; on pave en lots le long d'une voirie centrale ; on en tire un
TABLEAU DES LOTS (nombre, surfaces, accès), l'emprise de voirie, la pleine terre, le stationnement des
futures constructions et le régime procédural « à qualifier ». Les logements T1–T4 saisis sont des
hypothèses de constructions futures, JAMAIS un nombre de lots garanti.

Déterministe, sans IA. Pas une règle du PLU : le découpage est un ESTIMÉ (pavage le long d'une voirie),
borné dans le temps comme l'Étude. Aucune promesse de constructibilité d'un lot particulier.
"""
from __future__ import annotations

import math
from typing import Optional

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from . import terrain as terrain_mod

LOT_CIBLE_M2 = 450.0        # taille de lot visée (Estimé — pas de superficie minimale au PLU, loi ALUR)
VOIRIE_LARGEUR_M = 6.0      # largeur de la voirie de desserte (Estimé)
LOT_PROFONDEUR_MAX_M = 24.0 # au-delà, on plafonne la profondeur et on élargit la façade
GARDE_INTERIEUR = 0.60      # un lot n'est retenu que si ≥ 60 % de sa surface tombe dans l'assiette nette


def _frame(poly: BaseGeometry):
    """Repère local (origine, axe long u, axe court v, longueurs L, W) du rectangle orienté minimal."""
    mrr = poly.minimum_rotated_rectangle
    c = list(mrr.exterior.coords)[:4]
    e0 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
    e1 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l0, l1 = math.hypot(*e0), math.hypot(*e1)
    if l0 >= l1:
        return c[0], (e0[0] / l0, e0[1] / l0), (e1[0] / l1, e1[1] / l1), l0, l1
    return c[1], (e1[0] / l1, e1[1] / l1), (e0[0] / l0, e0[1] / l0), l1, l0


def _rect(origin, u, v, u0, u1, v0, v1) -> Polygon:
    pts = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return Polygon([(origin[0] + a * u[0] + b * v[0], origin[1] + a * u[1] + b * v[1]) for a, b in pts])


def _pave(net: BaseGeometry, lot_cible: float, voirie_l: float):
    """Pave l'assiette nette en lots de part et d'autre d'une voirie centrale. Renvoie (lots, voirie)."""
    origin, u, v, L, W = _frame(net)
    if L < 10 or W < voirie_l + 10:
        return [], None
    prof = max(8.0, min(LOT_PROFONDEUR_MAX_M, (W - voirie_l) / 2.0))
    facade = max(10.0, min(30.0, lot_cible / prof))
    ncol = int(L // facade)
    voirie = _rect(origin, u, v, 0, L, (W - voirie_l) / 2.0, (W + voirie_l) / 2.0).intersection(net)
    lots = []
    for i in range(ncol):
        for cote in (0, 1):
            v0 = (W + voirie_l) / 2.0 if cote else (W - voirie_l) / 2.0 - prof
            lot = _rect(origin, u, v, i * facade, (i + 1) * facade, v0, v0 + prof)
            inter = lot.intersection(net)
            if not inter.is_empty and inter.area >= GARDE_INTERIEUR * lot.area:
                lots.append(inter if inter.geom_type == "Polygon" else lot.intersection(net))
    return [g for g in lots if g.area > 100.0], (voirie if voirie and not voirie.is_empty else None)


def _ebc(session, idus: list[str], assiette: BaseGeometry) -> tuple[Optional[BaseGeometry], float]:
    """EBC intersectant l'assiette (si la donnée existe). Donnée absente = non vérifié, pas « absent »."""
    from sqlalchemy import text
    from shapely import wkt as shp_wkt
    row = session.execute(text(
        "SELECT ST_AsText(ST_Union(geom_2975)) FROM spatial_layers WHERE kind = 'ebc' "
        "AND ST_Intersects(geom_2975, ST_GeomFromText(:g, 2975))"
    ), {"g": assiette.wkt}).scalar()
    if not row:
        return None, 0.0
    g = shp_wkt.loads(row).intersection(assiette)
    return (g, round(g.area, 1)) if not g.is_empty else (None, 0.0)


def _raccordements(session, idus: list[str]) -> list[dict]:
    """Distance au plus proche réseau lu des couches (électricité MT, assainissement). Sourcé, honnête."""
    from sqlalchemy import text
    out = []
    for kind, label in (("ligne_mt", "Électricité (ligne MT)"),
                        ("zonage_assainissement", "Assainissement (zonage collectif)")):
        d = session.execute(text(
            "SELECT min(round(ST_Distance(s.geom_2975, p.geom_2975))::int) FROM parcels p, spatial_layers s "
            "WHERE p.idu = ANY(:i) AND s.kind = :k AND s.geom_2975 IS NOT NULL"), {"i": idus, "k": kind}).scalar()
        out.append({"reseau": label, "distance_m": int(d) if d is not None else None,
                    "statut": "non vérifié" if d is None else ("adjacent" if d == 0 else "à raccorder")})
    return out


def etudier_lotissement(session, idus: list[str], *, lot_cible_m2: float = LOT_CIBLE_M2,
                        voirie_largeur_m: float = VOIRIE_LARGEUR_M) -> dict:
    """Plan de division d'UNE assiette. Renvoie tableau des lots, voirie, pleine terre, stationnement,
    EBC, raccordements, régime et GeoJSON (assiette/voirie/lots/PPR/EBC). ValueError si assiette vide."""
    terrain = terrain_mod.charger(session, idus, recul_voie_m=0.0, recul_separative_m=0.0, avec_pente=False)
    assiette = terrain.assiette
    net = terrain.zone_implantation if terrain.zone_implantation is not None else assiette
    ebc_geom, ebc_m2 = _ebc(session, idus, assiette)
    if ebc_geom is not None:
        net = net.difference(ebc_geom)
    if net.is_empty or net.area < 400:
        raise ValueError("assiette constructible trop petite pour un lotissement (après zone, PPR, EBC).")

    lots, voirie = _pave(net, lot_cible_m2, voirie_largeur_m)
    aires = sorted(round(g.area, 1) for g in lots)
    nb = len(lots)
    voirie_m2 = round(voirie.area, 1) if voirie is not None else 0.0
    # pleine terre : exigence Ud (40 %) + estimation (lots hors future emprise bâtie au CES 40 %).
    contenance = terrain.contenance_totale_m2
    pleine_terre_estimee = round(sum(a for a in aires) * 0.60, 1)   # ~60 % du lot reste jardin (CES 40 %)
    # stationnement des futures constructions : 2 places / logement (Ud 12). Visiteurs = convention (Estimé).
    places_lots = nb * 2
    places_visiteurs = math.ceil(nb * 0.8)   # Estimé (non réglementé) — l'archi en pose ~0,8/lot
    regime = ("Permis d'aménager (lotissement de plus de 2 lots avec création de voirie/espaces communs) "
              "— à qualifier selon R.421-19 (voirie, équipements communs).")

    from sqlalchemy import text
    zone = session.execute(text("SELECT zone_lib FROM parcel_zone_plu WHERE idu = :i"),
                           {"i": idus[0]}).scalar()
    return {
        "commune": terrain.commune, "insee": terrain.insee, "zone": zone,
        "assiette_m2": round(assiette.area, 1),
        "contenance_m2": contenance,
        "net_constructible_m2": round(net.area, 1),
        "lot_cible_m2": lot_cible_m2,
        "tableau_lots": {
            "nombre": nb,
            "surface_moyenne_m2": round(sum(aires) / nb, 1) if nb else None,
            "surface_min_m2": aires[0] if aires else None,
            "surface_max_m2": aires[-1] if aires else None,
            "surfaces_m2": aires,
            "acces": "sur voirie de desserte créée" if voirie is not None else "accès à préciser",
        },
        "voirie_m2": voirie_m2,
        "voirie_largeur_m": voirie_largeur_m,
        "pleine_terre": {"exigee_pct": 40.0, "exigee_m2": round(contenance * 0.40, 1),
                         "estimee_m2": pleine_terre_estimee, "article": "UD 13"},
        "stationnement": {"par_lot": 2, "article": "UD 12 (renvoi dispositions générales Art. 11)",
                          "total_lots": places_lots, "visiteurs_estimes": places_visiteurs,
                          "note": "2 places / logement (PLU Ud) ; visiteurs = convention (Estimé, non réglementé)."},
        "ebc": {"m2": ebc_m2, "statut": "présent" if ebc_m2 > 0 else "non trouvé dans les données LABUSE (à vérifier)"},
        "ppr_rouge_m2": terrain.ppr_rouge_m2,
        "raccordements": _raccordements(session, idus),
        "regime_procedural": regime,
        "min_lot_plu": {"existe": False,
                        "note": "Zone Ud de Saint-Leu : aucune superficie/largeur minimale de lot au PLU "
                                "(suppression des articles 5 par la loi ALUR, 2014). Le découpage est "
                                "géométrique (Estimé), pas une règle opposable."},
        "geojson": _geojson(terrain, net, voirie, lots, ebc_geom),
        "note": "Pré-lotissement indicatif (pavage déterministe le long d'une voirie). Ni plan de géomètre, "
                "ni droit à diviser : le découpage réel dépend du projet, des accès et de l'instruction.",
    }


def _geojson(terrain, net, voirie, lots, ebc_geom) -> dict:
    """GeoJSON WGS84 pour le plan (assiette, voirie, lots, PPR rouge, EBC) — rendu par PlanMasseSvg."""
    from .service import _feature  # réutilise la projection 2975→4326 du service
    feats = []
    f = _feature(terrain.assiette, {"kind": "assiette"})
    if f:
        feats.append(f)
    if terrain.ppr_rouge is not None and not terrain.ppr_rouge.is_empty:
        g = _feature(terrain.ppr_rouge, {"kind": "ppr_rouge"})
        if g:
            feats.append(g)
    if ebc_geom is not None:
        g = _feature(ebc_geom, {"kind": "ebc"})
        if g:
            feats.append(g)
    if voirie is not None:
        g = _feature(voirie, {"kind": "allee"})
        if g:
            feats.append(g)
    for i, lot in enumerate(lots, 1):
        g = _feature(lot, {"kind": "lot", "numero": i, "surface_m2": round(lot.area, 1)})
        if g:
            feats.append(g)
    return {"type": "FeatureCollection", "features": feats}
