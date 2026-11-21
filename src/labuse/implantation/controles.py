"""Contrôles.

Deux familles :
  - GÉOMÉTRIQUES (bool) : cohérence interne, utilisées par le moteur pour accepter/refuser un
    candidat, ET re-vérifiées indépendamment par les tests du LOT C. Le non-chevauchement est testé
    sur TOUS les couples d'objets du plan de sol (module, noyau, coursive, place, allée, accès,
    espace libre) ; la somme des surfaces mesurées = l'assiette.
  - RÉGLEMENTAIRES (4 états) : Réussi · Échoué · Non effectué · Non applicable.
      * Réussi UNIQUEMENT si la règle est `validee` avec citation ET que la mesure la respecte.
      * Règle non validée ou non modélisée = Non effectué (jamais Réussi).
      * Contrainte absente du terrain = Non applicable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from shapely.ops import unary_union

_FERMETURE_M = 1e-4          # FIX-19 : fermeture de 0,1 mm (un dixième de la résolution). Soude deux pièces
#   jointives (bord à bord, désalignées par une rotation/un bruit flottant) et comble un pincement sub-micronique
#   à une jonction, SANS déplacer un bord ni combler un vrai vide : elle ne ponte que ≤ 0,2 mm (un écart de 2 cm
#   reste un écart). Bien en dessous du millimètre : ne perturbe aucune mesure. Bouts PLATS (join_style=2) pour ne
#   PAS arrondir les angles (un arrondi, lui, déplaçait le goulet de plusieurs cm dans le régime « voiture ≈ couloir »).

from .capacite import Capacite
from .conventions import Conventions
from .geometrie import Scene
from .regles import ReglesZone

REUSSI = "Réussi"
ECHOUE = "Échoué"
NON_EFFECTUE = "Non effectué"
NON_APPLICABLE = "Non applicable"
# ETUDE-V6 (Lot B) — 5ᵉ état : ambiguïté de DONNÉE ou de TEXTE (PPR présent non interprété, prospect
# non chiffrable, servitude présente, barème manquant). ≠ « Non effectué » (non calculé, ex. locaux
# vélos) et ≠ « Non applicable » (contrainte absente). « À confirmer » interdit un verdict « Exploitable ».
A_CONFIRMER = "À confirmer"

ETATS = (REUSSI, ECHOUE, NON_EFFECTUE, NON_APPLICABLE, A_CONFIRMER)

_TOL_AIRE = 1e-6
_TOL_CONTENU = 0.05


def _fr(x: float) -> str:
    """Nombre au format français (virgule), sans zéro inutile : 4.5→« 4,5 », 18.0→« 18 »."""
    return (f"{x:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def hauteur_projet_m(conv: Conventions, regles: ReglesZone, niveaux: int) -> tuple[float, str, bool]:
    """FAISA-REGLES-1 (E-059) — hauteur du PROJET mesurée SELON LA RÈGLE DU PLU (R.111-26), depuis le
    terrain naturel. Les murs = rez-de-chaussée + étages = `niveaux × hauteur d'étage` (le rez EST un
    niveau, compté). Si la règle qui plafonne se mesure au FAÎTAGE, on AJOUTE la toiture/acrotère
    (`conv.toiture_m`, faîtage = égout + toiture) — sinon un R+n passerait un plafond de faîtage en ne
    comptant que ses murs. Si elle se mesure à l'ÉGOUT, le haut des murs EST l'égout (toiture au-dessus,
    non comptée). Renvoie (hauteur_m, base, estimee) : base ∈ {« égout », « faîtage » } ; `estimee`=True
    quand la toiture a été ajoutée (marge prudente à DIRE sur le chiffre). Jamais une règle inventée :
    la hauteur d'étage et la toiture sont des conventions « Estimé »."""
    h_murs = niveaux * conv.hauteur_etage_m
    if regles.hauteur_egout.validee:
        return round(h_murs, 1), "égout", False
    return round(h_murs + conv.toiture_m, 1), "faîtage", True


@dataclass
class CheckGeo:
    nom: str
    ok: bool
    detail: str = ""
    # ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — un check « consultatif » est AFFICHÉ mais n'invalide PAS la
    # géométrie (n'entre pas dans `geometrie_valide`). Utilisé pour le dégagement sur les ASSEMBLAGES
    # multi-parcelles, où le pavage irrégulier rend la mesure peu fiable (faux pincements).
    advisory: bool = False


# ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — une place est jugée NON DÉGAGÉE si le couloir manquant devant elle
# dépasse ce plancher (≈ allée trop courte de > 0,4 m sur la largeur de la place) ; en deçà, c'est du bruit
# de pavage/jonction. Le contrôle échoue dès qu'une place est non dégagée (BW2635 : 13 places à 2,25 m).
# haie paysagère au pourtour des aires de stationnement : on capte la largeur imposée (« ≥ 1,50 m »).
_HAIE_RE = re.compile(r"haie[^0-9]*?(\d+(?:[.,]\d+)?)\s*m", re.IGNORECASE)
# ETUDE-STATIONNEMENT-FIX-4 (LOT 1) — mesure EXACTE, sans marge cachée : on ne retranche RIEN à la largeur
# exigée et on ne tolère que le bruit numérique du pavage (< 0,02 m²). Une allée de 4,99 m pour 5 m exigés
# ÉCHOUE (déficit ≈ largeur de place × 0,01 m). Avant : W = exigée − 0,60 m + tolérance 1 m² (cachait un plan
# sous le minimum). `_DEGAGEMENT_PLACE_FLOOR_M2`/`_DEGAGEMENT_SEUIL_M2` = seuls amortisseurs de bruit flottant.
_DEGAGEMENT_PLACE_FLOOR_M2 = 0.005
_DEGAGEMENT_SEUIL_M2 = 0.005   # aire totale non dégagée au-delà de laquelle le plan échoue (bruit flottant seul)
_PASSAGE_MIN_M = 2.4         # largeur mini de circulation d'une voiture ; sous ce seuil l'allée s'étrangle
_COMP_SIGNIF_M2 = 8.0        # aire mini d'un morceau d'allée pour qu'un étranglement le séparant compte
_MUR_EP = 0.05               # FIX-16 : épaisseur de la paroi « contour de l'assiette » coupée dans la bande
#   extérieure (ouverte au seul recouvrement) — fine, sépare la bande de l'aire roulante aux bords FERMÉS
_PREC_M = 0.001              # FIX-18 : RÉSOLUTION géométrique = le millimètre (PAS une marge de proximité). Un
#   point d'approche à < 1 mm du noyau atteignable lui appartient ; une largeur se compare au mm. Bien en dessous
#   des seuils testés (2,35 m et 2,39 m refusés, 2,40 m accepté, inchangés). Sert aussi à juger qu'un recouvrement
#   est sur le BORD de l'assiette (aires des deux lanières différentes de plus d'1 mm·longueur).


def _grille_mm(polys):
    """FIX-19 (défauts B & C du relecteur) — ROBUSTESSE géométrique sous la RÉSOLUTION déjà fixée (le mm). On réunit
    les pièces puis on applique une FERMETURE À BOUTS PLATS de 0,1 mm (`_FERMETURE_M`). Deux pièces simplement
    JOINTIVES (bord à bord, désalignées par une rotation quelconque → `unary_union` ordinaire rendait un
    MultiPolygon que l'érosion `buffer(-_er)` scindait, défaut B) ne forment plus qu'UN polygone ; un micro-biseau
    sub-millimétrique au coin d'une jonction accès↔allée (bruit ~1e-12…1e-6 d'une transformation monde→local,
    défaut C) est comblé avant l'érosion et ne la scinde plus. La fermeture NE RELIE JAMAIS un vrai vide : elle ne
    ponte que ≤ 0,2 mm, donc deux réseaux séparés de 2 cm restent disjoints (tous les contre-exemples « deux
    réseaux à 2 cm » restent refusés) et une entrée étranglée (≥ 6 cm sous 2,40 m) n'est pas élargie. Bouts PLATS :
    une fermeture ARRONDIE déplaçait le goulet de plusieurs cm dans le régime dégénéré « voiture ≈ couloir »."""
    nettes = [(g if g.is_valid else g.buffer(0)) for g in polys]
    nettes = [g for g in nettes if not g.is_empty]
    if not nettes:
        return unary_union([])
    u = unary_union(nettes).buffer(0)
    if u.is_empty:
        return u
    return u.buffer(_FERMETURE_M, join_style=2).buffer(-_FERMETURE_M, join_style=2).buffer(0)


def _troncons_droits(line):
    """FIX-19 (défaut A du relecteur) — découpe une polyligne en ses TRONÇONS DROITS maximaux (sommets
    colinéaires de même sens fusionnés). Le recouvrement `voie ∩ libre` peut être COUDÉ (accès dans un angle
    du terrain, voie décrite par plusieurs segments) : ne garder que `coords[0]`/`coords[-1]` donnait une
    corde oblique ne décrivant AUCUN bord réel → bande/normale fausses, place refusée à tort. Chaque tronçon
    droit est une OUVERTURE possible à part entière (qui doit mesurer ≥ passage à elle seule)."""
    import math as _m
    cs = list(getattr(line, "coords", []))
    if len(cs) < 2:
        return []
    runs = []
    start = cs[0]
    d_prev = None
    prev = cs[0]
    for cur in cs[1:]:
        dx, dy = cur[0] - prev[0], cur[1] - prev[1]
        L = _m.hypot(dx, dy)
        if L <= 1e-12:
            continue
        d = (dx / L, dy / L)
        if d_prev is not None and (abs(d[0] * d_prev[1] - d[1] * d_prev[0]) > 1e-9
                                   or d[0] * d_prev[0] + d[1] * d_prev[1] <= 0):
            runs.append((start, prev))     # changement de direction → clôt le tronçon courant
            start = prev
        d_prev = d
        prev = cur
    runs.append((start, prev))
    return runs


def _longueur_mrr(geom) -> float:
    """Plus grand côté du rectangle englobant minimal — pour une lanière fine (la morsure de l'accès sur la
    voie), c'est sa LONGUEUR le long du recouvrement. Robuste à l'orientation ; 0 sur une géométrie vide."""
    if geom is None or getattr(geom, "is_empty", True):
        return 0.0
    try:
        mrr = geom.minimum_rotated_rectangle
        xy = list(getattr(mrr, "exterior", mrr).coords)
    except Exception:
        return 0.0
    cotes = [((xy[i][0] - xy[i + 1][0]) ** 2 + (xy[i][1] - xy[i + 1][1]) ** 2) ** 0.5
             for i in range(len(xy) - 1)]
    return max(cotes) if cotes else 0.0


def _coords_xy(geom):
    """Toutes les coordonnées (x, y) d'une géométrie quelconque (Polygon/Multi/Line/Collection)."""
    if geom is None or getattr(geom, "is_empty", True):
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return list(geom.exterior.coords)
    if gt in ("MultiPolygon", "GeometryCollection", "MultiLineString", "MultiPoint"):
        out = []
        for g in geom.geoms:
            out += _coords_xy(g)
        return out
    if gt in ("LineString", "LinearRing"):
        return list(geom.coords)
    if gt == "Point":
        return [(geom.x, geom.y)]
    return []


def _etendue_le_long(geom, ox: float, oy: float, tx: float, ty: float) -> float:
    """Étendue de `geom` PROJETÉE sur l'axe tangent (tx, ty) issu de (ox, oy) — la longueur « le long du
    recouvrement ». Un contact latéral (perpendiculaire à R) y projette une étendue courte → écarté."""
    pts = _coords_xy(geom)
    if not pts:
        return 0.0
    proj = [(x - ox) * tx + (y - oy) * ty for x, y in pts]
    return max(proj) - min(proj)


