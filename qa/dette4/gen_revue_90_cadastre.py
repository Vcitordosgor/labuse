"""Dette #4 — revue des 90 têtes servies que le CADASTRE Etalab 2026-06 voit bâties
(alors que la couche BD TOPO les voit vides et qu'aucun indice piscine/PV/DVF n'existe).

Arbitrage Vic 04/08 : revue-exceptions, PAS de déclassement automatique — « une source qui ne
voit que 3 % de notre angle mort peut aussi se tromper dans l'autre sens ».
Standard O12 : ortho IGN + contour parcelle (vert) + emprise couche BD TOPO (orange) +
BÂTIMENT CADASTRE (violet, l'indice). Cartouche : IDU, commune, surface, emprise couche,
surface cadastre intersectée, tier + rang servis. Tri : tier puis rang.
Pré-requis : table qa_cadastre_bati chargée (642 344 bâtiments, millésime 2026-06-01).
Sortie : /tmp/revue_90.html → qa/dette4/revue_90_cadastre.pdf (print_pdf.mjs).
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
OUT_HTML = "/tmp/revue_90.html"

SQL = """
WITH ind AS (
  SELECT idu FROM ortho_detections WHERE validation IS DISTINCT FROM 'faux_positif' AND idu IS NOT NULL
  UNION SELECT id_parcelle FROM dvf_mutations_parcelle WHERE surface_reelle_bati>0),
pop AS (SELECT s.parcelle_id idu, s.tier, s.rang FROM parcel_p_score_v2 s
  LEFT JOIN p_model_bati b ON b.idu=s.parcelle_id
  WHERE s.run_id='q_v8_calibre' AND s.tier IN ('brulante','chaude')
    AND COALESCE(b.emprise_bati_m2,0)<20 AND s.parcelle_id NOT IN (SELECT idu FROM ind))
SELECT pop.idu, p.commune, pop.tier, pop.rang, ST_Area(p.geom_2975) surf,
       COALESCE(bm.emprise_bati_m2,0) emprise,
       cad.m2 AS cad_m2,
       ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) g
FROM pop JOIN parcels p ON p.idu=pop.idu
LEFT JOIN p_model_bati bm ON bm.idu=pop.idu
JOIN LATERAL (
  SELECT sum(ST_Area(ST_Transform(ST_Intersection(q.geom, ST_Transform(p.geom_2975,4326)),2975))) m2
  FROM qa_cadastre_bati q WHERE ST_Intersects(q.geom, ST_Transform(p.geom_2975,4326))) cad ON cad.m2 > 20
