"""GABARIT-3D-2 LOT A — A4 (LECTURE SEULE). Sur 30 parcelles bâties tirées au sort, combien ont une
« Rupture du terrain à vérifier » qui TOUCHE une emprise bâtie ?

On reproduit FIDÈLEMENT l'app : build_scene (axes A/B réels, même maillage, même `_rupture_d`), mais
on alimente le MNT par le MÊME produit IGN (LiDAR HD MNT 1 m, WMS RGR92UTM40S) fenêtre par parcelle —
le fond local ne couvre que 4 témoins. Aucune écriture en base, aucun code applicatif modifié.

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d2_rupture_prevalence.py
"""
from __future__ import annotations

import math
import statistics

import httpx
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from sqlalchemy import text

import labuse.gabarit.scene as scene_mod
from labuse.db import session_scope
from labuse.gabarit.coupe_svg import _rupture_d

WMS = "https://data.geopf.fr/wms-r"
LAYER = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S"
_client = httpx.Client(timeout=90.0)


def _fetch_surface(minx, miny, maxx, maxy, marge=35.0):
    """MNT 1 m IGN (même produit que fond_1m.tif) pour la fenêtre + marge → scene_mod._Surface."""
    x0, y0 = int(math.floor(minx - marge)), int(math.floor(miny - marge))
    x1, y1 = int(math.ceil(maxx + marge)), int(math.ceil(maxy + marge))
    w, h = x1 - x0, y1 - y0
    r = _client.get(WMS, params={"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
                                 "STYLES": "", "CRS": "EPSG:2975", "FORMAT": "image/geotiff",
                                 "WIDTH": w, "HEIGHT": h, "BBOX": f"{x0},{y0},{x1},{y1}", "LAYERS": LAYER})
    r.raise_for_status()
    with MemoryFile(r.content) as mf, mf.open() as ds:
        a = ds.read(1).astype("float64")
    a[(a <= -1000) | ~np.isfinite(a)] = np.nan
    # transform natif : origine coin haut-gauche (x0, y1), pas 1 m
    return scene_mod._Surface(a, float(x0), float(y1), 1.0)


def main() -> None:
    results = []
    with session_scope() as db:
        idus = db.execute(text(
            "SELECT p.idu FROM parcels p WHERE EXISTS (SELECT 1 FROM spatial_layers b "
            "WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)) "
            "ORDER BY md5(p.idu) LIMIT 45")).scalars().all()

        orig = scene_mod.charger_surface

        for idu in idus:
            if len([r for r in results if r.get("scene_ok")]) >= 30:
                break
            # fenêtre de la parcelle pour le fetch
            try:
                bbox = db.execute(text("SELECT ST_XMin(g), ST_YMin(g), ST_XMax(g), ST_YMax(g) "
                                       "FROM (SELECT geom_2975 g FROM parcels WHERE idu=:i) q"),
                                  {"i": idu}).one()
            except Exception:
                continue
            minx, miny, maxx, maxy = bbox

            def _patched(a, b, c, d, marge=170.0, _bb=(minx, miny, maxx, maxy)):
                try:
                    return _fetch_surface(_bb[0], _bb[1], _bb[2], _bb[3], marge=min(marge, 45.0))
                except Exception:
                    return None

            scene_mod.charger_surface = _patched
            try:
                scene = scene_mod.build_scene(db, idu, use_cache=False)
                d = scene.to_dict()
            except Exception as exc:  # noqa: BLE001
                results.append({"idu": idu, "scene_ok": False, "err": str(exc)[:80]})
                scene_mod.charger_surface = orig
                continue
            finally:
                scene_mod.charger_surface = orig

            coupes = d.get("coupes") or []
            n_bati_coupe = 0
            touche = False
            touche_eleve = False
            detail = []
            for c in coupes:
                profil = [p for p in c["profil"] if p["z"] is not None]
                L = c["longueur_m"]
                # sol de référence = médiane du profil parcelle HORS bâti
                bspans = [(b["d0"], b["d1"]) for b in c["batiments"]]
                hors = [p["z"] for p in profil if not any(a - 1 <= p["d"] <= b + 1 for a, b in bspans)]
                sol_ref = statistics.median(hors) if hors else None
                for b in c["batiments"]:
                    n_bati_coupe += 1
                    drb = _rupture_d(profil, b["d0"], min(b["d1"] + 3.0, L))
                    if drb is None:
                        continue
                    dans_emprise = b["d0"] - 1e-6 <= drb <= b["d1"] + 1e-6
                    # altitude au point de rupture
                    zr = next((p["z"] for p in profil if abs(p["d"] - drb) < 0.6), None)
                    eleve = (zr is not None and sol_ref is not None and (zr - sol_ref) >= 1.5)
                    if dans_emprise:
                        touche = True
                        if eleve:
                            touche_eleve = True
                        detail.append({"axe": c["label"], "d": round(drb, 1),
                                       "z": None if zr is None else round(zr, 1),
                                       "sur_sol": None if (zr is None or sol_ref is None) else round(zr - sol_ref, 1)})
            results.append({"idu": idu, "scene_ok": True, "n_bati_coupe": n_bati_coupe,
                            "touche_emprise": touche, "touche_eleve": touche_eleve, "detail": detail})

    ok = [r for r in results if r.get("scene_ok")]
    touchent = [r for r in ok if r["touche_emprise"]]
    eleves = [r for r in ok if r["touche_eleve"]]
    print(f"\n════ A4 — rupture à vérifier qui touche une emprise bâtie ════")
    print(f"parcelles avec scène exploitable : {len(ok)}")
    print(f"dont coupe traversant ≥1 bâtiment : {len([r for r in ok if r['n_bati_coupe'] > 0])}")
    print(f"RUPTURE touchant une emprise bâtie : {len(touchent)} / {len(ok)}")
    print(f"  dont terrain SURÉLEVÉ ≥1,5 m au point de rupture (signature « élément couvert ») : {len(eleves)}")
    print(f"\n── détail (parcelles avec rupture sur emprise) ──")
    for r in touchent:
        print(f"  {r['idu']}  {r['detail']}")
    echecs = [r for r in results if not r.get("scene_ok")]
    if echecs:
        print(f"\n({len(echecs)} parcelles sans scène exploitable, non comptées)")


if __name__ == "__main__":
    main()