def _bords_assiette(assiette):
    """Segments du contour de l'assiette ORIENTÉE (intérieur à gauche, via shapely.orient sign=+1) : chaque
    bord est (px, py, ux, uy, longueur) avec (ux, uy) le sens de parcours. La NORMALE EXTÉRIEURE d'un bord
    (vers le dehors du terrain) est alors (uy, -ux) — déduite du SENS DE PARCOURS, sans aucun point de test."""
    import math as _math
    from shapely.geometry.polygon import orient
    if assiette is None or getattr(assiette, "is_empty", True) or not hasattr(assiette, "exterior"):
        return []
    try:
        ao = orient(assiette, 1.0)
    except Exception:
        ao = assiette
    rings = [ao.exterior] + list(ao.interiors)
    bords = []
    for ring in rings:
        cs = list(ring.coords)
        for i in range(len(cs) - 1):
            (px, py), (qx, qy) = cs[i], cs[i + 1]
            ex, ey = qx - px, qy - py
            el = _math.hypot(ex, ey)
            if el <= 1e-9:
                continue
            bords.append((px, py, ex / el, ey / el, el))
    return bords


def _cote_exterieur_mesure(assiette, ax, ay, bx, by, nx, ny, t: float = 0.5):
    """Côté EXTÉRIEUR du recouvrement, MESURÉ. (nx, ny) = normale unitaire ; renvoie celle qui SORT de l'assiette.

    RÈGLE 1 (FIX-18, robustifiée FIX-19) : le recouvrement n'établit un raccord que s'il est SUR LE BORD de
    l'assiette. On le juge par la DISTANCE de R au contour (robuste à la rotation et au bruit flottant) : une voie
    de desserte longe le bord → R à ~0 du contour ; une voie posée À L'INTÉRIEUR (contre-exemple FIX-18) en est à
    plusieurs mètres → None, raccord NON établi.

    CÔTÉ : lanières de 0,5 m de part et d'autre de R, le côté de MOINDRE aire d'assiette est l'extérieur (robuste
    concave : un creux local ne renverse pas le bilan). FIX-18 : si les DEUX lanières sont quasi vides (R au ras
    d'un SOMMET convexe du terrain tourné), on tranche par l'aire EXTÉRIEURE des deux extrusions profondes."""
    import math as _m
    from shapely.geometry import Polygon as _P
    from shapely.geometry import LineString as _LS

    dl = _m.hypot(bx - ax, by - ay)
    if dl <= 1e-12:
        return nx, ny
    try:
        if _LS([(ax, ay), (bx, by)]).distance(assiette.boundary) > 0.03:
            return None                 # R loin du contour → voie À L'INTÉRIEUR de l'assiette → pas un bord
    except Exception:
        pass

    def _aire(dd):
        lp = _P([(ax, ay), (bx, by), (bx + nx * dd, by + ny * dd), (ax + nx * dd, ay + ny * dd)])
        lm = _P([(ax, ay), (bx, by), (bx - nx * dd, by - ny * dd), (ax - nx * dd, ay - ny * dd)])
        return lp.intersection(assiette).area, lm.intersection(assiette).area

    try:
        a_p, a_m = _aire(t)
    except Exception:
        return nx, ny
    if max(a_p, a_m) < _PREC_M * dl:     # R au ras d'un sommet → les deux lanières quittent l'assiette
        Dp = 12.0
        ep = _P([(ax, ay), (bx, by), (bx + nx * Dp, by + ny * Dp), (ax + nx * Dp, ay + ny * Dp)]).difference(assiette).area
        em = _P([(ax, ay), (bx, by), (bx - nx * Dp, by - ny * Dp), (ax - nx * Dp, ay - ny * Dp)]).difference(assiette).area
        return (nx, ny) if ep >= em else (-nx, -ny)
    return (nx, ny) if a_p <= a_m else (-nx, -ny)


def _cote_exterieur(bords, mx: float, my: float, tx: float, ty: float):
    """Normale extérieure unitaire du bord d'assiette qui PORTE le recouvrement : le bord le plus proche du
    milieu (mx, my) de R qui lui est ~parallèle ET le recouvre en projection. La normale vient du SENS DE
    PARCOURS du contour (= (uy, -ux)), exacte même sur une assiette concave. None si aucun bord ne convient."""
    best = None
    for (px, py, ux, uy, el) in bords:
        if abs(ux * tx + uy * ty) < 0.94:          # > ~20° d'écart → pas le bord qui porte la voie
            continue
        t = (mx - px) * ux + (my - py) * uy          # projection du milieu de R sur le bord
        if t < -0.05 or t > el + 0.05:               # le bord doit RECOUVRIR R en projection
            continue
        dist = abs((mx - px) * (-uy) + (my - py) * ux)   # distance du milieu de R à la droite du bord
        if best is None or dist < best[0]:
            best = (dist, uy, -ux)                   # normale extérieure = (dy, -dx) du sens de parcours
    if best is None:
        return None
    return best[1], best[2]


def _reach_depuis_voie(libre, acces, voie, passage, assiette):
    """NOYAU ROULANT atteignable depuis la voie à `passage` donné (demi-largeur `passage`/2). Construction FIX-10→19
    (bande de voie le long du recouvrement, mur de contour, érosion, composante contenant la graine de bande).
    Extrait de `_desserte_core` pour être partagé par le COMPTAGE (une place est desservie si son approche ∈ reach)
    ET la LARGEUR DE DESSERTE (FIX-19, au niveau des allées). Renvoie le polygone `reach` (vide si pas de raccord)."""
    import math as _math
    from shapely.ops import linemerge, unary_union
    from shapely.geometry import Polygon as _Poly
    from shapely.geometry import LineString as _LS
    vide = _Poly()
    r_pass = max(passage, 1e-3) / 2.0
    _er = r_pass - 1e-4
    if voie is not None and not getattr(voie, "is_empty", True):
        voie_l = voie if voie.geom_type in ("LineString", "MultiLineString") else voie.boundary
        cvt = voie_l.intersection(libre)
        merged = linemerge(cvt) if cvt.geom_type == "MultiLineString" else cvt
        segs = ([merged] if merged.geom_type == "LineString"
                else [s for s in getattr(merged, "geoms", []) if s.geom_type == "LineString"])
        recouvrements = []
        for s in segs:                                          # FIX-19 (A) : recouvrement coudé → tronçons droits
            for (p0, p1) in _troncons_droits(s):
                seg = _LS([p0, p1])
                if seg.length >= passage - _PREC_M:
                    recouvrements.append(seg)
        if not recouvrements:
            return vide
        D = 12.0
        acces_poly = unary_union([g if g.is_valid else g.buffer(0) for g in (acces or [])])
        assiette_eff = (assiette if (assiette is not None and not getattr(assiette, "is_empty", True))
                        else libre.convex_hull)
        contour = assiette_eff.boundary.buffer(_MUR_EP)
        # FIX-20 — CHAQUE TRONÇON DROIT du recouvrement est une OUVERTURE SÉPARÉE : sa propre bande (bornée à son
        # aplomb = l'extrusion perpendiculaire de ce seul tronçon), son propre percement du mur de contour (le mur
        # reste FERMÉ partout ailleurs, DONC à l'angle entre deux tronçons), son propre noyau atteignable. On réunit
        # seulement les NOYAUX à la fin. Ainsi la bande extérieure d'un tronçon ne peut ni enjamber l'angle ni
        # rejoindre celle de l'autre par l'extérieur (sinon, aux grands passages, elle sur-estimait la desserte en
        # pénétrant le projet par l'angle). Un recouvrement DROIT (un seul tronçon) est inchangé.
        reach_comps = []
        for R in recouvrements:
            (ax, ay), (bx, by) = R.coords[0], R.coords[-1]
            dl = _math.hypot(bx - ax, by - ay)
            if dl <= 1e-9:
                continue
            tx, ty = (bx - ax) / dl, (by - ay) / dl
            cote = _cote_exterieur_mesure(assiette_eff, ax, ay, bx, by, -ty, tx)
            if cote is None:                                    # recouvrement NON sur le bord (voie intérieure)
                continue
            nx, ny = cote
            poly = _Poly([(ax, ay), (bx, by), (bx + nx * D, by + ny * D), (ax + nx * D, ay + ny * D)])
            band_r = poly.difference(assiette_eff).buffer(0)
            comps = (list(band_r.geoms) if band_r.geom_type == "MultiPolygon"
                     else ([band_r] if not band_r.is_empty else []))
            kept = []
            for pc in comps:
                inter = pc.intersection(acces_poly)             # chevauchement RÉEL de l'accès LE LONG de R
                if inter.is_empty:
                    continue
                if _etendue_le_long(inter, ax, ay, tx, ty) + _PREC_M >= passage:
                    kept.append(pc)
            if not kept:
                continue
            band = unary_union(kept).buffer(0)
            ouverture = R.buffer(_MUR_EP * 3.0, cap_style=2)    # le mur n'est percé QUE sur CE tronçon (bouts plats)
            band = band.difference(contour.difference(ouverture)).buffer(0)
            bouts = (list(band.geoms) if band.geom_type == "MultiPolygon"
                     else ([band] if not band.is_empty else []))
            band = unary_union([pc for pc in bouts if pc.intersects(ouverture)]).buffer(0)
            if band.is_empty:
                continue
            surface = _grille_mm([libre, band])                 # FIX-19 (C) : nettoyée au mm avant l'érosion
            seed = band.buffer(-_er).buffer(0)
            noyau = surface.buffer(-_er).buffer(0)
            if seed.is_empty or noyau.is_empty:
                continue
            comps_n = list(noyau.geoms) if noyau.geom_type == "MultiPolygon" else [noyau]
            brut = unary_union([c for c in comps_n if c.intersects(seed)]).buffer(0)
            if brut.is_empty:
                continue
            # FIX-20 — le disque doit TENIR dans un VRAI couloir : l'aire roulante érodée (`libre` ⊖ r), OU la bande
            # de voie, la TRAVERSÉE de l'ouverture étant seule permise par une GORGE (le recouvrement dilaté de la
            # demi-largeur). Sans cette borne, l'érosion de l'UNION (libre ∪ bande) élargissait un étranglement
            # SITUÉ PRÈS DE L'OUVERTURE (la bande comble la gorge) → le noyau franchissait un couloir plus étroit
            # que `w` → desserte sur-estimée dans un angle. Ailleurs qu'à l'ouverture, on exige la largeur de `libre`.
            gorge = R.buffer(r_pass + _MUR_EP * 2.0)
            admissible = unary_union([libre.buffer(-_er), band, gorge]).buffer(0)
            coeur = brut.intersection(admissible).buffer(0)
            pcs = list(coeur.geoms) if coeur.geom_type == "MultiPolygon" else ([coeur] if not coeur.is_empty else [])
            reach_comps.extend(c for c in pcs if c.intersects(seed))
    else:
        noyau = libre.buffer(-_er).buffer(0)                    # tests unitaires sans voie
        if noyau.is_empty:
            return vide
        comps = list(noyau.geoms) if noyau.geom_type == "MultiPolygon" else [noyau]
        reach_comps = [max(comps, key=lambda g: g.area)] if comps else []
    if not reach_comps:
        return vide
    return unary_union(reach_comps)


