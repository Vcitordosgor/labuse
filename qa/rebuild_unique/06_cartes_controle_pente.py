"""REBUILD UNIQUE — 3 cartes de CONTRÔLE pente/forme (AY1608, AI2379, AT2300) pour Vic.
Ortho IGN + parcelle + grille de PENTE (RGE ALTI, colorée par slope_pct) + stats (pente moy, solidité, OCS).
"""
import sys, os, json, base64
sys.path.insert(0, "src")
from pathlib import Path
from io import BytesIO
import httpx
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, TILE_PX, IGN_ORTHO_URL, USER_AGENT)
from weasyprint import HTML
CACHE = Path("/tmp/labuse_tiles")

CTRL = {
 "97415000AY1608": "Saint-Paul — signalée ravine/pente ; OCS a sur-classé « Bâti » à tort (végétation)",
 "97404000AI2379": "L'Étang-Salé — signalée lanière",
 "97418000AT2300": "Sainte-Marie — signalée lanière",
}
def col(sp):
    return "rgba(60,180,75,0.35)" if sp<7 else "rgba(240,220,40,0.40)" if sp<15 else "rgba(240,140,30,0.45)" if sp<30 else "rgba(210,40,40,0.55)"

def carte(idu, zoom=19, W=680, H=460):
    with session_scope() as s:
        pgj = s.execute(text("SELECT ST_AsGeoJSON(ST_Transform(geom_2975,4326),7) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        pentes = s.execute(text("""SELECT ST_AsGeoJSON(ST_Transform(o.geom_2975,4326),7) gj, (o.attrs->>'slope_pct')::float sp
            FROM spatial_layers o, parcels p WHERE o.kind='pente' AND p.idu=:i
            AND ST_Intersects(o.geom_2975, ST_Buffer(p.geom_2975,25))"""), {"i": idu}).all()
        st = s.execute(text("SELECT pente_moy_deg, round(surface_m2::numeric) surf FROM p_model_ext_dataset WHERE idu=:i AND annee=2026"), {"i": idu}).first()
        sol = s.execute(text("SELECT round((ST_Area(geom_2975)/NULLIF(ST_Area(ST_ConvexHull(geom_2975)),0))::numeric,2) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        ocs = s.execute(text("""SELECT o.name, round((ST_Area(ST_Intersection(o.geom_2975,p.geom_2975))/ST_Area(p.geom_2975)*100)::numeric,0) pct
            FROM parcels p JOIN spatial_layers o ON o.kind='ocs_ge' AND ST_Intersects(o.geom_2975,p.geom_2975) WHERE p.idu=:i ORDER BY pct DESC LIMIT 1"""), {"i": idu}).first()
    rings = _rings(json.loads(pgj)); xs=[_lonlat_to_px(lo,la,zoom)[0] for r in rings for lo,la in r]; ys=[_lonlat_to_px(lo,la,zoom)[1] for r in rings for lo,la in r]
    cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2; left,top=cx-W/2,cy-H/2
    tiles=[]
    with httpx.Client(timeout=15, headers={"User-Agent": USER_AGENT}) as c:
        for tx in range(int(left//TILE_PX), int((left+W)//TILE_PX)+1):
            for ty in range(int(top//TILE_PX), int((top+H)//TILE_PX)+1):
                try: img=_fetch_tile(zoom,tx,ty,CACHE,c,tile_url=IGN_ORTHO_URL,prefix="ign")
                except Exception: img=None
                if img: tiles.append((round(tx*TILE_PX-left),round(ty*TILE_PX-top),"data:image/jpeg;base64,"+base64.b64encode(img).decode()))
    def poly(gj,fill,stroke,sw):
        out=[]
        for ring in _rings(json.loads(gj)):
            pts=" ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}" for lo,la in ring)
            out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
        return "".join(out)
    imgs="".join(f"<img src='{u}' style='position:absolute;left:{l}px;top:{t}px;width:256px;height:256px'>" for l,t,u in tiles)
    psvg="".join(poly(p.gj, col(p.sp), "rgba(0,0,0,0.25)", 0.5) for p in pentes)
    psvg+=poly(pgj,"none","#00E68C",4)
    m=f"<div class='map' style='position:relative;width:{W}px;height:{H}px;overflow:hidden;border:0.6pt solid #999'>{imgs}<svg width='{W}' height='{H}' style='position:absolute;left:0;top:0'>{psvg}</svg></div>"
    info=(f"<table><tr><td>Pente moyenne</td><td><b>{st.pente_moy_deg}°</b></td><td>Surface</td><td>{st.surf} m²</td></tr>"
          f"<tr><td>Solidité (aire/convexe)</td><td>{sol} {'⚠ lanière' if sol and sol<0.72 else ''}</td>"
          f"<td>OCS</td><td>{(ocs.name+' '+str(ocs.pct)+'%') if ocs else '—'}</td></tr></table>")
    return m, info

cards=[]
for idu,lab in CTRL.items():
    m,info=carte(idu)
    cards.append(f"<div class='card'><h3>{idu} — {lab}</h3>{m}"
                 f"<p class='leg'>Grille pente RGE ALTI : <b style='color:#3CB44B'>&lt;7%</b> · "
                 f"<b style='color:#C9A800'>7-15%</b> · <b style='color:#E08C1E'>15-30%</b> · <b style='color:#D22828'>&gt;30%</b> — "
                 f"parcelle en <b style='color:#00A86B'>vert vif</b></p>{info}</div>")
css=("@page{size:A4;margin:11mm} body{font-family:sans-serif;font-size:9pt} h1{font-size:14pt}"
     ".card{page-break-inside:avoid;margin:4mm 0;border:0.6pt solid #DCE5E0;border-radius:2mm;padding:3mm}"
     ".card h3{margin:0 0 1.5mm;font-size:10pt} table{width:100%;border-collapse:collapse;font-size:8.5pt;margin-top:1.5mm}"
     "td{padding:0.8mm 2mm} .leg{font-size:7.5pt;color:#555;margin:1mm 0}")
doc=f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><style>{css}</style></head><body><h1>Cartes de contrôle — pente / forme (3)</h1>{''.join(cards)}</body></html>"
out="qa/rebuild_unique/cartes_controle_pente.pdf"
HTML(string=doc).write_pdf(out); print("✓", out)
