"""NU4-B — le bouton « Régulariser » (bandeau/app) sur un compte EN DÉFAUT DE PAIEMENT.

Flux réel : /moi.lien_regularisation → /onboarding/paiement → creer_checkout() → NOUVELLE Checkout
Session mode=subscription (une 2e souscription). Or le compte paiement_requis porte DÉJÀ une
souscription (l'ancienne, past_due). Au webhook checkout.session.completed, la garde ROB-C
(facturation.py:437-457) voit `ancien != nouveau` et ANNULE la NOUVELLE souscription — en gardant
l'ANCIENNE (impayée). On vérifie : action retournée, souscription neuve annulée côté Stripe, statut
du compte APRÈS. Mode TEST. On appelle traiter_webhook EN PROCESS (pas de serveur requis).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
import sqlalchemy as sa
import stripe
from labuse.db import session_scope

ENV = {}
for line in (ROOT / ".env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k.startswith("LABUSE_"):
        ENV[k.strip()] = v.strip()
stripe.api_key = ENV["LABUSE_STRIPE_SECRET_KEY"]
assert stripe.api_key.startswith("sk_test_")
ENGINE = sa.create_engine(ENV["LABUSE_DATABASE_URL"])
PRICE_INTEGRAL = ENV["LABUSE_STRIPE_PRICE_INTEGRAL"]

out = {}

# 1) le client EXISTANT (déjà une souscription past_due) : on fabrique un client + une souscription
#    réelle "neuve" (ce que créerait la 2e Checkout). L'ANCIENNE est simulée par un id arbitraire.
cust = stripe.Customer.create(email="nu4b-regul@labuse.test", name="[CT-TEST] NU4B Regul")
pm = stripe.PaymentMethod.attach(stripe.PaymentMethod.create(
    type="card", card={"token": "tok_visa"}).id, customer=cust.id)
stripe.Customer.modify(cust.id, invoice_settings={"default_payment_method": pm.id})
sub_new = stripe.Subscription.create(customer=cust.id, items=[{"price": PRICE_INTEGRAL}],
                                     collection_method="charge_automatically",
                                     expand=["latest_invoice"])
_li = sub_new["latest_invoice"] if "latest_invoice" in sub_new else None
out["sous_neuve"] = {"id": sub_new.id, "status_initial": sub_new.status,
                     "1re_facture_payee_eur": (_li["amount_paid"] / 100 if _li else None)}

# 2) compte local EN DÉFAUT DE PAIEMENT avec une ANCIENNE souscription déjà posée
import datetime as _dt
with ENGINE.begin() as c:
    cid = c.execute(sa.text(
        "INSERT INTO comptes (nom, plan, statut, stripe_customer_id, stripe_subscription_id,"
        " paiement_requis_at) VALUES ('[CT-TEST] NU4B Regul','integral','paiement_requis',:cu,"
        " 'sub_ANCIENNE_impayee', now() - interval '1 day') RETURNING id"), {"cu": cust.id}).scalar()
    c.execute(sa.text("INSERT INTO utilisateurs (compte_id,email,hash,role,statut) "
                      "VALUES (:c,:e,'x','titulaire','actif')"),
              {"c": cid, "e": f"nu4b-regul+{cid}@labuse.test"})
out["compte_id"] = cid

with ENGINE.begin() as c:
    out["statut_avant"] = c.execute(sa.text(
        "SELECT statut FROM comptes WHERE id=:c"), {"c": cid}).scalar()

# 3) webhook checkout.session.completed : NOUVELLE souscription pour ce compte
import hashlib
import hmac
import time
from labuse.facturation import traiter_webhook
evt = {"id": f"evt_nu4b_regul_{int(time.time())}", "object": "event",
       "type": "checkout.session.completed",
       "data": {"object": {"mode": "subscription", "client_reference_id": str(cid),
                           "customer": cust.id, "subscription": sub_new.id}}}
payload = json.dumps(evt).encode()
ts = int(time.time())
sig = hmac.new(ENV["LABUSE_STRIPE_WEBHOOK_SECRET"].encode(),
               f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
with session_scope() as db:
    res = traiter_webhook(db, payload, f"t={ts},v1={sig}")
out["webhook_action"] = res

# 4) états APRÈS
with ENGINE.begin() as c:
    r = c.execute(sa.text("SELECT statut, stripe_subscription_id FROM comptes WHERE id=:c"),
                  {"c": cid}).mappings().first()
    out["compte_apres"] = dict(r)
sub_new_apres = stripe.Subscription.retrieve(sub_new.id)
out["sous_neuve_apres"] = {"id": sub_new.id, "status": sub_new_apres.status,
                           "canceled_at": (sub_new_apres["canceled_at"] if "canceled_at" in sub_new_apres else None)}

out["verdict"] = (
    "BUG CONFIRMÉ : la souscription NEUVE (1re facture payée) est "
    f"{sub_new_apres.status}, le compte reste « {out['compte_apres']['statut']} » et garde "
    f"l'ancienne souscription « {out['compte_apres']['stripe_subscription_id']} » (impayée). "
    "→ le client a payé via « Régulariser » mais reste bloqué / non régularisé."
    if sub_new_apres.status == "canceled" and out["compte_apres"]["statut"] == "paiement_requis"
    else f"résultat : {res['action']} — statut {out['compte_apres']['statut']}, "
         f"neuve {sub_new_apres.status} (à interpréter)")
print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