def _sonder_place(pg, largeur_requise, libre, reach, r_pass):
    """Une place : est-elle DESSERVIE (point d'approche devant le nez, à la demi-largeur, ∈ `reach` au mm près) et
    quel est son DÉFICIT de dégagement (part du rectangle de largeur requise non couverte par `libre`) ? Extrait de
    `_desserte_core`. Renvoie (état, valeur) : état None = place à ignorer (nez indéfini) ; False = NON desservie
    (valeur = aire de la place) ; True = desservie (valeur = déficit minimal du côté réellement desservi)."""
    from shapely.geometry import Polygon as _P
    from shapely.geometry import Point as _Pt
    W = max(float(largeur_requise), 0.1)
    c = pg.centroid
    coords = list(pg.exterior.coords)[:-1]
    edges = []
    for i in range(len(coords)):
        a, b = coords[i], coords[(i + 1) % len(coords)]
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        edges.append((L, a, b, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)))
    if not edges:
        return None, 0.0
    Lmin = min(e[0] for e in edges)
    petits = [e for e in edges if e[0] <= Lmin * 1.3]           # les DEUX petits côtés (nez ET arrière)
    options = []
    for _L, a, b, mid in petits:
        nx, ny = mid[0] - c.x, mid[1] - c.y
        ln = (nx * nx + ny * ny) ** 0.5 or 1.0
        nx, ny = nx / ln, ny / ln
        sonde = _P([a, b, (b[0] + W * nx, b[1] + W * ny), (a[0] + W * nx, a[1] + W * ny)])
        if not sonde.is_valid or sonde.area < 0.5:
            continue
        clear = sonde.intersection(libre)
        deficit = max(0.0, sonde.area - clear.area)
        approche = _Pt(mid[0] + r_pass * nx, mid[1] + r_pass * ny)
        # FIX-20 — une place est desservie SSI son point d'approche (1) appartient au noyau atteignable `reach`
        # (connecté à la voie, au mm près) ET (2) le DISQUE DE RAYON r_pass TIENT RÉELLEMENT à l'approche, dans
        # l'AIRE ROULANTE : approche ≥ r_pass − 1 mm du bord de `libre`. Sans (2), aux grands passages l'approche
        # pouvait n'être qu'à 1 mm d'un bord de la BANDE extérieure (la voiture ne tient pas dans le couloir réel) →
        # desserte sur-estimée dans un angle (c'est la garde que l'oracle applique par `boundary.distance ≥ r`).
        tient = libre.buffer(-(r_pass - _PREC_M)).distance(approche) <= _PREC_M
        desservie = (not clear.is_empty) and tient and reach.distance(approche) <= _PREC_M
        options.append((deficit, desservie))
    if not options:
        return None, 0.0
    desservies = [d for d, sv in options if sv]
    if not desservies:
        return False, pg.area
    return True, min(desservies)


def _desserte_core(allees, places, largeur_requise: float, acces=None, voie=None,
                   passage: float = _PASSAGE_MIN_M, assiette=None) -> tuple[float, int]:
    """ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — DÉGAGEMENT mesuré DEVANT CHAQUE PLACE, sur l'allée DÉSÉTRANGLÉE.
    ETUDE-STATIONNEMENT-FIX-9 (relecture) — NOYAU UNIQUE : la desserte d'une place et la LARGEUR du goulet
    reposent sur le MÊME calcul (ce noyau roulant érodé de `passage`/2). Renvoie (aire manquante, nb de places
    desservies). `_pincement_allee` l'appelle à `passage = _PASSAGE_MIN_M` (2,40 m) ; `_largeur_min_desserte`
    cherche le plus grand `passage` qui dessert encore une place → une place comptée ⟹ goulet ≥ 2,40 m.
    Deux pièges du PLAN réel, traités ensemble :
      1. CLEARANCE devant la place — on sonde un rectangle de la largeur de la place extrudé de `largeur_requise`
         vers CHACUN des deux petits côtés (nez/arrière) et on garde le MEILLEUR (déficit minimal) : l'allée
         dessert la place par un seul côté, l'autre donne sur un mur. Prendre « le plus près de l'allée » se
         trompait de côté sur les parkings denses (faux déficit de 4 m sur une allée de 5 m → écroulait HT0538
         et les assemblages). Prendre le min des deux ignore le côté mur.
      2. PINCEMENT de circulation — avant de sonder, on OUVRE l'allée (érosion/dilatation de `_PASSAGE_MIN_M`/2) :
         tout étranglement plus étroit que le passage d'une voiture (BW2635 : 2,25 m) DISPARAÎT, si bien que les
         places qui n'étaient desservies QU'À TRAVERS ce goulet perdent leur dégagement et sont comptées
         manquantes. Une allée large (≥ `_PASSAGE_MIN_M`) survit à l'ouverture → aucun faux positif.
    On ne compte que les places VRAIMENT déficientes (manque > `_DEGAGEMENT_PLACE_FLOOR_M2`). Renvoie l'aire (m²)."""
    if not allees or not places:
        return 0.0, 0
    # FIX-19 (défauts B & C) — géométrie nettoyée à la RÉSOLUTION du mm AVANT tout calcul : des pavés strictement
    # jointifs (places/allées/accès se touchent sans se chevaucher), désalignés par une rotation quelconque ou le
    # bruit d'une transformation monde→local, fusionnent en UN polygone au lieu d'un MultiPolygon que l'érosion
    # scinderait ; la fermeture 1 mm ne ponte jamais un vrai vide (2 cm restent 2 cm).
    libre = _grille_mm(list(allees) + list(acces or []))
    if libre.is_empty:
        return 0.0, 0
    _aire_places = float(sum((p if p.is_valid else p.buffer(0)).area for p in places))
    r_pass = max(passage, 1e-3) / 2.0
    # NOYAU ROULANT atteignable depuis la voie (FIX-10→19, cf. `_reach_depuis_voie`) : une place est desservie si
    # son point d'approche, devant le nez à la demi-largeur, appartient à ce noyau (`_sonder_place`).
    reach = _reach_depuis_voie(libre, acces, voie, passage, assiette)
    if reach.is_empty:
        return _aire_places, 0
    manque = 0.0
    nb_desservies = 0
    for p in places:
        pg = p if p.is_valid else p.buffer(0)
        etat, val = _sonder_place(pg, largeur_requise, libre, reach, r_pass)
        if etat is None:
            continue
        if etat is False:
            manque += val            # aucun couloir roulant jusqu'à la voie → place NON comptée
            continue
        nb_desservies += 1           # une voiture atteint la place par un passage ≥ `passage`
        if val > _DEGAGEMENT_PLACE_FLOOR_M2:
            manque += val
    return float(manque), nb_desservies


def _pincement_allee(allees, places, largeur_requise: float, acces=None, voie=None, assiette=None) -> float:
    """Aire (m²) de dégagement manquante au passage réglementaire (2,40 m) — cf. `_desserte_core`."""
    return _desserte_core(allees, places, largeur_requise, acces, voie, _PASSAGE_MIN_M, assiette)[0]


def _goulet_place(pg, largeur_requise, libre, acces, voie, assiette):
    """FIX-20 — le plus grand passage `w` auquel LA place `pg` reste DESSERVIE, mesuré avec EXACTEMENT la sonde du
    comptage (`_sonder_place` sur le noyau atteignable à `w`). Dichotomie sur [0 ; 12] m. C'est le goulot du trajet
    réel de cette place (son couloir le plus étroit depuis la voie), sans AUCUN rattachement à une allée."""
    lo, hi = 0.0, 12.0
    for _ in range(26):
        w = (lo + hi) / 2.0
        reach = _reach_depuis_voie(libre, acces, voie, w, assiette)
        if (not reach.is_empty) and _sonder_place(pg, largeur_requise, libre, reach, w / 2.0)[0] is True:
            lo = w
        else:
            hi = w
    return lo


def _largeur_min_desserte(allees, places, largeur_requise: float, acces=None, voie=None, assiette=None) -> float:
    """LARGEUR DE DESSERTE DE L'OPÉRATION (FIX-20, définition du relecteur). La règle (p.ex. 5 m dès 7 logements)
    porte sur la desserte de l'OPÉRATION. Définition : le MINIMUM, sur TOUTES les places COMPTÉES à 2,40 m, du plus
    grand passage auquel cette place reste desservie — mesuré avec EXACTEMENT la sonde du comptage (`_sonder_place`,
    prouvée juste). PLUS AUCUN rattachement d'une place à une allée.

    Corrige deux sur-estimations de FIX-19 (relecture 2) : (1) `reach.intersects(allée)` déclarait TOUTE l'allée
    atteinte dès qu'un bout l'était (une allée de 2,5 m pendue à un accès de 6 m annonçait 5 m ; un pincement de 3 m
    DANS une allée d'un seul tenant annonçait 6 m) ; (2) une place accrochée directement à l'accès était rattachée à
    une allée arbitraire, son vrai trajet (par l'accès) jamais contraint (6 m annoncés pour 2,4 m réels). Le goulot
    par place, mesuré avec la sonde du comptage, ne connaît ni l'un ni l'autre piège.

    Le goulet AFFICHÉ et le contrôle de la règle utilisent CETTE valeur ; l'oracle la mesure place par place par ses
    propres moyens (grille affinée au besoin). Si AUCUNE place n'est comptée à 2,40 m, on rend le plus grand passage
    desservant encore ≥ 1 place (l'étranglement, cohérent avec « 0 place comptée »)."""
    if not allees or not places:
        return 0.0
    libre = _grille_mm(list(allees) + list(acces or []))
    if libre.is_empty:
        return 0.0
    reach0 = _reach_depuis_voie(libre, acces, voie, _PASSAGE_MIN_M, assiette)
    pgs = [p if p.is_valid else p.buffer(0) for p in places]
    comptees = ([pg for pg in pgs if _sonder_place(pg, largeur_requise, libre, reach0, _PASSAGE_MIN_M / 2.0)[0] is True]
                if not reach0.is_empty else [])
    if not comptees:
        # aucune place comptée à 2,40 m → ÉTRANGLEMENT (plus grand passage desservant ≥ 1 place quelconque).
        lo, hi = 0.0, 12.0
        for _ in range(26):
            w = (lo + hi) / 2.0
            if _desserte_core(allees, places, largeur_requise, acces, voie, w, assiette)[1] >= 1:
                lo = w
            else:
                hi = w
        return lo
    return min(_goulet_place(pg, largeur_requise, libre, acces, voie, assiette) for pg in comptees)


def _ground_tiles(scene: Scene):
    """Objets du PLAN DE SOL (niveau 0 pour le bâti) qui pavent l'assiette sans se chevaucher."""
    out = []
    for o in scene.objets:
        # ETUDE-V6-2 (Lot 3) — la rampe de sous-sol est un objet du PLAN DE SOL : elle PAVE l'assiette
        # au même titre que l'accès aérien (sinon la somme des surfaces ne boucle pas).
        if o.kind in ("place", "allee", "acces", "rampe", "espace_libre"):
            out.append(o)
        elif o.kind in ("module", "noyau", "coursive") and o.niveau == 0:
            out.append(o)
    return out


