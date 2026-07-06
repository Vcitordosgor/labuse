"""Rendu HTML statique du top N chaudes d'un run dry-run — OUTIL DE REVUE INTERNE.

Une carte par parcelle : IDU, Q/A, complétude, statut, TOUS les motifs tracés (signal + points +
source + détail), flags, coordonnées, liens satellite/géoportail/cadastre pour contrôle visuel.
Pas le produit : un rig de contrôle d'absurdité pour Vic.

Usage : LABUSE_DATABASE_URL=... python scripts/render_top_chaudes.py <run_label> [N] [commune]
"""
from __future__ import annotations

import html
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from labuse.db import engine

RUN = sys.argv[1] if len(sys.argv) > 1 else "q_v2"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30
COMMUNE = sys.argv[3] if len(sys.argv) > 3 else "Saint-Paul"
OUT = f"outputs/top{N}_chaudes_{RUN}.html"

CSS = """
:root{--bg:#0f1216;--card:#181d24;--line:#262d38;--txt:#e6e9ee;--muted:#8b95a5;--pos:#3fb37f;--neg:#e0645f;--flag:#d9a441;--acc:#5b9bd5}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:20px 28px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:18px}
.sub{color:var(--muted);font-size:13px;margin-top:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:16px;padding:20px 28px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.chd{display:flex;justify-content:space-between;align-items:baseline;padding:12px 16px;border-bottom:1px solid var(--line)}
.idu{font-family:ui-monospace,Menlo,monospace;font-size:15px;font-weight:600}
.rank{color:var(--muted);font-size:12px}
.scores{display:flex;gap:8px;padding:10px 16px;flex-wrap:wrap;border-bottom:1px solid var(--line)}
.pill{background:#12161c;border:1px solid var(--line);border-radius:20px;padding:3px 11px;font-size:12px}
.pill b{color:var(--acc)}
.motifs{padding:8px 16px 12px}.mrow{display:flex;gap:8px;padding:5px 0;border-bottom:1px dashed #222932}
.mrow:last-child{border:0}.w{font-family:ui-monospace,monospace;min-width:44px;text-align:right;font-weight:600}
.w.p{color:var(--pos)}.w.n{color:var(--neg)}.w.z{color:var(--muted)}
.mbody{flex:1}.mlayer{font-weight:600}.mlayer .ev{color:var(--flag);font-weight:700}
.mdet{color:var(--muted);font-size:12.5px}.msrc{color:#5a6472;font-size:11px}
.links{padding:10px 16px;border-top:1px solid var(--line);display:flex;gap:14px;flex-wrap:wrap}
.links a{color:var(--acc);text-decoration:none;font-size:12.5px}.links a:hover{text-decoration:underline}
.coord{color:var(--muted);font-size:11.5px;font-family:ui-monospace,monospace}
"""


def wclass(w):
    if w is None:
        return "z", ""
    return ("p", f"{w:+g}") if w > 0 else (("n", f"{w:+g}") if w < 0 else ("z", "0"))


