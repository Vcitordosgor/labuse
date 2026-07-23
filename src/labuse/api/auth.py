"""Authentification PILOTE — compte unique, session cookie signée. Pas un SaaS.

Choix assumés (pilote encadré, un promoteur) :
- UN mot de passe global, fourni par variable d'environnement (LABUSE_AUTH_PASSWORD,
  en clair ou « sha256:<hexdigest> ») — jamais en dur, jamais committé ;
- session = cookie « labuse_session » signé HMAC-SHA256 (clé LABUSE_SECRET_KEY, sinon
  clé éphémère → sessions perdues au redémarrage, documenté) ; httpOnly, SameSite=Lax,
  Secure hors local ; expiration LABUSE_SESSION_HOURS (12 h par défaut) ;
- pas de création de compte, pas de multi-tenant, message d'échec NEUTRE, petit délai
  anti-force-brute, événements journalisés (logger « labuse.auth ») ;
- fail-closed : en pilote/production SANS mot de passe configuré, les routes métier
  répondent 503 (jamais « ouvert par accident »).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time

from ..config import get_settings
from . import coffre_ui

log = logging.getLogger("labuse.auth")

COOKIE = "labuse_session"
FAILURE_DELAY_S = 0.4          # ralentit la force brute sans pénaliser l'utilisateur légitime

# Toujours accessibles sans session (process/monitoring + cycle de connexion).
# /readyz est public mais son HANDLER réduit les détails sans session (cf. app.readyz).
# PREMIER EURO : l'onboarding (invitation/reset), les pages légales et le WEBHOOK Stripe
# (signé — sa sécurité est la signature, pas la session) sont publics par nature.
_PUBLIC = {"/health", "/healthz", "/healthz/crons", "/readyz", "/login", "/logout", "/favicon.ico",
           "/invitation", "/reset", "/reset-demande", "/cgv", "/mentions-legales", "/confidentialite",
           "/onboarding/retour", "/onboarding/paiement", "/stripe/webhook", "/guide",
           "/flash", "/flash/retour", "/flash/statut", "/flash/telecharger"}
# Documentation auto (surface de découverte de l'API) : publique en local seulement.
_DOCS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}

# Clé éphémère de secours (process-locale) si LABUSE_SECRET_KEY absente.
_EPHEMERAL_KEY = secrets.token_bytes(32)


def enabled() -> bool:
    """L'authentification s'applique-t-elle ? Oui dès qu'un mot de passe est posé,
    et TOUJOURS hors local (fail-closed si non configurée)."""
    s = get_settings()
    return bool(s.auth_password) or s.env != "local"


def configured() -> bool:
    return bool(get_settings().auth_password)


def is_public(path: str) -> bool:
    if path in _PUBLIC:
        return True
    if path in _DOCS:
        return get_settings().env == "local"
    return False


def wants_html(path: str) -> bool:
    """Navigation (page) → redirection /login ; appel API → 401 JSON.
    B2 : /app (proto Vue) est retiré du code — le préfixe reste traité comme une navigation
    (vieux favoris → /login puis 301 Caddy), /socle/ = le front local."""
    return path == "/" or path.startswith("/app") or path.startswith("/socle")


def _key() -> bytes:
    s = get_settings()
    if s.secret_key:
        return s.secret_key.encode("utf-8")
    return _EPHEMERAL_KEY


def _sign(payload: str) -> str:
    return hmac.new(_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_token() -> str:
    expiry = int(time.time() + get_settings().session_hours * 3600)
    payload = f"v1.{expiry}"
    return f"{payload}.{_sign(payload)}"


# PREMIER EURO · E1 (durci au test Vic) — la session utilisateur se vérifie EN BASE À
# CHAQUE REQUÊTE : une suspension (webhook Stripe, CLI) coupe l'accès au rechargement
# suivant, pas « dans la minute ». Coût : un lookup PK par requête (~0,2 ms) — assumé.
def session_info(token: str | None) -> dict | None:
    """Session utilisateur valide → {utilisateur_id, compte_id, role, statut_compte} ; None
    sinon. UN lookup par requête (partagé entre la garde et la résolution du tenant)."""
    if not token or not token.startswith("u."):
        return None
    try:
        from ..comptes import session_utilisateur
        from ..db import session_scope
        with session_scope() as db:
            return session_utilisateur(db, token[2:])
    except Exception:  # noqa: BLE001 — table absente (première install) → pas de session
        return None


def _user_token_ok(token: str) -> bool:
    return session_info(token) is not None


def token_ok(token: str | None) -> bool:
    if not token:
        return False
    # session UTILISATEUR (premier-euro) : cookie « u.<token> », vérité en base (hash)
    if token.startswith("u."):
        return _user_token_ok(token)
    try:
        version, expiry, sig = token.split(".", 2)
        payload = f"{version}.{expiry}"
        if version != "v1" or not hmac.compare_digest(sig, _sign(payload)):
            return False
        return int(expiry) > time.time()
    except (ValueError, TypeError):
        return False


def password_ok(candidate: str) -> bool:
    """Compare en temps constant ; supporte « sha256:<hex> » pour ne pas mettre le
    mot de passe en clair dans l'environnement si l'opérateur préfère un hash."""
    expected = get_settings().auth_password or ""
    if not expected or not candidate:
        return False
    if expected.startswith("sha256:"):
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, expected[len("sha256:"):].lower())
    return hmac.compare_digest(candidate, expected)


def cookie_kwargs() -> dict:
    s = get_settings()
    return {
        "key": COOKIE,
        "httponly": True,
        "samesite": "lax",
        "secure": s.env != "local",          # pilote/production = derrière HTTPS (documenté)
        "max_age": int(s.session_hours * 3600),
        "path": "/",
    }


def login_page(error: bool = False) -> str:
    """La PORTE — nuit « Coffre » portée au design system validé (AUDIT PAIEMENT, partie E,
    verdict Vic sur docs/mockups/auth/login.html) : deux champs (identifiant + mot de passe),
    l'oiseau doré, 4 états (défaut/focus/erreur de couple/chargement). Zéro hex local : tout
    naît des tokens de `coffre_ui`. FAÇADE inchangée : le moteur d'auth pilote ignore
    `identifiant`, le futur backend d'identité lira les deux champs du même POST /login.
    La MÉCANIQUE d'authentification n'est pas touchée ici (design ≠ mécanique)."""
    etat = "erreur" if error else "defaut"
    head = ("<style>"
            "body[data-state=erreur] #loginerr{display:flex}"
            "body:not([data-state=erreur]) #loginerr{display:none}"
            "body[data-state=chargement] .spin{display:inline-block!important}"
            "body[data-state=chargement] [data-hideon=chargement]{display:none}"
            "body[data-state=chargement] input{opacity:.55;pointer-events:none}"
            ".foot{font-size:11px;color:var(--dim);text-align:center;margin-top:22px;line-height:1.6}"
            "</style>")
    corps = coffre_ui.OISEAU + f"""