def verifier_geometrie(scene: Scene, terrain, conv: Conventions, cap: Capacite,
                       regles: ReglesZone) -> list[CheckGeo]:
    checks: list[CheckGeo] = []
    zone = terrain.zone_implantation
    assiette = terrain.assiette
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    places = [o.geom_world for o in scene.of("place")]
    allees = [o.geom_world for o in scene.of("allee")]
    acces = [o.geom_world for o in scene.of("acces")]
    modules = scene.of("module")

    hors = [b for b in batis if not zone.buffer(_TOL_CONTENU).contains(b)]
    checks.append(CheckGeo("bâtiments ⊆ zone d'implantation", not hors,
                           f"{len(hors)} hors zone" if hors else f"{len(batis)} bâtiment(s) dans la zone"))

    bati_u = unary_union(batis) if batis else None
    dedans = all(assiette.buffer(_TOL_CONTENU).contains(g) for g in places + allees + acces)
    hors_bati = True
    if bati_u is not None:
        hors_bati = all(g.intersection(bati_u).area <= _TOL_AIRE for g in places + allees + acces)
    checks.append(CheckGeo("places/allées/accès ⊆ assiette, hors bâti", dedans and hors_bati))

    # non-chevauchement sur TOUS les couples du plan de sol (aire d'intersection = 0)
    tiles = [(o.geom_world if o.geom_world.is_valid else o.geom_world.buffer(0))
             for o in _ground_tiles(scene)]
    chev = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i].intersection(tiles[j]).area > _TOL_AIRE:
                chev += 1
    checks.append(CheckGeo("aucun chevauchement — TOUS couples (aire ∩ = 0)", chev == 0, f"{chev} paire(s)"))

    # somme des surfaces mesurées = assiette
    somme = sum(t.area for t in tiles)
    checks.append(CheckGeo("somme des surfaces mesurées = assiette", abs(somme - assiette.area) < 1.0,
                           f"Σ={somme:.1f} vs assiette {assiette.area:.1f}"))

    allee_u = unary_union(allees) if allees else None
    if places and allee_u is not None:
        touche = all(p.distance(allee_u) < 1e-6 for p in places)
    else:
        touche = not places
    checks.append(CheckGeo("chaque place touche une allée", touche))

    # allées reliées à l'accès ; accès sur voie ; aucune allée sans places desservies
    acc_ok = False
    if acces and allee_u is not None:
        acc_u = unary_union(acces)
        relie = acc_u.distance(allee_u) < 1e-6
        voie_u = unary_union(terrain.voie_edges) if terrain.voie_edges else None
        sur_voie = (voie_u is not None and acc_u.distance(voie_u) < 0.6)
        # chaque morceau d'allée est desservi (a au moins une place) et relié à l'accès
        places_u = unary_union(places) if places else None
        allees_desservies = all(
            (places_u is not None and a.distance(places_u) < 1e-6) and a.distance(acc_u) < 1e-6
            for a in allees)
        acc_ok = relie and sur_voie and allees_desservies
    elif not places:
        acc_ok = True
    checks.append(CheckGeo("allées reliées à l'accès (sur voie), aucune en cul-de-sac", acc_ok))

    # allée COUPÉE au droit des places : aucun tronçon mort (ni place desservie, ni jonction d'accès).
    # Une place touche l'allée sur sa largeur ; on couvre l'allée par (places ∪ accès) bufferisé d'une
    # profondeur de place. Un prolongement d'allée dans le vide (ex. au-delà de la dernière place) reste.
    if places and allee_u is not None:
        couvre = unary_union(places + acces).buffer(conv.place_longueur_m)
        mort = allee_u.difference(couvre)
        checks.append(CheckGeo("allée sans tronçon mort (coupée au droit des places)",
                               mort.area < 1.0, f"{mort.area:.1f} m² morts"))

    # ETUDE-STATIONNEMENT-FIX-2 (LOT 3) — largeur du DÉGAGEMENT devant les places mesurée LOCALEMENT, pas sur
    # la boîte englobante : une allée clippée à un bord oblique peut pincer à 2,25 m au droit des places tout en
    # ayant une boîte de 5 m (cas BW2635 : 13 places à 2,25 m « validées » à tort). On mesure le pincement réel.
    # ETUDE-STATIONNEMENT-FIX-3 (LOT 1) — les DEUX géométries DANS LE MÊME REPÈRE : `allees` et `places` sont
    # ici en coordonnées PROJETÉES (geom_world) ; l'ancien code passait l'allée en geom_local → intersection
    # avec les places (geom_world) vide → pincement toujours 0 en production (le test unitaire, lui, était dans
    # un seul repère et passait). Sur BW2635 : 25,25 m² de pincement, 2,25 m au droit de 13 places.
    # ETUDE-STATIONNEMENT-FIX-4 (LOT 1) — mesure EXACTE en coordonnées LOCALES (repère aligné sur l'assiette) :
    # places, allées et accès y sont des rectangles AXÉS, sans l'erreur flottante de la rotation monde↔local
    # (qui faisait un faux déficit de ~0,008 m sur une place et écroulait AD0887 à 0,02 m² près). La voie locale
    # relie les bandes. Le même repère pour tous → un déficit mesuré est RÉEL (4,99 m pour 5 m exigés échoue).
    _allees_l = [o.geom_local for o in scene.of("allee")]
    _places_l = [o.geom_local for o in scene.of("place")]
    _acces_l = [o.geom_local for o in scene.of("acces")]
    _voie_l = unary_union(scene.voie_local) if getattr(scene, "voie_local", None) else None
    pince = _pincement_allee(_allees_l, _places_l, conv.allee_largeur_m, _acces_l, voie=_voie_l,
                             assiette=getattr(scene, "assiette_local", None))
    larg_ok = pince < _DEGAGEMENT_SEUIL_M2
    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — contrôle DUR, y compris sur un ASSEMBLAGE : la mesure par sonde du
    # meilleur des deux côtés (nez/arrière) + désétranglement de la circulation ne crée plus de faux pincements
    # sur le pavage dense (L'Étang-Salé 27 places OK), donc le dégagement d'un assemblage est aussi contraignant
    # que sur une parcelle seule (plus de « consultatif »). Il se calcule sur la géométrie FUSIONNÉE des parcelles.
    checks.append(CheckGeo(f"dégagement d'allée ≥ {conv.allee_largeur_m} m au droit des places (mesuré localement)",
                           larg_ok, "" if larg_ok else f"{pince:.1f} m² de dégagement sous la largeur requise"))

    dim_ok = True
    for o in modules:
        mnx, mny, mxx, mxy = o.geom_local.bounds
        if (mxx - mnx) < conv.largeur_module(o.type_logement) - 0.05 or \
           (mxy - mny) < conv.profondeur_logement_m() - 0.05:
            dim_ok = False
    checks.append(CheckGeo("dimensions modules ≥ convention", dim_ok))

    # ETUDE-V6-2 (Lot 3) — en sous-sol, les places sont au niveau −1 (aucun objet « place » au sol) :
    # on confronte alors le nombre annoncé au nombre logé au sous-sol, pas aux places dessinées.
    places_dessinees = (getattr(cap, "places_sous_sol", 0)
                        if getattr(cap, "stationnement_mode", "aerien") == "sous_sol" else len(places))
    nb_ok = (cap.logements == len(modules)) and (cap.places == places_dessinees)
    checks.append(CheckGeo("nb annoncé = nb dessiné (logements, places)", nb_ok))

    # SDP mesurée = modules + noyaux (coursive ouverte HORS SDP, art. R111-22 c. urb. — LOT D)
    sdp_mes = round(sum(o.geom_local.area for o in scene.objets
                        if o.kind in ("module", "noyau")), 1)
    emp_mes = round(unary_union([o.geom_local for o in scene.of("batiment_emprise")]).area, 1) if batis else 0.0
    surf_ok = abs(sdp_mes - cap.sdp_m2) < 0.2 and abs(emp_mes - cap.emprise_sol_m2) < 0.2
    checks.append(CheckGeo("surfaces tableau = surfaces mesurées", surf_ok))

    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None:
        # FAISA-REGLES-1 (E-059) — hauteur RÉELLE du projet selon la règle (égout/faîtage, toiture comptée).
        h, base, _est = hauteur_projet_m(conv, regles, cap.niveaux)
        checks.append(CheckGeo(f"hauteur projet ({base}) ≤ hauteur réglementaire",
                               h <= r.valeur + 1e-9, f"{_fr(h)} m ≤ {_fr(r.valeur)} m"))
    return checks


def geometrie_valide(checks: list[CheckGeo]) -> bool:
    # les checks CONSULTATIFS (ex. dégagement sur assemblage) sont affichés mais n'invalident pas le candidat.
    return all(c.ok for c in checks if not getattr(c, "advisory", False))


# --------------------------------------------------------------- réglementaires (4 états)
@dataclass
class ControleReg:
    nom: str
    regle: str
    mesure: str
    resultat: str
    citation: Optional[str] = None
    detail: Optional[str] = None


def _n_batiments(scene: Scene) -> int:
    return len(scene.of("batiment_emprise"))



def _distance_min_batiments(scene: Scene) -> Optional[float]:
    """Plus petite distance MESURÉE (bord à bord) entre deux emprises bâties, en m. None si < 2."""
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    if len(batis) < 2:
        return None
    return min(batis[i].distance(batis[j]) for i in range(len(batis)) for j in range(i + 1, len(batis)))


def _distance_requise(dc, cap: Capacite, conv: Conventions, max_logts_bati: int = 0) -> tuple[float, str, str]:
    """(distance requise en m, libellé de règle, mention) pour une règle de distance CHIFFRABLE.
    La hauteur retenue est celle du bâtiment proposé (niveaux × hauteur d'étage) ; `cumulee` = H+h
    (deux volumes identiques dans le modèle → 2×h), `plus_haut` = H du plus haut (= h).
    `max_logts_bati` = nombre de logements du bâtiment le plus peuplé (seuil « grand bâtiment »)."""
    h = cap.niveaux * conv.hauteur_etage_m
    if dc.forme == "fixe":
        # ETUDE-STATIONNEMENT-FIX-6 (point 3) — seuil PAR BÂTIMENT : le minimum passe à `min_m_grand_batiment`
        # dès qu'un bâtiment dépasse `seuil_logements_grand_batiment` logements (Le Tampon Ua8.2 : 3 m, porté
        # à 6 m si > 5 logements). On DIT quel seuil s'applique et pourquoi, au lieu d'appliquer 3 m aveuglément.
        if (dc.min_m_grand_batiment is not None and dc.seuil_logements_grand_batiment is not None
                and max_logts_bati > dc.seuil_logements_grand_batiment):
            return (float(dc.min_m_grand_batiment),
                    f"≥ {dc.min_m_grand_batiment:.1f} m (bâtiment de {max_logts_bati} logements > "
                    f"{dc.seuil_logements_grand_batiment})",
                    f"seuil relevé à {dc.min_m_grand_batiment:.0f} m : un bâtiment compte {max_logts_bati} "
                    f"logements (> {dc.seuil_logements_grand_batiment})")
        if dc.min_m_grand_batiment is not None and dc.seuil_logements_grand_batiment is not None:
            return (float(dc.min_m or 0.0),
                    f"≥ {dc.min_m:.1f} m (aucun bâtiment > {dc.seuil_logements_grand_batiment} logements)",
                    f"seuil de base {dc.min_m:.0f} m : le plus grand bâtiment compte {max_logts_bati} "
                    f"logements (≤ {dc.seuil_logements_grand_batiment})")
        return float(dc.min_m or 0.0), f"≥ {dc.min_m:.1f} m (distance fixe)", ""
    if dc.forme == "relative":
        base = 2.0 * h if dc.base_hauteur == "cumulee" else h
        req = (dc.fraction_hauteur or 0.0) * base
        plancher = float(dc.min_m or 0.0)
        req_final = max(req, plancher)
        quoi = "H+h" if dc.base_hauteur == "cumulee" else "H"
        lib = f"≥ {dc.fraction_hauteur:g}×{quoi} = {req:.1f} m" + (f", min {plancher:.0f} m" if plancher else "")
        mention = f"hauteur retenue {h:.1f} m (R+{cap.niveaux - 1})"
        return req_final, lib, mention
    if dc.forme == "conditionnelle":
        # cas le plus strict = façades AVEC ouvertures
        req = float(dc.avec_ouvertures_m or 0.0)
        mention = "cas le plus strict retenu (façades avec ouvertures)"
        if dc.fraction_hauteur is not None:
            base = 2.0 * h if dc.base_hauteur == "cumulee" else h
            req = max(req, dc.fraction_hauteur * base)
            mention += f" ; hauteur retenue {h:.1f} m"
        lib = f"≥ {req:.1f} m (avec ouvertures ; sans : {dc.sans_ouvertures_m:g} m)" if dc.sans_ouvertures_m \
            else f"≥ {req:.1f} m (façades avec ouvertures)"
        return req, lib, mention
    # contiguité
    if dc.contiguite_autorisee:
        return 0.0, "contiguïté autorisée (aucune distance imposée)", "les volumes peuvent être accolés"
    return 1e-6, "contiguïté non autorisée (volumes disjoints)", ""


