"""VEILLE-FIX-1 — les veilles tournent, et ne préviennent que qui est concerné.

Tests PURS (pas de base réelle requise pour la plupart) : registre des jobs, verrou V8a, ciblage
Radar, essai expiré, cloche d'un compte neuf, trace mail_queue. Marque `verrous` non posée : ces
tests tournent partout (le circuit joué sur base réelle est dans le rapport, pas ici)."""
from __future__ import annotations

import inspect

from labuse.jobs import JOBS


# ─────────────────────────── LOT 1 — le registre ───────────────────────────

def test_les_jobs_veille_existent():
    """VEILLE-2 (Lot 4) — les jobs de veille du matin (evaluer-secteurs RETIRÉ) ont chacun leur créneau,
    et leur impl appelle vraiment la fonction d'évaluation/envoi."""
    from labuse import jobs_impl
    attendu = {
        "evaluer-suivis":  ("2 3 * * *",  "evaluer_suivis",        "evaluer_suivis"),
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
    # evaluer-secteurs RETIRÉ (secteurs archivés — page Veille = PARCELLE + RADAR)
    assert "evaluer-secteurs" not in JOBS


def test_digest_envoie_mail_les_evaluateurs_non():
    """Le digest est le seul à envoyer un mail (règle dry-run) ; les évaluateurs non."""
    assert JOBS["digest"].envoie_mail is True
    for nom in ("evaluer-suivis", "detect-events"):
        assert JOBS[nom].envoie_mail is False


def test_les_jobs_veille_au_crontab_genere():
    """Le crontab GÉNÉRÉ porte une ligne pour chaque job de veille restant ; plus evaluer-secteurs."""
    from labuse.cli import _crontab_du_registre
    crontab = _crontab_du_registre("reunion")
    for nom in ("evaluer-suivis", "detect-events", "digest"):
        assert f"jobs run {nom}'" in crontab, f"{nom} absent du crontab généré"
    assert "jobs run evaluer-secteurs'" not in crontab


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


# ─────────────────────── LOT 4 — la cloche d'un compte neuf ───────────────────────

def test_cloche_compte_neuf_a_zero():
    """VEILLE-FIX-1 (lot 4) — un compte NEUF ouvre la cloche à 0 : les événements de marché diffusés
    AVANT sa création ne comptent pas en non-lus ; un événement de marché postérieur, si."""
    from sqlalchemy import text
    from labuse.db import session_scope, engine
    from labuse.api.events import ensure_tables
    from labuse.registre.moteurs.plateforme import notifications_non_lues
    ensure_tables(engine())
    ids = []
    try:
        with session_scope() as db:
            cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                                  "VALUES ('RT-neuf','integral',false,'actif',1) RETURNING id")).scalar()
            db.commit()
            # 3 bascules de MARCHÉ (compte_id NULL) ANTÉRIEURES à la création du compte
            for i in range(3):
                db.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id, ts) "
                                "VALUES ('bascule', :idu, :t, NULL, now() - interval '2 days')"),
                           {"idu": f"RTNEUF{i:08d}", "t": f"▲ ancienne bascule {i}"})
                ids.append(db.execute(text("SELECT max(id) FROM event_log")).scalar())
            db.commit()
            avant = notifications_non_lues(db, cid)
            assert avant == 0, f"compte neuf devrait ouvrir la cloche à 0, pas {avant}"
            # une bascule de marché POSTÉRIEURE à la création → elle, compte
            db.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id, ts) "
                            "VALUES ('bascule', 'RTNEUF99999999', '▲ nouvelle bascule', NULL, now())"))
            ids.append(db.execute(text("SELECT max(id) FROM event_log")).scalar())
            db.commit()
            apres = notifications_non_lues(db, cid)
            assert apres == 1, f"une bascule postérieure doit compter (attendu 1, obtenu {apres})"
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM event_log WHERE idu LIKE 'RTNEUF%'"))
            s.execute(text("DELETE FROM comptes WHERE nom='RT-neuf'"))
