"""JOHN-TAYLOR-1 — la LISTE FERMÉE des actions de John.

« Les ordres de Vic s'exécutent. Liste fermée d'actions : injecter une source (A ou B), relancer un job
du registre, lancer une sauvegarde, accepter un écart ou un incident, promouvoir un run aux contrôles
verts, retirer une source. Sur un ordre explicite, John agit immédiatement et rend compte du résultat,
contrôles préalables compris. Seules deux actions demandent d'abord "tu confirmes ?" dans le chat, parce
qu'elles touchent les clients et ne se défont pas d'un clic : PROMOUVOIR UN RUN et RETIRER UNE SOURCE ;
un "oui" suffit. Hors liste, John refuse et explique. Chaque action est journalisée avec l'heure et le compte. »

Chaque action porte ses CONTRÔLES PRÉALABLES (ex. promouvoir exige des contrôles verts ; injecter exige
une commande d'ingestion connue). Les effets de bord réels passent par un `Backend` injectable (défauts
liés aux vraies fonctions) → les actions sont testables sans sous-process ni flux-run réel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import journal


# ════════════════════════════════ Effets de bord (injectables) ════════════════════════════════
def _lancer_ingestion_defaut(nom: str) -> dict | None:
    from ..api.dashboard import lancer_ingestion_source
    return lancer_ingestion_source(nom)


def _lancer_job_defaut(nom: str) -> dict:
    """Lance un job par le wrapper commun (MÊME verrou flock que le cron). Détaché, comme le dashboard."""
    import os
    import subprocess
    from pathlib import Path
    racine = Path(__file__).resolve().parents[3]
    wrapper = str(racine / "scripts" / "jobs" / "run-job.sh")
    env = {**os.environ,
           "PYTHONPATH": os.pathsep.join([str(racine / "src"), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
           "LABUSE_LOCK_DIR": os.environ.get("LABUSE_LOCK_DIR") or "/tmp/labuse-locks",
           "LABUSE_JOBS_LOG_DIR": os.environ.get("LABUSE_JOBS_LOG_DIR") or "/tmp/labuse-logs"}
    with open(f"/tmp/labuse-john-job-{nom}.log", "ab") as fh:
        subprocess.Popen(["sh", wrapper, nom], cwd=str(racine), stdout=fh, stderr=fh,
                         start_new_session=True, env=env)
    return {"lance": nom}


def _basculer_defaut(db, run: str, par: str) -> dict:
    from .. import bascule_flux
    return bascule_flux.basculer(db, run, par)


def _retirer_source_defaut(db, source_id: int, raison: str) -> dict:
    from sqlalchemy import text
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS affichage_desactive "
                    "boolean NOT NULL DEFAULT false"))
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS retiree_raison text"))
    n = db.execute(text(
        "UPDATE data_sources SET status = 'retiree', retiree_raison = :r, affichage_desactive = true "
        "WHERE id = :i"), {"r": raison[:240], "i": source_id}).rowcount
    if not n:
        return {"ok": False, "motif": "source introuvable"}
    db.execute(text("UPDATE source_veille SET actif = false, updated_at = now() WHERE source_id = :i"),
               {"i": source_id})
    return {"ok": True, "source_id": source_id}


def _diagnostiquer_app_defaut() -> dict:
    """MAILS-EXPLOIT-1 — diagnostic LECTURE SEULE de l'app : sonde /readyz EN LOCAL (pas d'URL publique,
    aucun effet de bord — pas de restart, pas d'écriture d'état débounce). Rend {ready, motif}."""
    from .. import ops_alertes
    ready, motif = ops_alertes._readyz_local()
    return {"ready": bool(ready), "motif": motif}


def _accepter_incident_defaut(db, cle: str) -> bool:
    from .. import ops_alertes
    return ops_alertes.resoudre(db, cle)


def _accepter_ecart_defaut(db, ref: str, raison: str, par: str) -> dict:
    """Enregistre l'acceptation-avec-raison d'un écart dans un registre dédié (jamais un geste prod
    aveugle : c'est une trace, à l'image d'ECARTS-DISPOSITION.csv de TABLEAU-1)."""
    from sqlalchemy import text
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS john_ecarts_acceptes ("
        " id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),"
        " ref varchar(120) NOT NULL, raison text NOT NULL, par varchar(120))"))
    db.execute(text("INSERT INTO john_ecarts_acceptes (ref, raison, par) VALUES (:r, :ra, :p)"),
               {"r": ref[:120], "ra": raison, "p": par[:120]})
    return {"ok": True, "ref": ref}


