"""Dette #4 — revue des 46 têtes suspectes, STANDARD O12 (division_review) : ortho IGN +
contour parcelle + emprise couche bâtiment + géométrie de l'indice (piscine/PV).

Population = la MESURE pré-bascule (top 1000 rangs de q_v8_calibre_pre_pond, couche < 20 m²,
preuve indépendante piscine/PV/DVF-bâti). Tiers/rangs affichés = SERVIS (q_v8_calibre pondéré).
Tri : brûlantes servies, puis chaudes, puis le reste — rang croissant.

Sortie : /tmp/revue_suspectes.html (intermédiaire) → qa/dette4/revue_suspectes.pdf via
qa/dette4/print_pdf.mjs (Chrome, pattern pack_print_clair). Lecture seule, rien de déclassé.
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
OUT_HTML = "/tmp/revue_suspectes.html"

SQL = """
WITH pop AS (
  SELECT a.parcelle_id idu FROM parcel_p_score_v2 a
  LEFT JOIN p_model_bati b ON b.idu=a.parcelle_id
  WHERE a.run_id='q_v8_calibre_pre_pond' AND a.rang<=1000 AND COALESCE(b.emprise_bati_m2,0)<20),
det AS (SELECT idu, bool_or(type='piscine') pisc, bool_or(type='pv') pv,
               max(confiance) FILTER (WHERE type='piscine') conf
        FROM ortho_detections WHERE validation IS DISTINCT FROM 'faux_positif' GROUP BY idu),
dvfb AS (SELECT id_parcelle idu, max(date_mutation) dm, max(surface_reelle_bati) srb
         FROM dvf_mutations_parcelle WHERE surface_reelle_bati>0 GROUP BY 1)
SELECT pop.idu, p.commune, ST_Area(p.geom_2975) surf,
       COALESCE(b.emprise_bati_m2,0) emprise,
       s.tier, s.rang,
       d.pisc, d.conf, d.pv, v.srb, v.dm,
       ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) g
FROM pop JOIN parcels p ON p.idu=pop.idu
LEFT JOIN p_model_bati b ON b.idu=pop.idu
JOIN parcel_p_score_v2 s ON s.parcelle_id=pop.idu AND s.run_id='q_v8_calibre'
LEFT JOIN det d ON d.idu=pop.idu LEFT JOIN dvfb v ON v.idu=pop.idu
WHERE (d.idu IS NOT NULL OR v.idu IS NOT NULL)
  -- déjà arbitrées (retrait des 14 + CH1893) : exceptions journalisées → hors revue
  AND pop.idu NOT IN (SELECT idu FROM served_run_exceptions WHERE run_id='q_v8_calibre')
ORDER BY CASE s.tier WHEN 'brulante' THEN 0 WHEN 'chaude' THEN 1 ELSE 2 END,
         COALESCE(s.rang, 999999999)
"""

# géométries d'appui : bâtiments ∩ parcelle et détections ∩ parcelle (4326 pour le rendu)
SQL_BATI = """
SELECT ST_AsGeoJSON(ST_Transform(ST_Intersection(b.geom_2975, p.geom_2975), 4326))
FROM spatial_layers b, parcels p
WHERE p.idu=:i AND b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)
"""
SQL_DET = """
SELECT d.type, ST_AsGeoJSON(ST_Transform(d.geom_2975, 4326))
FROM ortho_detections d, parcels p
WHERE p.idu=:i AND d.validation IS DISTINCT FROM 'faux_positif'
  AND d.geom_2975 IS NOT NULL AND ST_Intersects(d.geom_2975, p.geom_2975)
