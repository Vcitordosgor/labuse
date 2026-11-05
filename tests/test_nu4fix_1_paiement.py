"""NU4-FIX-1 — Lot B (paiement). Reproductions ROUGE→VERTE des trouvailles du rapport
`docs/audit-2026-11/nu-4/B/RAPPORT.md`. Webhooks SIGNÉS (secret seul), Stripe STUBÉ pour les appels
API (aucun réseau, mode test).

- T1 « Régulariser » paie la facture ouverte de l'abonnement EXISTANT (jamais un 2ᵉ abo).
- T2 un essai expiré qui PAIE débloque l'accès (essai_expire_at effacé → pas de re-suspension).
- T3 la 1ʳᵉ facture d'abonnement porte la mention 293 B (pied posé sur le client AVANT la session).
- T4 ré-abonnement propre (adopte la NOUVELLE sub, efface acces_fin_at) ; le vrai doublon reste annulé.
- T5 l'admin lit Stripe dans le même mode que l'app.
- T6 le passage en lecture seule (J+7) est annoncé au client (une fois).
- T7 l'accès en lecture après non-paiement a une date de fin (suspension bornée).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import types
import uuid

import pytest
from sqlalchemy import text

from labuse import comptes, facturation
from labuse.config import get_settings
from labuse.db import engine as _engine
from labuse.db import session_scope

pytestmark = pytest.mark.db

SECRET = "whsec_nu4fix_1"


@pytest.fixture(autouse=True)
def _no_real_mail(monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template",
                        lambda to, key, params: {"envoye": True, "message_id": "<test>"})


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
    return {"id": f"evt_{uuid.uuid4().hex[:16]}", "object": "event", "type": type_,
            "data": {"object": obj}}


def _compte(db, *, statut="invite", sub=None, cus=None, essai_past=False,
            acces_fin_future=False, paiement_requis_jours=None):
    """Crée un compte+utilisateur ACTIF et le place dans l'état voulu. Retourne (cid, uid)."""
    email = f"nu4fixb-{uuid.uuid4().hex[:10]}@exemple.test"
    inv = comptes.creer_invitation(db, email)
    tok = inv["lien"].split("token=")[1]
    comptes.activer_par_invitation(db, tok, "mot-de-passe-nu4fix", "2026-07-22")
    cid, uid = int(inv["compte_id"]), int(inv["utilisateur_id"])
    sets, params = ["statut = :st"], {"st": statut, "c": cid}
    if sub is not None:
        sets.append("stripe_subscription_id = :sub"); params["sub"] = sub
    if cus is not None:
        sets.append("stripe_customer_id = :cus"); params["cus"] = cus
    if essai_past:
        sets.append("essai_expire_at = now() - interval '1 hour'")
    if acces_fin_future:
        sets.append("acces_fin_at = now() + interval '20 days'")
    if paiement_requis_jours is not None:
        sets.append(f"paiement_requis_at = now() - interval '{int(paiement_requis_jours)} days'")
    db.execute(text(f"UPDATE comptes SET {', '.join(sets)}, updated_at = now() WHERE id = :c"), params)
    db.commit()
    return cid, uid


def _fake_stripe(state):
    cust = types.SimpleNamespace(
        create=lambda **k: (state["customer_created"].append(k) or types.SimpleNamespace(id="cus_new")),
        modify=lambda cid, **k: state["customer_modified"].append((cid, k)))
    session = types.SimpleNamespace(
        create=lambda **k: (state["checkout_kwargs"].append(k)
                            or types.SimpleNamespace(id="cs_x", url="https://checkout.stripe.test/new")))
    return types.SimpleNamespace(
        Customer=cust,
        checkout=types.SimpleNamespace(Session=session),
        Subscription=types.SimpleNamespace(cancel=lambda sid: state["sub_canceled"].append(sid)),
        Invoice=types.SimpleNamespace(
            list=lambda **k: types.SimpleNamespace(data=state["open_invoices"])))


# ───────────────────────── T1 — « Régulariser » paie l'abo existant, pas un 2ᵉ ─────────────────────────

