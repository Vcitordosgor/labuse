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


def essai_fin_proche(ctx: JobContext) -> None:
    """NU5-FIX-1 (C-F7) — (1) AVERTIT à J-1 les essais qui se terminent dans les 24 h, (2) BASCULE en
    suspension les essais ÉCHUS — sans attendre un login (avant, l'essai échu n'était détecté qu'au
    login : un client qui ne revient pas ne recevait rien et restait `actif`). Idempotent : le mail
    d'avertissement est dédupliqué par compte × jour d'échéance ; la bascule ne touche qu'un compte
    encore `actif` et réutilise la primitive existante `basculer_essai_expire` (qui envoie la
    suspension). Le template Brevo de l'avertissement (id 20 `essai_fin_proche`) est un geste console."""
    from zoneinfo import ZoneInfo
    from .comptes import _prenom_titulaire, basculer_essai_expire
    from .mail import envoyer_mail
    db = ctx.db
    base = (get_settings().public_base_url or "https://app.labuse.immo").rstrip("/")
    # (1) AVERTISSEMENT J-1 : essais ACTIFS dont l'échéance tombe dans les prochaines 24 h.
    proches = db.execute(text(
        "SELECT c.id, c.nom, c.essai_expire_at AS fin, "
        " (SELECT u.email FROM utilisateurs u WHERE u.compte_id = c.id AND u.role='titulaire' "
        "  ORDER BY u.id LIMIT 1) AS email "
        "FROM comptes c WHERE c.statut = 'actif' AND c.essai_expire_at IS NOT NULL "
        "  AND c.essai_expire_at > now() AND c.essai_expire_at <= now() + interval '24 hours'")
    ).mappings().all()
    n_avertis = 0
    for r in proches:
        if not r["email"]:
            continue
        d = r["fin"]
        date_fin = d.astimezone(ZoneInfo("Indian/Reunion")).strftime("%d/%m/%Y") if d else ""
        envoyer_mail(key="essai_fin_proche", to=r["email"], compte_id=r["id"],
                     demandeur="job:essai-fin-proche",
                     params={"PRENOM": _prenom_titulaire(r["nom"], r["email"]),
                             "DATE_FIN": date_fin, "LIEN_PAIEMENT": f"{base}/facturation"},
                     dedup=f"essai-fin-proche:{r['id']}:{d.date().isoformat() if d else '?'}")
        n_avertis += 1
    # (2) BASCULE à l'échéance : essais ACTIFS échus → suspension (indépendante du login).
    echus = db.execute(text(
        "SELECT id FROM comptes WHERE statut = 'actif' AND essai_expire_at IS NOT NULL "
        "  AND essai_expire_at <= now()")).scalars().all()
    for cid in echus:
        basculer_essai_expire(db, int(cid))
    db.commit()
    ctx.compte(avertis_j_moins_1=n_avertis, bascules_echeance=len(echus))


def verite_permanente(ctx: JobContext) -> None:
    """NU5-FIX-1 (point 8) — VÉRITÉ-PERMANENTE-1 : rejoue les harnais des 6 lots NU-5 via le runner
    unique `scripts/verite_permanente`. Reporte vert/rouge/sauté par lot ; LÈVE si un harnais lancé
    a échoué (le runner du cron ouvre alors l'incident `job-echec:verite-permanente`)."""
    # PROD-SUITE-1 — `scripts/` est livré en prod mais la RACINE du dépôt n'est pas sur sys.path
    # quand le job tourne (le paquet `labuse` est installé, pas le dépôt) → `import scripts` échouait
    # (« No module named 'scripts' »). On insère la racine AVANT l'import (même geste que coherence_banc).
    import sys
    from pathlib import Path
    racine = Path(__file__).resolve().parents[2]
    if str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
    from scripts.verite_permanente import run
    r = run()
    ctx.compte(verts=r["verts"], rouges=r["rouges"], sautes=r["sautes"],
               lots=[f"{x['lot']}:{x['etat']}" for x in r["lots"]])
    if r["rouges"]:
        raise RuntimeError(f"VÉRITÉ-PERMANENTE — {r['rouges']} harnais en échec : "
                           + ", ".join(x["lot"] for x in r["lots"] if x["etat"] == "rouge"))


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
    # OPS-NUIT-2 — /readyz DÉBOUNCÉ : la décision (ouvrir seulement si « pas prêt » persiste au-delà de
    # la tolérance) est partagée avec `verifier_declencheurs` via `_readyz_decision` (sans base). On la
    # calcule ICI aussi pour garder le REPLI local quand la base est indisponible (pg_dump) : une coupure
    # COURTE de redéploiement ne descend pas dans a_signaler ; une vraie panne, si.
    rz = ops_alertes._readyz_decision(s)
    ready, motif = rz["ready"], rz["motif"]
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
    if rz["ouvrir"]:
        a_signaler.append(("readyz", "/readyz répond « pas prêt »",
                           f"La sonde /readyz locale dit le service NON prêt depuis {round(rz['age_s'])} s "
                           f"(> tolérance {round(rz['tol_s'])} s) : {motif}."))
    else:
        a_resoudre.append("readyz")   # prêt OU coupure courte tolérée → pas d'incident
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


# ═══════════════════════════ AUTONOMIE-1 — calcul de nuit sur le serveur ═══════════════════════════

def _prefixe_nice(s) -> list[str]:
    """Préfixe `nice`/`ionice` pour mettre le calcul SOUS les requêtes servies (le serveur reste
    réactif la nuit même s'il calcule). `ionice` est best-effort : absent (macOS/dev) → on saute."""
    pref = ["nice", "-n", str(getattr(s, "calcul_nuit_nice", 15))]
    if shutil.which("ionice"):
        pref += ["ionice", "-c", "2", "-n", str(getattr(s, "calcul_nuit_ionice", 7))]
    return pref


def _plafond_memoire(mo: int):
    """Un preexec_fn qui pose RLIMIT_AS (plafond mémoire adresse) à `mo` Mo sur le process enfant :
    un calcul qui déraille est tué par le noyau au lieu de faire tomber la prod (OOM). None hors Linux
    (RLIMIT_AS indisponible / dangereux sur macOS) — la fenêtre + nice restent les garde-fous."""
    try:
        import resource  # Linux/Unix ; absent sur certains OS
    except ImportError:
        return None
    octets = int(mo) * 1024 * 1024

    def _poser():  # pragma: no cover — exécuté dans le process enfant
        resource.setrlimit(resource.RLIMIT_AS, (octets, octets))
    return _poser


def _fenetre_calcul_ok(s) -> tuple[bool, str]:
    """Sommes-nous DANS la fenêtre de nuit [debut_h, fin_h[ en heure Réunion ? (garde du mandat :
    01 h–05 h ; abstention propre hors fenêtre, sauf LABUSE_CALCUL_NUIT_FORCE=1 pour la recette.)"""
    from . import autonomie
    if os.environ.get("LABUSE_CALCUL_NUIT_FORCE") == "1":
        return True, "fenêtre forcée (recette)"
    maintenant = _now_reunion_naive()
    if autonomie.fenetre_nuit(maintenant, s.calcul_nuit_debut_h, s.calcul_nuit_fin_h):
        return True, f"dans la fenêtre {s.calcul_nuit_debut_h}h–{s.calcul_nuit_fin_h}h Réunion"
    return False, (f"hors fenêtre de nuit (il est {maintenant.strftime('%H:%M')} Réunion ; "
                   f"fenêtre {s.calcul_nuit_debut_h}h–{s.calcul_nuit_fin_h}h) — abstention")


