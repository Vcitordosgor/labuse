"""AUTONOMIE-1 — les trois jobs de nuit sont AU REGISTRE (source unique) avec une planif cohérente."""
from labuse.jobs import JOBS, prochaine


def _job(nom):
    assert nom in JOBS, f"{nom} absent du registre"
    return JOBS[nom]


def test_calcul_nuit_au_registre():
    j = _job("calcul-nuit")
    assert j.planifie and not j.gel
    assert j.heure_reunion == "02:00"           # dans la fenêtre 01h-05h
    assert j.timeout_s >= 4 * 3600              # budget couvrant la fenêtre de nuit
    assert prochaine(j.cron_utc) is not None    # cron parseable


def test_injection_nuit_au_registre():
    j = _job("injection-nuit")
    assert j.planifie and not j.gel
    assert j.heure_reunion == "01:00"           # AVANT le calcul (feed le déclencheur)
    assert j.touche == "eau"                    # elle injecte de la donnée


def test_restore_test_au_registre():
    j = _job("restore-test")
    assert j.planifie and not j.gel
    assert j.cadence.startswith("mensuel")
    assert prochaine(j.cron_utc) is not None


def test_resume_matin_au_registre():
    """OPS-NUIT-1 — le résumé du matin est un job quotidien, à mail, lancable à la main, après la nuit."""
    j = _job("resume-matin")
    assert j.planifie and not j.gel
    assert j.cadence == "quotidien" and j.heure_reunion == "07:30"   # après verrous 07:25 + Radar de nuit
    assert j.envoie_mail and j.touche == "exploitation"
    assert prochaine(j.cron_utc) is not None
    from labuse.jobs import _FAMILLE_LIBELLE_ROLE
    assert _FAMILLE_LIBELLE_ROLE["resume-matin"][3] is True          # lancable (lecture seule, sans risque)


def test_les_trois_ont_une_famille():
    from labuse import jobs
    fam = {d["nom"]: d["famille"] for d in jobs.liste()}
    assert fam["injection-nuit"] == 2 and fam["calcul-nuit"] == 3 and fam["restore-test"] == 4


def test_pointeurs_run_coherents_dans_le_depot():
    """AUTONOMIE-1 — les 3 pointeurs (manifeste / served_run.txt / servi) sont cohérents dans le dépôt
    (q_v20 partout), et `pointeurs()` les expose avec un drapeau `coherents`."""
    from labuse import runs
    p = runs.pointeurs()
    assert set(p) >= {"env_override", "manifeste", "served_run_txt", "servi", "coherents", "divergence"}
    assert p["coherents"] is True and p["divergence"] is None