def _ppr_bleue_touche_projet(scene: Scene, terrain) -> list[str]:
    """ETUDE-FIABLE-1 (LOT C5) — quelle(s) PARTIE(S) du projet touche(nt) le PPR bleu : bâtiment, accès
    OU sous-sol (plus seulement le bâti). La géométrie ne change pas ; on le SIGNALE dans les points à
    instruire (« Prescriptions PPR à vérifier »). Renvoie la liste des parties concernées (vide = aucune)."""
    if terrain.ppr_bleue is None or terrain.ppr_bleue.is_empty:
        return []
    parties: list[str] = []
    for kind, libelle in (("batiment_emprise", "bâtiment"), ("acces", "accès"),
                          ("sous_sol_emprise", "sous-sol")):
        geoms = [o.geom_world for o in scene.of(kind) if o.geom_world is not None]
        if geoms and unary_union(geoms).intersection(terrain.ppr_bleue).area > _TOL_AIRE:
            parties.append(libelle)
    return parties


def controles_reglementaires(scene: Scene, terrain, conv: Conventions, cap: Capacite,
                             regles: ReglesZone) -> list[ControleReg]:
    out: list[ControleReg] = []
    # FAISA-REGLES-1 (E-058) — MÊME BASE que le dessin pour l'emprise au sol et la pleine terre : l'emprise
    # et la pleine terre sont MESURÉES sur la géométrie (EPSG:2975) ; le plafond CES/perméabilité est donc
    # calculé sur la SURFACE DESSINÉE de la portion constructible (`aire_dessin_m2`), pas sur la contenance
    # cadastrale (qui diffère du dessin de ~1-3 %). Numérateur et dénominateur dans le même repère.
    # (Le vrai Terrain porte toujours `aire_dessin_m2` ; repli défensif sur la contenance pour une
    # scène synthétique de test qui ne l'expose pas.)
    _aire_dessin = getattr(terrain, "aire_dessin_m2", None)
    contenance = _aire_dessin if _aire_dessin is not None else terrain.contenance_totale_m2

    r = regles.emprise_ces
    if r.validee and r.valeur is not None:
        plafond = contenance * r.valeur / 100.0
        ok = cap.emprise_sol_m2 <= plafond + 1e-6
        out.append(ControleReg("Emprise au sol", f"≤ {plafond:.0f} m² ({r.valeur:.0f} % de la surface du terrain)",
                               f"{cap.emprise_sol_m2:.0f} m²", REUSSI if ok else ECHOUE,
                               r.citation_complete, f"écart {plafond - cap.emprise_sol_m2:+.0f} m²"))
    elif getattr(r, "absent", False):
        # ETUDE-STATIONNEMENT-FIX-1 (LOT 5) — le PLU NE RÉGLEMENTE PAS l'emprise (silence prouvé, cité) :
        # « Non réglementé » (sans objet), pas « Non effectué » (qui laisserait croire à une lacune LABUSE).
        out.append(ControleReg("Emprise au sol", "non réglementé (silence prouvé)", f"{cap.emprise_sol_m2:.0f} m²",
                               NON_APPLICABLE, r.citation_complete,
                               detail="le règlement ne fixe pas d'emprise au sol dans cette zone"))
    else:
        out.append(ControleReg("Emprise au sol", "règle non validée", f"{cap.emprise_sol_m2:.0f} m²", NON_EFFECTUE))

    r = regles.hauteur_plafond
    if r.validee and r.valeur is not None:
        # FAISA-REGLES-1 (E-059) — hauteur du PROJET mesurée selon la règle (égout/faîtage), rez + toiture
        # comptés ; marge prudente DITE (« hauteur estimée, toiture comprise ») quand la toiture est ajoutée.
        h, base, estimee = hauteur_projet_m(conv, regles, cap.niveaux)
        ok = h <= r.valeur + 1e-9
        base_lbl = "à l'égout" if base == "égout" else "au faîtage (pas d'égout chiffré)"
        mesure = (f"R+{cap.niveaux - 1} ≈ {_fr(h)} m {base}"
                  + (" (hauteur estimée, toiture comprise)" if estimee else ""))
        out.append(ControleReg("Hauteur", f"≤ {_fr(r.valeur)} m {base_lbl}",
                               mesure, REUSSI if ok else ECHOUE, r.citation_complete))
    else:
        out.append(ControleReg("Hauteur", "règle non validée", f"R+{cap.niveaux - 1}", NON_EFFECTUE))

    # ETUDE-V6-2 (Lot 3, correction) — HAUTEUR SUR TERRAIN EN PENTE : la hauteur à l'égout se mesure depuis
    # le terrain NATUREL. Sur une pente, la façade AVAL est plus haute que niveaux × étage du dénivelé sous
    # le bâtiment. On VÉRIFIE (dénivelé LiDAR) si un volume à toiture plate dépasserait le plafond à l'égout
    # côté aval : si oui, le bâtiment doit être EN GRADINS (partie aval possiblement R+(N-1), comme
    # l'architecte). LABUSE suppose des gradins (R+N conservé) et le SIGNALE — à confirmer par l'architecte.
    # ETUDE-V6-2 (Lot 3, correction §1) — GRADINS MESURÉS SUR LE LiDAR (plus de « à confirmer »). La hauteur
    # à l'égout se mesure depuis le TN sous chaque partie du bâtiment ; on MESURE le dénivelé sous le bâti
    # (pente LiDAR × plus grande dimension du bâti, borné par le dénivelé de la parcelle), puis on conclut :
    #   · toiture plate tenable si niveaux × étage + relief ≤ plafond égout ;
    #   · sinon bâtiment EN GRADINS (un décrochement par étage) qui tient R+N — nombre de gradins = relief/étage.
    pente = getattr(terrain, "pente", None)
    he = regles.hauteur_egout
    if isinstance(pente, dict) and pente.get("disponible") and he.validee and he.valeur is not None:
        import math
        denivele_parcelle = float(pente.get("denivele_m") or 0.0)
        pm = float(pente.get("pente_moyenne_pct") or 0.0) / 100.0
        batis_w = [o.geom_world for o in scene.of("batiment_emprise") if o.geom_world is not None]
        if batis_w:
            mnx, mny, mxx, mxy = unary_union(batis_w).bounds
            L_bati = max(mxx - mnx, mxy - mny)
        else:
            L_bati = math.sqrt(max(0.0, cap.emprise_sol_m2))
        relief_bati = round(min(denivele_parcelle, pm * L_bati), 1)
        etage = conv.hauteur_etage_m
        egout_plat = round(cap.niveaux * etage + relief_bati, 1)   # façade aval d'un volume à toiture plate
        src = pente.get("source") or "LiDAR"
        if relief_bati < 0.5:
            out.append(ControleReg("Hauteur sur terrain en pente", "terrain quasi plat",
                                   f"relief sous bâti {relief_bati:.1f} m ({src})", REUSSI, he.citation))
        elif egout_plat <= he.valeur + 1e-9:
            out.append(ControleReg(
                "Hauteur sur terrain en pente", f"≤ {he.valeur:.0f} m à l'égout (toiture plate tenable)",
                f"R+{cap.niveaux - 1}, relief sous bâti {relief_bati:.1f} m, {src} → {egout_plat:.1f} m aval",
                REUSSI, he.citation))
        else:
            # ETUDE-FIABLE-1 (LOT C4) — un volume DROIT à toiture plate dépasserait le plafond à l'égout côté
            # AVAL ; LABUSE SUPPOSE des gradins (R+N conservé) mais c'est une HYPOTHÈSE d'architecte, pas un
            # fait vérifié : le statut n'est donc plus « Réussi » mais « Implantation étagée à vérifier »
            # (À confirmer). Le prospect, lui, reste « À confirmer » (ci-dessous).
            n_gradins = max(2, math.ceil(relief_bati / etage) + 1)
            out.append(ControleReg(
                "Implantation étagée à vérifier", f"≤ {he.valeur:.0f} m à l'égout — supposerait un bâtiment EN GRADINS",
                f"R+{cap.niveaux - 1} en {n_gradins} gradins — relief {relief_bati:.1f} m mesuré, {src}",
                A_CONFIRMER, he.citation,
                detail=(f"relief sous le bâti {relief_bati:.1f} m (pente moy. {pente.get('pente_moyenne_pct')} %) : "
                        f"un volume droit à toiture plate dépasserait de {egout_plat - he.valeur:.1f} m à l'égout aval → "
                        f"il faudrait un bâtiment en {n_gradins} gradins (un décrochement d'étage chacun) pour tenir "
                        f"{he.valeur:.0f} m partout. LABUSE le suppose (R+{cap.niveaux - 1} conservé) ; à CONFIRMER par "
                        f"l'architecte (partie aval possiblement R+{max(0, cap.niveaux - 2)}).")))

    # ETUDE-STATIONNEMENT-FIX-1 — hauteur PRÈS DES LIMITES (ex. Ua10.3, bande de 3,60 m) : la règle EXISTE
    # mais le moteur ne sait pas la chiffrer → « Non vérifié », jamais traitée comme absente.
    bande = getattr(regles, "hauteur_bande_limite", None)
    if bande:
        _art = bande.get("article")
        _cit = (f"PLU art. {_art}" if _art else "") + (f" · p. {bande['page_pdf']}" if bande.get("page_pdf") else "")
        _cit = (_cit + (f" — « {bande['citation']} »" if bande.get("citation") else "")) or None
        out.append(ControleReg("Hauteur près des limites", "règle existante, non chiffrable par le moteur",
                               "à vérifier", A_CONFIRMER, _cit,
                               detail="une hauteur réduite s'applique dans une bande le long des limites "
                                      "séparatives (règle de gabarit) — non modélisée ici, à vérifier au projet"))

    # Prospect / hauteur relative (ex. L ≥ h/2) : non chiffrable par le moteur -> Non effectué
    if regles.prospect is not None:
        # ETUDE-STATIONNEMENT-FIX-4 (LOT 3) — chaque « non vérifié » CITE sa règle exacte : le prospect porte
        # désormais son article et sa page (HT0538 : Ud3.5 p. 85–86), plus en « détail » seul.
        _pr = regles.prospect
        _pcit = (f"PLU art. {_pr.article}" if getattr(_pr, "article", None) else "")
        _pcit += (f" · p. {_pr.page_pdf}" if getattr(_pr, "page_pdf", None) else "")
        _pcit = (_pcit + (f" — « {_pr.citation} »" if getattr(_pr, "citation", None) else "")) or None
        out.append(ControleReg("Prospect (hauteur relative)", "non chiffrable par le moteur",
                               "hauteur bornée par la seule règle absolue", A_CONFIRMER,
                               citation=_pcit,
                               detail=(_pr.citation or "règle de prospect L ≥ h/2 — à vérifier par l'architecte")))
    else:
        out.append(ControleReg("Prospect (hauteur relative)", "pas de règle de prospect", "—", NON_APPLICABLE))

    rv, rs = regles.recul_voie, regles.recul_separatives
    batis = [o.geom_world for o in scene.of("batiment_emprise")]
    dans_zone = all(terrain.zone_implantation.buffer(_TOL_CONTENU).contains(b) for b in batis)
    if rv.validee and rs.validee:
        cit = " ; ".join(c for c in (rv.citation_complete, rs.citation_complete) if c)
        # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — « premier rideau » (implantation à l'alignement, ou sur les
        # limites séparatives : Saint-Pierre Ud3.1/Ud3.2) est une règle de POSITION que ce moteur ne modélise
        # pas : il applique un recul uniforme. « Bâti dans la zone » ne prouve donc PAS le respect du premier
        # rideau → « Non vérifié » avec la règle citée, jamais « Reculs — Réussi ».
        _rideau = "premier rideau" in cit.lower() or "limites séparatives et au maximum" in cit.lower()
        if _rideau:
            out.append(ControleReg("Reculs", f"voie {rv.valeur:.0f} m · séparatives {rs.valeur:.0f} m",
                                   "règle de « premier rideau » (alignement / sur limites) non modélisée",
                                   A_CONFIRMER if dans_zone else ECHOUE, cit,
                                   detail="implantation en premier rideau (à l'alignement ou sur limites "
                                          "séparatives) à vérifier au projet — non modélisée par ce moteur"))
        else:
            out.append(ControleReg("Reculs", f"voie {rv.valeur:.0f} m · séparatives {rs.valeur:.0f} m",
                                   "bâti dans la zone d'implantation", REUSSI if dans_zone else ECHOUE, cit))
    else:
        out.append(ControleReg("Reculs", "règle non validée", "bâti dans la zone", NON_EFFECTUE))

    # RECETTE-4 — contrôle ACCÈS, AJOUTÉ SEULEMENT quand aucune voie n'est classée : l'étude continue sous
    # l'hypothèse d'un accès (arête la plus longue), signalée « À confirmer » (réhibitoire pour un verdict
    # « Exploitable » — cf. _A_CONFIRMER_BLOQUANTS). Voie classée = rien à signaler (comportement d'origine).
    if getattr(terrain, "voie_hypothese", False):
        out.append(ControleReg("Accès (voie)", "aucune limite classée « voie »",
                               "accès supposé sur l'arête la plus longue", A_CONFIRMER,
                               detail="classement de la limite « voie » non établi — accès à confirmer"))

    r = regles.pleine_terre
    if r.validee and r.valeur is not None:
        requis = contenance * r.valeur / 100.0
        assez = cap.pleine_terre_m2 >= requis - 1e-6
        # ETUDE-STATIONNEMENT-FIX-5 (point 4) — « Réussi » est réservé à ce qui est MESURÉ. La surface libre
        # mesurée montre la PLACE DISPONIBLE, pas que la pleine terre sera plantée et perméable : si la place
        # suffit, on dit « surface disponible : X pour Y exigés ; caractère planté et perméable à confirmer »
        # (À confirmer), jamais « Réussi ». Si la place manque, c'est un ÉCHEC franc.
        if assez:
            out.append(ControleReg(
                "Perméabilité (pleine terre)", f"≥ {requis:.0f} m² ({r.valeur:.0f} % de la surface du terrain)",
                f"surface disponible {cap.pleine_terre_m2:.0f} m²", A_CONFIRMER, r.citation_complete,
                detail="la surface libre mesurée suffit ; le caractère PLANTÉ et PERMÉABLE de la pleine terre "
                       "reste à confirmer au projet (ce contrôle ne mesure que la place disponible)"))
        else:
            out.append(ControleReg(
                "Perméabilité (pleine terre)", f"≥ {requis:.0f} m² ({r.valeur:.0f} % de la surface du terrain)",
                f"surface disponible {cap.pleine_terre_m2:.0f} m²", ECHOUE, r.citation_complete,
                f"écart {cap.pleine_terre_m2 - requis:+.0f} m² (place insuffisante)"))
    else:
        out.append(ControleReg("Perméabilité (pleine terre)", "règle non validée",
                               f"{cap.pleine_terre_m2:.0f} m²", NON_EFFECTUE))

    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — COEFFICIENT DE BIOTOPE (CBS), exigence de sol DISTINCTE de la
    # pleine terre : c'est une somme PONDÉRÉE de surfaces éco-aménageables (toiture végétalisée, dalle
    # plantée, pleine terre…) que ce moteur ne sait pas calculer → affichée SÉPARÉMENT « à vérifier », jamais
    # fondue dans la perméabilité (Saint-Pierre Ud5.1 : CBS 30 % AVEC au moins 20 % de pleine terre).
    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — ADMISSION DE L'HABITAT sous condition d'un schéma d'affectation en
    # annexe NON lu (ex. Saint-Louis UZ) : on N'ACCEPTE PAS la zone entière → « à vérifier » (bloquant pour un
    # verdict « Exploitable »), avec la règle citée. L'étude est servie, mais son admission même reste à établir.
    hav = getattr(regles, "habitat_a_verifier", None)
    if isinstance(hav, dict) and (hav.get("citation") or hav.get("article")):
        _cit = hav.get("citation")
        if hav.get("article"):
            _cit = f"{hav['article']}" + (f" · p. {hav['page_pdf']}" if hav.get("page_pdf") else "") + (f" — {_cit}" if _cit else "")
        out.append(ControleReg("Admission de l'habitat", "soumise à un schéma d'affectation (annexe)",
                               "à vérifier : l'habitat n'est pas admis sur toute la zone", A_CONFIRMER, _cit,
                               detail="l'admission de l'habitat dépend du schéma d'affectation en annexe, non "
                                      "lu par le moteur — à vérifier avant tout projet de logements"))

    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — PENTE DE TOITURE (ex. Le Tampon Ud11.5) : le moteur ne dessine pas
    # la toiture → règle de POSITION/forme non modélisée, affichée « Non vérifié » avec la règle citée (comme le
    # premier rideau), jamais passée sous silence.
    pt = getattr(regles, "pente_toiture", None)
    if isinstance(pt, dict) and (pt.get("citation") or pt.get("article")):
        _cit = pt.get("citation")
        if pt.get("article"):
            _cit = f"{pt['article']}" + (f" · p. {pt['page_pdf']}" if pt.get("page_pdf") else "") + (f" — {_cit}" if _cit else "")
        out.append(ControleReg("Pente de toiture", "règle de pente non modélisée",
                               "non vérifié (toiture non dessinée par le moteur)", A_CONFIRMER, _cit,
                               detail="pente de toiture imposée par le PLU — à vérifier au projet d'architecte"))

    rb = getattr(regles, "biotope", None)
    if rb is not None and rb.validee and rb.valeur is not None:
        _nom = (rb.nom or "coefficient de biotope (CBS)").strip()
        out.append(ControleReg(_nom[:1].upper() + _nom[1:], f"≥ {rb.valeur:.0f} % de la surface du terrain",
                               "non chiffré par le moteur (somme pondérée / surfaces éco-aménageables)", A_CONFIRMER,
                               rb.citation_complete,
                               detail="exigence de sol distincte de la pleine terre plantée — à vérifier au projet"))

    # ETUDE-V6-2 (Lot 3, correction §2) — ESPACES VERTS (part végétalisée du terrain, hors stationnement).
    # EV = espace libre végétalisable = pleine terre + surface sur dalle plantée (en sous-sol).
    ev = getattr(regles, "espaces_verts", None)
    if ev is not None and ev.validee and ev.pct is not None:
        requis = contenance * ev.pct / 100.0
        ev_m2 = (cap.pleine_terre_m2 or 0.0) + (getattr(cap, "sur_dalle_m2", 0.0) or 0.0)
        hs = " · hors stationnement" if ev.hors_stationnement else ""
        ok = ev_m2 >= requis - 1e-6
        out.append(ControleReg("Espaces verts", f"≥ {requis:.0f} m² ({ev.pct:.0f} %{hs})",
                               f"{ev_m2:.0f} m²", REUSSI if ok else ECHOUE, ev.citation_complete,
                               f"écart {ev_m2 - requis:+.0f} m²"))

    # ETUDE-V6-2 (Lot 3, correction §2) — MARGE PLANTÉE périphérique : une bande de largeur_m sur une
    # fraction du linéaire. Elle s'INSCRIT dans les reculs (voie/séparatives) : vérifiée si le plus
    # petit recul validé ≥ la largeur de la bande (sinon À confirmer).
    mp = getattr(regles, "marge_plantee", None)
    if mp is not None and mp.validee and mp.largeur_m is not None:
        reculs = [x.valeur for x in (regles.recul_voie, regles.recul_separatives)
                  if x.validee and x.valeur is not None]
        recul_min = min(reculs) if reculs else 0.0
        hm = " hors mitoyenneté" if mp.hors_mitoyennete else ""
        ok = recul_min >= mp.largeur_m - 1e-6
        lin = f" sur {mp.pct_lineaire:.0f} % du linéaire" if mp.pct_lineaire is not None else ""
        out.append(ControleReg("Marge plantée", f"bande {mp.largeur_m:.1f} m{lin}{hm}",
                               f"reculs ≥ {recul_min:.0f} m" if ok else f"recul {recul_min:.0f} m < {mp.largeur_m:.1f} m",
                               REUSSI if ok else A_CONFIRMER, mp.citation_complete,
                               detail=("la bande plantée s'inscrit dans les reculs (périphérie végétalisée)"
                                       if ok else "recul insuffisant pour loger la bande plantée — à confirmer")))

    b = regles.stationnement
    sous_sol = getattr(cap, "stationnement_mode", "aerien") == "sous_sol"
    place_mot = "places au sous-sol" if sous_sol else "places dessinées"
    # NB — le MOTEUR utilise ce contrôle pour la faisabilité (une place manquante plafonne la capacité) :
    # il GARDE donc son verdict géométrique REUSSI/ECHOUE (les places dessinées tiennent-elles ?). La
    # réserve CAPACITE-1 (D1) « barème par logement → règle collective non vérifiée » est portée à
    # l'AFFICHAGE par l'Étude (etude_faisabilite), SANS toucher la capacité du moteur (sinon on gonflerait
    # la capacité en retirant la contrainte — l'inverse de la prudence voulue).
    if b.validee and cap.places_imposees is not None:
        ok = cap.places >= cap.places_imposees
        # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — l'exigence expose la formule RETENUE (la plus exigeante) et la
        # part visiteur ; le détail porte la lecture écartée, pour que le document dise POURQUOI ce nombre.
        vis = getattr(cap, "places_imposees_visiteurs", 0) or 0
        res = getattr(cap, "places_imposees_residents", None)
        attendu = f"≥ {cap.places_imposees} places (barème validé)"
        if vis:
            attendu += f" — dont {res} résident + {vis} visiteur"
        det = [f"écart {cap.places - cap.places_imposees:+d}"]
        if getattr(cap, "stationnement_formule", None):
            det.append("formule retenue : " + cap.stationnement_formule)
        for f in getattr(cap, "stationnement_formules_ecartees", ()) or ():
            det.append("lecture écartée : " + f)
        out.append(ControleReg("Stationnement", attendu,
                               f"{cap.places} {place_mot}", REUSSI if ok else ECHOUE,
                               b.citation_complete, " · ".join(det)))
    elif b.validee and cap.places_imposees is None:
        # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — barème VALIDÉ mais ne couvrant pas le programme dessiné (forme
        # non modélisable ou typologie non prévue) : « Non vérifié », jamais « Réussi ». On n'invente rien.
        out.append(ControleReg("Stationnement", "règle ne couvrant pas le programme dessiné",
                               f"{cap.places} {place_mot}", A_CONFIRMER, b.citation_complete,
                               detail="le barème validé ne s'applique pas au programme tel que dessiné — "
                                      "nombre de places non vérifié ici (à confirmer au règlement)"))
    else:
        # ETUDE-V6 — barème manquant = ambiguïté (exigence non chiffrée) → À confirmer, pas « Non effectué ».
        # CAPACITE-1 (C4) — la règle EXISTE au PLU, elle n'est pas ingérée par LABUSE (jamais « non réglementé »).
        out.append(ControleReg("Stationnement", "règle existante, non ingérée par LABUSE", f"{cap.places} {place_mot}",
                               A_CONFIRMER, detail="règle de stationnement existante au PLU mais non ingérée par LABUSE — à vérifier au règlement"))

    # ETUDE-STATIONNEMENT-FIX-2 — places PUBLIQUES (hors parcelle) : exigées, à réaliser sur le domaine
    # public, PAS dessinées sur le terrain → affichées À PART, jamais ajoutées aux places à dessiner.
    _pub = getattr(cap, "places_publiques_imposees", 0) or 0
    if _pub:
        out.append(ControleReg("Stationnement public (hors parcelle)", f"{_pub} places sur le domaine public",
                               "non dessinées sur le terrain", A_CONFIRMER, b.citation_complete if b.validee else None,
                               detail="places publiques exigées par le règlement, à réaliser hors de la parcelle — à confirmer"))

    # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — conditions NON MODÉLISABLES du barème (ex. « dont au moins 0,5 place
    # à l'extérieur des espaces privatisés ») : affichées « à vérifier », JAMAIS comptées comme satisfaites.
    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — la HAIE paysagère au pourtour des aires de stationnement EST
    # mesurable : on confronte la distance aire de stationnement ↔ bâti à la largeur imposée (ex. Saint-Pierre
    # Ud6 : 1,50 m). En deçà, c'est un ÉCHEC MESURÉ du plan (le pourtour ne tient pas la haie), pas un « à
    # vérifier » (HT0538 : 1,39 m < 1,50 m). La « voie piétonne » exigée EN PLUS ne ferait que durcir le seuil.
    _places_g = [o.geom_world for o in scene.of("place")]
    _allees_g = [o.geom_world for o in scene.of("allee")]
    _parking = unary_union(_places_g + _allees_g) if (_places_g or _allees_g) else None
    _bati_g = unary_union(batis) if batis else None
    for cond in (getattr(cap, "stationnement_conditions", ()) or ()):
        _m = _HAIE_RE.search(cond)
        if (_m and _parking is not None and not _parking.is_empty
                and _bati_g is not None and not _bati_g.is_empty):
            req = float(_m.group(1).replace(",", "."))
            d = _parking.distance(_bati_g)
            ok = d >= req - 0.01
            out.append(ControleReg(
                "Stationnement — haie paysagère", f"≥ {_fr(req)} m entre l'aire de stationnement et le bâti",
                f"{_fr(round(d, 2))} m mesuré", REUSSI if ok else ECHOUE,
                # FIX-4 (LOT 3) — cite la règle EXACTE (haie + voie piétonne, Ud6 p. 92) telle qu'au règlement.
                cond,
                detail="haie paysagère + voie piétonne au pourtour des aires de stationnement — mesuré au plan"))
            continue
        out.append(ControleReg("Stationnement — condition à vérifier", cond, "non modélisé",
                               A_CONFIRMER, b.citation_complete if b.validee else None,
                               detail="condition du barème non vérifiable par ce moteur — à confirmer au projet"))

    # ETUDE-STATIONNEMENT-FIX-4 (LOT 1) — LARGEUR DE DESSERTE : au-delà d'un seuil de logements, le règlement
    # impose une voie/accès d'au moins N mètres (L'Étang-Salé UA3.1.2 : 5 m à partir de 7 logements). On MESURE
    # la largeur de l'accès DESSINÉ (plus petite dimension de son rectangle orienté) et on la compare. En
    # dessous, le plan ÉCHOUE (montré en rouge ; verdict « À compléter »), avec la règle citée.
    _dess = getattr(regles, "desserte", None)
    if (isinstance(_dess, dict) and _dess.get("largeur_min_m")
            and cap.logements >= int(_dess.get("seuil_logements") or 0)):
        _acc = [o.geom_local for o in scene.of("acces")]
        _all = [o.geom_local for o in scene.of("allee")]
        _pla = [o.geom_local for o in scene.of("place")]
        req = float(_dess["largeur_min_m"])
        au = unary_union([g if g.is_valid else g.buffer(0) for g in _acc]) if _acc else None
        if au is not None and not au.is_empty and au.area >= 0.1 and _all and _pla:
            # ETUDE-STATIONNEMENT-FIX-9 (relecture) — largeur du GOULET du chemin qui dessert EFFECTIVEMENT les
            # places comptées, par le MÊME noyau roulant que le comptage (`_largeur_min_desserte` ⟶ `_desserte_core`).
            # Une place comptée ⟹ goulet ≥ 2,40 m : les deux contrôles ne se contredisent plus.
            _voie_u = unary_union(scene.voie_local) if scene.voie_local else None
            larg = _largeur_min_desserte(_all, _pla, conv.allee_largeur_m, _acc, _voie_u,
                                         assiette=getattr(scene, "assiette_local", None))
            ok = larg >= req - 0.05
            _dcit = (f"PLU art. {_dess['article']}" if _dess.get("article") else "")
            _dcit += (f" · p. {_dess['page_pdf']}" if _dess.get("page_pdf") else "")
            _dcit = (_dcit + (f" — « {_dess['citation']} »" if _dess.get("citation") else "")) or None
            out.append(ControleReg(
                "Largeur de desserte", f"≥ {_fr(req)} m (opération ≥ {int(_dess['seuil_logements'])} logements)",
                f"{_fr(round(larg, 1))} m (goulet du chemin desservant les places)", REUSSI if ok else ECHOUE, _dcit,
                detail="largeur du goulet du chemin qui dessert les places comptées (même passage roulant que le comptage)"))
        else:
            out.append(ControleReg(
                "Largeur de desserte", f"≥ {_fr(req)} m (opération ≥ {int(_dess['seuil_logements'])} logements)",
                "aucun accès dessiné", A_CONFIRMER,
                (f"PLU art. {_dess.get('article')}" if _dess.get("article") else None),
                detail="desserte à vérifier — aucun accès n'a pu être dessiné"))

    # ETUDE-V6-2 (Lot 3) — en SOUS-SOL, l'emprise du parking enterré doit tenir sous l'EMPRISE
    # RÉGLEMENTAIRE (CES × contenance) ; c'est ce contrôle (pas le comptage) qui plafonne la capacité.
    if sous_sol:
        rc = regles.emprise_ces
        if rc.validee and rc.valeur is not None:
            emp_max = contenance * rc.valeur / 100.0
            ok = cap.emprise_sous_sol_m2 <= emp_max + 1e-6
            out.append(ControleReg(
                "Emprise du sous-sol", f"≤ {emp_max:.0f} m² (emprise réglementaire, CES {rc.valeur:.0f} %)",
                f"{cap.emprise_sous_sol_m2:.0f} m² ({cap.places_sous_sol} places × {cap.emprise_sous_sol_m2 / cap.places_sous_sol:.0f} m²)"
                if cap.places_sous_sol else f"{cap.emprise_sous_sol_m2:.0f} m²",
                REUSSI if ok else ECHOUE, rc.citation_complete,
                f"écart {emp_max - cap.emprise_sous_sol_m2:+.0f} m²"))
        else:
            out.append(ControleReg("Emprise du sous-sol", "CES non servi — emprise réglementaire non chiffrée",
                                   f"{cap.emprise_sous_sol_m2:.0f} m²", A_CONFIRMER,
                                   detail="emprise réglementaire du sous-sol à confirmer au règlement"))

    # Distance entre constructions (PLU-CALIBRAGE-10, ex-art. 8) : MESURÉE sur la géométrie et
    # confrontée à la règle de la zone. Convention des 4 états :
    #   · Non applicable = UN SEUL BÂTIMENT (contrainte absente du projet, cf. ci-dessous) OU silence
    #                      prouvé (le règlement dit qu'il ne réglemente pas) ;
    #   · Non effectué   = PLUSIEURS bâtiments + règle NON servie (zone/commune non calibrée, non lue,
    #                      forme hors schéma) ;
    #   · Réussi/Échoué  = PLUSIEURS bâtiments + règle servie chiffrable, confrontée à la mesure.
    nb_bati = _n_batiments(scene)
    dc = regles.distance_constructions
    dmes = _distance_min_batiments(scene)
    if nb_bati <= 1:
        # IMPLANTATION-4 (distance mono-bâtiment) — un SEUL bâtiment (annexes dessinées comprises dans
        # le compte des emprises) : aucune distance entre constructions à mesurer, la contrainte est
        # ABSENTE du projet → « Non applicable · un seul bâtiment », zone calibrée ou non. On INVERSE le
        # choix d'origine (qui classait une lacune de calibrage en « Non effectué » même en mono-bâtiment) :
        # c'est exactement la définition de « Non applicable » posée dès IMPLANTATION-1 (contrainte absente).
        out.append(ControleReg("Distance entre constructions", "sans objet (un seul bâtiment)",
                               "un seul bâtiment", NON_APPLICABLE,
                               detail="un seul bâtiment : aucune construction en vis-à-vis à mesurer"))
    elif dc.est_silence:
        cmin = conv.retrait_inter_barre_m
        mes = f"{dmes:.1f} m mesurés · convention {cmin:.0f} m (Estimé)"
        out.append(ControleReg("Distance entre constructions", "non réglementé (silence prouvé)", mes,
                               NON_APPLICABLE, dc.citation_complete,
                               detail=(f"le règlement ne fixe pas de distance entre constructions ; "
                                       f"distance de convention {cmin:.0f} m appliquée au tracé (Estimé)")))
    elif dc.est_chiffrable:
        # ETUDE-STATIONNEMENT-FIX-6 (point 3) — nombre de logements du bâtiment le plus peuplé (modules groupés
        # par `ref`) : porte le seuil « grand bâtiment » (Le Tampon Ua8.2, 3 m → 6 m si > 5 logements).
        from collections import Counter
        _par_bati = Counter(o.ref for o in scene.of("module") if o.ref)
        max_logts_bati = max(_par_bati.values(), default=getattr(cap, "logements", 0) or 0)
        requis, lib, mention = _distance_requise(dc, cap, conv, max_logts_bati)
        ok = dmes >= requis - 1e-6
        out.append(ControleReg("Distance entre constructions", lib, f"{dmes:.1f} m mesurés",
                               REUSSI if ok else ECHOUE, dc.citation_complete, detail=(mention or None)))
    else:
        out.append(ControleReg("Distance entre constructions", "règle non servie (zone non calibrée)",
                               f"{nb_bati} bâtiments · {dmes:.1f} m mesurés", NON_EFFECTUE,
                               detail="distance inter-bâtiments non calibrée sur cette zone — à vérifier"))

    # ETUDE-STATIONNEMENT-FIX-2 (reliquat #5) — stationnement VÉLO CHIFFRÉ quand le PLU le fixe (le moteur ne
    # le dessine pas → « à prévoir : X », jamais « non modélisé »). Sinon « Non vérifié » (pas « sans règle »).
    _par_pieces = [conv.modules[o.type_logement].pieces for o in scene.of("module")
                   if o.type_logement in conv.modules]
    _velo = (regles.stationnement.velo_requis(cap.logements, cap.sdp_m2, _par_pieces)
             if regles.stationnement.validee else None)
    if _velo is not None:
        _cit = (regles.stationnement.velo or {}).get("citation")
        out.append(ControleReg("Stationnement vélo", f"{_velo[1]} (servi au PLU)", f"à prévoir : {_velo[0]}",
                               A_CONFIRMER, _cit,
                               detail="exigence vélo chiffrée ; emplacement à confirmer (non dessiné par le moteur)"))
    else:
        out.append(ControleReg("Stationnement vélo", "norme non servie pour cette zone", "—", A_CONFIRMER,
                               detail="à vérifier au règlement (local vélos) — non modélisé"))
    out.append(ControleReg("Local déchets", "non modélisé", "—", NON_EFFECTUE))

    # PPR rouge (interdiction) : déduite de l'implantation, mais l'interdiction reste à CONFIRMER au
    # règlement (on la retire par prudence, ce n'est pas une preuve de constructibilité du reste).
    if terrain.contraintes.get("ppr_rouge"):
        out.append(ControleReg("PPR zone rouge (interdiction)", "retirée de la zone (prudence)",
                               f"{terrain.ppr_rouge_m2:.0f} m²", A_CONFIRMER,
                               detail="partie interdite retirée de l'implantation ; interdiction à confirmer au règlement PPR"))
    else:
        out.append(ControleReg("PPR zone rouge (interdiction)", "absente du terrain", "—", NON_APPLICABLE))

    # PPR bleue (prescription) : signalée, non interprétée → à confirmer (prescriptions à lire).
    # ETUDE-FIABLE-1 (LOT C5) — si le bâtiment, l'accès OU le sous-sol tombe en PPR bleu : mention
    # « Prescriptions PPR à vérifier » dans les points à instruire (la géométrie ne change pas).
    if terrain.contraintes.get("ppr_bleue"):
        parties = _ppr_bleue_touche_projet(scene, terrain)
        if parties:
            out.append(ControleReg("Prescriptions PPR à vérifier",
                                   "projet en zone bleue (prescription)",
                                   "touche : " + ", ".join(parties),
                                   A_CONFIRMER, detail=("le " + ", le ".join(parties) + " tombe(nt) en PPR zone bleue : "
                                                        "prescriptions à lire (surélévation, vide sanitaire, interdiction de "
                                                        "sous-sol…) — tant qu'elles ne le sont pas, l'étude n'est pas exploitable")))
        else:
            out.append(ControleReg("PPR zone bleue (prescription)", "signalée, non interprétée",
                                   "ne touche pas le projet",
                                   A_CONFIRMER, detail="signalée, prescriptions à lire"))
    else:
        out.append(ControleReg("PPR zone bleue (prescription)", "absente du terrain", "—", NON_APPLICABLE))

    # ER / EBC / SUP
    autres = [k for k in ("emplacement_reserve", "ebc", "sup", "servitude") if terrain.contraintes.get(k)]
    if autres:
        out.append(ControleReg("ER / EBC / SUP / servitudes", "présente(s)", ", ".join(autres),
                               A_CONFIRMER, detail="servitude(s) présente(s) non interprétée(s) par ce moteur — à confirmer"))
    else:
        out.append(ControleReg("ER / EBC / SUP / servitudes", "absentes du terrain", "—", NON_APPLICABLE))

    # ETUDE-STATIONNEMENT-FIX-4 (LOT 2) — INVENTAIRE ZONE HUMIDE couvrant l'assiette : signalé AVANT le verdict
    # (via `terrain.contraintes`), À CONFIRMER et BLOQUANT pour « Exploitable » (un inventaire sur toute
    # l'assiette peut remettre en cause l'implantation même — AD0887 : « La Grande Ferme », 100 % de l'assiette).
    _zhp = int(terrain.contraintes.get("zone_humide_pct", 0) or 0)
    if _zhp >= 50:
        out.append(ControleReg("Zone humide (inventaire)", f"inventaire couvrant {_zhp} % de l'assiette",
                               "à vérifier : l'implantation peut être remise en cause", A_CONFIRMER,
                               detail="inventaire de zone humide (couche cartographique) non interprété par ce "
                                      "moteur ; recouvre le bâti proposé — à confirmer avant tout projet"))

    # ETUDE-STATIONNEMENT-FIX-6 (point 1) — la zone ROUGE du PPR interdit le bâti ET le stationnement : le plan
    # garde donc son bâti et TOUTES ses places HORS zone rouge. Mais quand le seul accès possible à la voie
    # TRAVERSE la zone rouge (aucun point de voie atteignable hors zone), on conserve le plan et on SIGNALE la
    # voie d'accès concernée : son admission dépend du règlement du PPR (une voie peut y être tolérée, pas du
    # stationnement). Contrôle À CONFIRMER et BLOQUANT (jamais « Exploitable » tant que ce n'est pas tranché).
    _app = float(getattr(scene, "acces_ppr_rouge_m2", 0.0) or 0.0)
    if _app > 0.5:
        out.append(ControleReg(
            "Accès en zone rouge (PPR)", "bâti et places hors zone rouge ; voie d'accès traversante",
            f"aucun raccord hors zone rouge trouvé pour ce plan ; voie d'accès traversant la zone rouge "
            f"sur {_app:.0f} m²", A_CONFIRMER,
            detail="le bâti et toutes les places sont hors zone rouge ; aucun raccord à la voie publique hors "
                   "zone rouge n'a été trouvé pour ce plan, la voie d'accès traverse donc la zone rouge du plan "
                   "de prévention — son admission (voie d'accès, pas de stationnement) est À CONFIRMER au "
                   "règlement du PPR"))
    return out


