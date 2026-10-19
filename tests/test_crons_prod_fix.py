"""CRON-PROD-1 — les 6 crons que /healthz/crons voyait « en défaut » le 19/10.

Deux causes, deux correctifs, prouvés ici SANS réseau (sauf le cas DB marqué) :

1. RACINE des 5 (sonde-sources, filtres-sources, coherence-robinets, sync-gpu, backup-postgres) :
   les dossiers d'état des jobs étaient RELATIFS → résolus contre le CWD. Le cron (CWD=$HOME)
   écrivait l'état à un endroit, l'API (WorkingDirectory=/opt/labuse/app) le LISAIT à un autre
   (snapshot gelé). On ancre tout chemin relatif sur $HOME ; un chemin absolu passe inchangé.

2. GEL VOLONTAIRE (ingest-dvf, Phase 8) : il était commenté À LA MAIN dans le crontab, invisible
   du registre → /healthz/crons le comptait « jamais_vu » et faisait sonner. Le gel vit désormais
   au registre (Job.gel) : crontab commenté PAR LE GÉNÉRATEUR, healthz « gele » SANS dégrader,
   vigie « jobs en retard » qui l'ignore.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ─────────────────────────── 1. dossiers job indépendants du CWD ───────────────────────────

def test_dossier_relatif_ancre_sur_home(monkeypatch):
    """Un dossier d'état RELATIF est résolu contre $HOME (pas le CWD) : cron et API convergent."""
    from labuse import config
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", "rel/state/jobs")
    config.get_settings.cache_clear()
    try:
        s = config.get_settings()
        assert Path(s.jobs_state_dir).is_absolute()
        assert s.jobs_state_dir == str(Path.home() / "rel/state/jobs")
    finally:
        config.get_settings.cache_clear()


def test_dossier_absolu_passe_inchange(monkeypatch, tmp_path):
    """Un dossier ABSOLU (env prod explicite, tests en tmp) n'est PAS réécrit."""
    from labuse import config
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LABUSE_JOBS_LOG_DIR", "/var/log/labuse/jobs")
    config.get_settings.cache_clear()
    try:
        s = config.get_settings()
        assert s.jobs_state_dir == str(tmp_path)
        assert s.jobs_log_dir == "/var/log/labuse/jobs"
    finally:
        config.get_settings.cache_clear()


# ─────────────────────────── 2. gel volontaire au registre ───────────────────────────

def test_ingest_dvf_est_gele_au_registre():
    from labuse.jobs import JOBS
    assert JOBS["ingest-dvf"].gel == "Phase 8 Stéphanie"
    # un job gelé reste PLANIFIÉ (connu, monitoré, exécutable à la main) — c'est `gel` qui le fige.
    assert JOBS["ingest-dvf"].planifie is True


def test_gel_commente_au_crontab_mais_present():
    """Le générateur émet un job gelé en ligne COMMENTÉE (jamais lancé par cron), mais la commande
    `jobs run <nom>` reste dans la ligne (trace + les gardes « une ligne par job » restent vraies)."""
    from labuse.cli import _crontab_du_registre
    from labuse.jobs import JOBS
    c = _crontab_du_registre("utc")
    for nom, j in JOBS.items():
        if not j.gel:
            continue
        ligne = next(l for l in c.splitlines() if f"jobs run {nom}'" in l)
        assert ligne.lstrip().startswith("# GELÉ ("), f"{nom} doit être commenté GELÉ"
        assert j.gel in ligne


def test_vigie_retard_ignore_les_geles(monkeypatch):
    """La vigie « jobs en retard » (ops_alertes) ne lève jamais d'alerte sur un job gelé, même si un
    vieux succès traîne dans l'historique. On simule un dernier succès TRÈS vieux pour TOUS les jobs :
    les actifs (quotidiens) ressortent en retard, les gelés JAMAIS."""
    import datetime as _dt
    from labuse import jobs_journal, ops_alertes
    from labuse.jobs import JOBS
    vieux = _dt.datetime(2020, 1, 1, tzinfo=_dt.timezone.utc)
    monkeypatch.setattr(jobs_journal, "dernier_succes", lambda _db: {nom: vieux for nom in JOBS})
    retards = {r["nom"] for r in ops_alertes._jobs_en_retard(db=None)}
    geles = {nom for nom, j in JOBS.items() if j.gel}
    assert geles, "au moins ingest-dvf doit être gelé"
    assert not (geles & retards), f"un job gelé ne doit jamais être « en retard » : {geles & retards}"
    # garde-fou : sans gel, un quotidien très en retard DOIT être capté (preuve que le test mord)
    assert "sonde-sources" in retards


# ─────────────────────────── 3. /healthz/crons : gele ≠ alerte ───────────────────────────

def test_crons_portent_le_gel():
    """Le registre des crons surveillés expose le gel (pour que healthz ne sonne pas dessus)."""
    from labuse.api import ops
    assert ops.CRONS["ingest-dvf"]["gele"] == "Phase 8 Stéphanie"


@pytest.mark.db
def test_healthz_classe_le_gele_sans_degrader(db_session, monkeypatch, tmp_path):
    """ingest-dvf (gelé) ressort « gele » avec son motif, JAMAIS « jamais_vu » (= pas une alerte)."""
    from labuse import config
    from labuse.api import ops
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path))
    config.get_settings.cache_clear()
    try:
        r = ops.healthz_crons(db_session)
        dvf = r["crons"]["ingest-dvf"]
        assert dvf["statut"] == "gele"
        assert dvf["motif_gel"] == "Phase 8 Stéphanie"
    finally:
        config.get_settings.cache_clear()
