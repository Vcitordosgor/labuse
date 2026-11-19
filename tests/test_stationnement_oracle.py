"""ETUDE-STATIONNEMENT-FIX-15 — VÉRIFICATEUR INDÉPENDANT (oracle) de la desserte roulante.

Cet oracle NE PARTAGE AUCUN CODE avec le contrôle `_desserte_core` : il décide l'atteignabilité par une
GRILLE FINE (1 cm, sous les 2 cm demandés — pour rasteriser sans biais les coins étroits) + carte de distance
(le centre d'un disque de la largeur de passage « tient » là où la distance au bord de l'aire roulante ≥
demi-passage) + un PARCOURS DE PROCHE EN PROCHE (étiquetage de composantes connexes, 8-voisins) amorcé depuis
l'EXTÉRIEUR de la voie, à travers le recouvrement.

On compare l'oracle et le contrôle sur ≥ 300 plans tirés au hasard à graine fixe (assiettes concaves avec
encoches/poches, étranglements à l'entrée/au milieu/près des places, plusieurs réseaux, rotations) PLUS tous
les contre-exemples du relecteur. Désaccord sur le nombre de places atteignables, ou > 5 cm sur le goulet → échec.

Test LENT : marqué `local` → hors hook (le hook joue `-m "not db and not local and not reel and not network"`).
Jouer explicitement : `pytest -m local tests/test_stationnement_oracle.py` ou directement le fichier.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import ndimage
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import linemerge, unary_union
from shapely.vectorized import contains

import labuse.implantation.controles as C

PASSAGE = C._PASSAGE_MIN_M
CELL = 0.01   # maille fine (≤ 2 cm demandés) : 1 cm pour rasteriser sans biais les étranglements/coins étroits


# ───────────────────────── ORACLE (aucun code commun avec le contrôle) ─────────────────────────
_MARGE = 4.0     # profondeur de la ROUTE extérieure autour de la parcelle (≥ demi-passage cherché)
_WALL = 0.03     # épaisseur du MUR (contour de l'assiette) rasterisé — bloque le disque hors de l'ouverture
_PREC = 0.001    # FIX-18 : résolution géométrique (le millimètre), identique au contrôle


def _ouverture_sur_bord(ouverture, assiette):
    """Règle 1 (FIX-18), par les moyens de l'oracle : l'ouverture (contact accès–voie) est-elle sur le BORD de
    l'assiette ? De part et d'autre de chaque tronçon, une lanière LOCALE (2 cm) ; un tronçon est « sur le bord »
    si un côté y est quasi vide d'assiette. Si TOUS les tronçons ont les deux côtés couverts (voie INTÉRIEURE à
    l'assiette), renvoie False → raccord non établi."""
    segs = list(ouverture.geoms) if ouverture.geom_type == "MultiLineString" else [ouverture]
    for s in segs:
        if s.geom_type != "LineString":
            continue
        cs = list(s.coords)
        for i in range(len(cs) - 1):
            (x0, y0), (x1, y1) = cs[i], cs[i + 1]
            ex, ey = x1 - x0, y1 - y0
            ln = math.hypot(ex, ey)
            if ln < 1e-9:
                continue
            nx, ny = -ey / ln, ex / ln
            lp = Polygon([(x0, y0), (x1, y1), (x1 + nx * 0.02, y1 + ny * 0.02), (x0 + nx * 0.02, y0 + ny * 0.02)])
            lm = Polygon([(x0, y0), (x1, y1), (x1 - nx * 0.02, y1 - ny * 0.02), (x0 - nx * 0.02, y0 - ny * 0.02)])
            ap, am = lp.intersection(assiette).area, lm.intersection(assiette).area
            if not (max(ap, am) > _PREC * ln and min(ap, am) > 0.30 * max(ap, am)):
                return True              # un côté quasi vide → tronçon sur le bord → raccord possible
    return False                         # tous les tronçons intérieurs → voie dans l'assiette → pas de raccord


