"""E9 (parcours d'entrée) — recette DE BOUT EN BOUT de l'app, côté serveur (Stripe mocké/signé).

Ce que ce test prouve SANS Stripe réel : les deux parcours de A à Z jusqu'à l'état de compte, y
compris les webhooks d'échec. Ce qu'il NE couvre pas (nécessite les clés TEST de Vic) : le rendu
du Checkout hébergé et les cartes 4242 / refus / 3DS → runbook `RUNBOOK-STRIPE-TEST.md`.

Les comptes créés sont préfixés « [PE-TEST] » et purgés en fin de test (vérifié).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

import pytest
from sqlalchemy import text

from labuse import comptes
from labuse.config import get_settings
from labuse.db import session_scope
from labuse.facturation import traiter_webhook

pytestmark = pytest.mark.db
SECRET = "whsec_e2e_parcours"
TAG = "[PE-TEST]"


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", SECRET)
    with session_scope() as s:
        comptes.ensure_tables(s)
        yield s
    # purge des comptes [PE-TEST] (vérifiée par test_purge_effective)
    with session_scope() as s:
        s.execute(text("DELETE FROM comptes WHERE nom LIKE :t"), {"t": f"{TAG}%"})
        s.execute(text("DELETE FROM utilisateurs WHERE email LIKE :t"), {"t": "pe-test-%"})
        s.commit()


def _signe(payload: dict):
    body = json.dumps(payload).encode()
    t = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={t},v1={sig}"


def _evt(type_, obj):
    return {"id": f"evt_{uuid.uuid4().hex[:12]}", "object": "event", "type": type_, "data": {"object": obj}}


def _compte_invite():
    """Crée un compte invité [PE-TEST] et rend (compte_id, email, token)."""
    email = f"pe-test-{uuid.uuid4().hex[:8]}@exemple.test"
    with session_scope() as s:
        inv = comptes.creer_invitation(s, email, nom=f"{TAG} client")
    return inv["compte_id"], email, inv["lien"].split("token=")[1]


def _statut(db, cid):
    return db.execute(text("SELECT statut FROM comptes WHERE id=:c"), {"c": cid}).scalar()


def test_parcours_integral_succes_de_bout_en_bout(db):
    """(a) invitation → mot de passe + CGV → [Checkout] → webhook payé → compte ACTIF → login OK."""
    cid, email, tok = _compte_invite()
    # mot de passe + CGV (activer_par_invitation = ce que fait POST /invitation)
    assert comptes.activer_par_invitation(db, tok, "MotDePasse123!", get_settings().cgv_version)
    assert _statut(db, cid) == "invite"                       # pas encore payé
    # webhook Stripe « paiement reçu » (ce que le Checkout 4242 déclenche en réel)
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": "cus_petest",
                             "subscription": "sub_petest", "customer_email": email}))
    assert traiter_webhook(db, body, sig)["action"] == "activation"
    assert _statut(db, cid) == "actif"                        # argent ↔ état : payé ⇒ actif
    # login réel possible (identifiants posés)
    u = comptes.verifier_login(db, email, "MotDePasse123!")
    assert u and u["statut_compte"] == "actif"


def test_parcours_integral_carte_refusee_puis_reprise(db):
    """Échec : carte refusée (4000…0341) → invoice.payment_failed → paiement_requis ; puis
    invoice.paid → retour actif (l'argent recolle l'état)."""
    cid, email, tok = _compte_invite()
    comptes.activer_par_invitation(db, tok, "MotDePasse123!", get_settings().cgv_version)
    # d'abord actif…
    b, s = _signe(_evt("checkout.session.completed",
                       {"client_reference_id": str(cid), "customer": "cus_x", "subscription": "sub_x"}))
    traiter_webhook(db, b, s)
    assert _statut(db, cid) == "actif"
    # …puis un prélèvement échoue
    b, s = _signe(_evt("invoice.payment_failed", {"customer": "cus_x", "subscription": "sub_x"}))
    traiter_webhook(db, b, s)
    assert _statut(db, cid) == "paiement_requis"
    # …puis il repasse (reprise)
    b, s = _signe(_evt("invoice.paid", {"customer": "cus_x", "subscription": "sub_x"}))
    traiter_webhook(db, b, s)
    assert _statut(db, cid) == "actif"


def test_parcours_integral_resiliation_suspend(db):
    """subscription.deleted (fin d'abonnement) → compte suspendu, données intactes."""
    cid, email, tok = _compte_invite()
    comptes.activer_par_invitation(db, tok, "MotDePasse123!", get_settings().cgv_version)
    b, s = _signe(_evt("checkout.session.completed",
                       {"client_reference_id": str(cid), "customer": "cus_y", "subscription": "sub_y"}))
    traiter_webhook(db, b, s)
    b, s = _signe(_evt("customer.subscription.deleted", {"customer": "cus_y", "subscription": "sub_y"}))
    traiter_webhook(db, b, s)
    assert _statut(db, cid) == "suspendu"


def test_webhook_non_signe_rejete(db):
    """Un webhook forgé (mauvaise signature) est REFUSÉ — la porte du webhook, c'est la signature."""
    body = json.dumps(_evt("checkout.session.completed", {"client_reference_id": "1"})).encode()
    with pytest.raises(Exception):  # noqa: B017 — Stripe lève SignatureVerificationError
        traiter_webhook(db, body, "t=1,v1=faux")


def test_purge_effective(db):
    """Après création + purge (teardown de la fixture d'un autre test), aucun compte [PE-TEST]
    ne subsiste. Ici on vérifie la purge dans la foulée."""
    cid, email, tok = _compte_invite()
    with session_scope() as s:
        s.execute(text("DELETE FROM comptes WHERE nom LIKE :t"), {"t": f"{TAG}%"})
        s.execute(text("DELETE FROM utilisateurs WHERE email LIKE :t"), {"t": "pe-test-%"})
        s.commit()
        reste = s.execute(text("SELECT count(*) FROM utilisateurs WHERE email LIKE :t"),
                          {"t": "pe-test-%"}).scalar()
    assert reste == 0
