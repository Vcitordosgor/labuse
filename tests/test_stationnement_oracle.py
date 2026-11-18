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
def _grille(allees, places, acces, voie, assiette, D=12.0):
    """Carte de distance au bord de (aire roulante + APRONS d'entrée), et masque des cellules « apron » (hors
    voie). L'entrée se fait UNIQUEMENT par le RECOUVREMENT (voie ∩ aire roulante) : à chaque tronçon recouvert
    on accole, DU CÔTÉ EXTÉRIEUR (déterminé par un micro-décalage perpendiculaire contre l'assiette — local au
    bord, indépendant du contrôle), un rectangle qui tient lieu de route d'entrée. Pas de route qui contourne
    la parcelle. Renvoie None si aucun recouvrement."""
    libre = unary_union([g for g in (list(allees) + list(acces))])
    if libre.is_empty:
        return None
    voie_l = voie if voie.geom_type in ("LineString", "MultiLineString") else voie.boundary
    cvt = voie_l.intersection(libre)
    merged = linemerge(cvt) if cvt.geom_type == "MultiLineString" else cvt
    segs = ([merged] if merged.geom_type == "LineString"
            else [s for s in getattr(merged, "geoms", []) if s.geom_type == "LineString"])
    aprons = []
    for s in segs:
        cs = list(s.coords)
        for i in range(len(cs) - 1):
            (x0, y0), (x1, y1) = cs[i], cs[i + 1]
            ex, ey = x1 - x0, y1 - y0
            ln = math.hypot(ex, ey)
            if ln < 1e-9:
                continue
            nx, ny = -ey / ln, ex / ln            # normale ; on l'oriente vers l'EXTÉRIEUR de l'assiette
            mxp, myp = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            if assiette.contains(Point(mxp + nx * 1e-3, myp + ny * 1e-3)):
                nx, ny = -nx, -ny
            aprons.append(Polygon([(x0, y0), (x1, y1), (x1 + nx * D, y1 + ny * D), (x0 + nx * D, y0 + ny * D)]))
    if not aprons:
        return None
    apron = unary_union(aprons).difference(assiette).buffer(0)   # l'apron est DEHORS (jamais dans le projet)
    if apron.is_empty:
        return None
    world = unary_union([libre, apron])
    minx, miny, maxx, maxy = world.bounds
    minx -= CELL; miny -= CELL; maxx += CELL; maxy += CELL
    nxc = int((maxx - minx) / CELL) + 1
    nyc = int((maxy - miny) / CELL) + 1
    xs = minx + (np.arange(nxc) + 0.5) * CELL
    ys = miny + (np.arange(nyc) + 0.5) * CELL
    X, Y = np.meshgrid(xs, ys)
    inside = contains(world, X, Y)
    dist = ndimage.distance_transform_edt(inside) * CELL     # distance (m) au bord de l'aire roulante
    road_mask = contains(apron, X, Y)
    return dict(dist=dist, road=road_mask, minx=minx, miny=miny, nxc=nxc, nyc=nyc)


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

    def cell_reached(px, py):
        j = int((px - minx) / CELL)
        i = int((py - miny) / CELL)
        return 0 <= i < nyc and 0 <= j < nxc and reached[i, j]

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


def contre_exemples():
    cas = []
    for rot in (0, 90, 180, 270):
        for d in (0.04, 0.051):
            for nom, fn in (("fix15", _ce_fix15), ("fix14", _ce_fix14)):
                al, pl, ac, v, a = fn(d)
                cas.append((f"{nom}_d{d}_r{rot}", _rot(al, pl, ac, v, a, rot)))
    al, pl, ac, v, a = _ce_11x9()
    for rot in (0, 45, 90, 180):
        cas.append((f"11x9_r{rot}", _rot(al, pl, ac, v, a, rot)))
    return cas


def _rot(allees, places, acces, voie, assiette, deg, origin=(5, 5)):
    if not deg:
        return allees, places, acces, voie, assiette
    f = lambda g: rotate(g, deg, origin=origin)
    return [f(g) for g in allees], [f(g) for g in places], [f(g) for g in acces], f(voie), f(assiette)


