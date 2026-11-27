"""OUTIL-ASSEMBLAGE-FIX-6 — MESURE double-passage (lecture seule) de la charge foncière des bilans
SINGLE parcelle (compute_bilan_servi : fiche + Bilan). Produit CSV (idu, commune, zone, regime,
cf_central). Lancé une fois sur le code COURANT (tag `courant`) et une fois sur le code d'AVANT
(tag `prefix`, via git stash), puis diff. ARRÊT du commit LOTS 1-3 si un cf_central bouge."""
import csv
import os
import sys

DBURL = "postgresql+psycopg://openclaw@localhost:5432/labuse"
TAG = sys.argv[1] if len(sys.argv) > 1 else "courant"
_S = None


def _init():
    global _S
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    _S = Session(create_engine(DBURL, future=True))
    _S.execute(text("SET default_transaction_read_only = on"))


def _one(rec):
    pid, idu, commune, zone = rec
    from labuse.faisabilite.bilan import compute_bilan_servi
    try:
        _S.rollback()
        b, _ = compute_bilan_servi(_S, int(pid))
    except Exception:
        return (idu, commune, zone, "ERR", "")
    if not b or not b.fiable or not b.charge_fonciere:
        return (idu, commune, zone, "nc", "")
    m = getattr(b, "mixite", None) or {}
    return (idu, commune, zone, (m.get("regime") or "-"), b.charge_fonciere.get("central"))


def main():
    from concurrent.futures import ProcessPoolExecutor
    recs = []
    with open("/tmp/fix6_single_candidates.csv") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            recs.append((row[0], row[1], row[2], row[3]))
    out = open(f"/tmp/fix6_single_{TAG}.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["idu", "commune", "zone", "regime", "cf_central"])
    with ProcessPoolExecutor(max_workers=8, initializer=_init) as ex:
        for res in ex.map(_one, recs, chunksize=200):
            w.writerow(res)
    out.close()
    print(f"[{TAG}] {len(recs)} bilans écrits -> /tmp/fix6_single_{TAG}.csv")


if __name__ == "__main__":
    main()
