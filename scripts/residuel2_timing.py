"""RESIDUEL-2 — timing du run résiduel (reconstruction C/E/D_net) AVEC le correctif union globale.

Chronomètre `compute_residuel` (qui produit C=sdp_max, E=sdp_existante, R, et D_net=C−E signé) sur
un échantillon réel d'une commune, SANS persistance (mesure pure du coût CPU/DB par parcelle).
Extrapole à l'île (433 229) et à 4 shards disjoints (mécanique `residuel_shard.sh`). Vérifie que ça
tient dans la nuit.

Usage : RESIDUEL2_COMMUNE="Entre-Deux" RESIDUEL2_NT=400 python scripts/residuel2_timing.py
Lecture seule. Base réelle via LABUSE_DATABASE_URL.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.faisabilite.residuel import compute_residuel  # noqa: E402

COMMUNE = os.environ.get("RESIDUEL2_COMMUNE", "Entre-Deux")
NT = int(os.environ.get("RESIDUEL2_NT", "400"))
ILE = 433229
NUIT_H = 8.0


def main() -> None:
    with session_scope() as s:
        ids = [r[0] for r in s.execute(text(
            "SELECT p.id FROM parcels p WHERE p.commune = :c ORDER BY p.id"), {"c": COMMUNE}).all()]
    if not ids:
        print(f"commune {COMMUNE} introuvable"); return
    # échantillon régulier (couvre tout le fichier, pas un bloc homogène)
    step = max(1, len(ids) // NT)
    sample = ids[::step][:NT]
    print(f"commune={COMMUNE} parcelles={len(ids)} échantillon chronométré={len(sample)}")

    d_net_neg = c_pos = e_pos = 0
    t0 = time.time()
    with session_scope() as s:
        for pid in sample:
            d = compute_residuel(s, pid)
            if d.get("disponible"):
                C = float(d.get("sdp_max_m2") or 0.0)
                E = float(d.get("sdp_existante_m2") or 0.0)
                if C > 0:
                    c_pos += 1
                if E > 0:
                    e_pos += 1
                if C - E < 0:
                    d_net_neg += 1
    dt = time.time() - t0
    per = dt / len(sample)
    print(f"temps total={dt:.1f}s  par parcelle={per*1000:.0f} ms  débit mono={1/per:.1f} p/s")
    print(f"(C>0 : {c_pos}  E>0 : {e_pos}  D_net<0 (saturées) : {d_net_neg})")

    mono_h = ILE * per / 3600.0
    print("\n=== EXTRAPOLATION ÎLE (433 229) ===")
    print(f"  mono-cœur séquentiel : {mono_h:.1f} h")
    for w in (2, 4):
        # rendement shard mesuré ~0,76× le linéaire (DB-bound) ; on l'applique prudemment.
        eff = 0.76 if w == 4 else 0.85
        h = mono_h / (w * eff)
        print(f"  {w} shards (rendement {eff:.0%}) : {h:.1f} h  → {'TIENT' if h < NUIT_H else 'NE TIENT PAS'} "
              f"dans la nuit ({NUIT_H:.0f} h)")


if __name__ == "__main__":
    main()
