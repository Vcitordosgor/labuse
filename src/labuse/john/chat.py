"""JOHN-TAYLOR-1 — l'ORCHESTRATION du chat (onglet « John Taylor », admin seul).

Un tour de chat = (1) le plafond de coût, (2) le carnet de bord lu en tête, (3) une boucle d'OUTILS
(lecture + actions de la liste fermée) menée par Opus, (4) le verrou ANTI-INVENTION sur la réponse.

Doctrine : John ne fabrique rien. Il n'a que des outils de LECTURE (contexte réel) et la LISTE FERMÉE
d'actions (`actions.py`). Deux actions demandent « tu confirmes ? » et attendent un « oui » au tour
suivant (état `pending_action` porté par la conversation). Au plafond, John est en pause (aucun appel
modèle). Conversations gardées `john_conversations_jours` jours (purge au premier usage du jour).

Le modèle est appelé via `appel(...)` — INJECTABLE : les tests passent un faux appel (aucun réseau).
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import text

log = logging.getLogger("labuse.john.chat")

from . import actions as _actions
from . import budget, carnet, journal

DDL_CONV = """
CREATE TABLE IF NOT EXISTS john_conversations (
  id         bigserial PRIMARY KEY,
  cree_at    timestamptz NOT NULL DEFAULT now(),
  maj_at     timestamptz NOT NULL DEFAULT now(),
  compte_id  integer,
  pending    jsonb                     -- action en attente de confirmation {action, args} | null
)
"""
DDL_MSG = """
CREATE TABLE IF NOT EXISTS john_messages (
  id       bigserial PRIMARY KEY,
  conv_id  bigint NOT NULL REFERENCES john_conversations(id) ON DELETE CASCADE,
  ts       timestamptz NOT NULL DEFAULT now(),
  role     varchar(12) NOT NULL,        -- user | assistant
  contenu  text NOT NULL,
  sources  jsonb NOT NULL DEFAULT '[]'::jsonb
)
"""

_AFFIRMATIF = re.compile(r"^\s*(oui|ok|okay|d'accord|daccord|vas[- ]?y|confirme|je confirme|go|yes|ouais)\b", re.I)

# anti-invention : on réutilise les utilitaires de nombres du socle IA (format FR, tolérances).
from ..ai import core as _core  # noqa: E402


# ════════════════════════════════ Tables / rétention ════════════════════════════════
def ensure(db) -> None:
    db.execute(text(DDL_CONV))
    db.execute(text(DDL_MSG))
    journal.ensure(db)
    carnet.ensure(db)


def purger(db, jours: int) -> int:
    """Purge les conversations plus vieilles que `jours` (RGPD + hygiène). Retourne le nb purgé."""
    ensure(db)
    return db.execute(text(
        "DELETE FROM john_conversations WHERE cree_at < now() - make_interval(days => :j)"),
        {"j": max(1, jours)}).rowcount or 0


# ════════════════════════════════ Prompt système ════════════════════════════════
def construire_system(db) -> str:
    """Le prompt système de John : persona + doctrine + carnet de bord + liste fermée d'actions.
    Le carnet est lu EN TÊTE (le mandat : « lu au début de chaque conversation »)."""
    lignes = carnet.lignes_actives(db)
    carnet_txt = "\n".join(f"- [{l['type']}] {l['titre']} : {l['corps']}" for l in lignes) or "(carnet vide)"
    actions_txt = "\n".join(
        f"- {a['cle']} : {a['label']}" + (" — DEMANDE « tu confirmes ? »" if a["confirme"] else "")
        for a in _actions.catalogue())
    return (
        "Tu es JOHN TAYLOR, le second de bord de LABUSE (plateforme de préqualification foncière à La "
        "Réunion), nommé d'après le second du pirate La Buse. Tu es l'agent d'EXPLOITATION : tu réponds à "
        "Vic (administrateur) sur l'état de l'app — jobs, incidents, sources, runs, contrôles, "
        "sauvegardes, Radar, journaux, carnet de bord, rapports.\n\n"
        "TON : français simple, direct, sans jargon. Un clin d'œil de marin tout au plus, jamais de "
        "folklore dans une réponse technique.\n\n"
        "RÈGLE D'OR (anti-invention) : tu ne fabriques RIEN. Chaque affirmation s'appuie sur un résultat "
        "d'OUTIL que tu as réellement lu, et tu cites la donnée d'où elle vient. Si aucun outil ne porte "
        "la réponse, tu dis « je ne sais pas » — jamais une supposition. N'invente aucun chiffre : un "
        "nombre que tu donnes doit venir d'un résultat d'outil.\n\n"
        "LECTURE : tu as des outils de lecture (lire_jobs, lire_incidents, lire_sources, lire_runs, "
        "lire_controles, lire_sauvegardes, lire_radar, lire_journaux, lire_carnet, lire_rapports, "
        "lire_rapport, lire_job). Appelle-les pour fonder ta réponse. Tu n'as ni shell ni SQL.\n\n"
        "ACTIONS (seulement sur ordre EXPLICITE de Vic, jamais de ta propre initiative — liste fermée) :\n"
        f"{actions_txt}\n"
        "Hors de cette liste, tu refuses et tu expliques. Deux actions touchent les clients et ne se "
        "défont pas d'un clic (promouvoir un run, retirer une source) : le système te fera confirmer.\n\n"
        "CARNET DE BORD (fait foi) :\n"
        f"{carnet_txt}\n"
    )


# ════════════════════════════════ Appel modèle (injectable) ════════════════════════════════
def _appel_reel(*, model, system, messages, tools, max_tokens):
    # NB : on n'envoie PAS `temperature` (opus-5-5/haiku-5-5 la refusent). REPLI automatique si
    # l'identifiant tombe en not_found (ex. un « 5.5 » retiré) → lignée 4.x, jamais silencieux.
    import anthropic

    from ..ai_models import est_not_found, repli_pour
    client = anthropic.Anthropic(timeout=60, max_retries=1)

    def _tenter(m):
        return client.messages.create(model=m, max_tokens=max_tokens, system=system,
                                      tools=tools, messages=messages)
    try:
        return _tenter(model)
    except Exception as exc:  # noqa: BLE001
        rep = repli_pour(model)
        if rep and est_not_found(exc):
            log.warning("john-chat : modèle %s introuvable → repli %s", model, rep)
            return _tenter(rep)
        raise


def _bloc_to_dict(b) -> dict:
    """Normalise un bloc de réponse (objet SDK OU stub de test) → dict pour le ré-envoyer en historique."""
    t = getattr(b, "type", None) or (b.get("type") if isinstance(b, dict) else None)
    if t == "text":
        return {"type": "text", "text": getattr(b, "text", None) if not isinstance(b, dict) else b.get("text", "")}
    if t == "tool_use":
        g = (lambda k: getattr(b, k, None)) if not isinstance(b, dict) else (lambda k: b.get(k))
        return {"type": "tool_use", "id": g("id"), "name": g("name"), "input": g("input") or {}}
    return {"type": t}


def _texte_de(msg) -> str:
    return "".join(getattr(b, "text", "") for b in getattr(msg, "content", [])
                   if (getattr(b, "type", None) == "text")).strip()


# ════════════════════════════════ Anti-invention ════════════════════════════════
def _nombres_autorises(outils_vus: list[dict]) -> set[float]:
    """Tous les nombres présents dans les résultats d'outils lus pendant le tour (+ actions)."""
    nums: set[float] = set()
    for r in outils_vus:
        nums |= _core._numbers_in_context(r if isinstance(r, dict) else {"v": r})
    return nums


