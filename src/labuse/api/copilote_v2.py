"""M78 · Phase 2 — ENDPOINT HTTP du Copilote v2 (le câblage de la couche de réponse Phase 1).

POST /api/copilote-v2/ask   → une demande client → réponse instruite (routeur + outils + formulation).
GET  /api/copilote-v2/telemetrie → la feuille de route mesurée (§1e), triée par fréquence.

Sonnet partout (doctrine). Chaque appel modèle est déjà journalisé dans `ia_log`. Les plafonds (1f)
sont en config (`copilote_v2_*`) — l'enforcement par compte réutilise le mécanisme `protection.py`
existant (à brancher au test de charge ; ici la couche métier est câblée et testée par la véracité).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..copilote_v2.answering import answer
from ..copilote_v2 import telemetrie

router = APIRouter(prefix="/api/copilote-v2", tags=["copilote-v2"])


def get_db():
    from .app import get_db as _g
    yield from _g()


class AskIn(BaseModel):
    message: str
    history: list[dict] | None = None
    contexte: dict | None = None       # {idu} | {selection} des surfaces embarquées (Phase 5)


@router.post("/ask")
def ask(body: AskIn, db: Session = Depends(get_db)) -> dict:
    """Le client écrit, LABUSE instruit. Retourne {text, intent, tool?, refus?, porte?, partiel?, …}."""
    return answer(db, body.message, history=body.history, contexte=body.contexte)


@router.get("/telemetrie")
def resume(db: Session = Depends(get_db)) -> dict:
    """§1e — ce qu'on demande sans l'obtenir, trié par fréquence : la liste des prochains outils."""
    return {"lignes": telemetrie.resume(db)}
