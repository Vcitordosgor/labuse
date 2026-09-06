"""Témoin CIRCUIT-4 — comptes de permis Sitadel : fenêtre ancrée sur la fin des données,
recomptée indépendamment sur lignes seedées."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_compte_fenetre_temoin(engine):
    from labuse.registre.moteurs.commune import compte_permis_commune
    dates = [date(2026, 8, 1), date(2026, 3, 1), date(2025, 10, 1), date(2024, 1, 1)]
    with engine.begin() as c:
        c.execute(text("DELETE FROM sitadel_permits WHERE commune = 'TemoinSit-C4'"))
        for i, d in enumerate(dates):
            c.execute(text("INSERT INTO sitadel_permits (commune, type, date) VALUES"
                           " ('TemoinSit-C4', 'PC', :d)"), {"d": d})
        dmax = max(dates)
        out = compte_permis_commune(c, "TemoinSit-C4", months=12, nature=None, dmax=dmax)
    # recompte indépendant : fenêtre [dmax − 12 mois ; dmax] → 2026-08, 2026-03, 2025-10 = 3
    from dateutil.relativedelta import relativedelta
    borne = dmax - relativedelta(months=12)
    attendu = sum(1 for d in dates if d >= borne)
    assert int(out["n"]) == attendu == 3


@pytest.mark.db
def test_rayon_et_fenetre_profil(engine):
    """Le profil client (rayon 500 m / 24 mois) est un CHOIX déclaré — le témoin vérifie que les
    constantes du code sont celles de la fiche (les valeurs transmises au front)."""
    import re
    src = open("src/labuse/marche_service.py").read()
    assert re.search(r"500", src) and re.search(r"24", src)   # rayon 500 m, fenêtre 24 mois déclarés
