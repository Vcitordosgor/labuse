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

def test_ingest_dvf_degele_le_20_10():
    """DÉGEL prod 20/10 : ingest-dvf n'est PLUS gelé (gel=None) → job actif, planifié, surveillé
    comme un job normal. Le mécanisme de gel reste exercé par les autres jobs Phase 8 (digest,
    radar-*, restore-test)."""
    from labuse.jobs import JOBS
    assert JOBS["ingest-dvf"].gel is None
    assert JOBS["ingest-dvf"].planifie is True
    assert any(j.gel for j in JOBS.values()), "le mécanisme de gel reste utilisé par d'autres jobs"


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
    assert geles, "au moins un job Phase 8 (digest, radar-*, restore-test) doit être gelé"
    assert not (geles & retards), f"un job gelé ne doit jamais être « en retard » : {geles & retards}"
    # garde-fou : sans gel, un quotidien très en retard DOIT être capté (preuve que le test mord)
    assert "sonde-sources" in retards


# ─────────────────────────── 3. /healthz/crons : gele ≠ alerte ───────────────────────────

def test_ingest_dvf_degel_propage_au_healthz():
    """Le registre healthz (ops.CRONS) DÉRIVE le gel du registre JOBS → le dégel d'ingest-dvf
    (jobs.py, prod 20/10) se propage automatiquement : plus aucun gel côté crons surveillés."""
    from labuse.api import ops
    assert ops.CRONS["ingest-dvf"]["gele"] is None


@pytest.mark.db
def test_healthz_classe_un_gele_sans_degrader(db_session, monkeypatch, tmp_path):
    """La LOGIQUE healthz « gele » (ne sonne jamais sur un cron volontairement gelé) reste exercée :
    on injecte un cron gelé dans le registre surveillé → statut='gele' + motif, jamais 'jamais_vu'.
    ingest-dvf, DÉGELÉ le 20/10, ressort désormais surveillé normalement (plus « gele »)."""
    from labuse import config
    from labuse.api import ops
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path))
    monkeypatch.setitem(ops.CRONS, "cron-gele-test",
                        {"trace": "etat_json", "motif": None, "attendu_jours": 9,
                         "gele": "Phase 8 test", "note": "cron de test gelé"})
    config.get_settings.cache_clear()
    try:
        r = ops.healthz_crons(db_session)
        gele = r["crons"]["cron-gele-test"]
        assert gele["statut"] == "gele"
        assert gele["motif_gel"] == "Phase 8 test"
        assert r["crons"]["ingest-dvf"]["statut"] != "gele"   # dégelé → surveillé comme un job normal
    finally:
        config.get_settings.cache_clear()
