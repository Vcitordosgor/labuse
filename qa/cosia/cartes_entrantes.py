"""TRAIN 1 — cartes ortho des MOUVEMENTS EN TÊTE de la pondération (mesure à blanc).

Pour chaque parcelle dont le tier change entre q_v8_calibre et q_v11_regle_apres avec la tête
concernée (brûlante/chaude d'un côté ou de l'autre) : carte ortho IGN (harnais maison
division_review, tuiles cachées /tmp) + contour parcelle + cartouche avant→après, rang, facteur
de pondération, seuil de zone. Sortie : qa/ponderation/cartes_entrantes_recomposition.html. Lecture seule.
"""
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import httpx
from pathlib import Path
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, VIEW_W, VIEW_H,
                                        TILE_PX, ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)
from labuse.faisabilite.au_ouverture import facteur_ponderation, zone_regime, seuil_surface_m2

CACHE = Path("/tmp/labuse_tiles"); CACHE.mkdir(exist_ok=True)
OUT = os.path.join(os.path.dirname(__file__), "cartes_entrantes_recomposition.html")

SQL_MOUV = """
SELECT a.parcelle_id AS idu, p.commune, a.tier AS avant, b.tier AS apres,
       a.rang AS rang_avant, b.rang AS rang_apres,
       (SELECT zone_lib FROM parcel_au_statut x WHERE x.idu=a.parcelle_id) AS zone_lib,
       (SELECT classe FROM parcel_au_statut x WHERE x.idu=a.parcelle_id) AS au_statut,
       ST_Area(p.geom_2975) AS surf,
       ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) AS g
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v11_regle_apres'
JOIN parcels p ON p.idu=a.parcelle_id
WHERE a.run_id='q_v8_calibre' AND a.tier IS DISTINCT FROM b.tier
  AND a.tier NOT IN ('brulante','chaude') AND b.tier IN ('brulante','chaude')
ORDER BY CASE b.tier WHEN 'brulante' THEN 0 ELSE 1 END,
         COALESCE(b.rang,999999)
"""


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
       "@page{size:A4;margin:10mm}h1{font-size:18px;color:#5CE6A1;page-break-after:always}.card{page-break-after:always;margin:18px 0;padding:14px;background:#111814;"
       "border:1px solid #1f2a24;border-radius:12px;max-width:760px}"
       ".idu{font-family:monospace;font-size:15px;color:#ECF5EF}"
       ".mv{font-weight:600}.mv .av{color:#E8695A}.mv .ap{color:#8FA69A}"
       ".muted{color:#5a6b62;font-size:12px}")

cards = []
with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
    rows = s.execute(text(SQL_MOUV)).mappings().all()
    for r in rows:
        insee = r["idu"][:5]
        f = (facteur_ponderation(insee, r["zone_lib"], float(r["surf"]))
             if r["zone_lib"] else None)
        reg = zone_regime(insee, r["zone_lib"]) if r["zone_lib"] else None
        seuil = seuil_surface_m2(reg) if reg else None
        fact_txt = (f"facteur {f:.3f} (manque {(1-f)*100:.0f} % — seuil {seuil:.0f} m², "
                    f"surface {r['surf']:.0f} m²)") if f is not None else "hors pondération (effet de bord recalibration)"
        svg = carte(cl, r["g"])
        cards.append(
            f"<div class='card'><p class='idu'>{r['idu']} <span class='muted'>{r['commune']}"
            f" · zone {r['zone_lib'] or '—'} · {r['au_statut'] or '—'}</span></p>"
            f"<p class='mv'><span class='av'>{r['avant']}</span> → <span class='ap'>{r['apres']}</span>"
            f" <span class='muted'>rang {r['rang_avant']} → {r['rang_apres']}</span></p>"
            f"<p class='muted'>{fact_txt}</p>{svg}</div>")

html = (f"<!doctype html><meta charset='utf-8'><title>Pondération — mouvements en tête</title>"
        f"<style>{CSS}</style><h1>Pondération option B — {len(cards)} mouvement(s) en tête "
        f"<span class='muted'>(mesure à blanc q_v8_calibre → q_v11_regle_apres, ortho IGN)</span></h1>"
        + "".join(cards))
open(OUT, "w", encoding="utf-8").write(html)
print(f"{len(cards)} cartes → {OUT}")
