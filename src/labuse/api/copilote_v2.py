"""M78 · Phase 2 — ENDPOINT HTTP du Copilote v2 (le câblage de la couche de réponse Phase 1).

POST /api/copilote-v2/ask   → une demande client → réponse instruite (routeur + outils + formulation).
GET  /api/copilote-v2/telemetrie → la feuille de route mesurée (§1e), triée par fréquence.

Sonnet partout (doctrine). Chaque appel modèle est déjà journalisé dans `ia_log`. Les plafonds (1f)
sont en config (`copilote_v2_*`) — l'enforcement par compte réutilise le mécanisme `protection.py`
existant (à brancher au test de charge ; ici la couche métier est câblée et testée par la véracité).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..copilote_v2.answering import answer
from ..copilote_v2 import historique, telemetrie
from .tenant import current_compte

router = APIRouter(prefix="/api/copilote-v2", tags=["copilote-v2"])


def get_db():
    from .app import get_db as _g
    yield from _g()


class AskIn(BaseModel):
    message: str
    history: list[dict] | None = None
    contexte: dict | None = None       # {idu} | {selection} des surfaces embarquées (Phase 5)
    conversation_id: int | None = None  # §2b — reprendre une conversation existante


def _executer_projet(act: dict, request: Request, db: Session, rep: dict) -> dict:
    """§3b — CRÉATION RÉELLE via l'API projets existante (jamais d'écriture directe en base). Quand le
    Copilote dit « c'est fait », la chose EST faite et visible dans Projets. Parcelle citée → attachée."""
    from .projets import ProjetIn, projet_create
    res = projet_create(ProjetIn(fiche=act.get("fiche") or {}, nom=act.get("nom")), request, db)
    p = res["projet"]
    if act.get("idu"):
        try:
            from .app import PipelineAddIn, pipeline_add
            pipeline_add(PipelineAddIn(idu=act["idu"], projet_id=p["id"]), request, db)
        except Exception:   # l'attache ne doit pas faire échouer la création
            pass
    deja = " (il existait déjà)" if res.get("existing") else ""
    return {**rep, "text": f"Projet créé : {p['nom']}{deja} — le voir dans Projets.",
            "intent": "PROJET", "projet_id": p["id"]}   # navigation vers Projets = surface embarquée (Phase 5)


def _executer_veille(act: dict, request: Request, db: Session, rep: dict) -> dict:
    """§4 — pose RÉELLE d'une veille (trigger persisté). Plafond par compte (config). Confirmation
    explicite. L'ALERTE elle-même dépend du canal de notification (BACKLOG) — voir RAPPORT_M78."""
    from .. import config
    from ..copilote_v2 import veilles
    cid = current_compte(request)
    s = config.get_settings() if hasattr(config, "get_settings") else config.Settings()
    if veilles.compter_actives(db, cid) >= s.copilote_v2_veilles_max:
        return {**rep, "text": f"Vous avez atteint le plafond de {s.copilote_v2_veilles_max} veilles "
                "actives. Supprimez-en une pour en poser une nouvelle.", "refus": "plafond_veilles"}
    v = veilles.creer(db, compte_id=cid, type_=act["veille_type"], commune=act["commune"])
    label = veilles.TYPES.get(act["veille_type"], act["veille_type"])
    return {**rep, "text": f"Veille posée : {label} · {act['commune']} — vérification à chaque mise à "
            "jour des données, notification in-app.", "intent": "VEILLE", "veille_id": v["id"]}


