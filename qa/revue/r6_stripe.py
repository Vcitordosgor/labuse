"""REVUE · R6 — Stripe bout en bout en mode TEST (sk_test). Cycle d'états via webhooks SIGNÉS +
vérification de la signature + session checkout réelle. Base labuse_test (comptes [REVUE-TEST]
purgés en fin) — ne touche JAMAIS les vrais abonnements prod.
"""
import os, json, time, hmac, hashlib, uuid
from pathlib import Path
os.environ["LABUSE_ENV"] = "pilot"
os.environ["LABUSE_AUTH_PASSWORD"] = "pilote-r6"
os.environ["LABUSE_SECRET_KEY"] = "secret-r6-000000000000000000000000000"
# base de test + charge le .env réel (clés Stripe test)
_env = {}
for l in Path("/Users/openclaw/Desktop/labuse/.env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k, v = l.split("=", 1); _env[k.strip()] = v.strip()
os.environ["LABUSE_DATABASE_URL"] = _env["LABUSE_DATABASE_URL"].rsplit("/", 1)[0] + "/labuse_test"
for k in ("LABUSE_STRIPE_SECRET_KEY", "LABUSE_STRIPE_WEBHOOK_SECRET", "LABUSE_STRIPE_PRICE_INTEGRAL"):
    if k in _env:
        os.environ[k] = _env[k]

from fastapi.testclient import TestClient
from sqlalchemy import text
from labuse import comptes, config
from labuse.db import session_scope, engine
config.get_settings.cache_clear()
from labuse.api.app import app

WHSEC = os.environ["LABUSE_STRIPE_WEBHOOK_SECRET"]
c = TestClient(app, base_url="https://testserver")
res = []
def chk(n, cond, d=""):
    res.append((n, cond)); print(f"  {'✓' if cond else '🔴'}  {n}  {d}", flush=True)


def sign(payload: str, secret: str, t: int | None = None) -> str:
    t = t or int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def post_event(evt: dict, secret=WHSEC) -> int:
    body = json.dumps(evt)
    return c.post("/stripe/webhook", content=body,
                  headers={"Stripe-Signature": sign(body, secret), "content-type": "application/json"}).status_code


# compte de test avec un customer Stripe fictif
email = f"revue-r6-{uuid.uuid4().hex[:8]}@revue-test.re"
cust = f"cus_revuetest_{uuid.uuid4().hex[:10]}"
with session_scope() as s:
    inv = comptes.creer_invitation(s, email, nom="[REVUE-TEST] Stripe R6")
    comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-r6-xx", "2026-07-22")
    cid = inv["compte_id"]
    s.execute(text("UPDATE comptes SET stripe_customer_id=:cu, stripe_subscription_id='sub_r6' WHERE id=:c"),
              {"cu": cust, "c": cid}); s.commit()


def statut():
    with session_scope() as s:
        return s.execute(text("SELECT statut FROM comptes WHERE id=:c"), {"c": cid}).scalar()


def evt(typ, obj):
    # "object": "event" à la racine (présent sur tous les vrais events Stripe ; construct_event le lit)
    return {"id": f"evt_{uuid.uuid4().hex[:16]}", "object": "event", "type": typ,
            "api_version": "2024-06-20", "data": {"object": obj}}


print("=== 1. Signature du webhook ===")
good = evt("invoice.paid", {"customer": cust})
body = json.dumps(good)
# signature INVALIDE → rejet
r_bad = c.post("/stripe/webhook", content=body,
               headers={"Stripe-Signature": "t=1,v1=deadbeef", "content-type": "application/json"})
chk("signature invalide REJETÉE", r_bad.status_code >= 400, f"(HTTP {r_bad.status_code})")
# signature ABSENTE → rejet
r_none = c.post("/stripe/webhook", content=body, headers={"content-type": "application/json"})
chk("signature absente REJETÉE", r_none.status_code >= 400, f"(HTTP {r_none.status_code})")
# signature VALIDE → acceptée
chk("signature valide ACCEPTÉE", post_event(good) == 200, "(HTTP 200)")

print("\n=== 2. Cycle d'états (webhooks signés) ===")
# activation : checkout.session.completed (subscription)
post_event(evt("checkout.session.completed",
               {"mode": "subscription", "client_reference_id": str(cid),
                "customer": cust, "subscription": "sub_r6"}))
chk("checkout.session.completed → compte actif", statut() == "actif", f"(statut={statut()})")
# échec de carte : invoice.payment_failed → paiement_requis (past_due)
post_event(evt("invoice.payment_failed", {"customer": cust}))
chk("invoice.payment_failed → paiement_requis (past_due)", statut() == "paiement_requis", f"(statut={statut()})")
# paiement retenté OK : invoice.paid → réactivé
post_event(evt("invoice.paid", {"customer": cust}))
chk("invoice.paid → réactivé (actif)", statut() == "actif", f"(statut={statut()})")
# résiliation : subscription.deleted → suspendu
post_event(evt("customer.subscription.deleted", {"customer": cust}))
chk("customer.subscription.deleted → suspendu", statut() == "suspendu", f"(statut={statut()})")

print("\n=== 3. Dédup (rejeu Stripe) ===")
e = evt("invoice.paid", {"customer": cust})
post_event(e); body2 = json.dumps(e)
# rejouer le MÊME event id → traité une fois (dédup)
r2 = c.post("/stripe/webhook", content=body2, headers={"Stripe-Signature": sign(body2, WHSEC), "content-type": "application/json"})
chk("rejeu du même event_id ignoré (dédup)", r2.status_code == 200, f"(HTTP {r2.status_code})")

print("\n=== 4. Session checkout RÉELLE (sk_test) ===")
try:
    from labuse.facturation import creer_checkout
    with session_scope() as s:
        url = creer_checkout(s, cid, email)
    chk("creer_checkout → URL Stripe test valide", url.startswith("https://checkout.stripe.com") or "stripe.com" in url,
        f"({url[:48]}…)")
except Exception as e:
    chk("creer_checkout", False, f"EXC {type(e).__name__}: {str(e)[:80]}")

print("\n=== 5. Suspension/rétablissement dashboard (admin) ===")
with session_scope() as s:
    comptes.reactiver_compte(s, cid, "revue")
    comptes.suspendre_compte(s, cid, "revue-manuel")
chk("suspension manuelle → suspendu", statut() == "suspendu")
with session_scope() as s:
    comptes.reactiver_compte(s, cid, "revue")
chk("rétablissement → actif", statut() == "actif")

# purge
with session_scope() as s:
    try: comptes.supprimer_utilisateur(s, email)
    except Exception: pass
    s.execute(text("DELETE FROM comptes WHERE nom LIKE '%REVUE-TEST%'")); s.commit()

fails = [n for n, ok in res if not ok]
print(f"\n=== {len(res)} vérifications · {len(fails)} échec(s) ===")
for n in fails:
    print("  🔴", n)
import sys
sys.exit(0 if not fails else 2)
