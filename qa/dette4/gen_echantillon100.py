"""Dette #4 — ÉCHANTILLON ALÉATOIRE REPRODUCTIBLE de 100 têtes servies « invisibles »
(emprise couche batiment < 20 m², AUCUN indice piscine/PV/DVF — jamais suspectées), pour
mesurer LE TAUX D'ERREUR RÉEL de la couche par lecture ortho (mandat Vic 04/08).

Tirage : brûlantes+chaudes du run servi, ORDER BY md5(idu||'974') LIMIT 100 — déterministe,
rejouable. Sortie : /tmp/ech100.html (grilles 2×2, contour parcelle + emprise couche) puis
qa/dette4/shot_grids.mjs → /tmp/ech100/grid_NN.png (une image par grille de 4, à classer).
Lecture seule. RIEN n'est corrigé (consigne).
"""
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import httpx
from pathlib import Path
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, TILE_PX,
                                        ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)

CACHE = Path("/tmp/labuse_tiles"); CACHE.mkdir(exist_ok=True)
OUT = "/tmp/ech100.html"
W, H = 560, 380          # mini-carte (grille 2×2)

SQL = """
WITH ind AS (
  SELECT idu FROM ortho_detections WHERE validation IS DISTINCT FROM 'faux_positif' AND idu IS NOT NULL
  UNION SELECT id_parcelle FROM dvf_mutations_parcelle WHERE surface_reelle_bati>0)
SELECT s.parcelle_id idu, p.commune, s.tier, s.rang, ST_Area(p.geom_2975) surf,
       COALESCE(b.emprise_bati_m2,0) emp,
       ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) g
FROM parcel_p_score_v2 s
JOIN parcels p ON p.idu=s.parcelle_id
LEFT JOIN p_model_bati b ON b.idu=s.parcelle_id
WHERE s.run_id='q_v8_calibre' AND s.tier IN ('brulante','chaude')
  AND COALESCE(b.emprise_bati_m2,0) < 20
  AND s.parcelle_id NOT IN (SELECT idu FROM ind)
ORDER BY md5(s.parcelle_id || '974') LIMIT 100
"""
SQL_BATI = """
SELECT ST_AsGeoJSON(ST_Transform(ST_Intersection(b.geom_2975, p.geom_2975), 4326))
FROM spatial_layers b, parcels p
WHERE p.idu=:i AND b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)
"""

def poly(g, zoom, left, top, fill, stroke, sw):
    out = []
    gj = json.loads(g)
    if gj.get("type") not in ("Polygon", "MultiPolygon"):
        return ""
    for ring in _rings(gj):
        pts = " ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}"
                       for lo, la in ring)
        out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
    return "".join(out)

def carte(s, cl, idu, g):
    rings = _rings(json.loads(g))
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats)); zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= W * 0.55 and (y1 - y0) <= H * 0.55:
            zoom = z; break
    cx, cy = _lonlat_to_px((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2, zoom)
    left, top = cx - W/2, cy - H/2
    tiles = []
    for tx in range(int(left//TILE_PX), int((left+W)//TILE_PX)+1):
        for ty in range(int(top//TILE_PX), int((top+H)//TILE_PX)+1):
            try:
                img = _fetch_tile(zoom, tx, ty, CACHE, cl, tile_url=IGN_ORTHO_URL, prefix="ign")
            except Exception:
                img = None
            if img:
                tiles.append((round(tx*TILE_PX-left), round(ty*TILE_PX-top),
                              "data:image/jpeg;base64," + base64.b64encode(img).decode()))
    imgs = "".join(f"<image x='{x}' y='{y}' width='{TILE_PX}' height='{TILE_PX}' href='{h}'/>"
                   for x, y, h in tiles)
    couche = "".join(poly(bg, zoom, left, top, "#E8B44C66", "#E8B44C", 2)
                     for (bg,) in s.execute(text(SQL_BATI), {"i": idu}).all() if bg)
    contour = poly(g, zoom, left, top, "none", "#5CE6A1", 3)
    # recadrage : la parcelle occupe ~38 % de la vue (même correctif que la revue des 46)
    x0, y1p = _lonlat_to_px(bbox[0], bbox[1], zoom); x1, y0p = _lonlat_to_px(bbox[2], bbox[3], zoom)
    pw, ph = abs(x1-x0), abs(y1p-y0p)
    vw = min(W, max(pw / 0.38, 200.0)); vh = min(H, max(ph / 0.38, vw * H / W))
    vw = max(vw, vh * W / H)
    vb = f"{(W-vw)/2:.1f} {(H-vh)/2:.1f} {vw:.1f} {vh:.1f}"
    return (f"<svg width='{W}' height='{H}' viewBox='{vb}'>{imgs}{couche}{contour}</svg>")

CSS = ("body{font:12px -apple-system,sans-serif;background:#fff;color:#111;margin:0}"
       ".grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px;width:1160px}"
       ".cell p{margin:1px 0;font:600 12px ui-monospace,Menlo,monospace}"
       ".cell span{font-weight:400;color:#555;font-family:-apple-system,sans-serif}")

with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
    rows = s.execute(text(SQL)).mappings().all()
    cells = []
    for n, r in enumerate(rows, 1):
        svg = carte(s, cl, r["idu"], r["g"])
        cells.append(f"<div class='cell'><p>#{n:03d} {r['idu']} <span>{r['commune']} · {r['tier']} "
                     f"rang {r['rang']} · {r['surf']:.0f} m² · couche {r['emp']:.0f} m²</span></p>{svg}</div>")
grids = ["<div class='grid'>" + "".join(cells[i:i+4]) + "</div>" for i in range(0, len(cells), 4)]
open(OUT, "w", encoding="utf-8").write(
    f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>" + "".join(grids))
print(f"{len(cells)} parcelles, {len(grids)} grilles → {OUT}")
