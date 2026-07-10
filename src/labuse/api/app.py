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
import threading
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import config, models, prospection
from ..db import session_scope
from ..enums import FeedbackVerdict
from ..scoring.score_v_constants import Q_A_RUN_LABEL, V_BAND_LABELS, V_BRULANTE_THRESHOLD

WEB_DIR = Path(__file__).resolve().parent / "web"

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
    try:
        from ..db import engine as _engine
        models.ensure_schema(_engine())
        # tables des routeurs (modules/ia/events/partners/projets) : l'ancien
        # @app.on_event("startup") était MORT depuis le passage au lifespan (FastAPI
        # ignore on_event quand lifespan est fourni) — les ensures vivent ICI.
        from .events import ensure_tables as _events_ens
        from .ia import ensure_tables as _ia_ens
        from .modules import ensure_tables as _modules_ens
        from .partners import ensure_tables as _partners_ens
        from .projets import ensure_tables as _projets_ens
        from .protection import ensure_tables as _protection_ens
        from .segments import ensure_tables as _segments_ens
        for _ens in (_modules_ens, _ia_ens, _events_ens, _partners_ens, _projets_ens,
                     _segments_ens, _protection_ens):
            _ens(_engine())
        app.state.schema_heal = "ok"
    except Exception as exc:  # noqa: BLE001 — l'app doit démarrer ; /readyz dira la vérité
        app.state.schema_heal = f"échec : {type(exc).__name__}: {exc}"
    from . import auth
    s = config.get_settings()
    log.info("LA BUSE démarrée · env=%s · auth=%s · schéma=%s",
             s.env,
             "active" if auth.enabled() else "désactivée (local)",
             app.state.schema_heal)
    if auth.enabled() and not auth.configured():
        log.error("env=%s sans LABUSE_AUTH_PASSWORD : routes métier en 503 (fail-closed) "
                  "jusqu'à configuration.", s.env)
    if auth.enabled() and not s.secret_key:
        log.warning("LABUSE_SECRET_KEY absente : clé de session éphémère "
                    "(les sessions ne survivront pas à un redémarrage).")
    yield


app = FastAPI(
    title="LA BUSE — radar foncier",
    version="0.1.0",
    description="La donnée publique ne suffit pas. LA BUSE l'interprète. "
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
    if not auth.enabled() or auth.is_public(path):
        return await call_next(request)
    if auth.token_ok(request.cookies.get(auth.COOKIE)):
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
    return {"status": "ok", "produit": "LA BUSE"}


@app.get("/healthz")
def healthz() -> dict:
    """Niveau 1 — le PROCESS répond. Zéro accès DB : ne dit RIEN de l'état des données
    (c'est /readyz et /demo-status qui le disent — ne jamais confondre)."""
    return {"status": "ok"}


# ───────────────────────────── Connexion pilote ─────────────────────────────

@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    from fastapi.responses import HTMLResponse

    from . import auth

    if not auth.enabled():                       # auth désactivée (local) → rien à demander
        return RedirectResponse("/app/", status_code=302)
    if auth.token_ok(request.cookies.get(auth.COOKIE)):
        return RedirectResponse("/app/", status_code=302)
    return HTMLResponse(auth.login_page())


@app.post("/login", include_in_schema=False)
async def login_submit(request: Request):
    """Connexion : formulaire urlencodé (parse stdlib — zéro dépendance) ou JSON.
    Échec → message NEUTRE + petit délai (anti force-brute) + journalisation."""
    from urllib.parse import parse_qs

    from fastapi.responses import HTMLResponse

    from . import auth

    body = await request.body()
    password = ""
    ctype = request.headers.get("content-type", "")
    if "json" in ctype:
        try:
            password = str(json.loads(body or b"{}").get("password") or "")
        except ValueError:
            password = ""
    else:
        password = (parse_qs(body.decode("utf-8", "replace")).get("password") or [""])[0]

    if not auth.configured() or not auth.password_ok(password):
        auth.log_event("login_failed", request)
        auth.slow_failure()
        return HTMLResponse(auth.login_page(error=True), status_code=401)
    auth.log_event("login_ok", request)
    resp = RedirectResponse("/app/", status_code=303)
    resp.set_cookie(value=auth.make_token(), **auth.cookie_kwargs())
    return resp


@app.get("/logout", include_in_schema=False)
def logout(request: Request):
    from . import auth

    auth.log_event("logout", request)
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


def clear_mem_cache() -> None:
    """Vide le cache mémoire des endpoints (tests / invalidation manuelle)."""
    with _MEM_LOCK:
        _MEM_CACHE.clear()


def _mem_cached(key, ttl: float, compute):
    """Renvoie compute() en le mémorisant `ttl` s sous `key` (lecture seule, en mémoire)."""
    now = time.monotonic()
    with _MEM_LOCK:
        hit = _MEM_CACHE.get(key)
        if hit is not None and (now - hit[0]) < ttl:
            return hit[1]
    val = compute()
    with _MEM_LOCK:
        _MEM_CACHE[key] = (time.monotonic(), val)
        if len(_MEM_CACHE) > _MEM_MAX:                       # éviction simple des plus anciens
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

@app.get("/sources")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(models.DataSource).order_by(models.DataSource.category, models.DataSource.name)).scalars().all()
    return [
        {
            "id": s.id, "name": s.name, "category": s.category, "provider": s.provider,
            "access_type": s.access_type,
            "status": s.status.value if s.status else None,
            "reliability_level": s.reliability_level.value if s.reliability_level else None,
            "rate_limit": s.rate_limit, "last_sync_at": s.last_sync_at,
            "documentation_url": s.documentation_url, "endpoint_url": s.endpoint_url,
            "legal_notes": s.legal_notes, "technical_notes": s.technical_notes,
            "testable": s.name in _connector_names(),
        }
        for s in rows
    ]


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


def _q_v2_where(run_label: str, statuts: str | None, score_min: int | None,
                surface_min: int | None, surface_max: int | None, sdp_min: int | None,
                evenement: bool, vue_mer: bool, flags: str | None,
                communes: str | None = None, flags_exclus: str | None = None,
                v_bands: str | None = None, v_signal: str | None = None,
                brulantes: bool = False) -> tuple[str, dict]:
    """Fragment WHERE partagé liste/stats — les MÊMES filtres que les chips du front. Mode
    « Toute l'île » : le client ne détient plus les 431k features en mémoire, le serveur
    filtre en SQL (chiffres SQL-exacts, mêmes clés que matchScope côté front)."""
    conds: list[str] = []
    params: dict = {"runf": run_label}
    if communes:   # secteurs du copilote cadreur (R2) : plusieurs communes à la fois
        conds.append("p.commune = ANY(:f_communes)")
        params["f_communes"] = [c.strip() for c in communes.split(",") if c.strip()]
    if statuts:
        conds.append("d.matrice_statut = ANY(:f_statuts)")
        params["f_statuts"] = [s.strip() for s in statuts.split(",") if s.strip()]
    if score_min is not None:
        conds.append("d.q_score >= :f_score")
        params["f_score"] = score_min
    if surface_min is not None:
        conds.append("p.surface_m2 >= :f_smin")
        params["f_smin"] = surface_min
    if surface_max is not None:
        conds.append("p.surface_m2 <= :f_smax")
        params["f_smax"] = surface_max
    if sdp_min is not None:
        conds.append("EXISTS (SELECT 1 FROM parcel_residuel r0 WHERE r0.parcel_id = p.id"
                     " AND r0.sdp_residuelle_m2 >= :f_sdp)")
        params["f_sdp"] = sdp_min
    if evenement:
        conds.append("EXISTS (SELECT 1 FROM dryrun_cascade_results c0 WHERE c0.parcel_id = p.id"
                     " AND c0.run_label = :runf AND c0.evenement = 'rouge')")
    if vue_mer:
        conds.append("EXISTS (SELECT 1 FROM parcel_vue_mer v0 WHERE v0.parcel_id = p.id"
                     " AND v0.vue = 'oui')")
    if flags:
        conds.append("EXISTS (SELECT 1 FROM dryrun_cascade_results c1 WHERE c1.parcel_id = p.id"
                     " AND c1.run_label = :runf AND c1.layer_name = ANY(:f_flags)"
                     " AND (c1.result = 'SOFT_FLAG' OR (c1.layer_name = 'abf' AND c1.result = 'UNKNOWN')))")
        params["f_flags"] = [f.strip() for f in flags.split(",") if f.strip()]
    if flags_exclus:   # contraintes RÉDHIBITOIRES (copilote-projet) : écarter les parcelles portant le flag
        conds.append("NOT EXISTS (SELECT 1 FROM dryrun_cascade_results c2 WHERE c2.parcel_id = p.id"
                     " AND c2.run_label = :runf AND c2.layer_name = ANY(:f_flags_x)"
                     " AND (c2.result = 'SOFT_FLAG' OR (c2.layer_name = 'abf' AND c2.result = 'UNKNOWN')))")
        params["f_flags_x"] = [f.strip() for f in flags_exclus.split(",") if f.strip()]
    # ── Score V (Vendabilité, Stage 3) : bandes, signal individuel, tier Brûlante ──
    if v_bands:
        conds.append("EXISTS (SELECT 1 FROM parcel_v_score vs0 WHERE vs0.parcelle_id = p.idu"
                     " AND vs0.v_band = ANY(:f_vbands))")
        params["f_vbands"] = [b.strip() for b in v_bands.split(",") if b.strip()]
    if v_signal:
        # signaux retenus (JSONB §5.4) : au moins UN des codes demandés présent
        conds.append("EXISTS (SELECT 1 FROM parcel_v_score vs1 WHERE vs1.parcelle_id = p.idu"
                     " AND EXISTS (SELECT 1 FROM jsonb_array_elements(vs1.signals) s0"
                     "             WHERE s0->>'code' = ANY(:f_vsig)))")
        params["f_vsig"] = [c.strip() for c in v_signal.split(",") if c.strip()]
    if brulantes:  # tier combiné 🔥 — vue DYNAMIQUE (suit l'évolution des chaudes)
        conds.append("EXISTS (SELECT 1 FROM v_parcelles_brulantes vb WHERE vb.idu = p.idu)")
    return (" AND " + " AND ".join(conds)) if conds else "", params