def _now_reunion_naive() -> datetime:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Indian/Reunion")).replace(tzinfo=None)


def _secondes_avant_fin_fenetre(s) -> float:
    """OPS-NUIT-1 — secondes restantes AVANT la fin de fenêtre (fin_h Réunion, aujourd'hui). Le calcul
    de nuit démarre à 02:00 mais budgétait 4 h (timeout du job) → il débordait à ~06:00, PASSÉ la
    fenêtre 01 h–05 h (incident 03/11 : run jusqu'à 05:59). Le budget du sous-process est désormais
    borné par ce reste : flux-run ne mord jamais sur les heures ouvrées ; s'il ne finit pas, il
    REPREND la nuit suivante (flux-run --resume saute les parcelles déjà faites). 0 si déjà passé."""
    now = _now_reunion_naive()
    fin = now.replace(hour=int(s.calcul_nuit_fin_h), minute=0, second=0, microsecond=0)
    reste = (fin - now).total_seconds()
    return reste if reste > 0 else 0.0


def _declencheur_entree(db, depuis: datetime | None) -> tuple[bool, str]:
    """Une ENTRÉE a-t-elle changé depuis la dernière promotion ? (nouvelle injection / source avancée).
    Heuristique lecture seule : une source dont `last_sync_at` ou `source_horizon_at` est postérieur à
    `depuis`. `depuis` None (jamais promu) → considéré comme déclenché."""
    if depuis is None:
        return True, "aucune promotion connue"
    try:
        n = db.execute(text(
            "SELECT count(*) FROM data_sources "
            "WHERE GREATEST(COALESCE(last_sync_at, 'epoch'), COALESCE(source_horizon_at, 'epoch')) > :d"),
            {"d": depuis}).scalar()
    except Exception as exc:  # noqa: BLE001 — table absente/colonne : pas de déclencheur plutôt que crash
        log.warning("calcul-nuit : déclencheur d'entrée illisible (%s)", exc)
        return False, "déclencheur illisible"
    return (n or 0) > 0, f"{n} source(s) avancée(s) depuis la dernière promotion"


# DEPLOY-AUTONOMIE — paliers « actionnables » : le vocabulaire SERVI (`parcel_p_score_v2.tier`) porte
# DEUX générations (anciens runs par rang : brulante/chaude ; runs récents par domaine : priorite/
# a_suivre). La définition « promues » fait foi — `golden_ops._distribution` : brulante ∪ chaude ∪
# priorite ∪ a_suivre. On la réutilise telle quelle (pas de 3ᵉ vocabulaire qui divergerait).
_TIERS_ACTIONNABLES = ("brulante", "chaude", "priorite", "a_suivre")
#: fragment SQL `IN (...)` dérivé de la constante (valeurs figées dans le code — jamais une entrée
#: utilisateur ; interpolation sûre, pas de bind-param « expanding » à déclarer dans chaque text()).
_IN_ACTIONNABLES = "(" + ", ".join(f"'{t}'" for t in _TIERS_ACTIONNABLES) + ")"


def _mesures_run(db, candidat: str, precedent: str) -> dict:
    """Rassemble les mesures de controler_run contre la base RÉELLE, chaque mesure isolée (une requête
    qui rate laisse la mesure à None → controler_run REFUSE, jamais un faux vert). Lecture seule.

    DEPLOY-AUTONOMIE — les requêtes d'AUTONOMIE-1 visaient des colonnes INEXISTANTES en prod (code_palier,
    parcel_id, parcel_flags.run_id/entierement_rouge, coherence_runs.ecarts/cree_at) — la couche DB du
    calcul de nuit n'avait jamais tourné contre le schéma servi. Elles sont réécrites ici sur les
    colonnes réelles (tier, parcelle_id=IDU) et les lectures CANONIQUES déjà servies :
      · complétude   → `bascule_flux._run_complet` (score v2 + cascade résolue, même garde que la bascule) ;
      · entièrement rouge → fraction PPR lue dans la cascade (`dryrun_cascade_results`, motif « N % de la
        surface »), MÊME source que `renouvellement.ppr_x` ; la cascade du run se résout via
        `bascule_flux.resoudre_cascade_run` (run propre ou étage 0 emprunté — ex. q_v21 sur q_v19_sources) ;
      · cohérence    → dernier passage du banc (`coherence_runs`), signal « vert » = `faux_client`
        (un client lit une valeur FAUSSE) + `erreurs_lecteur` (banc qui n'a pas pu lire). Le `n_ecarts`
        brut (écarts tolérables/incohérences connues du balayage île) n'est PAS un gate de promotion.
    Chaque requête a été validée en lecture seule contre la prod (cf. reports/DEPLOY-AUTONOMIE.md)."""
    from . import bascule_flux
    m: dict = {}

    def _scal(sql: str, params: dict | None = None):
        try:
            return db.execute(text(sql), params or {}).scalar()
        except Exception as exc:  # noqa: BLE001
            log.warning("calcul-nuit mesure illisible [%s] : %s", sql[:40], exc)
            return None

    # complétude : la garde CANONIQUE de bascule (score v2 présent ET cascade résoluble). Un run
    # incomplet est plus dangereux qu'un run qui échoue — _run_complet le dit sans servir.
    try:
        complet, motif = bascule_flux._run_complet(db, candidat)
        m["run_complet"] = bool(complet)
        m["run_complet_motif"] = motif
    except Exception as exc:  # noqa: BLE001
        log.warning("calcul-nuit : complétude illisible (%s)", exc)
        m["run_complet"] = False
    # le manifeste du candidat est écrit par le flux-run ; sa présence est vérifiée par le gatherer appelant.
    m["comptes_parcelles"] = _scal("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id = :r", {"r": candidat})
    m["comptes_precedent"] = _scal("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id = :r", {"r": precedent})
    # copropriétés en palier actionnable (doctrine E-010 : doit être 0)
    m["copro_actionnables"] = _scal(
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id = :r AND copro IS TRUE "
        f"AND tier IN {_IN_ACTIONNABLES}", {"r": candidat})
    # parcelles ENTIÈREMENT en zone rouge PPR (fraction = 100 %) en palier actionnable (doit être 0).
    # La cascade se résout (run propre ou étage 0 emprunté) ; non résolue → mesure manquante → REFUS.
    try:
        cascade_run, _motif = bascule_flux.resoudre_cascade_run(db, candidat)
    except Exception as exc:  # noqa: BLE001
        log.warning("calcul-nuit : cascade du candidat non résolue (%s)", exc)
        cascade_run = None
    if cascade_run:
        m["rouge_actionnables"] = _scal(
            "WITH rouge AS ("
            "  SELECT p.idu, max((regexp_match(cr.detail, '([0-9]+) % de la surface'))[1]::int) AS pct "
            "  FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id "
            "  WHERE cr.run_label = :c AND cr.layer_name = 'risques' AND cr.result = 'HARD_EXCLUDE' "
            "    AND cr.detail LIKE '%PPR zone rouge%' GROUP BY p.idu) "
            "SELECT count(*) FROM parcel_p_score_v2 s JOIN rouge ON rouge.idu = s.parcelle_id "
            f"WHERE s.run_id = :r AND s.tier IN {_IN_ACTIONNABLES} AND rouge.pct >= 100",
            {"c": cascade_run, "r": candidat})
    else:
        m["rouge_actionnables"] = None   # cascade non résolue : on NE conclut pas → controler_run refuse
    # écart de paliers vs précédent (parcelles communes qui changent de PALIER). QV21-PROMO-1 — on
    # compare des NOTIONS IDENTIQUES : chaque tier stocké (nouveau ou ancien code) est projeté sur son
    # palier canonique (`tiers_client.canon_sql` ← `code_palier`, source unique) AVANT de compter. Sans
    # cette projection, un candidat en vocabulaire PALIERS-1 (priorite/a_suivre/sans_signal/ecartee) vs
    # un servi en vocabulaire ancien (ou l'inverse) « changeait » de palier par simple renommage →
    # l'écart explosait (35,5 % mesuré sur q_v21) alors que le mouvement réel est minuscule.
    from .scoring.tiers_client import canon_sql
    _ca, _cb = canon_sql("a.tier"), canon_sql("b.tier")
    m["paliers_total"] = _scal(
        "SELECT count(*) FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b ON a.parcelle_id = b.parcelle_id "
        "WHERE a.run_id = :a AND b.run_id = :b", {"a": candidat, "b": precedent})
    m["paliers_change"] = _scal(
        "SELECT count(*) FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b ON a.parcelle_id = b.parcelle_id "
        f"WHERE a.run_id = :a AND b.run_id = :b AND {_ca} IS DISTINCT FROM {_cb}",
        {"a": candidat, "b": precedent})
    # cohérence : dernier passage du BANC (coherence_runs, mode « île » = coherence-banc de 03h45), JAMAIS
    # une mesure relancée ici. Vert = 0 FAUX-CLIENT et 0 erreur lecteur ; les écarts tolérables/incohérences
    # connues du balayage ne bloquent pas une promotion. OPS-NUIT-2 (piège cron DEPLOY-AUTONOMIE-2) : le
    # banc tourne à 03h45, APRÈS le début du calcul (02h) → la dernière ligne peut être celle d'HIER. On
    # exige qu'elle soit FRAÎCHE (ts ≥ now − max_age) ; sinon la cohérence est « en attente » du banc —
    # `coherence_frais=False` dit à controler_run de NE PAS conclure (pas de faux « contrôles en échec »).
    try:
        max_age_h = float(getattr(get_settings(), "calcul_nuit_coherence_max_age_h", 12.0))
        row = db.execute(text(
            "SELECT faux_client, COALESCE(erreurs_lecteur, 0), ts FROM coherence_runs "
            "WHERE mode = 'ile' ORDER BY ts DESC LIMIT 1")).first()
        if row is None:
            m["coherence_ecarts"], m["coherence_erreurs"], m["coherence_frais"] = None, None, False
        else:
            ts = row[2]
            if ts is not None and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            frais = ts is not None and (datetime.now(timezone.utc) - ts).total_seconds() <= max_age_h * 3600
            m["coherence_ecarts"] = row[0]
            m["coherence_erreurs"] = row[1]
            m["coherence_frais"] = bool(frais)
            m["coherence_ts"] = ts.isoformat() if ts else None
    except Exception as exc:  # noqa: BLE001
        log.warning("calcul-nuit : cohérence illisible (%s)", exc)
        m["coherence_ecarts"] = None
        m["coherence_erreurs"] = None
        m["coherence_frais"] = False
    return m


