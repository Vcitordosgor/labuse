"""Dette #4 — revue ortho des têtes suspectes (couche batiment ≈ 0 vs preuve d'habitation).

Population : top 1000 rangs du run servi q_v8_calibre, emprise couche batiment < 20 m²,
croisée avec les preuves INDÉPENDANTES : piscine/PV (ortho_detections, hors faux positifs)
et vente DVF bâtie (dvf_mutations_parcelle.surface_reelle_bati > 0).
Sortie : qa/dette4/revue_suspectes.html — un lien satellite par parcelle (revue visuelle Vic).
Lecture seule. Rien de déclassé.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import psycopg

DB = os.environ.get("LABUSE_DB", "postgresql://openclaw@127.0.0.1:5432/labuse")
OUT = os.path.join(os.path.dirname(__file__), "revue_suspectes.html")

SQL = """
WITH top AS (SELECT s.parcelle_id idu, s.rang, s.tier FROM parcel_p_score_v2 s
             WHERE s.run_id='q_v8_calibre' AND s.rang<=1000),
bati0 AS (SELECT t.*, COALESCE(b.emprise_bati_m2,0)::int emprise FROM top t
          LEFT JOIN p_model_bati b ON b.idu=t.idu WHERE COALESCE(b.emprise_bati_m2,0) < 20),
det AS (SELECT idu, bool_or(type='piscine') pisc, bool_or(type='pv') pv,
               max(confiance) FILTER (WHERE type='piscine') conf_pisc
        FROM ortho_detections WHERE validation IS DISTINCT FROM 'faux_positif' GROUP BY idu),
dvfb AS (SELECT id_parcelle idu, max(date_mutation) dm, max(surface_reelle_bati) srb
         FROM dvf_mutations_parcelle WHERE surface_reelle_bati > 0 GROUP BY 1)
SELECT b.rang, b.tier, b.idu, p.commune, ST_Area(p.geom_2975)::int surf, b.emprise,
       d.pisc, d.conf_pisc, d.pv, v.srb, v.dm,
       ST_Y(ST_Transform(ST_Centroid(p.geom_2975),4326)) lat,
       ST_X(ST_Transform(ST_Centroid(p.geom_2975),4326)) lon
FROM bati0 b JOIN parcels p ON p.idu=b.idu
LEFT JOIN det d ON d.idu=b.idu LEFT JOIN dvfb v ON v.idu=b.idu
WHERE d.idu IS NOT NULL OR v.idu IS NOT NULL
ORDER BY b.rang
"""

CSS = ("body{font:14px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
       "h1{font-size:18px;color:#5CE6A1}table{border-collapse:collapse;width:100%}"
       "th{font:600 10px monospace;color:#8FA69A;text-align:left;padding:6px 8px;border-bottom:1px solid #2a352f}"
       "td{padding:7px 8px;border-bottom:1px solid #1a221e;font-size:12.5px}"
       ".idu{font-family:monospace;color:#ECF5EF}.t-brulante{color:#E8695A;font-weight:600}"
       ".t-chaude{color:#5CE6A1;font-weight:600}.muted{color:#5a6b62}"
       "a{color:#7DE8E0;text-decoration:none}a:hover{text-decoration:underline}")

with psycopg.connect(DB) as conn, conn.cursor() as cur:
    cur.execute(SQL)
    rows = cur.fetchall()

trs = []
for rang, tier, idu, com, surf, emp, pisc, cp, pv, srb, dm, lat, lon in rows:
    preuves = []
    if pisc: preuves.append(f"piscine (conf. {cp:.2f})")
    if pv: preuves.append("PV")
    if srb: preuves.append(f"DVF bâti {srb:.0f} m² ({dm})")
    gm = f"https://www.google.com/maps/@{lat},{lon},110m/data=!3m1!1e3"
    trs.append(f"<tr><td>{rang}</td><td class='t-{tier}'>{tier}</td>"
               f"<td class='idu'>{idu}<div class='muted'>{com}</div></td>"
               f"<td>{surf} m²<div class='muted'>couche bâti {emp} m²</div></td>"
               f"<td>{' + '.join(preuves)}</td>"
               f"<td><a href='{gm}' target='_blank'>satellite ↗</a></td></tr>")

html = (f"<!doctype html><meta charset='utf-8'><title>Dette #4 — têtes suspectes</title>"
        f"<style>{CSS}</style><h1>Dette #4 — {len(rows)} têtes suspectes "
        f"<span class='muted'>(couche batiment &lt; 20 m² MAIS preuve d'habitation — run q_v8_calibre, top 1000)</span></h1>"
        f"<p class='muted'>Revue visuelle : ouvrir « satellite ». Une maison visible = couche batiment lacunaire "
        f"(le type CH1893). Rien n'est déclassé par cette mesure.</p>"
        f"<table><tr><th>RANG</th><th>TIER</th><th>PARCELLE</th><th>SURFACE</th><th>PREUVES</th><th>ORTHO</th></tr>"
        + "".join(trs) + "</table>")
open(OUT, "w", encoding="utf-8").write(html)
print(f"{len(rows)} suspectes → {OUT}")
