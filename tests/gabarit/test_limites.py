"""GABARIT-2 lot E — classification des limites v2, cœur PUR (aucune DB).

Géométries synthétiques en mètres (le cœur est agnostique du CRS). Couvre les cas 1-5 du
mandat + drapeau/enclave, rue cadastrée, ravine.
"""
from __future__ import annotations

from collections import Counter

from shapely.geometry import LineString, Polygon

from labuse.gabarit.limites import (
    MOTIF_ARETE_COURTE,
    MOTIF_NON_QUALIFIEE,
    Edge,
    Road,
    _attach_residual_microedges,
    _nonclass_motif,
    classify_edges,
    elongation_from_obb,
    is_private_road_parcel,
    summarize_edges,
)

# parcelle carrée 20 × 20 m ; arêtes : bas y=0, droite x=20, haut y=20, gauche x=0
SQUARE = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])


def _types(edges):
    return Counter(e.type for e in edges)


def test_cas1_voie_par_proximite_route():
    # route parallèle au bas, à 3 m sous l'arête (défaut 4 m → seuil 2 + 3,5 = 5,5) → bas = voie
    road = Road(LineString([(-5, -3), (25, -3)]), None)
    edges = classify_edges(SQUARE, [], [road])
    assert any(e.type == "voie" for e in edges)
    # les trois autres arêtes n'ont ni voisin ni route → non classées
    assert any(e.type == "nonclass" for e in edges)


def test_cas2_voie_par_parcelle_voirie():
    # voisin collé au bas, marqué parcelle de voirie → bas = voie, même sans axe fourni
    voirie = (Polygon([(0, -8), (20, -8), (20, 0), (0, 0)]), True)
    edges = classify_edges(SQUARE, [voirie], [])
    assert any(e.type == "voie" for e in edges)


def test_cas3_separative_voisin_reel():
    # voisin bâti collé à gauche (pas voirie), aucune route → gauche = séparative
    voisin = (Polygon([(-8, 0), (0, 0), (0, 20), (-8, 20)]), False)
    edges = classify_edges(SQUARE, [voisin], [])
    assert any(e.type in ("side", "rear") for e in edges)
    assert not any(e.type == "voie" for e in edges)


def test_cas4_non_classee_sans_voie_ni_voisin():
    edges = classify_edges(SQUARE, [], [])
    assert all(e.type == "nonclass" for e in edges)
    assert all(e.motif for e in edges if e.type == "nonclass")


def test_cas5_side_vs_rear():
    # bas = voie (route), gauche+droite = séparatives touchant la voie (side), haut = rear
    road = Road(LineString([(-5, -3), (25, -3)]), None)
    gauche = (Polygon([(-8, 0), (0, 0), (0, 20), (-8, 20)]), False)
    droite = (Polygon([(20, 0), (28, 0), (28, 20), (20, 20)]), False)
    haut = (Polygon([(0, 20), (20, 20), (20, 28), (0, 28)]), False)
    edges = classify_edges(SQUARE, [gauche, droite, haut], [road])
    t = _types(edges)
    assert t["voie"] >= 1 and t["side"] >= 1 and t["rear"] >= 1


def test_rue_cadastree_axe_dans_emprise_prime_sur_voisin():
    # centre-ville : voisin RÉEL collé au bas MAIS l'axe carrossable est sur la limite (≤ largeur/2)
    # → l'arête est DANS l'emprise → voie (correction GABARIT-1→2), pas séparative
    voisin_bas = (Polygon([(0, -8), (20, -8), (20, 0), (0, 0)]), False)  # non détecté parcelle-voirie
    axe = Road(LineString([(-5, 0), (25, 0)]), 4.0)  # axe sur y=0, largeur 4 → emprise ±2 m
    edges = classify_edges(SQUARE, [voisin_bas], [axe])
    assert any(e.type == "voie" for e in edges)


def test_route_derriere_voisin_ne_fait_pas_facade():
    # route à 4 m derrière un voisin réel collé (au-delà de largeur/2=2) → séparative, pas voie
    voisin_bas = (Polygon([(0, -8), (20, -8), (20, 0), (0, 0)]), False)
    route = Road(LineString([(-5, -4), (25, -4)]), 4.0)  # d≈4 > 2 (emprise) → pas road_on
    edges = classify_edges(SQUARE, [voisin_bas], [route])
    bas = [e for e in edges if e.geom.centroid.y < 1]
    assert bas and all(e.type in ("side", "rear") for e in bas)


