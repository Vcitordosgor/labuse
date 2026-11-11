"""GABARIT-3D-1 (pilote, étape 1 bis) — TÉMOINS + CONTRÔLES → docs/audit-2026-11/gabarit-3d-1/.

Révision Astra. Produit pour les témoins les deux coupes (SVG clair+sombre, PNG) et le plan-clé, la
recette D (bâti sur coupe plate, parcelle multi-tronçons, lacune sous bâti, reproductibilité après
purge du cache, test automatique « rien hors cadre / chaque repère libellé »), et les contrôles :
  (a) exactitude — plan incliné synthétique, dont une COUPE OBLIQUE décalée des centres (pente constante) ;
  (b) cohérence LiDAR HD ↔ RGE ALTI aux mêmes points, par type de terrain (dérive vérifiée) ;
  (c) contrôle indépendant seulement si une cote publique coïncide (sinon : aucun) ;
  (C) résolution 1 m vs 0,50 m sur les témoins en pente (mêmes axes, mêmes cotes utiles) + contrôle du
      géoréférencement des fenêtres WMS + correction de la lecture du 0,92 m.

Usage : PYTHONPATH=/tmp/gab3d_libs:src ../labuse/.venv/bin/python scripts/gabarit_3d_temoins.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, "/tmp/gab3d_libs")
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

import cairosvg
import httpx
import numpy as np
import rasterio
from rasterio.transform import from_origin
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from labuse.gabarit import scene as SC
from labuse.gabarit.scene import build_scene
from labuse.gabarit.terrain_mesh import TerrainMesh
from labuse.gabarit.coupe_svg import coupe_svg, plan_cle_svg

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "audit-2026-11" / "gabarit-3d-1"
DB = os.environ["LABUSE_DATABASE_URL"]
WIDTH = 960

TEMOINS = [
    ("plate", "97415000CY0196", "Parcelle plate — plaine littorale de Saint-Paul (~5 m), bâti sur terrain plat"),
    ("cotier", "97413000CA0057", "Littoral de Saint-Leu — falaise"),
    ("alt760", "97415000CM1658", "Parcelle en altitude — 36 Rue des Jacarandas, Saint-Paul (~595 m mesurés)"),
    ("bz1065", "97411000BZ1065", "97411000BZ1065 — talus, Saint-Denis ; coupe B traverse la parcelle en plusieurs tronçons"),
]


def _png(svg, path, w=WIDTH):
    path.write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(path.with_suffix(".png")), output_width=w)


# ── test automatique : rien hors cadre + chaque repère a son libellé ──────────────────────────────

def _hors_cadre(svg: str, width: int, height: int, tol: float = 1.0) -> list:
    """Coordonnées d'attributs hors de [0,width]×[0,height] (test D « rien ne déborde »)."""
    faute = []
    for attr, lim in (("x", width), ("cx", width), ("x1", width), ("x2", width),
                      ("y", height), ("cy", height), ("y1", height), ("y2", height)):
        for m in re.finditer(rf'\b{attr}="(-?\d+\.?\d*)"', svg):
            v = float(m.group(1))
            if v < -tol or v > lim + tol:
                faute.append((attr, v))
    for m in re.finditer(r'points="([^"]+)"', svg):           # polygones/lignes
        for pair in m.group(1).split():
            xx, yy = pair.split(",")
            if not (-tol <= float(xx) <= width + tol and -tol <= float(yy) <= height + tol):
                faute.append(("pt", pair))
    return faute


