"""GABARIT-3D-1 (pilote, étape 1 ter) — tests SCÈNE, MAILLAGE, PLANCHES, bloc PDF (révision Astra).

PUR (sans PostgreSQL) : maillage triangulé (maille non plane ≠ bilinéaire ; plan → pente constante),
lacune propagée, modèle bâti (hauteur null si non attribuée), planches (cadre tenu, aucun plafond,
une cote par point, thèmes). Un test `local` : lecture pixel-native (A1), invariant chiffres, état séparé,
déterminisme, parcelle multi-morceaux.
"""
from __future__ import annotations

import math
import os
import re

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from labuse.gabarit import scene as SC
from labuse.gabarit.terrain_mesh import TerrainMesh
from labuse.gabarit.coupe_svg import coupe_svg, plan_cle_svg, _runs, _soustraire
from labuse.exports.blocs import gabarit as BL


def _plan_mesh(n=60, gx=0.12, gy=-0.05, z0=100.0, hole=None):
    x0, y0 = 1000.0, 2000.0
    tr = from_origin(x0, y0 + n, 1.0, 1.0)
    jj, ii = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    cx, cy = rasterio.transform.xy(tr, jj.ravel().tolist(), ii.ravel().tolist())
    cx = np.array(cx).reshape(n, n); cy = np.array(cy).reshape(n, n)
    z = (z0 + gx * (cx - x0) + gy * (cy - y0)).astype("float64")
    if hole:
        z[:, hole[0]:hole[1]] = np.nan
    return TerrainMesh(z, x0, y0 + n, 1.0), (x0, y0, n, gx, gy)


# ── A2 : maillage triangulé (maille non plane ≠ bilinéaire ; plan → pente constante) ───────────────

def test_maille_non_plane_suit_la_triangulation():
    # maille 0,0,0,4 : triangulé = 2 (face), bilinéaire = 1
    m = TerrainMesh(np.array([[0.0, 0.0], [0.0, 4.0]]), ox=0.0, oy=2.0, pas=1.0)
    assert abs(m.altitude(1.0, 1.0) - 2.0) < 1e-9        # pas 1.0 (bilinéaire)


def test_coupe_oblique_pente_constante():
    m, (x0, y0, n, gx, gy) = _plan_mesh()
    ux, uy = math.cos(math.radians(37)), math.sin(math.radians(37))
    zs = [m.altitude(x0 + 10.3 + ux * d, y0 + 8.7 + uy * d) for d in range(30)]
    pentes = [(zs[i + 1] - zs[i]) * 100 for i in range(len(zs) - 1)]
    assert max(pentes) - min(pentes) < 1e-6              # un plan reste un plan
    assert abs(sum(pentes) / len(pentes) - (gx * ux + gy * uy) * 100) < 1e-6


def test_maillage_lacune_propagee():
    m, (x0, y0, n, *_1) = _plan_mesh(hole=(20, 25))
    yr = y0 + n - (n // 2 + 0.5)
    assert m.altitude(x0 + 22.5, yr) is None
    assert m.altitude(x0 + 5.5, yr) is not None


def test_faces_bornees_et_valides():
    m, (x0, y0, n, *_1) = _plan_mesh(hole=(20, 25))
    f = m.faces(x0, y0 + n, bounds=(x0 + 5, y0 + n - 15, x0 + 15, y0 + n - 5))
    assert f["triangles"] and len(f["vertices"]) < n * n   # borné, pas toute la fenêtre
    assert all(len(t) == 3 for t in f["triangles"])


# ── trous + bâti (modèle revu) ─────────────────────────────────────────────────────────────────────

def test_polys_local_conserve_trous():
    from shapely.geometry import Polygon
    p = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], holes=[[(3, 3), (7, 3), (7, 7), (3, 7)]])
    polys = SC._polys_local(p, 0, 0)
    assert len(polys) == 1 and len(polys[0]["trous"]) == 1


def _gr_batis(sources):
    import types

    def poly(ox, src):
        return {"type": "Feature", "properties": {"hauteur_m": (10.0 if src else None), "h_source": src},
                "geometry": {"type": "Polygon", "coordinates": [[[55.45 + ox, -20.88], [55.45 + ox + 1e-4, -20.88],
                             [55.45 + ox + 1e-4, -20.8799], [55.45 + ox, -20.8799], [55.45 + ox, -20.88]]]}}
    fc = {"type": "FeatureCollection", "features": [poly(i * 2e-4, s) for i, s in enumerate(sources)]}
    return types.SimpleNamespace(batiExistantGeoJSON=fc)


class _SamplerNul:
    def altitude(self, x, y):
        return 10.0


