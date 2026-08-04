"""REBUILD UNIQUE — cartes de revue des ENTRANTES en tête (brûlantes), pour validation visuelle de Vic.

Style division_review : fond ORTHO IGN + tracé PARCELLE + tracé ZONAGE PLU (polygone de zone + code).
Deux familles :
  * NOUVELLES BRÛLANTES : brûlante dans le candidat q_v9_apres, PAS brûlante dans le servi q_v7_defisc
    (= promues par la calibration q_v8, mérite) ;
  * SAINT-BENOÎT RESTAURÉES : les 8 brûlantes AUa5/AUb19 dé-déclassées par le correctif d'ouverture.
Chaque carte porte rang servi→après, tier servi→après, zone_lib corrigé, au_statut, motif.
"""
import base64, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from pathlib import Path
import httpx
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.division_review import (_rings, _lonlat_to_px, _fetch_tile, VIEW_W, VIEW_H,
    TILE_PX, ZOOM_MIN, ZOOM_MAX, IGN_ORTHO_URL, USER_AGENT)
from weasyprint import HTML

CACHE = Path("/tmp/labuse_tiles"); CACHE.mkdir(exist_ok=True)
SERVI, CAND = "q_v7_defisc", "q_v9_apres"

def carte(session, parcelle_gj, zones):
    """Fond IGN + zonage (polygones + labels) + parcelle verte, une transformée ancrée sur la parcelle."""
    rings = _rings(json.loads(parcelle_gj))
    if not rings:
        return "<p>parcelle sans géométrie</p>"
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= VIEW_W * 0.5 and (y1 - y0) <= VIEW_H * 0.5:
            zoom = z; break
    cx, cy = _lonlat_to_px((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2, zoom)
    left, top = cx - VIEW_W/2, cy - VIEW_H/2
    tiles = []
    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as client:
        for tx in range(int(left // TILE_PX), int((left+VIEW_W)//TILE_PX)+1):
            for ty in range(int(top // TILE_PX), int((top+VIEW_H)//TILE_PX)+1):
                try:
                    img = _fetch_tile(zoom, tx, ty, CACHE, client, tile_url=IGN_ORTHO_URL, prefix="ign")
                except Exception:
                    img = None
                if img:
                    tiles.append((round(tx*TILE_PX-left), round(ty*TILE_PX-top),
                                  "data:image/jpeg;base64,"+base64.b64encode(img).decode()))
    def poly(gj, fill, stroke, sw):
        out = []
        for ring in _rings(json.loads(gj)):
            pts = " ".join(f"{_lonlat_to_px(lo,la,zoom)[0]-left:.1f},{_lonlat_to_px(lo,la,zoom)[1]-top:.1f}"
                           for lo, la in ring)
            out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
        return "".join(out)
    imgs = "".join(f"<img src='{u}' style='position:absolute;left:{l}px;top:{t}px;width:256px;height:256px;'>"
                   for l, t, u in tiles)
    zsvg = "".join(poly(z["gj"], "rgba(40,90,200,0.10)", "#2A5AC8", 1.5) for z in zones if z["gj"])
    # labels de zone (au centroïde)
    zlab = ""
    for z in zones:
        if z.get("cx") is not None:
            px, py = _lonlat_to_px(z["cx"], z["cy"], zoom)
            zlab += (f"<text x='{px-left:.0f}' y='{py-top:.0f}' fill='#12356E' font-size='13' "
                     f"font-weight='bold' style='paint-order:stroke;stroke:#fff;stroke-width:3'>{z['code']}</text>")
    psvg = poly(parcelle_gj, "rgba(11,138,95,0.12)", "#0B8A5F", 3.2)
    svg = (f"<svg width='{VIEW_W}' height='{VIEW_H}' style='position:absolute;left:0;top:0;'>"
           f"{zsvg}{psvg}{zlab}</svg>")
    return f"<div class='map' style='position:relative;width:{VIEW_W}px;height:{VIEW_H}px;overflow:hidden;border:0.6pt solid #ccc'>{imgs}{svg}</div>"

def zones_of(session, idu):
    rows = session.execute(text("""
        SELECT ST_AsGeoJSON(ST_Transform(ST_MakeValid(z.geom_2975),4326),7) gj,
               COALESCE(NULLIF(rtrim(split_part(btrim(z.attrs->>'libelle'),' ',1),':'),''), z.subtype) code,
               ST_X(ST_Transform(ST_Centroid(z.geom_2975),4326)) cx,
               ST_Y(ST_Transform(ST_Centroid(z.geom_2975),4326)) cy
        FROM parcels p JOIN spatial_layers z
          ON z.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975, ST_MakeValid(z.geom_2975))
        WHERE p.idu=:i"""), {"i": idu}).mappings().all()
    return [dict(r) for r in rows]

def parcelle_gj(session, idu):
    return session.execute(text("SELECT ST_AsGeoJSON(ST_Transform(geom_2975,4326),7) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()

def tier_rang(session, run, idu):
    r = session.execute(text("SELECT tier, rang FROM parcel_p_score_v2 WHERE run_id=:r AND parcelle_id=:i"), {"r": run, "i": idu}).first()
    return (r.tier, r.rang) if r else ("—", None)

COMMUNE = {"97401":"Les Avirons","97402":"Bras-Panon","97403":"L'Entre-Deux","97404":"L'Étang-Salé",
 "97405":"Petite-Île","97406":"La Plaine-des-Palmistes","97407":"La Possession","97408":"La Possession",
 "97409":"Le Port","97410":"Saint-Benoît","97411":"Saint-André","97412":"Saint-Benoît","97413":"Saint-Leu",
 "97414":"Saint-Louis","97415":"Saint-Paul","97416":"Saint-Philippe","97418":"Sainte-Marie","97419":"Sainte-Rose",
 "97420":"Sainte-Suzanne","97421":"Salazie","97422":"Le Tampon","97423":"Les Trois-Bassins","97424":"Cilaos"}

def build(cards, titre):
    html_cards = []
    with session_scope() as s:
        for i, c in enumerate(cards, 1):
            idu = c["idu"]
            pgj = parcelle_gj(s, idu)
            zs = zones_of(s, idu)
            m = carte(s, pgj, zs) if pgj else "<p>pas de géométrie</p>"
            au = s.execute(text("SELECT classe, motif, zone_lib FROM parcel_au_statut WHERE idu=:i"), {"i": idu}).first()
            zl = s.execute(text("SELECT zone_lib, zone_libelle FROM parcel_zone_plu WHERE idu=:i"), {"i": idu}).first()
            svt, svr = tier_rang(s, SERVI, idu); apt, apr = tier_rang(s, CAND, idu)
            aucl = au.classe if au else "—"; aum = (au.motif if au else "") or ""
            zcode = zl.zone_lib if zl else "—"; zlib = (zl.zone_libelle if zl else "") or ""
            com = s.execute(text("SELECT commune FROM parcels WHERE idu=:i"), {"i": idu}).scalar() or idu[:5]
            html_cards.append(
                f"<div class='card'><h3>{i}. {idu} — {com} — {c['fam']}</h3>{m}"
                f"<p class='leg'>Tracés : <b style='color:#0B8A5F'>parcelle</b> · "
                f"<b style='color:#2A5AC8'>zonage PLU</b> (code au centre)</p>"
                f"<table><tr><td>Zone (corrigée)</td><td><b>{zcode}</b> {zlib}</td>"
                f"<td>Statut AU</td><td>{aucl}</td></tr>"
                f"<tr><td>Rang servi→après</td><td>{svr} → {apr}</td>"
                f"<td>Tier servi→après</td><td>{svt} → <b>{apt}</b></td></tr>"
                f"<tr><td colspan='4' class='motif'>{c['motif']}{(' — '+aum) if aum else ''}</td></tr></table></div>")
    css = ("@page{size:A4;margin:11mm} body{font-family:sans-serif;font-size:9pt;color:#222}"
           "h1{font-size:15pt} .sec{background:#FFF6DE;padding:2mm 3mm;border-radius:2mm;color:#7A5A12;font-size:9pt}"
           ".card{page-break-inside:avoid;margin:4mm 0;border:0.6pt solid #DCE5E0;border-radius:2mm;padding:3mm}"
           ".card h3{margin:0 0 1.5mm;font-size:10.5pt} table{width:100%;border-collapse:collapse;font-size:8.5pt;margin-top:1.5mm}"
           "td{padding:0.8mm 2mm} .leg{font-size:7.5pt;color:#555;margin:1mm 0} .motif{color:#7A5A12;font-style:italic}")
    return f"<style>{css}</style><h1>{titre}</h1>", "".join(html_cards)

if __name__ == "__main__":
    with session_scope() as s:
        def d(run): return {r.idu:(r.tier, r.rang, float(r.p_raw)) for r in s.execute(text("SELECT parcelle_id idu, tier, rang, p_raw FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": run}).all()}
        svd, apd = d(SERVI), d(CAND)
        sv = {i for i in svd if svd[i][0]=='brulante'}; ap = {i for i in apd if apd[i][0]=='brulante'}
        nouvelles = sorted(ap - sv, key=lambda i: apd[i][1] or 0)
        stbenoit = sorted([i for i in ap if i.startswith("97410")], key=lambda i: apd[i][1] or 0)
    cn = []
    for i in nouvelles:
        svr, svp = svd[i][1], svd[i][2]; car, cap = apd[i][1], apd[i][2]
        if cap - svp > 1e-6:  # score en hausse = vrai mérite
            motif = f"MÉRITE : signal en hausse (p_raw {svp:.4f}→{cap:.4f}, rang {svr}→{car})"
            fam = "NOUVELLE BRÛLANTE — mérite"
        else:  # p_raw inchangé → promue par abaissement du seuil (dette #9)
            motif = f"SEUIL (dette #9) : p_raw INCHANGÉ ({svp:.4f}), promue par abaissement du seuil brûlante (rang {svr}→{car})"
            fam = "NOUVELLE BRÛLANTE — seuil"
        cn.append({"idu": i, "fam": fam, "motif": motif})
    cn.sort(key=lambda c: (0 if "mérite" in c["fam"] else 1))  # mérite d'abord (les honnêtes en tête)
    n_mer = sum(1 for c in cn if "mérite" in c["fam"]); n_seu = len(cn) - n_mer
    cs = [{"idu": i, "fam": "SAINT-BENOÎT RESTAURÉE", "motif": "dé-déclassée par le correctif d'ouverture AU (AUa5/AUb19 = fiche annexe, opération d'ensemble = servie)"} for i in stbenoit]
    print(f"nouvelles brûlantes={len(cn)} (mérite {n_mer}, seuil {n_seu}) ; Saint-Benoît restaurées={len(cs)}", flush=True)
    h1, c1 = build(cn, f"Entrantes en tête — {len(cn)} nouvelles brûlantes : {n_mer} par MÉRITE, {n_seu} par SEUIL (dette #9)")
    h2, c2 = build(cs, f"Entrantes en tête — {len(cs)} SAINT-BENOÎT restaurées (correctif AU)")
    doc = f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'></head><body>{h1}{c1}<div style='page-break-before:always'></div>{h2}{c2}</body></html>"
    out = "qa/rebuild_unique/cartes_entrantes.pdf"
    HTML(string=doc).write_pdf(out)
    print(f"✓ {out}", flush=True)
