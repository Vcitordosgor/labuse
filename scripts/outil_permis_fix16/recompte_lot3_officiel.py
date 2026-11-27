#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-16 LOT 3 — recompte INDÉPENDANT des parcelles caduc depuis les fichiers OFFICIELS.

Rejoue la règle pc_caducs de LABUSE (PC octroyé {2,5,6} jamais réalisé {daact|5|6}, échéance de validité
dépassée par DATE) directement sur les 4 fichiers SDES/Dido d'octobre 2026 (dep 974), en explosant TOUTES
les colonnes cadastrales de CHAQUE ligne (un permis sur plusieurs parcelles compte toutes ses parcelles),
restreint à l'univers `parcels`. Compare au signal LOCAL (table pc_caducs) et explique l'écart.

Les CSV sont lus depuis /tmp/sdes_{logements,locaux,pa,pd}.csv (téléchargés avec &millesime=2026-10).
Lecture seule. Usage : PYTHONPATH=src LABUSE_DATABASE_URL=… python …/recompte_lot3_officiel.py [dir_csv]
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import datetime as dt
import re

from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion.permits import _idu
from labuse.ingestion.pc_caducs import _echeance

FILES = {"logements": ("NUM_DAU", "TYPE_DAU", "ETAT_DAU"),
         "locaux": ("NUM_DAU", "TYPE_DAU", "ETAT_DAU"),
         "pa": ("NUM_PA", None, "ETAT_PA"), "pd": ("NUM_PD", None, "ETAT_PD")}
TYPEFIX = {"pa": "PA", "pd": "PD"}
RX = re.compile(r"^SEC_CADASTRE(\d+)$")


def _parse_date(v):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return dt.date.fromisoformat(v[:10])
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dir_csv", nargs="?", default="/tmp")
    parser.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--avant-fix16", action="store_true", help="Comparer les 45 anciens écarts à la sauvegarde du 26/11/2026.")
    args = parser.parse_args()
    ref = args.date
    # agrégat par parcelle à partir des lignes PC officielles
    d_octroye: dict[str, dt.date] = {}
    realized: dict[str, bool] = {}
    granted: dict[str, bool] = {}
    for fam, (numcol, typecol, etatcol) in FILES.items():
        with open(f"{args.dir_csv}/sdes_{fam}.csv", newline="") as f:
            r = csv.DictReader(f, delimiter=";")
            flds = r.fieldnames or []
            pairs = [(c, f"NUM_CADASTRE{RX.match(c).group(1)}") for c in flds
                     if RX.match(c) and f"NUM_CADASTRE{RX.match(c).group(1)}" in flds]
            for rec in r:
                typ = ((rec.get(typecol) if typecol else TYPEFIX.get(fam)) or "").strip()
                if typ != "PC":
                    continue
                insee = (rec.get("COMM") or "").strip()
                etat = (rec.get(etatcol) or "").strip()
                d_aut = _parse_date(rec.get("DATE_REELLE_AUTORISATION"))
                daact = _parse_date(rec.get("DATE_REELLE_DAACT")) is not None
                octroye = etat in ("2", "5", "6")
                real = daact or etat in ("5", "6")
                for sc, nc in pairs:
                    idu = _idu(insee, rec.get(sc), rec.get(nc))
                    if not idu:
                        continue
                    if octroye:
                        granted[idu] = True
                        if d_aut is not None and (idu not in d_octroye or d_aut < d_octroye[idu]):
                            d_octroye[idu] = d_aut
                    if real:
                        realized[idu] = True
    # univers servi + signal local
    with session_scope() as db:
        univers = {r[0] for r in db.execute(text("SELECT idu FROM parcels")).all()}
        local = {r[0] for r in db.execute(text("SELECT idu FROM pc_caducs")).all()}
    officiel = set()
    for idu in granted:
        if idu not in univers or realized.get(idu):
            continue
        d = d_octroye.get(idu)
        if d is None:
            continue
        echeance, _ = _echeance(d)
        if echeance < ref:
            officiel.add(idu)
    only_off = sorted(officiel - local)
    only_loc = sorted(local - officiel)
    print(f"ref={ref}")
    print(f"LOCAL  (pc_caducs)                 : {len(local)}")
    print(f"OFFICIEL (recompte fichiers oct.)  : {len(officiel)}")
    print(f"seulement OFFICIEL (perdus à l'import) : {len(only_off)}")
    print(f"seulement LOCAL  (fonds historique régional / autre) : {len(only_loc)}")
    if args.avant_fix16:
        with session_scope() as db:
            avant = set(db.scalars(text("SELECT idu FROM pc_caducs_bak_fix16__20261126_085912")))
            anciens_ecarts = sorted(avant - officiel)
            origines = db.execute(text("""
                SELECT i.idu, array_agg(DISTINCT s.raw->>'src' ORDER BY s.raw->>'src')
                FROM unnest(CAST(:idus AS text[])) i(idu)
                JOIN sitadel_permits_bak_fix16__20261126_085912 s ON s.idu_codes ? i.idu AND s.type='PC'
                GROUP BY i.idu
            """), {"idus": anciens_ecarts}).all()
        categories = Counter(tuple(sources) for _, sources in origines)
        print(f"Avant correction : {len(anciens_ecarts)} seulement locaux")
        for sources, n in sorted(categories.items()):
            print(f"  {n} — {' + '.join(sources)}")
        print(f"Officiels récupérés : {len((officiel - avant) & local)}")
        print(f"Sortis après réimport : {', '.join(sorted(avant - local))}")


if __name__ == "__main__":
    main()
