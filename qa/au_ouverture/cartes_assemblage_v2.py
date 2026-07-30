"""Revue courte v2 (après correctif) : 3 cartes dont un voisin retenu-AVEC-RÉSERVE (bâti 20-50%).
Voisins colorés par régime : LIBRE (vert), RÉSERVE 20-50% (orange), DÉMOLITION >50% (rouge), exclu (gris pointillé).
Chaque carte montre la MENTION effectivement servie, pour vérifier qu'elle dit vrai."""
import base64, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, VIEW_W, VIEW_H,
                                        TILE_PX, ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)
from labuse.faisabilite.au_ouverture import (CONTIGUITE_MIN_M, FRONTIERE_PART_PERIMETRE_MIN,
    DELAISSE_MAX_M2, BATI_LIBRE_MAX, BATI_RESERVE_MAX, voisins_assemblables, classify)
import httpx
from pathlib import Path
CACHE = Path("/tmp/labuse_tiles"); CACHE.mkdir(exist_ok=True)
SRC = {'97423': (5, {'1AUa': 35, '1AUb': 30, '1AUc': 20})}

def gj(session, idu):
    return session.execute(text("SELECT ST_AsGeoJSON(ST_Transform(geom_2975,4326)) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()

def voisins_detail(session, idu, zl):
    return session.execute(text("""
      SELECT v.idu, ST_AsGeoJSON(ST_Transform(v.geom_2975,4326)) g, round(ST_Area(v.geom_2975)) surf,
        round((COALESCE((SELECT SUM(ST_Area(ST_Intersection(b.geom_2975,v.geom_2975))) FROM spatial_layers b
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,v.geom_2975)),0)/ST_Area(v.geom_2975)*100)::numeric,0) bati_pct,
        round(ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,c.geom_2975),2))::numeric,1) front,
        round((ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,c.geom_2975),2))/ST_Perimeter(v.geom_2975)*100)::numeric,1) ratio
      FROM parcels c, parcel_zone_plu vz JOIN parcels v ON v.idu=vz.idu
      WHERE c.idu=:i AND vz.zone_lib=:zl AND v.idu<>:i
        AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,c.geom_2975),2)) >= :m
        AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,c.geom_2975),2)) >= :p*ST_Perimeter(v.geom_2975)
        AND ST_Area(v.geom_2975) >= :d
      ORDER BY bati_pct DESC
    """), {"i": idu, "zl": zl, "m": CONTIGUITE_MIN_M, "p": FRONTIERE_PART_PERIMETRE_MIN, "d": DELAISSE_MAX_M2}).mappings().all()

def render(session, idu, zl, label):
    ml, d = SRC['97423'][0], SRC['97423'][1].get(zl[:4], 30); s = ml/d*10000.0
    cg = gj(session, idu); surf = session.execute(text("SELECT round(ST_Area(geom_2975)) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    vs = voisins_detail(session, idu, zl)
    v = voisins_assemblables(session, idu, zl, s)
    _, mention = classify("97423", zl, float(surf), voisins=v)
    allr = _rings(json.loads(cg)) + [r for x in vs for r in _rings(json.loads(x['g']))]
    lons=[c[0] for r in allr for c in r]; lats=[c[1] for r in allr for c in r]; bbox=(min(lons),min(lats),max(lons),max(lats))
    zoom=ZOOM_MIN
    for z in range(ZOOM_MAX,ZOOM_MIN-1,-1):
        x0,y1=_lonlat_to_px(bbox[0],bbox[1],z); x1,y0=_lonlat_to_px(bbox[2],bbox[3],z)
        if (x1-x0)<=VIEW_W*0.75 and (y1-y0)<=VIEW_H*0.75: zoom=z; break
    cx,cy=_lonlat_to_px((bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2,zoom); left,top=cx-VIEW_W/2,cy-VIEW_H/2
    tiles=[]
    with httpx.Client(timeout=15.0,headers={"User-Agent":USER_AGENT}) as cl:
        for tx in range(int(left//TILE_PX),int((left+VIEW_W)//TILE_PX)+1):
            for ty in range(int(top//TILE_PX),int((top+VIEW_H)//TILE_PX)+1):
                try: img=_fetch_tile(zoom,tx,ty,CACHE,cl,tile_url=IGN_ORTHO_URL,prefix="ign")
                except Exception: img=None
                if img: tiles.append((round(tx*TILE_PX-left),round(ty*TILE_PX-top),"data:image/jpeg;base64,"+base64.b64encode(img).decode()))
    def poly(g,fill,stroke,sw,dash=""):
        o=[]
        for ring in _rings(json.loads(g)):
            pts=" ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}" for lo,la in ring)
            o.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}' {dash}/>")
        return "".join(o)
    imgs="".join(f"<img src='{u}' style='position:absolute;left:{l}px;top:{t}px;width:256px;height:256px'>" for l,t,u in tiles)
    svg=[f"<svg width='{VIEW_W}' height='{VIEW_H}' style='position:absolute;left:0;top:0'>"]
    for x in vs:
        bp=float(x['bati_pct'])
        col=("rgba(11,138,95,0.25)","#0B8A5F") if bp<BATI_LIBRE_MAX*100 else ("rgba(201,138,0,0.30)","#C98A00") if bp<=BATI_RESERVE_MAX*100 else ("rgba(200,30,30,0.35)","#B01818")
        svg.append(poly(x['g'],col[0],col[1],2))
    svg.append(poly(cg,"rgba(0,0,0,0)","#111",3.5)); svg.append("</svg>")
    tv="".join(f"<tr><td>{x['idu']}</td><td>{int(x['surf'])} m²</td><td>bâti {int(x['bati_pct'])}%</td><td>front {x['front']} m ({x['ratio']}%)</td><td>{'LIBRE' if float(x['bati_pct'])<20 else 'RÉSERVE' if float(x['bati_pct'])<=50 else 'DÉMOLITION'}</td></tr>" for x in vs)
    return (f"<div class='card'><h3>{label}</h3><h4>{idu} ({zl}) — cible {int(surf)} m² · seuil {int(s)} m²</h4>"
            f"<div class='map' style='width:{VIEW_W}px;height:{VIEW_H}px;position:relative'>{imgs}{''.join(svg)}</div>"
            f"<p class='leg'>cible (noir) · voisin <b style='color:#0B8A5F'>LIBRE</b> · <b style='color:#C98A00'>RÉSERVE 20-50%</b> · <b style='color:#B01818'>DÉMOLITION >50%</b></p>"
            f"<table><tr><th>voisin</th><th>surface</th><th>bâti</th><th>frontière</th><th>régime</th></tr>{tv}</table>"
            f"<p><b>voisins_assemblables</b> : {v['libres']} libres · {v['reserve']} réserve · {v['demolition']} démolition — "
            f"atteint sans démo : {v['atteint_sans_demo']} · avec démo : {v['atteint_avec_demo']}</p>"
            f"<p class='mention'><b>MENTION SERVIE :</b> {mention}</p></div>")

with session_scope() as s:
    # CAS 1 : brûlante propre (tous libres) ; CAS 2 : un voisin RÉSERVE 20-50% ; CAS 3 : un voisin DÉMOLITION >50%
    def find(regime_sql):
        return s.execute(text(f"""
          SELECT sc.parcelle_id, z.zone_lib FROM parcel_p_score_v2 sc JOIN parcel_zone_plu z ON z.idu=sc.parcelle_id JOIN parcels p ON p.idu=sc.parcelle_id
          WHERE sc.run_id='q_v7_defisc' AND sc.tier<>'ecartee' AND substring(sc.parcelle_id from 1 for 5)='97423' AND z.zone_lib ~ '^1AU'
            AND EXISTS (SELECT 1 FROM parcel_zone_plu vz JOIN parcels v ON v.idu=vz.idu
                 WHERE vz.zone_lib=z.zone_lib AND v.idu<>sc.parcelle_id
                   AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,p.geom_2975),2))>=3
                   AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,p.geom_2975),2))>=0.02*ST_Perimeter(v.geom_2975)
                   AND ST_Area(v.geom_2975)>=50
                   AND {regime_sql})
          ORDER BY ST_Area(p.geom_2975) LIMIT 1
        """)).first()
    bati_ratio="(SELECT COALESCE(SUM(ST_Area(ST_Intersection(b.geom_2975,v.geom_2975))),0) FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,v.geom_2975))"
    c1=("97423000AB1907","1AUb","CAS 1 — brûlante, voisins libres")
    r2=find(f"{bati_ratio} BETWEEN 0.20*ST_Area(v.geom_2975) AND 0.50*ST_Area(v.geom_2975)")
    r3=find(f"{bati_ratio} > 0.50*ST_Area(v.geom_2975)")
    cases=[c1]
    if r2: cases.append((r2[0],r2[1],"CAS 2 — voisin RETENU AVEC RÉSERVE (bâti 20-50%)"))
    if r3: cases.append((r3[0],r3[1],"CAS 3 — voisin DÉMOLITION (bâti >50%, flaggé, pas silencé)"))
    cards=[render(s,i,z,l) for i,z,l in cases]
css="body{font-family:sans-serif;font-size:11px}.card{page-break-after:always}.map{border:1px solid #333}table{border-collapse:collapse;margin:6px 0}td,th{border:1px solid #bbb;padding:2px 6px}.mention{background:#f3f3f3;padding:6px;border-left:3px solid #0B8A5F}"
html=f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><h2>Revue v2 — assemblage corrigé (3 cas)</h2>{''.join(cards)}</body></html>"
out=Path(os.path.dirname(__file__))/"cartes_assemblage_v2.html"; out.write_text(html,encoding="utf-8"); print("HTML:",out)
try:
    from weasyprint import HTML; HTML(string=html,base_url=str(out.parent)).write_pdf(str(out.with_suffix(".pdf"))); print("PDF:",out.with_suffix(".pdf"))
except Exception as e: print("PDF:",str(e)[:60])
