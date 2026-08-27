"""DASHBOARD-V1 · MAILS (Brevo) — templates transactionnels référencés PAR IDENTIFIANT en .env.

Le transport historique (mail.py, SMTP) reste celui des mails techniques existants (reset,
digest…). ICI : les mails du CYCLE DE VIE CLIENT (essai, souscription, onboarding 1/2/3,
relance carte, suspension, rétablissement), envoyés par TEMPLATE Brevo (API v3) — le contenu
se règle chez Brevo, l'app n'envoie que l'identifiant + les paramètres.

Identifiants absents (ou clé API absente) → mode « NON CONFIGURÉ » PROPRE : le bouton reste
visible au dashboard, la réponse dit pourquoi rien n'est parti, AUCUN envoi silencieux
(mandat, section MAILS). Aucun envoi automatique en V1 : l'app RAPPELLE (J+3/J+10), Vic
déclenche chaque envoi.
"""
from __future__ import annotations

import logging

from .config import get_settings

log = logging.getLogger("labuse.brevo")

#: clés de template (mandat) → champ Settings portant l'ID Brevo (.env LABUSE_BREVO_TPL_*).
TEMPLATES: dict[str, str] = {
    "essai": "brevo_tpl_essai",                      # compte d'essai 48 h (D9)
    "souscription": "brevo_tpl_souscription",        # lien de souscription 349 €/mois
    "onboarding1": "brevo_tpl_onboarding_1",
    "onboarding2": "brevo_tpl_onboarding_2",
    "onboarding3": "brevo_tpl_onboarding_3",
    "relance_carte": "brevo_tpl_relance_carte",      # carte refusée → lien de paiement
    "suspension": "brevo_tpl_suspension",
    "retablissement": "brevo_tpl_retablissement",
}
#: libellés servis au dashboard (boutons/chips)
LIBELLES: dict[str, str] = {
    "essai": "Essai 48 h", "souscription": "Lien de souscription",
    "onboarding1": "Mail 1", "onboarding2": "Mail 2", "onboarding3": "Mail 3",
    "relance_carte": "Relance carte refusée", "suspension": "Suspension",
    "retablissement": "Rétablissement",
}


def template_id(key: str) -> int | None:
    champ = TEMPLATES.get(key)
    if not champ:
        return None
    v = getattr(get_settings(), champ, None)
    try:
        return int(v) if v else None
    except (TypeError, ValueError):
        return None


def etat_configuration() -> dict:
    """Pour le dashboard : quels templates sont branchés (jamais les IDs eux-mêmes au client)."""
    s = get_settings()
    return {"api": bool(s.brevo_api_key),
            "templates": {k: template_id(k) is not None for k in TEMPLATES}}


def envoyer_template(to: str, key: str, params: dict | None = None) -> dict:
    """Envoie le template `key` à `to`. Renvoie {envoye: bool, raison?: str} — JAMAIS une levée,
    JAMAIS un envoi silencieux : non configuré → raison explicite, le dashboard l'affiche."""
    s = get_settings()
    if key not in TEMPLATES:
        return {"envoye": False, "raison": f"Template inconnu « {key} »."}
    if not s.brevo_api_key:
        return {"envoye": False,
                "raison": "Brevo non configuré (LABUSE_BREVO_API_KEY absente) — aucun envoi."}
    tpl = template_id(key)
    if tpl is None:
        return {"envoye": False,
                "raison": f"Identifiant de template absent (LABUSE_{TEMPLATES[key].upper()}) — aucun envoi."}
    try:
        import httpx
        r = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": s.brevo_api_key, "content-type": "application/json"},
            json={"templateId": tpl, "to": [{"email": to}], "params": params or {}},
            timeout=15.0)
        if r.status_code // 100 == 2:
            return {"envoye": True}
        log.warning("Brevo %s → HTTP %s : %s", key, r.status_code, r.text[:200])
        return {"envoye": False, "raison": f"Brevo a refusé l'envoi (HTTP {r.status_code})."}
    except Exception as exc:  # noqa: BLE001 — le dashboard affiche l'échec, jamais un 500
        log.warning("Brevo %s injoignable : %s", key, exc)
        return {"envoye": False, "raison": f"Brevo injoignable ({type(exc).__name__})."}
