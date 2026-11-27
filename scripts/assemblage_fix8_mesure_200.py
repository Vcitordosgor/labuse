"""Mesure euro de compute_bilan_servi sur 200 parcelles déterministes (CA + charge foncière,
bas/central/haut). Écrit un JSON keyé par idu. Lancé 2× (avant/après) pour comparer à l'euro près."""
import json
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import compute_bilan_servi

DBURL = os.environ["LABUSE_APP_DATABASE_URL"]
out_path = sys.argv[1]
e = create_engine(DBURL, future=True)
db = Session(e)
db.execute(text("SET default_transaction_read_only = on"))

# 200 parcelles déterministes : 100 Saint-Paul + 100 Saint-Denis, triées par idu (stable), pas de random.
idus = []
for commune in ("Saint-Paul", "Saint-Denis"):
    rows = db.execute(text(
        "SELECT idu FROM parcels WHERE commune = :c ORDER BY idu LIMIT 100 OFFSET 5000"),
        {"c": commune}).scalars().all()
    idus += list(rows)

res = {}
for idu in idus:
    db.rollback()
    pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    try:
        b, _ = compute_bilan_servi(db, pid)
    except Exception as ex:  # noqa: BLE001
        res[idu] = {"err": repr(ex)}
        continue
    if b is None:
        res[idu] = None
        continue
    ca = getattr(b, "ca", None) or {}
    cf = getattr(b, "charge_fonciere", None) or {}
    res[idu] = {"ca": [ca.get("bas"), ca.get("central"), ca.get("haut")],
                "cf": [cf.get("bas"), cf.get("central"), cf.get("haut")]}
json.dump(res, open(out_path, "w"))
print(f"{len([v for v in res.values() if isinstance(v, dict) and 'ca' in v])} bilans chiffrés sur {len(idus)}")
