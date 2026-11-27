"""OUTIL-ASSEMBLAGE-FIX-2 — passe ÎLE en LECTURE SEULE : impact € des LOTS 1-3 (mixité) vs FIX-1.

Lecture seule imposée par la base (`SET default_transaction_read_only = on` ; preuve : un INSERT de
test est refusé AVANT la passe). Une seule connexion. Pour chaque parcelle en secteur de mixité
sociale (SMS) : charge foncière NEW (code FIX-2) vs OLD (FIX-1 simulé — on désactive le seul
déclencheur ajouté, « ≥ 20 logements » en bande, en portant `mixite_logements_seuil` hors d'atteinte ;
l'exclusion ZAC est inerte faute de périmètre, identique des deux côtés). Toute parcelle dont la charge
bouge est écrite au CSV. Sortie brute collée au compte-rendu.

Usage : PYTHONPATH=src python docs/audit-2026-11/outil-assemblage-fix-1/mesure_fix2.py
"""
from __future__ import annotations

import csv
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import compute_bilan_servi
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.engine import Hypotheses

OUT_CSV = os.path.join(os.path.dirname(__file__), "fix2-parcelles-qui-bougent.csv")
# communes à mixité = celles qui portent un SMS (prescription 16/17) ; les autres ne déclenchent jamais.
COMMUNES = ["Saint-Paul", "Saint-Pierre", "Saint-Benoît", "Saint-Denis", "Saint-Louis", "Le Tampon"]


def main() -> None:
    eng = create_engine(os.environ["LABUSE_DATABASE_URL"], pool_size=1, max_overflow=0)
    s = Session(eng)
    s.execute(text("SET default_transaction_read_only = on"))
    s.commit()
    try:
        s.execute(text("INSERT INTO bilan_params(secteur,param,value) VALUES ('_p','_p',1)"))
        s.commit()
        print("ERREUR : écriture autorisée — on ne lance pas la passe")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        s.rollback()
        print("PREUVE read-only OK :", str(e).splitlines()[0][:70])

    _orig = Hypotheses.charger.__func__

    def _old(cls, commune=None):
        h = _orig(cls, commune)
        h.mixite_logements_seuil = 1e9      # FIX-1 : pas de déclencheur « ≥ 20 logements » en bande
        return h

    rows_out: list[tuple] = []
    table: list[tuple] = []
    for commune in COMMUNES:
        # parcelles constructibles EN SMS (seules candidates au déclenchement) ; si aucune → 0 par construction.
        pids = s.execute(text(
            """SELECT p.id, p.idu FROM parcels p JOIN parcel_residuel r ON r.parcel_id = p.id
               WHERE p.commune = :c AND r.capacite_estimee
                 AND EXISTS (SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_prescription'
                             AND z.subtype IN ('16','17') AND z.commune = :c
                             AND ST_Intersects(z.geom_2975, p.geom_2975))"""), {"c": commune}).all()
        tested = changed = 0
        deltas: list[float] = []
        for pid, idu in pids:
            fz = parcel_faisabilite(s, pid)
            if not fz or not fz[1].constructible:
                continue
            b_new, _ = compute_bilan_servi(s, pid, fz=fz)
            Hypotheses.charger = classmethod(_old)
            try:
                b_old, _ = compute_bilan_servi(s, pid, fz=fz)
            finally:
                Hypotheses.charger = classmethod(_orig)

            def _c(b):
                return (b.charge_fonciere or {}).get("central") if (b and b.charge_fonciere) else None
            cn, co = _c(b_new), _c(b_old)
            if cn is None or co is None:
                continue
            tested += 1
            if abs(cn - co) >= 1:
                changed += 1
                deltas.append(cn - co)
                rows_out.append((idu, commune, round(co), round(cn), round(cn - co)))
        med = round(sorted(abs(d) for d in deltas)[len(deltas) // 2]) if deltas else 0
        mx = round(max((abs(d) for d in deltas), default=0))
        tot = round(sum(deltas)) if deltas else 0
        table.append((commune, len(pids), tested, changed, med, mx, tot))

    print(f"\n{'commune':14} {'SMS-constr':>10} {'testées':>8} {'changées':>8} {'médian€':>9} {'max€':>9} {'total€':>10}")
    for c, npar, tested, changed, med, mx, tot in table:
        print(f"{c:14} {npar:>10} {tested:>8} {changed:>8} {med:>9} {mx:>9} {tot:>10}")
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "commune", "charge_avant_eur", "charge_apres_eur", "delta_eur"])
        w.writerows(rows_out)
    print(f"\nparcelles qui bougent : {len(rows_out)} -> {OUT_CSV}")
    s.close()


if __name__ == "__main__":
    main()
