"""OUTIL-ASSEMBLAGE-FIX-6 — MESURE double-passage (lecture seule) de la charge foncière des
ASSEMBLAGES multizones (paires contiguës de zones différentes). C'est le SEUL chemin euro touché
par la somme des logements (LOT 2). CSV (commune, za, zb, regime, cf_central, log_prog, log_rep).
Passe `courant` (code actuel) puis `prefix` (git stash) → diff. ARRÊT du commit si un cf bouge."""
import csv
import os
import sys

DBURL = "postgresql+psycopg://openclaw@localhost:5432/labuse"
TAG = sys.argv[1] if len(sys.argv) > 1 else "courant"
CAND = sys.argv[2] if len(sys.argv) > 2 else "/tmp/fix6_asm_pairs_mesure.csv"
_S = None


def _init():
    global _S
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    _S = Session(create_engine(DBURL, future=True))
    _S.execute(text("SET default_transaction_read_only = on"))


def _one(rec):
    a, b, commune = rec
    from types import SimpleNamespace
    from sqlalchemy import text
    from labuse.assemblage import aggregate_assiette
    try:
        _S.rollback()
        rows = _S.execute(text("SELECT id, idu, COALESCE(contenance_m2,surface_m2) s, commune "
                               "FROM parcels WHERE idu IN (:a,:b)"), {"a": a, "b": b}).all()
        if len(rows) != 2:
            return (commune, a, b, "ERR2", "", "", "")
        parcels = [SimpleNamespace(id=r.id, idu=r.idu, surface_m2=r.s, commune=r.commune,
                                   contenance_m2=r.s) for r in rows]
        agg = aggregate_assiette(_S, parcels)
    except Exception:
        return (commune, a, b, "ERR", "", "", "")
    m = agg.get("mixite") or {}
    cf = (agg.get("charge_fonciere") or {}).get("central")
    return (commune, a, b, (m.get("regime") or "-"), cf if cf is not None else "",
            agg.get("logements_programme"), agg.get("logements_representatif"))


def main():
    from concurrent.futures import ProcessPoolExecutor
    recs = []
    with open(CAND) as f:
        r = csv.reader(f); next(r)
        for row in r:
            recs.append((row[0], row[1], row[2]))
    out = open(f"/tmp/fix6_asm_{TAG}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["commune", "a", "b", "regime", "cf_central", "log_prog", "log_rep"])
    with ProcessPoolExecutor(max_workers=8, initializer=_init) as ex:
        for res in ex.map(_one, recs, chunksize=50):
            w.writerow(res)
    out.close()
    print(f"[{TAG}] {len(recs)} assemblages -> /tmp/fix6_asm_{TAG}.csv")


if __name__ == "__main__":
    main()
