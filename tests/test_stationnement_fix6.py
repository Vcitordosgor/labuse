"""ETUDE-STATIONNEMENT-FIX-6 — point 1 : le raccord ACCÈS–VOIE se mesure comme la jonction allée–accès,
en LARGEUR DE CONTACT RÉELLE avec la limite de la voie, au moins la largeur de passage (2,40 m), SANS
bande de tolérance. Un contact ponctuel, un contact de 50 cm, ou un vide de 50 cm avant la voie ne
desservent AUCUNE place ; un contact de 2,40 m dessert."""
from __future__ import annotations

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import labuse.implantation.controles as C


def _scene():
    """Une place (nez en haut, y=5), une allée pleine au-dessus, un accès montant jusqu'à y=16. L'arête
    commune allée–accès (x ∈ [0 ; 6,5]) est LARGE : seul le raccord accès–voie varie d'un cas à l'autre."""
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    allee = Polygon([(-4, 5), (6.5, 5), (6.5, 10), (-4, 10)])
    acces = Polygon([(0, 10), (10, 10), (10, 16), (0, 16)])       # haut (y=16) large de 10 m
    return place, allee, acces


# Assiette du projet (bord supérieur sur la voie, y = 16) : les plans synthétiques sont tous SOUS la voie. Le
# contrôle réel reçoit toujours `scene.assiette_local` ; les tests la fournissent de même (FIX-12/13).
_ASS = Polygon([(-40, -40), (60, -40), (60, 16), (-40, 16)])


def _manque(voie):
    place, allee, acces = _scene()
    return C._pincement_allee([allee], [place], 5.0, [acces], voie, assiette=_ASS)


def test_raccord_voie_contact_ponctuel_refuse():
    """L'accès ne touche la voie qu'en UN POINT (x=10) → aucune voiture n'entre → place NON comptée."""
    assert _manque(LineString([(10, 16), (20, 16)])) > C._DEGAGEMENT_SEUIL_M2


def test_raccord_voie_contact_50cm_refuse():
    """Contact accès–voie de 50 cm (x ∈ [9,5 ; 10]) < largeur de passage → place NON comptée."""
    assert _manque(LineString([(9.5, 16), (20, 16)])) > C._DEGAGEMENT_SEUIL_M2


def test_raccord_voie_vide_50cm_refuse():
    """Un VIDE de 50 cm sépare l'accès (haut à y=16) de la voie (y=16,5) → le contrôle reste STRICT (contact
    réel sur la voie, aucune bande de tolérance) → place NON comptée. C'est le DESSIN qui doit toucher la voie
    (geometrie._raccorder_acces_voie prolonge l'accès jusqu'à la limite), pas le contrôle qui s'assouplit."""
    assert _manque(LineString([(0, 16.5), (10, 16.5)])) > C._DEGAGEMENT_SEUIL_M2


def test_raccord_voie_contact_240_desservi():
    """Contact accès–voie de 2,40 m (x ∈ [7,6 ; 10]) = largeur de passage → la place EST desservie."""
    assert _manque(LineString([(7.6, 16), (20, 16)])) <= C._DEGAGEMENT_SEUIL_M2


# FIX-7 — le raccord se mesure comme le BORD DE VOIE RECOUVERT par l'accès (voie_l ∩ accès), segment D'UN SEUL
# TENANT, au seuil EXACT de 2,40 m : AUCUNE bande de 3 cm, AUCUN arrondi. Un vide de 2 cm et un contact de
# 2,35 m, qui passaient par la bande (acceptée dès 2,38 m), sont désormais REFUSÉS.
def test_raccord_voie_vide_2cm_refuse():
    """Un VIDE de 2 cm (voie à y=16,02, accès à y=16) : l'accès ne recouvre AUCUN bord de voie → NON comptée."""
    assert _manque(LineString([(0, 16.02), (10, 16.02)])) > C._DEGAGEMENT_SEUIL_M2


def test_raccord_voie_contact_235_refuse():
    """Un recouvrement de 2,35 m (x ∈ [7,65 ; 10]) est SOUS le seuil EXACT de 2,40 m → NON comptée (plus
    d'acceptation à 2,38 m par l'ancienne bande de tolérance)."""
    assert _manque(LineString([(7.65, 16), (20, 16)])) > C._DEGAGEMENT_SEUIL_M2


# FIX-8 (point 1) — CONNEXITÉ réelle, tronçons jointifs réunis, largeur minimale le long de l'accès.
def test_deux_reseaux_separes_2cm_une_seule_place():
    """Deux réseaux séparés de 2 cm : A a un raccord réel de 3 m à la voie, B ne la touche pas (s'arrête à
    50 cm). B ne doit PAS être compté juste parce qu'il est PROCHE du raccord de A — il faut la MÊME
    composante connexe. Seule la place de A est desservie."""
    voie = LineString([(-5, 16), (20, 16)])
    # réseau A (gauche) : accès mordant la voie sur 3 m
    place_a = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    allee_a = Polygon([(-4, 5), (3, 5), (3, 10), (-4, 10)])
    acces_a = Polygon([(0, 10), (3, 10), (3, 16.1), (0, 16.1)])
    # réseau B (droite), à 2 cm de A, accès s'arrêtant à 50 cm sous la voie (ne la touche pas)
    place_b = Polygon([(3.52, 0), (6.02, 0), (6.02, 5), (3.52, 5)])
    allee_b = Polygon([(3.02, 5), (6.02, 5), (6.02, 10), (3.02, 10)])
    acces_b = Polygon([(3.02, 10), (6.02, 10), (6.02, 15.5), (3.02, 15.5)])
    # A seul : desservi
    assert C._pincement_allee([allee_a], [place_a], 5.0, [acces_a], voie, assiette=_ASS) <= C._DEGAGEMENT_SEUIL_M2
    # A + B : B n'est PAS desservi (manque ≈ aire d'une place), alors que A l'est
    manque = C._pincement_allee([allee_a, allee_b], [place_a, place_b], 5.0, [acces_a, acces_b], voie, assiette=_ASS)
    assert 11.0 < manque < 14.0, f"seule la place de B doit manquer (≈ 12,5 m²), obtenu {manque:.1f}"


def test_tronçons_jointifs_forment_240():
    """Deux tronçons d'accès JOINTIFS, chacun recouvrant 1,20 m de voie, forment un contact CONTINU de 2,40 m
    (réunis avant mesure, sans combler de vide) → la place est desservie."""
    voie = LineString([(-5, 16), (20, 16)])
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    allee = Polygon([(-4, 5), (2.5, 5), (2.5, 10), (-4, 10)])          # couvre la place (dégagement plein)
    acces1 = Polygon([(0, 10), (1.2, 10), (1.2, 16.1), (0, 16.1)])     # recouvre la voie sur x ∈ [0 ; 1,2]
    acces2 = Polygon([(1.2, 10), (2.4, 10), (2.4, 16.1), (1.2, 16.1)])  # JOINTIF, recouvre x ∈ [1,2 ; 2,4]
    assert C._pincement_allee([allee], [place], 5.0, [acces1, acces2], voie, assiette=_ASS) <= C._DEGAGEMENT_SEUIL_M2


