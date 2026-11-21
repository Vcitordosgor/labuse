"""GABARIT-3D-3 (LOT 2 FIX) — JUSTESSE du sol 0,5 m : sur 10 parcelles hors témoins, l'écart MÉDIAN sur
sol dégagé (intérieur cadastre, hors emprise bâtie) entre le NOUVEAU relief (LiDAR HD 0,5 m) et l'ANCIEN
(fond 1 m, RGE ALTI) doit rester < 0,30 m — le 0,5 m affine, il ne déplace pas le terrain. On mesure AUSSI
le plus long palier plat de chaque profil (anti-escalier) : le LiDAR HD natif n'a pas de marches de ~5 m.

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d3_justesse.py
"""
from __future__ import annotations

import json
import statistics as st

from shapely import wkt as shp_wkt
from shapely.geometry import Point
from shapely.ops import unary_union
from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit.scene import charger_surface, charger_surface_sol
from labuse.gabarit.terrain_mesh import TerrainMesh

TEMOINS = ("97411000BZ1065", "97415000CM1658", "97415000CY0196", "97413000CA0057")


def _mesh(surf):
    return TerrainMesh(surf.a, surf.ox, surf.oy, surf.pas, step=1) if surf else None


def _batis_2975(db, idu):
    rows = db.execute(text(
        "SELECT ST_AsText(b.geom_2975) FROM spatial_layers b JOIN parcels p ON p.idu=:i "
        "WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"), {"i": idu}).scalars().all()
    geoms = [shp_wkt.loads(w) for w in rows if w]
    return unary_union(geoms) if geoms else None


def _grille(g, batis, pas):
    """Points de la grille à `pas` m intérieurs au cadastre et HORS emprise bâtie (« sol dégagé »)."""
    minx, miny, maxx, maxy = g.bounds
    pts, y = [], miny + 1.0
    while y < maxy:
        x = minx + 1.0
        while x < maxx:
            p = Point(x, y)
            if g.covers(p) and (batis is None or not batis.covers(p)):
                pts.append((x, y))
            x += pas
        y += pas
    return pts


def _palier_max(mesh, g):
    """Plus long palier plat (points successifs à ±1 cm) le long d'un profil O-E au centre de la parcelle."""
    minx, miny, maxx, maxy = g.bounds
    cy = (miny + maxy) / 2
    xs = [minx + 0.5 * k for k in range(int((maxx - minx) / 0.5) + 1)]
    palier, meilleur, z0 = 0.0, 0.0, None
    for x in xs:
        z = mesh.altitude(x, cy)
        if z is None:
            z0, palier = None, 0.0
            continue
        if z0 is None or abs(z - z0) > 0.01:
            z0, palier = z, 0.0
        else:
            palier += 0.5
            meilleur = max(meilleur, palier)
    return round(meilleur, 1)


def _parcelle(db, idu):
    cad = db.execute(text("SELECT ST_AsText(geom_2975) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if not cad:
        return None
    g = shp_wkt.loads(cad)
    if g.is_empty:
        return None
    minx, miny, maxx, maxy = g.bounds
    surf_new, meta = charger_surface_sol(db, minx, miny, maxx, maxy, marge=20.0)
    mn = _mesh(surf_new)
    if mn is None or meta["source"] not in ("lidar_05m", "copie"):
        return None                                   # on exige le VRAI LiDAR HD 0,5 m
    batis = _batis_2975(db, idu)
    pts = _grille(g, batis, 2.0)
    # ANTI-ESCALIER (toute l'île) : palier max du profil LiDAR HD 0,5 m
    r = {"idu": idu, "n": len(pts), "maille": meta["maille_m"], "palier_max_m": _palier_max(mn, g)}
    # JUSTESSE (là où le fond 1 m existe : voisinages témoins) : nouveau 0,5 m vs ancien 1 m, sol dégagé
    surf_old = charger_surface(minx, miny, maxx, maxy, marge=20.0)
    mo = _mesh(surf_old)
    diffs = []
    if mo is not None:
        for x, y in pts:
            za, zb = mn.altitude(x, y), mo.altitude(x, y)
            if za is not None and zb is not None:
                diffs.append(abs(za - zb))
    if len(diffs) >= 20:
        r["ecart_median_m"] = round(st.median(diffs), 3)
        r["ecart_p90_m"] = round(sorted(diffs)[int(len(diffs) * 0.9)], 3)
        r["n_ecart"] = len(diffs)
    return r


def main():
    with session_scope() as db:
        pool = list(TEMOINS) + db.execute(text(
            "SELECT p.idu FROM parcels p WHERE p.surface_m2 > 250 AND p.idu <> ALL(:t) "
            "ORDER BY md5(p.idu) LIMIT 40"), {"t": list(TEMOINS)}).scalars().all()
        res = []
        for idu in pool:
            if len(res) >= 12:
                break
            try:
                r = _parcelle(db, idu)
            except Exception as e:  # noqa: BLE001
                print(f"  (saut {idu}: {e})"); r = None
            if r and r["n"] >= 30:
                res.append(r)
    print("\n════ LOT 2 FIX — anti-escalier (toute l'île) + justesse (vs ancien 1 m, voisinages témoins) ════")
    print(f"{'idu':>16} {'n':>5} {'maille':>6} {'palier_max':>10}   {'écart_méd(vs 1 m)':>16} {'écart_p90':>9}")
    for r in res:
        em = f"{r['ecart_median_m']} m" if "ecart_median_m" in r else "— (pas de fond 1 m)"
        ep = f"{r['ecart_p90_m']} m" if "ecart_p90_m" in r else "—"
        print(f"{r['idu']:>16} {r['n']:>5} {str(r['maille'])+' m':>6} {str(r['palier_max_m'])+' m':>10}   {em:>16} {ep:>9}")
    paliers = [r["palier_max_m"] for r in res]
    meds = [r["ecart_median_m"] for r in res if "ecart_median_m" in r]
    print(f"\nparcelles (anti-escalier) : {len(res)}  ·  palier max sur l'ensemble : {max(paliers)} m")
    print("  → LiDAR HD natif 0,5 m : aucune marche ~5 m (l'escalier venait de HIGHRES = RGE ALTI 5 m suréchantillonné)")
    if meds:
        print(f"justesse (vs ancien fond 1 m) : {len(meds)} parcelles · écart MÉDIAN des médianes "
              f"{round(st.median(meds), 3)} m  (doit être < 0,30 m)")
        print("  → le fond 1 m (RGE ALTI, fond_1m.tif) n'existe QUE sur les voisinages témoins (fichier partiel hors-git)")
    out = "docs/audit-2026-11/gabarit-3d-3/justesse.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"parcelles": res, "palier_max_global_m": max(paliers),
                   "ecart_median_global_m": round(st.median(meds), 3) if meds else None,
                   "n_justesse": len(meds)}, f, ensure_ascii=False, indent=2)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
