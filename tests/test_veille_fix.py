"""FIX-VEILLE — option A (armature morte retirée), V2 (débordement du plafond agrégé),
N1 (échec d'e-mail async tracé). Aucun email réel n'est envoyé (tout est mocké)."""
from __future__ import annotations

from contextlib import contextmanager

import pytest
from sqlalchemy import text

import labuse.mail as mail
from labuse.api.events import NOTIF_CAP_JOUR, creer_notification
from labuse.copilote_v2 import veilles


# ─────────────────────────── A — plus aucun type non évaluable ───────────────────────────

def test_types_tous_evaluables():
    """Invariant : chaque type proposé A un évaluateur (plus de fantôme dans TYPES)."""
    assert set(veilles.TYPES) == veilles.EVALUABLES == {"permis"}
    assert set(veilles._EVALUATEURS) == veilles.EVALUABLES


def test_creer_refuse_un_type_non_evaluable(db_session):
    """La garde est DANS `creer` : impossible de poser une veille qui ne s'évaluerait jamais."""
    with pytest.raises(ValueError):
        veilles.creer(db_session, compte_id=None, type_="bodacc", commune="Saint-Denis")
    # le type branché reste posable
    v = veilles.creer(db_session, compte_id=None, type_="permis", commune="Test-Ville")
    assert v["evaluable"] is True and v["type"] == "permis"


# ─────────────────────────── V2 — débordement du plafond agrégé ───────────────────────────

def test_cap_debordement_agrege_visible(db_session):
    """Au-delà du plafond, le surplus n'est plus jeté en silence : UN event « +N autres » monte."""
    db_session.execute(text("DELETE FROM event_log WHERE kind='veille' AND compte_id IS NULL "
                            "AND ts::date = now()::date"))
    for i in range(NOTIF_CAP_JOUR):                       # on remplit EXACTEMENT le plafond
        assert creer_notification(db_session, kind="veille", compte_id=None, titre=f"e{i}") > 0
    # les suivantes sont plafonnées (retour 0) MAIS agrégées
    assert creer_notification(db_session, kind="veille", compte_id=None, titre="sur1") == 0
    assert creer_notification(db_session, kind="veille", compte_id=None, titre="sur2") == 0
    over = db_session.execute(text(
        "SELECT titre, detail FROM event_log WHERE compte_id IS NULL AND dedup = 'debordement:veille' "
        "AND ts::date = now()::date"), {}).mappings().first()
    assert over is not None                                # trace présente (rien de silencieux)
    assert over["titre"].startswith("+2")                 # compteur monté à 2
    assert "plafond" in over["detail"].lower()


# ─────────────────────────── N1 — échec d'e-mail async tracé ───────────────────────────

class _SyncThread:
    """Exécute la cible immédiatement (thread rendu déterministe pour le test)."""
    def __init__(self, target=None, daemon=None, name=None):
        self._target = target
    def start(self):
        if self._target:
            self._target()


def test_async_echec_reel_journalise(monkeypatch):
    monkeypatch.setattr(mail.threading, "Thread", _SyncThread)
    monkeypatch.setattr(mail, "send_email", lambda *a, **k: mail.SendResult(False, "error: SMTPBoom"))
    vus = []
    monkeypatch.setattr(mail, "_journaliser_echec_admin", lambda *a: vus.append(a))
    mail.send_email_async("dest@x.test", "[LABUSE] demande", "corps", contexte="Courrier")
    assert len(vus) == 1
    to, subject, detail, contexte = vus[0]
    assert to == "dest@x.test" and "SMTPBoom" in detail and contexte == "Courrier"


def test_async_no_config_ne_journalise_pas(monkeypatch):
    """Mode journal (dev sans SMTP) : ce n'est PAS un échec → aucune trace admin (pas de bruit)."""
    monkeypatch.setattr(mail.threading, "Thread", _SyncThread)
    monkeypatch.setattr(mail, "send_email", lambda *a, **k: mail.SendResult(False, "no-config"))
    vus = []
    monkeypatch.setattr(mail, "_journaliser_echec_admin", lambda *a: vus.append(a))
    mail.send_email_async("dest@x.test", "sujet", "corps")
    assert vus == []


def test_async_succes_ne_journalise_pas(monkeypatch):
    monkeypatch.setattr(mail.threading, "Thread", _SyncThread)
    monkeypatch.setattr(mail, "send_email", lambda *a, **k: mail.SendResult(True, "ok"))
    vus = []
    monkeypatch.setattr(mail, "_journaliser_echec_admin", lambda *a: vus.append(a))
    mail.send_email_async("dest@x.test", "sujet", "corps")
    assert vus == []


def test_journaliser_echec_ecrit_un_event_systeme(monkeypatch):
    """La trace est un event `systeme` (feed ADMIN, compte NULL) portant la cause — sans DB réelle."""
    import labuse.api.events as ev
    import labuse.db as dbm
    cap = {}
    monkeypatch.setattr(ev, "creer_notification", lambda db, **kw: cap.update(kw) or 1)

    @contextmanager
    def _fake_scope():
        yield object()
    monkeypatch.setattr(dbm, "session_scope", _fake_scope)

    mail._journaliser_echec_admin("dest@x.test", "[LABUSE] X", "error: SMTPBoom", "Courrier")
    assert cap["kind"] == "systeme" and cap["compte_id"] is None
    assert "SMTPBoom" in cap["detail"] and "dest@x.test" in cap["detail"]
    assert "Courrier" in cap["titre"]
