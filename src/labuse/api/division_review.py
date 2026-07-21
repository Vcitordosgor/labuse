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

# géométries par candidat : parcelle, bâti (union), lot détachable (plus grand résiduel après retrait du bâti bufferisé)
_GEOMS = """
WITH p AS (SELECT geom_2975, ST_AsGeoJSON(geom, 7) gj FROM parcels WHERE idu = :idu),
bat AS (SELECT ST_Union(b.geom_2975) g FROM spatial_layers b, p
        WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)),
free AS (SELECT lg.geom g FROM p, bat
         CROSS JOIN LATERAL (SELECT gg.geom FROM ST_Dump(ST_Difference(p.geom_2975, ST_Buffer(bat.g,3))) gg
                             ORDER BY ST_Area(gg.geom) DESC LIMIT 1) lg)
SELECT p.gj AS parcelle,
       ST_AsGeoJSON(ST_Transform(bat.g, 4326), 7) AS bati,
       ST_AsGeoJSON(ST_Transform(free.g, 4326), 7) AS lot
FROM p, bat, free;
"""

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
.leg b.p{color:#0B8A5F} .leg b.b{color:#888} .leg b.l{color:#C98A00}
.valid { margin-top:1.5mm; font-size:8.5pt; }
"""


def _tiles_and_shapes(parcelle_gj, bati_gj, lot_gj, cache_dir):
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
           + to_svg(parcelle_gj, "none", "#0B8A5F", 3)
           + to_svg(bati_gj, "rgba(120,120,120,0.55)", "#666", 1)
           + to_svg(lot_gj, "rgba(201,138,0,0.30)", "#C98A00", 2.5) + "</svg>")
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
        geoms = session.execute(text(_GEOMS), {"idu": c["idu"]}).mappings().first()
        carte = _tiles_and_shapes(geoms["parcelle"], geoms["bati"], geoms["lot"], cache_dir) if geoms else None
        gain = f"{c['gain_estime_eur']:,} €".replace(",", " ") if c.get("gain_estime_eur") else "non estimable"
        cards.append(
            f"<div class='card'><h3>{i}. {html.escape(c['idu'])} — {html.escape(c['commune'])}</h3>"
            + (carte or "<p class='leg'>Fond IGN indisponible.</p>")
            + "<p class='leg'>Tracés : <b class='p'>parcelle</b> · <b class='b'>bâti</b> · "
              "<b class='l'>lot détachable proposé</b></p>"
            + f"<table><tr><td>Surface parcelle</td><td>{c['surface_m2']} m²</td>"
              f"<td>Emprise bâtie</td><td>{c['bati_ratio']*100:.0f} %</td></tr>"
              f"<tr><td>Lot détachable</td><td>{c['residuel_m2']} m²</td>"
              f"<td>Largeur constructible (⌀ inscrit)</td><td>~{c['residuel_rayon_m']*2:.0f} m</td></tr>"
              f"<tr><td>Façade voirie du lot</td><td>{c['residuel_facade_m']} m</td>"
              f"<td>Gain estimé (Score É, Estimé)</td><td>{gain}</td></tr></table>"
            + "<p class='valid'>Validation Vic : ☐ vrai positif &nbsp; ☐ faux positif &nbsp; ☐ douteux "
              "— remarque : ____________________</p></div>")

    intro = ("<div class='intro'><b>Dossier de revue — Division en or (O12).</b> Détection géométrique CONSERVATRICE "
             "de parcelles où un lot constructible semble détachable (bâti dans un coin, résiduel ≥ 500 m² avec accès "
             "voirie ≥ 12 m et largeur ≥ 18 m, les deux lots restant viables). <b>Faux positif = péché mortel</b> : "
             "l'outil reste MASQUÉ tant que ce dossier n'est pas validé. Aucune constructibilité réglementaire n'est "
             "affirmée (recul, prospect, servitudes) — la revue tranche.</div>")
    doc = (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"
           f"<h1>Division en or — revue de {len(cards)} candidats</h1>{intro}{''.join(cards)}</body></html>")
    return HTML(string=doc).write_pdf()
