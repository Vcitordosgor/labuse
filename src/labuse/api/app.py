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
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import config, models, prospection
from ..db import session_scope
from ..enums import FeedbackVerdict

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


@app.get("/demo-status")
def demo_status_endpoint(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Niveau 4 — état COMPLET de la démo (healthcheck 13 points, parcelles de démo
    conformes, cache chaud) + actions à lancer. Toujours 200 (informatif, panneau admin) ;
    le drapeau `ready_for_demo` fait foi."""
    from .. import state

    name = commune or config.get_settings().pilot_commune_name
    return state.demo_status(db, name)


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


@app.get("/parcels")
def list_parcels(commune: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(models.Parcel).order_by(models.Parcel.idu)
    if commune:
        stmt = stmt.where(models.Parcel.commune == commune)
    parcels = db.execute(stmt).scalars().all()
    out = []
    for p in parcels:
        ev = _latest_eval(db, p.id)
        out.append({
            "idu": p.idu, "commune": p.commune, "surface_m2": p.surface_m2,
            "status": ev.status.value if ev else None,
            "opportunity_score": ev.opportunity_score if ev else None,
            "completeness_score": ev.completeness_score if ev else None,
        })
    return out


@app.get("/stats")
def stats(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Cartouches du dashboard : volumétrie + statuts + scores (dernière évaluation)."""
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


@app.get("/map/parcels.geojson")
def parcels_geojson(commune: str | None = None, limit: int = Query(60000, ge=0, le=200000), db: Session = Depends(get_db)) -> dict:
    """Parcelles (géométrie simplifiée 4326) + verdict, pour la carte colorée."""
    rows = db.execute(
        text(
            """
            SELECT p.idu, p.surface_m2,
                   ST_AsGeoJSON(ST_SimplifyPreserveTopology(p.geom, 0.00002)) AS g,
                   e.status, e.opportunity_score, e.completeness_score, d.detail AS downgrade_reason
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
            },
        }
        for r in rows if r["g"]
    ]
    return {"type": "FeatureCollection", "features": feats}


@app.get("/parcels/{idu}")
def parcel_fiche(idu: str, db: Session = Depends(get_db)) -> dict:
    """Fiche « Tout ce que LA BUSE a trouvé » (§8)."""
    return _build_fiche(db, idu)


def _build_fiche(db: Session, idu: str) -> dict:
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
    verdict_block = {
        "status": ev.status.value if ev else None,
        "opportunity_score": ev.opportunity_score if ev else None,
        "completeness_score": ev.completeness_score if ev else None,
        "reasons": reasons,
        # Motif de déclassement (garde-fou faux positifs), si la parcelle a été corrigée.
        "downgrade_reason": next((r["detail"] for r in cascade if r["layer_name"] == "declassement"), None),
        "evaluated_at": ev.evaluated_at if ev else None,
        "rules_version": ev.rules_version if ev else None,
    }
    # Résumé « business » (Phase 2) — dérivé des signaux ci-dessus, repris dans les exports.
    from .resume import build_resume
    resume = build_resume(verdict_block, cascade, faisabilite, prosp_block)

    # Assemblage foncier (Phase 5) — voisines adjacentes + drapeau prudent (requête indexée).
    from .voisinage import compute_voisinage
    voisinage = compute_voisinage(db, p.id, p.surface_m2, verdict_block["status"])

    return {
        "parcel": {
            "idu": p.idu, "commune": p.commune, "section": p.section, "numero": p.numero,
            "surface_m2": p.surface_m2, "centroid": {"lon": lon, "lat": lat},
        },
        "resume": resume,
        "voisinage": voisinage,
        "faisabilite": faisabilite,
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


@app.get("/parcels/{idu}/enrichment")
def parcel_enrichment(idu: str, db: Session = Depends(get_db)) -> dict:
    """Bloc « promoteur » (altimétrie, façade, PLU détaillé, propriété, réseaux) — LAZY-LOAD.

    Sépare les appels externes LENTS (RGE ALTI ~1,5 s, prescriptions GPU ~2-6 s) de
    l'ouverture de la fiche : calculés UNE FOIS puis mis en cache (parcel_enrichment), et
    chargés en arrière-plan par le front → la fiche s'ouvre immédiatement. Jamais de 500
    (chaque section est isolée par `_safe`)."""
    from .enrichment import enrichment_cached

    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    lon, lat = db.execute(
        select(func.ST_X(p.__class__.centroid), func.ST_Y(p.__class__.centroid)).where(models.Parcel.id == p.id)
    ).one()
    payload = enrichment_cached(db, p, lon, lat)
    ca = db.execute(text("SELECT computed_at FROM parcel_enrichment WHERE parcel_id = :p"), {"p": p.id}).scalar()
    return {**payload, "computed_at": ca.isoformat() if ca else None}


@app.get("/parcels/{idu}/export")
def export_fiche(idu: str, format: str = Query("md", pattern="^(md|html)$"), db: Session = Depends(get_db)):
    """Export fiche premium (§12 étape 10) : Markdown (?format=md) ou HTML (?format=html)."""
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from .export import fiche_html, fiche_markdown

    fiche = _build_fiche(db, idu)
    if format == "html":
        return HTMLResponse(fiche_html(fiche))
    return PlainTextResponse(fiche_markdown(fiche), media_type="text/markdown")


@app.post("/parcels/{idu}/evaluate")
def evaluate_one(idu: str, ai: bool = Query(False), db: Session = Depends(get_db)) -> dict:
    from ..ai import get_provider
    from ..cascade import evaluate_parcels

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


# ───────────────────────────── Découverte (offre B) ─────────────────────────────

@app.get("/discover")
def discover(
    commune: str | None = None,
    min_opportunity: int = Query(0, ge=0, le=100),
    statuses: str = "opportunite,a_creuser",
    limit: int = Query(50, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Survivantes de la cascade, classées (radar). S'appuie sur la dernière évaluation."""
    wanted = {s.strip() for s in statuses.split(",") if s.strip()}
    # Dernière évaluation par parcelle (DISTINCT ON).
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (e.parcel_id) p.idu, p.commune, p.surface_m2,
                   e.status, e.opportunity_score, e.completeness_score, e.evaluated_at
            FROM parcel_evaluations e JOIN parcels p ON p.id = e.parcel_id
            WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
              AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)
            ORDER BY e.parcel_id, e.evaluated_at DESC
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


# ───────────────────────────── Feedback (§10) ─────────────────────────────

class FeedbackIn(BaseModel):
    idu: str
    verdict: FeedbackVerdict
    user_id: str | None = None
    comment: str | None = None


@app.post("/feedback")
def post_feedback(body: FeedbackIn, db: Session = Depends(get_db)) -> dict:
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
    }


class PipelineAddIn(BaseModel):
    idu: str
    status: str | None = None
    priority: str | None = None
    notes: str | None = None
    prospection: dict | None = None      # saisie MANUELLE (statut propriétaire, contact…)


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
    p = db.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    e = db.execute(
        select(models.PipelineEntry).where(models.PipelineEntry.parcel_id == p.id)
    ).scalar_one_or_none()
    return {"in_pipeline": bool(e), "entry": _entry_dict(db, e) if e else None}


@app.post("/pipeline")
def pipeline_add(body: PipelineAddIn, db: Session = Depends(get_db)) -> dict:
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
    e = models.PipelineEntry(parcel_id=p.id, status=status, priority=priority,
                             notes=(body.notes or ""), prospection=prosp)
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

if WEB_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(WEB_DIR), html=True), name="app")


@app.get("/", include_in_schema=False)
def _root() -> RedirectResponse:
    return RedirectResponse("/app/" if WEB_DIR.exists() else "/docs")