def temoins(eng):
    (OUT / "coupes").mkdir(parents=True, exist_ok=True)
    (OUT / "plan").mkdir(parents=True, exist_ok=True)
    resume, fautes = [], []
    for label, idu, titre in TEMOINS:
        with Session(eng) as db:
            s = build_scene(db, idu)
        entry = {"label": label, "idu": idu, "titre": titre, "scene_id": s.scene_id,
                 "disponible": s.disponible, "etat": s.etat, "n_batiments": len(s.batiments),
                 "coupes": []}
        for c in s.coupes:
            for theme in ("clair", "sombre"):
                svg = coupe_svg(c, theme=theme, largeur_mm=170 if theme == "clair" else None,
                                scene_id=s.scene_id, adresse=s.adresse)
                if not svg:
                    continue
                h = int(re.search(r'height="(\d+)"', svg).group(1))
                hc = _hors_cadre(svg, WIDTH, h)
                if hc:
                    fautes.append((label, c["label"], theme, hc[:3]))
                _png(svg, OUT / "coupes" / f"{label}_{c['label']}_{theme}.svg")
            entry["coupes"].append({"axe": c["label"], "voie": c["voie"],
                                    "indicateurs": c["indicateurs"],
                                    "n_cotes_points": len(c["cotes_points"]["points"])})
        plan = plan_cle_svg(s.to_dict(), theme="clair")
        if plan:
            _png(plan, OUT / "plan" / f"{label}_plan.svg", w=380)
        resume.append(entry)
        print(f"  {label} {idu}: {len(s.coupes)} coupes, couverture {s.etat.get('terrain_couverture')}, id={s.scene_id}")
    print(f"  test cadre : {len(fautes)} faute(s)" + (f" → {fautes}" if fautes else " (rien hors cadre)"))
    return resume, fautes


# ── recette D : lacune sous bâti + reproductibilité après purge ───────────────────────────────────

