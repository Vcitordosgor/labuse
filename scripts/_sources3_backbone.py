"""SOURCES-AUDIT-3 — backbone dump (lecture seule).
Résout DONNEES → reservoirs (RESERVOIR_TABLES) → data_sources (status/millésime).
Sortie TSV sur stdout : donnee_slug, libelle, niveau, calcul, fonction, reservoirs,
tables, source_ids, source_names, source_status, millesime_reservoir, millesime_db.
"""
import os, sys, csv
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
sys.path.insert(0, "src")

from labuse.registre.donnees import DONNEES
from labuse.registre.tables import RESERVOIR_TABLES
from labuse.circuit_etats import NOM_VERS_SLUG

import psycopg
SLUG_VERS_NOM = {v: k for k, v in NOM_VERS_SLUG.items()}
conn = psycopg.connect("postgresql://openclaw@localhost:5432/labuse")
rows = conn.execute("SELECT id, name, status, source_millesime FROM data_sources").fetchall()
NAME2ROW = {r[1]: r for r in rows}

def source_for_slug(slug):
    nom = SLUG_VERS_NOM.get(slug)
    if not nom:
        return (None, f"[slug {slug} absent NOM_VERS_SLUG]", "?", "")
    r = NAME2ROW.get(nom)
    if not r:
        return (None, nom, "[absent data_sources]", "")
    return (r[0], r[1], r[2], r[3] or "")

w = csv.writer(sys.stdout, delimiter="\t")
w.writerow(["donnee_slug","libelle","niveau","calcul","moteur","fonction","reservoirs",
            "tables","source_ids","source_status","millesime_reservoir","millesime_db"])
for slug, d in DONNEES.items():
    reservoirs = d.reservoirs or ()
    tables, sids, statuses, mres = [], [], [], []
    for rslug in reservoirs:
        rt = RESERVOIR_TABLES.get(rslug)
        if rt:
            tables.extend(rt.tables)
            if rt.millesime:
                mres.append(f"{rslug}:{rt.millesime[:40]}")
        sid, sname, sstatus, sdb = source_for_slug(rslug)
        sids.append(f"{sid}:{rslug}")
        statuses.append(sstatus)
    w.writerow([slug, d.libelle, d.niveau, d.calcul, d.moteur or "", d.fonction,
                "|".join(reservoirs), "|".join(sorted(set(tables))),
                "|".join(sids), "|".join(statuses),
                " ;; ".join(mres)[:200], ""])
conn.close()
