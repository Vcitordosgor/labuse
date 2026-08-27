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

# VPS · AC-025 — 2FA TOTP des admins : le mot de passe validé n'ouvre PAS la session, il
# ouvre un DÉFI (cookie signé court) que seul un code TOTP/secours transforme en session.
COOKIE_2FA = "labuse_2fa"
DEFI_2FA_TTL_S = 300           # 5 min pour saisir le code — au-delà, retour à la porte
DEFI_2FA_ESSAIS_MAX = 5        # tentatives par défi ; épuisé → défi invalidé (re-login)

# Toujours accessibles sans session (process/monitoring + cycle de connexion).
# /readyz est public mais son HANDLER réduit les détails sans session (cf. app.readyz).
# PREMIER EURO : l'onboarding (invitation/reset), les pages légales et le WEBHOOK Stripe
# (signé — sa sécurité est la signature, pas la session) sont publics par nature.
_PUBLIC = {"/health", "/healthz", "/healthz/crons", "/readyz", "/login", "/login/2fa", "/logout", "/favicon.ico",
           "/invitation", "/reset", "/reset-demande", "/cgv", "/mentions-legales", "/confidentialite",
           "/onboarding/retour", "/onboarding/paiement", "/stripe/webhook", "/guide",
           "/flash", "/flash/retour", "/flash/statut", "/flash/telecharger",
           # M21-B3 : désinscription du digest e-mail en 1 clic (lien public jeton — sécurité = le jeton).
           "/events/desabonner"}
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


def cle_signature() -> bytes:
    """Clé HMAC de l'application (session, jeton de bascule paiement, filigrane des exports).
    = LABUSE_SECRET_KEY, sinon clé éphémère process-locale — mais UNIQUEMENT en 'local' :
    hors local, `exiger_secret_prod()` (appelée au démarrage) impose la vraie clé. Aucune
    constante en dur n'est plus utilisée nulle part (un jeton de paiement était forgeable)."""
    return _key()


def exiger_secret_prod() -> None:
    """Fail-closed : hors `local`, LABUSE_SECRET_KEY est OBLIGATOIRE. Sans elle, les jetons
    signés (session, bascule paiement, filigrane) reposeraient sur une clé éphémère et le
    jeton de paiement redeviendrait forgeable → on REFUSE de démarrer, avec un message clair."""
    s = get_settings()
    if s.env != "local" and not s.secret_key:
        raise RuntimeError(
            f"LABUSE_SECRET_KEY absente en environnement '{s.env}' : clé de signature "
            "OBLIGATOIRE hors 'local' (jetons de session/paiement/filigrane). "
            "Posez-la dans /etc/labuse/labuse.env (openssl rand -hex 32) puis redémarrez.")


def exiger_env_deploiement() -> None:
    """Fail-closed SYMÉTRIQUE de `exiger_secret_prod` (M149 L2, audit M148 F4). Le risque : un
    déploiement laissé par erreur en `env='local'` désactive TOUTE l'auth (`enabled()` False) et
    ouvre les routes métier — dont l'émission d'attestations au nom de LABUSE.

    Signal fiable d'un déploiement : `LABUSE_SECRET_KEY` posée. Un dev tourne sur la clé éphémère
    (défaut documenté en 'local') ; TOUT déploiement pose la clé (exigée par `exiger_secret_prod`
    hors local, et présente dans les deux exemples pilote/production). Donc `secret_key` + `env=local`
    = configuration de déploiement incohérente → on REFUSE de démarrer plutôt que d'ouvrir. Invariant :
    clé de signature persistante ⟺ environnement de déploiement."""
    s = get_settings()
    if s.env == "local" and s.secret_key:
        raise RuntimeError(
            "LABUSE_ENV='local' alors que LABUSE_SECRET_KEY est posée : configuration de "
            "déploiement incohérente. En 'local' l'authentification est DÉSACTIVÉE (toutes les "
            "routes métier ouvertes, y compris l'émission d'attestations). Posez "
            "LABUSE_ENV=pilot|production, ou retirez LABUSE_SECRET_KEY en développement. "
            "Démarrage refusé (fail-closed).")


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


def exiger_admin(request) -> dict:
    """Gate ADMIN (M-K, P1-10/P1-11/P2-35) — réutilisable par tout endpoint d'administration
    (paramètres de bilan servis à tous, gel/dégel d'un sujet, re-score d'une parcelle…).

    - auth non active (local/rideau ouvert, comme test_api) → no-op : le reste de l'auth est
      déjà désactivé là, on ne durcit pas ce seul point ; hors 'local' `enabled()` est
      TOUJOURS vrai (fail-closed), donc le gate est actif en pilot/production ;
    - session UTILISATEUR de rôle 'admin' → OK ;
    - session UTILISATEUR non-admin (titulaire/membre/qa = client payant) → 403 ;
    - session PILOTE (mot de passe partagé, pas de compte utilisateur) → OK (admin de fait) ;
    - aucune session valide → 401.

    Double-vérifie la session (ne suppose pas la garde globale) pour rester correct même
    appelé hors garde."""
    from fastapi import HTTPException
    if not enabled():
        return {"role": "local"}
    cookie = request.cookies.get(COOKIE) or request.cookies.get("session")
    info = session_info(cookie)
    if info is not None:
        if info.get("role") != "admin":
            raise HTTPException(403, "Action réservée aux administrateurs LABUSE.")
        return info
    if token_ok(cookie):          # session pilote (mot de passe partagé) = admin de fait
        return {"role": "pilote"}
    raise HTTPException(401, "Session administrateur requise.")


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