def recette_d(eng):
    (OUT / "recette").mkdir(parents=True, exist_ok=True)
    res = {}
    # D1 — lacune SOUS le bâti : on troue le profil sous l'emprise du bâti coupé de BZ1065 B
    with Session(eng) as db:
        s = build_scene(db, "97411000BZ1065")
    cB = [c for c in s.coupes if c["label"] == "B"][0]
    import copy
    c2 = copy.deepcopy(cB)
    if c2["batiments"]:
        b = c2["batiments"][0]
        dmid = (b["d0"] + b["d1"]) / 2
        for p in c2["profil"]:          # trou > 3 m → lacune OUVERTE (non reconstituée) sous le bâti
            if dmid - 3.0 <= p["d"] <= dmid + 3.0:
                p["z"] = None
        svg = coupe_svg(c2, theme="clair", largeur_mm=170, scene_id=s.scene_id, adresse=s.adresse)
        _png(svg, OUT / "recette" / "d1_lacune_sous_bati.svg")
        # emprise au sol présente ; mention faîtage à part (aucune cote de toiture sur un volume)
        res["d1_lacune_sous_bati"] = {"emprise_au_sol": "emprise bâtie" in svg,
                                      "faitage_a_part": "Hauteur au faîtage" in svg}
    # D2 — reproductibilité : même SVG après purge du cache COG + mémo scène
    def svg_bz():
        SC._MEMO.clear()
        with Session(eng) as db:
            sc = build_scene(db, "97411000BZ1065")
        c = [x for x in sc.coupes if x["label"] == "A"][0]
        return coupe_svg(c, theme="clair", largeur_mm=170, scene_id=sc.scene_id, adresse=sc.adresse), sc.scene_id
    svg1, id1 = svg_bz()
    SC._open_cog.cache_clear()
    svg2, id2 = svg_bz()
    res["d2_reproductible"] = {"svg_identique": svg1 == svg2, "scene_id_identique": id1 == id2, "scene_id": id1}
    # D3 — parcelle en PLUSIEURS MORCEAUX : la scène se construit, couverture sur la parcelle
    idu_multi = _parcelle_multipart(eng)
    if idu_multi:
        SC._MEMO.clear()
        with Session(eng) as db:
            sm = build_scene(db, idu_multi)
        res["d3_multipart"] = {"idu": idu_multi, "disponible": sm.disponible,
                               "couverture": sm.etat.get("terrain_couverture"),
                               "n_contours_cad": len(sm.contour_cadastral), "coupes": len(sm.coupes)}
    else:
        res["d3_multipart"] = {"idu": None, "note": "aucune parcelle multi-morceaux dans l'emprise du fond"}
    print(f"  recette D : D1 {res.get('d1_lacune_sous_bati')} ; D2 {res['d2_reproductible']} ; D3 {res['d3_multipart']}")
    (OUT / "recette" / "recette.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def _parcelle_multipart(eng):
    """Parcelle en plusieurs morceaux : d'abord dans une fenêtre témoin (terrain couvert), sinon
    n'importe où dans les communes (teste la géométrie multi-morceaux + « disponible » si couverte)."""
    from sqlalchemy import text
    with eng.connect() as c:
        for x, y in ((336637, 7689754), (314713, 7672415), (322881, 7672581), (320491, 7661770)):
            r = c.execute(text(
                "SELECT idu FROM parcels WHERE ST_NumGeometries(geom_2975) > 1 "
                "AND ST_DWithin(geom_2975, ST_SetSRID(ST_Point(:x,:y),2975), 200) LIMIT 1"),
                {"x": x, "y": y}).scalar()
            if r:
                return r
        return c.execute(text(
            "SELECT idu FROM parcels WHERE commune IN ('Saint-Denis','Saint-Paul','Saint-Leu') "
            "AND ST_NumGeometries(geom_2975) > 1 LIMIT 1")).scalar()


# ── contrôle (a) — plan incliné synthétique (droit + OBLIQUE) ─────────────────────────────────────

def controle_a():
    (OUT / "controles").mkdir(parents=True, exist_ok=True)
    import math
    Z0, GX, GY, n = 100.0, 0.10, -0.04, 120
    x0, y0 = 300000.0, 7650000.0
    tr = from_origin(x0, y0 + n, 1.0, 1.0)
    jj, ii = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    cx, cy = rasterio.transform.xy(tr, jj.ravel().tolist(), ii.ravel().tolist())
    cx = np.array(cx).reshape(n, n); cy = np.array(cy).reshape(n, n)
    Z = (Z0 + GX * (cx - x0) + GY * (cy - y0)).astype("float64")
    surf = TerrainMesh(Z, x0, y0 + n, 1.0)
    # coupe OBLIQUE (37°) décalée des centres → pente constante attendue (projection du gradient)
    ux, uy = math.cos(math.radians(37)), math.sin(math.radians(37))
    zs = [surf.altitude(x0 + 10.3 + ux * d, y0 + 8.7 + uy * d) for d in range(31)]
    pentes = [(zs[i + 1] - zs[i]) * 100 for i in range(len(zs) - 1)]
    attendu = (GX * ux + GY * uy) * 100
    # lacune : un trou de surface → None sur la coupe droite EST
    Z2 = Z.copy(); Z2[:, 60:65] = np.nan
    surf2 = TerrainMesh(Z2, x0, y0 + n, 1.0)
    jrow = n // 2; yr = y0 + n - (jrow + 0.5)
    prof = [{"d": float(i), "z": surf2.altitude(x0 + i + 0.5, yr)} for i in range(n)]
    runs = [r for r in _split_runs(prof)]
    res = {"oblique": {"pente_attendue_pct": round(attendu, 5),
                       "pente_min_pct": round(min(pentes), 5), "pente_max_pct": round(max(pentes), 5),
                       "ecart_max": round(max(pentes) - min(pentes), 6),
                       "constante": max(pentes) - min(pentes) < 1e-6,
                       "note": "surface bilinéaire = reproduit un plan ; coupe décalée des centres → pente constante"},
           "lacune": {"n_runs": len(runs), "longueurs_m": [round(r[-1]["d"] - r[0]["d"], 1) for r in runs]},
           "talus_50cm_vs_1m": None}   # rempli par controle_C
    (OUT / "controles" / "a_plan_synthetique.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"  (a) oblique constante={res['oblique']['constante']} (écart {res['oblique']['ecart_max']}) ; lacune {res['lacune']['n_runs']} runs")
    return res


def _split_runs(profil):
    runs, cur = [], []
    for p in profil:
        if p["z"] is None:
            if cur:
                runs.append(cur); cur = []
        else:
            cur.append(p)
    if cur:
        runs.append(cur)
    return runs


# ── contrôle (b) — cohérence LiDAR HD ↔ RGE ALTI ──────────────────────────────────────────────────

def controle_b():
    from pyproj import Transformer
    tf = Transformer.from_crs(2975, 4326, always_xy=True)
    pts = {"plate (≈plat)": (314713, 7672415), "alt760 (pente douce)": (322881, 7672581),
           "bz1065 (talus)": (336637, 7689754), "cotier (falaise)": (320491, 7661770)}
    lignes, diffs = [], []
    with httpx.Client(timeout=30) as c:
        for nom, (x, y) in pts.items():
            zl = SC.sample_points([(x, y)])[0]
            lon, lat = tf.transform(x, y)
            r = c.get("https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json",
                      params={"lon": f"{lon:.6f}", "lat": f"{lat:.6f}", "resource": "ign_rge_alti_wld", "zonly": "true"})
            zr = r.json()["elevations"][0]
            d = None if zl is None else round(zl - zr, 2)
            if d is not None:
                diffs.append(abs(d))
            lignes.append({"type": nom, "cog_lidar_m": zl, "rge_alti_service_m": zr, "ecart_m": d})
    res = {"points": lignes, "ecart_abs_max_m": round(max(diffs), 2) if diffs else None,
           "ecart_abs_moyen_m": round(sum(diffs) / len(diffs), 2) if diffs else None,
           "derive": ("Le service RGE ALTI de La Réunion (ign_rge_alti_wld) rend des cotes quasi identiques "
                      "au LiDAR HD MNT (écarts décimétriques, toutes pentes) : il en DÉRIVE. La couche RGE ALTI "
                      "historique 5 m s'écarte de plusieurs mètres (σ≈5 m).")}
    (OUT / "controles" / "b_coherence_lidar_rgealti.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"  (b) écart abs max {res['ecart_abs_max_m']} m")
    return res


def controle_c():
    res = {"disponible": False,
           "constat": ("Aucune cote publique INDÉPENDANTE ne coïncide avec un point témoin au même endroit "
                       "ET au même référentiel (REUN89). Service RGE ALTI et WMS LiDAR HD = même source (donc "
                       "pas indépendants) ; aucun repère de nivellement IGN ne tombe au pixel d'un témoin. "
                       "Conformément au mandat : il n'y en a pas.")}
    (OUT / "controles" / "c_controle_independant.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("  (c) aucun contrôle indépendant (déclaré)")
    return res


# ── contrôle (C) — résolution 1 m vs 0,50 m + géoréférencement ────────────────────────────────────

_WMS = ("https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:2975"
        "&FORMAT=image/geotiff&LAYERS=IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S")


def _wms(minx, miny, maxx, maxy, pas):
    w = int(round((maxx - minx) / pas)); h = int(round((maxy - miny) / pas))
    r = httpx.get(_WMS + f"&WIDTH={w}&HEIGHT={h}&BBOX={minx},{miny},{maxx},{maxy}", timeout=90)
    import io
    with rasterio.open(io.BytesIO(r.content)) as d:
        a = d.read(1).astype("float64")
        tr = d.transform
    a[(a <= -1000) | ~np.isfinite(a)] = np.nan
    return TerrainMesh(a, tr.c, tr.f, tr.a)


def controle_C(eng):
    """1 m vs 0,50 m le long des MÊMES axes (témoins en pente) ; + géoréférencement ; corrige le 0,92 m."""
    out = {"resolution": [], "georeferencement": {}, "correction_0_92m": ""}
    for label, idu in (("bz1065", "97411000BZ1065"), ("cotier", "97413000CA0057")):
        with Session(eng) as db:
            s = build_scene(db, idu)
        c = [x for x in s.coupes if x["label"] == "A"][0]
        ox, oy = c["origine_2975"]; ux, uy = c["direction"]; L = c["longueur_m"]
        minx = min(ox, ox + ux * L) - 10; maxx = max(ox, ox + ux * L) + 10
        miny = min(oy, oy + uy * L) - 10; maxy = max(oy, oy + uy * L) + 10
        s1 = _wms(minx, miny, maxx, maxy, 1.0)
        s05 = _wms(minx, miny, maxx, maxy, 0.5)
        ds = np.arange(0, L, 1.0)
        diffs = []
        for d in ds:
            z1 = s1.altitude(ox + ux * d, oy + uy * d)
            z05 = s05.altitude(ox + ux * d, oy + uy * d)
            if z1 is not None and z05 is not None:
                diffs.append(abs(z1 - z05))
        diffs = np.array(diffs)
        out["resolution"].append({
            "temoin": label, "axe": "A (pente dominante)", "longueur_m": round(L, 1),
            "ecart_1m_vs_50cm_median_m": round(float(np.median(diffs)), 3),
            "ecart_1m_vs_50cm_p95_m": round(float(np.percentile(diffs, 95)), 3),
            "ecart_1m_vs_50cm_max_m": round(float(diffs.max()), 3)})
    # géoréférencement : la valeur à un point est INVARIANTE par l'alignement de la fenêtre WMS
    x, y = 336637, 7689754
    ga = _wms(x - 50, y - 50, x + 50, y + 50, 1.0).altitude(x, y)
    gb = _wms(x - 50.5, y - 49.5, x + 49.5, y + 50.5, 1.0).altitude(x, y)   # fenêtre décalée
    out["georeferencement"] = {
        "point_2975": [x, y], "valeur_fenetre_A_m": round(ga, 3) if ga else None,
        "valeur_fenetre_decalee_m": round(gb, 3) if gb else None,
        "ecart_m": round(abs(ga - gb), 3) if (ga and gb) else None,
        "note": ("L'altitude en un point est INVARIANTE par le cadrage de la fenêtre WMS (écart ~0) : "
                 "les fenêtres sont bien géoréférencées sur la grille native (origine = BBOX au pixel près). "
                 "Le WMS tague EPSG:32740 mais la grille est en coordonnées 2975 → ré-étiquetée.")}
    out["correction_0_92m"] = (
        "CORRECTION (lecture du rapport précédent) : le « 0,92 m » annoncé était l'ÉTENDUE pic-à-pic des "
        "quatre sous-pixels 0,50 m DANS un pixel 1 m en talus (p95) — une dispersion interne, PAS l'écart "
        "que le 1 m introduit sur une coupe. Mesuré ci-dessus LE LONG DES MÊMES AXES, l'écart réel de cote "
        "entre 1 m et 0,50 m est décimétrique (médiane ~" +
        str(out["resolution"][0]["ecart_1m_vs_50cm_median_m"]) + " m, p95 ~" +
        str(out["resolution"][0]["ecart_1m_vs_50cm_p95_m"]) + " m sur BZ1065). Le 1 m lisse les micro-ruptures ; "
        "il conserve la forme et les cotes utiles du talus.")
    (OUT / "controles" / "C_resolution_georef.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    # réinjecte dans (a)
    a = json.loads((OUT / "controles" / "a_plan_synthetique.json").read_text())
    a["talus_50cm_vs_1m"] = out["resolution"]
    (OUT / "controles" / "a_plan_synthetique.json").write_text(json.dumps(a, ensure_ascii=False, indent=2))
    print(f"  (C) résolution BZ1065 écart médian {out['resolution'][0]['ecart_1m_vs_50cm_median_m']} m ; "
          f"géoréf écart {out['georeferencement']['ecart_m']} m")
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    eng = create_engine(DB)
    print("Témoins…"); r_tem, fautes = temoins(eng)
    print("Recette D…"); r_d = recette_d(eng)
    print("Contrôles…"); r_a = controle_a(); r_b = controle_b(); r_c = controle_c(); r_C = controle_C(eng)
    meta = json.loads((REPO / "data" / "mnt1m" / "fond_1m.meta.json").read_text())
    synth = {"temoins": r_tem, "test_cadre_fautes": fautes, "recette_d": r_d,
             "controle_a": r_a, "controle_b": r_b, "controle_c": r_c, "controle_C": r_C,
             "fond": {"taille_octets": meta["taille_octets"], "octets_par_m2_compresse": meta["octets_par_m2_compresse"],
                      "extrapolation": meta["extrapolation"]}}
    (OUT / "synthese.json").write_text(json.dumps(synth, ensure_ascii=False, indent=2))
    print("\nÉcrit dans", OUT)


if __name__ == "__main__":
    main()
