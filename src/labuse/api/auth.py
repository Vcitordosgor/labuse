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


# PREMIER EURO · E1 — cache court des sessions UTILISATEUR (60 s) : 1 lookup DB max par
# minute et par session ; une révocation (logout/suspension) propage donc en ≤ 60 s (documenté).
_USER_CACHE: dict[str, tuple[float, bool]] = {}
_USER_CACHE_TTL = 60.0


def _user_token_ok(token: str) -> bool:
    now = time.time()
    hit = _USER_CACHE.get(token)
    if hit and now - hit[0] < _USER_CACHE_TTL:
        return hit[1]
    ok = False
    try:
        from ..comptes import session_utilisateur
        from ..db import session_scope
        with session_scope() as db:
            ok = session_utilisateur(db, token[2:]) is not None
    except Exception:  # noqa: BLE001 — table absente (première install) → simplement pas de session
        ok = False
    _USER_CACHE[token] = (now, ok)
    if len(_USER_CACHE) > 4096:
        for k in sorted(_USER_CACHE, key=lambda k: _USER_CACHE[k][0])[:1024]:
            _USER_CACHE.pop(k, None)
    return ok


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
    """La PORTE — direction « Coffre » (verdict Vic, revue UI/UX S16) : le luxe par la
    retenue. Deux champs (identifiant + mot de passe), l'oiseau doré seul, 4 états
    (défaut/focus/erreur de couple/chargement). FAÇADE prête : le moteur d'auth actuel
    (mot de passe pilote) ignore `identifiant` ; le futur backend d'identité (mandat
    premier-euro) lira les deux champs du même POST /login sans retoucher le design.
    Page autonome (aucune dépendance aux statiques protégés)."""
    etat = "erreur" if error else "defaut"
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>LABUSE — Connexion</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#050706; --mint:#5CE6A1; --err:#E8695A;
    --txt-hi:#ECF5EF; --txt:#C9DCD1; --txt-mut:#8FA69A; --line:#1B2620;
  }}
  * {{ box-sizing:border-box; margin:0; }}
  html, body {{ height:100%; }}
  body {{
    background:radial-gradient(120vh 80vh at 50% 38%, #070A08 0%, var(--bg) 55%, #030404 100%);
    color:var(--txt); font:15px/1.5 Inter, system-ui, sans-serif;
    display:grid; place-items:center; padding:24px; -webkit-font-smoothing:antialiased;
  }}
  main {{ width:min(360px,100%); text-align:center; animation:entree .5s cubic-bezier(.2,.7,.2,1) both; }}
  @keyframes entree {{ from {{ opacity:0; transform:translateY(10px); }} }}
  @media (prefers-reduced-motion: reduce) {{ main {{ animation:none; }} }}

  .oiseau {{ width:108px; margin:0 auto 22px; display:block;
             filter:drop-shadow(0 0 18px rgba(199,160,85,.22)); }}
  .wordmark {{ font:700 15px "Space Grotesk", sans-serif; letter-spacing:.42em;
               color:var(--txt-hi); text-indent:.42em; margin-bottom:42px; }}

  form {{ text-align:left; }}
  label {{ display:block; font-size:11px; letter-spacing:.14em; text-transform:uppercase;
           color:var(--txt-mut); margin-bottom:10px; }}
  .champ {{ position:relative; }}
  .champ + label {{ margin-top:28px; }}
  input {{
    width:100%; background:transparent; border:0; border-bottom:1px solid var(--line);
    color:var(--txt-hi); font:16px/1 Inter, system-ui, sans-serif; letter-spacing:.06em;
    padding:10px 44px 12px 2px; outline:none; border-radius:0;
    transition:border-color .25s, box-shadow .25s; caret-color:var(--mint);
  }}
  input:focus {{ border-bottom-color:var(--mint);
                 box-shadow:0 1px 0 0 var(--mint), 0 10px 24px -18px rgba(92,230,161,.45); }}
  input::placeholder {{ color:#3d4a43; }}
  .entrer {{
    position:absolute; right:0; top:50%; translate:0 -50%;
    width:34px; height:34px; border:0; border-radius:50%;
    background:transparent; color:var(--txt-mut); font-size:17px; cursor:pointer;
    display:grid; place-items:center; transition:color .2s, background .2s;
  }}
  .entrer:hover, input:focus ~ .entrer {{ color:var(--mint); }}
  .entrer:focus-visible {{ outline:1px solid var(--mint); outline-offset:2px; }}

  /* erreur de COUPLE : sobre, message neutre, la page ne tremble pas (espace réservé) */
  .erreur {{ min-height:34px; padding-top:12px; font-size:13px; color:var(--err);
             opacity:0; transition:opacity .3s; }}
  body[data-etat="erreur"] .erreur {{ opacity:1; }}
  body[data-etat="erreur"] input {{ border-bottom-color:rgba(232,105,90,.65); }}

  /* chargement : l'anneau remplace la flèche, rien d'autre ne bouge */
  .anneau {{ width:15px; height:15px; border-radius:50%; display:none;
             border:1.5px solid rgba(92,230,161,.25); border-top-color:var(--mint);
             animation:rot .7s linear infinite; }}
  @keyframes rot {{ to {{ rotate:1turn; }} }}
  body[data-etat="chargement"] .anneau {{ display:block; }}
  body[data-etat="chargement"] .fleche {{ display:none; }}
  body[data-etat="chargement"] input {{ opacity:.55; pointer-events:none; }}

  .signature {{ margin-top:56px; font-size:11.5px; letter-spacing:.18em;
                color:var(--txt-mut); text-transform:uppercase; }}
  .signature span {{ color:#46584f; padding:0 .5em; }}
  .foot {{ margin-top:16px; font-size:10.5px; line-height:1.5; color:#46584f; }}

  @media (max-width:480px) {{
    .oiseau {{ width:92px; }} .wordmark {{ margin-bottom:34px; }}
    .champ + label {{ margin-top:24px; }} .signature {{ margin-top:44px; }}
  }}
</style></head>
<body data-etat="{etat}">
<main>
  <svg class="oiseau" viewBox="0 0 240 82" role="img" aria-label="LA BUSE">
    <defs>
      <linearGradient id="or" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#EFD9A0"/><stop offset=".55" stop-color="#C7A055"/><stop offset="1" stop-color="#96733A"/>
      </linearGradient>
    </defs>
    <path fill="url(#or)" d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/>
  </svg>
  <div class="wordmark">LABUSE</div>

  <form method="post" action="/login" id="porte">
    <label for="identifiant">Identifiant</label>
    <div class="champ">
      <input id="identifiant" name="identifiant" type="text" autocomplete="username"
             autocapitalize="none" spellcheck="false" autofocus required>
    </div>
    <label for="password">Mot de passe</label>
    <div class="champ">
      <input id="password" name="password" type="password" placeholder="••••••••••••"
             autocomplete="current-password" required>
      <button class="entrer" type="submit" aria-label="Entrer">
        <span class="fleche">→</span><span class="anneau" aria-hidden="true"></span>
      </button>
    </div>
    <p class="erreur" role="alert" aria-live="polite">Identifiants invalides.</p>
  </form>

  <p class="signature">Radar foncier<span>·</span>La Réunion</p>
  <p class="foot">Accès réservé au pilote. Pré-analyse sur données publiques —
  constructibilité, propriété, rentabilité jamais garanties.</p>
</main>
<script>
  // La façade joue ses états ; le POST reste un envoi de formulaire classique.
  document.getElementById('porte').addEventListener('submit', function () {{
    document.body.dataset.etat = 'chargement';
  }});
  document.querySelectorAll('input').forEach(function (i) {{
    i.addEventListener('input', function () {{
      if (document.body.dataset.etat === 'erreur') document.body.dataset.etat = 'defaut';
    }});
  }});
</script>
</body></html>"""


def log_event(event: str, request) -> None:
    ip = getattr(getattr(request, "client", None), "host", "?")
    if event == "login_failed":
        log.warning("connexion refusée ip=%s", ip)
    else:
        log.info("%s ip=%s", event, ip)


def slow_failure() -> None:
    if not os.environ.get("PYTEST_CURRENT_TEST"):   # ne ralentit pas la suite de tests
        time.sleep(FAILURE_DELAY_S)
