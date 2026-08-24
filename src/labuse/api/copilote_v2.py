"""M78 · Phase 2 — ENDPOINT HTTP du Copilote v2 (le câblage de la couche de réponse Phase 1).

POST /api/copilote-v2/ask   → une demande client → réponse instruite (routeur + outils + formulation).
GET  /api/copilote-v2/scenarios → les chips de contexte (M113) servis par le serveur, jamais en dur.
GET  /api/copilote-v2/telemetrie → la feuille de route mesurée (§1e), triée par fréquence.

Routeur sur haiku (M113·Ph0), sélection + formulation sur sonnet. Chaque appel modèle est déjà
journalisé dans `ia_log`. PLAFOND par compte sur `/ask` (FIX-COPILOTE F3) : quota journalier
`copilote_v2_missions_jour` compté dans `usage_compteurs` (kind='copilote_v2_ask') — MÊME mécanique
et MÊME stockage que le run lourd (`/copilote/runs`), scope `c:<compte_id>` (bucket pilote : session/IP
via `protection.sujet_de`). Aucun canal parallèle. Dépassement → 429 honnête (repart à minuit) AVANT
tout appel modèle. `LABUSE_DEV_MODE=1` désactive (comme partout).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import config
from ..copilote_v2.answering import accueil_publie, answer, scenarios_publies
from ..copilote_v2 import historique, telemetrie
from .protection import compteur_incr_et_lire, sujet_de
from .tenant import current_compte

router = APIRouter(prefix="/api/copilote-v2", tags=["copilote-v2"])


def _sujet_quota(request: Request) -> str:
    """Scope du quota `/ask`, IDENTIQUE au run lourd (copilote.py) : compte connecté → « c:<id> »,
    bucket pilote (compte NULL) → session/IP. On partage `usage_compteurs`, pas de canal parallèle."""
    cid = current_compte(request)
    return f"c:{cid}" if cid is not None else sujet_de(request)


def get_db():
    from .app import get_db as _g
    yield from _g()


class AskIn(BaseModel):
    message: str
    history: list[dict] | None = None
    contexte: dict | None = None       # {idu} | {selection} des surfaces embarquées (Phase 5)
    conversation_id: int | None = None  # §2b — reprendre une conversation existante
    confirme: bool = False             # §M78-bis — le client a validé le récap → produire la mission
    scenario: str | None = None        # M113 — chip de contexte choisi (force le scénario) ; None = texte libre


# M113 · Phase 3 — la CRÉATION DIRECTE de projet par le Copilote est RETIRÉE (formulaire guidé).
# FIX-VEILLE (option A) — la CRÉATION DE VEILLE au chat est retirée elle aussi : depuis M118, l'intent
# VEILLE renvoie vers la Surveillance (`_refus_voie`), et la pose se fait dans les zones de veille
# (`watch_zones` / alertes.py). L'ancien `_executer_veille` (qui posait une veille `copilote_v2.veilles`
# et confirmait « Veille posée ») était INATTEIGNABLE (aucun producteur d'`_action` veille) — retiré
# avec `preparer_veille`. Le Copilote ne pose plus rien qui ne s'évaluerait pas.


@router.post("/ask")
def ask(body: AskIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Le client écrit, LABUSE instruit. Retourne {text, intent, …, conversation_id} (§2b : persisté).

    M102 P1 (constat 2) — GARDE GÉNÉRALE : aucune exception (y compris une HTTPException levée
    par un outil aval — mesuré : 404 « absente du run q_v9_m81 » servi BRUT à l'écran) ne sort
    de cet endpoint. Message honnête au client, TRACE COMPLÈTE côté serveur — un garde qui
    échoue doit le dire, jamais un 500 (ni un identifiant technique) au visage de l'utilisateur."""
    # FIX-COPILOTE F3 — plafond par compte AVANT tout appel modèle (même mécanique/stockage que le
    # run lourd : usage_compteurs, kind distinct). Dépassement → 429 honnête, jamais un appel modèle
    # dépensé pour rien. `LABUSE_DEV_MODE=1` désactive.
    s = config.get_settings()
    if not s.dev_mode:
        n = compteur_incr_et_lire(date.today().isoformat(), _sujet_quota(request), "copilote_v2_ask")
        if n > s.copilote_v2_missions_jour:
            return JSONResponse(status_code=429, content={
                "detail": f"Vous avez atteint la limite quotidienne du Copilote "
                          f"({s.copilote_v2_missions_jour} échanges par jour). Elle repart à minuit.",
                "quota": s.copilote_v2_missions_jour, "gel_jusqua": "minuit"})
    import logging
    log = logging.getLogger("labuse.copilote_v2")
    payload_tour = None
    try:
        # M102-B1 — LE FIL ALIMENTE L'INTERPRÉTATION : quand une conversation est en cours, le
        # serveur recharge les derniers tours (history) et le contexte du dernier tour Copilote
        # (prior_params) — plus jamais un routage à froid après une clarification. Le contexte a
        # une durée de vie bornée (config copilote_v2_contexte_ttl_minutes) ; conversation_id
        # absent = fil neuf (repartir de zéro). `body.history` reste un appoint des surfaces
        # embarquées quand il n'y a pas de conversation persistée.
        history, prior, faits_fil = body.history, None, None
        if body.conversation_id is not None:
            from .. import config as _cfg
            from ..copilote_v2 import registre_faits
            s = _cfg.get_settings() if hasattr(_cfg, "get_settings") else _cfg.Settings()
            # FIX-COPILOTE F6 — défaut de repli ALIGNÉ sur la config (10) et sur le TTL servi au front
            # (plus bas) : plus de divergence 120 vs 10 (le fil rechargé et l'annonce d'expiration
            # parlaient de fenêtres différentes si le champ venait à manquer).
            ttl = int(getattr(s, "copilote_v2_contexte_ttl_minutes", 10))
            fil_h, fil_p = historique.fil(db, current_compte(request), body.conversation_id, ttl)
            if fil_h:
                history, prior = fil_h, (fil_p or {}).get("params") or None
            # M102-B3 — le REGISTRE DE FAITS du fil (mêmes bornes que le fil) : l'oracle des
            # chiffres repris d'un tour antérieur.
            faits_fil = registre_faits.du_fil(db, current_compte(request), body.conversation_id, ttl)
        rep = answer(db, body.message, history=history, contexte=body.contexte,
                     confirme=body.confirme, prior_params=prior, faits_fil=faits_fil,
                     scenario=body.scenario)
        payload_tour = rep.pop("_route", None)        # contexte du tour → persistance, jamais servi
        rep.pop("_action", None)                       # FIX-VEILLE (A) : plus aucun `_action` — la création
        # de veille au chat est retirée (M118). On dépile la clé par sécurité, mais rien ne la produit.
    except Exception:  # noqa: BLE001 — garde générale M102 : trace serveur, réponse honnête
        log.exception("copilote /ask — exception non prévue (message=%r)", (body.message or "")[:200])
        db.rollback()
        rep = {"text": "Je n'ai pas su traiter cette demande — l'incident est enregistré côté "
                       "serveur. Reformulez-la autrement, ou réessayez dans un instant.",
               "intent": None, "erreur": True}
    rep.pop("_route", None)                           # ceinture : jamais servi, même sur un chemin d'action
    faits_tour = rep.pop("_faits_tour", None)         # M102-B3 — faits du tour → registre, jamais servis
    cid = historique.enregistrer(db, compte_id=current_compte(request),
                                 conversation_id=body.conversation_id, message=body.message,
                                 reponse=rep, payload=payload_tour)
    if faits_tour and cid is not None:
        from ..copilote_v2 import registre_faits
        registre_faits.enregistrer(db, cid, faits_tour)
    # M107 P3 — le TTL du fil VOYAGE vers le front (jamais une constante recopiée) : l'écran
    # arme son minuteur d'inactivité dessus et ANNONCE l'expiration (« nouvelle conversation »).
    from .. import config as _cfg2
    ttl_servi = int(getattr(_cfg2.get_settings(), "copilote_v2_contexte_ttl_minutes", 10))
    return {**rep, "conversation_id": cid, "contexte_ttl_minutes": ttl_servi}


