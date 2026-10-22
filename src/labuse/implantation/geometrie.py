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
        # Une assiette dégénérée (sliver, quasi-linéaire) peut rendre un MRR non polygonal ou à
        # moins de 4 arêtes : on retombe sur un repère non tourné plutôt que de lever.
        if not isinstance(mrr, Polygon) or mrr.is_empty:
            return cls(ox=0.0, oy=0.0, angle_deg=0.0)
        xs, ys = mrr.exterior.coords.xy
        # arête la plus longue = grand axe
        best = (0.0, 0, 0.0)
        for i in range(len(xs) - 1):
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


def _valide(geom: BaseGeometry) -> BaseGeometry:
    """Rend une géométrie valide (les différences/intersections peuvent produire des auto-contacts)."""
    if geom is None or geom.is_empty or geom.is_valid:
        return geom
    return geom.buffer(0)


def _plus_grand(geom: BaseGeometry) -> Polygon:
    geom = _valide(geom)
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
    stationnement_note: Optional[dict] = None   # {allee_unique, cotes, deux_cotes, raison}
    ppr_rouge_local: Optional[BaseGeometry] = None   # PPR interdiction (local), interdite au stationnement
    sous_sol: Optional[dict] = None   # ETUDE-V6-2 (Lot 3) — parking enterré : {places, emprise_m2, rampe_m2}

    def ajouter(self, o: Objet) -> None:
        self.objets.append(o)

    def of(self, kind: str) -> list[Objet]:
        return [o for o in self.objets if o.kind == kind]

    def finaliser_monde(self) -> None:
        # La rotation affine monde↔local peut, en flottant, rendre AUTO-SÉCANTE une géométrie valide
        # (typiquement les espaces libres / l'accès issus de différences). On revalide le monde pour
        # que la géométrie SERVIE (GeoJSON) soit toujours valide — mesures et comptes restent pris
        # sur le local, inchangé.
        for o in self.objets:
            o.geom_world = _valide(self.frame.to_world(o.geom_local))


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
    rouge_l = None
    if getattr(terrain, "ppr_rouge", None) is not None and not terrain.ppr_rouge.is_empty:
        rouge_l = frame.to_local(terrain.ppr_rouge)
    return Scene(frame=frame, assiette_local=assiette_l, zone_local=zone_l,
                 voie_bas=voie_bas, voie_local=voie_l, ppr_rouge_local=rouge_l)


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
    """Garnit [x0,x1] de modules (cycle `repartition`) avec autant de NOYAUX que nécessaire :
    un noyau au début, puis un nouveau dès qu'on dépasse `max_logements_par_noyau` modules OU
    `longueur_max_coursive_par_noyau_m` de coursive depuis le dernier noyau.
    Renvoie (modules=[(xa,xb,type)], noyaux=[(xa,xb)]). Déterministe."""
    nw = conv.largeur_noyau_m()
    kmax = conv.max_logements_par_noyau
    lmax = conv.longueur_max_coursive_par_noyau_m
    cur = x0
    modules: list[tuple[float, float, str]] = []
    noyaux: list[tuple[float, float]] = []
    depuis, coursive_depuis, i = 0, 0.0, 0

    def pose_noyau() -> bool:
        nonlocal cur, depuis, coursive_depuis
        if cur + nw > x1 + 1e-9:
            return False
        noyaux.append((cur, cur + nw))
        cur += nw
        depuis, coursive_depuis = 0, 0.0
        return True

    if not pose_noyau():
        return [], []
    while True:
        t = repartition[i % len(repartition)]
        w = conv.largeur_module(t)
        if depuis >= kmax or coursive_depuis + w > lmax + 1e-9:   # noyau supplémentaire requis
            if not pose_noyau():
                break
        if cur + w > x1 + 1e-9:
            break
        modules.append((cur, cur + w, t))
        cur += w
        depuis += 1
        coursive_depuis += w
        i += 1
    if not modules:
        return [], []
    # retire un éventuel noyau terminal sans module après lui
    if noyaux and noyaux[-1][0] >= max(m[1] for m in modules):
        noyaux.pop()
    return modules, noyaux


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
    modules, noyaux = _tiler_modules(conv, x0, x1, repartition)
    if not modules:
        return 0
    used_x1 = max([m[1] for m in modules] + [n[1] for n in noyaux])
    # emprise (plan) = barre réellement occupée
    scene.ajouter(Objet("batiment_emprise", rect(x0, yb0, used_x1, yb1), ref=ref))
    for n in range(niveaux):
        scene.ajouter(Objet("coursive", rect(x0, y_coursive[0], used_x1, y_coursive[1]),
                            niveau=n, ref=ref))
        for (nxa, nxb) in noyaux:
            scene.ajouter(Objet("noyau", rect(nxa, y_band[0], nxb, y_band[1]), niveau=n, ref=ref))
        for (xa, xb, t) in modules:
            scene.ajouter(Objet("module", rect(xa, y_band[0], xb, y_band[1]),
                                niveau=n, type_logement=t, ref=ref))
    return len(modules)


