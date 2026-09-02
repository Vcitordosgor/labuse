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
    "radar": "brevo_tpl_radar",                      # RADAR P4 — legacy (digest/alerte, template ID 12)
    "radar_digest": "brevo_tpl_radar_digest",        # RADAR-DIGESTS — digest quotidien (template Brevo ID 12)
    "radar_alerte": "brevo_tpl_radar_alerte",        # RADAR-DIGESTS — alerte de veille (template Brevo ID 13)
}
#: libellés servis au dashboard (boutons/chips). ADMIN-1 AD4 — les 3 mails d'onboarding sont nommés
#: explicitement partout (fini « Mail 1/2/3 ») ; la CLÉ code (onboarding1/2/3) reste porteuse (mapping
#: template Brevo + colonne licence_mails.mail_key), seul le LIBELLE servi change.
LIBELLES: dict[str, str] = {
    "essai": "Essai 48 h", "souscription": "Lien de souscription",
    "onboarding1": "Mail de bienvenue", "onboarding2": "Relance J+3", "onboarding3": "Dernier rappel J+10",
    "relance_carte": "Relance carte refusée", "suspension": "Suspension",
    "retablissement": "Rétablissement", "radar": "Radar (legacy)",
    "radar_digest": "Radar — digest quotidien", "radar_alerte": "Radar — alerte de veille",
}


def template_id(key: str) -> int | None:
    champ = TEMPLATES.get(key)
    if not champ:
        return None
    v = _setting_ou_env(champ)
    try:
        return int(v) if v else None
    except (TypeError, ValueError):
        return None


def _api_key() -> str | None:
    """REVUE · R7 — clé API Brevo : setting préfixé `LABUSE_BREVO_API_KEY` OU repli sans préfixe
    `BREVO_API_KEY` (le .env de prod utilise cette forme, comme `STRIPE_RESTRICTED_KEY`). Sans ce
    repli, Brevo était vu « non configuré » alors que les clés étaient bien présentes."""
    import os
    return (getattr(get_settings(), "brevo_api_key", None) or os.environ.get("BREVO_API_KEY", "").strip() or None)


def _setting_ou_env(champ: str):
    """Lit un réglage Brevo : setting préfixé (`LABUSE_<CHAMP>`) sinon repli sans préfixe (`<CHAMP>`)."""
    import os
    return getattr(get_settings(), champ, None) or os.environ.get(champ.upper()) or None


def etat_configuration() -> dict:
    """Pour le dashboard : quels templates sont branchés (jamais les IDs eux-mêmes au client)."""
    return {"api": bool(_api_key()),
            "templates": {k: template_id(k) is not None for k in TEMPLATES}}


def apercu_template(key: str, params: dict | None = None) -> dict:
    """ADMIN-1 (AD4) — APERÇU du mail réel : va chercher le template chez Brevo (GET smtpTemplates)
    et substitue naïvement les variables du compte ({{ params.x }} / {{params.x}}). Ne lève JAMAIS :
    non configuré / template absent / Brevo injoignable → {configure:false, raison, params}. Le rendu
    Brevo étant server-side, la substitution ici est indicative (les blocs conditionnels ne sont pas
    évalués) — l'infobulle du dashboard le dit."""
    params = params or {}
    base = {"configure": False, "key": key, "libelle": LIBELLES.get(key, key), "params": params}
    if key not in TEMPLATES:
        return {**base, "raison": f"Template inconnu « {key} »."}
    api_key = _api_key()
    if not api_key:
        return {**base, "raison": "Brevo non configuré (BREVO_API_KEY absente)."}
    tpl = template_id(key)
    if tpl is None:
        return {**base, "raison": f"Identifiant de template absent (LABUSE_{TEMPLATES[key].upper()})."}
    try:
        import re

        import httpx
        r = httpx.get(f"https://api.brevo.com/v3/smtpTemplates/{tpl}",
                      headers={"api-key": api_key}, timeout=15.0)
        if r.status_code // 100 != 2:
            return {**base, "raison": f"Brevo a refusé la lecture du template (HTTP {r.status_code})."}
        data = r.json()
        subject = data.get("subject") or ""
        html = data.get("htmlContent") or ""

        def _sub(txt: str) -> str:
            for k, v in params.items():
                txt = re.sub(r"\{\{\s*(?:params\.)?" + re.escape(k) + r"\s*\}\}", str(v), txt)
            return txt
        return {"configure": True, "key": key, "libelle": LIBELLES.get(key, key),
                "params": params, "subject": _sub(subject), "html": _sub(html)}
    except Exception as exc:  # noqa: BLE001 — l'aperçu n'échoue jamais en dur
        log.warning("Brevo apercu %s injoignable : %s", key, exc)
        return {**base, "raison": f"Brevo injoignable ({type(exc).__name__})."}


def envoyer_template(to: str, key: str, params: dict | None = None) -> dict:
    """Envoie le template `key` à `to`. Renvoie {envoye: bool, raison?: str} — JAMAIS une levée,
    JAMAIS un envoi silencieux : non configuré → raison explicite, le dashboard l'affiche."""
    if key not in TEMPLATES:
        return {"envoye": False, "raison": f"Template inconnu « {key} »."}
    api_key = _api_key()
    if not api_key:
        return {"envoye": False,
                "raison": "Brevo non configuré (BREVO_API_KEY absente) — aucun envoi."}
    tpl = template_id(key)
    if tpl is None:
        return {"envoye": False,
                "raison": f"Identifiant de template absent (LABUSE_{TEMPLATES[key].upper()}) — aucun envoi."}
    try:
        import httpx
        r = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "content-type": "application/json"},
            json={"templateId": tpl, "to": [{"email": to}], "params": params or {}},
            timeout=15.0)
        if r.status_code // 100 == 2:
            return {"envoye": True}
        log.warning("Brevo %s → HTTP %s : %s", key, r.status_code, r.text[:200])
        return {"envoye": False, "raison": f"Brevo a refusé l'envoi (HTTP {r.status_code})."}
    except Exception as exc:  # noqa: BLE001 — le dashboard affiche l'échec, jamais un 500
        log.warning("Brevo %s injoignable : %s", key, exc)
        return {"envoye": False, "raison": f"Brevo injoignable ({type(exc).__name__})."}
