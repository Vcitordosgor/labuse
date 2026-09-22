"""GABARIT-5 lot B — le plan 2D du gabarit (SVG serveur), miroir du mini-plan React.

Pur : construit un GabaritResult servi depuis la fixture de démonstration (aucune DB) et vérifie
que le SVG porte les géométries, les couleurs et la légende attendues ; None quand rien à tracer.
"""
from __future__ import annotations

from labuse.gabarit.engine import compute_gabarit
from labuse.gabarit.fixtures import demo_gabarit_input
from labuse.gabarit.plan_svg import C_CONTOUR, C_RETRAIT, C_ZONE, gabarit_svg


def test_svg_servi_porte_geometries_et_legende():
    res = compute_gabarit(demo_gabarit_input())
    assert res.status == "ok"
    svg = gabarit_svg(res)
    assert svg and svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    # les couleurs des trois familles servies (zone / retrait / contour) sont présentes
    assert C_ZONE in svg and C_RETRAIT in svg and C_CONTOUR in svg
    # la légende dit explicitement que c'est un schéma, pas un plan de masse
    assert "pas un plan de masse" in svg
    assert "Zone d'implantation" in svg and "Contour cadastral" in svg
    # au moins un tracé fermé (chemin SVG)
    assert svg.count("<path") >= 2


def test_svg_none_si_aucune_geometrie():
    assert gabarit_svg({"contourGeoJSON": None, "zoneImplantationGeoJSON": None,
                        "retraitsGeoJSON": None, "exclusionsGeoJSON": None}) is None
    assert gabarit_svg({}) is None


def test_svg_accepte_dict_ou_objet():
    res = compute_gabarit(demo_gabarit_input())
    as_dict = {"contourGeoJSON": res.contourGeoJSON, "zoneImplantationGeoJSON": res.zoneImplantationGeoJSON,
               "retraitsGeoJSON": res.retraitsGeoJSON, "exclusionsGeoJSON": res.exclusionsGeoJSON}
    assert gabarit_svg(as_dict) and gabarit_svg(res)
