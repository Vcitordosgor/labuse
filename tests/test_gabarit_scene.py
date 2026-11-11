"""GABARIT-3D-1 (pilote, étape 1 bis) — tests SCÈNE, COUPES, bloc PDF (révision Astra).

PUR (sans PostgreSQL) : surface de référence bilinéaire (coupe oblique = pente constante), trous
conservés, indicateurs par traversée, rendu SVG (cadre tenu, aucun plafond, thèmes), déterminisme.
Un test `local` vérifie, si la base réelle et le fond sont présents, que la scène ne change AUCUN
chiffre servi et expose l'état séparément.
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
from labuse.gabarit.scene import SurfaceReference
from labuse.gabarit.coupe_svg import coupe_svg, plan_cle_svg, _runs, _lacunes
from labuse.exports.blocs import gabarit as BL


def _plan_surface(n=60, gx=0.12, gy=-0.05, z0=100.0, hole=None):
    x0, y0 = 1000.0, 2000.0
    tr = from_origin(x0, y0 + n, 1.0, 1.0)
    jj, ii = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    cx, cy = rasterio.transform.xy(tr, jj.ravel().tolist(), ii.ravel().tolist())
    cx = np.array(cx).reshape(n, n); cy = np.array(cy).reshape(n, n)
    z = (z0 + gx * (cx - x0) + gy * (cy - y0)).astype("float64")
    if hole:
        z[:, hole[0]:hole[1]] = np.nan
    return SurfaceReference(z, x0, y0 + n, 1.0), (x0, y0, n, gx, gy, z0)


# ── A2 : surface bilinéaire → coupe oblique décalée des centres = pente constante ──────────────────

def test_coupe_oblique_pente_constante():
    surf, (x0, y0, n, gx, gy, _) = _plan_surface()
    ux, uy = math.cos(math.radians(37)), math.sin(math.radians(37))
    zs = [surf.altitude(x0 + 10.3 + ux * d, y0 + 8.7 + uy * d) for d in range(30)]
    pentes = [(zs[i + 1] - zs[i]) * 100 for i in range(len(zs) - 1)]
    attendu = (gx * ux + gy * uy) * 100
    assert max(pentes) - min(pentes) < 1e-6           # plan reproduit exactement
    assert abs(sum(pentes) / len(pentes) - attendu) < 1e-6


def test_surface_lacune_propagee():
    surf, (x0, y0, n, *_1) = _plan_surface(hole=(20, 25))
    yr = y0 + n - (n // 2 + 0.5)
    assert surf.altitude(x0 + 22.5, yr) is None        # appui dans le trou → lacune
    assert surf.altitude(x0 + 5.5, yr) is not None


# ── trous et parties multiples conservés ──────────────────────────────────────────────────────────

def test_polys_local_conserve_trous():
    from shapely.geometry import Polygon
    p = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], holes=[[(3, 3), (7, 3), (7, 7), (3, 7)]])
    polys = SC._polys_local(p, 0, 0)
    assert len(polys) == 1 and len(polys[0]["trous"]) == 1
    assert len(polys[0]["ext"]) == 5


# ── indicateurs par traversée : pente signée + amplitude séparément ; lacune coupe ────────────────

def test_indicateurs_par_traversee():
    profil = [{"d": float(i), "z": (None if 10 <= i < 14 else round(100 + 0.1 * i, 3))} for i in range(21)]
    ind = SC._indicateurs(profil, parcelle_spans=[[0.0, 20.0]], bati_spans=[], voie=None)
    assert len(ind["traversees"]) == 2                 # la lacune coupe la traversée en deux
    for tr in ind["traversees"]:
        assert tr["sens"] == "montée" and tr["pente_pct"] == pytest.approx(10.0, abs=0.3)
    assert ind["pente_max_5m"]["disponible"]


def test_stats_et_runs_lacune():
    profil = [{"d": float(i), "z": (None if i in (3, 4) else 1.0 * i)} for i in range(8)]
    assert len(_runs(profil)) == 2
    assert _lacunes(profil) == [(3.0, 5.0)]
    assert SC._stats_coupe(profil)["n_lacune"] == 2


# ── rendu SVG : cadre tenu, aucun plafond, datum une fois, thèmes ─────────────────────────────────

def _coupe_demo(bati_mesure=True, plat=False):
    profil = [{"d": float(i), "z": (100.0 if plat else round(100 + 0.2 * i, 2))} for i in range(40)]
    b = {"d0": 10.0, "d1": 18.0, "hauteur_m": 7.0, "provenance": "mesurée (LiDAR)" if bati_mesure else "estimée (BD TOPO)",
         "cotee": bati_mesure, "pied_amont_m": profil[10]["z"], "pied_aval_m": profil[18]["z"]}
    return {"label": "A", "titre": "Coupe A-A′ — pente dominante", "voie": None, "longueur_m": 39.0,
            "profil": profil, "limites_parcelle_d": [[2.0, 37.0]], "zone_implantation_d": [[8.0, 22.0]],
            "batiments": [b],
            "indicateurs": SC._indicateurs(profil, [[2.0, 37.0]], [[10.0, 18.0]], None),
            "cotes": SC._stats_coupe(profil),
            "cotes_points": {"points": [{"d": 2.0, "z": profil[2]["z"], "role": "limite"},
                                        {"d": 37.0, "z": profil[37]["z"], "role": "limite"}]}}


def _coords_hors_cadre(svg, w, h, tol=1.0):
    faute = []
    for attr, lim in (("x", w), ("cx", w), ("x1", w), ("x2", w), ("y", h), ("cy", h), ("y1", h), ("y2", h)):
        for m in re.finditer(rf'\b{attr}="(-?\d+\.?\d*)"', svg):
            v = float(m.group(1))
            if v < -tol or v > lim + tol:
                faute.append((attr, v))
    for m in re.finditer(r'points="([^"]+)"', svg):
        for pair in m.group(1).split():
            xx, yy = pair.split(",")
            if not (-tol <= float(xx) <= w + tol and -tol <= float(yy) <= h + tol):
                faute.append(("pt", pair))
    return faute


def test_coupe_svg_cadre_sans_plafond_datum():
    svg = coupe_svg(_coupe_demo(), theme="clair", width=960)
    assert svg and svg.startswith("<svg")
    h = int(re.search(r'height="(\d+)"', svg).group(1))
    assert _coords_hors_cadre(svg, 960, h) == []       # rien ne déborde (B6)
    assert "H = V" in svg and svg.count("IGN 1989") == 1   # échelle + datum une fois (B7/B11)
    assert "plafond" not in svg.lower()                # aucun plafond de hauteur dessiné
    assert "mesurée (LiDAR)" in svg                    # bâti coté car mesuré


def test_bati_plat_toit_cadre():
    """Recette D : un bâtiment sur coupe plate dont le toit reste dans le cadre."""
    svg = coupe_svg(_coupe_demo(plat=True), theme="clair")
    h = int(re.search(r'height="(\d+)"', svg).group(1))
    assert _coords_hors_cadre(svg, 960, h) == []


def _gr_batis(n, source="lidar", hauteur=10.0):
    import types

    def poly(ox):
        return {"type": "Feature", "properties": {"hauteur_m": hauteur, "h_source": source},
                "geometry": {"type": "Polygon", "coordinates": [[[55.45 + ox, -20.88], [55.45 + ox + 1e-4, -20.88],
                             [55.45 + ox + 1e-4, -20.8799], [55.45 + ox, -20.8799], [55.45 + ox, -20.88]]]}}
    fc = {"type": "FeatureCollection", "features": [poly(i * 2e-4) for i in range(n)]}
    return types.SimpleNamespace(batiExistantGeoJSON=fc)


def test_bati_cote_seulement_si_un_seul_batiment():
    """Faîtage LiDAR par PARCELLE : coté « mesurée » si 1 bâti ; « hauteur non attribuée » si plusieurs."""
    un = SC._batiments(_gr_batis(1), None, 0, 0)
    assert len(un) == 1 and un[0]["cotee"] is True and un[0]["provenance"] == "mesurée (LiDAR)"
    plusieurs = SC._batiments(_gr_batis(3), None, 0, 0)
    assert len(plusieurs) == 3
    assert all(b["cotee"] is False and b["provenance"] == "hauteur non attribuée" for b in plusieurs)
    assert all(b["schematique"] for b in plusieurs)


def test_bati_estime_non_cote():
    svg = coupe_svg(_coupe_demo(bati_mesure=False), theme="sombre")
    assert "estimée (BD TOPO)" in svg                  # mention du volume schématique
    assert "7,0 m ·" not in svg                        # mais AUCUNE cote chiffrée de toiture
    assert "polygon" in svg


def test_themes_clair_sombre():
    for th in ("clair", "sombre"):
        svg = coupe_svg(_coupe_demo(), theme=th)
        assert svg and "H = V" in svg


def test_coupe_svg_none_si_vide():
    assert coupe_svg({"label": "A", "titre": "x", "longueur_m": 5.0,
                      "profil": [{"d": 0.0, "z": None}, {"d": 1.0, "z": None}],
                      "limites_parcelle_d": [], "zone_implantation_d": [], "batiments": [],
                      "indicateurs": {}, "cotes": {"disponible": False},
                      "cotes_points": {"points": []}}) is None


def test_plan_cle_nord_axes_et_cadastre():
    scene = {"contour_cadastral": [{"ext": [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]], "trous": []}],
             "zone_implantation": [], "batiments": [],
             "axes_plan": {"A": {"label": "A", "p0": [0, 10], "p1": [20, 10]}}}
    svg = plan_cle_svg(scene, theme="clair")
    assert svg and ">N<" in svg and ">A<" in svg and "A′" in svg


# ── bloc PDF gated (document par défaut inchangé) ─────────────────────────────────────────────────

def test_bloc_pdf_gated():
    scene = {"disponible": True, "contour_cadastral": [{"ext": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], "trous": []}],
             "zone_implantation": [], "batiments": [], "axes_plan": {"A": {"label": "A", "p0": [0, 5], "p1": [10, 5]}},
             "coupes": [_coupe_demo()]}
    assert "coupes3d" not in BL.rendu({}, {"gabarit": None})
    html = BL.rendu({}, {"gabarit": None, "scene3d": scene})
    assert "coupes3d" in html and "Coupe A" in html


# ── invariant chiffres + état séparé (base réelle, sinon ignoré) ──────────────────────────────────

@pytest.mark.local
def test_scene_invariant_chiffres_et_etat():
    url = os.environ.get("LABUSE_REEL_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url or "labuse_test" in url:
        pytest.skip("base réelle requise")
    from labuse.config import get_settings
    if not get_settings().mnt1m_cog_file.exists():
        pytest.skip("fond 1 m absent")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from labuse.api.gabarit import gabarit_detail
    eng = create_engine(url)
    idu = "97411000BZ1065"
    with Session(eng) as db:
        gr = gabarit_detail(idu, db)
        s = SC.build_scene(db, idu)
    assert s.regles["zoneImplantationM2"] == gr.zoneImplantationM2
    assert s.regles["plafondEmpriseM2"] == gr.plafondEmpriseM2
    assert s.regles["hauteurReglementaireM"] == gr.hauteurReglementaireM
    # état séparé ; jamais « disponible » avec des grilles vides
    assert set(s.etat) >= {"gabarit", "terrain_couverture", "coupes"}
    if s.disponible:
        assert s.etat["terrain_couverture"] > 0.0
    # déterminisme : rebuild après purge du cache → même identifiant
    SC._open_cog.cache_clear()
    with Session(eng) as db:
        s2 = SC.build_scene(db, idu)
    assert s2.scene_id == s.scene_id
