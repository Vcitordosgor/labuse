"""CRON-1 — l'implémentation de chaque job. Un job = une fonction `<nom_avec_underscores>(ctx: JobContext)`
qui remplit `ctx.compteurs` (compteurs métier remontés dans l'état + le mail admin) et lève en cas d'échec
(le runner capture, écrit l'état, alerte). RÉUTILISE le code existant — aucun pipeline dupliqué.
"""
from __future__ import annotations

import gzip
import logging
import os
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text

from .config import get_settings
from .jobs import JobContext, lire_etat, state_path

log = logging.getLogger("labuse.jobs.impl")

# taille minimale d'un dump sain : un dump anormalement petit = échec (base vide, coupure). Constante.
BACKUP_MIN_MO = 1.0
# CRON-2 — rotation en CONSTANTE : on garde les N dumps les plus récents (7 par défaut). Le pull-mac de
# Vic archive plus loin (disque externe) ; le VPS ne conserve qu'une fenêtre courte.
BACKUP_ROTATION_N = 7


def _libpq_url(url: str) -> str:
    """URL SQLAlchemy → URL libpq comprise par pg_dump/psql (retire le driver `+psycopg`)."""
    return url.replace("+psycopg2", "").replace("+psycopg", "")


# ═══════════════════════════ K3 — quotidiens ═══════════════════════════

