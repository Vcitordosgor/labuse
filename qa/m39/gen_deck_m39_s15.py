"""M39 P2.2-ter — DECK du SCÉNARIO 15 % (piscine ≥ 15 % de la parcelle) pour revue Vic.

Vic : la piscine à 1-5 % d'une grande parcelle = maison occupée (filtre bâti), pas un signal
piscine. On mesure un critère de surface RELATIVE en plus de la bande absolue [15;60]. Ce deck
montre le scénario le plus probable : **pct piscine/parcelle ≥ 15 %** + garde de contenance
(centroïde dans la parcelle ET ratio piscine dans parcelle ≥ 0,5).

Contenu : les **5 retenues** (≥ 15 %) + **5 témoins juste sous le seuil** (pct décroissant sous 15),
même format géométrique que le deck principal (contour parcelle orange + polygone piscine bleu +
chiffres). Réutilise `carte()` de gen_deck_m39. Lecture seule.

Usage : PYTHONPATH=src python qa/m39/gen_deck_m39_s15.py
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
from gen_deck_m39 import carte  # noqa: E402  (même dossier)

OUT = os.path.join(HERE, "deck_m39_s15.html")
RUN = "q_v8_calibre"

# Base = règle [15;60] + contenance (centroïde dans ET ratio>=0,5). retenu = pct>=15 ; témoin = pct<15.
SQL = """
WITH base AS (
  SELECT s.parcelle_id AS idu, s.tier, p.surface_m2 AS surf_parc, d.surface_m2 AS surf_pool,
         p.geom, d.geom AS dgeom, p.geom_2975 pg, d.geom_2975 dg
  FROM parcel_p_score_v2 s
  JOIN parcel_equipements pe ON pe.idu=s.parcelle_id AND pe.piscine
  JOIN parcels p ON p.idu=s.parcelle_id
  JOIN LATERAL (SELECT geom, geom_2975, surface_m2 FROM ortho_detections
                WHERE idu=s.parcelle_id AND type='piscine' ORDER BY surface_m2 DESC LIMIT 1) d ON true
  WHERE s.run_id=:run AND s.tier IN ('brulante','chaude') AND pe.piscine_surface_m2 BETWEEN 15 AND 60
), g AS (
  SELECT idu, tier, round(surf_parc::numeric,0) surf_parc, round(surf_pool::numeric,1) surf_pool,
         round((100*surf_pool/NULLIF(surf_parc,0))::numeric,1) pct,
         round((ST_Area(ST_Intersection(ST_MakeValid(pg),ST_MakeValid(dg)))/NULLIF(ST_Area(ST_MakeValid(dg)),0))::numeric,2) ratio,
         ST_AsGeoJSON(geom) pgeo, ST_AsGeoJSON(dgeom) dgeo,
         (ST_Contains(ST_MakeValid(pg),ST_Centroid(dg)) AND
          ST_Area(ST_Intersection(ST_MakeValid(pg),ST_MakeValid(dg)))/NULLIF(ST_Area(ST_MakeValid(dg)),0) >= 0.5) contenue_ok
  FROM base )
SELECT idu, tier, surf_parc, surf_pool, pct, ratio, pgeo, dgeo,
       (pct >= 15) AS retenu
FROM g WHERE contenue_ok AND (pct >= 15 OR pct < 15)
ORDER BY (pct >= 15) DESC, pct DESC
LIMIT 10
"""


def main() -> None:
    with engine().connect() as c:
        rows = [dict(r) for r in c.execute(text(SQL), {"run": RUN}).mappings().all()]
    # 5 retenues + 5 témoins juste sous : garder les 5 retenues, puis les 5 témoins de pct max sous 15
    retenues = [r for r in rows if r["retenu"]]
    temoins = [r for r in rows if not r["retenu"]][:5]
    rows = retenues + temoins
    cards = []
    css = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
           "h1{font-size:19px;color:#3AA0FF;margin:2px 0}.sub{color:#8fbfa8}"
           ".card{margin:16px 0;padding:14px;background:#111814;border-radius:12px;display:flex;"
           "gap:16px;align-items:flex-start}.meta{min-width:300px}.k{color:#7d9;font-size:12px}"
           ".retenu{border:1px solid #5AE8A0}.temoin{border:1px dashed #E8B25A}"
           ".leg{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:5px}"
           ".big{font-size:16px;font-weight:600}.ok{color:#5AE8A0}.warn{color:#E8B25A}")
    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as cl:
        for i, r in enumerate(rows, 1):
            svg = carte(cl, r["pgeo"], r["dgeo"])
            ret = r["retenu"]
            tag = (f"<span class='ok'>RETENUE — piscine {r['pct']} % de la parcelle (≥ 15 %)</span>"
                   if ret else
                   f"<span class='warn'>TÉMOIN — piscine {r['pct']} % (&lt; 15 %, conservée)</span>")
            cards.append(
                f"<div class='card {'retenu' if ret else 'temoin'}'>"
                f"<div class='meta'><div class='k'>#{i} — {r['idu'][:5]} · tier {r['tier']}</div>"
                f"<h1>{r['idu']}</h1><div class='big'>{tag}</div>"
                f"<div style='margin-top:8px'>parcelle : <b>{r['surf_parc']} m²</b></div>"
                f"<div>piscine : <b>{r['surf_pool']} m²</b> · ratio dans parcelle {r['ratio']}</div>"
                f"<div class='sub' style='margin-top:8px'><span class='leg' style='background:#F2A24E'></span>"
                f"contour parcelle &nbsp;<span class='leg' style='background:#3AA0FF'></span>piscine</div>"
                f"</div>{svg}</div>")
    html = (f"<!doctype html><meta charset='utf-8'><style>{css}</style>"
            f"<h1>M39 — Scénario 15 % (piscine ≥ 15 % de la parcelle) + contenance</h1>"
            f"<div class='sub'>{len(retenues)} RETENUES (≥ 15 %) + {len(temoins)} TÉMOINS juste sous "
            f"le seuil. Règle testée : bande [15;60] m² <b>ET</b> piscine ≥ 15 % de la parcelle "
            f"<b>ET</b> contenance (centroïde dans + ratio ≥ 0,5). Ortho IGN 2025. "
            f"Question : à ce seuil, la piscine occupe-t-elle assez pour signaler un usage installé ?"
            f"</div>{''.join(cards)}")
    Path(OUT).write_text(html, encoding="utf-8")
    print(f"✓ deck 15 % écrit : {OUT} ({len(retenues)} retenues + {len(temoins)} témoins)")


if __name__ == "__main__":
    main()