def statut_etude(controles: list[ControleReg], geo_ok: bool, *, scene: Scene, terrain, regles) -> str:
    if not geo_ok:
        return "simulation impossible"
    if any(c.resultat == ECHOUE for c in controles):
        return "à compléter"
    # une règle de HAUTEUR non chiffrable (prospect L>H) ne laisse jamais l'étude exploitable
    if regles.hauteur_non_chiffrable:
        return "à compléter"
    # PLU-CALIBRAGE-10 : plusieurs bâtiments ne bloquent plus l'étude SI la distance inter-bâtiments
    # est servie (contrôle Réussi ou Non applicable=silence+convention). Elle ne reste bloquante que
    # si la règle n'est pas servie (contrôle Non effectué).
    if _n_batiments(scene) > 1:
        dc_ctrl = next((c for c in controles if c.nom == "Distance entre constructions"), None)
        if dc_ctrl is None or dc_ctrl.resultat == NON_EFFECTUE:
            return "à compléter"
    if _ppr_bleue_touche_projet(scene, terrain):   # ETUDE-FIABLE-1 (C5) — bâti/accès/sous-sol en PPR bleu
        return "à compléter"
    return "exploitable en pré-faisabilité"


# ETUDE-V6 (Lot B) — verdict GLOBAL de l'étude, dans les trois libellés du mandat. Distinct de
# `statut_etude` (conservé pour l'écran historique). Règle clé : un PPR, un accès ou un stationnement
# INDÉTERMINÉ (À confirmer) interdit « Exploitable » — trois contrôles verts ne suffisent pas.
VERDICT_EXPLOITABLE = "Exploitable sous hypothèses"
VERDICT_A_COMPLETER = "À compléter"
VERDICT_IMPOSSIBLE = "Impossible pour cause établie"