def _grille(allees, places, acces, voie, assiette):
    """Pose la réalité du relecteur SANS reprendre la bande : la circulation = AIRE ROULANTE (intérieur, intacte)
    ∪ ROUTE (la rue, AU-DELÀ DE LA VOIE — PAS tout le pourtour, sinon le disque contournerait la parcelle),
    SÉPARÉES par le CONTOUR DE L'ASSIETTE qui est un MUR, percé uniquement au droit du recouvrement (contact
    accès–voie). Grille : la route = `voie.buffer(marge) − assiette − mur` → elle ne touche l'aire roulante QU'À
    l'ouverture ; l'aire roulante n'est jamais coupée. Départ = la route. None si aucun contact accès–voie."""
    libre = unary_union([g for g in (list(allees) + list(acces))])
    if libre.is_empty:
        return None
    acces_poly = unary_union([g for g in (acces or [])])
    voie_l = voie if voie.geom_type in ("LineString", "MultiLineString") else voie.boundary
    ouverture = voie_l.intersection(acces_poly)          # OUVERTURE = là où l'accès perce le mur du contour
    if ouverture.is_empty:
        return None
    if not _ouverture_sur_bord(ouverture, assiette):     # règle 1 : voie à l'intérieur → pas de raccord
        return None
    mur = assiette.boundary.buffer(_WALL).difference(ouverture.buffer(_WALL * 3.0, cap_style=2))   # ouverture à BOUTS PLATS
    route = voie_l.buffer(_MARGE).difference(assiette).difference(mur).buffer(0)      # la rue, au-delà de la voie
    if route.is_empty:
        return None
    espace = unary_union([libre, route])
    minx, miny, maxx, maxy = espace.bounds
    minx -= CELL; miny -= CELL; maxx += CELL; maxy += CELL
    nxc = int((maxx - minx) / CELL) + 1
    nyc = int((maxy - miny) / CELL) + 1
    xs = minx + (np.arange(nxc) + 0.5) * CELL
    ys = miny + (np.arange(nyc) + 0.5) * CELL
    X, Y = np.meshgrid(xs, ys)
    inside = contains(espace, X, Y)
    dist = ndimage.distance_transform_edt(inside) * CELL
    road_mask = contains(route, X, Y)                    # départ = la route (au-delà de la voie), hors mur
    return dict(dist=dist, road=road_mask, minx=minx, miny=miny, nxc=nxc, nyc=nyc, espace=espace)


