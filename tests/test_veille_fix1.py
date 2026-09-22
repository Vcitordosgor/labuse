"""VEILLE-FIX-1 — les veilles tournent, et ne préviennent que qui est concerné.

Tests PURS (pas de base réelle requise pour la plupart) : registre des jobs, verrou V8a, ciblage
Radar, essai expiré, cloche d'un compte neuf, trace mail_queue. Marque `verrous` non posée : ces
tests tournent partout (le circuit joué sur base réelle est dans le rapport, pas ici)."""
from __future__ import annotations

import inspect

from labuse.jobs import JOBS


# ─────────────────────────── LOT 1 — le registre ───────────────────────────

def test_les_quatre_jobs_veille_existent():
    """Les quatre fonctions que le registre ne portait pas ont chacune un job, à leur créneau matinal,
    et leur impl appelle vraiment la fonction d'évaluation/envoi."""
    from labuse import jobs_impl
    attendu = {
        "evaluer-suivis":  ("2 3 * * *",  "evaluer_suivis",        "evaluer_suivis"),
        "evaluer-secteurs":("3 3 * * *",  "evaluer_secteurs",      "evaluer_tous_secteurs"),
        "detect-events":   ("4 3 * * *",  "detect_events",         "detect_events"),
        "digest":          ("15 3 * * *", "digest",                "envoyer_digests"),
    }
    for nom, (cron, impl, fonction) in attendu.items():
        assert nom in JOBS, f"job « {nom} » absent du registre"
        j = JOBS[nom]
        assert j.cron_utc == cron, f"{nom} : {j.cron_utc!r} != {cron!r}"
        assert j.cadence == "quotidien" and j.touche == "exploitation"
        fn = getattr(jobs_impl, impl, None)
        assert fn is not None, f"impl jobs_impl.{impl} absente"
        assert fonction in inspect.getsource(fn), f"jobs_impl.{impl} n'appelle pas {fonction}"


def test_digest_envoie_mail_les_evaluateurs_non():
    """Le digest est le seul des quatre qui envoie un mail (règle dry-run) ; les trois évaluateurs non."""
    assert JOBS["digest"].envoie_mail is True
    for nom in ("evaluer-suivis", "evaluer-secteurs", "detect-events"):
        assert JOBS[nom].envoie_mail is False


def test_les_quatre_jobs_au_crontab_genere():
    """Le crontab GÉNÉRÉ depuis le registre porte une ligne pour chacun des quatre jobs (sinon retirer
    le legacy éteindrait la fonction sans équivalent posé)."""
    from labuse.cli import _crontab_du_registre
    crontab = _crontab_du_registre("reunion")
    for nom in ("evaluer-suivis", "evaluer-secteurs", "detect-events", "digest"):
        assert f"jobs run {nom}'" in crontab, f"{nom} absent du crontab généré"


# ─────────────────────────── LOT 1 — verrou V8a ───────────────────────────

def test_v8a_vert():
    """V8a est vert : toute fonction de veille/envoi a un job du registre qui l'appelle."""
    from labuse.circuit_verrous import verrou_veille_a_un_job
    r = verrou_veille_a_un_job(None)
    assert r.verdict == "ok", f"V8a cassé : {r.preuve} — {r.details}"


def test_v8a_casse_si_un_job_est_retire(monkeypatch):
    """Preuve que V8a MORD : retirer un job de veille du registre le fait casser."""
    import labuse.jobs as jobs_mod
    from labuse.circuit_verrous import verrou_veille_a_un_job
    amputé = {k: v for k, v in jobs_mod.JOBS.items() if k != "digest"}
    monkeypatch.setattr(jobs_mod, "JOBS", amputé)
    r = verrou_veille_a_un_job(None)
    assert r.verdict == "casse", "V8a aurait dû casser sans le job digest"
    assert any("digest" in d for d in r.details)
