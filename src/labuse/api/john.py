"""JOHN-TAYLOR-1 — l'API de l'onglet « John Taylor » (page Données, ADMIN SEUL).

Tous les points passent par `exiger_admin` (401/403 sinon). Le chat, les actions, l'enquête et le
carnet sont servis ici ; le résumé du matin et la veille sont PRODUITS par des jobs et seulement LUS
ici (la production coûte un appel modèle, elle ne se déclenche pas à l'ouverture de l'onglet).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..db import session_scope
from ..john import actions as _actions
from ..john import budget as _budget
from ..john import carnet as _carnet
from ..john import chat as _chat
from ..john import enquete as _enquete
from ..john import resume as _resume
from ..john import veille as _veille

router = APIRouter(tags=["john"])


def _qui(info: dict) -> tuple[int | None, str]:
    """(compte_id, libellé) de l'admin à l'origine de l'ordre, pour le journal des actions."""
    cid = info.get("compte_id")
    label = info.get("email") or (f"compte {cid}" if cid else info.get("role") or "admin")
    return cid, str(label)[:120]


# ════════════════════════════════ L'onglet (lecture) ════════════════════════════════
@router.get("/admin/john")
def admin_john(request: Request) -> dict:
    """Le payload de l'onglet : état (actif/pause), coût du mois, résumé du matin, veille, carnet,
    propositions en attente, catalogue d'actions, journal récent. 100 % lecture."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..config import get_settings
    from ..john import journal as _journal
    s = get_settings()
    with session_scope() as db:
        etat = _budget.etat(db, s)
        _carnet.semer(db)       # idempotent : garantit le carnet de bord au premier affichage
        return {
            "actif": bool(getattr(s, "john_actif", True)),
            "cout": etat.to_json(),
            "resume_matin": _resume.dernier_resume(db),
            "veille": _veille.recentes(db, 20),
            "carnet": _carnet.lignes_actives(db),
            "carnet_propositions": _carnet.proposees(db),
            "actions": _actions.catalogue(),
            "journal": _journal.dernieres(db, 20),
        }


# ════════════════════════════════ Chat ════════════════════════════════
class ChatIn(BaseModel):
    message: str
    conversation_id: int | None = None


@router.post("/admin/john/chat")
def admin_john_chat(body: ChatIn, request: Request) -> dict:
    from .auth import exiger_admin
    info = exiger_admin(request)
    cid, label = _qui(info)
    with session_scope() as db:
        out = _chat.repondre(db, body.message, conversation_id=body.conversation_id,
                             compte_id=cid, compte=label)
        db.commit()
        return out


# ════════════════════════════════ Action directe (bouton / « oui ») ════════════════════════════════
class ActionIn(BaseModel):
    action: str
    args: dict | None = None
    confirme: bool = False


@router.post("/admin/john/action")
def admin_john_action(body: ActionIn, request: Request) -> dict:
    """Déclenche une action de la liste fermée depuis l'UI (ou confirme une action en attente).
    Journalisée avec le compte. Les actions à confirmation exigent `confirme=true`."""
    from .auth import exiger_admin
    info = exiger_admin(request)
    cid, label = _qui(info)
    with session_scope() as db:
        out = _actions.executer(db, body.action, body.args or {}, compte_id=cid, compte=label,
                                confirme=body.confirme)
        db.commit()
        return out


# ════════════════════════════════ Enquête sur incident ════════════════════════════════
class EnqueteIn(BaseModel):
    cle: str | None = None
    titre: str | None = None
    mode: str = "casse"          # casse | code


@router.post("/admin/john/enquete")
def admin_john_enquete(body: EnqueteIn, request: Request) -> dict:
    from .auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        out = _enquete.enqueter(db, cle=body.cle, titre=body.titre, mode=body.mode)
        db.commit()
        return out


# ════════════════════════════════ Carnet de bord ════════════════════════════════
class CarnetProposeIn(BaseModel):
    type: str
    titre: str
    corps: str


@router.post("/admin/john/carnet/proposer")
def admin_john_carnet_proposer(body: CarnetProposeIn, request: Request) -> dict:
    from .auth import exiger_admin
    info = exiger_admin(request)
    _, label = _qui(info)
    with session_scope() as db:
        ident = _carnet.proposer(db, type=body.type, titre=body.titre, corps=body.corps, par=label)
        db.commit()
        return {"ok": True, "id": ident}


@router.post("/admin/john/carnet/{ligne_id}/valider")
def admin_john_carnet_valider(ligne_id: int, request: Request) -> dict:
    from .auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        ok = _carnet.valider(db, ligne_id)
        db.commit()
        return {"ok": ok}


@router.post("/admin/john/carnet/{ligne_id}/rejeter")
def admin_john_carnet_rejeter(ligne_id: int, request: Request) -> dict:
    from .auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        ok = _carnet.rejeter(db, ligne_id)
        db.commit()
        return {"ok": ok}