def test_drapeau_enclave_sans_facade():
    # parcelle close par des voisins sur les 4 côtés, aucune route → sans façade → bloc
    nbrs = [
        (Polygon([(0, -8), (20, -8), (20, 0), (0, 0)]), False),
        (Polygon([(20, 0), (28, 0), (28, 20), (20, 20)]), False),
        (Polygon([(0, 20), (20, 20), (20, 28), (0, 28)]), False),
        (Polygon([(-8, 0), (0, 0), (0, 20), (-8, 20)]), False),
    ]
    res = summarize_edges(classify_edges(SQUARE, nbrs, []))
    assert not res.has_voie
    assert res.blocking and "sans façade" in res.blocking


def test_ravine_arete_non_qualifiee_bloque():
    # bas = voie ; les 3 autres arêtes ouvertes sur une ravine (ni voisin ni route) → non qualifiées → bloc
    road = Road(LineString([(-5, -3), (25, -3)]), None)
    res = summarize_edges(classify_edges(SQUARE, [], [road]))
    assert res.has_voie
    assert res.blocking and "non qualifiées" in res.blocking


def test_parcelle_complete_servie():
    # façade + séparatives sur 3 côtés, rien de non classé → servie (pas de blocage)
    road = Road(LineString([(-5, -3), (25, -3)]), None)
    nbrs = [
        (Polygon([(20, 0), (28, 0), (28, 20), (20, 20)]), False),
        (Polygon([(0, 20), (20, 20), (20, 28), (0, 28)]), False),
        (Polygon([(-8, 0), (0, 0), (0, 20), (-8, 20)]), False),
    ]
    res = summarize_edges(classify_edges(SQUARE, nbrs, [road]))
    assert res.has_voie and res.blocking is None
    assert not res.non_classees


def test_emprise_publique_arete_ouverte():
    # arête ouverte (ni voisin ni route) : nonclass par défaut, VOIE (emprise publique) si la citation couvre
    edges_off = classify_edges(SQUARE, [], [])
    assert all(e.type == "nonclass" for e in edges_off)
    edges_on = classify_edges(SQUARE, [], [], emprises_publiques=True)
    assert edges_on and all(e.type == "voie" for e in edges_on)
    assert all(e.source_kind == "emprise_publique" for e in edges_on if e.type == "voie")


def test_marge_p2_frontage_en_retrait():
    # route parallèle au bas : à 5,6 m (≤ 4/2 + 4 = 6) → voie ; à 7 m → hors portée
    proche = Road(LineString([(-5, -5.6), (25, -5.6)]), None)
    loin = Road(LineString([(-5, -7.0), (25, -7.0)]), None)
    assert any(e.type == "voie" and e.source_kind == "bdtopo" for e in classify_edges(SQUARE, [], [proche]))
    assert not any(e.type == "voie" for e in classify_edges(SQUARE, [], [loin]))   # 7 m > 6 m → hors portée


def test_entree_non_mutee():
    before = SQUARE.wkt
    classify_edges(SQUARE, [], [Road(LineString([(-5, -3), (25, -3)]), None)])
    assert SQUARE.wkt == before


# --------------------------------------------------------------- voie privée (GABARIT-5, E2)

def test_elongation_rectangle_allonge():
    # rectangle 100 × 10 : périmètre 220, aire 1000 → L/l = 10
    assert round(elongation_from_obb(220.0, 1000.0), 1) == 10.0
    # carré 10 × 10 : périmètre 40, aire 100 → L/l = 1
    assert round(elongation_from_obb(40.0, 100.0), 1) == 1.0
    assert elongation_from_obb(0, 0) is None


def test_private_road_trois_criteres_chacun_insuffisant_seul():
    ok = dict(has_bati=False, elongation=8.0, width_m=3.0, touches_road=True, axis_len_inside_m=0.0)
    assert is_private_road_parcel(**ok)                             # tous réunis → voie privée
    assert not is_private_road_parcel(**{**ok, "has_bati": True})   # bâti → non
    assert not is_private_road_parcel(**{**ok, "elongation": 3.0})  # trapue (L/l < 5) → non
    assert not is_private_road_parcel(**{**ok, "width_m": 10.0})    # large (lot, pas un chemin) → non
    assert not is_private_road_parcel(**{**ok, "touches_road": False})   # non raccordée au réseau → non
    assert not is_private_road_parcel(**{**ok, "axis_len_inside_m": 20.0})  # axe la traverse → voirie, non
    assert not is_private_road_parcel(**{**ok, "elongation": None})       # allongement inconnu → non
    assert not is_private_road_parcel(**{**ok, "width_m": None})          # largeur inconnue → non