def calcul_nuit(ctx: JobContext) -> None:
    """AUTONOMIE-1 — LE CALCUL DE NUIT (q_v21 au premier run), sur le SERVEUR (plus sur le Mac).

      1. Fenêtre 01 h–05 h Réunion : hors fenêtre → abstention propre (pas un échec).
      2. Déclencheur : une entrée a changé (injection/source) OU cadence de fond (≤ 1×/semaine) — sinon on
         ne recalcule pas pour rien.
      3. Dépendances de calcul (pandas/joblib) : ABSENTES → ÉCHEC BRUYANT (« venv prod sans ML »),
         jamais un faux vert. Le mandat veut que ces deps entrent au venv prod de façon tracée
         (deploy/requirements-calcul.txt + étape deploy) ; tant qu'elles manquent, ce job le crie.
      4. flux-run SOUS nice/ionice + plafond mémoire, borné à la fenêtre : dépassement → abandon propre.
      5. CONTRÔLES avant promotion (autonomie.controler_run) : manifeste, comptes, cohérence, 0 copro /
         0 rouge actionnable, écart de paliers sous le seuil. Tout vert → bascule. Sinon → PAS de
         promotion + mail à Vic (le run candidat reste en base, non servi — rejouable)."""
    import importlib
    import sys
    from . import autonomie, ops_alertes, runs
    from .db import session_scope
    s = get_settings()

    ok_fen, motif_fen = _fenetre_calcul_ok(s)
    if not ok_fen:
        ctx.compte(abstention=motif_fen, promu=False)
        return

    # OPS-NUIT-1 — pré-vol en SESSION COURTE, refermée AVANT le calcul. Le bug du 03/11 : calcul_nuit
    # tenait `ctx.db` (transaction ouverte par les lectures de pré-vol) pendant les ~4 h du sous-process
    # flux-run ; Postgres tuait la connexion à `idle_in_transaction_session_timeout` (2 min) →
    # IdleInTransactionSessionTimeout au premier usage d'après. Règle (décision Vic) : AUCUNE transaction
    # ouverte pendant le calcul Python — une session courte par phase. On n'utilise plus `ctx.db` ici.
    promu_at = None
    try:
        promu_at = runs.promu_at()
    except Exception:  # noqa: BLE001
        pass
    with session_scope() as db:
        declenche, motif_decl = _declencheur_entree(db, promu_at)
    doit, motif_doit = autonomie.doit_calculer(
        promu_at, declenche, s.calcul_nuit_cadence_min_jours, datetime.now(timezone.utc))
    if not doit:
        ctx.compte(abstention=motif_doit, declencheur=motif_decl, promu=False)
        return

    # OPS-URGENCE-2 (mandat Vic) — GARDE ANTI-DOUBLON. Un flux-run peut DÉJÀ tourner : reprise lancée
    # à la main en journée (fenêtre élargie pour finir q_v21), ou passage précédent pas encore fini.
    # Deux flux-run concurrents sur le MÊME label = course sur dryrun_parcel_evaluations (INSERT du
    # même parcel_id) + double CPU. On s'ABSTIENT proprement (pas un échec) : le run en cours continue.
    from . import run_progress
    try:
        deja = run_progress.en_cours()
    except Exception:  # noqa: BLE001
        deja = None
    if deja:
        ctx.compte(abstention=f"un calcul est déjà en cours (label {deja.get('label')}, "
                              f"pid {deja.get('pid')}) — pas de second passage concurrent",
                   promu=False)
        return

    # dépendances de calcul — loud si absentes (pas de faux vert)
    for mod in ("pandas", "numpy", "joblib"):
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"calcul-nuit : dépendance de calcul « {mod} » absente du venv ({exc}). "
                "Installer deploy/requirements-calcul.txt dans le venv prod (tracé) avant le premier "
                "run q_v21 — le mandat AUTONOMIE-1 l'exige ; on NE calcule PAS sans.") from exc

    label = os.environ.get("LABUSE_CALCUL_NUIT_LABEL", "q_v21")
    recette = os.environ.get("LABUSE_CALCUL_NUIT_RECETTE", "q_v15")

    # OPS-URGENCE-3 (mandat Vic) — UN RUN DÉJÀ COMPLET N'EST PAS RELANCÉ. Si la cascade ET le scoring du
    # label sont déjà faits (garde CANONIQUE de bascule `_run_complet` : score v2 présent + cascade
    # résoluble, la même que `_mesures_run`), relancer `flux-run` ne ferait que RE-SCORER pour rien — et,
    # tant que les artefacts q_v15 manquaient en prod, échouait à l'entrée du scoring (code 1 en 38 s),
    # transformant un run FINI en « calcul-nuit en échec ». On passe DROIT aux contrôles + verdict.
    from . import bascule_flux
    with session_scope() as db:
        try:
            deja_complet, motif_complet = bascule_flux._run_complet(db, label)
        except Exception as exc:  # noqa: BLE001 — complétude illisible → on calcule (jamais un faux « complet »)
            log.warning("calcul-nuit : complétude du label %s illisible (%s) — on (re)calcule", label, exc)
            deja_complet, motif_complet = False, None

    if deja_complet:
        log.info("calcul-nuit : run %s déjà complet (%s) — pas de recalcul, contrôles directs",
                 label, motif_complet)
    else:
        # OPS-NUIT-1 — budget BORNÉ PAR LA FIN DE FENÊTRE (plus le timeout brut) : le calcul ne déborde
        # jamais passé fin_h. Le run est REPRENABLE (flux-run --resume) : s'il ne tient pas dans la nuit, il
        # reprend la suivante. En recette (LABUSE_CALCUL_NUIT_FORCE=1) on garde le timeout brut, pas de borne.
        budget_job = float(getattr(ctx, "timeout_s", 14400) or 14400)
        if os.environ.get("LABUSE_CALCUL_NUIT_FORCE") == "1":
            budget = max(300.0, budget_job - _SOUS_PROCESS_MARGE_S)
        else:
            budget = max(300.0, min(budget_job, _secondes_avant_fin_fenetre(s)) - _SOUS_PROCESS_MARGE_S)
        cmd = _prefixe_nice(s) + [sys.executable, "-m", "labuse.cli", "flux-run",
                                 "--label", label, "--recette", recette]
        # AUCUNE connexion DB tenue pendant le sous-process (voir pré-vol ci-dessus).
        try:
            proc = _run_sous_process_nice(cmd, budget, _plafond_memoire(s.calcul_nuit_mem_mo))
        except SousProcessTimeout:
            # Fin de fenêtre atteinte AVANT la fin du calcul : abandon PROPRE, PAS un échec. flux-run a
            # persisté ce qu'il a fait (cascade commitée par commune) et REPREND la nuit suivante (--resume).
            # OPS-URGENCE-2 — SURFACER L'AVANCEMENT. R4 décrivait « la reprise repart sans avancer » : en
            # fait elle AVANCE (parcelles cumulées par nuit, sans doublon) mais la fenêtre ~3 h est trop
            # courte pour les communes lourdes restantes. On reporte donc faites/total/% dans les compteurs
            # pour que le résumé du matin montre la PROGRESSION, pas un faux « bloqué ».
            faits = total = None
            with session_scope() as db:
                ops_alertes.resoudre(db, f"calcul-nuit:{label}")  # ni promotion en attente, ni échec cette nuit
                try:
                    faits = db.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:r"),
                                       {"r": label}).scalar() or 0
                    total = db.execute(text("SELECT count(*) FROM parcels")).scalar() or 0
                except Exception:  # noqa: BLE001
                    faits = total = None
                db.commit()
            pct = round(100.0 * faits / total, 1) if (faits and total) else None
            ctx.compte(label=label, recette=recette, promu=False,
                       abandon=f"fin de fenêtre {s.calcul_nuit_fin_h}h atteinte avant la fin du calcul — "
                               "reprise la nuit prochaine (reprenable, flux-run --resume)",
                       parcelles_faites=faits, parcelles_total=total, avancement_pct=pct,
                       budget_s=round(budget))
            return
        if proc.returncode != 0:
            raise RuntimeError(f"flux-run {label} a échoué (code {proc.returncode}) : "
                               f"{(proc.stderr or proc.stdout or '')[-400:]}")

    par = f"calcul-nuit (automatique) — {label}"
    # DEPLOY-AUTONOMIE (décision Vic, première nuit) — GATE DE PROMOTION. Par défaut le calcul de nuit
    # promeut seul si tous les contrôles passent (pleine autonomie). Mais la PREMIÈRE mise en service de
    # q_v21 se fait « sous l'œil de Vic » (AUTONOMIE-1) : LABUSE_CALCUL_NUIT_PROMEUT=0 fait CALCULER +
    # CONTRÔLER ; le VERDICT part dans le RÉSUMÉ DU MATIN (plus de mail dédié), Vic promeut à la main.
    promeut = os.environ.get(
        "LABUSE_CALCUL_NUIT_PROMEUT", "1" if getattr(s, "calcul_nuit_promeut", True) else "0") != "0"

    # mesures + verdict/promotion — SESSION FRAÎCHE (la pré-vol est refermée depuis des heures).
    with session_scope() as db:
        precedent = runs.current()
        mesures = _mesures_run(db, label, precedent)
        mesures["manifeste_present"] = _manifeste_candidat_present(label)

        if not promeut:
            v = autonomie.controler_run(mesures, palier_delta_max_pct=s.calcul_nuit_palier_delta_max_pct)
            verdict_txt = v.resume()
            # OPS-NUIT-2 — TROIS issues, pas deux : OK (à promouvoir), EN ATTENTE (banc de cohérence pas
            # encore passé — PAS un incident, verdict au prochain résumé), ÉCHEC (problème actionnable).
            en_attente_seul = bool(v.en_attente) and not v.echecs
            if v.ok or en_attente_seul:
                # Rien de cassé : le RÉSUMÉ DU MATIN annonce « run calculé, contrôles OK, à promouvoir »
                # (ou « cohérence en attente du banc »). Pas de mail d'incident (OPS-NUIT-1 point 6).
                ops_alertes.resoudre(db, f"calcul-nuit:{label}")
            else:
                # Contrôles en ÉCHEC = problème actionnable → incident URGENT avec lien d'action.
                ops_alertes.signaler(
                    db, f"calcul-nuit:{label}",
                    f"Calcul de nuit {label} : contrôles en échec — promotion bloquée",
                    f"Le run candidat {label} est calculé mais les contrôles ÉCHOUENT : {verdict_txt}.\n"
                    f"Écart de paliers : {v.details.get('palier_delta_pct')} %\nMesures : {mesures}\n"
                    "Le run reste en base (non servi) — à corriger puis rejouer.", lien="/admin")
            db.commit()
            ctx.compte(label=label, recette=recette, promu=False, promotion_en_attente=v.ok,
                       controles_ok=v.ok, controles_en_attente=en_attente_seul,
                       calcul_saute=deja_complet, verdict=verdict_txt, mesures=mesures,
                       palier_delta_pct=v.details.get("palier_delta_pct"))
            return

        def _promouvoir():
            from . import bascule_flux
            return bascule_flux.basculer(db, label, par)

        def _alerter(verdict, **kw):
            corps = (f"Le run candidat {label} N'A PAS été promu : {verdict.resume()}.\n"
                     + (f"Erreur de promotion : {kw.get('erreur_promotion')}\n" if kw.get("erreur_promotion") else "")
                     + f"Mesures : {verdict.details.get('mesures')}\n"
                     "Le run reste en base (non servi) — rejouable après correction.")
            ops_alertes.signaler(db, f"calcul-nuit:{label}",
                                 f"Calcul de nuit non promu : {label}", corps, lien="/admin")

        resultat = autonomie.promouvoir_si_ok(
            mesures, palier_delta_max_pct=s.calcul_nuit_palier_delta_max_pct,
            promouvoir=_promouvoir, alerter=_alerter)
        if resultat["promu"]:
            ops_alertes.resoudre(db, f"calcul-nuit:{label}")  # un run promu referme l'incident de non-promotion
        db.commit()
        ctx.compte(label=label, recette=recette, promu=resultat["promu"],
                   verdict=resultat["resume"], mesures=mesures,
                   palier_delta_pct=resultat["verdict"].details.get("palier_delta_pct"))