def oracle_nb(grille, places, passage):
    """Nombre de places qu'un disque de rayon `passage/2`, parti de la route par un parcours de proche en
    proche à travers les cellules libres, peut atteindre par le NEZ (l'un des deux petits côtés)."""
    if grille is None:
        return 0
    r = passage / 2.0
    dist, road = grille["dist"], grille["road"]
    # CONNECTIVITÉ (franchissement des étranglements) : SANS cheveu → goulet exact. Le disque tient là où la
    # distance au bord ≥ demi-passage.
    free = dist >= r
    seed = free & road
    if not seed.any():
        return 0
    lbl, _ = ndimage.label(free, structure=np.ones((3, 3)))
    reached_labels = set(np.unique(lbl[seed])) - {0}
    if not reached_labels:
        return 0
    reached = np.isin(lbl, list(reached_labels))
    # Le point d'approche est, par nature, À la demi-largeur du bord de l'allée (voiture nez contre la place) —
    # donc SUR le bord de la zone atteinte. Le contrôle l'inclut (ensemble fermé). Sur la maille on dilate la
    # zone atteinte d'UNE cellule MAIS en la gardant dans les cellules où le disque TIENT PRESQUE (dist ≥ demi-
    # passage − 1 maille) : on inclut ainsi l'approche au ras du bord SANS pouvoir franchir un étranglement
    # (ses cellules, trop étroites, sont exclues) → le goulet n'est pas gonflé par la dilatation.
    reached = ndimage.binary_dilation(reached, iterations=1) & (dist >= r - CELL)
    minx, miny, nxc, nyc = grille["minx"], grille["miny"], grille["nxc"], grille["nyc"]
    espace = grille["espace"]

    def cell_reached(px, py):
        j = int((px - minx) / CELL)
        i = int((py - miny) / CELL)
        if not (0 <= i < nyc and 0 <= j < nxc and reached[i, j]):
            return False
        # la cellule est atteinte (connexité) ; on confirme le CONTACT EXACT du disque au point d'approche
        # (le disque de rayon r tient, bord inclus) — supprime les faux positifs sub-millimétriques de la maille
        # au ras du bord érodé (le contrôle, exact, tranche au même endroit).
        p = Point(px, py)
        return espace.contains(p) and espace.boundary.distance(p) >= r - _PREC   # mm près (règle 2)

    nb = 0
    for pl in places:
        c = pl.centroid
        coords = list(pl.exterior.coords)[:-1]
        edges = []
        for k in range(len(coords)):
            a, b = coords[k], coords[(k + 1) % len(coords)]
            ln = math.hypot(b[0] - a[0], b[1] - a[1])
            edges.append((ln, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)))
        lmin = min(e[0] for e in edges)
        petits = [e for e in edges if e[0] <= lmin * 1.3]
        ok = False
        for _ln, mid in petits:
            nx, ny = mid[0] - c.x, mid[1] - c.y
            ll = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ll, ny / ll
            if cell_reached(mid[0] + r * nx, mid[1] + r * ny):
                ok = True
                break
        if ok:
            nb += 1
    return nb


def oracle_goulet(grille, places, hi=12.0):
    """Plus grand passage pour lequel l'oracle atteint ≥ 1 place (recherche binaire, résolution ~1 cm). Le
    plancher bas (3 cm) est au-dessus de la maille (2 cm) mais permet de retrouver un goulet d'étranglement
    de quelques centimètres — pour comparer au contrôle même quand aucune place n'est atteignable à 2,40 m."""
    if grille is None or oracle_nb(grille, places, 0.03) < 1:
        return 0.0
    lo = 0.03
    while hi - lo > 0.01:
        mid = (lo + hi) / 2.0
        if oracle_nb(grille, places, mid) >= 1:
            lo = mid
        else:
            hi = mid
    return lo


# ───────────────────────── contre-exemples du relecteur ─────────────────────────
def _ce_fix15(d):
    assiette = box(0, 0, 11, 10).difference(box(2, d, 12, 4))
    acces = unary_union([box(0, -.04, 6, d), box(0, d, 2, 4)])
    allee = box(0, 4, 5, 9)
    place = box(5, 5, 10, 7.5)
    voie = LineString([(0, 0), (6, 0)])
    return [allee], [place], [acces], voie, assiette


def _ce_fix14(d):
    voie = LineString([(-5, 16), (35, 16)])
    bouche = box(22, 15.8, 28, 16.1)
    neck = box(24, 12.9, 26, 15.9)
    acc = unary_union([bouche, neck])
    wide = box(20, 2, 30, 13)
    lip = box(4, 15.9, 14, 16)
    conn = box(4, 2, 30, 5)
    allee = unary_union([wide, lip, conn])
    place = box(24, 2, 26.5, 7)
    assiette = box(-5, -4, 35, 16).difference(box(4, 5, 14, 16 - d))
    return [allee], [place], [acc], voie, assiette


def _ce_11x9():
    ass = box(0, 0, 11, 9)
    voie = LineString([(-2, 9), (13, 9)])
    acc = unary_union([box(2.5, 8.9, 8.5, 9.1), box(4, 8.8, 6, 8.9)])
    allee = box(0, 0, 11, 8.8)
    place = box(0, 0, 2.5, 5)
    return [allee], [place], [acc], voie, ass


