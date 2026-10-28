"""CRON-1 — l'implémentation de chaque job. Un job = une fonction `<nom_avec_underscores>(ctx: JobContext)`
qui remplit `ctx.compteurs` (compteurs métier remontés dans l'état + le mail admin) et lève en cas d'échec
(le runner capture, écrit l'état, alerte). RÉUTILISE le code existant — aucun pipeline dupliqué.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text

from .config import get_settings
from .jobs import JobContext, lire_etat, state_path
from .tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17/D-02/D-04) — LE jour métier = jour Réunion

log = logging.getLogger("labuse.jobs.impl")

# taille minimale d'un dump sain : un dump anormalement petit = échec (base vide, coupure). Constante.
BACKUP_MIN_MO = 1.0
# CRON-2 — rotation en CONSTANTE : on garde les N dumps les plus récents. Le pull-mac de Vic archive
# plus loin (disque externe) ; le VPS ne conserve qu'une fenêtre courte. CORRECTIFS-1 : aligné sur le
# shell de prod (`backup_postgres.sh`).
# DONNEES-ETAT-FIX-1 (Lot E) — 4 → 2 quotidiens (+ 1 hebdo côté shell) : un dump LEAN pèse ~7 Go ;
# 4 quotidiens + historique hebdo saturaient le disque (écart 1, disque à 94 % le 27/10). L'HISTORIQUE
# vit AILLEURS (le Mac rapatrie chaque matin + le disque externe) ; le VPS ne garde qu'une fenêtre
# courte de reprise. Le garde-disque structurel de backup_postgres.sh reste le dernier filet.
BACKUP_ROTATION_N = 2


def _libpq_url(url: str) -> str:
    """URL SQLAlchemy → URL libpq comprise par pg_dump/psql (retire le driver `+psycopg`)."""
    return url.replace("+psycopg2", "").replace("+psycopg", "")


# ═══════════════════════════ K3 — quotidiens ═══════════════════════════

def backup_postgres(ctx: JobContext) -> None:
    """UNE SEULE méthode de sauvegarde : le job DÉLÈGUE au script de prod `deploy/scripts/backup_postgres.sh`
    (dump LEAN `pg_dump -Fc` ~6,5 Go — data reconstructible + schémas reliquat `sauvegarde_*` exclus,
    contrôle `pg_restore --list`, rotation locale). Plus de pg_dump propre au job (qui produisait un
    `.sql.gz` FULL ~31 Go saturant le disque). Verrou / log / état / alerte restent portés par le runner
    (jobs.py). Rotation : BACKUP_ROTATION_N dumps quotidiens gardés (via LABUSE_BACKUP_KEEP)."""
    s = get_settings()
    script = Path(__file__).resolve().parents[2] / "deploy" / "scripts" / "backup_postgres.sh"
    if not script.is_file():
        raise RuntimeError(f"script de sauvegarde introuvable : {script}")
    env = dict(os.environ)
    env["LABUSE_BACKUP_KEEP"] = str(BACKUP_ROTATION_N)          # 2 dumps quotidiens gardés (Lot E)
    env.setdefault("LABUSE_BACKUP_DIR", s.backup_dir)
    if s.pg_bin_dir:                                            # pg_dump/pg_restore du bon PostgreSQL
        env["PATH"] = f"{s.pg_bin_dir}:{env.get('PATH', '')}"
    proc = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, check=False)
    sortie = (proc.stdout or "") + (proc.stderr or "")
    for ligne in sortie.splitlines():                          # le détail du script va dans le log du job
        log.info("backup_postgres.sh | %s", ligne)
    if proc.returncode != 0:
        raise RuntimeError(f"backup_postgres.sh a échoué (code {proc.returncode}) : {sortie.strip()[-400:]}")
    # Retrouver le dump produit : ligne « … → /chemin.dump » du script ; repli = le plus récent du dossier.
    dump = None
    for ligne in sortie.splitlines():
        if "→" in ligne and ligne.rstrip().endswith(".dump"):
            dump = Path(ligne.split("→", 1)[1].strip())
            break
    if dump is None or not dump.is_file():
        dumps = sorted(Path(env["LABUSE_BACKUP_DIR"]).glob("labuse-*.dump"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        dump = dumps[0] if dumps else None
    if dump is None or not dump.is_file():
        raise RuntimeError("backup_postgres.sh terminé sans dump localisable")
    taille_mo = round(dump.stat().st_size / 1e6, 2)
    if taille_mo < BACKUP_MIN_MO:                               # garde-fou : un dump minuscule = suspect
        raise RuntimeError(f"dump anormalement petit ({taille_mo} Mo < {BACKUP_MIN_MO}) — suspect, rejeté")
    ctx.compte(dump=dump.name, taille_mo=taille_mo, methode="backup_postgres.sh (lean)",
               rotation_gardes=BACKUP_ROTATION_N)


def sources_fraicheur(ctx: JobContext) -> None:
    """Pour chaque source affichée : dernier millésime/ingestion vs cadence attendue (data_sources.
    source_cadence — la table de référence des cadences, JAMAIS en dur) → statut à_jour / en_retard /
    en_panne écrit en base (`fraicheur_statut`). C'est CE job qui alimente les badges de la page sources."""
    db = ctx.db
    # colonnes de statut servi aux badges (idempotent, migration propre in-place).
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_statut varchar(16)"))
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_calcule_at timestamptz"))
    # CONNEXIONS-2 Lot 6.2 (KO-14) — un ÉCHEC d'ingestion doit devenir un état visible « en erreur »,
    # distinct de l'ancienneté : ces colonnes portent la DATE et le MOTIF du dernier run échoué.
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_erreur_at timestamptz"))
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_erreur_message text"))
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS affichage_desactive boolean "
                    "NOT NULL DEFAULT false"))
    # cadences → seuil en jours (au-delà = en_retard ; au-delà de 2× = en_panne). Depuis la table, pas le code.
    seuils = {"hebdomadaire": 10, "mensuelle": 40, "trimestrielle": 100, "semestrielle": 200,
              "annuelle": 400, "continue": 10}
    #: statuts de run considérés « en cours / réussis » — tout AUTRE statut non nul = ÉCHEC (KO-14).
    RUN_OK = {"ok", "success", "running", "en_cours", "started", "partial", "partiel"}
    # CRON-2 — les AFFICHÉES seulement, avec le MÊME prédicat que /sources (est_affichee, ceinture Python
    # canonique) : 59 sources annoncées = 59 statuts calculés. C'est ce qui réconcilie le compte (le 67
    # comptait des sources non affichées ; le prédicat retire doublons/retirées/dormantes/masquées).
    from .sources_catalog import est_affichee
    tous = db.execute(text(
        "SELECT id, name, technical_notes, status, source_cadence, affichage_desactive, "
        "  GREATEST(COALESCE(source_horizon_at, last_sync_at), last_sync_at) AS reference "
        "FROM data_sources")).mappings().all()
    rows = [r for r in tous
            if est_affichee(r["name"], r["technical_notes"], r["status"], r["affichage_desactive"])]
    # KO-14 — dernier run d'ingestion PAR source (via la FK data_source_id) : s'il a échoué, la source
    # passe « en erreur » quelle que soit son ancienneté (un plantage récent n'est pas « à jour »).
    dernier_run = {r["data_source_id"]: r for r in db.execute(text(
        "SELECT DISTINCT ON (data_source_id) data_source_id, status, "
        "  COALESCE(finished_at, started_at) AS le "
        "FROM ingestion_runs WHERE data_source_id IS NOT NULL "
        "ORDER BY data_source_id, started_at DESC")).mappings().all()}
    now = datetime.now(timezone.utc)
    compteurs = {"a_jour": 0, "en_retard": 0, "en_panne": 0, "sans_echeance": 0, "en_erreur": 0, "total": 0}
    for r in rows:
        compteurs["total"] += 1
        run = dernier_run.get(r["id"])
        run_echoue = run is not None and run["status"] is not None \
            and str(run["status"]).strip().lower() not in RUN_OK
        if run_echoue:
            statut = "en_erreur"
            db.execute(text(
                "UPDATE data_sources SET fraicheur_statut = 'en_erreur', fraicheur_calcule_at = now(), "
                "  fraicheur_erreur_at = :le, fraicheur_erreur_message = :m WHERE id = :i"),
                {"le": run["le"], "m": f"Dernière ingestion : {run['status']}", "i": r["id"]})
        else:
            cad = (r["source_cadence"] or "").strip().lower()
            seuil = next((v for k, v in seuils.items() if cad.startswith(k[:6])), None)
            ref = r["reference"]
            if seuil is None or ref is None:
                statut = "sans_echeance"
            else:
                age = (now - (ref if ref.tzinfo else ref.replace(tzinfo=timezone.utc))).days
                statut = "a_jour" if age <= seuil else ("en_retard" if age <= 2 * seuil else "en_panne")
            # un run redevenu bon EFFACE l'erreur mémorisée (jamais un « en erreur » qui colle).
            db.execute(text(
                "UPDATE data_sources SET fraicheur_statut = :s, fraicheur_calcule_at = now(), "
                "  fraicheur_erreur_at = NULL, fraicheur_erreur_message = NULL WHERE id = :i"),
                {"s": statut, "i": r["id"]})
        compteurs[statut] += 1
    ctx.compte(**compteurs)


