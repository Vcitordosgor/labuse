"""md5 du payload /parcels/{idu} sur 20 parcelles — preuve d'invariance avant/après.
Usage: vfiche2_md5.py [capture|compare] <fichier>
Lecture seule."""
from __future__ import annotations
import hashlib
import json
import sys
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from labuse.db import session_factory
from labuse import runs
from labuse.api import app as A


def _idus(s, cr, n=20):
    return s.execute(text(
        """SELECT p.idu FROM parcels p JOIN dryrun_parcel_evaluations d
           ON d.parcel_id=p.id AND d.run_label=:r WHERE p.commune IS NOT NULL
           ORDER BY md5('salt'||p.idu) LIMIT :n"""), {"r": cr, "n": n}).scalars().all()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "capture"
    path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/vfiche2_md5.json"
    run = runs.current()
    s = session_factory()()
    cr = A._cascade_run(s, run)
    idus = _idus(s, cr)
    out = {}
    for idu in idus:
        payload = A.parcel_fiche(idu, source=run, db=s, request=None, trace=0)
        body = json.dumps(jsonable_encoder(payload), sort_keys=True, ensure_ascii=False)
        out[idu] = hashlib.md5(body.encode()).hexdigest()
    s.close()
    if mode == "capture":
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"capturé {len(out)} md5 → {path}")
        for k, v in out.items():
            print(f"  {k} {v}")
    else:
        with open(path) as f:
            ref = json.load(f)
        ok = True
        for k, v in out.items():
            match = ref.get(k) == v
            ok = ok and match
            print(f"  {'OK ' if match else 'DIFF'} {k} {v}{'' if match else ' != '+str(ref.get(k))}")
        print("=== IDENTIQUE ===" if ok else "=== DIVERGENCE ===")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