def _ce_C16():
    """Assiette en C du relecteur : la bande extérieure traverse l'encoche et rejoint l'allée par un AUTRE bord
    (faux raccord, goulet 6 m). Attendu : 0 place, goulet ≈ 2 m (le vrai passage est la colonne gauche de 2 m)."""
    assiette = box(0, -20, 20, 20).difference(box(5, -5, 21, 5))
    acces = unary_union([box(6, 4.96, 12, 5.1), box(8, 5.1, 10, 10),
                         box(1, 6, 10, 8), box(1, -8, 3, 8), box(1, -8, 8, -6)])
    allee = box(5, -10, 15, -5)
    place = box(7, -15, 9.5, -10)
    voie = LineString([(6, 5), (12, 5)])
    return [allee], [place], [acces], voie, assiette


def _ce_voie_interieure():
    """Règle 1 (FIX-18) : la voie (et son contact accès) est À L'INTÉRIEUR de l'assiette (pas sur le bord) →
    plan invalide, raccord NON établi, 0 place. Le générateur ne produit plus ce cas ; il est testé ici."""
    assiette = box(0, 0, 20, 20)
    voie = LineString([(5, 10), (11, 10)])            # voie dans l'assiette (pas sur le bord)
    acces = box(5, 9.9, 11, 12)                       # accès touchant la voie (6 m) mais à l'intérieur
    allee = box(5, 12, 15, 15)
    place = box(6, 15, 8.5, 20)
    return [allee], [place], [acces], voie, assiette


def contre_exemples():
    cas = []
    al, pl, ac, v, a = _ce_voie_interieure()
    for rot in (0, 37, 90, 180, 270):
        cas.append((f"voie_interieure_r{rot}", _rot(al, pl, ac, v, a, rot, origin=(10, 10))))
    for rot in (0, 90, 180, 270):
        for d in (0.04, 0.051):
            for nom, fn in (("fix15", _ce_fix15), ("fix14", _ce_fix14)):
                al, pl, ac, v, a = fn(d)
                cas.append((f"{nom}_d{d}_r{rot}", _rot(al, pl, ac, v, a, rot)))
    al, pl, ac, v, a = _ce_11x9()
    for rot in (0, 45, 90, 180):
        cas.append((f"11x9_r{rot}", _rot(al, pl, ac, v, a, rot)))
    al, pl, ac, v, a = _ce_C16()
    for rot in (0, 17, 30, 45, 73, 90, 128, 180, 210, 270, 315, 340):   # C/U encoche, ROTATIONS QUELCONQUES
        cas.append((f"C16_r{rot}", _rot(al, pl, ac, v, a, rot, origin=(10, 0))))
    return cas


def _rot(allees, places, acces, voie, assiette, deg, origin=(5, 5)):
    if not deg:
        return allees, places, acces, voie, assiette
    f = lambda g: rotate(g, deg, origin=origin)
    return [f(g) for g in allees], [f(g) for g in places], [f(g) for g in acces], f(voie), f(assiette)