@dataclass
class Backend:
    """Les effets de bord réels, injectables en test. Défauts = les vraies fonctions LABUSE."""
    lancer_ingestion: Callable[[str], dict | None] = _lancer_ingestion_defaut
    lancer_job: Callable[[str], dict] = _lancer_job_defaut
    basculer: Callable[..., dict] = _basculer_defaut
    retirer_source: Callable[..., dict] = _retirer_source_defaut
    accepter_incident: Callable[..., bool] = _accepter_incident_defaut
    accepter_ecart: Callable[..., dict] = _accepter_ecart_defaut
    diagnostiquer_app: Callable[[], dict] = _diagnostiquer_app_defaut


# ════════════════════════════════ Le registre d'actions (liste fermée) ════════════════════════════════
@dataclass
class ActionDef:
    cle: str
    label: str
    confirme: bool                 # vrai = demande « tu confirmes ? » avant d'agir
    fn: Callable                   # fn(db, args, par, backend) -> (ok, resume, detail)


def _resoudre_source(db, args: dict) -> tuple[int | None, str | None]:
    """Résout (id, nom) d'une source depuis args {source_id} ou {source} (nom/fragment)."""
    from sqlalchemy import text
    sid = args.get("source_id")
    if sid is not None:
        r = db.execute(text("SELECT id, name FROM data_sources WHERE id = :i"),
                       {"i": int(sid)}).mappings().first()
        return (r["id"], r["name"]) if r else (None, None)
    nom = (args.get("source") or args.get("nom") or "").strip()
    if not nom:
        return None, None
    r = db.execute(text("SELECT id, name FROM data_sources WHERE name = :n"),
                   {"n": nom}).mappings().first()
    if not r:
        r = db.execute(text("SELECT id, name FROM data_sources WHERE name ILIKE :n ORDER BY name LIMIT 1"),
                       {"n": f"%{nom}%"}).mappings().first()
    return (r["id"], r["name"]) if r else (None, None)


def _act_injecter_source(db, args, par, backend: Backend):
    from ..autonomie import classe_source
    sid, nom = _resoudre_source(db, args)
    if not nom:
        return False, "source introuvable (préciser source_id ou le nom exact)", {}
    cl, raison = classe_source(nom)
    r = backend.lancer_ingestion(nom)
    if r is None:
        return (False, f"aucune commande d'ingestion connue pour « {nom} » — rien injecté (à câbler)",
                {"source": nom, "classe": cl})
    return (True, f"injection de « {nom} » (classe {cl}) lancée", {"source": nom, "classe": cl, "lancement": r})


def _act_relancer_job(db, args, par, backend: Backend):
    from .. import jobs as _jobs
    nom = (args.get("nom") or args.get("job") or "").strip()
    if nom not in _jobs.JOBS:
        return False, f"job « {nom} » absent du registre", {"job": nom}
    r = backend.lancer_job(nom)
    return True, f"job « {nom} » relancé", {"job": nom, "lancement": r}


def _act_lancer_sauvegarde(db, args, par, backend: Backend):
    r = backend.lancer_job("backup-postgres")
    return True, "sauvegarde (backup-postgres) lancée", {"lancement": r}


def _act_diagnostiquer_app(db, args, par, backend: Backend):
    """MAILS-EXPLOIT-1 — « Diagnostique l'app » : sonde /readyz (lecture seule) et rend l'état. Ne
    redémarre RIEN (le redémarrage reste un geste humain explicite) : John rapporte, Vic décide."""
    d = backend.diagnostiquer_app()
    if d.get("ready"):
        return True, "l'app répond (readyz vert)", d
    return (True, f"l'app NE répond PAS ({d.get('motif')}) — si ça persiste, redémarrer le service "
            "« labuse » sur le serveur", d)


def _act_accepter_incident(db, args, par, backend: Backend):
    cle = (args.get("cle") or "").strip()
    if not cle:
        return False, "clé d'incident manquante", {}
    ok = backend.accepter_incident(db, cle)
    return (ok, f"incident « {cle} » accepté (fermé)" if ok else f"aucun incident ouvert « {cle} »",
            {"cle": cle})


def _act_accepter_ecart(db, args, par, backend: Backend):
    ref = (args.get("ref") or "").strip()
    raison = (args.get("raison") or "").strip()
    if not ref or not raison:
        return False, "écart : « ref » et « raison » sont requis", {}
    r = backend.accepter_ecart(db, ref, raison, par)
    return True, f"écart « {ref} » accepté avec raison", {"ref": ref, "detail": r}


