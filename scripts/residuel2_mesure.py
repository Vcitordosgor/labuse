"""RESIDUEL-2 — mesure d'impact : double retrait (union globale) + qualification du repli + témoins.

Sur l'assiette EXACTE, avec les filtres du moteur (mêmes `parcel_faisabilite` / `compute_residuel`
que le service), pour chaque parcelle :
  - NEW = union globale des contraintes (code servi) ;
  - OLD = ancien double retrait (`legacy_union=False`, seam de mesure) ;
  - emprise OLD/NEW, C (sdp_max) OLD/NEW, E (inchangé), R OLD/NEW ;
  - catégories : augmentation géométrique / capacité inchangée après plafonds / résiduel redevenu
    positif ; verdict (R franchit 0, cause change).
  - qualification du repli (assiette_source NEW : gabarit / residuel_legacy_qualifie / residuel_legacy).

Usage :
  RESIDUEL2_MODE=temoins   → la liste de témoins nommés (batch ≡ fiche).
  RESIDUEL2_MODE=echantillon RESIDUEL2_N=600 → mesure sur un échantillon reproductible de legacy.

Lecture seule. Base réelle via LABUSE_DATABASE_URL.
"""
from __future__ import annotations

import hashlib
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.faisabilite.db import parcel_faisabilite  # noqa: E402
from labuse.faisabilite.residuel import compute_residuel  # noqa: E402

TEMOINS = [
    "97411000EH0043", "97411000EI0085", "97403000AL0258", "97415000DH0076",
    "97411000BZ1065", "97409000AK0804", "97403000AM0314", "97403000AM0473",
    "97403000AM0561",
]
N = int(os.environ.get("RESIDUEL2_N", "600"))
MODE = os.environ.get("RESIDUEL2_MODE", "temoins")


def _cer(d: dict) -> tuple:
    """(assiette_source, emprise, C, E, R, cause, disponible)."""
    if not d.get("disponible"):
        return (None, 0.0, 0.0, 0.0, 0.0, d.get("cause"), False)
    return (d.get("assiette_source"),
            float(d.get("emprise_constructible_m2") or 0.0),
            float(d.get("sdp_max_m2") or 0.0),
            float(d.get("sdp_existante_m2") or 0.0),
            float(d.get("sdp_residuelle_m2") or 0.0),
            None, True)


def _mesure_une(s, pid: int):
    new = parcel_faisabilite(s, pid)                       # code servi (union)
    old = parcel_faisabilite(s, pid, legacy_union=False)   # ancien double retrait
    d_new = compute_residuel(s, pid, faisa=new) if new else {"disponible": False}
    d_old = compute_residuel(s, pid, faisa=old) if old else {"disponible": False}
    asrc = new[1].fourchette.get("assiette_source") if new else None
    return asrc, _cer(d_new), _cer(d_old)


def temoins() -> None:
    with session_scope() as s:
        rows = {idu: pid for idu, pid in s.execute(text(
            "SELECT idu, id FROM parcels WHERE idu = ANY(:l)"), {"l": TEMOINS}).all()}
        print(f"{'IDU':16} {'source(NEW)':26} {'emp_old':>8} {'emp_new':>8} "
              f"{'C_old':>7} {'C_new':>7} {'E':>7} {'R_old':>7} {'R_new':>7}  note")
        for idu in TEMOINS:
            pid = rows.get(idu)
            if pid is None:
                print(f"{idu:16} INTROUVABLE")
                continue
            asrc, cn, co = _mesure_une(s, pid)
            dcnt = (co[1] + 0) - (cn[1])  # emprise: new >= old
            note = []
            if cn[1] > co[1] + 0.5:
                note.append(f"emprise +{cn[1]-co[1]:.0f}m² (double retrait levé)")
            if co[4] == 0 and cn[4] > 0:
                note.append("R 0→+")
            if cn[3] > cn[2] + 0.5:
                note.append(f"D_net={cn[2]-cn[3]:+.0f} (saturée)")
            print(f"{idu:16} {str(asrc):26} {co[1]:8.0f} {cn[1]:8.0f} "
                  f"{co[2]:7.0f} {cn[2]:7.0f} {cn[3]:7.0f} {co[4]:7.0f} {cn[4]:7.0f}  {'; '.join(note)}")


def echantillon() -> None:
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT parcel_id FROM parcel_residuel WHERE assiette_source='residuel_legacy'")).all()
    univ = sorted((r[0] for r in rows), key=lambda x: hashlib.md5(str(x).encode()).hexdigest())
    sample = univ[:N]
    print(f"legacy total={len(univ)} échantillon={len(sample)}")

    qual = Counter()
    emp_inc = c_inc = r_inc = r_0_to_pos = verdict_chg = 0
    cap_unchanged_after_plafond = 0
    double_sum = 0.0
    changed = []
    errors = 0
    with session_scope() as s:
        for i, pid in enumerate(sample):
            try:
                asrc, cn, co = _mesure_une(s, pid)
            except Exception as e:  # noqa: BLE001
                errors += 1
                continue
            qual[str(asrc)] += 1
            d_emp = cn[1] - co[1]
            if d_emp > 0.5:
                emp_inc += 1
                double_sum += d_emp
                if abs(cn[2] - co[2]) < 0.5:
                    cap_unchanged_after_plafond += 1
            if cn[2] - co[2] > 0.5:
                c_inc += 1
            if cn[4] - co[4] > 0.5:
                r_inc += 1
            if co[4] <= 0 and cn[4] > 0.5:
                r_0_to_pos += 1
            # verdict : R franchit 0, OU disponibilité/cause change
            if (co[6] != cn[6]) or (co[4] <= 0) != (cn[4] <= 0):
                verdict_chg += 1
                if len(changed) < 40:
                    changed.append((pid, co, cn))
    n = len(sample) - errors
    print(f"\nmesurées={n} erreurs={errors}")
    print("=== QUALIFICATION (assiette_source NEW) ===")
    for k, v in qual.most_common():
        print(f"  {v:5d}  {100.0*v/len(sample):5.1f}%  ~{round(len(univ)*v/len(sample)):6d}  {k}")
    print("\n=== DOUBLE RETRAIT (impact) ===")
    print(f"  emprise augmentée (double retrait levé) : {emp_inc}  ({100.0*emp_inc/n:.1f}%)  "
          f"~{round(len(univ)*emp_inc/n)} île")
    print(f"    dont capacité INCHANGÉE après plafonds (C_old==C_new) : {cap_unchanged_after_plafond}")
    print(f"  C (sdp_max) augmentée                   : {c_inc}")
    print(f"  R (résiduel) augmenté                   : {r_inc}")
    print(f"  R redevenu POSITIF (0 → +)              : {r_0_to_pos}  ~{round(len(univ)*r_0_to_pos/n)} île")
    print(f"  VERDICT changé                          : {verdict_chg}  ~{round(len(univ)*verdict_chg/n)} île")
    print(f"  surface doublement soustraite (somme échantillon) : {double_sum:.0f} m² "
          f"(moyenne/touchée {double_sum/max(1,emp_inc):.0f})")
    print("\n=== exemples de verdict changé (pid, R_old→R_new, C_old→C_new) ===")
    for pid, co, cn in changed[:25]:
        print(f"  {pid}  R {co[4]:.0f}→{cn[4]:.0f}  C {co[2]:.0f}→{cn[2]:.0f}  emp {co[1]:.0f}→{cn[1]:.0f}")


if __name__ == "__main__":
    (temoins if MODE == "temoins" else echantillon)()