# ───────────────────────── générateur aléatoire (graine fixe) ─────────────────────────
def _gen(rng):
    """Un plan varié : assiette RECTANGLE ou CONCAVE (C, U, L, poche), accès en corridor profond de largeur
    uniforme (franc ≥ 2,60 m OU étranglé ≤ 2,34 m — marge claire de 2,40 m), allée principale, option allée qui
    LONGE l'encoche (reliée au réseau réel, PAS atteignable par l'encoche = le mur), places en stalles
    affleurantes, rotation QUELCONQUE. Renvoie (famille, allees, places, acces, voie, assiette) ou None."""
    W = rng.uniform(12, 16)
    H = rng.uniform(11, 14)
    ass = box(0, 0, W, H)
    ya = 5.0
    main = box(0.5, ya, W - 0.5, ya + 3.0)                       # allée principale (desservie par l'accès)
    family = "rectangle"
    longe = None
    roll = rng.random()
    if roll < 0.24:                                              # C : encoche ouverte à droite + allée qui la longe
        family = "C"
        ey0 = rng.uniform(ya + 2.6, H - 3.0)
        eh = rng.uniform(2.2, max(2.3, H - ey0 - 0.6))
        ex0 = rng.uniform(5.0, W - 2.0)
        ass = ass.difference(box(ex0, ey0, W + 1.0, ey0 + eh))
        longe = box(0.5, ey0 - 2.4, ex0, ey0)                    # longe l'encoche, REJOINT `main` par la gauche
    elif roll < 0.42:                                            # U : deux encoches + allée qui longe entre elles
        family = "U"
        ey0 = rng.uniform(ya + 3.8, H - 2.2)
        ex0 = rng.uniform(5.0, W - 2.0)
        ass = ass.difference(box(ex0, ey0, W + 1.0, ey0 + 1.4)).difference(box(ex0, ey0 - 3.2, W + 1.0, ey0 - 1.8))
        longe = box(0.5, ey0 - 1.8, ex0, ey0)
    elif roll < 0.58:                                            # L : encoche d'angle (haut-gauche ou haut-droit)
        family = "L"
        if rng.random() < 0.5:
            ass = ass.difference(box(-1.0, ya + 3.6, rng.uniform(3.0, W / 2.0), H + 1.0))
        else:
            ass = ass.difference(box(rng.uniform(W / 2.0, W - 3.0), ya + 3.6, W + 1.0, H + 1.0))
    elif roll < 0.74:                                            # poche : encoche depuis un bord, concave
        family = "poche"
        px0 = rng.uniform(1.0, W - 4.0)
        ass = ass.difference(box(px0, ya + 3.6, px0 + rng.uniform(1.5, 3.5), H + 1.0))
    if ass.is_empty or ass.geom_type != "Polygon":
        return None
    voie = LineString([(0, 0), (W, 0)])
    # accès : corridor d'entrée de LARGEUR UNIFORME (bouche = corridor), profond, montant droit à l'allée. Largeur
    # `ebw` franche (≥ 2,60 m, desservi) ou étranglée (≤ 2,34 m, non desservi) — marge CLAIRE autour de 2,40 m
    # (maille 1 cm + rotation quelconque ≈ ±1,5 cm d'erreur de rasterisation).
    ebw = rng.choice([rng.uniform(2.6, 5.0), rng.uniform(1.6, 2.34)])
    bx0 = rng.uniform(0.8, max(0.9, W - ebw - 0.8))              # l'accès n'est pas collé au bord latéral (sinon,
    colx = bx0 + ebw / 2.0                                        #   après rotation, le recouvrement rase un angle)
    acc = box(colx - ebw / 2.0, -0.04, colx + ebw / 2.0, ya + 0.3)
    allees = [main] + ([longe] if longe is not None else [])
    # places 2,5 × 5, NON chevauchantes, en STALLE PERPENDICULAIRE : le NEZ affleure le bord de l'allée, la stalle
    # s'étend DEHORS (pas de chevauchement partiel ambigu) → l'approche tombe franchement dans l'allée.
    places = []
    cibles = [main] + ([longe] if longe is not None else [])
    for _ in range(rng.randint(1, 4)):
        for _essai in range(16):
            al = rng.choice(cibles)
            ax0, ay0, ax1, ay1 = al.bounds
            if ax1 - ax0 < 3.0:
                continue
            px = rng.uniform(ax0 + 0.2, ax1 - 2.7)
            cand = (box(px, ay1, px + 2.5, ay1 + 5.0) if rng.random() < 0.5
                    else box(px, ay0 - 5.0, px + 2.5, ay0))
            if cand.intersection(acc).area > 0.1 or cand.intersection(unary_union(allees)).area > 6.0:
                continue
            if any(cand.buffer(0.4).intersects(q) for q in places):
                continue
            places.append(cand)
            break
    if not places:
        return None
    deg = rng.uniform(0, 360)          # ROTATIONS QUELCONQUES
    al, pl, ac, v, a = _rot(allees, places, [acc], voie, ass, deg, origin=(W / 2, H / 2))
    # FIX-18 : le générateur NE PRODUIT PAS de voie à l'intérieur de l'assiette (plan invalide) — ce cas est
    # couvert à part par `contre_exemples` (règle 1). On jette le plan si le recouvrement n'est pas sur le bord.
    rec = v.intersection(unary_union(ac))
    if not rec.is_empty and rec.length > 0:
        mp = rec.interpolate(0.5, normalized=True)
        if a.contains(mp) and a.boundary.distance(mp) > 0.05:
            return None
    return (family, al, pl, ac, v, a)