def _manifeste_candidat_present(label: str) -> bool:
    """Le flux-run (et recompute-paliers) écrit le MANIFESTE DU CANDIDAT (config/candidat_manifest.json) ;
    sa présence POUR CE LABEL est une pré-condition de promotion. QV21-PROMO-1 — correction d'un faux
    « manifeste absent » permanent : l'ancien code lisait `runs._manifeste` (import LOCAL dans les
    fonctions de `runs`, jamais un attribut de module → AttributeError systématique → toujours False).
    On lit désormais le vrai manifeste candidat et on exige qu'il concerne CE run. Best-effort :
    absent/illisible/mauvais label → False → controler_run refuse."""
    try:
        from . import manifeste
        m = manifeste.lire_candidat() or {}
        return bool(m) and m.get("scoring_run") == label
    except Exception:  # noqa: BLE001
        return False


# ═══════════════════════════ OPS-NUIT-1 — le RÉSUMÉ DU MATIN (mail quotidien) ═══════════════════════════

def _resume_matin_texte(db, s) -> tuple[bool, str, str]:
    """Construit le résumé du matin : (urgent, sujet, corps). Part TOUS les jours, même « rien à
    signaler » (décision Vic, point 6b). Chaque source est best-effort — une lecture qui rate n'empêche
    pas le reste : le résumé DOIT toujours partir. `urgent` = il y a une panne ou un geste attendu."""
    from . import jobs_journal, ops_alertes
    jour = _now_reunion_naive().strftime("%d/%m/%Y")
    L: list[str] = []
    urgent = False

    # 1 — calcul de nuit : le verdict de la nuit (ce que Vic attend le matin).
    try:
        h = jobs_journal.historique(db, "calcul-nuit", 1)
        if not h:
            L.append("• Calcul de nuit : aucun passage enregistré.")
        else:
            r = h[0]
            c = r.get("compteurs") or {}
            statut = r.get("statut")
            lbl = c.get("label", "q_v21")
            if statut == "echec":
                urgent = True
                L.append(f"• Calcul de nuit : ÉCHEC — {(r.get('erreur') or '')[:200]}")
            elif c.get("abandon"):
                L.append(f"• Calcul de nuit : {c['abandon']}")
            elif c.get("abstention"):
                L.append(f"• Calcul de nuit : abstention — {c['abstention']}")
            elif c.get("promu"):
                L.append(f"• Calcul de nuit : {lbl} PROMU et servi aux clients.")
            elif c.get("promotion_en_attente"):
                L.append(f"• Calcul de nuit : {lbl} calculé, contrôles OK — À PROMOUVOIR : "
                         f"{ops_alertes._url_absolue(s, '/admin')}")
            elif c.get("controles_en_attente"):
                # OPS-NUIT-2 — cohérence pas encore mesurée cette nuit (banc 03h45) : INFO, pas URGENT.
                L.append(f"• Calcul de nuit : {lbl} calculé — cohérence EN ATTENTE du banc de 03h45 "
                         "(verdict au prochain résumé).")
            elif c.get("controles_ok") is False:
                urgent = True
                L.append(f"• Calcul de nuit : {lbl} contrôles EN ÉCHEC — {c.get('verdict')}")
            else:
                L.append(f"• Calcul de nuit : {statut} ({lbl}).")
    except Exception as exc:  # noqa: BLE001
        L.append(f"• Calcul de nuit : état illisible ({type(exc).__name__}).")

    # 2 — sauvegardes : dernier dump TERMINÉ (VPS) + copie hors-VPS. OPS-NUIT-2 : `_dumps_termines`
    # écarte un dump en cours d'écriture (sinon le résumé afficherait sa taille partielle « 1,2 Mo »).
    try:
        dumps = ops_alertes._dumps_termines(s.backup_dir)
        if not dumps:
            if ops_alertes._backup_en_cours():
                L.append("• Sauvegarde : en cours d'écriture (dump pas encore terminé).")
            else:
                urgent = True
                L.append("• Sauvegarde : AUCUN dump présent — la sauvegarde ne tourne plus.")
        else:
            d = dumps[0]
            age_h = round((datetime.now(timezone.utc).timestamp() - d.stat().st_mtime) / 3600, 1)
            L.append(f"• Sauvegarde : {d.name} — {round(d.stat().st_size / 1e6, 1)} Mo, il y a {age_h} h "
                     f"({len(dumps)} conservé(s)).")
        ce = ops_alertes.lire_copie_externe(s.backup_dir)
        if ce:
            age_j = (datetime.now(timezone.utc) - ce["copie_at"]).days
            L.append(f"• Copie hors-VPS : {ce['copie_at'].astimezone().strftime('%d/%m')} ({age_j} j).")
        else:
            L.append("• Copie hors-VPS : aucune enregistrée — branche le disque externe.")
    except Exception as exc:  # noqa: BLE001
        L.append(f"• Sauvegarde : état illisible ({type(exc).__name__}).")

    # 3 — Radar : LE compteur canonique de la nuit, par portail (OPS-NUIT-2) — le MÊME chiffre que le
    # Tableau de bord et l'admin Radar. Avant : la DERNIÈRE ligne pige_passes (ORDER BY id) seule → 119,
    # alors que le Tableau de bord sommait les passes → 152, pour la même nuit : trois nombres pour une
    # notion. Désormais « annonces nouvelles », par portail, lues de pige_annonces (vérité par portail).
    try:
        from .pige.comptage_nuit import comptage_nuit as _comptage_nuit, ligne_resume as _ligne_resume
        cn = _comptage_nuit(db)
        if cn.get("captured_at"):
            try:
                quand = datetime.fromisoformat(cn["captured_at"]).astimezone().strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                quand = cn.get("jour") or "?"
            L.append(f"• Radar : capture auto du {quand} — {_ligne_resume(cn)} · "
                     f"{int(cn.get('pages') or 0)} page(s) lue(s).")
        else:
            L.append("• Radar : aucune capture automatique enregistrée.")
    except Exception as exc:  # noqa: BLE001
        L.append(f"• Radar : état illisible ({type(exc).__name__}).")

    # 4 — verrous : dernier contrôle (sonde de nuit).
    try:
        row = db.execute(text("SELECT ts, resultat, details FROM circuit_journal WHERE cible='verrous' "
                              "ORDER BY id DESC LIMIT 1")).mappings().first()
        if row:
            det = row["details"] if isinstance(row["details"], dict) else {}
            casses = det.get("casses") or []
            a_decider = det.get("a_decider") or []
            avert = det.get("avertissements") or []   # SILENCE-1 (point 5) : G8 à part des cassés
            avert_txt = f" ; avertissements : {', '.join(avert)}" if avert else ""
            L.append(f"• Verrous : {row['resultat']} ({det.get('joues', '?')} joués ; "
                     f"cassés : {', '.join(casses) or 'aucun'} ; à décider : "
                     f"{', '.join(a_decider) or 'aucun'}{avert_txt}).")
        else:
            L.append("• Verrous : aucun contrôle enregistré.")
    except Exception as exc:  # noqa: BLE001
        L.append(f"• Verrous : état illisible ({type(exc).__name__}).")

    # 5 — cohérence : dernier passage du banc.
    try:
        row = db.execute(text("SELECT ts, faux_client, COALESCE(erreurs_lecteur,0) AS el, n_ecarts "
                              "FROM coherence_runs ORDER BY ts DESC LIMIT 1")).mappings().first()
        if row:
            L.append(f"• Cohérence : {row['faux_client']} faux-client, {row['el']} erreur(s) lecteur "
                     f"({row['n_ecarts']} écart(s) connus).")
        else:
            L.append("• Cohérence : aucun passage du banc.")
    except Exception as exc:  # noqa: BLE001
        L.append(f"• Cohérence : état illisible ({type(exc).__name__}).")

    # 6 — incidents OUVERTS (avec lien d'action) et 7 — rentrés dans l'ordre depuis hier.
    # SILENCE-1 (point 3) — la liste « à traiter » ne contient QUE de vraies cartes de Vic : on retire
    # les escalades d'ancienneté « escalade:ancien:<base> » quand leur incident <base> est DÉJÀ listé
    # (c'est un rappel interne, pas un second geste → un seul incident, un seul lien). [URGENT] ne se
    # décide que sur ces incidents réellement actionnables (+ panne de nuit/sauvegarde ci-dessus) :
    # plus de « à regarder » déclenché par un doublon d'escalade ou par un incident déjà refermé (la
    # requête `incidents_ouverts` ne rend que `resolu_at IS NULL`, donc jamais un « vient d'être résolu »).
    try:
        ouverts = ops_alertes.incidents_ouverts(db)
        a_traiter = ops_alertes.incidents_a_traiter(ouverts)
        if a_traiter:
            urgent = True
            L.append(f"\nIncidents ouverts ({len(a_traiter)}) — à traiter :")
            for i in a_traiter:
                lien = ops_alertes._url_absolue(s, ops_alertes._lien_action(i["cle"], None))
                L.append(f"  - {i['sujet']}  → {lien}")
        else:
            L.append("\nIncidents ouverts : aucun. 👍")
    except Exception as exc:  # noqa: BLE001
        L.append(f"\nIncidents ouverts : illisibles ({type(exc).__name__}).")
    try:
        resolus = ops_alertes.incidents_resolus_depuis(db, 26)
        if resolus:
            L.append(f"\nRentré dans l'ordre depuis hier ({len(resolus)}) :")
            for i in resolus:
                L.append(f"  - {i['sujet']}")
    except Exception as exc:  # noqa: BLE001
        L.append(f"\nRésolutions illisibles ({type(exc).__name__}).")

    tete = ops_alertes.URGENT if urgent else ops_alertes.INFO
    sujet = f"{tete} Résumé du matin — {'à regarder' if urgent else 'rien à signaler'} ({jour})"
    corps = f"Résumé d'exploitation LABUSE — {jour}\n\n" + "\n".join(L) + "\n\n— LABUSE, exploitation"
    return urgent, sujet, corps


