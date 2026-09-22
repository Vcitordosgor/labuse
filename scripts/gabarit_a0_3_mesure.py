#!/usr/bin/env python3
"""GABARIT-3 · Lot E · mesure finale de couverture (lecture seule).

Mesure via le BUILDER complet (build_gabarit_input = PLU + limites + citations + PPR) sur
100 parcelles U tirées au sort (24 communes, ≥ 30 centre-ville, ≥ 10 enclaves, ≥ 10 bord de
ravine/littoral) + les 70 d'A0-2 rejouées. Tableau servie / bloquée par cause, taux global,
audit 0 faux (voie/séparative) sur les servies.

Usage : PYTHONPATH=src <venv>/python scripts/gabarit_a0_3_mesure.py
"""
from __future__ import annotations

import csv
import os
from collections import Counter

from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit.builder import build_gabarit_input

CAPT = os.path.join(os.path.dirname(__file__), "..", "docs", "GABARIT", "captures", "gabarit-3")
A0_2 = os.path.join(os.path.dirname(__file__), "..", "docs", "GABARIT", "captures", "gabarit-2", "lim-synthese.csv")


def _bucket(msg: str) -> str:
    m = msg.lower()
    if "ces" in m or ("emprise" in m and "non régle" in m):
        return "PLU : CES (emprise) non validée"
    if "hauteur" in m:
        return "PLU : hauteur non validée"
    if "non calibr" in m or "hors calibrage" in m or "indéter" in m:
        return "PLU : zone non calibrée"
    if "propose" in m:
        return "PLU : règle propose"
    if "cheval" in m:
        return "multi-zone (règle non unique)"
    if "non qualifiées" in m:
        return "limite non qualifiée (emprise non couverte)"
    if "voie privée" in m or "façade" in m:
        return "enclave / voie privée"
    if "recul" in m:
        return "recul non validé"
    return "autre : " + msg[:40]


def _sample(s) -> list[str]:
    idus: list[str] = []
    q = lambda sql: [r[0] for r in s.execute(text(sql))]  # noqa: E731
    idus += q("""SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
                 WHERE z.zone_fam='U' ORDER BY md5(p.idu||'g3rand') LIMIT 45""")
    idus += q("""SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
                 WHERE z.zone_fam='U' AND p.commune IN ('Saint-Denis','Le Port','Saint-Pierre')
                   AND ST_Area(p.geom_2975) BETWEEN 120 AND 600
                 ORDER BY md5(p.idu||'g3cv') LIMIT 30""")   # centre-ville dense
    idus += q("""SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
                 WHERE z.zone_fam='U' AND ST_Area(p.geom_2975) BETWEEN 150 AND 1500
                   AND (SELECT COALESCE(ST_Length(ST_Intersection(ST_Boundary(p.geom_2975),
                          ST_Buffer(ST_Union(o.geom_2975),0.5))),0)
                        FROM parcels o WHERE o.id<>p.id AND ST_DWithin(o.geom_2975,p.geom_2975,0.5))
                       / NULLIF(ST_Perimeter(p.geom_2975),0) > 0.985
                 ORDER BY md5(p.idu||'g3enc') LIMIT 12""")   # enclaves
    idus += q("""SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
                 WHERE z.zone_fam='U' AND EXISTS(SELECT 1 FROM spatial_layers g
                   WHERE g.kind IN ('ravine','trait_de_cote') AND ST_DWithin(g.geom_2975,p.geom_2975,8))
                 ORDER BY md5(p.idu||'g3rav') LIMIT 13""")   # ravine / littoral
    # dédup, cap 100
    seen, out = set(), []
    for i in idus:
        if i not in seen:
            seen.add(i)
            out.append(i)
        if len(out) >= 100:
            break
    return out


def _faux(s, pid, b) -> int:
    """Faux servis : une arête 'road' de source BD TOPO sans route carrossable à portée
    (largeur/2 + 4 m, largeur-aware) NI parcelle-voirie collée. (Une voie « emprise publique »
    est légitime sans route : elle vient de la citation PLU.) 0 attendu."""
    from shapely.geometry import shape
    n = 0
    for sb in b.input.setbacks:
        if sb.type != "road" or "BD TOPO" not in (sb.source.provider or ""):
            continue
        wkt = shape(sb.geometry).wkt
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
            n += 1
    return n


def main():
    os.makedirs(CAPT, exist_ok=True)
    with session_scope() as s:
        a0_2 = [r["idu"] for r in csv.DictReader(open(A0_2))] if os.path.exists(A0_2) else []
        sample = _sample(s)
        seen, allid = set(), []
        for i in sample + a0_2:
            if i not in seen:
                seen.add(i)
                allid.append(i)
        rows = []
        served = faux = 0
        causes = Counter()
        for idu in allid:
            b = build_gabarit_input(s, idu)
            if b is None:
                continue
            if b.blocking:
                cause = _bucket(b.blocking[0])
                causes[cause] += 1
                rows.append({"idu": idu, "servie": 0, "cause": cause})
            else:
                served += 1
                pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
                faux += _faux(s, pid, b)
                rows.append({"idu": idu, "servie": 1, "cause": ""})
        n = len(rows)
        with open(os.path.join(CAPT, "couverture-synthese.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["idu", "servie", "cause"])
            w.writeheader()
            w.writerows(rows)
        print(f"n={n}  servies={served} ({100 * served / n:.0f}%)  bloquées={n - served}  FAUX servis={faux}")
        print("\nCauses de blocage :")
        for c, k in causes.most_common():
            print(f"  {k:3d}  {c}")
        # taux hors verrou PLU (ce que le périmètre limites/enclaves/emprises peut atteindre)
        plu = sum(v for c, v in causes.items() if c.startswith("PLU") or c.startswith("multi"))
        atteignables = n - plu
        print(f"\nVerrou PLU/multi-zone (hors périmètre GABARIT-3) : {plu}/{n}")
        print(f"Parcelles atteignant l'étape limites : {atteignables}  →  servies {served} "
              f"({100 * served / max(atteignables, 1):.0f}% des atteignables)")
        print(f"\nSEUIL ≥ 90 % servies : {'ATTEINT' if served / n >= 0.90 else 'NON ATTEINT'} · "
              f"0 faux : {'OUI' if faux == 0 else 'NON (' + str(faux) + ')'}")


if __name__ == "__main__":
    main()