def anti_invention(prose: str, outils_vus: list[dict]) -> tuple[bool, str | None]:
    """Vrai si tout nombre de la réponse figure dans un résultat d'outil lu (tolérance format + petits
    entiers de tournure, comme le socle). Sinon (False, raison) → on remplace par un repli honnête."""
    allowed = _nombres_autorises(outils_vus)
    for m in _core._NUM_RE.finditer(prose):
        n = _core._norm_number(m.group())
        if n is None:
            continue
        if not _core._number_ok(n, allowed):
            return False, f"chiffre non sourcé « {m.group().strip()} » (absent des lectures)"
    return True, None


# ════════════════════════════════ Persistance conversation ════════════════════════════════
def _charger_conv(db, conversation_id, compte_id):
    if conversation_id:
        r = db.execute(text("SELECT id, pending FROM john_conversations WHERE id = :i"),
                       {"i": conversation_id}).mappings().first()
        if r:
            return r["id"], r["pending"]
    cid = db.execute(text(
        "INSERT INTO john_conversations (compte_id) VALUES (:c) RETURNING id"),
        {"c": compte_id}).scalar()
    return cid, None


def _historique_messages(db, conv_id, n: int = 10) -> list[dict]:
    rows = db.execute(text(
        "SELECT role, contenu FROM (SELECT id, role, contenu FROM john_messages "
        "WHERE conv_id = :c ORDER BY id DESC LIMIT :n) t ORDER BY id ASC"),
        {"c": conv_id, "n": n}).mappings().all()
    return [{"role": r["role"], "content": r["contenu"]} for r in rows]