# FIX-9 (relecture) — la largeur de desserte (goulet) et le comptage des places reposent sur le MÊME noyau
# roulant (`_desserte_core`) : une place comptée implique un goulet ≥ 2,40 m. On construit un plan (accès depuis
# la voie avec un goulet de largeur w, une allée, une place) et on vérifie la largeur retenue.
def _plan_desserte(neck_w, neck_y=(12.0, 13.0), base=6.0):
    voie = LineString([(-5, 16), (20, 16)])
    cx = base / 2.0
    y0, y1 = neck_y
    morceaux = [Polygon([(cx - neck_w / 2, y0), (cx + neck_w / 2, y0),
                         (cx + neck_w / 2, y1), (cx - neck_w / 2, y1)])]     # le goulet
    if y1 < 16.1:
        morceaux.append(Polygon([(0, y1), (base, y1), (base, 16.1), (0, 16.1)]))   # haut (contact voie)
    if y0 > 10:
        morceaux.append(Polygon([(0, 10), (base, 10), (base, y0), (0, y0)]))       # bas (vers l'allée)
    acces = unary_union(morceaux)
    allee = Polygon([(-4, 5), (base, 5), (base, 10), (-4, 10)])
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    return [allee], [place], 5.0, [acces], voie


def _goulet(neck_w, **kw):
    a, p, lr, ac, v = _plan_desserte(neck_w, **kw)
    return C._largeur_min_desserte(a, p, lr, ac, v, _ASS)


def test_goulet_milieu_3m():
    """Rétrécissement à 3 m au MILIEU du chemin → largeur de desserte = 3 m."""
    assert abs(_goulet(3.0, neck_y=(12.0, 13.0)) - 3.0) <= 0.25


def test_goulet_entree_3m():
    """Rétrécissement à 3 m À L'ENTRÉE (contre la voie) → largeur de desserte = 3 m."""
    assert abs(_goulet(3.0, neck_y=(15.0, 16.1)) - 3.0) <= 0.25


def test_goulet_regulier_5m():
    """Chemin régulier de 5 m (aucun goulet) → largeur de desserte = 5 m."""
    assert abs(_goulet(5.0, base=5.0, neck_y=(10.0, 16.1)) - 5.0) <= 0.25


def test_desserte_et_comptage_jamais_contradictoires():
    """Garde-fou de la relecture : sur un même plan, une place COMPTÉE (desservie à 2,40 m par `_desserte_core`)
    implique TOUJOURS un goulet ≥ 2,40 m. Un goulet sous 2,40 m (ici 2,0 m) ne doit compter AUCUNE place."""
    for nw in (2.0, 2.4, 3.0, 5.0):
        a, p, lr, ac, v = _plan_desserte(nw)
        _manque, nb = C._desserte_core(a, p, lr, ac, v, C._PASSAGE_MIN_M, _ASS)
        goulet = C._largeur_min_desserte(a, p, lr, ac, v, _ASS)
        if nb >= 1:
            assert goulet >= C._PASSAGE_MIN_M - 0.05, f"place comptée (goulet {nw} m) mais desserte {goulet:.2f} m < 2,40"
        else:
            assert goulet < C._PASSAGE_MIN_M, f"aucune place desservie (goulet {nw} m) mais desserte {goulet:.2f} m"


# FIX-10 — atteignabilité PUREMENT TOPOLOGIQUE (bande de voie ajoutée à l'aire roulante, érodée, composante qui
# contient la graine), AUCUN rattachement par proximité. Un étranglement COURT après la voie ne doit plus être
# franchi par le disque de passage, où qu'il soit sur le trajet.
def _plan_etranglement(nw, y0, y1):
    """Bouche 6 m à la voie, étranglement `nw` sur [y0 ; y1] (court), accès de nouveau 6 m jusqu'au
    stationnement. Renvoie (allees, places, largeur, acces, voie)."""
    voie = LineString([(-5, 16), (15, 16)])
    allee = Polygon([(-2, 5), (8, 5), (8, 10), (-2, 10)])
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    parts = [Polygon([(3 - nw / 2, y0), (3 + nw / 2, y0), (3 + nw / 2, y1), (3 - nw / 2, y1)])]
    if y1 < 16.1:
        parts.append(Polygon([(0, y1), (6, y1), (6, 16.1), (0, 16.1)]))
    if y0 > 10:
        parts.append(Polygon([(0, 10), (6, 10), (6, y0), (0, y0)]))
    return [allee], [place], 5.0, [unary_union(parts)], voie


def test_contre_exemple_relecteur_passage_court_2m():
    """Le contre-exemple du relecteur : bouche 6 m, puis à 20 cm de la voie un passage de 2 m sur 10 cm, puis
    6 m. AUCUNE place comptée (2 m < 2,40 m) et goulet annoncé = 2 m (plus le 5,208 m du rattachement faux)."""
    a, p, lr, ac, v = _plan_etranglement(2.0, 15.7, 15.8)
    assert C._desserte_core(a, p, lr, ac, v, C._PASSAGE_MIN_M, _ASS)[1] == 0
    assert abs(C._largeur_min_desserte(a, p, lr, ac, v, _ASS) - 2.0) <= 0.2


def test_meme_etranglement_240_place_comptee():
    """Le même étranglement court porté à 2,40 m : une place EST comptée, goulet 2,40 m."""
    a, p, lr, ac, v = _plan_etranglement(2.40, 15.7, 15.8)
    assert C._desserte_core(a, p, lr, ac, v, C._PASSAGE_MIN_M, _ASS)[1] == 1
    assert abs(C._largeur_min_desserte(a, p, lr, ac, v, _ASS) - 2.40) <= 0.2


def test_etranglement_3m_entree_milieu_avant_stationnement():
    """Un étranglement COURT de 3 m donne un goulet de 3 m où qu'il soit sur le trajet (entrée, milieu, juste
    avant le stationnement) : le disque ne le franchit jamais par un coin."""
    for (y0, y1) in ((15.7, 15.8), (12.8, 12.9), (10.1, 10.2)):
        a, p, lr, ac, v = _plan_etranglement(3.0, y0, y1)
        g = C._largeur_min_desserte(a, p, lr, ac, v, _ASS)
        assert abs(g - 3.0) <= 0.25, f"étranglement 3 m @y[{y0};{y1}] → goulet {g:.2f} m (attendu 3)"


# FIX-12 — le côté de la bande n'est PLUS choisi par un centre (assiette.centroid tombe du mauvais côté sur une
# assiette CONCAVE). On construit la bande des DEUX côtés du recouvrement puis on lui RETIRE l'assiette : ce qui
# reste est à l'extérieur par construction, quelle que soit la forme du terrain.
def _bande_moins_assiette(R, assiette, D=12.0):
    """Reconstruit la bande du contrôle : bande des deux côtés du recouvrement R, moins l'assiette."""
    import math
    (ax, ay), (bx, by) = R.coords[0], R.coords[-1]
    dl = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / dl, (bx - ax) / dl
    plein = Polygon([(ax + nx * D, ay + ny * D), (bx + nx * D, by + ny * D),
                     (bx - nx * D, by - ny * D), (ax - nx * D, ay - ny * D)])
    return plein.difference(assiette).buffer(0)