# ───────────────────────── générateur aléatoire (graine fixe) ─────────────────────────
def _gen(rng):
    """Un plan varié : assiette concave (encoches/poches), accès mordant la voie, étranglement de position et
    largeur aléatoires, un ou plusieurs réseaux d'allées, places, rotation."""
    W = rng.uniform(11, 15)
    H = rng.uniform(9, 13)
    ass = box(0, 0, W, H)
    # encoches concaves (dont des poches près de la voie, à d petit)
    for _ in range(rng.randint(0, 3)):
        if rng.random() < 0.4:
            d = rng.choice([0.04, 0.051, rng.uniform(0.02, 0.2)])
            nx0 = rng.uniform(1.5, W - 3)
            ass = ass.difference(box(nx0, d, nx0 + rng.uniform(1.5, 4.0), rng.uniform(2.5, 5.0)))
        else:
            nx0 = rng.uniform(1, W - 3); ny0 = rng.uniform(2, H - 4)
            ass = ass.difference(box(nx0, ny0, nx0 + rng.uniform(1.5, 4), ny0 + rng.uniform(1.5, 4)))
    if ass.is_empty or ass.geom_type != "Polygon":
        return None
    voie = LineString([(0, 0), (W, 0)])          # la voie borde toute la façade (recouvrement = largeur de bouche)
    # accès : bouche mordant la voie + colonne avec un étranglement (entrée / milieu / haut). Largeur
    # d'étranglement tirée AVEC MARGE CLAIRE du passage (jamais dans [2,20 ; 2,60]) → la réponse est ROBUSTE
    # (la maille de 2 cm ne peut pas faire basculer un cas au ras du seuil ; ce n'est pas le bug qu'on traque).
    bw = rng.uniform(2.6, 5.0)
    bx0 = rng.uniform(0, max(0.1, W - bw))
    bouche = box(bx0, -0.04, bx0 + bw, 0.1)
    nkw = rng.choice([rng.uniform(1.4, 2.2), rng.uniform(2.6, 3.4)])
    colx = bx0 + bw / 2.0
    yb = {"entree": 0.1, "milieu": 2.0, "haut": 3.6}[rng.choice(["entree", "milieu", "haut"])]
    col_bas = box(colx - bw / 2.0, 0.1, colx + bw / 2.0, yb)
    neck = box(colx - nkw / 2.0, yb, colx + nkw / 2.0, yb + 1.0)
    col_haut = box(colx - 2.0, yb + 1.0, colx + 2.0, 5.2)
    acc = unary_union([bouche, col_bas, neck, col_haut])
    # un ou deux réseaux d'allées (le second derrière un étranglement interne à marge claire → places parfois
    # inatteignables même avec un accès large)
    ya = 5.0
    main = box(0.5, ya, W - 0.5, min(H - 1.0, ya + 3.0))
    allees = [main]
    arriere = None
    if rng.random() < 0.5 and H > 10:
        iw = rng.choice([rng.uniform(1.4, 2.2), rng.uniform(2.6, 3.4)])   # étranglement interne, marge claire
        ix = rng.uniform(1.5, W - 2.5)
        allees.append(box(ix - iw / 2, ya + 3.0, ix + iw / 2, ya + 4.0))           # goulet interne
        arriere = box(0.5, ya + 4.0, W - 0.5, min(H - 0.5, ya + 6.5))
        allees.append(arriere)
    # places 2,5 × 5, NON chevauchantes, posées en STALLE PERPENDICULAIRE à l'allée : le NEZ (petit côté 2,5 m)
    # AFFLEURE le bord de l'allée, la stalle s'étend DEHORS (aucun chevauchement partiel ambigu). L'allée
    # dépasse le nez → le point d'approche (demi-passage devant le nez) tombe franchement dans l'allée.
    places = []
    cibles = [main] + ([arriere] if arriere is not None else [])
    for _ in range(rng.randint(1, 4)):
        for _essai in range(14):
            al = rng.choice(cibles)
            ax0, ay0, ax1, ay1 = al.bounds
            if ax1 - ax0 < 3.0:
                continue
            px = rng.uniform(ax0 + 0.2, ax1 - 2.7)
            cand = (box(px, ay1, px + 2.5, ay1 + 5.0) if rng.random() < 0.5
                    else box(px, ay0 - 5.0, px + 2.5, ay0))          # nez AFFLEURANT le bord de l'allée
            if cand.intersection(acc).area > 0.1:
                continue
            if any(cand.buffer(0.4).intersects(q) for q in places):
                continue
            places.append(cand)
            break
    if not places:
        return None
    # rotations CARDINALES pour les plans aléatoires : les boîtes restent alignées sur les axes → la maille
    # rasterise les étranglements fins SANS erreur de diagonale (un oracle en grille surestime la largeur d'un
    # étranglement fin tourné de 30°). L'invariance aux angles QUELCONQUES (0/45/90/180/270) est vérifiée à part
    # sur les contre-exemples du relecteur, où le contrôle (analytiquement invariant par rotation) est exact.
    deg = rng.choice([0, 90, 180, 270])
    return _rot(allees, places, [acc], voie, ass, deg, origin=(W / 2, H / 2))


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
    import random
    rng = random.Random(20261118)
    n, desacc = 0, []
    while n < 320:
        plan = _gen(rng)
        if plan is None:
            continue
        allees, places, acces, voie, assiette = plan
        if not places:
            continue
        n += 1
        try:
            m = _compare(f"plan#{n}", allees, places, acces, voie, assiette)
        except Exception as e:  # noqa: BLE001
            m = f"[plan#{n}] exception : {type(e).__name__} {e}"
        if m:
            desacc.append(m)
    assert not desacc, f"{len(desacc)}/{n} désaccords oracle↔contrôle :\n" + "\n".join(desacc[:40])
