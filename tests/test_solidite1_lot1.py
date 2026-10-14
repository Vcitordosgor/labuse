"""SOLIDITE-1 (Lot 1) — plus aucune panne silencieuse.

On prouve, SANS réseau : (1) le registre/crontab/logs sont câblés comme le mandat le demande, (2)
l'historique `job_runs` retient chaque passage, (3) la machine à incidents ouvre UNE fois, rappelle au
plus une fois par jour, et résout proprement, (4) le détecteur de retard voit un job qui s'est tu.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from labuse.cli import _crontab_du_registre
from labuse.jobs import JOBS, Job


# ─────────────────────────── 1.1/1.4 — câblage (sans DB) ───────────────────────────

def test_recap_matin_au_registre():
    """Le récap du matin existe, part en mail, et tombe à 03:30 UTC = 07:30 Réunion, APRÈS le digest."""
    j = JOBS.get("recap-matin")
    assert j is not None and j.envoie_mail is True
    assert j.cron_utc == "30 3 * * *" and j.heure_reunion == "07:30"


def test_recap_sujet_porte_la_date(monkeypatch):
    """SOLIDITE-1 / incident 14/10 — le sujet du récap porte LA DATE du jour (sujet unique chaque jour)
    pour que Gmail ne regroupe/replie plus le récap quotidien (Brevo l'avait pourtant livré)."""
    import types
    from labuse import jobs_impl, ops_alertes
    monkeypatch.setattr(ops_alertes, "verifier_declencheurs",
                        lambda db: {"incidents_ouverts": [], "disque_pct": 50.0,
                                    "sauvegarde": {"dernier": "x.dump"}, "readyz": {"ready": True},
                                    "retards": []})
    capte = {}
    monkeypatch.setattr(jobs_impl, "_envoyer_alerte",
                        lambda corps, *, sujet, ctx=None: capte.update(sujet=sujet))
    ctx = types.SimpleNamespace(db=types.SimpleNamespace(commit=lambda: None),
                                dry_run=False, compte=lambda **k: None)
    jobs_impl.recap_matin(ctx)
    jour = datetime.now(timezone.utc).astimezone().strftime("%d/%m")
    assert jour in capte["sujet"], f"la date {jour} doit figurer dans le sujet : {capte.get('sujet')!r}"
    assert "récap du matin" in capte["sujet"] and "tout vert" in capte["sujet"]


def test_mailto_vide_dans_crontab():
    """SOLIDITE-1 (1.1) — fin du MAILTO « vers le vide » : plus de MAILTO=root, un MAILTO vide."""
    for tz in ("utc", "reunion"):
        c = _crontab_du_registre(tz)
        assert 'MAILTO=""' in c
        assert "MAILTO=root" not in c


def test_logs_jobs_rotation_12_mois():
    """SOLIDITE-1 (1.1) — logs de jobs dans /var/log/labuse/jobs, rotation 12 mois (pas 30 jours),
    sans chevaucher le logrotate applicatif."""
    from pathlib import Path
    racine = Path(__file__).resolve().parents[1]
    txt = (racine / "deploy" / "logrotate.d" / "labuse-jobs").read_text(encoding="utf-8")
    assert "/var/log/labuse/jobs/*.log" in txt
    assert "monthly" in txt and "rotate 12" in txt
    wrapper = (racine / "scripts" / "jobs" / "run-job.sh").read_text(encoding="utf-8")
    assert "/var/log/labuse/jobs" in wrapper


# ─────────────────────────── 1.1 — l'historique job_runs ───────────────────────────

def test_job_runs_historise(db_session):
    from labuse import jobs_journal
    jobs_journal.ensure_table(db_session)
    db_session.execute(text("DELETE FROM job_runs WHERE nom = 'zz-test'"))
    t0 = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    t1 = datetime.now(timezone.utc).isoformat()
    jobs_journal.enregistrer(db_session, {"nom": "zz-test", "debut": t0, "fin": t0,
                                          "statut": "echec", "duree_s": 1, "erreur": "boom",
                                          "compteurs": {}, "dry_run": False})
    jobs_journal.enregistrer(db_session, {"nom": "zz-test", "debut": t1, "fin": t1,
                                          "statut": "ok", "duree_s": 2, "compteurs": {"n": 3}})
    succ = jobs_journal.dernier_succes(db_session)
    assert "zz-test" in succ                                   # le dernier succès est retenu
    dern = jobs_journal.dernier_passage(db_session)["zz-test"]
    assert dern["statut"] == "ok"                              # le plus récent par début
    hist = jobs_journal.historique(db_session, "zz-test", n=10)
    assert len(hist) == 2 and hist[0]["statut"] == "ok"        # ordre antéchronologique


# ─────────────────────────── 1.2/1.3 — incidents : ouvrir / rappeler / résoudre ───────────────────────────

def test_incident_ouvre_rappelle_resout(db_session):
    from labuse import ops_alertes
    ops_alertes.ensure_table(db_session)
    cle = "zz-incident-test"
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle = :c"), {"c": cle})

    assert ops_alertes.signaler(db_session, cle, "Panne test", "détail") == "ouvert"
    # même jour → pas de second envoi (anti-déluge)
    assert ops_alertes.signaler(db_session, cle, "Panne test", "détail2") == "silence"
    assert len(ops_alertes.incidents_ouverts(db_session)) >= 1
    # on vieillit le dernier envoi d'un jour → un (seul) rappel repart
    db_session.execute(text(
        "UPDATE ops_incidents SET dernier_envoi_at = now() - interval '1 day' WHERE cle = :c"), {"c": cle})
    assert ops_alertes.signaler(db_session, cle, "Panne test", "détail3") == "rappel"
    assert ops_alertes.signaler(db_session, cle, "Panne test", "détail4") == "silence"
    # résolution : une fois oui, deux fois non (jamais un « résolu » pour rien)
    assert ops_alertes.resoudre(db_session, cle) is True
    assert ops_alertes.resoudre(db_session, cle) is False
    assert all(i["cle"] != cle for i in ops_alertes.incidents_ouverts(db_session))


def test_signaler_puis_resoudre_rouvre(db_session):
    """Un incident résolu puis qui se reproduit rouvre un INCIDENT NEUF (l'index partiel n'empêche que
    les doublons OUVERTS)."""
    from labuse import ops_alertes
    ops_alertes.ensure_table(db_session)
    cle = "zz-reouverture"
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle = :c"), {"c": cle})
    assert ops_alertes.signaler(db_session, cle, "x", "y") == "ouvert"
    assert ops_alertes.resoudre(db_session, cle) is True
    assert ops_alertes.signaler(db_session, cle, "x", "y") == "ouvert"   # reproduction → neuf


# ─────────────────────────── 1.2 — le détecteur de retard ───────────────────────────

def test_retard_detecte(db_session):
    """Un job qui a RÉUSSI puis s'est tu (dernier succès > 1,5 × sa cadence) est vu en retard ; un
    passage frais le fait disparaître. Exactement le cas des 19 tâches mortes du 07/10."""
    from labuse import jobs_journal, ops_alertes
    jobs_journal.ensure_table(db_session)
    nom = "zz-retard-test"
    JOBS[nom] = Job(nom, "Job retard test", "quotidien", "0 0 * * *", "04:00",
                    lambda ctx: None, raison="t", touche="exploitation", test="t", besoin_db=False)
    try:
        db_session.execute(text("DELETE FROM job_runs WHERE nom = :n"), {"n": nom})
        vieux = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        db_session.execute(text("INSERT INTO job_runs (nom, debut, fin, statut, dry_run) "
                                "VALUES (:n, :d, :d, 'ok', false)"), {"n": nom, "d": vieux})
        retards = {r["nom"] for r in ops_alertes._jobs_en_retard(db_session)}
        assert nom in retards                                  # quotidien, 3 j sans succès → retard
        # passage frais → plus en retard
        db_session.execute(text("INSERT INTO job_runs (nom, debut, fin, statut, dry_run) "
                                "VALUES (:n, now(), now(), 'ok', false)"), {"n": nom})
        retards2 = {r["nom"] for r in ops_alertes._jobs_en_retard(db_session)}
        assert nom not in retards2
    finally:
        JOBS.pop(nom, None)


def test_intervalle_cadences():
    """L'intervalle déduit de l'expression cron colle à la cadence (quotidien ≈ 24 h, hebdo ≈ 7 j)."""
    from labuse import ops_alertes
    assert abs(ops_alertes._intervalle_s("0 3 * * *") - 86400) < 120          # quotidien
    assert abs(ops_alertes._intervalle_s("0 0 * * 0") - 7 * 86400) < 120      # hebdo (dimanche)


def test_envoyer_ops_passe_par_brevo_sans_smtp(monkeypatch):
    """SOLIDITE-1 — le VPS n'a pas de SMTP mais a BREVO_API_KEY : les alertes doivent partir par Brevo
    (pas rester « no-config »). envoyer_ops choisit Brevo quand smtp_host est vide."""
    from labuse import mail, brevo, config
    s = config.get_settings()
    monkeypatch.setattr(s, "smtp_host", None)
    monkeypatch.setattr(brevo, "_api_key", lambda: "clef-test")
    vu = {}
    monkeypatch.setattr(brevo, "envoyer_texte",
                        lambda to, subject, texte: vu.update(to=to, subject=subject) or {"envoye": True})
    r = mail.envoyer_ops("kampusreunion@gmail.com", "[LABUSE] test", "corps", settings=s)
    assert r.sent is True and vu["to"] == "kampusreunion@gmail.com"


def test_verifier_declencheurs_rend_les_vigies(db_session):
    """verifier_declencheurs tourne sans réseau et renvoie les quatre vigies + les incidents ouverts."""
    from labuse import ops_alertes
    out = ops_alertes.verifier_declencheurs(db_session)
    for cle in ("disque_pct", "readyz", "sauvegarde", "retards", "incidents_ouverts"):
        assert cle in out
