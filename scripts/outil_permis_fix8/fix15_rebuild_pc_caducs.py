"""OUTIL-PERMIS-FIX-15 (item 3) — RECONSTRUCTION AUTORISÉE de `pc_caducs` dans labuse (CETTE TABLE SEULE).

Écriture autorisée nommément par l'utilisateur, table `pc_caducs` uniquement. Fait :
  1. empreinte AVANT (count + somme hashtext des colonnes métier) ;
  2. sauvegarde DATÉE `pc_caducs_bak_fix15__<ts>` (copie de l'état courant, même vide — trace d'audit) ;
  3. reconstruction par `build_pc_caducs` (source Sitadel ; le garde-fou FIX-15 est actif → ne publierait
     pas un résultat vide) ;
  4. empreinte APRÈS (4 440 attendues).

Usage :  PYTHONPATH=src LABUSE_DATABASE_URL=…/labuse python scripts/outil_permis_fix8/fix15_rebuild_pc_caducs.py
"""
from __future__ import annotations

import datetime as dt
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.ingestion import pc_caducs

URL = os.environ["LABUSE_DATABASE_URL"]
assert URL.rsplit("/", 1)[-1] == "labuse", f"refus : cible attendue 'labuse', reçu {URL.rsplit('/',1)[-1]}"
eng = create_engine(URL)


def empreinte(c) -> dict:
    n = c.execute(text("SELECT count(*) FROM pc_caducs")).scalar()
    h = c.execute(text(
        "SELECT coalesce(sum(hashtext(idu || ':' || pc_annee || ':' || caduc_depuis || ':' || "
        "n_pc_octroyes || ':' || libelle_court)::bigint), 0) FROM pc_caducs")).scalar()
    return {"count": n, "hash": int(h)}


with Session(eng) as s:
    avant = empreinte(s)
    print("EMPREINTE AVANT :", avant)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"pc_caducs_bak_fix15__{ts}"
    s.execute(text(f'CREATE TABLE "{bak}" AS SELECT * FROM pc_caducs'))
    s.commit()
    nb_bak = s.execute(text(f'SELECT count(*) FROM "{bak}"')).scalar()
    print(f"SAUVEGARDE : {bak} ({nb_bak} ligne(s))")

    out = pc_caducs.build_pc_caducs(s, ref_date=dt.date.today(), commit=True)
    print("build_pc_caducs ->", out)

    apres = empreinte(s)
    print("EMPREINTE APRÈS :", apres)
    print("ATTENDU 4440 :", "OK" if apres["count"] == 4440 else f"⚠ {apres['count']}")
