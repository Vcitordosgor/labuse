"""RECETTE-9 T8 — contrôle croisé de l'EXPOSITION (W22) sur 10 parcelles (lecture seule).
Compare exposition_parcelle (gdaldem) à enrichment.exposition (4 points RGE ALTI, indépendant)
et au productible/GHI (parcel_solar). Prouve que l'orientation n'est pas retournée et que le
productible est ~horizontal (GHI) donc pas un juge de l'orientation.
Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python scripts/_recette9_t8_exposition.py
"""
import math, statistics
from sqlalchemy import text
from labuse.db import session_factory
from labuse.faisabilite.exposition import exposition_parcelle
from labuse.api import enrichment

IDUS = ["97423000AI0696","97412000AM0801","97424000AE2008","97416000CX0790","97409000BD1213",
        "97412000AL0468","97407000AO0788","97407000AO0869","97416000HO1043","97407000AO0315"]
db = session_factory()()
print(f"{'IDU':16}{'gdaldem(W22)':>14}{'asp':>7}{'4pts':>13}{'azi':>6}{'prod':>7}{'ghi':>6}")
prods = []
for idu in IDUS:
    pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    e1 = exposition_parcelle(db, pid) or {}
    e2 = enrichment.exposition(db, pid) or {}
    sol = db.execute(text("SELECT round(prod_spec_kwh_kwc) p, round(ghi_kwh_m2_an) g "
                          "FROM parcel_solar WHERE idu=:i"), {"i": idu}).first()
    o2 = e2.get("exposition") or ("plat" if (e2.get("label") or "").startswith("terrain plat") else None)
    prods.append((sol.p if sol else None, sol.g if sol else None))
    print(f"{idu:16}{str(e1.get('orientation')):>14}{str(e1.get('aspect_deg')):>7}"
          f"{str(o2):>13}{str(e2.get('azimut_deg')):>6}{str(sol.p if sol else None):>7}{str(sol.g if sol else None):>6}")
xs = [p for p, g in prods if p]; gs = [g for p, g in prods if g]
mx, mg = statistics.mean(xs), statistics.mean(gs)
cov = sum((x-mx)*(g-mg) for x, g in zip(xs, gs))
sx = math.sqrt(sum((x-mx)**2 for x in xs)); sg = math.sqrt(sum((g-mg)**2 for g in gs))
print(f"\nr(productible, GHI) = {cov/(sx*sg):.3f}  → productible ~= irradiation horizontale (pas l'orientation)")
