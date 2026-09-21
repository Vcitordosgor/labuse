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
    """CRON-1 lot 0 (table rase) — `deploy/cron.d/` (legacy + OBSOLETE.md) et `deploy/cron.d-labuse`
    sont SUPPRIMÉS. La garde deploy.sh (génère le crontab du registre, retire tout legacy
    `/etc/cron.d/labuse-*` hors registre) est reconstruite au lot 3. Neutralisé en attendant."""
    import pytest
    pytest.skip("CRON-1 lot 0 : artefacts crontab supprimés ; garde deploy.sh reconstruite au lot 3")


def test_healthz_public():
    from labuse.api.auth import _PUBLIC
    assert "/healthz/crons" in _PUBLIC                    # monitoring externe sans session


@pytest.mark.db
def test_jamais_vu_honnete_et_ok_detecte(db_session, monkeypatch, tmp_path):
    # TESTS-0 — HERMÉTIQUE. Le test dépendait de l'état AMBIANT et échouait selon la machine : un run
    # sitadel « ok » DÉJÀ committé dans labuse_test (par une autre suite) OU un fichier d'état
    # `<jobs_state_dir>/backup-postgres.json` présent (backups réels du poste dev) donnaient « en_retard »
    # — un statut honnête mais hors de ("jamais_vu","ok"). On repart d'un état VIERGE : répertoire d'états
    # de jobs vide (tmp) + aucune trace sitadel. jamais_vu redevient déterministe et prouvable honnête.
    from labuse import config
    s = db_session
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path))   # aucun état JSON de job
    config.get_settings.cache_clear()
    s.execute(text("DELETE FROM ingestion_runs WHERE commune LIKE '974 (SDES Sitadel3%'"))
    try:
        # sitadel jamais tourné → jamais_vu (pas un faux OK)
        r = ops.healthz_crons(s)
        assert r["crons"]["ingest-sitadel"]["statut"] == "jamais_vu"
        # seed d'un run OK récent → passe à ok avec âge < 1
        s.execute(text("INSERT INTO ingestion_runs (commune, status, started_at, finished_at) "
                       "VALUES ('974 (SDES Sitadel3 — refresh)', 'ok', now(), now())"))
        r = ops.healthz_crons(s)
        assert r["crons"]["ingest-sitadel"]["statut"] == "ok" and r["crons"]["ingest-sitadel"]["age_jours"] < 1
        # job sans trace DB : l'état JSON du wrapper fait foi — absent (tmp vide) = jamais_vu, jamais un faux OK
        assert r["crons"]["backup-postgres"]["statut"] == "jamais_vu"
    finally:
        config.get_settings.cache_clear()
