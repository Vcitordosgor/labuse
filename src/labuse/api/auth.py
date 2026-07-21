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

log = logging.getLogger("labuse.auth")

COOKIE = "labuse_session"
FAILURE_DELAY_S = 0.4          # ralentit la force brute sans pénaliser l'utilisateur légitime

# Toujours accessibles sans session (process/monitoring + cycle de connexion).
# /readyz est public mais son HANDLER réduit les détails sans session (cf. app.readyz).
_PUBLIC = {"/health", "/healthz", "/healthz/crons", "/readyz", "/login", "/logout", "/favicon.ico"}
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
    """Navigation (page) → redirection /login ; appel API → 401 JSON."""
    return path == "/" or path.startswith("/app")


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


def token_ok(token: str | None) -> bool:
    if not token:
        return False
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
    """Page de connexion autonome (aucune dépendance aux statiques protégés)."""
    msg = '<p class="err">Identifiants invalides.</p>' if error else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>LA BUSE — connexion</title>
<style>
 body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
   background:#0e1116;color:#e7ebf0;font:15px/1.5 "Segoe UI",system-ui,sans-serif}}
 .card{{background:#161c24;border:1px solid #2a3340;border-radius:16px;padding:34px 36px;width:min(360px,92vw)}}
 h1{{font-size:22px;letter-spacing:.12em;color:#c9a86a;margin:0}}
 .sub{{color:#8b95a3;font-size:12.5px;margin:6px 0 22px}}
 label{{display:block;font-size:12px;color:#8b95a3;margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em}}
 input{{width:100%;box-sizing:border-box;background:#0e1116;border:1px solid #2a3340;border-radius:9px;
   color:#e7ebf0;padding:11px 13px;font:inherit}}
 input:focus{{outline:2px solid #c9a86a;border-color:#c9a86a}}
 button{{width:100%;margin-top:16px;background:#c9a86a;color:#1a1206;border:none;border-radius:9px;
   padding:12px;font:inherit;font-weight:700;cursor:pointer}}
 button:hover{{background:#e3cfa0}}
 .err{{color:#db8b7b;font-size:13px;margin:12px 0 0}}
 .foot{{color:#566070;font-size:11px;margin-top:20px;line-height:1.5}}
</style></head><body>
<form class="card" method="post" action="/login">
  <h1>LA&nbsp;BUSE</h1><div class="sub">Radar foncier · accès pilote</div>
  <label for="password">Mot de passe</label>
  <input id="password" name="password" type="password" autocomplete="current-password" autofocus required>
  <button type="submit">Se connecter</button>
  {msg}
  <div class="foot">Accès réservé au pilote. Pré-analyse sur données publiques —
  constructibilité, propriété, rentabilité jamais garanties.</div>
</form></body></html>"""


def log_event(event: str, request) -> None:
    ip = getattr(getattr(request, "client", None), "host", "?")
    if event == "login_failed":
        log.warning("connexion refusée ip=%s", ip)
    else:
        log.info("%s ip=%s", event, ip)


def slow_failure() -> None:
    if not os.environ.get("PYTEST_CURRENT_TEST"):   # ne ralentit pas la suite de tests
        time.sleep(FAILURE_DELAY_S)