def fiche_commune_cache(ctx: JobContext) -> None:
    """FICHE-COMMUNE-2 (C1) — précalcule le CONTEXTE de chaque commune (le payload ENTIER de
    /communes/{c}/contexte, ~20 s/commune) dans `commune_contexte_cache`, pour une ouverture < 500 ms.
    Chaque commune est ISOLÉE : un échec la marque et n'arrête pas le lot (rollback ciblé) ; le job DIT
    combien d'OK/échecs. Point d'écriture unique du cache (aussi « lançable à la main » : jobs run)."""
    db = ctx.db
    from .api.app import rafraichir_contexte_cache
    # VITESSE-2 (Lot 1) — réchauffe le cache PARTAGÉ des indicateurs bruts (24 communes, ~5 s) UNE
    # fois ici : tous les workers le liront en base au lieu de le recalculer au 1ᵉʳ clic (DEPLOY-1028
    # §Phase 4). Non bloquant pour le précalcul des fiches ci-dessous.
    try:
        from .api.comparateur import rafraichir_raw_cache
        rafraichir_raw_cache(db)
    except Exception as e:  # noqa: BLE001 — l'échec du raw cache ne doit pas tuer le précalcul des fiches
        db.rollback()
        ctx.compte(raw_cache_erreur=str(e)[:120])
    communes = [r[0] for r in db.execute(text(
        "SELECT DISTINCT commune FROM parcels WHERE commune IS NOT NULL ORDER BY commune")).all()]
    ok, echecs, noms_echecs = 0, 0, []
    for c in communes:
        try:
            rafraichir_contexte_cache(db, c)
            db.commit()                              # durabilité par commune
            ok += 1
        except Exception as e:  # noqa: BLE001 — une commune ratée ne tue pas le lot
            db.rollback()
            echecs += 1
            noms_echecs.append(f"{c}: {e}"[:120])
    ctx.compte(communes_ok=ok, communes_echecs=echecs, total=len(communes),
               echecs=noms_echecs[:5] or None)
    if echecs and ok == 0:                           # tout a raté → échec BRUYANT (jamais un cache vide muet)
        raise RuntimeError(f"fiche-commune-cache : {echecs} échecs sur {len(communes)}, 0 succès")


def signal_instantane(ctx: JobContext) -> None:
    """FIX-PRIX-ET-OPPORTUNITES lot 4 — fige l'instantané mensuel DATÉ du Signal servi (signal_p,
    niveau, bande par parcelle) dans SA table `signal_instantanes`, pour le juger forward contre les
    ventes DVF à venir (protocole volet E). N'écrit QUE dans sa table, n'envoie aucun mail. Idempotent
    (une clé par date×parcelle) : relancé le même jour, il ne duplique rien."""
    from .signal_instantane import figer
    r = figer(ctx.db)
    ctx.compte(snapshot_le=r.get("snapshot_le"), run=r.get("run_label"),
               figees=r.get("n"), inserees=r.get("inseres"), par_niveau=r.get("par_niveau"),
               note=r.get("note"))


def coherence_banc(ctx: JobContext) -> None:
    """COHERENCE-FIX-1 (lot G) + PRE-DEPLOY-1 (lot A) — joue le banc de cohérence (mode --ile)
    EN-PROCESS (TestClient FastAPI), journalise le passage (coherence_runs) et laisse la cloche
    sonner au premier FAUX-CLIENT nouveau.

    EN-PROCESS, jamais l'API publique : plus de HTTP vers le port servi, donc PLUS de quota
    anti-scraping ni de `LABUSE_DEV_MODE` (l'API refuse même de démarrer avec ce flag hors 'local').
    L'auth reste active — le banc mint une session pilote en interne (cf. lib.client_en_process)."""
    import sys
    from pathlib import Path
    racine = Path(__file__).resolve().parents[2]
    if str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
    try:
        from scripts.coherence.banc import run as _run_banc
    except Exception as e:  # noqa: BLE001 — le banc fait partie du produit : introuvable = échec
        raise RuntimeError(f"banc introuvable : {e}") from e
    _run_banc(ile=True, en_process=True)      # écrit ECARTS.csv (lecteurs en-process, sans réseau)
    from .coherence_journal import journaliser_passage
    res = journaliser_passage(ctx.db, mode="ile")
    ctx.db.commit()
    ctx.compte(**res)
    # SOLIDITE-1 (Lot 2) — PUIS les 25 gardes CHASSE-DONNÉES, en-process contre la prod. Toute garde en
    # écart ouvre un incident par la porte unique (chasse_journal → ops_alertes) ; retour au vert = résolu.
    from . import chasse_banc, chasse_journal
    resultats = chasse_banc.jouer_gardes_en_process()
    res2 = chasse_journal.journaliser_passage(ctx.db, resultats)
    ctx.db.commit()
    ctx.compte(chasse_gardes=res2["n_gardes"], chasse_ok=res2["ok"], chasse_ecart=res2["ecart"],
               chasse_skip=res2["skip"], chasse_ecart_nouveaux=res2["ecart_nouveaux"])
    # un banc qui n'a rien pu lire (tout en « erreur lecteur ») est un ÉCHEC bruyant, jamais un
    # passage vert par vacuité (app non démarrable, base coupée…).
    if res["ecarts"] == 0 and res["erreurs_lecteur"] > 100:
        raise RuntimeError(f"banc illisible : {res['erreurs_lecteur']} lecteurs en erreur "
                           "(app non démarrable en-process ou base coupée) — passage non probant.")
    # pareil pour la chasse : tout en SKIP = banc non probant (app/DB inatteignables en-process).
    if res2["n_gardes"] and res2["skip"] == res2["n_gardes"]:
        raise RuntimeError(f"banc chasse illisible : {res2['skip']}/{res2['n_gardes']} gardes en SKIP "
                           "(app non démarrable en-process ou base coupée) — passage non probant.")
    # CHASSE-INVARIANTS-FIX-2 (3) — PUIS le banc des 1 000+ invariants GÉNÉRÉS (vague 2). Chaque nuit
    # le sous-ensemble RAPIDE (`--nuit` : SQL île + moteur, ~4 min, sans les 2 boucles API cadencées) ;
    # le DIMANCHE, TOUT (`--tout`, ~18 min, inclut F2 valeur inter-surfaces et F5 API). Lecture seule.
    import os
    try:
        from scripts.coherence.invariants2.banc2 import executer as _banc2
    except Exception as e:  # noqa: BLE001 — le banc fait partie du produit : introuvable = échec
        raise RuntimeError(f"banc2 (invariants générés) introuvable : {e}") from e
    # FIX-ORFEVRE-1 pt 3 (D-02) — « dimanche » = dimanche RÉUNION, pas le fuseau du process : sur un
    # serveur UTC (branche admise par deploy.sh), le naïf disait samedi 23:45 → l'intégrale glissait
    # d'une nuit, silencieusement. Le cron vise 03:45 Réunion : le jour Réunion est LA référence.
    _mode = "tout" if today_reunion().weekday() == 6 else "nuit"   # dimanche = l'intégrale hebdo
    _api = os.environ.get("LABUSE_BANC2_API") or "http://127.0.0.1:8793"
    _bil = _banc2(mode=_mode, api=_api, base=True)
    ctx.compte(banc2_mode=_mode, banc2_ok=_bil["ok"], banc2_ecart=_bil["ecart"],
               banc2_skip=_bil["skip"], banc2_regles=_bil["n"], banc2_duree_s=_bil["duree_s"])
    # banc2 n'a rien pu exécuter (0 règle) = passage non probant (modules introuvables / DB coupée).
    if _bil["n"] == 0:
        raise RuntimeError("banc2 non probant : 0 règle exécutée (modules invariants2 ou base inatteignables).")


def radar_cycle(ctx: JobContext) -> None:
    """RADAR-AUTO-1 (Lot C) — cycle de vie QUOTIDIEN des annonces, désormais PLANIFIÉ (la collecte
    automatique par l'extension le rend utile chaque nuit) : expirées (expiration_date portail) →
    retiree ; > 90 j → en_vente_longue ; > 60 j sans confirmation → a_reverifier. Ne fetch RIEN."""
    from .pige import cycle
    r = cycle.run_quotidien(ctx.db)
    ctx.compte(**(r if isinstance(r, dict) else {"resultat": str(r)}))


def radar_cycle_dvf(ctx: JobContext) -> None:
    """RADAR-AUTO-1 (Lot C) — rapprochement DVF : un bien RATTACHÉ Sourcé + mutation DVF « Vente » dans
    [3;18] mois après publication → `vendue` (+ délai, écart affiché/acté). Après l'ingestion DVF."""
    from .pige import cycle
    r = cycle.run_dvf(ctx.db)
    ctx.compte(**(r if isinstance(r, dict) else {"resultat": str(r)}))