<h1>LABUSE</h1><p class="sub">Radar foncier · La Réunion</p>
<form method="post" action="/login" id="porte" novalidate aria-describedby="loginerr">
  <label for="identifiant">E-mail</label>
  <div class="field"><input id="identifiant" name="identifiant" type="email"
     autocomplete="email" inputmode="email" autocapitalize="none" spellcheck="false" autofocus
     placeholder="vous@cabinet.re" aria-required="true"></div>
  <label for="password">Mot de passe</label>
  <div class="field"><input id="password" name="password" type="password"
     autocomplete="current-password" aria-required="true"></div>
  <p class="err" id="loginerr" role="alert" aria-live="polite"{"" if error else " hidden"}>
    <span aria-hidden="true">▲</span> E-mail ou mot de passe incorrect.</p>
  <button type="submit"><span class="spin" hidden aria-hidden="true"></span>
    <span data-hideon="chargement">Entrer</span></button>
</form>
<p class="linkrow"><a href="/reset">Mot de passe oublié ?</a></p>
<p class="foot">Accès réservé aux abonnés. Pré-analyse sur données publiques —
constructibilité, propriété, rentabilité jamais garanties.</p>
<script>
  var porte = document.getElementById('porte');
  porte.addEventListener('submit', function () {{ document.body.dataset.state = 'chargement'; }});
  porte.querySelectorAll('input').forEach(function (i) {{
    i.addEventListener('input', function () {{
      if (document.body.dataset.state === 'erreur') document.body.dataset.state = 'defaut';
    }});
  }});
</script>"""
    html_doc = coffre_ui.page("Connexion", corps, head=head)
    return html_doc.replace('<body style="', f'<body data-state="{etat}" style="', 1)


def log_event(event: str, request) -> None:
    ip = getattr(getattr(request, "client", None), "host", "?")
    if event == "login_failed":
        log.warning("connexion refusée ip=%s", ip)
    else:
        log.info("%s ip=%s", event, ip)


def slow_failure() -> None:
    if not os.environ.get("PYTEST_CURRENT_TEST"):   # ne ralentit pas la suite de tests
        time.sleep(FAILURE_DELAY_S)