# contrôles dont l'état « À confirmer » est RÉDHIBITOIRE pour un verdict exploitable (mandat §4).
_A_CONFIRMER_BLOQUANTS = frozenset({
    "PPR zone rouge (interdiction)", "PPR zone bleue (prescription)",
    # ETUDE-FIABLE-1 (LOT C5) — PPR bleu touchant bâtiment/accès/sous-sol : bloque « Exploitable » (comme
    # l'ancien contrôle « PPR zone bleue » qui, lorsqu'il touchait le bâti, rendait l'étude non exploitable).
    "Prescriptions PPR à vérifier",
    "Stationnement", "Stationnement — condition à vérifier",
    "Admission de l'habitat",   # habitat sous condition d'un schéma d'affectation non lu (Saint-Louis UZ)
    "Zone humide (inventaire)",   # FIX-4 — inventaire couvrant l'assiette : peut remettre en cause l'implantation
    "Accès en zone rouge (PPR)",  # FIX-6 — voie d'accès traversant la zone rouge : admission à confirmer au PPR
    "Hauteur près des limites",
    "Prospect (hauteur relative)", "ER / EBC / SUP / servitudes",
    "Accès (voie)",   # RECETTE-4 — accès hypothétique (aucune voie classée) → verdict non « Exploitable »
})


