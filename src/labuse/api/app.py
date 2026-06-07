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
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import models
from ..db import session_scope
from ..enums import FeedbackVerdict

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(
    title="LA BUSE — radar foncier",
    version="0.1.0",
    description="La donnée publique ne suffit pas. LA BUSE l'interprète. "
                "Pré-analyse — constructibilité/propriété/rentabilité jamais garanties.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def get_db() -> Iterator[Session]:
    with session_scope() as s:
        yield s


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "produit": "LA BUSE"}


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
    return {k: (int(v) if v is not None else None) for k, v in row.items()}


@app.get("/map/parcels.geojson")
def parcels_geojson(commune: str | None = None, limit: int = 60000, db: Session = Depends(get_db)) -> dict:
    """Parcelles (géométrie simplifiée 4326) + verdict, pour la carte colorée."""
    rows = db.execute(
        text(
            """
            SELECT p.idu, p.surface_m2,
                   ST_AsGeoJSON(ST_SimplifyPreserveTopology(p.geom, 0.00002)) AS g,
                   e.status, e.opportunity_score, e.completeness_score
            FROM parcels p
            LEFT JOIN LATERAL (
                SELECT status, opportunity_score, completeness_score
                FROM parcel_evaluations e WHERE e.parcel_id = p.id
                ORDER BY evaluated_at DESC LIMIT 1
            ) e ON true
            WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
            LIMIT :lim
            """
        ), {"c": commune, "lim": limit}
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

    return {
        "parcel": {
            "idu": p.idu, "commune": p.commune, "section": p.section, "numero": p.numero,
            "surface_m2": p.surface_m2, "centroid": {"lon": lon, "lat": lat},
        },
        # En-tête : verdict + LES DEUX scores (jamais l'opportunité seule).
        "verdict": {
            "status": ev.status.value if ev else None,
            "opportunity_score": ev.opportunity_score if ev else None,
            "completeness_score": ev.completeness_score if ev else None,
            "reasons": reasons,
            "evaluated_at": ev.evaluated_at if ev else None,
            "rules_version": ev.rules_version if ev else None,
        },
        "cascade": cascade,
        "sources_responded": sources_responded,
        "sources_silent": sources_silent,
        "source_results": [dict(r) for r in source_results],
        "ai": ev.ai_payload if ev else None,
        "disclaimer": "Pré-analyse. Constructibilité, propriété, rentabilité, faisabilité jamais garanties.",
    }


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
    min_opportunity: int = 0,
    statuses: str = "opportunite,a_creuser",
    limit: int = 50,
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
            ORDER BY e.parcel_id, e.evaluated_at DESC
            """
        ), {"c": commune}
    ).mappings().all()
    survivors = [
        dict(r) for r in rows
        if r["status"] in wanted and (r["opportunity_score"] or 0) >= min_opportunity
    ]
    survivors.sort(key=lambda r: (r["opportunity_score"] or 0, r["completeness_score"] or 0), reverse=True)
    return survivors[:limit]


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


# ───────────────────────────── Front statique (carte + dashboard + fiche §8) ─────────────────────────────

if WEB_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(WEB_DIR), html=True), name="app")


@app.get("/", include_in_schema=False)
def _root() -> RedirectResponse:
    return RedirectResponse("/app/" if WEB_DIR.exists() else "/docs")
