"""M32 Phase C — MINI-DECK complémentaire : les mouvements SENSIBLES impliquant la brûlante
(vitrine produit) que le deck des 20 (saturé par les 20 dé-déclassées AU) avait coupés.
3 entrées en brûlante + 2 sorties de brûlante (ET2162 recalibr, AL1773 plancher L'Étang-Salé).
Format identique au deck principal. Sortie HTML → print_pdf.mjs.
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
OUT = os.path.join(os.path.dirname(__file__), "deck_mini.html")
PVA = "PVA 2025 (vols 21/07–02/08/2025) — ortho IGN"

# les 5 mouvements sensibles, ordre Vic : entrées brûlante d'abord, puis sorties
IDUS = ["97418000AT2542", "97422000CY0197", "97422000AK1442",  # → brûlante
        "97416000ET2162", "97404000AL1773"]                     # sorties de brûlante
CAUSES = {
    "97418000AT2542": "recalibration / départage — zone UB (hors AU)",
    "97422000CY0197": "recalibration / départage — zone Uc (hors AU)",
    "97422000AK1442": "a_creuser → brûlante ⚠ override REGISTRE M28 (piscine FLAIR 88 m²) → ré-appliqué a_creuser à la bascule",
    "97416000ET2162": "recalibration / départage — sortie douce (brûlante → chaude), reste en tête",
    "97404000AL1773": "SORTIE : plancher L'Étang-Salé (AUb 470 m² < 3333 m² min = au_sous_plancher pénalisé) — la parcelle est trop petite pour l'opération d'ensemble, correctement retirée de tête",
}


def carte(cl, g):
    rings = _rings(json.loads(g))
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats)); zoom = ZOOM_MIN
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
    imgs = "".join(f"<image x='{x}' y='{y}' width='{TILE_PX}' height='{TILE_PX}' href='{h}'/>" for x, y, h in tiles)
    polys = []
    for ring in rings:
        pts = " ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}" for lo, la in ring)
        polys.append(f"<polygon points='{pts}' fill='#E8695A22' stroke='#E8695A' stroke-width='2.5'/>")
    return (f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='0 0 {VIEW_W} {VIEW_H}' style='border-radius:10px'>{imgs}{''.join(polys)}</svg>")


CSS = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
       "h1{font-size:18px;color:#E8695A}.card{margin:18px 0;padding:14px;background:#111814;"
       "border:1px solid #2a1f1f;border-radius:12px;max-width:760px;break-inside:avoid}"
       ".idu{font-family:monospace;font-size:15px;color:#ECF5EF}"
       ".mv{font-weight:600}.mv .av{color:#8FA69A}.mv .ap{color:#E8695A}"
       ".cause{color:#E8B44C;font-size:12px;margin:4px 0}.muted{color:#5a6b62;font-size:12px}")

cards = []
with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
    for i, idu in enumerate(IDUS, 1):
        r = s.execute(text("""SELECT a.tier avant, b.tier apres, a.rang ra, b.rang rp, p.commune,
              z.zone_lib, ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) g
            FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b ON a.parcelle_id=b.parcelle_id AND b.run_id='q_v13_m32_mesure'
            JOIN parcels p ON p.idu=a.parcelle_id LEFT JOIN parcel_zone_plu z ON z.idu=a.parcelle_id
            WHERE a.run_id='q_v8_calibre' AND a.parcelle_id=:i"""), {"i": idu}).mappings().first()
        svg = carte(cl, r["g"])
        cards.append(
            f"<div class='card'><p class='idu'>{i}. {idu} <span class='muted'>{r['commune']} · zone {r['zone_lib'] or '—'}</span></p>"
            f"<p class='mv'><span class='av'>{r['avant']}</span> → <span class='ap'>{r['apres']}</span>"
            f" <span class='muted'>rang {r['ra']} → {r['rp']}</span></p>"
            f"<p class='cause'>{CAUSES.get(idu,'')}</p><p class='muted'>{PVA}</p>{svg}</div>")

html = (f"<!doctype html><meta charset='utf-8'><title>M32 — mini-deck brûlante</title>"
        f"<style>{CSS}</style><h1>M32 Phase C — mouvements SENSIBLES (brûlante) : {len(cards)} cartes "
        f"<span class='muted'>(complément du deck 20 ; 3 entrées + 2 sorties de brûlante)</span></h1>" + "".join(cards))
open(OUT, "w", encoding="utf-8").write(html)
print(f"{len(cards)} cartes → {OUT}")
