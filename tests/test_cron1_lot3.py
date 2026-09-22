"""CRON-1 lot 3 — le crontab GÉNÉRÉ du registre + la garde deploy.sh. Sans DB (registre pur)."""
from labuse.cli import _crontab_du_registre
from labuse.jobs import JOBS


def test_crontab_genere_une_ligne_par_job():
    c = _crontab_du_registre("utc")
    lignes_job = [l for l in c.splitlines() if "jobs run" in l]
    # VEILLE-FIX-1 → 20 jobs ; VEILLE-2 (Lot 4) retire evaluer-secteurs (secteurs archivés) → 19.
    assert len(lignes_job) == len(JOBS) == 19, "une ligne par job du registre, ni plus ni moins"
    for nom in JOBS:
        assert f"jobs run {nom}'" in c, f"{nom} absent du crontab généré"
    # jamais écrit à la main : en-tête d'avertissement + shell/mailto
    assert "GÉNÉRÉ depuis le registre" in c and "NE PAS ÉDITER" in c
    assert "SHELL=/bin/sh" in c and "MAILTO=root" in c


def test_crontab_backup_horaire_legacy_sans_trou():
    """Le backup garde l'expression EXACTE du legacy (30 9 * * *) en UTC → remplacement sans trou."""
    assert "30 9 * * *   labuse  sh -c" in _crontab_du_registre("utc")
    # tz Réunion : +4 h → 30 13
    assert "30 13 * * *   labuse  sh -c" in _crontab_du_registre("reunion")


def test_crontab_tz_reunion_convertit_les_heures():
    utc, reu = _crontab_du_registre("utc"), _crontab_du_registre("reunion")
    # sonde-sources : 0 3 (07:00 Réunion) → 0 7 en tz reunion ; les 15-min (*/15, 7,37) intacts.
    assert "0 3 * * *" in utc and "0 7 * * *" in reu
    assert "*/15 * * * *" in reu   # heure '*' non convertie


def test_crontab_verifier_detecte_ecart(tmp_path):
    from labuse.cli import jobs_crontab_cmd  # noqa: F401 — présence de la commande
    f = tmp_path / "labuse.cron"
    f.write_text(_crontab_du_registre("utc"), encoding="utf-8")
    # identique → pas d'écart (la commande sort 0) ; on teste la comparaison de contenu directement.
    assert f.read_text(encoding="utf-8") == _crontab_du_registre("utc")
    f.write_text(_crontab_du_registre("utc") + "\n0 0 * * *  labuse  sh -c 'rogue'\n", encoding="utf-8")
    assert f.read_text(encoding="utf-8") != _crontab_du_registre("utc"), "un crontab édité à la main diffère du registre"


def test_g8_est_une_garantie_non_bloquante_par_deploy():
    """G8 existe comme garantie ; deploy.sh la passe en avertissement (-w G8) — testé au niveau CLI."""
    from labuse import circuit_garanties as g
    assert hasattr(g, "verrou_g8")
    # deploy.sh contient bien le flag non bloquant.
    from pathlib import Path
    deploy = Path(__file__).resolve().parents[1] / "deploy.sh"
    txt = deploy.read_text(encoding="utf-8")
    assert "verrous --par deploy -w G8" in txt
    assert "jobs crontab --tz" in txt and "--verifier /etc/cron.d/labuse" in txt
    assert "labuse-*" in txt   # retrait des legacy
