"""Revue visuelle des 5 cas d'assemblage (Vic, Principe 2) — avant de servir la mention au_sous_plancher.
Cible (vert) + voisins retenus ≥3 m (orange, surface annotée) + bâti (gris) sur fond IGN ortho.
Cas : 3 brûlantes assemblables Trois-Bassins + 1 voisin manifestement bâti + 1 voisin le plus petit.
"""
import base64, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, VIEW_W, VIEW_H,
                                        TILE_PX, ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)
from labuse.faisabilite.au_ouverture import CONTIGUITE_MIN_M
import httpx
from pathlib import Path
CACHE = Path("/tmp/labuse_tiles"); CACHE.mkdir(exist_ok=True)

def geojson(session, idu):
    return session.execute(text("SELECT ST_AsGeoJSON(ST_Transform(geom_2975,4326)) FROM parcels WHERE idu=:i"),{"i":idu}).scalar()

def seuil(zl):
    d = 35 if zl.startswith('1AUa') else 30 if zl.startswith(('1AUb','AUb','AUa')) else 20 if zl.startswith(('1AUc','AUc')) else 15
    ml = 5 if zl.startswith(('1AU','2AU')) and '97423' else 10
    return ml, d, ml/d*10000.0

def voisins(session, idu, zl):
    return session.execute(text("""
      SELECT v.idu, ST_AsGeoJSON(ST_Transform(v.geom_2975,4326)) gj, round(ST_Area(v.geom_2975)) surf,
             round(ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,c.geom_2975),2))::numeric,1) front,
             COALESCE((SELECT round(sum(ST_Area(ST_Intersection(b.geom_2975,v.geom_2975)))) FROM spatial_layers b
                WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,v.geom_2975)),0) bati_m2
      FROM parcels c, parcel_zone_plu vz JOIN parcels v ON v.idu=vz.idu
      WHERE c.idu=:i AND vz.zone_lib=:zl AND v.idu<>:i
        AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,c.geom_2975),2)) >= :m
      ORDER BY surf
    """),{"i":idu,"zl":zl,"m":CONTIGUITE_MIN_M}).mappings().all()