ORDER BY CASE pop.tier WHEN 'brulante' THEN 0 ELSE 1 END, pop.rang
"""
SQL_BATI = """
SELECT ST_AsGeoJSON(ST_Transform(ST_Intersection(b.geom_2975, p.geom_2975), 4326))
FROM spatial_layers b, parcels p
WHERE p.idu=:i AND b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)
"""
SQL_CAD = """
SELECT ST_AsGeoJSON(ST_Intersection(q.geom, ST_Transform(p.geom_2975,4326)))
FROM qa_cadastre_bati q, parcels p
WHERE p.idu=:i AND ST_Intersects(q.geom, ST_Transform(p.geom_2975,4326))
"""

CSS = ("@page{size:A4;margin:10mm}body{font:12px -apple-system,sans-serif;background:#fff;color:#1a221e;margin:0}"
       ".cover{page-break-after:always;padding:28mm 6mm}.cover h1{font-size:22px;color:#0c4d33}"
       ".cover p{font-size:13px;line-height:1.6;max-width:640px}"
       ".card{page-break-after:always;padding:2mm 0}"
       ".idu{font:600 15px ui-monospace,Menlo,monospace;color:#0c1f16;margin:0}"
       ".t-brulante{color:#c2371f;font-weight:700}.t-chaude{color:#0c7a4d;font-weight:700}"
       ".kv{font-size:12px;margin:3px 0 6px;line-height:1.55}.kv b{color:#333}.muted{color:#667}"
       ".legend{font-size:10.5px;color:#556;margin:4px 0 0}"
       ".legend span{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px -1px 10px}")


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
        if (x1 - x0) <= VIEW_W * 0.55 and (y1 - y0) <= VIEW_H * 0.55:
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
    couche = "".join(poly(bg, zoom, left, top, "#E8B44C55", "#E8B44C", 2)
                     for (bg,) in s.execute(text(SQL_BATI), {"i": idu}).all() if bg)
    cad = "".join(poly(cg, zoom, left, top, "#8b5cf655", "#7c3aed", 2.5)
                  for (cg,) in s.execute(text(SQL_CAD), {"i": idu}).all() if cg)
    contour = poly(g, zoom, left, top, "none", "#5CE6A1", 3)
    x0, y1p = _lonlat_to_px(bbox[0], bbox[1], zoom); x1, y0p = _lonlat_to_px(bbox[2], bbox[3], zoom)
    pw, ph = abs(x1 - x0), abs(y1p - y0p)
    vw = min(VIEW_W, max(pw / 0.35, 240.0)); vh = min(VIEW_H, max(ph / 0.35, vw * VIEW_H / VIEW_W))
    vw = max(vw, vh * VIEW_W / VIEW_H)
    vb = f"{(VIEW_W - vw) / 2:.1f} {(VIEW_H - vh) / 2:.1f} {vw:.1f} {vh:.1f}"
    return (f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='{vb}' "
            f"style='border-radius:6px'>{imgs}{couche}{cad}{contour}</svg>")


def main():
    cards = []
    with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
        rows = s.execute(text(SQL)).mappings().all()
        n_b = sum(1 for r in rows if r["tier"] == "brulante")
        for r in rows:
            pct = 100.0 * float(r["emprise"]) / float(r["surf"]) if r["surf"] else 0.0
            svg = carte(s, cl, r["idu"], r["g"])
            cards.append(
                f"<div class='card'><p class='idu'>{r['idu']} <span class='muted'>· {r['commune']}</span></p>"
                f"<p class='kv'><b>Tier servi</b> <span class='t-{r['tier']}'>{r['tier']}</span>"
                f" · <b>rang</b> {r['rang']} · <b>surface</b> {r['surf']:.0f} m²"
                f" · <b>emprise couche BD TOPO</b> {r['emprise']:.0f} m² ({pct:.1f} %)<br>"
                f"<b>Indice</b> : bâtiment CADASTRE (2026-06) sur la parcelle — {r['cad_m2']:.0f} m² intersectés</p>"
                f"{svg}"
                f"<p class='legend'>légende :<span style='background:#5CE6A1'></span>parcelle"
                f"<span style='background:#E8B44C'></span>emprise couche BD TOPO"
                f"<span style='background:#7c3aed'></span>bâtiment cadastre (l'indice) — "
                f"violet SANS maison visible = erreur cadastre possible (l'inverse du type CH1893)</p></div>")
    cover = (f"<div class='cover'><h1>Dette #4 — les {len(rows)} têtes vues bâties par le CADASTRE</h1>"
             f"<p>Têtes servies (brûlantes+chaudes), couche BD TOPO &lt; 20 m², AUCUN indice piscine/PV/DVF — "
             f"mais le cadastre Etalab 2026-06 y voit un bâtiment (&gt; 20 m² intersectés).</p>"
             f"<p><b>Ordre : {n_b} brûlante(s) puis {len(rows)-n_b} chaudes</b>, rang croissant. "
             f"Revue-exceptions (arbitrage Vic 04/08) : PAS de déclassement automatique — le cadastre "
             f"ne voit que 3 % de l'angle mort mesuré et peut se tromper dans l'autre sens. "
             f"Vérifier à l'ortho : bâtiment violet AVEC maison visible = à retirer (type CH1893) ; "
             f"violet SANS maison = erreur cadastre (ne pas retirer).</p></div>")
    html = (f"<!doctype html><meta charset='utf-8'><title>Dette #4 — 90 cadastre</title>"
            f"<style>{CSS}</style>{cover}" + "".join(cards))
    open(OUT_HTML, "w", encoding="utf-8").write(html)
    print(f"{len(rows)} cartes ({n_b} brûlantes) → {OUT_HTML}")


if __name__ == "__main__":
    main()