@router.get("/scenarios")
def scenarios() -> dict:
    """M113 · Phase 2 — les missions, servies par le serveur (jamais en dur au front). M133 · Accueil
    v3 — la réponse porte AUSSI le hero (`accueil` : titre/sous-titre/placeholder/aide) + les 4
    capacités en texte (libellé + exemple réel). L'accueil ne renvoie PLUS de `scenario` forcé."""
    return {"scenarios": scenarios_publies(), "accueil": accueil_publie()}


@router.get("/veilles")
def veilles_lister(request: Request, db: Session = Depends(get_db)) -> dict:
    """§4 — l'écran minimal : les veilles actives du compte. M85 : les notifications qu'elles
    produisent vivent désormais dans le CENTRE (event_log, servi par la cloche /events), plus ici."""
    from ..copilote_v2 import veilles
    return {"veilles": veilles.lister(db, current_compte(request))}


@router.delete("/veilles/{veille_id}")
def veille_supprimer(veille_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    from ..copilote_v2 import veilles
    return {"ok": veilles.supprimer(db, current_compte(request), veille_id)}


# M85 — l'ancien GET /notifications (store parallèle veille_notifications) est SUPPRIMÉ : la cloche
# lit le centre unifié via /events. Plus de doublon (arbitrage Vic : le store parallèle disparaît).


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