def render(session, idu, zl, label):
    ml,d,s = seuil(zl)
    cg = geojson(session, idu)
    surf_cible = session.execute(text("SELECT round(ST_Area(geom_2975)) FROM parcels WHERE idu=:i"),{"i":idu}).scalar()
    vs = voisins(session, idu, zl)
    # bbox sur cible + voisins
    allrings=_rings(json.loads(cg))+[r for v in vs for r in _rings(json.loads(v['gj']))]
    lons=[c[0] for r in allrings for c in r]; lats=[c[1] for r in allrings for c in r]
    bbox=(min(lons),min(lats),max(lons),max(lats))
    zoom=ZOOM_MIN
    for z in range(ZOOM_MAX,ZOOM_MIN-1,-1):
        x0,y1=_lonlat_to_px(bbox[0],bbox[1],z); x1,y0=_lonlat_to_px(bbox[2],bbox[3],z)
        if (x1-x0)<=VIEW_W*0.75 and (y1-y0)<=VIEW_H*0.75: zoom=z; break
    cx,cy=_lonlat_to_px((bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2,zoom); left,top=cx-VIEW_W/2,cy-VIEW_H/2
    tiles=[]
    with httpx.Client(timeout=15.0, headers={"User-Agent":USER_AGENT}) as cl:
        for tx in range(int(left//TILE_PX),int((left+VIEW_W)//TILE_PX)+1):
            for ty in range(int(top//TILE_PX),int((top+VIEW_H)//TILE_PX)+1):
                try: img=_fetch_tile(zoom,tx,ty,CACHE,cl,tile_url=IGN_ORTHO_URL,prefix="ign")
                except Exception: img=None
                if img: tiles.append((round(tx*TILE_PX-left),round(ty*TILE_PX-top),"data:image/jpeg;base64,"+base64.b64encode(img).decode()))
    def poly(gj,fill,stroke,sw):
        out=[]
        for ring in _rings(json.loads(gj)):
            pts=" ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}" for lo,la in ring)
            out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
        return "".join(out)
    def label_at(gj,txt):
        r=_rings(json.loads(gj))[0]; xs=[_lonlat_to_px(lo,la,zoom)[0]-left for lo,la in r]; ys=[_lonlat_to_px(lo,la,zoom)[1]-top for lo,la in r]
        return f"<text x='{sum(xs)/len(xs):.0f}' y='{sum(ys)/len(ys):.0f}' font-size='11' fill='#fff' stroke='#000' stroke-width='0.4' text-anchor='middle'>{txt}</text>"
    imgs="".join(f"<img src='{u}' style='position:absolute;left:{l}px;top:{t}px;width:256px;height:256px;'>" for l,t,u in tiles)
    svg=[f"<svg width='{VIEW_W}' height='{VIEW_H}' style='position:absolute;left:0;top:0;'>"]
    for v in vs: svg.append(poly(v['gj'],"rgba(201,138,0,0.30)","#C98A00",2))
    svg.append(poly(cg,"rgba(11,138,95,0.15)","#0B8A5F",3))
    svg.append(label_at(cg,f"{int(surf_cible)} m²"))
    for v in vs: svg.append(label_at(v['gj'],f"{int(v['surf'])} m²"))
    svg.append("</svg>")
    combine=surf_cible+sum(v['surf'] for v in vs)
    tv="".join(f"<tr><td>{v['idu']}</td><td>{int(v['surf'])} m²</td><td>frontière {v['front']} m</td><td>bâti {int(v['bati_m2'])} m²</td></tr>" for v in vs)
    return (f"<div class='card'><h3>{label}</h3><h4>{idu} — Les Trois-Bassins ({zl})</h4>"
            f"<div class='map' style='width:{VIEW_W}px;height:{VIEW_H}px;position:relative'>{imgs}{''.join(svg)}</div>"
            f"<p class='leg'><b class='p'>cible</b> (vert) · <b class='l'>voisins retenus ≥{CONTIGUITE_MIN_M:g} m</b> (orange) · bâti (gris)</p>"
            f"<table><tr><td><b>Seuil visé</b></td><td colspan=3><b>{ml} log ÷ {d} log/ha = {int(s)} m²</b></td></tr>"
            f"<tr><td>Cible</td><td>{int(surf_cible)} m²</td><td colspan=2>manque {int(max(0,s-surf_cible))} m² seule</td></tr>"
            f"{tv}<tr><td><b>Assemblage cible+voisins</b></td><td colspan=3><b>{int(combine)} m² → {'ATTEINT' if combine>=s else 'insuffisant'} le seuil</b></td></tr></table></div>")

with session_scope() as s:
    cases=[
      ("97423000AB1907","1AUb","CAS 1 — brûlante assemblable"),
      ("97423000AB1906","1AUb","CAS 2 — brûlante assemblable"),
      ("97423000AB1911","1AUb","CAS 3 — brûlante assemblable"),
    ]
    # cas 4 : voisin manifestement bâti — sous-seuil dont un voisin a le plus de bâti
    r4=s.execute(text("""
      SELECT sc.parcelle_id, z.zone_lib FROM parcel_p_score_v2 sc JOIN parcel_zone_plu z ON z.idu=sc.parcelle_id
      JOIN parcels p ON p.idu=sc.parcelle_id
      WHERE sc.run_id='q_v7_defisc' AND sc.tier<>'ecartee' AND substring(sc.parcelle_id from 1 for 5)='97423' AND z.zone_lib ~ '^1AU'
        AND EXISTS (SELECT 1 FROM parcel_zone_plu vz JOIN parcels v ON v.idu=vz.idu
              JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975,v.geom_2975)
              WHERE vz.zone_lib=z.zone_lib AND v.idu<>sc.parcelle_id
                AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,p.geom_2975),2))>=3
                AND ST_Area(ST_Intersection(b.geom_2975,v.geom_2975))>0.5*ST_Area(v.geom_2975))
      ORDER BY ST_Area(p.geom_2975) LIMIT 1
    """)).first()
    if r4: cases.append((r4[0],r4[1],"CAS 4 — voisin manifestement BÂTI (assemblage douteux)"))
    # cas 5 : voisin le plus petit possible — sous-seuil dont le plus petit voisin retenu est minuscule
    r5=s.execute(text("""
      SELECT sc.parcelle_id, z.zone_lib, MIN(ST_Area(v.geom_2975)) mv FROM parcel_p_score_v2 sc
      JOIN parcel_zone_plu z ON z.idu=sc.parcelle_id JOIN parcels p ON p.idu=sc.parcelle_id
      JOIN parcel_zone_plu vz ON vz.zone_lib=z.zone_lib JOIN parcels v ON v.idu=vz.idu AND v.idu<>sc.parcelle_id
        AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975,p.geom_2975),2))>=3
      WHERE sc.run_id='q_v7_defisc' AND sc.tier<>'ecartee' AND substring(sc.parcelle_id from 1 for 5)='97423' AND z.zone_lib ~ '^1AU'
      GROUP BY sc.parcelle_id, z.zone_lib ORDER BY mv ASC LIMIT 1
    """)).first()
    if r5: cases.append((r5[0],r5[1],"CAS 5 — voisin retenu le PLUS PETIT"))
    cards=[render(s,idu,zl,lab) for idu,zl,lab in cases]

css="body{font-family:sans-serif;font-size:12px}.card{page-break-after:always;margin-bottom:20px}.map{border:1px solid #333}table{border-collapse:collapse;width:640px;margin-top:6px}td{border:1px solid #bbb;padding:2px 5px}.leg .p{color:#0B8A5F}.leg .l{color:#C98A00}"
html=f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><h2>Revue visuelle — assemblage au_sous_plancher (5 cas)</h2>{''.join(cards)}</body></html>"
out=Path(os.path.dirname(__file__))/"cartes_assemblage.html"; out.write_text(html,encoding="utf-8")
print("HTML:",out)
try:
    from weasyprint import HTML
    HTML(string=html,base_url=str(out.parent)).write_pdf(str(out.with_suffix(".pdf")))
    print("PDF:",out.with_suffix(".pdf"))
except Exception as e: print("PDF échec:",str(e)[:80])
