"""M39 P2.2 — DECK ORTHO de vérification (20 parcelles) pour revue visuelle Vic.

Échantillon (arbitrage Vic) : MAJORITÉ dans la bande déclassante [15;60] m² (17), plus 3 TÉMOINS
hors bande (sous 15 m², écartés par le plancher) — « ce que le seuil écarte ». Chaque vignette :
ortho IGN 2025 (PVA vols 21/07–02/08/2025) centrée sur la piscine DÉTECTÉE, polygone surlignés,
surface + confiance + tier servi. Vic tranche : vraie piscine ? bassin/bâche/FP ?

Sortie : qa/m39/deck_m39.html (+ capture PNG via un mjs si besoin). Lecture seule.
Usage : PYTHONPATH=src python qa/m39/gen_deck_m39.py
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import httpx  # noqa: E402
from pathlib import Path  # noqa: E402

from sqlalchemy import text  # noqa: E402

from labuse.api.division_review import (_fetch_tile, _lonlat_to_px, _rings, IGN_ORTHO_URL,  # noqa: E402
                                        TILE_PX, USER_AGENT, VIEW_H, VIEW_W, ZOOM_MAX, ZOOM_MIN)
from labuse.db import engine  # noqa: E402

CACHE = Path("/tmp/labuse_tiles_m39"); CACHE.mkdir(exist_ok=True)
OUT = os.path.join(os.path.dirname(__file__), "deck_m39.html")
RUN = "q_v8_calibre"

# Sélection : 17 en bande (stratifiée par commune + surface) + 3 témoins sous-15 (proches du plancher).
SQL_BANDE = """
SELECT DISTINCT ON (s.parcelle_id) s.parcelle_id AS idu, s.tier,
       round(pe.piscine_surface_m2::numeric,1) AS surf, round(pe.piscine_confiance::numeric,3) AS conf,
       ST_AsGeoJSON(d.geom) AS geom
FROM parcel_p_score_v2 s
JOIN parcel_equipements pe ON pe.idu=s.parcelle_id AND pe.piscine
JOIN ortho_detections d ON d.idu=s.parcelle_id AND d.type='piscine'
WHERE s.run_id=:run AND s.tier IN ('brulante','chaude')
  AND pe.piscine_surface_m2 BETWEEN 15 AND 60
ORDER BY s.parcelle_id, d.surface_m2 DESC
"""
SQL_TEMOIN = """
SELECT DISTINCT ON (s.parcelle_id) s.parcelle_id AS idu, s.tier,
       round(pe.piscine_surface_m2::numeric,1) AS surf, round(pe.piscine_confiance::numeric,3) AS conf,
       ST_AsGeoJSON(d.geom) AS geom
FROM parcel_p_score_v2 s
JOIN parcel_equipements pe ON pe.idu=s.parcelle_id AND pe.piscine
JOIN ortho_detections d ON d.idu=s.parcelle_id AND d.type='piscine'
WHERE s.run_id=:run AND s.tier IN ('brulante','chaude')
  AND pe.piscine_surface_m2 < 15
