"""PREMIER EURO · E2 — Stripe : produits/prix/coupon, Checkout hébergé, webhooks signés.

Doctrine :
- JAMAIS une donnée de carte côté LABUSE : Checkout hébergé Stripe, factures Stripe ;
- webhooks SIGNÉS obligatoires (`stripe_webhook_secret`) — un webhook non vérifiable est rejeté ;
- provisionnement par CLI (`labuse stripe-provisionne`) : produits Indé 290 €/Pro 490 €,
  coupon founding −50 % `duration=forever` (à vie TANT QUE l'abonnement reste actif — c'est
  la sémantique Stripe : le coupon meurt avec la souscription) ; les IDs reviennent en .env ;
- cycle : checkout.session.completed → compte `actif` · invoice.payment_failed →
  `paiement_requis` (relances Stripe font le reste) · customer.subscription.deleted →
  `suspendu` · invoice.paid → retour `actif`.
- Sans clé : chaque fonction lève ConfigError explicite — jamais un bouton de paiement factice.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from .comptes import PLANS, audit, reactiver_compte, suspendre_compte
from .config import get_settings

log = logging.getLogger("labuse.facturation")


class ConfigError(RuntimeError):
    pass


def _stripe():
    s = get_settings()
    if not s.stripe_secret_key:
        raise ConfigError("STRIPE_SECRET_KEY absente — E2 attend la clé mode TEST (prérequis Vic)")
    import stripe
    stripe.api_key = s.stripe_secret_key
    return stripe


def provisionner() -> dict:
    """Crée (idempotent, par recherche de lookup_key) produits + prix + coupon founding.
    Renvoie les IDs à poser en .env — la source de vérité de l'environnement."""
    stripe = _stripe()
    out: dict[str, str] = {}
    for key, p in PLANS.items():
        lookup = f"labuse_{key}_mensuel"
        prix = stripe.Price.list(lookup_keys=[lookup], limit=1).data
        if prix:
            out[f"stripe_price_{key}"] = prix[0].id
            continue
        produit = stripe.Product.create(
            name=f"LABUSE {p['label']}",
            description=f"Abonnement LABUSE {p['label']} — {p['sieges']} siège(s). "
                        "Pré-analyse sur données publiques ; ne remplace ni certificat "
                        "d'urbanisme ni conseil notarial.")
        prix = stripe.Price.create(product=produit.id, currency="eur",
                                   unit_amount=p["eur_mois"] * 100,
                                   recurring={"interval": "month"}, lookup_key=lookup)
        out[f"stripe_price_{key}"] = prix.id
    # coupon founding : −50 % forever = toute la VIE DE LA SOUSCRIPTION (résiliation = perte)
    coupons = stripe.Coupon.list(limit=100).data
    founding = next((c for c in coupons if c.name == "Founding −50 %"), None)
    if not founding:
        founding = stripe.Coupon.create(name="Founding −50 %", percent_off=50, duration="forever")
    out["stripe_coupon_founding"] = founding.id
    return out


def creer_checkout(db: Session, compte_id: int, email: str) -> str:
    """Session Checkout hébergée pour un compte invité — founding appliqué si le compte l'est.
    Renvoie l'URL Stripe (le client n'entre JAMAIS sa carte chez nous)."""
    stripe = _stripe()
    s = get_settings()
    c = db.execute(text("SELECT plan, founding, stripe_customer_id FROM comptes WHERE id = :c"),
                   {"c": compte_id}).mappings().first()
    if not c:
        raise ValueError(f"compte {compte_id} inconnu")
    price = {"inde": s.stripe_price_inde, "pro": s.stripe_price_pro}[c["plan"]]
    if not price:
        raise ConfigError("stripe_price_* absents — lancer `labuse stripe-provisionne` puis poser les IDs en .env")
    kwargs: dict = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": f"{s.public_base_url}/onboarding/retour?ok=1",
        "cancel_url": f"{s.public_base_url}/onboarding/retour?ok=0",
        "client_reference_id": str(compte_id),
        "customer_email": email,
        "locale": "fr",
    }
    if c["founding"]:
        if not s.stripe_coupon_founding:
            raise ConfigError("stripe_coupon_founding absent (.env)")
        kwargs["discounts"] = [{"coupon": s.stripe_coupon_founding}]
    session = stripe.checkout.Session.create(**kwargs)
    audit(db, "checkout_cree", compte_id, None, f"founding={c['founding']}")
    db.commit()
    return session.url


