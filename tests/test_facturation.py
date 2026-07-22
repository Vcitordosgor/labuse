"""PREMIER EURO · E2/E5 — le webhook SIGNÉ et le cycle d'états Stripe, prouvés SANS compte
Stripe (la signature se calcule avec le secret webhook — schéma officiel t.v1=HMAC)."""
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
from labuse.facturation import ConfigError, traiter_webhook

SECRET = "whsec_test_premier_euro"


@pytest.fixture()
def db(monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", SECRET)
    with session_scope() as s:
        comptes.ensure_tables(s)
        yield s


def _signe(payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    t = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={t},v1={sig}"


def _evt(type_, obj):
    return {"id": "evt_test", "object": "event", "api_version": "2024-06-20",
            "type": type_, "data": {"object": obj}}


def test_webhook_signature_invalide_rejete(db):
    body, _ = _signe(_evt("invoice.paid", {}))
    with pytest.raises(Exception):
        traiter_webhook(db, body, "t=1,v1=deadbeef")
    with pytest.raises(Exception):
        traiter_webhook(db, body, None)


def test_webhook_sans_secret_refuse(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", None)
    with pytest.raises(ConfigError):
        traiter_webhook(db, b"{}", "t=1,v1=x")


def test_cycle_stripe_complet(db):
    email = f"stripe-{uuid.uuid4().hex[:8]}@exemple.test"
    cus = f"cus_{uuid.uuid4().hex[:10]}"   # unique : les comptes des runs précédents restent en base
    inv = comptes.creer_invitation(db, email, "inde", founding=True)
    cid = inv["compte_id"]

    # activation (checkout.session.completed) : invite → actif + IDs stripe posés
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": cus,
                             "subscription": "sub_test"}))
    assert traiter_webhook(db, body, sig)["action"] == "activation"
    row = db.execute(text("SELECT statut, stripe_customer_id FROM comptes WHERE id = :c"),
                     {"c": cid}).mappings().first()
    assert row["statut"] == "actif" and row["stripe_customer_id"] == cus

    # impayé → paiement_requis (l'app affiche un état, jamais un 500)
    body, sig = _signe(_evt("invoice.payment_failed", {"customer": cus}))
    assert traiter_webhook(db, body, sig)["action"] == "paiement_requis"
    assert db.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() \
        == "paiement_requis"

    # facture payée → retour actif
    body, sig = _signe(_evt("invoice.paid", {"customer": cus}))
    assert traiter_webhook(db, body, sig)["action"] == "paiement_ok"
    assert db.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() == "actif"

    # souscription supprimée → suspendu (sessions révoquées)
    body, sig = _signe(_evt("customer.subscription.deleted", {"customer": cus}))
    assert traiter_webhook(db, body, sig)["action"] == "suspension"
    assert db.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() \
        == "suspendu"

    db.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})
    db.commit()