# ---------------------------------------------------------------- stationnement aérien
def poser_stationnement(scene: Scene, conv: Conventions, *, cible: int) -> int:
    """UNE allée unique, places des DEUX côtés quand la largeur le permet (sinon un seul côté, le
    `stationnement_note` dit pourquoi). Chaque place touche l'allée (aire ∩ = 0). Un accès relie
    l'allée à la voie. Renvoie le nb de places dessinées (≤ cible). Allée posée seulement si ≥ 1 place
    la dessert ET qu'elle est reliée à l'accès (sinon aucune allée, pas de cul-de-sac)."""
    if cible <= 0:
        return 0
    batis = [o.geom_local for o in scene.of("batiment_emprise")]
    bati = unary_union(batis) if batis else None
    free = scene.assiette_local.difference(bati) if bati is not None else scene.assiette_local
    # aucune allée ni place en PPR rouge (interdiction) : hypothèse prudente
    if scene.ppr_rouge_local is not None and not scene.ppr_rouge_local.is_empty:
        free = free.difference(scene.ppr_rouge_local)
    free = _valide(free)
    ax0, ay0, ax1, ay1 = scene.assiette_local.bounds
    pl, pw, aw, cw = (conv.place_longueur_m, conv.place_largeur_m,
                      conv.allee_largeur_m, conv.acces_largeur_m)

    def dans_libre(p: Polygon) -> bool:
        return free.covers(p.buffer(-1e-9))

    # choisit la bande d'allée (centre yc, le long de x) maximisant les places des deux côtés
    best = None
    yc = ay0 + aw / 2.0
    while yc + aw / 2.0 <= ay1 + 1e-9:
        allee_g = free.intersection(rect(ax0, yc - aw / 2.0, ax1, yc + aw / 2.0))
        allee_g = _plus_grand(allee_g) if not allee_g.is_empty else allee_g
        yc += 0.5
        if allee_g.is_empty or not isinstance(allee_g, Polygon):
            continue
        mnx, mny, mxx, mxy = allee_g.bounds
        if (mxx - mnx) < 2 * pw or (mxy - mny) < aw - 0.05:
            continue
        cyc = (mny + mxy) / 2.0
        cands = []
        for (yr0, yr1, side) in [(cyc - aw / 2.0 - pl, cyc - aw / 2.0, "bas"),
                                 (cyc + aw / 2.0, cyc + aw / 2.0 + pl, "haut")]:
            x = ax0
            while x + pw <= ax1 + 1e-9:
                p = rect(x, yr0, x + pw, yr1)
                x += pw
                if dans_libre(p) and p.distance(allee_g) < 1e-6:
                    cands.append((p, side))
        if not cands:
            continue
        key = (len(cands), -cyc)
        if best is None or key > best[0]:
            best = (key, allee_g, cands)
    if best is None:
        return 0
    _, allee_g, cands = best

    # toutes les places candidates, ordre déterministe (côté puis x)
    tries = sorted(cands, key=lambda pc: (round(pc[0].bounds[1], 2), round(pc[0].bounds[0], 2)))

    def _trim_allee(places_pc, acces=None):
        """Allée COUPÉE au droit de la dernière place desservie (+ la jonction d'accès) : aucun
        tronçon d'allée sans place ni accès en bout."""
        xs = [p.bounds[0] for p, _ in places_pc] + [p.bounds[2] for p, _ in places_pc]
        xmin, xmax = min(xs), max(xs)
        if acces is not None:
            from shapely.ops import nearest_points
            ap, _ = nearest_points(allee_g, acces)
            xmin, xmax = min(xmin, ap.x), max(xmax, ap.x)
        t = allee_g.intersection(rect(xmin, ay0 - 1, xmax, ay1 + 1))
        return _plus_grand(t) if not t.is_empty else t

    # 1) allée + accès provisoires (sur les `cible` premières) pour filtrer les places
    allee0 = _trim_allee(tries[:cible])
    if allee0.is_empty or not isinstance(allee0, Polygon):
        return 0
    acces0 = _acces_corridor(scene, conv, allee0, bati)
    if acces0 is None:
        return 0
    # 2) places retenues = celles hors accès (backfill au-delà de cible), jusqu'à cible
    retenues = [pc for pc in tries if pc[0].intersection(acces0).area <= 1e-6][:cible]
    if not retenues:
        return 0
    # 3) allée finale coupée au droit des places retenues (+ jonction d'accès)
    allee_final = _trim_allee(retenues, acces0)
    if allee_final.is_empty or not isinstance(allee_final, Polygon):
        return 0
    # 4) accès reconstruit CONTRE l'allée finale puis soustrait d'elle -> 0 chevauchement garanti
    acces_g = _acces_corridor(scene, conv, allee_final, bati)
    if acces_g is None:
        return 0
    acces_g = _plus_grand(acces_g.difference(allee_final))
    if (acces_g.is_empty or not isinstance(acces_g, Polygon) or acces_g.area < 0.5
            or acces_g.distance(allee_final) > 1e-6):
        return 0
    retenues = [pc for pc in retenues if pc[0].intersection(acces_g).area <= 1e-6]
    if not retenues:
        return 0
    scene.ajouter(Objet("allee", allee_final))
    scene.ajouter(Objet("acces", acces_g))
    cotes = set()
    for (p, side) in retenues:
        scene.ajouter(Objet("place", p))
        cotes.add(side)
    deux = len(cotes) == 2
    scene.stationnement_note = {
        "allee_unique": True, "cotes": sorted(cotes), "deux_cotes": deux,
        "raison": ("places des deux côtés de l'allée unique" if deux else
                   "places d'un seul côté : la largeur libre perpendiculaire à l'allée n'autorise pas "
                   "une seconde rangée (il faut allée 5 m + 2 × 5 m de places = 15 m)"),
    }
    return len(retenues)


