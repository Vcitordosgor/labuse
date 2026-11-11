"""FRAICHEUR-FIX-1 (point 8) — un déploiement qui réécrit le crontab RATTRAPE les tâches du jour
qu'il a fait sauter (ex. 10/11 : 00:00→05:08 Réunion sautés). Idempotent : un job déjà passé n'est
pas relancé ; un sous-horaire (15 min) se rattrape seul et n'est pas rejoué."""
from datetime import datetime, timezone

from labuse import jobs as jobs_mod


def _utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def test_taches_a_rattraper_cible_les_crons_passes_non_tournes():
    # Le 10/11/2026, déploiement à 01:08 UTC (05:08 Réunion). Fenêtre du jour Réunion = depuis
    # 2026-11-09 20:00 UTC (minuit Réunion). « now » = l'instant du déploiement.
    now = _utc(2026, 11, 10, 1, 8)
    depuis = _utc(2026, 11, 9, 20, 0)   # minuit Réunion = 20:00 UTC la veille

    # ingest-dvf : mardi 05:00 Réunion = 01:00 UTC mardi (10/11/2026 est un mardi) → prévu 01:00 UTC,
    # jamais tourné aujourd'hui → À RATTRAPER.
    # ingest-sitadel : le 10 à 04:30 Réunion = 00:30 UTC → À RATTRAPER.
    # injection-nuit : 01:00 Réunion = 21:00 UTC la veille → dans la fenêtre → À RATTRAPER.
    # ingest-bodacc : 06:40 Réunion = 02:40 UTC → APRÈS le déploiement (02:40 > 01:08) → PAS sauté.
    etats = {nom: None for nom in jobs_mod.JOBS}
    # ingest-bodacc a bien tourné ce matin après le deploy → début récent, ne doit pas ressortir.
    etats["ingest-bodacc"] = _utc(2026, 11, 10, 2, 40)

    a_faire = dict(jobs_mod.taches_a_rattraper(now, depuis, etats))
    assert "ingest-dvf" in a_faire
    assert "ingest-sitadel" in a_faire
    assert "injection-nuit" in a_faire
    assert "ingest-bodacc" not in a_faire          # prévu APRÈS le déploiement → pas sauté
    assert "healthcheck" not in a_faire            # sous-horaire (15 min) : se rattrape seul
    assert "mail-queue-consommer" not in a_faire   # sous-horaire (5 min)


def test_idempotent_un_job_deja_passe_nest_pas_rejoue():
    now = _utc(2026, 11, 10, 1, 8)
    depuis = _utc(2026, 11, 9, 20, 0)
    etats = {nom: None for nom in jobs_mod.JOBS}
    # ingest-sitadel a DÉJÀ tourné aujourd'hui après son créneau (00:30 UTC) → ne pas rejouer.
    etats["ingest-sitadel"] = _utc(2026, 11, 10, 0, 35)
    a_faire = dict(jobs_mod.taches_a_rattraper(now, depuis, etats))
    assert "ingest-sitadel" not in a_faire


def test_rattraper_relance_dans_lordre_et_njoue_que_le_saute(monkeypatch):
    lances: list[str] = []
    monkeypatch.setattr(jobs_mod, "lire_etat", lambda nom: None)   # rien n'a tourné aujourd'hui
    out = jobs_mod.rattraper(now=_utc(2026, 11, 10, 1, 8),
                             executer=lambda nom: lances.append(nom) or 0,
                             log=lambda *_: None)
    # au moins les trois crons de nuit sautés, et dans l'ordre chronologique des créneaux
    assert "ingest-sitadel" in lances and "ingest-dvf" in lances and "injection-nuit" in lances
    assert lances == out["a_rattraper"]
    assert "healthcheck" not in lances and "mail-queue-consommer" not in lances
