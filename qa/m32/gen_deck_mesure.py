"""M32 Phase C — deck des 20 plus gros mouvements de la mesure à blanc (q_v8_calibre →
q_v13_m32_mesure). Carte ortho IGN (harnais division_review) + contour parcelle + cartouche
avant→après tier/rang, cause unique, millésime PVA. Ordre (Vic) : dé-déclassées AU d'abord
(entrent en tête), puis recalibrations brûlante, puis la sortie. Sortie HTML → print_pdf.mjs.
"""
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import httpx
from pathlib import Path
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, VIEW_W, VIEW_H,
                                        TILE_PX, ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)

CACHE = Path("/tmp/labuse_tiles"); CACHE.mkdir(exist_ok=True)
OUT = os.path.join(os.path.dirname(__file__), "deck_mesure.html")
PVA = "PVA 2025 (vols 21/07–02/08/2025) — ortho IGN"   # millésime vérifié (dette4/gen_discordances)

SQL = """
SELECT a.parcelle_id AS idu, p.commune, a.tier AS avant, b.tier AS apres,
       a.rang AS rang_avant, b.rang AS rang_apres,
       z.zone_lib, s.classe AS au_statut, ST_Area(p.geom_2975) AS surf,
       ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) AS g
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v13_m32_mesure'
JOIN parcels p ON p.idu=a.parcelle_id
LEFT JOIN parcel_zone_plu z ON z.idu=a.parcelle_id
LEFT JOIN parcel_au_statut s ON s.idu=a.parcelle_id
WHERE a.run_id='q_v8_calibre' AND a.tier IS DISTINCT FROM b.tier
  AND (a.tier IN ('brulante','chaude') OR b.tier IN ('brulante','chaude'))
ORDER BY CASE
    WHEN a.tier LIKE 'declasse_au%' AND b.tier IN ('brulante','chaude') THEN 0   -- dé-déclassées AU
    WHEN b.tier = 'brulante' THEN 1                                              -- recalibrations brûlante
    WHEN a.tier IN ('brulante','chaude') THEN 2                                  -- sortie de tête
    ELSE 3 END,
  COALESCE(b.rang, 999999999)
LIMIT 20
"""


def cause(avant, au_statut):
    if avant and avant.startswith("declasse_au"):
        return "déclassement AU RETIRÉ (commune calibrée → conditionnelle_operation servable)"
    return "recalibration / départage (effet de bord du re-scoring)"


def carte(cl, g):
    rings = _rings(json.loads(g))
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= VIEW_W * 0.6 and (y1 - y0) <= VIEW_H * 0.6:
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
        polys.append(f"<polygon points='{pts}' fill='#5CE6A122' stroke='#5CE6A1' stroke-width='2.5'/>")
    return (f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='0 0 {VIEW_W} {VIEW_H}' "
            f"style='border-radius:10px'>{imgs}{''.join(polys)}</svg>")


CSS = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
       "h1{font-size:18px;color:#5CE6A1}.card{margin:18px 0;padding:14px;background:#111814;"
       "border:1px solid #1f2a24;border-radius:12px;max-width:760px;break-inside:avoid}"
       ".idu{font-family:monospace;font-size:15px;color:#ECF5EF}"
       ".mv{font-weight:600}.mv .av{color:#E8695A}.mv .ap{color:#5CE6A1}"
       ".cause{color:#8FD8B4;font-size:12px;margin:4px 0}.muted{color:#5a6b62;font-size:12px}")

cards = []
with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
    rows = s.execute(text(SQL)).mappings().all()
    for i, r in enumerate(rows, 1):
        note = ""
        if r["idu"] == "97422000AK1442":
            note = " ⚠ override registre M28 (piscine) → ré-appliqué a_creuser à la bascule"
        svg = carte(cl, r["g"])
        cards.append(
            f"<div class='card'><p class='idu'>{i}. {r['idu']} <span class='muted'>{r['commune']}"
            f" · zone {r['zone_lib'] or '—'} · {r['au_statut'] or '—'}</span></p>"
            f"<p class='mv'><span class='av'>{r['avant']}</span> → <span class='ap'>{r['apres']}</span>"
            f" <span class='muted'>rang {r['rang_avant']} → {r['rang_apres']}</span></p>"
            f"<p class='cause'>{cause(r['avant'], r['au_statut'])}{note}</p>"
            f"<p class='muted'>{PVA}</p>{svg}</div>")

html = (f"<!doctype html><meta charset='utf-8'><title>M32 — deck mesure (20 mouvements)</title>"
        f"<style>{CSS}</style><h1>M32 Phase C — mesure à blanc : {len(cards)} plus gros mouvements en tête "
        f"<span class='muted'>(q_v8_calibre → q_v13_m32_mesure, ordre : dé-déclassées AU · recalibr. brûlante · sortie)</span></h1>"
        + "".join(cards))
open(OUT, "w", encoding="utf-8").write(html)
print(f"{len(cards)} cartes → {OUT}")
