#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMATION-BANC-2 — PREUVE DE FIDÉLITÉ du réplica bâti du banc 2.

Le banc 2 ré-implémente `marche_service.comparateur_bien` point-in-time (coupe de date) au lieu de
l'appeler (il lirait la fenêtre pleine = du futur). Pour prouver que le réplica = la PRODUCTION à la
seule coupe de date près, on exécute le réplica SANS coupe (fenêtre pleine, ancre = max global DVF) et
on le compare à `comparateur_bien` appelée EN DIRECT, sur un échantillon de parcelles bâties jugées.

On attend : MÊME type de bien déduit (maison/appartement/bâti) ET médiane identique à quelques % près
(le bruit de bord vient de l'ancre de fenêtre : la prod ancre sur le max GLOBAL, le réplica reçoit ici
ce même max global via `anchor_force`, donc l'écart résiduel est nul ou marginal).

Lancer : PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/fidelite_v2.py
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import sqlalchemy as sa

import backtest_banc2 as B  # réplica + chargeurs

ICI = Path(__file__).resolve().parent
URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")


def main() -> None:
    from labuse.db import session_scope
    from labuse import marche_service as msvc

    univers, communes, parc, bati_rows, terr_rows = B.charger()
    idx_bati = B.index_bati(bati_rows, ma_only=False)   # banc 2 : tous locaux de vente (filtre z-MAD)

    # ancre = max global DVF (date_mutation à minuit), comme fenetre_dvf_sql de la prod
    eng = sa.create_engine(URL)
    with eng.connect() as c:
        amax = c.execute(sa.text(
            "SELECT max(date_mutation)::date FROM dvf_mutations "
            "WHERE date_mutation = date_trunc('day', date_mutation)")).scalar()
    print(f"ancre fenêtre pleine (max global DVF) : {amax}")

    # échantillon : parcelles bâties (ou non mesurées) jugées, avec géométrie et commune indexée
    ech = []
    seen = set()
    for row in univers:
        idu = row["idu"]
        p = parc.get(idu)
        if not p or idu in seen:
            continue
        nat = B.nature_parcelle(p)
        if nat == "nu" or p.get("commune") not in idx_bati:
            continue
        seen.add(idu)
        ech.append((idu, p))
        if len(ech) >= 80:
            break

    FUTUR = date(2100, 1, 1)
    NONE_MID = "__aucune__"
    ok_type = 0
    ok_med = 0
    n = 0
    ecarts = []
    details = []
    with session_scope() as db:
        for idu, p in ech:
            reel = msvc.comparateur_bien(db, idu)             # PRODUCTION (fenêtre pleine)
            if not reel:
                continue
            mine = B.estime_bien_v2(p, FUTUR, NONE_MID, idx_bati, force_type=None, anchor_force=amax)
            n += 1
            t_ok = (reel.get("type_bien") == mine.get("type_bien"))
            ok_type += int(t_ok)
            rm, mm = reel.get("median"), mine.get("median")
            if rm and mm:
                e = abs(mm - rm) / rm
                ecarts.append(e)
                if e <= 0.04:
                    ok_med += 1
            details.append((idu, reel.get("type_bien"), mine.get("type_bien"), rm, mm, reel.get("n"), mine.get("n")))

    print(f"\néchantillon comparé : {n} parcelles bâties")
    print(f"MÊME type de bien déduit   : {ok_type}/{n}")
    print(f"médiane à ±4 %             : {ok_med}/{len(ecarts)} (sur {len(ecarts)} avec médiane des deux côtés)")
    if ecarts:
        ecarts.sort()
        print(f"écart médian de médiane    : {100*ecarts[len(ecarts)//2]:.2f} %   max : {100*ecarts[-1]:.2f} %")
    print("\n  idu            type_prod  type_repl  med_prod  med_repl   n_prod n_repl")
    for idu, tp, tm, rm, mm, rn, mn in details[:25]:
        rm_s = f"{rm:>8}" if rm is not None else "    None"
        mm_s = f"{mm:>8.0f}" if mm is not None else "    None"
        flag = "" if tp == tm and (rm is None or mm is None or abs((mm or 0)-(rm or 0))/max(rm or 1, 1) <= 0.04) else "  <-- écart"
        print(f"  {idu}  {str(tp):<9}  {str(tm):<9}  {rm_s}  {mm_s}   {rn:>5} {mn:>5}{flag}")

    with open(ICI / "FIDELITE_V2.txt", "w") as f:
        f.write(f"ancre fenêtre pleine : {amax}\n")
        f.write(f"échantillon : {n} parcelles bâties jugées\n")
        f.write(f"même type de bien déduit : {ok_type}/{n}\n")
        f.write(f"médiane à ±4 % : {ok_med}/{len(ecarts)}\n")
        if ecarts:
            f.write(f"écart médian : {100*ecarts[len(ecarts)//2]:.2f} %  max : {100*ecarts[-1]:.2f} %\n")
        f.write("\nidu,type_prod,type_repl,med_prod,med_repl,n_prod,n_repl\n")
        for idu, tp, tm, rm, mm, rn, mn in details:
            f.write(f"{idu},{tp},{tm},{rm},{mm},{rn},{mn}\n")
    print(f"\nécrit : {ICI/'FIDELITE_V2.txt'}")


if __name__ == "__main__":
    main()
