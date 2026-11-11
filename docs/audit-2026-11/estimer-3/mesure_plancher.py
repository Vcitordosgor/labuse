#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-ECRAN-1 (défaut B) — mesure NO-LEAK : retenir la valeur du TERRAIN seul comme PLANCHER de
l'estimation d'un bien bâti améliore-t-il la précision, sur les ventes où la valeur du terrain dépasse
l'estimation bâtie ? (cas 97415000AW1367 : terrain 300 000 € > bien 188 000 €).

Réutilise la chaîne no-leak du banc permanent (`banc_estimer`) : pour chaque vente de MAISON, comparables
strictement antérieurs, même type ; estimation bâtie = surface SERVE-TIME × €/m² secteur ; valeur terrain
= contenance de la parcelle × €/m² terrain nu du secteur. On compte la part des ventes « terrain > bâti »
et on compare, SUR CES VENTES, l'écart |estimé − réel| avec et sans plancher = max(bâti, terrain).

    PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
      ~/Desktop/labuse/.venv/bin/python docs/audit-2026-11/estimer-3/mesure_plancher.py [N]
"""
from __future__ import annotations

import os
import random
import statistics
import sys

import sqlalchemy as sa

from labuse.pige import banc_estimer as B

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000


def med(xs):
    return round(statistics.median(xs), 1) if xs else None


def p20(xs):
    return round(100 * sum(1 for x in xs if x <= 20) / len(xs), 1) if xs else None


def main():
    url = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    engine = sa.create_engine(url, future=True)
    D = B.charger(engine)
    IDXB = B._index_bati(D["bati"])
    IDXT = B._index_terr(D["terr"])
    rng = random.Random(B.SEED)

    maisons = []
    for row in D["univers"]:
        p = D["parc"].get(row["idu"])
        if p is None:
            continue
        bati = float(row["bati_m2"] or 0)
        val = float(row["valeur"])
        if row["am"] and not row["aa"] and bati >= 20:
            reel = val / bati
            if B.GARDE_BATI[0] <= reel <= B.GARDE_BATI[1]:
                maisons.append({**row, "p": p, "reel_total": val})
    rng.shuffle(maisons)
    maisons = maisons[:N]

    tot = concern = 0
    eb_all, ef_all, eb_c, ef_c = [], [], [], []
    for k in maisons:
        p = k["p"]
        subj = {"x": p["x"], "y": p["y"]}
        med_b, _nb, _rb, _cfb = B.eur_m2_bati(subj, IDXB.get(p["commune"]), k["d"], k["mid"], "maison")
        sauto, _src = B.surface_auto(k["idu"], k["d"], k["mid"], D)
        med_t, _nt, _rt, _cft = B.eur_m2_terrain(subj, IDXT, k["insee"], k["d"], k["mid"])
        surf_parc = float(p.get("surf_parc") or 0)
        if not (med_b and sauto and med_t and surf_parc > 0):
            continue
        bati_est = sauto * med_b
        terr_val = surf_parc * med_t
        actual = k["reel_total"]
        tot += 1
        eb = abs(bati_est / actual - 1.0) * 100
        ef = abs(max(bati_est, terr_val) / actual - 1.0) * 100
        eb_all.append(eb)
        ef_all.append(ef)
        if terr_val > bati_est:
            concern += 1
            eb_c.append(eb)
            ef_c.append(ef)

    print(f"Maisons évaluées (no-leak) : {tot}")
    print(f"Part concernée « terrain > bâti » : {round(100 * concern / tot, 1)} %  ({concern}/{tot})")
    print("── SUR LES CAS CONCERNÉS (terrain > bâti) ──")
    print(f"  écart médian — bâti seul   : {med(eb_c)} %   (±20 % : {p20(eb_c)} %)")
    print(f"  écart médian — AVEC plancher: {med(ef_c)} %   (±20 % : {p20(ef_c)} %)")
    gain = (med(eb_c) - med(ef_c)) if (eb_c and ef_c) else None
    print(f"  → le plancher AMÉLIORE ? {'OUI' if (gain or 0) > 0 else 'NON'}  (gain d'écart médian {gain} pts)")
    print("── GLOBAL (toutes les maisons évaluées) ──")
    print(f"  écart médian — bâti seul    : {med(eb_all)} %   (±20 % : {p20(eb_all)} %)")
    print(f"  écart médian — AVEC plancher : {med(ef_all)} %   (±20 % : {p20(ef_all)} %)")


if __name__ == "__main__":
    main()
