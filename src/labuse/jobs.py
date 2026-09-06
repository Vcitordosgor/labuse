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


def _j(nom, titre, cadence, cron_utc, heure_reunion, *, timeout_s=900, envoie_mail=False, besoin_db=True):
    return Job(nom, titre, cadence, cron_utc, heure_reunion, _impl(nom),
               timeout_s=timeout_s, envoie_mail=envoie_mail, besoin_db=besoin_db)


#: CIRCUIT-1 lot 8.3 — les jobs qui TOUCHENT L'EAU (ingèrent, sondent, calculent, contrôlent) :
#: chacun laisse une ligne au journal unifié `circuit_journal` (quoi, quand, résultat, compteurs).
TOUCHE_EAU = frozenset({
    "sources-fraicheur", "radar-cycle", "fiche-commune-cache", "ingest-bodacc", "ingest-sirene",
    "ingest-sitadel", "ingest-dpe", "sync-gpu", "sentinelle-sources", "radar-releves",
    "coherence-run", "coherence-robinets", "filtres-sources",
})

JOBS: dict[str, Job] = {j.nom: j for j in [
    # K3 — quotidiens
    _j("backup-postgres", "Sauvegarde PostgreSQL (dump + rotation)", "quotidien",
       "45 1 * * *", "05:45", timeout_s=1800, besoin_db=False),
    _j("sources-fraicheur", "Fraîcheur des 59 sources (à_jour / en_retard / en_panne)", "quotidien",
       "0 2 * * *", "06:00", timeout_s=600),
    _j("radar-cycle", "Radar — traite les dépôts de la veille (parse, rattache, événements, badges)",
       "quotidien", "30 2 * * *", "06:30", timeout_s=1800),
    _j("radar-digests", "Digests & alertes de veille — un mail par client (Brevo)", "quotidien",
       "0 14 * * *", "18:00", timeout_s=1200, envoie_mail=True),
    _j("fiche-commune-cache", "Fiche commune — précalcule le contexte des communes (ouverture < 500 ms)",
       "quotidien", "0 23 * * *", "03:00", timeout_s=1800),
    # RETOURS-8 (R11) — purge des conversations Copilote au-delà de la rétention (défaut 7 j, réglage admin).
    _j("copilote-purge", "Copilote — purge des conversations au-delà de la rétention (défaut 7 j)",
       "quotidien", "30 23 * * *", "03:30", timeout_s=300),
    _j("healthcheck", "Sonde /health locale + espace disque (2 échecs → alerte)", "15 min",
       "*/15 * * * *", "toutes les 15 min", timeout_s=120, besoin_db=False),
    # CONNEXIONS-2 Lot 7.2 (N3) — sonde des endpoints MÉTIER (avec DB) : capte « écran vide » (run absent),
    # source vide, Radar/projets cassés — ce que /health sans DB ne voit pas. Notifie l'admin à la panne.
    _j("sante-endpoints", "Sonde endpoints métier (accueil/sources/fiche/radar/projets/ask) avec DB",
       "15 min", "7,37 * * * *", "toutes les 30 min", timeout_s=300),
    # K4 — hebdo & mensuels
    _j("pg-maintenance", "VACUUM ANALYZE des tables chaudes", "hebdo (dim)",
       "0 0 * * 0", "04:00 dim", timeout_s=3600, besoin_db=False),
    _j("rapport-admin", "Rapport hebdomadaire d'exploitation (mail admin)", "hebdo (lun)",
       "15 2 * * 1", "06:15 lun", timeout_s=600, envoie_mail=True),
    # CIRCUIT-1 lot 8.1 — BODACC entre au WRAPPER (quotidien, comme le legacy 02:30 UTC) : les
    # procédures collectives J+2 arrivent avant les notifications de 03:00.
    _j("ingest-bodacc", "BODACC quotidien (procédures collectives) + chaîne des dérivés légers",
       "quotidien", "40 2 * * *", "06:40", timeout_s=1800),
    _j("ingest-sirene", "SIRENE mensuel (date_creation + date_dernier_traitement, refresh concurrents)",
       "mensuel (7)", "0 0 7 * *", "04:00 le 7", timeout_s=3600),
    _j("ingest-sitadel", "Permis SITADEL mensuel → événements de veille foncière + golden candidat",
       "mensuel (10)", "30 0 10 * *", "04:30 le 10", timeout_s=3600, envoie_mail=True),
    _j("ingest-dpe", "DPE ADEME mensuel", "mensuel (12)", "0 0 12 * *", "04:00 le 12", timeout_s=3600),
    _j("sync-gpu", "Diff PLU des 24 communes → événements de veille foncière + bandeau PLU",
       "mensuel (15)", "0 0 15 * *", "04:00 le 15", timeout_s=1800, envoie_mail=True),
    # CIRCUIT-1 lot 8.1 — `ingest-bdnb` RETIRÉ du registre : l'amont BDNB ne couvre pas le 974
    # (SCORING-3 L3, constat mesuré 03/09/2026). Le CLI `labuse ingest-bdnb` reste pour le jour où
    # le 974 entrera dans l'export ; aucun cron ne le pose plus.
    # SENTINELLE-1 (W3) — veille QUOTIDIENNE des sources amont (généralise l'ancien sentinelle-dvf-cadastre,
    # devenu deux lignes de source_veille). Sonde api/page/entete, alerte, n'ingère RIEN. envoie_mail=False :
    # la notification passe par la cloche admin (event_log systeme), pas par un mail (bruit quotidien évité).
    _j("sentinelle-sources", "Veille des sources amont : détecte un nouveau millésime et alerte (n'ingère pas)",
       "quotidien", "0 3 * * *", "07:00", timeout_s=900),
    # FLUX-1 (F3.2) — relevé quotidien des compteurs Radar (fin de journée Réunion) : la courbe
    # d'accumulation se lit de radar_releves. Après le cycle Radar, avant les digests.
    _j("radar-releves", "Radar — relevé quotidien des compteurs (annonces, rattachées, paires DVF)",
       "quotidien", "0 13 * * *", "17:00", timeout_s=300),
    # CIRCUIT-3 lot 5.1 — LE FILTRE DE NUIT : rejoue les contrôles des filtres sur les versions
    # SERVIES (dérive dans le temps : une table modifiée par un correctif, un raster remplacé).
    # 07:05, AVANT la sonde de cohérence (07:15/07:25) — même famille, jamais en même temps.
    _j("filtres-sources", "Filtres des sources : rejoue les contrôles qualité sur les versions servies",
       "quotidien", "5 3 * * *", "07:05", timeout_s=1800),
    # FLUX-1 (F4) — garde de cohérence quotidienne : personne ne lit une ancienne donnée. Après la
    # sentinelle (07:00), avant l'ouverture. Notifie l'admin à la divergence.
    _j("coherence-run", "Garde de cohérence : chaque surface lit le run courant (tier/date identiques)",
       "quotidien", "15 3 * * *", "07:15", timeout_s=600),
    # CIRCUIT-1 (lot 4) — la sonde « Vérifier que tout coule » : fuites entre robinets + eau
    # ancienne par tampon → circuit_ecarts / circuit_eau_ancienne / circuit_controles. 07:25
    # (après coherence-run 07:15 — même famille, jamais en même temps sur les mêmes tables).
    _j("coherence-robinets", "Sonde du circuit : fuites entre robinets + eau ancienne (tampons)",
       # 0-bis : le passage nocturne joue AUSSI le cas recette_exports1 (24 PDF des 4 témoins,
       # WeasyPrint + pdftotext) → timeout élargi.
       "quotidien", "25 3 * * *", "07:25", timeout_s=3600),
    # CIRCUIT-1 lot 6.4 — agents-sources : le job MENSUEL EXISTE mais reste DÉSACTIVÉ (décision
    # Vic n° 8 : agents À LA DEMANDE, jamais en cron par défaut). Absent du crontab par
    # construction (test lot 8 : posés == registre − {agents-sources}).
    _j("agents-sources", "Agents de source (veille amont par IA) — DÉSACTIVÉ (à la demande seulement)",
       "mensuel (désactivé)", "0 0 3 * *", "04:00 le 3 (JAMAIS posé)", timeout_s=3600),
    # CIRCUIT-4 lot 5.4 — regles-references : renvoie les agents « règle » sur les références
    # datées de plus de six mois (un texte peut changer) et signale toute version nouvelle.
    # EXISTE au registre mais reste DÉSACTIVÉ (même doctrine que agents-sources : IA à la
    # demande, jamais en cron par défaut — absent du crontab par construction, test lot 8).
    _j("regles-references", "Agents de règle (références des calculs > 6 mois) — DÉSACTIVÉ",
       "mensuel (désactivé)", "0 0 4 * *", "04:00 le 4 (JAMAIS posé)", timeout_s=3600),
    # K9 — robustesse
    _j("restore-test", "Restaure le dernier dump dans une base jetable et vérifie (puis DROP)",
       "mensuel (1er)", "0 1 1 * *", "05:00 le 1er", timeout_s=3600, envoie_mail=True, besoin_db=False),
]}