@app.get("/parcels")
def list_parcels(commune: str | None = None,
                 limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                 source: str | None = None,
                 statuts: str | None = None, score_min: int | None = None,
                 surface_min: int | None = None, surface_max: int | None = None,
                 sdp_min: int | None = None, evenement: bool = False, vue_mer: bool = False,
                 flags: str | None = None, communes: str | None = None,
                 flags_exclus: str | None = None,
                 v_bands: str | None = None, v_signal: str | None = None,
                 brulantes: bool = False,
                 sort: str | None = Query(None, pattern="^(v)$"),
                 db: Session = Depends(get_db)) -> list[dict]:
    """Liste PAGINÉE (commune OU île entière) avec le dernier verdict.

    `source=<run q_v*>` (défaut Q_A_RUN_LABEL) → panneau résultats (matrice premium, trié ÉVÉNEMENT d'abord puis score).
    Les paramètres de filtre miroir des chips (statuts CSV, score_min, surface, sdp_min,
    evenement, vue_mer, flags CSV) servent le mode « Toute l'île ».
    Score V : `v_bands` (CSV fort/present/faible/aucun/na), `v_signal` (CSV codes §5.3),
    `brulantes` (tier 🔥), `sort='v'` (V décroissant — tri par défaut de la vue chaudes).

    safe-bugfix #2 : `limit` BORNÉ (défaut 100, max 1000) + `offset`, et le dernier `eval`
    récupéré en UNE seule requête LATERAL (plus de N+1 qui chargeait toute la commune et
    bloquait l'endpoint > 45 s)."""
    if source and source.startswith("q_v"):
        extra, extra_params = _q_v2_where(source, statuts, score_min, surface_min, surface_max,
                                          sdp_min, evenement, vue_mer, flags, communes, flags_exclus,
                                          v_bands, v_signal, brulantes)
        return _q_v2_list(db, commune, limit, offset, run_label=source,
                          extra_where=extra, extra_params=extra_params, sort=sort)
    rows = db.execute(text(
        """
        SELECT p.idu, p.commune, p.surface_m2,
               e.status, e.opportunity_score, e.completeness_score
        FROM parcels p
        LEFT JOIN LATERAL (
            SELECT status, opportunity_score, completeness_score
            FROM parcel_evaluations e WHERE e.parcel_id = p.id
            ORDER BY evaluated_at DESC LIMIT 1
        ) e ON true
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
        ORDER BY p.idu
        LIMIT :lim OFFSET :off
        """), {"c": commune, "lim": limit, "off": offset}).mappings().all()
    return [{
        "idu": r["idu"], "commune": r["commune"], "surface_m2": r["surface_m2"],
        "status": r["status"], "opportunity_score": r["opportunity_score"],
        "completeness_score": r["completeness_score"],
    } for r in rows]


@app.get("/parcels/export.csv")
def export_parcels_csv(commune: str | None = None, source: str = Q_A_RUN_LABEL,
                       statuts: str | None = None, score_min: int | None = None,
                       surface_min: int | None = None, surface_max: int | None = None,
                       sdp_min: int | None = None, evenement: bool = False, vue_mer: bool = False,
                       flags: str | None = None, communes: str | None = None,
                       flags_exclus: str | None = None,
                       v_bands: str | None = None, v_signal: str | None = None,
                       brulantes: bool = False,
                       sort: str | None = Query(None, pattern="^(v)$"),
                       limit: int = Query(1000, ge=1, le=5000),
                       db: Session = Depends(get_db)) -> Response:
    """Export CSV de la liste (mêmes filtres que /parcels) — colonnes Score V incluses :
    `v_score`, `v_band`, `top_signaux` (labels des 3 signaux les plus forts), `brulante`.
    ⚠ Doit rester déclarée AVANT /parcels/{idu} (ordre de résolution des routes)."""
    import csv as _csv
    import io as _io

    extra, extra_params = _q_v2_where(source, statuts, score_min, surface_min, surface_max,
                                      sdp_min, evenement, vue_mer, flags, communes, flags_exclus,
                                      v_bands, v_signal, brulantes)
    items = _q_v2_list(db, commune, limit, 0, run_label=source,
                       extra_where=extra, extra_params=extra_params, sort=sort)
    tops = {r[0]: r[1] for r in db.execute(text(
        "SELECT parcelle_id, (SELECT string_agg(s->>'label', ' | ') FROM ("
        "  SELECT s FROM jsonb_array_elements(signals) s "
        "  ORDER BY (s->>'points')::int DESC LIMIT 3) t(s)) "
        "FROM parcel_v_score WHERE parcelle_id = ANY(:idus)"),
        {"idus": [it["idu"] for it in items]}).all()}
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["idu", "commune", "surface_m2", "statut", "q_score", "a_score",
                "completeness", "proprio", "v_score", "v_band", "brulante", "top_signaux"])
    for it in items:
        w.writerow([it["idu"], it["commune"], it["surface_m2"], it["status"], it["q_score"],
                    it["a_score"], it["completeness_score"], it["proprio"] or "",
                    it["v_score"] if it["v_score"] is not None else "",
                    it["v_band"] or "", "oui" if it["brulante"] else "",
                    tops.get(it["idu"]) or ""])
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="labuse_parcelles.csv"'})


