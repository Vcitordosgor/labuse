"""FastAPI — endpoints LA BUSE.

- GET  /health
- GET  /sources                  page « Sources de données » (statut connecteurs)
- POST /sources/{id}/test        bouton « tester la connexion »
- GET  /parcels                  liste (commune) avec dernier verdict
- GET  /parcels/{idu}            FICHE parcelle (§8) : verdict + double score + cascade + sources + IA
- POST /parcels/{idu}/evaluate   relance la cascade (option ?ai=true)
- GET  /discover                 vue Découverte (offre B) : survivantes classées
- POST /feedback                 boucle de feedback (§10)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import config, models, prospection
from .. import rnu as _rnu
from ..db import session_scope
from ..enums import DataSourceStatus, FeedbackVerdict
from ..scoring.score_v_constants import Q_A_RUN_LABEL, V_BAND_LABELS, V_BRULANTE_THRESHOLD
from ..scoring.fraction_client import fraction_humaine as _fh, fraction_sql_case as _fraction_sql_case  # M135 P2
from ..scoring.p_v2.libelles_client import raison_dominante as _raison_dom   # M135 P3 — chip raison

# Couches EXCLUANTES / FLAGGANTES dont l'absence rend les verdicts partiels (§3).
# Tant qu'une de ces couches n'est pas ingérée, une "opportunité" peut masquer une
# contrainte → bandeau d'avertissement + distinction "opportunité vérifiée".
CRITICAL_LAYERS = {
    "sar": ("SAR (zonage régional — supérieur au PLU)", ["sar"]),
    "risques": ("Risques (Géorisques / PPR — inondation, mouvement de terrain)", ["ppr", "georisque_alea"]),
    "foret_publique": ("Forêts publiques / régime forestier (ONF)", ["foret_publique"]),
    "ens": ("Espaces Naturels Sensibles (ENS)", ["ens"]),
    "safer": ("Zonage agricole / SAFER", ["safer"]),
    "trait_de_cote": ("Recul du trait de côte", ["trait_de_cote"]),
    "abf": ("ABF / périmètres Monuments historiques", ["abf"]),
}
# Minimum requis pour qualifier une "opportunité VÉRIFIÉE" (consigne produit) : contrôle
# SAR + risques + forêts + littoral ingérés. Le SAR n'étant qu'un proxy de vocation à
# couverture partielle, « vérifiée » = contrôlée sur les couches disponibles, JAMAIS une
# garantie de constructibilité. Chaque clé -> liste de `kind` qui l'attestent.
RELIABLE_REQUIRED = ("sar", "risques", "foret_publique", "trait_de_cote")

# En deçà, ce sont des slivers cadastraux (artefacts) : masqués de la CARTE et de la
# DÉCOUVERTE (restent en base et dans les compteurs de volumétrie).
MIN_DISPLAY_SURFACE_M2 = 2.0

@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Auto-réconciliation LÉGÈRE du schéma au démarrage (recyclage d'environnement).

    Répare en quelques secondes : tables, colonnes critiques (geom_2975, prospection),
    triggers, index, cache enrichment. NE lance JAMAIS d'ingestion ni de backfill lourd
    (cf. models.ensure_schema). Best-effort : si la DB est injoignable, l'app démarre
    quand même (l'état est exposé par /readyz, jamais masqué)."""
    import logging

    # uvicorn ne configure pas le logger racine : sans ce basicConfig, les événements INFO
    # de LA BUSE (démarrage, connexions réussies) seraient invisibles. No-op si déjà configuré.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s — %(message)s")
    log = logging.getLogger("labuse")
    from ..db import engine as _engine
    # M6-A5 : la remédiation de schéma est sérialisée entre les workers uvicorn par un VERROU
    # CONSULTATIF Postgres. Au 1er boot après une migration, les 2 workers lançaient `CREATE TYPE`
    # en même temps → l'un tombait sur une violation d'unicité pg_type (schéma=échec bénin mais
    # bruyant, faux positif d'alerte à chaque migration). Le lock fait ATTENDRE le 2e worker ;
    # il ne voit ensuite que des objets existants (checkfirst les saute) → les deux finissent
    # `schéma=ok`. Clé arbitraire stable propre à LA BUSE.
    _SCHEMA_LOCK = 0x1ABE5C
    _lock_conn = None
    try:
        _lock_conn = _engine().connect()
        _lock_conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _SCHEMA_LOCK})
        _lock_conn.commit()
        models.ensure_schema(_engine())
        # tables des routeurs (modules/ia/events/partners/projets) : l'ancien
        # @app.on_event("startup") était MORT depuis le passage au lifespan (FastAPI
        # ignore on_event quand lifespan est fourni) — les ensures vivent ICI.
        from .courrier import ensure_tables as _courrier_ens
        from .events import ensure_tables as _events_ens
        from .ia import ensure_tables as _ia_ens
        from .modules import ensure_tables as _modules_ens
        from .partners import ensure_tables as _partners_ens
        from .projets import ensure_tables as _projets_ens
        from .protection import ensure_tables as _protection_ens
        # C-bis : segments (Vues) retiré. H : crm_columns conservé.
        from .crm_columns import ensure_tables as _crm_columns_ens
        for _ens in (_modules_ens, _ia_ens, _events_ens, _partners_ens, _projets_ens,
                     _protection_ens, _courrier_ens, _crm_columns_ens):
            _ens(_engine())
        # AUDIT PAIEMENT · SEC-IDOR — comptes + cloison multi-tenant (compte_id sur les
        # tables à données client). Après les ensures des modules (les tables existent).
        from ..comptes import ensure_tables as _comptes_ens
        from .tenant import ensure_scoping as _scoping_ens
        with session_scope() as _s:
            _comptes_ens(_s)
            _scoping_ens(_s)
        # M26-A — Copilote : après comptes (FK agent_runs.compte_id posée si la table existe).
        from ..copilote.tables import ensure_tables as _copilote_ens
        _copilote_ens(_engine())
        app.state.schema_heal = "ok"
    except Exception as exc:  # noqa: BLE001 — l'app doit démarrer ; /readyz dira la vérité
        app.state.schema_heal = f"échec : {type(exc).__name__}: {exc}"
    finally:
        if _lock_conn is not None:
            try:
                _lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _SCHEMA_LOCK})
                _lock_conn.commit()
            except Exception:  # noqa: BLE001 — le verrou tombe de toute façon à la fermeture de session
                pass
            _lock_conn.close()
    from . import auth
    s = config.get_settings()
    log.info("LA BUSE démarrée · env=%s · auth=%s · schéma=%s",
             s.env,
             "active" if auth.enabled() else "désactivée (local)",
             app.state.schema_heal)
    if auth.enabled() and not auth.configured():
        log.error("env=%s sans LABUSE_AUTH_PASSWORD : routes métier en 503 (fail-closed) "
                  "jusqu'à configuration.", s.env)
    # Fail-closed (P0-3) : hors 'local', LABUSE_SECRET_KEY est OBLIGATOIRE (sinon jeton de
    # paiement forgeable). Absente en prod/pilote → on refuse de démarrer, message clair.
    auth.exiger_secret_prod()
    if not s.secret_key:  # ici forcément 'local' : clé éphémère (sessions perdues au reboot)
        log.warning("LABUSE_SECRET_KEY absente (env=local) : clé de session éphémère "
                    "(les sessions ne survivront pas à un redémarrage).")
    # M-B : garde de CÂBLAGE scoring — BLOQUANTE au boot (statique, sans base, ~0 ms). Un câblage
    # incohérent (couche YAML sans implémentation ou l'inverse, sévérité inconnue, bonus_key absente
    # de la config) ne doit PAS servir. Fail-closed, comme exiger_secret_prod ci-dessus. La part DB
    # (kinds spatiaux, ~1,2 s) est déléguée au RUN de scoring, pas au boot.
    from ..cascade.cablage import check_cablage_scoring
    check_cablage_scoring()
    yield


app = FastAPI(
    title="LABUSE — radar foncier",
    version="0.1.0",
    description="La donnée publique ne suffit pas. LABUSE l'interprète. "
                "Pré-analyse — constructibilité/propriété/rentabilité jamais garanties.",
    lifespan=_lifespan,
)
# CORS par environnement : tout-venant utile en LOCAL (dev) seulement. En pilote/production,
# le front est servi par la même origine → aucun CORS requis, sauf LABUSE_PUBLIC_URL explicite.
_cors_origins = (["*"] if config.get_settings().env == "local"
                 else ([config.get_settings().public_url] if config.get_settings().public_url else []))
