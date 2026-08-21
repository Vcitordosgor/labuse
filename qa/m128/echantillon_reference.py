"""M128 — ÉCHANTILLON DE RÉFÉRENCE UNIQUE (M128-ECH-1) + deux compteurs.

Toute mesure du chantier M128 s'y réfère (fini les 374/423/150 lus comme une série).

Définition (reproductible) :
  · identifiant  : M128-ECH-1
  · critère      : toutes les parcelles de la base (constructibles filtrées à l'usage)
  · tirage       : PostgreSQL setseed(0.128) puis ORDER BY random()
  · taille       : 400 parcelles tirées ; sous-ensemble constructible mesuré
  · seed         : 0.128 (fixe)

Compteurs rejoués :
  A) part de parcelles à MARGE POSITIVE (méthode documents : compute_bilan − prix probable)
  B) part de « vendable > gabarit × 0,8 »

Usage : LABUSE_DATABASE_URL=... .venv311/bin/python qa/m128/echantillon_reference.py
"""
import sys
sys.path.insert(0, "src")
from labuse.db import session_scope                      # noqa: E402
from labuse.faisabilite.db import parcel_faisabilite     # noqa: E402
from labuse.faisabilite.bilan import compute_bilan_servi  # noqa: E402
from sqlalchemy import text                              # noqa: E402

SEED = 0.128
TAILLE = 400


def echantillon(db):
    db.execute(text("SELECT setseed(:s)"), {"s": SEED})
    return [r[0] for r in db.execute(
        text("SELECT id FROM parcels ORDER BY random() LIMIT :n"), {"n": TAILLE}).all()]


def main():
    with session_scope() as db:
        ids = echantillon(db)
        n = pos = over = 0
        for pid in ids:
            try:
                fa = parcel_faisabilite(db, pid)
                if not fa:
                    continue
                fo = fa[1].fourchette or {}
                v, sp = fo.get("shab_vendable_m2"), fo.get("surface_plancher_m2")
                if not (v and sp and sp > 0):
                    continue
                n += 1
                if v - sp * 0.8 > 0.5:
                    over += 1
                b, ps = compute_bilan_servi(db, pid, fa)
                if b is None or (ps or {}).get("non_calculable"):
                    continue
                charge = (b.charge_fonciere or {}).get("central")
                se = db.execute(text(
                    "SELECT prix_probable FROM score_e WHERE idu=(SELECT idu FROM parcels WHERE id=:p)"),
                    {"p": pid}).scalar()
                if charge is not None and se is not None and (charge - se) > 0:
                    pos += 1
            except Exception:  # noqa: BLE001
                pass
        print(f"M128-ECH-1 (seed {SEED}, {TAILLE} tirées) — constructibles mesurés : {n}")
        print(f"  A) marge positive (documents) : {pos} ({100 * pos / max(n, 1):.1f}%)")
        print(f"  B) vendable > gabarit x0.8     : {over} ({100 * over / max(n, 1):.1f}%)")


if __name__ == "__main__":
    main()
