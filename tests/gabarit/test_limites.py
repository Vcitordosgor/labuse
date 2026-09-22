"""GABARIT-2 lot E — classification des limites v2, cœur PUR (aucune DB).

Géométries synthétiques en mètres (le cœur est agnostique du CRS). Couvre les cas 1-5 du
mandat + drapeau/enclave, rue cadastrée, ravine.
"""
from __future__ import annotations

from collections import Counter

from shapely.geometry import LineString, Polygon

from labuse.gabarit.limites import Road, classify_edges, summarize_edges

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


def test_entree_non_mutee():
    before = SQUARE.wkt
    classify_edges(SQUARE, [], [Road(LineString([(-5, -3), (25, -3)]), None)])
    assert SQUARE.wkt == before