app.add_middleware(
    CORSMiddleware, allow_origins=_cors_origins, allow_methods=["*"], allow_headers=["*"],
)
# Compression gzip : les couches carte (/map/*.geojson) pèsent 20-30 Mo non compressées et
# échouaient à travers les tunnels d'aperçu distants ; gzip les divise par ~9 (charge fiable).
# N'affecte NI la DB NI le scoring NI les verdicts — uniquement le transport.
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def _security_headers(request, call_next):
    """AUDIT PAIEMENT · LEX-D — en-têtes de sécurité de base sur CHAQUE réponse (défense en
    profondeur : le Caddy prod en pose déjà, l'app les garantit aussi en local/QA)."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    # P1 : HSTS quand la requête est en HTTPS (derrière Caddy, uvicorn --proxy-headers lit
    # X-Forwarded-Proto). JAMAIS en clair : un HSTS posé sur du http local bloquerait l'accès
    # http à localhost. Absent du Caddy prod / commenté dans nginx → l'app le garantit.
    if request.url.scheme == "https":
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


@app.middleware("http")
async def _fix_double_encoded_query(request, call_next):
    """Répare les query-strings DOUBLE-ENCODÉES par certains tunnels/proxys d'aperçu.

    Symptôme : le navigateur envoie `?commune=Le%20Tampon` (espace = %20), mais le tunnel
    ré-encode le « % » → le serveur reçoit `Le%2520Tampon` → décodé une fois en `Le%20Tampon`
    LITTÉRAL → ne matche aucune commune → réponses VIDES (carte/KPIs à 0) pour toute commune à
    espace/accent (Le Tampon, Le Port, L'Étang-Salé…). On enlève la couche d'encodage en trop.
    Transport uniquement : ne touche NI la DB NI le scoring NI les verdicts. Inerte si pas de
    double-encodage (déclenché seulement si « %25 » est présent dans la query-string)."""
    qs = request.scope.get("query_string", b"")
    if b"%25" in qs:
        request.scope["query_string"] = unquote(qs.decode("latin-1")).encode("latin-1")
    return await call_next(request)


# Anti-scraping (mandat wave-adresses Lot 3) — enregistré AVANT _auth_guard donc exécuté
# APRÈS lui (Starlette : dernier enregistré = plus externe) : seuls les appels authentifiés
# consomment quotas et rate limit.
from .protection import garde_protection as _garde_protection  # noqa: E402

app.middleware("http")(_garde_protection)


@app.middleware("http")
async def _auth_guard(request, call_next):
    """Garde d'authentification PILOTE (cf. api/auth.py) — protège TOUTES les routes métier.

    Publiques : /healthz, /health, /readyz (détails réduits sans session), /login, /logout
    (+ /docs en local uniquement). Navigation sans session → redirection /login ;
    appel API sans session → 401 JSON ; pilote sans mot de passe configuré → 503 (fail-closed)."""
    from fastapi.responses import JSONResponse

    from . import auth

    path = request.url.path
    # AUDIT PAIEMENT · SEC-IDOR — résout le compte de la session et le pose sur request.state
    # (scope Starlette partagé jusqu'à l'endpoint) : la cloison multi-tenant s'applique partout.
    cookie = request.cookies.get(auth.COOKIE)
    info = auth.session_info(cookie)
    request.state.compte_id = info["compte_id"] if info else None
    if not auth.enabled() or auth.is_public(path):
        return await call_next(request)
    if info is not None or auth.token_ok(cookie):
        return await call_next(request)
    if not auth.configured():
        return JSONResponse(status_code=503, content={
            "detail": "Authentification non configurée (LABUSE_AUTH_PASSWORD absent) — accès fermé."})
    if auth.wants_html(path):
        return RedirectResponse("/login", status_code=302)
    return JSONResponse(status_code=401, content={"detail": "Authentification requise."})


def get_db() -> Iterator[Session]:
    with session_scope() as s:
        yield s


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "produit": "LABUSE"}


@app.get("/healthz")
def healthz() -> dict:
    """Niveau 1 — le PROCESS répond. Zéro accès DB : ne dit RIEN de l'état des données
    (c'est /readyz et /demo-status qui le disent — ne jamais confondre)."""
    return {"status": "ok"}


# ── 404 de NAVIGATION habillé (revue UI/UX S68 · O3 : porté au design system coffre_ui) :
# une faute d'URL au navigateur ne montre plus du JSON brut sur fond blanc, et naît des mêmes
# tokens que la porte/les pages légales (zéro hex local), ton sobre, toujours une sortie (LOI-2).
# Les appels API (Accept: */* ou application/json) gardent le JSON FastAPI exact — golden et
# clients inchangés.
from . import coffre_ui as _coffre_ui  # noqa: E402

_NOT_FOUND_HTML = _coffre_ui.page("page introuvable", _coffre_ui.OISEAU + """
<div class="big"><h1>Page introuvable</h1>
<p class="sub">cette adresse n'existe pas</p>
<p style="font-size:13px">Vérifiez l'URL — ou revenez à votre espace.</p>
<p style="margin-top:20px"><a href="/" class="pill">← Revenir à LABUSE</a></p></div>""")


@app.exception_handler(StarletteHTTPException)
async def _http_exception(request: Request, exc: StarletteHTTPException):
    from fastapi.responses import HTMLResponse, JSONResponse

    if (exc.status_code == 404 and request.method == "GET"
            and "text/html" in (request.headers.get("accept") or "")):
        return HTMLResponse(_NOT_FOUND_HTML, status_code=404)
    # comportement FastAPI par défaut, à l'identique (detail + status + headers éventuels)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                        headers=getattr(exc, "headers", None))


# ───────────────────────────── Connexion pilote ─────────────────────────────

@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    from fastapi.responses import HTMLResponse

    from . import auth

    # B2 (BLOC B) : le proto Vue « /app » est RETIRÉ (tag archive/proto-vue) — la cible
    # post-login est LA RACINE : en prod Caddy y sert le front, en local `/` → /socle/.
    if not auth.enabled():                       # auth désactivée (local) → rien à demander
        return RedirectResponse("/", status_code=302)
    if auth.token_ok(request.cookies.get(auth.COOKIE)):
        return RedirectResponse("/", status_code=302)
    return HTMLResponse(auth.login_page())


@app.post("/login", include_in_schema=False)
async def login_submit(request: Request):
    """Connexion : formulaire urlencodé (parse stdlib — zéro dépendance) ou JSON.
    Échec → message NEUTRE + petit délai (anti force-brute) + journalisation."""
    from urllib.parse import parse_qs

    from fastapi.responses import HTMLResponse

    from . import auth

    body = await request.body()
    password, identifiant = "", ""
    ctype = request.headers.get("content-type", "")
    if "json" in ctype:
        try:
            data = json.loads(body or b"{}")
            password = str(data.get("password") or "")
            identifiant = str(data.get("identifiant") or "")
        except ValueError:
            password = ""
    else:
        q = parse_qs(body.decode("utf-8", "replace"))
        password = (q.get("password") or [""])[0]
        identifiant = (q.get("identifiant") or [""])[0].strip()

    # PREMIER EURO · E1 — identifiant fourni = LOGIN UTILISATEUR (email + argon2id, verrou
    # après N échecs) ; identifiant vide = mot de passe PILOTE (compat — meurt à la bascule).
    if identifiant:
        from ..comptes import creer_session, verifier_login
        from ..db import session_scope
        with session_scope() as db:
            u = verifier_login(db, identifiant, password)
            if not u:
                auth.log_event("login_failed", request)
                auth.slow_failure()
                return HTMLResponse(auth.login_page(error=True), status_code=401)
            # REPRISE DE PAIEMENT (né du test Vic) : identifiants corrects mais compte
            # jamais payé (Checkout refusé/abandonné) → on relance un Checkout NEUF au
            # lieu d'ouvrir l'app. Le token d'invitation consommé n'est plus un cul-de-sac.
            if u["statut_compte"] == "invite":
                auth.log_event("login_ok_paiement_du", request)
                # ROB-B — filet du pire cas : si le paiement a réussi mais le webhook a été
                # perdu, on RÉCONCILIE avec Stripe (souscription active) plutôt que de relancer
                # un Checkout (double paiement). « A payé ⇒ a accès ».
                from ..facturation import reconcile_abonnement
                if reconcile_abonnement(db, u["compte_id"], identifiant):
                    tok = creer_session(db, u["utilisateur_id"])
                    resp = RedirectResponse("/", status_code=303)
                    resp.set_cookie(value=f"u.{tok}", **auth.cookie_kwargs())
                    return resp
                # → écran de bascule Checkout (design validé partie E), la même page de
                # confiance que l'onboarding ; la mécanique de paiement reste inchangée.
                from .coffre_ui import pay_token
                return RedirectResponse(f"/onboarding/paiement?t={pay_token(u['compte_id'])}",
                                        status_code=303)
            tok = creer_session(db, u["utilisateur_id"])
        auth.log_event("login_ok", request)
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(value=f"u.{tok}", **auth.cookie_kwargs())
        return resp

    if not auth.configured() or not auth.password_ok(password):
        auth.log_event("login_failed", request)
        auth.slow_failure()
        return HTMLResponse(auth.login_page(error=True), status_code=401)
    auth.log_event("login_ok", request)
    resp = RedirectResponse("/", status_code=303)   # B2 : la racine (Caddy en prod, /socle/ en local)
    resp.set_cookie(value=auth.make_token(), **auth.cookie_kwargs())
    return resp


@app.get("/logout", include_in_schema=False)
def logout(request: Request):
    from . import auth

    auth.log_event("logout", request)
    # P1 : RÉVOQUER la session côté serveur, pas seulement supprimer le cookie — sinon le
    # jeton restait valide en base jusqu'à son expiration (12 h) et un cookie rejoué gardait
    # l'accès. Sessions utilisateur uniquement (« u.<token> ») ; le jeton pilote est sans état.
    cookie = request.cookies.get(auth.COOKIE)
    if cookie and cookie.startswith("u."):
        try:
            from ..comptes import detruire_session
            from ..db import session_scope
            with session_scope() as db:
                detruire_session(db, cookie[2:])
        except Exception:  # noqa: BLE001 — déconnexion best-effort : le cookie est supprimé quoi qu'il arrive
            pass
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


@app.get("/readyz")
def readyz(request: Request, commune: str | None = None):
    """Niveau 2+3 — schéma prêt ET données critiques présentes (503 sinon, avec l'action
    à lancer). Session ouverte à la main : une DB injoignable rend un 503 propre, pas un 500.

    PUBLIC pour le monitoring, mais DÉTAILS RÉDUITS sans session quand l'auth est active
    (un sonde externe voit ready/checked_at, pas la liste des couches ni la commune)."""
    from fastapi.responses import JSONResponse

    from .. import state
    from . import auth

    name = commune or config.get_settings().pilot_commune_name
    try:
        with session_scope() as s:
            st = state.readiness(s, name)
    except Exception as exc:  # noqa: BLE001 — DB down → 503 explicite
        return JSONResponse(status_code=503, content={
            "ready": False, "error": f"base injoignable : {type(exc).__name__}",
            "actions": ["vérifier PostgreSQL / LABUSE_DATABASE_URL"]})
    if auth.enabled() and not auth.token_ok(request.cookies.get(auth.COOKIE)):
        st = {"ready": st["ready"], "checked_at": st["checked_at"]}
    return JSONResponse(status_code=200 if st.get("ready") else 503, content=st)


# ── Cache mémoire TTL pour endpoints de lecture coûteux (safe-bugfix #6/#7) ───────────────
# EN MÉMOIRE process uniquement (rien en DB) ; résultat IDENTIQUE au calcul (mêmes données),
# borné en taille, péremption courte par TTL. Vidé par clear_mem_cache() (tests).
_MEM_CACHE: dict = {}
_MEM_LOCK = threading.Lock()
_MEM_MAX = 256
# M6.2 perf : verrous single-flight PAR CLÉ — sans eux, N requêtes concurrentes sur une clé
# expirée recalculent TOUTES en même temps (stampede : /stats P95 mesuré à ~4 s sous 10 req).
_MEM_FLIGHT: dict = {}
_MEM_FLIGHT_LOCK = threading.Lock()

# M6.2 perf : cache du GEOJSON COMMUNE (string). Le json_build_object de 51k features × 26
# propriétés coûte ~11 s côté Postgres (plancher incompressible, mesuré EXPLAIN ANALYZE) —
# on le paie UNE fois par (commune, run), pas à chaque requête. Borné en OCTETS (les grosses
# communes pèsent ~47 Mo) ; single-flight (une seule génération concurrente) ; TTL aligné sur
# le Cache-Control navigateur. Invalidé naturellement au changement de run (clé = source).
from collections import OrderedDict as _OrderedDict  # noqa: E402

_GEOJSON_CACHE: "_OrderedDict[tuple, tuple[float, str]]" = _OrderedDict()
_GEOJSON_BYTES = 0
_GEOJSON_MAX_BYTES = 220 * 1024 * 1024   # ~4-5 grosses communes ; le reste évincé (LRU)
_GEOJSON_TTL = 600.0
_GEOJSON_LOCK = threading.Lock()
_GEOJSON_FLIGHT: dict = {}


def _geojson_cached(key: tuple, compute) -> str:
    """Renvoie le geojson-string mémorisé sous `key` (single-flight + LRU borné en octets)."""
    now = time.monotonic()
    with _GEOJSON_LOCK:
        hit = _GEOJSON_CACHE.get(key)
        if hit is not None and (now - hit[0]) < _GEOJSON_TTL:
            _GEOJSON_CACHE.move_to_end(key)
            return hit[1]
    with _MEM_FLIGHT_LOCK:
        flight = _GEOJSON_FLIGHT.get(key)
        if flight is None:
            flight = _GEOJSON_FLIGHT[key] = threading.Lock()
    with flight:
        with _GEOJSON_LOCK:
            hit = _GEOJSON_CACHE.get(key)
            if hit is not None and (time.monotonic() - hit[0]) < _GEOJSON_TTL:
                _GEOJSON_CACHE.move_to_end(key)
                return hit[1]
        val = compute()
        global _GEOJSON_BYTES
        with _GEOJSON_LOCK:
            old = _GEOJSON_CACHE.pop(key, None)
            if old is not None:
                _GEOJSON_BYTES -= len(old[1])
            _GEOJSON_CACHE[key] = (time.monotonic(), val)
            _GEOJSON_BYTES += len(val)
            while _GEOJSON_BYTES > _GEOJSON_MAX_BYTES and len(_GEOJSON_CACHE) > 1:
                _, (_, ev) = _GEOJSON_CACHE.popitem(last=False)
                _GEOJSON_BYTES -= len(ev)
    return val


def clear_mem_cache() -> None:
    """Vide le cache mémoire des endpoints (tests / invalidation manuelle)."""
    with _MEM_LOCK:
        _MEM_CACHE.clear()


def _mem_cached(key, ttl: float, compute):
    """Renvoie compute() en le mémorisant `ttl` s sous `key` (lecture seule, en mémoire).

    M6.2 : SINGLE-FLIGHT — une seule exécution de `compute()` par clé à la fois. Les requêtes
    concurrentes sur une clé expirée attendent la 1re et réutilisent son résultat (fin du
    stampede) au lieu de recalculer chacune."""
    now = time.monotonic()
    with _MEM_LOCK:
        hit = _MEM_CACHE.get(key)
        if hit is not None and (now - hit[0]) < ttl:
            return hit[1]
    # un verrou par clé : le 1er calcule, les autres attendent puis relisent le cache frais.
    with _MEM_FLIGHT_LOCK:
        flight = _MEM_FLIGHT.get(key)
        if flight is None:
            flight = _MEM_FLIGHT[key] = threading.Lock()
    with flight:
        with _MEM_LOCK:                                      # re-vérif : déjà calculé pendant l'attente ?
            hit = _MEM_CACHE.get(key)
            if hit is not None and (time.monotonic() - hit[0]) < ttl:
                return hit[1]
        val = compute()
        with _MEM_LOCK:
            _MEM_CACHE[key] = (time.monotonic(), val)
            if len(_MEM_CACHE) > _MEM_MAX:                   # éviction simple des plus anciens
                for k in sorted(_MEM_CACHE, key=lambda k: _MEM_CACHE[k][0])[:64]:
                    _MEM_CACHE.pop(k, None)
    return val


@app.get("/demo-status")
def demo_status_endpoint(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Niveau 4 — état COMPLET de la démo (healthcheck 13 points, parcelles de démo
    conformes, cache chaud) + actions à lancer. Toujours 200 (informatif, panneau admin) ;
    le drapeau `ready_for_demo` fait foi. Résultat mémorisé (cache mémoire 30 s, #6)."""
    from .. import state

    name = commune or config.get_settings().pilot_commune_name
    return _mem_cached(("demo-status", name), 30.0, lambda: state.demo_status(db, name))


@app.get("/coverage")
def coverage(db: Session = Depends(get_db)) -> dict:
    """Couverture des couches excluantes/flaggantes : ce qui est intégré vs absent.

    Pilote le bandeau d'avertissement (verdicts partiels) et la notion d'opportunité
    fiable. `present` = au moins une entité de ce `kind` est ingérée.
    """
    present = {k for (k,) in db.execute(text("SELECT DISTINCT kind FROM spatial_layers")).all()}

    def _present(kinds: list[str]) -> bool:
        return any(k in present for k in kinds)

    layers = [{"kind": key, "label": label, "present": _present(kinds)}
              for key, (label, kinds) in CRITICAL_LAYERS.items()]
    missing = [label for _, (label, kinds) in CRITICAL_LAYERS.items() if not _present(kinds)]
    return {
        "critical_layers": layers,
        "missing": missing,
        "complete": not missing,
        "reliable_requires": [CRITICAL_LAYERS[k][0] for k in RELIABLE_REQUIRED],
        "reliable_ready": all(_present(CRITICAL_LAYERS[k][1]) for k in RELIABLE_REQUIRED),
    }


@app.get("/demo")
def demo_overview_endpoint(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Panneau « Démo guidée » : parcelles de démo (rôle, statut attendu, statut LIVE).

    Ne masque AUCUNE donnée réelle — simple raccourci vers des parcelles DÉJÀ validées,
    avec un drapeau `conforme` (statut live == attendu) pour repérer une dérive avant une démo."""
    from .. import demo as demo_mod

    name = commune or config.get_settings().pilot_commune_name
    parcels = demo_mod.demo_overview(db, name)
    return {"commune": name, "parcels": parcels, "all_conform": all(p["conforme"] for p in parcels)}


# ───────────────────────────── Sources de données ─────────────────────────────

#: UX V1 ajout A — rattache un run d'ingestion (libellé `commune`) à sa source de catalogue.
#: Les runs par commune sont l'ingestion du PARCELLAIRE (cadastre bulk) ; les runs « 974 (…) »
#: portent leur famille dans le libellé. Fonction pure, testée.
def _source_pour_run(commune: str | None) -> str | None:
    if not commune:
        return None
    if commune.startswith("974 (SDES Sitadel3"):
        return "SITADEL (autorisations d'urbanisme)"
    if commune.startswith("974 (tuiles ortho"):
        return "Géoplateforme IGN"
    # M84 — les ingestions J+2 laissent désormais une trace ingestion_runs : les câbler ICI, sinon le
    # `else` cadastre s'approprierait leur date d'ingestion (faux positif de fraîcheur sur le cadastre).
    if commune.startswith("974 (BODACC"):
        return "BODACC (procédures collectives)"
    if commune.startswith("974 (DPE ADEME"):
        return "DPE ADEME (logements existants)"
    if commune.startswith("974 (Géorisques"):
        return "Géorisques"
    return "Cadastre Etalab (bulk DGFiP/Etalab)"


@app.get("/sources")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    # M71 BLOC A (audits M66/M66-B) : la page Sources ne sert QUE les sources réellement
    # branchées (status='connecte'). Hubs, a_faire, partiel, manuel n'y figurent plus —
    # le catalogue complet reste en base, seule la VITRINE est filtrée. Comptage 100 %
    # dynamique côté front ; les DOUBLONS (technical_notes commençant par « DOUBLON de »)
    # restent listés mais sont exclus du comptage du bandeau (champ `doublon` ci-dessous).
    rows = db.execute(
        select(models.DataSource)
        .where(models.DataSource.status == DataSourceStatus.CONNECTE)
        .order_by(models.DataSource.category, models.DataSource.name)
    ).scalars().all()
    # UX V1 ajout A (page « Sources & fraîcheur ») : la date affichée est LUE dans
    # ingestion_runs (jamais codée en dur) — max(finished_at|started_at) des runs ok par source.
    runs = db.execute(text(
        "SELECT commune, max(coalesce(finished_at, started_at)) AS fin, count(*) AS n "
        "FROM ingestion_runs WHERE status IN ('ok', 'success') GROUP BY commune")).mappings().all()
    # VUES item 4 : dernière VÉRIFICATION « à la dernière version publiée » par source —
    # lue dans source_checks (vide tant que le mandat d'audit data n'a pas tourné).
    # Le front n'affiche la mention QUE si la date existe : jamais une date inventée.
    checks = {int(r["data_source_id"]): r["verified_at"] for r in db.execute(text(
        "SELECT data_source_id, max(verified_at) AS verified_at "
        "FROM source_checks GROUP BY data_source_id")).mappings().all()}
    ingestions: dict[str, dict] = {}
    for r in runs:
        name = _source_pour_run(r["commune"])
        if not name:
            continue
        cur = ingestions.setdefault(name, {"derniere": None, "runs": 0})
        cur["runs"] += int(r["n"])
        if cur["derniere"] is None or (r["fin"] and r["fin"] > cur["derniere"]):
            cur["derniere"] = r["fin"]
    # J+2 (fraîcheur) : la date de la DERNIÈRE DONNÉE en base par source (≠ date d'ingestion) —
    # les dates parlent seules, wording sobre. Mapping via fraicheur.SOURCES (ds_name ILIKE).
    donnees: dict[str, str] = {}
    statuts: dict[str, dict] = {}   # M84 — verdict de fraîcheur live par source (statut « en retard »)
    try:
        from fnmatch import fnmatch

        from ..ingestion import fraicheur
        etats = fraicheur.etat_sources(db)
        for e in etats:
            motif = fraicheur.SOURCES[e["source"]]["ds_name"].lower().replace("%", "*")
            for src in rows:
                if fnmatch(src.name.lower(), motif):
                    if e["derniere_donnee"]:
                        donnees[src.name] = e["derniere_donnee"]
                    # statut dérivé du MÊME delta que la date affichée : cohérence (doctrine M73).
                    statuts[src.name] = {"statut": e["statut"], "seuil_jours": e["seuil_jours"],
                                         "delta_jours": e["delta_donnee_jours"]}
    except Exception:  # noqa: BLE001 — l'affichage de fraîcheur ne casse jamais la page Sources
        pass
    # B3 (BLOC B) : l'état du RADAR par source (dernière publication détectée amont) —
    # lecture seule, [] tant que `labuse radar-sources` n'a jamais tourné.
    from ..radar import etat_radar
    radar = {r["source_name"]: r for r in etat_radar(db)}
    # M74 C bis / M87 P0 — la page Sources = la VITRINE mesurée : définition CANONIQUE partagée avec
    # le compteur d'accueil (`sources_catalog.est_affichee`) : hors DOUBLON de catalogue ET hors
    # masquées (Office de l'eau, morte à l'affichage — ingestion/table conservées).
    from .. import sources_catalog as _srccat
    served = [s for s in rows if _srccat.est_affichee(s.name, s.technical_notes)]
    return [
        {
            "id": s.id, "name": s.name, "category": s.category, "provider": s.provider,
            "access_type": s.access_type,
            "status": s.status.value if s.status else None,
            "reliability_level": s.reliability_level.value if s.reliability_level else None,
            "rate_limit": s.rate_limit, "last_sync_at": s.last_sync_at,
            "documentation_url": s.documentation_url, "endpoint_url": s.endpoint_url,
            "legal_notes": s.legal_notes, "technical_notes": s.technical_notes,
            # M86 — millésime amont CENTRALISÉ (data_sources.source_millesime, écrit par persist_millesime
            # ou seed) : le front le LIT au lieu de coder des dates en dur (correction factuelle M86).
            "source_millesime": s.source_millesime,
            # M74 C bis — NOTE DE NATURE visible (proxy / servi par proxys) : une source proxy ne
            # doit JAMAIS être présentée comme la source officielle (doctrine anti-faux-positif).
            "nature": _source_nature(s.name, s.technical_notes),
            "testable": s.name in _connector_names(),
            "derniere_ingestion": ingestions.get(s.name, {}).get("derniere"),
            "derniere_donnee": donnees.get(s.name),
            "ingestion_runs": ingestions.get(s.name, {}).get("runs", 0),
            "verified_at": checks.get(s.id),
            "radar": radar.get(s.name),
            # M84 — statut de fraîcheur (en_retard / a_jour / cadence_libre / sans_donnee) : un
            # décrochage est VISIBLE sur la page Sources, distinct du radar amont (≠ millésime).
            "fraicheur_statut": statuts.get(s.name, {}).get("statut"),
            "fraicheur_seuil_jours": statuts.get(s.name, {}).get("seuil_jours"),
            "fraicheur_delta_jours": statuts.get(s.name, {}).get("delta_jours"),
        }
        for s in served
    ]


def _source_nature(name: str, notes: str | None) -> dict | None:
    """M74 C bis / M87 P0 — NATURE d'une source (proxy / servi par proxys / curée manuellement), pour un
    affichage visible et non replié. `detail` = la 1re phrase explicative. None si directe. `curee=True`
    et `proxy=True` : le front les rend TOUS deux en pointillé (même visuel)."""
    from .. import sources_catalog as _srccat
    if name in _srccat.SOURCES_CUREES:
        return {"label": "curée manuellement", "detail": _srccat.CUREES_NOTE, "dashed": True}
    n = notes or ""
    if n.startswith("SERVI PAR PROXYS"):
        label = "servi par proxys"
    elif n.startswith("PROXY"):
        label = "proxy"
    else:
        return None
    detail = n.split(" : ", 1)[1] if " : " in n else n
    detail = detail.split(". ", 1)[0].rstrip(".") + "."
    return {"label": label, "detail": detail, "dashed": True}


def _connector_names() -> set[str]:
    from ..connectors import REGISTRY

    return set(REGISTRY.keys())


@app.post("/sources/{source_id}/test")
def test_source(source_id: int, db: Session = Depends(get_db)) -> dict:
    src = db.get(models.DataSource, source_id)
    if not src:
        raise HTTPException(404, "Source inconnue")
    from ..connectors import get_connector

    connector = get_connector(src.name)
    if not connector:
        return {"source": src.name, "ok": False, "message": "Pas de connecteur live (import/manuel/à faire)."}
    return connector.test_connection().as_dict()


# ───────────────────────────── Parcelles ─────────────────────────────

def _latest_eval(db: Session, parcel_id: int) -> models.ParcelEvaluation | None:
    return db.execute(
        select(models.ParcelEvaluation)
        .where(models.ParcelEvaluation.parcel_id == parcel_id)
        .order_by(models.ParcelEvaluation.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()


#: exclusion dure de l'étage 0 (run SERVI) — la même expression partout (M5 règle 1).
_ETAGE0_SQL = "(d.status IN ('exclue', 'faux_positif_probable'))"


# ── Adresse BAN (M6 Phase 2a, §1.8) ──────────────────────────────────────────
# La MEILLEURE adresse BAN de la parcelle (index inverse `adresse_parcelles`, indexé idu) :
# priorité au rattachement direct du point ('principal'), puis numéro le plus bas —
# déterministe, MÊME règle que segments/registry.py (publipostage) et pre_dossier (CERFA).
_BAN_ORDER = ("(ap.source = 'principal') DESC, (a.numero IS NULL), "
              "NULLIF(regexp_replace(a.numero, '\\D', '', 'g'), '')::int NULLS LAST, a.id_ban")


def _ban_lateral(idu_expr: str) -> str:
    """Fragment LEFT JOIN LATERAL (colonnes ban_voie/ban_cp/ban_commune) — à joindre APRÈS
    la pagination (page de :lim lignes) : jamais de N+1, coût = 1 lookup indexé par ligne."""
    return ("LEFT JOIN LATERAL (SELECT trim(concat_ws(' ', a.numero, a.rep, a.voie)) AS ban_voie, "
            "a.code_postal AS ban_cp, a.commune AS ban_commune "
            "FROM adresse_parcelles ap JOIN adresses a ON a.id_ban = ap.id_ban "
            f"WHERE ap.idu = {idu_expr} ORDER BY {_BAN_ORDER} LIMIT 1) ban ON true")


def _ban_ready(db: Session) -> bool:
    """Tables BAN présentes ? (ingestion ban_adresses) — mémorisé 5 min. Absentes (base de
    test nue, install sans ingestion) → adresse None partout, le front affiche
    « Adresse non disponible » (jamais un champ vide ni une 500)."""
    return _mem_cached(("ban-ready",), 300.0, lambda: bool(db.execute(text(
        "SELECT to_regclass('adresses') IS NOT NULL"
        " AND to_regclass('adresse_parcelles') IS NOT NULL")).scalar()))


def _zone_plu_ready(db: Session) -> bool:
    """Table dérivée `parcel_zone_plu` (M6.1 item 1 — zone PLU dominante par parcelle)
    présente ? Mémorisé 60 s (elle apparaît après le build one-shot) ; absente → colonnes
    zone_lib/zone_fam NULL dans le geojson, le front replie proprement."""
    return _mem_cached(("zone-plu-ready",), 60.0, lambda: bool(db.execute(text(
        "SELECT to_regclass('parcel_zone_plu') IS NOT NULL")).scalar()))


def _adresse_ready(db: Session) -> bool:
    """Table dérivée `parcel_adresse` (M6.2 — meilleure adresse BAN matérialisée) présente ?
    Mémorisé 60 s. Présente → LEFT JOIN indexé (remplace le LATERAL par-parcelle coûteux) ;
    absente → repli sur le lateral BAN (`_ban_ready`), sémantiquement identique."""
    return _mem_cached(("adresse-ready",), 60.0, lambda: bool(db.execute(text(
        "SELECT to_regclass('parcel_adresse') IS NOT NULL")).scalar()))


def _fmt_ban(voie: str | None, cp: str | None, commune: str | None) -> str | None:
    """« 2 Impasse des Caramboles, 97414 Entre-Deux » — None si aucune adresse (le front
    porte le libellé d'absence, le payload reste honnête)."""
    if not voie:
        return None
    tail = " ".join(x for x in (cp, commune) if x)
    return f"{voie}, {tail}" if tail else voie


def _m28_badges(db: Session, idu: str) -> dict:
    """Badges M28 : `filtre_bati` (ratio, décision, motif, année étiquetée, source amont datée)
    + `geometrie` (largeur inscriptible, Polsby-Popper, contrainte <8 m ou PP<0,1 — Sourcé,
    cadastre Etalab 2026-06). Lecture seule des caches ; absents → clés absentes."""
    out: dict = {}
    fb = db.execute(text(
        "SELECT ratio_pct, etage, annee_construction, annee_etiquette, passoire, divisible, "
        "decision, motif FROM parcel_filtre_bati WHERE idu = :i"), {"i": idu}).mappings().first()
    if fb:
        out["filtre_bati"] = {**dict(fb), "ratio_pct": round(fb["ratio_pct"], 1),
                              "source": "max(BD TOPO éd. 2026-06-15, CoSIA PVA juil.-août 2025)"}
    # M29 (b)/(b) : signaux mérite/héritage (#9) + acquérabilité assemblage (#11) — fiche
    # seulement, AUCUN effet de classement. Libellés factuels arbitrés Vic 05/08.
    et = db.execute(text(
        "SELECT entree_le, geste, nature FROM parcel_entree_tete WHERE idu = :i"),
        {"i": idu}).mappings().first()
    if et:
        out["entree_tete"] = {
            "entree_le": et["entree_le"].isoformat(), "geste": et["geste"],
            "nature": et["nature"],
            "libelle": f"entrée dans la sélection à la bascule du {et['entree_le'].strftime('%d/%m/%Y')} — "
                       + ("signal inchangé" if et["nature"] == "signal_inchange"
                          else "signal en progression"),
            "etiquette": "Sourcé", "source": "archives de bascule (contrib_d/rang par run)"}
    aq = db.execute(text(
        "SELECT classe, n_meme_siren, n_siren_distincts, n_indetermine, source, "
        "source_millesime, etiquette FROM parcel_acquerabilite WHERE idu = :i"),
        {"i": idu}).mappings().first()
    if aq:
        lib = {"meme_proprietaire_pm": "même propriétaire (PM) — source DGFiP/Cerema"
                                       + (f", {aq['source_millesime']}" if aq["source_millesime"]
                                          else " (millésime amont non tracé — Estimé)"),
               "proprietaires_distincts_pm": "propriétaires distincts (PM)",
               "propriete_non_determinable": "propriété non déterminable"}[aq["classe"]]
        out["acquerabilite"] = {**dict(aq), "libelle": lib}
    g = db.execute(text(
        "SELECT largeur_inscriptible_m, polsby_popper FROM parcel_geometrie WHERE idu = :i"),
        {"i": idu}).mappings().first()
    if g and (float(g["largeur_inscriptible_m"]) < 8 or float(g["polsby_popper"]) < 0.1):
        out["geometrie"] = {**dict(g), "contrainte": True, "etiquette": "Sourcé",
                            "source": "cadastre Etalab 2026-06 (méthodes M-C)"}
    return out


def _ban_adresse(db: Session, idu: str) -> str | None:
    """Adresse BAN de LA parcelle (fiche, pipeline) — 1 lookup indexé, None si aucune."""
    if not _ban_ready(db):
        return None
    r = db.execute(text(
        "SELECT trim(concat_ws(' ', a.numero, a.rep, a.voie)) AS voie, a.code_postal AS cp, "
        "a.commune AS com FROM adresse_parcelles ap JOIN adresses a ON a.id_ban = ap.id_ban "
        f"WHERE ap.idu = :idu ORDER BY {_BAN_ORDER} LIMIT 1"), {"idu": idu}).mappings().first()
    return _fmt_ban(r["voie"], r["cp"], r["com"]) if r else None


# M45 (P1, clôture RGPD) : couches cascade INTERDITES en critère de requête — dérivées d'une
# personne PHYSIQUE. Le verrou est CODE (refus API), pas une simple absence d'UI : un partenaire
# API ne doit pas pouvoir les requêter via `flags`/`flags_exclus`. Cf. cadrage M45 (gérant âgé).
FORBIDDEN_FLAGS_RGPD = frozenset({"age_dirigeant"})

# M45 (P2a) : capacité logements ESTIMÉE = SDP résiduelle / ce ratio (SDP moyenne par logement,
# ordre de grandeur métropole/DOM collectif). Point de calcul unique du filtre « capacité ≥ N » ;
# le front l'étiquette « Estimé ». Un logement ~ 70 m² de SDP (surface de plancher, pas habitable).
SDP_PAR_LOGEMENT_M2 = 70


def _guard_flags_rgpd(demandes: list[str]) -> None:
    """Refuse toute couche personne physique en critère de requête (RGPD, cadrage M45).
    Levé AVANT toute exécution SQL — vaut pour l'UI comme pour un partenaire API direct."""
    interdits = [f for f in demandes if f in FORBIDDEN_FLAGS_RGPD]
    if interdits:
        raise HTTPException(status_code=400,
                            detail=f"critère interdit (RGPD, personne physique) : {', '.join(interdits)}")


def _q_v2_where(run_label: str, score_min: int | None,
                surface_min: int | None, surface_max: int | None, sdp_min: int | None,
                evenement: bool, flags: str | None,
                communes: str | None = None, flags_exclus: str | None = None,
                tiers: str | None = None,
                hors_copro: bool = False, veille: bool = False,
                personne_morale: bool = False, zonage: str | None = None,
                defisc_active: bool = False, pc_caduc: bool = False,
                marge_min: int | None = None,
                sdp_max: int | None = None, constructibilite: str | None = None,
                etat_sol: str | None = None, capacite_min: int | None = None,
                zone_plu: str | None = None,
                sous_densite: bool = False, mult_min: float | None = None,
                rang_max: int | None = None, renouvellement: bool = False,
                division_or: bool = False, proprietaire_type: str | None = None,
                etat_societe: str | None = None, copro: str | None = None,
                npnru: bool = False, adresse_absente: bool = False,
                budget_max: int | None = None, charge_min: int | None = None,
                charge_max: int | None = None, prix_marche_min: int | None = None,
                prix_marche_max: int | None = None, marche_fiable: bool = False,
                ca_min: int | None = None, mode_b_rentable: bool = False,
                modeb_travaux_m2: float | None = None, modeb_loyer_m2: float | None = None,
                modeb_rendement_pct: float | None = None,
                signaux: str | None = None,
                droits_residuels: str | None = None) -> tuple[str, dict]:
    """Fragment WHERE partagé liste/stats — les MÊMES filtres que les chips du front. Mode
    « Toute l'île » : le client ne détient plus les 431k features en mémoire, le serveur
    filtre en SQL (chiffres SQL-exacts, mêmes clés que matchScope côté front).

    M5.1 : le PILOTAGE passe au scoring v2 — `tiers` (CSV) filtre par tier EFFECTIF
    (l'étage 0 du run servi prime : une parcelle en étage 0 est « écartée » quel que
    soit son tier v2 ; l'opt-in « ecartee » ne montre QUE l'étage 0 dur).

    M45 (P1) : params `statuts` (matrice morte M37), `v_signal` (Score V retiré, RR 0,51,
    anti-filtre cadrage) et `brulantes` (alias v1.3) RETIRÉS — plus aucun filtre sur une
    source morte. Garde RGPD : `flags`/`flags_exclus` refusent les couches personne physique."""
    conds: list[str] = []
    params: dict = {"runf": run_label}
    if communes:   # secteurs du copilote cadreur (R2) : plusieurs communes à la fois
        conds.append("p.commune = ANY(:f_communes)")
        params["f_communes"] = [c.strip() for c in communes.split(",") if c.strip()]
    if tiers:
        tset = [t.strip() for t in tiers.split(",") if t.strip()]
        actifs = [t for t in tset if t != "ecartee"]
        sub: list[str] = []
        if actifs:
            sub.append(f"(s2.tier = ANY(:f_tiers) AND NOT {_ETAGE0_SQL})")
            params["f_tiers"] = actifs
        if "ecartee" in tset:
            sub.append(_ETAGE0_SQL)
        if sub:
            conds.append("(" + " OR ".join(sub) + ")")
    if hors_copro:  # toggle copro (M5.1 lot 1.5) : masquer les copropriétés (hors classement)
        conds.append("NOT COALESCE(s2.copro, false)")
    if veille:      # veille succession (radar patrimonial)
        conds.append("EXISTS (SELECT 1 FROM parcel_veille_succession vw0 WHERE vw0.parcelle_id = p.idu)")
    if score_min is not None:
        # M129-B : la matrice (q_score) est MORTE — le paramètre est accepté et IGNORÉ (compat
        # URL), jamais un filtre muet sur une colonne NULL. Le front n'envoie plus score_min.
        pass
    if surface_min is not None:
        conds.append("p.surface_m2 >= :f_smin")
        params["f_smin"] = surface_min
    if surface_max is not None:
        conds.append("p.surface_m2 <= :f_smax")
        params["f_smax"] = surface_max
    if sdp_min is not None:
        conds.append("EXISTS (SELECT 1 FROM parcel_residuel r0 WHERE r0.parcel_id = p.id"
                     " AND r0.cause IS NULL AND r0.sdp_residuelle_m2 >= :f_sdp)")  # M125 : lignes calculées seules
        params["f_sdp"] = sdp_min
    if evenement:
        conds.append("EXISTS (SELECT 1 FROM dryrun_cascade_results c0 WHERE c0.parcel_id = p.id"
                     " AND c0.run_label = :runf AND c0.evenement = 'rouge')")
    # M45 (P2) : les filtres de vigilance PROBENT `parcel_flags` (dénormalisée au geste de bascule,
    # non-francs déjà résolus, indexée) — le seq-scan de dryrun_cascade_results (4-7 s île entière)
    # devient un probe indexé. Table run-scopée cohérente-par-construction (garde au build).
    if flags:
        fl = [f.strip() for f in flags.split(",") if f.strip()]
        _guard_flags_rgpd(fl)
        conds.append("EXISTS (SELECT 1 FROM parcel_flags c1 WHERE c1.parcel_id = p.id"
                     " AND c1.run_label = :runf AND c1.layer_name = ANY(:f_flags))")
        params["f_flags"] = fl
    if flags_exclus:   # contraintes RÉDHIBITOIRES (copilote-projet) : écarter les parcelles portant le flag
        flx = [f.strip() for f in flags_exclus.split(",") if f.strip()]
        _guard_flags_rgpd(flx)
        conds.append("NOT EXISTS (SELECT 1 FROM parcel_flags c2 WHERE c2.parcel_id = p.id"
                     " AND c2.run_label = :runf AND c2.layer_name = ANY(:f_flags_x))")
        params["f_flags_x"] = flx
    # M45 (P1) : blocs `v_signal` (Score V) et `brulantes` (alias) RETIRÉS — cf. docstring.
    # M30 avait déjà supprimé `v_bands` (Score V, RR 0,51) ; M45 achève le retrait du dernier
    # vestige Score V côté filtre. Pour une brûlante : `tiers=brulante`.
    # ── M11 B2 : propriétaire PERSONNE MORALE (DGFiP open-data — SCI/société/commune/HLM/État…).
    # PRIVACY : parcelle_personne_morale ne contient QUE des personnes morales (données publiques :
    # SIREN, dénomination, forme juridique) ; une parcelle ABSENTE de la table = personne physique
    # (particulier) → JAMAIS exposée, jamais nommée. Le filtre est un simple test de présence.
    if personne_morale:
        conds.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pm0 WHERE pm0.idu = p.idu)")
    # ── M11 B2 : ZONAGE PLU par famille (U/AU/A/N) — parcel_zone_plu, granularité fiable inter-communes.
    if zonage:
        conds.append("EXISTS (SELECT 1 FROM parcel_zone_plu z0 WHERE z0.idu = p.idu"
                     " AND z0.zone_fam = ANY(:f_zonage))")
        params["f_zonage"] = [z.strip().upper() for z in zonage.split(",") if z.strip()]
    # ── Phase A-1 : fenêtre de sortie de défiscalisation ACTIVE (badge, maisons/monopropriété).
    # Simple test de présence dans la table dérivée defisc_fenetres ; aucun lien avec le run servi.
    if defisc_active:
        conds.append("EXISTS (SELECT 1 FROM defisc_fenetres df0 WHERE df0.idu = p.idu AND df0.fenetre_active)")
    # ── Phase A cycle 2 : PC caduc probable (badge). Simple test de présence dans pc_caducs.
    if pc_caduc:
        conds.append("EXISTS (SELECT 1 FROM pc_caducs pcz WHERE pcz.idu = p.idu)")
    # ── M55-D stage 6 : SIGNAUX DE VIE (liste validée Vic phase 2) — événements SOURCÉS, jamais
    # des jugements : filtrables SANS analyse. Composition = OU entre signaux du groupe, ET avec
    # le reste des filtres. Les 3 lourds (permis_actif/friche/assemblage_pm) lisent la table
    # PRÉ-CALCULÉE parcel_signaux_vie (labuse build-signaux-vie) — jamais de jointure lourde ici.
    if signaux:
        _SIG_SQL = {
            # toute procédure collective connue (arbitrage Vic : 658 — le « i » précise en cours ou récente)
            "procedure": ("EXISTS (SELECT 1 FROM parcelle_personne_morale pms "
                          "JOIN bodacc_procedures bps ON bps.siren = pms.siren WHERE pms.idu = p.idu)"),
            "permis_actif": ("EXISTS (SELECT 1 FROM parcel_signaux_vie sv1 "
                             "WHERE sv1.idu = p.idu AND sv1.signal = 'permis_actif')"),
            "permis_caduc": "EXISTS (SELECT 1 FROM pc_caducs pcv WHERE pcv.idu = p.idu)",
            "defisc": ("EXISTS (SELECT 1 FROM defisc_fenetres dfv "
                       "WHERE dfv.idu = p.idu AND dfv.fenetre_active)"),
            # terrain quasi nu (emprise < 5 %, même seuil que etat_sol=nu) détenu par une société
            # PRIVÉE (groupe MAJIC 0 — arbitrage Vic : pas les communes/État/HLM)
            "nu_pm": ("EXISTS (SELECT 1 FROM parcel_residuel rnu JOIN parcelle_personne_morale pmn "
                      "ON pmn.idu = p.idu AND pmn.groupe = 0 "
                      "WHERE rnu.parcel_id = p.id AND rnu.taux_emprise_pct < 5)"),
            # M55-G point 11 (décision Vic) : signal LARGE — parcelle détenue par une société
            # PRIVÉE (groupe MAJIC 0, même arbitrage que nu_pm), nu ET bâti confondus.
            # Volumétrie mesurée 12/08/2026 : 33 622 île / 7 460 servables (< plafond 100k).
            "pm_privee": ("EXISTS (SELECT 1 FROM parcelle_personne_morale pmt "
                          "WHERE pmt.idu = p.idu AND pmt.groupe = 0)"),
            "friche": ("EXISTS (SELECT 1 FROM parcel_signaux_vie sv2 "
                       "WHERE sv2.idu = p.idu AND sv2.signal = 'friche')"),
            # cession de fonds < 24 mois (arbitrage Vic)
            "cession": ("EXISTS (SELECT 1 FROM parcelle_personne_morale pmc "
                        "JOIN bodacc_annonces_owner bac ON bac.siren = pmc.siren "
                        "AND bac.famille = 'vente_cession' "
                        "AND bac.date_annonce >= now() - interval '24 months' "
                        "WHERE pmc.idu = p.idu)"),
            "assemblage": ("EXISTS (SELECT 1 FROM parcel_signaux_vie sv3 "
                           "WHERE sv3.idu = p.idu AND sv3.signal = 'assemblage_pm')"),
        }
        picked = [_SIG_SQL[s] for s in
                  (x.strip() for x in signaux.split(",")) if s in _SIG_SQL]
        if picked:
            conds.append("(" + " OR ".join(picked) + ")")
    # ── Nuit N1 : filtre « marge estimée » — parcelles dont la marge € estimable ≥ seuil.
    if marge_min is not None:
        conds.append("EXISTS (SELECT 1 FROM score_e se0 WHERE se0.idu = p.idu"
                     " AND se0.estimable AND se0.marge_estimee >= :f_marge)")
        params["f_marge"] = marge_min
    # ── M45 (P2a) — barre niveau 1 + tiroir « Puis-je construire ? » (facettes composables) ──
    if sdp_max is not None:   # SDP résiduelle plafonnée (barre niveau 1, borne haute)
        conds.append("EXISTS (SELECT 1 FROM parcel_residuel r1 WHERE r1.parcel_id = p.id"
                     " AND r1.cause IS NULL AND r1.sdp_residuelle_m2 <= :f_sdpmax)")  # M125
        params["f_sdpmax"] = sdp_max
    if constructibilite:
        # Constructibilité CALIBRÉE (le filtre différenciant) — dérivée du TIER effectif + zone,
        # PAS de la zone brute. constructible = tier vivant non déclassé ; au_conditionnelle =
        # AU fermée/statut inconnu ; fermee = zone fermée ; inconstructible = non constructible ;
        # rnu = hors PLU outillé (aucune zone au parcellaire).
        cl = [x.strip() for x in constructibilite.split(",") if x.strip()]
        sub = []
        if "constructible" in cl:
            sub.append("(s2.tier IN ('brulante','chaude','reserve_fonciere','a_creuser') AND NOT " + _ETAGE0_SQL + ")")
        if "au_conditionnelle" in cl:
            sub.append("s2.tier IN ('declasse_au_fermee','declasse_au_statut_inconnu')")
        if "fermee" in cl:
            sub.append("s2.tier = 'declasse_zone_fermee'")
        if "inconstructible" in cl:
            sub.append("s2.tier = 'declasse_non_constructible'")
        if "rnu" in cl:
            sub.append("NOT EXISTS (SELECT 1 FROM parcel_zone_plu zr WHERE zr.idu = p.idu)")
        if sub:
            conds.append("(" + " OR ".join(sub) + ")")
    if etat_sol:
        # M101 A2 (arbitrage Vic) : DEUX entrées seulement — « Terrain nu » / « Terrain bâti ».
        # Les tiers internes (saturé/révélé) sortent de l'interface de filtrage : c'est une
        # information de FIABILITÉ (désaccord BD TOPO/CoSIA), servie en fiche via le motif,
        # jamais un filtre. PARTITION EXACTE sur UN critère (emprise bâtie, seuil 5 % existant) :
        # nu = pas d'emprise ≥ 5 % connue ; bâti = emprise ≥ 5 % — disjoints, somme = parc
        # filtrable (contrôle chiffré Phase C). Clés legacy (bati_marginal/sature/revele des
        # URL/API antérieures) pliées sur 'bati' — jamais un no-op silencieux.
        cl = {x.strip() for x in etat_sol.split(",") if x.strip()}
        if cl & {"bati_marginal", "bati_sature", "bati_revele"}:
            cl = (cl - {"bati_marginal", "bati_sature", "bati_revele"}) | {"bati"}
        sub = []
        if "nu" in cl:
            sub.append("NOT EXISTS (SELECT 1 FROM parcel_residuel rs WHERE rs.parcel_id = p.id"
                       " AND COALESCE(rs.taux_emprise_pct,0) >= 5)")
        if "bati" in cl:
            sub.append("EXISTS (SELECT 1 FROM parcel_residuel rs WHERE rs.parcel_id = p.id"
                       " AND COALESCE(rs.taux_emprise_pct,0) >= 5)")
        if sub:
            conds.append("(" + " OR ".join(sub) + ")")
    if capacite_min is not None:
        # Capacité logements ESTIMÉE ≥ N — dérivée de la SDP résiduelle (≈ 70 m² SDP / logement).
        # Étiquette Estimé portée par le front. Le seuil SDP est le point de calcul unique.
        conds.append("EXISTS (SELECT 1 FROM parcel_residuel rc WHERE rc.parcel_id = p.id"
                     " AND rc.cause IS NULL AND rc.sdp_residuelle_m2 >= :f_capa)")  # M125
        params["f_capa"] = capacite_min * SDP_PAR_LOGEMENT_M2
    if zone_plu:   # zone PLU EXACTE (tiroir droit).
        # M99 : le critère normalisé vit dans la TABLE (zone_filtre, écrit par
        # build_parcel_zone_plu + ensure_zone_filtre). M99-B : le PLIAGE du paramètre se fait
        # en PG AUSSI — str.upper() Python monte les accents (NDé→NDÉ) quand upper() PG
        # (locale C) ne les touche pas : la colonne porte « NDé » (Cilaos, 10 parcelles,
        # mesuré), le pliage Python renvoyait 0 silencieux sur un clic du menu. Même fonction
        # des deux côtés = même clé, toujours.
        conds.append("EXISTS (SELECT 1 FROM parcel_zone_plu zx WHERE zx.idu = p.idu"
                     " AND zx.zone_filtre = ANY(SELECT upper(v) FROM unnest(CAST(:f_zplu AS text[])) v))")
        params["f_zplu"] = [z.strip() for z in zone_plu.split(",") if z.strip()]
    # ── M45 (P2d) — tiroirs éco / mutation / propriété / veille (facettes composables) ──
    if droits_residuels:
        # M129-D P3 — facette « droits résiduels » (les DEUX états du bâti, fait M125) :
        # 'encore' = on peut encore construire (SDP résiduelle > 0, ligne calculée) ;
        # 'maximum' = construite au maximum (SDP = 0 vraie, ou cause structurée ≠ hors_plu).
        dr = [x.strip() for x in droits_residuels.split(",") if x.strip()]
        sub_dr = []
        if "encore" in dr:
            sub_dr.append("EXISTS (SELECT 1 FROM parcel_residuel dr1 WHERE dr1.parcel_id = p.id"
                          " AND dr1.cause IS NULL AND dr1.sdp_residuelle_m2 > 0)")
        if "maximum" in dr:
            sub_dr.append("EXISTS (SELECT 1 FROM parcel_residuel dr2 WHERE dr2.parcel_id = p.id"
                          " AND ((dr2.cause IS NULL AND dr2.sdp_residuelle_m2 = 0)"
                          "      OR (dr2.cause IS NOT NULL AND dr2.cause <> 'hors_plu')))")
        if sub_dr:
            conds.append("(" + " OR ".join(sub_dr) + ")")
    if sous_densite:   # éco/risques : bâti en sous-densité (parcel_residuel)
        conds.append("EXISTS (SELECT 1 FROM parcel_residuel rd WHERE rd.parcel_id = p.id AND rd.sous_densite)")
    if mult_min is not None:   # mutation : probabilité relative ×N (mult_base du scoring v2)
        conds.append("s2.mult_base >= :f_mult")
        params["f_mult"] = mult_min
    if rang_max is not None:   # mutation : têtes de liste (rang P ≤ N, cohérent Q3-M36)
        conds.append("s2.rang IS NOT NULL AND s2.rang <= :f_rang")
        params["f_rang"] = rang_max
    if renouvellement:   # mutation : segment Renouvellement (run-scopé, vérifié live sur le run servi)
        conds.append("EXISTS (SELECT 1 FROM parcel_renouvellement rn WHERE rn.idu = p.idu AND rn.run_label = :runf)")
    if division_or:   # mutation : segment Division en or (O12)
        conds.append("EXISTS (SELECT 1 FROM division_or_candidates dor WHERE dor.idu = p.idu)")
    if proprietaire_type:
        # propriété : PM identifiée (SIREN) / bailleur (Office HLM ou SEM) / PP non déterminable (absence).
        pt = [x.strip() for x in proprietaire_type.split(",") if x.strip()]
        sub = []
        if "pm" in pt:
            sub.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pmx WHERE pmx.idu = p.idu)")
        if "bailleur" in pt:
            sub.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pmb WHERE pmb.idu = p.idu"
                       " AND (pmb.groupe_label ILIKE '%HLM%' OR pmb.groupe_label ILIKE '%conomie mixte%'))")
        if "pp" in pt:
            sub.append("NOT EXISTS (SELECT 1 FROM parcelle_personne_morale pmp WHERE pmp.idu = p.idu)")
        if "public" in pt:
            # M129-D P3 (dalle : le public négociable est VISIBLE) — groupes DGFiP 1-4/9
            # (État/Région/Département/Commune/établissements publics), la classification
            # de proprietaire_type.py servie en facette.
            sub.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pmu WHERE pmu.idu = p.idu"
                       " AND pmu.groupe IN (1,2,3,4,9))")
        if sub:
            conds.append("(" + " OR ".join(sub) + ")")
    if etat_societe:
        # propriété : état PUBLIC de la société (M43, factuel) — cessée / radiée / procédure collective.
        es = [x.strip() for x in etat_societe.split(",") if x.strip()]
        sub = []
        if "cessee" in es:
            sub.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pc JOIN owner_enrichment oe ON oe.siren = pc.siren"
                       " WHERE pc.idu = p.idu AND oe.payload->>'etat_administratif' = 'C')")
        if "radiee" in es:
            sub.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pr JOIN bodacc_annonces_owner br ON br.siren = pr.siren"
                       " WHERE pr.idu = p.idu AND br.famille = 'radiation')")
        if "procedure" in es:
            sub.append("EXISTS (SELECT 1 FROM parcelle_personne_morale pp2 JOIN bodacc_annonces_owner bp ON bp.siren = pp2.siren"
                       " WHERE pp2.idu = p.idu AND bp.famille = 'pcl')")
        if sub:
            conds.append("(" + " OR ".join(sub) + ")")
    if copro:   # propriété : copropriété RNIC (avec / sans) — s2.copro
        cp = [x.strip() for x in copro.split(",") if x.strip()]
        if "avec" in cp and "sans" not in cp:
            conds.append("COALESCE(s2.copro, false)")
        elif "sans" in cp and "avec" not in cp:
            conds.append("NOT COALESCE(s2.copro, false)")
    if npnru:   # veille : proximité NPNRU/QPV — commune portant un quartier ANRU (granularité commune, dite).
        conds.append("EXISTS (SELECT 1 FROM anru_quartiers aq WHERE aq.commune = p.commune)")
    if adresse_absente:   # veille : adresse BAN absente (dite « Absente (BAN) »)
        conds.append("NOT EXISTS (SELECT 1 FROM adresse_parcelles ap0 WHERE ap0.idu = p.idu)")
    # ── M45-B (Lot 1) — tiroir ÉCONOMIE (câblage sur données existantes ; étiquettes Sourcé/Estimé) ──
    if budget_max is not None:
        # « Mon budget » : prix d'achat max admissible (charge foncière SUPPORTABLE, M22-A) ≤ budget.
        # score_e.charge_supportable = bilan à rebours (Estimé). Rend le preset « Mon budget » réel.
        conds.append("EXISTS (SELECT 1 FROM score_e sb WHERE sb.idu = p.idu AND sb.estimable"
                     " AND sb.charge_supportable <= :f_budget)")
        params["f_budget"] = budget_max
    if charge_min is not None:   # charge foncière supportable — borne basse (tranches)
        conds.append("EXISTS (SELECT 1 FROM score_e sc1 WHERE sc1.idu = p.idu AND sc1.estimable"
                     " AND sc1.charge_supportable >= :f_chmin)")
        params["f_chmin"] = charge_min
    if charge_max is not None:
        conds.append("EXISTS (SELECT 1 FROM score_e sc2 WHERE sc2.idu = p.idu AND sc2.estimable"
                     " AND sc2.charge_supportable <= :f_chmax)")
        params["f_chmax"] = charge_max
    if prix_marche_min is not None:   # prix marché DVF (€/m² terrain, dernière mutation de LA parcelle)
        conds.append("EXISTS (SELECT 1 FROM v_parcel_dvf_last dl1 WHERE dl1.idu = p.idu"
                     " AND dl1.prix_m2_terrain >= :f_pmmin)")
        params["f_pmmin"] = prix_marche_min
    if prix_marche_max is not None:
        conds.append("EXISTS (SELECT 1 FROM v_parcel_dvf_last dl2 WHERE dl2.idu = p.idu"
                     " AND dl2.prix_m2_terrain <= :f_pmmax)")
        params["f_pmmax"] = prix_marche_max
    if marche_fiable:
        # M103 P1 (défaut M100 n°1) : « fiable » = le seuil de la DOCTRINE, lu du profil
        # secteur_dossier (config/dvf_profils.yaml, n≥8 — sous n≈8 la médiane oscille ±44 %,
        # mesuré MANDAT_DVF). L'ancien 3 local étiquetait 29 228 parcelles « fiables » sur un
        # échantillon que notre propre mesure déclare instable. Un critère, un endroit.
        from ..marche_service import DVF_SECTEUR_DOSSIER, profil_meta
        conds.append("EXISTS (SELECT 1 FROM dvf_secteur_medianes dm WHERE dm.secteur = left(p.idu, 10)"
                     " AND dm.n_ventes >= :f_marche_seuil)")
        params["f_marche_seuil"] = int(profil_meta(DVF_SECTEUR_DOSSIER).get("seuil_effectif") or 8)
    if ca_min is not None:
        # bilan CA indicatif : prix de sortie neuf sectoriel × SDP résiduelle (Estimé, hors coûts).
        conds.append("EXISTS (SELECT 1 FROM parcel_residuel rca JOIN dvf_prix_sortie_neuf sn"
                     " ON sn.cle = left(p.idu, 10) WHERE rca.parcel_id = p.id AND rca.cause IS NULL"  # M125
                     " AND rca.sdp_residuelle_m2 * sn.prix_m2_neuf >= :f_camin)")
        params["f_camin"] = ca_min
    if mode_b_rentable:
        # Mode B rentable AU PARAMÈTRE COURANT (curseur session : travaux/loyer/rendement). Même
        # forme que la fiche (M44) : achat_max = loyer_annuel / rendement − travaux ; rentable si
        # achat_max ≥ prix probable du foncier. SDP ≈ surface exploitable (Estimé). Défauts sûrs.
        conds.append(
            "EXISTS (SELECT 1 FROM parcel_residuel rmb JOIN score_e smb ON smb.idu = p.idu"
            " WHERE rmb.parcel_id = p.id AND smb.estimable AND rmb.sdp_residuelle_m2 > 0"
            " AND (rmb.sdp_residuelle_m2 * :f_loyer * 12.0 / (:f_rend / 100.0)"
            "      - rmb.sdp_residuelle_m2 * :f_travaux) >= smb.prix_probable)")
        params["f_loyer"] = modeb_loyer_m2 if modeb_loyer_m2 is not None else 12.21
        params["f_rend"] = modeb_rendement_pct if modeb_rendement_pct is not None else 6.0
        params["f_travaux"] = modeb_travaux_m2 if modeb_travaux_m2 is not None else 1200.0
    return (" AND " + " AND ".join(conds)) if conds else "", params


