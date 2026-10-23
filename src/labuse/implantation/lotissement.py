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

from shapely.geometry import Point
from shapely.ops import unary_union

from . import terrain as terrain_mod

LOT_CIBLE_M2 = 450.0        # taille de lot visée (Estimé — pas de superficie minimale au PLU, loi ALUR)
VOIRIE_LARGEUR_M = 5.0      # chaussée (hypothèse : aucune règle de voirie au PLU Ud ; trottoir à prévoir)
LOT_PROFONDEUR_MAX_M = 24.0 # au-delà, on plafonne la profondeur et on élargit la façade
GARDE_INTERIEUR = 0.55      # un lot n'est retenu que si ≥ 55 % de sa surface tombe dans l'assiette nette
TOURNE_FACTEUR = 2.2        # côté de l'aire de retournement (palette) = 2,2 × largeur de voirie


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


def _pt(origin, u, v, a, b) -> Point:
    return Point(origin[0] + a * u[0] + b * v[0], origin[1] + a * u[1] + b * v[1])


def _lots_u(origin, u, v, L, vc, w, depth, facade):
    """Lots de part et d'autre d'une voirie orientée selon u (à la cote v = vc)."""
    out = []
    for i in range(int(L // facade)):
        for side in (1, -1):
            v0 = vc + w / 2 if side > 0 else vc - w / 2 - depth
            out.append(_rect(origin, u, v, i * facade, (i + 1) * facade, v0, v0 + depth))
    return out


def _lots_v(origin, u, v, W, uc, w, depth, facade):
    """Lots de part et d'autre d'une voirie orientée selon v (à la cote u = uc)."""
    out = []
    for j in range(int(W // facade)):
        for side in (1, -1):
            u0 = uc + w / 2 if side > 0 else uc - w / 2 - depth
            out.append(_rect(origin, u, v, u0, u0 + depth, j * facade, (j + 1) * facade))
    return out


def _accepter(candidats, road, net):
    """Garde les lots dessinables : ≥ 55 % dans l'assiette, hors voirie, sans recouvrir un lot déjà retenu."""
    out = []
    for lot in candidats:
        inter = lot.intersection(net)
        if inter.is_empty or inter.area < GARDE_INTERIEUR * lot.area:
            continue
        if lot.intersection(road).area > 0.12 * lot.area:
            continue
        piece = inter if inter.geom_type == "Polygon" else max(inter.geoms, key=lambda g: g.area)
        if piece.area < 120.0:
            continue
        if any(piece.intersection(g).area > 0.20 * piece.area for g in out):
            continue
        out.append(piece)
    return out


def _bout(road_net, origin, u, v, proj_u: bool, sens: int) -> Optional[Point]:
    """Sommet extrême (dans l'assiette) d'un tronçon de voirie, selon l'axe u (proj_u) ou v, côté `sens`."""
    if road_net.is_empty:
        return None
    axe = u if proj_u else v
    geoms = road_net.geoms if road_net.geom_type == "MultiPolygon" else [road_net]
    pts = [c for g in geoms for c in g.exterior.coords]
    key = lambda c: sens * ((c[0] - origin[0]) * axe[0] + (c[1] - origin[1]) * axe[1])  # noqa: E731
    best = max(pts, key=key)
    return Point(best)


def _retournement(net, origin, u, v, L, W, w, config, u_spine, v_demi):
    """Aire de retournement (palette) au BOUT des voiries en impasse. Un réseau en croix débouche de
    part et d'autre (pas d'impasse) ; une voirie en I ou en T se termine en cul-de-sac → palette."""
    if config.startswith("croix"):
        return []
    cote = TOURNE_FACTEUR * w
    bouts = [_bout(u_spine.intersection(net), origin, u, v, True, +1)]   # bout du tronçon principal
    if config.startswith("T"):
        bouts.append(_bout(v_demi.intersection(net), origin, u, v, False, +1))   # bout de la branche
    heads = [p.buffer(cote / 2, cap_style=3).intersection(net) for p in bouts if p is not None]
    return [h for h in heads if not h.is_empty and h.area > 20.0]


def _dims(lot_cible):
    """Profondeur et façade VISÉES d'un lot (≈ lot_cible), indépendantes du nombre de voies — pour ne
    jamais sur-découper en micro-lots quand on ajoute des voies."""
    depth = min(LOT_PROFONDEUR_MAX_M, max(18.0, lot_cible / 18.0))
    facade = max(14.0, min(26.0, lot_cible / depth))
    return depth, facade


def _peigne(origin, u, v, L, W, w, lot_cible, n, axe_u: bool):
    """Réseau en PEIGNE : n voies parallèles couvrant toute la largeur, reliées par une épine centrale.
    Chaque voie dessert deux rangées de lots À PROFONDEUR FIXE (≈ lot_cible). Renvoie (voirie, lots)."""
    depth, facade = _dims(lot_cible)
    span = W if axe_u else L
    roads, lots = [], []
    for k in range(n):
        c = (k + 0.5) * span / n
        if axe_u:
            roads.append(_rect(origin, u, v, 0, L, c - w / 2, c + w / 2))
            lots += _lots_u(origin, u, v, L, c, w, depth, facade)
        else:
            roads.append(_rect(origin, u, v, c - w / 2, c + w / 2, 0, W))
            lots += _lots_v(origin, u, v, W, c, w, depth, facade)
    if axe_u:                                           # épine de liaison → réseau connexe
        roads.append(_rect(origin, u, v, (L - w) / 2, (L + w) / 2, 0, W))
    else:
        roads.append(_rect(origin, u, v, 0, L, (W - w) / 2, (W + w) / 2))
    return unary_union(roads), lots


def _pave_reseau(net: BaseGeometry, lot_cible: float, w: float):
    """Pave l'assiette : on essaie l'impasse simple ET des réseaux en peigne (voies parallèles couvrant
    toute la largeur, + liaison), 1 à 3 voies, dans les deux orientations. On garde le tracé qui donne le
    PLUS de lots — c'est ainsi qu'on couvre une parcelle large (pas seulement une bande centrale)."""
    origin, u, v, L, W = _frame(net)
    if L < 12 or W < w + 12:
        return [], None, "—", False
    configs = {}
    depth, facade = _dims(lot_cible)
    configs["voirie en impasse"] = (_rect(origin, u, v, 0, L, (W - w) / 2, (W + w) / 2),
                                    _lots_u(origin, u, v, L, W / 2, w, depth, facade), True)
    # nombre de voies parallèles pour couvrir la largeur (bande utile ≈ 2·profondeur + voie) :
    bande = 2 * depth + w
    n_u = max(1, min(4, round(W / bande)))
    n_v = max(1, min(4, round(L / bande)))
    for n in {n_u, max(1, n_u - 1), n_u + 1}:
        road, lots = _peigne(origin, u, v, L, W, w, lot_cible, n, axe_u=True)
        configs[f"réseau en peigne ({n} voies)"] = (road, lots, False)
    for n in {n_v, max(1, n_v - 1)}:
        road, lots = _peigne(origin, u, v, L, W, w, lot_cible, n, axe_u=False)
        configs[f"réseau en peigne transversal ({n} voies)"] = (road, lots, False)
    best = None
    for label, (road, cand, impasse) in configs.items():
        rn = road.intersection(net)
        if rn.is_empty:
            continue
        lots = _accepter(cand, rn, net)
        if best is None or len(lots) > len(best[1]):
            best = (label, lots, rn, impasse)
    if best is None:
        return [], None, "—", False
    label, lots, rn, impasse = best
    heads = []
    if impasse:
        u_spine = _rect(origin, u, v, 0, L, (W - w) / 2, (W + w) / 2)
        heads = _retournement(net, origin, u, v, L, W, w, "I", u_spine, u_spine)
    voirie = unary_union([rn] + heads) if heads else rn
    if heads:
        lots = [g for g in lots if g.intersection(voirie).area < 0.15 * g.area]
    config_label = label + (" + aire de retournement" if heads else "")
    return lots, voirie, config_label, bool(heads)


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
    from . import moteur as moteur_mod
    from .conventions import charger as charger_conv
    terrain, regles, zone = moteur_mod._charger(session, idus, None, charger_conv(), avec_pente=False)
    assiette = terrain.assiette
    net = terrain.zone_implantation if terrain.zone_implantation is not None else assiette
    ebc_geom, ebc_m2 = _ebc(session, idus, assiette)
    if ebc_geom is not None:
        net = net.difference(ebc_geom)
    commune = terrain.commune
    contenance = terrain.contenance_totale_m2

    # ETUDE-V6-6 (item 1) — règles LUES du PLU de la commune ET de la zone de l'assiette (jamais Saint-Leu
    # Ud en dur). CES, pleine terre et stationnement par lot viennent de `regles` ; chacune porte sa source
    # (article) ou est marquée « non servie » (hypothèse assumée), jamais une valeur fabriquée silencieuse.
    ces_servie = regles.emprise_ces.validee and regles.emprise_ces.valeur
    ces_pct = regles.emprise_ces.valeur if ces_servie else 40.0
    pt_servie = regles.pleine_terre.validee and regles.pleine_terre.valeur
    pt_pct = regles.pleine_terre.valeur if pt_servie else 40.0
    pt_article = regles.pleine_terre.article if pt_servie else None
    # stationnement par LOT = barème « logement individuel » de la zone (une maison par lot).
    b = regles.stationnement
    _pl = b.places_pour(pieces=4, sdp_m2=100, destination="individuel")
    if _pl is None and b.mode == "par_logement":
        _pl = b.flat_places
    stat_servie = bool(b.validee and _pl is not None)
    places_par_lot = float(_pl) if stat_servie else 2.0
    stat_article = b.article if stat_servie else None
    stat_citation = b.citation if stat_servie else None

    # ETUDE-V6-6 (item 2) — on ne lève JAMAIS : si l'assiette est trop petite, ou si aucun lot n'est
    # dessinable après la voirie, on renvoie un résultat qui DIT pourquoi et ce qui le permettrait.
    trop_petit = net.is_empty or net.area < 400
    if trop_petit:
        lots, voirie, voie_label, impasse = [], None, "aucune (assiette trop petite)", False
    else:
        lots, voirie, voie_label, impasse = _pave_reseau(net, lot_cible_m2, voirie_largeur_m)
    aires = sorted(round(g.area, 1) for g in lots)
    nb = len(lots)
    voirie_m2 = round(voirie.area, 1) if voirie is not None else 0.0
    raison = remede = None
    if nb == 0:
        apres_voirie = round(max(0.0, net.area - voirie_m2), 1)
        if trop_petit:
            raison = (f"Assiette constructible trop petite pour un lotissement : {net.area:.0f} m² nets "
                      f"(après zone, PPR, EBC) ne suffisent pas à des lots de {lot_cible_m2:.0f} m² plus une voirie.")
        else:
            raison = (f"Aucun lot de {lot_cible_m2:.0f} m² n'est dessinable : après la voirie de desserte "
                      f"({voirie_m2:.0f} m²), il reste {apres_voirie:.0f} m² sur {net.area:.0f} m² nets — "
                      f"insuffisant pour la profondeur et la façade d'un lot à cette taille.")
        remede = ("Réduisez la taille de lot visée (hypothèse modifiable), ou desservez les lots par un accès "
                  "direct sur la voie existante plutôt qu'une voirie interne, ou étudiez une assiette plus grande.")
    # PLEINE TERRE = jardins privatifs (lot − future emprise au CES de la zone) + espaces verts communs.
    jardins_privatifs = round(sum(aires) * (1.0 - ces_pct / 100.0), 1)
    communs = round(max(0.0, net.area - sum(aires) - voirie_m2), 1)
    pt_totale = round(jardins_privatifs + communs, 1)
    pt_requis = round(contenance * pt_pct / 100.0, 1)
    pt_ok = pt_totale >= pt_requis
    _pt_src = f"{pt_pct:.0f} % de la contenance" + (f" · {pt_article}" if pt_article else " · règle non servie (hypothèse)")
    controle_pt = {
        "nom": "Perméabilité (pleine terre)",
        "regle": f"≥ {pt_requis:.0f} m² ({_pt_src})",
        "mesure": f"{pt_totale:.0f} m² (jardins privatifs {jardins_privatifs:.0f} + communs {communs:.0f})",
        "resultat": "Réussi" if pt_ok else "Échoué",
        "citation": pt_article, "detail": f"écart {pt_totale - pt_requis:+.0f} m²",
    }

    # ETUDE-V6-6 (item 1) — stationnement par lot LU du PLU de la zone (maison individuelle).
    places_lots = int(math.ceil(nb * places_par_lot))
    places_visiteurs = math.ceil(nb * 0.8)   # Estimé (non réglementé) — l'archi en pose ~0,8/lot
    _stat_note = (f"{places_par_lot:g} place(s) / lot — barème « logement individuel » du PLU "
                  f"(zone {zone}, art. {stat_article}). Visiteurs = convention (Estimé, non réglementé)."
                  if stat_servie else
                  f"{places_par_lot:g} place(s) / lot — HYPOTHÈSE (barème non servi pour la zone {zone}). "
                  "Visiteurs = convention (Estimé, non réglementé).")
    regime = ("Permis d'aménager (lotissement de plus de 2 lots avec création de voirie/espaces communs) "
              "— à qualifier selon R.421-19 (voirie, équipements communs).")

    # ETUDE-V6-6 (item 1) — les règles SERVIES de la zone, chacune avec sa source (pour l'écran et le PDF).
    regles_sourcees = [
        {"nom": "Emprise au sol (CES)", "valeur": f"{ces_pct:.0f} %", "article": regles.emprise_ces.article,
         "servie": bool(ces_servie)},
        {"nom": "Pleine terre", "valeur": f"{pt_pct:.0f} %", "article": pt_article, "servie": bool(pt_servie)},
        {"nom": "Stationnement / lot", "valeur": f"{places_par_lot:g} pl.", "article": stat_article,
         "citation": stat_citation, "servie": stat_servie},
    ]
    return {
        "commune": commune, "insee": terrain.insee, "zone": zone,
        # ETUDE-V6-6 (item 2) — raison + remède quand aucun lot n'est dessinable (jamais muet).
        "raison": raison, "remede": remede,
        "regles_sourcees": regles_sourcees,
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
        "voirie_config": voie_label,
        "voirie_largeur_source": ("Largeur = hypothèse (aucune largeur de voirie n'est servie au PLU pour "
                                  f"cette zone) : chaussée {voirie_largeur_m:.0f} m, trottoir à prévoir (Estimé)."),
        "pleine_terre": {"exigee_pct": pt_pct, "exigee_m2": pt_requis, "estimee_m2": pt_totale,
                         "jardins_privatifs_m2": jardins_privatifs, "communs_m2": communs,
                         "ces_pct": ces_pct, "resultat": "Réussi" if pt_ok else "Échoué", "article": pt_article},
        "controles": [controle_pt],
        # BILAN SURFACIQUE CLOS (Lot E) : assiette = lots + voirie + communs + PPR rouge + EBC + hors-zone
        # (part non U/AU + marges clippées), sans double comptabilisation. Clos par construction.
        "bilan_surfacique": (lambda hz, som: {
            "assiette_m2": round(assiette.area, 1), "lots_m2": round(sum(aires), 1), "voirie_m2": voirie_m2,
            "communs_m2": communs, "ppr_rouge_m2": round(terrain.ppr_rouge_m2, 1), "ebc_m2": ebc_m2,
            "hors_zone_m2": hz, "somme_m2": round(som, 1), "ecart_m2": round(som - assiette.area, 1),
            "clos": abs(som - assiette.area) <= 0.02 * assiette.area,
        })(round(max(0.0, assiette.area - net.area - terrain.ppr_rouge_m2 - ebc_m2), 1),
           sum(aires) + voirie_m2 + communs + terrain.ppr_rouge_m2 + ebc_m2
           + max(0.0, assiette.area - net.area - terrain.ppr_rouge_m2 - ebc_m2)),
        "stationnement": {"par_lot": places_par_lot, "article": stat_article, "servie": stat_servie,
                          "total_lots": places_lots, "visiteurs_estimes": places_visiteurs,
                          "note": _stat_note},
        "ebc": {"m2": ebc_m2, "statut": "présent" if ebc_m2 > 0 else "non trouvé dans les données LABUSE (à vérifier)"},
        "ppr_rouge_m2": terrain.ppr_rouge_m2,
        "raccordements": _raccordements(session, idus),
        "regime_procedural": regime,
        # ETUDE-V6-6 (item 1) — superficie minimale de lot : non modélisée au PLU (l'article 5 « superficie
        # minimale » a été supprimé par la loi ALUR de 2014) ; formulé pour la commune/zone courante.
        "min_lot_plu": {"existe": False,
                        "note": f"Zone {zone} de {commune} : aucune superficie minimale de lot n'est servie "
                                "au PLU (article 5 supprimé par la loi ALUR, 2014). Le découpage est géométrique "
                                "(Estimé), pas une règle opposable."},
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
