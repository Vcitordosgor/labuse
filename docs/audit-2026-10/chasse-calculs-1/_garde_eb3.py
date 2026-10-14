"""CHASSE-CALCULS-FIX-1 Lot 5 (E-B3) — GARDE : le moteur de secours ne sert AUCUN intermédiaire
impossible, et porte la mention « estimation simplifiée ».
Vérifie, sur des parcelles servies par `residuel_legacy` dont le run porte pct_potentiel > 100 % :
  · le bloc potentiel servi NE contient PLUS de pourcentage > 100 (pct_consomme None) ;
  · il porte `estimation_simplifiee=True` + une note.
Exit 0 = garde tenue.
    LABUSE_DATABASE_URL=... PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_garde_eb3.py
"""
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
from labuse import db as dbmod
from labuse.api.app import _potentiel_transformation_block


def run():
    eng = dbmod.engine()
    with Session(eng) as s:
        idus = [r[0] for r in s.execute(text(
            "SELECT p.idu FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id "
            "WHERE r.assiette_source='residuel_legacy' AND r.pct_potentiel > 100 "
            "ORDER BY r.parcel_id LIMIT 30")).all()]
        if not idus:
            print("aucune parcelle legacy > 100 % (rien à garder)"); return 0
        ok = True
        for idu in idus:
            b = _potentiel_transformation_block(s, idu) or {}
            pct = b.get("pct_consomme")
            bad = pct is not None and pct > 100           # un % impossible encore servi ?
            simpl = bool(b.get("estimation_simplifiee")) and bool(b.get("estimation_simplifiee_note"))
            good = (not bad) and simpl
            ok = ok and good
            if not good:
                print(f"  [ÉCHEC] {idu} pct_consomme={pct} simplifie={simpl}")
        print(f"testé {len(idus)} parcelles legacy > 100 %")
        print("✓ E-B3 : aucun % impossible servi, mention « estimation simplifiée » présente." if ok
              else "✗ E-B3 : au moins une parcelle sert encore un intermédiaire impossible.")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