def test_voie_privee_servie_si_citation():
    # une parcelle de voie privée collée au bas (hors neighbors/roads BD TOPO) → voie SI citation
    priv = Polygon([(0, -8), (20, -8), (20, 0), (0, 0)])
    off = classify_edges(SQUARE, [], [], private_roads=[priv], voies_privees=False)
    assert not any(e.type == "voie" for e in off)
    assert any(e.type == "nonclass" and "voie privée" in (e.motif or "") for e in off)
    on = classify_edges(SQUARE, [], [], private_roads=[priv], voies_privees=True)
    bas = [e for e in on if e.geom.centroid.y < 1]
    assert bas and all(e.type == "voie" and e.source_kind == "voie_privee" for e in bas)


def test_voie_privee_non_couverte_bloque():
    # frontage privé non couvert par la citation → non qualifié → summarize bloque avec le motif
    priv = Polygon([(0, -8), (20, -8), (20, 0), (0, 0)])
    res = summarize_edges(classify_edges(SQUARE, [], [], private_roads=[priv], voies_privees=False))
    assert res.blocking and "voie privée" in res.blocking


# --------------------------------------------------------------- micro-arêtes résiduelles (GABARIT-6)

def _seg(a, b) -> LineString:
    return LineString([a, b])


def test_nonclass_motif_selon_longueur_fusionnee():
    # GABARIT-6 (a) : le motif suit la VRAIE longueur, jamais le premier chunk.
    assert _nonclass_motif(0.6) == MOTIF_ARETE_COURTE            # < 1 m → résiduelle
    assert _nonclass_motif(2.26) == MOTIF_NON_QUALIFIEE          # ≥ 1 m → limite non qualifiée (BZ1065)
    assert _nonclass_motif(1.0) == MOTIF_NON_QUALIFIEE           # borne : 1,0 m n'est pas « < 1 m »


def test_microarete_helper_rattachee_chunk_court():
    # une arête nonclass all_short de 0,6 m (< 2 % du périmètre 160) → rattachée à la plus longue
    # voisine (la voie 40 m), héritage type + source.
    rings = [[(0, 0), (40, 0), (40, 40), (0, 40)]]  # périmètre 160 → 2 % = 3,2 m
    edges = [
        Edge(_seg((0, 0), (40, 0)), "voie", 40.0, None, "bdtopo", ring=0),
        Edge(_seg((40, 0), (40, 0.6)), "nonclass", 0.6, MOTIF_ARETE_COURTE, None, ring=0, all_short=True),
        Edge(_seg((40, 0.6), (40, 10.6)), "side", 10.0, None, None, ring=0),
        Edge(_seg((40, 10.6), (0, 40)), "rear", 50.0, None, None, ring=0),
    ]
    assert _attach_residual_microedges(edges, rings) == 1
    micro = edges[1]
    assert micro.attached is True and micro.motif is None
    assert micro.type == "voie" and micro.source_kind == "bdtopo"  # voisine la plus longue = la voie 40 m


def test_microarete_helper_run_multichunk_rattache():
    # GABARIT-6 (b) : un run nonclass de 2,26 m composé UNIQUEMENT de chunks < 1 m (all_short) et
    # < 2 % du périmètre est un artefact (ré-entrance finement numérisée, cas 3 Chemin de la Citerne)
    # → rattaché, MÊME si sa longueur fusionnée ≥ 1 m.
    rings = [[(0, 0), (60, 0), (60, 60), (0, 60)]]  # périmètre 240 → 2 % = 4,8 m
    edges = [
        Edge(_seg((0, 0), (60, 0)), "voie", 60.0, None, "bdtopo", ring=0),
        Edge(_seg((60, 0), (60, 2.26)), "nonclass", 2.26, MOTIF_NON_QUALIFIEE, None, ring=0, all_short=True),
        Edge(_seg((60, 2.26), (60, 60)), "voie", 57.74, None, "bdtopo", ring=0),
        Edge(_seg((60, 60), (0, 60)), "rear", 60.0, None, None, ring=0),
    ]
    assert _attach_residual_microedges(edges, rings) == 1
    assert edges[1].attached is True and edges[1].type == "voie" and edges[1].source_kind == "bdtopo"