def _plan_C(nw=2.0, rot=0):
    """Assiette en C (ouverte à droite ; son centroïde tombe DANS l'encoche, HORS de l'assiette). Voie verticale
    sur le bord intérieur, accès dans la colonne gauche avec un étranglement `nw`, allée et place dedans."""
    from shapely.affinity import rotate
    ass = Polygon([(0, 0), (40, 0), (40, 12), (14, 12), (14, 28), (40, 28), (40, 40), (0, 40)])
    voie = LineString([(14, 16), (14, 24)])
    acc = unary_union([Polygon([(8, 16), (14.1, 16), (14.1, 24), (8, 24)]),                 # bouche (mord la voie)
                       Polygon([(7, 20 - nw / 2), (8, 20 - nw / 2), (8, 20 + nw / 2), (7, 20 + nw / 2)]),  # neck
                       Polygon([(0, 16), (7, 16), (7, 24), (0, 24)])])                        # corps
    allee = Polygon([(0, 8), (7, 8), (7, 16), (0, 16)])
    place = Polygon([(0, 2), (5, 2), (5, 8), (0, 8)])
    gs = [ass, voie, acc, allee, place]
    if rot:
        gs = [rotate(g, rot, origin=(20, 20)) for g in gs]
    ass, voie, acc, allee, place = gs
    return [allee], [place], 5.0, [acc], voie, ass


def test_fix12_assiette_concave_C_aucune_place():
    """Assiette en C (centroïde HORS de l'assiette) : la bande ne part plus dans le projet → l'étranglement de
    2 m n'est pas contourné. ZÉRO place, goulet ≈ 2 m, aux rotations 0°, 90°, 153°, 180°."""
    for rot in (0, 90, 153, 180):
        a, p, lr, ac, v, ass = _plan_C(2.0, rot)
        _manque, nb = C._desserte_core(a, p, lr, ac, v, C._PASSAGE_MIN_M, ass)
        g = C._largeur_min_desserte(a, p, lr, ac, v, ass)
        assert nb == 0 and abs(g - 2.0) <= 0.2, f"C rot {rot}° : nb={nb}, goulet={g:.2f} (attendu 0 place, 2 m)"


def test_fix12_bande_toujours_hors_assiette():
    """La bande artificielle n'intersecte JAMAIS l'assiette (C, L, U, angle rentrant), à toute rotation."""
    from shapely.affinity import rotate
    formes = {
        "C": Polygon([(0, 0), (40, 0), (40, 12), (14, 12), (14, 28), (40, 28), (40, 40), (0, 40)]),
        "L": Polygon([(0, 0), (30, 0), (30, 10), (10, 10), (10, 30), (0, 30)]),
        "U": Polygon([(0, 0), (30, 0), (30, 30), (22, 30), (22, 8), (8, 8), (8, 30), (0, 30)]),
    }
    for nom, ass in formes.items():
        # un recouvrement sur CHAQUE arête du bord (y compris les angles rentrants)
        bord = ass.exterior
        for t in (0.05, 0.2, 0.37, 0.55, 0.73, 0.9):
            p0 = bord.interpolate(t, normalized=True)
            p1 = bord.interpolate(min(t + 0.03, 1.0), normalized=True)
            R = LineString([(p0.x, p0.y), (p1.x, p1.y)])
            band = _bande_moins_assiette(R, ass)
            inter = band.intersection(ass).area
            assert inter < 1e-6, f"{nom} t={t} : bande ∩ assiette = {inter:.4g} m² (attendu 0)"


def test_fix13_terrain_moins_profond_que_la_bande():
    """Terrain 11×9 (moins profond que la bande de 12 m), voie UNIQUEMENT devant, bouche 6 m, étranglement 2 m :
    le morceau de bande DERRIÈRE le terrain (qui ne touche aucune voie) n'est plus pris comme départ → la place
    n'est plus atteignable « par l'arrière ». ZÉRO place, goulet ≈ 2 m, à plusieurs orientations."""
    from shapely.affinity import rotate
    for rot in (0, 45, 90, 180):
        ass = Polygon([(0, 0), (11, 0), (11, 9), (0, 9)])
        voie = LineString([(-2, 9), (13, 9)])
        acc = unary_union([Polygon([(2.5, 8.9), (8.5, 8.9), (8.5, 9.1), (2.5, 9.1)]),            # bouche 6 m
                           Polygon([(4, 8.8), (6, 8.8), (6, 8.9), (4, 8.9)])])                     # étranglement 2 m
        allee = Polygon([(0, 0), (11, 0), (11, 8.8), (0, 8.8)])        # rejoint le FOND du terrain (y = 0)
        place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
        gs = [ass, voie, acc, allee, place]
        if rot:
            gs = [rotate(g, rot, origin=(5.5, 4.5)) for g in gs]
        ass, voie, acc, allee, place = gs
        _m, nb = C._desserte_core([allee], [place], 5.0, [acc], voie, C._PASSAGE_MIN_M, ass)
        g = C._largeur_min_desserte([allee], [place], 5.0, [acc], voie, ass)
        assert nb == 0 and abs(g - 2.0) <= 0.25, f"11×9 rot {rot}° : nb={nb}, goulet={g:.2f} (attendu 0, 2 m)"


def test_fix13_deux_voies_une_seule_porte_un_raccord():
    """Terrain bordé par DEUX voies (devant y=9 ET derrière y=0), mais seule celle de DEVANT porte un accès
    (raccord). La voie arrière ne borde aucune aire roulante → aucun recouvrement, aucun départ : la place reste
    desservie par le seul chemin réel (devant, étranglé à 2 m) → 0 place, goulet ≈ 2 m."""
    ass = Polygon([(0, 0), (11, 0), (11, 9), (0, 9)])
    voie = unary_union([LineString([(-2, 9), (13, 9)]), LineString([(-2, 0), (13, 0)])])
    acc = unary_union([Polygon([(2.5, 8.9), (8.5, 8.9), (8.5, 9.1), (2.5, 9.1)]),
                       Polygon([(4, 8.8), (6, 8.8), (6, 8.9), (4, 8.9)])])
    allee = Polygon([(0, 3), (11, 3), (11, 8.8), (0, 8.8)])           # NE touche PAS la voie arrière (y=0)
    place = Polygon([(0, 0), (2.5, 0), (2.5, 3), (0, 3)])
    _m, nb = C._desserte_core([allee], [place], 5.0, [acc], voie, C._PASSAGE_MIN_M, ass)
    g = C._largeur_min_desserte([allee], [place], 5.0, [acc], voie, ass)
    assert nb == 0 and abs(g - 2.0) <= 0.25, f"deux voies : nb={nb}, goulet={g:.2f} (attendu 0, 2 m)"