def resume_matin(ctx: JobContext) -> None:
    """OPS-NUIT-1 point 6(b) (décision Vic) — LE RÉSUMÉ DU MATIN. UN mail, TOUS les jours (même « rien à
    signaler ») : verdict du calcul de nuit, sauvegardes (VPS + hors-VPS), Radar, verrous, cohérence,
    incidents ouverts (avec lien d'action) et ce qui est rentré dans l'ordre depuis hier. Remplace les
    mails « résolu » un-par-un (point 6a). Sujet préfixé [URGENT] s'il y a un geste attendu, sinon [INFO]."""
    from . import ops_alertes
    s = get_settings()
    # JOHN-TAYLOR-1 — c'est John qui ÉCRIT le résumé (à partir des faits du résumé actuel). S'il échoue
    # (plafond, dégradé, anti-invention), le résumé actuel part tel quel (meta.par = 'repli').
    par = "repli"
    if getattr(s, "john_actif", True):
        try:
            from .john import resume as _john_resume
            urgent, sujet, corps, meta = _john_resume.composer_resume_matin(ctx.db, s)
            par = meta.get("par", "repli")
            _john_resume.enregistrer_resume(ctx.db, urgent=urgent, sujet=sujet, corps=corps, par=par)
        except Exception:  # noqa: BLE001 — jamais John ne doit empêcher le mail de partir
            urgent, sujet, corps = _resume_matin_texte(ctx.db, s)
    else:
        urgent, sujet, corps = _resume_matin_texte(ctx.db, s)
    dest = ops_alertes._destinataire(s)
    envoi = "pas-de-destinataire"
    if dest:
        from .mail import envoyer_ops
        envoi = envoyer_ops(dest, sujet, corps, settings=s).detail
    ctx.compte(urgent=urgent, sujet=sujet, destinataire=dest or None, envoi=envoi, resume_par=par)