def verdict_global(controles: list[ControleReg], *, statut_base: str, terrain,
                   cause_etablie: str | None = None) -> str:
    """Traduit l'état de l'étude dans les 3 verdicts du mandat. `cause_etablie` (non None) force
    « Impossible pour cause établie » (ex. assiette entièrement inconstructible, dépassement prouvé)."""
    if cause_etablie:
        return VERDICT_IMPOSSIBLE
    if statut_base == "simulation impossible":
        return VERDICT_IMPOSSIBLE
    if any(c.resultat == ECHOUE for c in controles):
        return VERDICT_A_COMPLETER
    if any(c.resultat == A_CONFIRMER and c.nom in _A_CONFIRMER_BLOQUANTS for c in controles):
        return VERDICT_A_COMPLETER
    if not getattr(terrain, "has_voie", True):      # accès à la voie non établi
        return VERDICT_A_COMPLETER
    if statut_base != "exploitable en pré-faisabilité":
        return VERDICT_A_COMPLETER
    return VERDICT_EXPLOITABLE


def afficher_stationnement_a_confirmer(controles, regles) -> None:
    """CAPACITE-1 (D1) — AFFICHAGE : un barème « par logement » (taux unique, sans distinction de
    destination) ne garantit PAS la règle COLLECTIVE (au-delà de 5 logements, elle diffère — ex. art.
    Ud12.2). Le contrôle de stationnement s'affiche « À confirmer », jamais « Réussi » avec une règle
    qui ne s'applique pas (faute AD0887 : 8 places « Réussi » au taux individuel pour un collectif).
    N'altère PAS la capacité : le moteur a déjà décidé la faisabilité (verdict géométrique REUSSI/ÉCHOUÉ)
    AVANT ce point ; on ne mute que la LIGNE affichée du scénario packagé (compte + table la lisent)."""
    b = getattr(regles, "stationnement", None)
    if b is None or not getattr(b, "validee", False) or getattr(b, "mode", None) != "par_logement":
        return
    for c in (controles or []):
        if c.nom == "Stationnement" and c.resultat in (REUSSI, ECHOUE):
            c.resultat = A_CONFIRMER
            c.regle = "barème « par logement » — règle collective non vérifiée"
            c.detail = ("barème exprimé par logement, sans distinguer la destination ; la règle de "
                        "stationnement collectif (seuil au-delà de 5 logements) peut imposer davantage "
                        "— à vérifier au règlement")
