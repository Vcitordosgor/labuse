"""Les 14 DISCORDANCES CoSIA-vs-vérité-terrain — cartes DATÉES pour contre-revue Vic.

Exigence Vic 04/08 : la date de PRISE DE VUE de l'ortho est affichée sur chaque carte
(graphe de mosaïquage — vérifié : les 14 zones sont PVA 2025, vols 21/07-02/08/2025).
Rose = polygones CoSIA classe Bâtiment ∩ parcelle. Vert = contour parcelle.
Sortie : /tmp/discord_datees.html → qa/dette4/pilote_cosia_discordances.pdf (écrase la v1
non datée). Lecture seule.
"""
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
import httpx
from pathlib import Path
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, TILE_PX,
                                        ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)
from ortho_dates import date_vol

W, H = 560, 380
DISCORD = ([("RATÉE (vérité: bâtie, CoSIA: non)", i) for i in
            ["97408000AC2972", "97412000AO0912", "97413000CY0677", "97414000HA0440",
             "97416000CW1433", "97416000CW2399", "97422000BD3665", "97422000BV3186"]] +
           [("FAUSSE? (vérité: nue, CoSIA: bâti)", i) for i in
            ["97423000AB1908", "97415000ER1172", "97415000DE1235",
             "97410000CD0937", "97403000AM0816", "97408000AC2409"]])

CSS = ("@page{size:A4;margin:10mm}body{font:12px -apple-system,sans-serif;margin:0;background:#fff}"
       ".card{page-break-after:always;padding:2mm 0}"
       ".idu{font:600 14px ui-monospace,Menlo,monospace;margin:0}"
       ".date{font-size:11px;color:#0c4d33;font-weight:600;margin:2px 0}"
       ".muted{color:#667;font-size:11px}")


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


cards = []
with session_scope() as s, httpx.Client(timeout=20.0, headers={"User-Agent": USER_AGENT}) as cl:
    for typ, idu in DISCORD:
        r = s.execute(text(
            "SELECT ST_AsGeoJSON(ST_Transform(geom_2975,4326)) g, commune, ST_Area(geom_2975) surf, "
            "ST_X(ST_Transform(ST_Centroid(geom_2975),4326)) lon, "
            "ST_Y(ST_Transform(ST_Centroid(geom_2975),4326)) lat FROM parcels WHERE idu=:i"),
            {"i": idu}).mappings().one()
        cos = s.execute(text(
            "SELECT ST_AsGeoJSON(ST_Transform(ST_Intersection(q.geom,p.geom_2975),4326)), "
            "round(ST_Area(ST_Intersection(q.geom,p.geom_2975)))::int "
            "FROM qa_cosia_bati q, parcels p WHERE p.idu=:i AND ST_Intersects(q.geom,p.geom_2975)"),
            {"i": idu}).all()
        cos_m2 = sum(m for _, m in cos)
        dv = date_vol(cl, r["lon"], r["lat"], key=idu)
        rings = _rings(json.loads(r["g"]))
        lons = [c[0] for rg in rings for c in rg]; lats = [c[1] for rg in rings for c in rg]
        bbox = (min(lons), min(lats), max(lons), max(lats)); zoom = ZOOM_MIN
        for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
            x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
            if (x1 - x0) <= W * 0.5 and (y1 - y0) <= H * 0.5:
                zoom = z; break
        cx, cy = _lonlat_to_px((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2, zoom)
        left, top = cx - W/2, cy - H/2
        tiles = []
        for tx in range(int(left//TILE_PX), int((left+W)//TILE_PX)+1):
            for ty in range(int(top//TILE_PX), int((top+H)//TILE_PX)+1):
                try:
                    img = _fetch_tile(zoom, tx, ty, Path("/tmp/labuse_tiles"), cl,
                                      tile_url=IGN_ORTHO_URL, prefix="ign")
                except Exception:
                    img = None
                if img:
                    tiles.append((round(tx*TILE_PX-left), round(ty*TILE_PX-top),
                                  "data:image/jpeg;base64," + base64.b64encode(img).decode()))
        imgs = "".join(f"<image x='{x}' y='{y}' width='{TILE_PX}' height='{TILE_PX}' href='{h}'/>"
                       for x, y, h in tiles)
        cosp = "".join(poly(cg, zoom, left, top, "#e0245e55", "#e0245e", 2.5) for cg, _ in cos if cg)
        cont = poly(r["g"], zoom, left, top, "none", "#5CE6A1", 3)
        x0, y1p = _lonlat_to_px(bbox[0], bbox[1], zoom); x1, y0p = _lonlat_to_px(bbox[2], bbox[3], zoom)
        pw, ph = abs(x1-x0), abs(y1p-y0p)
        vw = min(W, max(pw/0.4, 200.0)); vh = min(H, max(ph/0.4, vw*H/W)); vw = max(vw, vh*W/H)
        vb = f"{(W-vw)/2:.1f} {(H-vh)/2:.1f} {vw:.1f} {vh:.1f}"
        cards.append(
            f"<div class='card'><p class='idu'>{typ} — {idu} <span class='muted'>{r['commune']} · "
            f"{r['surf']:.0f} m² · CoSIA {cos_m2} m²</span></p>"
            f"<p class='date'>{dv}</p>"
            f"<svg width='{W}' height='{H}' viewBox='{vb}'>{imgs}{cosp}{cont}</svg>"
            f"<p class='muted'>rose = CoSIA classe Bâtiment (dérivé de la MÊME PVA que l'ortho "
            f"affichée) · vert = parcelle</p></div>")

html = (f"<!doctype html><meta charset='utf-8'><title>14 discordances datées</title><style>{CSS}</style>"
        f"<div class='card'><h1 style='color:#0c4d33'>Pilote CoSIA — 14 discordances, cartes DATÉES</h1>"
        f"<p>Contre-revue Vic. La date de prise de vue (graphe de mosaïquage) est affichée sur chaque "
        f"carte. Vérifié : les 14 zones sont PVA 2025 (vols 21/07-02/08/2025) — CoSIA 2025 dérive des "
        f"MÊMES vols : les divergences sont des différences de LECTURE (chantier/dalle vs Bâtiment), "
        f"pas de millésime.</p></div>" + "".join(cards))
open("/tmp/discord_datees.html", "w", encoding="utf-8").write(html)
print(f"{len(cards)} cartes datées → /tmp/discord_datees.html")
