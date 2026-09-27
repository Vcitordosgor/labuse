"""VEILLE-FIX-2 · Lot D — la file de mails tient toute seule.

  · un WORKER (`mailfile.consommer`, cron 5 min) envoie les `en_attente` dûs + les `a_rejouer` échus ;
  · REJEU espacé (5 min → 1 h → 24 h) sur échec Brevo, puis `echec` définitif (ligne rouge) ;
  · le DIGEST passe par la file (différé) → il bénéficie du rejeu ;
  · jamais d'envoi en double (un `recu` n'est jamais retenté).

Brevo simulé en panne → rejeu ; Brevo revenu → repart. [VF2-D] purgés en fin.
"""
from __future__ import annotations

import types
import uuid

import pytest
from sqlalchemy import text

from labuse import mail, mailfile
from labuse.db import engine, session_scope

pytestmark = pytest.mark.db


def _fake(ok: bool):
    return types.SimpleNamespace(ok=ok, detail=None if ok else "Brevo injoignable (simulé)")


def _raw(to: str) -> dict:
    return {"key": "digest_quotidien", "to": to,
            "params": {"__raw": {"sujet": "test", "texte": "corps", "html": "<p>corps</p>", "nom": "Test"}}}


def _echus(eng):
    """Force les prevu_at dans le passé (simule l'écoulement du temps) pour que le worker reprenne."""
    with eng.begin() as c:
        c.execute(text("UPDATE mail_queue SET prevu_at = now() - interval '1 minute' "
                       "WHERE etat='a_rejouer' AND prevu_at IS NOT NULL"))


def _etat(eng, mid):
    with eng.begin() as c:
        return c.execute(text("SELECT etat, tentatives FROM mail_queue WHERE id=:i"), {"i": mid}).mappings().first()


def _purge_non_terminaux(eng):
    """Base de test partagée : on écarte les entrées non-terminales d'autres tests pour que le worker
    (LIMIT) traite DÉTERMINISTIQUEMENT nos lignes."""
    with eng.begin() as c:
        c.execute(text("DELETE FROM mail_queue WHERE etat IN ('en_attente','a_rejouer')"))


def test_worker_envoie_et_rejoue(monkeypatch):
    eng = engine()
    mailfile.ensure_tables(eng)
    _purge_non_terminaux(eng)
    tag = uuid.uuid4().hex[:8]
    to = f"vf2d-{tag}@labuse.immo"
    mid = None
    try:
        # (1) enfilé DIFFÉRÉ : rien ne part synchroniquement (c'est le worker qui enverra)
        ligne = mailfile.envoyer_mail(eng, **_raw(to), dedup=f"vf2d:{tag}", differe=True)
        mid = ligne["id"]
        assert _etat(eng, mid)["etat"] == "en_attente"

        # (2) Brevo EN PANNE → le worker le passe `a_rejouer` (backoff), jamais perdu
        monkeypatch.setattr(mail, "send_email", lambda *a, **k: _fake(False))
        r = mailfile.consommer(eng)
        assert r["a_rejouer"] >= 1
        e = _etat(eng, mid)
        assert e["etat"] == "a_rejouer" and e["tentatives"] == 1

        # (3) le temps passe, toujours en panne → 2ᵉ puis 3ᵉ rejeu
        _echus(eng); mailfile.consommer(eng)
        assert _etat(eng, mid)["tentatives"] == 2
        _echus(eng); mailfile.consommer(eng)
        assert _etat(eng, mid)["tentatives"] == 3

        # (4) au-delà des 3 rejeux → ÉCHEC définitif (ligne rouge, plus repris par le worker)
        _echus(eng); mailfile.consommer(eng)
        assert _etat(eng, mid)["etat"] == "echec"
        # l'échec compte pour le compte (aucun ici) — la file l'expose
        assert mailfile.compteurs(eng)["echecs"] >= 1

        # (5) Brevo REVENU + rejeu MANUEL → repart et arrive
        monkeypatch.setattr(mail, "send_email", lambda *a, **k: _fake(True))
        mailfile.rejouer(eng, mid)
        assert _etat(eng, mid)["etat"] == "recu"

        # (6) idempotence : un `recu` n'est jamais renvoyé par le worker
        before = _etat(eng, mid)["tentatives"]
        mailfile.consommer(eng)
        assert _etat(eng, mid)["etat"] == "recu" and _etat(eng, mid)["tentatives"] == before
    finally:
        with eng.begin() as c:
            c.execute(text("DELETE FROM mail_queue WHERE dedup=:d"), {"d": f"vf2d:{tag}"})