ORDER BY s.parcelle_id, d.surface_m2 DESC
"""


def _select() -> list[dict]:
    with engine().connect() as c:
        bande = [dict(r) for r in c.execute(text(SQL_BANDE), {"run": RUN}).mappings().all()]
        temoin = [dict(r) for r in c.execute(text(SQL_TEMOIN), {"run": RUN}).mappings().all()]
    # 17 en bande : stratifier par commune (répartition), puis compléter par surface décroissante
    bande.sort(key=lambda r: (r["idu"][:5], -r["surf"]))
    par_com: dict[str, list] = {}
    for r in bande:
        par_com.setdefault(r["idu"][:5], []).append(r)
    sel_bande, i = [], 0
    while len(sel_bande) < 17 and any(par_com.values()):
        for com in sorted(par_com):
            if par_com[com]:
                sel_bande.append(par_com[com].pop(0))
                if len(sel_bande) >= 17:
                    break
        i += 1
        if i > 40:
            break
    for r in sel_bande:
        r["classe"] = "BANDE [15;60] → déclassée"
    # 3 témoins : les plus proches du plancher (surface la plus haute sous 15)
    temoin.sort(key=lambda r: -r["surf"])
    sel_temoin = temoin[:3]
    for r in sel_temoin:
        r["classe"] = "TÉMOIN sous 15 m² → conservée (écartée par le plancher)"
    return sel_bande + sel_temoin


def carte(cl, geojson: str) -> str:
    rings = _rings(json.loads(geojson))
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats)); zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= VIEW_W * 0.35 and (y1 - y0) <= VIEW_H * 0.35:
            zoom = z; break
    cx, cy = _lonlat_to_px((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2, zoom)
    left, top = cx - VIEW_W/2, cy - VIEW_H/2
    tiles = []
    for tx in range(int(left//TILE_PX), int((left+VIEW_W)//TILE_PX)+1):
        for ty in range(int(top//TILE_PX), int((top+VIEW_H)//TILE_PX)+1):
            try:
                img = _fetch_tile(zoom, tx, ty, CACHE, cl, tile_url=IGN_ORTHO_URL, prefix="ign")
            except Exception:
                img = None
            if img:
                tiles.append((round(tx*TILE_PX-left), round(ty*TILE_PX-top),
                              "data:image/jpeg;base64," + base64.b64encode(img).decode()))
    imgs = "".join(f"<image x='{x}' y='{y}' width='{TILE_PX}' height='{TILE_PX}' href='{h}'/>"
                   for x, y, h in tiles)
    polys = []
    for ring in rings:
        pts = " ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}"
                       for lo, la in ring)
        polys.append(f"<polygon points='{pts}' fill='#3AA0FF33' stroke='#3AA0FF' stroke-width='2.5'/>")
    return (f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='0 0 {VIEW_W} {VIEW_H}' "
            f"style='border-radius:10px'>{imgs}{''.join(polys)}</svg>")


CSS = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
       "h1{font-size:19px;color:#3AA0FF}.sub{color:#8fa} .card{margin:16px 0;padding:14px;"
       "background:#111814;border-radius:12px;display:flex;gap:16px;align-items:flex-start}"
       ".meta{min-width:280px}.k{color:#7d9;font-size:12px}.temoin{border:1px solid #E8B25A}")


def main() -> None:
    rows = _select()
    cards = []
    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as cl:
        for i, r in enumerate(rows, 1):
            svg = carte(cl, r["geom"])
            temoin = "temoin" in r["classe"].lower()
            cards.append(
                f"<div class='card {'temoin' if temoin else ''}'>"
                f"<div class='meta'><div class='k'>#{i} — {r['idu'][:5]}</div>"
                f"<h1 style='margin:4px 0'>{r['idu']}</h1>"
                f"<div>tier servi : <b>{r['tier']}</b></div>"
                f"<div>piscine détectée : <b>{r['surf']} m²</b> (confiance {r['conf']})</div>"
                f"<div class='sub' style='margin-top:8px'>{r['classe']}</div></div>"
                f"{svg}</div>")
    n_bande = sum(1 for r in rows if "BANDE" in r["classe"])
    n_temoin = len(rows) - n_bande
    html = (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>"
            f"<h1>M39 — Déck ortho de vérification (dette #13)</h1>"
            f"<div class='sub'>{len(rows)} parcelles : {n_bande} en bande [15;60] m² (déclassées "
            f"par la règle) + {n_temoin} témoins sous 15 m² (conservées). Ortho IGN 2025 (PVA "
            f"21/07–02/08/2025). Polygone = piscine détectée (V0+FLAIR/probe, couche 90,7 %). "
            f"Vic tranche : vraie piscine ou FP ?</div>{''.join(cards)}")
    Path(OUT).write_text(html, encoding="utf-8")
    print(f"✓ deck écrit : {OUT} ({len(rows)} vignettes, {n_bande} bande + {n_temoin} témoins)")


if __name__ == "__main__":
    main()