"""

CSS = ("@page{size:A4;margin:10mm}body{font:12px -apple-system,sans-serif;background:#fff;color:#1a221e;margin:0}"
       ".cover{page-break-after:always;padding:28mm 6mm}.cover h1{font-size:22px;color:#0c4d33}"
       ".cover p{font-size:13px;line-height:1.6;max-width:640px}"
       ".card{page-break-after:always;padding:2mm 0}"
       ".idu{font:600 15px ui-monospace,Menlo,monospace;color:#0c1f16;margin:0}"
       ".t-brulante{color:#c2371f;font-weight:700}.t-chaude{color:#0c7a4d;font-weight:700}"
       ".kv{font-size:12px;margin:3px 0 6px;line-height:1.55}.kv b{color:#333}"
       ".muted{color:#667}"
       ".legend{font-size:10.5px;color:#556;margin:4px 0 0}"
       ".legend span{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px -1px 10px}")


def poly(g, zoom, left, top, fill, stroke, sw, dash=""):
    out = []
    gj = json.loads(g)
    if gj.get("type") not in ("Polygon", "MultiPolygon"):
        return ""
    for ring in _rings(gj):
        pts = " ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}"
                       for lo, la in ring)
        out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}' {dash}/>")
    return "".join(out)


def carte(s, cl, idu, g):
    rings = _rings(json.loads(g))
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats)); zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):     # standard O12 : la parcelle occupe ~1/2 vue
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
    dets = "".join(poly(dg, zoom, left, top,
                        "#25c8e055" if t == "piscine" else "#7de85f55",
                        "#0aa8c4" if t == "piscine" else "#3fae1f", 2.5)
                   for t, dg in s.execute(text(SQL_DET), {"i": idu}).all() if dg)
    contour = poly(g, zoom, left, top, "none", "#5CE6A1", 3)
    # ZOOM_MAX=18 (~0,6 m/px) laisse une parcelle de 300 m² minuscule (vue ~430 m) et rend la
    # piscine (10-15 m²) invisible → RECADRAGE viewBox : la parcelle occupe ~35 % de la vue,
    # tuiles inchangées (léger flou d'upscale acceptable), overlays vectoriels nets.
    x0, y1p = _lonlat_to_px(bbox[0], bbox[1], zoom); x1, y0p = _lonlat_to_px(bbox[2], bbox[3], zoom)
    pw, ph = abs(x1 - x0), abs(y1p - y0p)
    vw = min(VIEW_W, max(pw / 0.35, 240.0))
    vh = min(VIEW_H, max(ph / 0.35, vw * VIEW_H / VIEW_W))
    vw = max(vw, vh * VIEW_W / VIEW_H)              # conserver le ratio A4 de la vue
    vb = f"{(VIEW_W - vw) / 2:.1f} {(VIEW_H - vh) / 2:.1f} {vw:.1f} {vh:.1f}"
    return (f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='{vb}' "
            f"style='border-radius:6px'>{imgs}{couche}{dets}{contour}</svg>")


def main():
    cards = []
    with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
        rows = s.execute(text(SQL)).mappings().all()
        n_b = sum(1 for r in rows if r["tier"] == "brulante")
        n_c = sum(1 for r in rows if r["tier"] == "chaude")
        for r in rows:
            preuves = []
            if r["pisc"]:
                preuves.append(f"piscine détectée (ortho, confiance {r['conf']:.2f})")
            if r["pv"]:
                preuves.append("panneaux PV détectés (ortho)")
            if r["srb"]:
                preuves.append(f"vente DVF bâtie : {r['srb']:.0f} m² le {r['dm']}")
            pct = 100.0 * float(r["emprise"]) / float(r["surf"]) if r["surf"] else 0.0
            svg = carte(s, cl, r["idu"], r["g"])
            cards.append(
                f"<div class='card'><p class='idu'>{r['idu']} "
                f"<span class='muted'>· {r['commune']}</span></p>"
                f"<p class='kv'><b>Tier servi</b> <span class='t-{r['tier']}'>{r['tier']}</span>"
                f" · <b>rang</b> {r['rang']} · <b>surface</b> {r['surf']:.0f} m²"
                f" · <b>emprise couche bâtiment</b> {r['emprise']:.0f} m² ({pct:.1f} %)<br>"
                f"<b>Indice</b> : {' + '.join(preuves)}</p>"
                f"{svg}"
                f"<p class='legend'>légende :<span style='background:#5CE6A1'></span>parcelle"
                f"<span style='background:#E8B44C'></span>emprise couche bâtiment"
                f"<span style='background:#25c8e0'></span>piscine détectée"
                f"<span style='background:#7de85f'></span>PV détecté — "
                f"une maison visible SANS emprise orange = couche lacunaire (type CH1893)</p></div>")
    cover = (f"<div class='cover'><h1>Dette #4 — revue des {len(rows)} suspectes restantes</h1>"
             f"<p>Couche bâtiment &lt; 20 m² MAIS preuve indépendante d'habitation (piscine/PV ortho, "
             f"vente DVF bâtie), sur le top 1 000 rangs de la mesure pré-bascule. <b>Les 14 brûlantes "
             f"bâties sont RETIRÉES (verdict Vic 04/08 : declasse_non_constructible, exceptions "
             f"journalisées) — hors de ce document.</b></p>"
             f"<p><b>Ordre : {n_b} brûlante(s), puis {n_c} chaudes, puis {len(rows)-n_b-n_c} autres</b> "
             f"(écartées/déclassées/a_creuser) — rang croissant. Tiers et rangs = SERVIS (q_v8_calibre "
             f"pondéré, post-retrait).</p>"
             f"<p>Standard cartes O12 : ortho IGN, contour parcelle (vert), emprise couche bâtiment "
             f"(orange), indice (cyan piscine / vert PV). Une maison visible sans orange = couche "
             f"lacunaire. Rien n'est déclassé par ce document — arbitrage Vic parcelle par parcelle.</p></div>")
    html = (f"<!doctype html><meta charset='utf-8'><title>Dette #4 — 46 suspectes</title>"
            f"<style>{CSS}</style>{cover}" + "".join(cards))
    open(OUT_HTML, "w", encoding="utf-8").write(html)
    print(f"{len(rows)} cartes ({n_b} brûlantes, {n_c} chaudes) → {OUT_HTML}")


if __name__ == "__main__":
    main()