def test_t1_regulariser_paie_la_facture_ouverte(db, monkeypatch):
    cid, _ = _compte(db, statut="paiement_requis", sub="sub_existante", cus="cus_1")
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "sk_test_x")
    state = {"customer_created": [], "customer_modified": [], "sub_canceled": [],
             "checkout_kwargs": [], "open_invoices":
             [types.SimpleNamespace(hosted_invoice_url="https://pay.stripe.test/openinv")]}
    monkeypatch.setattr(facturation, "_stripe", lambda: _fake_stripe(state))

    assert facturation.a_abonnement(db, cid) is True
    lien = facturation.lien_regularisation(db, cid)
    assert lien == "https://pay.stripe.test/openinv"      # on paie la facture OUVERTE existante…
    assert not state["checkout_kwargs"], "…JAMAIS un nouveau Checkout d'abonnement (pas de 2ᵉ abo)"


# ───────────────────────── T2 — essai expiré qui paie → accès débloqué ─────────────────────────

def test_t2_essai_expire_qui_paie_debloque(db):
    cid, uid = _compte(db, statut="actif", essai_past=True)   # essai échu, pas encore suspendu
    cus = f"cus_{uuid.uuid4().hex[:8]}"
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_t2"}))
    assert facturation.traiter_webhook(db, body, sig)["action"] == "activation"
    row = db.execute(text("SELECT statut, essai_expire_at FROM comptes WHERE id = :c"),
                     {"c": cid}).mappings().first()
    assert row["statut"] == "actif" and row["essai_expire_at"] is None   # essai effacé (T2)
    # au 1ᵉʳ accès, le compte PAYÉ n'est PAS re-suspendu
    tok = comptes.creer_session(db, uid)
    assert comptes.session_utilisateur(db, tok) is not None


# ───────────────────────── T3 — mention 293 B sur la 1ʳᵉ facture ─────────────────────────