@dataclass
class FiltreCriteres:
    """M45 (P1) — critères composables du filtrage unifié. UN SEUL point d'entrée des filtres :
    les endpoints s'y adossent, et une nouvelle facette (P2) s'ajoute ICI + dans `_q_v2_where`,
    puis coule partout. Les champs deviennent des query-params (FastAPI `Depends`)."""
    source: str | None = None
    commune: str | None = None
    score_min: int | None = None
    surface_min: int | None = None
    surface_max: int | None = None
    sdp_min: int | None = None
    evenement: bool = False
    flags: str | None = None
    communes: str | None = None
    flags_exclus: str | None = None
    tiers: str | None = None
    hors_copro: bool = False
    veille: bool = False
    personne_morale: bool = False
    zonage: str | None = None
    defisc_active: bool = False
    pc_caduc: bool = False
    marge_min: int | None = None
    # M45 (P2a) — barre niveau 1 + tiroir « Puis-je construire ? »
    sdp_max: int | None = None
    constructibilite: str | None = None
    etat_sol: str | None = None
    capacite_min: int | None = None
    zone_plu: str | None = None
    # M45 (P2d) — tiroirs éco / mutation / propriété / veille
    sous_densite: bool = False
    mult_min: float | None = None
    rang_max: int | None = None
    renouvellement: bool = False
    division_or: bool = False
    proprietaire_type: str | None = None
    droits_residuels: str | None = None   # M129-D P3 : 'encore' / 'maximum' (fait M125)
    etat_societe: str | None = None
    copro: str | None = None
    npnru: bool = False
    adresse_absente: bool = False
    # M45-B (Lot 1+2) — tiroir Économie + curseur mode B (paramètres de session)
    budget_max: int | None = None
    charge_min: int | None = None
    charge_max: int | None = None
    prix_marche_min: int | None = None
    prix_marche_max: int | None = None
    marche_fiable: bool = False
    ca_min: int | None = None
    mode_b_rentable: bool = False
    modeb_travaux_m2: float | None = None
    modeb_loyer_m2: float | None = None
    modeb_rendement_pct: float | None = None
    # M55-D stage 6 — SIGNAUX DE VIE (CSV parmi : procedure, permis_actif, permis_caduc,
    # defisc, nu_pm, friche, cession, assemblage). OU dans le groupe, ET avec le reste.
    signaux: str | None = None

    def where(self) -> tuple[str, dict]:
        return _q_v2_where(self.source, self.score_min, self.surface_min, self.surface_max,
                           self.sdp_min, self.evenement, self.flags, self.communes, self.flags_exclus,
                           self.tiers, self.hors_copro, self.veille, self.personne_morale,
                           self.zonage, self.defisc_active, self.pc_caduc, self.marge_min,
                           self.sdp_max, self.constructibilite, self.etat_sol, self.capacite_min,
                           self.zone_plu, self.sous_densite, self.mult_min, self.rang_max,
                           self.renouvellement, self.division_or, self.proprietaire_type,
                           self.etat_societe, self.copro, self.npnru, self.adresse_absente,
                           self.budget_max, self.charge_min, self.charge_max, self.prix_marche_min,
                           self.prix_marche_max, self.marche_fiable, self.ca_min, self.mode_b_rentable,
                           self.modeb_travaux_m2, self.modeb_loyer_m2, self.modeb_rendement_pct,
                           signaux=self.signaux,
                           droits_residuels=self.droits_residuels)

    def cache_key(self) -> tuple:
        return ("filtre", self.source, self.commune, self.score_min, self.surface_min,
                self.surface_max, self.sdp_min, self.evenement, self.flags, self.communes,
                self.flags_exclus, self.tiers, self.hors_copro, self.veille,
                self.personne_morale, self.zonage, self.defisc_active, self.pc_caduc, self.marge_min,
                self.sdp_max, self.constructibilite, self.etat_sol, self.capacite_min, self.zone_plu,
                self.sous_densite, self.mult_min, self.rang_max, self.renouvellement, self.division_or,
                self.proprietaire_type, self.etat_societe, self.copro, self.npnru, self.adresse_absente,
                self.budget_max, self.charge_min, self.charge_max, self.prix_marche_min,
                self.prix_marche_max, self.marche_fiable, self.ca_min, self.mode_b_rentable,
                self.modeb_travaux_m2, self.modeb_loyer_m2, self.modeb_rendement_pct,
                self.signaux, self.droits_residuels)


@app.get("/parcels")
def list_parcels(commune: str | None = None,
                 limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                 source: str | None = None,
                 score_min: int | None = None,
                 surface_min: int | None = None, surface_max: int | None = None,
                 sdp_min: int | None = None, evenement: bool = False,
                 flags: str | None = None, communes: str | None = None,
                 flags_exclus: str | None = None,
                 tiers: str | None = None,
                 hors_copro: bool = False, veille: bool = False,
                 personne_morale: bool = False, zonage: str | None = None,
                 defisc_active: bool = False, pc_caduc: bool = False,
                 marge_min: int | None = None,
                 sort: str | None = Query(None, pattern="^(v|rang|mult|surface|commune)$"),
                 db: Session = Depends(get_db)) -> list[dict]:
    """Liste PAGINÉE (commune OU île entière), pilotée par le scoring v2.

    M5.1 — le scoring v2 PILOTE : périmètre par défaut = univers v2 HORS étage 0 du run
    servi ; tri par défaut = rang P. Filtres v2 : `tiers`, `hors_copro`, `veille`, etc.

    M45 (P1) : `source` (run q_v*) est REQUIS. L'ancien repli sans `source` lisait la table
    morte `parcel_evaluations` en IGNORANT tous les filtres (piège dormant) — il renvoie
    désormais un 404 explicite au lieu de mentir en silence. Params `statuts`/`v_signal`/
    `brulantes` retirés (sources mortes)."""
    if not (source and source.startswith("q_v")):
        raise HTTPException(status_code=404,
                            detail="source requise : préciser ?source=<run q_v*> (run servi)")
    extra, extra_params = _q_v2_where(source, score_min, surface_min, surface_max,
                                      sdp_min, evenement, flags, communes, flags_exclus,
                                      tiers, hors_copro, veille,
                                      personne_morale, zonage, defisc_active, pc_caduc, marge_min)
    return _q_v2_list(db, commune, limit, offset, run_label=source,
                      extra_where=extra, extra_params=extra_params, sort=sort)


@app.get("/parcels/export.csv")
def export_parcels_csv(c: FiltreCriteres = Depends(),
                       sort: str | None = Query(None, pattern="^(v|rang|mult|surface|surface_asc|commune)$"),
                       limit: int = Query(1000, ge=1, le=5000),
                       db: Session = Depends(get_db)) -> Response:
    """Export CSV de la liste — MÊMES facettes que le compteur et la liste (M46 Lot D : routé
    sur `FiltreCriteres`, plus jamais un export qui ignore les filtres actifs). Tier v2 EN
    PREMIER (M5.1), signaux propriétaire en fin de ligne. M6 2a : utf-8-sig (BOM Excel) +
    séparateur « ; » + adresse postale BAN (1re colonne = idu).
    ⚠ Doit rester déclarée AVANT /parcels/{idu} (ordre de résolution des routes)."""
    import csv as _csv
    import io as _io

    from .export_commun import adresses_ban

    source = c.source or Q_A_RUN_LABEL
    c.source = source
    extra, extra_params = c.where()
    items = _q_v2_list(db, c.commune, limit, 0, run_label=source,
                       extra_where=extra, extra_params=extra_params, sort=sort)
    tops = {r[0]: r[1] for r in db.execute(text(
        "SELECT parcelle_id, (SELECT string_agg(s->>'label', ' | ') FROM ("
        "  SELECT s FROM jsonb_array_elements(signals) s "
        "  ORDER BY (s->>'points')::int DESC LIMIT 3) t(s)) "
        "FROM parcel_v_score WHERE parcelle_id = ANY(:idus)"),
        {"idus": [it["idu"] for it in items]}).all()}
    adrs = adresses_ban(db, [it["idu"] for it in items])
    # M9 lot 1 — ICD (indice de confiance données) du run servi. Colonne annexe, jointe ici
    # (comme top_signaux) pour ne pas alourdir _q_v2_list ; CLOISONNÉE du score P.
    from ..scoring import icd as _icd
    v2run = _score_v2_run_id(db)
    icd_map = {r[0]: r[1] for r in db.execute(text(
        "SELECT parcelle_id, icd FROM parcel_p_score_v2 "
        "WHERE run_id = :r AND parcelle_id = ANY(:idus)"),
        {"r": v2run, "idus": [it["idu"] for it in items]}).all()} if v2run else {}
    buf = _io.StringIO()
    w = _csv.writer(buf, delimiter=";")          # Excel FR : point-virgule (standard maison)
    # M129-B : statut_matrice/q_score/a_score retirés (matrice morte) — le statut servi est
    # celui de la CASCADE (status), la présentation est le tier v2.
    w.writerow(["idu", "commune", "adresse_ban", "code_postal", "ville",
                "surface_m2", "tier_v2", "rang_v2", "mult_v2", "copro",
                "veille_succession", "statut_cascade",
                "completeness", "icd", "confiance_donnees",
                "proprio", "v_score", "v_band", "top_signaux"])
    for it in items:
        a = adrs.get(it["idu"]) or {}
        icd_val = icd_map.get(it["idu"])
        w.writerow([it["idu"], it["commune"],
                    a.get("adresse") or "", a.get("code_postal") or "", a.get("ville") or "",
                    it["surface_m2"],
                    ("ecartee" if it["etage0"] else it["tier_v2"]) or "",
                    it["rang_v2"] if it["rang_v2"] is not None else "",
                    f"{it['mult_v2']:.1f}" if it.get("mult_v2") is not None else "",
                    "oui" if it.get("copro_v2") else "",
                    "oui" if it.get("veille") else "",
                    it["status"], it["completeness_score"],
                    icd_val if icd_val is not None else "",
                    _icd.libelle_bande(icd_val) if icd_val is not None else "",
                    it["proprio"] or "",
                    it["v_score"] if it["v_score"] is not None else "",
                    it["v_band"] or "", tops.get(it["idu"]) or ""])
    return Response(buf.getvalue().encode("utf-8-sig"),   # BOM : accents corrects dans Excel
                    media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="labuse_parcelles.csv"',
                             "X-Rows": str(len(items))})


def _communes_data(db: Session, source: str) -> list[dict]:
    """Compteurs par commune (tiers du run servi) — POINT DE CALCUL UNIQUE, mémoïsé 5 min.
    Consommé par /communes (sélecteur, marqueurs carte) ET par la fiche commune (M36 Lot D) :
    le même chiffre partout, jamais figé, jamais la matrice historique.

    M35 Lot D : « chaudes » = brûlantes + chaudes du run servi (même convention que /stats) ;
    `evaluees` = parcelles présentes au run servi."""
    def _compute() -> list[dict]:
        rows = db.execute(text(
            """
            SELECT p.commune,
                   substring(min(p.idu) from 1 for 5)                       AS insee,
                   count(*)                                                 AS parcelles,
                   count(*) FILTER (WHERE s.tier IN ('brulante', 'chaude')) AS chaudes,
                   count(DISTINCT pm.siren) FILTER (WHERE s.tier IN ('brulante', 'chaude')
                         AND pm.siren IS NOT NULL)                          AS dossiers,
                   count(*) FILTER (WHERE s.tier IN ('brulante', 'chaude')
                         AND pm.siren IS NULL)                              AS chaudes_sans_identite,
                   count(s.parcelle_id)                                     AS evaluees,
                   ST_XMin(ST_Extent(p.geom)) AS x1, ST_YMin(ST_Extent(p.geom)) AS y1,
                   ST_XMax(ST_Extent(p.geom)) AS x2, ST_YMax(ST_Extent(p.geom)) AS y2
            FROM parcels p
            LEFT JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu AND s.run_id = :run
            LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
            GROUP BY p.commune ORDER BY 4 DESC, 3 DESC
            """), {"run": source}).mappings().all()
        # cas documenté (pré-vol île) : Saint-Philippe est au RNU — pas de PLU opposable,
        # capacité non calculable ; le front affiche ce bandeau plutôt qu'un score creux muet
        notes = {"Saint-Philippe": "RNU — pas de PLU opposable : capacité non calculable, "
                                   "signaux qualité/accessibilité seuls"}
        return [{
            "commune": r["commune"], "insee": r["insee"], "parcelles": int(r["parcelles"]),
            "chaudes": int(r["chaudes"] or 0), "dossiers": int(r["dossiers"] or 0),
            "chaudes_sans_identite": int(r["chaudes_sans_identite"] or 0),
            "evaluees": int(r["evaluees"] or 0),
            "bbox": [r["x1"], r["y1"], r["x2"], r["y2"]],
            "note": notes.get(r["commune"]),
        } for r in rows]
    return _mem_cached(("communes", source), 300.0, _compute)


@app.get("/communes")
def list_communes(source: str = Q_A_RUN_LABEL, db: Session = Depends(get_db)) -> list[dict]:
    """Les 24 communes pour le SÉLECTEUR : nom, INSEE, volumétrie, chaudes, bbox (recadrage
    carte). Trié par nombre de chaudes décroissant. Source unique : _communes_data."""
    return _communes_data(db, source)


def _foncier_commune(db: Session, commune: str) -> dict:
    """M83 C1 — LE FONCIER DE LA COMMUNE (le produit). Métriques CALCULÉES réutilisées des points de
    calcul EXISTANTS (M79 : `ligne2_terrain_zone` pour le prix terrain nu, `ligne6_offre_engagee` pour
    les permis 12 mois) — aucun recalcul. Les comptes (parcelles, surface, zonage, évaluées, sans-zonage,
    mutations 12 m) sont des AGRÉGATS DIRECTS sur les tables (pas la duplication d'une métrique calculée).
    « UNKNOWN » n'existe pas comme statut : c'est l'absence de zonage publié au GPU (→ écartée)."""
    from ..faisabilite.marche_commune import ligne2_terrain_zone, ligne6_offre_engagee

    def scal(sql: str):
        return db.execute(text(sql), {"c": commune, "r": Q_A_RUN_LABEL}).scalar()

    n_parcelles = scal("SELECT count(*) FROM parcels WHERE commune = :c") or 0
    surface_ha = db.execute(text(
        "SELECT round((sum(surface_m2) / 10000.0)::numeric)::int FROM parcels WHERE commune = :c"),
        {"c": commune}).scalar()
    zon = {(r["fam"] or "").upper(): r["n"] for r in db.execute(text(
        "SELECT z.zone_fam AS fam, count(*) n FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu "
        "WHERE p.commune = :c AND z.zone_fam IS NOT NULL GROUP BY 1"), {"c": commune}).mappings()}
    au = sum(v for k, v in zon.items() if k.startswith("AU"))
    a = sum(v for k, v in zon.items() if k.startswith("A") and not k.startswith("AU"))
    u = sum(v for k, v in zon.items() if k.startswith("U"))
    nz = sum(v for k, v in zon.items() if k.startswith("N"))
    total_zone = u + au + a + nz
    evaluees = scal("SELECT count(*) FROM parcels p JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu "
                    "WHERE p.commune = :c AND s.run_id = :r") or 0
    sans_zonage = scal("SELECT count(*) FROM parcels p WHERE p.commune = :c AND NOT EXISTS "
                       "(SELECT 1 FROM parcel_zone_plu z WHERE z.idu = p.idu)") or 0
    # 12 DERNIERS MOIS DE DONNÉES de la commune (pas relatif à now() : DVF est publié avec retard,
    # une fenêtre calendaire donnerait un volume partiel trompeur).
    # MANDAT_DVF-B — SIGNAL d'agrégat COMMUNE (un COMPTE de mutations, PAS un prix de parcelle) : reste
    # HORS marche_service et hors profils (ne pas mélanger deux grandeurs). Jamais lu comme un €/m².
    mutations_12m = db.execute(text(
        "SELECT count(*) FROM dvf_mutations WHERE commune = :c AND date_mutation > "
        "(SELECT max(date_mutation) FROM dvf_mutations WHERE commune = :c) - interval '12 months'"),
        {"c": commune}).scalar() or 0
    terrain = ligne2_terrain_zone(db, commune)     # point de calcul M79 (réutilisé, pas recréé)
    offre = ligne6_offre_engagee(db, commune)      # permis 12 mois (Sitadel), réutilisé
    return {
        "n_parcelles": int(n_parcelles),
        "surface_ha": int(surface_ha) if surface_ha is not None else None,
        "repartition_zonage": ({"U": u, "AU": au, "A": a, "N": nz, "total": total_zone} if total_zone else None),
        "classement": {"evaluees": int(evaluees), "sans_zonage": int(sans_zonage),
                       "raison_sans_zonage": "zonage non publié au GPU"},
        "prix_terrain_nu": {"par_zone": (terrain.get("valeurs") or {}).get("par_zone"),
                            "calculable": terrain.get("calculable"), "motif": terrain.get("motif"),
                            "seuil_n": 10, "etiquette": terrain.get("etiquette")},
        "mutations_12m": int(mutations_12m),
        "permis_12m": {"n": (offre.get("valeurs") or {}).get("permis_12m") or 0,
                       "reserve": "accordés seulement (les refus et abandons ne sont pas publiés)"},
    }


@app.get("/communes/{commune}/contexte")
def commune_contexte(commune: str, db: Session = Depends(get_db)) -> dict:
    """VOLET CONTEXTE COMMUNE (mandat promotrice) — SRU + ANRU + PLH + marché logement INSEE
    + rappel QPV. Donnée de CONTEXTE sourcée (échelle commune), hors scoring. Chaque bloc
    porte sa source + millésime ; introuvable = null (le front affiche « non disponible »
    sourcé, jamais un zéro menteur)."""
    def _one(sql: str, p: dict) -> dict | None:
        r = db.execute(text(sql), p).mappings().first()
        return dict(r) if r else None

    sru = _one("SELECT * FROM commune_contexte_sru WHERE commune = :c", {"c": commune})
    insee_log = _one("SELECT * FROM commune_insee_logement WHERE commune = :c", {"c": commune})
    anru = [dict(r) for r in db.execute(text(
        "SELECT nom, interet, code_qpv, source_nom, source_url FROM anru_quartiers"
        " WHERE commune = :c ORDER BY nom"), {"c": commune}).mappings().all()]
    qpv = [dict(r) for r in db.execute(text(
        "SELECT name AS nom, attrs->>'code_qp' AS code FROM spatial_layers"
        " WHERE kind = 'qpv' AND commune = :c ORDER BY name"), {"c": commune}).mappings().all()]
    # rattachement EPCI (référentiel BANATIC, config/epci_974.yaml) + PLH
    epci_cfg = config.load_yaml_config("epci_974")["epci"]
    epci = next((k for k, v in epci_cfg.items() if commune in v["communes"]), None)
    plh = _one("SELECT * FROM plh_epci WHERE epci = :e", {"e": epci}) if epci else None
    for d in (sru, insee_log, plh):
        if d:
            d.pop("importe_le", None)
    # M36 Lot D : le compteur du tier haut EN DUR sur la fiche commune — même point de
    # calcul (mémoïsé) que /communes : tiers du run servi, jamais figé, étiquette vraie.
    _cd = next((c for c in _communes_data(db, Q_A_RUN_LABEL) if c["commune"] == commune), None)
    classement = ({
        "tiers_hauts": _cd["chaudes"], "dossiers": _cd["dossiers"],
        "libelle": (f"{_cd['chaudes']} parcelles brûlantes ou chaudes au classement servi"
                    if _cd["chaudes"] != 1 else
                    "1 parcelle brûlante ou chaude au classement servi"),
        "source": "Classement servi LABUSE (tiers brûlante + chaude) — recalculé à chaque "
                  "bascule, jamais figé",
    } if _cd else None)
    # M55-C point 1 (arbitrage Vic) : bandeau RNU générique — toute commune SANS document local
    # (source de vérité config/rnu_communes.yaml via labuse.rnu). Wording DOCTRINAL réutilisé.
    from .. import rnu as rnu_mod
    _insee_c = _cd.get("insee") if _cd else None
    rnu = ({"libelle": rnu_mod.LIBELLE_RNU, "detail": rnu_mod.DETAIL_RNU}
           if rnu_mod.is_rnu_insee(_insee_c) else None)
    return {"commune": commune, "epci": epci,
            "epci_nom": epci_cfg[epci]["nom"] if epci else None,
            "rnu": rnu,
            "foncier": _foncier_commune(db, commune),   # M83 C1 — le foncier de la commune, EN TÊTE
            "classement": classement,
            "qualite": _qualite_commune(_cd.get("insee") if _cd else None),   # M52 L4 — encart qualité commune DITE
            "sru": sru, "anru": anru, "qpv": qpv, "plh": plh, "marche": insee_log,
            "notes": ["ZUS et ZFU sont des zonages abrogés (réforme 2014), devenus QPV — déjà "
                      "couverts par la couche QPV. Volet fiscal ZFU-Territoires Entrepreneurs : "
                      "pas de source spécifique à La Réunion identifiée à ce jour.",
                      "Données de CONTEXTE : aucune n'entre dans le scoring."]}


@app.get("/parcels/at")
def parcel_at(lon: float, lat: float, db: Session = Depends(get_db)) -> dict:
    """Résolution point → parcelle (C7, décision produit Vic : clic UNIVERSEL — n'importe
    quelle parcelle de la trame cadastrale ouvre sa fiche, promue ou écartée)."""
    row = db.execute(text(
        """SELECT p.idu FROM parcels p
           WHERE ST_Contains(p.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
           LIMIT 1"""), {"lon": lon, "lat": lat}).first()
    return {"idu": row[0] if row else None}




@app.get("/adresses/autocomplete")
def adresses_autocomplete(q: str = Query(..., min_length=3),
                          limit: int = Query(6, ge=1, le=12),
                          db: Session = Depends(get_db)) -> dict:
    """M13-B1 — autocomplétion d'adresse INTERNE, adossée à la table `adresses` (BAN rattachée
    aux parcelles, ~99,99 %). Plus fiable que l'API BAN externe (pas d'appel navigateur sortant)
    et alignée sur notre trame : chaque suggestion porte déjà son `idu` + ses coordonnées, donc
    la sélection atterrit directement sur la fiche sans second aller-retour de géocodage.

    Recherche insensible aux accents/casse sur « numéro voie », priorité au préfixe puis à la
    voie la plus courte. On ne renvoie que des adresses géolocalisées ET rattachées à une
    parcelle (jamais une chaîne libre)."""
    needle = q.strip()
    if len(needle) < 3:
        return {"features": []}
    # M103 P2/P6 — pliage PARTAGÉ (constants.sql_plie : casse + accents + ligatures œ/æ +
    # apostrophe typographique) — même fonction des deux côtés, même point que le patrimoine.
    from ..constants import params_pliage, sql_plie
    _col = sql_plie("coalesce(numero,'') || ' ' || voie")
    rows = db.execute(text(
        f"""
        SELECT id_ban,
               trim(coalesce(numero, '') || ' ' || voie) AS label_court,
               commune, code_postal, idu,
               ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM adresses
        WHERE idu IS NOT NULL AND geom IS NOT NULL
          AND {_col} LIKE {sql_plie("'%' || :q || '%'")}
        ORDER BY ({_col} LIKE {sql_plie(":q || '%'")}) DESC,
                 length(voie), voie, numero
        LIMIT :lim
        """),
        {"q": needle, "lim": limit, **params_pliage()}).mappings().all()
    feats = []
    for r in rows:
        label = r["label_court"]
        if r["commune"]:
            label = f"{label}, {r['commune']}"
            if r["code_postal"]:
                label = f"{label} ({r['code_postal']})"
        feats.append({
            "label": label, "lon": float(r["lon"]), "lat": float(r["lat"]),
            "idu": r["idu"], "commune": r["commune"], "postcode": r["code_postal"],
            "type": "housenumber",
        })
    return {"features": feats}


@app.get("/parcels/search")
def search_parcels(q: str = Query(..., min_length=2), commune: str | None = None,
                   source: str = Q_A_RUN_LABEL, limit: int = Query(10, ge=1, le=50),
                   db: Session = Depends(get_db)) -> list[dict]:
    """Recherche IDU/section pour l'omnibox en mode île (le client n'a plus les features en
    mémoire). Matche la fin d'IDU (section+numéro, ex. « AC0253 ») ou l'IDU complet.
    M5.1 : le tier v2 effectif accompagne chaque résultat (chip v2 en premier) et pilote
    l'ordre (brûlante → chaude → réserve → à creuser → écartée, puis rang).
    M6 2a (§1.8) : l'adresse BAN accompagne chaque résultat — jointure APRÈS le LIMIT
    (sous-requête paginée), jamais un lookup par parcelle scannée."""
    needle = q.strip().upper().replace(" ", "")
    ban_ok = _ban_ready(db)
    ban_cols = (", ban.ban_voie, ban.ban_cp, ban.ban_commune" if ban_ok
                else ", NULL AS ban_voie, NULL AS ban_cp, NULL AS ban_commune")
    ban_join = _ban_lateral("s.idu") if ban_ok else ""
    rows = db.execute(text(
        f"""
        SELECT s.idu, s.commune, s.status, s.tier_v2, s.rang_v2, s.etage0
               {ban_cols}
        FROM (
            SELECT p.idu, p.commune, d.status AS status, d.opportunity_score,  -- M129-B : matrice morte → statut cascade
                   s2.tier AS tier_v2, s2.rang AS rang_v2,
                   {_ETAGE0_SQL} AS etage0,
                   CASE WHEN {_ETAGE0_SQL} THEN 5
                        WHEN s2.tier = 'brulante' THEN 0 WHEN s2.tier = 'chaude' THEN 1
                        WHEN s2.tier = 'reserve_fonciere' THEN 2 WHEN s2.tier = 'a_creuser' THEN 3
                        ELSE 4 END AS ord
            FROM parcels p
            LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
            WHERE p.idu ILIKE :pat AND (CAST(:c AS text) IS NULL OR p.commune = :c)
            ORDER BY ord, s2.rang ASC NULLS LAST, p.idu
            LIMIT :lim
        ) s
        {ban_join}
        ORDER BY s.ord, s.rang_v2 ASC NULLS LAST, s.idu
        """), {"pat": f"%{needle}", "c": commune, "run": source, "lim": limit,
               "v2run": _score_v2_run_id(db)}).mappings().all()
    return [{"idu": r["idu"], "commune": r["commune"], "status": r["status"],
             "tier_v2": r["tier_v2"],
             "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
             "adresse": _fmt_ban(r["ban_voie"], r["ban_cp"], r["ban_commune"])} for r in rows]


@app.get("/stats/entonnoir")
def stats_entonnoir(commune: str | None = None, source: str = Q_A_RUN_LABEL,
                    db: Session = Depends(get_db)) -> dict:
    """L'ENTONNOIR PAR MOTIF (C4, revue Vic) : « LABUSE a analysé N parcelles et trié pour
    vous » — décomposition SQL-exacte des écartées par garde (matérialisée post-matrice ;
    une parcelle peut cumuler des motifs, affiché tel quel). Pédagogique ET auditable.

    M5.1 : « opportunités détectées » = brûlantes v2 + chaudes v2 (le run v2 est la
    source) ; la ventilation par tier accompagne les motifs d'écartement."""
    key = commune or "__ile__"
    rows = db.execute(text(
        "SELECT motif, n FROM entonnoir_motifs WHERE run_label = :r AND commune = :c ORDER BY ord"),
        {"r": source, "c": key}).mappings().all()
    stats_row = _q_v2_stats(db, commune, run_label=source)
    return {"commune": commune, "analysees": stats_row["total"],
            "opportunites": stats_row["opportunites"],
            "tiers": stats_row["tiers"],
            "motifs": [dict(r) for r in rows],
            "note": ("Opportunités = brûlantes v2 + chaudes v2 (scoring P×C, hors étage 0 du run "
                     "servi). Une parcelle peut cumuler plusieurs motifs (les pourcentages se "
                     "recouvrent). « Qualité insuffisante » = survivante du filtre dur mais Q<50.")}


@app.get("/stats")
def stats(commune: str | None = None, source: str | None = None,
          score_min: int | None = None,
          surface_min: int | None = None, surface_max: int | None = None,
          sdp_min: int | None = None, evenement: bool = False,
          flags: str | None = None, communes: str | None = None,
          flags_exclus: str | None = None,
          tiers: str | None = None,
          hors_copro: bool = False, veille: bool = False, legacy: bool = False,
          personne_morale: bool = False, zonage: str | None = None,
          db: Session = Depends(get_db)) -> dict:
    """Cartouches du dashboard : volumétrie + TIERS v2 effectifs — le COMPTEUR EN DIRECT.
    `legacy=1` (deprecated) ajoute la ventilation matrice historique. Mêmes paramètres de
    filtre que /parcels — compteurs SQL-exacts, mémorisés 30 s (#7).

    M45 (P1) : `source` (run q_v*) REQUISE, comme /parcels. L'ancien repli sans source lisait
    la table morte `parcel_evaluations` en ignorant les filtres → 404 explicite. Params morts
    `statuts`/`v_signal`/`brulantes` retirés."""
    if not (source and source.startswith("q_v")):
        raise HTTPException(status_code=404,
                            detail="source requise : préciser ?source=<run q_v*> (run servi)")
    extra, extra_params = _q_v2_where(source, score_min, surface_min, surface_max,
                                      sdp_min, evenement, flags, communes, flags_exclus,
                                      tiers, hors_copro, veille,
                                      personne_morale, zonage)
    key = ("stats_qv2", source, commune, score_min, surface_min, surface_max,
           sdp_min, evenement, flags, communes, flags_exclus,
           tiers, hors_copro, veille, legacy,
           personne_morale, zonage)
    return _mem_cached(key, 30.0, lambda: _q_v2_stats(
        db, commune, run_label=source, extra_where=extra, extra_params=extra_params,
        legacy=legacy))




#: M55-G suite (point 1) — plafond de la liste d'IDU servie à la carte : au-delà, un filtre
#: MapLibre « in literal » devient coûteux ; le front replie sur l'expression par critères
#: carte et le DIT (toast, règle no-silent-caps).
_FILTRE_IDUS_CAP = 20_000


@app.get("/zonage/zones")
def zonage_zones(communes: str | None = Query(None), db: Session = Depends(get_db)) -> dict:
    """M99 Phase 3 — les zones du sélecteur par famille. Familles triées par volume RÉEL,
    zones en graphie réglementaire MAJUSCULE (`zone_filtre`, le critère du filtre — un
    critère, un endroit) avec leur compte de parcelles CALCULÉ (jamais en dur : il suit les
    recalibrages PLU). Portée : l'île par défaut, les communes passées sinon — une zone à 0
    dans la portée est ABSENTE de la liste (comportement explicite : le front affiche la
    portée en tête de liste). La fiche, elle, garde `zone_lib` (graphie officielle)."""
    coms = [x.strip() for x in (communes or "").split(",") if x.strip()]
    join, where, params = "", "WHERE z.zone_filtre IS NOT NULL", {}
    if coms:
        join = "JOIN parcels p ON p.idu = z.idu"
        where += " AND p.commune = ANY(:coms)"
        params["coms"] = coms
    rows = db.execute(text(
        f"SELECT z.zone_fam AS fam, z.zone_filtre AS zone, count(*) AS n "
        f"FROM parcel_zone_plu z {join} {where} GROUP BY 1, 2"), params).mappings().all()
    fams: dict[str, dict] = {}
    for r in rows:
        f = fams.setdefault(r["fam"] or "autre", {"fam": r["fam"] or "autre", "n": 0, "zones": []})
        f["n"] += r["n"]
        f["zones"].append({"zone": r["zone"], "n": r["n"]})
    familles = sorted(fams.values(), key=lambda f: -f["n"])
    for f in familles:
        f["zones"].sort(key=lambda z: (-z["n"], z["zone"]))
    return {"portee": "commune" if coms else "ile", "communes": coms, "familles": familles}