def test_bati_attribution_et_hauteur_null():
    # règle « une seule emprise » RETIRÉE : plusieurs LiDAR → tous attribués ; pas de source → null
    b = SC._batiments(_gr_batis(["lidar", "lidar"]), _SamplerNul(), 0, 0)
    assert len(b) == 2 and all(x["attribution"] == "lidar" and x["hauteur_m"] == 10.0 for x in b)
    assert all(x["pied_m"] == 10.0 for x in b)           # pied conventionnel
    nul = SC._batiments(_gr_batis([None]), _SamplerNul(), 0, 0)
    assert nul[0]["attribution"] is None and nul[0]["hauteur_m"] is None   # plus de 3,0 arbitraire


# ── indicateurs : pente max 5 m à deux bornes, hors bâti ±1 m ─────────────────────────────────────

def test_pente_max_5m_deux_bornes_hors_bati():
    profil = [{"d": float(i), "z": round(100 + 0.1 * i, 3)} for i in range(21)]
    ind = SC._indicateurs(profil, parcelle_spans=[[0.0, 20.0]], bati_spans=[[8.0, 12.0]], voie=None)
    pm = ind["pente_max_5m"]
    assert pm["disponible"] and "d0" in pm and "d1" in pm
    assert not (7.0 <= pm["d0"] <= 13.0 and 7.0 <= pm["d1"] <= 13.0)   # fenêtre hors bâti ±1 m


def test_pente_acces_seulement_si_continu():
    profil = [{"d": float(i), "z": (None if i == 5 else 1.0 * i)} for i in range(15)]
    voie = {"etablie": True, "intersection_d": 2.0}
    ind = SC._indicateurs(profil, [[8.0, 14.0]], [], voie)
    assert ind["pente_acces_pct"] is None                # lacune à 5 → pas de pente d'accès


def test_soustraire_emprise():
    assert _soustraire((0, 10), [(3, 5)]) == [(0, 3), (5, 10)]


# ── planches : cadre tenu, aucun plafond, une cote par point, thèmes ──────────────────────────────

def _coupe_demo(attribution="lidar", plat=False, zone=True):
    profil = [{"d": float(i), "z": (100.0 if plat else round(100 + 0.2 * i, 2))} for i in range(40)]
    b = {"d0": 10.0, "d1": 18.0, "facade_amont_m": profil[10]["z"], "facade_aval_m": profil[18]["z"],
         "pied_m": profil[14]["z"], "hauteur_m": (7.0 if attribution else None), "attribution": attribution}
    return {"label": "A", "titre": "Coupe A-A′ — pente dominante", "voie": None, "longueur_m": 39.0,
            "profil": profil, "limites_parcelle_d": [[2.0, 37.0]],
            "zone_implantation_d": [[8.0, 22.0]] if zone else [], "zone_presente": zone,
            "batiments": [b],
            "indicateurs": SC._indicateurs(profil, [[2.0, 37.0]], [[10.0, 18.0]], None),
            "cotes": SC._stats_coupe(profil),
            "cotes_points": {"points": [{"d": 2.0, "z": profil[2]["z"], "role": "limite"},
                                        {"d": 37.0, "z": profil[37]["z"], "role": "limite"},
                                        {"d": 10.0, "z": profil[10]["z"], "role": "facade"}]}}


def _hors_cadre(svg, w, h, tol=1.0):
    faute = []
    for attr, lim in (("x", w), ("cx", w), ("x1", w), ("x2", w), ("y", h), ("cy", h), ("y1", h), ("y2", h)):
        for m in re.finditer(rf'\b{attr}="(-?\d+\.?\d*)"', svg):
            if not (-tol <= float(m.group(1)) <= lim + tol):
                faute.append((attr, float(m.group(1))))
    for m in re.finditer(r'points="([^"]+)"', svg):
        for pair in m.group(1).split():
            xx, yy = pair.split(",")
            if not (-tol <= float(xx) <= w + tol and -tol <= float(yy) <= h + tol):
                faute.append(("pt", pair))
    return faute


def test_coupe_svg_cadre_sans_plafond_faitage():
    svg = coupe_svg(_coupe_demo(), theme="clair", width=960, scene_id="abc123", adresse="12 Rue X")
    assert svg and svg.startswith("<svg")
    h = int(re.search(r'height="(\d+)"', svg).group(1))
    assert _hors_cadre(svg, 960, h) == []                # rien ne déborde (B6/B9)
    assert "H = V" in svg and svg.count("IGN 1989") == 0   # datum porté par la mention, pas répété
    assert "plafond" not in svg.lower()
    assert "emprise bâtie" in svg                         # emprise au sol (B5)
    assert "Hauteur au faîtage estimée par LiDAR" in svg and "7,0 m" in svg   # mention à part
    assert "scène abc123" in svg and "12 Rue X" in svg    # en-tête (B9)


