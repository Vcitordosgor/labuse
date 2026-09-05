"""Pré-vol M7 · P4 → CIRCUIT-1 lot 8.2 — /healthz/crons : l'état des crons lu dans les traces.

Zéro table nouvelle ; un cron sans trace le dit (« jamais_vu »), jamais un faux OK.
CIRCUIT-1 (8.2) : les cadences attendues viennent du REGISTRE des jobs (labuse.jobs.JOBS),
plus jamais d'une table à la main — l'ancienne recopiait les cadences des crons LEGACY
(bodacc quotidien / dpe « hebdo ») et contredisait le wrapper (constat CIRCUIT-0 Q3.5).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import ops


def test_82_crons_alignes_sur_le_registre_des_jobs():
    """CHAQUE entrée de healthz est un job du REGISTRE (touche l'eau + backup) ; les cadences
    en dérivent. Les anciens noms legacy (ban/dvf/abuse — sans job wrapper) ont disparu :
    leur fraîcheur de SOURCE vit sur la page Circuit (cadence 1.7 + « à vérifier » 8.4)."""
    from labuse.jobs import JOBS, TOUCHE_EAU
    attendu = (TOUCHE_EAU | {"backup-postgres"}) & set(JOBS)
    assert set(ops.CRONS) == attendu
    for nom, c in ops.CRONS.items():
        assert c["attendu_jours"] >= 1, nom
    # les mensonges de CIRCUIT-0 sont soldés : DPE mensuel (35 j), BODACC au wrapper (2 j)
    assert ops.CRONS["ingest-dpe"]["attendu_jours"] == 35
    assert ops.CRONS["ingest-bodacc"]["attendu_jours"] == 2


def test_81_legacy_marque_obsolete():
    """deploy/cron.d/ est OBSOLÈTE (fichiers conservés, OBSOLETE.md posé) ; le crontab wrapper
    est le seul jeu déployé et deploy.sh refuse tant qu'un legacy est posé."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert (root / "deploy/cron.d/OBSOLETE.md").exists()
    deploy = (root / "deploy.sh").read_text(encoding="utf-8")
    assert "labuse-*" in deploy and "retirer_crons_legacy" in deploy
    assert "Indian/Reunion" in deploy, "la conversion de fuseau (cause racine lot 0.1) est gérée"


def test_healthz_public():
    from labuse.api.auth import _PUBLIC
    assert "/healthz/crons" in _PUBLIC                    # monitoring externe sans session


@pytest.mark.db
def test_jamais_vu_honnete_et_ok_detecte(db_session):
    s = db_session
    # base de test : sitadel jamais tourné → jamais_vu (pas un faux OK)
    r = ops.healthz_crons(s)
    assert r["crons"]["ingest-sitadel"]["statut"] in ("jamais_vu", "ok")
    # seed d'un run OK récent → passe à ok avec âge
    s.execute(text("INSERT INTO ingestion_runs (commune, status, started_at, finished_at) "
                   "VALUES ('974 (SDES Sitadel3 — refresh)', 'ok', now(), now())"))
    r = ops.healthz_crons(s)
    assert r["crons"]["ingest-sitadel"]["statut"] == "ok" and r["crons"]["ingest-sitadel"]["age_jours"] < 1
    # jobs sans trace DB : l'état JSON du wrapper fait foi — absent = jamais_vu, jamais un faux OK
    assert r["crons"]["backup-postgres"]["statut"] in ("jamais_vu", "ok")