# FIX-14 — la MARGE DE 5 cm est supprimée. Sur une assiette concave, une poche derrière la voie (ici le réseau
# roulant MONTE jusqu'à la voie — recouvrement — mais l'ACCÈS ne la chevauche pas ; l'ancien code remplissait
# l'encoche côté projet et la gardait comme départ dès qu'elle était à ≤ 5 cm du recouvrement). Désormais la
# bande se construit d'un seul côté (extérieur) et SEULES les composantes que l'ACCÈS chevauche vraiment sont des
# départs : la poche n'est JAMAIS retenue, qu'elle soit à 4 cm ou à 5,1 cm. Reste le seul chemin réel (neck 2 m).
def _plan_poche(d, rot=0):
    """Accès réel étranglé à 2 m (goulet 2 m) + une poche de bypass derrière la voie, à `d` du recouvrement."""
    from shapely.affinity import rotate
    voie = LineString([(-5, 16), (35, 16)])
    bouche = Polygon([(22, 15.8), (28, 15.8), (28, 16.1), (22, 16.1)])        # accès mord la voie (6 m)
    neck = Polygon([(24, 12.9), (26, 12.9), (26, 15.9), (24, 15.9)])          # neck 2 m → chemin réel
    acc = unary_union([bouche, neck])
    wide = Polygon([(20, 2), (30, 2), (30, 13), (20, 13)])                    # allée large (dégagement place)
    lip = Polygon([(4, 15.9), (14, 15.9), (14, 16), (4, 16)])                 # réseau montant à la voie (x∈[4,14])
    conn = Polygon([(4, 2), (30, 2), (30, 5), (4, 5)])                        # connecteur bas (poche → allée large)
    allee = unary_union([wide, lip, conn])
    place = Polygon([(24, 2), (26.5, 2), (26.5, 7), (24, 7)])
    base = Polygon([(-5, -4), (35, -4), (35, 16), (-5, 16)])
    encoche = Polygon([(4, 5), (14, 5), (14, 16 - d), (4, 16 - d)])           # vide derrière la voie, bande `d`
    ass = base.difference(encoche)
    gs = [voie, acc, allee, place, ass]
    if rot:
        gs = [rotate(g, rot, origin=(15, 8)) for g in gs]
    voie, acc, allee, place, ass = gs
    nb = C._desserte_core([allee], [place], 5.0, [acc], voie, C._PASSAGE_MIN_M, ass)[1]
    g = C._largeur_min_desserte([allee], [place], 5.0, [acc], voie, ass)
    return nb, g


def test_fix14_poche_derriere_voie_jamais_depart():
    """La poche derrière la voie n'est JAMAIS un départ — à 4 cm comme à 5,1 cm (plus de marge de 5 cm), aux
    quatre orientations. Il reste le seul chemin réel (accès étranglé à 2 m) → 0 place, goulet ≈ 2 m partout."""
    for rot in (0, 90, 180, 270):
        for d in (0.04, 0.051):
            nb, g = _plan_poche(d, rot)
            assert nb == 0 and abs(g - 2.0) <= 0.25, \
                f"poche rot {rot}° d={d} : nb={nb}, goulet={g:.2f} (attendu 0 place, 2 m)"


# FIX-15 — le CÔTÉ de la bande vient du CONTOUR de l'assiette (sens de parcours), plus d'un point de test à
# 30 cm. Contre-exemple du relecteur : sur une assiette concave, le point à 30 cm tombait dans l'encoche (hors
# accès) → mauvais côté → la poche restante touchait l'accès LATÉRALEMENT et était retenue (1 place, 3,96 m).
# Désormais : 0 place, goulet ≈ 2 m (le seul chemin réel est l'accès étranglé à 2 m), à 4 cm comme à 5,1 cm.
def _plan_fix15(d, rot=0):
    from shapely.affinity import rotate
    from shapely.geometry import box
    assiette = box(0, 0, 11, 10).difference(box(2, d, 12, 4))
    acces = unary_union([box(0, -.04, 6, d), box(0, d, 2, 4)])
    allee = box(0, 4, 5, 9)
    place = box(5, 5, 10, 7.5)
    voie = LineString([(0, 0), (6, 0)])
    gs = [assiette, acces, allee, place, voie]
    if rot:
        gs = [rotate(g, rot, origin=(5, 5)) for g in gs]
    assiette, acces, allee, place, voie = gs
    nb = C._desserte_core([allee], [place], 5.0, [acces], voie, C._PASSAGE_MIN_M, assiette)[1]
    g = C._largeur_min_desserte([allee], [place], 5.0, [acces], voie, assiette)
    return nb, g


def test_fix15_cote_bande_par_le_contour_pas_point_de_test():
    """Contre-exemple du relecteur, repris tel quel, aux orientations 0/90/180/270 et à d = 0,04 puis 0,051 :
    le côté de la bande vient du contour de l'assiette → la poche n'est plus retenue → 0 place, goulet ≈ 2 m."""
    for rot in (0, 90, 180, 270):
        for d in (0.04, 0.051):
            nb, g = _plan_fix15(d, rot)
            assert nb == 0 and abs(g - 2.0) <= 0.25, \
                f"FIX-15 rot {rot}° d={d} : nb={nb}, goulet={g:.2f} (attendu 0 place, 2 m)"


# FIX-16 — le CONTOUR de l'assiette est un MUR, ouvert seulement au droit du recouvrement. Dans une assiette en
# C, la bande extérieure traverse l'encoche et rejoignait l'aire roulante par un AUTRE bord (faux raccord,
# goulet 6 m). Contre-exemple du relecteur repris tel quel.
def _plan_C16(rot=0):
    from shapely.affinity import rotate
    from shapely.geometry import box
    assiette = box(0, -20, 20, 20).difference(box(5, -5, 21, 5))
    acces = unary_union([box(6, 4.96, 12, 5.1), box(8, 5.1, 10, 10),
                         box(1, 6, 10, 8), box(1, -8, 3, 8), box(1, -8, 8, -6)])
    allee = box(5, -10, 15, -5)
    place = box(7, -15, 9.5, -10)
    voie = LineString([(6, 5), (12, 5)])
    gs = [assiette, acces, allee, place, voie]
    if rot:
        gs = [rotate(g, rot, origin=(10, 0)) for g in gs]
    assiette, acces, allee, place, voie = gs
    nb = C._desserte_core([allee], [place], 5.0, [acces], voie, C._PASSAGE_MIN_M, assiette)[1]
    g = C._largeur_min_desserte([allee], [place], 5.0, [acces], voie, assiette)
    return nb, g


def test_fix16_bande_ne_traverse_pas_l_encoche_assiette_C():
    """Contre-exemple du relecteur (assiette en C), aux orientations 0/90/180/270 ET à 30° : la bande extérieure
    ne franchit plus l'encoche pour rejoindre l'aire roulante par un autre bord → le vrai passage de 2 m n'est
    plus contourné → 0 place, goulet ≈ 2 m."""
    for rot in (0, 90, 180, 270, 30):
        nb, g = _plan_C16(rot)
        assert nb == 0 and abs(g - 2.0) <= 0.3, f"C16 rot {rot}° : nb={nb}, goulet={g:.2f} (attendu 0 place, 2 m)"


def test_fix16_allee_longe_la_voie_sans_acces_aucune_place():
    """Une allée LONGE la voie mais AUCUN accès ne la raccorde : le réseau roulant touche la voie, mais sans
    morsure d'accès le long du recouvrement → raccord NON établi → aucune place comptée."""
    voie = LineString([(0, 16), (20, 16)])
    allee = Polygon([(0, 11), (20, 11), (20, 16), (0, 16)])        # longe la voie (y = 16) mais n'est pas un accès
    place = Polygon([(2, 6), (4.5, 6), (4.5, 11), (2, 11)])
    acces = Polygon([(8, 11), (12, 11), (12, 13), (8, 13)])        # accès INTÉRIEUR, ne touche PAS la voie
    ass = Polygon([(-2, -2), (22, -2), (22, 16), (-2, 16)])
    nb = C._desserte_core([allee], [place], 5.0, [acces], voie, C._PASSAGE_MIN_M, ass)[1]
    assert nb == 0, f"allée longeant la voie sans accès : nb={nb} (attendu 0)"