def test_bati_non_attribue_sans_faitage():
    svg = coupe_svg(_coupe_demo(attribution=None), theme="sombre")
    assert "emprise bâtie" in svg
    assert "Hauteur au faîtage" not in svg               # hauteur null → pas de mention


def test_implantation_band_etats():
    assert "non traversée" not in coupe_svg(_coupe_demo(zone=True), theme="clair")  # zone traversée
    svg = coupe_svg(_coupe_demo(zone=False), theme="clair")
    assert "indisponible" in svg                         # pas de zone → indisponible


def test_themes_clair_sombre_fond():
    assert 'background:#0f1115' in coupe_svg(_coupe_demo(), theme="sombre")
    assert 'background:#ffffff' in coupe_svg(_coupe_demo(), theme="clair")


def test_bati_plat_toit_cadre():
    svg = coupe_svg(_coupe_demo(plat=True), theme="clair")
    h = int(re.search(r'height="(\d+)"', svg).group(1))
    assert _hors_cadre(svg, 960, h) == []


def test_coupe_svg_none_si_vide():
    assert coupe_svg({"label": "A", "titre": "x", "longueur_m": 5.0,
                      "profil": [{"d": 0.0, "z": None}, {"d": 1.0, "z": None}],
                      "limites_parcelle_d": [], "zone_implantation_d": [], "batiments": [],
                      "indicateurs": {}, "cotes": {"disponible": False}, "cotes_points": {"points": []}}) is None


def test_plan_cle_nord_axes_voie():
    scene = {"contour_cadastral": [{"ext": [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]], "trous": []}],
             "zone_implantation": [], "batiments": [],
             "axes_plan": {"A": {"label": "A", "p0": [0, 10], "p1": [20, 10]}},
             "coupes": [{"voie": {"etablie": True, "point_local": [10, 10]}}]}
    svg = plan_cle_svg(scene, theme="clair")
    assert svg and ">N<" in svg and ">A<" in svg and "A′" in svg and ">voie<" in svg


# ── bloc PDF gated ────────────────────────────────────────────────────────────────────────────────

def test_bloc_pdf_gated():
    scene = {"disponible": True, "scene_id": "x", "adresse": "y",
             "contour_cadastral": [{"ext": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], "trous": []}],
             "zone_implantation": [], "batiments": [], "axes_plan": {"A": {"label": "A", "p0": [0, 5], "p1": [10, 5]}},
             "coupes": [_coupe_demo()]}
    assert "coupes3d" not in BL.rendu({}, {"gabarit": None})
    html = BL.rendu({}, {"gabarit": None, "scene3d": scene})
    assert "coupes3d" in html and "Coupe A" in html


# ── locks sur base réelle ─────────────────────────────────────────────────────────────────────────

@pytest.mark.local
def test_locks_scene_base_reelle():
    url = os.environ.get("LABUSE_REEL_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url or "labuse_test" in url:
        pytest.skip("base réelle requise")
    from labuse.config import get_settings
    if not get_settings().mnt1m_cog_file.exists():
        pytest.skip("fond 1 m absent")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from labuse.api.gabarit import gabarit_detail
    from labuse.gabarit.terrain_mesh import TerrainMesh as TM
    eng = create_engine(url)
    # A1 — lecture pixel-native : même cote entre deux cadrages
    s1 = SC.charger_surface(336600, 7689700, 336680, 7689800, marge=40)
    s2 = SC.charger_surface(336600, 7689700, 336680, 7689800, marge=180)
    z1 = TM(s1.a, s1.ox, s1.oy, s1.pas).altitude(336637, 7689754)
    z2 = TM(s2.a, s2.ox, s2.oy, s2.pas).altitude(336637, 7689754)
    assert z1 is not None and z1 == z2
    idu = "97411000BZ1065"
    SC._MEMO.clear()
    with Session(eng) as db:
        gr = gabarit_detail(idu, db)
        s = SC.build_scene(db, idu)
    assert s.regles["zoneImplantationM2"] == gr.zoneImplantationM2         # chiffres identiques
    assert s.regles["hauteurReglementaireM"] == gr.hauteurReglementaireM
    assert set(s.etat) >= {"gabarit", "terrain_couverture", "coupes"}       # état séparé
    if s.disponible:
        assert s.etat["terrain_couverture"] > 0.5                           # parcelle couverte
    # déterminisme : rebuild après purge → même identifiant
    SC._MEMO.clear(); SC._open_cog.cache_clear()
    with Session(eng) as db:
        s2b = SC.build_scene(db, idu)
    assert s2b.scene_id == s.scene_id
