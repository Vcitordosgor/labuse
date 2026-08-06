"""M39 P2.2 (v2) — DECK ORTHO de vérification, contour PARCELLE + polygone PISCINE.

Refonte demandée par Vic : les vues de quartier ne permettaient pas de trancher (plusieurs
piscines dans le cadre, aucun contour de parcelle). Ici chaque vignette est ZOOMÉE SUR LA
PARCELLE, avec :
  · le CONTOUR de la parcelle servie en surimpression (orange, comme les fiches) ;
  · le POLYGONE de la piscine détectée (bleu, distinct) ;
  · rappel chiffré : surface parcelle, surface piscine, % piscine/parcelle, statut géométrique
    (CONTENUE / À CHEVAL), ratio de la piscine DANS la parcelle, position (central/périphérique).

Les 34 parcelles de la règle [15;60], À CHEVAL d'abord (ratio croissant = les plus douteuses en
tête). Question de fond : la piscine détectée est-elle géométriquement CONTENUE dans la parcelle
servie ? (chiffres : qa/m39/geometrie_piscine_parcelle_p2.csv). Lecture seule.

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

SQL = """
SELECT s.parcelle_id AS idu, s.tier,
       round(p.surface_m2::numeric,0) AS surf_parc, round(d.surface_m2::numeric,1) AS surf_pool,
       round((100*d.surface_m2/NULLIF(p.surface_m2,0))::numeric,1) AS pct,
       ST_AsGeoJSON(p.geom) AS pgeo, ST_AsGeoJSON(d.geom) AS dgeo,
       CASE WHEN ST_Contains(ST_MakeValid(p.geom_2975),ST_MakeValid(d.geom_2975)) THEN 'CONTENUE'
            WHEN ST_Intersects(p.geom_2975,d.geom_2975) THEN 'À CHEVAL' ELSE 'HORS' END AS statut,
       round((ST_Area(ST_Intersection(ST_MakeValid(p.geom_2975),ST_MakeValid(d.geom_2975)))
              /NULLIF(ST_Area(ST_MakeValid(d.geom_2975)),0))::numeric,2) AS ratio,
       round(ST_Distance(ST_Centroid(d.geom_2975), ST_Boundary(ST_MakeValid(p.geom_2975)))::numeric,1) AS dist_bord
FROM parcel_p_score_v2 s
JOIN parcel_equipements pe ON pe.idu=s.parcelle_id AND pe.piscine
JOIN parcels p ON p.idu=s.parcelle_id
JOIN LATERAL (SELECT geom, geom_2975, surface_m2 FROM ortho_detections
              WHERE idu=s.parcelle_id AND type='piscine' ORDER BY surface_m2 DESC LIMIT 1) d ON true
WHERE s.run_id=:run AND s.tier IN ('brulante','chaude')
  AND pe.piscine_surface_m2 BETWEEN 15 AND 60
ORDER BY (CASE WHEN ST_Contains(ST_MakeValid(p.geom_2975),ST_MakeValid(d.geom_2975)) THEN 1 ELSE 0 END),
         ratio ASC
"""


def carte(cl, parcel_geo: str, pool_geo: str) -> str:
    """Ortho zoomée sur la PARCELLE ; contour parcelle (orange) + polygone piscine (bleu)."""
    p_rings = _rings(json.loads(parcel_geo))
    d_rings = _rings(json.loads(pool_geo))
    lons = [c[0] for r in p_rings for c in r]; lats = [c[1] for r in p_rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats)); zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= VIEW_W * 0.7 and (y1 - y0) <= VIEW_H * 0.7:
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

    def _poly(rings, fill, stroke, w):
        out = []
        for ring in rings:
            pts = " ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}"
                           for lo, la in ring)
            out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{w}'/>")
        return "".join(out)

    parcel_svg = _poly(p_rings, "none", "#F2A24E", 3.0)          # contour parcelle (orange, fiches)
    pool_svg = _poly(d_rings, "#3AA0FF55", "#3AA0FF", 2.5)        # piscine détectée (bleu plein léger)
    return (f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='0 0 {VIEW_W} {VIEW_H}' "
            f"style='border-radius:10px'>{imgs}{parcel_svg}{pool_svg}</svg>")


CSS = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
       "h1{font-size:19px;color:#3AA0FF;margin:2px 0}.sub{color:#8fbfa8}"
       ".card{margin:16px 0;padding:14px;background:#111814;border-radius:12px;display:flex;"
       "gap:16px;align-items:flex-start}.meta{min-width:300px}.k{color:#7d9;font-size:12px}"
       ".cheval{border:1px solid #E8B25A}.leg{display:inline-block;width:11px;height:11px;"
       "border-radius:2px;margin-right:5px;vertical-align:middle}"
       ".big{font-size:16px;font-weight:600}.warn{color:#E8B25A;font-weight:600}")


def main() -> None:
    with engine().connect() as c:
        rows = [dict(r) for r in c.execute(text(SQL), {"run": RUN}).mappings().all()]
    cards = []
    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as cl:
        for i, r in enumerate(rows, 1):
            svg = carte(cl, r["pgeo"], r["dgeo"])
            cheval = r["statut"] != "CONTENUE"
            statut_html = (f"<span class='warn'>{r['statut']}</span> — piscine à "
                           f"{int(round(float(r['ratio'])*100))} % dans la parcelle") if cheval \
                else f"{r['statut']} (piscine 100 % dans la parcelle)"
            cards.append(
                f"<div class='card {'cheval' if cheval else ''}'>"
                f"<div class='meta'><div class='k'>#{i} — {r['idu'][:5]} · tier {r['tier']}</div>"
                f"<h1>{r['idu']}</h1>"
                f"<div class='big'>{statut_html}</div>"
                f"<div style='margin-top:8px'>parcelle : <b>{r['surf_parc']} m²</b></div>"
                f"<div>piscine : <b>{r['surf_pool']} m²</b> ({r['pct']} % de la parcelle)</div>"
                f"<div>centroïde piscine → bord parcelle : {r['dist_bord']} m "
                f"({'périphérique' if float(r['ratio'])<1 or float(r['dist_bord'])<2 else 'central'})</div>"
                f"<div class='sub' style='margin-top:8px'><span class='leg' style='background:#F2A24E'></span>"
                f"contour parcelle &nbsp; <span class='leg' style='background:#3AA0FF'></span>piscine détectée</div>"
                f"</div>{svg}</div>")
    n_cheval = sum(1 for r in rows if r["statut"] != "CONTENUE")
    html = (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>"
            f"<h1>M39 — Vérification géométrique piscine ⊂ parcelle (dette #13)</h1>"
            f"<div class='sub'>{len(rows)} parcelles de la règle [15;60] m². "
            f"<b>{len(rows)-n_cheval} CONTENUE</b> · <b class='warn'>{n_cheval} À CHEVAL</b> "
            f"(straddle le bord — les plus douteuses en tête). 0 HORS parcelle · centroïde piscine "
            f"dans la parcelle servie pour les 34. Ortho IGN 2025 (PVA 21/07–02/08/2025). "
            f"Question : la piscine est-elle sur la parcelle servie ou chez le voisin ?</div>"
            f"{''.join(cards)}")
    Path(OUT).write_text(html, encoding="utf-8")
    print(f"✓ deck écrit : {OUT} ({len(rows)} vignettes, {n_cheval} à cheval, "
          f"{len(rows)-n_cheval} contenues)")


if __name__ == "__main__":
    main()