@app.get("/filtre")
def filtre(c: FiltreCriteres = Depends(),
           limit: int = Query(20, ge=0, le=200), offset: int = Query(0, ge=0),
           sort: str | None = Query(None, pattern="^(rang|mult|surface|surface_asc|commune)$"),
           idus: int = Query(0, ge=0, le=1),
           groupes: int = Query(0, ge=0, le=1),
           db: Session = Depends(get_db)) -> dict:
    """Filtrage UNIFIÉ (M45 P1) — le « théâtre » : compteur EXACT + ventilation par tier + page
    d'aperçu en UN appel (une requête par ajustement de filtre). Critères composables via
    `FiltreCriteres` → `_q_v2_where`. Compteur mémorisé 30 s (SQL exact, index `ix_p_v2_run_rang`).
    `source` (run q_v*) REQUISE — jamais de repli sur une source morte.

    M55-G suite (point 1) : `idus=1` ajoute la liste des IDU du résultat (mêmes critères,
    plafond _FILTRE_IDUS_CAP + drapeau `idus_tronque`) — la CARTE raccorde sa palette au
    résultat exact de la liste, y compris pour les critères non exprimables en tuiles
    (signaux de vie, état du sol, constructibilité…).

    M55-H : `sort=surface_asc` (point 4, sens inverse du tri Surface) ; `groupes=1`
    (point 5, décision Vic) — la page se groupe par tier (brûlantes → … → potentiel
    épuisé), le tri choisi s'appliquant DANS chaque groupe."""
    if not (c.source and c.source.startswith("q_v")):
        raise HTTPException(status_code=404,
                            detail="source requise : préciser ?source=<run q_v*> (run servi)")
    extra, extra_params = c.where()
    stats = _mem_cached(c.cache_key(), 30.0, lambda: _q_v2_stats(
        db, c.commune, run_label=c.source, extra_where=extra, extra_params=extra_params))
    page = _q_v2_list(db, c.commune, limit, offset, run_label=c.source,
                      extra_where=extra, extra_params=extra_params, sort=sort,
                      groupes=bool(groupes)) if limit else []
    out = {
        **stats,                                     # total, tiers, opportunites, opportunites_evenement,
                                                     # dossiers_* — la LISTE et les cartouches lisent LE MÊME
                                                     # point (M45-B L3) : plus jamais un compteur et une liste
                                                     # qui divergent sur les facettes.
        "compte": stats["total"],                    # le compteur (« 3 847 → 47 »)
        "page": page, "limit": limit, "offset": offset, "sort": sort or "rang",
    }
    if idus:
        rows = db.execute(text(
            f"""
            SELECT p.idu
            FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
            LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
            WHERE d.run_label = :run AND (CAST(:c AS text) IS NULL OR p.commune = :c)
              {extra}
            LIMIT {_FILTRE_IDUS_CAP + 1}
            """), {"c": c.commune, "run": c.source, "v2run": _score_v2_run_id(db),
                   **extra_params}).scalars().all()
        tronque = len(rows) > _FILTRE_IDUS_CAP
        out["idus"] = None if tronque else list(rows)
        out["idus_tronque"] = tronque
    return out


def _owner_famille(groupe, forme, denom) -> str:
    """Famille de propriétaire (public/prive/inconnu) pour le filtre carte (1.A — DGFiP). Source
    unique : classify_dgfip. `inconnu` = parcelle absente du fichier des morales (= particulier)."""
    if groupe is None and not denom:
        return "inconnu"
    from ..proprietaire_type import classify_dgfip
    return classify_dgfip(groupe, forme, denom)["famille"]


@app.get("/map/parcels.geojson")
def parcels_geojson(commune: str | None = None, limit: int = Query(60000, ge=0, le=200000),
                    source: str = Q_A_RUN_LABEL, db: Session = Depends(get_db)) -> dict:
    """Parcelles (géométrie simplifiée 4326) + verdict SERVI, pour la carte colorée.

    M37 : DÉFAUT = run servi (`Q_A_RUN_LABEL`, lu du point de vérité unique
    `config/served_run.txt`) → toujours le scoring premium v2 (`dryrun_parcel_evaluations`),
    tier servi. Le fallback legacy `parcel_evaluations.status` (rail éteint M37) est SUPPRIMÉ —
    un seul chemin, une seule vérité. Le front envoyait déjà `?source=…` via le helper `q()`."""
    return _q_v2_geojson(db, commune, limit, run_label=source)


#: statuts de la matrice premium v2 (dryrun) — source de vérité du Socle V1.
_Q_V2_STATUTS = ("chaude", "a_surveiller", "a_creuser", "ecartee", "exclue")


def _score_v2_run_id(db: Session) -> str | None:
    """Dernier run scoring v2 (P×C) — None si la table n'existe pas ou est vide.
    Correctif M5 (verdict d'en-tête) : quand un run v2 existe, le tier v2 pilote le
    verdict affiché partout (fiche, listes, carte) ; l'étage 0 du run SERVI prime
    (`etage0`, calculé sur d.status — le pipeline v2 peut lire un autre run cascade).
    None → LEFT JOIN sur run_id NULL → colonnes NULL → repli legacy silencieux.

    ÉPINGLÉ AU LABEL (fix pré-lancement) : le run v2 servi est celui de `Q_A_RUN_LABEL`
    (source unique de vérité du run servi), PAS « le dernier run v2 par timestamp ». Un run
    v2 futur sous un autre label ne devient donc JAMAIS servi tant que Q_A_RUN_LABEL n'a pas
    été changé (= décision explicite, comme une bascule) — ferme la bombe latente du diagnostic.
    Si le label n'est pas (encore) présent en table → None → repli legacy."""
    if not db.execute(text("SELECT to_regclass('p_score_v2_runs')")).scalar():
        return None
    return db.execute(text(
        "SELECT run_id FROM p_score_v2_runs WHERE run_id = :label LIMIT 1"),
        {"label": Q_A_RUN_LABEL}).scalar()


#: cache mémoire du nombre de parcelles analysées par run (théâtre M52 L2). Le compte est GELÉ
#: à l'écriture du run (`p_score_v2_runs.n_parcelles`) — pas un COUNT(*) par fiche.
_PARC_ANALYSEES: dict[str, int | None] = {}


def _parc_analysees(db: Session, run: str | None) -> int | None:
    """Nombre de parcelles analysées du run servi (théâtre « N parcelles analysées »). Lit le
    compte GELÉ dans `p_score_v2_runs.n_parcelles` (aucun COUNT par requête). Requête EN
    begin_nested (contrat savepoint : toute requête ajoutée au build de fiche est isolée)."""
    if not run:
        return None
    if run not in _PARC_ANALYSEES:
        with db.begin_nested():
            _PARC_ANALYSEES[run] = db.execute(text(
                "SELECT n_parcelles FROM p_score_v2_runs WHERE run_id = :r"), {"r": run}).scalar()
    return _PARC_ANALYSEES[run]


def _qualite_commune(insee: str | None) -> dict | None:
    """M52 L4 — qualité PAR COMMUNE, DITE (mesure réelle gelée : `config/qualite_commune.yaml`,
    dérivé de l'audit RR fold 2025 OOS). Renvoie le RR intra-commune, l'échantillon, le drapeau
    « fragile » (<5 positifs → fréquence indicative) et une phrase honnête. `degradee` arme le
    rappel discret en fiche parcelle. PRÉSENTATION SEULE : aucun tier, aucun seuil, aucun modèle."""
    if not insee:
        return None
    try:
        cfg = config.load_yaml_config("qualite_commune")
    except FileNotFoundError:
        return None
    c = (cfg.get("communes") or {}).get(insee)
    if not c:
        return None
    rr_ile = (cfg.get("ile") or {}).get("rr_1158")
    # M52-B micro-correction (règle Lot D audit RR : JAMAIS la fausse précision) — le RR île
    # affiché est un ordre de grandeur, pas une mesure au centième. On DIT « ~6,7 » (une décimale,
    # virgule FR, tilde d'approximation) au lieu de « 6.73 ». La valeur brute reste en config.
    rr_ile_dit = f"~{rr_ile:.1f}".replace(".", ",") if isinstance(rr_ile, (int, float)) else None
    fragile = bool(c.get("positifs_faibles"))
    nom = c.get("commune")
    n = c.get("n_hors_copro")
    rr = c.get("rr_intra")
    n_fr = f"{n:,}".replace(",", " ") if isinstance(n, int) else str(n)   # espace fine insécable comme séparateur de milliers
    if fragile:
        libelle = (f"{nom} : marché peu actif ({n_fr} parcelles analysées, base {c.get('taux_base_pct')} %) — "
                   "le classement reste fiable, la fréquence exacte est indicative (échantillon limité : "
                   "pouvoir discriminant mesuré sur moins de 5 ventes dans le haut du classement).")
    else:
        libelle = (f"{nom} : pouvoir discriminant RR {rr} mesuré sur {n_fr} parcelles (robuste, "
                   f"≥ 5 ventes dans le haut du classement) — île {rr_ile_dit or rr_ile}.")
    return {
        "commune": nom, "insee": insee, "rr_intra": rr, "rr_ile": rr_ile, "rr_ile_dit": rr_ile_dit,
        "echantillon": n, "taux_base_pct": c.get("taux_base_pct"),
        "fragile": fragile, "degradee": fragile, "libelle": libelle,
        "source": "audit RR fold 2025 (out-of-sample) · mesure seule",
    }