def _acces_corridor(scene: Scene, conv: Conventions, allee_g: Polygon,
                    bati: Optional[BaseGeometry]) -> Optional[Polygon]:
    """Corridor (acces_largeur) reliant la limite voie à l'allée. None si rien ne les relie."""
    from shapely.ops import nearest_points
    if not scene.voie_local:
        return None
    voie = unary_union(scene.voie_local)
    vp, ap = nearest_points(voie, allee_g)
    seg = LineString([vp, ap])
    if seg.length < 0.1:
        corridor = vp.buffer(conv.acces_largeur_m / 2.0, cap_style=3)
    else:
        corridor = seg.buffer(conv.acces_largeur_m / 2.0, cap_style=2)
    corridor = scene.assiette_local.intersection(corridor)
    # l'accès TOUCHE l'allée (partage d'arête) mais ne la recouvre pas, évite le bâti et la PPR rouge
    corridor = corridor.difference(allee_g)
    if bati is not None and not corridor.is_empty:
        corridor = corridor.difference(bati)
    if scene.ppr_rouge_local is not None and not corridor.is_empty:
        corridor = corridor.difference(scene.ppr_rouge_local)
    corridor = _plus_grand(corridor) if not corridor.is_empty else corridor
    if (corridor.is_empty or not isinstance(corridor, Polygon) or corridor.area < 0.5
            or corridor.distance(voie) > 0.6 or corridor.distance(allee_g) > 1e-6):
        return None
    return corridor


