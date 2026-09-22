"""CRON-1 — EXPLOITATION PLANIFIÉE : le registre des jobs + le runner commun.

Un seul mécanisme : chaque tâche périodique est un JOB déclaré ici (nom, description, planification en
heure serveur UTC + heure Réunion affichée, timeout, callable). Le cron ne fait QUE lancer `labuse jobs
run <nom>` — zéro logique dans le crontab. Le wrapper `scripts/jobs/run-job.sh` pose le verrou flock et
redirige le log ; ce module tient le reste : timeout par job, fichier d'état JSON (début, fin, statut,
durée, compteurs métier, erreur), alerte mail admin en cas d'échec, ping témoin externe (dead man's switch).

RÈGLE DRY-RUN GLOBALE : si SMTP n'est pas configuré, tout job qui enverrait un mail calcule tout, logue
tout, marque « dry-run » dans son état, et n'envoie RIEN. Aucun autre changement de comportement.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import get_settings
from .tz import now_reunion

log = logging.getLogger("labuse.jobs")


@dataclass
class JobContext:
    """Ce qu'un job reçoit : une session DB (ouverte/fermée par le runner), l'état dry-run global, un
    logger, et un dict de compteurs à remplir (remontés dans l'état + le mail admin)."""
    db: object
    dry_run: bool
    compteurs: dict = field(default_factory=dict)

    def compte(self, **kw) -> None:
        self.compteurs.update(kw)


@dataclass
class Job:
    nom: str
    titre: str                      # description en clair (page admin, mail)
    cadence: str                    # quotidien | hebdo | mensuel | 15 min
    cron_utc: str                   # expression cron EN HEURE SERVEUR (UTC)
    heure_reunion: str              # affichage humain (heure Réunion = UTC+4)
    fn: Callable[[JobContext], None]
    # CRON-1 lot 1 — un job sans RAISON n'existe pas. Chaque job porte : pourquoi il existe (raison, en
    # français), ce qu'il touche (`eau` = surveille/ingère/contrôle la donnée des 94 ; `exploitation` =
    # fait tourner le serveur), et le node-id du TEST qui le couvre (vérifié par le méta-test du registre).
    raison: str = ""
    touche: str = "exploitation"    # 'eau' | 'exploitation'
    test: str = ""
    timeout_s: int = 900
    envoie_mail: bool = False       # concerné par la règle dry-run
    besoin_db: bool = True


# ─────────────────────────────── le runner commun ───────────────────────────────

class _Timeout(Exception):
    pass


def _state_dir() -> Path:
    p = Path(get_settings().jobs_state_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_path(nom: str) -> Path:
    return _state_dir() / f"{nom}.json"


def lire_etat(nom: str) -> dict | None:
    p = state_path(nom)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _ecrire_etat(nom: str, etat: dict) -> None:
    tmp = state_path(nom).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(state_path(nom))   # écriture atomique (jamais un état à moitié écrit)


def _ping_temoin(nom: str, ok: bool) -> None:
    """K9 — dead man's switch : chaque job pingue une URL de suivi (healthchecks.io ou équivalent), par
    variable d'env `LABUSE_PING_<NOM>` (tirets → underscores). Absente → on saute SANS erreur. C'est la
    seule alerte qui survit à la mort du serveur : si le ping cesse, le service externe alerte."""
    url = os.environ.get(f"LABUSE_PING_{nom.upper().replace('-', '_')}")
    if not url:
        return
    cible = url if ok else (url.rstrip("/") + "/fail")
    try:
        import urllib.request
        urllib.request.urlopen(cible, timeout=10).read()
    except Exception as exc:  # noqa: BLE001 — le ping ne doit JAMAIS faire échouer le job
        log.warning("ping témoin %s injoignable (%s) — sans conséquence sur le job", nom, exc)


def _alerte_admin(job: Job, etat: dict) -> None:
    """Mail à l'admin en cas d'échec. Respecte la règle dry-run : sans SMTP, on logue, on ne bloque pas."""
    s = get_settings()
    dest = s.admin_email or s.contact_email
    if not dest:
        return
    corps = (f"Le job « {job.nom} » ({job.titre}) a échoué.\n\n"
             f"Statut : {etat.get('statut')}\n"
             f"Début : {etat.get('debut')}\nFin : {etat.get('fin')}\n"
             f"Durée : {etat.get('duree_s')} s\n"
             f"Erreur : {etat.get('erreur')}\n"
             f"Compteurs : {json.dumps(etat.get('compteurs') or {}, ensure_ascii=False)}\n\n"
             f"— LABUSE, exploitation planifiée")
    from .mail import send_email
    r = send_email(dest, f"[LABUSE] échec du job {job.nom}", corps, settings=s)
    log.info("alerte admin job=%s envoyée=%s (%s)", job.nom, r.sent, r.detail)


def exec_one(nom: str) -> int:
    """Exécute UN job (le verrou flock est tenu en amont par run-job.sh). Écrit l'état, alerte à l'échec,
    pingue le témoin. Retourne 0 (ok/dry-run) ou 1 (échec). NE POSE PAS le verrou (une seule couche)."""
    job = JOBS.get(nom)
    if job is None:
        raise SystemExit(f"job inconnu : {nom} (voir `labuse jobs list`)")

    from .mail import mail_configured
    dry_run = job.envoie_mail and not mail_configured()
    debut = datetime.now(timezone.utc)
    etat = {"nom": nom, "titre": job.titre, "debut": debut.isoformat(),
            "debut_reunion": now_reunion().strftime("%Y-%m-%d %H:%M:%S"),
            "statut": "en_cours", "dry_run": dry_run, "compteurs": {}, "erreur": None}
    _ecrire_etat(nom, etat)

    ctx = JobContext(db=None, dry_run=dry_run)
    ancien = signal.getsignal(signal.SIGALRM)

    def _sonne(_s, _f):
        raise _Timeout(f"dépassement du timeout ({job.timeout_s}s)")

    ok = False
    try:
        signal.signal(signal.SIGALRM, _sonne)
        signal.alarm(job.timeout_s)
        if job.besoin_db:
            from .db import session_scope
            with session_scope() as db:
                ctx.db = db
                job.fn(ctx)
                db.commit()
        else:
            job.fn(ctx)
        etat["statut"] = "dry-run" if dry_run else "ok"
        ok = True
    except _Timeout as exc:
        etat["statut"], etat["erreur"] = "timeout", str(exc)
    except Exception as exc:  # noqa: BLE001 — tout échec est capturé, jamais un traceback nu au cron
        etat["statut"], etat["erreur"] = "echec", f"{type(exc).__name__}: {str(exc)[:500]}"
        log.exception("job %s en échec", nom)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, ancien)

    fin = datetime.now(timezone.utc)
    etat["fin"] = fin.isoformat()
    etat["duree_s"] = round((fin - debut).total_seconds(), 1)
    etat["compteurs"] = ctx.compteurs
    _ecrire_etat(nom, etat)
    # CIRCUIT-1 lot 8.3 — trace UNIFIÉE des jobs qui touchent l'eau (crons compris) : une ligne
    # circuit_journal (quoi, quand, résultat, compteurs). Jamais bloquant.
    if nom in TOUCHE_EAU:
        try:
            from .circuit_journal import journaliser
            from .db import session_scope
            with session_scope() as _db:
                journaliser(_db, "job", nom, "cron", etat["statut"],
                            {"duree_s": etat["duree_s"], "compteurs": ctx.compteurs})
                _db.commit()
        except Exception:  # noqa: BLE001
            log.error("trace circuit_journal impossible pour le job %s", nom)
    if not ok:
        _alerte_admin(job, etat)
    _ping_temoin(nom, ok)
    return 0 if ok else 1


def _champ_match(val: int, champ: str) -> bool:
    """Un champ cron (minute/heure/jour/mois/jour-semaine) matche-t-il une valeur ?

    RETOURS-8 (R4.1) — supporte la GRAMMAIRE cron réelle, séparément ou combinée :
      · `*`      — n'importe quelle valeur ;
      · `a,b,c`  — LISTE (le job `sante-endpoints` tourne à `7,37`) — l'ancien `int('7,37')` plantait ;
      · `a-b`    — PLAGE (bornes incluses) ;
      · `*/n`    — PAS sur `*` ; `a-b/n` — pas sur une plage ; `a/n` — pas depuis `a` jusqu'au max.
    Une virgule combine plusieurs de ces termes (`1-5,30,*/15`). Un terme illisible ne matche pas
    (jamais une exception qui remonte et casse l'Horloge)."""
    return any(_terme_match(val, t) for t in champ.split(","))


def _terme_match(val: int, terme: str) -> bool:
    """Un TERME cron (sans virgule) : `*`, entier, `a-b`, `*/n`, `a-b/n`, `a/n`. False si illisible."""
    terme = terme.strip()
    try:
        base, _, pas_s = terme.partition("/")
        pas = int(pas_s) if pas_s else 1
        if pas <= 0:
            return False
        if base == "*":
            return val % pas == 0
        if "-" in base:
            lo_s, _, hi_s = base.partition("-")
            lo, hi = int(lo_s), int(hi_s)
            return lo <= val <= hi and (val - lo) % pas == 0
        n = int(base)
        # `a/n` (sans borne haute) = à partir de a, tous les n ; `a` seul (pas=1) = égalité stricte.
        return val >= n and (val - n) % pas == 0 if pas_s else val == n
    except ValueError:
        return False


def prochaine(cron_utc: str, *, horizon_jours: int = 40) -> datetime | None:
    """CRON-2 (K7) — prochaine exécution (UTC) d'une expression cron « m h dom mon dow ». Pas de
    dépendance : on avance minute par minute jusqu'au premier match (crons simples). None si aucun match
    sous l'horizon. dow cron : 0 = dimanche (Python weekday : lundi=0 → conversion)."""
    m, h, dom, mon, dow = cron_utc.split()
    from datetime import timedelta
    t = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
    fin = t + timedelta(days=horizon_jours)
    while t < fin:
        cron_dow = (t.weekday() + 1) % 7   # lundi=0 (py) → dimanche=0 (cron)
        if (_champ_match(t.minute, m) and _champ_match(t.hour, h) and _champ_match(t.day, dom)
                and _champ_match(t.month, mon) and _champ_match(cron_dow, dow)):
            return t
        t += timedelta(minutes=1)
    return None


def liste() -> list[dict]:
    """Pour `labuse jobs list` + la page admin : chaque job avec sa planif, sa prochaine exécution et son
    dernier état."""
    from .tz import REUNION_TZ
    out = []
    for j in JOBS.values():
        e = lire_etat(j.nom) or {}
        p = prochaine(j.cron_utc)
        out.append({
            "nom": j.nom, "titre": j.titre, "cadence": j.cadence,
            "cron_utc": j.cron_utc, "heure_reunion": j.heure_reunion,
            # CRON-1 lot 3 — la page Horloge lit LE REGISTRE : la raison (fr) et ce qu'il touche
            # (eau/exploitation) voyagent avec chaque job, à côté de son dernier passage.
            "raison": j.raison, "touche": j.touche, "test": j.test,
            "timeout_s": j.timeout_s, "envoie_mail": j.envoie_mail,
            "prochaine_utc": p.isoformat() if p else None,
            "prochaine_reunion": p.astimezone(REUNION_TZ).strftime("%d/%m %H:%M") if p else None,
            "dernier": {"statut": e.get("statut"), "fin": e.get("fin"),
                        "duree_s": e.get("duree_s"), "dry_run": e.get("dry_run"),
                        "compteurs": e.get("compteurs"), "erreur": e.get("erreur")},
        })
    return out


# ─────────────────────────────── le registre des jobs ───────────────────────────────
# L'implémentation de chaque job vit dans labuse.jobs_impl (importée à l'usage, pas au chargement, pour
# ne pas tirer tout l'ingest quand on ne fait que lister). Chaque callable reçoit un JobContext.

def _impl(nom: str) -> Callable[[JobContext], None]:
    def _run(ctx: JobContext) -> None:
        from . import jobs_impl
        getattr(jobs_impl, nom.replace("-", "_"))(ctx)
    return _run


def _j(nom, titre, cadence, cron_utc, heure_reunion, *, raison, touche, test,
       timeout_s=900, envoie_mail=False, besoin_db=True):
    assert raison and test and touche in ("eau", "exploitation"), f"job {nom} : raison/touche/test obligatoires"
    return Job(nom, titre, cadence, cron_utc, heure_reunion, _impl(nom),
               raison=raison, touche=touche, test=test,
               timeout_s=timeout_s, envoie_mail=envoie_mail, besoin_db=besoin_db)


JOBS: dict[str, Job] = {j.nom: j for j in [
    # ══════════════════ L'EAU — surveillance & ingestion des sources vitrine ══════════════════
    _j("sonde-sources", "Sonde des sources amont — détecte une nouvelle version, n'ingère pas",
       "quotidien", "0 3 * * *", "07:00", touche="eau", timeout_s=1800,
       raison="L'œil sur les 94 : chaque nuit, une requête HTTP sur toute source à amont interrogeable "
              "(millésime API/page, GetCapabilities daté, en-tête de fichier). Une version amont plus "
              "récente ⇒ cloche admin. N'ingère rien : la sentinelle prévient, Vic décide.",
       test="tests/test_cron1_registre.py::test_sonde_sources_couvre_le_max"),
    _j("agents-sources", "Agents de source (veille amont par IA) — le dimanche, plafonné",
       "hebdo (dim)", "0 19 * * 0", "23:00 dim", touche="eau", timeout_s=3600,
       raison="Le détective : là où la sonde mécanique ne suffit pas, un agent IA lit la page amont et "
              "dit s'il y a du neuf (jamais une réponse sans URL réellement consultée). Un passage par "
              "semaine (dimanche nuit), sous PLAFOND de dépense (LABUSE_AGENT_PLAFOND_EUR, défaut 0 = ne "
              "dépense rien) qui arrête proprement et signale les sources non traitées.",
       test="tests/test_cron1_registre.py::test_agents_sources_dimanche"),
    _j("filtres-sources", "Filtres des sources : rejoue les contrôles qualité sur les versions servies",
       "quotidien", "5 3 * * *", "07:05", touche="eau", timeout_s=1800,
       raison="Le filtre de nuit : rejoue les contrôles qualité sur les versions RÉELLEMENT servies (une "
              "table dérive : correctif, raster remplacé). 07:05, avant la sonde du circuit.",
       test="tests/test_cron1_registre.py::test_filtres_sources_repris"),
    _j("coherence-robinets", "Sonde du circuit : fuites entre robinets + eau ancienne (tampons)",
       "quotidien", "25 3 * * *", "07:25", touche="eau", timeout_s=3600,
       raison="La sonde « tout coule » : deux chemins d'un même chiffre doivent donner la même valeur ; "
              "sinon fuite (ligne rouge du Résumé). Détecte aussi l'eau ancienne (tampons). 07:25.",
       test="tests/test_cron1_registre.py::test_coherence_robinets_repris"),
    _j("ingest-bodacc", "BODACC quotidien (procédures collectives) + chaîne des dérivés légers",
       "quotidien", "40 2 * * *", "06:40", touche="eau", timeout_s=1800,
       raison="Les procédures collectives (BODACC) arrivent J+2 et nourrissent Radar/score. RECOUPEMENT "
              "tranché : QUOTIDIEN (les deux jeux l'avaient en quotidien), à 06:40 — AVANT les alertes de "
              "07:00 (l'heure du wrapper l'emporte : elle place l'ingestion avant les notifications).",
       test="tests/test_cron1_registre.py::test_recoupements_arbitres"),
    _j("ingest-sitadel", "Permis SITADEL → événements de veille foncière + golden candidat",
       "mensuel (10)", "30 0 10 * *", "04:30 le 10", touche="eau", timeout_s=3600, envoie_mail=True,
       raison="Les permis SDES/Sitadel nourrissent la veille foncière. RECOUPEMENT tranché : MENSUEL le 10 "
              "(cadence du wrapper) — le producteur SDES publie une fois par mois ; le QUOTIDIEN legacy "
              "re-téléchargeait chaque jour le même jeu (gâchis + faux « frais »).",
       test="tests/test_cron1_registre.py::test_recoupements_arbitres"),
    _j("ingest-dpe", "DPE ADEME mensuel", "mensuel (12)", "0 0 12 * *", "04:00 le 12",
       touche="eau", timeout_s=3600,
       raison="Les DPE ADEME sortent en train MENSUEL (mesuré : dataUpdatedAt mensuel). RECOUPEMENT tranché : "
              "MENSUEL le 12 (wrapper) — l'HEBDO legacy (mardi) re-téléchargeait sans nouvelle donnée.",
       test="tests/test_cron1_registre.py::test_recoupements_arbitres"),
    _j("ingest-sirene", "SIRENE mensuel (refresh des concurrents géolocalisés)",
       "mensuel (7)", "0 0 7 * *", "04:00 le 7", touche="eau", timeout_s=3600,
       raison="SIRENE (établissements géolocalisés) rafraîchit les concurrents de l'étude de zone. "
              "Mensuel le 7 — cadence du producteur.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("sync-gpu", "Diff PLU des 24 communes → événements de veille foncière + bandeau PLU",
       "mensuel (15)", "0 0 15 * *", "04:00 le 15", touche="eau", timeout_s=1800, envoie_mail=True,
       raison="Le diff des 24 documents PLU (GPU) fait remonter une révision opposable en événement de "
              "veille + bandeau. Mensuel le 15.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),

    # ══════════════════ L'EXPLOITATION — faire tourner le serveur ══════════════════
    _j("backup-postgres", "Sauvegarde PostgreSQL (dump + rotation, 7 conservés)", "quotidien",
       "30 9 * * *", "13:30", touche="exploitation", timeout_s=1800, besoin_db=False,
       raison="La seule sauvegarde : sans elle, une panne disque perd toute la base. Quotidien, 7 dumps "
              "conservés. RECOUPEMENT tranché : l'expression LEGACY (`30 9 * * *`) est reprise à "
              "l'identique — c'est le job réellement actif en prod ; garder l'horaire exact garantit un "
              "remplacement SANS TROU (le nouveau tourne au même instant que l'ancien ; deploy.sh pose "
              "avant de retirer le legacy).",
       test="tests/test_cron1_registre.py::test_backup_sans_trou"),
    _j("pg-maintenance", "VACUUM ANALYZE des tables chaudes", "hebdo (dim)",
       "0 0 * * 0", "04:00 dim", touche="exploitation", timeout_s=3600, besoin_db=False,
       raison="Sans VACUUM ANALYZE, le planner PostgreSQL dérive et les requêtes chaudes ralentissent. "
              "Hebdomadaire (dimanche), hors des heures d'usage.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("healthcheck", "Sonde /health locale + espace disque (2 échecs → alerte)", "15 min",
       "*/15 * * * *", "toutes les 15 min", touche="exploitation", timeout_s=120, besoin_db=False,
       raison="Dead-man local : si /health tombe ou le disque se remplit, l'admin est alerté (2 échecs). "
              "La seule alerte qui survit même quand le reste est mort.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("sante-endpoints", "Sonde endpoints métier (accueil/sources/fiche/radar/projets/ask) avec DB",
       "15 min", "7,37 * * * *", "toutes les 30 min", touche="exploitation", timeout_s=300,
       raison="/health sans DB ne voit pas un « écran vide » (run absent), une source vide, Radar/projets "
              "cassés. Cette sonde métier (avec DB) le voit et alerte.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("copilote-purge", "Copilote — purge des conversations au-delà de la rétention (défaut 7 j)",
       "quotidien", "30 23 * * *", "03:30", touche="exploitation", timeout_s=300,
       raison="Les conversations Copilote au-delà de la rétention (défaut 7 j) sont purgées : coût de "
              "stockage + minimisation des données.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("radar-digests", "Alertes de veille — un mail par client (les biens qui matchent)", "quotidien",
       "0 14 * * *", "18:00", touche="exploitation", timeout_s=1200, envoie_mail=True,
       raison="Les clients paient la veille : chaque jour, un mail par client avec les biens qui matchent "
              "ses critères (Brevo). Sans dépôt Radar récent, il n'y a rien à envoyer (dry-run si SMTP absent).",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),

    # ── VEILLE-FIX-1 (lot 1) — les quatre fonctions du LEGACY du matin que le registre ne portait pas.
    # Sans elles, retirer les crons legacy éteignait la veille (suivis/secteurs/recherches) et le digest.
    # Créneau matinal du legacy (07:00 Réunion), APRÈS l'ingestion (ingest-bodacc 06:40) ; les trois
    # évaluateurs D'ABORD, le digest APRÈS (07:15) pour qu'il e-maile les événements du jour. Verrou V8a.
    _j("evaluer-suivis", "Veille — parcelles suivies (mutation/permis/BODACC/zonage SUR la parcelle)",
       "quotidien", "2 3 * * *", "07:02", touche="exploitation", timeout_s=600,
       raison="Les parcelles SUIVIES par un client doivent le prévenir quand un fait tombe SUR elles "
              "(vente, permis, procédure, zonage). Reprend le legacy du matin ; sans ce job, retirer les "
              "crons legacy éteint la veille de suivi. Zéro modèle, dédup par fait (rejeu = 0).",
       test="tests/test_veille_fix1.py::test_les_quatre_jobs_veille_existent"),
    # VEILLE-2 (Lot 4) — le job `evaluer-secteurs` est RETIRÉ : la page Veille n'a plus que PARCELLE et
    # RADAR (secteurs et recherches sauvegardées archivés, plus évalués). `detect-events` reste (bascules
    # du marché + bascule du score sur parcelle suivie), sans l'évaluation des recherches.
    _j("detect-events", "Veille — bascules du marché (diff du run servi et du précédent)",
       "quotidien", "4 3 * * *", "07:04", touche="exploitation", timeout_s=900,
       raison="Le marché voit les bascules de classement (diff du run servi et de son précédent), et une "
              "parcelle SUIVIE qui bascule prévient son suiveur. Idempotent par (kind, idu, run_from, "
              "run_to). Sans ce job, les bascules du run ne se propagent jamais.",
       test="tests/test_veille_fix1.py::test_les_quatre_jobs_veille_existent"),
    _j("digest", "Veille — DIGEST du matin (un mail par compte : suivis de parcelle + bascules)",
       "quotidien", "15 3 * * *", "07:15", touche="exploitation", timeout_s=900, envoie_mail=True,
       raison="Les notifications de veille (parcelles suivies) sont e-mailées en UN digest quotidien par "
              "compte, filtré par préférence, jamais vide, un par jour. Passe par mail_queue. Sans ce job, "
              "aucune notification cloche ne serait jamais e-mailée (dry-run si SMTP absent).",
       test="tests/test_veille_fix1.py::test_les_quatre_jobs_veille_existent"),
    _j("restore-test", "Restaure le dernier dump dans une base jetable et vérifie (puis DROP)",
       "mensuel (1er)", "0 1 1 * *", "05:00 le 1er", touche="exploitation", timeout_s=3600,
       envoie_mail=True, besoin_db=False,
       raison="Une sauvegarde non restaurable ne vaut rien : une fois par mois, on restaure le dernier dump "
              "dans une base jetable, on vérifie, on DROP. Alerte si la restauration échoue.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),

    # ── NON REPRIS (retirés du registre par CRON-1 lot 1, avec la raison — cf. CRON-1-LOT1.md) ──
    # Radar : PAS de job. Le traitement des dépôts est déclenché au dépôt (manuel) ; une ÉCHÉANCE
    #   attendue vit en base → dépassée = tâche du Résumé (verrou G8, lot 2). Donc radar-cycle,
    #   radar-releves : retirés.
    # sources-fraicheur : le verdict de fraîcheur est calculé À LA LECTURE (etats_sources) + la sonde
    #   des sources (sonde-sources) porte la veille amont ; un job nocturne de plus faisait doublon.
    # fiche-commune-cache : réchauffeur de cache non essentiel (la fiche commune se calcule à la demande).
    # coherence-run : le mandat ne reprend QUE filtres-sources + coherence-robinets ; la cohérence de run
    #   est couverte par ces deux + les verrous (labuse circuit verrous).
    # rapport-admin : redondant avec la Tour de contrôle (Pilotage), qui montre l'exploitation en direct.
    # regles-references / ingest-bdnb : IA à la demande / amont 974 absent — jamais en cron (inchangé).
]}

#: CRON-1 lot 1 — les jobs qui TOUCHENT L'EAU, DÉRIVÉS du registre (`touche == 'eau'`) : chacun laisse
#: une ligne au journal unifié `circuit_journal`. Plus de liste tenue à la main (une seule source).
TOUCHE_EAU = frozenset(nom for nom, j in JOBS.items() if j.touche == "eau")
