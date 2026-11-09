"""RESIDUEL-2 — mesure EXACTE du double retrait sur TOUTE la population qui peut être touchée.

Le double retrait ne peut affecter qu'une parcelle legacy portant À LA FOIS une prescription ER/EBC
ET une contrainte certaine (PPR/PEB/DPF/ravine/50 pas) qui se recouvrent sur l'assiette. On énumère
donc les parcelles legacy avec ER/EBC (surensemble strict de l'ensemble touché) et on mesure, sur
l'assiette exacte avec les filtres du moteur : emprise OLD (double retrait) vs NEW (union), C/E/R
OLD/NEW. Donne le NOMBRE exact île de parcelles dont la capacité change et la LISTE des verdicts
changés (R franchit 0).

Lecture seule. Base réelle via LABUSE_DATABASE_URL.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.faisabilite.db import parcel_faisabilite  # noqa: E402
from labuse.faisabilite.residuel import compute_residuel  # noqa: E402

_SQL_CANDIDATS = text("""
WITH leg AS (SELECT pr.parcel_id, p.geom_2975 g, p.commune
             FROM parcel_residuel pr JOIN parcels p ON p.id = pr.parcel_id
             WHERE pr.assiette_source IN ('residuel_legacy','residuel_legacy_qualifie'))
SELECT DISTINCT l.parcel_id
FROM leg l JOIN spatial_layers pr
  ON pr.kind='plu_gpu_prescription' AND pr.commune=l.commune AND pr.subtype IN ('05','01')
     AND ST_Intersects(pr.geom_2975, l.g)
""")


def main() -> None:
    with session_scope() as s:
        ids = [r[0] for r in s.execute(_SQL_CANDIDATS).all()]
    print(f"legacy porteuses d'ER/EBC (surensemble du touché) : {len(ids)}")

    emp_chg = c_chg = r_chg = r_0_to_pos = 0
    double_tot = 0.0
    changed = []     # (pid, R_old, R_new, C_old, C_new)
    verdict_list = []
    errors = 0
    t0 = time.time()
    with session_scope() as s:
        for i, pid in enumerate(ids):
            try:
                new = parcel_faisabilite(s, pid)
                old = parcel_faisabilite(s, pid, legacy_union=False)
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            if new is None or old is None:
                continue
            dn = compute_residuel(s, pid, faisa=new)
            do = compute_residuel(s, pid, faisa=old)
            if not dn.get("disponible") or not do.get("disponible"):
                continue
            e_new = float(dn.get("emprise_constructible_m2") or 0.0)
            e_old = float(do.get("emprise_constructible_m2") or 0.0)
            C_new = float(dn.get("sdp_max_m2") or 0.0); C_old = float(do.get("sdp_max_m2") or 0.0)
            R_new = float(dn.get("sdp_residuelle_m2") or 0.0); R_old = float(do.get("sdp_residuelle_m2") or 0.0)
            if e_new - e_old > 0.5:
                emp_chg += 1
                double_tot += (e_new - e_old)
            if C_new - C_old > 0.5:
                c_chg += 1
            if R_new - R_old > 0.5:
                r_chg += 1
                if len(changed) < 60:
                    changed.append((pid, R_old, R_new, C_old, C_new))
            if R_old <= 0 and R_new > 0.5:
                r_0_to_pos += 1
                verdict_list.append(pid)
            if i % 500 == 0 and i:
                print(f"  … {i}/{len(ids)} ({time.time()-t0:.0f}s) — emp_chg={emp_chg} r_chg={r_chg}")
    dt = time.time() - t0
    print(f"\nmesurées={len(ids)-errors} erreurs={errors} en {dt:.0f}s")
    print("=== IMPACT EXACT DU DOUBLE RETRAIT (île entière, population touchable) ===")
    print(f"  emprise augmentée (double retrait levé) : {emp_chg}")
    print(f"  C (sdp_max) augmentée                   : {c_chg}")
    print(f"  R (capacité servie) augmentée           : {r_chg}")
    print(f"  R redevenu POSITIF (faux zéro corrigé)  : {r_0_to_pos}")
    print(f"  surface doublement soustraite (somme)   : {double_tot:.0f} m² "
          f"(moy/touchée {double_tot/max(1,emp_chg):.0f})")
    print(f"\n  → NOMBRE DE PARCELLES DONT LA CAPACITÉ (R) CHANGE : {r_chg}")
    print(f"  → VERDICT CHANGÉ (R franchit 0) : {r_0_to_pos}  {verdict_list[:40]}")
    print("\n=== détail (pid, R_old→R_new, C_old→C_new) ===")
    for pid, ro, rn, co, cn in changed:
        print(f"  {pid}  R {ro:.0f}→{rn:.0f}  C {co:.0f}→{cn:.0f}")


if __name__ == "__main__":
    main()
