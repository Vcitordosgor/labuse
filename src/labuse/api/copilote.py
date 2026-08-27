"""M26-A — API du Copilote : runs, SSE, réponse de clarification, annulation.

Tout est DÉRIVÉ de l'event log (source de vérité unique). Le SSE rejoue les événements
existants (`after_seq` → reprise sans doublon ni trou) puis streame les nouveaux par
polling de la table agent_events (intervalle _POLL_S — pas de LISTEN/NOTIFY en M26-A,
décision GO). À la déconnexion du client, le générateur est fermé par Starlette : le run
continue en arrière-plan, un rafraîchissement retombe sur le même fil via after_seq.

Quota (emplacement M23) : compté AVANT run_started, kind='agent', même scope que la
propriété du run (décision Vic GO Q2) : compte connecté → sujet « c:<compte_id> » ;
bucket pilote (compte NULL) → sujet session/IP de protection.sujet_de. Dépassement →
429 honnête, même style que M23. LABUSE_DEV_MODE=1 désactive (comme partout).
"""
from __future__ import annotations

import json
import time
from datetime import date
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from ..copilote import events as ev
from ..copilote.executeur import demarrer_run, versions_moteurs
from ..copilote.interpreteur import MISSIONS
from ..copilote.plans import plan_serialise
from ..db import session_scope
from .protection import compteur_incr_et_lire, sujet_de
from .tenant import current_compte

router = APIRouter(prefix="/api/copilote", tags=["copilote"])

_POLL_S = 0.4          # intervalle de polling SSE (documenté M26A_RAPPORT)
_SSE_MAX_S = 180.0     # filet : un flux SSE ne survit pas à 1,5× le budget d'un run


def get_db() -> Iterator[Session]:
    with session_scope() as s:
        yield s


def _sujet_quota(request: Request) -> str:
    cid = current_compte(request)
    return f"c:{cid}" if cid is not None else sujet_de(request)


