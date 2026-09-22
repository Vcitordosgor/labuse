#!/usr/bin/env python3
"""GABARIT-5 · Lot A · mesure de couverture (lecture seule).

Rejoue le BUILDER complet sur le MÊME cohorte de 170 parcelles que GABARIT-3/4 (lue depuis
`captures/gabarit-3/couverture-synthese.csv`, reproductible) → couverture avant/après, causes.
Cible le lot voie privée (E2) : détection par les trois critères + citation PLU. Audit 0 faux,
étendu aux arêtes « voie privée » (une voie privée servie DOIT longer une parcelle de voie privée
réellement détectée). Échantillon lotissement : parcelles collées à une voie privée détectée.

Usage : PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib <venv>/python \
        scripts/gabarit_a0_5_mesure.py
"""
from __future__ import annotations

import csv
import os
from collections import Counter

from sqlalchemy import text

from labuse.db import session_scope
from labuse.gabarit.builder import build_gabarit_input
from labuse.gabarit.limites import (
    PRIVATE_ROAD_TOUCH_M,
    is_private_road_parcel,
    obb_dims,
)


def _priv(r) -> bool:
    """r = (obb_perim, obb_area, has_bati, touches_road, axis_len_inside)."""
    d = obb_dims(r[0], r[1])
    return d is not None and is_private_road_parcel(
        has_bati=bool(r[2]), elongation=d[0] / d[1], width_m=d[1],
        touches_road=bool(r[3]), axis_len_inside_m=float(r[4] or 0))

HERE = os.path.dirname(__file__)
CAPT = os.path.join(HERE, "..", "docs", "GABARIT", "captures", "gabarit-5")
COHORTE = os.path.join(HERE, "..", "docs", "GABARIT", "captures", "gabarit-3", "couverture-synthese.csv")


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
    if "cheval" in m or "2 zones" in m:
        return "multi-zone (règle non unique)"
    if "voie privée" in m:
        return "E2 : voie privée (citation absente)"
    if "non qualifiées" in m:
        return "limite non qualifiée (emprise non couverte)"
    if "façade" in m:
        return "enclave sans façade"
    if "recul" in m:
        return "recul non validé"
    if "non constructible" in m:
        return "multi-zone : tout non constructible"
    return "autre : " + msg[:40]


def _faux(s, pid, b) -> list[str]:
    """Arêtes 'road' servies sans justification géométrique. 0 attendu.
      - source BD TOPO : ni route carrossable à portée (largeur/2 + 4 m) ni parcelle-voirie collée.
      - source « voie privée » : aucune parcelle de voie privée réellement détectée le long de l'arête.
    (Une voie « emprise publique » vient de la citation PLU : légitime sans route — non auditée ici.)"""
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
            # une parcelle de voie privée doit longer l'arête (trois critères réévalués sur place)
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


def _lotissement_sample(s, n=20) -> list[str]:
    """Parcelles bâties collées à une voie privée DÉTECTÉE (les trois critères en SQL : sans bâti,
    allongée L/l ≥ 5 ET étroite largeur ≤ 6 m, raccordée au réseau BD TOPO à une extrémité sans le
    traverser). Contexte de lotissement. Étalé sur les communes (≤ 3 par commune, round-robin)."""
    rows = s.execute(text(
        """
        WITH priv AS (   -- parcelles de voie privée détectées (dims OBB → L, l ; critères GABARIT-5)
          SELECT o.id, o.geom_2975, (s.s + s.root)/2 AS L, (s.s - s.root)/2 AS w
          FROM parcels o
          CROSS JOIN LATERAL (
            SELECT ST_Perimeter(ST_OrientedEnvelope(o.geom_2975))/2 AS s,
                   sqrt(GREATEST(power(ST_Perimeter(ST_OrientedEnvelope(o.geom_2975))/2, 2)
                                 - 4*ST_Area(ST_OrientedEnvelope(o.geom_2975)), 0)) AS root
          ) s
          WHERE NOT EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,o.geom_2975))
            AND EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier')
                       AND ST_DWithin(v.geom_2975,o.geom_2975,:touch))
            AND COALESCE((SELECT SUM(ST_Length(ST_Intersection(v.geom_2975,o.geom_2975))) FROM spatial_layers v
                       WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier') AND ST_Intersects(v.geom_2975,o.geom_2975)),0) <= :axis
        ),
        cand AS (
          SELECT DISTINCT p.idu, LEFT(p.idu,6) AS insee
          FROM priv, parcels p
          WHERE priv.w > 0 AND priv.w <= :maxw AND priv.L >= :elong * priv.w   -- étroite ET allongée
            AND p.id <> priv.id AND ST_DWithin(p.geom_2975, priv.geom_2975, 0.5)
            AND EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975,p.geom_2975))
        )
        SELECT idu, insee FROM (
          SELECT idu, insee, ROW_NUMBER() OVER (PARTITION BY insee ORDER BY idu) AS rn FROM cand
        ) q WHERE rn <= 3 ORDER BY insee, idu
        """
    ), {"touch": PRIVATE_ROAD_TOUCH_M, "axis": 3.0, "maxw": 6.0, "elong": 5.0}).fetchall()
    from collections import OrderedDict
    par_commune: "OrderedDict[str, list]" = OrderedDict()
    for idu, insee in rows:
        par_commune.setdefault(insee, []).append(idu)
    out: list[str] = []
    while len(out) < n and any(par_commune.values()):
        for c in list(par_commune):
            if par_commune[c]:
                out.append(par_commune[c].pop(0))
                if len(out) >= n:
                    break
    return out


