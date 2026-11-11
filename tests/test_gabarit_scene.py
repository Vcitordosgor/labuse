"""GABARIT-3D-1 (pilote) — tests de la SCÈNE, des COUPES et du bloc PDF gated.

Essentiel PUR (sans PostgreSQL) : exactitude de l'échantillonnage sur un plan incliné synthétique,
segmentation des cotes aux lacunes, rendu SVG (échelle 1:1, aucun plafond dessiné), gating du PDF.
Un test marqué `local` vérifie, si la base RÉELLE et le fond 1 m sont présents, que la scène ne change
AUCUN chiffre servi par le Gabarit (invariant « chiffres identiques »).
"""
from __future__ import annotations

import os

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from labuse.gabarit import scene as SC
from labuse.gabarit.coupe_svg import _lacunes, _runs, coupe_svg, plan_cle_svg
from labuse.exports.blocs import gabarit as BL


# ── plan incliné synthétique : exactitude de l'échantillonnage (contrôle a) ────────────────────────

def _synth_cog(tmp_path, gx=0.10, gy=-0.04, z0=100.0, n=80, hole=(40, 45)):
    x0, y0 = 300000.0, 7650000.0
    tr = from_origin(x0, y0 + n, 1.0, 1.0)
    jj, ii = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    cx, cy = rasterio.transform.xy(tr, jj.ravel().tolist(), ii.ravel().tolist())
    cx = np.array(cx).reshape(n, n); cy = np.array(cy).reshape(n, n)
    z = (z0 + gx * (cx - x0) + gy * (cy - y0)).astype("float32")
    z[:, hole[0]:hole[1]] = -9999.0
    p = tmp_path / "synth.tif"
    with rasterio.open(p, "w", driver="GTiff", height=n, width=n, count=1, dtype="float32",
                       crs="EPSG:2975", transform=tr, nodata=-9999.0) as dst:
        dst.write(z, 1)
    return p, (x0, y0, n, gx, gy, z0)


def test_sample_points_exact_sur_plan(tmp_path, monkeypatch):
    p, (x0, y0, n, gx, gy, z0) = _synth_cog(tmp_path, hole=(40, 45))
    ds = rasterio.open(p)
    monkeypatch.setattr(SC, "_cog", lambda: ds)
    jrow = n // 2
    cx, cy = rasterio.transform.xy(ds.transform, [jrow] * n, list(range(n)))
    vals = SC.sample_points(list(zip(cx, cy)))
    for i in range(n):
        if cx[i] is None:
            continue
        z_attendu = z0 + gx * (cx[i] - x0) + gy * (cy[i] - y0)
        if 40 <= i < 45:                      # bande lacune
            assert vals[i] is None
        else:
            assert vals[i] is not None and abs(vals[i] - z_attendu) < 1e-3


def test_cotes_interrompues_par_la_lacune():
    # profil : 10 m de plan à 10 %, trou de 3 m, puis 10 m à 10 %
    profil = [{"d": float(i), "z": (None if 10 <= i < 13 else round(100 + 0.1 * i, 3))} for i in range(21)]
    runs = _runs(profil)
    assert len(runs) == 2                                   # la lacune coupe en deux morceaux
    assert _lacunes(profil) == [(10.0, 13.0)]
    st = SC._stats_coupe(profil)
    assert st["n_lacune"] == 3
    assert st["pente_moyenne_pct"] == pytest.approx(10.0, abs=0.2)   # calculée PAR morceau
    # la pente ne « saute » jamais la lacune : dénivelé = somme des morceaux, pas 100→113
    assert st["denivele_positif_m"] == pytest.approx(0.1 * (9 + 7), abs=0.05)


def test_stats_vides_si_tout_lacune():
    profil = [{"d": float(i), "z": None} for i in range(5)]
    assert SC._stats_coupe(profil) == {"disponible": False}


# ── rendu SVG : échelle 1:1, aucun plafond de hauteur dessiné ──────────────────────────────────────

def _coupe_demo():
    profil = [{"d": float(i), "z": round(100 + 0.2 * i, 2)} for i in range(30)]
    return {"label": "A", "titre": "Coupe A-A' — test", "voie": None, "longueur_m": 29.0,
            "profil": profil, "limites_parcelle_d": [[2.0, 27.0]],
            "zone_implantation_d": [[8.0, 20.0]],
            "batiments": [{"d0": 10.0, "d1": 15.0, "hauteur_m": 6.0, "provenance": "mesurée", "base_alt_m": 102.0}],
            "cotes": SC._stats_coupe(profil)}


def test_coupe_svg_echelle_1_1_et_sans_plafond():
    svg = coupe_svg(_coupe_demo())
    assert svg and svg.startswith("<svg")
    assert "échelle 1:1" in svg                 # H = V, pas d'exagération
    assert "mesurée" in svg                      # bâtiment coupé avec provenance
    # aucun plafond réglementaire de hauteur n'est dessiné (mandat : mandat suivant)
    assert "plafond" not in svg.lower()


def test_coupe_svg_none_si_profil_vide():
    assert coupe_svg({"label": "A", "titre": "x", "longueur_m": 5.0,
                      "profil": [{"d": 0.0, "z": None}, {"d": 1.0, "z": None}],
                      "limites_parcelle_d": [], "zone_implantation_d": [], "batiments": [],
                      "cotes": {"disponible": False}}) is None


def test_plan_cle_svg_reporte_les_axes():
    scene = {"parcelle": [[[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]]],
             "zone_implantation": [[[4, 4], [16, 4], [16, 16], [4, 16], [4, 4]]],
             "axes_plan": {"A": {"p0": [0, 10], "p1": [20, 10]}, "B": {"p0": [10, -5], "p1": [10, 20]}}}
    svg = plan_cle_svg(scene)
    assert svg and ">A<" in svg and "A′" in svg and ">B<" in svg   # A, A′, B reportés


# ── bloc PDF : gating (le document par défaut ne change pas) ───────────────────────────────────────

def test_bloc_pdf_gated_sur_scene3d():
    scene = {"disponible": True, "parcelle": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
             "zone_implantation": [], "axes_plan": {"A": {"p0": [0, 5], "p1": [10, 5]}},
             "coupes": [_coupe_demo()]}
    assert "coupes3d" not in BL.rendu({}, {"gabarit": None})               # sans → inchangé
    html = BL.rendu({}, {"gabarit": None, "scene3d": scene})
    assert "coupes3d" in html and "Coupe A" in html                        # avec → coupes présentes


def test_bloc_pdf_vide_si_scene_indisponible():
    assert BL._bloc_coupes_pilote({"disponible": False, "coupes": []}) == ""


# ── invariant « chiffres identiques » (base réelle + fond, sinon ignoré) ────────────────────────────

@pytest.mark.local
def test_scene_ne_change_aucun_chiffre_servi():
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
        sc = SC.build_scene(db, idu)
    assert sc.regles["zoneImplantationM2"] == gr.zoneImplantationM2
    assert sc.regles["plafondEmpriseM2"] == gr.plafondEmpriseM2
    assert sc.regles["hauteurReglementaireM"] == gr.hauteurReglementaireM
    assert sc.regles["surfaceParcelleM2"] == gr.surfaceParcelleM2
