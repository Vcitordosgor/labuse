#!/usr/bin/env python3
"""GABARIT-2 · Lot A · mesure de la classification des limites v2 (lecture seule).

Rejoue `labuse.gabarit.limites.classify_parcel_limits` sur 70 parcelles (les 31 d'A0 +
39 nouvelles dont centre-ville dense et drapeau/enclave), rend une capture ortho IGN par
parcelle (arêtes colorées : voie / séparative latérale / fond / non classée) et produit une
synthèse CSV. Seuil pour servir : 0 faux sur 70 ; « non classée » compte comme juste si le
motif est le bon.

Usage : PYTHONPATH=src <venv>/python scripts/gabarit_a0_2_mesure.py [--sample | <idu> ...]
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit._geom import to_wgs
from labuse.gabarit.limites import classify_parcel_limits

CAPT = os.path.join(os.path.dirname(__file__), "..", "docs", "GABARIT", "captures", "gabarit-2")
WMS = ("https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
       "&LAYERS=HR.ORTHOIMAGERY.ORTHOPHOTOS&STYLES=&CRS=EPSG:4326"
       "&BBOX={miny},{minx},{maxy},{maxx}&WIDTH={w}&HEIGHT={h}&FORMAT=image/png")
COLOR = {"voie": "#E8491D", "side": "#1D74E8", "rear": "#8A2BE2", "nonclass": "#9AA0A6"}
LABELFR = {"voie": "Voie", "side": "Séparative latérale", "rear": "Séparative fond",
           "nonclass": "Non classée"}
A0_CSV = os.path.join(os.path.dirname(__file__), "..", "docs", "GABARIT", "captures", "a0-limites-synthese.csv")


def a0_idus() -> list[str]:
    if not os.path.exists(A0_CSV):
        return ["97410000AN0347"]
    with open(A0_CSV) as f:
        return [r["idu"] for r in csv.DictReader(f)]


def new_idus(s) -> list[str]:
    out: list[str] = []
    out += [r[0] for r in s.execute(text("""
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE p.commune IN ('Saint-Denis','Le Port') AND z.zone_fam='U'
          AND ST_Area(p.geom_2975) BETWEEN 120 AND 700
        ORDER BY md5(p.idu||'cv') LIMIT 20"""))]
    out += [r[0] for r in s.execute(text("""
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE z.zone_fam='U' AND ST_Area(p.geom_2975) BETWEEN 150 AND 1500
          AND (SELECT COALESCE(ST_Length(ST_Intersection(ST_Boundary(p.geom_2975),
                 ST_Buffer(ST_Union(o.geom_2975),0.5))),0)
               FROM parcels o WHERE o.id<>p.id AND ST_DWithin(o.geom_2975,p.geom_2975,0.5))
              / NULLIF(ST_Perimeter(p.geom_2975),0) > 0.985
        ORDER BY md5(p.idu||'dr') LIMIT 10"""))]
    out += [r[0] for r in s.execute(text("""
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE p.commune IN ('Le Tampon','Saint-Louis','Saint-André') AND z.zone_fam='U'
          AND ST_Area(p.geom_2975) BETWEEN 300 AND 2000
        ORDER BY md5(p.idu||'pu') LIMIT 9"""))]
    return out


def render(s, idu, res):
    os.makedirs(CAPT, exist_ok=True)
    row = s.execute(text("SELECT ST_XMin(e),ST_YMin(e),ST_XMax(e),ST_YMax(e),commune FROM "
                         "(SELECT ST_Extent(geom) e, max(commune) commune FROM parcels WHERE idu=:i) q"),
                    {"i": idu}).first()
    minx, miny, maxx, maxy, commune = row
    mx = max((maxx - minx) * 0.9, 3.0e-4)
    my = max((maxy - miny) * 0.9, 3.0e-4)
    minx, maxx, miny, maxy = minx - mx, maxx + mx, miny - my, maxy + my
    h = 680
    w = int(h * (maxx - minx) / (maxy - miny))
    url = WMS.format(miny=miny, minx=minx, maxy=maxy, maxx=maxx, w=w, h=h)
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=110)
    try:
        raw = subprocess.run(["curl", "-sf", "--max-time", "30", url], capture_output=True, timeout=40).stdout
        ax.imshow(imread(io.BytesIO(raw), format="png"), extent=[minx, maxx, miny, maxy], aspect="auto", zorder=0)
    except Exception as e:  # pragma: no cover
        print(f"  ortho KO {idu}: {e}")
    for e in res.edges:
        xs, ys = to_wgs(e.geom).xy
        ax.plot(xs, ys, color=COLOR[e.type], lw=3.4, solid_capstyle="round", zorder=3)
    c = Counter(e.type for e in res.edges)
    tag = "BLOQUE" if res.blocking else "servi"
    ax.set_title(f"{idu} · {commune} — voie {c['voie']}/lat {c['side']}/fond {c['rear']}/"
                 f"nc {c['nonclass']} — {tag}", fontsize=8)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(handles=[plt.Line2D([], [], color=COLOR[k], lw=3, label=LABELFR[k]) for k in COLOR],
              fontsize=7, loc="lower right", framealpha=0.85)
    fig.savefig(os.path.join(CAPT, f"lim-{idu}.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    args = sys.argv[1:]
    os.makedirs(CAPT, exist_ok=True)
    with session_scope() as s:
        if args and args != ["--sample"]:
            idus = args
        else:
            seen, idus = set(), []
            for i in a0_idus() + new_idus(s):
                if i not in seen:
                    seen.add(i)
                    idus.append(i)
        rows = []
        for idu in idus:
            pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            if not pid:
                print(f"{idu}: introuvable")
                continue
            res = classify_parcel_limits(s, pid)
            if res is None:
                print(f"{idu}: pas de géométrie")
                continue
            render(s, idu, res)
            c = Counter(e.type for e in res.edges)
            rows.append({"idu": idu, "voie": c["voie"], "side": c["side"], "rear": c["rear"],
                         "nonclass": c["nonclass"], "has_voie": res.has_voie,
                         "blocking": (res.blocking or "")[:90]})
            print(f"{idu}: voie={c['voie']} lat={c['side']} fond={c['rear']} nc={c['nonclass']} "
                  f"-> {'BLOQUE: '+res.blocking[:40] if res.blocking else 'servi'}")
        with open(os.path.join(CAPT, "lim-synthese.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["idu", "voie", "side", "rear", "nonclass", "has_voie", "blocking"])
            wr.writeheader()
            wr.writerows(rows)
        servi = sum(1 for r in rows if not r["blocking"])
        print(f"\n{len(rows)} parcelles · {servi} servies · {len(rows)-servi} bloquées · "
              f"CSV {os.path.join(CAPT, 'lim-synthese.csv')}")


if __name__ == "__main__":
    main()
