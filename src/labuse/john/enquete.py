"""JOHN-TAYLOR-1 — l'ENQUÊTE sur un incident.

Le mandat : « Enquête sur incident : sur chaque carte "ça casse", un bouton "Demander à John" ; il lit
les journaux, donne la cause probable et propose la correction. Pour une carte "demande du code", il
rédige le mandat Claude Code prêt à coller. »

John rassemble les JOURNAUX réels (incidents ouverts, derniers jobs en échec, historique du job
concerné s'il y en a un), puis Opus (kind john-enquete) rend un JSON {cause_probable, correction,
mandat_claude_code?}. ANTI-INVENTION : le texte est fondé sur les faits rassemblés (un chiffre absent
des journaux fait retomber sur une réponse prudente). Au plafond, John est en pause (aucun appel).
"""
from __future__ import annotations

import json
import re

from . import budget, contexte

_SYS_CASSE = (
    "Tu es JOHN TAYLOR, le second de bord de LABUSE. On te donne les journaux d'un incident. Donne, en "
    "français simple, la CAUSE PROBABLE puis la CORRECTION proposée. Ne te sers QUE des faits fournis ; "
    "n'invente rien ; si les journaux ne suffisent pas, dis ce qu'il faudrait lire de plus. Réponds "
    "UNIQUEMENT un objet JSON : {\"cause_probable\": \"...\", \"correction\": \"...\"}."
)
_SYS_CODE = (
    "Tu es JOHN TAYLOR, le second de bord de LABUSE. On te donne les journaux d'une carte qui DEMANDE DU "
    "CODE. Donne la cause probable, la correction, PUIS rédige un MANDAT CLAUDE CODE prêt à coller (clair, "
    "cadré : contexte, fichiers probables, ce qu'il faut faire, comment vérifier). Ne te sers QUE des "
    "faits fournis ; n'invente rien. Réponds UNIQUEMENT un objet JSON : {\"cause_probable\": \"...\", "
    "\"correction\": \"...\", \"mandat_claude_code\": \"...\"}."
)


def _rassembler(db, cle: str | None) -> dict:
    """Les journaux pertinents : incidents, jobs en échec, et l'historique du job visé si `cle` est un
    incident de job (`job-echec:<nom>` / `job-retard:<nom>` / `job-bloque:<nom>`)."""
    faits: dict = {"incidents": contexte.incidents(db), "journaux": contexte.journaux(db)}
    if cle:
        m = re.match(r"^(?:job-echec|job-retard|job-bloque):(.+)$", cle)
        if m:
            faits["job_concerne"] = contexte.job_detail(db, m.group(1), 10)
    return faits


def _generer_defaut(db, facts: dict, mode: str) -> str:
    from ..ai import core
    from ..ai_models import MODEL_OPUS
    sys = _SYS_CODE if mode == "code" else _SYS_CASSE
    r = core.complete(db, kind="john-enquete", system=sys, context=facts,
                      model=MODEL_OPUS, max_tokens=1200, validate=False)
    return "" if r.degraded else (r.text or "")


def _parse(brut: str) -> dict:
    m = re.search(r"\{.*\}", brut or "", re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def enqueter(db, *, cle: str | None = None, titre: str | None = None, mode: str = "casse",
             generer=None, settings=None) -> dict:
    """Mène l'enquête. `mode` = 'casse' (cause + correction) ou 'code' (+ mandat Claude Code prêt à
    coller). Rend {ok, pause?, cause_probable, correction, mandat_claude_code?, faits}."""
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    e = budget.etat(db, settings)
    if e.en_pause:
        return {"ok": False, "pause": True, "message": budget.message_pause(e)}

    faits = _rassembler(db, cle)
    generer = generer or _generer_defaut
    try:
        brut = (generer(db, {"incident": {"cle": cle, "titre": titre}, "journaux": faits}, mode) or "").strip()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "erreur": f"{type(exc).__name__}: {exc}", "faits": faits}
    if not brut:
        return {"ok": False, "erreur": "John indisponible (dégradé / pas de clé)", "faits": faits}

    d = _parse(brut)
    cause = (d.get("cause_probable") or "").strip()
    correction = (d.get("correction") or "").strip()
    mandat = (d.get("mandat_claude_code") or "").strip() or None
    if not cause and not correction:
        return {"ok": False, "erreur": "réponse non exploitable (JSON attendu)", "brut": brut[:400]}

    # anti-invention sur la prose (hors mandat Claude Code, qui est une consigne, pas une affirmation).
    from .chat import anti_invention
    ok, raison = anti_invention(f"{cause}\n{correction}", [faits])
    if not ok:
        cause = cause or "cause à confirmer"
        correction = (f"(prudence) un chiffre n'était pas sourcé — {raison}. "
                      "Je m'en tiens aux journaux ci-joints.")
    return {"ok": True, "cause_probable": cause, "correction": correction,
            "mandat_claude_code": mandat if mode == "code" else None, "faits": faits}