def john_veille(ctx: JobContext) -> None:
    """JOHN-TAYLOR-1 — LA VEILLE DE NUIT (informe, n'injecte rien). Un passage IA plafonné ; les items
    (sourcés + datés) sont rangés dans `john_veille`. En pause (plafond) ou dégradé = passage à vide
    propre (aucun échec)."""
    from .john import veille as _john_veille
    out = _john_veille.lancer(ctx.db, settings=get_settings())
    ctx.compte(ok=out.get("ok"), pause=out.get("pause", False), n_items=out.get("n", 0),
               erreur=out.get("erreur"))


def _run_sous_process_nice(cmd, budget_s, preexec):
    """Comme `_run_sous_process_borne` mais avec un preexec_fn (plafond mémoire). Même garde de groupe :
    dépassement ou interruption → kill du GROUPE (aucun calcul orphelin qui continue de committer)."""
    import signal as _signal

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            cwd=os.getcwd(), start_new_session=True, preexec_fn=preexec)

    def _tuer_groupe():
        try:
            os.killpg(proc.pid, _signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()

    try:
        out, err = proc.communicate(timeout=budget_s)
    except subprocess.TimeoutExpired:
        _tuer_groupe()
        out, err = proc.communicate()
        raise SousProcessTimeout(
            f"calcul tué après {round(budget_s)} s (fin de fenêtre/budget) — groupe arrêté, aucun "
            f"calcul orphelin. Dernière sortie : {(err or out or '')[-300:]}", proc.pid)
    except BaseException:
        _tuer_groupe()
        proc.communicate()
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


# ═══════════════════════════ AUTONOMIE-1 — injection des sources de classe A ═══════════════════════════

def injection_nuit(ctx: JobContext) -> None:
    """AUTONOMIE-1 — injecte SEULE, la nuit, les sources de CLASSE A (référence à faible risque) qui ont
    avancé, avec contrôles (comptes non nuls, géométries valides, couverture 974, écart sous seuil) et
    RETOUR ARRIÈRE automatique si un contrôle échoue. Les sources de CLASSE B (structurant) ne sont
    JAMAIS injectées ici : elles sont LISTÉES et un mail demande le clic de Vic.

    Ce job ORCHESTRE ; l'ingestion réelle reste le pipeline existant (CLI par source). En l'absence de
    mapping source→commande d'ingestion vérifié pour une classe A donnée, la source est signalée « à
    câbler » (jamais injectée à l'aveugle). Idempotent : une source déjà à jour n'est pas réinjectée."""
    from . import autonomie
    db = ctx.db
    s = get_settings()
    # le registre des sources + leur dernier état de veille
    try:
        srcs = db.execute(text(
            "SELECT name, category FROM data_sources ORDER BY name")).mappings().all()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"injection-nuit : registre data_sources illisible ({exc})") from exc
    rangees = autonomie.sources_par_classe([dict(r) for r in srcs])
    classe_a = rangees["A"]
    classe_b = rangees["B"]

    # Les sources qui ont AVANCÉ amont (sentinelle) — une seule lecture, partagée A/B.
    try:
        nouvelles = set(db.execute(text(
            "SELECT d.name FROM data_sources d JOIN source_veille v ON v.source_id = d.id "
            "WHERE v.dernier_statut = 'nouvelle_version'")).scalars().all())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"injection-nuit : lecture de la veille impossible ({exc})") from exc

    # Les sources de classe B qui ont avancé → mail « à valider » (clic de Vic), jamais injectées.
    try:
        from . import ops_alertes
        nouvelles_b = sorted(b["name"] for b in classe_b if b["name"] in nouvelles)
        if nouvelles_b:
            ops_alertes.signaler(
                db, "injection-b-en-attente",
                f"{len(nouvelles_b)} source(s) structurante(s) à injecter (ton clic)",
                "Ces sources structurantes (classe B) ont une nouvelle version amont et ATTENDENT ta "
                "validation (elles ne s'injectent jamais seules) :\n  · " + "\n  · ".join(nouvelles_b)
                + "\n\nOuvre le Tableau de bord → Injecter pour les passer une à une.")
        else:
            ops_alertes.resoudre(db, "injection-b-en-attente")
    except Exception as exc:  # noqa: BLE001 — la demande B ne doit pas casser l'injection A
        log.warning("injection-nuit : demande classe B impossible (%s)", exc)

    # Classe A : injection SEULE la nuit (mandat AUTONOMIE / TABLEAU-1 point 1). On ne lance QUE les
    # sources de classe A qui ont AVANCÉ amont ET qui sont SÛRES (INJECTION-SOLIDE-3 : routées par
    # `injection_sure`, ou vérifiées sans remplacement-en-place — `garde_injection.SOURCES_SURES`), par le
    # MÊME chemin que le bouton « Injecter » / le cron (`lancer_ingestion_source`). La cohérence de nuit +
    # le résumé du matin contrôlent le résultat. Une source de classe A sans commande mappée reste listée
    # « à câbler » — jamais injectée à l'aveugle.
    #
    # INJECTION-SOLIDE-3 — la voie « héritée » (injecter par le chemin direct sous le seul filet de la
    # cohérence du lendemain) DISPARAÎT : une source de classe A avancée qui n'est PAS sûre n'est PLUS
    # injectée. Elle remonte comme DÉCISION À PRENDRE (`injection-a-decider`) — à router par
    # `injection_sure.remplacer_servie` puis à inscrire dans `SOURCES_SURES`. « Sur-protéger est bénin ».
    #
    # POURQUOI le câblage importe (TABLEAU-1) : 2 sources A (Population légale INSEE, OFB/APER) n'avaient
    # pas de ligne dans config/sources_ingestion.yaml → elles restaient « nouvelle version » à tort.
    from .api.dashboard import lancer_ingestion_source
    from .ingestion import garde_injection
    from . import ops_alertes
    injectees, en_echec, a_cabler, a_decider, deja = [], [], [], [], []
    injectees_sures = []
    for a in classe_a:
        nom = a["name"]
        if nom not in nouvelles:
            deja.append(nom)          # rien de neuf amont → rien à faire (idempotent)
            continue
        if not garde_injection.source_sur_chemin_sur(nom):
            a_decider.append(nom)     # non sûre → JAMAIS injectée seule ; décision à prendre (vetter + router)
            continue
        try:
            lance = lancer_ingestion_source(nom)
        except Exception as exc:  # noqa: BLE001 — un lancement raté n'arrête pas les autres sources
            en_echec.append(nom)
            log.warning("injection-nuit : lancement %r échoué (%s)", nom, exc)
            continue
        if lance is None:
            a_cabler.append(nom)      # sûre mais aucune commande connue → listée, jamais à l'aveugle
            continue
        injectees.append(nom)
        injectees_sures.append(nom)   # SOLIDE-3 : toute source injectée la nuit est sûre (par construction)
        # trace du lancement (idempotence : la sentinelle repassera « ok » après ingestion) — best-effort.
        try:
            db.execute(text(
                "UPDATE source_veille SET injection_lancee_at = now(), injection_vu = dernier_vu "
                "WHERE source_id = (SELECT id FROM data_sources WHERE name = :n)"), {"n": nom})
        except Exception as exc:  # noqa: BLE001
            log.warning("injection-nuit : trace injection_lancee_at %r impossible (%s)", nom, exc)
    # INJECTION-SOLIDE-3 — les sources A avancées NON sûres : alerte CLAIRE « décision à prendre » (non
    # urgente). Elles ne s'injectent plus seules tant qu'elles ne passent pas par l'injection sûre ; leur
    # veille reste « nouvelle version » (elles reviennent jusqu'à ce qu'on les route). Sinon, on résout.
    try:
        if a_decider:
            ops_alertes.signaler(
                db, "injection-a-decider",
                f"{len(a_decider)} source(s) de classe A non sécurisée(s) — décision à prendre",
                "Ces sources de classe A ont une nouvelle version amont mais NE sont PAS sur le chemin de "
                "l'injection sûre (staging + swap atomique + retour arrière) — elles ne s'injectent donc "
                "plus seules la nuit :\n  · " + "\n  · ".join(sorted(a_decider))
                + "\n\nRoute chacune par injection_sure.remplacer_servie, ajoute-la à "
                  "garde_injection.SOURCES_SURES, puis relance.", lien="/admin/sources")
        else:
            ops_alertes.resoudre(db, "injection-a-decider")
    except Exception as exc:  # noqa: BLE001 — la transparence ne doit pas casser l'injection
        log.warning("injection-nuit : alerte « à décider » impossible (%s)", exc)
    ctx.compte(classe_a=len(classe_a), classe_b=len(classe_b),
               nouvelles_a=len(injectees) + len(en_echec) + len(a_cabler) + len(a_decider),
               injectees=injectees, injectees_sures=injectees_sures, en_echec=en_echec,
               a_cabler=a_cabler, a_decider=sorted(a_decider),
               attente_b=sorted(b["name"] for b in classe_b if b["name"] in nouvelles),
               note="classe A avancée : injectée seule UNIQUEMENT si sûre (injection_sure / sans "
                    "remplacement-en-place) ; non sûre → décision à prendre ; sans commande → « à câbler ». "
                    "La voie « héritée » a disparu (INJECTION-SOLIDE-3).")


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
    # AUTONOMIE-1 — RESTAURATION DE CONTRÔLE, RÉSULTAT ENREGISTRÉ ET VISIBLE. On écrit TOUJOURS le
    # marqueur `.restore-test.json` (lu par la vigie `restore-test-ancien` + le Tableau de bord) : le
    # contrôle de lisibilité (pg_restore --list) est désormais tracé côté serveur, l'incident
    # « jamais enregistré » se ferme donc de lui-même. Le VRAI test (restauration réelle dans une BASE
    # À PART du VPS + comparaison des comptes) tourne via deploy/scripts/restore_test_base.sh quand
    # LABUSE_RESTORE_TEST_REEL=1 et que le disque le permet — sinon ce contrôle de lisibilité tient lieu
    # de preuve enregistrée (honnête : le marqueur dit lequel des deux a été joué).
    reel = os.environ.get("LABUSE_RESTORE_TEST_REEL") == "1"
    statut, message, tables, duree_s = "ok", f"lisibilité OK ({n_objets} objets TOC)", None, None
    if reel:
        try:
            tables, duree_s = _restauration_reelle_base_a_part(dump)
            message = f"restauration réelle dans base à part OK ({tables} tables)"
        except Exception as exc:  # noqa: BLE001 — l'échec de la restauration réelle = marqueur KO (visible)
            statut, message = "ko", f"restauration réelle échouée : {str(exc)[:300]}"
    _ecrire_marqueur_restore(dump, taille_mo, n_objets, statut, message, tables, duree_s)
    if statut == "ko":
        raise RuntimeError(message)
    ctx.compte(dump=dump.name, taille_mo=taille_mo, objets_toc=n_objets, statut=statut,
               reel=reel, tables=tables, note="contrôle enregistré dans .restore-test.json (visible)")


