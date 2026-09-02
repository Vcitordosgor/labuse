"""M26-A — exécuteur de runs : déroule le plan FIGÉ dans run_started, journalise tout.

Un run s'exécute dans un thread applicatif (décision plan M26-A : pas de worker séparé
en M26-A ; budget global 120 s). Chaque étape émet step_started puis
step_completed/step_failed. Erreurs compactées (Factor 9) : jamais de stacktrace en
payload — elle part dans les logs serveur. Retry automatique : UN seul, uniquement sur
erreur transitoire (timeout/connexion). Zéro retenue = run `done` avec n_retenues=0 —
jamais d'assouplissement silencieux des critères.
"""
from __future__ import annotations

import json
import logging
import threading
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .. import config, runs
from ..db import session_factory
from . import events, moteurs
from .interpreteur import IAIndisponible, interpreter_brief, interpreter_refs

log = logging.getLogger("labuse.copilote")


def versions_moteurs() -> dict:
    """Versions/étiquettes des moteurs au moment du run (reproductibilité, §7-J : le run
    servi épinglé est gravé ici — décision Vic, GO M26-A Q3)."""
    from .prompts import PROMPT_VERSION
    out = {"run_servi": runs.current(), "rules_version": config.rules_version(),
           "prompt_interpreteur": PROMPT_VERSION}
    try:
        import subprocess
        out["git_sha"] = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
            cwd=str(config._repo_root()), timeout=5).stdout.strip() or None
    except Exception:  # noqa: BLE001 — environnement sans git (prod déployée) : pas bloquant
        out["git_sha"] = None
    return out


def _transitoire(exc: Exception) -> bool:
    """Erreur transitoire (retry UNIQUE autorisé) : timeout ou connexion, rien d'autre."""
    if isinstance(exc, (TimeoutError, ConnectionError, OperationalError)):
        return True
    name = type(exc).__name__
    return "Timeout" in name or "Connect" in name


def _resume_erreur(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:200]


def demarrer_run(run_id: str) -> threading.Thread:
    t = threading.Thread(target=executer_run, args=(run_id,), daemon=True,
                         name=f"copilote-{run_id[:8]}")
    t.start()
    return t


def executer_run(run_id: str) -> None:
    """Corps du run : interprétation puis exécution du plan. Toute issue est un événement."""
    db: Session = session_factory()()
    t0 = time.monotonic()
    try:
        _executer(db, run_id, t0)
    except Exception:  # noqa: BLE001 — filet : un bug de l'exécuteur = run_failed honnête
        log.exception("run %s : échec exécuteur", run_id)
        try:
            db.rollback()
            if events.run_status(db, run_id) not in events.TERMINAL:
                events.emit(db, run_id, "run_failed",
                            {"code": "erreur_interne",
                             "message": "Erreur interne du Copilote — le dossier n'a pas "
                                        "pu être instruit. L'incident est journalisé."})
        except Exception:  # noqa: BLE001
            log.exception("run %s : émission run_failed impossible", run_id)
    finally:
        db.close()


def _run_row(db: Session, run_id: str) -> dict:
    return dict(db.execute(text(
        "SELECT id::text, mission, brief_raw, brief_json, status FROM agent_runs "
        "WHERE id = :r"), {"r": run_id}).mappings().one())


def _precisions(db: Session, run_id: str) -> list[str]:
    rows = db.execute(text(
        "SELECT payload->>'reponse' FROM agent_events "
        "WHERE run_id = :r AND kind = 'clarification_answered' ORDER BY seq"),
        {"r": run_id}).all()
    return [r[0] for r in rows if r[0]]


def _plan_fige(db: Session, run_id: str) -> list[dict]:
    plan = db.execute(text(
        "SELECT payload->'plan' FROM agent_events "
        "WHERE run_id = :r AND kind = 'run_started'"), {"r": run_id}).scalar()
    if not plan:
        raise RuntimeError("run sans run_started/plan figé")
    return plan


def _interpretation(db: Session, run_id: str, row: dict) -> dict | None:
    """Brief validé, ou None si une clarification a été demandée (awaiting_user)."""
    if row["brief_json"]:
        return row["brief_json"]
    precisions = _precisions(db, run_id)
    try:
        if row["mission"] == "verifier_adresse":
            texte = row["brief_raw"] + ("\n" + "\n".join(precisions) if precisions else "")
            interp = interpreter_refs(texte, db=db)
        else:
            interp = interpreter_brief(row["brief_raw"], row["mission"],
                                       precisions=precisions, db=db)
    except IAIndisponible as exc:
        events.emit(db, run_id, "run_failed",
                    {"code": "ia_indisponible",
                     "message": "L'interpréteur IA est indisponible "
                                f"({exc}). Le besoin n'a pas été interprété — aucun "
                                "brief n'est deviné à votre place. Réessayez plus tard."})
        return None
    except (ValueError, KeyError) as exc:
        events.emit(db, run_id, "run_failed",
                    {"code": "interpretation_invalide",
                     "message": "L'interpréteur a produit une sortie invalide — le run "
                                "s'arrête plutôt que de deviner.",
                     "detail": _resume_erreur(exc)})
        return None

    if interp.clarification is not None:
        events.emit(db, run_id, "clarification_requested", dict(interp.clarification))
        return None
    events.emit(db, run_id, "brief_parsed", {"brief_json": interp.brief})
    db.execute(text("UPDATE agent_runs SET brief_json = CAST(:b AS jsonb) WHERE id = :r"),
               {"b": json.dumps(interp.brief, ensure_ascii=False), "r": run_id})
    db.commit()
    return interp.brief


