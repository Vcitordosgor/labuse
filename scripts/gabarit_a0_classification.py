#!/usr/bin/env python3
"""GABARIT-1 · Lot A0 · point 5 — mesure de la classification des limites (lecture seule).

Méthode (mandat point 5), par segment du contour cadastral (métrique EPSG:2975) :
  - un voisin cadastré à <= SEP_TOL (0.5 m)              -> limite séparative
  - sinon un tronçon voirie BD TOPO à <= VOIE_TOL m      -> voie
  - sinon (ni voisin ni route)                           -> NON CLASSÉE = bloquant
  - side vs rear : rear = séparative ne partageant aucun sommet avec un segment voie.

La classification servie porte sa propre source :
  provider = "LABUSE — adjacence cadastre + BD TOPO voirie".
C'est une MESURE, pas une supposition.

Sortie : une capture par parcelle (segments colorés sur ortho IGN) dans
docs/GABARIT/captures/ + un CSV de synthèse (taux juste / faux / non classé).

Usage :
  PYTHONPATH=src <venv>/python scripts/gabarit_a0_classification.py <idu> [<idu> ...]
  PYTHONPATH=src <venv>/python scripts/gabarit_a0_classification.py --sample
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psycopg
from matplotlib.image import imread
from shapely import wkt as shapely_wkt
from shapely.geometry import LineString

SEP_TOL = 0.5     # m — voisin cadastré (mandat)
VOIE_TOL = 6.0    # m — tronçon voirie (axe BD TOPO ; ~demi-chaussée) ; calibré en A0
NN_SEARCH = 3.0   # m — rayon de recherche voisin (borne le calcul)
VOIE_SEARCH = 25.0

CAPT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "GABARIT", "captures")
WMS = ("https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
       "&LAYERS=HR.ORTHOIMAGERY.ORTHOPHOTOS&STYLES=&CRS=EPSG:4326"
       "&BBOX={miny},{minx},{maxy},{maxx}&WIDTH={w}&HEIGHT={h}&FORMAT=image/png")

COLOR = {"voie": "#E8491D", "side": "#1D74E8", "rear": "#8A2BE2", "nonclass": "#9AA0A6"}
LABELFR = {"voie": "Voie", "side": "Limite séparative (latérale)",
           "rear": "Limite séparative (fond)", "nonclass": "Non classée (bloquant)"}


def dburl() -> str:
    with open("/tmp/gab_psql_url.txt") as f:
        return f.read().strip()


def classify(cur, idu: str):
    """Retourne (segments, meta). segments = liste de dict {ord, wkt4326, label, nn_parcel, nn_voirie}."""
    cur.execute("SELECT idu, commune FROM parcels WHERE idu=%s", (idu,))
    row = cur.fetchone()
    if not row:
        return None, {"idu": idu, "error": "introuvable"}
    commune = row[1]
    cur.execute(
        """
        WITH p AS (SELECT geom_2975 g FROM parcels WHERE idu=%s),
        seg AS (
          SELECT (ST_DumpSegments(ST_Boundary(p.g))).path[1] ord,
                 (ST_DumpSegments(ST_Boundary(p.g))).geom s, p.g pg
          FROM p)
        SELECT seg.ord,
               ST_AsText(ST_Transform(seg.s,4326)) wkt4326,
               (SELECT min(ST_Distance(o.geom_2975, seg.s)) FROM parcels o
                 WHERE o.idu<>%s AND ST_DWithin(o.geom_2975, seg.s, %s)) nn_parcel,
               (SELECT min(ST_Distance(v.geom_2975, seg.s)) FROM spatial_layers v
                 WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, seg.s, %s)) nn_voirie
        FROM seg ORDER BY seg.ord
        """,
        (idu, idu, NN_SEARCH, VOIE_SEARCH),
    )
    segs = []
    for ordn, wkt4326, nn_p, nn_v in cur.fetchall():
        if nn_p is not None and nn_p <= SEP_TOL:
            label = "sep"
        elif nn_v is not None and nn_v <= VOIE_TOL:
            label = "voie"
        else:
            label = "nonclass"
        segs.append({"ord": ordn, "wkt": wkt4326, "label": label,
                     "nn_parcel": nn_p, "nn_voirie": nn_v})

    # side vs rear : rear = séparative ne partageant aucun sommet avec un segment voie
    voie_pts = set()
    for s in segs:
        if s["label"] == "voie":
            g = shapely_wkt.loads(s["wkt"])
            for c in g.coords:
                voie_pts.add((round(c[0], 7), round(c[1], 7)))
    for s in segs:
        if s["label"] == "sep":
            g = shapely_wkt.loads(s["wkt"])
            touches = any((round(c[0], 7), round(c[1], 7)) in voie_pts for c in g.coords)
            s["label"] = "side" if touches else "rear"

    counts = {k: 0 for k in ("voie", "side", "rear", "nonclass")}
    for s in segs:
        counts[s["label"]] += 1
    return segs, {"idu": idu, "commune": commune, "counts": counts}


def render(cur, idu: str, segs, meta):
    os.makedirs(CAPT_DIR, exist_ok=True)
    # bbox 4326 de la parcelle + voisines proches, avec marge
    cur.execute(
        """SELECT ST_XMin(e),ST_YMin(e),ST_XMax(e),ST_YMax(e) FROM
           (SELECT ST_Extent(geom) e FROM parcels WHERE idu=%s) q""", (idu,))
    minx, miny, maxx, maxy = cur.fetchone()
    # marge large + plancher ~30 m (0.00030°) pour voir routes/voisines et juger sur ortho
    mx = max((maxx - minx) * 0.9, 3.0e-4)
    my = max((maxy - miny) * 0.9, 3.0e-4)
    minx, maxx, miny, maxy = minx - mx, maxx + mx, miny - my, maxy + my
    # image carrée-ish : IGN attend l'aspect cohérent avec le bbox
    aspect = (maxx - minx) / (maxy - miny)
    h = 700
    w = int(h * aspect)
    url = WMS.format(miny=miny, minx=minx, maxy=maxy, maxx=maxx, w=w, h=h)
    # Fetch via curl (certifs système, TLS vérifié) — le venv n'a pas de bundle certifi.
    try:
        raw = subprocess.run(["curl", "-sf", "--max-time", "30", url],
                             capture_output=True, timeout=40).stdout
        img = imread(io.BytesIO(raw), format="png")
        ok = True
    except Exception as e:  # pragma: no cover
        img, ok = None, False
        print(f"  ortho KO {idu}: {e}")

    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=110)
    if ok:
        ax.imshow(img, extent=[minx, maxx, miny, maxy], aspect="auto", zorder=0)
    # voisines (contour fin) + voirie
    cur.execute(
        """SELECT ST_AsText(ST_Intersection(geom, ST_MakeEnvelope(%s,%s,%s,%s,4326)))
           FROM parcels WHERE idu<>%s AND geom && ST_MakeEnvelope(%s,%s,%s,%s,4326)""",
        (minx, miny, maxx, maxy, idu, minx, miny, maxx, maxy))
    for (wktv,) in cur.fetchall():
        try:
            gv = shapely_wkt.loads(wktv)
        except Exception:
            continue
        for poly in getattr(gv, "geoms", [gv]):
            if poly.geom_type == "Polygon":
                xs, ys = poly.exterior.xy
                ax.plot(xs, ys, color="white", lw=0.5, alpha=0.6, zorder=1)
    cur.execute(
        """SELECT ST_AsText(ST_Intersection(geom, ST_MakeEnvelope(%s,%s,%s,%s,4326)))
           FROM spatial_layers WHERE kind='voirie'
             AND geom && ST_MakeEnvelope(%s,%s,%s,%s,4326)""",
        (minx, miny, maxx, maxy, minx, miny, maxx, maxy))
    for (wktr,) in cur.fetchall():
        try:
            gr = shapely_wkt.loads(wktr)
        except Exception:
            continue
        for ln in getattr(gr, "geoms", [gr]):
            if ln.geom_type == "LineString":
                xs, ys = ln.xy
                ax.plot(xs, ys, color="yellow", lw=0.8, alpha=0.5, ls=":", zorder=1)
    # segments classés
    for s in segs:
        g = shapely_wkt.loads(s["wkt"])
        xs, ys = g.xy
        ax.plot(xs, ys, color=COLOR[s["label"]], lw=3.2, solid_capstyle="round", zorder=3)
    c = meta["counts"]
    ax.set_title(f"{idu} · {meta['commune']} — voie {c['voie']} / lat {c['side']} / "
                 f"fond {c['rear']} / non classée {c['nonclass']}", fontsize=9)
    ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy)
    ax.set_xticks([]); ax.set_yticks([])
    handles = [plt.Line2D([], [], color=COLOR[k], lw=3, label=LABELFR[k])
               for k in ("voie", "side", "rear", "nonclass")]
    ax.legend(handles=handles, fontsize=7, loc="lower right", framealpha=0.8)
    out = os.path.join(CAPT_DIR, f"a0-limites-{idu}.png")
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


SAMPLE_COMMUNES = ["Saint-Denis", "Saint-Pierre", "Saint-Paul"]


def sample_idus(cur, per=10):
    idus = []
    for com in SAMPLE_COMMUNES:
        cur.execute(
            """SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
               WHERE p.commune=%s AND z.zone_fam='U'
                 AND ST_Area(p.geom_2975) BETWEEN 200 AND 3000
                 AND ST_NPoints(p.geom_2975) BETWEEN 5 AND 40
               ORDER BY md5(p.idu) LIMIT %s""", (com, per))
        idus += [r[0] for r in cur.fetchall()]
    return idus


def main():
    args = sys.argv[1:]
    with psycopg.connect(dburl().replace("postgresql+psycopg", "postgresql")) as conn:
        cur = conn.cursor()
        if args == ["--sample"]:
            idus = sample_idus(cur) + ["97410000AN0347"]  # + parcelle nommée du mandat (zone N)
        else:
            idus = args or ["97410000AN0347"]
        rows = []
        for idu in idus:
            segs, meta = classify(cur, idu)
            if segs is None:
                print(f"{idu}: {meta.get('error')}"); continue
            out = render(cur, idu, segs, meta)
            c = meta["counts"]
            rows.append({"idu": idu, "commune": meta["commune"], **c,
                         "total": sum(c.values()),
                         "non_classee_pct": round(100 * c["nonclass"] / max(1, sum(c.values())), 1)})
            print(f"{idu} {meta['commune']}: voie={c['voie']} side={c['side']} "
                  f"rear={c['rear']} nonclass={c['nonclass']} -> {out}")
        csv_path = os.path.join(CAPT_DIR, "a0-limites-synthese.csv")
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["idu", "commune", "voie", "side", "rear",
                                              "nonclass", "total", "non_classee_pct"])
            w.writeheader(); w.writerows(rows)
        print(f"\nCSV: {csv_path}  ({len(rows)} parcelles)")


if __name__ == "__main__":
    main()
