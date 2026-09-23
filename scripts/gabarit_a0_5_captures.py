#!/usr/bin/env python3
"""GABARIT-5 · Lot A · captures ortho (lecture seule).

Une capture par parcelle : ortho IGN + contour + voisines + voirie BD TOPO + parcelles de voie
privée DÉTECTÉES (surbrillance) + arêtes classées par le BUILDER (voie / voie privée / séparative
/ non qualifiée). Le titre porte le verdict servi/bloqué. Sert à juger « 0 faux » à l'œil.

Usage : PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib <venv>/python \
        scripts/gabarit_a0_5_captures.py <idu> [<idu> ...]
"""
from __future__ import annotations

import io
import os
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit._geom import to_wgs
from labuse.gabarit.builder import build_gabarit_input, _voie_citation_flags
from labuse.gabarit.limites import PRIVATE_ROAD_TOUCH_M, classify_parcel_limits, is_private_road_parcel, obb_dims

CAPT = os.path.join(os.path.dirname(__file__), "..", "docs", "GABARIT", "captures", "gabarit-5")
WMS = ("https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
       "&LAYERS=HR.ORTHOIMAGERY.ORTHOPHOTOS&STYLES=&CRS=EPSG:4326"
       "&BBOX={miny},{minx},{maxy},{maxx}&WIDTH={w}&HEIGHT={h}&FORMAT=image/png")
COL = {"voie_bdtopo": "#E8491D", "voie_privee": "#FF00FF", "sep": "#1D74E8", "nonclass": "#9AA0A6"}


def _priv_geoms(s, pid):
    rows = s.execute(text(
        """SELECT ST_AsText(o.geom_2975), ST_Perimeter(ST_OrientedEnvelope(o.geom_2975)),
                  ST_Area(ST_OrientedEnvelope(o.geom_2975)),
                  EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,o.geom_2975)),
                  EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier') AND ST_DWithin(v.geom_2975,o.geom_2975,:t)),
                  COALESCE((SELECT SUM(ST_Length(ST_Intersection(v.geom_2975,o.geom_2975))) FROM spatial_layers v WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier') AND ST_Intersects(v.geom_2975,o.geom_2975)),0)
           FROM parcels o WHERE o.id<>:p AND ST_DWithin(o.geom_2975,(SELECT geom_2975 FROM parcels WHERE id=:p),0.5)"""),
        {"p": pid, "t": PRIVATE_ROAD_TOUCH_M}).fetchall()
    from shapely import wkt as W
    out = []
    for r in rows:
        d = obb_dims(r[1], r[2])
        if d and is_private_road_parcel(has_bati=bool(r[3]), elongation=d[0] / d[1], width_m=d[1],
                                        touches_road=bool(r[4]), axis_len_inside_m=float(r[5] or 0)):
            out.append(W.loads(r[0]))
    return out


