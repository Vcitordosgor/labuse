"""OUTIL-ASSEMBLAGE-FIX-2 — distribution des RÉGIMES de mixité (lecture seule), pour chiffrer les
explications du compte-rendu :
  Q1 — combien de parcelles Saint-Paul sont en « borne haute » (régime intermédiaire, CA au prix libre,
       accession non chiffrée) ;
  Q2 — combien sont en intermédiaire DÉCLENCHÉES PAR LE SEUL « ≥ 20 logements » (programme < 1 500 m²) ;
  Q3 — Saint-Denis / Saint-Pierre : 3 parcelles constructibles chacune → `eco["mixite"]` (SMS) = ?

Lecture seule imposée (INSERT refusé avant la passe). On lit `Bilan.mixite` (regime + critère), jamais
les champs `logements_*` directement (doctrine LOGEMENTS-SOURCE-UNIQUE).

Usage : PYTHONPATH=src python docs/audit-2026-11/outil-assemblage-fix-1/regimes_fix2.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import compute_bilan_servi
from labuse.faisabilite.db import parcel_faisabilite


def main() -> None:
    eng = create_engine(os.environ["LABUSE_DATABASE_URL"], pool_size=1, max_overflow=0)
    s = Session(eng)
    s.execute(text("SET default_transaction_read_only = on"))
    s.commit()
    try:
        s.execute(text("INSERT INTO bilan_params(secteur,param,value) VALUES ('_p','_p',1)")); s.commit()
        print("ERREUR : écriture autorisée"); sys.exit(1)
    except Exception as e:  # noqa: BLE001
        s.rollback(); print("PREUVE read-only OK :", str(e).splitlines()[0][:70])

    # Q1/Q2 — régimes des parcelles Saint-Paul constructibles EN SMS.
    pids = s.execute(text(
        """SELECT p.id, p.idu FROM parcels p JOIN parcel_residuel r ON r.parcel_id = p.id
           WHERE p.commune = 'Saint-Paul' AND r.capacite_estimee
             AND EXISTS (SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_prescription'
                         AND z.subtype IN ('16','17') AND z.commune='Saint-Paul'
                         AND ST_Intersects(z.geom_2975, p.geom_2975))""")).all()
    n = {"plein": 0, "intermediaire": 0, "intermediaire_via_logements": 0, "non_declenchee": 0, "sans_bilan": 0}
    ex_borne, ex_log = [], []
    for pid, idu in pids:
        fz = parcel_faisabilite(s, pid)
        if not fz or not fz[1].constructible:
            n["sans_bilan"] += 1; continue
        b, _ = compute_bilan_servi(s, pid, fz=fz)
        mx = (b.mixite if b else None)
        if not mx:
            n["sans_bilan"] += 1; continue
        reg = mx.get("regime")
        if reg == "plein":
            n["plein"] += 1
        elif reg == "intermediaire":
            n["intermediaire"] += 1
            if "logements" in (mx.get("critere") or ""):
                n["intermediaire_via_logements"] += 1
                if len(ex_log) < 3:
                    ex_log.append((idu, mx.get("critere")))
            if mx.get("borne_haute") and len(ex_borne) < 3:
                ex_borne.append((idu, (b.charge_fonciere or {}).get("central")))
        else:
            n["non_declenchee"] += 1
    print(f"\nSaint-Paul, parcelles constructibles en SMS : {len(pids)}")
    for k, v in n.items():
        print(f"  {k:30} {v}")
    print(f"  (borne haute = intermédiaire = {n['intermediaire']})")
    print("  exemples borne haute (idu, charge €) :", ex_borne)
    print("  exemples ≥20 logts seuls (idu, critère) :", ex_log)

    # Q3 — Saint-Denis / Saint-Pierre : 3 parcelles constructibles → eco["mixite"] (SMS) ?
    for comm in ("Saint-Denis", "Saint-Pierre"):
        rows = s.execute(text(
            "SELECT p.id, p.idu FROM parcels p JOIN parcel_residuel r ON r.parcel_id=p.id "
            "WHERE p.commune=:c AND r.capacite_estimee ORDER BY r.surface_terrain_m2 DESC NULLS LAST LIMIT 3"),
            {"c": comm}).all()
        print(f"\n{comm} — 3 parcelles constructibles (eco['mixite'] = en secteur de mixité sociale ?) :")
        for pid, idu in rows:
            fz = parcel_faisabilite(s, pid)
            eco = fz[0].prescriptions_eco if fz else {}
            print(f"  {idu}  eco[mixite]={eco.get('mixite')}")
    s.close()


if __name__ == "__main__":
    main()