def test_microarete_helper_garde_zero_faux_voie_hors_portee():
    # GARDE 0 FAUX : donneuse = voie BD TOPO, mais l'artefact n'est PAS à portée d'une route
    # (road_near renvoie False) → rattaché en SÉPARATIVE, jamais en voie (pas de fausse façade).
    rings = [[(0, 0), (60, 0), (60, 60), (0, 60)]]  # 2 % = 4,8 m
    def edges():
        return [
            Edge(_seg((60, 0), (60, 27.93)), "voie", 27.93, None, "bdtopo", ring=0),
            Edge(_seg((60, 27.93), (60, 28.69)), "nonclass", 0.76, MOTIF_ARETE_COURTE, None, ring=0, all_short=True),
            Edge(_seg((60, 28.69), (60, 60)), "voie", 31.31, None, "bdtopo", ring=0),
        ]
    hors = edges()
    assert _attach_residual_microedges(hors, rings, road_near=lambda g: False) == 1
    assert hors[1].attached and hors[1].type == "side" and hors[1].source_kind is None
    # à portée d'une route → la voie est légitime, héritée telle quelle
    ok = edges()
    assert _attach_residual_microedges(ok, rings, road_near=lambda g: True) == 1
    assert ok[1].attached and ok[1].type == "voie" and ok[1].source_kind == "bdtopo"


def test_microarete_helper_run_court_mais_2pct_bloque():
    # all_short mais ≥ 2 % du périmètre (parcelle minuscule, l'arête pèse) → reste bloquante.
    rings = [[(0, 0), (10, 0), (10, 10), (0, 10)]]  # périmètre 40 → 2 % = 0,8 m
    edges = [
        Edge(_seg((0, 0), (10, 0)), "voie", 10.0, None, "bdtopo", ring=0),
        Edge(_seg((10, 0), (10, 0.9)), "nonclass", 0.9, MOTIF_ARETE_COURTE, None, ring=0, all_short=True),
        Edge(_seg((10, 0.9), (0, 10)), "rear", 20.0, None, None, ring=0),
    ]
    assert _attach_residual_microedges(edges, rings) == 0
    assert edges[1].type == "nonclass" and edges[1].attached is False


def test_microarete_helper_face_droite_non_qualifiee_bloque():
    # une face droite non qualifiée (chunks ≥ 1 m → all_short=False) n'est PAS un artefact : jamais
    # rattachée, même si < 2 % du périmètre. Bloque.
    rings = [[(0, 0), (60, 0), (60, 60), (0, 60)]]  # périmètre 240 → 2 % = 4,8 m
    edges = [
        Edge(_seg((0, 0), (60, 0)), "voie", 60.0, None, "bdtopo", ring=0),
        Edge(_seg((60, 0), (60, 4.0)), "nonclass", 4.0, MOTIF_NON_QUALIFIEE, None, ring=0, all_short=False),
        Edge(_seg((60, 4.0), (0, 60)), "rear", 80.0, None, None, ring=0),
    ]
    assert _attach_residual_microedges(edges, rings) == 0
    assert edges[1].type == "nonclass" and edges[1].attached is False


def test_microarete_bout_en_bout_mordu_court():
    # parcelle 40×40 desservie (route en bas), voisins gauche/droite/haut. Un « mordu » de 0,6 m sur le
    # côté droit → arête nonclass isolée entre deux séparatives : ne bloque pas, tracée (attached).
    parcel = Polygon([(0, 0), (40, 0),
                      (40, 19.7), (39.4, 19.7), (39.4, 20.3), (40, 20.3),   # mordu vers l'intérieur
                      (40, 40), (0, 40)])
    road = Road(LineString([(-5, -3), (45, -3)]), None)   # voie en bas
    nbrs = [
        (Polygon([(40, 0), (48, 0), (48, 40), (40, 40)]), False),      # droite (le mordu s'en écarte)
        (Polygon([(-8, 0), (0, 0), (0, 40), (-8, 40)]), False),        # gauche
        (Polygon([(0, 40), (40, 40), (40, 48), (0, 48)]), False),      # haut
    ]
    edges = classify_edges(parcel, nbrs, [road])
    res = summarize_edges(edges)
    assert res.blocking is None
    assert res.residual_attached >= 1
    assert not any(e.type == "nonclass" for e in edges)
    assert any(e.attached for e in edges)


