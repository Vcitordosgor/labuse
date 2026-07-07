#!/usr/bin/env python3
"""Tops HTML — support du contrôle d'absurdité de Vic (mandat île, phase 3a).

Un fichier par commune (top 10 chaudes, complété « à surveiller » si < 10) + un top 50 île.
Chaque ligne = IDU, statut, événement, Q/A/complétude, surface, zone PLU, SDP résiduelle,
vue mer, propriétaire (PM), le POURQUOI (meilleures lignes de cascade) et deux liens de
contrôle : Google Maps satellite (l'absurdité se voit à l'ortho : rue, parking, tennis…)
et la fiche produit (deep-link omnibox).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

DB = os.environ.get("LABUSE_DB", "postgresql://openclaw@127.0.0.1:5432/labuse")
OUT = Path(__file__).resolve().parents[1] / "docs" / "tops_ile"
APP = "http://127.0.0.1:8010/socle/"

CSS = """body{font:14px/1.5 -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}
h1{font-size:19px;color:#5CE6A1}h1 small{color:#8FA69A;font-weight:400}
table{border-collapse:collapse;width:100%;margin-top:12px}
th{font:600 10px monospace;letter-spacing:.08em;color:#8FA69A;text-align:left;padding:6px 8px;border-bottom:1px solid #2a352f}
td{padding:8px;border-bottom:1px solid #1a221e;vertical-align:top}
.idu{font:600 12px monospace;color:#ECF5EF;white-space:nowrap}
.st-chaude{color:#5CE6A1;font-weight:600}.st-a_surveiller{color:#4ADE96}.st-a_creuser{color:#E8B44C}
.ev{background:#3a1614;color:#E8695A;border-radius:99px;padding:1px 7px;font-size:10px;font-weight:600}
.why{font-size:11px;color:#8FA69A;max-width:420px}.why b{color:#b8cbc0}
a{color:#7DE8E0;text-decoration:none;font-size:11px}a:hover{text-decoration:underline}
.num{font-family:monospace;text-align:right}.muted{color:#5a6b62;font-size:11px}"""

SQL_TOP = """
SELECT p.idu, p.commune, d.matrice_statut AS st, d.q_score, d.a_score, d.a_completude,
       d.completeness_score, round(p.surface_m2) AS surface,
       r.sdp_residuelle_m2, vm.vue AS vue_mer,
       (ev.parcel_id IS NOT NULL) AS evenement,
       pm.denomination AS proprio, pm.siren,
       (SELECT count(*) FROM dryrun_parcel_evaluations d2
        JOIN parcels p2 ON p2.id = d2.parcel_id
        JOIN parcelle_personne_morale pm2 ON pm2.idu = p2.idu
        WHERE d2.run_label = %(run)s AND d2.matrice_statut = 'chaude'
          AND pm2.siren = pm.siren) AS cluster,
       ST_Y(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lat,
       ST_X(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lon,
       zc.detail AS zone_detail
FROM dryrun_parcel_evaluations d
JOIN parcels p ON p.id = d.parcel_id
LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
LEFT JOIN parcel_vue_mer vm ON vm.parcel_id = p.id
LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
           WHERE run_label = %(run)s AND evenement = 'rouge') ev ON ev.parcel_id = p.id
LEFT JOIN LATERAL (SELECT detail FROM dryrun_cascade_results c
                   WHERE c.run_label = %(run)s AND c.parcel_id = p.id
                     AND c.layer_name = 'zonage_plu_gpu' LIMIT 1) zc ON true
WHERE d.run_label = %(run)s
  AND (%(commune)s::text IS NULL OR p.commune = %(commune)s)
  AND d.matrice_statut = ANY(%(statuts)s)
ORDER BY (ev.parcel_id IS NOT NULL) DESC, (d.matrice_statut = 'chaude') DESC,
         (d.q_score + d.a_score) DESC
LIMIT %(n)s
"""

SQL_WHY = """
SELECT layer_name, result, weight_applied, detail FROM dryrun_cascade_results
WHERE run_label = %(run)s AND parcel_id = (SELECT id FROM parcels WHERE idu = %(idu)s)
  AND weight_applied IS NOT NULL AND weight_applied <> 0
ORDER BY abs(weight_applied) DESC LIMIT 4
"""


def esc(s: object) -> str:
    return str(s if s is not None else "—").replace("&", "&amp;").replace("<", "&lt;")


def rows_html(cur, rows) -> str:
    out = []
    for r in rows:
        cur.execute(SQL_WHY, {"run": "q_v2", "idu": r["idu"]})
        why = " · ".join(f"<b>{esc(w['layer_name'])}</b> {int(w['weight_applied']):+d}" for w in cur.fetchall())
        import re as _re
        zm = _re.search(r"« ([^»]+) »", r["zone_detail"] or "")
        zone = zm.group(1) if zm else "—"
        gmaps = f"https://www.google.com/maps/@{r['lat']},{r['lon']},120m/data=!3m1!1e3"
        app = f"{APP}#f=1&c={r['commune'].replace(' ', '%20')}"
        out.append(f"""<tr>
<td class="idu">{esc(r['idu'][8:10])} {esc(r['idu'][10:])}<div class="muted">{esc(r['commune'])}</div></td>
<td><span class="st-{r['st']}">{esc(r['st'])}</span>{' <span class="ev">● ÉVÉNEMENT</span>' if r['evenement'] else ''}</td>
<td class="num">Q {r['q_score']} · A {r['a_score']}<div class="muted">compl. {r['completeness_score']} %</div></td>
<td class="num">{int(r['surface'] or 0):,} m²<div class="muted">SDP {int(r['sdp_residuelle_m2'] or 0):,} m²</div></td>
<td>{esc(zone)}{'<div class="muted">vue mer</div>' if r['vue_mer'] == 'oui' else ''}</td>
<td class="why">{why or '—'}<div class="muted">{esc(r['proprio'] or 'proprio : personne physique / n.c.')}{f" · DOSSIER ×{r['cluster']}" if (r['cluster'] or 0) > 1 else ''}</div></td>
<td><a href="{gmaps}" target="_blank">satellite ↗</a><br><a href="{app}" target="_blank">produit ↗</a><div class="muted">omnibox : {esc(r['idu'][8:])}</div></td>
</tr>""".replace(",", " "))
    return "\n".join(out)


def page(title: str, sub: str, body: str) -> str:
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style><body><h1>{title} <small>{sub}</small></h1>
<table><tr><th>PARCELLE</th><th>STATUT</th><th>SCORES</th><th>SURFACE</th><th>ZONE PLU</th><th>POURQUOI (poids dominants) · PROPRIO</th><th>CONTRÔLE</th></tr>
{body}</table>
<p class="muted">Généré depuis dryrun_parcel_evaluations run q_v2 — tri : événement, puis statut, puis Q+A.
Contrôle d'absurdité : ouvrir « satellite » (rue/parking/terrain de sport = faux positif à signaler).</p></body></html>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(DB) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("SELECT DISTINCT commune FROM parcels ORDER BY 1")
        communes = [r["commune"] for r in cur.fetchall()]
        for c in communes:
            cur.execute(SQL_TOP, {"run": "q_v2", "commune": c, "statuts": ["chaude"], "n": 10})
            rows = cur.fetchall()
            note = f"top {len(rows)} chaudes"
            if len(rows) < 10:   # commune sans 10 chaudes : compléter « à surveiller » (annoncé)
                cur.execute(SQL_TOP, {"run": "q_v2", "commune": c,
                                      "statuts": ["a_surveiller"], "n": 10 - len(rows)})
                extra = cur.fetchall()
                rows += extra
                note = f"{note} + {len(extra)} à surveiller (complément)"
            slug = c.lower().replace(" ", "_").replace("'", "_").replace("-", "_").replace("é", "e").replace("è", "e").replace("î", "i").replace("û", "u")
            (OUT / f"top10_{slug}.html").write_text(
                page(f"TOP — {c}", note, rows_html(cur, rows)), encoding="utf-8")
            print(f"  {c}: {note}")
        cur.execute(SQL_TOP, {"run": "q_v2", "commune": None, "statuts": ["chaude"], "n": 50})
        rows = cur.fetchall()
        (OUT / "top50_ile.html").write_text(
            page("TOP 50 ÎLE — chaudes", f"{len(rows)} chaudes (24 communes)", rows_html(cur, rows)),
            encoding="utf-8")
        print(f"  ÎLE: top {len(rows)} chaudes")
    print(f"✓ tops écrits dans {OUT}")


if __name__ == "__main__":
    sys.exit(main())