def test_brevo_revient_avant_echec(monkeypatch):
    """Brevo tombe une fois (a_rejouer), puis revient AVANT l'échec → le mail part."""
    eng = engine()
    mailfile.ensure_tables(eng)
    _purge_non_terminaux(eng)
    tag = uuid.uuid4().hex[:8]
    try:
        ligne = mailfile.envoyer_mail(eng, **_raw(f"r-{tag}@labuse.immo"), dedup=f"vf2dr:{tag}", differe=True)
        mid = ligne["id"]
        monkeypatch.setattr(mail, "send_email", lambda *a, **k: _fake(False))
        mailfile.consommer(eng)
        assert _etat(eng, mid)["etat"] == "a_rejouer"
        monkeypatch.setattr(mail, "send_email", lambda *a, **k: _fake(True))
        _echus(eng); mailfile.consommer(eng)
        assert _etat(eng, mid)["etat"] == "recu"
    finally:
        with eng.begin() as c:
            c.execute(text("DELETE FROM mail_queue WHERE dedup=:d"), {"d": f"vf2dr:{tag}"})


def test_digest_passe_par_la_file(monkeypatch):
    """envoyer_digests (non dry-run) ENFILE le digest (en_attente) sans envoi synchrone ; le worker le
    livre. Prouve « le digest passe par la file »."""
    from labuse.api import events
    tag = uuid.uuid4().hex[:6]
    cid = None
    try:
        with session_scope() as db:
            events.ensure_tables(db.get_bind())
            mailfile.ensure_tables(db.get_bind())
            cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                                  "VALUES (:n,'integral',false,'actif',1) RETURNING id"),
                             {"n": f"[VF2-D] {tag}"}).scalar()
            db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                            "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": f"d{tag}@labuse.immo"})
            events.set_digest_freq(db, cid, "quotidien")
            db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
            db.execute(text("INSERT INTO event_log (kind, titre, compte_id, source) "
                            "VALUES ('parcelle_suivie', :t, :c, 'Mutation')"),
                       {"t": f"Vente sur votre parcelle ({tag})", "c": cid})
            db.commit()
            # non dry-run → la ligne est ENFILÉE (en_attente), PAS envoyée dans le job
            r = events.envoyer_digests(db, base_url="https://app.labuse.immo", force=True, dry_run=False)
            d = next(x for x in r["details"] if x["compte"] == cid)
            assert d["statut"] == "en file"
        eng = engine()
        row = None
        with eng.begin() as c:
            row = c.execute(text("SELECT id, etat FROM mail_queue WHERE compte_id=:c "
                                 "AND mail_key='digest_quotidien'"), {"c": cid}).mappings().first()
        assert row and row["etat"] == "en_attente", "le digest attend le worker (pas d'envoi synchrone)"
        # worker + Brevo up → livré (les autres non-terminaux écartés pour un worker déterministe)
        monkeypatch.setattr(mail, "send_email", lambda *a, **k: _fake(True))
        with eng.begin() as c:
            c.execute(text("DELETE FROM mail_queue WHERE etat IN ('en_attente','a_rejouer') AND id <> :i"),
                      {"i": row["id"]})
        mailfile.consommer(eng)
        with eng.begin() as c:
            assert c.execute(text("SELECT etat FROM mail_queue WHERE id=:i"), {"i": row["id"]}).scalar() == "recu"
    finally:
        with session_scope() as db:
            if cid:
                db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM notif_prefs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            db.commit()
