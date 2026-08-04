"""Revue Vic — cartes DÉDIÉES AB1908/AB1910 (condition du GO bascule pondération).

Pour chacune : ortho IGN zoomée (contour parcelle + voisines AB du même îlot en pointillé),
cartouche complet — surface, seuil, manque, facteur, tier avant/après pondération, top 5 du
p brut (pourquoi le modèle la classe si haut). Lecture seule.
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
OUT = os.path.join(os.path.dirname(__file__), "cartes_ab1908_ab1910.html")
CIBLES = ["97423000AB1908", "97423000AB1910"]

CSS = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
       "h1{font-size:18px;color:#5CE6A1}.card{margin:18px 0;padding:16px;background:#111814;"
       "border:1px solid #1f2a24;border-radius:12px;max-width:860px}"
       ".idu{font-family:monospace;font-size:16px;color:#ECF5EF}"
       ".muted{color:#5a6b62;font-size:12px}.kv{font-size:13px;line-height:1.7}"
       ".kv b{color:#b8cbc0}.contrib{font-size:12px;color:#8FA69A;margin:2px 0}"
       ".warn{color:#E8B44C}")

def render(s, cl, idu):
    row = s.execute(text("""
        SELECT ST_AsGeoJSON(ST_Transform(p.geom_2975,4326)) g, ST_Area(p.geom_2975) surf,
               a.zone_lib,
               (SELECT tier FROM parcel_p_score_v2 WHERE run_id='q_v9_pond_avant' AND parcelle_id=p.idu) t_av,
               (SELECT rang FROM parcel_p_score_v2 WHERE run_id='q_v9_pond_avant' AND parcelle_id=p.idu) r_av,
               (SELECT tier FROM parcel_p_score_v2 WHERE run_id='q_v9_pond_apres' AND parcelle_id=p.idu) t_ap,
               (SELECT rang FROM parcel_p_score_v2 WHERE run_id='q_v9_pond_apres' AND parcelle_id=p.idu) r_ap,
               (SELECT round(p_raw::numeric,4) FROM parcel_p_score_v2 WHERE run_id='q_v8_calibre' AND parcelle_id=p.idu) praw,
               (SELECT top5_contributions FROM parcel_p_score_v2 WHERE run_id='q_v8_calibre' AND parcelle_id=p.idu) top5
        FROM parcels p LEFT JOIN parcel_au_statut a ON a.idu=p.idu WHERE p.idu=:i"""),
        {"i": idu}).mappings().one()
    voisins = s.execute(text("""
        SELECT v.idu, ST_AsGeoJSON(ST_Transform(v.geom_2975,4326)) g
        FROM parcels c JOIN parcels v ON v.idu LIKE '97423000AB%' AND v.idu<>c.idu
          AND ST_DWithin(v.geom_2975, c.geom_2975, 60)
        WHERE c.idu=:i"""), {"i": idu}).mappings().all()
    insee, zl = idu[:5], row["zone_lib"]
    reg = zone_regime(insee, zl); seuil = seuil_surface_m2(reg)
    f = facteur_ponderation(insee, zl, float(row["surf"]))
    rings = _rings(json.loads(row["g"]))
    # zoom choisi sur la PARCELLE seule (pas les voisines) — sinon la bbox du rayon 60 m
    # écrase le contour ; ×0.18 = la parcelle occupe ~1/5 de la vue, l'îlot reste lisible.
    lons=[c[0] for r in rings for c in r]; lats=[c[1] for r in rings for c in r]
    bbox=(min(lons),min(lats),max(lons),max(lats)); zoom=ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN-1, -1):
        x0,y1=_lonlat_to_px(bbox[0],bbox[1],z); x1,y0=_lonlat_to_px(bbox[2],bbox[3],z)
        if (x1-x0)<=VIEW_W*0.18 and (y1-y0)<=VIEW_H*0.18: zoom=z; break
    cx,cy=_lonlat_to_px((bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2,zoom); left,top=cx-VIEW_W/2,cy-VIEW_H/2
    tiles=[]
    for tx in range(int(left//TILE_PX), int((left+VIEW_W)//TILE_PX)+1):
        for ty in range(int(top//TILE_PX), int((top+VIEW_H)//TILE_PX)+1):
            try: img=_fetch_tile(zoom,tx,ty,CACHE,cl,tile_url=IGN_ORTHO_URL,prefix="ign")
            except Exception: img=None
            if img: tiles.append((round(tx*TILE_PX-left),round(ty*TILE_PX-top),
                                  "data:image/jpeg;base64,"+base64.b64encode(img).decode()))
    imgs="".join(f"<image x='{x}' y='{y}' width='{TILE_PX}' height='{TILE_PX}' href='{h}'/>" for x,y,h in tiles)
    def poly(g, fill, stroke, sw, dash=""):
        o=[]
        for ring in _rings(json.loads(g)):
            pts=" ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}" for lo,la in ring)
            o.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}' {dash}/>")
        return "".join(o)
    vp="".join(poly(v["g"], "none", "#8FA69A", 1.2, "stroke-dasharray='4 3'") for v in voisins)
    cp=poly(row["g"], "#5CE6A126", "#5CE6A1", 3)
    svg=(f"<svg width='{VIEW_W}' height='{VIEW_H}' viewBox='0 0 {VIEW_W} {VIEW_H}' "
         f"style='border-radius:10px'>{imgs}{vp}{cp}</svg>")
    contribs="".join(f"<p class='contrib'>+{c['log_hazard']:.2f} · {c['libelle']} ({c['bin'] or 'croisement'})</p>"
                     for c in (row["top5"] or []))
    manque = seuil - float(row["surf"])
    return (f"<div class='card'><p class='idu'>{idu} <span class='muted'>Les Trois-Bassins · zone {zl} · "
            f"au_sous_plancher</span></p>"
            f"<p class='kv'><b>Surface</b> {row['surf']:.0f} m² · <b>seuil</b> {seuil:.0f} m² "
            f"(5 log ÷ 30 log/ha) · <b>manque</b> {manque:.0f} m² ({(1-f)*100:.0f} %) · "
            f"<b>facteur</b> {f:.3f}</p>"
            f"<p class='kv'><b>Sans pondération</b> {row['t_av']} rang {row['r_av']} · "
            f"<b>avec pondération</b> <span class='warn'>{row['t_ap']} rang {row['r_ap']}</span> · "
            f"p brut {row['praw']}"
            + (" <span class='warn'>— SATURATION MODÈLE (p = 1,0 exact ; 5 parcelles dans ce cas "
               "sur l'île : rangs 1-5 du servi, 2 lotissements récents — audit train 5)</span>"
               if float(row['praw'] or 0) >= 0.999 else "") + "</p>"
            f"<p class='kv'><b>Pourquoi le p brut est haut</b> (top 5 du modèle) :</p>{contribs}"
            f"<p class='muted'>Couche batiment : 0 m². AUCUNE détection ortho (ni piscine ni PV) — "
            f"la suspicion dette #4 annoncée au rapport était une erreur de recoupement, corrigée. "
            f"Voisines AB en pointillé (même îlot que AB1911, ex-rang 6).</p>{svg}</div>")

with session_scope() as s, httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as cl:
    cards = [render(s, cl, i) for i in CIBLES]
html=(f"<!doctype html><meta charset='utf-8'><title>Revue AB1908 / AB1910</title><style>{CSS}</style>"
      f"<h1>Revue AB1908 / AB1910 — condition du GO bascule <span class='muted'>(ortho IGN)</span></h1>"
      + "".join(cards))
open(OUT,"w",encoding="utf-8").write(html)
print(f"2 cartes → {OUT}")
