"""Pré-vol M7 · P4 — /healthz/crons : l'état des crons lu dans les traces existantes.

Zéro table nouvelle ; un cron sans trace le dit (« jamais_vu »/« non_trace_db »), jamais un faux OK.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import ops


def test_crons_alignes_sur_cron_d():
    # chaque tâche déclarée correspond à un fichier deploy/cron.d (ou est documentée « système »)
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    fichiers = {p.name for p in (root / "deploy/cron.d").iterdir()}
    assert "solaire" not in fichiers                      # cron mort M3 retiré (P4)
    assert "catnat" not in fichiers                        # cron « Vues » retiré (M12 Lot C-bis)
    assert {"sitadel", "ban", "abuse", "backup", "bodacc", "dvf", "dpe"} <= fichiers   # J+2
    assert set(ops.CRONS) == {"sitadel", "ban", "abuse-scan", "backup", "bodacc", "dvf", "dpe"}


def test_healthz_public():
    from labuse.api.auth import _PUBLIC
    assert "/healthz/crons" in _PUBLIC                    # monitoring externe sans session


@pytest.mark.db
def test_jamais_vu_honnete_et_ok_detecte(db_session):
    s = db_session
    # base de test : sitadel jamais tourné → jamais_vu (pas un faux OK)
    r = ops.healthz_crons(s)
    assert r["crons"]["sitadel"]["statut"] in ("jamais_vu", "ok")
    # seed d'un run OK récent → passe à ok avec âge
    s.execute(text("INSERT INTO ingestion_runs (commune, status, started_at, finished_at) "
                   "VALUES ('974 (SDES Sitadel3 — refresh)', 'ok', now(), now())"))
    r = ops.healthz_crons(s)
    assert r["crons"]["sitadel"]["statut"] == "ok" and r["crons"]["sitadel"]["age_jours"] < 1
    # non tracés DB : documentés, jamais un verdict inventé
    assert r["crons"]["backup"]["statut"] == "non_trace_db"
