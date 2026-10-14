"""CHASSE-CALCULS-FIX-1 Lot 4 (E-B2) — GARDE : une SEULE zone d'implantation.
L'outil Gabarit et l'outil Faisabilité doivent servir la MÊME zone d'implantation au m² près
(même fonction compute_gabarit, même échelle contenance CONTENANCE-1 C3). Exit 0 = parité.
    LABUSE_DATABASE_URL=... PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_garde_eb2.py
"""
import json, sys
from fastapi.testclient import TestClient
from labuse.api import auth
from labuse.api.app import app
from labuse.api.protection import HOTE_INTERNE

C = TestClient(app, client=(HOTE_INTERNE, 0)); C.cookies.set(auth.COOKIE, auth.make_token())
# témoins B1 où le Gabarit sert une zone (status ok)
TEMOINS = ["97409000AK0804", "97412000BV0419", "97411000BK0101", "97412000BV0039", "97408000AN0062"]


def run():
    ok = True
    for idu in TEMOINS:
        gb = json.loads(C.get(f"/outils/gabarit/{idu}").content)
        fa = json.loads(C.get(f"/modules/faisabilite/{idu}").content)
        zg = gb.get("zoneImplantationM2")
        zf = ((fa.get("capacite") or {}).get("fourchette") or {}).get("zone_implantation_m2")
        match = zg is not None and zf is not None and abs(zg - zf) <= 1
        ok = ok and match
        print(f"  [{'OK' if match else 'DIVERGE':8}] {idu}  Gabarit={zg}  Faisabilité={zf}")
    print("\n✓ E-B2 : zone d'implantation UNIQUE (Gabarit = Faisabilité au m² près)." if ok
          else "\n✗ E-B2 : divergence restante.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