def render():
    with Session(engine()) as s:
        rows = s.execute(text(
            "SELECT p.id, p.idu, d.q_score, d.a_score, d.a_completude, d.completeness_score, "
            "  d.matrice_statut, d.opportunity_score, "
            "  round(ST_Y(ST_Transform(ST_Centroid(p.geom_2975),4326))::numeric,6) AS lat, "
            "  round(ST_X(ST_Transform(ST_Centroid(p.geom_2975),4326))::numeric,6) AS lon "
            "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
            "WHERE d.run_label=:r AND p.commune=:c AND d.matrice_statut='chaude' "
            "ORDER BY d.q_score+d.a_score DESC, d.q_score DESC LIMIT :n"),
            {"r": RUN, "c": COMMUNE, "n": N}).mappings().all()

        cards = []
        for i, row in enumerate(rows, 1):
            lines = s.execute(text(
                "SELECT cr.layer_name, cr.result, cr.weight_applied, cr.detail, cr.severity, "
                "  cr.evenement, cr.source_table, cr.source_id, ds.name AS source "
                "FROM dryrun_cascade_results cr LEFT JOIN data_sources ds ON ds.id=cr.data_source_id "
                "WHERE cr.run_label=:r AND cr.parcel_id=:pid "
                "ORDER BY (cr.weight_applied IS NULL), abs(COALESCE(cr.weight_applied,0)) DESC, cr.layer_name"),
                {"r": RUN, "pid": row["id"]}).mappings().all()

            mrows = []
            for ln in lines:
                # on montre : tout ce qui pèse, plus les flags/unknown signifiants (pas les PASS neutres)
                w = ln["weight_applied"]
                is_flag = ln["result"] in ("SOFT_FLAG", "HARD_EXCLUDE", "UNKNOWN") or ln["evenement"]
                if w is None and not is_flag:
                    continue
                cls, wtxt = wclass(float(w) if w is not None else None)
                if w is None:
                    tag = {"UNKNOWN": "?", "SOFT_FLAG": "⚑", "HARD_EXCLUDE": "✕"}.get(ln["result"], "·")
                    wtxt = tag
                ev = ' <span class="ev">● ROUGE</span>' if ln["evenement"] == "rouge" else ""
                src = ln["source"] or ""
                trace = f' · {ln["source_table"]}#{ln["source_id"]}' if ln["source_id"] else ""
                mrows.append(
                    f'<div class="mrow"><div class="w {cls}">{html.escape(str(wtxt))}</div>'
                    f'<div class="mbody"><div class="mlayer">{html.escape(ln["layer_name"])}{ev}</div>'
                    f'<div class="mdet">{html.escape(ln["detail"] or "")}</div>'
                    f'<div class="msrc">{html.escape(src)}{html.escape(trace)}</div></div></div>')

            lat, lon = row["lat"], row["lon"]
            gmaps = f"https://www.google.com/maps/@{lat},{lon},19z/data=!3m1!1e3"
            geopf = f"https://www.geoportail.gouv.fr/carte?c={lon},{lat}&z=19&l0=ORTHOIMAGERY.ORTHOPHOTOS"
            cadastre = "https://www.cadastre.gouv.fr/scpc/rechercherPlan.do"
            cards.append(f"""
<div class="card">
  <div class="chd"><span class="idu">{html.escape(row['idu'])}</span><span class="rank">#{i} · {html.escape(row['matrice_statut'])}</span></div>
  <div class="scores">
    <span class="pill">Q <b>{row['q_score']}</b></span>
    <span class="pill">A <b>{row['a_score']}</b></span>
    <span class="pill">A-compl <b>{row['a_completude'] if row['a_completude'] is not None else '—'}</b></span>
    <span class="pill">complétude <b>{row['completeness_score']}</b></span>
    <span class="pill">opp <b>{row['opportunity_score']}</b></span>
  </div>
  <div class="motifs">{''.join(mrows)}</div>
  <div class="links">
    <span class="coord">{lat}, {lon}</span>
    <a href="{gmaps}" target="_blank">🛰 satellite</a>
    <a href="{geopf}" target="_blank">géoportail</a>
    <a href="{cadastre}" target="_blank">cadastre</a>
  </div>
</div>""")

        doc = (f"<!doctype html><html lang=fr><head><meta charset=utf-8>"
               f"<meta name=viewport content='width=device-width,initial-scale=1'>"
               f"<title>Top {N} chaudes — {RUN}</title><style>{CSS}</style></head><body>"
               f"<header><h1>Top {len(rows)} chaudes — run <code>{html.escape(RUN)}</code> — {html.escape(COMMUNE)}</h1>"
               f"<div class=sub>Contrôle d'absurdité interne. Chaque ligne = signal tracé (points · détail · source#id). "
               f"Q = constructibilité/qualité · A = vendeur (pur). ● ROUGE = bascule BODACC.</div></header>"
               f"<div class=grid>{''.join(cards)}</div></body></html>")
        with open(OUT, "w") as f:
            f.write(doc)
        print(f"✓ {OUT} — {len(rows)} chaudes")


if __name__ == "__main__":
    render()