def _valider_run_id(run_id: str) -> str:
    """GB-028 — un run_id non-UUID doit donner un 422 PROPRE, jamais un 500 (le CAST(:r AS uuid) en
    base lève `invalid input syntax for type uuid` → DataError → 500). On valide le format AVANT la
    requête. Couvre tous les endpoints /runs/{run_id}* (chacun passe par _run_ou_404 en premier)."""
    import uuid as _uuid
    try:
        _uuid.UUID(str(run_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(422, "run_id invalide : un identifiant de run est un UUID.")
    return run_id


def _run_ou_404(db: Session, run_id: str, request: Request) -> dict:
    _valider_run_id(run_id)
    row = db.execute(text(
        "SELECT id::text AS id, mission, status, brief_raw, brief_json, engine_versions, "
        "       created_at, finished_at "
        "FROM agent_runs WHERE id = CAST(:r AS uuid) "
        "  AND compte_id IS NOT DISTINCT FROM :cid"),
        {"r": run_id, "cid": current_compte(request)}).mappings().first()
    if row is None:
        raise HTTPException(404, "Run inconnu.")
    return dict(row)


class RunIn(BaseModel):
    mission: str
    brief_raw: str


class AnswerIn(BaseModel):
    reponse: str


@router.post("/runs")
def creer_run(body: RunIn, request: Request, db: Session = Depends(get_db)) -> dict:
    if body.mission not in MISSIONS:
        raise HTTPException(422, f"Mission inconnue « {body.mission} » — "
                                 f"missions M26-A : {', '.join(MISSIONS)}.")
    if not body.brief_raw.strip():
        raise HTTPException(422, "brief_raw vide.")

    s = config.get_settings()
    if not s.dev_mode:
        sujet = _sujet_quota(request)
        from ..tz import today_reunion   # R2 — quota jour aligné minuit Réunion
        n = compteur_incr_et_lire(today_reunion().isoformat(), sujet, "agent")
        if n > s.copilote_quota_jour:
            # Même style de 429 que M23 (protection.py) : detail + quota + gel_jusqua.
            return JSONResponse(status_code=429, content={
                "detail": f"Quota Copilote atteint ({s.copilote_quota_jour} runs/jour). "
                          "Reprend à minuit.",
                "quota": s.copilote_quota_jour, "gel_jusqua": "minuit"})

    info = getattr(request.state, "compte_id", None)
    utilisateur_id = None
    # session_info pose compte_id ; l'utilisateur précis (si session utilisateur) est
    # relu du token — best-effort, nullable par conception.
    try:
        from . import auth
        si = auth.session_info(request.cookies.get(auth.COOKIE))
        if si:
            utilisateur_id = si.get("utilisateur_id")
    except Exception:  # noqa: BLE001 — auth pilote sans table utilisateurs
        pass

    run_id = db.execute(text(
        "INSERT INTO agent_runs (compte_id, utilisateur_id, mission, brief_raw, engine_versions) "
        "VALUES (:cid, :uid, :m, :b, CAST(:v AS jsonb)) RETURNING id::text"),
        {"cid": info, "uid": utilisateur_id, "m": body.mission, "b": body.brief_raw,
         "v": json.dumps(versions_moteurs(), ensure_ascii=False)}).scalar_one()
    db.commit()
    ev.emit(db, run_id, "run_started",
            {"mission": body.mission, "brief_raw": body.brief_raw,
             "plan": plan_serialise(body.mission)})
    demarrer_run(run_id)
    return {"run_id": run_id}


@router.get("/runs")
def lister_runs(request: Request, limit: int = Query(20, ge=1, le=100),
                offset: int = Query(0, ge=0), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text(
        "SELECT id::text AS run_id, mission, status, brief_raw, created_at, finished_at "
        "FROM agent_runs WHERE compte_id IS NOT DISTINCT FROM :cid "
        "ORDER BY created_at DESC LIMIT :l OFFSET :o"),
        {"cid": current_compte(request), "l": limit, "o": offset}).mappings().all()
    return {"runs": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.get("/runs/{run_id}")
def detail_run(run_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run_ou_404(db, run_id, request)
    # Récap DÉRIVÉ de l'event log (le statut servi est recalculé, jamais le cache seul).
    evts = ev.events_after(db, run_id, 0)
    row["status"] = ev.reduce_run([e["kind"] for e in evts])
    recap = next((e["payload"] for e in reversed(evts)
                  if e["kind"] in ("run_completed", "run_failed")), None)
    clarif = next((e["payload"] for e in reversed(evts)
                   if e["kind"] == "clarification_requested"), None)
    row["recap"] = recap
    row["clarification"] = clarif if row["status"] == "awaiting_user" else None
    row["n_events"] = len(evts)
    return row


@router.get("/runs/{run_id}/events")
def flux_events(run_id: str, request: Request,
                after_seq: int = Query(0, ge=0)) -> StreamingResponse:
    # Contrôle d'accès AVANT d'ouvrir le flux (session courte dédiée).
    with session_scope() as db:
        _run_ou_404(db, run_id, request)

    def _stream():
        dernier = after_seq
        debut = time.monotonic()
        while True:
            with session_scope() as db:
                lot = ev.events_after(db, run_id, dernier)
                statut = ev.run_status(db, run_id)
            for e in lot:
                dernier = e["seq"]
                yield (f"id: {e['seq']}\nevent: {e['kind']}\n"
                       f"data: {json.dumps(e, ensure_ascii=False, default=str)}\n\n")
            if statut in ev.TERMINAL or statut == "awaiting_user":
                yield f"event: fin\ndata: {json.dumps({'status': statut})}\n\n"
                return
            if time.monotonic() - debut > _SSE_MAX_S:
                yield "event: fin\ndata: {\"status\": \"flux_expire\"}\n\n"
                return
            time.sleep(_POLL_S)

    return StreamingResponse(_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.post("/runs/{run_id}/answer")
def repondre(run_id: str, body: AnswerIn, request: Request,
             db: Session = Depends(get_db)) -> dict:
    _run_ou_404(db, run_id, request)
    if ev.run_status(db, run_id) != "awaiting_user":
        raise HTTPException(409, "Ce run n'attend pas de réponse.")
    if not body.reponse.strip():
        raise HTTPException(422, "Réponse vide.")
    ev.emit(db, run_id, "clarification_answered", {"reponse": body.reponse.strip()})
    demarrer_run(run_id)
    return {"run_id": run_id, "status": "interpreting"}


@router.post("/runs/{run_id}/cancel")
def annuler(run_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    _run_ou_404(db, run_id, request)
    statut = ev.run_status(db, run_id)
    if statut in ev.TERMINAL:
        raise HTTPException(409, f"Run déjà terminal ({statut}).")
    ev.emit(db, run_id, "run_cancelled", {"motif": "annulé par l'utilisateur"})
    return {"run_id": run_id, "status": "cancelled"}
