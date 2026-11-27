#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-16 LOT 2 — mesure de l'impact de l'article 3 du décret n° 2025-461.

Le bénéfice des articles 1er (5 ans) et 2 (+1 an) est réservé aux autorisations ENCORE VALIDES le
27/05/2025 (jour de publication). On recompte l'échéance de chaque PC octroyé-non-réalisé avec
l'ANCIENNE règle (prorogation appliquée sans condition) et la NOUVELLE (art. 3), à la même date de
référence, et on mesure : échéances changées, parcelles qui ENTRENT / SORTENT du signal.

Lecture seule. Usage :
  LABUSE_DATABASE_URL=…  PYTHONPATH=src  python scripts/outil_permis_fix16/mesure_lot2_decret_art3.py
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion.pc_caducs import (_SELECT_RAW, _plus_annees, _echeance as new_echeance,
                                        _DECRET_P1, _DECRET_P2)

PUB = dt.date(2025, 5, 27)   # publication au JO (art. 3)


def _old_echeance(d: dt.date) -> dt.date:
    """Ancienne règle (FIX-13/14) : prorogation appliquée SANS la condition de l'art. 3."""
    if _DECRET_P1[0] <= d <= _DECRET_P1[1]:
        return _plus_annees(d, 5)
    if _DECRET_P2[0] <= d <= _DECRET_P2[1]:
        return _plus_annees(d, 4)
    return _plus_annees(d, 3)


def main() -> None:
    ref = dt.date.today()
    with session_scope() as db:
        raw = db.execute(text(_SELECT_RAW)).mappings().all()
    chg = enter = leave = both = 0
    sub195 = 0
    for r in raw:
        d = r["d_octroye"]
        eo = _old_echeance(d)
        en, _ = new_echeance(d)
        co, cn = eo < ref, en < ref
        if co and not cn:
            leave += 1
        if cn and not co:
            enter += 1
        if co and cn:
            both += 1
            if eo != en:
                chg += 1
        # sous-ensemble cité par l'audit : échéance de 4 ans (art. 2) ANTÉRIEURE à la publication
        if _DECRET_P2[0] <= d <= _DECRET_P2[1] and _plus_annees(d, 4) < PUB:
            sub195 += 1
    print(f"date de référence : {ref}")
    print(f"PC octroyé-non-réalisé (lignes sitadel)        : {len(raw)}")
    print(f"caduc avant ET après                           : {both}")
    print(f"échéances CHANGÉES (date)                      : {chg}")
    print(f"  dont sous-ensemble audit (4 ans < 27/05/2025): {sub195}")
    print(f"parcelles qui ENTRENT dans le signal           : {enter}")
    print(f"parcelles qui SORTENT du signal                : {leave}")


if __name__ == "__main__":
    main()
