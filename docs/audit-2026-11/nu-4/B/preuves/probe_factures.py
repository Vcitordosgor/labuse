"""NU4-B — sonde LECTURE des factures Stripe (mode TEST uniquement).

Reproduit FIDÈLEMENT le flux de l'app pour observer la FACTURE :
- abonnement Intégral : l'app crée une Checkout Session mode=subscription SANS pied de facture,
  puis (dans le webhook checkout.session.completed) pose le pied sur le CLIENT via Customer.modify.
  → on vérifie si la PREMIÈRE facture (finalisée au paiement) porte la mention 293 B, et si la
  facture du cycle SUIVANT la porte.
- Flash : Checkout mode=payment avec invoice_creation.footer = mention (LEX-D).

Aucune écriture dans l'app. Clé TEST lue du .env (sk_test_). N'exécute rien en LIVE.
"""
import json
import os
import pathlib

import stripe

ROOT = pathlib.Path(__file__).resolve().parents[5]
ENV = {}
for line in (ROOT / ".env").read_text().splitlines():
    if line.startswith("LABUSE_STRIPE") or line.startswith("LABUSE_"):
        k, _, v = line.partition("=")
        ENV[k.strip()] = v.strip()

stripe.api_key = ENV["LABUSE_STRIPE_SECRET_KEY"]
assert stripe.api_key.startswith("sk_test_"), "SÉCURITÉ: clé non-test, abandon"
PRICE_INTEGRAL = ENV["LABUSE_STRIPE_PRICE_INTEGRAL"]
PRICE_FLASH = ENV["LABUSE_STRIPE_PRICE_FLASH"]
MENTION = ("TVA non applicable, art. 293 B du CGI. "
           "LABUSE — pré-analyse foncière sur données publiques.")

out = {"mode": "test", "livemode": None, "integral": {}, "flash": {}}


def inv_brief(inv):
    inv = inv.to_dict() if hasattr(inv, "to_dict") else dict(inv)
    return {
        "id": inv.get("id"),
        "number": inv.get("number"),
        "status": inv.get("status"),
        "created": inv.get("created"),
        "footer": inv.get("footer"),
        "amount_due": inv.get("amount_due"),
        "amount_paid": inv.get("amount_paid"),
        "currency": inv.get("currency"),
        "customer_email": inv.get("customer_email"),
        "hosted_invoice_url": bool(inv.get("hosted_invoice_url")),
        "invoice_pdf": bool(inv.get("invoice_pdf")),
        "tax": inv.get("tax"),
        "total_tax_amounts": inv.get("total_tax_amounts"),
    }


# ───────────── ABONNEMENT INTÉGRAL (reproduction du flux app) ─────────────
# 1) l'app ne crée PAS le client à la main : Checkout le fait. On reproduit avec une
#    Customer "neuve" SANS pied (exactement l'état au moment où Stripe finalise la 1re facture).
import time as _t
clock = stripe.test_helpers.TestClock.create(frozen_time=int(_t.time()), name="nu4b")
cust = stripe.Customer.create(email="nu4b-integral@labuse.test", name="[CT-TEST] NU4B Integral",
                              test_clock=clock.id)
# carte test attachée AVANT la souscription (comme le fait Checkout : PM collecté puis sub créée,
# SANS pied de facture sur le client à cet instant).
pm = stripe.PaymentMethod.attach(stripe.PaymentMethod.create(
    type="card", card={"token": "tok_visa"}).id, customer=cust.id)
stripe.Customer.modify(cust.id, invoice_settings={"default_payment_method": pm.id})
sub = stripe.Subscription.create(
    customer=cust.id, items=[{"price": PRICE_INTEGRAL}],
    collection_method="charge_automatically",
    expand=["latest_invoice"])
first_inv = stripe.Invoice.retrieve(sub["latest_invoice"]["id"])
out["livemode"] = bool(first_inv.to_dict().get("livemode"))
out["integral"]["premiere_facture_AVANT_pied_client"] = inv_brief(first_inv)

# 2) le webhook pose ENSUITE le pied sur le CLIENT (Customer.modify)
stripe.Customer.modify(cust.id, invoice_settings={"footer": MENTION})

# 3) facture du cycle SUIVANT : on avance l'horloge de test de ~32 jours
clock_id = clock.id
stripe.test_helpers.TestClock.advance(clock_id, frozen_time=int(_t.time()) + 32 * 86400)
for _ in range(30):
    c = stripe.test_helpers.TestClock.retrieve(clock_id)
    if c["status"] == "ready":
        break
    _t.sleep(2)
invs = stripe.Invoice.list(customer=cust.id, limit=10)["data"]
out["integral"]["nb_factures_apres_cycle"] = len(invs)
out["integral"]["factures_apres_pied_client"] = [inv_brief(i) for i in invs]

# ───────────── FLASH (reproduction LEX-D : footer sur la facture one-shot) ─────────────
# l'app passe invoice_creation.footer dans la Checkout Session (mode=payment). On ne peut pas
# compléter un Checkout hébergé sans navigateur ; on reproduit l'effet FACTURE : PaymentIntent payé
# + Invoice one-shot portant le footer (ce que Stripe génère quand invoice_creation=enabled).
fcust = stripe.Customer.create(email="nu4b-flash@labuse.test", name="[CT-TEST] NU4B Flash")
finv = stripe.Invoice.create(customer=fcust.id, footer=MENTION, auto_advance=False,
                             collection_method="charge_automatically")
stripe.InvoiceItem.create(customer=fcust.id, amount=7900, currency="eur",
                          description="LABUSE Flash — 1 parcelle (reconstruction LEX-D)",
                          invoice=finv.id)
finv = stripe.Invoice.finalize_invoice(finv.id)
out["flash"]["facture_flash"] = inv_brief(finv)

print(json.dumps(out, indent=2, ensure_ascii=False))
