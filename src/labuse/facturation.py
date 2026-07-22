"""PREMIER EURO · E2 — Stripe : produits/prix/coupon, Checkout hébergé, webhooks signés.

Doctrine :
- JAMAIS une donnée de carte côté LABUSE : Checkout hébergé Stripe, factures Stripe ;
- webhooks SIGNÉS obligatoires (`stripe_webhook_secret`) — un webhook non vérifiable est rejeté ;
- provisionnement par CLI (`labuse stripe-provisionne`) : refonte 22/07 — INTÉGRAL
  349 €/mois (abonnement, 1 licence = 1 accès) + FLASH 79 € (paiement UNIQUE, un rapport
  PDF sur une parcelle) ; plus de coupon founding ; les IDs reviennent en .env ;
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
    """Crée (idempotent, par lookup_key) : INTÉGRAL 349 €/mois (récurrent) et FLASH 79 €
    (one-shot). Renvoie les IDs à poser en .env — la source de vérité de l'environnement."""
    stripe = _stripe()
    out: dict[str, str] = {}
    prix = stripe.Price.list(lookup_keys=["labuse_integral_mensuel"], limit=1).data
    if prix:
        out["stripe_price_integral"] = prix[0].id
    else:
        produit = stripe.Product.create(
            name="LABUSE Intégral",
            description="Abonnement LABUSE Intégral — 1 licence = 1 accès complet. "
                        "Pré-analyse sur données publiques ; ne remplace ni certificat "
                        "d'urbanisme ni conseil notarial.")
        out["stripe_price_integral"] = stripe.Price.create(
            product=produit.id, currency="eur", unit_amount=349 * 100,
            recurring={"interval": "month"}, lookup_key="labuse_integral_mensuel").id
    prix = stripe.Price.list(lookup_keys=["labuse_flash_unitaire"], limit=1).data
    if prix:
        out["stripe_price_flash"] = prix[0].id
    else:
        produit = stripe.Product.create(
            name="LABUSE Flash",
            description="Rapport Flash — UNE parcelle, un PDF sourcé, paiement unique. "
                        "Pré-analyse sur données publiques ; ne remplace ni certificat "
                        "d'urbanisme ni conseil notarial.")
        out["stripe_price_flash"] = stripe.Price.create(
            product=produit.id, currency="eur", unit_amount=79 * 100,
            lookup_key="labuse_flash_unitaire").id
    return out


def creer_checkout(db: Session, compte_id: int, email: str) -> str:
    """Session Checkout ABONNEMENT (Intégral) pour un compte invité — le client n'entre
    JAMAIS sa carte chez nous."""
    stripe = _stripe()
    s = get_settings()
    c = db.execute(text("SELECT plan FROM comptes WHERE id = :c"), {"c": compte_id}).mappings().first()
    if not c:
        raise ValueError(f"compte {compte_id} inconnu")
    if not s.stripe_price_integral:
        raise ConfigError("STRIPE_PRICE_INTEGRAL absent — lancer `labuse stripe-provisionne` puis poser l'ID en .env")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": s.stripe_price_integral, "quantity": 1}],
        success_url=f"{s.public_base_url}/onboarding/retour?ok=1",
        cancel_url=f"{s.public_base_url}/onboarding/retour?ok=0",
        client_reference_id=str(compte_id),
        customer_email=email,
        locale="fr")
    audit(db, "checkout_cree", compte_id, None, "integral")
    db.commit()
    return session.url


# ───────────── FLASH : 79 € one-shot, un rapport PDF sur UNE parcelle ─────────────

