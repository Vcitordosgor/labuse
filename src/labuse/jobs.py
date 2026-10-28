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
    logger, et un dict de compteurs à remplir (remontés dans l'état + le mail admin).

    ORF-02 (FIX-ORFEVRE-1) — `precedent` = l'état JSON du DERNIER passage, lu par le runner AVANT
    d'écraser le fichier avec « en_cours » (compteurs vides). Avant, healthcheck relisait son propre
    fichier d'état PENDANT son exécution → `echecs_consecutifs` valait toujours 0 → l'alerte « 2 échecs
    consécutifs » était du code mort (le ping témoin restait vert, /health pouvait être HS des heures)."""
    db: object
    dry_run: bool
    compteurs: dict = field(default_factory=dict)
    precedent: dict | None = None
    # ORF-10 (FIX-ORFEVRE-1) — le TIMEOUT du job voyage avec le contexte : les sous-process
    # (`_ingest_via_cli`) se bornent DESSOUS (marge), pour mourir AVANT le SIGALRM du runner —
    # jamais d'ingestion ORPHELINE qui continue d'écrire après le « timeout » du job.
    timeout_s: int = 900

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
    # COCKPIT-1 (Lot B) — l'habillage HUMAIN du poste pour la page « L'usine » : son libellé (jamais
    # un identifiant technique à l'écran), sa FAMILLE (colonne : 1 Veille des sources · 2 Livraisons
    # quotidiennes · 3 Le moteur · 4 Contrôle, clients, sécurité) et son rôle en une phrase. Posés
    # APRÈS la construction du registre (table _FAMILLE_LIBELLE_ROLE, un méta-test vérifie la couverture
    # des 31). `lancable` = Vic peut le « Lancer maintenant » sans risque (sonde/contrôle/livraison) ;
    # les agents IA ont leur propre bouton « Démarrer » (coût + plafond), jamais lancable.
    famille: int = 4
    libelle: str = ""
    role: str = ""
    lancable: bool = False
    timeout_s: int = 900
    envoie_mail: bool = False       # concerné par la règle dry-run
    besoin_db: bool = True
    # planifie=False : job RETIRÉ du crontab généré ET du monitoring healthz, mais toujours
    # exécutable (bouton admin / `labuse jobs run`). Ex. agents-sources (pas de crédit API, choix
    # assumé — le bouton manuel reste). Décision 13/10.
    planifie: bool = True
    # CRON-PROD-1 — GEL VOLONTAIRE (motif court, ex. « Phase 8 Stéphanie »). Un job gelé RESTE au
    # registre (connu, exécutable à la main, monitoré), mais : (1) le crontab généré l'émet COMMENTÉ
    # (jamais lancé par cron — dégel = décommenter), (2) /healthz/crons le classe « gele » SANS
    # dégrader (gel assumé ≠ panne), (3) la vigie « jobs en retard » l'ignore. Avant : le gel vivait
    # en commentaire posé À LA MAIN (poser_crontab_solidite.sh), invisible du registre et du healthz
    # (→ ingest-dvf comptait comme « jamais vu » et faisait sonner la sonde). None = job actif.
    gel: str | None = None


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


def _purger_connexions() -> None:
    """ORF-01 (FIX-ORFEVRE-1) — après un TIMEOUT (SIGALRM reçu en plein échange psycopg), la connexion
    interrompue est SALE : le serveur attend encore la fin de la requête et tout usage suivant répond
    « another command is already in progress » (incidents quotidiens mail-queue-consommer 13:35, fenêtre
    pg_dump). Si elle retourne au pool, c'est la trace (_journaliser_et_alerter) puis les passages
    suivants qui échouent en cascade. On jette donc TOUT le pool : les connexions saines coûtent une
    reconnexion (processus cron de toute façon court), la sale ne ressert jamais."""
    try:
        from . import db
        if db._engine is not None:
            db._engine.dispose()
            log.info("pool de connexions purgé après timeout (connexion potentiellement sale)")
    except Exception:  # noqa: BLE001 — la purge qui rate ne doit pas masquer l'erreur du job
        log.error("purge du pool après timeout impossible", exc_info=True)


def _journaliser_et_alerter(job: Job, etat: dict, ok: bool) -> None:
    """SOLIDITE-1 (Lot 1.1/1.2) — après chaque passage : pose la ligne d'HISTORIQUE durable (`job_runs`)
    ET ouvre/referme l'incident `job-echec:<nom>` par la PORTE D'ALERTE UNIQUE (ops_alertes — mail + cloche,
    dry-run respecté, un seul envoi puis rappel quotidien, mail « résolu » au retour au vert).

    Session courte dédiée, jamais bloquante : une trace ou une alerte qui rate ne transforme pas un job
    réussi en échec, et ne masque pas un échec déjà capturé par le runner."""
    try:
        from . import jobs_journal, ops_alertes
        from .db import session_scope
        with session_scope() as db:
            try:
                jobs_journal.enregistrer(db, etat)
            except Exception:  # noqa: BLE001 — l'historique qui rate ne casse rien
                log.error("historique job_runs impossible pour %s", job.nom)
            cle = f"job-echec:{job.nom}"
            if ok:
                ops_alertes.resoudre(db, cle)
            else:
                ops_alertes.signaler(
                    db, cle, f"Job en échec : {job.nom}",
                    f"« {job.titre} » a échoué.\n"
                    f"Statut : {etat.get('statut')}\n"
                    f"Début : {etat.get('debut')}  Fin : {etat.get('fin')}  "
                    f"Durée : {etat.get('duree_s')} s\n"
                    f"Erreur : {etat.get('erreur')}\n"
                    f"Compteurs : {json.dumps(etat.get('compteurs') or {}, ensure_ascii=False)}")
            db.commit()
    except Exception as exc:  # noqa: BLE001 — base injoignable au moment de tracer : on logue, on n'échoue pas
        log.error("journal/alerte impossible pour le job %s (%s)", job.nom, exc)


def exec_one(nom: str) -> int:
    """Exécute UN job (le verrou flock est tenu en amont par run-job.sh). Écrit l'état, alerte à l'échec,
    pingue le témoin. Retourne 0 (ok/dry-run) ou 1 (échec). NE POSE PAS le verrou (une seule couche)."""
    job = JOBS.get(nom)
    if job is None:
        raise SystemExit(f"job inconnu : {nom} (voir `labuse jobs list`)")

    from .mail import mail_configured
    dry_run = job.envoie_mail and not mail_configured()
    debut = datetime.now(timezone.utc)
    # ORF-02 — l'état du passage PRÉCÉDENT est lu AVANT d'être écrasé par « en_cours » : c'est la seule
    # façon pour un job (healthcheck) de voir ses compteurs d'avant (`echecs_consecutifs`).
    precedent = lire_etat(nom)
    etat = {"nom": nom, "titre": job.titre, "debut": debut.isoformat(),
            "debut_reunion": now_reunion().strftime("%Y-%m-%d %H:%M:%S"),
            "statut": "en_cours", "dry_run": dry_run, "compteurs": {}, "erreur": None}
    _ecrire_etat(nom, etat)

    ctx = JobContext(db=None, dry_run=dry_run, precedent=precedent, timeout_s=job.timeout_s)
    ancien = signal.getsignal(signal.SIGALRM)
    # ORF-01 — mémorise que l'alarme A SONNÉ, même si le _Timeout est ensuite MASQUÉ par une autre
    # exception (ex. : rollback impossible sur la connexion interrompue) : le finally purge le pool.
    alarme_sonnee = False

    def _sonne(_s, _f):
        nonlocal alarme_sonnee
        alarme_sonnee = True
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
        if alarme_sonnee:
            # ORF-01 — connexion possiblement interrompue en plein échange : on purge le pool AVANT la
            # trace/alerte (sinon « journal/alerte impossible pour le job » — la connexion sale ressert).
            _purger_connexions()

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
    # SOLIDITE-1 (Lot 1) — historique durable + alerte par la porte unique (échec → incident ; succès →
    # résolution). Remplace l'ancien `_alerte_admin` (mail seul, sans dédup ni « résolu »).
    _journaliser_et_alerter(job, etat, ok)
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


def semaine_agents(d) -> bool:
    """CIRCUIT-P7 — le cron des agents passe UNE SEMAINE SUR DEUX : « on » les semaines ISO paires.
    Un seul point de vérité, partagé par le cron (jobs_impl) et la carte Agents (prochain passage)."""
    return d.isocalendar()[1] % 2 == 0


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
            # COCKPIT-1 (Lot B) — l'habillage humain de « L'usine ».
            "famille": j.famille, "libelle": j.libelle, "role": j.role, "lancable": j.lancable,
            "planifie": j.planifie,
            "timeout_s": j.timeout_s, "envoie_mail": j.envoie_mail, "gel": j.gel,
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
       timeout_s=900, envoie_mail=False, besoin_db=True, planifie=True, gel=None):
    assert raison and test and touche in ("eau", "exploitation"), f"job {nom} : raison/touche/test obligatoires"
    return Job(nom, titre, cadence, cron_utc, heure_reunion, _impl(nom),
               raison=raison, touche=touche, test=test,
               timeout_s=timeout_s, envoie_mail=envoie_mail, besoin_db=besoin_db, planifie=planifie, gel=gel)


JOBS: dict[str, Job] = {j.nom: j for j in [
    # ══════════════════ L'EAU — surveillance & ingestion des sources vitrine ══════════════════
    _j("sonde-sources", "Sonde des sources amont — détecte une nouvelle version, n'ingère pas",
       "quotidien", "0 3 * * *", "07:00", touche="eau", timeout_s=1800,
       raison="L'œil sur les 94 : chaque nuit, une requête HTTP sur toute source à amont interrogeable "
              "(millésime API/page, GetCapabilities daté, en-tête de fichier). Une version amont plus "
              "récente ⇒ cloche admin. N'ingère rien : la sentinelle prévient, Vic décide.",
       test="tests/test_cron1_registre.py::test_sonde_sources_couvre_le_max"),
    _j("agents-sources", "Agents de source (veille amont par IA) — le dimanche, 1 semaine sur 2, plafonné",
       "tous les 15 j (dim)", "0 19 * * 0", "23:00 dim", touche="eau", timeout_s=3600,
       raison="Le détective : sur les sources SANS amont lisible (que la sonde ne peut pas lire), un "
              "agent IA lit la page amont et dit s'il y a du neuf (jamais une réponse sans URL "
              "réellement consultée). Un passage TOUS LES 15 JOURS (dimanche nuit, semaines ISO paires), "
              "sous PLAFOND de dépense (LABUSE_AGENT_PLAFOND_EUR, défaut 0 = ne dépense rien) qui arrête "
              "proprement et signale les sources non traitées.",
       # COCKPIT-1 (Lot C, correction B) — REMIS AU CRONTAB (dimanche, 1 semaine sur 2 via
       # semaine_agents) : sans lui, les sources illisibles par la sonde n'étaient vérifiées par
       # personne. Prod : poser LABUSE_AGENT_PLAFOND_EUR=5 (le job cède au plafond, zéro surprise).
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
    # flux-13-10 — DVF (hebdo) reste au registre : flux QUOTIDIEN-DE-NUIT côté prod (prod fait foi,
    # le Mac récupère ensuite — cf. docs/EXPLOITATION.md). `ingest-ban` a été RETIRÉ du registre le
    # 13/10 : la table `adresses` (BAN) est une source de FOND Mac→prod (copiée par sources-maj-1 /
    # Phase 3a), jamais ingérée en prod → plus de cron ni de monitoring healthz pour elle.
    _j("ingest-dvf", "DVF — recharge à la nouvelle livraison Etalab",
       "hebdo (mar)", "0 1 * * 2", "05:00 mardi", touche="eau", timeout_s=3600,
       raison="DVF (mutations) nourrit le marché (prix secteur, radar). Détection J+2 (Last-Modified) : "
              "contrôle HEBDOMADAIRE (mardi) qui ne recharge QUE si une nouvelle livraison est publiée.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),   # dégel prod 20/10 : gel= retiré (job actif)

    # ══════════════════ L'EXPLOITATION — faire tourner le serveur ══════════════════
    _j("backup-postgres", "Sauvegarde PostgreSQL (dump + rotation, 4 conservés)", "quotidien",
       "30 9 * * *", "13:30", touche="exploitation", timeout_s=1800, besoin_db=False,
       raison="La seule sauvegarde : sans elle, une panne disque perd toute la base. Quotidien, 4 dumps "
              "conservés. RECOUPEMENT tranché : l'expression LEGACY (`30 9 * * *`) est reprise à "
              "l'identique — c'est le job réellement actif en prod ; garder l'horaire exact garantit un "
              "remplacement SANS TROU (le nouveau tourne au même instant que l'ancien ; deploy.sh pose "
              "avant de retirer le legacy).",
       test="tests/test_cron1_registre.py::test_backup_sans_trou"),
    # DISQUE-EXTERNE-1 (14/10) — la copie hors-VPS n'est PLUS un job VPS : c'est le Mac de Vic qui
    # tire le dernier dump par ssh et le range sur son disque externe (deploy/mac/backup_offsite_disque.sh,
    # agent launchd com.labuse.backup-offsite). Le VPS ne pousse plus rien (le stockage objet chiffré est
    # abandonné) ; il se contente de LIRE la date de la dernière copie externe (marqueur .copie-externe.json
    # déposé par le Mac) et d'ALERTER « branche le disque » si elle a plus de 10 j — cf. ops_alertes et le
    # récap du matin. Le job `backup-offsite` a donc été RETIRÉ du registre (et du crontab, en ciblé).
    _j("pg-maintenance", "VACUUM ANALYZE des tables chaudes", "hebdo (dim)",
       "0 0 * * 0", "04:00 dim", touche="exploitation", timeout_s=3600, besoin_db=False,
       raison="Sans VACUUM ANALYZE, le planner PostgreSQL dérive et les requêtes chaudes ralentissent. "
              "Hebdomadaire (dimanche), hors des heures d'usage.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("purge-runs", "Purge des vieux runs de scoring (garde servi + 2 précédents)", "hebdo (dim)",
       "30 0 * * 0", "04:30 dim", touche="exploitation", timeout_s=3600,
       raison="Sans purge, les runs de scoring s'empilent (q_v11→q_v20) et gonflent dryrun_cascade_results "
              "à 12–16 Go (cause n°1 du ménage MENAGE-1). Garde le servi + 2 précédents + les runs "
              "référencés (lignée/exceptions/démo) + les épinglés ; supprime le reste puis VACUUM ANALYZE "
              "(pas FULL : aucun verrou exclusif, sûr en prod). Hebdo (dim) après l'entretien de la base.",
       # MENAGE-1 (geste 10) — GELÉ au registre : la rétention vivait à la BASCULE (purge-runs-morts,
       # « jamais un cron »). Au registre (connu, monitoré, lançable à la main, crontab COMMENTÉ) ;
       # dégel quand Vic valide l'automatisation du DELETE.
       gel="MENAGE-1 — purge auto à valider avant dégel",
       test="tests/test_cron1_registre.py::test_purge_runs_gele_garde_servi_plus_deux"),
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
    # CORRECTIFS-1 E5 — maintenance quotidienne : détection d'abus + purge des sessions expirées.
    # Horaires REPRIS À L'IDENTIQUE des fichiers cron legacy (labuse-abuse 10:00 Réunion, labuse-sessions
    # 08:00 Réunion) → remplacement sans trou avant retrait des fichiers legacy (réconciliation 14/10).
    _j("abuse-scan", "Détection d'abus (usage anormal / partage de compte)", "quotidien",
       "0 6 * * *", "10:00", touche="exploitation", timeout_s=300,
       raison="Repère chaque jour les usages anormaux (extraction massive, partage de compte : IP "
              "distinctes simultanées) et les signale — jamais de blocage automatique, informatif.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    _j("purge-sessions", "Purge des sessions d'authentification expirées", "quotidien",
       "0 4 * * *", "08:00", touche="exploitation", timeout_s=120,
       raison="Supprime les sessions_auth EXPIRÉES (expire_at < now) : minimisation des données et "
              "hygiène de la table de sessions. Aucune session active touchée.",
       test="tests/test_cron1_registre.py::test_job_a_une_raison"),
    # VEILLE-2 (Lot 5) — plus d'ALERTE Radar séparée : le Radar alimente la CLOCHE (kind radar), et le
    # digest du matin (07:15) l'e-maile avec le reste. Ce job (07:05) POSE les événements Radar à la cloche
    # AVANT le digest ; il n'envoie AUCUN mail lui-même.
    _j("radar-cloche", "Radar — annonces du jour qui matchent une veille → cloche (avant le digest)",
       "quotidien", "5 3 * * *", "07:05", touche="exploitation", timeout_s=1200,
       raison="Chaque annonce du jour qui matche une veille Radar d'un client se pose à SA cloche (kind "
              "radar → l'annonce), pour que le digest du matin l'e-maile avec les parcelles suivies et les "
              "nouveautés. Idempotent (dédup compte+bien+jour). N'envoie aucun mail (le digest s'en charge).",
       test="tests/test_veille2_lot5.py::test_un_seul_mail_par_jour_trois_comptes", gel="Phase 8 Stéphanie"),
    # ── RADAR-AUTO-1 (Lot C) — le cycle de vie, DÉSORMAIS PLANIFIÉ. La capture automatique (extension,
    # rythme humain) rend ces jobs utiles chaque nuit : sans eux, une annonce expirée reste « active »,
    # aucune vente DVF ne se rapproche, la cible Courrier ne se qualifie jamais (cf. RADAR-AUDIT-1 §6c).
    # Ils étaient codés+idempotents mais non branchés ; le mandat RADAR-AUTO-1 renverse ce choix.
    _j("radar-cycle", "Radar — cycle de vie quotidien (expirées / en-vente-longue / à-revérifier)",
       "quotidien", "0 0 * * *", "04:00", touche="exploitation", timeout_s=600,
       raison="Après la capture du soir : une annonce expirée côté portail passe `retiree`, > 90 j en "
              "ligne → `en_vente_longue`, > 60 j sans confirmation → `a_reverifier`. Sans ce job, le "
              "cycle fige et une annonce expirée reste « active » indéfiniment (RADAR-AUDIT-1 §6c). "
              "Idempotent, zéro réseau.",
       test="tests/test_radar_auto1.py::test_jobs_cycle_planifies", gel="Phase 8 Stéphanie"),
    _j("radar-cycle-dvf", "Radar — rapprochement DVF (bien rattaché Sourcé + vente → vendue)",
       "quotidien", "30 0 * * *", "04:30", touche="exploitation", timeout_s=900,
       raison="Un bien RATTACHÉ Sourcé dont la parcelle a une mutation DVF « Vente » dans [3;18] mois "
              "après publication passe `vendue` (+ délai, écart affiché/acté). Alimente l'entonnoir "
              "vendue → Courrier et le digest. Après l'ingestion DVF. Jamais sur une PISTE.",
       test="tests/test_radar_auto1.py::test_jobs_cycle_planifies", gel="Phase 8 Stéphanie"),
    _j("radar-cycle-mensuel", "Radar — qualification mensuelle retiree_sans_vente (cible Courrier)",
       "mensuel (1er)", "30 1 1 * *", "05:30 le 1er", touche="exploitation", timeout_s=600,
       raison="La CIBLE Courrier : un bien `retiree` rattaché, retiré depuis > 12 mois et SANS mutation "
              "DVF « Vente » depuis la publication → `retiree_sans_vente`. JAMAIS depuis un lien mort — "
              "seule l'absence de vente DVF prouvée qualifie. Sans ce job, l'entonnoir Courrier dort.",
       test="tests/test_radar_auto1.py::test_jobs_cycle_planifies", gel="Phase 8 Stéphanie"),

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
    _j("digest", "Veille — DIGEST du matin (UN mail par compte : suivis + Radar + nouveautés)",
       "quotidien", "15 3 * * *", "07:15", touche="exploitation", timeout_s=900, envoie_mail=True,
       raison="TOUT ce qui change pour un compte la veille (parcelles suivies, Radar, nouveautés de l'app) "
              "part en UN digest quotidien, filtré par préférence, jamais vide, un par jour (dédup mail_queue). "
              "Passe par mail_queue. Sans événement la veille : pas de mail (dry-run si SMTP absent).",
       test="tests/test_veille_fix1.py::test_les_jobs_veille_existent", gel="Phase 8 Stéphanie"),
    # VEILLE-FIX-2 (Lot D) — LE CONSOMMATEUR DE LA FILE. Toutes les 5 min, il fait partir ce qui est
    # `en_attente` (immédiats différés, dont le digest ; programmés J+3/J+10) et rejoue les `a_rejouer`
    # dont l'heure est venue (5 min → 1 h → 24 h). Sans lui, un mail programmé ne partait jamais et un
    # échec Brevo n'était jamais rejoué (VEILLE-AUDIT-2 §2.2). envoie_mail=True → dry-run si SMTP absent.
    # COCKPIT-1 (Lot C, correction A) — RESTE toutes les 5 min (mots de passe, confirmations, invitations
    # ne peuvent pas attendre un jour), mais CÈDE À LA SAUVEGARDE : s'il démarre pendant le pg_dump
    # (verrou de backup-postgres tenu), il SAUTE ce passage proprement (statut ok, ni échec ni alerte) et
    # repart 5 min plus tard, hors de la fenêtre du dump. Fin de la fausse alerte quotidienne de 13:35
    # (ECARTS.md #1) SANS ralentir les mails clients. Garde : jobs_impl._sauvegarde_en_cours.
    _j("mail-queue-consommer", "File des mails — envoie les dûs + rejoue les échecs transitoires",
       "5 min", "*/5 * * * *", "toutes les 5 min", touche="exploitation", timeout_s=300, envoie_mail=True,
       raison="La file mail_queue ne part pas toute seule : ce worker (toutes les 5 min) envoie les mails "
              "`en_attente` dûs (mot de passe, confirmation, invitation, digest différé, programmés "
              "J+3/J+10) et rejoue les `a_rejouer` (échec Brevo transitoire, backoff 5 min/1 h/24 h) ; "
              "au-delà de 3 rejeux → `echec` (ligne rouge Comptes). Idempotent, jamais d'envoi en double. "
              "CÈDE à la sauvegarde : s'il démarre pendant le pg_dump, il saute ce passage (sans échec) "
              "et repart 5 min plus tard.",
       test="tests/test_veille_fix2_lot_d.py::test_worker_envoie_et_rejoue"),
    # COMMUNE-FIX-1 — RÉINSCRIT (le pied de la fiche commune promet « rafraîchis chaque nuit » : il faut
    # que la tâche existe VRAIMENT). Précalcule le contexte des 24 communes chaque nuit → ouverture < 500 ms
    # et date de précalcul honnête. Wrapper run-job.sh + verrou flock comme les autres (crontab dérivé du registre).
    _j("fiche-commune-cache", "Fiche commune — précalcul nocturne du contexte (24 communes)",
       "quotidien", "0 23 * * *", "03:00", touche="exploitation", timeout_s=1800,
       raison="Le contexte commune coûte 20–27 s à assembler (comparateur, Radar, Filosofi spatial, "
              "PPR…). Précalculé chaque nuit dans commune_contexte_cache, la fiche ouvre en < 500 ms et "
              "affiche une VRAIE date de calcul. Chaque commune est isolée (une ratée n'arrête pas le lot). "
              "Sans ce job, le cache fige et le pied « rafraîchis chaque nuit » ment.",
       test="tests/test_commune_fix1.py::test_a4_job_cache_nocturne_enregistre"),
    # COHERENCE-FIX-1 (lot G) — le banc de cohérence tourne CHAQUE NUIT sur l'île : chaque notion,
    # tous ses lecteurs, comparés à la tolérance près. Résultat dans coherence_runs (onglet
    # « Cohérence » de la page Données) ; cloche admin au premier écart FAUX-CLIENT NOUVEAU.
    _j("coherence-banc", "Banc de cohérence nocturne — chaque notion, tous ses lecteurs (île)",
       "quotidien", "45 23 * * *", "03:45", touche="exploitation", timeout_s=7200,
       raison="COHERENCE-1 a prouvé que deux caches périmés en silence faisaient mentir 70 % des "
              "écrans concernés pendant des jours. Le banc rejoue chaque nuit les comparaisons "
              "multi-lecteurs (fiche/SQL/tuiles/outils) sur l'échantillon gelé + les 24 communes, PUIS "
              "les 25 gardes CHASSE-DONNÉES (chasse_donnees) en-process contre la prod (SOLIDITE-1 Lot 2), "
              "PUIS le banc des 1 000+ invariants GÉNÉRÉS (CHASSE-INVARIANTS-2, scripts.coherence.invariants2.banc2) "
              "— le sous-ensemble rapide `--nuit` chaque nuit (SQL île + moteur), l'intégrale `--tout` le dimanche ; "
              "un FAUX-CLIENT nouveau / une garde en écart ouvre un incident à J+1 — plus jamais des mois.",
       test="tests/verrous/test_v6b_coherence.py::test_v6b_coherence_banc"),
    # COCKPIT-1 (Lot C, correction D) — `recap-matin` RETIRÉ du registre (Vic ne veut plus le mail récap
    # de 07:30). Mais « les ALERTES restent » : les vigies qu'il évaluait (disque, /readyz, sauvegarde,
    # copie externe, jobs en retard) via `ops_alertes.verifier_declencheurs` sont désormais ÉVALUÉES par
    # `healthcheck` (toutes les 15 min, besoin_db ouvre sa propre session) — chaque incident part par la
    # PORTE UNIQUE ops_alertes (mail Brevo + cloche, un rappel/jour, un « résolu »), SANS mail récap.
    # Le site en panne reste couvert par /health (healthcheck lève à 2 échecs → incident job-echec).
    # SOLIDITE-1 (Lot 5) — la vérité face aux sources, chaque mois : 20 parcelles au hasard (stratifiées)
    # comparées aux sources officielles EN LIGNE (cadastre IGN, Géorisques, DVF, bâtiments). Le 15 à 06:00.
    _j("verite-sources", "Vérité sources — 20 parcelles au hasard confrontées aux sources officielles en ligne",
       "mensuel (15)", "0 2 15 * *", "06:00 le 15", touche="exploitation", timeout_s=3600,
       raison="Une fois par mois, on confronte ce que LABUSE SERT aux sources officielles en ligne "
              "(cadastre IGN API Carto, GPU/Géorisques, DVF, bâtiments) sur 20 parcelles tirées au hasard "
              "et stratifiées (bizone, zone rouge, nouvelle, contenance ≠ dessin). Tout écart servi↔source "
              "ouvre un incident (parcelle + les deux valeurs). Séquentiel et espacé (quotas respectés), "
              "aucune écriture en base hors le rapport. L'œil extérieur qui ne dépend pas de nos propres caches.",
       test="tests/test_solidite1_lot5.py::test_verite_sources_au_registre"),
    # COCKPIT-1 (Lot C, correction E) — `restore-test` RETIRÉ du registre (donc du crontab VPS) : le
    # test mensuel de restauration tourne DÉJÀ hors-VPS sur le Mac (agent launchd deploy/mac/restore_test.sh,
    # DISQUE-EXTERNE-1 / AGENTS-LAUNCHD). Le poste VPS faisait doublon (et restait gelé). L'implémentation
    # `jobs_impl.restore_test` reste (exécutable à la main / testée) ; seul le JOB du registre part.
    _j("signal-instantane", "Instantané mensuel du Signal servi (fige la prédiction datée, mesurable forward)",
       "mensuel (1er)", "0 2 1 * *", "06:00 le 1er", touche="exploitation", timeout_s=1800,
       besoin_db=True,
       raison="FIX-PRIX-ET-OPPORTUNITES lot 4 — le volet E a montré que le Signal servi (P de vente 12 "
              "mois) sépare, mais que l'instantané réellement livré n'est pas jugeable tant que DVF "
              "n'a pas avancé. Chaque 1er du mois, on FIGE une copie datée du Signal servi (signal_p, "
              "niveau, bande par parcelle) dans sa seule table `signal_instantanes` — rien d'autre, aucun "
              "mail — pour la rejouer plus tard contre les ventes DVF postérieures (protocole forward).",
       test="tests/test_signal_instantane.py::test_job_signal_instantane_dans_le_registre"),

    # ── NON REPRIS (retirés du registre par CRON-1 lot 1, avec la raison — cf. CRON-1-LOT1.md) ──
    # Radar : PAS de job. Le traitement des dépôts est déclenché au dépôt (manuel) ; une ÉCHÉANCE
    #   attendue vit en base → dépassée = tâche du Résumé (verrou G8, lot 2). Donc radar-cycle,
    #   radar-releves : retirés.
    # sources-fraicheur : le verdict de fraîcheur est calculé À LA LECTURE (etats_sources) + la sonde
    #   des sources (sonde-sources) porte la veille amont ; un job nocturne de plus faisait doublon.
    # coherence-run : le mandat ne reprend QUE filtres-sources + coherence-robinets ; la cohérence de run
    #   est couverte par ces deux + les verrous (labuse circuit verrous).
    # rapport-admin : redondant avec la Tour de contrôle (Pilotage), qui montre l'exploitation en direct.
    # regles-references / ingest-bdnb : IA à la demande / amont 974 absent — jamais en cron (inchangé).
]}

#: CRON-1 lot 1 — les jobs qui TOUCHENT L'EAU, DÉRIVÉS du registre (`touche == 'eau'`) : chacun laisse
#: une ligne au journal unifié `circuit_journal`. Plus de liste tenue à la main (une seule source).
TOUCHE_EAU = frozenset(nom for nom, j in JOBS.items() if j.touche == "eau")


# ─────────── COCKPIT-1 (Lot B) — l'habillage humain de « L'usine » ───────────
# Quatre familles (colonnes, dans ce sens) : 1 Veille des sources · 2 Livraisons quotidiennes ·
# 3 Le moteur · 4 Contrôle, clients, sécurité. Chaque poste : (famille, libellé humain, rôle en une
# phrase, lancable). `lancable=True` = « Lancer maintenant » sans risque (sonde, contrôles, livraisons,
# ménage) ; les agents IA ont leur bouton « Démarrer » dédié (coût/plafond), jamais lancable ici ;
# sauvegarde/restauration/déploiement restent des gestes à part (pas de bouton de lancement libre).
FAMILLES = {1: "Veille des sources", 2: "Livraisons quotidiennes",
            3: "Le moteur", 4: "Contrôle, clients, sécurité"}

_FAMILLE_LIBELLE_ROLE: dict[str, tuple[int, str, str, bool]] = {
    # ── 1 · Veille des sources ──
    "sonde-sources": (1, "Le veilleur de nuit",
                      "Regarde chaque nuit si les producteurs ont publié une nouvelle version. Gratuit.", True),
    "agents-sources": (1, "Les enquêteurs IA",
                       "Pour les sources que le veilleur ne sait pas lire : un agent lit la page amont. Coûte quelques centimes le passage.", False),
    # ── 2 · Livraisons quotidiennes ──
    "ingest-bodacc": (2, "Livreur BODACC", "Procédures collectives, chaque matin.", True),
    "ingest-dvf": (2, "Livreur DVF", "Ventes immobilières, à chaque nouvelle livraison.", True),
    "ingest-sitadel": (2, "Livreur Sitadel", "Permis de construire, une fois par mois.", True),
    "ingest-dpe": (2, "Livreur DPE", "Diagnostics énergie, une fois par mois.", True),
    "ingest-sirene": (2, "Livreur SIRENE", "Entreprises géolocalisées, une fois par mois.", True),
    "sync-gpu": (2, "Livreur GPU", "Documents d'urbanisme (PLU), une fois par mois.", True),
    # ── 3 · Le moteur ──
    "fiche-commune-cache": (3, "Le précalcul des fiches commune",
                            "Prépare chaque nuit le contexte des 24 communes pour que la fiche ouvre vite.", True),
    "signal-instantane": (3, "L'instantané du Signal",
                          "Fige une copie datée du Signal servi, une fois par mois, pour la mesurer plus tard.", True),
    # ── 4 · Contrôle, clients, sécurité ──
    "filtres-sources": (4, "Le filtre des sources",
                        "Rejoue chaque nuit les contrôles qualité sur les versions réellement servies.", True),
    "coherence-robinets": (4, "La sonde du circuit",
                           "Vérifie que deux chemins d'un même chiffre donnent bien la même valeur (fuites).", True),
    "coherence-banc": (4, "Le contrôleur de nuit",
                       "Relit chaque chiffre sur tous les écrans — zéro faux chez le client.", True),
    "verite-sources": (4, "Le vérificateur mensuel",
                       "Compare 20 parcelles au hasard aux sites officiels, une fois par mois.", True),
    "backup-postgres": (4, "La sauvegarde",
                        "Copie complète de la base chaque jour, 4 conservées.", False),
    "pg-maintenance": (4, "L'entretien de la base",
                       "Réaligne le moteur PostgreSQL chaque dimanche pour garder les requêtes rapides.", True),
    "purge-runs": (4, "La purge des vieux runs",
                   "Garde le run servi et les 2 précédents, supprime les plus anciens pour que la base n'enfle pas. Gelé tant que Vic ne l'a pas validé.", True),
    "healthcheck": (4, "La sonde de vie",
                    "Vérifie toutes les 15 min que l'app répond, le disque, la sauvegarde et les jobs en retard.", False),
    "sante-endpoints": (4, "La sonde métier",
                        "Vérifie toutes les 30 min que les écrans clés répondent avec la base.", False),
    "copilote-purge": (4, "La purge du Copilote",
                       "Efface les conversations Copilote au-delà de la rétention.", True),
    "abuse-scan": (4, "Le détecteur d'abus",
                   "Repère chaque jour les usages anormaux (partage de compte). Informatif.", True),
    "purge-sessions": (4, "Le ménage des sessions",
                       "Supprime chaque jour les sessions de connexion expirées.", True),
    "mail-queue-consommer": (4, "Le courrier aux clients",
                             "Envoie les mails en attente toutes les 5 min ; cède à la sauvegarde.", True),
    "evaluer-suivis": (4, "La veille des parcelles suivies",
                       "Prévient un client quand un fait tombe sur une parcelle qu'il suit.", True),
    "detect-events": (4, "La veille du marché",
                      "Repère les bascules de classement entre le run servi et le précédent.", True),
    "digest": (4, "Le digest du matin",
               "Un mail par client avec tout ce qui a changé pour lui la veille.", False),
    "radar-cloche": (4, "Le Radar → cloche",
                     "Pose à la cloche de chaque client les annonces du jour qui matchent sa veille.", True),
    "radar-cycle": (4, "Le cycle du Radar",
                    "Fait vivre les annonces : expirées, en vente longue, à revérifier.", True),
    "radar-cycle-dvf": (4, "Le rapprochement Radar ↔ ventes",
                        "Marque « vendue » une annonce dont la parcelle a une vente DVF.", True),
    "radar-cycle-mensuel": (4, "La cible Courrier du Radar",
                            "Qualifie chaque mois les biens retirés sans vente (cible Courrier).", True),
}

# un méta-contrôle : chaque job du registre a son habillage (et réciproquement) — sinon l'assertion
# saute au chargement du module (plus jamais un poste « nu » ou une entrée morte à l'écran).
assert set(_FAMILLE_LIBELLE_ROLE) == set(JOBS), (
    "COCKPIT-1 : écart registre ↔ habillage usine — "
    f"manquants : {sorted(set(JOBS) - set(_FAMILLE_LIBELLE_ROLE))} · "
    f"en trop : {sorted(set(_FAMILLE_LIBELLE_ROLE) - set(JOBS))}")
for _nom, (_fam, _lib, _role, _lanc) in _FAMILLE_LIBELLE_ROLE.items():
    _j_obj = JOBS[_nom]
    _j_obj.famille, _j_obj.libelle, _j_obj.role, _j_obj.lancable = _fam, _lib, _role, _lanc