# ---------------------------------------------------------------- stationnement en SOUS-SOL (Lot 3)
def poser_sous_sol(scene: Scene, conv: Conventions, *, cible: int) -> int:
    """ETUDE-V6-2 (Lot 3) — parking ENTERRÉ : aucune place aérienne ; on pose une RAMPE au sol (accès au
    niveau −1) et on RECORD l'emprise du sous-sol (cible × m²/place usuels). L'emprise est confrontée à
    l'emprise réglementaire par un contrôle (controles.py). Le sol reste libre pour le bâti et la pleine
    terre → davantage de logements qu'en aérien. Renvoie le nombre de places logées au −1 (= cible)."""
    if cible <= 0:
        scene.sous_sol = {"places": 0, "emprise_m2": 0.0, "rampe_m2": 0.0,
                          "m2_par_place": conv.m2_par_place_sous_sol}
        return 0
    emprise = round(cible * conv.m2_par_place_sous_sol, 1)
    # rampe au sol : un rectangle (accès véhicule) adossé à la voie, dans l'espace libre (hors bâti/PPR).
    rampe_m2 = 0.0
    batis = [o.geom_local for o in scene.of("batiment_emprise")]
    bati = unary_union(batis) if batis else None
    free = scene.assiette_local.difference(bati) if bati is not None else scene.assiette_local
    if scene.ppr_rouge_local is not None and not scene.ppr_rouge_local.is_empty:
        free = free.difference(scene.ppr_rouge_local)
    free = _valide(free)
    ax0, ay0, ax1, ay1 = scene.assiette_local.bounds
    w, d = conv.acces_largeur_m, max(6.0, conv.place_longueur_m)   # rampe ≈ 4 × 6 m
    y0, y1 = (ay0, ay0 + d) if scene.voie_bas else (ay1 - d, ay1)  # adossée à la voie
    xc = (ax0 + ax1) / 2.0
    rampe = free.intersection(rect(xc - w / 2.0, y0, xc + w / 2.0, y1))
    rampe = _plus_grand(rampe) if not rampe.is_empty else rampe
    if isinstance(rampe, Polygon) and rampe.area > 1.0:
        scene.ajouter(Objet("rampe", rampe))
        rampe_m2 = round(rampe.area, 1)
    scene.sous_sol = {"places": cible, "emprise_m2": emprise, "rampe_m2": rampe_m2,
                      "m2_par_place": conv.m2_par_place_sous_sol}
    return cible


# ---------------------------------------------------------------- espaces libres
def poser_espaces_libres(scene: Scene) -> None:
    """Espaces libres = assiette − (bâti ∪ places ∪ allées ∪ accès ∪ rampe). Mesuré, jamais annoncé."""
    occupe = [o.geom_local for o in scene.objets
              if o.kind in ("batiment_emprise", "place", "allee", "acces", "rampe")]
    if not occupe:
        libres = scene.assiette_local
    else:
        libres = _valide(scene.assiette_local.difference(unary_union(occupe)))
    if libres.is_empty:
        return
    geoms = libres.geoms if isinstance(libres, MultiPolygon) else [libres]
    for g in geoms:
        if isinstance(g, Polygon) and g.area > 0.5:
            scene.ajouter(Objet("espace_libre", g))