# ───────────────────────── comparaison oracle ↔ contrôle ─────────────────────────
def _compare(nom, allees, places, acces, voie, assiette):
    """Renvoie None si accord, sinon une chaîne décrivant le désaccord."""
    ctrl_nb = C._desserte_core(allees, places, 2.5, acces, voie, PASSAGE, assiette)[1]
    gril = _grille(allees, places, acces, voie, assiette)
    ora_nb = oracle_nb(gril, places, PASSAGE)
    if ctrl_nb != ora_nb:
        return f"[{nom}] nb : contrôle={ctrl_nb} oracle={ora_nb}"
    ctrl_g = C._largeur_min_desserte(allees, places, 2.5, acces, voie, assiette)
    ora_g = oracle_goulet(gril, places)
    if abs(ctrl_g - ora_g) > 0.05:
        return f"[{nom}] goulet : contrôle={ctrl_g:.3f} oracle={ora_g:.3f} (écart {abs(ctrl_g-ora_g):.3f} > 5 cm)"
    return None


@pytest.mark.local
def test_oracle_contre_exemples_du_relecteur():
    desacc = [m for nom, (al, pl, ac, v, a) in contre_exemples()
              if (m := _compare(nom, al, pl, ac, v, a))]
    assert not desacc, "Désaccords oracle↔contrôle sur les contre-exemples :\n" + "\n".join(desacc)


@pytest.mark.local
def test_oracle_vs_controle_300_plans():
    """≥ 300 plans tirés à graine fixe, PAR FAMILLE DE FORMES (rectangle, C, U, L, poche), rotations quelconques,
    largeurs d'entrée proches de 2,40 m. Zéro désaccord dans les deux sens (ni place comptée à tort, ni place
    valable refusée). Un désaccord → on donne la géométrie du plan fautif et on échoue (sans réduire le périmètre)."""
    import random
    rng = random.Random(20261118)
    n, desacc = 0, []
    par_famille = {}
    while n < 340:
        plan = _gen(rng)
        if plan is None:
            continue
        family, allees, places, acces, voie, assiette = plan
        if not places:
            continue
        n += 1
        par_famille[family] = par_famille.get(family, 0) + 1
        try:
            m = _compare(f"plan#{n}[{family}]", allees, places, acces, voie, assiette)
        except Exception as e:  # noqa: BLE001
            m = f"[plan#{n}[{family}]] exception : {type(e).__name__} {e}"
        if m:
            wkt = (f"\n  assiette={assiette.wkt}\n  acces={unary_union(acces).wkt}"
                   f"\n  allees={unary_union(allees).wkt}\n  places={unary_union(places).wkt}\n  voie={voie.wkt}")
            desacc.append(m + wkt)
    print("plans par famille :", par_famille)
    assert not desacc, f"{len(desacc)}/{n} désaccords oracle↔contrôle (par famille {par_famille}) :\n" + "\n".join(desacc[:4])
