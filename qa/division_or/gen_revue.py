#!/usr/bin/env python
"""O12 Division en or — DOSSIER DE REVUE 20 CARTES (pattern J3, validation visuelle Vic).

Génère qa/division_or/revue/carte_01.png … carte_20.png : pour chaque candidat du top
(clarté décroissante, MÊME tri que division_or.top_candidates), une carte vectorielle
EPSG:2975 (mètres, aspect égal) avec :
  · la PARCELLE (contour menthe épais) et les parcelles voisines (contexte gris léger) ;
  · l'EMPRISE BÂTIE (BD TOPO, gris rempli) ;
  · le LOT DÉTACHABLE proposé (MÊME formule que le détecteur : plus grand polygone de
    parcelle − bâti bufferisé 3 m — hachures cuivre) + son cercle inscrit (pointillé) ;
  · l'ACCÈS VOIRIE du lot (segments de façade ≥ … en jaune épais) + la voirie en contexte ;
  · légende : IDU, commune, surface totale, surface du lot, largeur du cercle inscrit
    (2 × rayon), façade voirie du lot.

LECTURE SEULE (SELECT uniquement). La géométrie du lot est RECONSTRUITE avec la formule
exacte du détecteur (division_or._DETECT) — aucune géométrie stockée, aucun écart possible.
Rappel doctrinal : POTENTIEL géométrique — rien n'est affirmé sur la constructibilité
réglementaire ; l'accès restant du lot BÂTI se juge À L'ŒIL sur ces cartes (finding O12).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from shapely.geometry import shape
from shapely.plotting import plot_polygon, plot_line
from sqlalchemy import create_engine, text

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
OUT = os.path.join(os.path.dirname(__file__), "revue")
N = 20

# Une passe SQL par candidat : parcelle, bâti, lot (formule du détecteur), cercle inscrit,
# façade voirie du lot, voisins et voirie en contexte. Tout en EPSG:2975 (mètres).
GEO_SQL = """
WITH p AS (SELECT id, idu, geom_2975 FROM parcels WHERE idu = :idu),
bat AS (SELECT ST_Union(b.geom_2975) AS g FROM spatial_layers b, p
        WHERE b.kind = 'batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)),
lot AS (SELECT g.geom FROM p, bat,
        LATERAL ST_Dump(ST_Difference(p.geom_2975, ST_Buffer(bat.g, 3))) g
        ORDER BY ST_Area(g.geom) DESC LIMIT 1),
mic AS (SELECT (ST_MaximumInscribedCircle(lot.geom)).* FROM lot)
SELECT
  ST_AsGeoJSON(p.geom_2975)                                            AS parcelle,
  ST_AsGeoJSON(ST_Intersection(bat.g, p.geom_2975))                    AS bati,
  ST_AsGeoJSON(lot.geom)                                               AS lot,
  ST_AsGeoJSON(mic.center)                                             AS mic_center,
  mic.radius                                                           AS mic_radius,
  ST_AsGeoJSON((SELECT ST_Union(ST_Intersection(ST_Buffer(v.geom_2975, 1.5), ST_Boundary(lot.geom)))
                FROM spatial_layers v
                WHERE v.kind = 'voirie' AND ST_DWithin(v.geom_2975, lot.geom, 2)))   AS acces,
  ST_AsGeoJSON((SELECT ST_Collect(ST_Intersection(v.geom_2975, ST_Expand(ST_Envelope(p.geom_2975), 40)))
                FROM spatial_layers v
                WHERE v.kind = 'voirie'
                  AND ST_Intersects(v.geom_2975, ST_Expand(ST_Envelope(p.geom_2975), 40)))) AS voirie,
  ST_AsGeoJSON((SELECT ST_Collect(pv.geom_2975) FROM parcels pv, p
                WHERE pv.id <> p.id
                  AND ST_Intersects(pv.geom_2975, ST_Expand(ST_Envelope(p.geom_2975), 30)))) AS voisins
FROM p, bat, lot, mic;
"""

# palette (charte : menthe / cuivre M-RENOUV / gris)
C = {"parcelle": "#2f7a54", "voisin": "#9aa7a0", "bati": "#6b7672", "bati_edge": "#4a5450",
     "lot": "#C9834E", "acces": "#f4d35e", "voirie": "#c4cdc8", "mic": "#8a5a30"}


def g(row, key):
    v = row[key]
    return shape(json.loads(v)) if v else None


def each(geom, kinds):
    """Itère récursivement les sous-géométries des types voulus (les collections
    PostGIS mélangent points/lignes/polygones — plot_* de shapely ne les gère pas)."""
    if geom is None or geom.is_empty:
        return
    if geom.geom_type in ("MultiPolygon", "MultiLineString", "MultiPoint", "GeometryCollection"):
        for sub in geom.geoms:
            yield from each(sub, kinds)
    elif geom.geom_type in kinds:
        yield geom


def draw_polys(ax, geom, **kw):
    for p in each(geom, ("Polygon",)):
        plot_polygon(p, ax=ax, add_points=False, **kw)


def draw_lines(ax, geom, **kw):
    for l in each(geom, ("LineString", "LinearRing")):
        plot_line(l, ax=ax, add_points=False, **kw)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    eng = create_engine(DB)
    with eng.connect() as cx:
        cands = cx.execute(text(
            "SELECT * FROM division_or_candidates "
            "ORDER BY clarte DESC, residuel_m2 DESC LIMIT :n"), {"n": N}).mappings().all()
        if len(cands) < N:
            print(f"ATTENTION : {len(cands)} candidats seulement (< {N})")
        for i, cand in enumerate(cands, 1):
            row = cx.execute(text(GEO_SQL), {"idu": cand["idu"]}).mappings().first()
            if not row or not row["lot"]:
                print(f"carte_{i:02d} : géométrie irrecomposable pour {cand['idu']} — SAUTÉE")
                continue
            parcelle, bati, lot = g(row, "parcelle"), g(row, "bati"), g(row, "lot")
            acces, voirie, voisins = g(row, "acces"), g(row, "voirie"), g(row, "voisins")
            center = g(row, "mic_center")

            fig, ax = plt.subplots(figsize=(9.6, 8.6), dpi=150)
            # contexte
            draw_polys(ax, voisins, facecolor="none", edgecolor=C["voisin"], linewidth=0.5, alpha=0.6)
            draw_lines(ax, voirie, color=C["voirie"], linewidth=2.2, alpha=0.8)
            # lot proposé (hachures cuivre) puis bâti par-dessus
            draw_polys(ax, lot, facecolor=C["lot"], alpha=0.28,
                       edgecolor=C["lot"], linewidth=1.6, hatch="//")
            draw_polys(ax, bati, facecolor=C["bati"], alpha=0.85,
                       edgecolor=C["bati_edge"], linewidth=0.8)
            # parcelle (contour épais, par-dessus tout)
            draw_polys(ax, parcelle, facecolor="none", edgecolor=C["parcelle"], linewidth=2.4)
            # cercle inscrit du lot (pointillé)
            if center is not None and row["mic_radius"]:
                ax.add_patch(Circle((center.x, center.y), float(row["mic_radius"]),
                                    fill=False, edgecolor=C["mic"], linewidth=1.4, linestyle=":"))
            # façade voirie du lot (jaune épais)
            draw_lines(ax, acces, color=C["acces"], linewidth=5.0, alpha=0.95, capstyle="round")

            # cadrage : parcelle + marge 15 m
            minx, miny, maxx, maxy = parcelle.bounds
            m = 15
            ax.set_xlim(minx - m, maxx + m); ax.set_ylim(miny - m, maxy + m)
            ax.set_aspect("equal"); ax.axis("off")

            # échelle 20 m
            sx, sy = minx - m + 8, miny - m + 6
            ax.plot([sx, sx + 20], [sy, sy], color="#333", lw=2)
            ax.text(sx + 10, sy + 1.5, "20 m", ha="center", fontsize=7, color="#333")

            largeur = 2 * float(cand["residuel_rayon_m"])
            ax.set_title(f"carte {i:02d}/20 — {cand['idu']} · {cand['commune']}   "
                         f"(clarté {cand['clarte']})", fontsize=11, loc="left")
            legende = (
                f"surface totale {cand['surface_m2']:,} m² · lot proposé {cand['residuel_m2']:,} m² · "
                f"largeur cercle inscrit {largeur:.0f} m · façade voirie du lot {cand['residuel_facade_m']} m\n"
                f"bâti {cand['bati_m2']:,} m² ({float(cand['bati_ratio']) * 100:.0f} %)"
                + (f" · gain estimé {cand['gain_estime_eur']:,} € (Estimé)" if cand["gain_estime_eur"] else "")
            ).replace(",", " ")
            avert = ("POTENTIEL GÉOMÉTRIQUE — constructibilité réglementaire non vérifiée ; "
                     "accès restant du lot bâti : à juger À L'ŒIL.")
            handles = [
                plt.Line2D([], [], color=C["parcelle"], lw=2.4, label="parcelle"),
                plt.Rectangle((0, 0), 1, 1, facecolor=C["bati"], alpha=0.85, label="emprise bâtie"),
                plt.Rectangle((0, 0), 1, 1, facecolor=C["lot"], alpha=0.28, hatch="//",
                              edgecolor=C["lot"], label="lot détachable proposé"),
                plt.Line2D([], [], color=C["acces"], lw=5, label="façade voirie du lot"),
                plt.Line2D([], [], color=C["mic"], lw=1.4, ls=":", label="cercle inscrit"),
                plt.Line2D([], [], color=C["voirie"], lw=2.2, label="voirie"),
            ]
            ax.legend(handles=handles, loc="upper right", fontsize=7, framealpha=0.9)
            fig.text(0.02, 0.045, legende, fontsize=8.5, color="#222")
            fig.text(0.02, 0.012, avert, fontsize=7, color="#8a3324")
            fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.09)
            path = os.path.join(OUT, f"carte_{i:02d}.png")
            fig.savefig(path); plt.close(fig)
            print(f"✓ carte_{i:02d}.png  {cand['idu']}  clarté={cand['clarte']} "
                  f"lot={cand['residuel_m2']} m² façade={cand['residuel_facade_m']} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
