"""O12 — DOSSIER DE REVUE « DIVISION EN OR » (20 cartes, pattern J3) pour validation VISUELLE de Vic.

FAUX POSITIF = PÉCHÉ MORTEL : l'outil reste MASQUÉ tant que Vic n'a pas validé ce dossier. Chaque carte =
photo aérienne IGN + tracés (parcelle, bâti, lot détachable proposé) + métriques + case de validation.
On ne prétend rien sur la constructibilité réglementaire — la revue humaine tranche.
"""
from __future__ import annotations

import base64
import html
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..flash.carte import (IGN_ORTHO_URL, TILE_PX, USER_AGENT, VIEW_H, VIEW_W, ZOOM_MAX, ZOOM_MIN,
                           _fetch_tile, _lonlat_to_px, _rings)

log = logging.getLogger("labuse.division_review")

# géométries par candidat : parcelle, bâti (union), lot détachable, bâti à démolir (∩ lot).
# Le lot reproduit la variante du détecteur : 'libre' = tout le bâti retiré ;
# 'demolition' = seul le bâtiment PRINCIPAL retiré (le lot peut contenir du bâti secondaire).
_GEOMS = """
WITH p AS (SELECT geom_2975, ST_AsGeoJSON(geom, 7) gj FROM parcels WHERE idu = :idu),
bldg AS (SELECT b.geom_2975 g, ST_Area(ST_Intersection(b.geom_2975, p.geom_2975)) a
         FROM spatial_layers b, p WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)),
bat AS (SELECT ST_Union(g) g FROM bldg),
sub AS (SELECT CASE WHEN :type = 'demolition'
                    THEN (SELECT g FROM bldg ORDER BY a DESC LIMIT 1) ELSE (SELECT g FROM bat) END g),
free AS (SELECT lg.geom g FROM p, sub
         CROSS JOIN LATERAL (SELECT gg.geom FROM ST_Dump(ST_Difference(p.geom_2975, ST_Buffer(sub.g,3))) gg
                             ORDER BY ST_Area(gg.geom) DESC LIMIT 1) lg),
-- type 'decoupe' (O12-PARTIEL) : le lot AFFICHÉ est la découpe STOCKÉE par le détecteur,
-- jamais recalculée (fidélité au run) ; sinon le résiduel recalculé comme avant
lotg AS (SELECT CASE WHEN :type = 'decoupe'
                     THEN (SELECT dc.lot_geom FROM division_or_candidates dc WHERE dc.idu = :idu)
                     ELSE (SELECT g FROM free) END g),
voi AS (SELECT ST_Union(ST_Buffer(ST_Intersection(v.geom_2975, ST_Buffer(p.geom_2975, 30)), 1.5)) g
        FROM spatial_layers v, p WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, p.geom_2975, 30))
SELECT p.gj AS parcelle,
       ST_AsGeoJSON(ST_Transform(bat.g, 4326), 7) AS bati,
       ST_AsGeoJSON(ST_Transform(lotg.g, 4326), 7) AS lot,
       CASE WHEN ST_Area(ST_Intersection(bat.g, lotg.g)) > 1
            THEN ST_AsGeoJSON(ST_Transform(ST_Intersection(bat.g, lotg.g), 4326), 7) END AS demolir,
       (SELECT ST_AsGeoJSON(ST_Transform(voi.g, 4326), 7) FROM voi) AS voirie,
       -- solidité affichée aussi pour les résiduels (non stockée pour eux) : calculée ici
       round((ST_Area(lotg.g) / NULLIF(ST_Area(ST_ConvexHull(lotg.g)), 0))::numeric, 3) AS solidite_calc
FROM p, bat, lotg;
"""

# libellé du statut de tracé (revue 2) — la validation porte sur un tracé, pas sur un IDU
_STATUT_LABEL = {
    "nouveau": "🆕 Nouveau candidat (non vu en revue précédente)",
    "modifie": "✎ Tracé MODIFIÉ depuis la revue précédente — à revoir",
    "inchange": "✓ Tracé inchangé depuis la revue précédente",
    "residuel": "",  # famille résiduelle : tracé déterministe (résiduel), pas de comparaison
}

_CSS = """
@page { size: A4; margin: 12mm; }
body { font-family: sans-serif; color: #222; font-size: 9pt; }
h1 { font-size: 16pt; }
.intro { background:#FFF6DE; border-radius:2mm; padding:3mm; font-size:8.5pt; color:#7A5A12; }
.card { page-break-inside: avoid; margin: 5mm 0; border:0.6pt solid #DCE5E0; border-radius:2mm; padding:3mm; }
.card h3 { margin:0 0 1mm; font-size:10.5pt; }
.map { position:relative; overflow:hidden; border:0.6pt solid #ccc; border-radius:1.5mm; }
table { width:100%; border-collapse:collapse; font-size:8pt; margin-top:1.5mm; }
td { padding:0.8mm 2mm 0.8mm 0; }
.leg { font-size:7.5pt; color:#555; }
.leg b.p{color:#1E9E58} .leg b.b{color:#888} .leg b.l{color:#C98A00} .leg b.d{color:#B01818} .leg b.v{color:#2A5AC8}
.valid { margin-top:1.5mm; font-size:8.5pt; }
.statut { margin:0 0 1mm; font-size:8pt; font-weight:bold; color:#7A5A12; }
"""


