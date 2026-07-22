"""PREMIER EURO — emails transactionnels (invitation, reset, suspension).

Transport : **Resend** (API HTTPS, clé `resend_api_key`) sur un SOUS-domaine d'envoi
(`email_from`, défaut acces@notif.labuse.immo) — les MX du domaine (mail Cloudflare)
sont INTOUCHABLES. Sans clé : transport DEV — le mail est écrit en .eml sous
`outputs/mails/` (contenu réel, livraison différée) et journalisé. Jamais un envoi
silencieusement perdu : chaque appel renvoie son verdict.

Gabarits : sobres, DA cockpit en version email (tables inline, fond sombre évité — les
clients pros lisent sur Outlook), français impeccable, JAMAIS une promesse.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .config import get_settings

log = logging.getLogger("labuse.mailer")

_PIED = ("LABUSE — radar foncier, La Réunion · app.labuse.immo\n"
         "Cet email fait suite à votre échange avec LABUSE ; il n'est pas une prospection.")


def _envoyer(to: str, sujet: str, texte: str) -> str:
    """Envoie (Resend) ou dépose (.eml dev). Renvoie 'resend:<id>' | 'dev:<chemin>' | 'erreur:…'."""
    s = get_settings()
    corps = f"{texte.rstrip()}\n\n—\n{_PIED}"
    if s.resend_api_key:
        try:
            r = httpx.post("https://api.resend.com/emails", timeout=15.0,
                           headers={"Authorization": f"Bearer {s.resend_api_key}"},
                           json={"from": s.email_from, "to": [to], "subject": sujet,
                                 "text": corps})
            r.raise_for_status()
            mid = r.json().get("id", "?")
            log.info("mail resend %s → %s (%s)", sujet, to, mid)
            return f"resend:{mid}"
        except Exception as e:  # noqa: BLE001 — l'appelant décide (CLI l'affiche, webhook alerte)
            log.warning("mail ÉCHEC %s → %s : %s", sujet, to, e)
            return f"erreur:{type(e).__name__}"
    # transport DEV : contenu réel sur disque — rien de « simulé », la livraison attend la clé
    out = Path("outputs/mails")
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fn = out / f"{stamp}_{re.sub(r'[^a-z0-9]+', '-', to.lower())}.eml"
    fn.write_text(f"From: {s.email_from}\nTo: {to}\nSubject: {sujet}\n\n{corps}\n")
    log.info("mail DEV déposé : %s", fn)
    return f"dev:{fn}"


def envoyer_invitation(to: str, lien: str, founding: bool, plan: str) -> str:
    from .comptes import PLANS
    p = PLANS[plan]
    prix = f"{p['eur_mois']} €/mois"
    if founding:
        prix += f" — tarif founding : {p['eur_mois'] // 2} €/mois, à vie tant que l'abonnement reste actif"
    return _envoyer(to, "Votre accès LABUSE — invitation", f"""Bonjour,

Suite à notre échange, voici votre invitation à ouvrir votre accès LABUSE
(plan {p['label']}, {p['sieges']} siège{'s' if p['sieges'] > 1 else ''} · {prix}).

Créez votre mot de passe ici (lien valable 7 jours) :
{lien}

Le parcours : mot de passe → conditions générales → paiement sécurisé (Stripe) →
votre espace. Aucune donnée de carte ne transite par LABUSE.

À très vite,
Vic — LABUSE""")


def envoyer_reset(to: str, lien: str) -> str:
    return _envoyer(to, "LABUSE — réinitialisation du mot de passe", f"""Bonjour,

Une réinitialisation du mot de passe a été demandée pour ce compte. Si vous n'êtes
pas à l'origine de cette demande, ignorez cet email — rien ne changera.

Pour choisir un nouveau mot de passe (lien valable 1 heure) :
{lien}""")


def envoyer_paiement_requis(to: str) -> str:
    return _envoyer(to, "LABUSE — paiement requis", """Bonjour,

Le dernier prélèvement de votre abonnement LABUSE n'a pas abouti. Stripe va
retenter automatiquement ; vous pouvez aussi mettre à jour votre moyen de
paiement depuis la facture reçue par email (lien Stripe).

Sans régularisation, l'accès sera suspendu — vos données et votre historique
restent intacts et vous retrouverez tout à la réactivation.""")


def envoyer_suspension(to: str) -> str:
    return _envoyer(to, "LABUSE — accès suspendu", """Bonjour,

Faute de paiement après les relances, votre accès LABUSE est suspendu.
Vos données restent intactes. Pour réactiver : réglez la facture en attente
(lien Stripe dans l'email de facture) ou répondez à cet email.""")
