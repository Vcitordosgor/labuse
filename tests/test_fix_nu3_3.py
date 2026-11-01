"""FIX-NU3-3 — RECETTE d'exploitation : surveillance des jobs, sauvegardes, chaîne des données, charge.

Les scénarios du mandat, en tests déterministes :
  · un job BLOQUÉ (tué en plein run) et un job JAMAIS réussi apparaissent « en retard » ;
  · une source AVANCÉE se voit (millésime composé) — fiche ET PDF lisent la même valeur ;
  · les files d'attente (PDF ×2, plafond d'études) bornent bien la concurrence.
La preuve de charge « 25 users, fiche & carte < 1 s » est jouée hors-test (API bootée) et consignée
dans le compte-rendu ; ici on prouve le MÉCANISME (les sémaphores plafonnent).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.db


# ───────────────────────── jobs : bloqué / jamais réussi (I-ADM-01/03, L-JOB-01) ─────────────────────────

def test_bloque_depuis_pur():
    from labuse.jobs import bloque_depuis
    vieux = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    frais = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    # en_cours depuis plus que timeout + marge → bloqué (timeout 120 s → grace 420 s < 2 h)
    assert bloque_depuis("en_cours", vieux, 120) is not None
    # en_cours récent (sous la marge) → pas bloqué (run légitimement en cours)
    assert bloque_depuis("en_cours", frais, 120) is None
    # un état terminal n'est jamais « bloqué »
    assert bloque_depuis("ok", vieux, 120) is None
    assert bloque_depuis("echec", vieux, 120) is None


def test_jobs_en_retard_bloque_et_jamais(db_session, monkeypatch, tmp_path):
    """Un job gelé (volontairement mis en état « en_cours » figé) ET un job jamais lancé apparaissent
    en retard — exactement la recette du mandat."""
    from labuse import config, jobs, jobs_journal, ops_alertes

    # état des jobs dans un dossier jetable (ne pas polluer le dépôt)
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path / "state"))
    config.get_settings.cache_clear()

    jobs_journal.ensure_table(db_session)
    now = datetime.now(timezone.utc)

    # le système « vit depuis » 3 jours (un vieux passage, peu importe lequel) → les quotidiens jamais
    # réussis sont en retard. Et un job A a un succès RÉCENT → il ne doit PAS être en retard.
    jobs_journal.enregistrer(db_session, {"nom": "sonde-sources", "statut": "ok",
                                          "debut": (now - timedelta(days=3)).isoformat(),
                                          "fin": (now - timedelta(minutes=10)).isoformat()})

    # job B « tué en plein run » : état en_cours figé il y a 2 h (healthcheck timeout 120 s → bloqué)
    jobs._ecrire_etat("healthcheck", {"nom": "healthcheck", "statut": "en_cours",
                                      "debut": (now - timedelta(hours=2)).isoformat()})

    retards = {r["nom"]: r for r in ops_alertes._jobs_en_retard(db_session)}
    config.get_settings.cache_clear()

    # bloqué : healthcheck, motif « bloque »
    assert "healthcheck" in retards and retards["healthcheck"]["motif"] == "bloque"
    # jamais réussi : un quotidien sans aucun succès (backup-postgres) → motif « jamais »
    assert "backup-postgres" in retards and retards["backup-postgres"]["motif"] == "jamais"
    # le job à succès récent n'est PAS en retard
    assert "sonde-sources" not in retards
    # un job GELÉ (purge-runs) n'est jamais compté (gel volontaire)
    assert "purge-runs" not in retards


def test_pastille_bloque_rouge_partout():
    """Le même job bloqué est dit BLOQUÉ (rouge) dans les trois lecteurs (tuiles, usine, résumé)."""
    from labuse import cockpit_resume as ck
    vieux = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job = {"nom": "x", "gel": None, "timeout_s": 120,
           "dernier": {"statut": "en_cours", "debut": vieux}}
    assert ck._job_bloque(job) is True
    assert ck._pastille_job(job) == "rouge"
    assert ck._pastille_poste(job, set()) == "rouge"          # pas « violet » à vie
    resume = ck._resume_usine([job])
    assert resume["echec"] == 1 and resume["arret"] == 0       # bloqué compte en échec, pas « à l'arrêt »


# ───────────────────────── sauvegardes : fraîcheur + escalade (K-SAV + Vic) ─────────────────────────

def test_vigie_sauvegarde_perimee_et_escalade(db_session, monkeypatch, tmp_path):
    """La vigie juge la FRAÎCHEUR du dump (pas sa seule présence) : > 30 h → incident ; panne durable
    (> 24 h après) → escalade mail à Vic (clé `escalade:sauvegarde`)."""
    import os

    from labuse import config, ops_alertes

    bdir = tmp_path / "backups"
    bdir.mkdir()
    dump = bdir / "labuse-labuse-20261029-161844.dump"
    dump.write_bytes(b"x" * 1000)
    # dump vieux de 60 h → au-delà du seuil 30 h ET de l'escalade (30 + 24 = 54 h)
    vieux = (datetime.now(timezone.utc) - timedelta(hours=60)).timestamp()
    os.utime(dump, (vieux, vieux))

    monkeypatch.setenv("LABUSE_BACKUP_DIR", str(bdir))
    config.get_settings.cache_clear()
    ops_alertes.ensure_table(db_session)

    out = ops_alertes.verifier_declencheurs(db_session)
    config.get_settings.cache_clear()

    assert out["sauvegarde"]["present"] is True
    assert out["sauvegarde"]["age_h"] > 54
    ouverts = {i["cle"] for i in out["incidents_ouverts"]}
    assert "sauvegarde-perimee" in ouverts           # fraîcheur dépassée
    assert "escalade:sauvegarde" in ouverts          # panne > 24 h → escalade (mail Vic)


# ───────────────────────── chaîne des données : la source avancée se voit (L-CHN-01/02) ─────────────────────────

def test_composer_surface_une_avance_amont():
    """Un libellé figé daté (« PPR 2011–2024 ») voit l'avance quand l'horizon passe à une année neuve."""
    from datetime import date

    from labuse.millesime_source import composer
    # horizon plus récent que la dernière année du libellé → « à jour au 2026 » ajouté
    assert composer("PPR approuvés 2011–2024", source_horizon_at=date(2026, 4, 16)).endswith("à jour au 2026")
    # horizon déjà couvert par le libellé → inchangé (pas de bruit)
    assert composer("PPR approuvés 2011–2026", source_horizon_at=date(2026, 4, 16)) == "PPR approuvés 2011–2026"
    # un libellé sans année ne se voit PAS inventer une date depuis l'horizon (anti L-MIL-05)
    assert composer("extraction annuelle", source_horizon_at=date(2026, 1, 1)) == "extraction annuelle"


def test_pdf_sources_montre_le_millesime():
    """Le §12 « Sources » du PDF affiche le millésime composé (plus « noms seuls ») : une source
    avancée s'y voit comme en fiche."""
    from labuse.exports.blocs import sources as bloc

    # fausse une source RÉELLEMENT servie (sources_lues lit les Valeur) : on neutralise ce filtre.
    monkey_servies = {"Cadastre PCI"}
    import labuse.exports.pieds as pieds
    orig = pieds.sources_lues
    pieds.sources_lues = lambda _v: {(n, None) for n in monkey_servies}
    try:
        valeurs = {"run_label_servi": type("V", (), {"valeur": [
            {"nom": "Cadastre PCI", "fournisseur": "DGFiP", "millesime": "édition 2026"}]})(),
            "potentiel_verdict": type("V", (), {"valeur": {}})()}
        # `val` lit l'attribut .valeur ; on reproduit la forme attendue par le bloc.
        html = bloc.corps_sources({k: v for k, v in valeurs.items()})
    finally:
        pieds.sources_lues = orig
    assert "Cadastre PCI" in html and "édition 2026" in html