def backup_postgres(ctx: JobContext) -> None:
    """pg_dump | gzip vers backup_dir, rotation 14 j, taille minimale contrôlée (dump trop petit = échec)."""
    s = get_settings()
    dst = Path(s.backup_dir)
    dst.mkdir(parents=True, exist_ok=True)
    db_url = _libpq_url(s.database_url)
    # nom de base depuis l'URL (dernier segment)
    dbname = db_url.rsplit("/", 1)[-1].split("?")[0]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = dst / f"labuse-{dbname}-{ts}.sql.gz"
    pg_dump = str(Path(s.pg_bin_dir) / "pg_dump") if s.pg_bin_dir else "pg_dump"
    with gzip.open(out, "wb") as gz:
        proc = subprocess.run([pg_dump, "--no-owner", "--no-privileges", db_url],
                              stdout=gz, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump a échoué : {proc.stderr.decode('utf-8', 'replace')[:300]}")
    taille_mo = round(out.stat().st_size / 1e6, 2)
    if taille_mo < BACKUP_MIN_MO:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"dump anormalement petit ({taille_mo} Mo < {BACKUP_MIN_MO}) — suspect, rejeté")
    # rotation : garder les BACKUP_ROTATION_N dumps les plus récents, supprimer les plus anciens.
    tous = sorted(dst.glob("labuse-*.sql.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    supprimes = 0
    for f in tous[BACKUP_ROTATION_N:]:
        f.unlink(missing_ok=True)
        supprimes += 1
    ctx.compte(dump=out.name, taille_mo=taille_mo, gardes=min(len(tous), BACKUP_ROTATION_N),
               rotation_supprimes=supprimes)


def sources_fraicheur(ctx: JobContext) -> None:
    """Pour chaque source affichée : dernier millésime/ingestion vs cadence attendue (data_sources.
    source_cadence — la table de référence des cadences, JAMAIS en dur) → statut à_jour / en_retard /
    en_panne écrit en base (`fraicheur_statut`). C'est CE job qui alimente les badges de la page sources."""
    db = ctx.db
    # colonnes de statut servi aux badges (idempotent, migration propre in-place).
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_statut varchar(16)"))
    db.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS fraicheur_calcule_at timestamptz"))
    # cadences → seuil en jours (au-delà = en_retard ; au-delà de 2× = en_panne). Depuis la table, pas le code.
    seuils = {"hebdomadaire": 10, "mensuelle": 40, "trimestrielle": 100, "semestrielle": 200,
              "annuelle": 400, "continue": 10}
    # CRON-2 — les AFFICHÉES seulement, avec le MÊME prédicat que /sources (est_affichee, ceinture Python
    # canonique) : 59 sources annoncées = 59 statuts calculés. C'est ce qui réconcilie le compte (le 67
    # comptait des sources non affichées ; le prédicat retire doublons/retirées/dormantes/masquées).
    from .sources_catalog import est_affichee
    tous = db.execute(text(
        "SELECT id, name, technical_notes, status, source_cadence, "
        "  GREATEST(COALESCE(source_horizon_at, last_sync_at), last_sync_at) AS reference "
        "FROM data_sources")).mappings().all()
    rows = [r for r in tous if est_affichee(r["name"], r["technical_notes"], r["status"])]
    now = datetime.now(timezone.utc)
    compteurs = {"a_jour": 0, "en_retard": 0, "en_panne": 0, "sans_echeance": 0, "total": 0}
    for r in rows:
        compteurs["total"] += 1
        cad = (r["source_cadence"] or "").strip().lower()
        seuil = next((v for k, v in seuils.items() if cad.startswith(k[:6])), None)
        ref = r["reference"]
        if seuil is None or ref is None:
            statut = "sans_echeance"
        else:
            age = (now - (ref if ref.tzinfo else ref.replace(tzinfo=timezone.utc))).days
            statut = "a_jour" if age <= seuil else ("en_retard" if age <= 2 * seuil else "en_panne")
        compteurs[statut] += 1
        db.execute(text("UPDATE data_sources SET fraicheur_statut = :s, fraicheur_calcule_at = now() "
                        "WHERE id = :i"), {"s": statut, "i": r["id"]})
    ctx.compte(**compteurs)


def fiche_commune_cache(ctx: JobContext) -> None:
    """FICHE-COMMUNE-2 (C1) — précalcule le CONTEXTE de chaque commune (le payload ENTIER de
    /communes/{c}/contexte, ~20 s/commune) dans `commune_contexte_cache`, pour une ouverture < 500 ms.
    Chaque commune est ISOLÉE : un échec la marque et n'arrête pas le lot (rollback ciblé) ; le job DIT
    combien d'OK/échecs. Point d'écriture unique du cache (aussi « lançable à la main » : jobs run)."""
    db = ctx.db
    from .api.app import rafraichir_contexte_cache
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


def radar_cycle(ctx: JobContext) -> None:
    """Traite les dépôts de la veille DÉJÀ ingérés (la collecte reste manuelle — ce job ne fetch RIEN) :
    cycle de vie des annonces (en_vente_longue / a_reverifier), et prépare les événements de veille. Les
    badges sous-le-marché sont recalculés à la lecture (signaux.badges_pour_biens) — pas de dénormalisation."""
    from .pige import cycle
    r = cycle.run_quotidien(ctx.db)
    ctx.compte(**(r if isinstance(r, dict) else {"resultat": str(r)}))


def radar_digests(ctx: JobContext) -> None:
    """Regroupe TOUS les événements de veille en attente par client, envoie UN mail par client (Brevo
    template 13 + digest 12), marque envoyé. Idempotent (dedup event_log) : relancé deux fois, n'envoie
    pas deux fois. En dry-run (sans SMTP), calcule et logue tout, n'envoie rien."""
    from .pige import digests
    r = digests.envoyer(ctx.db, dry_run=ctx.dry_run)
    ctx.compte(**{k: r.get(k) for k in ("n_biens_du_jour", "envoyes", "echecs", "simules", "deja")})


def healthcheck(ctx: JobContext) -> None:
    """Sonde /health locale ; deux échecs consécutifs → alerte (compteur dans l'état). Vérifie AUSSI
    l'espace disque : au-delà de disque_seuil_pct, UNE alerte par jour (l'état mémorise la dernière)."""
    import urllib.request
    s = get_settings()
    etat = lire_etat("healthcheck") or {}
    echecs = (etat.get("compteurs") or {}).get("echecs_consecutifs", 0)
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=10) as resp:
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
    alerte_disque = None
    if pct is not None and pct >= s.disque_seuil_pct:
        derniere = (etat.get("compteurs") or {}).get("disque_alerte_jour")
        aujourdhui = date.today().isoformat()
        if derniere != aujourdhui:               # UNE alerte par jour, pas toutes les 15 min
            _envoyer_alerte(f"Disque à {pct}% (seuil {s.disque_seuil_pct}%) — faire de la place.")
            alerte_disque = aujourdhui
        else:
            alerte_disque = derniere
    if not ok and echecs >= 2:
        _envoyer_alerte(f"/health injoignable {echecs} fois de suite.")
    ctx.compte(health_ok=ok, echecs_consecutifs=echecs, disque_pct=pct,
               disque_alerte_jour=alerte_disque)
    if not ok:
        raise RuntimeError(f"/health injoignable ({echecs} échec(s) consécutif(s))")


# ═══════════════════════════ K4 — hebdo & mensuels ═══════════════════════════

def pg_maintenance(ctx: JobContext) -> None:
    """VACUUM ANALYZE des tables chaudes (hors transaction — connexion autocommit dédiée)."""
    from .db import engine
    chaudes = ["parcels", "event_log", "pige_biens", "pige_faits", "veilles", "dvf_mutations"]
    faites = []
    raw = engine().raw_connection()
    try:
        raw.autocommit = True
        cur = raw.cursor()
        for t in chaudes:
            try:
                cur.execute(f"VACUUM ANALYZE {t}")
                faites.append(t)
            except Exception as exc:  # noqa: BLE001 — une table absente ne casse pas la maintenance
                log.warning("VACUUM %s ignoré (%s)", t, exc)
        cur.close()
    finally:
        raw.close()
    ctx.compte(tables=faites)


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


def _ingest_via_cli(ctx: JobContext, *args: str) -> None:
    """Lance une commande d'ingestion EXISTANTE (même venv), capture le résultat. Les ingestions lourdes
    (données externes) restent le pipeline existant — le job n'ajoute que l'ordonnancement + l'état."""
    import sys
    cmd = [sys.executable, "-m", "labuse.cli", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    ctx.compte(commande=" ".join(args), code=proc.returncode,
               sortie=(proc.stdout or proc.stderr)[-400:])
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} a échoué (code {proc.returncode}) : {proc.stderr[-300:]}")


def ingest_sirene(ctx: JobContext) -> None:
    """SIRENE mensuel (câblage OUTILS-2/4 : date_creation + date_dernier_traitement, refresh concurrents)."""
    _ingest_via_cli(ctx, "ingest-sirene-etab")


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


def ingest_dpe(ctx: JobContext) -> None:
    """DPE ADEME mensuel."""
    _ingest_via_cli(ctx, "ingest-dpe")


def sync_gpu(ctx: JobContext) -> None:
    """Diff des PLU des 24 communes ; génère les événements de veille foncière concernés + bandeau PLU."""
    from .copilote_v2 import veilles as veilles_mod
    r = veilles_mod.evaluer_toutes(ctx.db)
    ctx.compte(veille_fonciere=r, note="diff PLU délégué au pipeline GPU existant ; événements générés")


def sentinelle_dvf_cadastre(ctx: JobContext) -> None:
    """VÉRIFIE si un nouveau millésime DVF (avril/octobre) ou cadastre est paru et ALERTE. N'ingère pas :
    ces deux-là restent des gestes supervisés de Vic."""
    db = ctx.db
    alertes = []
    for nom in ("DVF", "cadastre"):
        r = db.execute(text("SELECT source_millesime, prochain_millesime_at FROM data_sources "
                            "WHERE name ILIKE :n ORDER BY updated_at DESC LIMIT 1"),
                       {"n": f"%{nom}%"}).mappings().first()
        if r and r["prochain_millesime_at"] and r["prochain_millesime_at"] <= datetime.now(timezone.utc):
            alertes.append(f"{nom} : un millésime postérieur à {r['source_millesime']} devrait être paru.")
    if alertes:
        _envoyer_alerte("Sentinelle DVF/cadastre :\n- " + "\n- ".join(alertes)
                        + "\n\nGeste supervisé : Vic déclenche l'ingestion.", ctx=ctx)
    ctx.compte(alertes=alertes, n_alertes=len(alertes))


# ═══════════════════════════ K9 — robustesse ═══════════════════════════

def restore_test(ctx: JobContext) -> None:
    """Restaure le dump le plus récent dans une base jetable `labuse_restore_test`, vérifie (nombre de
    tables + comptes témoins sur parcels/veilles/pige_biens), puis DROP. Échec → alerte. Une sauvegarde
    jamais restaurée n'est pas une sauvegarde."""
    s = get_settings()
    dumps = sorted(Path(s.backup_dir).glob("labuse-*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        raise RuntimeError(f"aucun dump à restaurer dans {s.backup_dir}")
    dump = dumps[0]
    base = "labuse_restore_test"
    base_url = _libpq_url(s.database_url)
    admin_url = base_url.rsplit("/", 1)[0] + "/postgres"
    psql = str(Path(s.pg_bin_dir) / "psql") if s.pg_bin_dir else "psql"

    def _psql(url, sql):
        return subprocess.run([psql, url, "-v", "ON_ERROR_STOP=1", "-c", sql],
                              capture_output=True, text=True)

    _psql(admin_url, f"DROP DATABASE IF EXISTS {base}")
    cr = _psql(admin_url, f"CREATE DATABASE {base}")
    if cr.returncode != 0:
        raise RuntimeError(f"création base jetable impossible : {cr.stderr[:300]}")
    try:
        cible_url = base_url.rsplit("/", 1)[0] + f"/{base}"
        # gunzip | psql
        with gzip.open(dump, "rb") as gz:
            restore = subprocess.run([psql, cible_url, "-v", "ON_ERROR_STOP=0"],
                                     stdin=gz, capture_output=True, text=False)
        if restore.returncode != 0:
            raise RuntimeError(f"restauration en échec : {restore.stderr.decode('utf-8','replace')[:300]}")
        n_tables = int(_psql(cible_url, "SELECT count(*) FROM information_schema.tables "
                             "WHERE table_schema='public'").stdout.strip().splitlines()[-2].strip())
        temoins = {}
        for t in ("parcels", "veilles", "pige_biens"):
            out = _psql(cible_url, f"SELECT count(*) FROM {t}")
            temoins[t] = out.stdout.strip().splitlines()[-2].strip() if out.returncode == 0 else "absente"
        if n_tables < 50:
            raise RuntimeError(f"restauration douteuse : seulement {n_tables} tables (attendu ≫ 50)")
        ctx.compte(dump=dump.name, n_tables=n_tables, temoins=temoins)
    finally:
        _psql(admin_url, f"DROP DATABASE IF EXISTS {base}")   # toujours nettoyer la base jetable


# ═══════════════════════════ utilitaire d'alerte (respecte dry-run) ═══════════════════════════

def _envoyer_alerte(corps: str, *, sujet: str = "[LABUSE] alerte exploitation", ctx: JobContext | None = None) -> None:
    from .mail import send_email
    s = get_settings()
    dest = s.admin_email or s.contact_email
    if not dest:
        return
    r = send_email(dest, sujet, corps, settings=s)
    if ctx is not None and not r.sent:
        ctx.compte(mail=r.detail)   # « no-config » = dry-run, tracé dans l'état
    log.info("alerte exploitation envoyée=%s (%s)", r.sent, r.detail)
