#!/usr/bin/env python3
"""GABARIT-6 · Lot A · mesure de couverture (lecture seule).

Rejoue le BUILDER complet sur la MÊME cohorte de 170 parcelles que GABARIT-3/4/5 → écrit un CSV
par-idu (servie 0/1, cause de blocage, arêtes résiduelles rattachées) + un audit « 0 faux » (arêtes
'road' servies sans justification géométrique). Comparer AVANT (git stash) vs APRÈS = régression /
déblocage / faux. Ne modifie rien.

Usage : PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib <venv>/python \
        scripts/gabarit_a0_6_mesure.py <sortie.csv>
"""
from __future__ import annotations

import csv
import os
import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit.builder import build_gabarit_input
from labuse.gabarit.limites import PRIVATE_ROAD_TOUCH_M, is_private_road_parcel, obb_dims

HERE = os.path.dirname(__file__)
COHORTE = os.path.join(HERE, "..", "docs", "GABARIT", "captures", "gabarit-3", "couverture-synthese.csv")


def _priv(r) -> bool:
    d = obb_dims(r[0], r[1])
    return d is not None and is_private_road_parcel(
        has_bati=bool(r[2]), elongation=d[0] / d[1], width_m=d[1],
        touches_road=bool(r[3]), axis_len_inside_m=float(r[4] or 0))


def _faux(s, pid, b) -> list[str]:
    """Arêtes 'road' servies sans justification géométrique (BD TOPO : route à portée ou parcelle-
    voirie ; voie privée : parcelle de voie privée détectée). 0 attendu."""
    from shapely.geometry import shape
    faux = []
    for sb in b.input.setbacks:
        if sb.type != "road":
            continue
        prov = sb.source.provider or ""
        wkt = shape(sb.geometry).wkt
        if "BD TOPO" in prov:
            near_road = s.execute(text(
                "SELECT EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' "
                "AND v.subtype NOT IN ('Sentier','Escalier') AND ST_DWithin(v.geom_2975, "
                "ST_Transform(ST_GeomFromText(:w,4326),2975), COALESCE((v.attrs->>'largeur')::float,4)/2+4))"),
                {"w": wkt}).scalar()
            road_parcel = s.execute(text(
                "SELECT EXISTS(SELECT 1 FROM parcels o WHERE o.id<>:p AND ST_DWithin(o.geom_2975, "
                "ST_Transform(ST_GeomFromText(:w,4326),2975),0.6) AND EXISTS(SELECT 1 FROM spatial_layers v "
                "WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier') AND ST_Intersects(v.geom_2975,o.geom_2975)) "
                "AND NOT EXISTS(SELECT 1 FROM spatial_layers bt WHERE bt.kind='batiment' AND ST_Intersects(bt.geom_2975,o.geom_2975)))"),
                {"p": pid, "w": wkt}).scalar()
            if not near_road and not road_parcel:
                faux.append(f"voie BD TOPO sans route ni parcelle-voirie : {sb.id}")
        elif "voie privée" in prov:
            cand = s.execute(text(
                "SELECT ST_Perimeter(ST_OrientedEnvelope(o.geom_2975)), ST_Area(ST_OrientedEnvelope(o.geom_2975)), "
                "EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,o.geom_2975)), "
                "EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier') "
                "  AND ST_DWithin(v.geom_2975,o.geom_2975,:t)), "
                "COALESCE((SELECT SUM(ST_Length(ST_Intersection(v.geom_2975,o.geom_2975))) FROM spatial_layers v "
                "  WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier') AND ST_Intersects(v.geom_2975,o.geom_2975)),0) "
                "FROM parcels o WHERE o.id<>:p AND ST_DWithin(o.geom_2975,ST_Transform(ST_GeomFromText(:w,4326),2975),0.6)"),
                {"p": pid, "w": wkt, "t": PRIVATE_ROAD_TOUCH_M}).fetchall()
            if not any(_priv(r) for r in cand):
                faux.append(f"voie privée servie sans parcelle de voie privée détectée : {sb.id}")
    return faux


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "gabarit6-mesure.csv"
    with session_scope() as s:
        cohorte = list(csv.DictReader(open(COHORTE)))
        allid = [r["idu"] for r in cohorte]
        rows, served, faux_tot = [], 0, []
        for idu in allid:
            b = build_gabarit_input(s, idu)
            if b is None:
                rows.append({"idu": idu, "servie": "", "cause": "build=None", "rattachees": ""})
                continue
            pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            cl = (b.raccordement or {}).get("classification", {}) if b.raccordement else {}
            ratt = cl.get("aretes_residuelles_rattachees", "")
            if b.blocking:
                rows.append({"idu": idu, "servie": 0, "cause": b.blocking[0][:80], "rattachees": ratt})
            else:
                served += 1
                fx = _faux(s, pid, b)
                faux_tot += [(idu, f) for f in fx]
                rows.append({"idu": idu, "servie": 1, "cause": "", "rattachees": ratt})
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["idu", "servie", "cause", "rattachees"])
            w.writeheader()
            w.writerows(rows)
        n = len(rows)
        print(f"=== {out} ===")
        print(f"servies = {served}/{n} ({100*served/n:.0f} %)")
        print(f"FAUX = {len(faux_tot)}")
        for idu, fx in faux_tot:
            print("   FAUX:", idu, fx)
        tot_ratt = sum(int(r["rattachees"]) for r in rows if str(r["rattachees"]).isdigit())
        n_parc_ratt = sum(1 for r in rows if str(r["rattachees"]).isdigit() and int(r["rattachees"]) > 0)
        print(f"arêtes résiduelles rattachées = {tot_ratt} sur {n_parc_ratt} parcelle(s)")


if __name__ == "__main__":
    main()
