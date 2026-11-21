"""MOTEUR-VERITE-FIX-4 — tests PURS de la géométrie des limites (LOT 1).

Une limite séparative est un CÔTÉ du contour cadastral, partagé avec une parcelle voisine :
jamais une coupe interne, jamais une ligne hors du contour, jamais une polyligne qui fait le
tour. Le budget « une limite / deux limites » se compte sur ces côtés (`_split_cotes`).
Les cas parcellaires du relecteur (AE0114, AV1339, AH0074…) sont joués sur base réelle dans
tests/coherence_ecrans/test_moteur_verite_fix4.py.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon

from labuse.gabarit.limites import Edge, _split_cotes


def _edge(coords, type_="side"):
    line = LineString(coords)
    return Edge(line, type_, line.length)


def test_polyligne_en_l_se_coupe_en_deux_cotes():
    """Un angle franc (90°) sépare deux côtés : le budget « une limite » n'ouvre plus une
    polyligne qui réunit plusieurs côtés (AI1063 en réunissait trois). Le typage suit la
    définition de l'article : LATÉRALE = le côté ABOUTIT à la voie, FOND = le reste."""
    voie = _edge([(0, 0), (0, -5)], type_="voie")
    e = _edge([(0, 0), (10, 0), (10, 8)])
    parts = _split_cotes([voie, e])
    seps = [p for p in parts if p.type in ("side", "rear")]
    assert len(seps) == 2
    assert {round(p.length_m) for p in seps} == {10, 8}
    lat = next(p for p in seps if round(p.length_m) == 10)
    fond = next(p for p in seps if round(p.length_m) == 8)
    assert lat.type == "side"       # aboutit à la voie (extrémité (0,0))
    assert fond.type == "rear"      # ne touche pas la voie
    assert all(p.cadastrale for p in seps)


def test_ligne_droite_reste_un_cote():
    e = _edge([(0, 0), (5, 0.05), (10, 0.1)])   # quasi droite (bruit)
    parts = _split_cotes([e])
    assert len(parts) == 1


def test_coupe_interne_marquee_non_cadastrale():
    """Sur une portion multizone, un segment à plus de 1 m du contour cadastral réel est une
    COUPE INTERNE : séparé et marqué cadastrale=False (AE0114 : 16,3 m hors contour ouverts)."""
    cadastre = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)]).boundary
    # arête mixte : 10 m SUR le contour (y=0), puis 10 m en coupe interne (remonte à y=10)
    e = _edge([(0, 0), (10, 0), (10, 10)])
    parts = _split_cotes([e], cadastre)
    assert len(parts) == 2
    sur, coupe = sorted(parts, key=lambda p: not p.cadastrale)
    assert sur.cadastrale is True and round(sur.length_m) == 10
    assert coupe.cadastrale is False and round(coupe.length_m) == 10


def test_ligne_hors_contour_entierement_non_cadastrale():
    cadastre = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)]).boundary
    e = _edge([(5, 5), (15, 5)], type_="rear")      # entièrement intérieure
    parts = _split_cotes([e], cadastre)
    assert len(parts) == 1 and parts[0].cadastrale is False


def test_anneau_jamais_decoupe_garde_fix3():
    """Un contour fermé (anneau) n'est pas découpé en côtés : la garde FIX-3 (jamais posé en
    limite) reste entière (AH0293, AY0554, AH1368, AW0503)."""
    ring = LineString([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    e = Edge(ring, "rear", ring.length)
    parts = _split_cotes([e])
    assert len(parts) == 1 and parts[0].geom.is_ring


def test_types_non_separatifs_intacts():
    ev = _edge([(0, 0), (10, 0), (10, 8)], type_="voie")
    parts = _split_cotes([ev])
    assert len(parts) == 1 and parts[0] is ev