# FIX-18 (règle 1) — si le recouvrement n'est PAS sur le bord de l'assiette (voie à l'intérieur : les deux
# lanières contiennent la même surface d'assiette, à la précision près), le raccord n'est pas établi.
def test_fix18_voie_interieure_a_l_assiette_pas_de_raccord():
    from shapely.geometry import box
    from shapely.affinity import rotate
    for rot in (0, 90, 180, 270):
        ass = box(0, 0, 20, 20)
        voie = LineString([(5, 10), (11, 10)])                 # voie À L'INTÉRIEUR de l'assiette
        acc = box(5, 9.9, 11, 12)                              # accès touchant la voie (6 m) mais intérieur
        allee = box(5, 12, 15, 15)
        place = box(6, 15, 8.5, 20)
        gs = [ass, voie, acc, allee, place]
        if rot:
            gs = [rotate(g, rot, origin=(10, 10)) for g in gs]
        ass, voie, acc, allee, place = gs
        nb = C._desserte_core([allee], [place], 5.0, [acc], voie, C._PASSAGE_MIN_M, ass)[1]
        assert nb == 0, f"voie intérieure rot {rot}° : nb={nb} (attendu 0, recouvrement hors bord)"


# FIX-18 (règle 2) — RÉSOLUTION au millimètre : 2,40 m accepté, 2,39 m et 2,35 m refusés (inchangés), à tous angles.
def test_fix18_largeur_ouverture_au_millimetre():
    from shapely.geometry import box
    from shapely.affinity import rotate

    def nb_ouverture(ow, rot):
        ass = box(0, 0, 12, 12)
        acc = box(6 - ow / 2, -0.04, 6 + ow / 2, 5.2)
        allee = box(1, 5, 11, 8)
        place = box(5.5, 8, 8, 13)
        voie = LineString([(0, 0), (12, 0)])
        gs = [ass, acc, allee, place, voie]
        if rot:
            gs = [rotate(g, rot, origin=(6, 6)) for g in gs]
        return C._desserte_core([gs[2]], [gs[3]], 5.0, [gs[1]], gs[4], C._PASSAGE_MIN_M, gs[0])[1]

    for rot in (0, 37, 90, 180, 270):
        assert nb_ouverture(2.40, rot) == 1, f"2,40 m rot {rot}° doit PASSER"
        assert nb_ouverture(2.39, rot) == 0, f"2,39 m rot {rot}° doit être REFUSÉ"
        assert nb_ouverture(2.35, rot) == 0, f"2,35 m rot {rot}° doit être REFUSÉ"


# FIX-11 (défaut 1) — le côté de la bande de voie est donné par l'ASSIETTE, jamais par les aires roulantes :
# une aire roulante isolée de l'AUTRE CÔTÉ de la voie ne retourne plus la bande (verdict stable, toute rotation).
def _plan_def1(nw, rot_deg=0, avec_aire_opposee=True):
    from shapely.affinity import rotate
    voie = LineString([(-5, 16), (20, 16)])
    acc = unary_union([Polygon([(0, 15.8), (6, 15.8), (6, 16.1), (0, 16.1)]),                # bouche 6 m
                       Polygon([(3 - nw / 2, 15.7), (3 + nw / 2, 15.7),
                                (3 + nw / 2, 15.8), (3 - nw / 2, 15.8)]),                      # étranglement nw
                       Polygon([(0, 10), (6, 10), (6, 15.7), (0, 15.7)])])                     # corps 6 m
    allee = Polygon([(-2, 5), (8, 5), (8, 10), (-2, 10)])
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    assiette = Polygon([(-5, 0), (10, 0), (10, 16), (-5, 16)])                                 # parcelle SOUS la voie
    aires = [allee] + ([Polygon([(10, 17), (16, 17), (16, 22), (10, 22)])] if avec_aire_opposee else [])
    geoms = [voie, acc, place, assiette] + aires
    if rot_deg:
        geoms = [rotate(g, rot_deg, origin=(2.5, 8)) for g in geoms]
    voie, acc, place, assiette = geoms[:4]
    aires = geoms[4:]
    nb = C._desserte_core(aires, [place], 5.0, [acc], voie, C._PASSAGE_MIN_M, assiette)[1]
    g = C._largeur_min_desserte(aires, [place], 5.0, [acc], voie, assiette)
    return nb, g


def test_defaut1_bande_cote_assiette_invariante_rotation():
    """Étranglement 2 m + une aire roulante isolée de l'autre côté de la voie : la bande reste du côté voie
    (donnée par l'assiette), le passage de 2 m n'est PAS contourné → 0 place, goulet 2 m, à toute rotation."""
    for rot in (0, 90, 153, 180):
        nb, g = _plan_def1(2.0, rot, avec_aire_opposee=True)
        assert nb == 0 and abs(g - 2.0) <= 0.2, f"rot {rot}° : nb={nb}, goulet={g:.2f} (attendu 0 place, 2 m)"
    # le verdict ne dépend QUE du chemin réel : l'aire opposée ne change rien.
    assert _plan_def1(2.0, 0, avec_aire_opposee=False)[0] == 0


# FIX-11 (défaut 2) — plus de redilatation : on teste la POSITION du véhicule (point d'approche devant le nez,
# à la demi-largeur, dans le noyau atteignable), pas la zone balayée.
def _plan_def2(nw, avant_allee, passage=5.0):
    voie = LineString([(-5, 16), (20, 16)])
    allee = Polygon([(-2, 5), (8, 5), (8, 10), (-2, 10)])
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    assiette = Polygon([(-5, 0), (10, 0), (10, 16), (-5, 16)])
    y0 = 10 + avant_allee
    y1 = y0 + 0.1                                                      # étranglement COURT (10 cm)
    acc = unary_union([Polygon([(0, y1), (6, y1), (6, 16.1), (0, 16.1)]),
                       Polygon([(3 - nw / 2, y0), (3 + nw / 2, y0), (3 + nw / 2, y1), (3 - nw / 2, y1)]),
                       Polygon([(0, 10), (6, 10), (6, y0), (0, y0)])])
    nb_passage = C._desserte_core([allee], [place], 5.0, [acc], voie, passage, assiette)[1]
    goulet = C._largeur_min_desserte([allee], [place], 5.0, [acc], voie, assiette)
    return nb_passage, goulet


def test_defaut2_disque_ne_depasse_plus_par_l_ouverture():
    """Accès 6 m, étranglement court de 4,70 m placé 10 cm / 50 cm / 2 m avant l'allée : le passage testé à 5 m
    est REFUSÉ (le disque ne « dépasse » plus par l'ouverture) et le goulet vaut 4,70 m, où que soit l'étranglement."""
    for avant in (0.1, 0.5, 2.0):
        nb5, goulet = _plan_def2(4.70, avant, passage=5.0)
        assert nb5 == 0, f"étranglement 4,70 m @{avant} m : passage 5 m accepté à tort (nb={nb5})"
        assert abs(goulet - 4.70) <= 0.2, f"étranglement 4,70 m @{avant} m : goulet {goulet:.3f} (attendu 4,70)"


def test_defaut2_etranglement_exactement_a_la_largeur_testee_passe():
    """Un étranglement EXACTEMENT à la largeur testée (5 m) laisse passer : le véhicule tient pile."""
    nb5, _ = _plan_def2(5.0, 0.5, passage=5.0)
    assert nb5 == 1