def _poser_message(db, conv_id, role, contenu, sources=None):
    db.execute(text(
        "INSERT INTO john_messages (conv_id, role, contenu, sources) "
        "VALUES (:c, :r, :co, CAST(:s AS jsonb))"),
        {"c": conv_id, "r": role, "co": contenu, "s": json.dumps(sources or [], ensure_ascii=False)})
    db.execute(text("UPDATE john_conversations SET maj_at = now() WHERE id = :i"), {"i": conv_id})


def _set_pending(db, conv_id, pending):
    db.execute(text("UPDATE john_conversations SET pending = CAST(:p AS jsonb) WHERE id = :i"),
               {"p": json.dumps(pending, ensure_ascii=False) if pending else None, "i": conv_id})


# ════════════════════════════════ LE TOUR DE CHAT ════════════════════════════════
def repondre(db, message: str, *, conversation_id=None, compte_id=None, compte=None,
             appel=None, backend=None, settings=None, max_tours=6) -> dict:
    """Un tour de chat. Rend {conversation_id, texte, sources, action, besoin_confirmation, pause, cout}."""
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    ensure(db)
    purger(db, int(getattr(settings, "john_conversations_jours", 90)))
    appel = appel or _appel_reel
    backend = backend or _actions.Backend()
    conv_id, pending = _charger_conv(db, conversation_id, compte_id)
    _poser_message(db, conv_id, "user", message)

    # (0) plafond de coût — coupure propre, aucun appel modèle.
    e = budget.etat(db, settings)
    if e.en_pause:
        msg = budget.message_pause(e)
        _poser_message(db, conv_id, "assistant", msg)
        return {"conversation_id": conv_id, "texte": msg, "sources": [], "pause": True,
                "cout": e.to_json()}

    # (1) une action attend « tu confirmes ? » et l'utilisateur dit oui → on exécute (confirme=True).
    if pending and _AFFIRMATIF.match(message):
        res = _actions.executer(db, pending["action"], pending.get("args") or {},
                                compte_id=compte_id, compte=compte, confirme=True, backend=backend)
        _set_pending(db, conv_id, None)
        texte = f"C'est fait : {res.get('resume')}." if res.get("ok") else f"Pas fait : {res.get('resume')}."
        _poser_message(db, conv_id, "assistant", texte)
        return {"conversation_id": conv_id, "texte": texte, "sources": [], "action": res,
                "cout": budget.etat(db, settings).to_json()}
    if pending and not _AFFIRMATIF.match(message):
        _set_pending(db, conv_id, None)   # tout autre message annule l'attente de confirmation

    # (2) boucle d'outils menée par le modèle.
    system = construire_system(db)
    tools = _tools_modele()
    msgs = _historique_messages(db, conv_id, 10) + [{"role": "user", "content": message}]
    outils_vus: list[dict] = []
    action_faite = None
    texte = ""
    for _ in range(max_tours):
        reponse = appel(model=_core.model_for("john-chat"), system=system, messages=msgs,
                        tools=tools, max_tokens=1200)
        # coût au ledger (best-effort — ne bloque jamais le chat)
        try:
            u = getattr(reponse, "usage", None)
            if u is not None:
                _core._log_cost(db, "john-chat", _core.model_for("john-chat"), False,
                                getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0))
        except Exception:  # noqa: BLE001
            pass
        blocs = list(getattr(reponse, "content", []))
        tool_uses = [b for b in blocs if getattr(b, "type", None) == "tool_use"]
        if not tool_uses:
            texte = _texte_de(reponse)
            break
        # rejoue l'assistant (avec ses tool_use) puis les résultats
        msgs.append({"role": "assistant", "content": [_bloc_to_dict(b) for b in blocs]})
        resultats = []
        for tu in tool_uses:
            nom = getattr(tu, "name", "")
            entree = getattr(tu, "input", None) or {}
            res, stop = _executer_outil(db, nom, entree, compte_id, compte, backend)
            outils_vus.append(res)
            if stop is not None:            # action en attente de confirmation
                _set_pending(db, conv_id, stop)
                q = stop["question"]
                _poser_message(db, conv_id, "assistant", q)
                return {"conversation_id": conv_id, "texte": q, "sources": [],
                        "besoin_confirmation": True, "action": stop["action"],
                        "cout": budget.etat(db, settings).to_json()}
            if res.get("_action"):
                action_faite = res["_action"]
            resultats.append({"type": "tool_result", "tool_use_id": getattr(tu, "id", None),
                              "content": json.dumps(res, ensure_ascii=False, default=str)})
        msgs.append({"role": "user", "content": resultats})
    else:
        texte = texte or "Je me suis arrêté après plusieurs lectures sans conclure. Reformule ta question ?"

    # (3) anti-invention sur la réponse finale.
    if texte:
        ok, raison = anti_invention(texte, outils_vus)
        if not ok:
            # on N'AFFICHE PAS la prose douteuse ni le chiffre fautif (le `raison` reste pour le log) :
            # « en cas de doute, on n'affiche pas ».
            texte = ("Je préfère ne pas répondre là-dessus : je n'ai pas de donnée qui le porte "
                     "(un chiffre de ma réponse n'était pas sourcé).")
    else:
        texte = "Je n'ai rien à dire de sourcé sur ce point pour l'instant."

    _poser_message(db, conv_id, "assistant", texte)
    return {"conversation_id": conv_id, "texte": texte, "sources": [],
            "action": action_faite, "cout": budget.etat(db, settings).to_json()}