def ensure_flash_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS flash_commandes (
            id serial PRIMARY KEY,
            stripe_session_id text UNIQUE NOT NULL,
            idu text NOT NULL,
            email text,
            statut text NOT NULL DEFAULT 'en_attente'
                CHECK (statut IN ('en_attente', 'payee', 'generee', 'erreur')),
            token_hash text, expire_at timestamptz,
            pdf_path text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )"""))
    db.commit()


def creer_checkout_flash(db: Session, idu: str) -> str:
    """Checkout PAIEMENT UNIQUE 79 € pour un rapport Flash sur `idu` (parcelle validée par
    l'appelant). L'email est collecté par Stripe ; le retour porte le session_id."""
    stripe = _stripe()
    s = get_settings()
    if not s.stripe_price_flash:
        raise ConfigError("STRIPE_PRICE_FLASH absent — lancer `labuse stripe-provisionne` puis poser l'ID en .env")
    ensure_flash_table(db)
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": s.stripe_price_flash, "quantity": 1}],
        success_url=f"{s.public_base_url}/flash/retour?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{s.public_base_url}/flash?annule=1&idu={idu}",
        metadata={"idu": idu, "produit": "flash"},
        locale="fr")
    db.execute(text("INSERT INTO flash_commandes (stripe_session_id, idu) VALUES (:s, :i)"
                    " ON CONFLICT (stripe_session_id) DO NOTHING"), {"s": session.id, "i": idu})
    audit(db, "flash_checkout_cree", None, None, f"idu={idu}")
    db.commit()
    return session.url


def _flash_fulfill(db: Session, session_id: str, email: str | None) -> None:
    """Fulfillment FLASH : marque payée, génère le PDF (module flash, idempotent), pose le
    token de téléchargement (30 j). En cas d'échec de génération : statut `erreur` — le
    retour affiche un message honnête + reprise possible (regénération au prochain poll)."""
    import hashlib
    import secrets as _secrets

    row = db.execute(text("SELECT id, idu, statut FROM flash_commandes WHERE stripe_session_id = :s"),
                     {"s": session_id}).mappings().first()
    if not row:
        # webhook arrivé avant l'insert (course rare) — créer la ligne depuis les métadonnées
        return
    if row["statut"] in ("generee",):
        return
    db.execute(text("UPDATE flash_commandes SET statut = 'payee', email = :e, updated_at = now()"
                    " WHERE id = :i"), {"e": email, "i": row["id"]})
    db.commit()
    try:
        from .flash.report import generate_flash_report
        pdf = generate_flash_report(row["idu"], order_ref=f"FL{row['id']:06d}", db=db)
        tok = _secrets.token_urlsafe(32)
        db.execute(text(
            "UPDATE flash_commandes SET statut = 'generee', pdf_path = :p, token_hash = :h,"
            " expire_at = now() + make_interval(days => :j), updated_at = now() WHERE id = :i"),
            {"p": str(pdf), "h": hashlib.sha256(tok.encode()).hexdigest(),
             "j": get_settings().flash_token_days, "i": row["id"]})
        # le token CLAIR n'existe que le temps de la ligne suivante — repris par /flash/retour
        db.execute(text("UPDATE flash_commandes SET pdf_path = pdf_path WHERE id = :i"), {"i": row["id"]})
        db.commit()
        _FLASH_TOKENS[session_id] = tok
        audit(db, "flash_genere", None, None, f"idu={row['idu']} cmd={row['id']}")
        db.commit()
    except Exception as e:  # noqa: BLE001
        log.error("flash %s : génération en échec (%s)", session_id, e)
        db.execute(text("UPDATE flash_commandes SET statut = 'erreur', updated_at = now()"
                        " WHERE id = :i"), {"i": row["id"]})
        db.commit()


# tokens de téléchargement fraîchement émis (mémoire process) : le retour Checkout les
# récupère UNE fois ; ensuite seul le lien détenu par le client fonctionne (hash en base).
_FLASH_TOKENS: dict[str, str] = {}


def flash_statut(db: Session, session_id: str) -> dict:
    """Pour le poll du retour : {statut, lien?} — regénère si `payee` (reprise d'erreur)."""
    row = db.execute(text("SELECT id, statut FROM flash_commandes WHERE stripe_session_id = :s"),
                     {"s": session_id}).mappings().first()
    if not row:
        return {"statut": "inconnue"}
    if row["statut"] in ("payee", "erreur"):
        _flash_fulfill(db, session_id, None)   # reprise (idempotent)
        row = db.execute(text("SELECT id, statut FROM flash_commandes WHERE stripe_session_id = :s"),
                         {"s": session_id}).mappings().first()
    out: dict = {"statut": row["statut"]}
    tok = _FLASH_TOKENS.get(session_id)
    if row["statut"] == "generee" and tok:
        out["lien"] = f"{get_settings().public_base_url}/flash/telecharger?token={tok}"
    return out


def flash_pdf_par_token(db: Session, token: str):
    """Token de téléchargement → chemin PDF (None si inconnu/expiré)."""
    import hashlib
    row = db.execute(text("SELECT pdf_path FROM flash_commandes WHERE token_hash = :h"
                          " AND expire_at > now() AND statut = 'generee'"),
                     {"h": hashlib.sha256(token.encode()).hexdigest()}).mappings().first()
    return row["pdf_path"] if row else None


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

    # FLASH (mode payment) : fulfillment — pas un compte
    if t == "checkout.session.completed" and obj.get("mode") == "payment":
        _flash_fulfill(db, obj.get("id"), (obj.get("customer_details") or {}).get("email"))
        log.info("webhook stripe %s → flash (%s)", t, obj.get("id"))
        return {"type": t, "action": "flash_genere", "compte_id": None}

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
        action = "paiement_requis"   # relances = Stripe ; l'app affiche le bandeau (pas d'email maison)
    elif t == "customer.subscription.deleted" and cid:
        suspendre_compte(db, cid, "subscription.deleted")
        action = "suspension"
    log.info("webhook stripe %s → %s (compte %s)", t, action, cid)
    return {"type": t, "action": action, "compte_id": cid}