def traiter_webhook(db: Session, payload: bytes, signature: str | None) -> dict:
    """Webhook SIGNÉ — signature invalide/absente = rejet sec. Idempotent par nature
    (les transitions d'état le sont). Renvoie {type, action} pour le log/l'alerte."""
    # la vérification de signature n'a besoin QUE du secret webhook (pas de la clé API) —
    # le cycle d'états se teste donc intégralement sans compte Stripe.
    import stripe
    s = get_settings()
    if not s.stripe_webhook_secret:
        raise ConfigError("STRIPE_WEBHOOK_SECRET absente — le webhook non signé est REFUSÉ")
    event = stripe.Webhook.construct_event(payload, signature or "", s.stripe_webhook_secret)
    t = event["type"]
    obj = event["data"]["object"]
    # StripeObject (v8+) n'expose pas .get — dict natif pour un accès uniforme
    obj = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)

    def _compte_id() -> int | None:
        ref = obj.get("client_reference_id")
        if ref:
            return int(ref)
        cust = obj.get("customer")
        if cust:
            r = db.execute(text("SELECT id FROM comptes WHERE stripe_customer_id = :c"),
                           {"c": cust}).scalar()
            return int(r) if r else None
        return None

    cid = _compte_id()
    action = "ignore"
    if t == "checkout.session.completed" and cid:
        db.execute(text("UPDATE comptes SET statut = 'actif', stripe_customer_id = :cu,"
                        " stripe_subscription_id = :su, updated_at = now() WHERE id = :c"),
                   {"cu": obj.get("customer"), "su": obj.get("subscription"), "c": cid})
        audit(db, "stripe_activation", cid, None, "checkout.session.completed")
        db.commit()
        action = "activation"
    elif t == "invoice.paid" and cid:
        row = db.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar()
        if row in ("paiement_requis", "suspendu"):
            reactiver_compte(db, cid, "invoice.paid")
        action = "paiement_ok"
    elif t == "invoice.payment_failed" and cid:
        # relances Stripe d'abord — l'app passe « paiement requis » (bandeau, pas un 500)
        db.execute(text("UPDATE comptes SET statut = 'paiement_requis', updated_at = now()"
                        " WHERE id = :c AND statut = 'actif'"), {"c": cid})
        audit(db, "stripe_paiement_echec", cid, None)
        db.commit()
        _prevenir(db, cid, "paiement_requis")
        action = "paiement_requis"
    elif t == "customer.subscription.deleted" and cid:
        suspendre_compte(db, cid, "subscription.deleted")
        _prevenir(db, cid, "suspension")
        action = "suspension"
    log.info("webhook stripe %s → %s (compte %s)", t, action, cid)
    return {"type": t, "action": action, "compte_id": cid}


def _prevenir(db: Session, compte_id: int, quoi: str) -> None:
    """Email au(x) titulaire(s) — jamais bloquant pour le webhook."""
    try:
        from .mailer import envoyer_paiement_requis, envoyer_suspension
        emails = [r[0] for r in db.execute(text(
            "SELECT email FROM utilisateurs WHERE compte_id = :c AND statut = 'actif'"
            " AND role IN ('titulaire', 'admin')"), {"c": compte_id})]
        for e in emails:
            (envoyer_paiement_requis if quoi == "paiement_requis" else envoyer_suspension)(e)
    except Exception as exc:  # noqa: BLE001
        log.warning("email %s compte %s non parti : %s", quoi, compte_id, exc)