# ───────────────────────── charge : les files bornent la concurrence (K-CHG) ─────────────────────────

def test_files_plafonnent_la_concurrence(monkeypatch):
    """Le sémaphore PDF ne laisse passer que `pdf_rendu_max` rendus à la fois ; la file d'étude lève
    quand toutes les places sont prises (→ 503 honnête côté route)."""
    import threading

    from labuse import config, perf_limits

    monkeypatch.setenv("LABUSE_PDF_RENDU_MAX", "2")
    monkeypatch.setenv("LABUSE_ETUDE_PROCESSUS_MAX", "1")
    monkeypatch.setenv("LABUSE_ETUDE_FILE_ATTENTE_S", "0.2")
    config.get_settings.cache_clear()
    perf_limits._reset_pour_tests()

    # PDF : 2 places → une 3ᵉ acquisition non bloquante échoue tant que les 2 sont tenues.
    sem = perf_limits._sem("pdf")
    assert sem.acquire(blocking=False) and sem.acquire(blocking=False)
    assert sem.acquire(blocking=False) is False
    sem.release(); sem.release()

    # Étude : 1 place. On la tient, une 2ᵉ demande lève FileEtudePleine après l'attente bornée.
    tenue = threading.Event()
    libere = threading.Event()

    def _occupe():
        with perf_limits.etude_slot():
            tenue.set()
            libere.wait(2.0)

    t = threading.Thread(target=_occupe, daemon=True)
    t.start()
    assert tenue.wait(1.0)
    with pytest.raises(perf_limits.FileEtudePleine):
        with perf_limits.etude_slot():
            pass
    libere.set()
    t.join(2.0)
    perf_limits._reset_pour_tests()
    config.get_settings.cache_clear()


# ───────────────────────── backup : le filet par table est présent dans le script ─────────────────────────

def test_backup_script_a_un_filet_par_table():
    from pathlib import Path
    sh = Path(__file__).resolve().parents[1] / "deploy/scripts/backup_postgres.sh"
    txt = sh.read_text()
    assert "has_table_privilege" in txt          # détecte les tables illisibles par le rôle de dump
    assert "--exclude-table=public." in txt       # et les exclut nominativement (le dump ne tombe plus)
    assert "EXCLUDE_TABLES" in txt