def radar_cycle_mensuel(ctx: JobContext) -> None:
    """RADAR-AUTO-1 (Lot C) — mensuel : la CIBLE Courrier. `retiree` rattaché > 12 mois SANS vente DVF
    → `retiree_sans_vente`. Jamais depuis un lien mort : seule l'absence de mutation DVF qualifie."""
    from .pige import cycle
    r = cycle.run_mensuel(ctx.db)
    ctx.compte(**(r if isinstance(r, dict) else {"resultat": str(r)}))


def radar_cloche(ctx: JobContext) -> None:
    """VEILLE-2 (Lot 5) — POSE à la cloche (kind `radar`, compte-scopé) chaque annonce du jour qui matche
    une veille d'un client → clic vers l'annonce. AUCUN mail : le digest du matin (07:15) l'e-maile avec
    le reste (plus d'alerte Radar séparée). Idempotent (dédup compte+bien+jour)."""
    from .pige import digests
    from .api.events import ensure_tables
    from .db import engine
    ensure_tables(engine())
    r = digests.evaluer_radar_cloche(ctx.db)
    ctx.compte(**r)


def evaluer_suivis(ctx: JobContext) -> None:
    """VEILLE-2 (Lot 1) — évalue les PARCELLES SUIVIES : vente (DVF) / permis (Sitadel) / procédure
    (BODACC) / changement de propriétaire PM SUR la parcelle → notifications event_log
    kind=parcelle_suivie (la bascule du score est produite par detect-events). Reprend le legacy du matin
    (07:00). Zéro modèle, dédup par fait → un rejeu ne recrée rien (idempotent)."""
    from .api.events import ensure_tables, evaluer_suivis as _eval
    from .db import engine
    ensure_tables(engine())
    r = _eval(ctx.db)
    ctx.compte(total=sum(r.values()), **r)


# VEILLE-2 (Lot 4) — `evaluer_secteurs` RETIRÉ : les secteurs (zones dessinées) sont archivés, plus
# jamais évalués (la page Veille n'a que PARCELLE et RADAR). `alertes.evaluer_tous_secteurs` n'a plus de
# job (retiré du registre et du verrou V8a).


def detect_events(ctx: JobContext) -> None:
    """VEILLE-2 (Lot 4) — BASCULES DU MARCHÉ : diffe le run servi et son précédent (table des runs, jamais
    une constante) → événements `bascule`/`bodacc` + bascule du score sur les parcelles suivies. (L'ancienne
    évaluation des recherches sauvegardées est retirée.) Idempotent par (kind, idu, run_from, run_to) :
    rejeu = 0. Aucun run précédent (première install) → rien à diffuser, exit 0."""
    from sqlalchemy import text as _text

    from . import runs
    from .api.events import detect_events as _detect, ensure_tables
    from .db import engine
    ensure_tables(engine())
    run_to = runs.current()
    # Le VRAI précédent du run SERVI = le run calculé JUSTE AVANT lui (computed_at < servi), jamais le
    # « dernier autre run » (qui peut être un CANDIDAT calculé APRÈS le servi et non promu → un diff à
    # l'envers qui fabrique des bascules fantômes). run_precedent_servi ne filtre pas sur computed_at ;
    # ici on prend le prédécesseur chronologique réel. Aucun prédécesseur → rien à diffuser (exit 0).
    prev = ctx.db.execute(_text(
        "SELECT run_id FROM p_score_v2_runs "
        "WHERE computed_at < (SELECT computed_at FROM p_score_v2_runs WHERE run_id = :s) "
        "ORDER BY computed_at DESC LIMIT 1"), {"s": run_to}).scalar()
    if not prev:
        ctx.compte(inserted=0, note="aucun run antérieur au servi — rien à diffuser")
        return
    out = _detect(ctx.db, prev, run_to, demo=False)
    ctx.compte(run_from=prev, run_to=run_to, **out)


def digest(ctx: JobContext) -> None:
    """VEILLE-FIX-1 (lot 1) — DIGEST DU MATIN (chaînes 1+2 : suivis de parcelle + secteurs + recherches)
    aux comptes actifs, filtré par préférence e-mail et par type. Passe par mail_queue (une ligne par
    envoi). Anti-double-envoi (last_digest_at + intervalle) ; digest vide ne part pas. En dry-run (sans
    SMTP) : calcule, ÉCRIT la ligne mail_queue, n'envoie RIEN."""
    from .api.events import ensure_tables, envoyer_digests
    from .db import engine
    ensure_tables(engine())
    base = get_settings().public_base_url or ""
    # VEILLE-FIX-2 (Lot C) — freq=None : chaque compte reçoit à SA cadence (quotidien/hebdo/cloche_seule).
    r = envoyer_digests(ctx.db, base_url=base, dry_run=ctx.dry_run)
    ctx.compte(**{k: r.get(k) for k in ("envoyes", "ignores", "echecs", "simules")})


def _sauvegarde_en_cours(nom: str = "backup-postgres") -> bool:
    """COCKPIT-1 (Lot C, correction A) — la SAUVEGARDE (pg_dump) tient-elle son verrou en ce moment ?
    On inspecte le MÊME verrou que pose le wrapper run-job.sh pour `backup-postgres` :
      · Linux (prod) : verrou flock sur `<LOCK_DIR>/labuse-job-backup-postgres.lock` — si on ne peut PAS
        le prendre en non bloquant, c'est qu'il est tenu (le dump tourne) ;
      · macOS (dev) : repli mkdir → le dossier `…​.lock.d` existe tant que le dump tourne.
    Jamais bloquant, jamais une exception qui remonte : en cas de doute on répond False (on envoie)."""
    lock_dir = os.environ.get("LABUSE_LOCK_DIR", "/run/lock")
    base = os.path.join(lock_dir, f"labuse-job-{nom}.lock")
    if os.path.isdir(base + ".d"):           # repli mkdir (macOS) : dossier présent = verrou tenu
        return True
    try:
        import fcntl
        fd = os.open(base, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return False                         # pas de LOCK_DIR accessible → on n'empêche pas l'envoi
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)       # libre : on a pu le prendre → le dump ne tourne pas
        return False
    except OSError:
        return True                          # verrou tenu → le dump tourne
    finally:
        os.close(fd)


def mail_queue_consommer(ctx: JobContext) -> None:
    """VEILLE-FIX-2 (Lot D) — LE CONSOMMATEUR DE LA FILE (cron 5 min). Envoie les mails `en_attente` dûs
    (digest différé, programmés J+3/J+10) et rejoue les `a_rejouer` dont l'heure est venue. En dry-run
    (SMTP absent) : ne fait rien partir (les tentatives échoueraient → on n'appelle pas le worker).

    COCKPIT-1 (Lot C, correction A) — CÈDE À LA SAUVEGARDE : s'il démarre pendant le pg_dump (verrou
    de backup-postgres tenu), il SAUTE ce passage proprement (statut ok, ni échec ni alerte) et repart
    5 min plus tard, hors de la fenêtre du dump — fin de la fausse alerte quotidienne de 13:35, sans
    jamais ralentir les mails clients (mot de passe, confirmation, invitation)."""
    from .mailfile import consommer, ensure_tables
    from .db import engine
    if _sauvegarde_en_cours():
        ctx.compte(traites=0, saute="sauvegarde en cours — passage cédé, reprise dans 5 min")
        return
    ensure_tables(engine())
    if ctx.dry_run:
        ctx.compte(traites=0, note="dry-run (SMTP absent) — worker non lancé")
        return
    r = consommer(engine())
    ctx.compte(**r)


def copilote_purge(ctx: JobContext) -> None:
    """RETOURS-8 (R11) — purge quotidienne des conversations Copilote au-delà de la rétention (réglage
    admin `copilote_retention_jours`, défaut 7 j). Les messages tombent par CASCADE. Compte-rendu :
    rétention appliquée, conversations purgées, et le POIDS restant (nb, Mo, croissance/jour)."""
    from . import reglages
    from .copilote_v2 import historique
    jours = reglages.copilote_retention_jours()
    purgees = historique.purger(ctx.db, jours)
    ctx.db.commit()
    poids = historique.mesure(ctx.db)
    ctx.compte(retention_jours=jours, conversations_purgees=purgees,
               conversations=poids["conversations"], messages=poids["messages"],
               mo=poids["mo"], croissance_jour=poids["croissance_jour"])