def render(s, idu):
    row = s.execute(text("SELECT id, commune, ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) "
                         "FROM parcels WHERE idu=:i"), {"i": idu}).first()
    if not row:
        print("  inconnue", idu); return
    pid, commune, minx, miny, maxx, maxy = row
    mx = max((maxx - minx) * 1.1, 4.0e-4); my = max((maxy - miny) * 1.1, 4.0e-4)
    minx, maxx, miny, maxy = minx - mx, maxx + mx, miny - my, maxy + my
    aspect = (maxx - minx) / (maxy - miny); h = 700; w = int(h * aspect)
    url = WMS.format(miny=miny, minx=minx, maxy=maxy, maxx=maxx, w=w, h=h)
    try:
        raw = subprocess.run(["curl", "-sf", "--max-time", "30", url], capture_output=True, timeout=40).stdout
        img = imread(io.BytesIO(raw), format="png"); ok = True
    except Exception as e:
        img, ok = None, False; print("  ortho KO", idu, e)

    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=110)
    if ok:
        ax.imshow(img, extent=[minx, maxx, miny, maxy], aspect="auto", zorder=0)
    from shapely import wkt as W
    env = f"ST_MakeEnvelope({minx},{miny},{maxx},{maxy},4326)"
    for (wv,) in s.execute(text(f"SELECT ST_AsText(ST_Intersection(geom,{env})) FROM parcels "
                                f"WHERE idu<>:i AND geom && {env}"), {"i": idu}).fetchall():
        if not wv: continue
        gv = W.loads(wv)
        for poly in getattr(gv, "geoms", [gv]):
            if poly.geom_type == "Polygon":
                ax.plot(*poly.exterior.xy, color="white", lw=0.5, alpha=0.5, zorder=1)
    for (wr,) in s.execute(text(f"SELECT ST_AsText(ST_Intersection(geom,{env})) FROM spatial_layers "
                                f"WHERE kind='voirie' AND geom && {env}")).fetchall():
        if not wr: continue
        gr = W.loads(wr)
        for ln in getattr(gr, "geoms", [gr]):
            if ln.geom_type == "LineString":
                ax.plot(*ln.xy, color="yellow", lw=0.9, alpha=0.6, ls=":", zorder=1)
    # parcelles de voie privée détectées (surbrillance orange)
    for g in _priv_geoms(s, pid):
        gw = to_wgs(g)
        for poly in getattr(gw, "geoms", [gw]):
            if poly.geom_type == "Polygon":
                ax.fill(*poly.exterior.xy, color="#FF8C00", alpha=0.35, zorder=2)
                ax.plot(*poly.exterior.xy, color="#FF8C00", lw=1.2, zorder=2)
    # arêtes classées par le builder (citation prise en compte)
    ep, vp, _art, _cit = _voie_citation_flags(commune, s.execute(
        text("SELECT z.attrs->>'libelle' FROM spatial_layers z, parcels p WHERE p.id=:p "
             "AND z.kind='plu_gpu_zone' AND ST_Intersects(z.geom_2975,p.geom_2975) LIMIT 1"), {"p": pid}).scalar() or "")
    lim = classify_parcel_limits(s, pid, emprises_publiques=ep, voies_privees=vp)
    counts = {"voie_bdtopo": 0, "voie_privee": 0, "sep": 0, "nonclass": 0}
    if lim:
        for e in lim.edges:
            if e.type == "voie":
                k = "voie_privee" if e.source_kind == "voie_privee" else "voie_bdtopo"
            elif e.type in ("side", "rear"):
                k = "sep"
            else:
                k = "nonclass"
            counts[k] += 1
            gw = to_wgs(e.geom)
            ax.plot(*gw.xy, color=COL[k], lw=3.2, solid_capstyle="round", zorder=3)
    b = build_gabarit_input(s, idu)
    verdict = "SERVIE" if (b and not b.blocking) else ("BLOQUÉE : " + (b.blocking[0][:52] if b and b.blocking else "?"))
    ax.set_title(f"{idu} · {commune} — {verdict}\nvoie {counts['voie_bdtopo']} · voie privée "
                 f"{counts['voie_privee']} · sép {counts['sep']} · non qual. {counts['nonclass']}"
                 f"  (citation voies privées: {'oui' if vp else 'non'})", fontsize=8)
    ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy); ax.set_xticks([]); ax.set_yticks([])
    handles = [plt.Line2D([], [], color=COL[k], lw=3, label=lab) for k, lab in
               (("voie_bdtopo", "Voie BD TOPO"), ("voie_privee", "Voie privée (servie)"),
                ("sep", "Séparative"), ("nonclass", "Non qualifiée"))]
    handles.append(plt.Line2D([], [], color="#FF8C00", lw=3, label="Parcelle de voie privée détectée"))
    ax.legend(handles=handles, fontsize=6.5, loc="lower right", framealpha=0.85)
    os.makedirs(CAPT, exist_ok=True)
    out = os.path.join(CAPT, f"a5-voiepriv-{idu}.png")
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print("  capture", out, "|", verdict[:40])


def main():
    idus = sys.argv[1:]
    with session_scope() as s:
        for idu in idus:
            render(s, idu)


if __name__ == "__main__":
    main()