def _executer(db: Session, run_id: str, t0: float) -> None:
    s = config.get_settings()
    row = _run_row(db, run_id)
    if events.run_status(db, run_id) in events.TERMINAL:
        return

    brief = _interpretation(db, run_id, row)
    if brief is None:
        return                                       # awaiting_user ou run_failed déjà émis

    plan = _plan_fige(db, run_id)
    dossier = moteurs.Dossier()
    appels = 0

    def _annule() -> bool:
        """Consulté par les étapes longues (sessions parallèles) : un run annulé coupe
        les travaux en cours au lieu de les laisser finir (exigence Vic)."""
        from ..db import session_factory
        s2 = session_factory()()
        try:
            return events.run_status(s2, run_id) == "cancelled"
        finally:
            s2.close()
    for etape in plan:
        nom, bloquant = etape["moteur"], bool(etape["bloquant"])
        # Budgets + annulation, vérifiés AVANT chaque étape.
        if events.run_status(db, run_id) == "cancelled":
            return
        if time.monotonic() - t0 > s.copilote_timeout_run_s:
            events.emit(db, run_id, "run_failed",
                        {"code": "timeout_global",
                         "message": f"Budget d'exécution dépassé ({s.copilote_timeout_run_s:.0f} s) "
                                    "— le dossier est incomplet et n'est pas servi."})
            return
        if appels >= s.copilote_max_appels_moteurs:
            events.emit(db, run_id, "run_failed",
                        {"code": "plafond_appels",
                         "message": f"Plafond d'appels moteurs atteint "
                                    f"({s.copilote_max_appels_moteurs}) — arrêt propre."})
            return

        events.emit(db, run_id, "step_started", {"moteur": nom, "params": {
            "communes": brief.get("communes"), "n_candidats": len(dossier.retenus()) or None,
            "n_refs": len(brief.get("refs", [])) or None}})
        res = None
        for tentative in (1, 2):
            appels += 1
            try:
                res, duree_ms = moteurs.appeler(nom, db, brief, dossier, run_id=run_id,
                                                annule=_annule)
                db.commit()
                break
            except Exception as exc:  # noqa: BLE001 — compacté en step_failed, stacktrace en logs
                db.rollback()
                log.exception("run %s · moteur %s : échec (tentative %d)", run_id, nom, tentative)
                if tentative == 1 and _transitoire(exc) \
                        and appels < s.copilote_max_appels_moteurs:
                    continue                          # retry UNIQUE, transitoire seulement
                events.emit(db, run_id, "step_failed",
                            {"moteur": nom,
                             "code_erreur": ("transitoire" if _transitoire(exc)
                                             else "erreur_moteur"),
                             "resume": _resume_erreur(exc)})
                break
        if events.run_status(db, run_id) == "cancelled":
            return                                    # annulé pendant l'étape : arrêt propre
        if res is None:                               # étape en échec
            if bloquant:
                events.emit(db, run_id, "run_failed",
                            {"code": "etape_bloquante",
                             "message": f"L'étape « {nom} » a échoué — le dossier ne peut "
                                        "pas être instruit sans elle."})
                return
            continue                                  # non-bloquant : la note dira le manque

        payload = {"moteur": nom, "resultat": res.resultat, "etiquette": res.etiquette,
                   "duree_ms": duree_ms}
        if res.n_avant is not None:
            payload["compteur"] = {"avant": res.n_avant, "apres": res.n_apres}
        events.emit(db, run_id, "step_completed", payload)

    if events.run_status(db, run_id) == "cancelled":
        return
    if row["mission"] == "verifier_adresse":
        n_ret = sum(1 for v in dossier.verdicts if v.get("trouvee"))
        n_eca = len(dossier.verdicts) - n_ret
    else:
        n_ret = len(dossier.retenus())
        n_eca = sum(1 for c in dossier.candidats if not c.get("retenu", True))
    events.emit(db, run_id, "run_completed",
                {"n_retenues": n_ret, "n_ecartees": n_eca,
                 "duree_totale_ms": int((time.monotonic() - t0) * 1000)})
