#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OUTILS-P0-2 (P2) — mesure NO-LEAK de l'écart d'estimation d'un TERRAIN NU par rapport à la GAMME de
surface de ses ventes de référence. Objectif : fixer, à partir des transactions, le seuil « hors gamme »
au-delà duquel un total `surface × €/m² médian` n'est plus fiable (le témoin 97409000AK0804 > 21 M€).

Rejoue la chaîne servie (rayon adaptatif 500→1000→1500 m puis repli commune, trim 5 %, bornes), mais
capture AUSSI la surface des ventes de référence retenues → mesure l'écart |estimé − réel| par :
  · tranche de surface ABSOLUE du sujet ;
  · ratio surface_sujet / p90(surfaces de référence) — « combien de fois au-dessus de la gamme ».

Lancer :
  LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \\
    <venv>/python docs/audit-2026-11/outils-p0-2/mesure_terrain_gamme.py   # (PYTHONPATH=src)
"""
from __future__ import annotations

import os
import statistics

import numpy as np
import sqlalchemy as sa

from labuse.pige import banc_estimer as B

BORNES = B.BORNES_TERR          # (50, 20000) €/m²
RAYONS = B.RAYONS               # 500/1000/1500
MIN_N = B.MIN_N                 # 8
GARDE = B.GARDE_TERR            # (50, 4000) €/m² réel — garde du prix observé


def _trim(xs):
    xs = sorted(xs)
    k = int(len(xs) * 0.025)
    return xs[k:len(xs) - k] if k else xs


def charger_terr_surfaces(engine):
    """Pool TERRAIN NU géo-DVF avec SURFACE par vente (le banc ne garde que le €/m²)."""
    with engine.connect() as c:
        rows = c.execute(sa.text("""
          WITH parc AS (
            SELECT DISTINCT dm.id_mutation, dm.id_parcelle, dm.valeur_fonciere AS vf,
                   dm.date_mutation::date AS d, left(dm.id_parcelle,5) AS insee,
                   max(COALESCE(dm.surface_terrain,0)) OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS terr_p,
                   ST_X(ST_Transform(pp.centroid,2975)) AS x, ST_Y(ST_Transform(pp.centroid,2975)) AS y
            FROM dvf_mutations_parcelle dm JOIN parcels pp ON pp.idu = dm.id_parcelle
            WHERE dm.nature_mutation IN ('Vente','Vente terrain à bâtir')
              AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain > 0
              AND dm.date_mutation IS NOT NULL),
          t AS (SELECT id_mutation, insee, min(d) AS d, sum(terr_p) AS surf, max(vf) AS vf,
                       avg(x) AS x, avg(y) AS y
                FROM parc GROUP BY id_mutation, insee)
          SELECT id_mutation AS mid, insee, d, surf, (vf / NULLIF(surf,0)) AS prix_m2, x, y
          FROM t WHERE vf / NULLIF(surf,0) BETWEEN :lo AND :hi
        """).bindparams(lo=BORNES[0], hi=BORNES[1])).mappings().all()
    idx = {}
    by = {}
    for r in rows:
        by.setdefault(r["insee"], []).append(r)
    for insee, lst in by.items():
        idx[insee] = {
            "mid": np.array([x["mid"] for x in lst]),
            "d": np.array([x["d"] for x in lst]),
            "prix": np.array([float(x["prix_m2"]) for x in lst]),
            "surf": np.array([float(x["surf"]) for x in lst]),
            "x": np.array([float(x["x"]) for x in lst]),
            "y": np.array([float(x["y"]) for x in lst]),
        }
    return idx


def reference(subj, p, d_vente, mid):
    """Reproduit eur_m2_terrain MAIS renvoie aussi les surfaces de référence retenues."""
    if p is None:
        return None
    avant = (p["d"] < d_vente) & (p["mid"] != mid) & (p["prix"] >= BORNES[0]) & (p["prix"] <= BORNES[1])
    if not avant.any():
        return None
    dx, dy = p["x"] - subj["x"], p["y"] - subj["y"]
    dist = np.sqrt(dx * dx + dy * dy)
    for r in RAYONS:
        m = avant & (dist <= r)
        prix = _trim([float(x) for x in p["prix"][m]])
        if len(prix) >= MIN_N:
            return statistics.median(prix), [float(x) for x in p["surf"][m]]
    prix = _trim([float(x) for x in p["prix"][avant]])
    if prix:
        return statistics.median(prix), [float(x) for x in p["surf"][avant]]
    return None


def main():
    url = os.environ["LABUSE_DATABASE_URL"]
    engine = sa.create_engine(url)
    D = B.charger(engine)
    IDXT = charger_terr_surfaces(engine)

    # mêmes sujets terrain que le banc (toutes les ventes terrain jugeables, SANS cap de 200)
    terrains = []
    for row in D["univers"]:
        p = D["parc"].get(row["idu"])
        if p is None:
            continue
        bati = float(row["bati_m2"] or 0)
        terr = float(row["terrain_m2"] or 0)
        val = float(row["valeur"])
        if (not row["am"]) and (not row["aa"]) and bati == 0 and terr > 0:
            reel = val / terr
            if GARDE[0] <= reel <= GARDE[1]:
                terrains.append({**row, "p": p, "reel_total": val, "terr": terr})

    # chaque sujet : écart + position vis-à-vis de la gamme des ventes de référence
    enr = []
    for k in terrains:
        subj = {"x": k["p"]["x"], "y": k["p"]["y"]}
        ref = reference(subj, IDXT.get(k["insee"]), k["d"], k["mid"])
        surf_parc = float(k["p"]["surf_parc"] or 0)
        if not ref or surf_parc <= 0:
            continue
        med, surfs = ref
        if not surfs:
            continue
        err = abs(surf_parc * med / k["reel_total"] - 1.0) * 100
        p90 = float(np.percentile(surfs, 90))
        p75 = float(np.percentile(surfs, 75))
        smax = max(surfs)
        enr.append({"surf": surf_parc, "err": err,
                    "ratio_p90": surf_parc / p90 if p90 else None,
                    "ratio_p75": surf_parc / p75 if p75 else None,
                    "ratio_max": surf_parc / smax if smax else None,
                    "ref_med_surf": statistics.median(surfs), "n_ref": len(surfs)})

    def med_err(sel):
        es = [e["err"] for e in sel]
        return (round(statistics.median(es), 1) if es else None, len(es))

    print(f"\n== n sujets terrain mesurés : {len(enr)} ==\n")

    print("— Écart médian par TRANCHE DE SURFACE ABSOLUE du sujet —")
    tranches = [(0, 300), (300, 500), (500, 800), (800, 1200), (1200, 2000),
                (2000, 3500), (3500, 6000), (6000, 12000), (12000, 10**9)]
    for lo, hi in tranches:
        sel = [e for e in enr if lo <= e["surf"] < hi]
        m, n = med_err(sel)
        lbl = f"{lo}-{hi} m²" if hi < 10**9 else f"> {lo} m²"
        bar = "#" * int((m or 0) / 5)
        print(f"  {lbl:>16} : écart médian {str(m):>6} %  (n={n:>4})  {bar}")

    print("\n— Écart médian par RATIO surface_sujet / p90(surfaces de référence) —")
    for lo, hi, lbl in [(0, 0.5, "≤ 0,5"), (0.5, 1.0, "0,5-1,0"), (1.0, 1.5, "1,0-1,5"),
                        (1.5, 2.0, "1,5-2,0"), (2.0, 3.0, "2,0-3,0"), (3.0, 5.0, "3,0-5,0"),
                        (5.0, 10.0, "5,0-10"), (10.0, 10**9, "> 10")]:
        sel = [e for e in enr if e["ratio_p90"] is not None and lo <= e["ratio_p90"] < hi]
        m, n = med_err(sel)
        bar = "#" * int((m or 0) / 5)
        print(f"  ratio p90 {lbl:>8} : écart médian {str(m):>6} %  (n={n:>4})  {bar}")

    print("\n— Part des sujets AU-DESSUS de divers seuils de ratio p90 —")
    for seuil in (1.0, 1.5, 2.0, 2.5, 3.0):
        au = [e for e in enr if e["ratio_p90"] is not None and e["ratio_p90"] > seuil]
        dessous = [e for e in enr if e["ratio_p90"] is not None and e["ratio_p90"] <= seuil]
        ma, _ = med_err(au)
        md, _ = med_err(dessous)
        print(f"  ratio p90 > {seuil:>3} : {len(au):>4} sujets hors ({100*len(au)/max(1,len(enr)):.1f} %), "
              f"écart médian hors={ma} % / dans la gamme={md} %")


if __name__ == "__main__":
    main()
