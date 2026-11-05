"""NU4-B — sonde du CYCLE DE VIE via les webhooks Stripe signés (DB locale de dev = bac à sable).

On POSTe des événements Stripe SIGNÉS (secret .env) au serveur local /stripe/webhook et on lit la
table `comptes` avant/après. Reproduit la vraie mécanique (facturation.traiter_webhook) sans toucher
le code. Comptes de TEST (@labuse.test). Prouve : activation, grâce, résiliation (fin de période vs
immédiate), rétablissement, + les PIÈGES de transition (essai non effacé au paiement ; acces_fin_at
non effacé à la ré-souscription).
"""
import hashlib
import hmac
import json
import os
import pathlib
import time
import urllib.request

import sqlalchemy as sa

ROOT = pathlib.Path(__file__).resolve().parents[5]
os.environ.setdefault("PYTHONPATH", str(ROOT / "src"))
ENV = {}
for line in (ROOT / ".env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k.startswith("LABUSE_"):
        ENV[k.strip()] = v.strip()

WH_SECRET = ENV["LABUSE_STRIPE_WEBHOOK_SECRET"]
DB_URL = ENV["LABUSE_DATABASE_URL"]
URL = "http://127.0.0.1:9640/stripe/webhook"
ENGINE = sa.create_engine(DB_URL)

TRACE = []


def post_event(evt: dict) -> dict:
    payload = json.dumps(evt)
    ts = int(time.time())
    sig = hmac.new(WH_SECRET.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        URL, data=payload.encode(),
        headers={"Content-Type": "application/json", "Stripe-Signature": f"t={ts},v1={sig}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return {"http": r.status, "body": json.loads(r.read().decode())}


def ev(etype, obj, eid=None):
    return {"id": eid or f"evt_nu4b_{etype}_{int(time.time()*1000)%10_000_000}",
            "object": "event", "type": etype, "data": {"object": obj}}


def compte_row(cid):
    with ENGINE.begin() as c:
        r = c.execute(sa.text(
            "SELECT statut, stripe_customer_id, stripe_subscription_id, essai_expire_at,"
            " paiement_requis_at, acces_fin_at FROM comptes WHERE id=:c"), {"c": cid}).mappings().first()
    return dict(r) if r else None


def mk_compte(nom, statut="invite", essai=None, sub=None, cust=None, acces_fin=None, pr_at=None):
    with ENGINE.begin() as c:
        cid = c.execute(sa.text(
            "INSERT INTO comptes (nom, plan, statut, essai_expire_at, stripe_subscription_id,"
            " stripe_customer_id, acces_fin_at, paiement_requis_at)"
            " VALUES (:n,'integral',:s,:e,:su,:cu,:af,:pr) RETURNING id"),
            {"n": f"[CT-TEST] {nom}", "s": statut, "e": essai, "su": sub, "cu": cust,
             "af": acces_fin, "pr": pr_at}).scalar()
        c.execute(sa.text(
            "INSERT INTO utilisateurs (compte_id,email,hash,role,statut,cgv_acceptees_at,cgv_version)"
            " VALUES (:c,:e,'x','titulaire','actif',now(),'t')"),
            {"c": cid, "e": f"nu4b+{cid}@labuse.test"})
    return cid


def step(titre, cid, etype, obj):
    avant = compte_row(cid)
    resp = post_event(ev(etype, obj))
    apres = compte_row(cid)
    TRACE.append({"etape": titre, "compte": cid, "event": etype,
                  "reponse_app": resp["body"], "avant": _fmt(avant), "apres": _fmt(apres)})
    return apres


def _fmt(r):
    if not r:
        return None
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()}


import datetime as _dt
now = int(time.time())
FUTURE = now + 20 * 86400          # epoch (pour les payloads d'event Stripe)
PAST = now - 1 * 86400
DT_FUTURE = _dt.datetime.fromtimestamp(FUTURE, tz=_dt.timezone.utc)   # datetimes (colonnes DB)
DT_PAST = _dt.datetime.fromtimestamp(PAST, tz=_dt.timezone.utc)
RUN = str(now)

# ── 1) PREMIER PAIEMENT : invite → actif (checkout.session.completed) ──
c1 = mk_compte("premier-paiement", statut="invite")
step("1. Premier paiement (checkout.session.completed)", c1, "checkout.session.completed",
     {"mode": "subscription", "client_reference_id": str(c1), "customer": "cus_nu4b_1_"+RUN,
      "subscription": "sub_nu4b_1_"+RUN})

# ── 2) CARTE REFUSÉE : actif → paiement_requis (ancre de grâce) ──
c2 = mk_compte("carte-refusee", statut="actif", sub="sub_nu4b_2_"+RUN, cust="cus_nu4b_2_"+RUN)
step("2. Carte refusée (invoice.payment_failed)", c2, "invoice.payment_failed",
     {"id": "in_nu4b_2", "customer": "cus_nu4b_2_"+RUN, "hosted_invoice_url": "https://pay.stripe/x"})

# ── 3) RÉGULARISATION : paiement_requis → actif (invoice.paid) ──
step("3. Régularisation (invoice.paid)", c2, "invoice.paid",
     {"id": "in_nu4b_2b", "customer": "cus_nu4b_2_"+RUN})

# ── 4) RÉSILIATION fin de période payée (current_period_end futur) → acces_fin_at posé ──
c4 = mk_compte("resiliation-fin-periode", statut="actif", sub="sub_nu4b_4_"+RUN, cust="cus_nu4b_4_"+RUN)
step("4. Résiliation en fin de période (subscription.deleted, période future)", c4,
     "customer.subscription.deleted",
     {"id": "sub_nu4b_4_"+RUN, "customer": "cus_nu4b_4_"+RUN, "current_period_end": FUTURE})

# ── 5) RÉSILIATION immédiate (pas de période future) → suspendu ──
c5 = mk_compte("resiliation-immediate", statut="actif", sub="sub_nu4b_5_"+RUN, cust="cus_nu4b_5_"+RUN)
step("5. Résiliation immédiate (subscription.deleted, pas de période)", c5,
     "customer.subscription.deleted", {"id": "sub_nu4b_5_"+RUN, "customer": "cus_nu4b_5_"+RUN})

# ── 6) PIÈGE A : essai EXPIRÉ qui paie → essai_expire_at reste au PASSÉ (statut actif) ──
c6 = mk_compte("essai-expire-paye", statut="suspendu", essai=DT_PAST)
step("6. PIÈGE essai-expiré qui paie (checkout.session.completed)", c6, "checkout.session.completed",
     {"mode": "subscription", "client_reference_id": str(c6), "customer": "cus_nu4b_6_"+RUN,
      "subscription": "sub_nu4b_6_"+RUN})

# ── 7) PIÈGE B : ré-souscription APRÈS résiliation fin-de-période → acces_fin_at reste ──
c7 = mk_compte("resub-apres-resiliation", statut="actif", sub="sub_nu4b_7old_"+RUN,
               cust="cus_nu4b_7_"+RUN, acces_fin=DT_FUTURE)
step("7. PIÈGE ré-souscription (checkout.session.completed) avec acces_fin_at futur présent", c7,
     "checkout.session.completed",
     {"mode": "subscription", "client_reference_id": str(c7), "customer": "cus_nu4b_7_"+RUN,
      "subscription": "sub_nu4b_7new_"+RUN})

# ── 8) REJEU (idempotence) : même event id deux fois ──
c8 = mk_compte("rejeu", statut="invite")
e8 = ev("checkout.session.completed",
        {"mode": "subscription", "client_reference_id": str(c8), "customer": "cus_nu4b_8_"+RUN,
         "subscription": "sub_nu4b_8_"+RUN}, eid="evt_nu4b_rejeu_"+RUN)
r1 = post_event(e8)
r2 = post_event(e8)
TRACE.append({"etape": "8. Rejeu même event (idempotence)", "compte": c8,
              "reponse_1": r1["body"], "reponse_2": r2["body"], "apres": _fmt(compte_row(c8))})

print(json.dumps({"trace": TRACE}, indent=2, ensure_ascii=False))