def healthcheck(ctx: JobContext) -> None:
    """Dead-man LOCAL toutes les 15 min — la sonde rapide. Vérifie le process (/health), la disponibilité
    réelle (/readyz) et l'espace disque. SOLIDITE-1 (Lot 1.2) : DISQUE et /readyz passent par la PORTE
    D'ALERTE UNIQUE (ops_alertes — un incident par panne, un rappel/jour, un « résolu » au retour), au lieu
    de l'ancienne alerte mail « une fois par jour » faite ici. /health à DEUX échecs consécutifs (dampe un
    faux positif au redémarrage) : au-delà, le job LÈVE → le runner ouvre l'incident `job-echec:healthcheck`."""
    import urllib.request
    s = get_settings()
    port = os.environ.get("LABUSE_HEALTH_PORT", "8000")
    # ORF-02 — le compteur d'échecs vient de l'état PRÉCÉDENT transmis par le runner (ctx.precedent) :
    # relire son propre fichier d'état ici lisait « en_cours, compteurs {} » que le runner venait
    # d'écrire → echecs valait toujours 0 → l'alerte « 2 échecs consécutifs » ne partait jamais.
    echecs = ((ctx.precedent or {}).get("compteurs") or {}).get("echecs_consecutifs", 0)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as resp:
            ok = resp.status == 200
    except Exception:  # noqa: BLE001
        ok = False
    echecs = 0 if ok else echecs + 1
    # disque — chemin ACCESSIBLE (le backup_dir peut ne pas exister/être lisible en dev) ; jamais bloquant.
    chemin = s.backup_dir if os.access(s.backup_dir, os.R_OK) else "."
    try:
        usage = shutil.disk_usage(chemin)
        pct = round(100 * usage.used / usage.total, 1)
    except OSError:
        pct = None
    from . import ops_alertes
    ready, motif = ops_alertes._readyz_local()
    # ORF-02 — on DÉCIDE d'abord quoi signaler/résoudre, puis on écrit par la porte unique. Si la base
    # est indisponible (ex. : verrouillée pendant le pg_dump — précisément quand le disque franchit le
    # seuil), chaque alerte décidée part en REPLI local (fichier + journald) : la sonde n'est plus
    # aveugle au moment exact où elle sonne.
    a_signaler: list[tuple[str, str, str]] = []
    a_resoudre: list[str] = []
    if pct is not None and pct >= s.disque_seuil_pct:
        a_signaler.append(("disque", f"Disque à {pct}% (seuil {s.disque_seuil_pct}%)",
                           f"Le disque du serveur est à {pct}% (seuil {s.disque_seuil_pct}%). "
                           "Faire de la place (cf. inventaire SOLIDITE-1 Lot 3)."))
    elif pct is not None:
        a_resoudre.append("disque")
    if not ready:
        a_signaler.append(("readyz", "/readyz répond « pas prêt »",
                           f"La sonde /readyz locale dit le service NON prêt : {motif}."))
    else:
        a_resoudre.append("readyz")
    vigies: dict = {}
    try:
        from .db import session_scope
        with session_scope() as db:
            for cle, sujet, detail in a_signaler:
                ops_alertes.signaler(db, cle, sujet, detail)
            for cle in a_resoudre:
                ops_alertes.resoudre(db, cle)
            # COCKPIT-1 (Lot C, correction D) — recap-matin SUPPRIMÉ : ce sont désormais ces 15 min qui
            # évaluent les vigies sans point d'appel naturel (sauvegarde absente/rétrécie, copie externe
            # ancienne, jobs en retard — disque/readyz déjà traités ci-dessus, re-signalés à l'identique,
            # idempotent). « Les ALERTES restent » : chaque incident part par la porte unique ops_alertes,
            # SANS mail récap. Jamais bloquant (une vigie qui rate ne casse pas la sonde /health).
            try:
                vigies = ops_alertes.verifier_declencheurs(db)
            except Exception as exc_v:  # noqa: BLE001
                log.error("healthcheck : vigies (ex recap-matin) impossibles (%s)", exc_v)
            db.commit()
    except Exception as exc:  # noqa: BLE001 — l'alerte qui rate ne casse pas la sonde… mais elle EXISTE
        log.error("healthcheck : alerte ops impossible (%s)", exc)
        for cle, sujet, detail in a_signaler:
            ops_alertes.repli_local(cle, sujet, detail, erreur=f"{type(exc).__name__}: {exc}")
    ctx.compte(health_ok=ok, readyz_ok=ready, readyz_motif=motif,
               echecs_consecutifs=echecs, disque_pct=pct,
               sauvegarde=(vigies.get("sauvegarde") or {}).get("dernier"),
               jobs_en_retard=len(vigies.get("retards") or []))
    if not ok and echecs >= 2:
        raise RuntimeError(f"/health injoignable ({echecs} échec(s) consécutif(s))")


# COCKPIT-1 (Lot C, correction D) — `recap_matin` RETIRÉ : le mail récap de 07:30 est supprimé (Vic
# ne le veut plus). Les vigies qu'il évaluait (disque, /readyz, sauvegarde, copie externe, jobs en
# retard) sont désormais évaluées par `healthcheck` (toutes les 15 min) via
# `ops_alertes.verifier_declencheurs` → chaque incident part par la porte unique (mail Brevo + cloche),
# SANS mail récap. « Les ALERTES restent ». Le site en panne reste couvert par /health (healthcheck).


def sante_endpoints(ctx: JobContext) -> None:
    """CONNEXIONS-2 Lot 7.2 (N3) — sonde les endpoints MÉTIER (avec DB) et vérifie forme + non-vacuité.
    À la PREMIÈRE panne (dédup jour), notifie l'admin (event systeme). Le dashboard lit le même résultat
    via /admin/sante-endpoints. Ne teste PAS que le process vit (ça, c'est `healthcheck`) — teste que les
    ÉCRANS ont de quoi s'afficher (le cas `/accueil/chiffres` vivant mais vide).

    DONNEES-ETAT-FIX-1 (Lot C) — CÈDE À LA SAUVEGARDE, comme `mail-queue` (COCKPIT-1 corr. A) : s'il
    démarre pendant le pg_dump (verrou de backup-postgres tenu), ses requêtes rament sous la charge du
    dump, dépassent le timeout du job (SIGALRM en plein échange psycopg → « another command is already
    in progress ») et ouvrent un faux incident quotidien à 13:37 (journaux prod 14→27/10). On saute
    proprement ce passage (statut ok, ni échec ni alerte) et on repart au prochain créneau, hors de la
    fenêtre du dump. La sonde /health (`healthcheck`), elle, continue — ce n'est que la sonde MÉTIER lourde
    (requêtes DB) qui cède."""
    if _sauvegarde_en_cours():
        ctx.compte(ok=True, total=0, en_echec=None,
                   saute="sauvegarde en cours — passage cédé, reprise au prochain créneau")
        return
    from .api import sante
    res = sante.sonde_metier(ctx.db)
    en_echec = [e["endpoint"] for e in res["endpoints"] if not e["ok"]]
    ctx.compte(ok=res["ok"], total=len(res["endpoints"]), en_echec=en_echec or None)
    if not res["ok"]:
        from .api.events import creer_notification
        detail = " · ".join(f"{e['endpoint']} : {e['detail']}"
                            for e in res["endpoints"] if not e["ok"])
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Sonde endpoints",
            titre=f"Endpoints métier en échec ({len(en_echec)})", detail=detail[:500],
            dedup=f"sante_endpoints:{today_reunion().isoformat()}")
        ctx.db.commit()
        raise RuntimeError(f"sonde endpoints : {len(en_echec)} en échec ({', '.join(en_echec)})")


def radar_releves(ctx: JobContext) -> None:
    """FLUX-1 (F3.2) — RELEVÉ QUOTIDIEN des compteurs Radar (fin de journée) : écrit la photo cumulée
    du jour dans `radar_releves` (annonces, rattachées, paires annonce↔DVF, communes, types). La courbe
    dans le temps se lit de cette table — elle commence au jour du déploiement, aucune reconstruction."""
    from .pige.releves import ecrire_releve
    r = ecrire_releve(ctx.db)
    ctx.compte(**r)


def coherence_run(ctx: JobContext) -> None:
    """FLUX-1 (F4) — GARDE DE COHÉRENCE quotidienne : pour chaque surface, le run lu est-il le run
    courant, et tier / date de valeur identiques partout (parcelles témoins) ? Réutilise la sonde de
    santé (CONNEXIONS-2 lot 7.2). Une divergence notifie l'admin (event systeme, dédup jour). Le
    résultat est lu par la page Flux et la tuile Santé."""
    from .coherence_flux import verifier
    res = verifier(ctx.db)
    en_echec = [c["libelle"] for c in res["checks"] if not c["ok"]]
    ctx.compte(ok=res["ok"], run=res["run"], n_surfaces=res["n_surfaces"], en_echec=en_echec or None)
    if not res["ok"]:
        from .api.events import creer_notification
        detail = " · ".join(f"{c['libelle']} : {c['detail']}" for c in res["checks"] if not c["ok"])
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Cohérence run",
            titre=f"Garde de cohérence : {len(en_echec)} divergence(s)", detail=detail[:500],
            lien="/admin", dedup=f"coherence_run:{today_reunion().isoformat()}")
        ctx.db.commit()
        raise RuntimeError(f"garde de cohérence : {len(en_echec)} divergence(s) ({', '.join(en_echec)})")