@app.get("/communes")
def list_communes(source: str = Q_A_RUN_LABEL, db: Session = Depends(get_db)) -> list[dict]:
    """Les 24 communes pour le SÉLECTEUR : nom, INSEE, volumétrie, chaudes, bbox (recadrage carte).
    Trié par nombre de chaudes décroissant (l'ordre utile au prospecteur). Cache 5 min."""
    def _compute() -> list[dict]:
        rows = db.execute(text(
            """
            SELECT p.commune,
                   substring(min(p.idu) from 1 for 5)                       AS insee,
                   count(*)                                                 AS parcelles,
                   count(*) FILTER (WHERE d.matrice_statut = 'chaude')      AS chaudes,
                   count(DISTINCT pm.siren) FILTER (WHERE d.matrice_statut = 'chaude'
                         AND pm.siren IS NOT NULL)                          AS dossiers,
                   count(*) FILTER (WHERE d.matrice_statut = 'chaude'
                         AND pm.siren IS NULL)                              AS chaudes_sans_identite,
                   count(d.parcel_id)                                       AS evaluees,
                   ST_XMin(ST_Extent(p.geom)) AS x1, ST_YMin(ST_Extent(p.geom)) AS y1,
                   ST_XMax(ST_Extent(p.geom)) AS x2, ST_YMax(ST_Extent(p.geom)) AS y2
            FROM parcels p
            LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
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
    return {"commune": commune, "epci": epci,
            "epci_nom": epci_cfg[epci]["nom"] if epci else None,
            "sru": sru, "anru": anru, "qpv": qpv, "plh": plh, "marche": insee_log,
            "notes": ["ZUS et ZFU sont des zonages abrogés (réforme 2014), devenus QPV — déjà "
                      "couverts par la couche QPV. Volet fiscal ZFU-Territoires Entrepreneurs : "
                      "pas de source propre 974 identifiée (écart consigné).",
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


@app.get("/parcels/search")
def search_parcels(q: str = Query(..., min_length=2), commune: str | None = None,
                   source: str = Q_A_RUN_LABEL, limit: int = Query(10, ge=1, le=50),
                   db: Session = Depends(get_db)) -> list[dict]:
    """Recherche IDU/section pour l'omnibox en mode île (le client n'a plus les features en
    mémoire). Matche la fin d'IDU (section+numéro, ex. « AC0253 ») ou l'IDU complet."""
    needle = q.strip().upper().replace(" ", "")
    rows = db.execute(text(
        """
        SELECT p.idu, p.commune, d.matrice_statut AS status, d.q_score, d.a_score
        FROM parcels p
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE p.idu ILIKE :pat AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        ORDER BY (d.matrice_statut = 'chaude') DESC NULLS LAST, p.idu
        LIMIT :lim
        """), {"pat": f"%{needle}", "c": commune, "run": source, "lim": limit}).mappings().all()
    return [dict(r) for r in rows]


@app.get("/stats/entonnoir")
def stats_entonnoir(commune: str | None = None, source: str = Q_A_RUN_LABEL,
                    db: Session = Depends(get_db)) -> dict:
    """L'ENTONNOIR PAR MOTIF (C4, revue Vic) : « LABUSE a analysé N parcelles et trié pour
    vous » — décomposition SQL-exacte des écartées par garde (matérialisée post-matrice ;
    une parcelle peut cumuler des motifs, affiché tel quel). Pédagogique ET auditable."""
    key = commune or "__ile__"
    rows = db.execute(text(
        "SELECT motif, n FROM entonnoir_motifs WHERE run_label = :r AND commune = :c ORDER BY ord"),
        {"r": source, "c": key}).mappings().all()
    stats_row = _q_v2_stats(db, commune, run_label=source)
    return {"commune": commune, "analysees": stats_row["total"],
            "opportunites": stats_row["chaude"] + stats_row["a_surveiller"] + stats_row["a_creuser"],
            "motifs": [dict(r) for r in rows],
            "note": ("Une parcelle peut cumuler plusieurs motifs (les pourcentages se recouvrent). "
                     "« Qualité insuffisante » = survivante du filtre dur mais Q<50.")}


@app.get("/stats")
def stats(commune: str | None = None, source: str | None = None,
          statuts: str | None = None, score_min: int | None = None,
          surface_min: int | None = None, surface_max: int | None = None,
          sdp_min: int | None = None, evenement: bool = False, vue_mer: bool = False,
          flags: str | None = None, communes: str | None = None,
          flags_exclus: str | None = None,
          v_bands: str | None = None, v_signal: str | None = None,
          brulantes: bool = False,
          db: Session = Depends(get_db)) -> dict:
    """Cartouches du dashboard : volumétrie + statuts + scores (dernière évaluation).

    `source=<run q_v*>` (défaut Q_A_RUN_LABEL) → comptes de la matrice premium (chaude/à surveiller/à creuser/écartée),
    filtrables (mêmes paramètres que /parcels — compteurs SQL-exacts du mode île).
    Résultat mémorisé par commune+filtres (cache mémoire 30 s, #7) : sortie identique au calcul."""
    if source and source.startswith("q_v"):
        extra, extra_params = _q_v2_where(source, statuts, score_min, surface_min, surface_max,
                                          sdp_min, evenement, vue_mer, flags, communes, flags_exclus,
                                          v_bands, v_signal, brulantes)
        key = ("stats_qv2", source, commune, statuts, score_min, surface_min, surface_max,
               sdp_min, evenement, vue_mer, flags, communes, flags_exclus,
               v_bands, v_signal, brulantes)
        return _mem_cached(key, 30.0, lambda: _q_v2_stats(
            db, commune, run_label=source, extra_where=extra, extra_params=extra_params))

    def _compute() -> dict:
        row = db.execute(
            text(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE e.status = 'opportunite') AS opportunite,
                       count(*) FILTER (WHERE e.status = 'a_creuser')   AS a_creuser,
                       count(*) FILTER (WHERE e.status = 'exclue')      AS exclue,
                       round(avg(e.completeness_score)) AS completeness_avg,
                       max(e.opportunity_score)         AS opportunity_max
                FROM parcels p
                LEFT JOIN LATERAL (
                    SELECT status, opportunity_score, completeness_score
                    FROM parcel_evaluations e WHERE e.parcel_id = p.id
                    ORDER BY evaluated_at DESC LIMIT 1
                ) e ON true
                WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
                """
            ), {"c": commune}
        ).mappings().one()
        out = {k: (int(v) if v is not None else None) for k, v in row.items()}
        out["active_signals"] = int(db.execute(
            text("""SELECT count(*) FROM parcel_signals s JOIN parcels p ON p.id = s.parcel_id
                    WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)"""), {"c": commune}).scalar() or 0)
        return out

    return _mem_cached(("stats", commune), 30.0, _compute)


def _owner_famille(groupe, forme, denom) -> str:
    """Famille de propriétaire (public/prive/inconnu) pour le filtre carte (1.A — DGFiP). Source
    unique : classify_dgfip. `inconnu` = parcelle absente du fichier des morales (= particulier)."""
    if groupe is None and not denom:
        return "inconnu"
    from ..proprietaire_type import classify_dgfip
    return classify_dgfip(groupe, forme, denom)["famille"]


@app.get("/map/parcels.geojson")
def parcels_geojson(commune: str | None = None, limit: int = Query(60000, ge=0, le=200000),
                    source: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Parcelles (géométrie simplifiée 4326) + verdict, pour la carte colorée.

    `source=<run q_v*>` (défaut Q_A_RUN_LABEL) (Socle V1) → lit le scoring premium v2 dans `dryrun_parcel_evaluations`
    (matrice chaude/à surveiller/à creuser/écartée + Q/A + complétude + événement rouge),
    la SOURCE DE VÉRITÉ. Sans `source`, comportement historique (parcel_evaluations live)."""
    if source and source.startswith("q_v"):
        return _q_v2_geojson(db, commune, limit, run_label=source)
    rows = db.execute(
        text(
            """
            SELECT p.idu, p.surface_m2,
                   ST_AsGeoJSON(ST_SimplifyPreserveTopology(p.geom, 0.00002)) AS g,
                   e.status, e.opportunity_score, e.completeness_score, d.detail AS downgrade_reason,
                   r.taux_emprise_pct, r.sous_densite, r.sdp_residuelle_m2,
                   own.groupe AS own_groupe, own.forme_juridique AS own_forme, own.denomination AS own_denom
            FROM parcels p
            LEFT JOIN LATERAL (
                SELECT status, opportunity_score, completeness_score
                FROM parcel_evaluations e WHERE e.parcel_id = p.id
                ORDER BY evaluated_at DESC LIMIT 1
            ) e ON true
            LEFT JOIN LATERAL (
                SELECT detail FROM cascade_results
                WHERE parcel_id = p.id AND layer_name = 'declassement' LIMIT 1
            ) d ON true
            LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
            LEFT JOIN parcelle_personne_morale own ON own.idu = p.idu
            WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
              AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)
            LIMIT :lim
            """
        ), {"c": commune, "lim": limit, "minsurf": MIN_DISPLAY_SURFACE_M2}
    ).mappings().all()
    feats = [
        {
            "type": "Feature",
            "geometry": json.loads(r["g"]),
            "properties": {
                "idu": r["idu"],
                "surface_m2": round(r["surface_m2"]) if r["surface_m2"] else None,
                "status": r["status"],
                "opportunity_score": r["opportunity_score"],
                "completeness_score": r["completeness_score"],
                "downgrade_reason": r["downgrade_reason"],
                "taux_emprise_pct": r["taux_emprise_pct"],
                "sous_densite": r["sous_densite"],
                "sdp_residuelle_m2": r["sdp_residuelle_m2"],
                "owner_famille": _owner_famille(r["own_groupe"], r["own_forme"], r["own_denom"]),
            },
        }
        for r in rows if r["g"]
    ]
    return {"type": "FeatureCollection", "features": feats}


#: statuts de la matrice premium v2 (dryrun) — source de vérité du Socle V1.
_Q_V2_STATUTS = ("chaude", "a_surveiller", "a_creuser", "ecartee", "exclue")


def _q_v2_geojson(db: Session, commune: str | None, limit: int, run_label: str = Q_A_RUN_LABEL) -> dict:
    """Parcelles + matrice premium v2 (dryrun_parcel_evaluations). `status` = matrice_statut ;
    Q/A + complétude + événement rouge exposés (exigences #1/#2/#4). Une parcelle exclue à
    l'étage 0 apparaît en `ecartee` ; les `evenement='rouge'` (BODACC ouvert) sont marquées."""
    rows = db.execute(text(
        """
        SELECT p.idu, p.surface_m2,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(p.geom, 0.00002)) AS g,
               d.matrice_statut AS status, d.q_score, d.a_score, d.a_completude,
               d.completeness_score, r.sdp_residuelle_m2, r.sous_densite, vm.vue AS vue_mer,
               (ev.parcel_id IS NOT NULL) AS evenement_rouge, fl.flags,
               cl.n AS cluster, COALESCE(cl.denom, own.denomination) AS proprio,
               vs.v_score, vs.v_band, vs.owner_type,
               (d.matrice_statut = 'chaude' AND vs.v_score >= :vth) AS brulante,
               (SELECT array_agg(s0->>'code') FROM jsonb_array_elements(vs.signals) s0) AS v_sig
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu
        LEFT JOIN parcelle_personne_morale own ON own.idu = p.idu
        LEFT JOIN (SELECT pm2.siren, count(*) AS n, max(pm2.denomination) AS denom
                   FROM dryrun_parcel_evaluations d2
                   JOIN parcels p2 ON p2.id = d2.parcel_id
                   JOIN parcelle_personne_morale pm2 ON pm2.idu = p2.idu
                   WHERE d2.run_label = :run AND d2.matrice_statut = 'chaude'
                     AND pm2.siren IS NOT NULL
                   GROUP BY pm2.siren HAVING count(*) > 1) cl ON cl.siren = own.siren
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN parcel_vue_mer vm ON vm.parcel_id = p.id
        LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                   WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
        -- flags actifs par parcelle (filtres métier) : couches en SOFT_FLAG + ABF non instruit
        LEFT JOIN (SELECT parcel_id, array_agg(DISTINCT layer_name) AS flags
                   FROM dryrun_cascade_results
                   WHERE run_label = :run AND (result = 'SOFT_FLAG'
                         OR (layer_name = 'abf' AND result = 'UNKNOWN'))
                   GROUP BY parcel_id) fl ON fl.parcel_id = p.id
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
          AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)
        LIMIT :lim
        """), {"c": commune, "run": run_label, "lim": limit, "minsurf": MIN_DISPLAY_SURFACE_M2,
               "vth": V_BRULANTE_THRESHOLD}
    ).mappings().all()
    feats = [{
        "type": "Feature",
        "geometry": json.loads(r["g"]),
        "properties": {
            "idu": r["idu"],
            "surface_m2": round(r["surface_m2"]) if r["surface_m2"] else None,
            "status": r["status"],
            "q_score": r["q_score"],
            "a_score": r["a_score"],
            "a_completude": r["a_completude"],
            "completeness_score": r["completeness_score"],
            "sdp_residuelle_m2": r["sdp_residuelle_m2"],
            "sous_densite": r["sous_densite"],
            "vue_mer": r["vue_mer"],
            "evenement": "rouge" if r["evenement_rouge"] else None,
            "flags": r["flags"] or [],
            "cluster": int(r["cluster"]) if r["cluster"] else None,
            "proprio": r["proprio"],
            "v_score": r["v_score"],
            "v_band": r["v_band"],
            "owner_type": r["owner_type"],
            "brulante": bool(r["brulante"]),
            "v_sig": r["v_sig"] or [],
        },
    } for r in rows if r["g"]]
    return {"type": "FeatureCollection", "features": feats}


def _q_v2_list(db: Session, commune: str | None, limit: int, offset: int, run_label: str = Q_A_RUN_LABEL,
               extra_where: str = "", extra_params: dict | None = None,
               sort: str | None = None) -> list[dict]:
    """Liste triée ÉVÉNEMENT d'abord puis score (Q+A) — même tri métier que le front. `extra_where`
    = fragment de _q_v2_where (mode île : filtres SQL). `sort='v'` : V décroissant (NULLS LAST)
    — tri par défaut de la vue chaudes (Score V, Phase 3)."""
    order = ("vs.v_score DESC NULLS LAST, (ev.parcel_id IS NOT NULL) DESC, "
             "(d.q_score + d.a_score) DESC" if sort == "v" else
             "(ev.parcel_id IS NOT NULL) DESC, (d.q_score + d.a_score) DESC, d.q_score DESC")
    rows = db.execute(text(
        f"""
        SELECT p.idu, p.commune, p.surface_m2, p.section,
               d.matrice_statut AS status, d.q_score, d.a_score, d.a_completude, d.completeness_score,
               (ev.parcel_id IS NOT NULL) AS evenement_rouge,
               cl.n AS cluster, COALESCE(cl.denom, own.denomination) AS proprio,
               vs.v_score, vs.v_band, vs.owner_type,
               (d.matrice_statut = 'chaude' AND vs.v_score >= :vth) AS brulante
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                   WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
        LEFT JOIN parcelle_personne_morale own ON own.idu = p.idu
        LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu
        LEFT JOIN (SELECT pm2.siren, count(*) AS n, max(pm2.denomination) AS denom
                   FROM dryrun_parcel_evaluations d2
                   JOIN parcels p2 ON p2.id = d2.parcel_id
                   JOIN parcelle_personne_morale pm2 ON pm2.idu = p2.idu
                   WHERE d2.run_label = :run AND d2.matrice_statut = 'chaude'
                     AND pm2.siren IS NOT NULL
                   GROUP BY pm2.siren HAVING count(*) > 1) cl ON cl.siren = own.siren
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
          AND d.matrice_statut = ANY(:base_statuts)
          {extra_where}
        ORDER BY {order}
        LIMIT :lim OFFSET :off
        """), {"c": commune, "run": run_label, "lim": limit, "off": offset,
               "vth": V_BRULANTE_THRESHOLD,
               # opt-in écartées (C7) : le filtre statut explicite ÉLARGIT le périmètre promues
               "base_statuts": (extra_params or {}).get("f_statuts")
                               or ["chaude", "a_surveiller", "a_creuser"],
               **(extra_params or {})}
    ).mappings().all()
    return [{
        "idu": r["idu"], "commune": r["commune"], "surface_m2": round(r["surface_m2"]) if r["surface_m2"] else None,
        "lieu_dit": r["commune"], "status": r["status"], "q_score": r["q_score"], "a_score": r["a_score"],
        "a_completude": r["a_completude"], "completeness_score": r["completeness_score"],
        "evenement": "rouge" if r["evenement_rouge"] else None,
        "cluster": int(r["cluster"]) if r["cluster"] else None,
        "proprio": r["proprio"],
        "v_score": r["v_score"], "v_band": r["v_band"], "owner_type": r["owner_type"],
        "brulante": bool(r["brulante"]),
    } for r in rows]


def _q_v2_stats(db: Session, commune: str | None, run_label: str = Q_A_RUN_LABEL,
                extra_where: str = "", extra_params: dict | None = None) -> dict:
    """Comptes par statut matrice (en-tête + barre de répartition). « N chaudes · M à surveiller ».
    `extra_where` = filtres chips en SQL (mode île : les compteurs restent SQL-exacts filtrés).

    DOSSIERS (unité de prospection) : parmi les chaudes, propriétaires uniques identifiés —
    clé = SIREN (personnes morales, DGFiP). Limite consignée : les personnes physiques n'ont
    pas d'identité en base (doctrine) → « sans identité », jamais un total prétendu exact."""
    params = {"c": commune, "run": run_label, **(extra_params or {})}
    row = db.execute(text(
        f"""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE matrice_statut = 'chaude')       AS chaude,
               count(*) FILTER (WHERE matrice_statut = 'chaude' AND EXISTS (
                   SELECT 1 FROM dryrun_cascade_results ev WHERE ev.parcel_id = d.parcel_id
                     AND ev.run_label = :run AND ev.evenement = 'rouge')) AS chaude_evenement,
               count(*) FILTER (WHERE matrice_statut = 'a_surveiller') AS a_surveiller,
               count(*) FILTER (WHERE matrice_statut = 'a_creuser')    AS a_creuser,
               count(*) FILTER (WHERE matrice_statut = 'ecartee')      AS ecartee
        FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
        WHERE d.run_label = :run AND (CAST(:c AS text) IS NULL OR p.commune = :c)
          {extra_where}
        """), params).mappings().one()
    dossiers = db.execute(text(
        f"""
        SELECT count(DISTINCT pm.siren) FILTER (WHERE pm.siren IS NOT NULL) AS dossiers,
               count(*) FILTER (WHERE pm.siren IS NULL)                     AS sans_identite
        FROM dryrun_parcel_evaluations d
        JOIN parcels p ON p.id = d.parcel_id
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE d.run_label = :run AND d.matrice_statut = 'chaude'
          AND (CAST(:c AS text) IS NULL OR p.commune = :c)
          {extra_where}
        """), params).mappings().one()
    # Score V (Stage 3) : Brûlantes 🔥 + répartition par bande — mêmes filtres, SQL-exact.
    v_row = db.execute(text(
        f"""
        SELECT count(*) FILTER (WHERE d.matrice_statut = 'chaude' AND vs.v_score >= :vth) AS brulantes,
               count(*) FILTER (WHERE vs.v_band = 'fort')    AS v_fort,
               count(*) FILTER (WHERE vs.v_band = 'present') AS v_present,
               count(*) FILTER (WHERE vs.v_band = 'faible')  AS v_faible,
               count(*) FILTER (WHERE vs.v_band = 'aucun')   AS v_aucun,
               count(*) FILTER (WHERE vs.v_band = 'na')      AS v_na
        FROM dryrun_parcel_evaluations d
        JOIN parcels p ON p.id = d.parcel_id
        LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu
        WHERE d.run_label = :run AND (CAST(:c AS text) IS NULL OR p.commune = :c)
          {extra_where}
        """), {**params, "vth": V_BRULANTE_THRESHOLD}).mappings().one()
    return {**{k: int(v or 0) for k, v in row.items()},
            "dossiers_chaudes": int(dossiers["dossiers"] or 0),
            "chaudes_sans_identite": int(dossiers["sans_identite"] or 0),
            **{k: int(v or 0) for k, v in v_row.items()}}


#: axe A (pur vendeur) — cf. config/scoring_matrice.yaml a_layers. Tout le reste = Q.
_A_LAYERS = {"proprietaire", "age_dirigeant", "bodacc", "dpe_passoire"}
#: rattachement couche → onglet de la fiche (Synthèse/Bilan sont des vues, pas des groupes de lignes).
_ONGLET = {
    "regles": {"zonage_plu_gpu", "prescription_plu", "foncier_public", "emprise_lineaire",
               "residuel_socle", "safer", "sar", "surface", "parc_national", "foret_publique"},
    "risques": {"risques", "sol_pollue", "cavite", "icpe", "mvt", "pente", "ravine",
                "trait_de_cote", "abf", "ens", "eau"},
    "marche": {"dvf", "sitadel", "vue_mer", "amenites", "potentiel_foncier_region", "ocs_ge",
               "friche", "acces"},
    "proprio": {"proprietaire", "age_dirigeant", "bodacc", "dpe_passoire", "assemblage"},
}
_LAYER_ONGLET = {layer: onglet for onglet, layers in _ONGLET.items() for layer in layers}


def _q_v2_fiche(db: Session, idu: str, run_label: str = Q_A_RUN_LABEL) -> dict:
    """Fiche premium v2 (dryrun) : en-tête matrice + lignes cascade TRACÉES (axe Q/A, onglet,
    source cliquable, date), flags, événement. « La traçabilité EST le produit »."""
    head = db.execute(text(
        """SELECT p.id, p.idu, p.commune, p.surface_m2,
                  ST_Y(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lat,
                  ST_X(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lon,
                  d.matrice_statut, d.q_score, d.a_score, d.a_completude, d.completeness_score
           FROM parcels p JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
           WHERE p.idu = :idu"""), {"idu": idu, "run": run_label}).mappings().first()
    if not head:
        raise HTTPException(404, f"Parcelle {idu} absente du run {run_label}")

    rows = db.execute(text(
        """SELECT cr.layer_name, cr.result, cr.severity, cr.weight_applied, cr.detail,
                  cr.source_table, cr.source_id, cr.evenement, cr.created_at, ds.name AS source
           FROM dryrun_cascade_results cr LEFT JOIN data_sources ds ON ds.id = cr.data_source_id
           WHERE cr.run_label = :run AND cr.parcel_id = :pid
           ORDER BY abs(COALESCE(cr.weight_applied, 0)) DESC, cr.layer_name"""),
        {"pid": head["id"], "run": run_label}).mappings().all()

    lines, flags, evenement_detail = [], [], None
    for r in rows:
        w = r["weight_applied"]
        line = {
            "layer": r["layer_name"],
            "axis": "a" if r["layer_name"] in _A_LAYERS else "q",
            "onglet": _LAYER_ONGLET.get(r["layer_name"], "regles"),
            "result": r["result"],
            "severity": r["severity"],
            "weight": round(w) if w is not None else None,
            "detail": r["detail"],
            "source": r["source"],
            "source_table": r["source_table"],
            "source_id": r["source_id"],
            "date": r["created_at"].date().isoformat() if r["created_at"] else None,
        }
        lines.append(line)
        if r["evenement"] == "rouge":
            evenement_detail = r["detail"]
        if (w is None or w == 0) and r["result"] in ("SOFT_FLAG", "HARD_EXCLUDE", "UNKNOWN"):
            flags.append(line)

    pm = db.execute(text(
        "SELECT denomination, siren, groupe_label FROM parcelle_personne_morale WHERE idu = :idu"),
        {"idu": idu}).mappings().first()
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
        dvf_parcelle = {
            "derniere_mutation": ({**dict(dvf_last),
                                   "date_mutation": dvf_last["date_mutation"].isoformat()
                                   if dvf_last["date_mutation"] else None}
                                  if dvf_last else None),
            "secteur": dvf_secteur,
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
            "brulante": bool(head["matrice_statut"] == "chaude" and vrow["v_score"] is not None
                             and vrow["v_score"] >= V_BRULANTE_THRESHOLD),
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
        "proprietaire_moral": dict(pm) if pm else None,
        "anru": {"quartier": anru["name"], "interet": anru["interet"],
                 "position": "dans" if anru["dans"] else "adjacente"} if anru else None,
        "surface_m2": round(head["surface_m2"]) if head["surface_m2"] else None,
        "statut": head["matrice_statut"], "q_score": head["q_score"], "a_score": head["a_score"],
        "a_completude": head["a_completude"], "completeness_score": head["completeness_score"],
        "coords": [round(head["lon"], 6), round(head["lat"], 6)],
        "evenement": "rouge" if evenement_detail else None, "evenement_detail": evenement_detail,
        "lines": lines, "flags": flags,
        "score_v": score_v,
        "dvf_parcelle": dvf_parcelle,
        "terrain": dict(terrain) if terrain else None,
        "coproprietes": copros,
        "marche_secteur": marche_secteur,
    }


@app.get("/parcels/{idu}")
def parcel_fiche(idu: str, source: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Fiche « Tout ce que LA BUSE a trouvé » (§8). `source=<run q_v*>` (défaut Q_A_RUN_LABEL) → fiche premium (dryrun)."""
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
    from .pdf_premium import render_fiche_pdf
    fiche = _q_v2_fiche(db, idu, run_label=source)
    # bloc CONTEXTE COMMUNE (mandat promotrice) : SRU + QPV/ANRU + 2-3 chiffres marché
    fiche["contexte_commune"] = commune_contexte(fiche["commune"], db)
    fiche["rtaa"] = config.load_yaml_config("rtaa_dom")   # rappel réglementaire (5bis)
    if cout_construction_m2 is not None and marge_frais_pct is not None:
        fiche["calculette"] = _calculette_for_pdf(db, idu, cout_construction_m2, marge_frais_pct, prix_demande_eur)
    return Response(content=render_fiche_pdf(fiche), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="labuse_{idu}.pdf"'})


def _calculette_for_pdf(db: Session, idu: str, cout: float, marge: float, prix_demande: float | None) -> dict | None:
    """Recalcule la charge foncière (moteur) pour l'export PDF — None si non calculable."""
    from ..faisabilite.bilan import compute_calculette, sector_price
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses
    row = db.execute(text("SELECT id, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        return None
    fz = parcel_faisabilite(db, row["id"])
    shab = (fz[1].fourchette or {}).get("shab_vendable_m2") if fz else None
    if not shab:
        return None
    prix = sector_price(db, row["id"], Hypotheses())
    res = compute_calculette(float(shab), float(row["s"] or 0), prix, cout, marge, prix_demande)
    return res if res.get("calculable") else None


#: kinds de couches carte exposées au front (Brique 1) — whitelist stricte.
_MAP_LAYER_KINDS = {"plu_gpu_zone", "ppr", "parc_national", "anru", "amenite"}


@app.get("/map/layers.geojson")
def map_layers_geojson(kind: str, commune: str | None = None,
                       limit: int = Query(6000, ge=1, le=20000), db: Session = Depends(get_db)) -> dict:
    """Couches carte (zonage PLU, PPR, Parc national) — géométries simplifiées pour l'overlay.

    Les couches sans commune (île entière, ex. Parc) passent le filtre commune."""
    if kind not in _MAP_LAYER_KINDS:
        raise HTTPException(422, f"kind inconnu : {kind}")
    rows = db.execute(text(
        """SELECT sl.id, sl.subtype, sl.name,
                  ST_AsGeoJSON(ST_SimplifyPreserveTopology(sl.geom, 0.0002)) AS g
           FROM spatial_layers sl
           WHERE sl.kind = :k AND (CAST(:c AS text) IS NULL OR sl.commune = :c OR sl.commune IS NULL)
           LIMIT :lim"""), {"k": kind, "c": commune, "lim": limit}).mappings().all()
    feats = [{"type": "Feature", "geometry": json.loads(r["g"]),
              "properties": {"id": r["id"], "subtype": r["subtype"], "name": r["name"]}}
             for r in rows if r["g"]]
    return {"type": "FeatureCollection", "features": feats}


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
    commune = commune or config.get_settings().pilot_commune_name
    # Candidats = verdicts actionnables (opportunité / à creuser), mêmes champs que la carte.
    rows = db.execute(
        text(
            """
            SELECT p.idu, p.commune, p.surface_m2,
                   e.status, e.opportunity_score, e.completeness_score,
                   d.detail AS downgrade_reason,
                   r.sous_densite, r.sdp_residuelle_m2,
                   own.groupe AS own_groupe, own.forme_juridique AS own_forme, own.denomination AS own_denom
            FROM parcels p
            JOIN LATERAL (
                SELECT status, opportunity_score, completeness_score
                FROM parcel_evaluations e WHERE e.parcel_id = p.id
                ORDER BY evaluated_at DESC LIMIT 1
            ) e ON true
            LEFT JOIN LATERAL (
                SELECT detail FROM cascade_results
                WHERE parcel_id = p.id AND layer_name = 'declassement' LIMIT 1
            ) d ON true
            LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
            LEFT JOIN parcelle_personne_morale own ON own.idu = p.idu
            WHERE p.commune = :c AND e.status IN ('opportunite', 'a_creuser')
            """
        ), {"c": commune}
    ).mappings().all()
    candidates = [
        {**{k: r[k] for k in ("idu", "commune", "surface_m2", "status",
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


# ───────────────────────────── Radar Mutation (V1, lecture seule) ────────────────────────
# Score Mutation DISTINCT du verdict d'opportunité (cf. src/labuse/mutation.py /
# docs/product/RADAR_MUTATION_PHASE1_SPEC.md). Lecture seule : aucune écriture, ne touche NI
# le scoring d'opportunité NI le verdict. Pas d'UI à ce stade (Phase 2B = API uniquement).

@app.get("/mutation/{idu}")
def mutation_parcel(idu: str, db: Session = Depends(get_db)) -> dict:
    """Score Mutation (Radar Mutation) d'une parcelle — potentiel de transformation à étudier."""
    from .. import mutation as mut

    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if p is None:
        raise HTTPException(404, "Parcelle inconnue")
    m = mut.mutation_for_parcels(db, [p.id]).get(p.id)
    if m is None:
        raise HTTPException(404, "Parcelle non évaluée")
    return {"idu": p.idu, "commune": p.commune, "mutation": m}


@app.get("/mutation")
def mutation_top(commune: str | None = None, niveau: str | None = None,
                 min_score: int = Query(0, ge=0, le=100), limit: int = Query(20, ge=1, le=100),
                 db: Session = Depends(get_db)) -> dict:
    """Top Radar Mutation d'une commune — shortlist premium triée par Score Mutation (lecture seule).

    Paramètres durcis : `niveau` hors nomenclature → 422 ; `commune` inconnue → 404 (plutôt
    qu'une liste vide silencieuse). `min_score`/`limit` sont déjà bornés par FastAPI."""
    from .. import mutation as mut

    if niveau is not None and niveau not in mut.NIVEAUX:
        raise HTTPException(422, f"niveau invalide : {niveau!r} (attendu : {', '.join(mut.NIVEAUX)})")
    commune = commune or config.get_settings().pilot_commune_name
    known = db.execute(text("SELECT 1 FROM parcels WHERE commune = :c LIMIT 1"), {"c": commune}).first()
    if known is None:
        raise HTTPException(404, f"Commune inconnue : {commune!r}")
    parcels = mut.top_for_commune(db, commune, niveau=niveau, min_score=min_score, limit=limit)
    return {"commune": commune, "niveau": niveau, "count": len(parcels), "parcels": parcels}


@app.get("/map/mutation.geojson")
def mutation_geojson(commune: str | None = None, niveau: str = "prioritaire",
                     limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)) -> dict:
    """Calque carte Radar Mutation (LECTURE SEULE) : géométries du TOP mutation d'une commune,
    `score_mutation`/`niveau` en propriétés. Réutilise le top MÉMORISÉ (léger) — n'évalue JAMAIS
    toutes les parcelles. Fondation backend d'un futur calque « Radar » optionnel (Phase 2E),
    distinct des couches verdict ; ne modifie aucune couche carte existante."""
    from .. import mutation as mut

    if niveau not in mut.NIVEAUX:
        raise HTTPException(422, f"niveau invalide : {niveau!r} (attendu : {', '.join(mut.NIVEAUX)})")
    commune = commune or config.get_settings().pilot_commune_name
    known = db.execute(text("SELECT 1 FROM parcels WHERE commune = :c LIMIT 1"), {"c": commune}).first()
    if known is None:
        raise HTTPException(404, f"Commune inconnue : {commune!r}")
    top = mut.top_for_commune(db, commune, niveau=niveau, min_score=0, limit=limit)
    by_idu = {p["idu"]: p for p in top}
    feats = []
    if by_idu:
        for idu, g in db.execute(text(
                "SELECT idu, ST_AsGeoJSON(geom) g FROM parcels WHERE idu = ANY(:idus)"),
                {"idus": list(by_idu)}).all():
            if not g:
                continue
            p = by_idu.get(idu, {})
            feats.append({"type": "Feature", "geometry": json.loads(g),
                          "properties": {"idu": idu, "score_mutation": p.get("score_mutation"),
                                         "niveau": p.get("niveau")}})
    return {"type": "FeatureCollection", "features": feats}


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

    # Cascade (avec nom de source) — la traçabilité EST le produit.
    cascade_rows = db.execute(
        text(
            """SELECT cr.layer_name, cr.result, cr.severity, cr.weight_applied, cr.detail, ds.name AS source
               FROM cascade_results cr LEFT JOIN data_sources ds ON ds.id = cr.data_source_id
               WHERE cr.parcel_id = :pid ORDER BY cr.id"""
        ), {"pid": p.id}
    ).mappings().all()
    cascade = [dict(r) for r in cascade_rows]
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
    from .resume import is_micro_opportunite
    _status_val = ev.status.value if ev else None
    verdict_block = {
        "status": _status_val,
        "opportunity_score": ev.opportunity_score if ev else None,
        "completeness_score": ev.completeness_score if ev else None,
        "reasons": reasons,
        # Motif de déclassement (garde-fou faux positifs), si la parcelle a été corrigée.
        "downgrade_reason": next((r["detail"] for r in cascade if r["layer_name"] == "declassement"), None),
        "evaluated_at": ev.evaluated_at if ev else None,
        "rules_version": ev.rules_version if ev else None,
        # Badge d'AFFICHAGE « micro-opportunité » (≤ 500 m²) — nuance promoteur, n'affecte NI le
        # verdict NI les scores (cf. resume.is_micro_opportunite). Le statut ci-dessus est intact.
        "micro_opportunite": is_micro_opportunite(_status_val, p.surface_m2),
    }
    # Occupation bâtie (correctif R1) — ratio/nb/plus grand bâtiment + label prudent.
    from .. import bati as bati_mod
    bati_block = bati_mod.fiche_block(db, p.id, p.surface_m2)

    # Résumé « business » (Phase 2) — dérivé des signaux ci-dessus, repris dans les exports.
    from .resume import build_resume
    resume = build_resume(verdict_block, cascade, faisabilite, prosp_block, bati=bati_block)

    # Assemblage foncier (Phase 5) — voisines adjacentes + drapeau prudent (requête indexée).
    from .voisinage import compute_voisinage
    voisinage = compute_voisinage(db, p.id, p.surface_m2, verdict_block["status"])

    # Autorisations d'urbanisme à proximité (Lot C4) — historique SITADEL < 300 m.
    try:
        from ..ingestion.permits import nearby_permits
        permits = nearby_permits(db, p.id)
    except Exception:  # noqa: BLE001 - n'empêche jamais la fiche
        permits = None

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

    # LOT 4-C — Marché Obsimmo (vente) : indicateurs locaux + comparaison régionale pour la commune.
    obsimmo_block = None
    try:
        from .. import obsimmo as obsimmo_mod
        obsimmo_block = obsimmo_mod.fiche_block(p.commune)
    except Exception:  # noqa: BLE001 - indicateur marché optionnel, jamais bloquant
        obsimmo_block = None

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

    fiche = {
        "parcel": {
            "idu": p.idu, "commune": p.commune, "section": p.section, "numero": p.numero,
            "surface_m2": p.surface_m2, "centroid": {"lon": lon, "lat": lat},
            "origine": p.origine,  # 'audit' → bandeau « audit à la demande » sur la fiche
        },
        "resume": resume,
        "bati": bati_block,
        "voisinage": voisinage,
        "faisabilite": faisabilite,
        "plh": plh_block,   # LOT 4.1 — orientations habitat (PLH TCO)
        "obsimmo": obsimmo_block,   # LOT 4-C — marché Obsimmo (vente)
        "loyers": loyers_block,     # LOT 4-B — marché locatif (carte des loyers DHUP)
        "occupation": occupation_block,   # LOT 4-B — statut d'occupation (INSEE RP 2022)
        "permits": permits,
        "prospection": prosp_block,
        # Le bloc « promoteur » (altimétrie/façade/PLU détaillé/réseaux) est servi À PART, en
        # LAZY-LOAD, par GET /parcels/{idu}/enrichment : il fait des appels externes lents
        # (RGE ALTI, prescriptions GPU) qui ne doivent jamais bloquer l'ouverture de la fiche.
        "verdict": verdict_block,
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
    # 3.B — lien « Remonter le temps » calculé HORS cache (déterministe, jamais périmé).
    return {**payload, "remonter_le_temps": remonter_le_temps(lon, lat),
            "computed_at": ca.isoformat() if ca else None}


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
def export_fiche(idu: str, format: str = Query("md", pattern="^(md|html|onepager)$"),
                 db: Session = Depends(get_db)):
    """Export fiche : Markdown (md), HTML détaillé (html), ou one-pager A4 imprimable (onepager,
    Lot D1 — le document de comité : verdict, capacité, résiduel, bilan, contraintes, mini-carte)."""
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from .export import fiche_html, fiche_markdown, fiche_onepager

    fiche = _build_fiche(db, idu)
    if format == "onepager":
        _check_idu(idu)
        gj = db.execute(
            text("SELECT ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.000005)) FROM parcels WHERE idu = :i"),
            {"i": idu}).scalar()
        return HTMLResponse(fiche_onepager(fiche, json.loads(gj) if gj else None))
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
    return {
        "idu": p["idu"], "commune": p.get("commune"), "section": p.get("section"), "numero": p.get("numero"),
        "surface_m2": round(p["surface_m2"]) if p.get("surface_m2") else None,
        "status": v.get("status"), "opportunity_score": v.get("opportunity_score"),
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
def list_filters(db: Session = Depends(get_db)) -> list[dict]:
    """Filtres de recherche sauvegardés (Lot D3)."""
    rows = db.execute(text("SELECT id, name, params, created_at FROM saved_filters ORDER BY created_at DESC")).mappings().all()
    return [{"id": r["id"], "name": r["name"], "params": r["params"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None} for r in rows]


@app.post("/filters")
def save_filter(body: SavedFilterIn, db: Session = Depends(get_db)) -> dict:
    name = (body.name or "").strip()[:80]
    if not name:
        raise HTTPException(422, "Nom de filtre requis.")
    fid = db.execute(text("INSERT INTO saved_filters (name, params) VALUES (:n, CAST(:p AS jsonb)) RETURNING id"),
                     {"n": name, "p": json.dumps(body.params or {})}).scalar()
    return {"id": fid, "name": name, "params": body.params}


@app.delete("/filters/{filter_id}")
def delete_filter(filter_id: int, db: Session = Depends(get_db)) -> dict:
    db.execute(text("DELETE FROM saved_filters WHERE id = :i"), {"i": filter_id})
    return {"ok": True}


class BilanParamIn(BaseModel):
    secteur: str
    param: str
    value: float | None = None   # None → réinitialise au défaut


@app.get("/bilan/params")
def get_bilan_params(secteur: str = Query("*"), db: Session = Depends(get_db)) -> dict:
    """Paramètres du bilan (1.C) résolus pour un secteur (registre + overrides + non calibrés)."""
    from ..faisabilite import bilan_params as bp
    resolved = bp.resolve(db, secteur)
    return {"secteur": secteur,
            "params": [{**p, **resolved.get(p["key"], {})} for p in bp.registry()],
            "non_calibres_critiques": bp.uncalibrated_critical(resolved)}


@app.post("/bilan/params")
def set_bilan_param(body: BilanParamIn, db: Session = Depends(get_db)) -> dict:
    """Calibre (ou réinitialise) un paramètre du bilan pour un secteur (1.C — Vic calibre)."""
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
    out = []
    for idu in ids:
        try:
            out.append(_compare_row(_build_fiche(db, idu, with_assistant=False)))
        except HTTPException:
            continue
    return {"count": len(out), "parcels": out}


@app.post("/parcels/{idu}/evaluate")
def evaluate_one(idu: str, ai: bool = Query(False), db: Session = Depends(get_db)) -> dict:
    from ..ai import get_provider
    from ..cascade import evaluate_parcels

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

@app.get("/discover")
def discover(
    commune: str | None = None,
    min_opportunity: int = Query(0, ge=0, le=100),
    statuses: str = "opportunite,a_creuser",
    limit: int = Query(50, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Survivantes de la cascade, classées (radar). S'appuie sur la dernière évaluation.

    Dernière évaluation via LATERAL depuis `parcels` (comme la carte) plutôt que
    DISTINCT ON sur TOUT l'historique d'évaluations : mêmes résultats, mais le coût ne
    grossit plus avec l'historique (audit J1 : ~1,9 s → quelques dizaines de ms)."""
    wanted = {s.strip() for s in statuses.split(",") if s.strip()}
    rows = db.execute(
        text(
            """
            SELECT p.idu, p.commune, p.surface_m2,
                   e.status, e.opportunity_score, e.completeness_score, e.evaluated_at
            FROM parcels p
            JOIN LATERAL (
                SELECT status, opportunity_score, completeness_score, evaluated_at
                FROM parcel_evaluations e WHERE e.parcel_id = p.id
                ORDER BY evaluated_at DESC LIMIT 1
            ) e ON true
            WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
              AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)
            """
        ), {"c": commune, "minsurf": MIN_DISPLAY_SURFACE_M2}
    ).mappings().all()
    survivors = [
        dict(r) for r in rows
        if r["status"] in wanted and (r["opportunity_score"] or 0) >= min_opportunity
    ]
    survivors.sort(key=lambda r: (r["opportunity_score"] or 0, r["completeness_score"] or 0), reverse=True)
    return survivors[:limit]


# ───────────────────────────── Veille / signaux (offre C) ─────────────────────────────

@app.get("/signals")
def list_signals(commune: str | None = None, signal_type: str | None = None,
                 limit: int = Query(200, ge=0, le=10000), db: Session = Depends(get_db)) -> list[dict]:
    """Signaux de veille (offre C) récents, filtrables par commune / type."""
    rows = db.execute(
        text(
            """SELECT s.signal_type, s.payload, s.detected_at, p.idu, p.commune
               FROM parcel_signals s JOIN parcels p ON p.id = s.parcel_id
               WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
                 AND (CAST(:t AS text) IS NULL OR s.signal_type = :t)
               ORDER BY s.detected_at DESC LIMIT :lim"""
        ), {"c": commune, "t": signal_type, "lim": limit}
    ).mappings().all()
    return [dict(r) for r in rows]


# ───────────────────────── Alertes intelligentes (3.C) ─────────────────────────
# Scope défini par l'utilisateur (zones de veille + parcelles suivies) → « nouveautés ».

class WatchZoneIn(BaseModel):
    name: str
    geometry: dict           # polygone GeoJSON (EPSG:4326)
    commune: str | None = None


class AlerteAckIn(BaseModel):
    id: int | None = None    # None → accuse réception de toutes les nouveautés de la commune
    commune: str | None = None


@app.get("/watch-zones")
def watch_zones_list(commune: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Zones de veille définies (polygones surveillés)."""
    from .. import alertes
    commune = commune or config.get_settings().pilot_commune_name
    return alertes.list_watch_zones(db, commune)


@app.post("/watch-zones")
def watch_zones_create(body: WatchZoneIn, db: Session = Depends(get_db)) -> dict:
    """Crée une zone de veille (polygone dessiné). Détecte aussitôt les nouveautés du scope."""
    from .. import alertes
    if (body.geometry or {}).get("type") != "Polygon":
        raise HTTPException(422, "geometry doit être un Polygon GeoJSON")
    commune = body.commune or config.get_settings().pilot_commune_name
    zone = alertes.create_watch_zone(db, body.name, commune, body.geometry)
    counts = alertes.compute_alertes(db, commune)
    return {"zone": zone, "detected": counts}


@app.delete("/watch-zones/{zone_id}")
def watch_zones_delete(zone_id: int, db: Session = Depends(get_db)) -> dict:
    """Supprime une zone de veille (et ses alertes, par cascade)."""
    from .. import alertes
    if not alertes.delete_watch_zone(db, zone_id):
        raise HTTPException(404, "Zone de veille inconnue")
    return {"ok": True}


@app.get("/alertes")
def alertes_list(commune: str | None = None, only_new: bool = False,
                 limit: int = Query(100, ge=0, le=1000), db: Session = Depends(get_db)) -> list[dict]:
    """Liste des « nouveautés » : ventes DVF en zone de veille + permis près d'une parcelle suivie."""
    from .. import alertes
    commune = commune or config.get_settings().pilot_commune_name
    return alertes.list_alertes(db, commune, only_new=only_new, limit=limit)


@app.post("/alertes/refresh")
def alertes_refresh(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Re-détecte les nouveautés du scope au rafraîchissement des données (idempotent)."""
    from .. import alertes
    commune = commune or config.get_settings().pilot_commune_name
    return alertes.compute_alertes(db, commune)


@app.post("/alertes/ack")
def alertes_ack(body: AlerteAckIn, db: Session = Depends(get_db)) -> dict:
    """Marque une nouveauté (ou toutes celles de la commune) comme lue."""
    from .. import alertes
    commune = body.commune or config.get_settings().pilot_commune_name
    n = alertes.acknowledge(db, alerte_id=body.id, commune=commune)
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


def _col_keys() -> list[str]:
    return [c["key"] for c in _pipeline_cfg().get("columns", [])]


def _prio_keys() -> list[str]:
    return [p["key"] for p in _pipeline_cfg().get("priorities", [])]


def _entry_dict(db: Session, e: models.PipelineEntry) -> dict:
    p = e.parcel
    ev = _latest_eval(db, e.parcel_id)
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
        "parcel": {"commune": p.commune, "section": p.section, "surface_m2": p.surface_m2},
        "verdict": {
            "status": ev.status.value if ev else None,
            "opportunity_score": ev.opportunity_score if ev else None,
        },
        # scoring premium v2 (source de vérité affichage Socle V1) — pour les cartes Kanban
        "premium": _premium_head(db, e.parcel_id),
        # d'où vient la piste (copilote-projet) — None si ajoutée hors projet
        "projet": _projet_ref(db, e.projet_id),
    }


def _projet_ref(db: Session, projet_id: int | None) -> dict | None:
    if projet_id is None:
        return None
    pr = db.get(models.Projet, projet_id)
    return {"id": pr.id, "nom": pr.nom} if pr else None


def _premium_head(db: Session, parcel_id: int, run_label: str = Q_A_RUN_LABEL) -> dict | None:
    r = db.execute(text(
        "SELECT matrice_statut, q_score, a_score, completeness_score "
        "FROM dryrun_parcel_evaluations WHERE run_label = :run AND parcel_id = :pid"),
        {"run": run_label, "pid": parcel_id}).mappings().first()
    return ({"statut": r["matrice_statut"], "q_score": r["q_score"], "a_score": r["a_score"],
             "completeness_score": r["completeness_score"]} if r else None)


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
def pipeline_meta() -> dict:
    """Colonnes & priorités (config) pour piloter le Kanban côté front."""
    cfg = _pipeline_cfg()
    return {"columns": cfg.get("columns", []), "priorities": cfg.get("priorities", []),
            "defaults": cfg.get("defaults", {})}


@app.get("/pipeline")
def pipeline_list(db: Session = Depends(get_db)) -> list[dict]:
    entries = db.execute(
        select(models.PipelineEntry).order_by(models.PipelineEntry.created_at.desc())
    ).scalars().all()
    return [_entry_dict(db, e) for e in entries]


@app.get("/pipeline/parcel/{idu}")
def pipeline_for_parcel(idu: str, db: Session = Depends(get_db)) -> dict:
    _check_idu(idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    e = db.execute(
        select(models.PipelineEntry).where(models.PipelineEntry.parcel_id == p.id)
    ).scalar_one_or_none()
    return {"in_pipeline": bool(e), "entry": _entry_dict(db, e) if e else None}


@app.post("/pipeline")
def pipeline_add(body: PipelineAddIn, db: Session = Depends(get_db)) -> dict:
    _check_idu(body.idu)
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == body.idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    existing = db.execute(
        select(models.PipelineEntry).where(models.PipelineEntry.parcel_id == p.id)
    ).scalar_one_or_none()
    if existing:                                            # déjà suivie → on renvoie son état courant
        return {"ok": True, "already": True, "entry": _entry_dict(db, existing)}

    dfl = _pipeline_cfg().get("defaults", {})
    status = body.status or dfl.get("status", "reperee")
    priority = body.priority or dfl.get("priority", "moyenne")
    if status not in _col_keys():
        raise HTTPException(422, f"Statut invalide : {status}")
    if priority not in _prio_keys():
        raise HTTPException(422, f"Priorité invalide : {priority}")
    try:
        prosp = prospection.merge_prospection(prospection.default_prospection(), body.prospection)
    except ValueError as exc:
        raise HTTPException(422, f"Prospection invalide : {exc}") from None
    projet_id = None
    if body.projet_id is not None:
        if not db.get(models.Projet, body.projet_id):
            raise HTTPException(404, "Projet inconnu")
        projet_id = body.projet_id
    e = models.PipelineEntry(parcel_id=p.id, status=status, priority=priority,
                             notes=(body.notes or ""), prospection=prosp, projet_id=projet_id)
    db.add(e)
    db.flush()
    return {"ok": True, "already": False, "entry": _entry_dict(db, e)}


@app.patch("/pipeline/{entry_id}")
def pipeline_patch(entry_id: int, body: PipelinePatchIn, db: Session = Depends(get_db)) -> dict:
    e = db.get(models.PipelineEntry, entry_id)
    if not e:
        raise HTTPException(404, "Entrée de pipeline inconnue")
    if body.status is not None:
        if body.status not in _col_keys():
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
def pipeline_delete(entry_id: int, db: Session = Depends(get_db)) -> dict:
    e = db.get(models.PipelineEntry, entry_id)
    if not e:
        raise HTTPException(404, "Entrée de pipeline inconnue")
    db.delete(e)
    db.flush()
    return {"ok": True}


# ───────────────────────────── Front statique (carte + dashboard + fiche §8) ─────────────────────────────

# ── Modules outils (Vague 1+) ──
from .dossier import router as _dossier_router  # noqa: E402
from .events import router as _events_router  # noqa: E402
from .ia import router as _ia_router  # noqa: E402
from .modules import router as _modules_router  # noqa: E402
from .moteurs import router as _moteurs_router  # noqa: E402
from .partners import router as _partners_router  # noqa: E402
from .pre_dossier import router as _pre_dossier_router  # noqa: E402
from .projets import router as _projets_router  # noqa: E402
from .protection import router as _protection_router  # noqa: E402
from .segments import router as _segments_router  # noqa: E402
from .tiles import router as _tiles_router  # noqa: E402

app.include_router(_modules_router)
app.include_router(_dossier_router)
app.include_router(_pre_dossier_router)
app.include_router(_protection_router)
app.include_router(_tiles_router)
app.include_router(_ia_router)
app.include_router(_events_router)
app.include_router(_moteurs_router)
app.include_router(_partners_router)
app.include_router(_projets_router)
app.include_router(_segments_router)


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

if WEB_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(WEB_DIR), html=True), name="app")  # UI Vue historique (transition)


@app.get("/", include_in_schema=False)
def _root() -> RedirectResponse:
    if FRONTEND_DIST.exists():
        return RedirectResponse("/socle/")
    return RedirectResponse("/app/" if WEB_DIR.exists() else "/docs")


if FRONTEND_DIST.exists():
    app.mount("/socle", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="socle")  # Socle V1
