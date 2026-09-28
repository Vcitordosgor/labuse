"""COHERENCE-FIX-1 (lot B) — recalcul CHIRURGICAL des lignes plafonnées « 999 » du run servi.

Le plafond `min(999, …)` (residuel.py, retiré par ce mandat) a écrit 999 dans
`parcel_residuel_runs` pour 2 304 taux et 4 302 pct du run servi (seq 10) : la valeur exacte
est PERDUE en base (emprise_max/sdp_max ne sont stockés nulle part). On la recalcule avec le
MOTEUR (compute_residuel, désormais non plafonné) pour CES parcelles seulement — ni run île,
ni bascule : un UPDATE des deux colonnes mensongères, le reste de la ligne inchangé.

    python -m scripts.coherence.fix_999_seq10 [seq]
"""
from __future__ import annotations

import sys
import time

from sqlalchemy import text


def main(seq: int = 10) -> None:
    from labuse.db import session_factory
    from labuse.faisabilite.residuel import compute_residuel

    db = session_factory()()
    ids = [r[0] for r in db.execute(text(
        "SELECT parcel_id FROM parcel_residuel_runs WHERE run_seq = :s "
        "AND (taux_emprise_pct = 999 OR pct_potentiel = 999) ORDER BY parcel_id"),
        {"s": seq}).all()]
    print(f"{len(ids)} parcelles à recalculer (run seq {seq})")
    t0 = time.time()
    maj = indispo = 0
    for i, pid in enumerate(ids):
        try:
            res = compute_residuel(db, pid)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ parcel {pid}: {e}")
            db.rollback()
            continue
        if not res.get("disponible"):
            # le moteur d'aujourd'hui ne calcule plus cette parcelle (données amont ayant bougé) :
            # on NE touche PAS la ligne du run (pas de réécriture d'histoire), on le compte.
            indispo += 1
            continue
        db.execute(text(
            "UPDATE parcel_residuel_runs SET taux_emprise_pct = :t, pct_potentiel = :p "
            "WHERE run_seq = :s AND parcel_id = :pid"),
            {"t": res.get("taux_emprise_pct"), "p": res.get("pct_potentiel"),
             "s": seq, "pid": pid})
        maj += 1
        if (i + 1) % 500 == 0:
            db.commit()
            print(f"  {i+1}/{len(ids)} ({time.time()-t0:.0f}s)")
    db.commit()
    n999 = db.execute(text(
        "SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=:s "
        "AND (taux_emprise_pct = 999 OR pct_potentiel = 999)"), {"s": seq}).scalar()
    print(f"✓ {maj} mises à jour, {indispo} laissées (indisponibles au moteur du jour), "
          f"reste {n999} lignes à 999 · {time.time()-t0:.0f}s")
    db.close()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