# ═══════════════════════════ K4 — hebdo & mensuels ═══════════════════════════

#: ORF-03 — module-niveau (testable) : les tables chaudes à VACUUM ANALYZE chaque dimanche.
TABLES_CHAUDES = ["parcels", "event_log", "pige_biens", "pige_faits", "veilles", "dvf_mutations"]


def pg_maintenance(ctx: JobContext) -> None:
    """VACUUM ANALYZE des tables chaudes (hors transaction — connexion autocommit dédiée).

    ORF-03 (FIX-ORFEVRE-1) — deux racines corrigées (le VACUUM hebdo n'avait JAMAIS fonctionné, job vert) :
    1. `raw.autocommit = True` posait un attribut FANTÔME sur le proxy de pool SQLAlchemy
       (PoolProxiedConnection) — no-op : psycopg restait en transaction → « VACUUM cannot run inside a
       transaction block » chaque dimanche. L'autocommit se pose sur la VRAIE connexion psycopg via
       `raw.driver_connection` (même porte que scoring/score_v.py:585 pour son COPY).
    2. L'`except` par table avalait TOUT → `fin (code 0)` mensonger. Seule une table ABSENTE est
       tolérée (UndefinedTable) ; tout autre échec remonte → job ROUGE. Et zéro table vacuumée = ROUGE
       aussi (jamais de vert par vacuité)."""
    from psycopg.errors import UndefinedTable

    from .db import engine
    faites, absentes = [], []
    raw = engine().raw_connection()
    try:
        dbapi = raw.driver_connection                   # la connexion psycopg réelle, pas le proxy
        autocommit_avant = dbapi.autocommit
        dbapi.autocommit = True                         # VACUUM est interdit dans une transaction
        try:
            with dbapi.cursor() as cur:
                for t in TABLES_CHAUDES:
                    try:
                        cur.execute(f"VACUUM ANALYZE {t}")
                        faites.append(t)
                    except UndefinedTable:              # une table absente ne casse pas la maintenance
                        absentes.append(t)
                        log.warning("VACUUM %s ignoré : table absente", t)
        finally:
            dbapi.autocommit = autocommit_avant         # la connexion retourne PROPRE au pool
    finally:
        raw.close()
    ctx.compte(tables=faites, absentes=absentes or None)
    if not faites:
        raise RuntimeError(
            f"pg-maintenance : AUCUNE table vacuumée (absentes : {', '.join(absentes) or '—'}) "
            "— un vert ici serait un vert par vacuité")


def purge_runs(ctx: JobContext) -> None:
    """MENAGE-1 (geste 10) — PURGE DES VIEUX RUNS DE SCORING pour que la base n'empile plus q_v11→q_v20
    (la cause des 12–16 Go de `dryrun_cascade_results`, cf. rapport MENAGE-1 A1.1/A2). Garde le SERVI +
    les 2 PRÉCÉDENTS (par récence, `score_labuse_runs.computed_at`) + tout run RÉFÉRENCÉ (lignée /
    exceptions de service / démo) + les runs ÉPINGLÉS (`residuel_runs.is_pinned`). Supprime le reste de
    façon ATOMIQUE sur toutes les tables run-scopées TEXTE (labels `q_*`) puis VACUUM ANALYZE — JAMAIS
    `FULL` : pas de verrou exclusif, sûr sur la prod vivante (la place est réutilisée en interne,
    l'empilement cesse ; le gain-disque-vers-l'OS reste un geste de bascule/nuit). Respecte le dry-run.

    Ne touche PAS les tables keyées par `run_seq` entier (`parcel_residuel_runs`) : celles-là sont
    purgées à la bascule (`residuel_runs.purge_run`). Le gros du volume (dryrun_cascade_results,
    score_labuse, parcel_p_score_v2) est keyé par label → couvert ici.

    GELÉ au registre par défaut (geste destructeur) : la rétention historique vivait À LA BASCULE
    (`labuse purge-runs-morts`, délibérément « jamais un cron »). Dégel = décommenter la ligne du
    crontab généré, quand Vic valide l'automatisation."""
    from . import db, runs

    purgeables: list[str] = []
    touched: list[str] = []
    with db.session_scope() as s:
        # 1) tables run-scopées TEXTE (labels q_*) — même périmètre que `purge-runs-morts`.
        tables = [(r[0], r[1]) for r in s.execute(text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND column_name IN ('run_id','run_label') "
            "AND data_type IN ('character varying','text','character') ORDER BY table_name")).all()]

        # 2) keep = servi + 2 précédents (récence) + référencés + épinglés (+ cascades/_sources).
        servi = runs.current()
        try:
            from .scoring.score_v_constants import RUN_PRECEDENT
        except Exception:  # noqa: BLE001
            RUN_PRECEDENT = servi
        recents = [r[0] for r in s.execute(text(
            "SELECT run_label FROM score_labuse_runs ORDER BY computed_at DESC NULLS LAST")).all() if r[0]]
        keep = set(recents[:3])                         # servi + 2 précédents par récence
        keep |= {servi, RUN_PRECEDENT, "q_v2_demo"}
        try:                                            # lignée (lignee_tete lit leur donnée)
            from .scoring.lignee_tete import CHAINE_GESTES
            for a, b, *_ in CHAINE_GESTES:
                keep.update({a, b})
        except Exception:  # noqa: BLE001 — la lignée ne doit jamais faire échouer la purge
            log.warning("purge-runs : lignée indisponible, keep = servi + 2 précédents", exc_info=True)
        keep.update(r[0] for r in s.execute(text(       # exceptions de service encore posées
            "SELECT DISTINCT run_id FROM served_run_exceptions")).all() if r[0])
        for lbl, casc in s.execute(text(                # cascade des gardés (dryrun_cascade_results)
                "SELECT run_label, cascade_label FROM score_labuse_runs")).all():
            if lbl in keep and casc:
                keep.add(casc)
        keep.update({f"{k}_sources" for k in list(keep)})   # défensif : garde aussi le *_sources
        keep.update(r[0] for r in s.execute(text(           # runs ÉPINGLÉS (label)
            "SELECT label FROM residuel_runs WHERE is_pinned")).all() if r[0])

        # 3) présents - keep = purgeables.
        present: set[str] = set()
        for t, c in tables:
            present.update(r[0] for r in s.execute(text(f"SELECT DISTINCT {c} FROM {t}")).all() if r[0])
        purgeables = sorted(present - keep)
        ctx.compte(servi=servi, garde=sorted(keep & present), purgeables=purgeables)
        if not purgeables:
            ctx.compte(purges=0, tables_touchees=[])
            return
        if ctx.dry_run:
            ctx.compte(purges=len(purgeables), note="dry-run — rien supprimé")
            return

        # 4) purge ATOMIQUE (toutes les tables run-scoped dans une transaction).
        for t, c in tables:
            n = s.execute(text(f"DELETE FROM {t} WHERE {c} = ANY(:r)"), {"r": purgeables}).rowcount
            if n:
                touched.append(t)
        from . import circuit_journal
        circuit_journal.journaliser(s, "purger", ",".join(purgeables), "cron", "ok",
                                    {"tables": sorted(set(touched))})
        s.commit()

    # 5) VACUUM ANALYZE (plain, autocommit) sur les tables touchées — PAS de verrou exclusif.
    if touched:
        from .db import engine
        raw = engine().raw_connection()
        try:
            dbapi = raw.driver_connection
            av = dbapi.autocommit
            dbapi.autocommit = True
            try:
                with dbapi.cursor() as cur:
                    for t in sorted(set(touched)):
                        cur.execute(f"VACUUM (ANALYZE) {t}")
            finally:
                dbapi.autocommit = av
        finally:
            raw.close()
    ctx.compte(purges=len(purgeables), tables_touchees=sorted(set(touched)))