# FIX-9 (point 1) — chemin praticable continu décidé SANS rattachement par distance : une liaison plus étroite
# que la largeur de passage (qui s'évanouit à l'érosion) ne transmet aucun raccord.
def _lien(w):
    """Deux allées (A, raccordée à la voie par un accès de 3 m ; B, sans accès) reliées par une bande de
    largeur w. Place sous chaque allée. Seule A doit desservir sa place si la bande est < 2,40 m."""
    voie = LineString([(-5, 16), (25, 16)])
    al = Polygon([(0, 5), (8, 5), (8, 10), (0, 10)])
    ca = Polygon([(0, 10), (3, 10), (3, 16.1), (0, 16.1)])           # accès de A, mord la voie (3 m)
    pa = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    band = Polygon([(8, 7.5 - w / 2), (12, 7.5 - w / 2), (12, 7.5 + w / 2), (8, 7.5 + w / 2)])
    ar = Polygon([(12, 5), (20, 5), (20, 10), (12, 10)])
    pb = Polygon([(15, 0), (17.5, 0), (17.5, 5), (15, 5)])
    return C._pincement_allee([al, band, ar], [pa, pb], 5.0, [ca], voie, assiette=_ASS)


def test_lien_etroit_10cm_une_seule_place():
    """Liaison de 10 cm entre les deux réseaux : B ne reçoit AUCUN raccord (la bande s'évanouit à l'érosion) →
    seule la place de A est comptée."""
    assert 11.0 < _lien(0.10) < 14.0


def test_lien_235_une_seule_place():
    """Liaison de 2,35 m (< largeur de passage) : s'évanouit à l'érosion → seule la place de A est comptée."""
    assert 11.0 < _lien(2.35) < 14.0


def test_lien_240_deux_places():
    """Liaison de 2,40 m (= largeur de passage) : survit à l'érosion → B est RELIÉ à A, les deux places comptées."""
    assert _lien(2.40) <= C._DEGAGEMENT_SEUIL_M2



# ── point 2 : barème / citations à seuil de surface ─────────────────────────────────────────────
import labuse.implantation.regles as R          # noqa: E402
from labuse.implantation.service import _regle_stationnement_courte   # noqa: E402


class _Logt:
    def __init__(self, surf, pieces=2):
        self.surface_m2 = surf
        self.pieces = pieces
        self.libelle = None


def _formule(insee, zone, surf, n=20):
    b = R.charger(insee, zone).stationnement
    e = b.exiger([_Logt(surf) for _ in range(n)], destination="collectif", sdp_total=surf * n)
    return b, e.formule


def test_la_plaine_ambiguite_seulement_au_seuil_exact():
    """La Plaine Ub12.2 (1 place < 30 m², 1,5 ≥ 30 m²) : l'ambiguïté « X ou Y » n'apparaît QU'À 30 m² PILE.
    À 29,7 m² le texte est net (sous le seuil), aucune alternative affichée."""
    assert "AMBIGUË" not in _formule("97406", "UB", 29.7)[1]
    assert "AMBIGUË" not in _formule("97406", "UB", 31.0)[1]
    f30 = _formule("97406", "UB", 30.0)[1]
    assert "AMBIGUË" in f30 and "ou" in f30 and "prudente" in f30


def test_la_plaine_resume_court_montre_le_seuil():
    """Le résumé court de La Plaine affiche la RÈGLE À SEUIL, pas un « 1,5 place / logement » tronqué."""
    courte = _regle_stationnement_courte(R.charger("97406", "UB").stationnement)
    assert courte is not None and "< 30 m²" in courte and "≥ 30 m²" in courte


def test_bras_panon_1aud_ambiguite_a_100m2():
    """Bras-Panon 1AUd (« ≤ 100 m² » 1 place ET « ≥ 100 m² » 1,5 place, bornes inclusives) : à 100 m² PILE,
    les deux lectures sont données, la prudente retenue ; à 99/101 m², aucune ambiguïté."""
    assert "AMBIGUË" not in _formule("97402", "1AUd", 99.0)[1]
    assert "AMBIGUË" not in _formule("97402", "1AUd", 101.0)[1]
    f100 = _formule("97402", "1AUd", 100.0)[1]
    assert "AMBIGUË" in f100 and "ou" in f100 and "prudente" in f100


# ── point 3 : seuil « grand bâtiment » de la distance entre constructions ────────────────────────
def test_distance_seuil_grand_batiment():
    """Le Tampon Ua8.2 : 3 m en général, 6 m dès qu'un bâtiment dépasse 5 logements. `_distance_requise`
    applique le bon seuil selon le bâtiment le plus peuplé."""
    dc = R.DistanceConstructions(validee=True, forme="fixe", min_m=3.0,
                                 min_m_grand_batiment=6.0, seuil_logements_grand_batiment=5,
                                 article="Ua8.2", citation="…")

    class _Cap:
        niveaux = 2
    class _Conv:
        hauteur_etage_m = 3.0
    req5, lib5, _ = C._distance_requise(dc, _Cap(), _Conv(), max_logts_bati=5)
    req6, lib6, _ = C._distance_requise(dc, _Cap(), _Conv(), max_logts_bati=6)
    assert req5 == 3.0 and "aucun bâtiment > 5" in lib5
    assert req6 == 6.0 and "6 logements > 5" in lib6


# ── ETUDE-STATIONNEMENT-FIX-19 — les trois défauts du relecteur indépendant (relecture-stationnement-1.md),
#    chacun « place valable refusée » (faux négatif). Chaque cas Shapely du rapport devient un test. ─────────
from shapely.geometry import box as _box  # noqa: E402
from shapely.affinity import rotate as _rotate  # noqa: E402


def _rect(x0, y0, x1, y1):
    return _box(x0, y0, x1, y1)


def test_fix19_A_recouvrement_coude_voie_plusieurs_segments():
    """Défaut A — accès dans un angle du terrain / voie à plusieurs segments : `voie ∩ libre` est une ligne
    COUDÉE. Ne garder que les deux extrémités donnait une corde oblique fausse → place refusée. Désormais
    chaque TRONÇON DROIT ≥ passage est une ouverture : la place est desservie, voie droite OU coudée."""
    assiette = _rect(0, 0, 40, 40)
    acces = [_rect(-1, -1, 5, 6)]        # accès dans l'angle (0,0), mord la voie
    allee = [_rect(2, 5, 35, 10)]        # allée 5 m
    place = [_rect(10, 10, 12.5, 15)]    # nez sur l'allée
    voie_droite = LineString([(40, 0), (0, 0)])
    voie_coudee = LineString([(40, 0), (0, 0), (0, 40)])   # bord bas PUIS bord gauche
    assert C._desserte_core(allee, place, 5.0, acces, voie_droite, 2.4, assiette) == (0.0, 1)
    manque, nb = C._desserte_core(allee, place, 5.0, acces, voie_coudee, 2.4, assiette)
    assert nb == 1 and manque < 1e-6, f"voie coudée : place refusée à tort (manque={manque}, nb={nb})"


def test_fix19_A_troncons_droits_decoupe_la_polyligne():
    """Le découpage en tronçons droits sépare un recouvrement coudé en deux segments (un par bord)."""
    runs = C._troncons_droits(LineString([(5, 0), (0, 0), (0, 6)]))
    assert len(runs) == 2
    longs = sorted(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 for (ax, ay), (bx, by) in runs)
    assert abs(longs[0] - 5.0) < 1e-9 and abs(longs[1] - 6.0) < 1e-9
    # une ligne droite (même à trois points colinéaires) reste UN seul tronçon
    assert len(C._troncons_droits(LineString([(0, 0), (3, 0), (7, 0)]))) == 1


