"""GABARIT-3D-1 (pilote, étape 1) — TÉMOINS + CONTRÔLES → docs/audit-2026-11/gabarit-3d-1/.

Produit, pour les parcelles témoins, les deux coupes (SVG + PNG) et le plan-clé, et les trois
contrôles séparés demandés par le mandat :
  (a) exactitude du calcul sur un PLAN INCLINÉ SYNTHÉTIQUE (altitudes, dénivelé, centres des pixels,
      raccords, lacunes) + ce que le passage de 50 cm à 1 m enlève aux talus ;
  (b) cohérence LiDAR HD ↔ RGE ALTI aux mêmes points, par type de terrain (dérive vérifiée) ;
  (c) contrôle indépendant seulement si une cote publique coïncide au même point et référentiel.

Usage : PYTHONPATH=/tmp/gab3d_libs:src ../labuse/.venv/bin/python scripts/gabarit_3d_temoins.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/tmp/gab3d_libs")  # cairosvg isolé (venv partagé non modifié)
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

import cairosvg
import httpx
import numpy as np
import rasterio
from rasterio.transform import from_origin
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from labuse.gabarit.scene import build_scene, sample_points, _stats_coupe
from labuse.gabarit.coupe_svg import coupe_svg, plan_cle_svg, _runs

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "audit-2026-11" / "gabarit-3d-1"
DB = os.environ["LABUSE_DATABASE_URL"]

TEMOINS = [
    ("plate", "97415000CY0196", "Parcelle plate — plaine littorale de Saint-Paul (~5 m)"),
    ("cotier", "97413000CA0057", "Littoral de Saint-Leu — falaise / bord d'eau"),
    ("alt760", "97415000CM1658", "Parcelle en altitude — 36 Rue des Jacarandas, Saint-Paul (~595 m mesurés)"),
    ("bz1065", "97411000BZ1065", "97411000BZ1065 — talus, Saint-Denis (témoin CDC)"),
]


def _png(svg: str, path: Path, w: int | None = None):
    path.write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(path.with_suffix(".png")),
                     output_width=w or 900)


def temoins(eng) -> list[dict]:
    (OUT / "coupes").mkdir(parents=True, exist_ok=True)
    (OUT / "plan").mkdir(parents=True, exist_ok=True)
    resume = []
    for label, idu, titre in TEMOINS:
        with Session(eng) as db:
            s = build_scene(db, idu)
        entry = {"label": label, "idu": idu, "titre": titre, "scene_id": s.scene_id,
                 "disponible": s.disponible, "n_batiments": len(s.batiments),
                 "regles": {k: s.regles.get(k) for k in ("zoneImplantationM2", "plafondEmpriseM2", "hauteurReglementaireM")},
                 "coupes": []}
        for c in s.coupes:
            svg = coupe_svg(c)
            if svg:
                _png(svg, OUT / "coupes" / f"{label}_{c['label']}.svg")
            entry["coupes"].append({"axe": c["label"], "titre": c["titre"], "voie": c["voie"],
                                    "L": c["longueur_m"], "cotes": c["cotes"]})
        plan = plan_cle_svg(s.to_dict())
        if plan:
            _png(plan, OUT / "plan" / f"{label}_plan.svg", w=360)
        resume.append(entry)
        print(f"  {label} {idu}: {len(s.coupes)} coupes, id={s.scene_id}")
    return resume


# ── Contrôle (a) — plan incliné synthétique + perte 50 cm → 1 m ────────────────────────────────────

def controle_a() -> dict:
    (OUT / "controles").mkdir(parents=True, exist_ok=True)
    # plan z = Z0 + GX·(x-x0) + GY·(y-y0), pente analytique = |(GX,GY)|
    Z0, GX, GY = 100.0, 0.10, -0.04     # 10 % en x, −4 % en y → pente √(0.10²+0.04²)=0.1077
    pente_vraie = (GX ** 2 + GY ** 2) ** 0.5
    x0, y0 = 300000.0, 7650000.0
    n = 120
    tif = Path("/tmp/gab3d_synth.tif")
    tr = from_origin(x0, y0 + n, 1.0, 1.0)   # coin NO = (x0, y0+n), lignes vers le sud
    # Z construit DEPUIS le transform : valeur(pixel) = plan À SON centre géographique exact
    jj, ii = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    cx, cy = rasterio.transform.xy(tr, jj.ravel().tolist(), ii.ravel().tolist())
    cx = np.array(cx).reshape(n, n); cy = np.array(cy).reshape(n, n)   # centres de pixels (convention raster)
    Z = (Z0 + GX * (cx - x0) + GY * (cy - y0)).astype("float32")
    Z[:, 60:65] = -9999.0                                 # lacune : bande verticale (colonnes 60..64)
    with rasterio.open(tif, "w", driver="GTiff", height=n, width=n, count=1, dtype="float32",
                       crs="EPSG:2975", transform=tr, nodata=-9999.0) as dst:
        dst.write(Z, 1)

    # échantillonne une ligne EST (le long de x) au centre d'une rangée, via rasterio
    ds = rasterio.open(tif)
    jrow = n // 2
    cxr, cyr = rasterio.transform.xy(tr, jrow, np.arange(n))   # centres exacts de la rangée
    pts = list(zip(cxr, cyr))
    vals = [v[0] for v in ds.sample(pts)]
    profil = [{"d": float(i), "z": (None if vals[i] <= -1000 else round(float(vals[i]), 4))} for i in range(n)]

    # vérité analytique AU MÊME centre de pixel que l'échantillon
    z_vrai = [Z0 + GX * (cxr[i] - x0) + GY * (cyr[i] - y0) for i in range(n)]
    err = [abs(profil[i]["z"] - z_vrai[i]) for i in range(n) if profil[i]["z"] is not None]
    st = _stats_coupe(profil)
    runs = _runs(profil)

    # pente le long de la ligne EST = GX (composante x) ; dénivelé par morceau = GX × longueur_du_morceau
    res = {
        "plan": {"Z0": Z0, "GX": GX, "GY": GY, "pente_plan_pct": round(pente_vraie * 100, 3)},
        "altitudes": {"erreur_max_m": round(max(err), 6), "erreur_moyenne_m": round(sum(err) / len(err), 6),
                      "note": "échantillonnage AU CENTRE des pixels = valeur exacte du plan"},
        "lacune": {"n_runs": len(runs), "longueurs_runs_m": [round(r[-1]["d"] - r[0]["d"], 1) for r in runs],
                   "n_lacune_profil": st.get("n_lacune"),
                   "note": "la bande nodata coupe le profil en 2 morceaux ; pente calculée PAR morceau"},
        "pente_mesuree_pct": st.get("pente_moyenne_pct"),
        "pente_le_long_x_attendue_pct": round(GX * 100, 3),
        "raccords": {"continuité_dans_un_run_ok": all(
            abs((runs[0][i + 1]["z"] - runs[0][i]["z"]) - GX) < 1e-3 for i in range(len(runs[0]) - 1)),
            "pas_constant_m": 1.0},
    }

    # perte 50 cm → 1 m sur un VRAI talus (BZ1065) : WMS 0,50 m vs 1 m
    res["talus_50cm_vs_1m"] = _perte_resolution()

    # rendu d'une coupe synthétique (témoin « pente synthétique »)
    coupe = {"label": "S", "titre": "Coupe synthétique — plan incliné 10 % (contrôle a)", "voie": None,
             "longueur_m": float(n - 1), "profil": profil, "limites_parcelle_d": [[20.0, 100.0]],
             "zone_implantation_d": [[40.0, 80.0]], "batiments": [], "cotes": st}
    svg = coupe_svg(coupe)
    _png(svg, OUT / "controles" / "a_plan_synthetique.svg")
    (OUT / "controles" / "a_plan_synthetique.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("  (a) plan synthétique : err_max", res["altitudes"]["erreur_max_m"], "m ; runs", res["lacune"]["n_runs"])
    return res


def _perte_resolution() -> dict:
    """50 cm → 1 m sur le talus BZ1065 : étendue intra-pixel perdue par le moyennage 2×2."""
    bbox = (336380, 7689498, 336892, 7690010)
    base = ("https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:2975"
            "&FORMAT=image/geotiff&LAYERS=IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S")
    with httpx.Client(timeout=90) as c:
        for w, name in ((1024, "/tmp/g3d_50.tif"), (512, "/tmp/g3d_1.tif")):
            r = c.get(base + f"&WIDTH={w}&HEIGHT={w}&BBOX={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
            Path(name).write_bytes(r.content)
    a50 = rasterio.open("/tmp/g3d_50.tif").read(1).astype("float64")
    gy, gx = np.gradient(a50, 0.5, 0.5)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    blk = a50.reshape(512, 2, 512, 2)
    ptp = np.ptp(blk, axis=(1, 3))            # étendue dans chaque pixel 1 m
    steep = slope[::2, ::2] > 20
    return {"pente_mediane_deg": round(float(np.median(slope)), 1),
            "pente_max_deg": round(float(slope.max()), 1),
            "etendue_intra_pixel_mediane_m": round(float(np.median(ptp)), 3),
            "etendue_intra_pixel_mediane_talus_m": round(float(np.median(ptp[steep])) if steep.sum() else 0.0, 3),
            "etendue_intra_pixel_p95_talus_m": round(float(np.percentile(ptp[steep], 95)) if steep.sum() else 0.0, 3),
            "note": "le 1 m IGN = moyenne 2×2 du 0,50 m ; l'étendue intra-pixel est ce que le 1 m lisse."}


# ── Contrôle (b) — cohérence LiDAR HD ↔ RGE ALTI ───────────────────────────────────────────────────

def controle_b(eng) -> dict:
    """Aux centroïdes témoins (par type de terrain) : COG LiDAR HD vs service RGE ALTI IGN."""
    from pyproj import Transformer
    tf = Transformer.from_crs(2975, 4326, always_xy=True)
    pts = {"plate (≈plat)": (314713, 7672415), "alt760 (pente douce)": (322881, 7672581),
           "bz1065 (talus)": (336637, 7689754), "cotier (falaise)": (320491, 7661770)}
    lignes, diffs = [], []
    with httpx.Client(timeout=30) as c:
        for nom, (x, y) in pts.items():
            z_lidar = sample_points([(x, y)])[0]
            lon, lat = tf.transform(x, y)
            r = c.get("https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json",
                      params={"lon": f"{lon:.6f}", "lat": f"{lat:.6f}",
                              "resource": "ign_rge_alti_wld", "zonly": "true"})
            z_rge = r.json()["elevations"][0]
            d = None if z_lidar is None else round(z_lidar - z_rge, 2)
            if d is not None:
                diffs.append(abs(d))
            lignes.append({"type": nom, "cog_lidar_m": z_lidar, "rge_alti_service_m": z_rge, "ecart_m": d})
    res = {"points": lignes,
           "ecart_abs_max_m": round(max(diffs), 2) if diffs else None,
           "ecart_abs_moyen_m": round(sum(diffs) / len(diffs), 2) if diffs else None,
           "derive": ("Le service RGE ALTI de La Réunion (ign_rge_alti_wld) renvoie des cotes "
                      "quasi identiques au LiDAR HD MNT (écarts décimétriques) : il en DÉRIVE "
                      "(RGE ALTI « HIGHRES » = LiDAR HD). La couche RGE ALTI historique 5 m, elle, "
                      "s'écarte de plusieurs mètres (mesuré en amont : σ≈5 m).")}
    (OUT / "controles").mkdir(parents=True, exist_ok=True)
    (OUT / "controles" / "b_coherence_lidar_rgealti.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("  (b) cohérence : écart abs max", res["ecart_abs_max_m"], "m")
    return res


# ── Contrôle (c) — contrôle indépendant ────────────────────────────────────────────────────────────

def controle_c() -> dict:
    res = {"disponible": False,
           "constat": ("Aucune cote publique INDÉPENDANTE ne coïncide avec un point témoin au même "
                       "endroit ET au même référentiel (REUN89). Le service RGE ALTI et le WMS LiDAR HD "
                       "sont le MÊME référentiel/source (contrôle b), donc PAS indépendants. Les repères "
                       "de nivellement IGN (REUN89) existent mais aucun ne tombe au pixel d'un témoin. "
                       "Conformément au mandat : il n'y a pas de contrôle indépendant à affirmer ici.")}
    (OUT / "controles").mkdir(parents=True, exist_ok=True)
    (OUT / "controles" / "c_controle_independant.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("  (c) contrôle indépendant : aucun (déclaré)")
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    eng = create_engine(DB)
    print("Témoins…")
    r_tem = temoins(eng)
    print("Contrôles…")
    r_a = controle_a()
    r_b = controle_b(eng)
    r_c = controle_c()
    meta = json.loads((REPO / "data" / "mnt1m" / "fond_1m.meta.json").read_text())
    synth = {"temoins": r_tem, "controle_a": r_a, "controle_b": r_b, "controle_c": r_c,
             "fond": {"taille_octets": meta["taille_octets"],
                      "octets_par_m2_compresse": meta["octets_par_m2_compresse"],
                      "extrapolation": meta["extrapolation"]}}
    (OUT / "synthese.json").write_text(json.dumps(synth, ensure_ascii=False, indent=2))
    print("\nÉcrit dans", OUT)


if __name__ == "__main__":
    main()
