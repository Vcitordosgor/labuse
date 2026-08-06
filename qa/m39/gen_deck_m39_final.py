"""M39 P2 (final) — DECK de la RÈGLE FIGÉE : les 4 déclassées + CY0985 en témoin EXCLU.

Règle figée (seuil Vic) : bande [15;60] m² · part ≥ 15 % · contenance (centroïde dans + ratio ≥ 0,7).
Montre les 4 RETENUES et **CY0985 (ratio 0,55 < 0,7)** en témoin exclu — la garde de contenance a
fait son travail (piscine visiblement mitoyenne, à moitié chez le voisin). Format géométrique :
contour parcelle (orange) + polygone piscine (bleu) + chiffres. Réutilise carte() de gen_deck_m39.

Usage : PYTHONPATH=src python qa/m39/gen_deck_m39_final.py
"""
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, HERE)

import httpx  # noqa: E402
from pathlib import Path  # noqa: E402
from sqlalchemy import text  # noqa: E402

from labuse.api.division_review import USER_AGENT  # noqa: E402
from labuse.db import engine  # noqa: E402
from gen_deck_m39 import carte  # noqa: E402

OUT = os.path.join(HERE, "deck_m39_final.html")
RUN = "q_v8_calibre"
RETENUES = ("97401000AR1289", "97408000AC2215", "97415000BV0606", "97415000CX0650")
TEMOIN_EXCLU = "97415000CY0985"  # ratio 0,55 < 0,7 : piscine mitoyenne, écartée par la contenance

SQL = """
SELECT s.parcelle_id AS idu, s.tier, round(p.surface_m2::numeric,0) surf_parc,
       round(d.surface_m2::numeric,1) surf_pool, round((100*d.surface_m2/NULLIF(p.surface_m2,0))::numeric,1) pct,
       round((ST_Area(ST_Intersection(ST_MakeValid(p.geom_2975),ST_MakeValid(d.geom_2975)))
              /NULLIF(ST_Area(ST_MakeValid(d.geom_2975)),0))::numeric,2) ratio,
       ST_AsGeoJSON(p.geom) pgeo, ST_AsGeoJSON(d.geom) dgeo
FROM parcel_p_score_v2 s
JOIN parcels p ON p.idu=s.parcelle_id
JOIN LATERAL (SELECT geom, geom_2975, surface_m2 FROM ortho_detections
              WHERE idu=s.parcelle_id AND type='piscine' ORDER BY surface_m2 DESC LIMIT 1) d ON true
WHERE s.run_id=:run AND s.parcelle_id = ANY(:idus)
"""


def main() -> None:
    idus = list(RETENUES) + [TEMOIN_EXCLU]
    with engine().connect() as c:
        by = {r["idu"]: dict(r) for r in c.execute(text(SQL), {"run": RUN, "idus": idus}).mappings().all()}
    rows = [by[i] for i in idus if i in by]
    css = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
           "h1{font-size:19px;color:#3AA0FF;margin:2px 0}.sub{color:#8fbfa8}"
           ".card{margin:16px 0;padding:14px;background:#111814;border-radius:12px;display:flex;"
           "gap:16px;align-items:flex-start}.meta{min-width:300px}.k{color:#7d9;font-size:12px}"
           ".ret{border:1px solid #5AE8A0}.exc{border:2px dashed #E8695A}"
           ".leg{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:5px}"
           ".big{font-size:16px;font-weight:600}.ok{color:#5AE8A0}.no{color:#E8695A}")
    cards = []
    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as cl:
        for i, r in enumerate(rows, 1):
            svg = carte(cl, r["pgeo"], r["dgeo"])
            exclu = r["idu"] == TEMOIN_EXCLU
            tag = (f"<span class='no'>TÉMOIN EXCLU — ratio {r['ratio']} &lt; 0,7 : piscine mitoyenne, "
                   f"à moitié chez le voisin → la garde de contenance l'écarte</span>" if exclu else
                   f"<span class='ok'>DÉCLASSÉE — {r['pct']} % de la parcelle, ratio {r['ratio']} ≥ 0,7</span>")
            cards.append(
                f"<div class='card {'exc' if exclu else 'ret'}'>"
                f"<div class='meta'><div class='k'>#{i} — {r['idu'][:5]} · tier {r['tier']}</div>"
                f"<h1>{r['idu']}</h1><div class='big'>{tag}</div>"
                f"<div style='margin-top:8px'>parcelle : <b>{r['surf_parc']} m²</b></div>"
                f"<div>piscine : <b>{r['surf_pool']} m²</b> ({r['pct']} % de la parcelle)</div>"
                f"<div class='sub' style='margin-top:8px'><span class='leg' style='background:#F2A24E'></span>"
                f"contour parcelle &nbsp;<span class='leg' style='background:#3AA0FF'></span>piscine</div>"
                f"</div>{svg}</div>")
    html = (f"<!doctype html><meta charset='utf-8'><style>{css}</style>"
            f"<h1>M39 — Règle figée : 4 déclassées + 1 témoin exclu (dette #13)</h1>"
            f"<div class='sub'>Règle : bande [15;60] m² · part piscine ≥ 15 % · contenance (centroïde "
            f"dans + ratio ≥ 0,7). <b class='ok'>4 déclassées</b> (petites parcelles 125–216 m² saturées) "
            f"+ <b class='no'>CY0985 témoin exclu</b> (ratio 0,55 : bassin mitoyen — la garde a fait son "
            f"travail). Ortho IGN 2025.</div>{''.join(cards)}")
    Path(OUT).write_text(html, encoding="utf-8")
    print(f"✓ deck final : {OUT} ({len(RETENUES)} retenues + 1 témoin exclu)")


if __name__ == "__main__":
    main()
