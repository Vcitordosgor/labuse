#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMATION-BANC-1 — preuve de FIDÉLITÉ du réplica.

On démontre que les estimateurs RÉ-IMPLÉMENTÉS dans backtest_estimation_annonce.py, exécutés SANS
coupe temporelle (toute la fenêtre 2021-2025), reproduisent exactement la production :

  • TERRAIN : la médiane terrain recalculée par secteur == `dvf_secteur_medianes` servie (la table que
    l'outil lit via `_terrain_section`). → prouve que le réplica terrain est fidèle et que la SEULE
    différence dans le banc est le filtre de date (donc la non-fuite).
  • BÂTI : pour un échantillon de parcelles, l'estimation `estime_bati` (fenêtre pleine, année de
    référence 2026 comme en prod) == la vraie `faisabilite.bilan.sector_price` appelée en direct.

Si les deux concordent, alors le banc = production + coupe de date, rien d'autre.
"""
from __future__ import annotations
import os, sys
from datetime import date
import numpy as np
import sqlalchemy as sa

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import backtest_estimation_annonce as B

ENGINE = B.ENGINE


def fidelite_terrain():
    univers, communes, parc, bati_rows, terr_rows = B.charger()
    idx = B.index_terrain(terr_rows)
    with ENGINE.connect() as c:
        served = {r[0]: r[1] for r in c.execute(sa.text(
            "SELECT secteur, mediane_prix_m2 FROM dvf_secteur_medianes WHERE type_bien='terrain'"
        )).all()}
    # médiane pleine fenêtre (pas de coupe) par secteur, bornée [50;20000] comme en prod
    LOIN = date(2099, 1, 1)
    ok = diff = manquant = 0
    exemples = []
    for sect, srv in served.items():
        pool = idx.get(sect)
        if pool is None:
            manquant += 1
            continue
        band = pool["prix"][(pool["prix"] >= 50) & (pool["prix"] <= 20000)]
        if band.size == 0:
            manquant += 1
            continue
        mien = round(float(np.median(band)))
        if abs(mien - srv) <= 1:      # tolérance d'arrondi (prod round vs numpy)
            ok += 1
        else:
            diff += 1
            if len(exemples) < 10:
                exemples.append((sect, srv, mien, pool["prix"].size))
    tot = ok + diff
    print("== FIDÉLITÉ TERRAIN (médiane recalculée pleine fenêtre vs dvf_secteur_medianes servie) ==")
    print(f"   secteurs terrain servis : {len(served)}")
    print(f"   concordants (±1 €)      : {ok}/{tot} = {round(100*ok/tot,2) if tot else 0}%")
    print(f"   écarts > 1 €            : {diff}")
    print(f"   non comparables (0 comp band) : {manquant}")
    for e in exemples:
        print(f"      secteur {e[0]} servi={e[1]} recalculé={e[2]} n={e[3]}")
    return parc, bati_rows


def fidelite_bati(parc, bati_rows, n_ech=60):
    """Compare estime_bati (fenêtre pleine, ref 2026) à la vraie sector_price appelée en direct."""
    idx = B.index_bati(bati_rows)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
    from labuse.faisabilite.bilan import sector_price
    from labuse.faisabilite.engine import Hypotheses
    from sqlalchemy.orm import Session
    hyp = Hypotheses.charger()
    d_ref = date(2026, 6, 1)   # année de réf 2026 = annee_ref() de prod ; aucune vente 2026 → fenêtre pleine
    # échantillon de parcelles bâties réparties sur plusieurs communes
    idus = [i for i in sorted(parc) if parc[i].get("t") is not None and parc[i]["t"] >= 5]
    pas = max(1, len(idus) // n_ech)
    ech = idus[::pas][:n_ech]
    ok = diff = skip = 0
    exemples = []
    with ENGINE.connect() as c:
        sess = Session(bind=c)
        for idu in ech:
            pid = c.execute(sa.text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            if not pid:
                skip += 1; continue
            vrai = sector_price(sess, pid, hyp)
            mien = B.estime_bati(parc[idu], d_ref, None, idx)
            vm = vrai.get("median") if vrai else None
            mm = mien.get("median")
            if vm is None and mm is None:
                ok += 1; continue
            if vm is None or mm is None:
                diff += 1
                if len(exemples) < 12: exemples.append((idu, vm, mm, "l'un None"))
                continue
            if abs(round(vm) - round(mm)) <= 1:
                ok += 1
            else:
                diff += 1
                if len(exemples) < 12:
                    exemples.append((idu, round(vm), round(mm),
                                     f"prix prod={vrai.get('type_prix')} / mien={mien.get('type_prix')}"))
    tot = ok + diff
    print("\n== FIDÉLITÉ BÂTI (estime_bati fenêtre pleine vs sector_price en direct) ==")
    print(f"   parcelles testées : {tot} (+{skip} ignorées)")
    print(f"   médianes identiques (±1 €) : {ok}/{tot} = {round(100*ok/tot,2) if tot else 0}%")
    print(f"   écarts : {diff}")
    for e in exemples:
        print(f"      {e[0]} prod={e[1]} mien={e[2]} — {e[3]}")


if __name__ == "__main__":
    parc, bati_rows = fidelite_terrain()
    fidelite_bati(parc, bati_rows)