def _ecrire_marqueur_restore(dump: Path, taille_mo: float, n_objets: int, statut: str,
                             message: str, tables, duree_s) -> None:
    """Écrit `.restore-test.json` dans backup_dir (même esprit que le Mac : un FICHIER lu par la vigie +
    le Tableau de bord, indépendant de tout code servi). Jamais bloquant."""
    import json as _json
    s = get_settings()
    try:
        p = Path(s.backup_dir) / ".restore-test.json"
        p.write_text(_json.dumps({
            "test_at": datetime.now(timezone.utc).isoformat(), "statut": statut, "message": message,
            "dump": dump.name, "taille_mo": taille_mo, "objets_toc": n_objets,
            "tables": tables, "duree_s": duree_s, "par": "restore-test (serveur)"},
            ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        log.warning("restore-test : marqueur non écrit (%s)", exc)


def _restauration_reelle_base_a_part(dump: Path) -> tuple[int, float]:
    """Restaure le dump dans une BASE À PART (`labuse_restore_ctrl`), compte ses tables, puis la
    DÉTRUIT. Garde-disque : refuse si l'espace libre < 4× la taille du dump. Retourne (n_tables, durée_s).
    Délègue au script prod `deploy/scripts/restore_test_base.sh` (createdb/pg_restore/dropdb)."""
    import time
    s = get_settings()
    libre = shutil.disk_usage(s.backup_dir).free
    besoin = dump.stat().st_size * 4
    if libre < besoin:
        raise RuntimeError(f"disque insuffisant pour une restauration réelle "
                           f"({round(libre/1e9,1)} Go libres < {round(besoin/1e9,1)} Go requis)")
    script = Path(__file__).resolve().parents[2] / "deploy" / "scripts" / "restore_test_base.sh"
    if not script.is_file():
        raise RuntimeError(f"script de restauration de contrôle introuvable : {script}")
    env = dict(os.environ)
    env["LABUSE_RESTORE_DUMP"] = str(dump)
    if s.pg_bin_dir:
        env["PATH"] = f"{s.pg_bin_dir}:{env.get('PATH', '')}"
    t0 = time.monotonic()
    proc = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, check=False)
    duree = round(time.monotonic() - t0, 1)
    if proc.returncode != 0:
        raise RuntimeError(f"restore_test_base.sh code {proc.returncode} : {(proc.stderr or proc.stdout)[-300:]}")
    tables = None
    for ligne in (proc.stdout or "").splitlines():
        if ligne.strip().startswith("TABLES="):
            tables = int(ligne.split("=", 1)[1].strip())
    return tables or 0, duree


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
    # SILENCE-1 (point 5) — G8 est un AVERTISSEMENT non bloquant (VERROUS_AVERTISSEMENT, source unique) :
    # il ne doit PLUS s'écrire « échec » dans le journal chaque matin, ni ouvrir une notification « verrous
    # cassés ». On sépare les vrais cassés (bloquants) des avertissements : le résultat journalisé est
    # « echec » seulement s'il reste un cassé BLOQUANT, « avertissement » s'il n'y a que des avertissements
    # (G8), « ok » sinon. Le détail porte `avertissements` à part de `casses` pour que le Résumé et le front
    # les distinguent (le front colore « avertissement » en ambre, jamais en rouge).
    from .circuit_resume import VERROUS_AVERTISSEMENT
    casses_tous = [r.id for r in resultats if r.verdict == "casse"]
    casses = [c for c in casses_tous if c not in VERROUS_AVERTISSEMENT]
    avertissements = [c for c in casses_tous if c in VERROUS_AVERTISSEMENT]
    resultat = "echec" if casses else ("avertissement" if avertissements else "ok")
    circuit_journal.journaliser(
        ctx.db, "controle", "verrous", "cron", resultat,
        {"joues": len(resultats), "casses": casses, "avertissements": avertissements,
         "a_decider": [r.id for r in resultats if r.verdict == "a_decider"],
         "preuves": {r.id: r.preuve for r in resultats}})
    ctx.compte(verrous_joues=len(resultats), verrous_casses=len(casses),
               verrous_avertissements=len(avertissements))
    if casses:   # SILENCE-1 : seuls les cassés BLOQUANTS sonnent (G8 n'ouvre plus de notification)
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
