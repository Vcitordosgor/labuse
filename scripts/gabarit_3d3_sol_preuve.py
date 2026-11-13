"""GABARIT-3D-3 (LOT 2) — preuves du sol 0,5 m : 10 parcelles hors témoins (bâties/nues/en pente),
temps d'ouverture FROID puis CHAUD, et la 2ᵉ ouverture = 0 appel extérieur. Via l'API (port 7290).

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  python scripts/gabarit_3d3_sol_preuve.py
"""
from __future__ import annotations

import json
import time

import httpx
from sqlalchemy import text

from labuse.db import session_scope

API = "http://127.0.0.1:7290"
TEMOINS = ("97411000BZ1065", "97415000CM1658", "97415000CY0196", "97413000CA0057")
_c = httpx.Client(timeout=120.0)


def _stats():
    return _c.get(f"{API}/outils/gabarit/sol/stats").json()["appels_wms"]


def _scene(idu):
    t0 = time.perf_counter()
    r = _c.get(f"{API}/outils/gabarit/scene/{idu}", params={"frais": 1})
    dt = (time.perf_counter() - t0) * 1000
    return (r.json() if r.status_code == 200 else None), dt


def _choisir():
    with session_scope() as db:
        bat = db.execute(text(
            "SELECT p.idu FROM parcels p WHERE EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' "
            "AND ST_Intersects(b.geom_2975, p.geom_2975)) AND p.idu <> ALL(:t) ORDER BY md5(p.idu) LIMIT 6"),
            {"t": list(TEMOINS)}).scalars().all()
        nu = db.execute(text(
            "SELECT p.idu FROM parcels p WHERE NOT EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' "
            "AND ST_Intersects(b.geom_2975, p.geom_2975)) AND p.idu <> ALL(:t) AND p.surface_m2 > 200 "
            "ORDER BY md5(p.idu) LIMIT 6"),
            {"t": list(TEMOINS)}).scalars().all()
    return list(bat), list(nu)


def main():
    bat, nu = _choisir()
    pool = bat[:6] + nu[:6]
    resultats = []
    for idu in pool:
        if len([r for r in resultats if r["ok"]]) >= 10:
            break
        c0 = _stats()
        froid, t_froid = _scene(idu)
        if not froid or not froid.get("disponible"):
            resultats.append({"idu": idu, "ok": False})
            continue
        c1 = _stats()
        chaud, t_chaud = _scene(idu)
        c2 = _stats()
        m = froid.get("meta", {})
        cb = next((c for c in froid.get("coupes", []) if c["label"] == "A"), None)
        pente = None
        if cb:
            zs = [p["z"] for p in cb["profil"] if p["z"] is not None]
            pente = round(max(zs) - min(zs), 1) if zs else None
        resultats.append({
            "idu": idu, "ok": True, "bati": len(froid.get("batiments", [])),
            "denivele_m": pente, "maille": m.get("maille_m"), "source": m.get("sol_source"),
            "acq": m.get("acquisition_date"), "repli": m.get("sol_repli"),
            "froid_ms": round(t_froid), "chaud_ms": round(t_chaud),
            "wms_froid": c1 - c0, "wms_chaud": c2 - c1})
    ok = [r for r in resultats if r["ok"]]
    print(f"\n════ LOT 2 — 10 parcelles hors témoins : froid / chaud / appels extérieurs ════")
    print(f"{'idu':>16} {'bâti':>4} {'déniv':>6} {'maille':>6} {'source':>10} {'froid':>7} {'chaud':>7} {'wms↓froid':>9} {'wms↓chaud':>9}")
    for r in ok:
        print(f"{r['idu']:>16} {r['bati']:>4} {str(r['denivele_m']) + ' m':>6} {str(r['maille']) + ' m':>6} "
              f"{r['source']:>10} {str(r['froid_ms']) + 'ms':>7} {str(r['chaud_ms']) + 'ms':>7} "
              f"{r['wms_froid']:>9} {r['wms_chaud']:>9}")
    print(f"\nparcelles ouvertes : {len(ok)} / {len(resultats)}")
    print(f"2ᵉ ouverture (chaud) — appels extérieurs : {sum(r['wms_chaud'] for r in ok)} (doit être 0)")
    print(f"froid médian {sorted(r['froid_ms'] for r in ok)[len(ok)//2]} ms · chaud médian "
          f"{sorted(r['chaud_ms'] for r in ok)[len(ok)//2]} ms")
    print(json.dumps(ok, ensure_ascii=False))


if __name__ == "__main__":
    main()