def _tiles_and_shapes(parcelle_gj, bati_gj, lot_gj, cache_dir, demolir_gj=None, voirie_gj=None):
    """Fond IGN + tracés SVG (parcelle, bâti, lot) dans une MÊME transformée ancrée sur la parcelle."""
    import json
    rings = _rings(json.loads(parcelle_gj))
    if not rings:
        return None
    lons = [c[0] for r in rings for c in r]; lats = [c[1] for r in rings for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    zoom = ZOOM_MIN
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z); x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= VIEW_W * 0.55 and (y1 - y0) <= VIEW_H * 0.55:
            zoom = z; break
    cx, cy = _lonlat_to_px((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2, zoom)
    left, top = cx - VIEW_W / 2, cy - VIEW_H / 2
    tiles = []
    with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
        for tx in range(int(left // TILE_PX), int((left + VIEW_W) // TILE_PX) + 1):
            for ty in range(int(top // TILE_PX), int((top + VIEW_H) // TILE_PX) + 1):
                try:
                    img = _fetch_tile(zoom, tx, ty, cache_dir, client, tile_url=IGN_ORTHO_URL, prefix="ign")
                except Exception:  # noqa: BLE001
                    continue
                if img:
                    tiles.append((round(tx * TILE_PX - left), round(ty * TILE_PX - top),
                                  "data:image/jpeg;base64," + base64.b64encode(img).decode()))

    def to_svg(gj, fill, stroke, sw):
        if not gj:
            return ""
        out = []
        for ring in _rings(json.loads(gj)):
            pts = " ".join(f"{_lonlat_to_px(lo, la, zoom)[0]-left:.1f},{_lonlat_to_px(lo, la, zoom)[1]-top:.1f}"
                           for lo, la in ring)
            out.append(f"<polygon points='{pts}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
        return "".join(out)

    imgs = "".join(f"<img src='{u}' style='position:absolute;left:{l}px;top:{t}px;width:256px;height:256px;'>"
                   for l, t, u in tiles)
    svg = (f"<svg width='{VIEW_W}' height='{VIEW_H}' style='position:absolute;left:0;top:0;'>"
           + to_svg(voirie_gj, "rgba(40,90,200,0.35)", "#2A5AC8", 0.8)
           + to_svg(parcelle_gj, "none", "#1E9E58", 3)
           + to_svg(bati_gj, "rgba(120,120,120,0.55)", "#666", 1)
           + to_svg(lot_gj, "rgba(201,138,0,0.30)", "#C98A00", 2.5)
           + to_svg(demolir_gj, "rgba(200,30,30,0.45)", "#B01818", 2) + "</svg>")
    return f"<div class='map' style='width:{VIEW_W}px;height:{VIEW_H}px;'>{imgs}{svg}</div>"


def build_review_dossier(session: Session, candidates: list[dict]) -> bytes:
    """Génère le PDF de revue (une carte par candidat) pour validation visuelle de Vic."""
    from weasyprint import HTML
    try:
        from ..flash.report import storage_dir
        cache_dir = storage_dir() / "tiles"
    except Exception:  # noqa: BLE001
        from pathlib import Path
        cache_dir = Path("/tmp/labuse_tiles")

    cards = []
    for i, c in enumerate(candidates, 1):
        type_div = c.get("type_division") or "libre"
        geoms = session.execute(text(_GEOMS), {"idu": c["idu"], "type": type_div}).mappings().first()
        carte = (_tiles_and_shapes(geoms["parcelle"], geoms["bati"], geoms["lot"], cache_dir,
                                   demolir_gj=geoms["demolir"], voirie_gj=geoms["voirie"]) if geoms else None)
        # mandat O12-PARTIEL-2 C1 : la marge Score É n'apparaît plus sur les fiches (c'est la
        # marge d'une opération de PROMOTION sur la parcelle entière, pas le produit d'une
        # division — chiffres négatifs massifs ; piste gelée, cf. O12_PARTIEL_RAPPORT.md)
        compacite = f"{c['compacite']}" if c.get("compacite") is not None else "—"
        # solidité (revue 2) : stockée pour les découpes, calculée à la volée pour les résiduels
        sol_val = c.get("solidite") if c.get("solidite") is not None else (
            geoms["solidite_calc"] if geoms else None)
        solidite = f"{sol_val}" if sol_val is not None else "—"
        type_txt = ("Division libre (lot nu — le terrain libre existe tel quel)" if type_div == "libre"
                    else f"Division avec démolition — dont {c.get('bati_lot_m2') or 0} m² à démolir"
                    if type_div == "demolition" else
                    "Lot À DÉCOUPER (hypothétique — le lot proposé exige un découpage géomètre)")
        zone_txt = (f"{c['zone']} ({c['zone_lib']})" if c.get("zone") and c.get("zone_lib")
                    else c.get("zone") or "RNU — PAU estimée")
        emprise_txt = (f"{c['emprise_restante'] * 100:.0f} % après division"
                       if c.get("emprise_restante") is not None else "—")
        statut = _STATUT_LABEL.get(c.get("revue_statut") or "", "")
        statut_html = f"<p class='statut'>{html.escape(statut)}</p>" if statut else ""
        cards.append(
            f"<div class='card'><h3>{i}. {html.escape(c['idu'])} — {html.escape(c['commune'])}</h3>"
            + statut_html
            + (carte or "<p class='leg'>Fond IGN indisponible.</p>")
            + "<p class='leg'>Tracés : <b class='p'>parcelle</b> · <b class='b'>bâti</b> · "
              "<b class='l'>lot proposé</b> · <b class='d'>bâti à démolir</b> · <b class='v'>voirie</b></p>"
            + f"<table><tr><td colspan='2'><b>{html.escape(type_txt)}</b></td>"
              f"<td>Zonage du lot</td><td>{html.escape(zone_txt)}</td></tr>"
              f"<tr><td>Emprise du lot restant</td><td>{html.escape(emprise_txt)}</td>"
              f"<td>Solidité du lot (aire/convexe)</td><td>{html.escape(solidite)}</td></tr>"
              f"<tr><td>Surface parcelle</td><td>{c['surface_m2']} m²</td>"
              f"<td>Emprise bâtie</td><td>{c['bati_ratio']*100:.0f} %</td></tr>"
              f"<tr><td>Lot détachable</td><td>{c['residuel_m2']} m²</td>"
              f"<td>Largeur constructible (⌀ inscrit)</td><td>~{c['residuel_rayon_m']*2:.0f} m</td></tr>"
              f"<tr><td>Façade voirie du lot</td><td>{c['residuel_facade_m']} m</td>"
              f"<td>Compacité du lot</td><td>{html.escape(compacite)}</td></tr></table>"
            + "<p class='valid'>Validation Vic : ☐ vrai positif &nbsp; ☐ faux positif &nbsp; ☐ douteux "
              "— remarque : ____________________</p></div>")

    intro = ("<div class='intro'><b>Dossier de revue — Division en or (O12).</b> Détection géométrique CONSERVATRICE "
             "de parcelles où un lot constructible semble détachable. Règles COMMUNES : accès voirie qualifiée "
             "≥ 12 m contigus, largeur ≥ 18 m (cercle inscrit), compacité, zonage U/AU (PAU estimée en RNU), hors "
             "littoral/domaine public et zonages d'activité, les deux lots restant viables (reste d'un seul tenant, "
             "façade conservée, emprise bâtie résultante plafonnée). Règles PAR FAMILLE — <b>lot résiduel</b> "
             "(libre ou avec démolition) : le terrain libre existe tel quel, résiduel ≥ 500 m² et ≤ 50 % de la "
             "parcelle ; <b>lot à découper</b> : bande de façade de 600-900 m² taillée dans le résiduel des parcelles "
             "où le terrain libre DÉPASSE 50 % — la borne « ≤ 50 % » ne s'applique pas à cette famille (sur petite "
             "parcelle, le lot peut peser plus de la moitié ; c'est la surface absolue et la viabilité du reste qui "
             "bornent). Solidité = aire ÷ enveloppe convexe (une bande franche ≈ 1, un lot en U autour d'un bâtiment "
             "chute) ; compacité = Polsby-Popper. <b>Revue EXHAUSTIVE</b> (revue 2) : un lot en U « modéré » n'est "
             "séparable d'une bande franche par AUCUN critère géométrique — la revue voit donc 100 % du pool, pas un "
             "échantillon. Le bandeau de chaque fiche indique si le tracé est nouveau, modifié depuis la revue "
             "précédente (à revoir) ou inchangé — la validation porte sur un tracé, pas sur un IDU. "
             "<b>Faux positif = péché mortel</b> : "
             "l'outil reste MASQUÉ tant que ce dossier n'est pas validé. Aucune constructibilité réglementaire n'est "
             "affirmée (recul, prospect, servitudes) — la revue tranche.</div>")
    doc = (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"
           f"<h1>Division en or — revue de {len(cards)} candidats</h1>{intro}{''.join(cards)}</body></html>")
    return HTML(string=doc).write_pdf()