def test_microarete_bout_en_bout_run_multimarches_ne_bloque_plus():
    # GABARIT-6 (b) bout-en-bout, cas 3 Chemin de la Citerne : une ré-entrance en ESCALIER de 5 marches
    # de 0,6 m (coins 90°, préservés par simplify) plonge sous le voisin haut → run nonclass de 3,0 m
    # entièrement composé de chunks < 1 m. < 2 % du périmètre (~402 m) → rattaché, la parcelle est servie.
    parcel = Polygon([(0, 0), (100, 0), (100, 100),
                      (51, 100), (51, 99.4), (50.4, 99.4), (50.4, 98.8), (49.8, 98.8),
                      (49.8, 99.4), (49.2, 99.4), (49.2, 100), (0, 100)])
    road = Road(LineString([(-5, -3), (105, -3)]), None)
    nbrs = [
        (Polygon([(-8, 0), (0, 0), (0, 100), (-8, 100)]), False),      # gauche
        (Polygon([(100, 0), (108, 0), (108, 100), (100, 100)]), False),  # droite
        (Polygon([(0, 100), (100, 100), (100, 108), (0, 108)]), False),  # haut (l'escalier s'en écarte)
    ]
    edges = classify_edges(parcel, nbrs, [road])
    res = summarize_edges(edges)
    assert res.blocking is None                     # servie : la ré-entrance ne bloque plus
    assert res.residual_attached == 1               # tracée
    assert not any(e.type == "nonclass" for e in edges)
    attached = [e for e in edges if e.attached]
    assert len(attached) == 1 and round(attached[0].length_m, 1) == 3.0
    assert attached[0].type in ("side", "rear")     # héritée de la voisine la plus longue (fond)


def test_microarete_bout_en_bout_run_multimarches_pese_bloque():
    # même escalier de 3,0 m mais sur une PETITE parcelle (30×30, périmètre ~123 → 2 % ≈ 2,46 m) :
    # 3,0 m ≥ 2 % → NON rattaché, la parcelle bloque, et (a) le motif dit « limite non qualifiée »
    # (longueur fusionnée 3,0 m ≥ 1 m), jamais « résiduelle < 1 m ».
    parcel = Polygon([(0, 0), (30, 0), (30, 30),
                      (16, 30), (16, 29.4), (15.4, 29.4), (15.4, 28.8), (14.8, 28.8),
                      (14.8, 29.4), (14.2, 29.4), (14.2, 30), (0, 30)])
    road = Road(LineString([(-5, -3), (35, -3)]), None)
    nbrs = [
        (Polygon([(-8, 0), (0, 0), (0, 30), (-8, 30)]), False),
        (Polygon([(30, 0), (38, 0), (38, 30), (30, 30)]), False),
        (Polygon([(0, 30), (30, 30), (30, 38), (0, 38)]), False),
    ]
    edges = classify_edges(parcel, nbrs, [road])
    res = summarize_edges(edges)
    assert res.blocking and "non qualifi" in res.blocking
    nc = [e for e in edges if e.type == "nonclass"]
    assert nc and nc[0].motif == MOTIF_NON_QUALIFIEE          # (a) : pas MOTIF_ARETE_COURTE
    assert res.residual_attached == 0


def test_voie_privee_ignoree_si_facade_publique():
    # parcelle DESSERVIE par une vraie voie (bas), voisin réel à gauche + fond, et un chemin privé à
    # droite : le chemin n'est qu'une limite séparative (pas de bloc, pas de régression sur le desservi).
    road = Road(LineString([(-5, -3), (25, -3)]), None)
    gauche = (Polygon([(-8, 0), (0, 0), (0, 20), (-8, 20)]), False)
    haut = (Polygon([(0, 20), (20, 20), (20, 28), (0, 28)]), False)
    priv = Polygon([(20, 0), (28, 0), (28, 20), (20, 20)])   # chemin privé collé au côté droit
    edges = classify_edges(SQUARE, [gauche, haut], [road], private_roads=[priv], voies_privees=False)
    res = summarize_edges(edges)
    assert res.has_voie and res.blocking is None
    assert not any(e.type == "nonclass" for e in edges)
    droite = [e for e in edges if e.geom.centroid.x > 19]
    assert droite and all(e.type in ("side", "rear") for e in droite)