def test_fix19_B_rotation_quelconque_pas_de_scission():
    """Défaut B — pavés strictement jointifs (se touchent sans se chevaucher) : après rotation quelconque
    `unary_union` rendait un MultiPolygon, l'érosion scindait le réseau, la place refusée (67/180 angles à
    5 m). Nettoyée au mm (grille fine + fermeture 1 mm), la place est desservie à TOUTE rotation."""
    assiette = _rect(0, 0, 40, 40)
    voie = LineString([(0, 0), (40, 0)])
    acces = [_rect(10, -1, 15, 5)]       # accès 5 m ; bord haut y=5 JOUXTE l'allée
    allee = [_rect(5, 5, 35, 10)]
    place = [_rect(11, 10, 13.5, 15)]
    refus = []
    for ang in range(0, 180):
        Rf = lambda g, a=ang: _rotate(g, a, origin=(0, 0))
        nb = C._desserte_core([Rf(g) for g in allee], [Rf(g) for g in place], 5.0,
                              [Rf(g) for g in acces], Rf(voie), 2.4, Rf(assiette))[1]
        if nb < 1:
            refus.append(ang)
    assert refus == [], f"place refusée à {len(refus)} angles (ex. {refus[:8]}) — accès 5 m ≫ 2,40 m"


def test_fix19_C_bruit_sub_micronique_ne_scinde_pas_a_l_erosion():
    """Défaut C — un biseau de coordonnées de l'ordre de 1e-12 à la jonction accès↔allée (union pourtant
    en UN polygone) faisait scinder `buffer(-_er)` et refuser la place. Nettoyée au mm avant l'érosion, la
    place est desservie pour tout bruit sub-millimétrique (accès 4 m, étroit mais > 2,40 m)."""
    assiette = _rect(0, 0, 40, 40)
    voie = LineString([(0, 0), (40, 0)])
    allee = [_rect(5, 5, 35, 10)]
    place = [_rect(11, 10, 13.5, 15)]
    for eps in (0.0, 1e-12, 1e-9, 1e-6):
        acces = [Polygon([(10, -1), (14, -1), (14, 5 + eps), (10, 5 - eps)])]
        manque, nb = C._desserte_core(allee, place, 5.0, acces, voie, 2.4, assiette)
        assert nb == 1 and manque < 1e-6, f"eps={eps} : place refusée à tort (manque={manque}, nb={nb})"


def test_fix19_BC_la_fermeture_ne_ponte_jamais_un_vrai_vide():
    """La fermeture d'un millimètre (défauts B & C) NE RELIE PAS deux réseaux SÉPARÉS DE 2 cm : une place du
    réseau lointain, sans accès propre, reste REFUSÉE (contre-exemple du relecteur, à conserver)."""
    assiette = _rect(0, 0, 40, 40)
    voie = LineString([(0, 0), (40, 0)])
    acces = [_rect(10, -1, 15, 5)]
    proche = _rect(5, 5, 35, 10)
    lointain = _rect(5, 10.02, 35, 15)       # 2 cm de vide franc
    place = [_rect(11, 15, 13.5, 20)]         # nez sur le réseau LOINTAIN
    manque, nb = C._desserte_core([proche, lointain], place, 5.0, acces, voie, 2.4, assiette)
    assert nb == 0 and manque > 1.0, f"2 cm de vide pontés à tort (manque={manque}, nb={nb})"


def test_fix19_desserte_operation_contre_exemple_relecteur():
    """Contre-exemple du relecteur sur `_largeur_min_desserte` : une bouche de 6 m, UNE place juste derrière
    l'entrée (canal large), puis un RÉTRÉCISSEMENT à 3 m avant une allée qui dessert DOUZE autres places. Attendu :
    13 places comptées (toutes atteignables à 2,40 m) et une DESSERTE de 3 m (l'allée des 12 n'est atteinte qu'à
    3 m) → en ÉCHEC pour une exigence de 5 m. La desserte se mesure au niveau des ALLÉES desservant les places
    comptées, pas de la place la mieux desservie — l'ancienne lecture « ≥ 1 place » annonçait ~7,5 m (réussi à tort)."""
    assiette = _rect(-1, 0, 55, 22)
    voie = LineString([(-1, 0), (55, 0)])
    acces = [_rect(0, -0.5, 8, 2)]                                # bouche 8 m
    canal = _rect(0, 2, 8, 12)                                    # canal d'entrée large (sert la place 13)
    retrecissement = _rect(8, 4, 11, 7)                           # 3 m
    allee_arriere = _rect(11, 2, 50, 8)                           # sert les 12 places
    allees = [canal, retrecissement, allee_arriere]
    places = [_rect(2.5, 12, 5, 17)] + [_rect(12 + 3 * i, 8, 12 + 3 * i + 2.5, 13) for i in range(12)]
    nb = C._desserte_core(allees, places, 2.5, acces, voie, 2.4, assiette)[1]
    assert nb == 13, f"les 13 places doivent être comptées à 2,40 m (nb={nb})"
    desserte = C._largeur_min_desserte(allees, places, 2.5, acces, voie, assiette)
    assert 2.8 <= desserte <= 3.2, f"desserte = {desserte:.3f} m : doit valoir le rétrécissement 3 m (échec pour 5 m)"
    assert desserte < 5.0 - 0.05, "une exigence de 5 m doit ÉCHOUER sur cette desserte"


def test_fix19_desserte_deux_allees_dont_une_derriere_un_retrecissement():
    """Deux allées, chacune desservant des places comptées ; l'une est derrière un rétrécissement de 3 m. La
    desserte de l'opération = la plus SERRÉE des deux (3 m), pas la plus large."""
    assiette = _rect(-1, 0, 40, 20)
    voie = LineString([(-1, 0), (40, 0)])
    acces = [_rect(0, -0.5, 8, 2)]
    tronc = _rect(0, 2, 8, 9)                                     # tronc commun large (depuis la voie)
    allee_large = _rect(0, 9, 14, 12)                             # allée atteinte largement
    retro = _rect(8, 7, 11, 9)                                    # rétrécissement 3 m vers l'allée serrée
    allee_serree = _rect(11, 9, 34, 12)                           # allée atteinte seulement à 3 m
    allees = [tronc, allee_large, retro, allee_serree]
    places = [_rect(2, 12, 4.5, 17), _rect(14, 12, 16.5, 17), _rect(24, 12, 26.5, 17)]
    nb = C._desserte_core(allees, places, 2.5, acces, voie, 2.4, assiette)[1]
    assert nb == 3, f"les 3 places doivent être comptées (nb={nb})"
    desserte = C._largeur_min_desserte(allees, places, 2.5, acces, voie, assiette)
    assert 2.8 <= desserte <= 3.2, f"desserte = {desserte:.3f} m : la plus serrée des allées servantes (3 m)"