@router.post("/ask")
def ask(body: AskIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Le client écrit, LABUSE instruit. Retourne {text, intent, …, conversation_id} (§2b : persisté)."""
    rep = answer(db, body.message, history=body.history, contexte=body.contexte)
    act = rep.pop("_action", None)                    # écriture réelle demandée → API existante
    if act and act.get("type") == "projet":
        rep = _executer_projet(act, request, db, rep)
    elif act and act.get("type") == "veille":
        rep = _executer_veille(act, request, db, rep)
    cid = historique.enregistrer(db, compte_id=current_compte(request),
                                 conversation_id=body.conversation_id, message=body.message, reponse=rep)
    return {**rep, "conversation_id": cid}


@router.get("/veilles")
def veilles_lister(request: Request, db: Session = Depends(get_db)) -> dict:
    """§4 — l'écran minimal : les veilles actives du compte (+ notifications non vues)."""
    from ..copilote_v2 import veilles
    return {"veilles": veilles.lister(db, current_compte(request))}


@router.delete("/veilles/{veille_id}")
def veille_supprimer(veille_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    from ..copilote_v2 import veilles
    return {"ok": veilles.supprimer(db, current_compte(request), veille_id)}


@router.get("/notifications")
def notifications(request: Request, db: Session = Depends(get_db)) -> dict:
    """§4 — les notifications STOCKÉES (la moitié livrée). Le CANAL qui les pousse au client (cloche,
    digest) est au BACKLOG — c'est la moitié manquante (RAPPORT_M78)."""
    from ..copilote_v2 import veilles
    return {"notifications": veilles.notifications(db, current_compte(request))}


@router.post("/veilles/evaluer")
def veilles_evaluer(db: Session = Depends(get_db)) -> dict:
    """§4 — point d'entrée du déclenchement (le CRON J+1 de prod appellera ceci après ingestion).
    ZÉRO modèle : SQL + notifications. Exposé pour le déclenchement simulé du STOP Phase 4."""
    from ..copilote_v2 import veilles
    return veilles.evaluer_toutes(db)


class HerosIn(BaseModel):
    parcelle: dict                       # la meilleure parcelle (payload restituees[0])
    budget_max_eur: float | None = None  # pour dire « au-dessus de votre budget » sans inventer


@router.post("/heros")
def heros(body: HerosIn, db: Session = Depends(get_db)) -> dict:
    """§2e — phrase du héros (pourquoi cette parcelle gagne, faiblesses comprises) avec verrou
    anti-invention : tout nombre ∈ JSON parcelle, sinon gabarit sans modèle. Retourne {phrase, gabarit}."""
    from ..copilote_v2 import heros as _h
    return _h.phrase(db, body.parcelle, body.budget_max_eur)


@router.get("/missions")
def missions(request: Request, db: Session = Depends(get_db)) -> dict:
    """§2b — les missions passées du compte (titre auto, date, statut) pour rouvrir."""
    return {"missions": historique.lister(db, current_compte(request))}


@router.get("/missions/{conversation_id}")
def mission(conversation_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """§2b — restaure une conversation et ses messages."""
    conv = historique.charger(db, current_compte(request), conversation_id)
    if conv is None:
        from fastapi import HTTPException
        raise HTTPException(404, "conversation introuvable")
    return conv


class FeedbackIn(BaseModel):
    conversation_id: int | None = None
    pouce: str                          # 'haut' | 'bas'
    commentaire: str | None = None      # le 👎 ouvre un champ libre optionnel


@router.post("/feedback")
def feedback(body: FeedbackIn, db: Session = Depends(get_db)) -> dict:
    """§2f — 👍/👎 sur une réponse. Rejoint la télémétrie (§1e). NB : canal télémétrie dédié
    (mission_id), pas /signalements (spécifique aux erreurs de DONNÉE parcelle) — écart consigné."""
    telemetrie.feedback(db, mission_id=str(body.conversation_id or ""),
                        pouce=body.pouce, commentaire=body.commentaire or "")
    return {"ok": True}


@router.get("/telemetrie")
def resume(db: Session = Depends(get_db)) -> dict:
    """§1e — ce qu'on demande sans l'obtenir, trié par fréquence : la liste des prochains outils."""
    return {"lignes": telemetrie.resume(db)}
