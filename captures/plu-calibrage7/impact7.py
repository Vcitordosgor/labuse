"""PLU-CALIBRAGE-7 §4 — IMPACT rejoué (lecture seule). Même méthode que PLU-CALIBRAGE-6 §4.

Mesure, sur les 22 zones rendues « non calculable — règle PLU non validée » par PLU-CALIBRAGE-6,
la cause du résiduel calculée par `compute_residuel` (code courant), sur le MÊME échantillon
reproductible (id-ordonné, ≤N/zone). À lancer AVANT l'application des formes (état PLU-6) puis
APRÈS (état PLU-7) — le fichier de sortie est suffixé par `--tag`.

Usage : LABUSE_DATABASE_URL=postgresql+psycopg:///labuse PYTHONPATH=src \
        .venv/bin/python captures/plu-calibrage7/impact7.py --tag avant [--par-zone 40]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.residuel import compute_residuel

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "run"
PAR_ZONE = int(sys.argv[sys.argv.index("--par-zone") + 1]) if "--par-zone" in sys.argv else 40

AFF = json.load(open("/tmp/plu6_affected_zones.json"))
NC_ZONES = [tuple(x) for x in AFF["nc_zones"]]


def _cause(session, pid):
    d = compute_residuel(session, pid)
    if d.get("disponible"):
        return "calculable"
    c = d.get("cause") or "indetermine"
    return c.split(":")[0]                     # famille (sans le suffixe zone)


def main():
    par_commune = defaultdict(lambda: defaultdict(int))
    extrap = defaultdict(lambda: defaultdict(float))   # commune -> cause -> parcelles estimées
    n = 0
    with session_scope() as s:
        for (commune, zone) in sorted(NC_ZONES):
            rows = s.execute(text(
                """SELECT p.id FROM parcel_zone_plu zp JOIN parcels p ON p.idu = zp.idu
                   WHERE p.commune = :c AND zp.zone_lib = :z ORDER BY p.id"""),
                {"c": commune, "z": zone}).scalars().all()
            if not rows:
                continue
            step = max(1, len(rows) // PAR_ZONE)
            sample = rows[::step][:PAR_ZONE]
            local = defaultdict(int)
            for pid in sample:
                n += 1
                c = _cause(s, pid)
                par_commune[commune][c] += 1
                local[c] += 1
            for c, k in local.items():
                extrap[commune][c] += (k / len(sample)) * len(rows)

    grand = defaultdict(int)
    print(f"[{TAG}] Échantillon {n} parcelles ({len(NC_ZONES)} zones NC PLU-6, ≤{PAR_ZONE}/zone)\n")
    for commune in sorted(par_commune):
        line = ", ".join(f"{c}={k}" for c, k in sorted(par_commune[commune].items(), key=lambda x: -x[1]))
        print(f"  {commune:14} {line}")
        for c, k in par_commune[commune].items():
            grand[c] += k
    print("\n  TOTAL échantillon :", ", ".join(f"{c}={k}" for c, k in sorted(grand.items(), key=lambda x: -x[1])))
    # extrapolation par cause
    grand_ex = defaultdict(float)
    for commune, causes in extrap.items():
        for c, v in causes.items():
            grand_ex[c] += v
    print("\n  EXTRAPOLATION île (22 zones NC) par cause :")
    for c, v in sorted(grand_ex.items(), key=lambda x: -x[1]):
        print(f"     ~{round(v):6}  {c}")
    out = {"tag": TAG, "n": n, "par_commune": {k: dict(v) for k, v in par_commune.items()},
           "total": dict(grand), "extrapolation": {c: round(v) for c, v in grand_ex.items()}}
    json.dump(out, open(f"captures/plu-calibrage7/impact_{TAG}.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n→ captures/plu-calibrage7/impact_{TAG}.json")


if __name__ == "__main__":
    main()