def _division_fiche(db: Session, idu: str, surface_m2: float | None) -> dict | None:
    """M129-C P3 — la ligne « Division » de la fiche (un seul juge : division_or_candidates)."""
    r = db.execute(text(
        "SELECT residuel_m2, residuel_facade_m, type_division, "
        "       (coalesce(note_revue,'') <> '') AS revue "
        "FROM division_or_candidates WHERE idu = :i"), {"i": idu}).mappings().first()
    if not r:
        return None
    try:
        from .. import config as _cfg
        lot_type = float(_cfg.seuils_geometrie()["division_or"].get("lot_type_m2_defaut", 350))
    except Exception:  # noqa: BLE001
        lot_type = 350.0
    pot = max(1, int((surface_m2 or 0) // lot_type)) if surface_m2 else None
    return {
        "lot_m2": int(r["residuel_m2"]) if r["residuel_m2"] is not None else None,
        "facade_m": float(r["residuel_facade_m"]) if r["residuel_facade_m"] is not None else None,
        "type": r["type_division"],
        "statut_revue": "vérifié" if r["revue"] else "calculé, non revu",
        "potentiel_lots": pot,                       # ESTIMÉ — surface ÷ lot type (config)
        "potentiel_source": "Estimé — surface ÷ lot type de la zone (config), pas une promesse",
        "ligne": (f"1 lot détachable de {int(r['residuel_m2'])} m²"
                  + (f" (façade {r['residuel_facade_m']:.0f} m)" if r["residuel_facade_m"] else "")
                  + (f" · potentiel total ~{pot} lots (Estimé)" if pot else "")),
    }


def _data_sources_fiche(db: Session, parcel_id: int, run_label: str) -> list[dict]:
    """M52 L3 — « Les données » : sources RÉELLEMENT utilisées sur CETTE fiche (distinct des
    couches cascade), avec millésime et fiabilité. Réutilise la table `data_sources` (0 nouvelle
    donnée). Requête EN begin_nested (contrat savepoint : requête ajoutée au build de fiche)."""
    with db.begin_nested():
        rows = db.execute(text(
            """SELECT DISTINCT ds.name, ds.category, ds.provider,
                      ds.source_millesime, ds.source_horizon_at, ds.reliability_level
               FROM dryrun_cascade_results cr JOIN data_sources ds ON ds.id = cr.data_source_id
               WHERE cr.run_label = :run AND cr.parcel_id = :pid
               ORDER BY ds.category, ds.name"""),
            {"run": run_label, "pid": parcel_id}).mappings().all()
    # M70 décision 4 — « vérifiée » MENTAIT : source_checks est VIDE, aucune vérification amont ne
    # l'adosse (reliability_level = déclaration de catalogue). Libellé honnête = « suivie » (la
    # source est cataloguée + suivie par le radar, jamais « vérifiée à la dernière version »).
    _FIAB = {"verifie": "suivie", "estime": "estimée", "declaratif": "déclarative",
             "a_confirmer": "à confirmer"}
    out = []
    for r in rows:
        mill = r["source_millesime"] or (str(r["source_horizon_at"].year) if r["source_horizon_at"] else None)
        out.append({
            "nom": r["name"], "categorie": r["category"], "fournisseur": r["provider"],
            "millesime": mill, "fiabilite": _FIAB.get(r["reliability_level"], r["reliability_level"]),
        })
    return out


def _q_v2_geojson(db: Session, commune: str | None, limit: int, run_label: str = Q_A_RUN_LABEL) -> dict:
    """Parcelles + matrice premium v2 (dryrun_parcel_evaluations). `status` = matrice_statut ;
    Q/A + complétude + événement rouge exposés (exigences #1/#2/#4). Une parcelle exclue à
    l'étage 0 apparaît en `ecartee` ; les `evenement='rouge'` (BODACC ouvert) sont marquées.
    M6 2a (§1.8) : l'adresse BAN entre dans les properties (cartes de résultats mode commune) —
    lateral indexé, mesuré +0,3 s / +1,7 MB sur Saint-Paul (51k parcelles, base 8,2 s / 38,6 Mo)."""
    # M6.2 perf (#1) : adresse BAN via la table matérialisée `parcel_adresse` (LEFT JOIN PK
    # indexé) quand elle existe — sinon repli sur le LATERAL par-parcelle (~5,4 s pour 21k en
    # commune). Les deux produisent la MÊME adresse (DISTINCT ON = même ORDER BY que le lateral).
    if _adresse_ready(db):
        ban_cols = ", pa.ban_voie, pa.ban_cp, pa.ban_commune"
        ban_join = "LEFT JOIN parcel_adresse pa ON pa.idu = p.idu"
    elif _ban_ready(db):
        ban_cols = ", ban.ban_voie, ban.ban_cp, ban.ban_commune"
        ban_join = _ban_lateral("p.idu")
    else:
        ban_cols = ", NULL AS ban_voie, NULL AS ban_cp, NULL AS ban_commune"
        ban_join = ""
    # M6.1 item 1 : zone PLU dominante (jointure PK légère) — NULL si table pas encore bâtie
    zone_ok = _zone_plu_ready(db)
    zone_cols = (", zp.zone_lib, zp.zone_fam" if zone_ok
                 else ", NULL AS zone_lib, NULL AS zone_fam")
    zone_join = "LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu" if zone_ok else ""
    # M6.2 perf (#1) : la FeatureCollection est assemblée EN SQL (json_build_object + json_agg) et
    # renvoyée en STRING BRUTE — l'ancienne version faisait `json.loads(g)` × 51k puis FastAPI
    # re-sérialisait (~13 s côté Python pour ~1 s de SQL). Le SELECT interne est INCHANGÉ (mêmes
    # colonnes/jointures) ; les transformations Python (round, _fmt_ban, "rouge", bool…) sont
    # traduites 1:1 en SQL. Sortie vérifiée BYTE-À-BYTE identique (Salazie 7032 + Saint-Paul 51005).
    # Le json_build de 51k features reste ~11 s côté Postgres (plancher mesuré) → résultat CACHÉ
    # par (commune, run) via _geojson_cached : payé une fois, instantané ensuite.
    v2run = _score_v2_run_id(db)
    # CLOISON exfiltration (P0) : le nom du propriétaire (PM) ne sort JAMAIS par le dump ÎLE
    # ENTIÈRE (commune absente) — ce canal de masse ne doit pas déverser l'identité des
    # propriétaires. En mode COMMUNE (borné, usage normal de la carte), proprio/owner_type
    # restent exposés. Le front sert l'île en TUILES (les tuiles ne portent aucun propriétaire).
    _own_proprio = "b.proprio" if commune else "NULL"
    _frac_case = _fraction_sql_case("b.p_raw")   # M135 — fraction humaine EN SQL (geojson caché), config-driven
    _own_type = "b.owner_type" if commune else "NULL"
    _geo_sql = text(
        f"""
        WITH base AS (
        SELECT p.idu, p.surface_m2,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(p.geom, 0.00002)) AS g,
               s2.tier AS tier_v2, s2.rang AS rang_v2, s2.mult_base AS mult_v2,
               s2.p_raw AS p_raw, s2.top5_contributions AS top5,   -- M135 : fraction + raison (carte)
               s2.copro AS copro_v2, s2.event_date,
               (vw.parcelle_id IS NOT NULL) AS veille,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               d.status AS status, d.opportunity_score,  -- M129-B : matrice morte → statut cascade
               d.completeness_score, r.sdp_residuelle_m2, r.sous_densite,
               (ev.parcel_id IS NOT NULL) AS evenement_rouge, fl.flags,
               cl.n AS cluster, COALESCE(cl.denom, own.denomination) AS proprio,
               vs.v_score, vs.v_band, vs.owner_type,
               -- CRED-4 : fraîcheur du signal V daté le plus récent (BODACC/cessation/DPE)
               (SELECT max(s1->>'date_evenement') FROM jsonb_array_elements(vs.signals) s1
                 WHERE s1->>'date_evenement' IS NOT NULL)    AS v_dernier_signal,
               (SELECT array_agg(s0->>'code') FROM jsonb_array_elements(vs.signals) s0) AS v_sig
               {ban_cols}{zone_cols}
        FROM parcels p
        {ban_join}
        {zone_join}
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcel_veille_succession vw ON vw.parcelle_id = p.idu
        LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu
        LEFT JOIN parcelle_personne_morale own ON own.idu = p.idu
        LEFT JOIN (SELECT pm2.siren, count(*) AS n, max(pm2.denomination) AS denom
                   FROM dryrun_parcel_evaluations d2
                   JOIN parcels p2 ON p2.id = d2.parcel_id
                   JOIN parcel_p_score_v2 s22 ON s22.parcelle_id = p2.idu AND s22.run_id = :v2run
                   JOIN parcelle_personne_morale pm2 ON pm2.idu = p2.idu
                   WHERE d2.run_label = :run AND s22.tier IN ('brulante', 'chaude')
                     AND NOT (d2.status IN ('exclue', 'faux_positif_probable'))
                     AND pm2.siren IS NOT NULL
                   GROUP BY pm2.siren HAVING count(*) > 1) cl ON cl.siren = own.siren
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id AND r.cause IS NULL
        LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                   WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
        -- flags actifs par parcelle (filtres métier) : couches en SOFT_FLAG + ABF non instruit.
        -- M6.2 perf (#1) : SCOPÉ à la commune (join parcels) — sinon cette agrégation scanne les
        -- 14 M lignes de dryrun_cascade_results à l'île entière (~5,4 s FIXE) à CHAQUE requête
        -- commune. Les flags sont PAR PARCELLE (indépendants entre parcelles) → scoper est
        -- sémantiquement identique. Commune NULL (mode île, rare en geojson) = comportement inchangé.
        LEFT JOIN (SELECT cr.parcel_id, array_agg(DISTINCT cr.layer_name) AS flags
                   FROM dryrun_cascade_results cr
                   JOIN parcels pf ON pf.id = cr.parcel_id
                        AND (CAST(:c AS text) IS NULL OR pf.commune = :c)
                   WHERE cr.run_label = :run AND (cr.result = 'SOFT_FLAG'
                         OR (cr.layer_name = 'abf' AND cr.result = 'UNKNOWN'))
                   GROUP BY cr.parcel_id) fl ON fl.parcel_id = p.id
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
          AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)
        LIMIT :lim
        )
        SELECT json_build_object('type', 'FeatureCollection', 'features',
          coalesce(json_agg(json_build_object(
            'type', 'Feature',
            'geometry', b.g::json,
            'properties', json_build_object(
              'idu', b.idu,
              'surface_m2', CASE WHEN b.surface_m2 IS NULL OR b.surface_m2 = 0 THEN NULL
                                 ELSE round(b.surface_m2)::int END,
              'adresse', CASE WHEN b.ban_voie IS NULL OR b.ban_voie = '' THEN NULL
                              ELSE b.ban_voie || CASE
                                WHEN NULLIF(concat_ws(' ', b.ban_cp, b.ban_commune), '') IS NOT NULL
                                THEN ', ' || concat_ws(' ', b.ban_cp, b.ban_commune) ELSE '' END END,
              'status', b.status,
              'tier_v2', b.tier_v2, 'rang_v2', b.rang_v2, 'mult_v2', b.mult_v2,
              'fraction', {_frac_case}, 'top5', b.top5,   -- M135 : fraction (SQL) + top5 (raison au front)
              'etage0', b.etage0,
              -- M129-B : q_score/a_score/a_completude retirés (matrice morte)
              'completeness_score', b.completeness_score,
              'sdp_residuelle_m2', b.sdp_residuelle_m2, 'sous_densite', b.sous_densite,
              'evenement', CASE WHEN b.evenement_rouge THEN 'rouge' ELSE NULL END,
              'evenement_date', CASE WHEN b.event_date IS NULL THEN NULL ELSE b.event_date::text END,
              'flags', to_jsonb(coalesce(b.flags, '{{}}')),
              'cluster', CASE WHEN b.cluster IS NULL OR b.cluster = 0 THEN NULL ELSE b.cluster::int END,
              'proprio', {_own_proprio}, 'v_score', b.v_score, 'v_dernier_signal', b.v_dernier_signal,
              'v_band', b.v_band, 'owner_type', {_own_type},
              'copro_v2', coalesce(b.copro_v2, false), 'veille', b.veille,
              'v_sig', to_jsonb(coalesce(b.v_sig, '{{}}')),
              'zone_lib', b.zone_lib, 'zone_fam', b.zone_fam
            )
          )), '[]'::json))::text
        FROM base b WHERE b.g IS NOT NULL
        """)

    def _compute() -> str:
        return db.execute(_geo_sql, {"c": commune, "run": run_label, "lim": limit,
                                     "minsurf": MIN_DISPLAY_SURFACE_M2, "v2run": v2run}).scalar() \
            or '{"type":"FeatureCollection","features":[]}'

    # Cache serveur en mode COMMUNE (le cas lourd, 51k features) ; île = tuiles (pas ce chemin).
    fc = _geojson_cached((commune, run_label, v2run, limit), _compute) if commune else _compute()
    # source=<run> pinné dans l'URL → le contenu ne change qu'au re-run (rare) : cache navigateur court.
    return Response(content=fc, media_type="application/json",
                    headers={"Cache-Control": "public, max-age=600"})


#: tris de la liste (M5.1 lot 1.3) — rang P par défaut ; ×N, surface, commune en options ;
#: 'v' (vendabilité) accepté mais deprecated (disparu du sélecteur). Deux formes : sur les
#: alias de la requête de page (p/d/s2/ev/vs) et sur la page matérialisée (pg).
_Q_V2_ORDERS = {
    "rang": "s2.rang ASC NULLS LAST, s2.mult_base DESC NULLS LAST, "
            "(ev.parcel_id IS NOT NULL) DESC, d.opportunity_score DESC",  # M129-B
    "mult": "s2.mult_base DESC NULLS LAST, s2.rang ASC NULLS LAST",
    "surface": "p.surface_m2 DESC NULLS LAST, s2.rang ASC NULLS LAST",
    # M55-H point 4 : le tri Surface gagne son sens INVERSE (re-clic sur la pill) —
    # même clé, ordre ASC (les slivers < 2 m² restent masqués par MIN_DISPLAY_SURFACE_M2).
    "surface_asc": "p.surface_m2 ASC NULLS LAST, s2.rang ASC NULLS LAST",
    "commune": "p.commune ASC, s2.rang ASC NULLS LAST",
    "v": "vs.v_score DESC NULLS LAST, (ev.parcel_id IS NOT NULL) DESC, "
         "d.opportunity_score DESC",  # M129-B
}
_Q_V2_ORDERS_PAGE = {
    "rang": "pg.rang_v2 ASC NULLS LAST, pg.mult_v2 DESC NULLS LAST, "
            "pg.evenement_rouge DESC, pg.opportunity_score DESC",  # M129-B
    "mult": "pg.mult_v2 DESC NULLS LAST, pg.rang_v2 ASC NULLS LAST",
    "surface": "pg.surface_m2 DESC NULLS LAST, pg.rang_v2 ASC NULLS LAST",
    "surface_asc": "pg.surface_m2 ASC NULLS LAST, pg.rang_v2 ASC NULLS LAST",
    "commune": "pg.commune ASC, pg.rang_v2 ASC NULLS LAST",
    "v": "vs.v_score DESC NULLS LAST, pg.evenement_rouge DESC, "
         "pg.opportunity_score DESC",  # M129-B
}

# M55-H point 5 (décision Vic) — GROUPEMENT PAR TIER : la liste d'analyse se groupe
# brûlantes → chaudes → potentiel long terme → à creuser → potentiel épuisé (declasse_*) ;
# le tri choisi s'applique DANS chaque groupe (l'ORDER BY est préfixé par ce CASE).
_TIER_GROUPE_SQL = (
    "CASE WHEN (d.status IN ('exclue', 'faux_positif_probable')) THEN 6 "
    "WHEN s2.tier = 'brulante' THEN 0 WHEN s2.tier = 'chaude' THEN 1 "
    "WHEN s2.tier = 'reserve_fonciere' THEN 2 WHEN s2.tier = 'a_creuser' THEN 3 "
    "WHEN s2.tier LIKE 'declasse%' THEN 4 ELSE 5 END")
_TIER_GROUPE_PAGE_SQL = (
    "CASE WHEN pg.etage0 THEN 6 "
    "WHEN pg.tier_v2 = 'brulante' THEN 0 WHEN pg.tier_v2 = 'chaude' THEN 1 "
    "WHEN pg.tier_v2 = 'reserve_fonciere' THEN 2 WHEN pg.tier_v2 = 'a_creuser' THEN 3 "
    "WHEN pg.tier_v2 LIKE 'declasse%' THEN 4 ELSE 5 END")

# M131 P3 — ÉTAT DU BIEN (affichage pur du FAIT M125/M129-D, aucun recalcul) : partition
# EXACTE sur les colonnes existantes de parcel_residuel (1 ligne/parcelle, PK parcel_id).
# nu = emprise bâtie < 5 % (même seuil que etat_sol=nu) ; sinon bâti, deux états par la SDP
# résiduelle (cause NULL) : « encore construire » (>0) / « construite au maximum » (=0).
# Mesuré sur le vivier servi : nu 67 250 · encore 110 053 · maximum 108 478 = 285 781.
_ETAT_BIEN_SQL = (
    "CASE WHEN COALESCE(rb.taux_emprise_pct, 0) < 5 THEN 'nu' "
    "WHEN COALESCE(rb.sdp_residuelle_m2, 0) > 0 THEN 'bati_encore' ELSE 'bati_max' END")


def _q_v2_list(db: Session, commune: str | None, limit: int, offset: int, run_label: str = Q_A_RUN_LABEL,
               extra_where: str = "", extra_params: dict | None = None,
               sort: str | None = None, groupes: bool = False) -> list[dict]:
    """Liste pilotée par le scoring v2 (M5.1) : tri par défaut = RANG P (croissant, copros
    en queue), périmètre par défaut = univers v2 HORS étage 0 du run servi — une brûlante
    v2 « écartée matrice » APPARAÎT. Un filtre `tiers` explicite (extra_where) remplace ce
    périmètre (l'opt-in « ecartee » = étage 0 dur uniquement).

    M55-H point 5 : `groupes=True` préfixe l'ORDER BY par l'ordre des tiers (groupement) —
    le tri choisi devient secondaire, DANS chaque groupe."""
    sort_key = sort if (sort or "rang") in _Q_V2_ORDERS else "rang"
    order = _Q_V2_ORDERS[sort_key or "rang"]
    if groupes:
        order = f"{_TIER_GROUPE_SQL}, {order}"
    xp = extra_params or {}
    # périmètre par défaut : hors étage 0 servi, sauf filtre tier explicite qui scope déjà
    base = "" if ("f_tiers" in xp
                  or "s2.tier" in extra_where or _ETAGE0_SQL in extra_where) \
        else f"AND NOT {_ETAGE0_SQL}"
    # M31 PC4 (arbitrage M30) : ALIGNER la LISTE sur la CARTE — les slivers cadastraux < 2 m²
    # (MIN_DISPLAY_SURFACE_M2), masqués de la carte/geojson depuis toujours, l'étaient PAS de la
    # liste (asymétrie relevée à l'inventaire M30). Même plancher d'AFFICHAGE ici : les slivers
    # restent en base et dans les compteurs de volumétrie (comme la carte), simplement pas listés.
    _sliver = "AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)"
    # Adresse BAN (M6 2a) : jointure APRÈS pagination (page de :lim lignes seulement) —
    # 1 lookup indexé par ligne servie, mesuré +0,03 s sur la liste île (contrainte 1,5 s OK).
    ban_ok = _ban_ready(db)
    ban_cols = (", ban.ban_voie, ban.ban_cp, ban.ban_commune" if ban_ok
                else ", NULL AS ban_voie, NULL AS ban_cp, NULL AS ban_commune")
    ban_join = _ban_lateral("pg.idu") if ban_ok else ""
    # perf (M5.1) : tri + filtres d'abord (page de :lim lignes), PUIS les jointures
    # d'affichage (propriétaire, cluster, veille, signaux) sur cette page seulement —
    # 3,6 s → <1 s sur l'île entière (baseline legacy : 4,1 s).
    #
    # perf (BLOC B · B1.2) : pour le TRI PAR DÉFAUT (rang), la page se construit en
    # PARCOURANT L'INDEX `ix_p_v2_run_rang` (top-N sans scan ni tri : ~2 ms au lieu de
    # ~1 s sur l'île). Préconditions VÉRIFIÉES en base : s2 couvre 100 % des parcelles du
    # run (le LEFT JOIN historique ≡ INNER) et `rang` est UNIQUE quand non nul (les
    # tiebreakers historiques n'ordonnaient réellement que la queue rang IS NULL = les
    # copros). La queue est petite et se lit par le même index (rang IS NULL) ; l'union
    # rejoue l'ordre historique + un tiebreaker p.idu explicite qui rend TOTAL un ordre
    # que l'ancien plan laissait flotter sur les égalités de queue (constaté au garde-fou
    # avant/après). Les autres tris (mult/surface/commune/v) gardent la requête historique.
    _page_cols = """p.id, p.idu, p.commune, p.surface_m2, p.section,
                   d.status AS status, d.opportunity_score,  -- M129-B : matrice morte → statut cascade
                   d.completeness_score,
                   s2.tier AS tier_v2, s2.rang AS rang_v2, s2.mult_base AS mult_v2, s2.p_raw AS p_raw,
                   s2.top5_contributions AS top5,   -- M135 P3 : la raison dominante (affichage)
                   s2.copro AS copro_v2, s2.event_date,
                   (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
                   (ev.parcel_id IS NOT NULL) AS evenement_rouge"""
    v2run = _score_v2_run_id(db)
    # chemin rapide seulement si un run v2 existe : sans lui, le LEFT JOIN historique
    # sert le repli legacy (colonnes v2 NULL) — le chemin s2-driven renverrait vide.
    # (groupes : le chemin rapide « index rang » ne sait pas préfixer par tier → requête générale)
    if sort_key == "rang" and v2run is not None and not groupes:
        _fast_from = f"""
            FROM parcel_p_score_v2 s2
            JOIN parcels p ON p.idu = s2.parcelle_id
            JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                       WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
            WHERE s2.run_id = :v2run
              AND (CAST(:c AS text) IS NULL OR p.commune = :c)
              {_sliver}
              {base}
              {extra_where}"""
        page_sql = f"""
        page AS (
            SELECT * FROM (
                (SELECT {_page_cols} {_fast_from} AND s2.rang IS NOT NULL
                 ORDER BY s2.rang ASC LIMIT :need)
                UNION ALL
                (SELECT {_page_cols} {_fast_from} AND s2.rang IS NULL
                 ORDER BY s2.mult_base DESC NULLS LAST, (ev.parcel_id IS NOT NULL) DESC,
                          d.opportunity_score DESC, p.idu ASC LIMIT :need)  -- M129-B
            ) page_u
            ORDER BY rang_v2 ASC NULLS LAST, mult_v2 DESC NULLS LAST,
                     evenement_rouge DESC, opportunity_score DESC, idu ASC  -- M129-B
            LIMIT :lim OFFSET :off
        )"""
    else:
        page_sql = f"""
        page AS (
            SELECT {_page_cols}
            FROM parcels p
            JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
            LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu
            LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                       WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
            WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
              {_sliver}
              {base}
              {extra_where}
            ORDER BY {order}
            LIMIT :lim OFFSET :off
        )"""
    rows = db.execute(text(
        f"""
        WITH {page_sql},
        /* B1.2 : le cluster même-proprio est MATÉRIALISÉ (une exécution, ~11 ms) — en
           sous-requête jointe, le planner le ré-exécutait PAR LIGNE dès que la page
           devenait bon marché (4,8 ms × lignes servies, constaté au plan). */
        cl AS MATERIALIZED (
            SELECT pm2.siren, count(*) AS n, max(pm2.denomination) AS denom
            FROM dryrun_parcel_evaluations d2
            JOIN parcels p2 ON p2.id = d2.parcel_id
            JOIN parcel_p_score_v2 s22 ON s22.parcelle_id = p2.idu AND s22.run_id = :v2run
            JOIN parcelle_personne_morale pm2 ON pm2.idu = p2.idu
            WHERE d2.run_label = :run AND s22.tier IN ('brulante', 'chaude')
              AND NOT (d2.status IN ('exclue', 'faux_positif_probable'))
              AND pm2.siren IS NOT NULL
            GROUP BY pm2.siren HAVING count(*) > 1
        )
        SELECT pg.*, (vw.parcelle_id IS NOT NULL) AS veille,
               cl.n AS cluster, COALESCE(cl.denom, own.denomination) AS proprio,
               vs.v_score, vs.v_band, vs.owner_type,
               {_ETAT_BIEN_SQL} AS etat_bien,   -- M131 P3 : état du bien (affichage pur)
               -- CRED-4 : fraîcheur du signal V daté le plus récent (BODACC/cessation/DPE)
               (SELECT max(s1->>'date_evenement') FROM jsonb_array_elements(vs.signals) s1
                 WHERE s1->>'date_evenement' IS NOT NULL)    AS v_dernier_signal
               {ban_cols}
        FROM page pg
        {ban_join}
        LEFT JOIN parcel_veille_succession vw ON vw.parcelle_id = pg.idu
        LEFT JOIN parcelle_personne_morale own ON own.idu = pg.idu
        LEFT JOIN parcel_v_score vs ON vs.parcelle_id = pg.idu
        LEFT JOIN parcel_residuel rb ON rb.parcel_id = pg.id   -- M131 P3 : 1 ligne/parcelle
        LEFT JOIN cl ON cl.siren = own.siren
        ORDER BY {(_TIER_GROUPE_PAGE_SQL + ', ') if groupes else ''}{_Q_V2_ORDERS_PAGE[sort_key or "rang"]}
        """), {"c": commune, "run": run_label, "lim": limit, "off": offset,
               "need": limit + offset, "minsurf": MIN_DISPLAY_SURFACE_M2,
               "v2run": v2run, **xp}
    ).mappings().all()
    return [{
        "idu": r["idu"], "commune": r["commune"], "surface_m2": round(r["surface_m2"]) if r["surface_m2"] else None,
        "adresse": _fmt_ban(r["ban_voie"], r["ban_cp"], r["ban_commune"]),
        "lieu_dit": r["commune"], "status": r["status"],  # M129-B : q/a (matrice morte) retirés
        "completeness_score": r["completeness_score"],
        "evenement": "rouge" if r["evenement_rouge"] else None,
        "evenement_date": str(r["event_date"]) if r["event_date"] else None,
        "cluster": int(r["cluster"]) if r["cluster"] else None,
        "proprio": r["proprio"],
        "v_score": r["v_score"], "v_band": r["v_band"], "owner_type": r["owner_type"],
        "v_dernier_signal": r["v_dernier_signal"],
        "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"],
        "mult_v2": float(r["mult_v2"]) if r["mult_v2"] is not None else None,
        # M135 P2 — la fraction humaine (« 1/5 sous 1 an ») de la proba calibrée servie ; None = « — »
        "fraction": (_fh(r["p_raw"]) or {}).get("texte"),
        # M135 P3 — la raison dominante (chip court, reason code n°1 positif) ; None = pas de badge
        "raison": _raison_dom(r["top5"]),
        "copro_v2": bool(r["copro_v2"]), "veille": bool(r["veille"]),
        "etage0": bool(r["etage0"]),
        "etat_bien": r["etat_bien"],   # M131 P3 : nu | bati_encore | bati_max (affichage)
    } for r in rows]


def _q_v2_stats(db: Session, commune: str | None, run_label: str = Q_A_RUN_LABEL,
                extra_where: str = "", extra_params: dict | None = None,
                legacy: bool = False) -> dict:
    """Comptes par TIER v2 EFFECTIF (M5.1) — l'étage 0 du run servi prime : une parcelle
    en étage 0 compte « écartée » quel que soit son tier. « Opportunités » = brûlantes v2
    + chaudes v2 (définition produit, tooltip « pourquoi ? »). `legacy=True` (deprecated)
    ajoute la ventilation matrice historique.

    DOSSIERS (unité de prospection) : parmi les OPPORTUNITÉS v2, propriétaires uniques
    identifiés — clé = SIREN (personnes morales, DGFiP). Limite consignée : les personnes
    physiques n'ont pas d'identité en base (doctrine) → « sans identité »."""
    params = {"c": commune, "run": run_label, "v2run": _score_v2_run_id(db),
              **(extra_params or {})}
    join_v2 = ("LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu"
               " AND s2.run_id = :v2run")
    eff = f"(CASE WHEN {_ETAGE0_SQL} THEN 'ecartee' ELSE COALESCE(s2.tier, 'ecartee') END)"
    row = db.execute(text(
        f"""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE {eff} = 'brulante')          AS t_brulante,
               count(*) FILTER (WHERE {eff} = 'chaude')            AS t_chaude,
               count(*) FILTER (WHERE {eff} = 'reserve_fonciere')  AS t_reserve,
               count(*) FILTER (WHERE {eff} = 'a_creuser')         AS t_a_creuser,
               count(*) FILTER (WHERE {eff} = 'ecartee')           AS t_ecartee,
               count(*) FILTER (WHERE {eff} IN ('brulante', 'chaude') AND EXISTS (
                   SELECT 1 FROM dryrun_cascade_results ev WHERE ev.parcel_id = d.parcel_id
                     AND ev.run_label = :run AND ev.evenement = 'rouge')) AS opportunites_evenement
        FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
        {join_v2}
        WHERE d.run_label = :run AND (CAST(:c AS text) IS NULL OR p.commune = :c)
          {extra_where}
        """), params).mappings().one()
    dossiers = db.execute(text(
        f"""
        SELECT count(DISTINCT pm.siren) FILTER (WHERE pm.siren IS NOT NULL) AS dossiers,
               -- CRED-3 : le compteur MANQUANT qui rend la somme lisible — les PARCELLES
               -- couvertes par un dossier, au lieu d'un « 80 (+36) » illisible
               count(*) FILTER (WHERE pm.siren IS NOT NULL)                 AS avec_dossier,
               count(*) FILTER (WHERE pm.siren IS NULL)                     AS sans_identite
        FROM dryrun_parcel_evaluations d
        JOIN parcels p ON p.id = d.parcel_id
        {join_v2}
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE d.run_label = :run AND {eff} IN ('brulante', 'chaude')
          AND (CAST(:c AS text) IS NULL OR p.commune = :c)
          {extra_where}
        """), params).mappings().one()
    out = {
        "total": int(row["total"] or 0),
        "tiers": {"brulante": int(row["t_brulante"] or 0), "chaude": int(row["t_chaude"] or 0),
                  "reserve_fonciere": int(row["t_reserve"] or 0),
                  "a_creuser": int(row["t_a_creuser"] or 0), "ecartee": int(row["t_ecartee"] or 0)},
        "opportunites": int(row["t_brulante"] or 0) + int(row["t_chaude"] or 0),
        "opportunites_evenement": int(row["opportunites_evenement"] or 0),
        "dossiers_opportunites": int(dossiers["dossiers"] or 0),
        "opportunites_avec_dossier": int(dossiers["avec_dossier"] or 0),
        "opportunites_sans_identite": int(dossiers["sans_identite"] or 0),
    }
    if legacy:  # M129-B : la matrice est MORTE — la ventilation legacy est retirée, DIT.
        out["legacy"] = {"mort": "matrice retirée (M129) — statut cascade + tier v2 la remplacent"}
    return out


#: axe A (pur vendeur) — cf. config/scoring_matrice.yaml a_layers. Tout le reste = Q.
_A_LAYERS = {"proprietaire", "age_dirigeant", "bodacc"}  # M71 B1 : dpe_passoire retiré du scoring
#: rattachement couche → onglet de la fiche (Synthèse/Bilan sont des vues, pas des groupes de lignes).
#: SOURCE UNIQUE dans served_cascade (M73 §1) — importé ici pour que fiche et documents partagent
#: le même rattachement (bruit_route/cinquante_pas classés en 'risques', pas en 'regles').
from .served_cascade import _ONGLET, _LAYER_ONGLET  # noqa: E402


#: CRED-2 (revue externe 12/07) — les lignes DVF STOCKÉES des runs antérieurs disent
#: « médiane 699 €/m² » sans dire que c'est un prix de TERRAIN (valeur ÷ surface terrain,
#: tous biens) : illisible face à la médiane BÂTI du Bilan (2 745 €/m²). Re-libellé à la
#: LECTURE (les données stockées ne bougent pas) ; les nouveaux runs sont nommés à la
#: source (cascade/layers/phase2.py). Fonction pure, testée.
def _relabel_dvf_terrain(layer: str, detail: str | None) -> str | None:
    if layer == "dvf" and detail and "médiane " in detail and "terrain" not in detail:
        return detail.replace("médiane ", "médiane terrain ", 1).replace(
            " €/m².", " €/m² (valeur ÷ surface terrain, tous biens).", 1)
    return detail


def _q_v2_fiche(db: Session, idu: str, run_label: str = Q_A_RUN_LABEL) -> dict:
    """Fiche premium v2 (dryrun) : en-tête matrice + lignes cascade TRACÉES (axe Q/A, onglet,
    source cliquable, date), flags, événement. « La traçabilité EST le produit »."""
    head = db.execute(text(
        """SELECT p.id, p.idu, p.commune, p.surface_m2,
                  ST_Y(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lat,
                  ST_X(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lon,
                  d.status AS status, d.completeness_score,  -- M129-B : matrice morte
                  (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
           FROM parcels p JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
           WHERE p.idu = :idu"""), {"idu": idu, "run": run_label}).mappings().first()
    if not head:
        # M102 P1.4 — jamais un identifiant de run dans un message susceptible d'atteindre
        # l'écran (mesuré : servi brut via le Copilote). Le run reste dans les logs serveur.
        raise HTTPException(404, f"Parcelle {idu} inconnue de l'analyse en cours.")

    # Correctif M5 (verdict d'en-tête) : tier v2 du run SERVI (`_score_v2_run_id` = Q_A_RUN_LABEL,
    # épinglé — PAS « le dernier run par timestamp ») — pilote la bannière/badge quand il existe ;
    # l'étage 0 du run SERVI (head.etage0) prime toujours (règle 1).
    v2run = _score_v2_run_id(db)
    s2 = db.execute(text(
        "SELECT tier, rang, mult_base, p_raw, percentile, copro, icd, icd_detail, top5_contributions "
        "FROM parcel_p_score_v2 "
        "WHERE run_id = :r AND parcelle_id = :idu"),
        {"r": v2run, "idu": idu}).mappings().first() if v2run else None
    score_v2 = None
    if s2:
        from ..scoring.echelle_verbale import enrichir_verbal
        from ..scoring.p_v2.libelles_client import enrichir_contributions
        _mult = float(s2["mult_base"]) if s2["mult_base"] is not None else None
        # M135 P2 — MÊME fraction que la carte de tri (calcul unique fraction_client)
        _fraction = (_fh(s2["p_raw"]) or {}).get("texte")
        _top5 = s2["top5_contributions"]
        if isinstance(_top5, str):
            _top5 = json.loads(_top5)
        # M54-AB F1 : le VERDICT servi (libellé client + motif) vient du POINT DE TRADUCTION
        # UNIQUE (verdict_servi) — jamais le code technique du tier, jamais une table recopiée.
        # + dénominateur du rang (un rang seul ne dit rien).
        from ..verdict_servi import (verdict_servi as _verdict_servi, rang_total as _rang_total,
                                      DECLASSE_COLOR as _DECLASSE_COLOR, COPRO_MOTIF as _COPRO_MOTIF)
        _vs = _verdict_servi(db, idu, run=v2run)
        score_v2 = {"tier": s2["tier"], "rang": s2["rang"], "mult_base": _mult,
                    "fraction": _fraction,   # M135 P2 — « 1/5 » ou None (« — »)
                    "percentile": float(s2["percentile"]) if s2["percentile"] is not None else None,
                    "copro": bool(s2["copro"]),
                    # libellé/motif client = source unique verdict_servi (miroir de l'écran)
                    "label": _vs["label"], "motif": _vs["motif"], "declasse": _vs["declasse"],
                    "exception_registre": _vs["exception_registre"],
                    "couleur_hex": _DECLASSE_COLOR if _vs["declasse"] else None,
                    "rang_total": _rang_total(db, v2run),
                    # M52 Lot 1 (présentation, 0 calcul) : mot verbal + ⓘ + fréquence par tier (config)
                    # + « pourquoi » (top5 traduites, libelles_client existant).
                    "verbal": enrichir_verbal(_mult, s2["tier"]),
                    "pourquoi": enrichir_contributions(_top5) if _top5 else []}
        # M89 — copropriété sans rang : on DIT pourquoi (jamais un vide). Clé AJOUTÉE seulement pour une
        # copro non classée (absente sinon → golden baseline inchangé). Libellé unique verdict_servi.
        if bool(s2["copro"]) and s2["rang"] is None:
            score_v2["hors_classement"] = _COPRO_MOTIF
    # M9 lot 1 — Indice de confiance données (ICD). Méta d'AFFICHAGE, CLOISONNÉE du score P :
    # ne modifie ni le tier, ni le rang, ni p_raw (cf. scoring/icd.py). Bloc annexe.
    icd_block = _icd_block(s2)

    rows = db.execute(text(
        """SELECT cr.layer_name, cr.result, cr.severity, cr.weight_applied, cr.detail,
                  cr.source_table, cr.source_id, cr.evenement, cr.created_at,
                  ds.name AS source, ds.source_millesime
           FROM dryrun_cascade_results cr LEFT JOIN data_sources ds ON ds.id = cr.data_source_id
           WHERE cr.run_label = :run AND cr.parcel_id = :pid
           -- `cr.id` : tiebreaker DÉTERMINISTE — une couche peut émettre 2 lignes de même |poids|
           -- (ex. zonage mixte : « Zonage mixte… » + « Zone PLU U… », poids nul tous deux). Sans
           -- lui, l'ordre des ex æquo suivait l'ordre physique (heap) → un gros UPDATE de la table
           -- le rebattait. L'ordre d'émission (= id croissant) est stable et fixe le « premier ».
           ORDER BY abs(COALESCE(cr.weight_applied, 0)) DESC, cr.layer_name, cr.id"""),
        {"pid": head["id"], "run": run_label}).mappings().all()

    lines, flags, evenement_detail = [], [], None
    _seen: set = set()
    # M124-B (audit) — nettoyage CLIENT des libellés (RGPD personne physique + codes techniques
    # bruts), au POINT UNIQUE de service de la fiche : écran ET pdf premium lisent ces `lines`.
    from .export_commun import nettoyer_libelle_client
    for r in rows:
        # M46 (Lot D) : DÉDUP des contraintes servies — une même contrainte peut être produite en
        # double par la cascade (intersections multiples d'une même source, ex. « PPR zone rouge
        # (inconstructible) » x2 sur 97421000AC0156, ou un aléa niveau moyen x3). Point de calcul
        # unique : une contrainte identique (couche + résultat + détail) = UNE ligne servie.
        _k = (r["layer_name"], r["result"], r["detail"])
        if _k in _seen:
            continue
        _seen.add(_k)
        w = r["weight_applied"]
        line = {
            "layer": r["layer_name"],
            "axis": "a" if r["layer_name"] in _A_LAYERS else "q",
            "onglet": _LAYER_ONGLET.get(r["layer_name"], "regles"),
            "result": r["result"],
            "severity": r["severity"],
            "weight": round(w) if w is not None else None,
            "detail": nettoyer_libelle_client(
                r["layer_name"], _relabel_dvf_terrain(r["layer_name"], r["detail"])),
            "source": r["source"],
            "source_table": r["source_table"],
            "source_id": r["source_id"],
            "date": r["created_at"].date().isoformat() if r["created_at"] else None,
            # M73 E : millésime AMONT réel de la source (data_sources.source_millesime) — c'est LUI
            # la fraîcheur par ligne, pas la date de run (uniforme = date pipeline, trompeuse).
            "millesime_amont": r["source_millesime"],
        }
        lines.append(line)
        if r["evenement"] == "rouge":
            evenement_detail = r["detail"]

    # M73 §1 — arbitrage & libellés client des lignes de risque (POINT DE CALCUL UNIQUE) : un seul
    # niveau par aléa (le plus contraignant, nommé), régime PPR réglementaire > intersection
    # géométrique marginale, aucun libellé technique brut. Consommé par les 5 documents via la
    # fiche servie (premium/dossier/banquier/fiche écran lisent ces lignes arbitrées).
    from .risques_arbitrage import arbitrer_risques
    lines = arbitrer_risques(lines)
    flags = [l for l in lines
             if l["weight"] in (None, 0) and l["result"] in ("SOFT_FLAG", "HARD_EXCLUDE", "UNKNOWN")]

    pm = db.execute(text(
        "SELECT denomination, siren, groupe_label FROM parcelle_personne_morale WHERE idu = :idu"),
        {"idu": idu}).mappings().first()
    pm = dict(pm) if pm else None
    if pm and pm.get("siren"):
        pm["etat_societe"] = _pm_etat_societe(db, pm["siren"])   # M43 — fait public société (PM only)
    # LOT 1 (data-gap) : dernière mutation DVF de LA parcelle + médianes du secteur cadastral.
    dvf_last = db.execute(text(
        "SELECT date_mutation, nature, valeur, prix_m2_bati, prix_m2_terrain, multi_parcelles "
        "FROM v_parcel_dvf_last WHERE idu = :idu"), {"idu": idu}).mappings().first()
    dvf_secteur = [dict(r) for r in db.execute(text(
        "SELECT type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre "
        "FROM dvf_secteur_medianes WHERE secteur = substring(:idu FROM 1 FOR 10) "
        "ORDER BY n_ventes DESC"), {"idu": idu}).mappings().all()]
    dvf_parcelle = None
    if dvf_last or dvf_secteur:
        # M101 B2 — le NEUF (VEFA) de la commune, par le point d'appel unique (profil neuf_vefa,
        # config dvf_profils.yaml). Sous le seuil : « échantillon insuffisant » AVEC la grandeur —
        # l'absence est un état normal de ce profil (11/24 communes servables, mesuré).
        from ..marche_service import DVF_NEUF_VEFA, marche_dvf as _marche_dvf
        try:
            neuf_vefa = _marche_dvf(db, idu, profil=DVF_NEUF_VEFA)
        except Exception:  # noqa: BLE001 — le neuf VEFA ne casse jamais la fiche
            neuf_vefa = None
        dvf_parcelle = {
            "derniere_mutation": ({**dict(dvf_last),
                                   "date_mutation": dvf_last["date_mutation"].isoformat()
                                   if dvf_last["date_mutation"] else None}
                                  if dvf_last else None),
            "secteur": dvf_secteur,
            "neuf_vefa": neuf_vefa,
            "caveat": "valeur = mutation entière (multi-parcelles possible) ; fenêtre 2021-2025",
        }
    # LOT 9 (data-gap) : terrain (pente RGE ALTI 5 m) — hypothèses affichées, jamais un « 0 » muet.
    terrain = db.execute(text(
        "SELECT pente_moy_deg, pente_max_deg, flag_terrassement_lourd "
        "FROM parcel_terrain WHERE idu = :idu"), {"idu": idu}).mappings().first()
    # LOT 10 (data-gap) : copropriété(s) RNIC rattachées à la parcelle (cible MdB, hors scoring).
    copros = [dict(r) for r in db.execute(text(
        "SELECT numero_immatriculation, nom_usage, adresse, nb_lots_total, nb_lots_habitation, "
        "       periode_construction, syndic_type, syndic_nom, rattachement "
        "FROM rnic_coproprietes WHERE parcelle_idu = :idu ORDER BY nb_lots_total DESC NULLS LAST"),
        {"idu": idu}).mappings().all()]
    # LOT 11 (data-gap) : contexte marché du secteur — carreau Filosofi 2021 (200 m, INSEE)
    # au centroïde + parc social RPLS de la commune. Contexte fiche, hors scoring.
    carreau = db.execute(text(
        """SELECT f.ind, f.men, f.men_pauv, f.men_prop,
                  round((f.ind_snv / NULLIF(f.ind, 0))::numeric) AS nivvie_moyen_eur
           FROM filosofi_carreaux_200m f JOIN parcels p2 ON p2.idu = :idu
           WHERE ST_Contains(f.geom, ST_Transform(p2.centroid, 2975)) LIMIT 1"""),
        {"idu": idu}).mappings().first()
    rpls = db.execute(text(
        "SELECT nb_logements, construct_median, pct_qpv FROM rpls_commune "
        "WHERE insee = substring(:idu FROM 1 FOR 5)"), {"idu": idu}).mappings().first()
    marche_secteur = None
    if carreau or rpls:
        marche_secteur = {
            "filosofi_200m": ({**dict(carreau),
                               "taux_pauvrete_pct": round(100 * carreau["men_pauv"] / carreau["men"])
                               if carreau["men"] else None,
                               "millesime": "Filosofi 2021 (INSEE, carreaux 200 m)"}
                              if carreau else None),
            "rpls_commune": ({**dict(rpls), "millesime": "RPLS 01/01/2025"} if rpls else None),
        }
    # Score V (Vendabilité, Stage 3 additif) : score + panneau « Pourquoi ce score » (signaux
    # JSONB §5.4, lus tels quels) + badges spéciaux (public/bailleur/copro/partiel).
    vrow = db.execute(text(
        "SELECT v_score, v_band, v_coverage, v_confidence, owner_type, owner_siren, "
        "       owner_denomination, signals, computed_at FROM parcel_v_score "
        "WHERE parcelle_id = :idu"), {"idu": idu}).mappings().first()
    score_v = None
    if vrow:
        badge = {"public": "Foncier public — démarche dédiée",
                 "bailleur": "Bailleur social",
                 "copro": "Copro — acquisition complexe"}.get(vrow["owner_type"])
        if badge is None and vrow["v_coverage"] == "partial":
            badge = "Signaux partiels"
        score_v = {
            "v_score": vrow["v_score"], "v_band": vrow["v_band"],
            "v_band_label": V_BAND_LABELS.get(vrow["v_band"] or "na"),
            "v_coverage": vrow["v_coverage"],
            "v_confidence": float(vrow["v_confidence"]) if vrow["v_confidence"] is not None else None,
            "owner_type": vrow["owner_type"], "owner_siren": vrow["owner_siren"],
            "owner_denomination": vrow["owner_denomination"],
            # M5.1 lexical : « brûlante » = tier v2 uniquement — le flag v1.3 (chaude ∧ V≥17)
            # n'est plus exposé ; les signaux vendeur restent le dossier propriétaire.
            "badge": badge,
            "signals": vrow["signals"] or [],
            "computed_at": vrow["computed_at"].isoformat() if vrow["computed_at"] else None,
        }
    # NPNRU (contexte, hors scoring) : parcelle DANS un périmètre de renouvellement urbain,
    # ou ADJACENTE (<= 100 m) — l'environnement immédiat d'un programme se transforme
    anru = db.execute(text(
        """SELECT a.name, a.attrs->>'interet' AS interet,
                  ST_Intersects(p2.geom_2975, a.geom_2975) AS dans
           FROM spatial_layers a JOIN parcels p2 ON p2.idu = :idu
           WHERE a.kind = 'anru' AND ST_DWithin(p2.geom_2975, a.geom_2975, 100)
           ORDER BY ST_Intersects(p2.geom_2975, a.geom_2975) DESC LIMIT 1"""),
        {"idu": idu}).mappings().first()
    return {
        "idu": head["idu"], "commune": head["commune"],
        # M6 2a (§1.8) : la meilleure adresse BAN rattachée — None si aucune (le front
        # affiche « Adresse non disponible », jamais un champ vide)
        "adresse": _ban_adresse(db, idu),
        # M28 (gaté LABUSE_M28_BADGES=1, servi à la bascule phase B) : badges filtre bâti +
        # géométrie contrainte — signaux de fiche, étiquetés, jamais un déclassement ici.
        **(_m28_badges(db, idu) if os.environ.get("LABUSE_M28_BADGES") == "1" else {}),
        "proprietaire_moral": pm,   # M43 : + etat_societe (fait public PM, si présent)
        "anru": {"quartier": anru["name"], "interet": anru["interet"],
                 "position": "dans" if anru["dans"] else "adjacente"} if anru else None,
        "surface_m2": round(head["surface_m2"]) if head["surface_m2"] else None,
        # M48 (F4) : le champ mort `statut` (matrice_statut v1, éteinte M37) est RETIRÉ du payload —
        # il contredisait le tier (71 115 parcelles) et a servi de munition à l'IA (F1). Le classement
        # se lit sur `score_v2.tier` (via verdictMeta au front) ; la matrice reste un signal interne.
        "score_v2": score_v2, "etage0": bool(head["etage0"]),  # M129-B : q/a retirés
        "parc_analysees": _parc_analysees(db, v2run),   # M52 L2 — théâtre « N parcelles analysées » (compte gelé du run)
        "data_sources": _data_sources_fiche(db, head["id"], run_label),   # M52 L3 — « Les données » (sources utilisées)
        "qualite_commune": _qualite_commune(idu[:5] if idu else None),     # M52 L4 — qualité commune DITE
        "icd": icd_block,
        "reglement_plu": _reglement_plu_block(db, idu, head["commune"]),
        "plu_fraicheur": _plu_fraicheur(idu),   # M32 §2 : fraîcheur GPU-vs-mairie du zonage
        "radar_procedure": _radar_proc(idu, (score_v2 or {}).get("tier")),   # M41 — radar procédures PLU
        "historique_site": _historique_site(db, idu),      # M42 — « Sur cette parcelle » (permis + caduc)
        "voisinage_proche": _voisinage_proche(db, idu),    # M42 — « Autour, à moins de 100 m »
        "potentiel_transformation": _potentiel_transformation_block(db, idu),
        "completeness_score": head["completeness_score"],  # M129-B : a_completude (matrice) retiré
        "coords": [round(head["lon"], 6), round(head["lat"], 6)],
        "evenement": "rouge" if evenement_detail else None, "evenement_detail": evenement_detail,
        "lines": lines, "flags": flags,
        "score_v": score_v,
        "dvf_parcelle": dvf_parcelle,
        "terrain": dict(terrain) if terrain else None,
        "coproprietes": copros,
        "marche_secteur": marche_secteur,
        # M-VIA : indicateur de viabilisation (faisceau de preuves) + gestionnaires.
        "viabilisation": _viabilisation_block(db, idu),
        # M86-B — assainissement (ANC / tout-à-l'égout) : contrainte de constructibilité, point de
        # calcul UNIQUE partagé avec le PDF/export (anc_service). Toujours servi (Absent = un état).
        "anc": _anc_block(db, idu),
        "gestionnaires": _gestionnaires_block(head["commune"]),
        # M75 — obligation APER (ombrières PV) portant sur la parcelle → tiroir Urbanisme. Information.
        "aper": _aper_block(db, idu),
        # M-RENOUV : segment Renouvellement (table additive, lecture seule) — le verdict
        # d'en-tête reste « Écartée » ; ce bloc n'ajoute qu'un badge + un « pourquoi ».
        "renouvellement": _renouvellement_block(db, idu),
        # MANDAT RNU (B3) : étiquetage commune sans document local — flag GÉNÉRAL
        # (config/rnu_communes.yaml), jamais un cas Saint-Philippe codé en dur.
        "rnu": _rnu.rnu_block(idu, db),
        # M33 — MODE B (réhabilitation) : lecture de fiche sur la population des 2 tiers
        # déclassés bâti (rien persisté, aucun tier touché, TOUJOURS Estimé). Hors
        # population → disponible=False, le front n'affiche rien.
        "mode_b": _mode_b_block(db, idu, run_label),
        # M106 P3 — dispositifs fiscaux TERRITORIAUX (ZFANG / FRR ex-ZRR) : attribut de
        # COMMUNE (patron M95), point de service unique territoire_fiscal.attributs_commune.
        # Des ÉTATS sourcés/datés + lien vers le texte — JAMAIS un chiffre fiscal (interdit
        # absolu du mandat) ; None si table absente (l'absence ne casse pas la fiche).
        "territoire_fiscal": _territoire_fiscal_block(db, idu),
        # M106 P4 — PROXIMITÉS (arbitrage : distance, jamais un booléen) : arrêt, pôle
        # d'échange (statut + concordance OSM↔GTFS dite), téléphérique, ligne HT (contrainte).
        "proximites": _proximites_block(db, idu),
    }


def _territoire_fiscal_block(db: Session, idu: str) -> dict | None:
    from ..territoire_fiscal import attributs_commune
    base = attributs_commune(db, idu[:5])
    # M134 — les PÉRIMÈTRES FINS qui touchent LA parcelle (ZFANG/FRR sont à la commune) : QPV
    # (dedans) ou, à défaut, la bande des 500 m (dérivée). En français, sourcés, jamais un sigle nu.
    qpv = db.execute(text(
        "SELECT sl.name FROM spatial_layers sl JOIN parcels p ON p.idu = :idu "
        "WHERE sl.kind = 'qpv' AND ST_Intersects(p.geom_2975, sl.geom_2975) LIMIT 1"),
        {"idu": idu}).scalar()
    tva = db.execute(text(
        "SELECT 1 FROM spatial_layers sl JOIN parcels p ON p.idu = :idu "
        "WHERE sl.kind = 'tva_primo' AND ST_Intersects(p.geom_2975, sl.geom_2975) LIMIT 1"),
        {"idu": idu}).first()
    anru = db.execute(text(
        "SELECT sl.name FROM spatial_layers sl JOIN parcels p ON p.idu = :idu "
        "WHERE sl.kind = 'anru' AND ST_Intersects(p.geom_2975, sl.geom_2975) LIMIT 1"),
        {"idu": idu}).scalar()
    perimetres = []
    if anru:
        perimetres.append({
            "libelle": "Renouvellement urbain — NPNRU / ANRU",
            "detail": f"La parcelle est dans le périmètre « {anru} » d'un programme national de "
                      "renouvellement urbain : opérations d'aménagement pilotées par l'ANRU, "
                      "maîtrise foncière publique active.",
            "source": "DEAL Réunion / ANCT", "derive": False})
    if qpv:
        perimetres.append({
            "libelle": "Quartier prioritaire — QPV",
            "detail": f"La parcelle est dans le quartier « {qpv} » : un logement neuf destiné à "
                      "l'accession y ouvre la TVA réduite pour l'accession sociale (sous conditions "
                      "de ressources de l'acquéreur).",
            "source": "ANCT — quartiers de génération 2024", "derive": False})
    elif tva:
        perimetres.append({
            "libelle": "Bande des 500 m d'un quartier prioritaire",
            "detail": "La parcelle est à moins de 500 m d'un QPV : la TVA réduite pour l'accession "
                      "sociale peut s'y étendre. Périmètre DÉRIVÉ par LABUSE à partir des QPV "
                      "(Estimé) — à confirmer, ce n'est pas une source officielle.",
            "source": "LABUSE — dérivé des QPV (500 m)", "derive": True})
    if base is None and not perimetres:
        return None
    return {**(base or {}), "perimetres": perimetres}


def _plus_proche(db: Session, idu: str, kind: str, subtype: str | None = None) -> dict | None:
    """L'objet `kind` le plus proche de la parcelle (KNN geom_2975) + distance en mètres.
    M106 : PROXIMITÉ, jamais appartenance — on sert la distance, le lecteur juge."""
    row = db.execute(text(
        "SELECT sl.name, sl.subtype, sl.attrs, round(ST_Distance(sl.geom_2975, p.geom_2975))::int AS d "
        "FROM spatial_layers sl, parcels p WHERE p.idu = :idu AND sl.kind = :k "
        "AND sl.geom_2975 IS NOT NULL AND (CAST(:st AS text) IS NULL OR sl.subtype = :st) "
        "ORDER BY sl.geom_2975 <-> p.geom_2975 LIMIT 1"),
        {"idu": idu, "k": kind, "st": subtype}).mappings().first()
    if not row:
        return None
    return {"nom": row["name"], "subtype": row["subtype"],
            "attrs": row["attrs"] or {}, "distance_m": row["d"]}


_FICHE_LOG = logging.getLogger("labuse.fiche")


def _bloc_indisponible(nom: str) -> dict:
    """M125 (boussole : pas de constat non sourcé) — un bloc de fiche qui LÈVE (panne technique)
    ne renvoie plus None (= « rien à signaler »). Il renvoie un ÉTAT DISTINCT, LOGGÉ (traceback),
    que l'écran ET le PDF rendent en clair (« donnée indisponible — erreur technique »). À appeler
    DEPUIS un `except` (log.exception lit la trace courante). L'ABSENCE réelle reste None."""
    _FICHE_LOG.exception("fiche · bloc « %s » indisponible (erreur technique)", nom)
    return {"indisponible": True, "raison": "erreur technique"}


def _proximites_block(db: Session, idu: str) -> dict | None:
    """M106 P4 — proximité transport (arrêt / pôle d'échange / téléphérique) et ligne HT.
    Données absentes (base de test, ingestion pas passée) → None : l'absence ne casse pas."""
    try:
        arret = _plus_proche(db, idu, "transport_arret")
        pole = _plus_proche(db, idu, "pole_echange")
        tele = _plus_proche(db, idu, "telepherique", "station")
        ht = _plus_proche(db, idu, "ligne_ht")
    except Exception:
        db.rollback()
        return _bloc_indisponible("proximites")   # M125 — panne ≠ absence
    if not any((arret, pole, tele, ht)):
        return None
    out: dict = {}
    if arret:
        out["arret"] = {"nom": arret["nom"], "reseau": arret["attrs"].get("reseau"),
                        "distance_m": arret["distance_m"]}
    if pole:
        a = pole["attrs"]
        est_osm = pole["subtype"] == "osm"
        out["pole"] = {
            "nom": pole["nom"], "distance_m": pole["distance_m"],
            # le STATUT dit la nature : Sourcé (station OSM) ou Estimé (dérivé GTFS, critère dit)
            "statut": "Sourcé" if est_osm else "Estimé",
            "source": "station OSM" if est_osm else a.get("critere", "dérivé GTFS"),
            # une contradiction entre les deux sources se DIT, jamais tranchée en silence
            "concordance": a.get("concordance"),
            "nb_lignes": a.get("nb_lignes"),
        }
    if tele:
        out["telepherique"] = {"station": tele["nom"], "distance_m": tele["distance_m"],
                               "licence": "OSM (ODbL)"}
    # M106-B P3 — l'AXE STRUCTURANT le plus proche (BD TOPO, hiérarchie « importance » IGN 1-2,
    # jamais une hiérarchie inventée). Le libellé porte LES DEUX FACES : accessibilité ET
    # nuisance — jamais un avantage nu. Le recul L. 111-6 des axes classés n'est pas cartographié
    # en donnée ouverte (dit) ; le classement SONORE est déjà évalué au tiroir Risques
    # (couche bruit_route) — pointé, pas dupliqué.
    try:
        axe = _plus_proche(db, idu, "axe_structurant")
    except Exception:
        db.rollback()
        # M125 — sous-requête isolée : on ne masque plus l'échec en silence (log), mais le bloc
        # garde ses autres proximités réelles ; l'axe est simplement omis (dégradation partielle).
        _FICHE_LOG.exception("fiche · bloc « proximites.axe » indisponible (erreur technique)")
        axe = None
    if axe:
        nat = (axe["attrs"].get("nature") or "route")
        d = axe["distance_m"]
        out["axe"] = {
            "nom": axe["nom"], "nature": nat, "distance_m": d,
            "libelle": (f"Axe structurant {axe['nom']} ({nat.lower()}) "
                        + ("au contact de la parcelle" if d <= 5 else f"à ~{d} m")
                        + " — deux faces : accessibilité (desserte rapide) ET nuisances "
                        "potentielles (bruit, pollution ; recul le long des axes classés, "
                        "art. L. 111-6 — non cartographié en donnée ouverte, à vérifier au PLU). "
                        "Le classement sonore, lui, est évalué au tiroir Risques."),
            "source": "BD TOPO IGN — hiérarchie « importance » de l'IGN (niveaux 1-2)",
        }
    if ht:
        t = ht["attrs"].get("tension") or "tension non renseignée"
        out["ligne_ht"] = {
            "distance_m": ht["distance_m"], "tension": t,
            # CONTRAINTE, pas un avantage — et la servitude I4 n'est pas cartographiée : on le dit.
            "libelle": (f"Ligne haute tension ({t}) "
                        + ("au contact de la parcelle" if ht["distance_m"] <= 5
                           else f"à ~{ht['distance_m']} m")
                        + " — contrainte potentielle (servitudes, reculs). La servitude I4 n'est "
                        "pas cartographiée en donnée ouverte : à vérifier auprès du gestionnaire "
                        "de réseau (EDF SEI)."),
            "source": "BD TOPO IGN (aérien seul — le souterrain n'y figure pas)",
        }
    return out


def _mode_b_block(db: Session, idu: str, run_label: str) -> dict:
    """M33 — bloc mode B de la fiche (défaut travaux). Jamais un 500 sur la fiche."""
    try:
        from ..faisabilite.bilan import compute_mode_b
        return compute_mode_b(db, idu, run=run_label)
    except Exception:  # noqa: BLE001 — le mode B ne casse jamais la fiche
        # M125 — PANNE distincte de l'absence : `disponible=False` (contrat existant) + `indisponible`
        # pour que l'écran/PDF disent « erreur technique », jamais « rien à signaler ».
        return {"disponible": False, **_bloc_indisponible("mode_b")}


@app.get("/parcels/{idu}/mode-b")
def parcel_mode_b(idu: str, travaux_m2: float | None = Query(None, ge=500, le=4000),
                  regime_locatif: str | None = Query(None, pattern="^(base|intermediaire)$"),
                  loyer_marche_m2: float | None = Query(None, ge=1, le=100),
                  rendement_cible_pct: float | None = Query(None, ge=1, le=20),
                  db: Session = Depends(get_db)) -> dict:
    """M33/M44 — recalcul du bilan MODE B avec les paramètres CLIENT (travaux €/m² SHAB ; et, pour la
    sortie LOCATIVE M44 : régime de plafond, loyer de marché, rendement cible). État de session/UI
    uniquement : RIEN n'est persisté en base (exigence P3.2)."""
    _check_idu(idu)
    from ..faisabilite.bilan import compute_mode_b
    return compute_mode_b(db, idu, travaux_m2=travaux_m2, regime_locatif=regime_locatif,
                          loyer_marche_m2=loyer_marche_m2, rendement_cible_pct=rendement_cible_pct)


def _renouvellement_block(db: Session, idu: str) -> dict | None:
    """M-RENOUV lot B — segment Renouvellement (None si table absente ou parcelle hors
    segment). DOCTRINE : « potentiel de renouvellement urbain », jamais « opportunité »."""
    if not db.execute(text("SELECT to_regclass('parcel_renouvellement') IS NOT NULL")).scalar():
        return None
    r = db.execute(text(
        "SELECT renouv_score, comp_potentiel, comp_assiette, comp_marche, "
        "       code_bati_origine, sdp_residuelle_m2, surface_m2, zone_plu, commune, "
        "       rang_segment, rang_commune, "
        # M47 (P2) : millésime/source de la couche servie — run servi + date de matérialisation.
        "       run_label, to_char(computed_at, 'YYYY-MM-DD') AS maj, "
        "       (SELECT count(*) FROM parcel_renouvellement WHERE run_label = :run)  AS total_segment, "
        "       (SELECT count(*) FROM parcel_renouvellement r2 "
        "        WHERE r2.commune = parcel_renouvellement.commune "
        "          AND r2.run_label = :run)                                          AS total_commune "
        # M47 : scopé sur le run servi (config/served_run.txt via Q_A_RUN_LABEL) — jamais un label en dur.
        "FROM parcel_renouvellement WHERE idu = :idu AND run_label = :run"),
        {"idu": idu, "run": Q_A_RUN_LABEL}).mappings().first()
    if not r:
        return None
    from ..renouvellement import LIBELLE_SEGMENT, LIBELLES_COMPOSANTES
    return {
        "libelle": LIBELLE_SEGMENT,
        # M47 (P2) : étiquette « source · millésime » (doctrine : toute couche servie porte la date
        # de sa source amont). Source = Analyse LABUSE (segment calculé) ; millésime = run servi + maj.
        "source": "Analyse LABUSE", "run_label": r["run_label"], "maj": r["maj"],
        "renouv_score": r["renouv_score"],
        "rang_segment": r["rang_segment"], "total_segment": r["total_segment"],
        "rang_commune": r["rang_commune"], "total_commune": r["total_commune"],
        "code_bati_origine": r["code_bati_origine"],
        "zone_plu": r["zone_plu"],
        "sdp_residuelle_m2": r["sdp_residuelle_m2"], "surface_m2": r["surface_m2"],
        "composantes": [
            {"cle": k, "points": r[k], "max": m, "libelle": LIBELLES_COMPOSANTES[k]}
            for k, m in (("comp_potentiel", 47), ("comp_assiette", 29),
                         ("comp_marche", 24))
        ],
    }


def _viabilisation_block(db: Session, idu: str) -> dict | None:
    """M-VIA lot 2 — indicateur de viabilisation de la parcelle (None si non calculé).
    Aucun tracé réseau : uniquement le faisceau de preuves stocké dans parcel_viabilisation."""
    from ..faisabilite import viabilisation as V
    from ..faisabilite.viabilisation_build import ilot_s3renr_note, solaire_note
    row = db.execute(text(
        "SELECT zone_fam, c100, c200, c100_recent, c100_acheve, voie10, voie75, "
        "       bati10, bati30, bati75, assainissement_zonage "
        "FROM parcel_viabilisation WHERE idu = :idu"), {"idu": idu}).mappings().first()
    if not row:
        return None
    # M75 — PVGIS branché ici (volet PV, à côté du S3REnR) en INFORMATION seule.
    return V.build_indicateur(dict(row), elec_pv=ilot_s3renr_note(db),
                              solaire=solaire_note(db, idu))


def _aper_block(db: Session, idu: str) -> dict | None:
    """M75 — obligation APER portant sur la parcelle → tiroir Urbanisme. INFORMATION.
    Délègue au point de calcul unique (viabilisation_build.aper_note) partagé avec les exports."""
    from ..faisabilite.viabilisation_build import aper_note
    return aper_note(db, idu)


def _anc_block(db: Session, idu: str) -> dict:
    """M88 — état ANC servi (Sourcé / Sourcé secteur / Absent) + couverture réglementaire, via le point
    de calcul UNIQUE `anc_service.statut_anc` (partagé fiche/PDF/export). Le secteur sert le taux INSEE
    brut (RP2022), jamais proba_anc. Toujours un dict (Absent = état)."""
    from ..anc_service import couverture_anc, statut_anc
    out = statut_anc(db, idu)
    out["couverture"] = couverture_anc(db)
    return out


def _gestionnaires_block(commune: str) -> dict | None:
    """M-VIA lot 1 — bloc gestionnaires (contact administratif, aucune donnée sensible)."""
    from ..faisabilite import viabilisation as V
    try:
        return V.resolve_gestionnaires(commune)
    except Exception:  # noqa: BLE001 — jamais de 500 sur la fiche
        return _bloc_indisponible("gestionnaires")   # M125 — panne ≠ absence


def _icd_block(s2) -> dict | None:
    """M9 lot 1 — bloc Indice de confiance données (ICD) pour la fiche.

    Méta d'AFFICHAGE lue telle quelle depuis parcel_p_score_v2 (colonnes icd/icd_detail,
    backfill scoring/icd.py). CLOISONNÉE du score P : n'entre ni dans le tier ni dans le
    rang. None si le run n'a pas d'ICD (repli silencieux)."""
    if not s2 or s2.get("icd") is None:
        return None
    from ..scoring import icd as _icd
    val = int(s2["icd"])
    detail = s2["icd_detail"] or {}
    return {
        "score": val,
        "bande": _icd.bande(val),                 # haute | partielle | faible
        "libelle": _icd.libelle_bande(val),
        "detail": detail,                         # {groupe: bool}
        "manquants": _icd.manquants(detail),      # libellés client des groupes absents
        "cloisonnement": "Complétude des données de la parcelle — n'entre PAS dans le "
                         "score d'opportunité (score P gelé, calculé indépendamment).",
    }


_PLU_FRAICHEUR_CACHE: dict = {}


def _plu_fraicheur(idu: str) -> dict | None:
    """M32 Phase B §2 — étiquette de FRAÎCHEUR du zonage PLU (spec millésime, GPU-vs-mairie).
    L'HORIZON du zonage = date d'approbation MAIRIE (point de vérité config/plu_millesimes.yaml,
    ancré par l'annuaire + la campagne de ré-extraction). Le STATUT expose l'écart GPU↔mairie :
    `a_jour` (GPU = mairie) · `annule_partiel` (annulation de portée hors zonage servi) ·
    `opposabilite_en_attente` (mairie opposable mais AUCUN document GPU — révision en cours) · `rnu`.
    L'API sert l'objet structuré ; le front formate. INSEE = 5 premiers car. de l'IDU."""
    insee = (idu or "")[:5]
    if "cfg" not in _PLU_FRAICHEUR_CACHE:
        try:
            _PLU_FRAICHEUR_CACHE["cfg"] = (config.load_yaml_config("plu_millesimes") or {}).get("communes", {})
        except Exception:  # noqa: BLE001 — config absente = pas d'étiquette, jamais un 500
            _PLU_FRAICHEUR_CACHE["cfg"] = {}
    c = _PLU_FRAICHEUR_CACHE["cfg"].get(insee)
    if not c:
        return None
    statut = c.get("statut")
    horizon = c.get("date_mairie")
    note = c.get("note")
    # M40 — les TROIS choses distinctes, jamais mélangées : (1) quel document LABUSE SERT,
    # (2) qu'il est bien celui qui FAIT FOI à ce jour, (3) ce qui est EN COURS et non servi.
    # `en_cours` dit UNIQUEMENT ce qui est pendant/non servi (jamais ne répète le document servi) ;
    # le `note` config détaillé reste servi à part (traçabilité), il ne se substitue pas aux 3 temps.
    doc = f"PLU approuvé le {horizon}" if horizon else "PLU"
    if statut == "a_jour":
        document_servi, fait_foi = doc, "Document à jour du GPU — c'est celui qui fait foi."
        # M57-P1 (d) : ce libellé est GÉNÉRIQUE (gated sur `note` config = assertion d'agent, PAS
        # une source ni une procédure détectée). Reformulé en avertissement NEUTRE, sans « en cours »
        # ni sablier (cf. rendu front qui n'applique plus le cadre « En cours (non servi) » à a_jour).
        en_cours = ("Des modifications postérieures au document peuvent exister — à confirmer en mairie."
                    if note else None)
        action = None  # l'avertissement neutre porte déjà « à confirmer en mairie »
    elif statut == "annule_partiel":
        document_servi = doc
        fait_foi = "Document opposable servi — l'annulation partielle ne touche pas le zonage servi."
        en_cours = "Annulation contentieuse limitée, hors zonage servi (détail en note)."
        action = "Pour le secteur visé par l'annulation, vérifier le règlement en mairie."
    elif statut == "opposabilite_en_attente":
        document_servi = f"{doc} (opposable, présent au GPU)"
        fait_foi = "Document opposable — il fait foi à ce jour."
        en_cours = "Une révision est en cours, non approuvée — non opposable, non servie."
        action = "Vérifier en mairie le calendrier de révision avant engagement."
    elif statut == "rnu":
        document_servi = "Aucun PLU — RNU (règlement national d'urbanisme)."
        fait_foi = "Le RNU s'applique ; aucun zonage communal servi."
        en_cours = None
        action = "Constructibilité au cas par cas (RNU) — vérifier en mairie."
    else:
        document_servi, fait_foi, en_cours, action = doc, None, None, None
    # M41 — le radar procédures PLU précise « en cours » pour les cibles SOURCE (« révision générale
    # prescrite le X, constaté le Y »), remplaçant le texte générique. None si commune non-cible.
    try:
        from ..veille_plu import fiche_en_cours as _radar_en_cours
        _rec = _radar_en_cours(insee)
        if _rec:
            en_cours = _rec
    except Exception:  # noqa: BLE001 - le radar ne bloque jamais la fiche
        pass
    libelle = (f"{document_servi} — {fait_foi}" if fait_foi else document_servi)
    return {"idurba": c.get("idurba"), "horizon": horizon, "statut": statut,
            "libelle": libelle, "note": note, "cadence": "révisions (périodique)",
            # M40 : exposition en 3 temps (front). fait_foi_ok = booléen honnête.
            "document_servi": document_servi, "fait_foi": fait_foi, "en_cours": en_cours,
            "action": action, "fait_foi_ok": statut in ("a_jour", "annule_partiel", "opposabilite_en_attente")}


def _radar_proc(idu: str, tier: str | None) -> dict | None:
    """M41 — bloc RADAR procédures PLU de la parcelle (point de calcul unique labuse.veille_plu) :
    synthèse commune + sursis (si armé) + veille AU (si déclassée AU/zone-fermée). None si rien."""
    try:
        from ..veille_plu import radar_parcelle
        return radar_parcelle(idu, tier)
    except Exception:  # noqa: BLE001 - le radar ne bloque jamais la fiche
        return _bloc_indisponible("radar_procedure")   # M125 — panne ≠ absence


def _pm_etat_societe(db: Session, siren: str | None) -> dict | None:
    """M43 — état PUBLIC de la SOCIÉTÉ propriétaire (PM ONLY, niveau société) : cessée / radiée /
    procédure collective, chacun Sourcé + daté. C'est un FAIT public d'entreprise — on le DIT, on
    n'en déduit RIEN à l'écran (pas de vigilance, pas de badge, pas de filtre). None si société
    saine / absente. RGPD : jamais la personne (dirigeants NON lus). SAVEPOINT : table absente en
    base de test n'avorte pas la fiche."""
    if not siren:
        return None
    try:
        with db.begin_nested():
            etats = []
            ce = db.execute(text(
                "SELECT payload->>'etat_administratif' AS etat, payload->>'date_fermeture' AS d "
                "FROM owner_enrichment WHERE siren = :s LIMIT 1"), {"s": siren}).mappings().first()
            if ce and ce["etat"] == "C":
                etats.append({"type": "cessée", "date": (ce["d"] or None),
                              "libelle": f"cessée{(' le ' + ce['d']) if ce['d'] else ''}",
                              "source": "Sirene/INSEE (recherche-entreprises)", "etiquette": "Sourcé"})
            for b in db.execute(text(
                "SELECT famille, max(date_annonce)::text AS d FROM bodacc_annonces_owner "
                "WHERE siren = :s AND famille IN ('radiation','pcl') GROUP BY famille"),
                    {"s": siren}).mappings().all():
                if b["famille"] == "radiation":
                    etats.append({"type": "radiée", "date": b["d"],
                                  "libelle": f"radiée le {b['d']}", "source": "BODACC", "etiquette": "Sourcé"})
                else:
                    etats.append({"type": "procédure collective", "date": b["d"],
                                  "libelle": f"procédure collective (dernière annonce {b['d']})",
                                  "source": "BODACC", "etiquette": "Sourcé"})
    except Exception:  # noqa: BLE001 — jamais bloquant pour la fiche
        return None
    if not etats:
        return None
    return {"etats": etats,
            "libelle": "Société propriétaire : " + " ; ".join(e["libelle"] for e in etats) + ".",
            "note": "Fait public d'entreprise (état de la société) — information de contexte, aucune déduction."}


def _historique_site(db: Session, idu: str) -> dict | None:
    """M42 — « Sur cette parcelle » (historique permis + caducité). None si rien. Jamais bloquant.
    SAVEPOINT (idiome fraicheur.py) : une table/colonne absente (base de test) n'avorte pas la TX fiche."""
    try:
        from .site_voisinage import historique_permis
        with db.begin_nested():
            return historique_permis(db, idu)
    except Exception:  # noqa: BLE001
        return _bloc_indisponible("historique_site")   # M125 — panne ≠ absence


def _voisinage_proche(db: Session, idu: str) -> dict | None:
    """M42 — « Autour, à moins de 100 m » (ventes DVF + permis, 36 mois). None si rien. Jamais bloquant.
    SAVEPOINT : une table/colonne absente (base de test) n'avorte pas la TX fiche."""
    try:
        from .. import marche_service          # M73-B Volet C — point d'appel UNIQUE (profil 100 m M38)
        with db.begin_nested():
            return marche_service.marche_dvf(db, idu, profil=marche_service.DVF_VOISINAGE_100M)
    except Exception:  # noqa: BLE001
        return _bloc_indisponible("voisinage_proche")   # M125 — panne ≠ absence


def _reglement_plu_block(db: Session, idu: str, commune: str) -> dict | None:
    """M9 lot 2 — lien règlement PLU par zone. Croise plu_gpu_zone au centroïde/emprise
    de la parcelle → (zone, idurba) → référence article/page (config/plu_<commune>.yaml).
    Repli propre si la commune n'est pas outillée (cf. plu_reglement.reglement_block)."""
    from ..plu_reglement import reglement_block
    zones = [dict(r) for r in db.execute(text(
        """SELECT DISTINCT sl.subtype AS zone,
                  sl.attrs->>'libelle' AS libelle, sl.attrs->>'idurba' AS idurba
             FROM spatial_layers sl JOIN parcels p ON p.idu = :idu
            WHERE sl.kind = 'plu_gpu_zone'
              AND ST_Intersects(sl.geom_2975, p.geom_2975)"""), {"idu": idu}).mappings().all()]
    try:
        return reglement_block(zones, commune)
    except Exception:  # noqa: BLE001 — jamais de 500 sur la fiche
        return _bloc_indisponible("reglement_plu")   # M125 — panne ≠ absence (même classe que les 7)


def _potentiel_transformation_block(db: Session, idu: str) -> dict | None:
    """M9 lot 4 — indicateur « Potentiel de transformation » (fond de l'ancien outil Mutabilité).

    Alimenté par le ratio SDP consommée/autorisée déjà calculé (bloc D : parcel_residuel.
    pct_potentiel) et enrichi du signal SURÉLÉVATION (parcel_residuel_bati), qui n'est PAS
    couvert par le seul ratio SDP — cf. SYNTHESE-M9 (avant/après). None si aucune donnée
    résiduelle (repli propre : parcelle non bâtie / hors périmètre calcul)."""
    try:
        row = db.execute(text(
            """SELECT r.pct_potentiel, r.sdp_residuelle_m2, r.sous_densite, r.capacite_estimee,
                      rb.surelevation_possible, rb.hauteur_bati_m, rb.hauteur_max_m, rb.confiance
                 FROM parcels p
                 LEFT JOIN parcel_residuel r ON r.parcel_id = p.id AND r.cause IS NULL
                 LEFT JOIN parcel_residuel_bati rb ON rb.idu = p.idu
                WHERE p.idu = :idu"""), {"idu": idu}).mappings().first()
    except Exception:  # noqa: BLE001 — jamais de 500 sur la fiche (tables résiduel absentes)
        return _bloc_indisponible("potentiel_transformation")   # M125 — panne ≠ absence
    if not row or (row["pct_potentiel"] is None and row["surelevation_possible"] is None):
        return None
    pct = row["pct_potentiel"]
    if pct is None:
        niveau, libelle = "indetermine", "Marge SDP non calculée"
    elif pct < 40:
        niveau, libelle = "fort", "Fort potentiel — parcelle en forte sous-densité"
    elif pct < 70:
        niveau, libelle = "modere", "Potentiel modéré — droits à bâtir partiellement dormants"
    elif pct < 100:
        niveau, libelle = "faible", "Potentiel faible — parcelle proche de sa densité autorisée"
    else:
        niveau, libelle = "nul", "Densité autorisée atteinte ou dépassée"
    hauteur_marge = (round(row["hauteur_max_m"] - row["hauteur_bati_m"], 1)
                     if row["hauteur_max_m"] is not None and row["hauteur_bati_m"] is not None
                     else None)
    return {
        "niveau": niveau, "libelle": libelle,
        "pct_consomme": pct,                                  # SDP consommée / autorisée (%)
        "pct_residuel": (max(0, 100 - pct) if pct is not None else None),
        "sdp_residuelle_m2": row["sdp_residuelle_m2"],
        "sous_densite": row["sous_densite"],
        "capacite_estimee": row["capacite_estimee"],
        # Signal surélévation : NON couvert par le seul ratio SDP → conservé de l'outil Mutabilité.
        "surelevation_possible": row["surelevation_possible"],
        "hauteur_bati_m": row["hauteur_bati_m"], "hauteur_max_m": row["hauteur_max_m"],
        "hauteur_marge_m": hauteur_marge,
        "confiance": row["confiance"],
        "source": "Ratio SDP consommée/autorisée (bloc D du modèle P) + potentiel bâti "
                  "résiduel (BD TOPO × règles PLU calibrées)",
        "note": "Remplace l'ancien mode carte « Mutabilité » : même donnée résiduelle, "
                "à la parcelle, complétée du signal surélévation.",
    }


@app.get("/parcels/{idu}")
def parcel_fiche(idu: str, source: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Fiche « Tout ce que LA BUSE a trouvé » (§8).

    P2-32 (mesuré) : SANS `source`, on rend la fiche LEGACY (`_build_fiche`) ; la fiche premium
    (dryrun, `_q_v2_fiche`) n'est servie QUE si `source` commence par `q_v`. Le front envoie
    TOUJOURS `source=VITE_RUN_LABEL` (= Q_A_RUN_LABEL, cf. api.ts `getFiche`) → le client voit donc
    la premium ; le défaut sans `source` n'est PAS premium (l'ancienne docstring l'affirmait à tort).
    Le `Q_A_RUN_LABEL` n'est le défaut que du paramètre `run_label` de `_q_v2_fiche`, atteint
    seulement quand `source` est un label `q_v*`."""
    if source and source.startswith("q_v"):
        return _q_v2_fiche(db, idu, run_label=source)
    return _build_fiche(db, idu)


@app.get("/parcels/{idu}/export.pdf")
def parcel_export_pdf(idu: str, source: str = Q_A_RUN_LABEL,
                      cout_construction_m2: float | None = Query(None, ge=500, le=8000),
                      marge_frais_pct: float | None = Query(None, ge=0, le=60),
                      prix_demande_eur: float | None = Query(None, ge=0, le=500_000_000),
                      db: Session = Depends(get_db)) -> Response:
    """Export PDF de la fiche premium (Brique 3) — design system, fiche complète tracée.

    A6 (mandat bilan-calculette) : si les hypothèses de la calculette sont passées, le PDF porte
    la CHARGE FONCIÈRE « selon vos hypothèses » (recalculée par le moteur, jamais un faux chiffre)."""
    from .export_commun import adresse_ban_texte
    from .pdf_premium import render_fiche_pdf
    fiche = _q_v2_fiche(db, idu, run_label=source)
    # M6 2a : adresse postale BAN en tête du PDF (l'écran l'a, le papier doit l'avoir)
    fiche["adresse_ban"] = adresse_ban_texte(db, idu)
    # bloc CONTEXTE COMMUNE (mandat promotrice) : SRU + QPV/ANRU + 2-3 chiffres marché
    fiche["contexte_commune"] = commune_contexte(fiche["commune"], db)
    # M54-AB C5 : UNE ligne de synthèse marché DVF datée (bloc M-U), pas les 9 lignes.
    try:
        from .marche_bloc import bloc_condense
        _mc = {l["cle"]: l["phrase"] for l in
               bloc_condense(db, fiche["commune"], ["prix_ancien_median", "tendance_12m"])}
        fiche["marche_synthese"] = _mc.get("prix_ancien_median") or _mc.get("tendance_12m")
    except Exception:  # noqa: BLE001
        pass
    # M54-AB C7 : pente CLIENT = RGE ALTI (parcel_terrain), ° ET %, MÊME source que dossier/flash.
    try:
        from ..pente_fmt import pente_texte
        _pd = db.execute(text("SELECT pente_moy_deg FROM parcel_terrain WHERE idu = :i"),
                         {"i": idu}).scalar()
        if _pd is not None:
            fiche["pente_terrain"] = pente_texte(float(_pd))
    except Exception:  # noqa: BLE001
        pass
    fiche["rtaa"] = config.load_yaml_config("rtaa_dom")   # rappel réglementaire (5bis)
    # M73-E Volet B — comparables DVF du premium via le point d'appel UNIQUE (jamais un appel DVF
    # direct). Chaque vente porte date/distance/surface/prix ; n et rayon dits ; liste possiblement vide.
    from .. import marche_service
    fiche["comparables"] = marche_service.comparables(db, idu)
    # M73-F — plan de situation ORTHO : composite via build_situation_map (point d'appel UNIQUE, jamais
    # un fournisseur de tuiles en direct). Un échec de carte NE CASSE PAS le PDF (dict ok/echec). Le
    # millésime ortho est LU depuis data_sources (source unique, jamais en dur).
    from .plan_situation import plan_ortho
    from ..flash.report import storage_dir
    _gj = db.execute(text("SELECT ST_AsGeoJSON(geom) FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    fiche["plan_situation"] = plan_ortho(_gj, storage_dir() / "tiles")
    fiche["ortho_millesime"] = db.execute(text(
        "SELECT source_millesime FROM data_sources WHERE name = 'BD ORTHO 20 cm (IGN)'")).scalar()
    if cout_construction_m2 is not None and marge_frais_pct is not None:
        fiche["calculette"] = _calculette_for_pdf(db, idu, cout_construction_m2, marge_frais_pct, prix_demande_eur)
    return Response(content=render_fiche_pdf(fiche), media_type="application/pdf",
                    # M124-A4 — nom de fichier {IDU}-labuse.pdf (IDU d'abord : tri/recherche par parcelle).
                    headers={"Content-Disposition": f'inline; filename="{idu}-labuse.pdf"'})


def _calculette_for_pdf(db: Session, idu: str, cout: float, marge: float, prix_demande: float | None) -> dict | None:
    """Recalcule la charge foncière (moteur) pour l'export PDF — None si non calculable."""
    from ..faisabilite.bilan import compute_calculette, resolve_prix_sortie_servi
    from ..faisabilite.db import parcel_faisabilite
    from .. import marche_service          # MANDAT_DVF-B — point d'appel UNIQUE (plus de sector_price direct)
    row = db.execute(text("SELECT id, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        return None
    fz = parcel_faisabilite(db, row["id"])
    shab = (fz[1].fourchette or {}).get("shab_vendable_m2") if fz else None
    if not shab:
        return None
    # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — prix de sortie NEUF via le point partagé
    # (plus jamais sector_price/existant) ; non calculable (social-dominant) → None (pas de charge).
    ps = resolve_prix_sortie_servi(db, row["id"])
    if ps["non_calculable"]:
        return None
    prix = marche_service.marche_dvf(db, idu, profil=marche_service.DVF_BANQUIER_ADAPTATIF)
    prix = {**prix, "q1": ps["prix"], "median": ps["prix"], "q3": ps["prix"]}   # prix de sortie NEUF
    res = compute_calculette(float(shab), float(row["s"] or 0), prix, cout, marge, prix_demande)
    return res if res.get("calculable") else None


#: kinds de couches carte exposées au front (Brique 1) — whitelist stricte.
#: M6.1 item 2 : + cinquante_pas (réserve des 50 pas géométriques, 163 polygones île).
_MAP_LAYER_KINDS = {"plu_gpu_zone", "ppr", "parc_national", "anru", "amenite", "cinquante_pas",
                    # M106 P1 : aléas DEAL séparés (inondation / mouvement_terrain en subtype) —
                    # le zonage PPR réglementaire reste agrégé (document multirisque insécable).
                    "georisque_alea",
                    # M106 P4 / M106-B : transport public (tracés + arrêts + pôles + Papang),
                    # lignes HT et axes structurants (BD TOPO, hiérarchie « importance » IGN 1-2).
                    # Les arrêts sont servis en couche depuis M106-B (petits points, minzoom front).
                    "transport_ligne", "transport_arret", "pole_echange", "telepherique",
                    "ligne_ht", "axe_structurant",
                    # M134 — couche « Dispositifs et périmètres » : QPV + NPNRU/ANRU (géométrie),
                    # TVA primo (buffer 500 m dérivé), ZFANG/FRR (aplat COMMUNE, subtype=régime).
                    "qpv", "tva_primo", "zfang", "frr"}


@app.get("/map/layers.geojson")
def map_layers_geojson(kind: str, commune: str | None = None,
                       limit: int = Query(6000, ge=1, le=20000), db: Session = Depends(get_db)) -> dict:
    """Couches carte (zonage PLU, PPR, Parc national) — géométries simplifiées pour l'overlay.

    Les couches sans commune (île entière, ex. Parc) passent le filtre commune."""
    if kind not in _MAP_LAYER_KINDS:
        raise HTTPException(422, f"kind inconnu : {kind}")
    rows = db.execute(text(
        """SELECT sl.id, sl.subtype, sl.name, sl.attrs->>'niveau' AS niveau,
                  sl.attrs->>'critere' AS critere, sl.attrs->>'concordance' AS concordance,
                  sl.attrs->>'tension' AS tension, sl.attrs->>'nature' AS nature,
                  ST_AsGeoJSON(ST_SimplifyPreserveTopology(sl.geom, 0.0002)) AS g
           FROM spatial_layers sl
           WHERE sl.kind = :k AND (CAST(:c AS text) IS NULL OR sl.commune = :c OR sl.commune IS NULL)
           LIMIT :lim"""), {"k": kind, "c": commune, "lim": limit}).mappings().all()
    # M106 : `niveau` (aléa), `critere`/`concordance` (pôles dérivés — le seuil vient de la config,
    # jamais en dur à l'écran) et `tension` (HT) voyagent avec la géométrie — null ailleurs.
    feats = [{"type": "Feature", "geometry": json.loads(r["g"]),
              "properties": {"id": r["id"], "subtype": r["subtype"], "name": r["name"],
                             "niveau": r["niveau"], "critere": r["critere"],
                             "concordance": r["concordance"], "tension": r["tension"],
                             "nature": r["nature"]}}
             for r in rows if r["g"]]
    # M106 : millésime SERVI, jamais en dur (doctrine M86) — date d'intégration du flux
    # (max created_at du kind) ; la légende la dit comme telle.
    mill = db.execute(text(
        "SELECT max(created_at)::date FROM spatial_layers WHERE kind = :k"), {"k": kind}).scalar()
    return {"type": "FeatureCollection", "features": feats,
            "millesime_integration": mill.isoformat() if mill else None}


@app.get("/map/bati")
def map_bati(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Taux de bâti par parcelle (BD TOPO), pour le mode carte « mutabilité » (LOT 2).

    Calcul à la demande (spatial geom_2975) — la couche par défaut (verdict) reste rapide.
    `disponible=false` si la couche bâtiments n'est pas ingérée → l'UI le dit, ne ment pas."""
    from .. import bati as bati_mod
    commune = commune or config.get_settings().pilot_commune_name
    if not bati_mod.layer_available(db):
        return {"commune": commune, "disponible": False, "ratios": {}}
    rows = db.execute(
        text("SELECT id, idu FROM parcels WHERE commune = :c"), {"c": commune}
    ).all()
    id2idu = {r[0]: r[1] for r in rows}
    stats = bati_mod.stats_batch(db, list(id2idu.keys()))
    ratios = {id2idu[pid]: round(s.get("bati_ratio", 0.0), 3) for pid, s in stats.items()}
    return {"commune": commune, "disponible": True, "ratios": ratios}


@app.get("/assemblages")
def assemblages(commune: str | None = None, limit: int = Query(100, ge=1, le=500),
                db: Session = Depends(get_db)) -> dict:
    """Liste dédiée des assemblages fonciers (Lot C5) : paires contiguës qui, réunies,
    franchissent le seuil de taille — même propriétaire morale priorisé."""
    from .. import assemblage
    commune = commune or config.get_settings().pilot_commune_name
    groups = assemblage.find_assemblages(db, commune, limit=limit)
    return {"commune": commune, "count": len(groups),
            "prioritaires": sum(1 for g in groups if g["meme_proprietaire"]), "assemblages": groups}


@app.get("/assemblage/study")
def assemblage_study(idus: str, db: Session = Depends(get_db)) -> dict:
    """Étude de faisabilité sur un ENSEMBLE de parcelles regroupées (LOT 2) : surface cumulée,
    capacité cumulée (SDP / logements) et bilan cumulé, par AGRÉGATION des faisabilités
    par parcelle. Vérifie la contiguïté (mitoyenneté) — jamais d'assemblage fabriqué.
    `idus` = liste séparée par des virgules (cap à 8)."""
    from ..assemblage import ADJ_BUFFER_M
    from ..faisabilite.db import fiche_payload
    idu_list = [s.strip() for s in idus.split(",") if s.strip()][:8]
    for i in idu_list:
        _check_idu(i)
    if len(idu_list) < 2:
        raise HTTPException(400, "Sélectionnez au moins 2 parcelles mitoyennes.")
    parcels = db.execute(
        select(models.Parcel).where(models.Parcel.idu.in_(idu_list))
    ).scalars().all()
    if len(parcels) < 2:
        raise HTTPException(404, "Parcelles introuvables.")
    ids = [p.id for p in parcels]
    # Contiguïté : l'union des parcelles (tamponnées d'une demi-largeur d'adjacence) doit former
    # UN seul bloc connexe. Sinon, ce n'est pas un assemblage mitoyen.
    contigu = bool(db.execute(text(
        "SELECT ST_NumGeometries(ST_Union(ST_Buffer(geom_2975, :b))) = 1 "
        "FROM parcels WHERE id = ANY(:ids)"), {"b": ADJ_BUFFER_M / 2.0, "ids": ids}).scalar())
    surface_cumulee = round(sum(p.surface_m2 or 0 for p in parcels))
    sdp = 0.0
    log_min = log_max = 0
    ca = {"bas": 0, "central": 0, "haut": 0}
    charge = {"bas": 0, "central": 0, "haut": 0}
    n_chiffrables = 0
    for p in parcels:
        try:
            fa = fiche_payload(db, p.id)
        except Exception:  # noqa: BLE001 - une parcelle illisible ne casse pas l'étude
            fa = None
        fr = (fa or {}).get("fourchette") or {}
        sdp += fr.get("surface_plancher_m2") or 0
        rng = fr.get("logements_sous_sol") or fr.get("logements_au_sol") or [0, 0]
        log_min += rng[0] or 0
        log_max += rng[1] or 0
        bil = (fa or {}).get("bilan") or {}
        if bil.get("ca"):
            for k in ca:
                ca[k] += bil["ca"].get(k) or 0
            n_chiffrables += 1
        if bil.get("charge_fonciere"):
            for k in charge:
                charge[k] += bil["charge_fonciere"].get(k) or 0
    cf_m2 = round(charge["central"] / surface_cumulee) if surface_cumulee else None
    return {
        "idus": [p.idu for p in parcels],
        "n_parcelles": len(parcels),
        "contigu": contigu,
        "surface_cumulee_m2": surface_cumulee,
        "capacite": {"sdp_m2": round(sdp), "logements": [log_min, log_max]},
        "ca": ca if n_chiffrables else None,
        "charge_fonciere": ({**charge, "par_m2_terrain": cf_m2} if n_chiffrables else None),
        "n_chiffrables": n_chiffrables,
        "note": ("Faisabilité cumulée par agrégation des parcelles. "
                 + ("Ensemble mitoyen (contigu). " if contigu else "⚠ Parcelles non contiguës — ce n'est pas un assemblage mitoyen. ")
                 + "Surfaces et capacités indicatives ; accords propriétaires, géométrie d'opération "
                 "et règlement (reculs, mutualisation) restent à valider."),
    }


@app.get("/shortlist")
def shortlist(commune: str | None = None, limit: int = Query(5, ge=1, le=20),
              db: Session = Depends(get_db)) -> dict:
    """Shortlist promoteur — « les N sujets à traiter aujourd'hui ».

    Priorisation PROMOTEUR (pas le score brut) : exploitabilité + fiabilité + densification +
    poids économique + actionnabilité propriétaire − risque, puis bonus d'assemblage sur le
    haut du panier (enrichi via la fiche existante). Aucune donnée inventée : tout provient
    d'évaluations déjà calculées ; ce qui manque reste explicitement nul côté UI."""
    from .. import shortlist as sl
    from ..verdict_servi import TIERS_SERVABLES
    commune = commune or config.get_settings().pilot_commune_name
    # M34 (dette #14) : candidats = parcelles SERVIES dans un tier actif du run servi —
    # plus jamais le statut cascade legacy. `status` = tier servi (traduction unique) ;
    # les scores legacy restent des entrées de priorisation informatives, le motif de
    # déclassement non-franc reste un malus de risque (vigilance), pas un verdict.
    rows = db.execute(
        text(
            """
            SELECT p.idu, p.commune, p.surface_m2,
                   s.tier AS status, s.rang,
                   e.opportunity_score, e.completeness_score,
                   d.detail AS downgrade_reason,
                   r.sous_densite, r.sdp_residuelle_m2,
                   own.groupe AS own_groupe, own.forme_juridique AS own_forme, own.denomination AS own_denom
            FROM parcels p
            JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu AND s.run_id = :run
                 AND s.tier = ANY(:servables)
            LEFT JOIN LATERAL (
                SELECT opportunity_score, completeness_score
                FROM parcel_evaluations e WHERE e.parcel_id = p.id
                ORDER BY evaluated_at DESC LIMIT 1
            ) e ON true
            LEFT JOIN LATERAL (
                SELECT detail FROM cascade_results
                WHERE parcel_id = p.id AND layer_name = 'declassement' LIMIT 1
            ) d ON true
            LEFT JOIN parcel_residuel r ON r.parcel_id = p.id AND r.cause IS NULL
            LEFT JOIN parcelle_personne_morale own ON own.idu = p.idu
            WHERE p.commune = :c
            """
        ), {"c": commune, "run": Q_A_RUN_LABEL, "servables": list(TIERS_SERVABLES)}
    ).mappings().all()
    candidates = [
        {**{k: r[k] for k in ("idu", "commune", "surface_m2", "status", "rang",
                              "opportunity_score", "completeness_score", "downgrade_reason",
                              "sous_densite", "sdp_residuelle_m2")},
         "owner_famille": _owner_famille(r["own_groupe"], r["own_forme"], r["own_denom"])}
        for r in rows
    ]
    # 1) classement « cheap » → 2) enrichissement du panier → 3) bonus assemblage → 4) re-tri.
    pool = sl.rank_candidates(candidates, pool=min(max(limit * 2, limit), 12))
    enriched = []
    for row in pool:
        try:
            fiche = _build_fiche(db, row["idu"], with_assistant=False)
        except Exception:  # noqa: BLE001 - un sujet illisible ne casse jamais la shortlist
            fiche = None
        asm = ((fiche or {}).get("voisinage") or {}).get("assemblage") or {}
        fiab = (((fiche or {}).get("faisabilite") or {}).get("bilan") or {}).get("fiabilite")
        ab = sl.assemblage_bonus(bool(asm.get("possible")), asm.get("surface_cumulee_m2"))
        mb = sl.marche_bonus(fiab)
        row["_priority"] = (row.get("_priority") or 0) + ab + mb
        if isinstance(row.get("_components"), dict):
            row["_components"].update({"assemblage": ab, "marche": mb})   # transparence calibration
        enriched.append((row, fiche))
    enriched.sort(key=lambda t: (-(t[0].get("_priority") or 0),
                                 -(t[0].get("opportunity_score") or 0), t[0].get("idu") or ""))
    sujets = [sl.assemble_sujet(i + 1, row, fiche) for i, (row, fiche) in enumerate(enriched[:limit])]
    return {
        "commune": commune,
        "count": len(sujets),
        "candidates_total": len(candidates),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sujets": sujets,
    }


# ───────────────────────────── Radar Mutation : SUPPRIMÉ (M35 Lot E) ─────────────────────
# Le moteur V1 (src/labuse/mutation.py, pondérations placeholder, hors tiers, zéro UI) et ses
# 3 endpoints d'exploration [NON SERVI — ALGO-1 §7-G] sont retirés — décision Vic M35 (ALGO-1
# recommandait conserver-documenter ; le maintien d'un deuxième « score » non servi nuisait à
# la confiance). Récupération : git revert (module + endpoints + tests dans l'historique).


# ═══ M-RENOUV lot B — segment Renouvellement : couche carte + liste (LECTURE SEULE) ═══
# DOCTRINE : parcelles OCCUPÉES, « potentiel de renouvellement urbain », jamais
# « opportunité » ; vitrine parallèle, jamais mélangée aux Chaudes/Brûlantes (le flux
# principal /parcels n'est PAS touché). Toggle OFF par défaut côté carte.

@app.get("/map/renouvellement.geojson")
def renouvellement_geojson(commune: str | None = None,
                           limit: int = Query(1500, ge=1, le=3000),
                           db: Session = Depends(get_db)) -> dict:
    """Calque carte du segment Renouvellement : géométries des MEILLEURS rangs (île ou
    commune), score/rang en propriétés. `total` et `servis` sont renvoyés — la légende
    dit si le calque est tronqué (jamais un « tout » silencieux)."""
    if not db.execute(text("SELECT to_regclass('parcel_renouvellement') IS NOT NULL")).scalar():
        return {"type": "FeatureCollection", "features": [], "total": 0, "servis": 0}
    # M47 : TOUJOURS scopé sur le run servi (config/served_run.txt via Q_A_RUN_LABEL) ; commune en sus.
    where = "WHERE r.run_label = :run" + (" AND p.commune = :c" if commune else "")
    rows = db.execute(text(f"""
        SELECT r.idu, r.renouv_score, r.rang_segment, r.rang_commune, ST_AsGeoJSON(p.geom) AS g
        FROM parcel_renouvellement r JOIN parcels p ON p.idu = r.idu
        {where} ORDER BY r.rang_segment LIMIT :n"""),
        {"c": commune, "n": limit, "run": Q_A_RUN_LABEL}).all()
    meta = db.execute(text(f"""
        SELECT count(*) AS n, to_char(max(r.computed_at), 'YYYY-MM-DD') AS maj
        FROM parcel_renouvellement r JOIN parcels p ON p.idu = r.idu {where}"""),
        {"c": commune, "run": Q_A_RUN_LABEL}).mappings().first()
    total = int(meta["n"] or 0)
    feats = [{"type": "Feature", "geometry": json.loads(g),
              "properties": {"idu": idu, "renouv_score": sc, "rang_segment": rg, "rang_commune": rc}}
             for idu, sc, rg, rc, g in rows if g]
    # M47 (P2) : millésime/source de la couche servie (run servi + date de matérialisation).
    return {"type": "FeatureCollection", "features": feats, "total": total, "servis": len(feats),
            "source": "Analyse LABUSE", "run_label": Q_A_RUN_LABEL, "maj": meta["maj"]}


@app.get("/renouvellement/liste")
def renouvellement_liste(commune: str | None = None,
                         sort: str = Query("score", pattern="^(score|sdp|surface|rang_commune)$"),
                         limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
                         db: Session = Depends(get_db)) -> dict:
    """Liste du segment Renouvellement, triable (score par défaut). Sert l'outil dédié —
    JAMAIS le flux principal (doctrine : pas de mélange avec les tiers servis)."""
    if not db.execute(text("SELECT to_regclass('parcel_renouvellement') IS NOT NULL")).scalar():
        raise HTTPException(503, "segment Renouvellement non calculé (table absente).")
    from ..renouvellement import LIBELLE_SEGMENT, LIBELLES_COMPOSANTES
    orders = {"score": "r.renouv_score DESC, r.idu",
              "sdp": "r.sdp_residuelle_m2 DESC NULLS LAST, r.idu",
              "surface": "r.surface_m2 DESC NULLS LAST, r.idu",
              "rang_commune": "r.commune, r.rang_commune"}
    # M47 : TOUJOURS scopé sur le run servi (config/served_run.txt via Q_A_RUN_LABEL) ; commune en sus.
    where = "WHERE r.run_label = :run" + (" AND p.commune = :c" if commune else "")
    rows = db.execute(text(f"""
        SELECT r.idu, p.commune AS commune_nom, r.commune AS commune_insee, r.renouv_score,
               r.comp_potentiel, r.comp_assiette, r.comp_marche,
               r.code_bati_origine, r.sdp_residuelle_m2, r.surface_m2, r.zone_plu,
               r.rang_segment, r.rang_commune
        FROM parcel_renouvellement r JOIN parcels p ON p.idu = r.idu
        {where} ORDER BY {orders[sort]} LIMIT :n OFFSET :o"""),
        {"c": commune, "n": limit, "o": offset, "run": Q_A_RUN_LABEL}).mappings().all()
    meta = db.execute(text(f"""
        SELECT count(*) AS n, to_char(max(r.computed_at), 'YYYY-MM-DD') AS maj
        FROM parcel_renouvellement r JOIN parcels p ON p.idu = r.idu {where}"""),
        {"c": commune, "run": Q_A_RUN_LABEL}).mappings().first()
    total = int(meta["n"] or 0)
    # M47 (P2) : millésime/source de la couche servie (run servi + date de matérialisation).
    return {"total": total, "n": len(rows), "items": [dict(r) for r in rows],
            "source": "Analyse LABUSE", "run_label": Q_A_RUN_LABEL, "maj": meta["maj"],
            "libelle": LIBELLE_SEGMENT, "composantes_libelles": LIBELLES_COMPOSANTES,
            "avertissement": ("Parcelles occupées : potentiel physique et réglementaire de "
                              "renouvellement — ni une mise en vente prévisible, ni une "
                              "opportunité qualifiée.")}


@app.get("/map/permits.geojson")
def permits_geojson(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Marqueurs SITADEL (Lot C4) : autorisations d'urbanisme géolocalisées (point = parcelle
    rattachée). Pour la couche « permis » de la carte."""
    rows = db.execute(
        text(
            """SELECT s.permit_id, s.type, s.date, ST_AsGeoJSON(s.geom) AS g
               FROM sitadel_permits s
               WHERE s.geom IS NOT NULL AND (CAST(:c AS text) IS NULL OR s.commune = :c)"""
        ), {"c": commune}
    ).mappings().all()
    feats = [{"type": "Feature", "geometry": json.loads(r["g"]),
              "properties": {"num": r["permit_id"], "type": r["type"],
                             "date": r["date"].date().isoformat() if r["date"] else None}}
             for r in rows if r["g"]]
    return {"type": "FeatureCollection", "features": feats}


def _check_idu(idu: str) -> str:
    """Valide la forme d'un IDU avant tout accès DB : un octet nul ou un caractère de
    contrôle dans le chemin provoquait un 500 (erreur driver) au lieu d'un 404 propre
    (audit O5). Alphanumérique ≤ 20 caractères, sinon 404 — jamais d'erreur serveur."""
    import re as _re

    if not _re.fullmatch(r"[0-9A-Za-z]{1,20}", idu or ""):
        raise HTTPException(404, "Parcelle inconnue")
    return idu


def _build_fiche(db: Session, idu: str, *, with_assistant: bool = True) -> dict:
    _check_idu(idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    ev = _latest_eval(db, p.id)
    lon, lat = db.execute(
        select(func.ST_X(p.__class__.centroid), func.ST_Y(p.__class__.centroid)).where(models.Parcel.id == p.id)
    ).one()

    # M73 §1 (bascule de rail) — md/html lisaient le rail LEGACY `cascade_results`,
    # divergent de la fiche écran (dryrun servi) : d'où « intersection marginale < 10 % » et les
    # niveaux d'aléa côte à côte. Doctrine « le dryrun servi fait foi » : on lit désormais la MÊME
    # cascade servie que _q_v2_fiche, dédupliquée (M46) et arbitrée/libellée (risques_arbitrage).
    # Le rail cascade_results n'alimente plus AUCUN document (déclaré mort, cf. RAPPORT_M73).
    cascade_rows = db.execute(
        text(
            """SELECT cr.layer_name, cr.result, cr.severity, cr.weight_applied, cr.detail,
                      ds.name AS source
               FROM dryrun_cascade_results cr LEFT JOIN data_sources ds ON ds.id = cr.data_source_id
               WHERE cr.run_label = :run AND cr.parcel_id = :pid
               ORDER BY abs(COALESCE(cr.weight_applied, 0)) DESC, cr.layer_name, cr.id"""  # cr.id : tiebreaker déterministe (cf. _q_v2_fiche)
        ), {"pid": p.id, "run": Q_A_RUN_LABEL}
    ).mappings().all()
    from .risques_arbitrage import arbitrer_risques
    _seen: set = set()
    cascade = []
    for r in cascade_rows:
        k = (r["layer_name"], r["result"], r["detail"])
        if k in _seen:
            continue
        _seen.add(k)
        cascade.append(dict(r))
    cascade = arbitrer_risques(cascade)
    reasons = [r for r in cascade if r["result"] in ("HARD_EXCLUDE", "SOFT_FLAG")]

    sources_responded = sorted({r["source"] for r in cascade if r["source"] and r["result"] != "UNKNOWN"})
    sources_silent = sorted({r["source"] for r in cascade if r["source"] and r["result"] == "UNKNOWN"})

    source_results = db.execute(
        text(
            """SELECT ds.name AS source, psr.status, psr.summary, psr.confidence_level
               FROM parcel_source_results psr JOIN data_sources ds ON ds.id = psr.data_source_id
               WHERE psr.parcel_id = :pid ORDER BY psr.fetched_at DESC"""
        ), {"pid": p.id}
    ).mappings().all()

    # Carte de pré-faisabilité (ÉTAPE B) — isolée, ne casse jamais la fiche si indispo.
    try:
        from ..faisabilite.db import fiche_payload
        faisabilite = fiche_payload(db, p.id)
    except Exception:  # noqa: BLE001 - module optionnel, dégrade en silence
        faisabilite = None

    # Bloc PROSPECTION (manuel) : état propriétaire/contact si la parcelle est suivie au pipeline.
    pe = db.execute(
        select(models.PipelineEntry).where(models.PipelineEntry.parcel_id == p.id)
    ).scalar_one_or_none()
    pe_data = (pe.prospection or {}) if pe else {}
    prosp_block = {
        "in_pipeline": bool(pe),
        "entry_id": pe.id if pe else None,
        "pipeline_status": pe.status if pe else None,
        "data": pe_data,
        "statut_label": prospection.statut_label(pe_data.get("statut_proprietaire")),
        "has_manual_contact": prospection.has_manual_contact(pe_data),
        "disclaimer": prospection.disclaimer(),
    }

    # En-tête : verdict + LES DEUX scores (jamais l'opportunité seule).
    # M34 (dette #14, option a) : le statut est la TRADUCTION du tier servi (verdict_servi,
    # point de calcul unique) — le rail cascade legacy ne pilote plus AUCUN verdict. Ses
    # signaux non-francs (accès/pente/surface/bâti partiel) restent des VIGILANCES (resume),
    # ses scores restent informatifs. Constat : qa/m34/M34_P0_CONSTAT.md.
    from ..verdict_servi import verdict_servi
    from .resume import is_micro_opportunite
    vs = verdict_servi(db, idu)
    verdict_block = {
        "status": vs["statut"], "label": vs["label"],
        "tier": vs["tier"], "rang": vs["rang"], "servable": vs["servable"],
        # Badge « bâtie + division possible » (étage 3 du filtre bâti, M28) — nuance, pas
        # un déclassement.
        "badge_division": vs["badge_division"],
        "badge_division_libelle": vs["badge_division_libelle"],
        "motif": vs["motif"], "exception_registre": vs["exception_registre"],
        "source_run": vs["run"],
        "opportunity_score": ev.opportunity_score if ev else None,
        "completeness_score": ev.completeness_score if ev else None,
        "reasons": reasons,
        # Signal non-franc de la cascade legacy — VIGILANCE informative (jamais un verdict).
        "downgrade_reason": next((r["detail"] for r in cascade if r["layer_name"] == "declassement"), None),
        "evaluated_at": ev.evaluated_at if ev else None,
        "rules_version": ev.rules_version if ev else None,
        # Badge d'AFFICHAGE « micro-opportunité » (≤ 500 m²) — nuance promoteur (tiers hauts).
        "micro_opportunite": is_micro_opportunite(vs["statut"], p.surface_m2),
    }
    # Occupation bâtie (correctif R1) — ratio/nb/plus grand bâtiment + label prudent.
    from .. import bati as bati_mod
    bati_block = bati_mod.fiche_block(db, p.id, p.surface_m2)

    # M39 (dette #13) — signal PISCINE matérialisée (couche 90,7 %) pour la vigilance informative :
    # surface piscine + surface parcelle (part de parcelle) + contenance (ratio piscine dans parcelle,
    # centroïde dans). N'affecte ni tier ni verdict. SAVEPOINT (idiome fraicheur.py) : une table
    # absente (base de test) n'avorte pas la TX de fiche.
    _pisc = None
    try:
        with db.begin_nested():
            _row = db.execute(text("""
                SELECT d.surface_m2 AS pool_m2, p.surface_m2 AS parc_m2,
                       ST_Area(ST_Intersection(ST_MakeValid(p.geom_2975), ST_MakeValid(d.geom_2975)))
                         / NULLIF(ST_Area(ST_MakeValid(d.geom_2975)), 0) AS ratio_dans,
                       ST_Contains(ST_MakeValid(p.geom_2975), ST_Centroid(d.geom_2975)) AS centro
                FROM parcels p
                JOIN parcel_equipements pe ON pe.idu = p.idu AND pe.piscine
                JOIN LATERAL (SELECT geom_2975, surface_m2 FROM ortho_detections
                              WHERE idu = p.idu AND type = 'piscine'
                              ORDER BY surface_m2 DESC LIMIT 1) d ON true
                WHERE p.idu = :i"""), {"i": idu}).mappings().first()
        if _row:
            _pisc = {"surface_m2": _row["pool_m2"], "parcel_surface_m2": _row["parc_m2"],
                     "ratio_dans": _row["ratio_dans"], "centroide_dans": _row["centro"]}
    except Exception:  # noqa: BLE001 - bloc additif, jamais bloquant pour la fiche
        _pisc = None

    # Résumé « business » (Phase 2) — dérivé des signaux ci-dessus, repris dans les exports.
    from .resume import build_resume
    resume = build_resume(verdict_block, cascade, faisabilite, prosp_block, bati=bati_block,
                          piscine=_pisc)

    # Assemblage foncier (Phase 5) — voisines adjacentes + drapeau prudent (requête indexée).
    from .voisinage import compute_voisinage
    voisinage = compute_voisinage(db, p.id, p.surface_m2, verdict_block["status"])

    # Autorisations d'urbanisme à proximité (Lot C4) — historique SITADEL < 300 m.
    try:
        from ..ingestion.permits import nearby_permits
        permits = nearby_permits(db, p.id)
    except Exception:  # noqa: BLE001 - n'empêche jamais la fiche
        permits = None

    # M38 — activité de DÉPÔT récente (Sitadel3 date_depot). Informatif seul : redate l'activité
    # sur le dépôt (~9 mois avant l'autorisation), ne touche NI tier NI verdict. None hors couverture.
    try:
        from ..ingestion.permits import depots_recents
        depots = depots_recents(db, p.id)
    except Exception:  # noqa: BLE001 - bloc additif, jamais bloquant pour la fiche
        depots = None

    # Assemblage foncier v1 (Lot C5) — paire contiguë qui débloque le seuil de taille.
    try:
        from .. import assemblage as _asm
        voisinage["assemblage_unlock"] = _asm.parcel_assemblage(db, p.id)
    except Exception:  # noqa: BLE001
        pass

    # LOT 4.1 — Orientations PLH (TCO) pour la commune, avec alignement sur la capacité estimée.
    plh_block = None
    try:
        from .. import plh as plh_mod
        fr = ((faisabilite or {}).get("fourchette") or {})
        rng = fr.get("logements_sous_sol") or fr.get("logements_au_sol") or [0, 0]
        logements_est = rng[1] or None
        plh_block = plh_mod.orientations(p.commune, logements_est)
    except Exception:  # noqa: BLE001 - orientation optionnelle, jamais bloquante
        plh_block = None

    # M-U volet B — le signal de marché servi vient désormais des ACTES (DVF liquidité + Sitadel
    # offre), plus AUCUNE lecture Obsimmo. obsimmo.fiche_block/market_signal ne sont plus servis.
    market_signal_block = None
    try:
        from ..faisabilite.marche_commune import market_signal as _mkt_signal
        market_signal_block = _mkt_signal(db, p.commune)
    except Exception:  # noqa: BLE001 - indicateur marché optionnel, jamais bloquant
        market_signal_block = None

    # LOT 4-B — Marché locatif (carte des loyers DHUP) : loyer €/m² appartement & maison, source ouverte.
    loyers_block = None
    try:
        from .. import loyers as loyers_mod
        loyers_block = loyers_mod.fiche_block(insee=(p.idu or "")[:5], commune=p.commune)
    except Exception:  # noqa: BLE001 - indicateur marché optionnel, jamais bloquant
        loyers_block = None

    # LOT 4-B (structure) — Statut d'occupation (INSEE RP 2022) : part propriétaires / locataires.
    occupation_block = None
    try:
        from .. import occupation as occ_mod
        occupation_block = occ_mod.fiche_block(insee=(p.idu or "")[:5], commune=p.commune)
    except Exception:  # noqa: BLE001 - indicateur structure optionnel, jamais bloquant
        occupation_block = None

    # Phase A-1 — badge « fenêtre de sortie de défiscalisation » (signal additif, maisons/monopropriété).
    # Timing par parcelle, JAMAIS une date de vente ni une personne physique. Table dérivée defisc_fenetres.
    # to_regclass : la table peut ne pas encore être construite (CLI defisc-fenetres) — on vérifie son
    # existence AVANT de la référencer, pour ne jamais aborter la transaction de la fiche.
    defisc_block = None
    try:
        if db.execute(text("SELECT to_regclass('defisc_fenetres')")).scalar() is not None:
            _df = db.execute(text(
                "SELECT achat_neuf_annee, fenetre_debut, fenetre_fin, fenetre_active, statut, "
                "source_libelle, libelle_badge, libelle_court, detail, decote_pct, decote_n, decote_libelle "
                "FROM defisc_fenetres WHERE idu = :i"),
                {"i": p.idu}).mappings().first()
            defisc_block = dict(_df) if _df else None
    except Exception:  # noqa: BLE001 - table additive optionnelle, jamais bloquant
        defisc_block = None

    # Phase A cycle 2 — badge « PC caduc » (signal parcellaire, greffé au bloc permis M10). Faits datés
    # uniquement, JAMAIS le demandeur ni un jugement du propriétaire. Table dérivée pc_caducs (to_regclass).
    pc_caduc_block = None
    try:
        if db.execute(text("SELECT to_regclass('pc_caducs')")).scalar() is not None:
            _pc = db.execute(text(
                "SELECT pc_annee, caduc_depuis, n_pc_octroyes, statut_autorisation, statut_caducite, "
                "libelle_court, detail FROM pc_caducs WHERE idu = :i"), {"i": p.idu}).mappings().first()
            pc_caduc_block = dict(_pc) if _pc else None
    except Exception:  # noqa: BLE001 - table additive optionnelle, jamais bloquant
        pc_caduc_block = None

    # Nuit N1 — SCORE É (marge estimée €). Estimé ; jamais un prix ni une promesse. Table dérivée score_e.
    score_e_block = None
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar() is not None:
            _se = db.execute(text(
                "SELECT estimable, marge_estimee, charge_supportable, prix_probable, niveau_prix, "
                "hypotheses_version, libelle_court, detail FROM score_e WHERE idu = :i"), {"i": p.idu}).mappings().first()
            score_e_block = dict(_se) if _se else None
            if score_e_block and score_e_block.get("estimable"):
                # Exigence Vic (flag levé) : le niveau du prix DOIT être visible côté client (tooltip/détail).
                from ..ingestion.score_e import niveau_label
                score_e_block["niveau_label"] = niveau_label(score_e_block.get("niveau_prix"))
    except Exception:  # noqa: BLE001 - table additive optionnelle, jamais bloquant
        score_e_block = None

    # M71 B1 (audits M66/M66-B) — DPE en INFO FICHE uniquement : le signal scoring
    # dpe_passoire a été retiré (13 DPE utiles pour 431 663 parcelles — l'amont réunionnais
    # authentique ≈ 17, le DPE réglementaire est neuf en DROM). « DPE connu : G, 2023 » si un
    # DPE est rattaché à la parcelle, rien sinon. SAVEPOINT : jamais bloquant pour la fiche.
    dpe_connu_block = None
    try:
        with db.begin_nested():
            _dpe = db.execute(text(
                "SELECT etiquette_dpe, date_etablissement, type_batiment FROM dpe_records "
                "WHERE parcelle_idu = :i AND etiquette_dpe IS NOT NULL "
                "ORDER BY date_etablissement DESC NULLS LAST LIMIT 1"), {"i": idu}).mappings().first()
        if _dpe:
            dpe_connu_block = {
                "etiquette": _dpe["etiquette_dpe"],
                "annee": _dpe["date_etablissement"].year if _dpe["date_etablissement"] else None,
                "type_batiment": _dpe["type_batiment"],
            }
    except Exception:  # noqa: BLE001 - bloc additif, jamais bloquant pour la fiche
        dpe_connu_block = None

    fiche = {
        "parcel": {
            "idu": p.idu, "commune": p.commune, "section": p.section, "numero": p.numero,
            "surface_m2": p.surface_m2, "centroid": {"lon": lon, "lat": lat},
            "adresse": _ban_adresse(db, p.idu),   # M6 2a (§1.8) — meilleure adresse BAN
            "origine": p.origine,  # 'audit' → bandeau « audit à la demande » sur la fiche
        },
        "resume": resume,
        "bati": bati_block,
        "voisinage": voisinage,
        "faisabilite": faisabilite,
        # M40 — source qui fait foi (GPU-vs-mairie) : présent aussi sur le payload par défaut et les
        # exports (md/html), pas seulement la fiche premium. Jamais un zonage servi sans mention.
        "plu_fraicheur": _plu_fraicheur(idu),
        "radar_procedure": _radar_proc(idu, verdict_block["tier"]),   # M41 — radar procédures PLU
        "historique_site": _historique_site(db, idu),      # M42 — « Sur cette parcelle » (permis + caduc)
        "voisinage_proche": _voisinage_proche(db, idu),    # M42 — « Autour, à moins de 100 m »
        "plh": plh_block,   # LOT 4.1 — orientations habitat (PLH TCO)
        "market_signal": market_signal_block,   # M-U — signal marché DVF (actes) + Sitadel (autorisations)
        "loyers": loyers_block,     # LOT 4-B — marché locatif (carte des loyers DHUP)
        "occupation": occupation_block,   # LOT 4-B — statut d'occupation (INSEE RP 2022)
        "defisc_fenetres": defisc_block,  # Phase A-1 — fenêtre de sortie de défisc (badge, mono, Estimé)
        "pc_caduc": pc_caduc_block,       # Phase A cycle 2 — PC caduc probable (badge, greffé bloc permis)
        "score_e": score_e_block,         # Nuit N1 — marge estimée € (Estimé, jamais un prix)
        "dpe_connu": dpe_connu_block,     # M71 B1 — DPE en info fiche SEULE (plus jamais un signal)
        "permits": permits,
        "depots": depots,   # M38 — activité de dépôt (permis aboutis, datés au dépôt) ; informatif
        "prospection": prosp_block,
        # Le bloc « promoteur » (altimétrie/façade/PLU détaillé/réseaux) est servi À PART, en
        # LAZY-LOAD, par GET /parcels/{idu}/enrichment : il fait des appels externes lents
        # (RGE ALTI, prescriptions GPU) qui ne doivent jamais bloquer l'ouverture de la fiche.
        "verdict": verdict_block,
        # M33 — mode B (réhabilitation) : présent aussi sur le payload legacy (exports
        # md/html) — cohérence P2.3 : avec ses étiquettes ou pas du tout.
        "mode_b": _mode_b_block(db, idu, Q_A_RUN_LABEL),
        # M73-D — ANC servi (statut_anc, point unique) sur le payload legacy aussi (premium
        # fpdf) : le critère était absent de _build_fiche. Jamais recalculé, jamais lu depuis zone_anc.
        "anc": _anc_block(db, idu),
        "cascade": cascade,
        "sources_responded": sources_responded,
        "sources_silent": sources_silent,
        "source_results": [dict(r) for r in source_results],
        "ai": ev.ai_payload if ev else None,
        "disclaimer": "Pré-analyse. Constructibilité, propriété, rentabilité, faisabilité jamais garanties.",
    }
    # Synthèse assistant DÉTERMINISTE (règles), dérivée des SEULS faits ci-dessus — alimente l'état
    # premium de l'assistant SANS clé API (jamais d'invention), et sert d'aperçu quand la clé est posée.
    # Calculée seulement pour la fiche affichée ; inutile pour les builds internes (shortlist, compare).
    if with_assistant:
        from .assistant import assistant_facts, rules_summary
        fiche["assistant_rules"] = rules_summary(assistant_facts(fiche))
        # Garde-fou FIABILITÉ (LOT 6) : signale si la commune n'est pas encore au standard Saint-Paul.
        # Information seulement — n'altère aucune donnée, aucun verdict, aucune cascade.
        from .. import communes
        fiche["commune_reliability"] = communes.reliability(p.commune)
    return fiche


@app.get("/parcels/{idu}/enrichment")
def parcel_enrichment(idu: str, db: Session = Depends(get_db)) -> dict:
    """Bloc « promoteur » (altimétrie, façade, PLU détaillé, propriété, réseaux) — LAZY-LOAD.

    Sépare les appels externes LENTS (RGE ALTI ~1,5 s, prescriptions GPU ~2-6 s) de
    l'ouverture de la fiche : calculés UNE FOIS puis mis en cache (parcel_enrichment), et
    chargés en arrière-plan par le front → la fiche s'ouvre immédiatement. Jamais de 500
    (chaque section est isolée par `_safe`)."""
    from .enrichment import enrichment_cached, remonter_le_temps

    _check_idu(idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    lon, lat = db.execute(
        select(func.ST_X(p.__class__.centroid), func.ST_Y(p.__class__.centroid)).where(models.Parcel.id == p.id)
    ).one()
    payload = enrichment_cached(db, p, lon, lat)
    ca = db.execute(text("SELECT computed_at FROM parcel_enrichment WHERE parcel_id = :p"), {"p": p.id}).scalar()
    # M-C (F3) : le cache parcel_enrichment n'a PAS de TTL (le recalcul déclenche des appels
    # externes lents RGE ALTI/GPU → péremption automatique trop coûteuse ; le refresh reste
    # explicite, cf. `enrichment_cached(refresh=True)` / CLI enrich). On EXPOSE donc la fraîcheur :
    # `computed_at` (date du calcul) + `cache_age_jours` (âge dérivé) → le client sait de quand
    # date l'enrichissement servi au lieu de le croire « live ».
    age_jours = (datetime.now(timezone.utc) - ca).days if ca else None
    # 3.B — lien « Remonter le temps » calculé HORS cache (déterministe, jamais périmé).
    return {**payload, "remonter_le_temps": remonter_le_temps(lon, lat),
            "computed_at": ca.isoformat() if ca else None, "cache_age_jours": age_jours}


@app.get("/assistant/status")
def assistant_status() -> dict:
    """3.A — l'assistant IA est-il configuré (clé API présente) ? Pilote l'état du bouton côté UI."""
    from .assistant import is_configured
    return {"configured": is_configured()}


@app.get("/communes/status")
def communes_status() -> dict:
    """LOT 6 — état & FIABILITÉ des 24 communes (garde-fou produit). Lecture seule, depuis la config
    `communes_gold_standard.yaml` : seules les communes au standard Saint-Paul sont « fiables »."""
    from .. import communes
    items = communes.status_list()
    return {"gold_reference": communes.meta().get("gold_reference", "Saint-Paul"),
            "fiables": [x["commune"] for x in items if x["reliable"]],
            "communes": items}


@app.get("/parcels/{idu}/explain")
def parcel_explain(idu: str, db: Session = Depends(get_db)) -> dict:
    """3.A — Assistant : explication en langage naturel de la fiche (API Anthropic).

    Le prompt ne contient QUE les faits structurés de la fiche (anti-hallucination). Sans clé
    API (`ANTHROPIC_API_KEY`), renvoie un message clair — jamais d'erreur 500."""
    from .assistant import explain_parcel
    fiche = _build_fiche(db, idu)
    return explain_parcel(fiche)


@app.get("/parcels/{idu}/export")
def export_fiche(idu: str, format: str = Query("md", pattern="^(md|html)$"),
                 db: Session = Depends(get_db)):
    """Export fiche : Markdown (md) ou HTML détaillé (html). M93 — le one-pager (format
    `onepager`) a été retiré : quatre documents cohérents (dossier/banquier/argumentaire/premium)."""
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from .export import fiche_html, fiche_markdown

    fiche = _build_fiche(db, idu)
    if format == "html":
        return HTMLResponse(fiche_html(fiche))
    return PlainTextResponse(fiche_markdown(fiche), media_type="text/markdown")


@app.get("/parcels/{idu}/spf-letter")
def spf_letter(idu: str, db: Session = Depends(get_db)):
    """Courrier de demande au Service de la Publicité Foncière (Lot C3), pré-rempli avec la
    référence cadastrale publique — voie légale d'identification, aucune donnée nominative."""
    from fastapi.responses import PlainTextResponse

    from ..proprietaire_type import spf_letter as build_letter

    _check_idu(idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    letter = build_letter({"idu": p.idu, "commune": p.commune, "section": p.section,
                           "numero": p.numero, "surface_m2": p.surface_m2})
    return PlainTextResponse(letter, media_type="text/plain; charset=utf-8")


def _compare_row(fiche: dict) -> dict:
    """Résumé COMPARABLE d'une parcelle (Lot D2) — champs alignés pour la vue côte à côte."""
    p, v = fiche["parcel"], fiche["verdict"]
    fa = fiche.get("faisabilite") or {}
    fr = fa.get("fourchette") or {}
    res = fa.get("residuel") or {}
    bilan = fa.get("bilan") or {}
    ca = bilan.get("ca") or {}
    cf = bilan.get("charge_fonciere") or {}
    contraintes = [c for c in fiche["cascade"] if c["result"] in ("HARD_EXCLUDE", "SOFT_FLAG")]
    # M82 — la contrainte MAJEURE explicite (la plus sévère) pour la vue côte à côte : HARD_EXCLUDE
    # d'abord, sinon le 1er SOFT_FLAG (ABF…), sinon rien.
    majeure = next((c["detail"] for c in contraintes if c["result"] == "HARD_EXCLUDE"),
                   next((c["detail"] for c in contraintes if c["result"] == "SOFT_FLAG"), None))
    return {
        "contrainte_majeure": majeure,
        "idu": p["idu"], "commune": p.get("commune"), "section": p.get("section"), "numero": p.get("numero"),
        "surface_m2": round(p["surface_m2"]) if p.get("surface_m2") else None,
        "status": v.get("status"),
        # M54-EXPO-3 A8 — le verdict CLIENT côté front dérive du tier v2 + étage 0 (verdictMeta).
        "tier_v2": v.get("tier_v2"), "etage0": v.get("etage0"), "rang_v2": v.get("rang_v2"),
        "opportunity_score": v.get("opportunity_score"),
        "completeness_score": v.get("completeness_score"),
        "zone": fa.get("zone"), "constructible": fa.get("constructible"),
        "capacite": fa.get("verdict") if fa.get("constructible") else None,
        "sdp_max_m2": fr.get("surface_plancher_m2"),
        "taux_emprise_pct": res.get("taux_emprise_pct") if res.get("disponible") else None,
        "sdp_residuelle_m2": res.get("sdp_residuelle_m2") if res.get("disponible") else None,
        "sous_densite": res.get("sous_densite") if res.get("disponible") else None,
        "ca_bas": ca.get("bas"), "ca_haut": ca.get("haut"),
        "charge_fonciere_m2": cf.get("par_m2_terrain"),
        "n_contraintes": len(contraintes),
        "contraintes": [c["detail"] for c in contraintes[:4]],
        "synthese": (fiche.get("resume") or {}).get("synthese"),
    }


class SavedFilterIn(BaseModel):
    name: str
    params: dict


@app.get("/filters")
def list_filters(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    """Filtres de recherche sauvegardés (Lot D3). CLOISON : chaque compte ne voit que les siens."""
    from .tenant import current_compte
    rows = db.execute(text("SELECT id, name, params, created_at FROM saved_filters"
                           " WHERE compte_id IS NOT DISTINCT FROM :cid ORDER BY created_at DESC"),
                      {"cid": current_compte(request)}).mappings().all()
    return [{"id": r["id"], "name": r["name"], "params": r["params"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None} for r in rows]


@app.post("/filters")
def save_filter(body: SavedFilterIn, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    name = (body.name or "").strip()[:80]
    if not name:
        raise HTTPException(422, "Nom de filtre requis.")
    fid = db.execute(text("INSERT INTO saved_filters (name, params, compte_id) VALUES (:n, CAST(:p AS jsonb), :cid) RETURNING id"),
                     {"n": name, "p": json.dumps(body.params or {}), "cid": current_compte(request)}).scalar()
    return {"id": fid, "name": name, "params": body.params}


@app.delete("/filters/{filter_id}")
def delete_filter(filter_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    # SEC-IDOR : on ne supprime QUE ses propres filtres → 404 sinon
    from .tenant import current_compte
    n = db.execute(text("DELETE FROM saved_filters WHERE id = :i AND compte_id IS NOT DISTINCT FROM :cid"),
                   {"i": filter_id, "cid": current_compte(request)}).rowcount
    if not n:
        raise HTTPException(404, "Filtre inconnu")
    return {"ok": True}


# ── M9 lot 3 — Signalement d'erreur (file de QA HUMAINE, aucune action automatique) ──
# Types d'erreur proposés au formulaire (le back accepte aussi « autre »).
SIGNALEMENT_TYPES = {"zonage", "bati", "adresse", "proprietaire", "risque",
                     "faux_positif", "score", "viabilisation", "autre"}


class SignalementIn(BaseModel):
    idu: str
    type_erreur: str
    champ: str | None = None
    commentaire: str | None = None
    utilisateur: str | None = None


@app.post("/signalements")
def creer_signalement(body: SignalementIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Enregistre un signalement d'erreur horodaté. AUCUNE modification des données :
    c'est un ticket dans une file de QA humaine (utile notamment aux faux positifs —
    piscines 90,7 %, futurs verrous). Le champ `statut` démarre à « nouveau ».
    CLOISON : le signalement appartient au compte qui l'a émis (revue QA transverse = CLI)."""
    from .tenant import current_compte
    idu = (body.idu or "").strip()
    if not idu:
        raise HTTPException(422, "IDU de la parcelle requis.")
    type_err = (body.type_erreur or "").strip().lower()
    if type_err not in SIGNALEMENT_TYPES:
        type_err = "autre"
    sid = db.execute(text(
        """INSERT INTO signalements (parcelle_id, type_erreur, champ, commentaire, utilisateur, compte_id)
           VALUES (:idu, :t, :c, :com, :u, :cid) RETURNING id"""),
        {"idu": idu[:14], "t": type_err,
         "c": (body.champ or None), "com": (body.commentaire or None),
         "u": (body.utilisateur or None), "cid": current_compte(request)}).scalar()
    return {"ok": True, "id": sid, "statut": "nouveau"}


@app.get("/signalements")
def liste_signalements(request: Request, statut: str | None = None,
                       limit: int = Query(500, ge=1, le=5000),
                       db: Session = Depends(get_db)) -> list[dict]:
    """File des signalements (revue QA). Filtrable par statut. CLOISON : ses propres signalements."""
    from .tenant import current_compte
    where = " AND statut = :s" if statut else ""
    rows = db.execute(text(
        f"""SELECT id, parcelle_id, type_erreur, champ, commentaire, utilisateur,
                   statut, created_at
              FROM signalements WHERE compte_id IS NOT DISTINCT FROM :cid{where}
              ORDER BY created_at DESC LIMIT :lim"""),
        {"s": statut, "lim": limit, "cid": current_compte(request)}).mappings().all()
    return [{**dict(r), "created_at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in rows]


@app.get("/signalements/export.csv")
def export_signalements_csv(request: Request, statut: str | None = None,
                            db: Session = Depends(get_db)) -> Response:
    """Export CSV des signalements pour revue (utf-8-sig BOM + séparateur « ; »). CLOISON par compte."""
    import csv as _csv
    import io as _io

    from .tenant import current_compte
    where = " AND statut = :s" if statut else ""
    rows = db.execute(text(
        f"""SELECT id, parcelle_id, type_erreur, champ, commentaire, utilisateur,
                   statut, created_at
              FROM signalements WHERE compte_id IS NOT DISTINCT FROM :cid{where}
              ORDER BY created_at DESC"""),
        {"s": statut, "cid": current_compte(request)}).mappings().all()
    buf = _io.StringIO()
    w = _csv.writer(buf, delimiter=";")
    w.writerow(["id", "idu", "type_erreur", "champ", "commentaire",
                "utilisateur", "statut", "date"])
    for r in rows:
        w.writerow([r["id"], r["parcelle_id"], r["type_erreur"], r["champ"] or "",
                    (r["commentaire"] or "").replace("\n", " "), r["utilisateur"] or "",
                    r["statut"], r["created_at"].isoformat() if r["created_at"] else ""])
    return Response(buf.getvalue().encode("utf-8-sig"),
                    media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="labuse_signalements.csv"',
                             "X-Rows": str(len(rows))})


class BilanParamIn(BaseModel):
    secteur: str
    param: str
    value: float | None = None   # None → réinitialise au défaut


@app.get("/bilan/calculette-defaults")
def get_calculette_defaults() -> dict:
    """M-Q P1-16 — défauts d'hypothèses de la calculette (coût de construction, marge & frais),
    DÉRIVÉS de la source unique (`hypotheses_faisabilite` du YAML → CALCULETTE_COUT_DEFAUT_M2 /
    CALCULETTE_MARGE_FRAIS_DEFAUT_PCT). Point unique servi au front : la calculette n'embarque plus
    sa propre constante (2500 gravé en React) qui divergeait du serveur (2550). Ainsi calculette,
    Dossier banquier et Note de financement portent le MÊME coût par défaut sur la même parcelle."""
    from ..faisabilite.bilan import CALCULETTE_COUT_DEFAUT_M2, CALCULETTE_MARGE_FRAIS_DEFAUT_PCT
    return {"cout_construction_m2": CALCULETTE_COUT_DEFAUT_M2,
            "marge_frais_pct": CALCULETTE_MARGE_FRAIS_DEFAUT_PCT}


@app.get("/bilan/params")
def get_bilan_params(secteur: str = Query("*"), db: Session = Depends(get_db)) -> dict:
    """Paramètres du bilan (1.C) résolus pour un secteur (registre + overrides + non calibrés)."""
    from ..faisabilite import bilan_params as bp
    resolved = bp.resolve(db, secteur)
    return {"secteur": secteur,
            "params": [{**p, **resolved.get(p["key"], {})} for p in bp.registry()],
            "non_calibres_critiques": bp.uncalibrated_critical(resolved)}


@app.post("/bilan/params")
def set_bilan_param(body: BilanParamIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Calibre (ou réinitialise) un paramètre du bilan pour un secteur (1.C — Vic calibre).
    GATE ADMIN (M-K P1-10) : ces paramètres sont SERVIS À TOUS ; seul un admin les réécrit
    (sans le gate, n'importe quel client payant réécrivait le bilan de tout le monde)."""
    from . import auth
    auth.exiger_admin(request)
    from ..faisabilite import bilan_params as bp
    try:
        bp.save(db, body.secteur.strip() or "*", body.param, body.value)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"ok": True, "secteur": body.secteur, "param": body.param, "value": body.value}


@app.get("/compare")
def compare(idus: str = Query(..., description="2 à 3 IDU séparés par des virgules"),
            db: Session = Depends(get_db)) -> dict:
    """Comparateur de parcelles (Lot D2) : 2-3 parcelles côte à côte (verdict, capacité,
    résiduel, bilan, contraintes). Ignore silencieusement un IDU introuvable."""
    ids = [x.strip() for x in idus.split(",") if x.strip()][:3]
    from ..faisabilite.marche_commune import build_marche_commune
    out: list[dict] = []
    marche_cache: dict[str, dict] = {}
    for idu in ids:
        try:
            row = _compare_row(_build_fiche(db, idu, with_assistant=False))
        except HTTPException:
            continue
        # M82 — prix terrain nu PAR ZONE (point de calcul M79 unique, comme la fiche et l'outil Marché).
        commune, zone = row.get("commune"), (row.get("zone") or "")
        fam = "AU" if zone.upper().startswith("AU") else (zone[:1].upper() if zone else "")
        if commune and fam in ("U", "AU"):
            if commune not in marche_cache:
                try:
                    marche_cache[commune] = build_marche_commune(db, commune)
                except Exception:  # noqa: BLE001
                    marche_cache[commune] = {}
            for l in (marche_cache[commune].get("lignes") or []):
                if isinstance(l, dict) and l.get("cle") == "prix_terrain_nu_par_zone":
                    pz = ((l.get("valeurs") or {}).get("par_zone") or {}).get(fam)
                    if pz and pz.get("calculable"):
                        row["terrain_zone_eur_m2"] = pz.get("median_eur_m2")
                    break
        out.append(row)
    return {"count": len(out), "parcels": out}


@app.post("/parcels/{idu}/evaluate")
def evaluate_one(idu: str, request: Request, ai: bool = Query(False), db: Session = Depends(get_db)) -> dict:
    """Re-score + PERSISTE une parcelle (rail ops/admin legacy). GATE ADMIN (M-K P2-35) :
    écrivain lourd (DELETE+INSERT cascade, appel IA optionnel), aucun appelant front — réservé
    à l'admin plutôt que retiré (encore utilisé en ops/QA)."""
    from ..ai import get_provider
    from ..cascade import evaluate_parcels
    from . import auth

    auth.exiger_admin(request)
    _check_idu(idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    provider = get_provider() if ai else None
    out = evaluate_parcels([p.id], db, persist=True, ai_provider=provider)[0]
    return {
        "idu": out.idu, "status": out.status,
        "opportunity_score": out.opportunity.score,
        "completeness_score": out.completeness.score,
        "promoted": out.promoted,
    }


# ───────────────────────────── Audit pull (Lot A) ─────────────────────────────

class AuditRefIn(BaseModel):
    section: str
    numero: str
    code_insee: str | None = None


class AuditAddressIn(BaseModel):
    q: str


class AuditPolygonIn(BaseModel):
    geometry: dict


@app.post("/audit/reference")
def audit_reference(body: AuditRefIn, db: Session = Depends(get_db)) -> dict:
    """Auditer un terrain par référence cadastrale (section + numéro). Fetch cadastre à la
    volée → ingestion (origine='audit') → cascade → renvoie l'idu pour ouvrir la fiche."""
    from .. import audit
    return audit.audit_by_reference(db, body.section, body.numero, body.code_insee)


@app.post("/audit/adresse")
def audit_adresse(body: AuditAddressIn, db: Session = Depends(get_db)) -> dict:
    """Auditer un terrain par adresse (géocodage BAN → parcelle cadastrale)."""
    from .. import audit
    return audit.audit_by_address(db, body.q)


@app.post("/audit/polygone")
def audit_polygone(body: AuditPolygonIn, db: Session = Depends(get_db)) -> dict:
    """Auditer un terrain par polygone dessiné sur la carte."""
    from .. import audit
    return audit.audit_by_polygon(db, body.geometry)


# ───────────────────────────── Découverte (offre B) ─────────────────────────────

# M30 théâtre : /discover SUPPRIMÉ — endpoint orphelin (remplacé par /parcels + /stats
# depuis M5.1, plus aucun appelant front ni QA).
# M49 (Lot A) : GET /signals RETIRÉ — vestige de l'offre C (parcel_signals), 0 caller prouvé
# (front `signals` = vestige retiré filters.ts ; 0 hit frontend/qa/scripts ; seul test_api l'exerçait).

# ───────────────────────── Alertes intelligentes (3.C) ─────────────────────────
# Scope défini par l'utilisateur (zones de veille + parcelles suivies) → « nouveautés ».

class WatchZoneIn(BaseModel):
    name: str
    geometry: dict           # polygone GeoJSON (EPSG:4326)
    commune: str | None = None


class WatchZoneRenameIn(BaseModel):
    name: str


class AlerteAckIn(BaseModel):
    id: int | None = None    # None → accuse réception de toutes les nouveautés de la commune
    commune: str | None = None


@app.get("/watch-zones")
def watch_zones_list(request: Request, commune: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Zones de veille du compte connecté (cloison M-K : jamais celles d'un autre compte)."""
    from .. import alertes
    from .tenant import current_compte
    commune = commune or config.get_settings().pilot_commune_name
    return alertes.list_watch_zones(db, commune, current_compte(request))


@app.post("/watch-zones")
def watch_zones_create(body: WatchZoneIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Crée une zone de veille (polygone dessiné). Détecte aussitôt les nouveautés du scope."""
    from .. import alertes
    from .tenant import current_compte
    if (body.geometry or {}).get("type") != "Polygon":
        raise HTTPException(422, "geometry doit être un Polygon GeoJSON")
    cid = current_compte(request)
    commune = body.commune or config.get_settings().pilot_commune_name
    zone = alertes.create_watch_zone(db, body.name, commune, body.geometry, cid)
    counts = alertes.compute_alertes(db, commune, cid)
    return {"zone": zone, "detected": counts}


@app.patch("/watch-zones/{zone_id}")
def watch_zones_rename(zone_id: int, body: WatchZoneRenameIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """M54-EXPO-3 — renomme une zone de veille du compte. SEC-IDOR : 404 si pas au compte."""
    from .. import alertes
    from .tenant import current_compte
    if not alertes.rename_watch_zone(db, zone_id, body.name, current_compte(request)):
        raise HTTPException(404, "Zone de veille inconnue")
    return {"ok": True, "name": body.name.strip()[:120]}


@app.delete("/watch-zones/{zone_id}")
def watch_zones_delete(zone_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Supprime une zone de veille du compte (et ses alertes, par cascade). SEC-IDOR : 404 si
    la zone n'est pas au compte connecté."""
    from .. import alertes
    from .tenant import current_compte
    if not alertes.delete_watch_zone(db, zone_id, current_compte(request)):
        raise HTTPException(404, "Zone de veille inconnue")
    return {"ok": True}


@app.get("/alertes")
def alertes_list(request: Request, commune: str | None = None, only_new: bool = False,
                 limit: int = Query(100, ge=0, le=1000), db: Session = Depends(get_db)) -> list[dict]:
    """Liste des « nouveautés » DU COMPTE : ventes DVF en zone de veille + permis près d'une parcelle suivie."""
    from .. import alertes
    from .tenant import current_compte
    commune = commune or config.get_settings().pilot_commune_name
    return alertes.list_alertes(db, commune, current_compte(request), only_new=only_new, limit=limit)


@app.post("/alertes/refresh")
def alertes_refresh(request: Request, commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Re-détecte les nouveautés du scope du compte au rafraîchissement des données (idempotent)."""
    from .. import alertes
    from .tenant import current_compte
    commune = commune or config.get_settings().pilot_commune_name
    return alertes.compute_alertes(db, commune, current_compte(request))


@app.post("/alertes/ack")
def alertes_ack(body: AlerteAckIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Marque une nouveauté du compte (ou toutes celles de la commune) comme lue. SEC-IDOR."""
    from .. import alertes
    from .tenant import current_compte
    commune = body.commune or config.get_settings().pilot_commune_name
    n = alertes.acknowledge(db, current_compte(request), alerte_id=body.id, commune=commune)
    return {"ok": True, "acknowledged": n}


# ───────────────────────────── Feedback (§10) ─────────────────────────────

class FeedbackIn(BaseModel):
    idu: str
    verdict: FeedbackVerdict
    user_id: str | None = None
    comment: str | None = None


@app.post("/feedback")
def post_feedback(body: FeedbackIn, db: Session = Depends(get_db)) -> dict:
    _check_idu(body.idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == body.idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    fb = models.ParcelFeedback(parcel_id=p.id, verdict=body.verdict, user_id=body.user_id, comment=body.comment)
    db.add(fb)
    db.flush()
    return {"ok": True, "id": fb.id}


# ───────────────────────────── Pipeline de prospection (Kanban, T1) ─────────────────────────────

def _pipeline_cfg() -> dict:
    return config.pipeline()


def _prio_keys() -> list[str]:
    return [p["key"] for p in _pipeline_cfg().get("priorities", [])]


def _entry_dict(db: Session, e: models.PipelineEntry) -> dict:
    p = e.parcel
    ev = _latest_eval(db, e.parcel_id)
    # M34 (dette #14) : le verdict des cartes CRM = traduction du tier servi (le front
    # affiche déjà `premium` via verdictMeta — ce bloc API raconte désormais le même run).
    from ..verdict_servi import verdict_servi
    vs = verdict_servi(db, p.idu)
    return {
        "id": e.id,
        "idu": p.idu,
        "status": e.status,
        "priority": e.priority,
        "notes": e.notes or "",
        "reminder_date": e.reminder_date.isoformat() if e.reminder_date else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "prospection": e.prospection or {},
        "proprietaire_label": prospection.statut_label((e.prospection or {}).get("statut_proprietaire")),
        "has_manual_contact": prospection.has_manual_contact(e.prospection),
        "parcel": {"commune": p.commune, "section": p.section, "surface_m2": p.surface_m2,
                   # M6 2a (§1.8) : l'adresse BAN sur les cartes CRM (pipeline = volume faible)
                   "adresse": _ban_adresse(db, p.idu)},
        "verdict": {
            "status": vs["statut"], "label": vs["label"], "rang": vs["rang"],
            "opportunity_score": ev.opportunity_score if ev else None,
        },
        # scoring premium v2 (source de vérité affichage Socle V1) — pour les cartes Kanban
        "premium": _premium_head(db, e.parcel_id),
        # d'où vient la piste (copilote-projet) — None si ajoutée hors projet
        "projet": _projet_ref(db, e.projet_id),
        # contact proprio (PRIVACY : personne morale publique seulement, jamais un particulier)
        "proprietaire_public": _proprietaire_public(db, p.idu),
    }


def _projet_ref(db: Session, projet_id: int | None) -> dict | None:
    if projet_id is None:
        return None
    pr = db.get(models.Projet, projet_id)
    return {"id": pr.id, "nom": pr.nom} if pr else None


def _proprietaire_public(db: Session, idu: str) -> dict:
    """Contact propriétaire pour le CRM — PRIVACY (ligne rouge) : `parcelle_personne_morale` ne
    contient QUE des personnes morales (DGFiP public). Présent → dénomination + SIREN affichables ;
    absent → propriétaire PARTICULIER, AUCUNE identité exposée (jamais nommé)."""
    pm = db.execute(text(
        "SELECT denomination, siren, groupe_label FROM parcelle_personne_morale WHERE idu = :i"),
        {"i": idu}).mappings().first()
    if pm and pm["denomination"]:
        return {"type": "personne_morale", "denomination": pm["denomination"],
                "siren": pm["siren"], "groupe": pm["groupe_label"]}
    return {"type": "particulier"}    # aucune identité — non communiqué


def _premium_head(db: Session, parcel_id: int, run_label: str = Q_A_RUN_LABEL) -> dict | None:
    r = db.execute(text(
        "SELECT d.status AS status, d.completeness_score, "  # M129-B : matrice morte
        "       (d.status IN ('exclue', 'faux_positif_probable')) AS etage0, "
        "       s2.tier AS tier_v2, s2.rang AS rang_v2 "
        "FROM dryrun_parcel_evaluations d "
        "LEFT JOIN parcels p ON p.id = d.parcel_id "
        "LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run "
        "WHERE d.run_label = :run AND d.parcel_id = :pid"),
        {"run": run_label, "pid": parcel_id, "v2run": _score_v2_run_id(db)}).mappings().first()
    return ({"statut": r["status"],  # M129-B : matrice morte → statut cascade
             "completeness_score": r["completeness_score"], "etage0": bool(r["etage0"]),
             "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"]} if r else None)


class PipelineAddIn(BaseModel):
    idu: str
    status: str | None = None
    priority: str | None = None
    notes: str | None = None
    prospection: dict | None = None      # saisie MANUELLE (statut propriétaire, contact…)
    projet_id: int | None = None         # référence du projet d'où vient la piste (copilote-projet)


class PipelinePatchIn(BaseModel):
    status: str | None = None
    priority: str | None = None
    notes: str | None = None
    reminder_date: str | None = None     # "YYYY-MM-DD" = définir ; "" = effacer ; absent = inchangé
    prospection: dict | None = None      # patch partiel validé (merge dans l'existant)


@app.get("/pipeline/meta")
def pipeline_meta(request: Request, db: Session = Depends(get_db)) -> dict:
    """Colonnes (PAR TENANT en base, M12 LOT H) + priorités (config) pour piloter le Kanban.
    Les colonnes sont semées au kanban LABUSE par défaut au premier accès d'un compte."""
    from . import crm_columns
    from .tenant import current_compte
    cfg = _pipeline_cfg()
    cid = current_compte(request)
    cols = crm_columns.columns_for(db, cid)
    dfl = dict(cfg.get("defaults", {}))
    dfl["status"] = crm_columns.default_status(db, cid)
    return {"columns": [{"key": c["key"], "label": c["label"], "tone": c["tone"], "id": c["id"]}
                        for c in cols],
            "priorities": cfg.get("priorities", []), "defaults": dfl}


@app.get("/pipeline")
def pipeline_list(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    from .tenant import current_compte
    cid = current_compte(request)
    q = select(models.PipelineEntry).order_by(models.PipelineEntry.created_at.desc())
    q = q.where(models.PipelineEntry.compte_id.is_(None) if cid is None
                else models.PipelineEntry.compte_id == cid)   # SEC-IDOR
    entries = db.execute(q).scalars().all()
    return [_entry_dict(db, e) for e in entries]


@app.get("/pipeline/parcel/{idu}")
def pipeline_for_parcel(idu: str, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    _check_idu(idu)
    cid = current_compte(request)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    q = select(models.PipelineEntry).where(models.PipelineEntry.parcel_id == p.id)
    q = q.where(models.PipelineEntry.compte_id.is_(None) if cid is None
                else models.PipelineEntry.compte_id == cid)   # SEC-IDOR
    e = db.execute(q).scalar_one_or_none()
    return {"in_pipeline": bool(e), "entry": _entry_dict(db, e) if e else None}


@app.post("/pipeline")
def pipeline_add(body: PipelineAddIn, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    _check_idu(body.idu)
    cid = current_compte(request)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == body.idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    _ex = select(models.PipelineEntry).where(models.PipelineEntry.parcel_id == p.id)
    _ex = _ex.where(models.PipelineEntry.compte_id.is_(None) if cid is None
                    else models.PipelineEntry.compte_id == cid)   # SEC-IDOR
    existing = db.execute(_ex).scalar_one_or_none()
    if existing:                                            # déjà suivie → on renvoie son état courant
        return {"ok": True, "already": True, "entry": _entry_dict(db, existing)}

    from . import crm_columns
    dfl = _pipeline_cfg().get("defaults", {})
    status = body.status or crm_columns.default_status(db, cid)
    priority = body.priority or dfl.get("priority", "moyenne")
    if status not in crm_columns.col_keys(db, cid):     # colonnes PAR TENANT (M12 LOT H)
        raise HTTPException(422, f"Statut invalide : {status}")
    if priority not in _prio_keys():
        raise HTTPException(422, f"Priorité invalide : {priority}")
    try:
        prosp = prospection.merge_prospection(prospection.default_prospection(), body.prospection)
    except ValueError as exc:
        raise HTTPException(422, f"Prospection invalide : {exc}") from None
    projet_id = None
    if body.projet_id is not None:
        # SEC-IDOR : on ne rattache qu'à un projet DU compte (sinon 404)
        _pr = db.get(models.Projet, body.projet_id)
        if not _pr or (_pr.compte_id or None) != (cid or None):
            raise HTTPException(404, "Projet inconnu")
        projet_id = body.projet_id
    e = models.PipelineEntry(parcel_id=p.id, status=status, priority=priority, compte_id=cid,
                             notes=(body.notes or ""), prospection=prosp, projet_id=projet_id)
    db.add(e)
    db.flush()
    return {"ok": True, "already": False, "entry": _entry_dict(db, e)}


@app.patch("/pipeline/{entry_id}")
def pipeline_patch(entry_id: int, body: PipelinePatchIn, request: Request, db: Session = Depends(get_db)) -> dict:
    from . import crm_columns
    from .tenant import current_compte
    cid = current_compte(request)
    e = db.get(models.PipelineEntry, entry_id)
    if not e or (e.compte_id or None) != (cid or None):   # SEC-IDOR
        raise HTTPException(404, "Entrée de pipeline inconnue")
    if body.status is not None:
        if body.status not in crm_columns.col_keys(db, cid):   # colonnes PAR TENANT (M12 LOT H)
            raise HTTPException(422, f"Statut invalide : {body.status}")
        e.status = body.status
    if body.priority is not None:
        if body.priority not in _prio_keys():
            raise HTTPException(422, f"Priorité invalide : {body.priority}")
        e.priority = body.priority
    if body.notes is not None:
        e.notes = body.notes
    if body.reminder_date is not None:
        rd = body.reminder_date.strip()
        if rd == "":
            e.reminder_date = None
        else:
            try:
                e.reminder_date = date.fromisoformat(rd)
            except ValueError:
                raise HTTPException(422, "Date de rappel invalide (attendu YYYY-MM-DD).") from None
    if body.prospection is not None:
        try:
            e.prospection = prospection.merge_prospection(e.prospection, body.prospection)
        except ValueError as exc:
            raise HTTPException(422, f"Prospection invalide : {exc}") from None
    db.flush()
    return {"ok": True, "entry": _entry_dict(db, e)}


@app.delete("/pipeline/{entry_id}")
def pipeline_delete(entry_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    e = db.get(models.PipelineEntry, entry_id)
    if not e or (e.compte_id or None) != (current_compte(request) or None):   # SEC-IDOR
        raise HTTPException(404, "Entrée de pipeline inconnue")
    db.delete(e)
    db.flush()
    return {"ok": True}


# ───────────────────────────── Front statique (carte + dashboard + fiche §8) ─────────────────────────────

# ── Modules outils (Vague 1+) ──
from .courrier import router as _courrier_router  # noqa: E402
from .dossier import router as _dossier_router  # noqa: E402
from .events import router as _events_router  # noqa: E402
from .ia import router as _ia_router  # noqa: E402
from .modules import router as _modules_router  # noqa: E402
from .moteurs import router as _moteurs_router  # noqa: E402
from .partners import router as _partners_router  # noqa: E402
from .pre_dossier import router as _pre_dossier_router  # noqa: E402
from .banquier import router as _banquier_router  # noqa: E402  (O1 — dossier banquier PDF)
from .lettre_zonage import router as _lettre_zonage_router  # noqa: E402  (M22-B — lettre de zonage PDF)
from .scoreur import router as _scoreur_router  # noqa: E402  (O2 — scoreur d'adresse inversé)
from .anti_fiche import router as _anti_fiche_router  # noqa: E402  (O3 — anti-fiche « pourquoi pas »)
from .traducteur import router as _traducteur_router  # noqa: E402  (O4 — traducteur de règlement PLU)
from .servitudes import router as _servitudes_router  # noqa: E402  (O5 — servitudes invisibles)
from .comparateur import router as _comparateur_router  # noqa: E402  (O6 — comparateur de communes)
from .carnet import router as _carnet_router  # noqa: E402  (O7 — carnet de secteur)
from .argumentaire import router as _argumentaire_router  # noqa: E402  (M22-C — argumentaire de négociation PDF)
from .onboarding import router as _onboarding_router  # noqa: E402  (PREMIER EURO — onboarding + légal + webhook)
from .rarete import router as _rarete_router  # noqa: E402  (O9 — pipeline de rareté)
from .ops import router as _ops_router  # noqa: E402  (P4 — /healthz/crons)
from .projets import router as _projets_router  # noqa: E402
from .protection import router as _protection_router  # noqa: E402
from .ortho import router as _ortho_router  # noqa: E402
from .tiles import router as _tiles_router  # noqa: E402
from .score_v2 import router as _score_v2_router  # noqa: E402  (M5, additif)
from .fiche_ask import router as _fiche_ask_router  # noqa: E402  (M11 surface A — barre de fiche)
from .crm_columns import router as _crm_columns_router  # noqa: E402  (M12 LOT H — CRM personnalisable)
from .copilote import router as _copilote_router  # noqa: E402  (M26-A — Copilote, socle agentique)
from .copilote_v2 import router as _copilote_v2_router  # noqa: E402  (M78 — Copilote v2 : routeur + outils)
from .accueil import router as _accueil_router  # noqa: E402  (M55-D stage 9 — chiffres de l'accueil)

app.include_router(_crm_columns_router)
app.include_router(_copilote_router)
app.include_router(_copilote_v2_router)
app.include_router(_accueil_router)
app.include_router(_fiche_ask_router)
app.include_router(_score_v2_router)
app.include_router(_modules_router)
app.include_router(_courrier_router)
app.include_router(_dossier_router)
app.include_router(_pre_dossier_router)
app.include_router(_banquier_router)
app.include_router(_lettre_zonage_router)
app.include_router(_scoreur_router)
app.include_router(_anti_fiche_router)
app.include_router(_traducteur_router)
app.include_router(_servitudes_router)
app.include_router(_comparateur_router)
app.include_router(_carnet_router)
app.include_router(_argumentaire_router)
app.include_router(_onboarding_router)
app.include_router(_rarete_router)
app.include_router(_ops_router)
app.include_router(_protection_router)
app.include_router(_tiles_router)
app.include_router(_ia_router)
app.include_router(_events_router)
app.include_router(_moteurs_router)
app.include_router(_partners_router)
app.include_router(_projets_router)
app.include_router(_ortho_router)


# (les ensure_tables des routeurs sont appelés dans _lifespan — un @app.on_event("startup")
#  serait IGNORÉ par FastAPI quand un lifespan est fourni ; l'ancien bloc était mort.)


#: Socle V1 (front React+MapLibre, build Vite → frontend/dist), servi à la même origine.
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


@app.middleware("http")
async def _no_cache_html(request: Request, call_next):
    """Le HTML du Socle ne doit JAMAIS être mis en cache : un index.html périmé pointe vers un
    vieux bundle → écrans cassés après déploiement (bug constaté). Les assets hashés restent cacheables."""
    resp = await call_next(request)
    if request.url.path.rstrip("/") in ("", "/socle") or request.url.path.endswith(".html"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

# B2 (BLOC B) : le mount statique du proto Vue « /app » est retiré — code archivé sous le
# tag `archive/proto-vue`, le 301 /app → / de la prod reste dans Caddy.


@app.get("/", include_in_schema=False)
def _root() -> RedirectResponse:
    if FRONTEND_DIST.exists():
        return RedirectResponse("/socle/")
    return RedirectResponse("/docs")


if FRONTEND_DIST.exists():
    app.mount("/socle", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="socle")  # Socle V1
