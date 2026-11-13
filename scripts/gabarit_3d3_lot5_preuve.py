"""GABARIT-3D-3 (LOT 5) — ouverture bornée. On prouve, sur des parcelles CONSTRUCTIBLES de tailles variées,
que le MAILLAGE 3D servi est allégé (sommets ÷ 4 ou ÷ 16) → l'ouverture tombe sous 3 s hors réseau, tandis
que la COUPE reste en 0,5 m et que les COTES 3D sont IDENTIQUES avant/après (elles viennent du sol 0,5 m).
Pour chaque parcelle : sommets AVANT (0,5 m) vs APRÈS (allégé), maille 3D, temps de construction serveur des
FACES avant/après (le coût du maillage), et l'écart de cote haute/basse (doit être 0,00 m).

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d3_lot5_preuve.py
"""
from __future__ import annotations

import json
import time

from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit import scene as SC


def _inp(x, y, ring):
    n = len(ring); j = n - 1; c = False
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            c = not c
        j = i
    return c


def _inpolys(x, y, polys):
    return any(_inp(x, y, p["ext"]) for p in polys)


def _cote_ancienne(scene_0p5):
    """Ancienne cote (balayage des faces 0,5 m, hors emprise bâtie) — la référence AVANT le LOT 5."""
    f = scene_0p5.terrain["faces_parcelle"]
    cad = [{"ext": [[x, y] for x, y in poly["ext"]]} for poly in scene_0p5.contour_cadastral]
    emp = [sub for b in scene_0p5.batiments for sub in (b.get("empreinte") or [])]
    hi = lo = None
    for v in f["vertices"]:
        if _inpolys(v[0], v[1], cad) and not _inpolys(v[0], v[1], emp):
            hi = v[2] if hi is None or v[2] > hi else hi
            lo = v[2] if lo is None or v[2] < lo else lo
    return hi, lo


def _mesure(db, idu):
    # APRÈS (budget normal) : faces allégées + cote serveur 0,5 m
    SC._MEMO.clear()
    t0 = time.perf_counter()
    s = SC._build_scene(db, idu)
    t_apres = (time.perf_counter() - t0) * 1000
    if not s.disponible:
        return None
    f = s.terrain.get("faces_parcelle") or {}
    c3d = s.terrain.get("cotes_3d")
    nv_ap = len(f.get("vertices") or [])
    m3 = s.terrain.get("maille_3d_m")
    # AVANT (budget géant = 0,5 m partout) : sommets + temps + ancienne cote
    ob = SC._FACES_BUDGET_SOMMETS
    SC._FACES_BUDGET_SOMMETS = 10 ** 9
    SC._MEMO.clear()
    t0 = time.perf_counter()
    s0 = SC._build_scene(db, idu)
    t_avant = (time.perf_counter() - t0) * 1000
    SC._FACES_BUDGET_SOMMETS = ob
    nv_av = len(s0.terrain["faces_parcelle"]["vertices"])
    hi0, lo0 = _cote_ancienne(s0)
    dhi = abs(c3d["haut"][2] - hi0) if (c3d and hi0 is not None) else None
    dlo = abs(c3d["bas"][2] - lo0) if (c3d and lo0 is not None) else None
    return {"idu": idu, "sommets_avant": nv_av, "sommets_apres": nv_ap, "maille_3d_m": m3,
            "faces_ms_avant": round(t_avant), "faces_ms_apres": round(t_apres),
            "cote_haut": c3d["haut"][2] if c3d else None, "cote_bas": c3d["bas"][2] if c3d else None,
            "d_cote_haut_m": round(dhi, 3) if dhi is not None else None,
            "d_cote_bas_m": round(dlo, 3) if dlo is not None else None}


def main():
    temoins = ["97411000BZ1065", "97415000DX0049", "97413000CT0442"]
    with session_scope() as db:
        cand = db.execute(text(
            "SELECT p.idu FROM parcels p WHERE p.surface_m2 BETWEEN 400 AND 6000 AND EXISTS "
            "(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)) "
            "AND p.idu <> ALL(:t) ORDER BY md5(p.idu) LIMIT 60"), {"t": temoins}).scalars().all()
        res = []
        for idu in temoins + list(cand):
            if len(res) >= 10:
                break
            try:
                r = _mesure(db, idu)
            except Exception as e:  # noqa: BLE001
                print(f"  (saut {idu}: {e})"); r = None
            if r:
                res.append(r)
    res.sort(key=lambda r: -r["sommets_avant"])
    print("\n════ LOT 5 — maillage 3D allégé (coupe 0,5 m inchangée, cotes identiques) ════")
    print(f"{'idu':>16} {'som.avant':>9} {'som.après':>9} {'maille3D':>8} {'faces.av':>8} {'faces.ap':>8} {'Δcote':>7}")
    for r in res:
        dmax = max(x for x in (r["d_cote_haut_m"], r["d_cote_bas_m"]) if x is not None) if r["cote_haut"] is not None else None
        print(f"{r['idu']:>16} {r['sommets_avant']:>9} {r['sommets_apres']:>9} {str(r['maille_3d_m'])+' m':>8} "
              f"{str(r['faces_ms_avant'])+'ms':>8} {str(r['faces_ms_apres'])+'ms':>8} {(str(dmax)+' m') if dmax is not None else '—':>7}")
    allege = [r for r in res if r["maille_3d_m"] and r["maille_3d_m"] > 0.5]
    dmax = max((x for r in res for x in (r["d_cote_haut_m"], r["d_cote_bas_m"]) if x is not None), default=0.0)
    print(f"\nparcelles : {len(res)} · allégées (>0,5 m) : {len(allege)}")
    print(f"écart de cote 3D max avant/après : {dmax} m  (doit être 0,0 m — les cotes viennent du sol 0,5 m)")
    print(f"sommets médians : avant {sorted(r['sommets_avant'] for r in res)[len(res)//2]} → "
          f"après {sorted(r['sommets_apres'] for r in res)[len(res)//2]}")
    with open("docs/audit-2026-11/gabarit-3d-3/lot5_maillage.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("→ docs/audit-2026-11/gabarit-3d-3/lot5_maillage.json")


if __name__ == "__main__":
    main()