def main():
    os.makedirs(CAPT, exist_ok=True)
    with session_scope() as s:
        cohorte = list(csv.DictReader(open(COHORTE)))
        before = {r["idu"]: (int(r["servie"]), r["cause"]) for r in cohorte}
        allid = [r["idu"] for r in cohorte]

        rows, served, faux_tot = [], 0, []
        causes = Counter()
        e2_before = [i for i, (sv, c) in before.items() if "voie privée" in c or "enclave" in c]
        e2_now = {"bloc_E2": [], "servie_E1": [], "servie_voie_privee": [], "autre": []}
        for idu in allid:
            b = build_gabarit_input(s, idu)
            if b is None:
                continue
            pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            if b.blocking:
                cause = _bucket(b.blocking[0])
                causes[cause] += 1
                rows.append({"idu": idu, "servie": 0, "cause": cause})
            else:
                served += 1
                fx = _faux(s, pid, b)
                faux_tot += [(idu, f) for f in fx]
                rows.append({"idu": idu, "servie": 1, "cause": ""})
            if idu in e2_before:
                cl = (b.raccordement or {}).get("classification", {})
                if b.blocking and "voie privée" in b.blocking[0]:
                    e2_now["bloc_E2"].append(idu)
                elif not b.blocking and cl.get("voie_privee"):
                    e2_now["servie_voie_privee"].append(idu)
                elif not b.blocking and str((b.raccordement or {}).get("enclave", "")).startswith("E1"):
                    e2_now["servie_E1"].append(idu)
                else:
                    e2_now["autre"].append(idu)

        n = len(rows)
        with open(os.path.join(CAPT, "couverture-synthese.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["idu", "servie", "cause"])
            w.writeheader()
            w.writerows(rows)

        # échantillon lotissement (voies privées fréquentes)
        lot = _lotissement_sample(s, 20)
        lot_rows = []
        for idu in lot:
            b = build_gabarit_input(s, idu)
            pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            fx = _faux(s, pid, b) if b and not b.blocking else []
            faux_tot += [(idu, f) for f in fx]
            lot_rows.append({"idu": idu, "servie": 0 if (b and b.blocking) else 1,
                             "cause": _bucket(b.blocking[0]) if (b and b.blocking) else ""})
        with open(os.path.join(CAPT, "lotissement-synthese.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["idu", "servie", "cause"])
            w.writeheader()
            w.writerows(lot_rows)

        # rapport console
        srv_before = sum(sv for sv, _ in before.values())
        print("=== COHORTE 170 (identique GABARIT-3/4) ===")
        print(f"AVANT : servies={srv_before}/{n}  ({100*srv_before/n:.0f} %)")
        print(f"APRÈS : servies={served}/{n}  ({100*served/n:.0f} %)   Δ={served-srv_before:+d}")
        print(f"FAUX (arêtes road injustifiées) = {len(faux_tot)}")
        for idu, fx in faux_tot:
            print("   FAUX:", idu, fx)
        print("--- causes de blocage restantes ---")
        for c, k in causes.most_common():
            print(f"  {k:3}  {c}")
        print("--- lot E2 (12 ex-« enclave/voie privée » GABARIT-4) ---")
        for k, v in e2_now.items():
            print(f"  {k}: {len(v)}  {v}")
        print(f"--- échantillon lotissement : {len(lot_rows)} parcelles, "
              f"servies={sum(r['servie'] for r in lot_rows)}, "
              f"bloquées E2={sum(1 for r in lot_rows if 'voie privée' in r['cause'])}")


if __name__ == "__main__":
    main()