def rapport_admin(ctx: JobContext) -> None:
    """Un mail hebdo : disque, 5 plus grosses tables, statut de chaque job sur 7 j, sources en retard,
    veilles actives, dépôts traités, digests envoyés, date du dernier restore-test réussi."""
    db = ctx.db
    s = get_settings()
    chemin_disque = s.backup_dir if os.access(s.backup_dir, os.R_OK) else "."
    usage = shutil.disk_usage(chemin_disque)
    disque = f"{round(100*usage.used/usage.total,1)}% ({round(usage.free/1e9,1)} Go libres)"
    # CRON-2 — taille du dernier dump (un dump qui rétrécit = signal ; absent = backup jamais passé).
    dumps = sorted(Path(s.backup_dir).glob("labuse-*.sql.gz"), key=lambda f: f.stat().st_mtime,
                   reverse=True) if Path(s.backup_dir).exists() else []
    dernier_dump = (f"{dumps[0].name} · {round(dumps[0].stat().st_size/1e6,1)} Mo" if dumps
                    else "aucun dump présent")
    tables = db.execute(text(
        "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) taille "
        "FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 5")).all()
    from .jobs import JOBS
    lignes_jobs = []
    for nom in JOBS:
        e = lire_etat(nom) or {}
        lignes_jobs.append(f"  {nom:28s} {e.get('statut','—'):9s} {e.get('fin','jamais')}")
    retard = db.execute(text("SELECT count(*) FROM data_sources WHERE fraicheur_statut IN "
                             "('en_retard','en_panne')")).scalar() or 0
    veilles = db.execute(text("SELECT count(*) FROM veilles WHERE actif")).scalar() or 0
    rt = lire_etat("restore-test") or {}
    corps = (
        "RAPPORT HEBDOMADAIRE D'EXPLOITATION — LABUSE\n\n"
        f"Disque : {disque}\n"
        f"Dernier dump : {dernier_dump}\n\n"
        "5 plus grosses tables :\n" + "".join(f"  {r[0]:32s} {r[1]}\n" for r in tables) + "\n"
        "Jobs (dernier passage) :\n" + "\n".join(lignes_jobs) + "\n\n"
        f"Sources en retard/panne : {retard}\n"
        f"Veilles actives : {veilles}\n"
        f"Dernier restore-test : {rt.get('statut','jamais')} le {rt.get('fin','—')}\n\n"
        "— LABUSE, exploitation planifiée")
    _envoyer_alerte(corps, sujet="[LABUSE] rapport hebdomadaire d'exploitation", ctx=ctx)
    ctx.compte(sources_en_retard=retard, veilles_actives=veilles, dernier_dump=dernier_dump)


#: ORF-10 — marge (s) entre la mort du sous-process et le SIGALRM du job : le kill et l'écriture de
#: l'état doivent tenir dedans.
_SOUS_PROCESS_MARGE_S = 60


class SousProcessTimeout(RuntimeError):
    """ORF-10 — le sous-process a dépassé son budget : son GROUPE a été tué (aucun orphelin)."""

    def __init__(self, message: str, pid: int):
        super().__init__(message)
        self.pid = pid


def _run_sous_process_borne(cmd: list[str], budget_s: float) -> subprocess.CompletedProcess:
    """ORF-10 (FIX-ORFEVRE-1) — lance `cmd` dans SON PROPRE groupe de process, borné à `budget_s`.
    Au-delà (ou sur toute interruption, SIGALRM du job compris) : kill du GROUPE entier (SIGKILL) puis
    récolte — plus jamais d'enfant qui survit au « timeout » du job et continue de committer en base
    (le piège SCORING-6 : relance manuelle = deux ingestions concurrentes sur la même table)."""
    import signal as _signal

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            cwd=os.getcwd(), start_new_session=True)

    def _tuer_groupe() -> None:
        try:
            os.killpg(proc.pid, _signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()

    try:
        out, err = proc.communicate(timeout=budget_s)
    except subprocess.TimeoutExpired:
        _tuer_groupe()
        out, err = proc.communicate()        # récolte (jamais de zombie)
        raise SousProcessTimeout(
            f"sous-process tué après {round(budget_s)} s (budget du job) — groupe de process arrêté, "
            f"aucune ingestion orpheline. Dernière sortie : {(err or out or '')[-300:]}", proc.pid)
    except BaseException:                    # _Timeout du job (SIGALRM), KeyboardInterrupt… même geste
        _tuer_groupe()
        proc.communicate()
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def _ingest_via_cli(ctx: JobContext, *args: str) -> None:
    """Lance une commande d'ingestion EXISTANTE (même venv), capture le résultat. Les ingestions lourdes
    (données externes) restent le pipeline existant — le job n'ajoute que l'ordonnancement + l'état.
    ORF-10 — borné SOUS le timeout du job (marge) + kill du groupe : le « timeout » d'un job tue
    VRAIMENT l'ingestion (statut d'échec propre, compteurs posés), au lieu de la laisser orpheline."""
    import sys
    cmd = [sys.executable, "-m", "labuse.cli", *args]
    budget = max(60.0, float(getattr(ctx, "timeout_s", 900) or 900) - _SOUS_PROCESS_MARGE_S)
    try:
        proc = _run_sous_process_borne(cmd, budget)
    except SousProcessTimeout as exc:
        ctx.compte(commande=" ".join(args), code="timeout-tue", budget_s=round(budget),
                   sortie=str(exc)[-400:])
        raise RuntimeError(f"{' '.join(args)} : {exc}") from exc
    ctx.compte(commande=" ".join(args), code=proc.returncode,
               sortie=(proc.stdout or proc.stderr)[-400:])
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} a échoué (code {proc.returncode}) : {proc.stderr[-300:]}")


def ingest_sirene(ctx: JobContext) -> None:
    """SIRENE mensuel (câblage OUTILS-2/4 : date_creation + date_dernier_traitement, refresh concurrents).
    KELFONCIER-FIX-1 (Lot H) — PUIS reconstruit le rattachement établissement→parcelle par l'adresse BAN
    (`etablissement_parcelle`), au registre CRON UNIQUE (pas de nouveau cron : le rattachement dépend du
    refresh SIRENE, il en est la suite naturelle)."""
    _ingest_via_cli(ctx, "ingest-sirene-etab")
    from .ingestion.etablissement_parcelle import build_etablissement_parcelle
    r = build_etablissement_parcelle(ctx.db)
    log.info("etablissement_parcelle reconstruit : %s rattachés / %s (adresse) — %s non rattachés",
             r["rattaches"], r["n_etab_adresse"], r["non_rattaches"])


def ingest_sitadel(ctx: JobContext) -> None:
    """Permis SITADEL mensuel, PUIS événements de veille foncière (comparaison aux critères clients) +
    calcul d'un golden CANDIDAT (jamais servi — bascule = geste de Vic, cf. K5)."""
    _ingest_via_cli(ctx, "ingest-permits")
    from .copilote_v2 import veilles as veilles_mod
    r = veilles_mod.evaluer_toutes(ctx.db)
    ctx.compte(veille_fonciere=r)
    # CRON-2 (K5) — en fin d'ingestion réussie : run candidat + rapport mail de comparaison (dry-run
    # aware). La bascule reste manuelle (`labuse golden promote`). Ne touche JAMAIS le run servi.
    from . import golden_ops
    ctx.compte(candidat=golden_ops.rapport_candidat(dry_run=ctx.dry_run))
    _persist_millesime(ctx, "sitadel")   # E3


def _persist_millesime(ctx: JobContext, key: str) -> None:
    """CORRECTIFS-1 E3 — branche le magasin UNIQUE des millésimes (data_sources.source_millesime,
    via `persist_millesime`) à la fin d'une ingestion. Best-effort : ne fait jamais échouer le job."""
    try:
        from .ingestion.fraicheur import persist_millesime
        persist_millesime(ctx.db, only=key)
    except Exception as exc:  # noqa: BLE001
        log.warning("persist_millesime(%s) a échoué (non bloquant) : %s", key, exc)


def ingest_dpe(ctx: JobContext) -> None:
    """DPE ADEME mensuel."""
    _ingest_via_cli(ctx, "ingest-dpe")
    _persist_millesime(ctx, "dpe")   # E3 — millésime vivant à la fin de l'ingestion


def ingest_bdnb(ctx: JobContext) -> None:
    """SCORING-3 (L3) — BDNB trimestriel : stream de l'export national (~39 Go), filtre 974,
    tables bdnb_* + couverture parcelle mesurée. Idempotent par millésime (skip si déjà ingéré).
    N'inscrit AUCUNE variable au modèle : les candidates passent au banc K0 d'abord (L3.2)."""
    _ingest_via_cli(ctx, "ingest-bdnb")


# ── CORRECTIFS-1 E5 — jobs manquants du registre (ban / dvf / abuse / sessions). Chaque impl
#    délègue à la commande CLI EXISTANTE (même patron que les autres ingestions) ; le crontab
#    n'est PAS posé ici (geste Vic via `labuse jobs crontab`). ──
def ingest_ban(ctx: JobContext) -> None:
    """Adresses BAN 974 (géocodage interne), refresh MENSUEL."""
    _ingest_via_cli(ctx, "ingest-ban")
    _persist_millesime(ctx, "ban")   # E3


def ingest_dvf(ctx: JobContext) -> None:
    """DVF — détecte une nouvelle livraison Etalab (Last-Modified) et recharge. Hebdomadaire."""
    _ingest_via_cli(ctx, "refresh-dvf")


def abuse_scan(ctx: JobContext) -> None:
    """Détection d'abus (usage anormal / partage de compte), quotidienne."""
    _ingest_via_cli(ctx, "abuse-scan")


def purge_sessions(ctx: JobContext) -> None:
    """Supprime les sessions d'authentification EXPIRÉES (minimisation), quotidienne."""
    _ingest_via_cli(ctx, "purge-sessions")


def sync_gpu(ctx: JobContext) -> None:
    """Diff des PLU des 24 communes ; génère les événements de veille foncière concernés + bandeau PLU."""
    from .copilote_v2 import veilles as veilles_mod
    r = veilles_mod.evaluer_toutes(ctx.db)
    ctx.compte(veille_fonciere=r, note="diff PLU délégué au pipeline GPU existant ; événements générés")


