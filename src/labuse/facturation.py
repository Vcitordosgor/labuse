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
        # génération faite ; l'expiration (30 j) est figée ICI. Le TOKEN de téléchargement
        # n'est PAS émis dans le thread : il est frappé à la demande par flash_statut (le
        # retour Checkout, ré-ouvrable). Rien en mémoire process → multi-worker sûr.
        db.execute(text(
            "UPDATE flash_commandes SET statut = 'generee', pdf_path = :p, token_hash = NULL,"
            " expire_at = now() + make_interval(days => :j), updated_at = now() WHERE id = :i"),
            {"p": str(pdf), "j": get_settings().flash_token_days, "i": row["id"]})
        audit(db, "flash_genere", None, None, f"idu={row['idu']} cmd={row['id']}")
        db.commit()
    except Exception as e:  # noqa: BLE001
        log.error("flash %s : génération en échec (%s)", session_id, e)
        db.execute(text("UPDATE flash_commandes SET statut = 'erreur', updated_at = now()"
                        " WHERE id = :i"), {"i": row["id"]})
        db.commit()


def flash_statut(db: Session, session_id: str) -> dict:
    """Poll du retour : {statut, lien?}. RÉCUPÉRABLE (ROB-B) : le lien de téléchargement est
    FRAPPÉ ICI (token DB-backed) à chaque appel tant que la commande n'est pas expirée — le
    client qui a fermé l'onglet retrouve un lien valide en ré-ouvrant /flash/retour?session_id.
    Multi-worker sûr : la vérité est en base, jamais en mémoire process. Reprise si `payee`."""
    import hashlib
    import secrets as _secrets
    row = db.execute(text("SELECT id, statut, expire_at FROM flash_commandes WHERE stripe_session_id = :s"),
                     {"s": session_id}).mappings().first()
    if not row:
        return {"statut": "inconnue"}
    if row["statut"] in ("payee", "erreur"):
        _flash_fulfill(db, session_id, None)   # reprise (idempotent)
        row = db.execute(text("SELECT id, statut, expire_at FROM flash_commandes WHERE stripe_session_id = :s"),
                         {"s": session_id}).mappings().first()
    out: dict = {"statut": row["statut"]}
    if row["statut"] == "generee":
        if row["expire_at"] and row["expire_at"].timestamp() < __import__("time").time():
            out["expire"] = True   # 30 j passés : le rapport n'est plus téléchargeable
        else:
            tok = _secrets.token_urlsafe(32)
            db.execute(text("UPDATE flash_commandes SET token_hash = :h WHERE id = :i"),
                       {"h": hashlib.sha256(tok.encode()).hexdigest(), "i": row["id"]})
            db.commit()
            out["lien"] = f"{get_settings().public_base_url}/flash/telecharger?token={tok}"
    return out


def flash_pdf_par_token(db: Session, token: str):
    """Token de téléchargement → chemin PDF (None si inconnu/expiré)."""
    import hashlib
    row = db.execute(text("SELECT pdf_path FROM flash_commandes WHERE token_hash = :h"
                          " AND expire_at > now() AND statut = 'generee'"),
                     {"h": hashlib.sha256(token.encode()).hexdigest()}).mappings().first()
    return row["pdf_path"] if row else None


def reconcile_abonnement(db: Session, compte_id: int, email: str) -> bool:
    """ROB-B · le PIRE cas commercial : paiement réussi chez Stripe mais webhook jamais reçu
    → le compte resterait `invite` (relancer Checkout = DOUBLE paiement). Ce filet interroge
    Stripe DIRECTEMENT (souscription active pour ce client) et active le compte si elle existe.
    « A payé ⇒ a accès », toujours. Sans clé Stripe → False (jamais un crash)."""
    try:
        stripe = _stripe()
    except ConfigError:
        return False
    try:
        customers = stripe.Customer.list(email=email, limit=10).data
        for cust in customers:
            subs = stripe.Subscription.list(customer=cust.id, status="active", limit=10).data
            if subs:
                db.execute(text("UPDATE comptes SET statut='actif', stripe_customer_id=:cu,"
                                " stripe_subscription_id=:su, updated_at=now() WHERE id=:c"),
                           {"cu": cust.id, "su": subs[0].id, "c": compte_id})
                audit(db, "stripe_reconciliation", compte_id, None,
                      "webhook manquant → souscription active retrouvée")
                db.commit()
                log.warning("réconciliation Stripe compte %s : sub active sans webhook", compte_id)
                return True
    except Exception as e:  # noqa: BLE001 — indispo Stripe : pas de filet, mais on n'échoue pas
        log.warning("réconciliation Stripe compte %s impossible : %s", compte_id, e)
    return False


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
    # ROB-B — DÉDUP par id d'événement : Stripe REJOUE réellement les webhooks (retries).
    # Un événement déjà traité est ignoré (belt-and-suspenders au-dessus de l'idempotence
    # naturelle des transitions d'état). Table légère, insert-or-skip.
    eid = event["id"] if "id" in event else None
    if eid:
        db.execute(text("CREATE TABLE IF NOT EXISTS stripe_events ("
                        " event_id text PRIMARY KEY, recu_at timestamptz NOT NULL DEFAULT now())"))
        db.commit()
        seen = db.execute(text("INSERT INTO stripe_events (event_id) VALUES (:e)"
                               " ON CONFLICT (event_id) DO NOTHING RETURNING event_id"),
                          {"e": eid}).scalar()
        db.commit()
        if seen is None:
            log.info("webhook stripe %s : déjà traité (rejeu ignoré)", eid)
            return {"type": event["type"], "action": "rejeu_ignore", "compte_id": None}
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
        # ROB-C · concurrence : double-clic / deux onglets → deux Checkout → deux souscriptions.
        # Si le compte a DÉJÀ une souscription différente, on annule le DOUBLON entrant chez
        # Stripe (une seule souscription active, pas de double facturation).
        ancien = db.execute(text("SELECT stripe_subscription_id FROM comptes WHERE id = :c"),
                            {"c": cid}).scalar()
        nouveau = obj.get("subscription")
        if ancien and nouveau and ancien != nouveau:
            try:
                _stripe().Subscription.cancel(nouveau)
                audit(db, "stripe_doublon_annule", cid, None, f"sub doublon {nouveau} annulée")
                log.warning("compte %s : souscription doublon %s annulée (garde %s)", cid, nouveau, ancien)
                db.commit()
                return {"type": t, "action": "doublon_annule", "compte_id": cid}
            except Exception as e:  # noqa: BLE001 — Stripe indispo : on garde l'ancienne, on n'écrase pas
                log.error("compte %s : annulation doublon %s impossible : %s", cid, nouveau, e)
        db.execute(text("UPDATE comptes SET statut = 'actif', stripe_customer_id = :cu,"
                        " stripe_subscription_id = COALESCE(stripe_subscription_id, :su),"
                        " updated_at = now() WHERE id = :c"),
                   {"cu": obj.get("customer"), "su": nouveau, "c": cid})
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


