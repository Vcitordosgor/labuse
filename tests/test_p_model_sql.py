"""PHASE 0 « Le Juge » — J1.b : fenêtres AS-OF du dataset modèle P (anti-leakage).

Le test le plus précieux du mandat : le dataset « as-of année N » ne doit contenir AUCUNE trace
d'un événement de l'année N (label) ni du futur. On caractérise le PRÉDICAT DE FENÊTRE EXACT de
`sql.build_dataset` — `date >= greatest(make_date(N-3,1,1), DVF_START) AND date < make_date(N,1,1)` —
avec les CONSTANTES RÉELLES des modules (`DVF_START` côté M3, `EXT_DVF_START` côté ext). Requête
pure (aucune écriture), transaction rollback.

(`build_dataset`/`build_ext_dataset` appellent `session.commit()` → non invoqués ici pour préserver
l'isolation ; on verrouille leur INVARIANT de fenêtre, qui est le siège de la fuite éventuelle.)
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.p_model.ext_sql import EXT_DVF_START
from labuse.scoring.p_model.sql import DVF_START

pytestmark = pytest.mark.db


def _in_window(session, mut_date: str, asof_year: int, start_const: str) -> bool:
    """Réplique EXACTEMENT la fenêtre features du dataset : [greatest(N-3, START), N)."""
    return session.execute(text(
        f"SELECT (CAST(:d AS date) >= greatest(make_date(:y - 3, 1, 1), {start_const}) "
        f"        AND CAST(:d AS date) < make_date(:y, 1, 1))"), {"d": mut_date, "y": asof_year}).scalar()


def test_asof_aucune_fuite_annee_courante_ni_futur(db_session):
    # as-of N = 2023. Une mutation de l'année N (2023, = le LABEL) ou du futur (2024) NE DOIT PAS
    # entrer dans les features (date < asof exclut asof et au-delà) → pas de fuite temporelle.
    assert _in_window(db_session, "2023-06-01", 2023, DVF_START) is False   # année courante (label)
    assert _in_window(db_session, "2024-06-01", 2023, DVF_START) is False   # futur
    # une mutation de l'année N-1 (2022) est un feature LÉGITIME (passé strict).
    assert _in_window(db_session, "2022-06-01", 2023, DVF_START) is True


def test_fenetre_bornee_dvf_start_2021(db_session):
    # DVF_START borne la fenêtre M3 au 01/01/2021 : une mutation 2020 est HORS de la fenêtre M3
    # même quand N-3 la couvrirait (as-of 2023 : N-3 = 2020, mais greatest(2020, 2021) = 2021).
    assert DVF_START == "DATE '2021-01-01'"
    assert _in_window(db_session, "2020-06-01", 2023, DVF_START) is False


def test_fenetre_ext_remonte_a_2014(db_session):
    # EXT_DVF_START remonte la fenêtre ÉTENDUE au 01/01/2014 : la MÊME mutation 2020 (as-of 2023)
    # entre dans la fenêtre ext (greatest(2020, 2014) = 2020) — la seule différence est la CONSTANTE.
    assert EXT_DVF_START == "DATE '2014-01-01'"
    assert _in_window(db_session, "2020-06-01", 2023, EXT_DVF_START) is True
    # un exemple pivot : mutation 2018, as-of 2020 → HORS M3 (bornée 2021), DANS ext (bornée 2014).
    assert _in_window(db_session, "2018-06-01", 2020, DVF_START) is False
    assert _in_window(db_session, "2018-06-01", 2020, EXT_DVF_START) is True