def sentinelle_sources(ctx: JobContext) -> None:
    """SENTINELLE-1/2 (W3/X5) — UN passage quotidien de la veille des sources : parcourt les lignes
    `source_veille` actives dont la cadence est échue, sonde l'amont (api/page/entete) SÉQUENTIELLEMENT
    avec un délai, écrit le résultat DANS source_veille (JAMAIS dans data_sources), et dépose AU PLUS UNE
    notification — le RÉSUMÉ du jour (X5.1) : « N sources ont une nouvelle version », dépliable, dédup par
    (source, millésime) via `dernier_notifie_vu`. Une sonde en échec n'alerte qu'après 3 passages ratés
    d'affilée (X5.2). Généralise l'ancien `sentinelle-dvf-cadastre`. Surveille et prévient — n'ingère rien."""
    from . import sentinelle
    recap = sentinelle.passer(ctx.db, notifier=True)
    # SENTINELLE-3 (Y4) — même passage : rappel de rafraîchissement des sources MANUELLES (PAS une sonde
    # amont — aucun appel réseau ; « donnée manuelle non rafraîchie depuis N jours », une fois par dépassement).
    rap = sentinelle.passer_rappels(ctx.db, notifier=True)
    ctx.compte(sondees=recap["sondees"], nouvelles=recap["nouvelles"],
               injoignables=recap["injoignables"], illisibles=recap["illisibles"],
               notifs=recap["notifs"] + rap["notifs"],
               rappels=rap["rappels"], rappels_en_retard=rap["retards"], details=recap["details"])


def sonde_sources(ctx: JobContext) -> None:
    """CRON-1 lot 1 — le job s'appelle désormais `sonde-sources` (la SONDE mécanique). Même passage que
    l'ancien `sentinelle-sources` : parcourt les lignes source_veille échues, sonde l'amont, alerte,
    n'ingère rien. Alias conservé pour ne pas dupliquer la logique."""
    sentinelle_sources(ctx)


def _cout_agent_source_eur(db) -> float:
    """Coût cumulé (EUR) des appels `agent_source` au ledger ia_log — pour le plafond du passage.

    DONNEES-ETAT-FIX-1 (Lot B) — on NE garde JAMAIS `ia_log` verrouillé après ce SELECT. La session
    du job (`ctx.db`) reste « idle in transaction » après une lecture non validée et tient un
    AccessShareLock sur `ia_log` ; or chaque passage de `_log_cost` (ai/core) fait un
    `ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS …` qui prend un ACCESS EXCLUSIVE (même en no-op) depuis
    la session PAR SOURCE → cycle de verrous applicatif que Postgres ne tranche pas → le passage réel du
    28/10 a pataugé 11 min puis échoué en `PendingRollbackError` (0 source traitée utilement). On relâche
    donc la transaction juste après la lecture : le plafond se mesure toujours, mais plus aucun verrou
    n'est tenu pendant l'appel API de l'agent."""
    from sqlalchemy import text
    try:
        v = db.execute(text("SELECT COALESCE(SUM(cout_eur), 0) FROM ia_log WHERE kind = 'agent_source'")).scalar()
        return float(v or 0.0)
    except Exception:  # noqa: BLE001 — pas de ledger → pas de plafond mesurable, on ne bloque pas
        return 0.0
    finally:
        try:
            db.rollback()          # lecture seule : rien à perdre, et on libère le verrou ia_log
        except Exception:  # noqa: BLE001 — libérer le verrou ne doit jamais masquer le résultat
            pass


def agents_sources(ctx: JobContext) -> None:
    """CRON-1 lot 1 / CIRCUIT-P7 — LE DÉTECTIVE : `agent_source` sur les sources SANS amont lisible
    (celles que la sonde de nuit ne peut pas lire — `circuit_garanties.sources_sans_amont`), 5 en
    parallèle, SOUS PLAFOND de dépense par passage (env `LABUSE_AGENT_PLAFOND_EUR`, défaut 0 = ne
    dépense RIEN). Cadence : UNE SEMAINE SUR DEUX (semaines ISO paires) — les sources à amont lisible
    restent sur la sonde quotidienne. Coût cumulé sondé au ledger entre chaque source ; au plafond, on
    ARRÊTE et on signale les non traitées. Un résultat sans URL réellement consultée est rejeté."""
    import os
    from datetime import datetime, timezone
    from . import agent_source, circuit_garanties as _g
    from .db import session_scope
    from .jobs import semaine_agents

    # CIRCUIT-P7 — une semaine sur deux : les semaines ISO impaires, le passage est sauté (cadence 15 j).
    if not semaine_agents(datetime.now(timezone.utc).date()):
        ctx.compte(traites=0, non_traites=0, note="semaine « off » — cadence 15 jours, passage sauté")
        return

    plafond = 0.0
    try:
        plafond = float(os.environ.get("LABUSE_AGENT_PLAFOND_EUR", "0") or 0)
    except ValueError:
        plafond = 0.0
    if plafond <= 0:
        ctx.compte(traites=0, non_traites=0, plafond_eur=0.0,
                   note="LABUSE_AGENT_PLAFOND_EUR non fixé (0) — passage sauté, aucune dépense")
        return

    ids = [x["id"] for x in _g.sources_sans_amont(ctx.db)]   # la portée : sources sans amont lisible
    depart = _cout_agent_source_eur(ctx.db)
    traites, neuf, rejetes, non_traites = 0, 0, 0, list(ids)
    for i, sid in enumerate(ids):
        if _cout_agent_source_eur(ctx.db) - depart >= plafond:
            non_traites = ids[i:]
            break
        try:
            out = agent_source.lancer_agents(session_scope, [sid])
            traites += 1
            for r in out or []:
                if r.get("verdict") in ("nouvelle_version", "nouveau", "vu_neuf"):
                    neuf += 1
                if r.get("rejete") or r.get("url_consultee") in (None, ""):
                    rejetes += 1
        except Exception:  # noqa: BLE001 — un agent qui échoue n'arrête pas le passage
            rejetes += 1
        else:
            non_traites = ids[i + 1:]
    depense = round(_cout_agent_source_eur(ctx.db) - depart, 4)
    ctx.compte(traites=traites, neuf=neuf, rejetes=rejetes, non_traites=len(non_traites),
               plafond_eur=plafond, depense_eur=depense)


def sentinelle_dvf_cadastre(ctx: JobContext) -> None:
    """SUPERSÉDÉ par `sentinelle_sources` (SENTINELLE-1 W2) — conservé pour le test de NON-RÉGRESSION :
    l'ancienne heuristique DATE (prochain_millesime_at échu) est comparée au nouveau passage réel.
    N'est plus enregistré au registre des jobs ; ne tourne plus en production."""
    db = ctx.db
    alertes = []
    for nom in ("DVF", "cadastre"):
        # SOURCES-1 lot 4 : « DVF Réunion (Région…) » matche aussi %DVF% — l'heuristique
        # historique visait LA ligne à échéance datée ; on préfère une ligne portant
        # prochain_millesime_at (comportement d'origine conservé, job supersédé/test-only).
        r = db.execute(text("SELECT source_millesime, prochain_millesime_at FROM data_sources "
                            "WHERE name ILIKE :n "
                            "ORDER BY (prochain_millesime_at IS NULL), updated_at DESC LIMIT 1"),
                       {"n": f"%{nom}%"}).mappings().first()
        # prochain_millesime_at est un DATE : comparer à une DATE (l'ancien code comparait à un datetime
        # → TypeError latent dès qu'une source portait cette date ; corrigé ici, la reprise le rend sain).
        if r and r["prochain_millesime_at"] and r["prochain_millesime_at"] <= datetime.now(timezone.utc).date():
            alertes.append(f"{nom} : un millésime postérieur à {r['source_millesime']} devrait être paru.")
    if alertes:
        _envoyer_alerte("Sentinelle DVF/cadastre :\n- " + "\n- ".join(alertes)
                        + "\n\nGeste supervisé : Vic déclenche l'ingestion.", ctx=ctx)
    ctx.compte(alertes=alertes, n_alertes=len(alertes))


# ═══════════════════════════ K9 — robustesse ═══════════════════════════

def verite_sources(ctx: JobContext) -> None:
    """SOLIDITE-1 (Lot 5) — confronte 20 parcelles tirées au hasard (stratifiées) aux sources officielles
    en ligne, journalise le rapport (verite_sources_runs) et ouvre un incident agrégé par écart servi↔source.
    Échantillon vide (base/API injoignables) → note, pas d'échec (le passage suivant réessaiera)."""
    from . import verite_sources as vs
    res = vs.jouer(n=20)
    r = vs.journaliser_passage(ctx.db, res)
    ctx.db.commit()
    ctx.compte(**r, parcelles_echantillon=len(res.get("echantillon") or []))


