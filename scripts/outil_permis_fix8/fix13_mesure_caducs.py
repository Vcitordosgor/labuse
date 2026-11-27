"""OUTIL-PERMIS-FIX-13 (LOT 1) — mesure : quelles parcelles SORTENT du signal « PC caduc » avec la
nouvelle règle (échéance par DATE + décret n° 2025-461), par commune et par année d'autorisation.

Lecture seule de `labuse` : compare l'ensemble SERVI aujourd'hui (table pc_caducs) à l'ensemble que la
NOUVELLE règle produit (lecture directe sitadel + _echeance). N'écrit rien.
"""
from __future__ import annotations

import datetime as dt
import os
from collections import Counter

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.ingestion.pc_caducs import _SELECT_RAW, _echeance  # noqa: E402

REF = dt.date.today()


def main() -> int:
    with session_scope() as s:
        print(f"Base : {s.execute(text('SELECT current_database()')).scalar()} (lecture seule) · réf {REF}")
        old = set(s.execute(text("SELECT idu FROM pc_caducs")).scalars().all())
        # NOUVELLE règle, read-only : candidats octroyés-non-réalisés + échéance par date
        cand = s.execute(text(_SELECT_RAW)).mappings().all()
        new, annee_par_idu = set(), {}
        for r in cand:
            d = r["d_octroye"]
            if _echeance(d)[0] < REF:
                new.add(r["idu"])
                annee_par_idu[r["idu"]] = d.year
        sortent = old - new
        entrent = new - old
        print(f"\nSERVI (ancien) : {len(old)} · NOUVELLE règle : {len(new)}")
        print(f"SORTENT du signal : {len(sortent)} · ENTRENT : {len(entrent)}")

        # commune des parcelles qui sortent
        if sortent:
            communes = dict(s.execute(text(
                "SELECT idu, commune FROM parcels WHERE idu = ANY(:ids)"),
                {"ids": list(sortent)}).all())
            par_commune = Counter(communes.get(i, "?") for i in sortent)
            # année d'autorisation des sortantes : via la nouvelle lecture (d_octroye) quand dispo,
            # sinon via la table servie (pc_annee)
            pcann = dict(s.execute(text(
                "SELECT idu, pc_annee FROM pc_caducs WHERE idu = ANY(:ids)"), {"ids": list(sortent)}).all())
            par_annee = Counter(annee_par_idu.get(i, pcann.get(i)) for i in sortent)
            print("\n— SORTENT par commune —")
            for com, n in sorted(par_commune.items(), key=lambda x: -x[1]):
                print(f"  {com:<22} {n}")
            print("\n— SORTENT par année d'autorisation —")
            for an, n in sorted(par_annee.items(), key=lambda x: (x[0] is None, x[0])):
                print(f"  {an} : {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
