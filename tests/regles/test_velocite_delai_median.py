"""Témoin CIRCUIT-4 — vélocité : la médiane percentile_cont recomparée à une implémentation
indépendante (statistics.median) sur lignes seedées (delai_mois est un ENTIER en base)."""
from __future__ import annotations

import statistics

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_mediane_temoin(engine):
    delais = [3, 5, 8, 13]
    with engine.begin() as c:
        c.execute(text("DELETE FROM m10_permit_delais WHERE commune = 'TemoinVel-C4'"))
        for i, d in enumerate(delais):
            c.execute(text(
                "INSERT INTO m10_permit_delais (permit_id, commune, delai_mois, valide, famille)"
                " VALUES (:p, 'TemoinVel-C4', :d, true, 'logements')"),
                {"p": f"c4vel{i}", "d": d})
        # un invalide et un hors-famille NE comptent PAS (mêmes WHERE que le moteur)
        c.execute(text("INSERT INTO m10_permit_delais (permit_id, commune, delai_mois, valide,"
                       " famille) VALUES ('c4velx', 'TemoinVel-C4', 99, false, 'logements')"))
        c.execute(text("INSERT INTO m10_permit_delais (permit_id, commune, delai_mois, valide,"
                       " famille) VALUES ('c4vely', 'TemoinVel-C4', 99, true, 'locaux')"))
        med = c.execute(text(
            "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois)"
            " FROM m10_permit_delais WHERE commune = 'TemoinVel-C4' AND valide"
            " AND famille = 'logements' AND delai_mois >= 0")).scalar()
        c.execute(text("DELETE FROM m10_permit_delais WHERE commune = 'TemoinVel-C4'"))
    # recalcul indépendant : médiane interpolée de [3,5,8,13] = (5+8)/2 = 6,5
    assert float(med) == statistics.median(delais) == 6.5