def restore_test(ctx: JobContext) -> None:
    """SOLIDITE-1 (Lot 3.3) — sur le VPS, on ne restaure PLUS un dump complet (45 Go) : il n'y a pas la
    place (6,6 Go libres) et ce serait dangereux. Ce job vérifie seulement que le dernier dump est
    RESTAURABLE sans le restaurer (`pg_restore --list` lit la table des matières : un dump tronqué/corrompu
    est pris ici), et contrôle sa taille. Le VRAI test de restauration (restauration réelle + comparaison
    des comptages) tourne sur le MAC, une fois par mois : deploy/mac/restore_test.sh."""
    s = get_settings()
    dumps = sorted(Path(s.backup_dir).glob("labuse-*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        raise RuntimeError(f"aucun dump .dump à vérifier dans {s.backup_dir}")
    dump = dumps[0]
    taille_mo = round(dump.stat().st_size / 1e6, 1)
    pg_restore = str(Path(s.pg_bin_dir) / "pg_restore") if s.pg_bin_dir else "pg_restore"
    proc = subprocess.run([pg_restore, "--list", str(dump)], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"dump illisible par pg_restore --list ({dump.name}) : {proc.stderr[:300]}")
    n_objets = sum(1 for l in proc.stdout.splitlines() if l.strip() and not l.lstrip().startswith(";"))
    if n_objets < 50:
        raise RuntimeError(f"table des matières maigre ({n_objets} objets) — dump douteux {dump.name}")
    ctx.compte(dump=dump.name, taille_mo=taille_mo, objets_toc=n_objets,
               note="contrôle lisibilité VPS ; restauration réelle = deploy/mac/restore_test.sh (mensuel Mac)")


# ═══════════════════════════ utilitaire d'alerte (respecte dry-run) ═══════════════════════════

def _envoyer_alerte(corps: str, *, sujet: str = "[LABUSE] alerte exploitation", ctx: JobContext | None = None) -> None:
    from .mail import envoyer_ops
    s = get_settings()
    dest = s.admin_email or s.contact_email
    if not dest:
        return
    r = envoyer_ops(dest, sujet, corps, settings=s)
    if ctx is not None and not r.sent:
        ctx.compte(mail=r.detail)   # « no-config » = dry-run, tracé dans l'état
    log.info("alerte exploitation envoyée=%s (%s)", r.sent, r.detail)


def coherence_robinets(ctx: JobContext) -> None:
    """CIRCUIT-1 lot 4 — LA SONDE « Vérifier que tout coule » : chiffres à ≥ 2 robinets mesurés
    sur les témoins (écarts → circuit_ecarts, statut soldé conservé) + eau ancienne par tampon
    (circuit_eau_ancienne) + verdict (circuit_controles, lu par la page Circuit). Une fuite
    OUVERTE notifie l'admin (dédup jour). Tourne la nuit, après chaque bascule, et au bouton."""
    from .sonde_circuit import controle
    res = controle(ctx.db, declencheur="cron")
    ctx.compte(**{k: v for k, v in res.items() if isinstance(v, (int, float))})
    # CIRCUIT-5 (lot 6.1) — la sonde de nuit joue AUSSI les verrous : une ligne par verrou au
    # journal (geste « controle », cible « verrous »), lue par le Résumé — la même vérité que
    # `labuse circuit verrous` et que la porte de deploy.sh. La sonde vient de tourner : V1b
    # a déjà son passage frais dans la même session.
    from . import circuit_journal, circuit_verrous
    resultats = circuit_verrous.jouer_tous(ctx.db)
    # CIRCUIT-6 lot 8 — la nuit joue AUSSI les sept garanties (même vérité que la CLI et la
    # porte de deploy.sh) ; lot 2 : le remplissage COMPLET (couches carte incluses, ~1 min)
    # est mesuré ici, sur les 12 témoins du jour, et journalisé.
    from . import circuit_garanties
    resultats += circuit_garanties.jouer_garanties(ctx.db)
    try:
        from .registre import remplissage as _rempl
        _mes = _rempl.mesurer_vitrine(ctx.db)          # complet (carte incluse)
        _vides = sorted(s for s, m in _mes.items() if m.get("quasi_vide"))
        circuit_journal.journaliser(
            ctx.db, "controle", "garanties-remplissage", "cron",
            "echec" if _vides else "ok",
            {"mesures": len(_mes), "vides": _vides,
             "types": {t: sum(1 for m in _mes.values() if m["type"] == t)
                       for t in ("parcelle", "commune", "carte", "n.a.")}})
        ctx.compte(remplissage_mesures=len(_mes), remplissage_vides=len(_vides))
    except Exception:  # noqa: BLE001 — la mesure ne casse pas la sonde
        pass
    casses = [r.id for r in resultats if r.verdict == "casse"]
    circuit_journal.journaliser(
        ctx.db, "controle", "verrous", "cron", "echec" if casses else "ok",
        {"joues": len(resultats), "casses": casses,
         "a_decider": [r.id for r in resultats if r.verdict == "a_decider"],
         "preuves": {r.id: r.preuve for r in resultats}})
    ctx.compte(verrous_joues=len(resultats), verrous_casses=len(casses))
    if casses:
        from .api.events import creer_notification
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Circuit",
            titre=f"Verrous cassés : {', '.join(casses)}",
            detail="Le déploiement refusera tant que ça tient. Détail : labuse circuit verrous.",
            lien="/admin", dedup=f"verrous:{today_reunion().isoformat()}")
    if res.get("fuites_ouvertes") or res.get("eau_ancienne_ouverte"):
        from .api.events import creer_notification
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Circuit",
            titre=f"Sonde du circuit : {res.get('fuites_ouvertes', 0)} fuite(s) ouverte(s), "
                  f"{res.get('eau_ancienne_ouverte', 0)} eau(x) ancienne(s)",
            detail="Détail dans circuit_ecarts / circuit_eau_ancienne (page Circuit).",
            lien="/admin", dedup=f"coherence_robinets:{today_reunion().isoformat()}")


def filtres_sources(ctx: JobContext) -> None:
    """CIRCUIT-3 lot 5.1 — LE FILTRE DE NUIT : rejoue les contrôles de chaque filtre sur la version
    SERVIE (dérive dans le temps). Résultats dans filtre_resultats / filtre_versions. Une NOUVELLE
    quarantaine notifie l'admin (dédup jour)."""
    from . import filtres
    nouveaux_quarantaine = []
    n_ok = n_avert = n_quar = 0
    for cle in filtres.sources():
        f = filtres.get_filtre(cle)
        if f is None:
            continue
        try:
            v = filtres.jouer(ctx.db, f)
        except Exception as exc:  # noqa: BLE001 — une source ne fait pas tomber le job
            log.error("filtres-sources : %s a levé (%s)", cle, exc)
            continue
        if v.verdict == "quarantaine":
            n_quar += 1
            nouveaux_quarantaine.append(cle)
        elif v.verdict == "avertissements":
            n_avert += 1
        else:
            n_ok += 1
    ctx.compte(sources_ok=n_ok, sources_avertissements=n_avert, sources_quarantaine=n_quar)
    if nouveaux_quarantaine:
        from .api.events import creer_notification
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Circuit",
            titre=f"Filtre de nuit : {n_quar} source(s) en quarantaine",
            detail="Sources en quarantaine : " + ", ".join(nouveaux_quarantaine)
                   + " (page Circuit — « servir quand même » ou corriger la source).",
            lien="/admin", dedup=f"filtres_sources:{today_reunion().isoformat()}")


def ingest_bodacc(ctx: JobContext) -> None:
    """CIRCUIT-1 lot 8.1 — BODACC au wrapper (quotidien, reprend le legacy) : procédures
    collectives (upsert idempotent) PUIS la chaîne des dérivés légers (fraicheur-derives),
    exactement ce que faisait /etc/cron.d/labuse-bodacc."""
    _ingest_via_cli(ctx, "ingest-bodacc")
    _ingest_via_cli(ctx, "fraicheur-derives")


def regles_references(ctx) -> None:
    """CIRCUIT-4 lot 5.4 — renvoie les agents « règle » sur les fiches dont la référence date de
    plus de six mois ; chaque rapport atterrit dans regle_agent_rapports + circuit_journal (jamais
    d'écriture dans les fiches — un humain relit). Job DÉSACTIVÉ par défaut (jamais posé au
    crontab) : ne tourne qu'à la main (`labuse jobs run regles-references`)."""
    from . import agent_regle
    from .db import session_scope
    cibles = agent_regle.fiches_a_reverifier(plus_de_jours=180)
    verdicts: dict[str, int] = {}
    for did in cibles:
        with session_scope() as s:
            out = agent_regle.lancer_agent(s, did, par="cron")
            s.commit()
        v = out.get("verdict", "erreur")
        verdicts[v] = verdicts.get(v, 0) + 1
    ctx.compte(fiches_a_reverifier=len(cibles), **{f"verdict_{k}": n for k, n in verdicts.items()})