# ── ETUDE-STATIONNEMENT-FIX-20 — deux sur-estimations de la largeur de desserte (relecture-stationnement-2.md).
#    La largeur de desserte = MINIMUM sur les places comptées du plus grand passage où la place reste desservie
#    (même sonde que le comptage), SANS rattachement place→allée. ───────────────────────────────────────────────
def test_fix20_allee_plus_etroite_que_acces():
    """Défaut 1(a) du relecteur : une allée de 2,5 m pendue à une bouche d'accès de 6 m, place au fond. La jonction
    large allée↔accès faisait déclarer l'allée « atteinte » jusqu'à 5 m (`reach.intersects(allée)`). Le vrai passage
    vers la place au fond est 2,5 m (la largeur de l'allée). Variante accès 6 m / allée 5 m → 5,0 m."""
    assiette = _rect(0, 0, 60, 40)
    voie = LineString([(0, 0), (60, 0)])
    acces = [_rect(5, -1, 11, 6)]                         # bouche 6 m
    allee = [_rect(5, 5, 50, 7.5)]                        # allée 2,5 m, longue
    place = [_rect(40, 7.5, 42.5, 12.5)]                  # au fond, loin de l'accès
    assert C._desserte_core(allee, place, 5.0, acces, voie, 2.4, assiette)[1] == 1
    d = C._largeur_min_desserte(allee, place, 5.0, acces, voie, assiette)
    assert 2.4 <= d <= 2.6, f"desserte = {d:.3f} m : doit valoir l'allée 2,5 m, PAS la bouche 6 m"
    # variante allée 5 m / accès 6 m → 5,0 m
    d5 = C._largeur_min_desserte([_rect(5, 5, 50, 10)], [_rect(40, 10, 42.5, 15)], 5.0, acces, voie, assiette)
    assert 4.9 <= d5 <= 5.1, f"variante : desserte = {d5:.3f} m (allée 5 m)"


def test_fix20_pincement_au_milieu_dune_meme_allee():
    """Défaut 1(b) : un étranglement de 3 m AU MILIEU d'une allée d'UN SEUL polygone (large ailleurs). FIX-19 ne le
    voyait QUE si le pincement était un polygone séparé ; dans un polygone unique, `reach.intersects(allée)` restait
    vrai à 6 m. La mesure par place rend 3,0 m (le pincement), que le pincement soit séparé ou fusionné."""
    assiette = _rect(0, 0, 60, 40)
    voie = LineString([(0, 0), (60, 0)])
    acces = [_rect(5, -1, 11, 6)]
    place = [_rect(40, 11, 42.5, 16)]
    allee_fusion = [Polygon([(5, 5), (50, 5), (50, 11), (30, 11), (30, 8), (20, 8), (20, 11), (5, 11)])]
    d = C._largeur_min_desserte(allee_fusion, place, 5.0, acces, voie, assiette)
    assert 2.9 <= d <= 3.1, f"pincement fusionné : desserte = {d:.3f} m (doit valoir le pincement 3 m)"
    # pincement en polygone séparé : même résultat
    sep = [_rect(5, 5, 20, 11), Polygon([(20, 5), (30, 5), (30, 8), (20, 8)]), _rect(30, 5, 50, 11)]
    dsep = C._largeur_min_desserte(sep, place, 5.0, acces, voie, assiette)
    assert 2.9 <= dsep <= 3.1, f"pincement séparé : desserte = {dsep:.3f} m"


def test_fix20_place_accrochee_directement_a_l_acces():
    """Défaut 2 : une place dont le nez touche l'ACCÈS (pas une allée) était rattachée à une allée arbitraire ; son
    vrai trajet (par l'accès de 2,4 m) n'entrait jamais dans la recherche. Deux places comptées, mais la desserte de
    l'opération ≤ 2,4 m (la place sur l'accès n'est atteinte qu'à 2,4 m)."""
    assiette = _rect(0, 0, 70, 40)
    voie = LineString([(0, 0), (70, 0)])
    acces = [_rect(5, -1, 11, 6), _rect(55, -1, 57.4, 6)]     # un réseau large + un accès de 2,4 m
    allee = [_rect(5, 5, 40, 11)]
    places = [_rect(30, 11, 32.5, 16), _rect(55, 6, 57.4, 11)]  # place1 sur l'allée large, place2 sur l'accès 2,4 m
    assert C._desserte_core(allee, places, 5.0, acces, voie, 2.4, assiette)[1] == 2
    d = C._largeur_min_desserte(allee, places, 5.0, acces, voie, assiette)
    assert d <= 2.5, f"desserte = {d:.3f} m : la place sur l'accès 2,4 m borne l'opération (≤ 2,4 m)"


def test_fix20_plan_regulier_5m_reussit():
    """Un plan régulier (accès et allée de 5 m) donne 5,0 m et RÉUSSIT une exigence de 5 m."""
    assiette = _rect(0, 0, 60, 40)
    voie = LineString([(0, 0), (60, 0)])
    acces = [_rect(5, -0.5, 10, 5.3)]                    # accès 5 m
    allee = [_rect(2, 5, 40, 10)]                        # allée 5 m
    place = [_rect(12, 10, 14.5, 15), _rect(20, 10, 22.5, 15)]
    assert C._desserte_core(allee, place, 5.0, acces, voie, 2.4, assiette)[1] == 2
    d = C._largeur_min_desserte(allee, place, 5.0, acces, voie, assiette)
    assert 4.95 <= d <= 5.1, f"plan régulier : desserte = {d:.3f} m (doit valoir 5,0 m)"
    assert d >= 5.0 - 0.05, "une exigence de 5 m doit RÉUSSIR"


def test_fix20_desserte_angle_ouverture_large_couloir_etroit():
    """ETUDE-STATIONNEMENT-FIX-20 (relecture 2, correctif de SUR-ESTIMATION dans un angle). Accès en BLOC d'angle
    avec une OUVERTURE LARGE sur un bord (ici 7 m sur le bord gauche d'une voie coudée) mais un COULOIR ÉTROIT
    (3 m) vers la place. L'érosion de l'UNION (aire roulante ∪ bande de voie) laissait la bande combler
    l'étranglement PRÈS DE L'OUVERTURE et le noyau franchir un couloir plus étroit que `w` → desserte annoncée à
    la largeur de l'ouverture (~7 m) alors que la place n'est atteinte qu'à 3 m. Correctif : chaque tronçon est
    une ouverture séparée (sa propre bande, mur fermé à l'angle) ET le disque doit TENIR dans un VRAI couloir
    (aire roulante érodée OU bande, traversée de l'ouverture seule permise par la gorge) → desserte = 3 m.
    Le comptage à 2,40 m est INCHANGÉ (la place reste desservie)."""
    assiette = _rect(0, 0, 50, 40)
    voie = LineString([(50, 0), (0, 0), (0, 40)])        # coudée : bord bas PUIS bord gauche
    acces = [_rect(-1, -1, 3, 7)]                         # bloc d'angle : ouverture gauche 7 m, bas 3 m
    allee = [_rect(3, 3, 35, 6)]                          # couloir 3 m vers la place
    place = [_rect(28, 6, 30.5, 11)]                      # nez sur le couloir, au fond
    assert C._desserte_core(allee, place, 5.0, acces, voie, 2.4, assiette)[1] == 1, "place comptée à 2,40 m"
    d = C._largeur_min_desserte(allee, place, 5.0, acces, voie, assiette)
    assert 2.9 <= d <= 3.1, f"desserte = {d:.3f} m : doit valoir le couloir 3 m, PAS l'ouverture large (~7 m)"
    assert d < 5.0 - 0.05, "une exigence de 5 m doit ÉCHOUER (la place n'est desservie qu'à 3 m)"