def _act_promouvoir_run(db, args, par, backend: Backend):
    """CONTRÔLES PRÉALABLES : on ne promeut QUE si la cohérence est verte (faux-client 0, lecteurs 0).
    Sinon, refus (jamais un run douteux servi aux clients) — « sous-protéger est le bug »."""
    from . import contexte
    run = (args.get("run") or "").strip()
    if not run:
        # défaut : le candidat non promu
        run = (contexte.runs_etat(db).get("candidat") or "").strip()
    if not run:
        return False, "aucun run à promouvoir (préciser « run » ou calculer un candidat)", {}
    ctrl = contexte.controles(db).get("coherence")
    if not ctrl:
        return False, f"promotion refusée : aucun contrôle de cohérence probant (run {run})", {"run": run}
    if not ctrl.get("vert"):
        return (False, f"promotion refusée : contrôles NON verts "
                f"(faux-client {ctrl.get('faux_client')}, lecteurs {ctrl.get('erreurs_lecteur')})",
                {"run": run, "controle": ctrl})
    r = backend.basculer(db, run, par)
    ok = bool(r.get("ok"))
    return (ok, f"run « {run} » promu (servi aux clients)" if ok else f"bascule refusée : {r.get('motif')}",
            {"run": run, "bascule": r})


def _act_retirer_source(db, args, par, backend: Backend):
    sid, nom = _resoudre_source(db, args)
    if not sid:
        return False, "source introuvable (préciser source_id ou le nom exact)", {}
    raison = (args.get("raison") or "retirée sur ordre de Vic").strip()
    r = backend.retirer_source(db, sid, raison)
    ok = bool(r.get("ok"))
    return (ok, f"source « {nom} » retirée" if ok else f"retrait refusé : {r.get('motif')}",
            {"source": nom, "source_id": sid, "raison": raison})


ACTIONS: dict[str, ActionDef] = {a.cle: a for a in [
    ActionDef("injecter_source", "Injecter une source (A ou B)", False, _act_injecter_source),
    ActionDef("relancer_job", "Relancer un job du registre", False, _act_relancer_job),
    ActionDef("lancer_sauvegarde", "Lancer une sauvegarde", False, _act_lancer_sauvegarde),
    ActionDef("diagnostiquer_app", "Diagnostiquer l'app (readyz, lecture seule)", False,
              _act_diagnostiquer_app),
    ActionDef("accepter_incident", "Accepter (fermer) un incident", False, _act_accepter_incident),
    ActionDef("accepter_ecart", "Accepter un écart avec raison", False, _act_accepter_ecart),
    ActionDef("promouvoir_run", "Promouvoir un run aux contrôles verts", True, _act_promouvoir_run),
    ActionDef("retirer_source", "Retirer une source", True, _act_retirer_source),
]}


def catalogue() -> list[dict]:
    """La liste des actions (pour le prompt du modèle et l'onglet) : clé, label, confirmation requise."""
    return [{"cle": a.cle, "label": a.label, "confirme": a.confirme} for a in ACTIONS.values()]


def executer(db, action: str, args: dict[str, Any] | None = None, *,
             compte_id: int | None = None, compte: str | None = None,
             confirme: bool = False, backend: Backend | None = None) -> dict:
    """Exécute une action de la LISTE FERMÉE. Journalise TOUJOURS le résultat (exécution OU refus).

    · action hors liste → REFUS explicite (journalisé ok=False), rien n'est fait ;
    · action à confirmation (promouvoir / retirer) sans `confirme=True` → renvoie une DEMANDE de
      confirmation (« tu confirmes ? »), SANS agir et SANS journaliser (rien n'a eu lieu) ;
    · sinon → exécute, journalise, rend compte.
    """
    args = args or {}
    backend = backend or Backend()
    par = compte or (f"compte {compte_id}" if compte_id else "système")
    defn = ACTIONS.get(action)
    if defn is None:
        resume = (f"action « {action} » hors de la liste autorisée — refusée. "
                  f"Actions possibles : {', '.join(ACTIONS)}.")
        journal.enregistrer(db, action=action, args=args, ok=False, resume=resume,
                            compte_id=compte_id, compte=compte)
        return {"ok": False, "refuse": True, "resume": resume}

    if defn.confirme and not confirme:
        return {"ok": False, "besoin_confirmation": True, "action": action,
                "question": f"{defn.label} — cette action touche les clients et ne se défait pas "
                            f"d'un clic. Tu confirmes ? (un « oui » suffit)"}

    try:
        ok, resume, detail = defn.fn(db, args, par, backend)
    except Exception as exc:  # noqa: BLE001 — un effet de bord qui lève = action non faite, tracée
        ok, resume, detail = False, f"échec de l'action ({type(exc).__name__}: {exc})", {}
    journal.enregistrer(db, action=action, args=args, ok=ok, resume=resume,
                        compte_id=compte_id, compte=compte, confirme=defn.confirme)
    return {"ok": ok, "action": action, "resume": resume, "detail": detail, "confirme": defn.confirme}
