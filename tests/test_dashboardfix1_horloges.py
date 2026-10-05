"""DASHBOARD-FIX-1 (point 1) — le crontab posé par deploy.sh couvre les 25 horloges.

deploy.sh (ligne 62) pose `/etc/cron.d/labuse` en lançant EXACTEMENT
`labuse jobs crontab --tz <tz>` = `cli._crontab_du_registre(tz)`. Le crontab est GÉNÉRÉ depuis
le registre `labuse.jobs.JOBS` : une ligne `labuse jobs run <nom>` par job. Ce test prouve, sur
la sortie réelle de cette commande (le « dry-run » du crontab), que CHAQUE job du registre a sa
ligne — aucun absent, aucun en trop — pour les deux fuseaux que deploy.sh sait poser (utc/reunion).

Il verrouille aussi HORLOGES.csv (la liste finale du rapport) sur le registre : si un job entre ou
sort du registre, la CSV doit suivre, sinon ce test casse.
"""
from pathlib import Path

from labuse.cli import _crontab_du_registre
from labuse.jobs import JOBS

_CSV = (Path(__file__).resolve().parents[1]
        / "docs" / "audit-2026-10" / "DASHBOARD-FIX-1" / "HORLOGES.csv")


def _lignes_jobs(contenu: str) -> list[str]:
    """Les noms de job réellement lancés par le crontab (`… jobs run <nom>'`)."""
    noms = []
    for ligne in contenu.splitlines():
        if "jobs run " in ligne:
            noms.append(ligne.split("jobs run ", 1)[1].strip().rstrip("'").strip())
    return noms


def test_crontab_deploy_contient_les_25_jobs_utc():
    """Le crontab généré (tz=utc, ce que deploy.sh pose sur un serveur UTC) lance chaque job du
    registre, une fois et une seule."""
    contenu = _crontab_du_registre("utc")
    lances = _lignes_jobs(contenu)
    attendus = sorted(JOBS.keys())
    assert sorted(lances) == attendus, (
        f"crontab ≠ registre — manquants {set(attendus) - set(lances)}, "
        f"en trop {set(lances) - set(attendus)}")
    assert len(lances) == len(JOBS) == 25   # 25 horloges, aucune en double


def test_crontab_deploy_contient_les_25_jobs_reunion():
    """Même preuve pour tz=reunion (l'autre fuseau que deploy.sh sait poser) : la conversion +4 h
    ne doit perdre ni dédoubler aucun job."""
    contenu = _crontab_du_registre("reunion")
    lances = _lignes_jobs(contenu)
    assert sorted(lances) == sorted(JOBS.keys())
    assert len(lances) == len(JOBS)


def test_horloges_csv_reflete_le_registre():
    """HORLOGES.csv (rapport DASHBOARD-FIX-1) liste EXACTEMENT les jobs du registre — la liste
    finale ne peut pas diverger de ce que le crontab pose."""
    lignes = [l for l in _CSV.read_text(encoding="utf-8").splitlines() if l.strip()]
    entete, corps = lignes[0], lignes[1:]
    assert entete.split(";")[0] == "job"
    jobs_csv = sorted(l.split(";", 1)[0] for l in corps)
    assert jobs_csv == sorted(JOBS.keys())
    # chaque ligne porte la commande du wrapper (ce que lance le cron)
    for l in corps:
        nom, *_rest, commande = l.split(";")
        assert commande.strip() == f"labuse jobs run {nom}"
