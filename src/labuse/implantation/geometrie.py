"""Géométrie de l'implantation (EPSG:2975).

Tout est construit dans un REPÈRE LOCAL aligné sur le grand axe de l'assiette (rotation de son
rectangle orienté minimal), puis reprojeté en coordonnées monde 2975. Objets dessinés :
bâtiments (emprise + niveaux), modules de logement, noyaux, coursives, places, allées, accès,
espaces libres. Tous les comptes sont TIRÉS de ces objets (jamais l'inverse).

Déterministe : aucune aléa, parcours de grille ordonné, départage stable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from shapely import minimum_rotated_rectangle
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .conventions import Conventions


# ---------------------------------------------------------------- objet dessiné
@dataclass
class Objet:
    kind: str                      # batiment_emprise|module|noyau|coursive|place|allee|acces|espace_libre
    geom_local: Polygon
    niveau: Optional[int] = None
    type_logement: Optional[str] = None
    ref: Optional[str] = None
    geom_world: Optional[Polygon] = None


# ---------------------------------------------------------------- repère local
@dataclass
class Frame:
    """Transforme monde(2975) <-> local (grand axe de l'assiette sur +x, origine en bas-gauche)."""
    ox: float
    oy: float
    angle_deg: float               # angle du grand axe dans le repère monde

    @classmethod
    def depuis(cls, assiette: Polygon) -> "Frame":
        mrr = minimum_rotated_rectangle(assiette)
        xs, ys = mrr.exterior.coords.xy
        # arête la plus longue = grand axe
        best = (0.0, 0, 0.0)
        for i in range(4):
            dx, dy = xs[i + 1] - xs[i], ys[i + 1] - ys[i]
            L = math.hypot(dx, dy)
            if L > best[0]:
                best = (L, i, math.degrees(math.atan2(dy, dx)))
        _, i, ang = best
        return cls(ox=xs[i], oy=ys[i], angle_deg=ang)

    def to_local(self, geom: BaseGeometry) -> BaseGeometry:
        g = translate(geom, xoff=-self.ox, yoff=-self.oy)
        return rotate(g, -self.angle_deg, origin=(0, 0), use_radians=False)

    def to_world(self, geom: BaseGeometry) -> BaseGeometry:
        g = rotate(geom, self.angle_deg, origin=(0, 0), use_radians=False)
        return translate(g, xoff=self.ox, yoff=self.oy)


def rect(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _plus_grand(geom: BaseGeometry) -> Polygon:
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    return geom


# ---------------------------------------------------------------- scène
@dataclass
class Scene:
    frame: Frame
    assiette_local: Polygon
    zone_local: Polygon
    voie_bas: bool                 # True si la voie est côté y faible (sinon y fort)
    voie_local: list[LineString]
    objets: list[Objet] = field(default_factory=list)

    def ajouter(self, o: Objet) -> None:
        self.objets.append(o)

    def of(self, kind: str) -> list[Objet]:
        return [o for o in self.objets if o.kind == kind]

    def finaliser_monde(self) -> None:
        for o in self.objets:
            o.geom_world = self.frame.to_world(o.geom_local)


def scene_depuis(terrain, frame: Frame) -> Scene:
    assiette_l = _plus_grand(frame.to_local(terrain.assiette))
    zone_l = _plus_grand(frame.to_local(terrain.zone_implantation))
    voie_l = [frame.to_local(g) for g in terrain.voie_edges]
    ay0, ay1 = assiette_l.bounds[1], assiette_l.bounds[3]
    if voie_l:
        ymid = sum(g.centroid.y for g in voie_l) / len(voie_l)
        voie_bas = ymid < (ay0 + ay1) / 2
    else:
        voie_bas = True
    return Scene(frame=frame, assiette_local=assiette_l, zone_local=zone_l,
                 voie_bas=voie_bas, voie_local=voie_l)


# ---------------------------------------------------------------- bâtiment : barre
def _bande_x(zone: Polygon, y0: float, y1: float, x0: float, x1: float,
             pas: float = 0.25, min_len: float = 8.0) -> Optional[tuple[float, float]]:
    """Plus long intervalle x contigu tel que le segment vertical [x]×[y0,y1] ⊆ zone (donc, zone
    ~convexe, le rectangle [a,b]×[y0,y1] ⊆ zone). Robuste quand la zone ne touche son rectangle
    englobant qu'en des sommets. None si on reste sous `min_len`."""
    n = int((x1 - x0) / pas)
    dedans = [zone.covers(LineString([(x0 + k * pas, y0), (x0 + k * pas, y1)])) for k in range(n + 1)]
    best = (0.0, None)
    i = 0
    while i <= n:
        if dedans[i]:
            j = i
            while j + 1 <= n and dedans[j + 1]:
                j += 1
            longueur = (j - i) * pas
            if longueur > best[0]:
                best = (longueur, (x0 + i * pas, x0 + j * pas))
            i = j + 1
        else:
            i += 1
    if best[0] < min_len or best[1] is None:
        return None
    return best[1]


def _meilleure_bande(zone: Polygon, y_lo: float, y_haut: float, D: float, x0: float, x1: float,
                     plaquer_bas: bool) -> Optional[tuple[float, float, float, float]]:
    """Fait glisser une bande de profondeur D entre y_lo et y_haut et garde la position donnant la
    plus longue emprise. `plaquer_bas` privilégie, à longueur égale, la bande la plus proche de y_lo.
    Renvoie (x_a, x_b, yb0, yb1) ou None."""
    marge = max(0.0, (y_haut - y_lo) - D)
    offsets = [round(k * 0.25, 2) for k in range(int(marge / 0.25) + 1)]
    best = None
    for off in offsets:
        yb0 = y_lo + off
        yb1 = yb0 + D
        if yb1 > y_haut + 1e-9:
            break
        res = _bande_x(zone, yb0, yb1, x0, x1)
        if res is None:
            continue
        longueur = res[1] - res[0]
        prio = (longueur, -off if plaquer_bas else off)
        if best is None or prio > best[0]:
            best = (prio, (res[0], res[1], yb0, yb1))
    return best[1] if best else None


def _tiler_modules(conv: Conventions, x0: float, x1: float, repartition: list[str]
                   ) -> tuple[list[tuple[float, float, str]], Optional[tuple[float, float]]]:
    """Garnit [x0,x1] de modules (cycle `repartition`) + UN noyau inséré au plus près du milieu.
    Renvoie (modules=[(xa,xb,type)], noyau=(xa,xb)|None). Déterministe."""
    milieu = (x0 + x1) / 2.0
    cur = x0
    modules: list[tuple[float, float, str]] = []
    noyau: Optional[tuple[float, float]] = None
    i = 0
    while True:
        # insérer le noyau une seule fois, dès qu'on franchit le milieu
        if noyau is None and cur >= milieu and (cur + conv.largeur_noyau_m) <= x1:
            noyau = (cur, cur + conv.largeur_noyau_m)
            cur += conv.largeur_noyau_m
            continue
        t = repartition[i % len(repartition)]
        w = conv.largeur_module(t)
        if cur + w > x1 + 1e-9:
            break
        modules.append((cur, cur + w, t))
        cur += w
        i += 1
    if noyau is None and modules:        # noyau non casé : remplace le dernier module par le noyau
        xa, xb, _ = modules.pop()
        noyau = (xa, min(xa + conv.largeur_noyau_m, xb))
    return modules, noyau


def poser_barre(scene: Scene, conv: Conventions, *, x_start: float, x_end: float,
                repartition: list[str], niveaux: int, ref: str = "B") -> int:
    """Pose une barre (emprise + modules/noyau/coursive sur `niveaux`) dans la zone, le long de
    l'axe x, plaquée sur la grande limite OPPOSÉE à la voie. Renvoie modules/niveau posés (0 si échec)."""
    zx0, zy0, zx1, zy1 = scene.zone_local.bounds
    D = conv.profondeur_m
    # barre plaquée sur la grande limite OPPOSÉE à la voie ; coursive côté voie
    plaquer_bas = not scene.voie_bas       # voie en haut -> barre en bas (plaquer_bas=True)
    bande = _meilleure_bande(scene.zone_local, zy0, zy1, D, max(x_start, zx0), min(x_end, zx1),
                             plaquer_bas=plaquer_bas)
    if bande is None:
        return 0
    x0, x1, yb0, yb1 = bande
    if scene.voie_bas:                     # voie côté y faible -> coursive en bas de la barre
        y_coursive = (yb0, yb0 + conv.largeur_coursive_m)
        y_band = (yb0 + conv.largeur_coursive_m, yb1)
    else:                                  # voie côté y fort -> coursive en haut de la barre
        y_coursive = (yb1 - conv.largeur_coursive_m, yb1)
        y_band = (yb0, yb1 - conv.largeur_coursive_m)
    modules, noyau = _tiler_modules(conv, x0, x1, repartition)
    if not modules:
        return 0
    used_x1 = max([m[1] for m in modules] + ([noyau[1]] if noyau else []))
    # emprise (plan) = barre réellement occupée
    scene.ajouter(Objet("batiment_emprise", rect(x0, yb0, used_x1, yb1), ref=ref))
    for n in range(niveaux):
        scene.ajouter(Objet("coursive", rect(x0, y_coursive[0], used_x1, y_coursive[1]),
                            niveau=n, ref=ref))
        if noyau:
            scene.ajouter(Objet("noyau", rect(noyau[0], y_band[0], noyau[1], y_band[1]),
                                niveau=n, ref=ref))
        for (xa, xb, t) in modules:
            scene.ajouter(Objet("module", rect(xa, y_band[0], xb, y_band[1]),
                                niveau=n, type_logement=t, ref=ref))
    return len(modules)


# ---------------------------------------------------------------- stationnement aérien
def poser_stationnement(scene: Scene, conv: Conventions, *, cible: int) -> int:
    """Pose jusqu'à `cible` places (2,5 × 5 m) desservies par une allée, entre la voie et le bâti.
    Chaque place TOUCHE l'allée (partage d'arête, aire d'intersection nulle). Un accès relie l'allée
    à la voie. Renvoie le nombre de places RÉELLEMENT dessinées (contenues dans l'assiette, hors bâti)."""
    if cible <= 0:
        return 0
    bati = unary_union([o.geom_local for o in scene.of("batiment_emprise")]) if scene.of("batiment_emprise") else None
    ax0, ay0, ax1, ay1 = scene.assiette_local.bounds
    pl, pw = conv.place_longueur_m, conv.place_largeur_m         # 5 (profondeur y), 2.5 (largeur x)
    aw = conv.allee_largeur_m
    # on garnit TOUTE la hauteur libre de l'assiette : les places/allées sous le bâti sont écartées
    # par `libre()`. Le stationnement occupe donc la bande devant le bâti ET les bouts au-delà de la
    # barre (où toute la largeur de l'assiette est disponible). La traversée depuis la voie se fait
    # en partant du côté voie.
    if scene.voie_bas:
        y_lo, y_hi = ay0, ay1
    else:
        y_lo, y_hi = ay0, ay1

    def libre(p: Polygon) -> bool:
        if not scene.assiette_local.contains(p.buffer(-1e-9)):
            return False
        if bati is not None and p.intersects(bati) and p.intersection(bati).area > 1e-6:
            return False
        return True

    # bandes alternées sur toute la hauteur de l'assiette : place(5) / allée(5) / place(5) / allée(5)…
    # Chaque rangée de places est adjacente à une allée. Places/allées sous le bâti ou hors assiette
    # écartées. On conserve TOUS les morceaux d'allée (le bâti peut couper une bande en deux).
    pose = 0
    place_rows: list[tuple[float, float]] = []
    allee_bandes: list[tuple[float, float]] = []
    y, est_place = y_lo, True
    while y < y_hi - 1e-9:
        if est_place:
            if y + pl <= y_hi + 1e-9:
                place_rows.append((y, y + pl))
            y += pl
        else:
            allee_bandes.append((y, y + aw))
            y += aw
        est_place = not est_place

    allee_objs: list[Objet] = []
    for (ya, yb) in allee_bandes:
        bande = scene.assiette_local.intersection(rect(ax0, ya, ax1, yb))
        if bati is not None and not bande.is_empty:
            bande = bande.difference(bati)
        if bande.is_empty:
            continue
        morceaux = list(bande.geoms) if isinstance(bande, MultiPolygon) else [bande]
        for g in morceaux:
            if not isinstance(g, Polygon) or g.area < 2.0:
                continue
            mnx, mny, mxx, mxy = g.bounds
            if min(mxx - mnx, mxy - mny) < aw - 0.05:        # trop étroit pour une allée
                continue
            o = Objet("allee", g)
            scene.ajouter(o)
            allee_objs.append(o)
    if not allee_objs:
        return 0

    # accès d'abord (relie la voie à l'allée la plus proche) : les places ne doivent pas l'empiéter
    acces_geom = _acces_geom(scene, conv, allee_objs)
    if acces_geom is not None:
        scene.ajouter(Objet("acces", acces_geom))

    # places rangée par rangée, de gauche à droite ; chaque place touche une allée (partage d'arête)
    for (yr0, yr1) in place_rows:
        x = ax0
        while x + pw <= ax1 + 1e-9 and pose < cible:
            p = rect(x, yr0, x + pw, yr1)
            x += pw
            if not libre(p):
                continue
            if acces_geom is not None and p.intersection(acces_geom).area > 1e-6:
                continue
            if not any(p.distance(a.geom_local) < 1e-6 for a in allee_objs):
                continue
            scene.ajouter(Objet("place", p))
            pose += 1
    return pose


def _acces_geom(scene: Scene, conv: Conventions, allee_objs: list[Objet]) -> Optional[Polygon]:
    ax0, ay0, ax1, ay1 = scene.assiette_local.bounds
    cw = conv.acces_largeur_m
    # allée la plus proche de la voie
    if scene.voie_bas:
        a = min(allee_objs, key=lambda o: o.geom_local.bounds[1])
        y_voie, y_all = ay0, a.geom_local.bounds[1]
        acces = rect(0, y_voie, cw, y_all)
    else:
        a = max(allee_objs, key=lambda o: o.geom_local.bounds[3])
        y_voie, y_all = ay1, a.geom_local.bounds[3]
        acces = rect(0, y_all, cw, y_voie)
    # centre l'accès sur l'emprise x de la voie (segments voie en local)
    vx = unary_union(scene.voie_local).centroid.x if scene.voie_local else (ax0 + ax1) / 2.0
    acces = translate(acces, xoff=vx - cw / 2.0)
    acces = scene.assiette_local.intersection(acces)
    acces = _plus_grand(acces) if not acces.is_empty else acces
    if not acces.is_empty and isinstance(acces, Polygon) and acces.area > 0.5:
        return acces
    return None


# ---------------------------------------------------------------- espaces libres
def poser_espaces_libres(scene: Scene) -> None:
    """Espaces libres = assiette − (bâti ∪ places ∪ allées ∪ accès). Mesuré, jamais annoncé."""
    occupe = [o.geom_local for o in scene.objets
              if o.kind in ("batiment_emprise", "place", "allee", "acces")]
    if not occupe:
        libres = scene.assiette_local
    else:
        libres = scene.assiette_local.difference(unary_union(occupe))
    if libres.is_empty:
        return
    geoms = libres.geoms if isinstance(libres, MultiPolygon) else [libres]
    for g in geoms:
        if isinstance(g, Polygon) and g.area > 0.5:
            scene.ajouter(Objet("espace_libre", g))