# ── VPS · AC-025 — jeton de DÉFI 2FA (mot de passe OK, code TOTP attendu) ──
# Format compact signé « exp.uid.n.sig » (n = tentatives consommées) : sans état serveur,
# infalsifiable (HMAC clé app), court (5 min). Le compteur vit DANS le jeton — chaque échec
# ré-émet le cookie avec n+1 ; un client qui rejoue un vieux cookie ne « gagne » que les
# tentatives déjà comptées de CE jeton, l'expiration à 5 min borne le tout.

def defi_2fa(utilisateur_id: int, tentatives: int = 0) -> str:
    exp = int(time.time() + DEFI_2FA_TTL_S)
    payload = f"{exp}.{utilisateur_id}.{tentatives}"
    return f"{payload}.{_sign('2fa.' + payload)[:32]}"


def defi_2fa_lire(token: str | None) -> tuple[int, int] | None:
    """Jeton → (utilisateur_id, tentatives) ; None si absent/altéré/expiré/épuisé."""
    if not token:
        return None
    try:
        exp, uid, n, sig = token.split(".", 3)
        payload = f"{exp}.{uid}.{n}"
        if not hmac.compare_digest(sig, _sign("2fa." + payload)[:32]):
            return None
        if int(exp) < time.time() or int(n) >= DEFI_2FA_ESSAIS_MAX:
            return None
        return int(uid), int(n)
    except (ValueError, TypeError):
        return None


def cookie_2fa_kwargs() -> dict:
    return {"key": COOKIE_2FA, "httponly": True, "samesite": "lax",
            "secure": get_settings().env != "local", "max_age": DEFI_2FA_TTL_S, "path": "/"}


def _page_2fa(titre: str, sous: str, corps: str, error: str | None = None) -> str:
    """Gabarit commun des écrans 2FA — même nuit Coffre que la porte (coffre_ui)."""
    err = (f'<p class="err" role="alert"><span aria-hidden="true">▲</span> {error}</p>'
           if error else "")
    return coffre_ui.page(titre, coffre_ui.OISEAU + f"""
<h1>LABUSE</h1><p class="sub">{sous}</p>{corps}{err}""")


def page_2fa_code(error: str | None = None) -> str:
    """Saisie du code — TOTP à 6 chiffres, ou code de secours (même champ : la vérification
    essaie l'un puis l'autre, l'utilisateur n'a pas à choisir un « mode »)."""
    return _page_2fa("Vérification", "vérification en deux étapes", """
<form method="post" action="/login/2fa" novalidate>
  <label for="code">Code de votre application</label>
  <div class="field"><input id="code" name="code" type="text" inputmode="numeric"
     autocomplete="one-time-code" autofocus placeholder="123 456" aria-required="true"></div>
  <button type="submit">Vérifier</button>
</form>
<p class="note">Téléphone indisponible&nbsp;? Saisissez l'un de vos
<b>codes de secours</b> dans le même champ.</p>""", error)


def page_2fa_enrolement(secret: str, qr_svg: str, error: str | None = None) -> str:
    """Premier passage : QR à scanner (Google Authenticator, Aegis, 1Password…) + le secret
    en toutes lettres (saisie manuelle si le scan échoue), puis le premier code confirme."""
    groupes = " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))
    return _page_2fa("Activer la 2FA", "activez la vérification en deux étapes", f"""
<p style="font-size:13px">Votre compte administrateur exige une seconde clé. Scannez ce
QR avec votre application d'authentification, puis saisissez le code affiché.</p>
<div style="background:#fff;border-radius:var(--r);padding:10px;margin:16px auto;width:196px">{qr_svg}</div>
<p class="note">Saisie manuelle — secret&nbsp;: <code id="totp-secret"
style="color:var(--mint);letter-spacing:.06em">{groupes}</code></p>
<form method="post" action="/login/2fa" novalidate>
  <label for="code">Code affiché par l'application</label>
  <div class="field"><input id="code" name="code" type="text" inputmode="numeric"
     autocomplete="one-time-code" autofocus placeholder="123 456" aria-required="true"></div>
  <button type="submit">Activer et entrer</button>
</form>""", error)


def page_2fa_secours(codes: list[str]) -> str:
    """AFFICHÉS UNE SEULE FOIS : en base ne restent que les hash — cette page est le seul
    exemplaire des codes de secours."""
    lis = "".join(f'<li style="padding:3px 0"><code>{c[:5]}-{c[5:]}</code></li>' for c in codes)
    return _page_2fa("Codes de secours", "vérification en deux étapes activée", f"""
<p style="font-size:13px">Notez ces <b>8 codes de secours</b> (gestionnaire de mots de passe,
coffre). Chacun ne sert qu'<b>une fois</b>, si votre téléphone est indisponible.
<b>Ils ne seront plus jamais affichés.</b></p>
<ul style="list-style:none;columns:2;padding:14px 18px;margin:16px 0;background:var(--s2);
border:1px solid var(--line);border-radius:var(--r);color:var(--hi);
font-variant-numeric:tabular-nums">{lis}</ul>
<a class="btn" href="/">J'ai noté mes codes → entrer</a>""")


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
     placeholder="prenom.nom@cabinet.re" aria-required="true"></div>
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