def test_t3_mention_293b_des_la_premiere_facture(db, monkeypatch):
    cid, _ = _compte(db, statut="invite")
    s = get_settings()
    monkeypatch.setattr(s, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(s, "stripe_price_integral", "price_x")
    monkeypatch.setattr(facturation, "_garde_coherence_prix", lambda *a, **k: None)
    state = {"customer_created": [], "customer_modified": [], "sub_canceled": [],
             "checkout_kwargs": [], "open_invoices": []}
    monkeypatch.setattr(facturation, "_stripe", lambda: _fake_stripe(state))

    facturation.creer_checkout(db, cid, "client@exemple.test")
    # le CLIENT Stripe est créé AVANT la session, avec le pied de facture → la 1ʳᵉ facture le porte
    assert state["customer_created"], "le client Stripe doit être pré-créé (pied posé avant la 1ʳᵉ facture)"
    assert state["customer_created"][0]["invoice_settings"]["footer"] == s.facture_mention
    kw = state["checkout_kwargs"][0]
    assert kw.get("customer") == "cus_new" and "customer_email" not in kw
    assert db.execute(text("SELECT stripe_customer_id FROM comptes WHERE id = :c"),
                      {"c": cid}).scalar() == "cus_new"


# ───────────────────────── T4 — ré-abonnement propre vs vrai doublon ─────────────────────────

def test_t4_reabo_depuis_suspendu_adopte_la_nouvelle_sub(db):
    cid, _ = _compte(db, statut="suspendu", sub="sub_old", cus="cus_4a")
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": "cus_4a", "subscription": "sub_new"}))
    assert facturation.traiter_webhook(db, body, sig)["action"] == "activation"
    row = db.execute(text("SELECT statut, stripe_subscription_id, acces_fin_at FROM comptes WHERE id = :c"),
                     {"c": cid}).mappings().first()
    assert row["statut"] == "actif" and row["stripe_subscription_id"] == "sub_new"
    assert row["acces_fin_at"] is None


def test_t4_reabo_fin_periode_efface_acces_fin(db):
    cid, _ = _compte(db, statut="actif", sub="sub_old", cus="cus_4b", acces_fin_future=True)
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": "cus_4b", "subscription": "sub_new"}))
    facturation.traiter_webhook(db, body, sig)
    row = db.execute(text("SELECT stripe_subscription_id, acces_fin_at FROM comptes WHERE id = :c"),
                     {"c": cid}).mappings().first()
    assert row["stripe_subscription_id"] == "sub_new" and row["acces_fin_at"] is None


def test_t4_vrai_doublon_double_clic_toujours_annule(db, monkeypatch):
    """Régression ROB-C : un compte ACTIF sans fin programmée qui reçoit une 2ᵉ sub = double-clic →
    la neuve est annulée, l'ancienne gardée (pas de double facturation)."""
    cid, _ = _compte(db, statut="actif", sub="sub_old", cus="cus_4c")
    state = {"customer_created": [], "customer_modified": [], "sub_canceled": [],
             "checkout_kwargs": [], "open_invoices": []}
    monkeypatch.setattr(facturation, "_stripe", lambda: _fake_stripe(state))
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": "cus_4c", "subscription": "sub_dup"}))
    assert facturation.traiter_webhook(db, body, sig)["action"] == "doublon_annule"
    assert "sub_dup" in state["sub_canceled"]
    assert db.execute(text("SELECT stripe_subscription_id FROM comptes WHERE id = :c"),
                      {"c": cid}).scalar() == "sub_old"


# ───────────────────────── T5 — admin lit Stripe dans le même mode que l'app ─────────────────────────

def test_t5_lecture_stripe_meme_mode_que_app(monkeypatch):
    from labuse import stripe_lecture
    monkeypatch.delenv("STRIPE_RESTRICTED_KEY", raising=False)
    s = get_settings()
    # app en TEST, clé restreinte en LIVE → on lit en TEST (clé de l'app), jamais le LIVE
    monkeypatch.setattr(s, "stripe_secret_key", "sk_test_app")
    monkeypatch.setattr(s, "stripe_restricted_key", "rk_live_lecture")
    assert stripe_lecture.cle_restreinte() == "sk_test_app"
    # app en LIVE, clé restreinte LIVE → même mode → on garde la clé restreinte (lecture seule)
    monkeypatch.setattr(s, "stripe_secret_key", "sk_live_app")
    assert stripe_lecture.cle_restreinte() == "rk_live_lecture"


# ───────────────────────── T6 — la bascule lecture seule est annoncée (une fois) ─────────────────────────

def test_t6_bascule_lecture_seule_annoncee_une_fois(db):
    from labuse import mailfile
    mailfile.ensure_tables(_engine())
    cid, uid = _compte(db, statut="paiement_requis", paiement_requis_jours=8)   # J+8 > grâce 7 j
    tok = comptes.creer_session(db, uid)
    out = comptes.session_utilisateur(db, tok)
    assert out is not None and out["acces"] == "lecture_seule"
    avertie = db.execute(text("SELECT lecture_seule_avertie_at FROM comptes WHERE id = :c"),
                         {"c": cid}).scalar()
    assert avertie is not None                        # ancre posée
    rows = [r for r in mailfile.lister(_engine(), filtre="tous", compte_id=cid)
            if r["demandeur"] == "job:lecture-seule"]
    assert len(rows) == 1 and rows[0]["mail_key"] == "relance_carte"
    assert rows[0]["params"].get("LIEN_PAIEMENT")
    # deuxième accès : toujours lecture seule, mais PAS de second mail (dédup par l'ancre)
    comptes.session_utilisateur(db, comptes.creer_session(db, uid))
    rows2 = [r for r in mailfile.lister(_engine(), filtre="tous", compte_id=cid)
             if r["demandeur"] == "job:lecture-seule"]
    assert len(rows2) == 1


# ───────────────────────── T7 — l'accès en lecture après non-paiement a une fin ─────────────────────────

def test_t7_acces_lecture_borne_dans_le_temps(db):
    cid, uid = _compte(db, statut="paiement_requis", paiement_requis_jours=40)   # au-delà de 7+30
    tok = comptes.creer_session(db, uid)
    assert comptes.session_utilisateur(db, tok) is None       # accès coupé (borné)
    assert db.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() == "suspendu"
