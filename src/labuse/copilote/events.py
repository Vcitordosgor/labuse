"""M26-A — event log du Copilote : taxonomie FERMÉE, émission append-only, réduction.

Le dossier d'instruction EST la suite d'événements (Factors 5 + 12). Le champ
`agent_runs.status` n'est qu'un CACHE : il est TOUJOURS recalculable par
`reduce_run(events)`, fonction pure testée.

Taxonomie fermée — toute extension = décision Vic. `run_cancelled` a été ajouté à la
taxonomie du mandat (qui prévoit le statut `cancelled` et POST /cancel sans événement
correspondant : sans lui, le statut ne serait pas dérivable de l'event log). Soumis à
validation dans M26A_RAPPORT.md.
"""
from __future__ import annotations

import json
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .boussole import filtrer_payload

# ── Taxonomie (fermée) ──────────────────────────────────────────────────────────────────
KINDS = frozenset({
    "run_started", "brief_parsed", "clarification_requested", "clarification_answered",
    "step_started", "step_completed", "step_failed",
    "run_paused", "run_resumed", "run_completed", "run_failed", "run_cancelled",
})

STATUSES = ("interpreting", "awaiting_user", "running", "paused",
            "done", "failed", "cancelled")
TERMINAL = frozenset({"done", "failed", "cancelled"})

_TRANSITIONS = {
    "run_started": "interpreting",
    "brief_parsed": "running",
    "clarification_requested": "awaiting_user",
    "clarification_answered": "interpreting",
    "step_started": "running",
    "step_completed": "running",
    "step_failed": "running",           # l'échec TERMINAL est porté par run_failed
    "run_paused": "paused",
    "run_resumed": "running",
    "run_completed": "done",
    "run_failed": "failed",
    "run_cancelled": "cancelled",
}


def reduce_run(kinds: Sequence[str]) -> str:
    """Statut d'un run par RÉDUCTION de ses événements (fonction pure, source de vérité).

    Un état terminal est ABSORBANT : tout événement postérieur est ignoré (et `emit`
    refuse d'en écrire). Aucun événement → 'interpreting' (run créé, log pas encore écrit).
    """
    status = "interpreting"
    for kind in kinds:
        if status in TERMINAL:
            return status
        nxt = _TRANSITIONS.get(kind)
        if nxt is None:
            raise ValueError(f"événement hors taxonomie : {kind!r}")
        status = nxt
    return status


def run_status(db: Session, run_id: str) -> str:
    kinds = [r[0] for r in db.execute(
        text("SELECT kind FROM agent_events WHERE run_id = :r ORDER BY seq"),
        {"r": run_id}).all()]
    return reduce_run(kinds)


def emit(db: Session, run_id: str, kind: str, payload: dict | None = None) -> int:
    """Écrit UN événement (append-only) et rafraîchit le cache de statut du run.

    * kind validé contre la taxonomie fermée ;
    * payload passé au filtre boussole (aucune identité de personne physique) ;
    * seq strictement croissant par run (UNIQUE (run_id, seq), retry court en cas de
      course entre l'exécuteur et l'API — answer/cancel) ;
    * refuse d'écrire après un état terminal (l'event log ne « ressuscite » jamais).
    Renvoie le seq attribué.
    """
    if kind not in KINDS:
        raise ValueError(f"événement hors taxonomie : {kind!r}")
    current = run_status(db, run_id)
    if current in TERMINAL:
        raise RuntimeError(f"run {run_id} terminal ({current}) : émission de {kind} refusée")
    clean, n_filtres = filtrer_payload(payload or {})
    if n_filtres:
        clean["_boussole_filtre"] = n_filtres
    body = json.dumps(clean, ensure_ascii=False, default=str)

    last_err: Exception | None = None
    for _ in range(3):
        try:
            seq = int(db.execute(text(
                "INSERT INTO agent_events (run_id, seq, kind, payload) "
                "SELECT :r, COALESCE(MAX(seq), 0) + 1, :k, CAST(:p AS jsonb) "
                "FROM agent_events WHERE run_id = :r RETURNING seq"),
                {"r": run_id, "k": kind, "p": body}).scalar_one())
            break
        except IntegrityError as exc:      # course sur (run_id, seq) → on rejoue
            db.rollback()
            last_err = exc
    else:
        raise RuntimeError(f"emit {kind} : seq concurrent non résolu") from last_err

    status = _TRANSITIONS[kind] if current not in TERMINAL else current
    db.execute(text(
        "UPDATE agent_runs SET status = :s, updated_at = now(), "
        "finished_at = CASE WHEN :terminal THEN now() ELSE finished_at END "
        "WHERE id = :r"),
        {"s": status, "terminal": status in TERMINAL, "r": run_id})
    db.commit()
    return seq


def events_after(db: Session, run_id: str, after_seq: int = 0) -> list[dict]:
    """Événements d'un run après `after_seq` (rejeu SSE sans doublon ni trou)."""
    rows = db.execute(text(
        "SELECT seq, kind, payload, created_at FROM agent_events "
        "WHERE run_id = :r AND seq > :a ORDER BY seq"),
        {"r": run_id, "a": after_seq}).mappings().all()
    return [{"seq": r["seq"], "kind": r["kind"], "payload": r["payload"],
             "created_at": r["created_at"].isoformat()} for r in rows]
