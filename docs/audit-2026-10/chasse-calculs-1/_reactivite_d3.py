"""CHASSE-CALCULS-1 — D3 : réactivité à un changement de donnée (TRANSACTION ANNULÉE, rollback).

Audit (passe 2) : après +10 000 m² de contenance, la SDP (run gelé) ne bougeait pas ET un même
Dossier mêlait surface fraîche + SDP périmée (ratio faux), le cache de fiche servant du périmé.

FIX CHASSE-CALCULS-FIX-1 Lot 3 (E-B1) — GARDE : rejoué, le scénario ne produit PLUS de ratio faux :
  1. le run enregistre sa surface (`parcel_residuel.surface_terrain_m2`) ;
  2. la fiche sert la SDP AVEC la surface du run, et DIT si la surface vive a changé (note datée) ;
  3. la clé du cache de fiche inclut un jeton PAR PARCELLE (updated_at + contenance) → invalidée
     dès qu'une parcelle change.
Tout est mesuré en-process sur le bloc potentiel (rapide) + la clé de cache ; aucune écriture durable.
    LABUSE_DATABASE_URL=... PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_reactivite_d3.py
"""
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
from labuse import db as dbmod
from labuse.api.app import _potentiel_transformation_block

IDU = "97412000BV0419"   # St-Joseph U2, constructible


def jeton_cache(s, idu):
    """Le jeton PAR PARCELLE ajouté à la clé du cache de fiche (app.py) : updated_at + contenance."""
    return s.execute(text(
        "SELECT to_char(updated_at,'YYYYMMDDHH24MISSUS')||':'||coalesce(contenance_m2::text,'-') "
        "FROM parcels WHERE idu=:i"), {"i": idu}).scalar()


def run():
    eng = dbmod.engine()
    conn = eng.connect(); tr = conn.begin(); s = Session(bind=conn)   # transaction ANNULÉE
    ok = True
    try:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": IDU}).scalar()
        rs = s.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
        base = s.execute(text("SELECT contenance_m2 FROM parcels WHERE idu=:i"), {"i": IDU}).scalar()
        # simule un run backfillé (surface du run = contenance au calcul)
        s.execute(text("UPDATE parcel_residuel_runs SET surface_terrain_m2=:c WHERE run_seq=:r AND parcel_id=:p"),
                  {"c": base, "r": rs, "p": pid})
        j0 = jeton_cache(s, IDU)
        b0 = _potentiel_transformation_block(s, IDU)
        sdp0 = b0.get("sdp_residuelle_m2")
        print(f"[avant] contenance={base}  SDP={sdp0}  surf_calcul={b0.get('surface_calcul_m2')} "
              f"surf_actuelle={b0.get('surface_actuelle_m2')}  note={b0.get('surface_calcul_note')}")

        s.execute(text("UPDATE parcels SET contenance_m2=contenance_m2+10000 WHERE id=:p"), {"p": pid})
        j1 = jeton_cache(s, IDU)
        b1 = _potentiel_transformation_block(s, IDU)
        print(f"[après +10000] SDP={b1.get('sdp_residuelle_m2')}  surf_calcul={b1.get('surface_calcul_m2')} "
              f"surf_actuelle={b1.get('surface_actuelle_m2')}")
        print(f"  NOTE: {b1.get('surface_calcul_note')}")

        # GARDES
        g1 = j1 != j0
        g2 = b1.get("sdp_residuelle_m2") == sdp0                      # SDP reste sur le run (gelée)
        g3 = b1.get("surface_calcul_m2") == base                     # surface servie = surface du run
        g4 = b1.get("surface_actuelle_m2") == base + 10000           # surface vive dite à côté
        g5 = bool(b1.get("surface_calcul_note"))                     # l'écart est DIT → pas de ratio muet
        print("\nGARDES E-B1 :")
        print(f"  clé cache change au changement de parcelle : {'OK' if g1 else 'ÉCHEC'}")
        print(f"  SDP servie reste celle du run (gelée)       : {'OK' if g2 else 'ÉCHEC'}")
        print(f"  surface affichée = surface du run           : {'OK' if g3 else 'ÉCHEC'}")
        print(f"  surface vive dite à côté                    : {'OK' if g4 else 'ÉCHEC'}")
        print(f"  écart surface DIT (pas de ratio faux muet)  : {'OK' if g5 else 'ÉCHEC'}")
        ok = all([g1, g2, g3, g4, g5])
    finally:
        tr.rollback(); conn.close()
        chk = eng.connect().execute(text("SELECT contenance_m2 FROM parcels WHERE idu=:i"), {"i": IDU}).scalar()
        print(f"\nrollback OK — contenance en base = {chk} (inchangée)")
    print("\n✓ E-B1 fermé : le scénario D3 ne produit plus de ratio faux." if ok
          else "\n✗ E-B1 : au moins une garde a échoué.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
