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
    return {"id": f"evt_{uuid.uuid4().hex[:16]}", "object": "event", "api_version": "2024-06-20",
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
    inv = comptes.creer_invitation(db, email)
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


def test_flash_fulfillment_reel(db):
    """FLASH : webhook signé mode=payment → génération RÉELLE du PDF (weasyprint, .venv)
    → statut generee → token de téléchargement valide. Le test le plus cher de la suite
    (~8 s) — c'est le produit à 79 €, il se prouve en vrai."""
    from labuse.facturation import ensure_flash_table, flash_pdf_par_token, flash_statut
    ensure_flash_table(db)
    sid = f"cs_test_{uuid.uuid4().hex[:12]}"
    # une parcelle de LA BASE DE TEST (labuse_test) — jamais un IDU en dur d'une autre base
    idu = db.execute(text("SELECT idu FROM parcels ORDER BY idu LIMIT 1")).scalar()
    if not idu:
        pytest.skip("base de test sans parcelles — génération Flash non testable ici")
    db.execute(text("INSERT INTO flash_commandes (stripe_session_id, idu) VALUES (:s, :i)"),
               {"s": sid, "i": idu})
    db.commit()
    body, sig = _signe(_evt("checkout.session.completed",
                            {"id": sid, "mode": "payment",
                             "customer_details": {"email": "flash@exemple.test"}}))
    assert traiter_webhook(db, body, sig)["action"] == "flash_genere"
    st = flash_statut(db, sid)
    assert st["statut"] == "generee" and st.get("lien"), st
    token = st["lien"].split("token=")[1]
    pdf = flash_pdf_par_token(db, token)
    assert pdf and pdf.endswith(".pdf")
    import pathlib as _pl
    assert _pl.Path(pdf).stat().st_size > 20_000       # un vrai PDF, pas un fichier vide
    assert flash_pdf_par_token(db, "mauvais-token") is None


def test_suspension_coupe_les_sessions_actives(db):
    """Bug du test Vic (mi-course) : la suspension doit couper une session DÉJÀ ouverte,
    immédiatement — pas au prochain login, pas « dans la minute »."""
    email = f"susp-{uuid.uuid4().hex[:8]}@exemple.test"
    cus = f"cus_{uuid.uuid4().hex[:10]}"
    inv = comptes.creer_invitation(db, email)
    tok_i = inv["lien"].split("token=")[1]
    comptes.activer_par_invitation(db, tok_i, "session-active-974", "2026-07-22")
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(inv["compte_id"]), "customer": cus,
                             "subscription": "sub_x"}))
    traiter_webhook(db, body, sig)
    u = comptes.verifier_login(db, email, "session-active-974")
    session = comptes.creer_session(db, u["utilisateur_id"])
    assert comptes.session_utilisateur(db, session)                 # session ouverte

    # 1. la voie normale : webhook subscription.deleted → purge + statut → refus immédiat
    body, sig = _signe(_evt("customer.subscription.deleted", {"customer": cus}))
    traiter_webhook(db, body, sig)
    assert comptes.session_utilisateur(db, session) is None

    # 2. défense en profondeur : une session qui aurait SURVÉCU à la purge est refusée
    #    par le statut du compte seul
    comptes.reactiver_compte(db, inv["compte_id"])
    session2 = comptes.creer_session(db, u["utilisateur_id"])
    assert comptes.session_utilisateur(db, session2)
    db.execute(text("UPDATE comptes SET statut = 'suspendu' WHERE id = :c"),
               {"c": inv["compte_id"]})   # suspension SANS purge (le cas pathologique)
    db.commit()
    assert comptes.session_utilisateur(db, session2) is None
    db.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})
    db.commit()
