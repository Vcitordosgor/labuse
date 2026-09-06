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


def sante_endpoints(ctx: JobContext) -> None:
    """CONNEXIONS-2 Lot 7.2 (N3) — sonde les endpoints MÉTIER (avec DB) et vérifie forme + non-vacuité.
    À la PREMIÈRE panne (dédup jour), notifie l'admin (event systeme). Le dashboard lit le même résultat
    via /admin/sante-endpoints. Ne teste PAS que le process vit (ça, c'est `healthcheck`) — teste que les
    ÉCRANS ont de quoi s'afficher (le cas `/accueil/chiffres` vivant mais vide)."""
    from .api import sante
    res = sante.sonde_metier(ctx.db)
    en_echec = [e["endpoint"] for e in res["endpoints"] if not e["ok"]]
    ctx.compte(ok=res["ok"], total=len(res["endpoints"]), en_echec=en_echec or None)
    if not res["ok"]:
        from datetime import date as _date
        from .api.events import creer_notification
        detail = " · ".join(f"{e['endpoint']} : {e['detail']}"
                            for e in res["endpoints"] if not e["ok"])
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Sonde endpoints",
            titre=f"Endpoints métier en échec ({len(en_echec)})", detail=detail[:500],
            dedup=f"sante_endpoints:{_date.today().isoformat()}")
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
        from datetime import date as _date
        from .api.events import creer_notification
        detail = " · ".join(f"{c['libelle']} : {c['detail']}" for c in res["checks"] if not c["ok"])
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Cohérence run",
            titre=f"Garde de cohérence : {len(en_echec)} divergence(s)", detail=detail[:500],
            lien="/admin", dedup=f"coherence_run:{_date.today().isoformat()}")
        ctx.db.commit()
        raise RuntimeError(f"garde de cohérence : {len(en_echec)} divergence(s) ({', '.join(en_echec)})")


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


def ingest_bdnb(ctx: JobContext) -> None:
    """SCORING-3 (L3) — BDNB trimestriel : stream de l'export national (~39 Go), filtre 974,
    tables bdnb_* + couverture parcelle mesurée. Idempotent par millésime (skip si déjà ingéré).
    N'inscrit AUCUNE variable au modèle : les candidates passent au banc K0 d'abord (L3.2)."""
    _ingest_via_cli(ctx, "ingest-bdnb")


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


def sentinelle_dvf_cadastre(ctx: JobContext) -> None:
    """SUPERSÉDÉ par `sentinelle_sources` (SENTINELLE-1 W2) — conservé pour le test de NON-RÉGRESSION :
    l'ancienne heuristique DATE (prochain_millesime_at échu) est comparée au nouveau passage réel.
    N'est plus enregistré au registre des jobs ; ne tourne plus en production."""
    db = ctx.db
    alertes = []
    for nom in ("DVF", "cadastre"):
        r = db.execute(text("SELECT source_millesime, prochain_millesime_at FROM data_sources "
                            "WHERE name ILIKE :n ORDER BY updated_at DESC LIMIT 1"),
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


def coherence_robinets(ctx: JobContext) -> None:
    """CIRCUIT-1 lot 4 — LA SONDE « Vérifier que tout coule » : chiffres à ≥ 2 robinets mesurés
    sur les témoins (écarts → circuit_ecarts, statut soldé conservé) + eau ancienne par tampon
    (circuit_eau_ancienne) + verdict (circuit_controles, lu par la page Circuit). Une fuite
    OUVERTE notifie l'admin (dédup jour). Tourne la nuit, après chaque bascule, et au bouton."""
    from .sonde_circuit import controle
    res = controle(ctx.db, declencheur="cron")
    ctx.compte(**{k: v for k, v in res.items() if isinstance(v, (int, float))})
    if res.get("fuites_ouvertes") or res.get("eau_ancienne_ouverte"):
        from datetime import date as _date
        from .api.events import creer_notification
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Circuit",
            titre=f"Sonde du circuit : {res.get('fuites_ouvertes', 0)} fuite(s) ouverte(s), "
                  f"{res.get('eau_ancienne_ouverte', 0)} eau(x) ancienne(s)",
            detail="Détail dans circuit_ecarts / circuit_eau_ancienne (page Circuit).",
            lien="/admin", dedup=f"coherence_robinets:{_date.today().isoformat()}")


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
        from datetime import date as _date
        from .api.events import creer_notification
        creer_notification(
            ctx.db, kind="systeme", compte_id=None, source="Circuit",
            titre=f"Filtre de nuit : {n_quar} source(s) en quarantaine",
            detail="Sources en quarantaine : " + ", ".join(nouveaux_quarantaine)
                   + " (page Circuit — « servir quand même » ou corriger la source).",
            lien="/admin", dedup=f"filtres_sources:{_date.today().isoformat()}")


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