def _executer_outil(db, nom, entree, compte_id, compte, backend):
    """Aiguille un appel d'outil du modèle : lecture (outils.dispatch) ou action (actions.executer).
    Retourne (resultat_dict, stop) où `stop` ≠ None = action en attente de confirmation."""
    from . import outils
    if nom in outils.NOMS:
        return outils.dispatch(db, nom, entree), None
    if nom in _actions.ACTIONS:
        res = _actions.executer(db, nom, entree, compte_id=compte_id, compte=compte,
                                confirme=False, backend=backend)
        if res.get("besoin_confirmation"):
            return ({"besoin_confirmation": True, "question": res["question"]},
                    {"action": nom, "args": entree, "question": res["question"]})
        return {**res, "_action": res}, None
    return {"refuse": f"outil/action inconnu « {nom} » (hors liste)"}, None


def _tools_modele() -> list[dict]:
    """Les outils vus par le modèle : lecture + actions (la confirmation est gérée côté serveur)."""
    from . import outils
    acts = {
        "injecter_source": {"source_id": {"type": "integer"}, "source": {"type": "string"}},
        "relancer_job": {"nom": {"type": "string"}},
        "lancer_sauvegarde": {},
        "accepter_incident": {"cle": {"type": "string"}},
        "accepter_ecart": {"ref": {"type": "string"}, "raison": {"type": "string"}},
        "promouvoir_run": {"run": {"type": "string"}},
        "retirer_source": {"source_id": {"type": "integer"}, "source": {"type": "string"},
                           "raison": {"type": "string"}},
    }
    tools = list(outils.TOOLS)
    for a in _actions.ACTIONS.values():
        tools.append({"name": a.cle, "description": a.label + " (action — ordre de Vic).",
                      "input_schema": {"type": "object", "properties": acts.get(a.cle, {})}})
    return tools
