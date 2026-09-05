"""CLI LA BUSE (`labuse ...`).

    labuse init-db                 # schéma PostGIS
    labuse seed-sources            # catalogue de sources (§6)
    labuse seed-demo               # jeu de démo Saint-Paul (synthétique)
    labuse evaluate [--commune] [--ai]   # cascade + scoring (offre A/B)
    labuse discover [--commune]    # vue Découverte : survivantes classées (offre B)
    labuse sources                 # page Sources de données (statut connecteurs)
    labuse test-source "<nom>"     # bouton « tester la connexion »
    labuse api                     # FastAPI (uvicorn)
"""
from __future__ import annotations

import typer
from sqlalchemy import select, text

from . import models
from .brand import MINT as _MINT  # vert de marque — source unique (config/brand_colors.json)
from .config import get_settings
from .db import engine, ensure_postgis, session_scope

app = typer.Typer(add_completion=False, help="LABUSE — radar foncier intelligent de La Réunion.")


def _resolve_commune(commune: str | None) -> str | None:
    """Résout une entrée commune (nom OU INSEE) vers le NOM stocké en base.

    Les parcelles sont indexées par NOM de commune (Parcel.commune). Un INSEE passé brut ne
    matcherait aucune parcelle → 0 résultat silencieux (bug historique cli.py). On résout donc
    tout INSEE (pilote OU non-pilote) via le référentiel des 24 communes avant de renvoyer.
    """
    s = get_settings()
    if commune is None:
        return s.pilot_commune_name
    if commune == s.pilot_commune_insee:
        return s.pilot_commune_name
    # Entrée ressemblant à un INSEE (5 chiffres) : résoudre vers le nom officiel si connu.
    if commune.isdigit() and len(commune) == 5:
        nom = _commune_nom(commune)
        if nom is not None:
            return nom
    return commune


def _commune_nom(insee: str) -> str | None:
    """Nom officiel d'une commune depuis son INSEE (référentiel des 24 communes)."""
    from . import communes
    return next((n for n, e in communes.load_communes().items()
                 if str(e.get("insee")) == str(insee)), None)


def _parcel_ids(session, commune: str | None) -> list[int]:
    stmt = select(models.Parcel.id).order_by(models.Parcel.idu)
    if commune:
        stmt = stmt.where(models.Parcel.commune == commune)
    return [r[0] for r in session.execute(stmt).all()]


def _fail_zero_parcel(session, raw: str | None, resolved: str | None) -> None:
    """Échec BRUYANT quand une commune résout à 0 parcelle — JAMAIS un succès vide silencieux.

    Distingue « base vide » (aucune parcelle du tout → lancer l'ingestion) de « commune inconnue
    en base » (résolution INSEE probablement échouée : l'entrée n'a pas matché un nom stocké)."""
    total = session.execute(select(models.Parcel.id).limit(1)).first()
    if total is None:
        typer.echo("Aucune parcelle ingérée en base. Lancer `labuse seed-demo` ou `labuse ingest-real`.")
        raise typer.Exit(1)
    hint = ""
    if raw and str(raw).isdigit():
        hint = (f" — INSEE « {raw} » résolu en « {resolved} » : résolution probablement échouée "
                f"(commune non ingérée, ou INSEE hors des 24 communes de La Réunion).")
    typer.echo(f"✗ Commune « {resolved} » → 0 parcelle en base{hint}")
    raise typer.Exit(1)


def _parcels_bbox(session) -> tuple[float, float, float, float]:
    """Emprise (minlon, minlat, maxlon, maxlat) des parcelles ingérées."""
    row = session.execute(
        text("SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) "
             "FROM (SELECT ST_Extent(geom) AS e FROM parcels) t")
    ).one()
    return (float(row[0]), float(row[1]), float(row[2]), float(row[3]))


@app.command("init-db")
def init_db() -> None:
    """Crée l'extension PostGIS et toutes les tables."""
    ensure_postgis()
    models.create_all(engine())
    typer.echo("✓ Schéma PostGIS prêt.")


@app.command("suggestions")
def suggestions_cmd(nouvelles: bool = typer.Option(False, "--nouvelles", help="Seulement les non traitées")) -> None:
    """M16-C : lit les retours « Proposer une amélioration » envoyés depuis le menu compte."""
    with session_scope() as s:
        where = " WHERE statut = 'nouveau'" if nouvelles else ""
        rows = s.execute(text(
            "SELECT id, created_at::date AS d, categorie, compte_mode, statut, texte"
            f" FROM suggestions{where} ORDER BY id DESC")).mappings().all()
    if not rows:
        typer.echo("Aucune suggestion.")
        return
    for r in rows:
        typer.echo(f"#{r['id']} [{r['d']}] {r['categorie']}/{r['compte_mode']} ({r['statut']}) — {r['texte']}")
    typer.echo(f"\n{len(rows)} suggestion(s).")


@app.command("avis-echeance")
def avis_echeance_cmd() -> None:
    """NEUTRALISÉE (décision Vic 27/08/2026 — abonnement mensuel SANS engagement).

    L'avis d'échéance de la loi Chatel (art. L. 215-1) encadre les contrats à DURÉE DÉTERMINÉE
    reconductibles ; Intégral étant désormais mensuel sans engagement, il est SANS OBJET. La
    commande ne déclenche plus rien et son cron a été retiré (deploy/cron.d/avis-echeance).
    Conservée en no-op explicite pour ne pas casser un appel historique."""
    typer.echo("↷ avis-echeance : SANS OBJET (abonnement mensuel sans engagement — loi Chatel non "
               "applicable). Rien à déclencher, aucun e-mail envoyé.")


@app.command("mail-test")
def mail_test_cmd(destinataire: str = typer.Argument(..., help="Adresse e-mail de vérification")) -> None:
    """M21-A : envoie un e-mail de test — prouve que la config SMTP marche. À lancer après avoir
    rempli le .env (VPS). N'affiche ni ne logue JAMAIS le mot de passe."""
    from .config import get_settings
    from .mail import mail_configured, send_email

    s = get_settings()
    if not mail_configured(s):
        typer.echo("⚠ SMTP non configuré (LABUSE_SMTP_HOST absent) — le mail sera journalisé, PAS envoyé.")
    r = send_email(
        destinataire,
        "LABUSE — test d'envoi",
        "Ceci est un e-mail de test envoyé par LABUSE.\n\n"
        "Si vous le recevez, le transport SMTP est opérationnel.\n\n— LABUSE",
        settings=s,
    )
    if r.sent:
        typer.echo(f"✓ Mail envoyé à {destinataire} (expéditeur : {s.mail_from}).")
    elif r.detail == "no-config":
        typer.echo("• Mail journalisé (SMTP non configuré) — rien n'a été envoyé (comportement dev honnête).")
    else:
        typer.echo(f"✗ Échec d'envoi : {r.detail} (voir les logs pour la cause).")
        raise typer.Exit(1)


@app.command("seed-sources")
def seed_sources_cmd() -> None:
    from .ingestion import seed_sources

    with session_scope() as s:
        n = seed_sources.seed(s)
    typer.echo(f"✓ Catalogue de sources : {n} sources.")


@app.command("transport-reseaux")
def transport_reseaux_cmd() -> None:
    """M106 P4 — ingère transport public (7 GTFS PAN), pôles d'échange (OSM + dérivés GTFS,
    concordance dite), téléphérique Papang (OSM, en service seul) et lignes HT (BD TOPO).
    Versionné (IngestionRun) ; geom_2975 backfillée ensuite pour les distances."""
    from . import models
    from .ingestion.transport_reseaux import run_m106

    with session_scope() as s:
        run_m106(s, log_fn=typer.echo)
    models.ensure_geom_2975(engine())
    typer.echo("✓ geom_2975 backfillée (distances prêtes)")


@app.command("territoire-fiscal")
def territoire_fiscal_cmd() -> None:
    """M106 P3 — charge le seed des dispositifs fiscaux territoriaux (ZFANG / FRR ex-ZRR,
    attributs de COMMUNE, patron M95). Aucun chiffre fiscal en base : des états sourcés."""
    from .territoire_fiscal import load_territoire_fiscal

    with session_scope() as s:
        typer.echo(f"✓ territoire fiscal (ZFANG/FRR) : {load_territoire_fiscal(s)}")


@app.command("dispositifs-build")
def dispositifs_build_cmd() -> None:
    """M134 — matérialise la couche « Dispositifs » dans spatial_layers : buffer TVA 500 m
    (dérivé des QPV) + aplats commune ZFANG/FRR. QPV et NPNRU/ANRU sont déjà en base."""
    from .ingestion.dispositifs import build_all

    with session_scope() as s:
        build_all(s, log=typer.echo)


@app.command("vefa-neuf-build")
def vefa_neuf_build_cmd() -> None:
    """SECTEUR-2 (T4) — (re)matérialise la couche « Prix du logement neuf (VEFA) » dans spatial_layers :
    médiane €/m² bâti des ventes VEFA actées (geo-DVF), aplat COMMUNE, seuil 10 ventes (sinon absente).
    ECLN écartée (métropole seule, N/A DOM) → aucun stock. Idempotent."""
    from .ingestion.vefa_neuf import build_vefa_neuf

    with session_scope() as s:
        r = build_vefa_neuf(s, log=typer.echo)
        typer.echo(f"vefa_neuf : {r['communes']} communes peintes, {r['absentes']} sous le seuil.")


@app.command("ingest-cosia")
def ingest_cosia_cmd(extract_dir: str = typer.Option(None, help="Dossier des tuiles .gpkg CoSIA "
                     "(défaut : data/cosia/extract/COSIA_*)")) -> None:
    """PAU-CoSIA — ingère les footprints bâti CoSIA (IGN, D974 2025) dans spatial_layers
    kind='batiment_cosia'. Source GÉOMÉTRIQUE canonique du recalcul PAU (RNU). Idempotent.
    Prérequis : lot .7z téléchargé + extrait (cf. docs/mandats/PAU_COSIA_PHASE2_BLOCAGE.md)."""
    from .ingestion.cosia import build_cosia_batiment

    with session_scope() as s:
        r = build_cosia_batiment(s, extract_dir=extract_dir, log=typer.echo)
    typer.echo(f"✓ CoSIA bâtiment : {r['inserted']} polygones, {r['communes_tagged']} tagués "
               f"commune, {r['tiles']} tuiles — {r['source_millesime']}")


@app.command("znieff-build")
def znieff_build_cmd() -> None:
    """M137-U — ingère les ZNIEFF continentales (type I + II) de La Réunion → spatial_layers
    kind='znieff' (INPN via Géoplateforme WFS, Licence Ouverte). Marines exclues. Contrainte hors cascade."""
    from . import models
    from .db import engine
    from .ingestion import seed_sources
    from .ingestion.znieff import build_znieff

    with session_scope() as s:
        seed_sources.seed(s)                                     # crée/actualise la source INPN/MNHN
        # M137-U — purge l'ancienne ligne Région ODS renommée (doublon amputé) si elle traîne.
        s.execute(text("DELETE FROM data_sources WHERE name = 'ZNIEFF (INPN / Région)' "
                       "AND NOT EXISTS (SELECT 1 FROM spatial_layers sl "
                       "                WHERE sl.data_source_id = data_sources.id)"))
        counts = build_znieff(s, log=typer.echo)
    models.ensure_geom_2975(engine())                            # remplit geom_2975 (intersections servitudes)
    typer.echo(f"✓ ZNIEFF : {counts} (total {sum(counts.values())})")


@app.command("bpe-build")
def bpe_build_cmd() -> None:
    """M137-U — ingère la BPE INSEE (équipements géolocalisés, DEP=974) → spatial_layers
    kind='amenite_bpe' (Licence Ouverte, millésime 2025). Couche DISTINCTE d'OSM."""
    from . import models
    from .db import engine
    from .ingestion import seed_sources
    from .ingestion.bpe import build_bpe

    with session_scope() as s:
        seed_sources.seed(s)
        counts = build_bpe(s, log=typer.echo)
    models.ensure_geom_2975(engine())
    typer.echo(f"✓ BPE 974 : {counts} (total {sum(counts.values())})")


@app.command("ingest-trafic-rn")
def ingest_trafic_rn_cmd() -> None:
    """ZONE-DONNÉES LOT 5 — ingère le trafic moyen journalier annuel des routes nationales (Région
    Réunion, open data ODS) → table `trafic_rn`. Trafic VÉHICULES sur RN (pas de flux piéton)."""
    from .ingestion import seed_sources
    from .ingestion.trafic_rn import build_trafic_rn
    with session_scope() as s:
        seed_sources.seed(s)
        r = build_trafic_rn(s, log=typer.echo)
    typer.echo(f"✓ Trafic RN : {r['n']} tronçons ({r['annees'][0] if r['annees'] else '—'}–{r['annees'][-1] if r['annees'] else '—'})")


@app.command("ingest-sirene-etab")
def ingest_sirene_etab_cmd(
    geo_url: str = typer.Option(None, "--geo-url", help="parquet géo INSEE (défaut : dernier data.gouv)"),
    stock_url: str = typer.Option(None, "--stock-url", help="parquet StockEtablissement (défaut : dernier)"),
) -> None:
    """ZONE-DONNÉES LOT 1 — ingère les établissements SIRENE actifs géolocalisés (974) via DuckDB
    (fichier géo INSEE × StockEtablissement, parquet distant, jointure sur SIRET). Cron MENSUEL Réunion.
    Statut de diffusion respecté (les non-'O' n'ont ni nom ni adresse en clair)."""
    from . import models
    from .db import engine
    from .ingestion import seed_sources
    from .ingestion.sirene_etablissements import build_sirene_etablissements

    with session_scope() as s:
        seed_sources.seed(s)
        r = build_sirene_etablissements(s, geo_url=geo_url, stock_url=stock_url, log=typer.echo)
    models.ensure_geom_2975(engine())
    typer.echo(f"✓ SIRENE établissements 974 : {r['n']} ({r['n_diffusion_partielle']} en diffusion "
               f"partielle) · millésime {r['millesime']}")


@app.command("ingest-mobpro")
def ingest_mobpro_cmd(file: str = typer.Option(..., "--file", help="CSV MOBPRO (INSEE)"),
                      millesime: str = typer.Option("MOBPRO INSEE", "--millesime")) -> None:
    """ÉTUDE DE ZONE Z1 — ingère MOBPRO (emplois au lieu de travail, maille commune 974)."""
    from .ingestion import seed_sources
    from .ingestion.mobpro import build_mobpro

    with session_scope() as s:
        seed_sources.seed(s)
        r = build_mobpro(s, file=file, millesime=millesime, log=typer.echo)
    typer.echo(f"✓ MOBPRO 974 : {r['n_communes']} communes")


@app.command("entites-acronymes")
def entites_acronymes_cmd() -> None:
    """M110 — (re)charge le référentiel des acronymes de personnes morales (SIDR, SHLMR…) depuis
    le seed versionné data/entites/acronymes_moraux.csv. Le Copilote l'auto-sème à la 1re demande ;
    cette commande force le rechargement (SIREN vérifiés en base)."""
    from sqlalchemy import text as _text

    from .copilote_v2.outils import _ensure_acronymes
    with session_scope() as s:
        s.execute(_text("DELETE FROM entite_acronyme"))   # force le rechargement depuis le CSV
        s.commit()
        _ensure_acronymes(s)
        n = s.execute(_text("SELECT count(*) FROM entite_acronyme")).scalar()
    typer.echo(f"✓ Référentiel acronymes : {n} entrées (SIDR, SHLMR, SAFER, SODIAC, SEMADER…).")


@app.command("backfill-sources")
def backfill_sources_cmd() -> None:
    """M-H — seed le catalogue (crée les sources manquantes) puis rattache les couches
    spatial_layers HISTORIQUES sans data_source_id à leur source, et affiche la garde."""
    from .bascule_gardes import check_sources_declarees
    from .ingestion import layers_ingest, seed_sources

    with session_scope() as s:
        n = seed_sources.seed(s)
        rattaches = layers_ingest.backfill_layer_sources(s)
        s.commit()
        typer.echo(f"✓ Catalogue : {n} sources. Backfill : {rattaches or 'rien à rattacher'}.")
        check_sources_declarees(session=s)


@app.command("bilan-calibrate")
def bilan_calibrate_cmd(
    csv_path: str = typer.Argument("config/bilan_calibration_vic.csv",
                                   help="Gabarit CSV rempli (colonnes secteur,param,valeur,source)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Prévisualise sans rien écrire en base."),
) -> None:
    """Injecte les valeurs de bilan saisies dans le gabarit CSV (par secteur, upsert, sans toucher
    aux lignes vides). Une valeur saisie n'est plus « estimée » → le bandeau « à affiner » tombe."""
    from pathlib import Path

    from .faisabilite import bilan_params as bp

    if not Path(csv_path).exists():
        typer.echo(f"Fichier introuvable : {csv_path}")
        raise typer.Exit(1)
    rows = bp.read_calibration_csv(csv_path)
    if not rows:
        typer.echo("Aucune valeur à injecter (toutes les lignes « valeur » sont vides).")
        raise typer.Exit(0)
    with session_scope() as s:
        res = bp.apply_calibration(s, rows, dry_run=dry_run)
        if dry_run:
            s.rollback()
    for a in res["applied"]:
        typer.echo(f"  {a['secteur']:24} {a['param']:34} → {a['value']:g}  "
                   f"[{a['provenance'] or 'saisie'}{(' · ' + a['source']) if a['source'] else ''}]")
    for secteur, param, msg in res["errors"]:
        typer.echo(f"  ⚠ {secteur or '?'} / {param or '?'} : {msg}")
    mode = "PRÉVISUALISÉ (rien écrit)" if dry_run else "injecté(s) en base"
    typer.echo(f"✓ {len(res['applied'])} valeur(s) {mode} · {len(res['errors'])} erreur(s).")


@app.command("bilan-params-perimes")
def bilan_params_perimes_cmd(
    jours: int = typer.Option(30, "--jours", help="Âge au-delà duquel une estimée non confirmée est signalée."),
) -> None:
    """Liste les params de bilan de provenance « estimée » jamais confirmés depuis plus de N jours
    (verrou anti-« provisoire devenu permanent », décision Vic 28/07/2026 — cas du 2100).
    Code retour 1 si au moins un paramètre est signalé (utilisable en contrôle automatique)."""
    from .faisabilite import bilan_params as bp

    with session_scope() as s:
        rows = bp.estimees_non_confirmees(s, jours=jours)
    if not rows:
        typer.echo(f"✓ Aucune valeur estimée non confirmée depuis plus de {jours} jours.")
        raise typer.Exit(0)
    for r in rows:
        typer.echo(f"  ⚠ {r['secteur']:24} {r['param']:34} = {r['value']:g}  "
                   f"({r['age_jours']} j) — {r['libelle']}")
    typer.echo(f"{len(rows)} estimée(s) non confirmée(s) > {jours} j — à confirmer via le gabarit "
               "config/bilan_calibration_vic.csv (labuse bilan-calibrate) ou à supprimer.")
    raise typer.Exit(1)


@app.command("seed-demo")
def seed_demo_cmd() -> None:
    from .ingestion import demo_saint_paul, seed_sources

    s = get_settings()
    with session_scope() as session:
        seed_sources.seed(session)
        info = demo_saint_paul.seed_demo(session, s.pilot_commune_insee, s.pilot_commune_name)
    typer.echo(f"✓ Démo {s.pilot_commune_name} : {info['parcels']} parcelles (synthétiques).")


@app.command("ingest-real")
def ingest_real_cmd(
    commune: str = typer.Option(None, help="INSEE (défaut = pilote 97415)."),
    bbox: str = typer.Option(None, help="Sous-ensemble borné « minlon,minlat,maxlon,maxlat » (4326)."),
    limit: int = typer.Option(None, help="Cap du nombre de parcelles (après bbox) — passage borné."),
    reset: bool = typer.Option(True, help="Vide les tables avant ingestion."),
) -> None:
    """Ingestion RÉELLE : cadastre bulk Etalab + couches structurantes live (remplace la démo)."""
    from .ingestion.cadastre_ingest import ingest_parcels
    from .ingestion import cadastre_bulk, demo_saint_paul, layers_ingest, seed_sources
    from .models import IngestionRun

    s = get_settings()
    insee = commune or s.pilot_commune_insee
    commune_name = s.pilot_commune_name if insee == s.pilot_commune_insee else insee
    bb = None
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            typer.echo("bbox attendu : minlon,minlat,maxlon,maxlat")
            raise typer.Exit(1)
        bb = (parts[0], parts[1], parts[2], parts[3])

    typer.echo(f"Téléchargement cadastre bulk {insee}…")
    parcels = cadastre_bulk.parse_etalab(cadastre_bulk.download_parcelles(insee))
    total = len(parcels)
    parcels = cadastre_bulk.filter_bbox(parcels, bb)
    if limit:
        parcels = parcels[:limit]
    typer.echo(f"  {total} parcelles au total ; {len(parcels)} retenues (bbox/limit).")
    if not parcels:
        typer.echo("Aucune parcelle retenue — vérifier le bbox.")
        raise typer.Exit(1)

    with session_scope() as session:
        seed_sources.seed(session)
        if reset:
            demo_saint_paul.reset_demo(session)
        run = IngestionRun(commune=commune_name, status="running", parcels_count=len(parcels))
        session.add(run)
        session.flush()
        n = ingest_parcels(session, parcels, commune_name, run.id)
        typer.echo(f"✓ {n} parcelles ingérées (géométrie 4326, surface 2975).")
        layer_bbox = bb or _parcels_bbox(session)
        counts = layers_ingest.ingest_layers(session, insee, commune_name, layer_bbox, run.id)
        run.status = "ok"
    # Hors transaction : geom_2975 valide (ST_MakeValid) + index GIST sur parcelles & couches
    # (dont l'assiette PPR, dont la géométrie GPU peut être auto-sécante).
    models.ensure_geom_2975(engine())
    typer.echo("✓ Couches structurantes (kind : nombre) :")
    for k, v in counts.items():
        typer.echo(f"    {k:18} : {v}")


def _fmt_layers(counts: dict) -> str:
    return ", ".join(f"{k}:{v}" for k, v in counts.items()) or "—"


@app.command("ingest-island")
def ingest_island_cmd(
    only: str = typer.Option(None, help="INSEE ou noms (séparés par virgule) ; défaut = les 24."),
    force: bool = typer.Option(False, help="Réingère même les communes déjà « ok »."),
    limit: int = typer.Option(None, help="Cap de parcelles par commune (tests)."),
    spacing: float = typer.Option(4.0, help="Pause (s) entre communes — politesse API."),
) -> None:
    """Ingestion + évaluation des 24 communes, EN SÉRIE et REPRENABLE.

    Reprise : saute les communes déjà « ok », ne ré-évalue que celles « ingested »,
    (re)fait celles en erreur / jamais tentées. Chaque commune est committée seule :
    un arrêt ne reperd jamais le travail déjà fait.
    """
    import time

    from .ingestion import run_all, seed_sources

    targets = run_all.REUNION_COMMUNES
    if only:
        wanted = {x.strip() for x in only.split(",")}
        targets = [(i, n) for (i, n) in targets if i in wanted or n in wanted]
    if not targets:
        typer.echo("Aucune commune ciblée (vérifier --only).")
        raise typer.Exit(1)

    with session_scope() as s:
        seed_sources.seed(s)  # idempotent

    ok: list[tuple] = []
    failed: list[tuple] = []
    skipped: list[str] = []
    t_all = time.monotonic()

    for k, (insee, name) in enumerate(targets, 1):
        with session_scope() as s:
            st = run_all.run_status(s, name)
        if st == "ok" and not force:
            typer.echo(f"  [{k}/{len(targets)}] {name} ({insee}) — déjà OK, saute.")
            skipped.append(name)
            continue
        t0 = time.monotonic()
        typer.echo(f"▶ [{k}/{len(targets)}] {name} ({insee}) …")
        try:
            if st == "ingested" and not force:
                models.ensure_geom_2975(engine())                # geom_2975 valide+indexée avant cascade
                with session_scope() as s:                       # parcelles déjà là → ré-évaluation
                    nev = run_all.evaluate_commune(s, name)
                info = {"parcels": "(déjà ingérées)", "layers": {}}
            else:
                with session_scope() as s:                       # phase A (commit)
                    info = run_all.ingest_commune(s, insee, name, limit=limit)
                # Hors transaction (anti-deadlock) : trigger ST_MakeValid + reprojection 2975 +
                # réparation des géométries invalides (ex. assiette PPR auto-sécante) + index GIST.
                models.ensure_geom_2975(engine())
                with session_scope() as s:                       # phase B (commit) → ok
                    nev = run_all.evaluate_commune(s, name)
            dt = time.monotonic() - t0
            plu = (info.get("layers") or {}).get("plu_gpu_zone", "?")
            typer.echo(f"  ✓ {name} : {info['parcels']} parcelles · PLU={plu} · {nev} évaluées · {dt:.0f}s")
            typer.echo(f"      couches : {_fmt_layers(info.get('layers') or {})}")
            ok.append((name, nev, dt))
        except Exception as exc:  # noqa: BLE001 - on isole la commune, on continue
            dt = time.monotonic() - t0
            typer.echo(f"  ✗ {name} : ÉCHEC {type(exc).__name__}: {exc} ({dt:.0f}s)")
            failed.append((name, f"{type(exc).__name__}: {exc}", dt))
        time.sleep(spacing)

    with session_scope() as s:
        total_p = s.execute(text("SELECT count(*) FROM parcels")).scalar()
        communes_db = s.execute(text("SELECT count(DISTINCT commune) FROM parcels")).scalar()

    dt_all = time.monotonic() - t_all
    typer.echo("\n" + "═" * 60)
    typer.echo(f"BILAN — {len(ok)} OK · {len(failed)} échec(s) · {len(skipped)} sauté(s) · {dt_all:.0f}s")
    for name, nev, dt in ok:
        typer.echo(f"  ✓ {name:24} {nev:>7} évaluées  ({dt:.0f}s)")
    for name, err, dt in failed:
        typer.echo(f"  ✗ {name:24} {err}")
    typer.echo(f"TOTAL EN BASE : {total_p} parcelles sur {communes_db} commune(s).")


@app.command("evaluate")
def evaluate_cmd(
    commune: str = typer.Option(None, help="Commune (nom ou INSEE ; défaut = pilote)."),
    ai: bool = typer.Option(False, "--ai", help="Active l'agent IA (provider configuré)."),
) -> None:
    """Fait tourner la cascade + le scoring et persiste les évaluations."""
    from .ai import get_provider
    from .cascade import evaluate_parcels

    raw = commune
    commune = _resolve_commune(commune)
    provider = get_provider() if ai else None
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
        if not ids:
            _fail_zero_parcel(session, raw, commune)
        outcomes = evaluate_parcels(ids, session, persist=True, ai_provider=provider)

    from collections import Counter

    counts = Counter(o.status for o in outcomes)
    typer.echo(f"✓ {len(outcomes)} parcelles évaluées ({commune}).")
    for status, n in counts.most_common():
        typer.echo(f"    {status:24} : {n}")


@app.command("dryrun-evaluate")
def dryrun_evaluate_cmd(
    label: str = typer.Option(..., help="run_label du calcul à blanc (baseline/etape1/etape2/etape3)."),
    commune: str = typer.Option("97415", help="Commune (défaut = 97415 Saint-Paul, périmètre dry-run)."),
    chunk: int = typer.Option(2000, help="Commit + progression tous les N parcelles."),
    resume: bool = typer.Option(True, help="Sauter les parcelles déjà calculées pour ce label."),
) -> None:
    """DRY-RUN étages 1+2 : cascade + scoring écrits dans les tables PARALLÈLES dryrun_* — n'écrase
    NI parcel_evaluations NI cascade_results live. Chunké/résumable, progression visible."""
    import time

    from .cascade import evaluate_parcels
    from .cascade.cablage import check_cablage_scoring

    nom = _resolve_commune(commune)
    t0 = time.time()
    with session_scope() as s:
        # M-B : garde de câblage COMPLÈTE (statique + kinds spatiaux en base) au lancement du run —
        # la part DB (~1,2 s) est ici, pas au boot de l'API. Bloquante, nomme le fautif.
        check_cablage_scoring(session=s)
        ids = _parcel_ids(s, nom)
        if not ids:
            _fail_zero_parcel(s, commune, nom)
        done: set[int] = set()
        if resume:
            done = {r[0] for r in s.execute(
                text("SELECT parcel_id FROM dryrun_parcel_evaluations WHERE run_label=:r"),
                {"r": label}).all()}
        todo = [i for i in ids if i not in done]
        typer.echo(f"DRY-RUN [{label}] {nom} : {len(ids)} parcelles, {len(done)} déjà faites, "
                   f"{len(todo)} à évaluer à blanc.")
        if not todo:
            typer.echo("✓ Rien à faire.")
            return
        n = 0
        for k in range(0, len(todo), chunk):
            part = todo[k:k + chunk]
            evaluate_parcels(part, s, persist=True, dryrun_label=label)
            s.commit()
            s.expunge_all()   # conso mémoire plate sur 51k parcelles
            n += len(part)
            typer.echo(f"  … {n}/{len(todo)} ({time.time() - t0:.0f}s)")
    typer.echo(f"✓ DRY-RUN [{label}] {nom} : {len(todo)} parcelles évaluées à blanc (tables dryrun_*).")


@app.command("flux-run")
def flux_run_cmd(
    label: str = typer.Option(..., help="run_label du run à calculer (ex. q_v12_flux)."),
    resume: bool = typer.Option(True, help="Reprend un run interrompu (saute les parcelles déjà faites)."),
    recette: str = typer.Option("m36", help="Recette du scoring : m36 (servie) ou q_v12 "
                                            "(SCORING-3 L1 — artefact gelé qv12, calculé jamais basculé)."),
) -> None:
    """FLUX-1 (F2.2) — LANCE UN RUN COMPLET comme la production, en CHAÎNANT les étapes EXISTANTES
    (aucune réécriture du pipeline) : cascade (dryrun-evaluate) sur les 24 communes, puis scoring/tiers
    (score-v2) sous le MÊME label. Le run ENREGISTRE sa photo des sources+millésimes (F2.2). Progression
    visible (une ligne par commune + le scoring). N'est PAS servi : la bascule reste un geste manuel
    (`labuse golden promote <label>` ou le bouton admin de la page Flux)."""
    import os
    import time

    from . import run_progress
    from .cascade import evaluate_parcels
    from .cascade.cablage import check_cablage_scoring
    from .ingestion.run_all import REUNION_COMMUNES
    from .scoring.p_v2.pipeline import run_score_v2

    t0 = time.time()
    # DONNEES-2 (B3) — le run écrit sa PROGRESSION dans un fichier lu par l'API (barre + %, étape 2).
    # `total` = 24 communes (cascade) + 1 pas de scoring. L'API a pu ouvrir l'état au lancement ; on le
    # (ré)ouvre ici avec NOTRE pid (celui du process détaché) — c'est celui que « Arrêter » signalera.
    total = len(REUNION_COMMUNES) + 1
    run_progress.start(label, pid=os.getpid(), kind="run", recette=recette, total=total,
                       log=f"/tmp/labuse-flux-run-{label}.log")
    with session_scope() as s:
        check_cablage_scoring(session=s)     # garde de câblage AVANT de démarrer (bloquante, nomme le fautif)
    # 1 — CASCADE par commune (tables dryrun_*), reprenable.
    for i, (insee, _) in enumerate(REUNION_COMMUNES):
        nom = _resolve_commune(insee)
        # DONNEES-2 (B3) — annonce la commune EN COURS de traitement AVANT de la calculer (une grosse
        # commune prend du temps ; sinon la barre resterait « démarrage » plusieurs minutes).
        run_progress.progress(label, phase="cascade", commune=nom, done=i, total=total,
                              pct=round(i / total * 100))
        with session_scope() as s:
            ids = _parcel_ids(s, nom)
            if not ids:
                typer.echo(f"  · {nom} ({insee}) : 0 parcelle, ignorée")
                run_progress.progress(label, phase="cascade", commune=nom, done=i + 1,
                                      total=total, pct=round((i + 1) / total * 100))
                continue
            done: set[int] = set()
            if resume:
                done = {r[0] for r in s.execute(text(
                    "SELECT parcel_id FROM dryrun_parcel_evaluations WHERE run_label=:r"), {"r": label}).all()}
            todo = [i2 for i2 in ids if i2 not in done]
            for k in range(0, len(todo), 2000):
                evaluate_parcels(todo[k:k + 2000], s, persist=True, dryrun_label=label)
                s.commit()
                s.expunge_all()
            typer.echo(f"  ✓ {nom} : {len(todo)} évaluées ({time.time() - t0:.0f}s)")
        run_progress.progress(label, phase="cascade", commune=nom, done=i + 1, total=total,
                              pct=round((i + 1) / total * 100))
    # 2 — SCORING / tiers sous le MÊME label (enregistre les sources+millésimes, F2.2).
    run_progress.progress(label, phase="scoring", commune=None, done=len(REUNION_COMMUNES),
                          total=total, pct=round(len(REUNION_COMMUNES) / total * 100))
    with session_scope() as s:
        res = run_score_v2(s, run_id=label, rebuild=True, snapshot=True, recette=recette)
    run_progress.finish(label, n_parcelles=res["n"])
    typer.echo(f"✓ FLUX-RUN [{label}] : {res['n']} parcelles scorées, tiers {res['tiers']} "
               f"({time.time() - t0:.0f}s total). NON servi — bascule manuelle.")


#: M80 — tables run-scoped connues qui portent une colonne run_id/run_label (découvertes en base au
#: lancement ; cette liste sert de repli/documentation). Le cycle de vie d'un run est ATOMIQUE :
#: un run se crée et se PURGE dans TOUTES ces tables ensemble (défaut #1 du RAPPORT_M80).
def _tables_run_scoped(session) -> list[tuple[str, str]]:
    # M80 — uniquement les colonnes TEXTE : les runs de SCORING sont des labels 'q_*' (text). Les
    # colonnes run_id de type UUID (agent_events/agent_run_parcels) sont des runs d'AGENT, hors périmètre.
    rows = session.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND column_name IN ('run_id','run_label') "
        "AND data_type IN ('character varying','text','character') ORDER BY table_name")).all()
    return [(r[0], r[1]) for r in rows]


def _runs_a_garder(session) -> set[str]:
    """RÈGLE DE RÉTENTION M80 : garder le SERVI + le PRÉCÉDENT (les deux points de vérité versionnés,
    served_run.txt + run_precedent.txt) + TOUT run encore RÉFÉRENCÉ (lignée, exceptions, démo). Un run
    référencé n'est jamais purgé."""
    from . import runs
    from .scoring.lignee_tete import CHAINE_GESTES
    from .scoring.score_v_constants import RUN_PRECEDENT
    keep = {runs.current(), RUN_PRECEDENT, "q_v2_demo"}         # servi + précédent + démo vivante
    for a, b, *_ in CHAINE_GESTES:                              # lignée (lignee_tete lit leur donnée)
        keep.update({a, b})
    keep.update(r[0] for r in session.execute(                 # exceptions de service encore posées
        text("SELECT DISTINCT run_id FROM served_run_exceptions")).all() if r[0])
    return keep


@app.command("purge-runs-morts")
def purge_runs_morts_cmd(
    apply: bool = typer.Option(False, "--apply", help="Exécute la purge (défaut : dry-run, rien supprimé)."),
    vacuum: bool = typer.Option(True, help="VACUUM FULL après purge — VERROU EXCLUSIF, app à l'arrêt."),
) -> None:
    """M80 — RÈGLE DE RÉTENTION appelée À LA BASCULE de run (jamais un cron indépendant).

    Garde le SERVI + le PRÉCÉDENT + tout run RÉFÉRENCÉ (lignée/exceptions/démo) ; purge le reste de
    façon ATOMIQUE (toutes les tables run-scoped ensemble — un run ne vit jamais à moitié). Dry-run par
    défaut. `--apply` supprime puis VACUUM FULL (app arrêtée). Jamais le run servi, jamais un référencé."""
    with session_scope() as s:
        tables = _tables_run_scoped(s)
        keep = _runs_a_garder(s)
        present: set[str] = set()
        for t, c in tables:
            present.update(r[0] for r in s.execute(text(f"SELECT DISTINCT {c} FROM {t}")).all() if r[0])
        purgeables = sorted(present - keep)
        typer.echo(f"Tables run-scoped : {len(tables)} · runs présents : {len(present)} · à GARDER : "
                   f"{sorted(keep & present)}")
        if not purgeables:
            typer.echo("✓ Aucun run à purger (rétention déjà respectée).")
            return
        typer.echo(f"À PURGER ({len(purgeables)}) : {purgeables}")
        if not apply:
            typer.echo("Dry-run — rien supprimé. Relancer avec --apply (app arrêtée) pour exécuter.")
            return
        # Purge ATOMIQUE : chaque run retiré de TOUTES les tables dans la même transaction.
        touched: set[str] = set()
        for t, c in tables:
            n = s.execute(text(f"DELETE FROM {t} WHERE {c} = ANY(:r)"), {"r": purgeables}).rowcount
            if n:
                touched.add(t)
                typer.echo(f"  DELETE {t} : {n}")
        # CIRCUIT-1 lot 3.6 — la purge entre au journal unifié (geste humain, jamais un cron).
        from . import circuit_journal
        circuit_journal.journaliser(s, "purger", ",".join(purgeables), "cli", "ok",
                                    {"tables": sorted(touched)})
        s.commit()
    if vacuum and touched:
        typer.echo("VACUUM FULL (verrou exclusif) …")
        with engine().connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for t in sorted(touched):
                conn.execute(text(f"VACUUM FULL {t}"))
                typer.echo(f"  ✓ {t}")
    typer.echo(f"✓ Purge terminée : {len(purgeables)} run(s), {len(touched)} table(s).")


@app.command("dryrun-report")
def dryrun_report_cmd(
    label: str = typer.Option("baseline", help="run_label à lire."),
    commune: str = typer.Option("97415", help="Commune (défaut = 97415)."),
) -> None:
    """Livrable d'un run dry-run : distributions, top, UNKNOWN-ABF, contrôle de traçabilité."""
    import json

    from .scoring.dryrun import report

    nom = _resolve_commune(commune)
    with session_scope() as s:
        rep = report(s, label, nom)
    typer.echo(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


@app.command("matrice-simulate")
def matrice_simulate_cmd(
    # ANO-1 (M8a) : défaut = run SERVI (Q_A_RUN_LABEL), source unique — plus de « q_v2 » gelé en dur.
    label: str = typer.Option(None, help="run_label à simuler (défaut : run de référence Q_A_RUN_LABEL)."),
    candidates: str = typer.Option(
        "", help="Candidats « q:a » ou « q:a:acompl » séparés par des virgules "
                 "(défaut : balayage q∈{60..80} × a∈{55..70} autour de la convention courante)."),
) -> None:
    """SIMULATION À BLANC de conventions de matrice (aucune écriture persistante — table
    temporaire de session). Sortie : tableau console + grille HTML docs/tops_ile/
    matrice_sensibilite.html. La bascule événementielle n'est JAMAIS balayée (doctrine)."""
    from pathlib import Path

    from .api.tiles import RUN
    from .config import load_yaml_config
    from .scoring.dryrun import simulate_matrice

    label = label or RUN
    cur = load_yaml_config("scoring_matrice")["seuils"]
    if candidates.strip():
        cands = []
        for tok in candidates.split(","):
            parts = [int(x) for x in tok.strip().split(":")]
            cands.append({"q_chaude": parts[0], "a_chaude": parts[1],
                          "a_completude_min": parts[2] if len(parts) > 2 else cur["a_completude_min"]})
    else:
        cands = [{"q_chaude": q, "a_chaude": a} for q in (60, 65, 70, 75, 80) for a in (55, 60, 65, 70)]
    # la convention COURANTE d'abord (référence des deltas)
    cands = [{"q_chaude": cur["q_chaude"], "a_chaude": cur["a_chaude"],
              "a_completude_min": cur["a_completude_min"]}] + [
        c for c in cands if not (c["q_chaude"] == cur["q_chaude"] and c["a_chaude"] == cur["a_chaude"])]
    with session_scope() as s:
        rows = simulate_matrice(s, label, cands)
        s.rollback()   # ceinture ET bretelles : rien à committer, on annule même la temp
    ref = rows[0]
    typer.echo(f"{'q':>3} {'a':>3} {'acompl':>6} │ {'chaudes':>7} {'(matrice+évén.)':>15} "
               f"{'Δ vs cour.':>10} {'dossiers':>8} {'sans id.':>8} {'surveiller':>10}")
    for r in rows:
        cur_mark = " ◀ COURANTE" if r is ref else ""
        detail = f"{r['chaude_matrice']}+{r['chaude_evenement']}"
        typer.echo(f"{r['q_chaude']:>3} {r['a_chaude']:>3} {r.get('a_completude_min', 50):>6} │ "
                   f"{r['chaude']:>7} {detail:>15} "
                   f"{r['chaude'] - ref['chaude']:>+10} {r['dossiers']:>8} {r['chaudes_sans_identite']:>8} "
                   f"{r['a_surveiller']:>10}{cur_mark}")
    out = Path("docs/tops_ile/matrice_sensibilite.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_sensibilite_html(rows, cur), encoding="utf-8")
    typer.echo(f"✓ grille écrite : {out} (aucune écriture en base — simulation à blanc)")


def _sensibilite_html(rows: list[dict], cur: dict) -> str:
    """Grille de sensibilité — le support de la DÉCISION Vic (mandat 1.3/1.5)."""
    communes = sorted({c for r in rows for c in r["par_commune"]})
    css = ("body{font:13px -apple-system,sans-serif;background:#0b0f0d;color:#dce8e1;margin:24px}"
           "h1{font-size:18px;color:" + _MINT + "}h2{font-size:14px;color:#8FA69A;margin-top:28px}"
           "table{border-collapse:collapse;margin-top:10px}th{font:600 10px monospace;color:#8FA69A;"
           "padding:5px 8px;border-bottom:1px solid #2a352f;text-align:right}td{padding:5px 8px;"
           "border-bottom:1px solid #1a221e;text-align:right;font-family:monospace;font-size:12px}"
           "tr.cur{background:#0F1A14}tr.cur td{color:" + _MINT + ";font-weight:600}"
           ".muted{color:#5a6b62}.neg{color:#E8695A}.pos{color:#4ADE96}")
    ref = rows[0]
    main = "".join(
        f"<tr class='{'cur' if r is ref else ''}'>"
        f"<td>Q≥{r['q_chaude']} · A≥{r['a_chaude']} · compl≥{r.get('a_completude_min', 50)}</td>"
        f"<td>{r['chaude']}</td><td class='muted'>{r['chaude_matrice']} + {r['chaude_evenement']} évén.</td>"
        f"<td class='{'pos' if r['chaude'] >= ref['chaude'] else 'neg'}'>{r['chaude'] - ref['chaude']:+d}</td>"
        f"<td>{r['dossiers']}</td><td class='muted'>{r['chaudes_sans_identite']}</td>"
        f"<td>{r['a_surveiller']}</td><td>{r['a_creuser']}</td><td class='muted'>{r['ecartee']}</td></tr>"
        for r in rows)
    det = "".join(
        f"<tr class='{'cur' if r is ref else ''}'><td>Q≥{r['q_chaude']}·A≥{r['a_chaude']}</td>"
        + "".join(f"<td>{r['par_commune'].get(c, 0) or '·'}</td>" for c in communes) + "</tr>"
        for r in rows)
    return (f"<!doctype html><meta charset='utf-8'><title>Sensibilité matrice</title><style>{css}</style>"
            f"<h1>Grille de sensibilité — convention de matrice <span class='muted'>(simulation à blanc, run de référence)</span></h1>"
            f"<p class='muted'>Ligne verte = convention COURANTE (Q≥{cur['q_chaude']} · A≥{cur['a_chaude']} · compl≥{cur['a_completude_min']}). "
            f"Les chaudes « + N évén. » = bascule BODACC, doctrinale, insensible aux seuils. "
            f"Dossiers = propriétaires uniques (SIREN) parmi les chaudes ; « sans id. » = parcelles chaudes sans identité connue.</p>"
            f"<table><tr><th style='text-align:left'>CANDIDAT</th><th>CHAUDES</th><th>DONT (matrice+évén.)</th>"
            f"<th>Δ</th><th>DOSSIERS</th><th>SANS ID.</th><th>SURVEILLER</th><th>CREUSER</th><th>ÉCARTÉES</th></tr>{main}</table>"
            f"<h2>Chaudes par commune</h2><table><tr><th style='text-align:left'>CANDIDAT</th>"
            + "".join(f"<th>{c[:12]}</th>" for c in communes) + f"</tr>{det}</table>")


@app.command("matrice-apply")
def matrice_apply_cmd(
    # ANO-1 (M8a) : défaut aligné sur le run SERVI (Q_A_RUN_LABEL), source unique — « q_v2 » codé
    # en dur appliquait la convention (matrice ×24 + tuiles + tops) sur un run gelé ≠ run servi.
    label: str = typer.Option(None, help="run_label sur lequel appliquer la convention "
                                         "(défaut : run de référence Q_A_RUN_LABEL)."),
) -> None:
    """Applique la CONVENTION VERSIONNÉE (config/scoring_matrice.yaml) : matrice ×24 + tuiles
    MVT + tops HTML — idempotent, minutes. Le canari 97415000AC0253 (chaude PAR événement)
    stoppe tout s'il tombe."""
    import json as _json
    import subprocess
    import sys as _sys

    from .api.tiles import RUN
    from .scoring.dryrun import apply_convention

    label = label or RUN
    with session_scope() as s:
        out = apply_convention(s, label)
    typer.echo(_json.dumps(out, ensure_ascii=False, indent=1))
    r = subprocess.run([_sys.executable, "scripts/gen_tops_ile.py"], capture_output=True, text=True)
    typer.echo(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else f"✗ tops : {r.stderr[-300:]}")
    # 3.1 (train 5, Vic 04/08) : l'entonnoir se reconstruit avec la matrice — il était censé
    # l'être (« à reconstruire après chaque matrice ») et est mort en silence sur 2 bascules.
    from .scoring.dryrun import build_entonnoir
    with session_scope() as s:
        n_ent = build_entonnoir(s, label)
        s.commit()
    typer.echo(f"✓ entonnoir_motifs reconstruit ({n_ent} lignes).")
    typer.echo("✓ convention appliquée (matrice ×24 + MVT + tops + entonnoir).")


@app.command("build-mvt")
def build_mvt_cmd(
    # correctif M5 : défaut aligné sur le run SERVI (Q_A_RUN_LABEL) — « q_v2 » codé en dur
    # matérialisait la carte île sur un autre run que les fiches/listes.
    label: str = typer.Option(None, help="run_label dont matérialiser les tuiles "
                                         "(défaut : run de référence Q_A_RUN_LABEL)."),
) -> None:
    """(Re)construit la table `mvt_parcels` servie en tuiles vectorielles (carte île entière).
    À relancer après CHAQUE run de scoring — les tuiles lisent cette matérialisation, pas le run."""
    # M48 : le geste tuiles est un POINT UNIQUE (`rebuild_mvt_servies`), partagé avec les bascules
    # (« un geste = tout ou rien ») — le CLI n'en est qu'un mince appelant.
    import time as _t

    from sqlalchemy.exc import OperationalError

    from . import runs
    from .api.tiles import rebuild_mvt_servies

    # DONNEES-2 (B1) — défaut = run SERVI, lu VIVANT via runs.current() (l'ancien `from .api.tiles
    # import RUN` était cassé : `RUN` n'existe pas dans tiles → `build-mvt` levait ImportError).
    servi = runs.current()
    label = label or servi
    # DONNEES-2 (B1) — la reconstruction DROP/RENAME des tables servies prend un verrou EXCLUSIF qui
    # peut DEADLOCK avec les lectures de la garde de cohérence (l'admin poll /admin/flux). On borne
    # l'attente d'un verrou (lock_timeout) pour échouer VITE plutôt que d'entrer en deadlock, et on
    # RÉESSAIE le geste entier (transaction annulée → rien de partiel persisté). Lancé détaché par la
    # bascule ; en tâche isolée un `build-mvt` manuel garde le même comportement.
    res = None
    for tentative in range(3):
        try:
            with session_scope() as s:
                s.execute(text("SET lock_timeout = '30s'"))
                res = rebuild_mvt_servies(s, label, log=typer.echo)
            break
        except OperationalError as exc:
            if tentative == 2:
                raise
            typer.echo(f"⚠ verrou/deadlock (tentative {tentative + 1}/3) : {type(exc).__name__} — "
                       f"nouvelle tentative dans 6 s…")
            _t.sleep(6)
    if label != servi:
        typer.echo(f"⚠ ATTENTION : tuiles matérialisées sur « {label} » ≠ run servi « {servi} » "
                   f"— les fiches/listes et la carte raconteront deux mondes.")
    typer.echo(f"✓ mvt_parcels reconstruite : {res['n']} parcelles (label {label}).")


@app.command("dryrun-matrice")
def dryrun_matrice_cmd() -> None:
    """M129-B — LA MATRICE EST MORTE (dalle : elle fusionne dans la cascade). Le statut servi est
    celui de la CASCADE (dryrun_parcel_evaluations.status) ; la présentation est le tier v2.
    Cette commande refuse explicitement — jamais un no-op silencieux."""
    typer.echo("⛔ dryrun-matrice : la matrice est MORTE (M129) — le statut cascade + le tier v2 "
               "la remplacent. Rien n'a été calculé.")
    raise typer.Exit(2)


@app.command("ingest-permits")
def ingest_permits_cmd(
    refresh: bool = typer.Option(False, help="Delta mensuel (recouvrement 3 mois) au lieu du chargement complet."),
    geocode: bool = typer.Option(True, help="Géocoder les permis sans IDU après l'ingestion."),
) -> None:
    """Ingère les autorisations d'urbanisme SITADEL via la voie VIVANTE (flux national SDES/Dido,
    Sitadel3, dép. 974 entier, MAJ mensuelle). [Pré-vol M7 P1 : l'ancienne voie ODS Région est
    MORTE depuis 2023-09 (permits.py, legacy documenté) — cette commande appelait encore la morte.]"""
    from .ingestion import permits_sdes

    res = permits_sdes.run(refresh=refresh, geocode=geocode, log=typer.echo)
    typer.echo(f"✓ SITADEL (SDES/Dido) : {res}")


@app.command("geocode-permits")
def geocode_permits_cmd(commune: str = typer.Option(None, help="INSEE (défaut = pilote).")) -> None:
    """1.B-fix — géolocalise les permis SITADEL non géocodés via le cadastre (API Carto, par section)."""
    from .ingestion.permits import geocode_permits_via_cadastre

    insee = commune if (commune and commune.isdigit()) else get_settings().pilot_commune_insee
    with session_scope() as s:
        r = geocode_permits_via_cadastre(s, insee)
    typer.echo(f"✓ Permis géolocalisés : {r['avant']} → {r['apres']} (+{r['ajoutes']}) "
               f"via {r['sections_recuperees']} sections.")


@app.command("ingest-personnes-morales")
def ingest_pm_cmd(
    commune: str = typer.Option(None, help="INSEE (défaut = pilote 97415)."),
    csv: str = typer.Option(None, help="CSV départemental DGFiP déjà extrait (sinon téléchargé)."),
) -> None:
    """Charge les propriétaires PERSONNES MORALES (1.A — fichier DGFiP, Licence Ouverte)."""
    from .ingestion.personnes_morales import fetch_974_csv, ingest_personnes_morales

    insee = commune if (commune and commune.isdigit()) else get_settings().pilot_commune_insee
    path = csv or str(fetch_974_csv())
    with session_scope() as s:
        n = ingest_personnes_morales(s, path, insee=insee)
    typer.echo(f"✓ {n} parcelles de personnes morales chargées (DGFiP, INSEE {insee}).")


@app.command("ingest-inpi-rne")
def ingest_inpi_rne_cmd(
    commune: str = typer.Option(None, help="INSEE pour restreindre (défaut = île entière 974)."),
    throttle: float = typer.Option(0.5, help="Pause (s) entre requêtes SIREN (poli, anti-ban)."),
    chunk: int = typer.Option(100, help="Commit + log de progression tous les N SIREN (reprise)."),
    resume: bool = typer.Option(True, help="Sauter les SIREN déjà présents dans pm_dirigeants."),
) -> None:
    """Ingère les dirigeants RNE (Vague A3) des personnes morales foncières — signal âge dirigeant.

    SIREN-based (comme BODACC), depth-0. RÉSUMABLE (saute les déjà faits) et CHUNKÉ (commit +
    progression par lot) → un arrêt ne reperd rien. Identifiants en env INPI_API_* (jamais en dur).
    ⚠ Appels réseau + écriture : l'île entière ≈ 9 579 SIREN (~1 h 45). Ne touche PAS au score
    (# TODO étage 2)."""
    import time

    from .connectors.inpi_rne import InpiRneConnector, QuotaExceededError
    from .ingestion.inpi_rne import eligible_sirens, ingest_inpi_rne

    insee = commune if (commune and commune.isdigit()) else None
    conn = InpiRneConnector(throttle_s=throttle)
    with session_scope() as s:
        sirens = eligible_sirens(s, insee)
        done: set[str] = set()
        if resume:
            done = {r[0] for r in s.execute(text("SELECT DISTINCT siren FROM pm_dirigeants")).all()}
        todo = [x for x in sirens if x not in done]
        scope = f"INSEE {insee}" if insee else "île entière (974)"
        typer.echo(f"INPI RNE — {scope} : {len(sirens)} éligibles, {len(done)} déjà faits, "
                   f"{len(todo)} à traiter.")
        if not todo:
            typer.echo("✓ Rien à faire.")
            return
        t0 = time.time()
        tot_d = tot_h = 0
        done_global = 0
        try:
            for k in range(0, len(todo), chunk):
                part = todo[k:k + chunk]
                res = ingest_inpi_rne(s, part, connector=conn)
                s.commit()   # lot committé → reprise possible ; conso mémoire plate
                tot_d += res["dirigeants"]
                tot_h += res["sirens_with_dirigeant"]
                done_global = min(k + chunk, len(todo))
                typer.echo(f"  … {done_global}/{len(todo)} — +{res['dirigeants']} dirigeants "
                           f"(cumul {tot_d}, sirens_hit {tot_h}, {time.time() - t0:.0f}s)")
        except QuotaExceededError as exc:
            typer.echo(f"✗ QUOTA INPI ÉPUISÉ après {done_global}/{len(todo)} SIREN "
                       f"({tot_d} dirigeants écrits). Résumable : relancer plus tard (quota quotidien). "
                       f"Détail : {exc}")
            raise typer.Exit(1) from exc
    typer.echo(f"✓ INPI RNE : {tot_d} dirigeants, {tot_h} SIREN avec dirigeant.")


@app.command("ingest-inpi-gigogne")
def ingest_inpi_gigogne_cmd(
    commune: str = typer.Option(None, help="INSEE pour restreindre (défaut = île entière 974)."),
    throttle: float = typer.Option(0.5, help="Pause (s) entre requêtes gérant (poli, anti-ban)."),
    chunk: int = typer.Option(100, help="Commit + log de progression tous les N SIREN cibles."),
    resume: bool = typer.Option(True, help="Sauter les cibles déjà présentes dans pm_dirigeant_gigogne."),
) -> None:
    """DEPTH-1 (2ᵉ itération) : résout l'âge dirigeant des SIREN SANS dirigeant physique direct
    (age_source='aucun_individu') en suivant le gérant-société sur UN seul niveau.

    À jouer APRÈS la passe depth-0 (`ingest-inpi-rne`). RÉSUMABLE / CHUNKÉE. Bornée à 1 niveau,
    anti-cycle. Identifiants en env INPI_API_*. Ne touche PAS au score (# TODO étage 2)."""
    import time

    from .connectors.inpi_rne import InpiRneConnector, QuotaExceededError
    from .ingestion.inpi_rne import _gigogne_targets, resolve_gigogne

    # Point critique : la table pm_dirigeant_gigogne doit exister AVANT que la vue la référence.
    # On la crée (idempotent) PUIS on (re)construit la vue — jamais l'inverse.
    models.PmDirigeantGigogne.__table__.create(engine(), checkfirst=True)
    models.ensure_pm_propension_view(engine())

    insee = commune if (commune and commune.isdigit()) else None
    conn = InpiRneConnector(throttle_s=throttle)
    gerant_cache: dict = {}   # partagé entre lots : un gérant n'est requêté qu'une fois sur toute la passe
    with session_scope() as s:
        all_targets = _gigogne_targets(s, insee)
        done: set[str] = set()
        if resume:
            done = {r[0] for r in s.execute(
                text("SELECT DISTINCT siren FROM pm_dirigeant_gigogne")).all()}
        cibles = [c for c in all_targets if c not in done]
        scope = f"INSEE {insee}" if insee else "île entière (974)"
        typer.echo(f"INPI gigogne (depth-1) — {scope} : {len(all_targets)} cibles 'aucun_individu', "
                   f"{len(done)} déjà résolues, {len(cibles)} à traiter.")
        if not cibles:
            typer.echo("✓ Rien à faire.")
            return
        t0 = time.time()
        tot_d = tot_r = tot_e = 0
        done_global = 0

        def _progress(i, n, n_ind, n_err):
            # battement intra-lot : la commande n'est JAMAIS muette plus de ~10 cibles (incident 3h)
            typer.echo(f"      · lot {done_global + i}/{len(cibles)} — +{n_ind} physiques, "
                       f"{n_err} gérants injoignables ({time.time() - t0:.0f}s)")

        try:
            for k in range(0, len(cibles), chunk):
                sub = {c: all_targets[c] for c in cibles[k:k + chunk]}
                res = resolve_gigogne(s, connector=conn, targets=sub, throttle_s=throttle,
                                      gerant_cache=gerant_cache, progress=_progress)
                s.commit()
                tot_d += res["dirigeants_gigogne"]
                tot_r += res["cibles_resolues"]
                tot_e += res["erreurs_gerant"]
                done_global = min(k + chunk, len(cibles))
                typer.echo(f"  … {done_global}/{len(cibles)} — +{res['dirigeants_gigogne']} physiques "
                           f"(cibles résolues {tot_r}, erreurs {tot_e}, {time.time() - t0:.0f}s)")
        except QuotaExceededError as exc:
            # ÉCHEC EXPLICITE : quota INPI épuisé — on ne grince PAS 3h en silence.
            typer.echo(f"✗ QUOTA INPI ÉPUISÉ après {done_global}/{len(cibles)} cibles "
                       f"({tot_r} résolues, {tot_d} écrites). Réessayer plus tard (quota quotidien). "
                       f"Détail : {exc}")
            raise typer.Exit(1) from exc
    typer.echo(f"✓ INPI gigogne : {tot_r} cibles résolues, {tot_d} dirigeants physiques rattachés "
               f"({tot_e} gérants injoignables).")


@app.command("ingest-georisques")
def ingest_georisques_cmd(
    commune: str = typer.Option(None, help="INSEE d'une commune (défaut = les 24 communes)."),
    throttle: float = typer.Option(0.15, help="Pause (s) entre pages API (rate-limit ~1000/min)."),
    alea: bool = typer.Option(True, help="Compléter aussi les aléas DEAL (WFS) manquants."),
    force: bool = typer.Option(False, help="Ré-ingérer même les communes déjà faites."),
) -> None:
    """Vague B — couches Géorisques dans spatial_layers : sites/sols pollués, cavités, ICPE
    (API) + complétion des aléas DEAL (WFS). Une commune = une unité COMMITTÉE → résumable
    (saute les communes déjà faites sauf --force). Ne touche PAS au score (# TODO étage 1)."""
    import time

    from .connectors.georisques import GeorisquesConnector
    from .ingestion import fraicheur, georisques_layers, layers_ingest
    from .ingestion.run_all import REUNION_COMMUNES, _commune_bbox

    conn = GeorisquesConnector(throttle_s=throttle)
    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    api_kinds = list(georisques_layers.KIND_SOURCE)
    t0 = time.time()
    tot: dict[str, int] = {k: 0 for k in api_kinds}
    tot["georisque_alea"] = 0
    # M84 — trace ingestion_runs (running → ok | error) : un échec Géorisques devient VISIBLE (avant :
    # aucune trace). Session de trace dédiée ; chaque commune garde sa session committée isolément.
    with session_scope() as _trace, fraicheur.trace_ingestion(_trace, "974 (Géorisques)", fraicheur.DS_NAMES["georisques"]):
        for insee, nom in targets:
            with session_scope() as s:
                has_api = s.execute(text(
                    "SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind=ANY(:k)"),
                    {"c": nom, "k": api_kinds}).scalar()
                if has_api and not force:
                    typer.echo(f"  ⏭ {nom} : couches API déjà là ({has_api}), sauté.")
                else:
                    counts = georisques_layers.ingest_commune(s, insee, nom, connector=conn)
                    for k, v in counts.items():
                        tot[k] += v
                    typer.echo(f"  ✓ {nom} API : {counts}")
                if alea:
                    has_alea = s.execute(text(
                        "SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind='georisque_alea'"),
                        {"c": nom}).scalar()
                    if has_alea and not force:
                        typer.echo(f"     aléas déjà là ({has_alea}), sauté.")
                    else:
                        bbox = _commune_bbox(s, nom)
                        if bbox is None:
                            typer.echo(f"     ⚠ {nom} : pas de parcelles → bbox absente, aléas sautés.")
                        else:
                            sids = layers_ingest._source_ids(s)
                            s.execute(text("DELETE FROM spatial_layers WHERE commune=:c AND kind='georisque_alea'"),
                                      {"c": nom})
                            try:
                                n_al = layers_ingest.ingest_georisque_alea(s, bbox, nom, None, sids, insee)
                                tot["georisque_alea"] += n_al
                                typer.echo(f"     ✓ aléas DEAL : {n_al}")
                            except Exception as exc:  # noqa: BLE001 — une commune en échec ne bloque pas les autres
                                typer.echo(f"     ⚠ aléas {nom} en échec : {type(exc).__name__}: {exc}")
                s.commit()
    typer.echo(f"✓ Géorisques île : {tot} ({time.time() - t0:.0f}s)")


@app.command("ingest-cartofriches")
def ingest_cartofriches_cmd(
    commune: str = typer.Option(None, help="INSEE d'une commune (défaut = les 24 communes)."),
    throttle: float = typer.Option(0.15, help="Pause (s) entre appels (rate-limit non exposé)."),
    detail: bool = typer.Option(True, help="Enrichir chaque friche des 78 champs détail (1 appel/friche)."),
    force: bool = typer.Option(False, help="Ré-ingérer même les communes déjà faites."),
) -> None:
    """Vague C1 — friches Cartofriches (Cerema) → spatial_layers kind='friche'. Rattachement
    parcelle EXACT via refcad. Une commune = une unité committée → résumable (saute les faites
    sauf --force). Ne touche PAS au score (# TODO étage 1/2)."""
    import time

    from .connectors.cartofriches import CartofrichesConnector
    from .ingestion import cartofriches
    from .ingestion.run_all import REUNION_COMMUNES

    conn = CartofrichesConnector(throttle_s=throttle)
    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    t0 = time.time()
    total = 0
    for insee, nom in targets:
        with session_scope() as s:
            has = s.execute(text(
                "SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind='friche'"),
                {"c": nom}).scalar()
            if has and not force:
                typer.echo(f"  ⏭ {nom} : friches déjà là ({has}), sauté.")
                continue
            n = cartofriches.ingest_commune(s, insee, nom, connector=conn, with_detail=detail)
            s.commit()
            total += n
            typer.echo(f"  ✓ {nom} : {n} friches")
    typer.echo(f"✓ Cartofriches île : {total} friches ({time.time() - t0:.0f}s)")


@app.command("potentiel-backfill")
def potentiel_backfill_cmd(
    run: str = typer.Option(..., help="run_id du run à équiper (ex. q_v12)."),
) -> None:
    """SCORING-3 (L4) — calcule et stocke le POTENTIEL d'un run existant : SDP résiduelle,
    valeur créée (€, intervalle q1-q3 communal), indice d'opportunité (percentile communal de
    p × valeur), accès (PM/SIREN, courrier). Colonnes annexes — ni p_raw, ni rang, ni tier."""
    from .scoring.p_v2.potentiel import backfill_run
    with session_scope() as s:
        r = backfill_run(s, run)
        s.commit()
    typer.echo(f"✓ potentiel [{run}] : {r}")


@app.command("ingest-bdnb")
def ingest_bdnb_cmd(
    force: bool = typer.Option(False, help="Rejouer même si le millésime courant est déjà ingéré."),
) -> None:
    """SCORING-3 (L3) — BDNB (CSTB, Licence Ouverte) : année de construction, classe DPE, surfaces,
    usage PAR BÂTIMENT. L'amont ne publie que l'export France entier (~39 Go) : STREAME l'archive et
    ne garde que le 974 → tables bdnb_rel_parcelle / bdnb_ffo / bdnb_dpe / bdnb_bdtopo + couverture
    parcelle mesurée. Idempotent par millésime. Aucune variable au modèle sans banc K0 (L3.2)."""
    from .ingestion.bdnb import build_bdnb
    with session_scope() as s:
        r = build_bdnb(s, force=force, log=typer.echo)
        s.commit()
    typer.echo(f"✓ BDNB : {r}")


@app.command("ingest-dpe")
def ingest_dpe_cmd(
    commune: str = typer.Option(None, help="INSEE d'une commune (défaut = les 24 communes)."),
    throttle: float = typer.Option(0.1, help="Pause (s) entre appels."),
    force: bool = typer.Option(False, help="Ré-ingérer même les communes déjà faites."),
) -> None:
    """DPE ADEME (logements existants) → table dpe_records. Rattachement parcelle 100 % LOCAL
    (id_ban → adresses, point BAN EPSG:2975, adresse brute — le _geopoint ADEME est faux au 974).
    Une commune = une unité committée → résumable. Termine par la passe « orphelins » (CP brut
    974xx sans code_insee_ban). Ne touche PAS au score (recalcul Score V séparé)."""
    import time

    from .connectors.dpe import DpeConnector
    from .ingestion import dpe, fraicheur
    from .ingestion.run_all import REUNION_COMMUNES

    conn = DpeConnector(throttle_s=throttle)
    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    t0 = time.time()
    tot = {"dpe": 0, "geocodes": 0, "rattaches_parcelle": 0, "hors_reunion": 0}
    # M84 — trace ingestion_runs (running → ok | error) : un échec DPE devient VISIBLE (avant : aucune
    # trace → décrochage possible en silence). Session de trace dédiée ; les communes gardent la leur.
    # CIRCUIT-1 lot 0.3 — le saut des communes peuplées est un CHOIX EXPLICITE (rafraîchir = --force,
    # à la cadence du cron DPE) et le tampon ne ment plus : si AUCUNE commune n'a été interrogée
    # (tout sauté), `last_sync_at` reste INCHANGÉ (handle["tampon"]=False) — /healthz/crons ne peut
    # plus afficher « ok » sur un passage à vide.
    n_traitees = 0
    with session_scope() as _trace, fraicheur.trace_ingestion(
            _trace, "974 (DPE ADEME)", fraicheur.DS_NAMES["dpe"]) as _h:
        for insee, nom in targets:
            with session_scope() as s:
                has = s.execute(text("SELECT count(*) FROM dpe_records WHERE code_insee=:c"), {"c": insee}).scalar()
                if has and not force:
                    typer.echo(f"  ⏭ {nom} : DPE déjà là ({has}), sauté (ré-ingérer : --force).")
                    continue
                res = dpe.ingest_commune(s, insee, nom, connector=conn)
                s.commit()
                n_traitees += 1
                for k in tot:
                    tot[k] += res.get(k, 0)
                typer.echo(f"  ✓ {nom} : {res}")
        if not commune:
            with session_scope() as s:
                res = dpe.ingest_orphelins(s, connector=conn)
                s.commit()
                n_traitees += 1     # la passe orphelins interroge l'ADEME et upserte : traitement réel
                tot["dpe"] += res["dpe"]
                tot["rattaches_parcelle"] += res["rattaches_parcelle"]
                tot["hors_reunion"] += res.get("hors_reunion", 0)
                typer.echo(f"  ✓ orphelins (CP brut 974xx sans code_insee_ban) : {res}")
        _h["tampon"] = n_traitees > 0
        if not n_traitees:
            typer.echo("  ⓘ aucune commune interrogée (toutes déjà peuplées) — last_sync_at INCHANGÉ.")
    typer.echo(f"✓ DPE île : {tot} ({time.time() - t0:.0f}s)")
    if tot["hors_reunion"]:
        typer.echo(f"  ⓘ {tot['hors_reunion']} lignes métropolitaines écartées (géocodage BAN "
                   f"ADEME rabattu sur INSEE 974 — jugées sur le CP brut, cf. is_reunion_authentic).")


@app.command("ingest-mvt")
def ingest_mvt_cmd(
    commune: str = typer.Option(None, help="INSEE d'une commune (défaut = les 24 communes)."),
    throttle: float = typer.Option(0.15, help="Pause (s) entre pages."),
    force: bool = typer.Option(False, help="Ré-ingérer même les communes déjà faites."),
) -> None:
    """Bonus Vague C2 — mouvements de terrain Géorisques /mvt → spatial_layers kind='mvt'.
    Une commune = une unité committée → résumable. Ne touche PAS au score (# TODO étage 1)."""
    import time

    from .connectors.georisques import GeorisquesConnector
    from .ingestion import georisques_layers
    from .ingestion.run_all import REUNION_COMMUNES

    conn = GeorisquesConnector(throttle_s=throttle)
    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    t0 = time.time()
    total = 0
    for insee, nom in targets:
        with session_scope() as s:
            has = s.execute(text(
                "SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind='mvt'"), {"c": nom}).scalar()
            if has and not force:
                typer.echo(f"  ⏭ {nom} : mvt déjà là ({has}), sauté.")
                continue
            n = georisques_layers.ingest_mvt_commune(s, insee, nom, connector=conn)
            s.commit()
            total += n
            typer.echo(f"  ✓ {nom} : {n} mvt")
    typer.echo(f"✓ /mvt île : {total} ({time.time() - t0:.0f}s)")


@app.command("ingest-qpv")
def ingest_qpv_cmd() -> None:
    """Vague C bonus — QPV 2024 (ANCT) → spatial_layers kind='qpv', filtre 974. Sert le BILAN
    PROMOTEUR (# TODO bilan), PAS le score. Idempotent (purge+réinsère)."""
    from .ingestion import qpv

    with session_scope() as s:
        res = qpv.ingest(s)
        s.commit()
        b = qpv.bilan(s)
    typer.echo(f"✓ QPV 2024 : {res['qpv']} QPV ({b['communes']} communes), "
               f"{b['parcelles_en_qpv']} parcelles en QPV.")


@app.command("ingest-amenites")
def ingest_amenites_cmd(
    commune: str = typer.Option(None, help="INSEE d'une commune (défaut = les 24 communes)."),
    force: bool = typer.Option(False, help="Recalculer même les communes déjà faites."),
) -> None:
    """Vague C bonus — aménités OSM (école/santé/commerce/tcsp) → spatial_layers kind='amenite'
    + distances par parcelle (parcel_amenites). Résumable. Signal calculé, poids # TODO étage 1."""
    import time

    from .ingestion import amenites
    from .ingestion.run_all import REUNION_COMMUNES, _commune_bbox

    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    t0 = time.time()
    # Phase 1 — POI (Overpass, par commune)
    for insee, nom in targets:
        with session_scope() as s:
            has = s.execute(text("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind='amenite'"),
                            {"c": nom}).scalar()
            if has and not force:
                typer.echo(f"  ⏭ {nom} POI déjà là ({has}), sauté.")
                continue
            bbox = _commune_bbox(s, nom)
            if bbox is None:
                typer.echo(f"  ⚠ {nom} : pas de parcelles, sauté.")
                continue
            try:
                counts = amenites.ingest_poi_commune(s, nom, bbox)
                s.commit()
                typer.echo(f"  ✓ {nom} POI : {counts}")
            except Exception as exc:  # noqa: BLE001 — Overpass saturé : on saute cette commune,
                s.rollback()          # la passe continue (résumable : reprise au prochain run)
                typer.echo(f"  ⚠ {nom} POI en échec ({type(exc).__name__}), sauté — reprise au prochain run.")
    # Phase 2 — distances par parcelle (contre TOUS les POI de l'île)
    typer.echo("— calcul des distances par parcelle —")
    for insee, nom in targets:
        with session_scope() as s:
            has = s.execute(text("SELECT count(*) FROM parcel_amenites a JOIN parcels p ON p.id=a.parcel_id "
                                 "WHERE p.commune=:c"), {"c": nom}).scalar()
            if has and not force:
                typer.echo(f"  ⏭ {nom} distances déjà là ({has}), sauté.")
                continue
            n = amenites.compute_amenites_commune(s, nom)
            s.commit()
            typer.echo(f"  ✓ {nom} : {n} parcelles calculées")
    typer.echo(f"✓ Aménités île ({time.time() - t0:.0f}s)")


@app.command("ingest-amenites-affichage")
def ingest_amenites_affichage_cmd(
    commune: str = typer.Option(None, help="INSEE d'une commune (défaut = les 24 communes)."),
) -> None:
    """M55-A — catégories d'AFFICHAGE des aménités OSM (mairie, police, sport, marché forain,
    crèche, collège/lycée) → spatial_layers kind='amenite'. Affichage seul (le scoring ne les lit
    pas). Idempotent : ne purge/re-tire QUE ces subtypes, jamais les 4 du signal distance.
    ⚠ APPELS RÉSEAU Overpass (résumable : une commune en échec est sautée)."""
    import time

    from .ingestion import amenites
    from .ingestion.run_all import REUNION_COMMUNES, _commune_bbox

    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    t0 = time.time()
    for _insee, nom in targets:
        with session_scope() as s:
            bbox = _commune_bbox(s, nom)
            if bbox is None:
                typer.echo(f"  ⚠ {nom} : pas de parcelles, sauté.")
                continue
            try:
                counts = amenites.ingest_poi_affichage(s, nom, bbox)
                s.commit()
                typer.echo(f"  ✓ {nom} affichage : {counts}")
            except Exception as exc:  # noqa: BLE001 — Overpass saturé : on saute, reprise au prochain run
                s.rollback()
                typer.echo(f"  ⚠ {nom} affichage en échec ({type(exc).__name__}), sauté.")
    typer.echo(f"✓ Aménités affichage île ({time.time() - t0:.0f}s)")


@app.command("build-signaux-vie")
def build_signaux_vie_cmd() -> None:
    """M55-D stage 6 — pré-calcule les Signaux de vie lourds (permis_actif, friche,
    assemblage_pm) → table parcel_signaux_vie, interrogée par /filtre en EXISTS indexé.
    Idempotent (DELETE+INSERT par signal). Les 5 autres signaux restent calculés en direct."""
    from . import signaux_vie

    with session_scope() as s:
        counts = signaux_vie.build_signaux_vie(s)
        s.commit()
    typer.echo("✓ Signaux de vie pré-calculés : "
               + " · ".join(f"{k} {v}" for k, v in counts.items()))


@app.command("ingest-abf")
def ingest_abf_cmd() -> None:
    """Clôture Vague B — abords ABF (base Mérimée, tampon ~500 m) → spatial_layers kind='abf',
    île entière. FLAG QUALITÉ (# TODO étage 1), PAS exclusion étage 0. Remplace l'ancien GPU AC1."""
    from .ingestion import abf_merimee

    with session_scope() as s:
        res = abf_merimee.ingest(s)
        s.commit()
        b = abf_merimee.bilan(s)
    typer.echo(f"✓ ABF Mérimée : {res['mh_geolocalises']}/{res['mh_total']} MH → abords. "
               f"{b['abords']} abords, {b['parcelles_intersectees']} parcelles intersectées.")


@app.command("compute-residuel")
def compute_residuel_cmd(
    commune: str = typer.Option(None, help="Commune (nom/INSEE ; défaut pilote). Ignoré si --ile."),
    ile: bool = typer.Option(False, "--ile", help="Toute l'île (toutes les parcelles)."),
    chunk: int = typer.Option(500, help="Taille des lots (commit par lot)."),
    new_run: str = typer.Option(None, "--new-run", help="Crée un run NEUF (libellé) et y écrit."),
    into_run: int = typer.Option(None, "--into-run", help="Écrit dans un run existant NON servi."),
) -> None:
    """Calcule et cache le POTENTIEL RÉSIDUEL (Lot B) dans un RUN désigné — M135. Écrit dans
    --new-run <label> OU --into-run <seq> ; JAMAIS le run servi (garde-fou : erreur)."""
    import subprocess
    import time

    from .faisabilite.residuel import compute_residuel_batch
    from .faisabilite.residuel_runs import ServedRunWriteError, assert_writable, create_run

    if (new_run is None) == (into_run is None):
        typer.echo("Désigner UN run cible : --new-run <label> OU --into-run <seq> (jamais le servi).")
        raise typer.Exit(2)
    resolved = None if ile else _resolve_commune(commune)
    models.ensure_residuel_cache(engine())   # assure aussi le schéma de versionnement
    with session_scope() as session:
        ids = _parcel_ids(session, resolved)
    if not ids:
        typer.echo("Aucune parcelle ingérée.")
        raise typer.Exit(1)
    with session_scope() as s:
        if new_run is not None:
            sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip() or None
            run_seq = create_run(s, new_run, communes=(None if ile else resolved), code_commit=sha)
            typer.echo(f"run neuf : run_seq={run_seq} « {new_run} » (commit {sha})")
        else:
            run_seq = into_run
        try:
            assert_writable(s, run_seq)   # ERREUR si run_seq == run servi
        except ServedRunWriteError as e:
            typer.echo(f"REFUSÉ : {e}")
            raise typer.Exit(3) from None
    t0 = time.time()
    total = 0
    causes: dict = {}
    erreurs = 0
    for k in range(0, len(ids), chunk):
        with session_scope() as s:
            r = compute_residuel_batch(s, ids[k:k + chunk], run_seq, log=typer.echo)
        total += r["calcules"]
        erreurs += r["erreurs"]
        for cz, n in r["causes"].items():
            causes[cz] = causes.get(cz, 0) + n
        typer.echo(f"    {min(k + chunk, len(ids))}/{len(ids)} parcelles…")
    with session_scope() as s:   # métadonnées du run
        s.execute(text(
            "UPDATE residuel_runs SET duree_s=:d,"
            " computed_at_min=(SELECT min(computed_at) FROM parcel_residuel_runs WHERE run_seq=:rs),"
            " computed_at_max=(SELECT max(computed_at) FROM parcel_residuel_runs WHERE run_seq=:rs)"
            " WHERE run_seq=:rs"), {"d": int(time.time() - t0), "rs": run_seq})
    with engine().begin() as c:
        c.execute(text("ANALYZE parcel_residuel_runs"))   # stats pour le planificateur
    typer.echo(f"✓ run {run_seq} : {total} calculées · {sum(causes.values())} avec cause · "
               f"{erreurs} erreur(s) · {int(time.time() - t0)}s ({'île' if ile else resolved})")
    for cz, n in sorted(causes.items(), key=lambda kv: -kv[1]):
        typer.echo(f"    cause {cz}: {n}")


@app.command("residuel-migrate")
def residuel_migrate_cmd() -> None:
    """M135 — migration one-time : parcel_residuel (table) → run 1 « legacy » + VUE (idempotent)."""
    from .faisabilite.residuel_runs import migrate_to_runs
    typer.echo(f"migration : {migrate_to_runs(engine())}")


@app.command("residuel-runs")
def residuel_runs_cmd() -> None:
    """M135 — liste les runs résiduels (servi ★, épinglé 📌)."""
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT r.run_seq, r.label, r.is_served, r.is_pinned, r.communes, r.code_commit,"
            " r.duree_s, (SELECT count(*) FROM parcel_residuel_runs pr WHERE pr.run_seq=r.run_seq) n"
            " FROM residuel_runs r ORDER BY r.run_seq")).all()
    for rs, label, served, pinned, com, sha, dur, n in rows:
        typer.echo(f"  {'★' if served else ' '}{'📌' if pinned else ' '} run {rs}: « {label} » "
                   f"n={n} {com or 'île'} commit={sha or '?'} {dur or '?'}s")


@app.command("residuel-serve")
def residuel_serve_cmd(run_seq: int = typer.Argument(..., help="run_seq à SERVIR (bascule).")) -> None:
    """M135 — BASCULE le service sur `run_seq` (geste de Vic). Réversible : rappeler avec l'ancien."""
    from .faisabilite.residuel_runs import served_run_seq, set_served
    with engine().begin() as c:
        avant = served_run_seq(c)
        set_served(c, run_seq)
    typer.echo(f"✓ bascule : run servi {avant} → {run_seq} (retour : residuel-serve {avant})")


@app.command("residuel-purge")
def residuel_purge_cmd(run_seq: int = typer.Argument(..., help="run_seq à PURGER.")) -> None:
    """M135 — purge un run (geste de Vic). REFUSE un run servi ou épinglé."""
    from .faisabilite.residuel_runs import purge_run
    with engine().begin() as c:
        purge_run(c, run_seq)
    typer.echo(f"✓ run {run_seq} purgé.")


@app.command("residuel-pin")
def residuel_pin_cmd(
    run_seq: int = typer.Argument(..., help="run_seq à épingler/désépingler."),
    unpin: bool = typer.Option(False, "--unpin", help="Désépingle au lieu d'épingler."),
) -> None:
    """M135 — épingle un run (reproductibilité entraînement scoring) : la purge le refusera."""
    with engine().begin() as c:
        c.execute(text("UPDATE residuel_runs SET is_pinned=:v WHERE run_seq=:s"),
                  {"v": not unpin, "s": run_seq})
    typer.echo(f"✓ run {run_seq} {'désépinglé' if unpin else 'épinglé 📌'}.")


@app.command("compute-constructibilite")
def compute_constructibilite_cmd(
    commune: str = typer.Option(None, help="Commune (nom ou INSEE ; défaut = pilote)."),
    chunk: int = typer.Option(500, help="Taille des lots (commit par lot)."),
) -> None:
    """Calcule et cache le VERDICT DE CONSTRUCTIBILITÉ (déclassement étage 0 : tête de liste non
    constructible). Alimente `parcel_constructibilite` (A zone fermée / B parcelle inconstructible
    / C non vérifiable), lu par le scoring pour déclasser les parcelles servies non bâtissables."""
    from .faisabilite.constructibilite import build_constructibilite_batch

    commune = _resolve_commune(commune)
    models.ensure_constructibilite_cache(engine())
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
    if not ids:
        typer.echo("Aucune parcelle ingérée.")
        raise typer.Exit(1)
    total = 0
    for k in range(0, len(ids), chunk):
        with session_scope() as s:
            total += build_constructibilite_batch(s, ids[k:k + chunk])
        typer.echo(f"    {min(k + chunk, len(ids))}/{len(ids)} parcelles…")
    typer.echo(f"✓ Constructibilité cachée : {total} parcelles déclassées/non vérifiables ({commune}).")


@app.command("compute-au-statut")
def compute_au_statut_cmd(
    commune: str = typer.Option(None, help="Commune (nom ou INSEE ; défaut = pilote)."),
    chunk: int = typer.Option(500, help="Taille des lots (commit par lot)."),
) -> None:
    """Calcule et cache le STATUT D'OUVERTURE des zones AU (ANCIEN modèle, communes NON calibrées).
    Alimente `parcel_au_statut` : 'générique' (AU non calibrée → déclassée `declasse_au_statut_inconnu`)
    ou 'dimensions_seules' (règles extraites, ouverture non lue → servie + mention). Lu par le scoring
    et la fiche. Horodaté (péremption). M-S : les communes CALIBRÉES sont traitées par
    `compute-au-ouverture` (modèle affiné) et IGNORÉES ici — les deux modèles ne se chevauchent pas."""
    from .faisabilite.au_statut import build_au_statut_batch

    commune = _resolve_commune(commune)
    models.ensure_au_statut_cache(engine())
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
        idus = [i for (i,) in session.execute(
            text("SELECT idu FROM parcels WHERE id = ANY(:ids)"), {"ids": ids}).all()]
    if not idus:
        typer.echo("Aucune parcelle ingérée.")
        raise typer.Exit(1)
    total = 0
    for k in range(0, len(idus), chunk):
        with session_scope() as s:
            total += build_au_statut_batch(s, idus[k:k + chunk])
        typer.echo(f"    {min(k + chunk, len(idus))}/{len(idus)} parcelles…")
    with session_scope() as s:
        from .faisabilite.au_statut import au_statut_peremption
        per = au_statut_peremption(s)
    typer.echo(f"✓ Statut AU caché : {total} parcelles marquées ({per['declassees']} déclassées, "
               f"{per['servies_avec_mention']} servies+mention) — {commune}.")


@app.command("compute-au-ouverture")
def compute_au_ouverture_cmd() -> None:
    """Calcule le statut d'ouverture AU AFFINÉ (GPU-PILOTE, Vic 30/07) pour les communes CALIBRÉES
    de `config/calibrage/au_ouverture_planchers.yaml`. Trois traitements lus au règlement :
    `declasse_au_fermee` (réserve), `declasse_au_statut_inconnu` (phasage 2AU→1AU),
    `conditionnelle_operation` (SERVIE) et `au_sous_plancher` (SERVIE, candidate à l'assemblage —
    surface manquante + voisines). Prime sur l'ancien modèle là où la commune est calibrée
    (les deux ne se chevauchent pas). Alimente `parcel_au_statut` UNIQUEMENT (peupler ≠ basculer)."""
    from .faisabilite.au_ouverture import build_au_ouverture, _config

    communes = list(_config().keys())
    if not communes:
        typer.echo("Aucune commune calibrée dans au_ouverture_planchers.yaml.")
        raise typer.Exit(1)
    models.ensure_au_statut_cache(engine())
    with session_scope() as s:
        compte = build_au_ouverture(s, communes)
    total = sum(compte.values())
    typer.echo(f"✓ Ouverture AU affinée : {total} parcelles marquées sur {len(communes)} communes "
               f"calibrées.")
    for statut, n in sorted(compte.items(), key=lambda kv: -kv[1]):
        typer.echo(f"    {statut:32} {n}")
    with session_scope() as s:
        from .faisabilite.au_statut import au_statut_peremption
        per = au_statut_peremption(s)
    typer.echo(f"  → péremption : {per['declassees']} déclassées en attente, "
               f"{per['servies_avec_mention']} servies+mention "
               f"(plus ancienne {per['jours_plus_ancien']} j, statut {per['statut']}).")


@app.command("au-statut-compteur")
def au_statut_compteur_cmd() -> None:
    """Compteur de PÉREMPTION du déclassement AU (exigence Vic : « un déclassement temporaire sans
    date devient permanent par oubli »). Combien de parcelles en attente de vérification d'ouverture,
    et depuis combien de jours. Lecture seule."""
    from .faisabilite.au_statut import au_statut_peremption
    with session_scope() as s:
        per = au_statut_peremption(s)
    if not per["total_en_attente"]:
        typer.echo("Aucune parcelle en attente de vérification d'ouverture AU.")
        return
    typer.echo(f"⏳ {per['total_en_attente']} parcelles AU en attente de vérification d'ouverture :")
    for classe, d in sorted(per["par_classe"].items()):
        typer.echo(f"   {classe:18s} {d['n']:5d} parcelles — plus ancienne : {d['jours_plus_ancien']} j, "
                   f"médiane : {d['jours_median']} j")
    typer.echo(f"   → {per['declassees']} déclassées, {per['servies_avec_mention']} servies avec mention.")


def _print_healthcheck(commune: str) -> bool:
    from . import demo

    with session_scope() as s:
        res = demo.healthcheck(s, commune)
    typer.echo(f"\n── Healthcheck démo ({res['commune']}) ──")
    for c in res["checks"]:
        mark = "✓" if c["ok"] else ("✗" if c["critical"] else "•")
        typer.echo(f"  {mark} {c['name']:34} {c['detail']}")
    typer.echo("\n" + ("✅ PRÊT POUR LA DÉMO" if res["ok"] else "❌ NON PRÊT — voir les ✗ ci-dessus"))
    return res["ok"]


@app.command("rebuild-demo")
def rebuild_demo_cmd(
    commune: str = typer.Option("97415", help="INSEE de la commune de démo (défaut Saint-Paul)."),
    limit: int = typer.Option(None, help="Cap de parcelles (tests)."),
    seed_pipeline: bool = typer.Option(True, help="Seed quelques entrées pipeline (démo non vide)."),
    skip_ingest: bool = typer.Option(False, help="Ne ré-ingère pas les couches (ré-évalue seulement)."),
) -> None:
    """Reconstruit une base de DÉMO cohérente et IDEMPOTENTE pour une commune.

    Enchaîne les briques DURABLES : schéma + colonnes (geom_2975 trigger, prospection) →
    cadastre + couches (geo-dvf/PPR/SAR/OSM/pente/PLU) → geom_2975 valide + index →
    évaluation (cascade + scoring + déclassement) → seed pipeline → healthcheck.
    Aucun changement de scoring/seuils : on ne fait que (re)jouer l'existant.
    """
    from . import demo
    from .ingestion import layers_ingest, run_all, seed_sources

    s_set = get_settings()
    name = s_set.pilot_commune_name if commune == s_set.pilot_commune_insee else commune
    ensure_postgis()
    # Schéma + colonnes (rapide) — le backfill geom_2975 GLOBAL est ÉVITÉ ici (fait SCOPÉ plus bas).
    models.Base.metadata.create_all(engine())
    models.ensure_pipeline_prospection(engine())
    with session_scope() as s:
        seed_sources.seed(s)
        n_parcels = s.execute(
            text("SELECT count(*) FROM parcels WHERE commune = :c"), {"c": name}).scalar() or 0
    if skip_ingest:
        layers = {"(couches inchangées)": "skip"}
    elif n_parcels == 0:
        typer.echo(f"▶ Ingestion COMPLÈTE {name} ({commune}) — cadastre + couches…")
        with session_scope() as s:
            layers = (run_all.ingest_commune(s, commune, name, limit=limit).get("layers") or {})
    else:
        # Parcelles déjà là (cas du recyclage) : on ne re-télécharge PAS le cadastre,
        # on ré-ingère seulement les COUCHES de la commune (geo-dvf/PPR/SAR/OSM/pente/PLU).
        typer.echo(f"▶ {n_parcels} parcelles présentes → ré-ingestion des COUCHES seulement…")
        with session_scope() as s:
            s.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": name})
            s.execute(text("DELETE FROM dvf_mutations WHERE commune = :c"), {"c": name})
            bb = s.execute(text("SELECT ST_XMin(e),ST_YMin(e),ST_XMax(e),ST_YMax(e) "
                                "FROM (SELECT ST_Extent(geom) e FROM parcels WHERE commune=:c) t"),
                           {"c": name}).one()
            layers = layers_ingest.ingest_layers(s, commune, name, tuple(bb), None)
    typer.echo(f"  couches : {_fmt_layers(layers)}")
    models.ensure_geom_2975(engine(), commune=name)          # SCOPÉ commune → rapide (MakeValid + GIST)
    typer.echo("▶ Évaluation (cascade + scoring + déclassement)…")
    with session_scope() as s:
        nev = run_all.evaluate_commune(s, name)
    typer.echo(f"  {nev} parcelles évaluées.")
    if seed_pipeline:
        with session_scope() as s:
            k = demo.seed_demo_pipeline(s, name)
        typer.echo(f"  pipeline : {k} entrées de démo (aucun nom réel).")
    _print_healthcheck(name)


@app.command("demo-healthcheck")
def demo_healthcheck_cmd(
    commune: str = typer.Option("Saint-Paul", help="Nom de commune (défaut Saint-Paul)."),
) -> None:
    """Vérifie que la base est prête pour une démo (code de sortie ≠ 0 si une couche critique manque)."""
    raise typer.Exit(0 if _print_healthcheck(commune) else 1)


def _warm_demo_core(name: str, seed_pipeline: bool) -> list[str]:
    """Cœur de warm-demo (réutilisé par prepare-pilot) : pré-chauffe + vérifie chaque
    parcelle de démo (statut attendu, export avec résumé). Renvoie la liste des alertes."""
    import time

    from . import demo
    from .api.app import _build_fiche
    from .api.enrichment import enrichment_cached
    from .api.export import fiche_html, fiche_markdown

    typer.echo(f"▶ Pré-chauffe démo ({name}) — {len(demo.DEMO_PARCELS)} parcelles…")
    issues: list[str] = []
    for spec in demo.DEMO_PARCELS:
        idu = spec["idu"]
        with session_scope() as s:
            p = s.execute(select(models.Parcel).where(models.Parcel.idu == idu)).scalar_one_or_none()
            if not p:
                typer.echo(f"  ✗ {idu:16} ABSENTE")
                issues.append(f"{idu} absente")
                continue
            lon, lat = s.execute(
                text("SELECT ST_X(centroid), ST_Y(centroid) FROM parcels WHERE id = :i"), {"i": p.id}).one()
            t0 = time.monotonic()
            enrichment_cached(s, p, float(lon), float(lat))      # calcule si froid, sinon sert le cache
            dt = time.monotonic() - t0
            fiche = _build_fiche(s, idu)
            status = fiche["verdict"]["status"]
            md, html = fiche_markdown(fiche), fiche_html(fiche)
            exp_ok = "Résumé opportunité" in md and "Résumé opportunité" in html
            conforme = status == spec["attendu"]
            if not conforme:
                issues.append(f"{idu} statut={status} (attendu {spec['attendu']})")
            if not exp_ok:
                issues.append(f"{idu} export incomplet")
            mark = "✓" if conforme and exp_ok else "•"
            typer.echo(f"  {mark} {idu:16} {status:22} cache {dt:4.1f}s · export {'ok' if exp_ok else 'KO'}")
    if seed_pipeline:
        with session_scope() as s:
            k = demo.seed_demo_pipeline(s, name)
        typer.echo(f"  pipeline : {k} entrées de démo (aucun nom réel).")
    return issues


@app.command("warm-demo")
def warm_demo_cmd(
    commune: str = typer.Option("Saint-Paul", help="Nom de commune (défaut Saint-Paul)."),
    seed_pipeline: bool = typer.Option(True, help="(Re)seed quelques entrées pipeline (Kanban non vide)."),
) -> None:
    """Pré-chauffe le cache d'enrichissement des parcelles de démo + vérifie verdicts & exports.

    À lancer juste AVANT une démo : la 1ʳᵉ ouverture des fiches de démo devient instantanée
    (RGE ALTI/GPU déjà calculés et mis en cache), et on confirme que chaque parcelle montre le
    statut attendu et qu'elle s'exporte (avec son résumé). Idempotent ; ne touche NI le scoring
    NI les couches. Code de sortie ≠ 0 si une parcelle dérive ou manque."""
    from . import demo

    s_set = get_settings()
    name = s_set.pilot_commune_name if commune == s_set.pilot_commune_insee else commune
    issues = _warm_demo_core(name, seed_pipeline)
    if issues:
        typer.echo("\n⚠️  Alertes :")
        for x in issues:
            typer.echo(f"   - {x}")
        typer.echo(f"→ corriger avec : labuse rebuild-demo --commune {s_set.pilot_commune_insee}")
        raise typer.Exit(1)
    typer.echo(f"\n✅ {len(demo.DEMO_PARCELS)}/{len(demo.DEMO_PARCELS)} parcelles pré-chauffées, conformes et exportables.")


@app.command("doctor")
def doctor_cmd(
    commune: str = typer.Option("Saint-Paul", help="Nom de commune (défaut Saint-Paul)."),
    fix: bool = typer.Option(True, help="Répare le schéma (léger, idempotent) avant le diagnostic."),
    as_json: bool = typer.Option(False, "--json", help="Sortie JSON (monitoring/outillage) — mêmes codes de sortie."),
) -> None:
    """Diagnostic complet de l'état : DB → schéma → données → démo, avec quoi faire.

    Répare automatiquement le SCHÉMA (colonnes/triggers/index — secondes, sans risque) ;
    ne reconstruit JAMAIS les données (c'est `rebuild-demo`, dit explicitement).
    Codes de sortie : 0 = prêt pour la démo · 1 = dégradé (actions affichées) · 2 = DB injoignable."""
    import json as _json

    from . import state

    try:
        ensure_postgis()
    except Exception as exc:  # noqa: BLE001 — sans DB, rien d'autre n'a de sens
        if as_json:
            typer.echo(_json.dumps({"db_reachable": False, "ready_for_demo": False,
                                    "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        else:
            typer.echo(f"✗ Base injoignable : {type(exc).__name__}: {exc}")
            typer.echo("→ vérifier PostgreSQL et LABUSE_DATABASE_URL")
        raise typer.Exit(2) from None
    if not as_json:
        typer.echo("✓ Base joignable")

    if fix:
        models.ensure_schema(engine())
        if not as_json:
            typer.echo("✓ Schéma réconcilié (léger : tables, colonnes, triggers, index — aucune donnée recalculée)")

    with session_scope() as s:
        sch = state.schema_status(s)
        data = state.data_status(s, commune)
        st = state.demo_status(s, commune)
        peremption = state._au_statut_readiness(s)

    if as_json:
        typer.echo(_json.dumps({"db_reachable": True, "schema": sch, "data": data,
                                "au_statut_en_attente": peremption, **st},
                               ensure_ascii=False))
        if not st["ready_for_demo"]:
            raise typer.Exit(1)
        return

    typer.echo(f"{'✓' if sch['ok'] else '✗'} Schéma : {'OK' if sch['ok'] else ' · '.join(sch['missing'])}")
    typer.echo(f"{'✓' if data['ok'] else '✗'} Données ({commune}) : "
               f"{'OK' if data['ok'] else 'manquant → ' + ' · '.join(data['missing'])}")
    hc = st["healthcheck"]
    n_ok = sum(1 for c in hc["checks"] if c["ok"])
    typer.echo(f"{'✓' if hc['ok'] else '✗'} Healthcheck : {n_ok}/{len(hc['checks'])}")
    typer.echo(f"{'✓' if st['demo']['all_conform'] else '✗'} Parcelles de démo conformes")
    w = st["warm"]
    typer.echo(f"{'✓' if w['done'] else '•'} Cache fiches démo : {w['warmed']}/{w['total']} pré-chauffées")
    if peremption and peremption["n"]:
        glyph = {"ok": "•", "warn": "⚠", "blocage": "⛔"}.get(peremption["statut"], "•")
        typer.echo(f"{glyph} Déclassements AU en attente : {peremption['n']} "
                   f"(plus ancienne {peremption['jours_plus_ancien']} j, statut {peremption['statut']})")

    if st["ready_for_demo"]:
        typer.echo("\n✅ PRÊT POUR LA DÉMO")
        return
    typer.echo("\n❌ NON PRÊT — à lancer :")
    for a in st["actions"]:
        typer.echo(f"   $ {a}")
    raise typer.Exit(1)


@app.command("prepare-pilot")
def prepare_pilot_cmd(
    commune: str = typer.Option("97415", help="INSEE de la commune pilote (défaut Saint-Paul)."),
    skip_rebuild: bool = typer.Option(False, help="Vérifie sans jamais reconstruire (échoue si non prêt)."),
) -> None:
    """UNE commande pour préparer un pilote/démo : schéma → (rebuild si nécessaire) →
    healthcheck → warm-demo → confirmation. Ne relance PAS un rebuild si l'état est déjà
    prêt (idempotent et économe). Code de sortie ≠ 0 si l'état final n'est pas prêt."""
    s_set = get_settings()
    name = s_set.pilot_commune_name if commune == s_set.pilot_commune_insee else commune

    typer.echo("━━ 1/4 · Schéma ━━")
    ensure_postgis()
    models.ensure_schema(engine())
    typer.echo("  ✓ schéma réconcilié (léger)")

    typer.echo("━━ 2/4 · Données ━━")
    from . import demo, state
    with session_scope() as s:
        hc_ok = demo.healthcheck(s, name)["ok"]
    if hc_ok:
        typer.echo("  ✓ healthcheck déjà OK → rebuild sauté (rien à reconstruire)")
    elif skip_rebuild:
        typer.echo("  ✗ healthcheck NON OK et --skip-rebuild demandé")
        typer.echo(f"  → lancer : labuse rebuild-demo --commune {commune}")
        raise typer.Exit(1)
    else:
        typer.echo("  • healthcheck NON OK → rebuild-demo (~5 min)…")
        rebuild_demo_cmd(commune=commune, limit=None, seed_pipeline=True, skip_ingest=False)

    typer.echo("━━ 3/4 · Healthcheck final ━━")
    if not _print_healthcheck(name):
        typer.echo(f"→ diagnostic : labuse doctor --commune {name}")
        raise typer.Exit(1)

    typer.echo("━━ 4/4 · Pré-chauffe démo ━━")
    issues = _warm_demo_core(name, seed_pipeline=True)
    if issues:
        typer.echo("⚠️  " + " ; ".join(issues))
        raise typer.Exit(1)

    with session_scope() as s:
        ready = state.demo_status(s, name)["ready_for_demo"]
    if not ready:
        typer.echo("❌ État final incohérent — lancer : labuse doctor")
        raise typer.Exit(1)
    typer.echo("\n✅ PILOTE PRÊT — lancer : labuse api  → http://127.0.0.1:8000/app/")


@app.command("discover")
def discover_cmd(
    commune: str = typer.Option(None, help="Commune (nom ou INSEE ; défaut = pilote)."),
    limit: int = typer.Option(20, help="Nombre de survivantes à afficher."),
) -> None:
    """Vue Découverte (offre B) : cascade sur la commune → survivantes classées."""
    from .cascade import evaluate_parcels

    raw = commune
    commune = _resolve_commune(commune)
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
        if not ids:
            _fail_zero_parcel(session, raw, commune)
        outcomes = evaluate_parcels(ids, session, persist=True)

    survivors = [o for o in outcomes if o.status in ("opportunite", "a_creuser")]
    survivors.sort(key=lambda o: (o.opportunity.score, o.completeness.score), reverse=True)
    typer.echo(f"\nDécouverte {commune} — {len(survivors)} survivante(s) sur {len(outcomes)} parcelles :\n")
    typer.echo(f"{'IDU':16} {'statut':22} {'opp':>4} {'compl':>6}")
    typer.echo("-" * 52)
    for o in survivors[:limit]:
        typer.echo(f"{o.idu:16} {o.status:22} {o.opportunity.score:>4} {o.completeness.score:>6}")


@app.command("sources")
def sources_cmd() -> None:
    """Page Sources de données : statut de chaque connecteur."""
    with session_scope() as session:
        rows = session.execute(
            select(models.DataSource.name, models.DataSource.status, models.DataSource.reliability_level,
                   models.DataSource.category).order_by(models.DataSource.category, models.DataSource.name)
        ).all()
    typer.echo(f"{'source':42} {'statut':10} {'fiabilité':14} catégorie")
    typer.echo("-" * 88)
    for name, status, reliab, cat in rows:
        st = status.value if status else "?"
        rl = reliab.value if reliab else "?"
        typer.echo(f"{name:42} {st:10} {rl:14} {cat or ''}")


@app.command("test-source")
def test_source_cmd(name: str = typer.Argument(..., help="Nom exact de la source.")) -> None:
    """Bouton « tester la connexion » : tente l'appel réel (souvent bloqué ici)."""
    from .connectors import get_connector

    connector = get_connector(name)
    if not connector:
        typer.echo(f"Pas de connecteur pour « {name} » (import/manuel/à faire).")
        raise typer.Exit(1)
    res = connector.test_connection()
    typer.echo(f"{'✓' if res.ok else '✗'} {res.source} — {res.message}")


@app.command("watch")
def watch_cmd(commune: str = typer.Argument(None, help="Commune (nom ou INSEE ; défaut = pilote).")) -> None:
    """Veille (offre C) : run snapshot/delta → signaux + ré-évaluation des parcelles touchées."""
    from .ingestion import signals

    name = _resolve_commune(commune)
    with session_scope() as session:
        res = signals.run_watch(session, name)
    if res["baseline"]:
        typer.echo(f"✓ Veille {name} : photo de référence posée (1er run, aucune alerte).")
    else:
        typer.echo(
            f"✓ Veille {name} : {res['signals_total']} signal(aux) détecté(s) — "
            f"zonage_change={res['zonage_change']}, mutation_dvf={res['mutation_dvf']}, "
            f"new_permit_nearby={res['new_permit_nearby']} ; {res['reevaluated']} parcelle(s) ré-évaluée(s)."
        )


def _pg_env_and_db(url_str: str) -> tuple[dict, str]:
    """Variables d'environnement PG* + nom de base, depuis l'URL SQLAlchemy (jamais de
    mot de passe sur la ligne de commande — il passe par PGPASSWORD)."""
    import os

    from sqlalchemy.engine import make_url

    url = make_url(url_str)
    env = dict(os.environ)
    env.update({k: v for k, v in {
        "PGHOST": url.host, "PGPORT": str(url.port) if url.port else None,
        "PGUSER": url.username, "PGPASSWORD": url.password,
    }.items() if v})
    return env, url.database or "labuse"


# FIX-C6 (GB-054) — tables VOLUMINEUSES et RECONSTRUCTIBLES (dryrun/scoring/entraînement, non
# saisies par l'utilisateur) : leur DATA est exclue du backup « lean » (schéma conservé). Sur le
# pilote, elles pèsent ~16 Go (dryrun_cascade_results seule ≈ 8,7 Go) → un dump complet saturait
# le disque et laissait un fichier partiel. Elles se reconstruisent par ingestion/scoring.
_BACKUP_RECONSTRUCTIBLES = (
    "dryrun_cascade_results", "cascade_results",
    "p_model_dataset", "p_model_dataset_v2", "p_model_dataset_v2bis",
    "p_model_ext_dataset", "p_model_candidates", "score_snapshot_parcelles",
)


def _pg_bin(name: str) -> str | None:
    """Chemin de pg_dump/pg_restore : LABUSE_PG_BIN_DIR s'il est posé (VP-001 — le PATH peut
    servir un client d'une autre MAJEURE que le serveur), sinon le PATH."""
    from pathlib import Path
    from shutil import which

    bin_dir = get_settings().pg_bin_dir
    if bin_dir:
        cand = Path(bin_dir) / name
        return str(cand) if cand.is_file() else None
    return which(name)


def _garde_version_pg_dump(pg_dump: str, env: dict, dbname: str) -> None:
    """VP-001 — un pg_dump d'une majeure PLUS VIEILLE que le serveur échoue (ou pire, produit un
    artefact suspect). Comparer les majeures AVANT de dumper et refuser avec la marche à suivre.
    (Un client plus récent que le serveur sait dumper — seule la régression est bloquée.)"""
    import re
    import subprocess

    out = subprocess.run([pg_dump, "--version"], capture_output=True, text=True)
    m = re.search(r"(\d+)", out.stdout or "")
    client = int(m.group(1)) if m else None
    from sqlalchemy import create_engine, text as sql_text

    eng = create_engine(get_settings().database_url)
    try:
        with eng.connect() as conn:
            serveur = int(conn.execute(sql_text("show server_version_num")).scalar_one()) // 10000
    finally:
        eng.dispose()
    if client is not None and client < serveur:
        typer.echo(f"✗ pg_dump {client} < serveur PostgreSQL {serveur} — le dump échouerait.")
        typer.echo(f"  binaire utilisé : {pg_dump}")
        typer.echo(f"  → installer postgresql-client-{serveur}, ou poser LABUSE_PG_BIN_DIR sur le")
        typer.echo(f"    dossier du bon binaire (ex. LABUSE_PG_BIN_DIR=$(dirname $(which pg_dump)) d'un env qui l'a).")
        raise typer.Exit(2)


@app.command("backup-db")
def backup_db_cmd(
    dir: str = typer.Option("backups", help="Dossier des sauvegardes (créé si absent)."),
    full: bool = typer.Option(False, "--full", help="Dump COMPLET (inclut les tables reconstructibles ~16 Go)."),
) -> None:
    """Sauvegarde de la base (pg_dump format custom compressé). Par DÉFAUT « lean » : exclut la
    DATA des tables reconstructibles (dryrun/entraînement, ~16 Go) — schéma gardé, données
    rebâties par ingestion. `--full` pour tout inclure. Contrôle d'espace disque avant écriture."""
    import shutil
    import subprocess
    import time
    from pathlib import Path

    pg_dump = _pg_bin("pg_dump")
    if not pg_dump:
        typer.echo("✗ pg_dump introuvable — installer postgresql-client (ou corriger LABUSE_PG_BIN_DIR).")
        raise typer.Exit(2)
    env, dbname = _pg_env_and_db(get_settings().database_url)
    _garde_version_pg_dump(pg_dump, env, dbname)
    out_dir = Path(dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # GB-054 — GARDE D'ESPACE : refuser AVANT d'écrire si le disque est trop juste (sinon
    # pg_dump sature et laisse un fichier partiel trompeur). Seuil prudent : 2 Go libres.
    free_go = shutil.disk_usage(out_dir).free / 1e9
    seuil_go = 2.0
    if free_go < seuil_go:
        typer.echo(f"✗ Espace disque insuffisant : {free_go:.1f} Go libres < {seuil_go:.0f} Go requis.")
        typer.echo("  → libérez de la place (purge tables reconstructibles) ou pointez --dir sur un autre volume.")
        raise typer.Exit(2)
    excludes: list[str] = []
    if not full:
        for t in _BACKUP_RECONSTRUCTIBLES:
            excludes += ["--exclude-table-data", t]
    out = out_dir / f"labuse-{dbname}-{'full' if full else 'lean'}-{time.strftime('%Y%m%d-%H%M%S')}.dump"
    typer.echo(f"▶ pg_dump {dbname} ({'COMPLET' if full else 'lean : reconstructibles exclues'}) → {out}")
    res = subprocess.run([pg_dump, "-Fc", "--no-owner", *excludes, "-d", dbname, "-f", str(out)],
                         env=env, capture_output=True, text=True)
    if res.returncode != 0:
        typer.echo(f"✗ pg_dump a échoué :\n{res.stderr.strip()}")
        # ne pas laisser un fichier partiel trompeur
        try:
            out.unlink(missing_ok=True)
        except OSError:
            pass
        raise typer.Exit(1)
    size_mb = out.stat().st_size / 1e6
    typer.echo(f"✓ Sauvegarde : {out} ({size_mb:.1f} Mo)")
    if not full:
        typer.echo(f"  (lean — {len(_BACKUP_RECONSTRUCTIBLES)} tables reconstructibles sans data ; --full pour tout)")
    typer.echo(f"  restauration : labuse restore-db --file {out}")


@app.command("restore-db")
def restore_db_cmd(
    file: str = typer.Option(..., help="Fichier .dump (sortie de labuse backup-db)."),
    target_url: str = typer.Option(None, help="URL SQLAlchemy cible (défaut : la base configurée)."),
    yes: bool = typer.Option(False, "--yes", help="Ne pas demander confirmation (ÉCRASE la cible)."),
) -> None:
    """Restaure une sauvegarde dans la base (pg_restore --clean : ÉCRASE l'existant).

    Vérifie d'abord que le fichier est une archive pg_dump valide (erreur claire sinon).
    Après restauration : lancer `labuse doctor` pour confirmer l'état."""
    import subprocess
    from pathlib import Path

    pg_restore = _pg_bin("pg_restore")
    if not pg_restore:
        typer.echo("✗ pg_restore introuvable — installer postgresql-client (ou corriger LABUSE_PG_BIN_DIR).")
        raise typer.Exit(2)
    src = Path(file)
    if not src.is_file():
        typer.echo(f"✗ Fichier introuvable : {src}")
        raise typer.Exit(1)
    probe = subprocess.run([pg_restore, "--list", str(src)], capture_output=True, text=True)
    if probe.returncode != 0:
        typer.echo(f"✗ Fichier invalide (pas une archive pg_dump) : {src}\n{probe.stderr.strip()}")
        raise typer.Exit(1)

    env, dbname = _pg_env_and_db(target_url or get_settings().database_url)
    if not yes and not typer.confirm(f"⚠ Restaurer {src.name} dans « {dbname} » ? Les données actuelles seront ÉCRASÉES."):
        typer.echo("Abandon.")
        raise typer.Exit(1)
    typer.echo(f"▶ pg_restore → {dbname}…")
    res = subprocess.run(
        [pg_restore, "--clean", "--if-exists", "--no-owner", "-d", dbname, str(src)],
        env=env, capture_output=True, text=True)
    if res.returncode != 0:
        typer.echo(f"✗ pg_restore a échoué :\n{res.stderr.strip()[:2000]}")
        raise typer.Exit(1)
    typer.echo("✓ Restauration terminée.")
    typer.echo("  vérifier l'état : labuse doctor")


@app.command("api")
def api_cmd(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Lance l'API FastAPI (uvicorn)."""
    import uvicorn

    uvicorn.run("labuse.api.app:app", host=host, port=port, reload=False)


# ─────────────────────── scoring v2 produit — P × C (M5) ───────────────────────

@app.command("score-v2")
def score_v2_cmd(
    run_id: str = typer.Option(None, help="Identifiant de run (défaut : m36-l2f-2026-<date>). Refus si existant."),
    rebuild: bool = typer.Option(True, help="Re-matérialise les features ext (DVF/Sitadel frais)."),
    snapshot: bool = typer.Option(True, help="Gèle un snapshot m5-<date> (protocole M1)."),
) -> None:
    """Scoring v2 production : artifact M3.6 gelé (sha256 vérifié, refus si mismatch),
    features as-of, tiers v2 avec hystérésis, écriture versionnée + snapshot.

    Politique de recalibration : intercept seul à chaque run (dernière année
    labellisée) ; re-train complet = décision humaine annuelle (cf. pipeline.py)."""
    from .scoring.p_v2.pipeline import run_score_v2

    with session_scope() as session:
        res = run_score_v2(session, run_id=run_id, rebuild=rebuild, snapshot=snapshot)
    typer.echo(f"✓ run {res['run_id']} : {res['n']} parcelles scorées "
               f"({res['duree_s']}s, modèle sha {res['sha256']}…)")
    typer.echo(f"  tiers : {res['tiers']}")
    typer.echo(f"  N_entrée={res['params'].n_entree} N_sortie={res['params'].n_sortie} "
               f"seuil_D_brûlante={res['params'].brulante_seuil_d:.3f}")
    # Rappel de péremption à CHAQUE run (arbitrage Vic 30/07) — impossible de servir un run sans
    # relire ce chiffre : un déclassement « temporaire » oublié ne peut pas se faire discret.
    with session_scope() as s:
        from .faisabilite.au_statut import au_statut_peremption
        per = au_statut_peremption(s)
    if per["declassees"]:
        glyph = {"ok": "⏳", "warn": "⚠", "blocage": "⛔"}.get(per["statut"], "⏳")
        typer.echo(f"  {glyph} {per['declassees']} déclassées AU en attente de vérification "
                   f"d'ouverture (plus ancienne {per['jours_plus_ancien']} j, statut {per['statut']})")
    if res["snapshot"]:
        typer.echo(f"  snapshot gelé : {res['snapshot']}")


@app.command("arene")
def arene_cmd(
    challenger: str = typer.Option(..., help="run_id du challenger (dans parcel_p_score_v2)."),
    champion: str = typer.Option(None, help="run_id du champion (défaut : dernier run servi)."),
    eval_year: int = typer.Option(None, help="Année d'évaluation (défaut : dernière année labellisée)."),
    churn_max: float = typer.Option(0.25, help="Budget de rotation du top-1158 (défaut 0,25)."),
    n_boot: int = typer.Option(1000, help="Tirages bootstrap de l'IC95 (seed 974)."),
) -> None:
    """ARÈNE — juge un challenger contre le champion (LECTURE SEULE). Écrit un rapport dans
    reports/arene/ et affiche l'AVIS. Ne bascule JAMAIS le run servi (décision humaine)."""
    from datetime import datetime, timezone
    from pathlib import Path

    from .scoring import arene

    with session_scope() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        res = arene.run_arene(session, challenger=challenger, champion=champion,
                              eval_year=eval_year, churn_max=churn_max, n_boot=n_boot)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out_dir = Path(__file__).resolve().parents[2] / "reports" / "arene"
    out_dir.mkdir(parents=True, exist_ok=True)
    if res["is_baseline"]:
        fname = f"BASELINE_{challenger}.md"
    else:
        fname = f"{datetime.now(timezone.utc).strftime('%Y%m%d')}_{challenger}.md"
    path = out_dir / fname
    path.write_text(arene.render_report(res, stamp), encoding="utf-8")
    typer.echo(f"→ {path.relative_to(Path(__file__).resolve().parents[2])}")
    typer.echo(f"AVIS : {res['avis']}")
    if res["criteres_rejet"] and not res["is_baseline"]:
        for c in res["criteres_rejet"]:
            typer.echo(f"  · {c}")


@app.command("monitor-forward")
def monitor_forward_cmd(
    snapshot_label: str = typer.Option(None, help="Snapshot gelé à suivre (défaut : dernier m5-*)."),
) -> None:
    """Monitoring forward mensuel (manuel) : hits du top gelé vs nouvelles mutations
    L2-F et permis, sonde faux négatifs, churn observé → reports/monitoring/AAAA-MM.md.

    Protocole B0 : le CLASSEMENT se suit en continu ; les NIVEAUX ne se jugent
    qu'à l'édition N+2 (censure DVF 974 : ~40 % de complétude à 18 mois)."""
    from .scoring.p_v2.monitoring import run_monitor

    with session_scope() as session:
        res = run_monitor(session, snapshot_label=snapshot_label)
    typer.echo(f"✓ rapport : {res['rapport']} ({res['hits']} hits top gelé, "
               f"{res['faux_negatifs']} faux négatifs sondés)")


@app.command("viabilisation")
def viabilisation_cmd(
    commune: str = typer.Option(None, help="Une commune (défaut : les 24)."),
) -> None:
    """M-VIA lot 2 — construit parcel_viabilisation (indicateur de viabilisation par
    faisceau de preuves : permis proximité, façade voie urbanisée, adjacence bâti,
    zone PLU). Seuils calibrés (cf. reports/m-via/SYNTHESE-M-VIA.md). Aucun tracé réseau."""
    from .faisabilite.viabilisation_build import build_viabilisation

    communes = [commune] if commune else None
    with session_scope() as session:
        res = build_viabilisation(session, communes=communes)
    typer.echo(f"✓ parcel_viabilisation : {res['n']} parcelles, {res['communes']} commune(s), "
               f"{res['duree_s']}s")


if __name__ == "__main__":
    app()


@app.command("detect-events")
def detect_events_cmd(run_from: str | None = None, run_to: str = "q_v2_demo",
                      rattrapage: bool = typer.Option(
                          False, "--rattrapage",
                          help="Rejeu : run_from = run PRÉCÉDENT lu de la table des runs (jamais une "
                               "constante), run_to = servi, événements marqués 'rattrapage'.")) -> None:
    """Diffe deux runs de scoring → événements (bascules, BODACC, permis proches). Cronable.
    Défaut run_from = run servi (Q_A_RUN_LABEL), plus « q_v2 » codé en dur (bascule M8).
    `--rattrapage` : le run de référence vient de p_score_v2_runs (précédent du servi), pas d'un q_v9 en dur."""
    from sqlalchemy.orm import Session

    from .api.events import detect_events, ensure_tables, run_precedent_servi
    from .api.tiles import RUN
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        if rattrapage:
            prev = run_precedent_servi(s, RUN)   # #4 — précédent LU DE LA TABLE
            if not prev:
                typer.echo("Rejeu impossible : aucun run précédent dans p_score_v2_runs.")
                raise typer.Exit(1)
            run_from, run_to = prev, RUN
            out = detect_events(s, run_from, run_to, demo=False, rattrapage=True)
        else:
            run_from = run_from or RUN
            out = detect_events(s, run_from, run_to, demo=run_to.endswith("_demo"))
        s.commit()
    typer.echo(f"Événements émis {run_from} → {run_to}{' (rattrapage)' if rattrapage else ''} : {out}")


@app.command("migrer-prefs")
def migrer_prefs_cmd() -> None:
    """M85-B — migre notif_canaux vers les types du REGISTRE : veille→veille_zone, suivi→parcelle_suivie,
    marche SUPPRIMÉ (le marché n'est plus un type de mail — flux cloche seul). Idempotent."""
    with session_scope() as s:
        a = s.execute(text("UPDATE notif_canaux SET pref_type='veille_zone' WHERE pref_type='veille'")).rowcount
        b = s.execute(text("UPDATE notif_canaux SET pref_type='parcelle_suivie' WHERE pref_type='suivi'")).rowcount
        n = s.execute(text("DELETE FROM notif_canaux WHERE pref_type='marche'")).rowcount
        s.commit()
    typer.echo(f"✓ Préférences migrées au registre : veille→veille_zone ({a}), suivi→parcelle_suivie ({b}), "
               f"marche supprimé ({n}).")


@app.command("migrer-notifications")
def migrer_notifications_cmd() -> None:
    """M85 — migration UNIQUE : veille_notifications (store parallèle M78) → event_log (centre unifié),
    puis SUPPRESSION de la table. Idempotent (no-op si la table n'existe plus). Zéro perte : les 12
    notifs Copilote deviennent des lignes event_log kind='veille', source='Copilote'."""
    from sqlalchemy.orm import Session

    from .api.events import _ensure_cols, ensure_tables
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        existe = s.execute(text("SELECT to_regclass('public.veille_notifications')")).scalar()
        if not existe:
            typer.echo("veille_notifications déjà supprimée — no-op."); return
        _ensure_cols(s)
        n = s.execute(text(
            "INSERT INTO event_log (kind, idu, titre, detail, compte_id, source, lien, dedup, lu, ts) "
            "SELECT 'veille', NULL, titre, detail, compte_id, 'Copilote · veille', "
            "       '/copilote?veille=' || veille_id, 'migr:vn:' || id, vu, created_at "
            "FROM veille_notifications "
            "WHERE NOT EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = 'migr:vn:' || veille_notifications.id)"
        )).rowcount
        s.execute(text("DROP TABLE veille_notifications"))
        s.commit()
    typer.echo(f"✓ Migration : {n} notification(s) veille → event_log, table veille_notifications supprimée.")


@app.command("evaluer-veilles")
def evaluer_veilles_cmd() -> None:
    """M85 — évalue toutes les veilles Copilote actives → notifications dans le centre (event_log).
    À appeler après l'ingestion (le cron J+1). Zéro modèle : SQL + regroupement + dédup."""
    from sqlalchemy.orm import Session

    from .copilote_v2 import veilles
    from .db import engine

    with Session(engine()) as s:
        out = veilles.evaluer_toutes(s)
        s.commit()
    typer.echo(f"✓ Veilles évaluées : {out['veilles_evaluees']}, notifications créées : {out['notifications_creees']}.")


@app.command("evaluer-secteurs")
def evaluer_secteurs_cmd() -> None:
    """M104 — évalue les SECTEURS (zones dessinées) de tous les comptes : ventes DVF, permis,
    BODACC, zonage → alertes + notifications event_log (raccordement du double tuyau).
    À appeler après l'ingestion (cron J+1), comme evaluer-suivis / evaluer-veilles."""
    from sqlalchemy.orm import Session

    from .alertes import evaluer_tous_secteurs
    from .api.events import ensure_tables
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        out = evaluer_tous_secteurs(s)
        s.commit()
    typer.echo(f"✓ Secteurs évalués : {out['scopes']} scope(s), {out['alertes']} alerte(s), "
               f"{out['notifications']} notification(s) event_log.")


@app.command("notif-test")
def notif_test_cmd(compte: int = typer.Option(None, help="compte_id destinataire (défaut : pilote NULL).")) -> None:
    """M85 — crée UNE notification de test (kind=veille, e-mail-activée) pour vérifier la chaîne
    cloche + digest de bout en bout. Idempotente par jour (dédup). Pour un DIGEST réel : viser SON
    compte (--compte <id>), puis `labuse digest --force`."""
    from sqlalchemy.orm import Session

    from .api.events import creer_notification, ensure_tables
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        nid = creer_notification(
            s, kind="veille", compte_id=compte, source="Test",
            titre="Notification de test LABUSE",
            detail="Ceci est une notification de test — la chaîne cloche + digest fonctionne.",
            lien="/", dedup=f"test:{compte}")
        s.commit()
    typer.echo(f"✓ Notification de test créée (id={nid}) pour compte {compte if compte is not None else 'pilote (NULL)'}."
               if nid else "• Déjà créée aujourd'hui (dédup) — aucune nouvelle ligne.")


@app.command("evaluer-suivis")
def evaluer_suivis_cmd() -> None:
    """M85-B — évalue les PARCELLES SUIVIES : changements SUR la parcelle (mutation, permis, BODACC,
    zonage) → notifications typées parcelle_suivie. À appeler après l'ingestion. Zéro modèle, dédup."""
    from sqlalchemy.orm import Session

    from .api.events import ensure_tables, evaluer_suivis
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        out = evaluer_suivis(s)
        s.commit()
    typer.echo(f"✓ Suivis évalués : {out}")


@app.command("notifier-fraicheur")
def notifier_fraicheur_cmd() -> None:
    """M85/M84 — produit une notification systeme (pilote/admin) pour chaque source EN RETARD. À
    appeler par le cron quotidien après l'ingestion. Dédup par source/jour. Zéro modèle."""
    from sqlalchemy.orm import Session

    from .api.events import ensure_tables, notifier_fraicheur
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        n = notifier_fraicheur(s)
        s.commit()
    typer.echo(f"✓ Fraîcheur → notifications : {n} source(s) en retard signalée(s).")


@app.command("purge-notifications")
def purge_notifications_cmd(jours: int = typer.Option(90, help="Rétention (jours).")) -> None:
    """M85 — rétention : supprime les notifications de plus de N jours (défaut 90). Cronable."""
    from sqlalchemy.orm import Session

    from .api.events import ensure_tables, purge_notifications
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        n = purge_notifications(s, jours)
        s.commit()
    typer.echo(f"✓ Purge : {n} notification(s) de plus de {jours} j supprimée(s).")


@app.command("digest")
def digest_cmd(freq: str = typer.Option("quotidien", help="quotidien | hebdo"),
               force: bool = typer.Option(False, help="ignore l'intervalle mini (test)"),
               dry_run: bool = typer.Option(False, "--dry-run",
                   help="Rend ce qui SERAIT envoyé (destinataire, sujet, corps) SANS appeler Brevo — recette VPS.")) -> None:
    """M85 : envoie le DIGEST e-mail QUOTIDIEN (7h00 Réunion via le cron) aux comptes actifs, FILTRÉ
    par préférence e-mail/type. Anti-double-envoi ; digest vide ne part pas ; désinscription +
    préférences dans chaque e-mail ; statut d'envoi tracé (jamais silencieux).
    `--dry-run` (fix #2) : aucun envoi, aucun last_digest_at bougé — le corps prévu est affiché."""
    from sqlalchemy.orm import Session

    from .api.events import ensure_tables, envoyer_digests
    from .db import engine

    ensure_tables(engine())
    base = get_settings().public_base_url or ""
    with Session(engine()) as s:
        out = envoyer_digests(s, base_url=base, freq=freq, force=force, dry_run=dry_run)
    # M85 — un MOTIF par compte : jamais un « ignoré » muet (le silence qu'on interdit partout).
    for d in out.get("details", []):
        marque = {"envoyé": "✓", "simulé": "◇", "ignoré": "•", "échec": "⚠"}.get(d["statut"], "·")
        typer.echo(f"  {marque} compte {d['compte']} ({d.get('email') or 'sans e-mail'}) — "
                   f"{d['statut']} : {d['motif']}")
        if dry_run and d.get("corps"):
            typer.echo("    ┌─ corps (aperçu) ─\n    │ " + d["corps"].replace("\n", "\n    │ "))
    if dry_run:
        typer.echo(f"◇ Digest DRY-RUN ({freq}) : {out['simules']} simulé(s), {out['ignores']} ignoré(s) — "
                   "AUCUN envoi, aucun last_digest_at modifié.")
    else:
        typer.echo(f"✓ Digest ({freq}) : {out['envoyes']} envoyé(s), {out['ignores']} ignoré(s), "
                   f"{out['echecs']} échec(s).")


@app.command("annonce")
def annonce_cmd(
    titre: str = typer.Option(..., help="Titre de l'annonce."),
    corps: str = typer.Option(..., help="Corps du message (le fait, se suffit à lui-même)."),
    lien: str = typer.Option(None, help="Lien optionnel."),
    type_: str = typer.Option("annonce_produit", "--type", help="annonce_produit | maintenance"),
    test: str = typer.Option(None, help="Envoi de TEST à cette adresse (à soi, avant le vrai)."),
    confirmer: bool = typer.Option(False, help="Confirme l'envoi RÉEL à tous les comptes actifs."),
    debut: str = typer.Option("", help="Maintenance : début de coupure."),
    fin: str = typer.Option("", help="Maintenance : fin."),
    duree: str = typer.Option("", help="Maintenance : durée estimée."),
) -> None:
    """M85-B — ANNONCE (chaîne 3) : cloche + mail à tous les comptes actifs. APERÇU obligatoire ;
    --test <email> essaie à soi d'abord ; --confirmer requis pour l'envoi réel. `maintenance` = gabarit
    distinct (dates/durée en évidence), non désactivable."""
    from .api.events import apercu_annonce, ensure_tables, envoyer_annonce
    from .db import engine, session_scope

    ensure_tables(engine())
    base = get_settings().public_base_url or ""
    with session_scope() as s:                       # 1) APERÇU systématique
        ap = apercu_annonce(s, type_=type_, titre=titre, corps=corps, lien=lien,
                            debut=debut, fin=fin, duree=duree)
    typer.echo("─────────── APERÇU ───────────")
    typer.echo(f"Sujet : {ap['sujet']}\n")
    typer.echo(ap["texte"])
    typer.echo(f"──── Destinataires : {ap['n_destinataires']} compte(s) actif(s) ────")
    if test:                                         # 2) TEST à soi, avant le vrai
        with session_scope() as s:
            r = envoyer_annonce(s, type_=type_, titre=titre, corps=corps, lien=lien, base_url=base,
                                test_email=test, debut=debut, fin=fin, duree=duree)
        typer.echo(f"✉ Test envoyé à {test} : {r['statut']}")
    if not confirmer:                                # 3) envoi RÉEL seulement sur --confirmer
        typer.echo("⏸ Aperçu seul. --test <votre-email> pour un essai, puis --confirmer pour l'envoi réel.")
        return
    with session_scope() as s:
        r = envoyer_annonce(s, type_=type_, titre=titre, corps=corps, lien=lien, base_url=base,
                            debut=debut, fin=fin, duree=duree)
    typer.echo(f"✓ Annonce envoyée — cible {r['n_cible']}, mail ok {r['n_mail_ok']}, "
               f"échecs {r['n_mail_echec']}, cloche {r['n_cloche']}. Tracée dans `annonces`.")


@app.command("score-v-fetch")
def score_v_fetch_cmd(
    passe: str = typer.Option("all", help="all | owners | denoms | bodacc"),
    limit: int = typer.Option(None, help="Cap de requêtes (test)."),
    throttle: float = typer.Option(0.2, help="Pause (s) entre requêtes recherche-entreprises."),
) -> None:
    """Récupère les données externes du Score V (Phase 1-2) — RESUMABLE, cache en base.

    owners : recherche-entreprises par SIREN → owner_enrichment ;
    denoms : fallback dénomination (§4.2) → owner_denom_lookup ;
    bodacc : annonces PC + radiations + ventes-cessions → bodacc_annonces_owner."""
    from .connectors.recherche_entreprises import RechercheEntreprisesConnector
    from .ingestion import score_v_fetch as svf

    models.ensure_schema(engine())
    conn = RechercheEntreprisesConnector(throttle_s=throttle)
    with session_scope() as s:
        if passe in ("all", "owners"):
            res = svf.fetch_owner_enrichment(s, conn, limit=limit, log=typer.echo)
            typer.echo(f"✓ owner_enrichment : {res}")
        if passe in ("all", "denoms"):
            res = svf.fetch_denom_lookups(s, conn, limit=limit, log=typer.echo)
            typer.echo(f"✓ owner_denom_lookup : {res}")
        if passe in ("all", "bodacc"):
            n = svf.fetch_bodacc_annonces(s, log=typer.echo)
            typer.echo(f"✓ bodacc_annonces_owner : {n} lignes annonces×SIREN.")


@app.command("score-v-compute")
def score_v_compute_cmd(
    limit: int = typer.Option(None, help="Cap parcelles (test)."),
) -> None:
    """Calcule le Score V (Vendabilité) sur TOUTES les parcelles → parcel_v_score (Phase 2).

    Stage 3 ADDITIF : ne touche ni la cascade, ni Q/A, ni la matrice. Idempotent, relançable
    (upsert + computed_at). Barème verrouillé : scoring/score_v_constants.py."""
    from .scoring.score_v import compute_all

    models.ensure_schema(engine())
    with session_scope() as s:
        stats = compute_all(s, limit=limit, log=typer.echo)
    typer.echo(f"✓ Score V : {stats}")


@app.command("dvf-marche")
def dvf_marche_cmd() -> None:
    """LOT 1 data-gap : recalcule les médianes €/m² par secteur × type de bien (idempotent)."""
    from .ingestion.dvf_marche import compute_medianes_secteur

    models.ensure_schema(engine())
    with session_scope() as s:
        res = compute_medianes_secteur(s)
    typer.echo(f"✓ dvf_secteur_medianes : {res}")


@app.command("ingest-sup")
def ingest_sup_cmd(
    commune: str = typer.Option(None, help="Nom d'une commune (défaut = les 24)."),
) -> None:
    """LOT 4 data-gap : assiettes SUP (GPU/API Carto) → spatial_layers kind='sup'.
    Une commune = une unité committée (résumable). Purge+réinsertion par commune (idempotent)."""
    from .ingestion.run_all import REUNION_COMMUNES
    from .ingestion.sup_gpu import SOURCE_NAME, ingest_commune

    targets = [n for _, n in REUNION_COMMUNES if not commune or n == commune]
    tot = 0
    for nom in targets:
        with session_scope() as s:
            sid = s.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                            {"n": SOURCE_NAME}).scalar()
            res = ingest_commune(s, nom, source_id=sid, log=typer.echo)
            s.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                      {"n": SOURCE_NAME})
        tot += res["sup"]
        typer.echo(f"  ✓ {nom} : {res['sup']} assiettes")
    typer.echo(f"✓ SUP : {tot} assiettes ({len(targets)} communes).")


@app.command("ingest-bruit-route")
def ingest_bruit_route_cmd() -> None:
    """LOT 3 data-gap : bandes du classement sonore (Cerema) → spatial_layers kind='bruit_route'."""
    from .ingestion.bruit_route import SOURCE_NAME, ingest_bruit_route

    with session_scope() as s:
        res = ingest_bruit_route(s, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                  {"n": SOURCE_NAME})
    typer.echo(f"✓ Classement sonore : {res}")


@app.command("ingest-cinquante-pas")
def ingest_cinquante_pas_cmd() -> None:
    """LOT 6 data-gap : corridor de la limite haute des 50 pas (DEAL) → kind='cinquante_pas'."""
    from .ingestion.cinquante_pas import SOURCE_NAME, ingest_cinquante_pas

    with session_scope() as s:
        res = ingest_cinquante_pas(s, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                  {"n": SOURCE_NAME})
    typer.echo(f"✓ 50 pas : {res}")


@app.command("ingest-rnic")
def ingest_rnic_cmd(
    csv: str = typer.Option(..., help="Chemin du CSV national RNIC (data.gouv, ~453 Mo)."),
) -> None:
    """LOT 10 data-gap : copropriétés RNIC 974 → rnic_coproprietes (rattachées aux parcelles)."""
    from .ingestion.rnic import SOURCE_NAME, ingest_rnic

    with session_scope() as s:
        res = ingest_rnic(s, csv, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                  {"n": SOURCE_NAME})
    typer.echo(f"✓ RNIC : {res}")


@app.command("rnic-complements")
def rnic_complements_cmd() -> None:
    """Compléments RNIC sans CSV (Wave copro re-scopée 11/07) : purge RGPD des syndics non
    professionnels (nom/SIRET + clés représentant dans raw) + rattachement proche_20m du
    reliquat non rattaché. Idempotent."""
    from .ingestion.rnic import complements

    with session_scope() as s:
        res = complements(s, log=typer.echo)
    typer.echo(f"✓ RNIC compléments : {res}")


# (Commandes segments-seed / segments-counts / segments-residuel / ingest-catnat retirées
#  avec le spin-off « Vues » — M12 Lot C-bis. Les tables restent en base, données intactes.)


# ───────────── Wave Adresses, Courrier, Protection & Recherche IA ─────────────

@app.command("ingest-ban")
def ingest_ban_cmd(
    csv: str = typer.Option(None, help="CSV BAN 974 local (sinon --download)."),
    download: bool = typer.Option(False, "--download",
                                  help="Télécharge l'export officiel BAN 974 (Licence Ouverte)."),
    copros: bool = typer.Option(True, help="Rattache aussi les copros RNIC sans parcelle."),
) -> None:
    """Lot 1 (wave-adresses) : BAN 974 → table `adresses` rattachée aux parcelles.
    Refresh mensuel : deploy/cron.d/ban. Référence locale de TOUT géocodage du produit."""
    from pathlib import Path

    from .ingestion import ban_adresses

    if download or not csv:
        path = ban_adresses.download_ban_csv(Path("data/ban"))
    else:
        path = Path(csv)
    with session_scope() as s:
        res = ban_adresses.ingest_ban(s, path)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() "
                       "WHERE name = 'Base Adresse Nationale'"))
    typer.echo(f"✓ BAN : {res['adresses']} adresses, {res['liees']} rattachées "
               f"({100 * res['taux_liees']:.1f} %) en {res['duree_s']} s "
               f"[parcelle {res['parcelle']} · ban_cad {res['ban_cad']} · proche {res['proche_20m']}]")
    with session_scope() as s:
        cov = ban_adresses.couverture_bati_residentiel(s)
    seuil = "✓" if cov["taux"] >= 0.90 else "⚠"
    typer.echo(f"{seuil} Couverture bâti résidentiel : {cov['avec_adresse']}/{cov['parcelles_baties']} "
               f"({100 * cov['taux']:.1f} % — acceptation ≥ 90 %)")
    if copros:
        with session_scope() as s:
            rc = ban_adresses.rattacher_copros_par_adresse(s)
        typer.echo(f"✓ Copros RNIC par adresse : {rc['liees']} rattachée(s) sur {rc['candidates']} "
                   f"({rc['ambigues']} ambiguë(s), {rc['sans_match']} sans correspondance)")


@app.command("abuse-scan")
def abuse_scan_cmd(
    jour: str = typer.Option(None, help="Journée à scorer (YYYY-MM-DD, défaut : hier)."),
) -> None:
    """Lot 3 (wave-adresses) : score quotidien des patterns de scraping → abuse_scores.
    JAMAIS de blocage automatique : alerte admin, gel manuel par Vic. Cron : deploy/cron.d/abuse."""
    from datetime import date as _date

    from .api.protection import ensure_tables as prot_ensure
    from .api.protection import scan_abus

    prot_ensure(engine())
    j = _date.fromisoformat(jour) if jour else None
    with session_scope() as s:
        res = scan_abus(s, j)
    typer.echo(f"✓ abuse-scan {res['jour']} : {res['sujets']} sujet(s), "
               f"{res['alertes']} alerte(s) admin.")
    for sujet, det in sorted(res["scores"].items(), key=lambda kv: -kv[1]["score"])[:10]:
        typer.echo(f"  {sujet:26} score {det['score']:>3}  {det}")


# (Commande nl-eval retirée avec le spin-off « Vues » — M12 Lot C-bis : elle évaluait la
#  recherche NL → moteur de segments, parti avec « Vues ».)


# ─────────────────────────── Wave Détection Ortho ───────────────────────────

@app.command("ortho-pente")
def ortho_pente_cmd(batch: int = typer.Option(2000, help="Parcelles par lot (checkpoint).")) -> None:
    """Lot 1 (wave-ortho) : pente de la partie NON BÂTIE des parcelles bâties, depuis
    le raster de pente RGE ALTI 5 m conservé — complète parcel_terrain (réutilisée,
    jamais de table concurrente). Relançable (ne recalcule que les NULL)."""
    from .ingestion import ortho_pente

    with session_scope() as s:
        res = ortho_pente.run(s, log=typer.echo)
    typer.echo(f"✓ Pente non bâtie : {res}")
    if not res["sanity"]["ok"]:
        typer.echo("✗ SANITY : médiane bâties ≥ médiane île — bug projection/unités, INVESTIGUER.")
        raise typer.Exit(1)


@app.command("ortho-tiles")
def ortho_tiles_cmd(
    limit: int = typer.Option(None, help="Nb max de tuiles à acquérir (tests)."),
    grid_only: bool = typer.Option(False, "--grid-only", help="Construit la grille sans télécharger."),
) -> None:
    """Lot 2 (wave-ortho) : grille 512 m (bâti ∪ parkings) + acquisition BD ORTHO 20 cm
    par WMS Géoplateforme (millésime 974 = 2025), cache disque, reprise par tuile."""
    from .ingestion import ortho_tiles
    from .models import IngestionRun

    with session_scope() as s:
        n = ortho_tiles.build_grid(s)
        typer.echo(f"✓ grille : {n} nouvelle(s) tuile(s) utiles")
        if grid_only:
            return
        run = IngestionRun(commune="974 (tuiles ortho)", status="running")
        s.add(run)
        s.commit()  # libère les verrous : l'acquisition dure, d'autres jobs lisent ortho_tiles
        res = ortho_tiles.acquire(s, limit=limit, log=typer.echo)
        run.status = "ok" if not res["echecs"] else "partiel"
        run.parcels_count = res["acquises"]
        from sqlalchemy import func as _f
        run.finished_at = _f.now()
    typer.echo(f"✓ acquisition : {res}")


@app.command("ortho-detect")
def ortho_detect_cmd(
    limit: int = typer.Option(None, help="Nb max de tuiles (tests)."),
    skip_post: bool = typer.Option(False, "--skip-post", help="Détection seule, sans post-traitement SQL."),
) -> None:
    """Lot 3 (wave-ortho) : détection piscines V0 (HSV calibré config) sur les tuiles
    acquises + post-traitement contextuel (rattachement, rejets eau/toits bleus,
    confiance composite). Relançable (checkpoint = ortho_tiles.traite_at).
    Validation Vic : `labuse api` → /ortho/validation."""
    from .ingestion import ortho_piscines

    with session_scope() as s:
        res = ortho_piscines.detect_tiles(s, limit=limit, log=typer.echo)
        typer.echo(f"✓ détection : {res}")
        if not skip_post:
            post = ortho_piscines.post_traitement(s, log=typer.echo)
            typer.echo(f"✓ post-traitement : {post}")


@app.command("solaire-build")
def solaire_build_cmd(
    rps: float = typer.Option(None, help="Débit PVGIS (défaut config, 10 req/s)."),
    fetch_limit: int = typer.Option(None, help="Nb max de points PVGIS à récupérer (tests)."),
    skip_fetch: bool = typer.Option(False, "--skip-fetch", help="Sauter le fetch PVGIS (interpolation/flags seuls sur la grille déjà récupérée)."),
    rebuild_grid: bool = typer.Option(False, "--rebuild-grid", help="Reconstruire la grille solar_grid (efface les points existants)."),
) -> None:
    """SOLAIRE M1 — reconstruit parcel_solar depuis les sources (PVGIS + bâti + cascade + Filosofi).
    Idempotent et RÉSUMABLE (checkpoint = solar_grid.prod_spec NULL). Mensuel EN DB (12 + annuel +
    mois_optimal), azimut du bâti (Estimé), schéma 14 colonnes. Voir ingestion/solaire.py."""
    from .ingestion import solaire

    with session_scope() as s:
        res = solaire.run(s, rps=rps, rebuild_grid=rebuild_grid, skip_fetch=skip_fetch,
                          fetch_limit=fetch_limit, log=typer.echo)
        typer.echo(f"✓ solaire-build : {res}")


@app.command("ortho-materialise")
def ortho_materialise_cmd() -> None:
    """Lot 5 (wave-ortho) : matérialise parcel_equipements depuis les détections
    (profil strict + verdicts Vic) + signal piscine_detectee. Relançable."""
    from .ingestion import ortho_equipements

    with session_scope() as s:
        res = ortho_equipements.run(s, log=typer.echo)
    typer.echo(f"✓ matérialisation : {res}")


@app.command("ortho-detect-pv")
def ortho_detect_pv_cmd(limit: int = typer.Option(None, help="Nb max de tuiles (tests).")) -> None:
    """Lot 4 (wave-ortho) : détection PV V0 sur emprises bâties + parkings (candidats
    SCORÉS, cible ≥ 75 % à la validation) — CES 4-8 m² séparés, ombrières → equipe."""
    from .ingestion import ortho_pv

    with session_scope() as s:
        res = ortho_pv.detect_tiles(s, limit=limit, log=typer.echo)
        typer.echo(f"✓ détection PV : {res}")
        post = ortho_pv.post_traitement(s, log=typer.echo)
        typer.echo(f"✓ post-traitement PV : {post}")


@app.command("ortho-refresh")
def ortho_refresh_cmd(
    purge_cache: bool = typer.Option(False, "--purge-cache",
                                     help="Supprime les images du cache (garde les tables)."),
) -> None:
    """Lot 7 (wave-ortho) : la BD ORTHO 974 est re-survolée tous les ~3-4 ans — pas de
    cron. Détecte un changement de millésime (constante vs ortho_tiles), remet les
    tuiles concernées en file (acquisition + détections piscines/PV) et rejoue."""
    from .ingestion import ortho_tiles as ot

    with session_scope() as s:
        n = s.execute(text(
            "UPDATE ortho_tiles SET acquise_at = NULL, traite_at = NULL,"
            " pv_traite_at = NULL, millesime = :m WHERE millesime IS DISTINCT FROM :m"),
            {"m": ot.MILLESIME}).rowcount
    if n:
        typer.echo(f"✓ {n} tuile(s) remises en file (millésime {ot.MILLESIME}) — "
                   "enchaîner : labuse ortho-tiles && labuse ortho-detect && "
                   "labuse ortho-detect-pv && labuse ortho-materialise")
    else:
        typer.echo(f"✓ millésime {ot.MILLESIME} inchangé — rien à rejouer.")
    if purge_cache:
        n_p = ot.purge_cache()
        typer.echo(f"✓ cache purgé : {n_p} image(s) supprimée(s) (tables conservées)")


@app.command("ortho-juge-probe")
def ortho_juge_probe_cmd(
    etape: str = typer.Option("tout", help="crops | embeddings | mesure | tout"),
) -> None:
    """Cascade de juges, étage 1 : probe linéaire (DINOv2 gelé + logreg) —
    entraînée sur jeu='train', MESURÉE sur les 300 sanctuarisés. Critère Vic :
    précision ≥ 90 % en gardant ≥ 80 % des vrais → juge retenu, STOP cascade."""
    from .ml import probe

    with session_scope() as s:
        if etape in ("crops", "tout"):
            typer.echo(f"✓ crops : {probe.extraire_crops(s, log=typer.echo)}")
        if etape in ("embeddings", "tout"):
            typer.echo(f"✓ embeddings : {probe.calculer_embeddings(log=typer.echo)}")
        if etape in ("mesure", "tout"):
            res = probe.entrainer_et_mesurer(s, log=typer.echo)
            for pt in res["courbe"]:
                typer.echo(f"  seuil {pt['seuil']} : précision {pt['precision']}, "
                           f"rappel des vrais {pt['rappel_vrais']} ({pt['gardees']} gardées)")
            typer.echo(f"{'✓ CRITÈRE ATTEINT' if res['critere_atteint'] else '✗ critère non atteint'}"
                       f" : {res.get('point')}")


@app.command("ortho-juge-vlm")
def ortho_juge_vlm_cmd(
    cible: str = typer.Option("sanctuaire", help="sanctuaire (mesure 300) | tout (re-score complet)"),
    type_: str = typer.Option("piscine", "--type", help="piscine | pv"),
) -> None:
    """Cascade de juges, étage 2 : juge VLM (Haiku 4.5, prompt binaire + confiance,
    cadre rouge sur le candidat). Coût estimé : 0,16 $ (mesure 300) / ~10-11 $
    (re-score 19 899). Mesure TOUJOURS sur le jeu sanctuarisé."""
    from .ml import juge_vlm

    with session_scope() as s:
        if cible == "sanctuaire":
            ids = [i for (i,) in s.execute(text(
                "SELECT id FROM ortho_detections WHERE jeu = 'validation'")).all()]
        else:
            ids = [i for (i,) in s.execute(text(
                "SELECT id FROM ortho_detections WHERE type = :t"), {"t": type_}).all()]
        typer.echo(f"→ {len(ids)} détections à juger ({cible})")
        res = juge_vlm.juger(s, ids, log=typer.echo)
        typer.echo(f"✓ juge VLM : {res}")
        if cible == "sanctuaire":
            m = juge_vlm.mesurer_sur_sanctuaire(s)
            for pt in m["courbe"]:
                typer.echo(f"  conf ≥ {pt['conf_min']} : précision {pt['precision']}, "
                           f"rappel des vrais {pt['rappel_vrais']} ({pt['gardees']} gardées)")
            typer.echo(f"{'✓ CRITÈRE ATTEINT' if m['critere_atteint'] else '✗ critère non atteint'}"
                       f" : {m.get('point')}")


@app.command("fraicheur-etat")
def fraicheur_etat_cmd() -> None:
    """J+2 — la matrice des sources : cadence réelle × dernière donnée × dernière ingestion × delta."""
    from .ingestion import fraicheur

    with session_scope() as s:
        for r in fraicheur.etat_sources(s):
            typer.echo(f"{r['source']:<12} {r['cadence']:<34} donnée {r['derniere_donnee'] or '—':<11} "
                       f"ingestion {r['derniere_ingestion'] or '—':<11} Δ{r['delta_donnee_jours']} j"
                       f"{'' if r['auto'] else '  [détection seule — grande passe requise]'}")


@app.command("check-fraicheur")
def check_fraicheur_cmd() -> None:
    """M84 — la SENTINELLE : verdict live de chaque source (statut dérivé de sa cadence). Code de
    sortie 1 si au moins une source est en RETARD (delta > 2× cadence) → le cron le DIT (mail/log),
    une source ne peut plus décrocher en silence. Les cadences libres (event-driven/annuel) et sans
    donnée ne comptent jamais comme un retard (anti-faux-positif — cf. DVF, SITADEL à 45 j)."""
    from .ingestion import fraicheur

    with session_scope() as s:
        etats = fraicheur.etat_sources(s)
    retards = [e for e in etats if e["statut"] == "en_retard"]
    for e in etats:
        marque = {"en_retard": "⚠ RETARD", "a_jour": "✓", "cadence_libre": "·", "sans_donnee": "?"}[e["statut"]]
        seuil = f"seuil {e['seuil_jours']} j" if e["seuil_jours"] else "cadence libre"
        typer.echo(f"{marque:<9} {e['source']:<12} donnée {e['derniere_donnee'] or '—':<11} "
                   f"Δ{e['delta_donnee_jours']} j ({seuil})")
    if retards:
        typer.echo(f"⚠ {len(retards)} source(s) EN RETARD : {', '.join(r['source'] for r in retards)}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✓ fraîcheur : aucune source en retard ({len(etats)} évaluées).")


@app.command("sentinelle-inventaire")
def sentinelle_inventaire_cmd(
    sortie: str = typer.Option("docs/audit-2026-09/SENTINELLE-INVENTAIRE.md", help="fichier Markdown à (ré)écrire"),
) -> None:
    """SENTINELLE-3 (Y5.2) — RÉGÉNÈRE l'inventaire des 64 sources DEPUIS LE CATALOGUE (jamais à la main) :
    croise `seed_sources.SOURCES` avec SEED / RAPPELS / RAISONS / DOUBLONS, enrichit le millésime servi
    depuis `data_sources` si la base est joignable, écrit le fichier. Le contenu EST l'état du code."""
    from pathlib import Path

    from . import sentinelle
    millesimes: dict[str, str] = {}
    try:
        from sqlalchemy import text as _t
        with session_scope() as s:
            for r in s.execute(_t("SELECT name, source_millesime FROM data_sources "
                                  "WHERE source_millesime IS NOT NULL")).mappings():
                millesimes[r["name"]] = r["source_millesime"]
    except Exception:  # noqa: BLE001 — base absente = on génère depuis le catalogue seul (millésime catalogue)
        pass
    md = sentinelle.inventaire_markdown(millesimes or None)
    Path(sortie).write_text(md, encoding="utf-8")
    typer.echo(f"✓ Inventaire régénéré : {sortie} ({md.count(chr(10)) + 1} lignes, "
               f"{len(millesimes)} millésimes lus en base)")


@app.command("ingest-bodacc")
def ingest_bodacc_cmd() -> None:
    """J+2 — BODACC quotidien : ré-interroge (batché) les SIREN propriétaires, upsert idempotent."""
    from .ingestion import fraicheur

    with session_scope() as s:
        r = fraicheur.ingest_bodacc_quotidien(s, log_fn=typer.echo)
        typer.echo(f"✓ BODACC : {r['sirens']} SIREN, dernière annonce {r['derniere_annonce']}")


@app.command("ingest-mairies")
def ingest_mairies_cmd() -> None:
    """K2 — coordonnées des 24 mairies depuis l'Annuaire de l'administration (service-public.fr).
    Upsert par INSEE, champ absent = NULL (jamais inventé), date de récupération stockée. À relancer
    quand les coordonnées changent (les mairies déménagent, changent de téléphone)."""
    from .ingestion import mairies

    with session_scope() as s:
        r = mairies.ingest(s)
    typer.echo(f"✓ Mairies : {r['trouvees']}/{r['communes']} ingérées"
               + (f" — absentes de l'annuaire : {', '.join(r['absentes'])}" if r["absentes"] else ""))


@app.command("radar-depot-html")
def radar_depot_html_cmd(
    fichier: str = typer.Argument(..., help="page de résultats HTML enregistrée (Cmd+S, « page web complète »)"),
) -> None:
    """RADAR-HTML (Lot 1) — ingère une page de résultats HTML déposée (remplace capture/vision). Idempotent
    par list_id. Échoue BRUYAMMENT si __NEXT_DATA__ est absent/altéré (jamais un « 0 annonce » silencieux)."""
    from pathlib import Path

    from .pige import html_ingest, html_next
    html = Path(fichier).read_text(encoding="utf-8")
    try:
        with session_scope() as s:
            r = html_ingest.ingester(s, html, Path(fichier).name)
    except html_next.NextDataError as exc:
        typer.echo(f"✗ ÉCHEC BRUYANT : {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"✓ Radar HTML : {r['nb_annonces']} annonces — {r['nb_nouvelles']} nouvelles, "
               f"{r['nb_maj']} MAJ, {r['nb_a_qualifier']} à qualifier "
               f"(rattachement : {r['etats']}) · archive {r['archive']}")


@app.command("radar-cycle-quotidien")
def radar_cycle_quotidien_cmd() -> None:
    """RADAR P5 — cycle de vie QUOTIDIEN (heure Réunion) : en_vente_longue (> 90 j publication) +
    a_reverifier (> 60 j sans confirmation). Idempotent. À poser au crontab (voir EXPLOITATION-CRON.md)."""
    from .pige import cycle
    with session_scope() as s:
        r = cycle.run_quotidien(s)
    typer.echo(f"✓ Radar quotidien : {r['en_vente_longue']} → en vente longue, {r['a_reverifier']} → à revérifier")


@app.command("radar-cycle-dvf")
def radar_cycle_dvf_cmd() -> None:
    """RADAR P5 — rapprochement DVF (vendue) : à lancer APRÈS chaque ingestion DVF. Rattachement SOURCÉ
    uniquement + mutation DVF « Vente » dans [3;18] mois après publication → vendue + écart de prix."""
    from .pige import cycle
    with session_scope() as s:
        r = cycle.run_dvf(s)
    typer.echo(f"✓ Radar DVF : {r['vendue']} bien(s) rapproché(s) → vendue")


@app.command("radar-cycle-mensuel")
def radar_cycle_mensuel_cmd() -> None:
    """RADAR P5 — qualification MENSUELLE retiree_sans_vente (cible Courrier) : retirée + rattachée +
    > 12 mois + AUCUNE vente DVF. JAMAIS déduit d'un lien mort."""
    from .pige import cycle
    with session_scope() as s:
        r = cycle.run_mensuel(s)
    typer.echo(f"✓ Radar mensuel : {r['retiree_sans_vente']} → retirée sans vente")


@app.command("radar-digests")
def radar_digests_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="ne rien envoyer, écrire le HTML produit dans --dry-dir"),
    dry_dir: str = typer.Option("outputs/radar-digests", "--dry-dir", help="dossier où écrire le HTML (dry-run)"),
) -> None:
    """RADAR-DIGESTS — les DEUX envois de fin de journée (heure Réunion) : (a) digest quotidien
    (template Brevo 12) à tous les clients actifs + (b) alerte de veille (template 13), un mail par
    veille déclenchée. Jamais un mail vide, idempotent sur la journée, échec bruyant."""
    from .pige import digests
    base = get_settings().public_url or ""
    with session_scope() as s:
        r = digests.envoyer(s, base_url=base, dry_run=dry_run, dry_dir=(dry_dir if dry_run else None))
    typer.echo(f"✓ Radar digests : {r['n_biens_du_jour']} nouveauté(s) du jour · "
               f"{r['envoyes']} envoyé(s), {r['echecs']} échec(s), {r['simules']} simulé(s), "
               f"{r['deja']} déjà envoyé(s)" + (f" [dry-run → {dry_dir}]" if dry_run else ""))
    if r["echecs"]:
        typer.echo(f"⚠ {r['echecs']} échec(s) d'envoi — voir la cloche système du dashboard (templates Brevo 12 et 13 montés ?)")


@app.command("ingest-pm-millesimes")
def ingest_pm_millesimes_cmd(
    annees: str = typer.Option("2019-2024", help="millésimes à (ré)ingérer, ex. « 2019-2024 » ou « 2025 »"),
    fraicheur_seule: bool = typer.Option(False, "--fraicheur-seule",
                                         help="ne rien télécharger, poser seulement la fraîcheur du catalogue"),
) -> None:
    """KF-2 L1/L3 — panel millésimes DGFiP « parcelles des personnes morales » (Licence Ouverte v2,
    situation au 1ᵉʳ janvier) → table VERSIONNÉE pm_proprietaires_millesimes (jamais la table servie).
    Cadence ANNUELLE. Idempotent (DELETE+réinsertion par millésime). Pose ensuite la fraîcheur du
    catalogue (dashboard admin). Le 2025 est servi par la table de prod ; l'ingérer ici est optionnel."""
    from .ingestion import pm_millesimes as pmm

    if not fraicheur_seule:
        a, _, b = annees.partition("-")
        bornes = range(int(a), int(b) + 1) if b else [int(a)]
        for annee in bornes:
            if annee not in pmm.MILLESIME_ATTACHMENTS:
                typer.echo(f"· millésime {annee} : aucun attachment connu — ignoré")
                continue
            csv_path = pmm.fetch_974_csv(annee)
            with session_scope() as s:
                r = pmm.ingest_millesime(s, annee, csv_path, log=lambda m: typer.echo(f"  {m}"))
            typer.echo(f"✓ millésime {annee} : {r['parcelles']} parcelles PM")
    with session_scope() as s:
        pose = pmm.enregistrer_fraicheur(s)
    typer.echo(f"✓ fraîcheur catalogue posée : {pose or 'panel vide'}")


@app.command("refresh-dvf")
def refresh_dvf_cmd() -> None:
    """J+2 — DVF : détecte une nouvelle livraison Etalab (Last-Modified) et recharge SEULEMENT
    les millésimes modifiés (idempotent). No-op si rien de neuf — on ne retélécharge pas ce qu'on a."""
    from .ingestion import fraicheur

    with session_scope() as s:
        r = fraicheur.refresh_dvf(s, log_fn=typer.echo)
        typer.echo("✓ DVF : no-op (aucune livraison)" if r["no_op"] else f"✓ DVF rechargé : {r['recharges']}")


@app.command("stripe-provisionne")
def stripe_provisionne_cmd() -> None:
    """Crée les deux produits Stripe (Intégral 349 €/mois récurrent · Flash 79 € paiement unique)
    idempotemment (par lookup_key) et affiche les IDs à poser en .env. Prix = offres.py (source
    unique). Mode = celui de la clé (sk_test_ = test, sk_live_ = live)."""
    from .facturation import provisionner

    ids = provisionner()
    typer.echo("IDs Stripe (à poser en .env — la source de vérité de l'environnement) :")
    for k, v in ids.items():
        typer.echo(f"  {k.upper()}={v}")


@app.command("stripe-verifie")
def stripe_verifie_cmd() -> None:
    """E5 — VÉRIFIE (lecture seule) que les Prix Stripe pointés par .env correspondent EXACTEMENT
    aux offres affichées (Intégral 349 €/mois, Flash 79 € unique). À lancer contre le mode TEST
    ET le mode LIVE (une clé à la fois). Sort non-zéro si un écart existe — ne modifie jamais Stripe."""
    from .facturation import verifier_prix_stripe

    lignes = verifier_prix_stripe()
    tout_ok = True
    for r in lignes:
        if r.get("ok"):
            typer.echo(f"  ✓ {r['offre']:9} {r['stripe_eur']} € {r['recurrence']} (= l'affiché)")
        else:
            tout_ok = False
            typer.echo(f"  ✗ {r['offre']:9} ÉCART — {r.get('detail')}")
    if tout_ok:
        typer.echo("✓ Stripe et l'app affichent le MÊME prix.")
    else:
        typer.echo("✗ Écart Stripe ⇄ app — corrigez le price_id en .env ou re-provisionnez "
                   "(NE PAS modifier un prix LIVE sans arbitrage Vic).")
        raise typer.Exit(1)


@app.command("compte-invite")
def compte_invite_cmd(
    email: str,
    nom: str = typer.Option(None, help="Nom du compte (défaut : l'email)"),
) -> None:
    """PREMIER EURO — crée l'invitation INTÉGRAL (349 €/mois, 1 licence) et AFFICHE le lien
    (refonte 22/07 : aucun email automatique — Vic l'envoie à la main)."""
    from .comptes import creer_invitation

    with session_scope() as s:
        inv = creer_invitation(s, email, nom=nom)
    typer.echo(f"invitation créée — compte #{inv['compte_id']} · {inv['email']} · expire {inv['expire_at'][:10]}")
    typer.echo("LIEN À ENVOYER À LA MAIN (seul exemplaire, en base : le hash) :")
    typer.echo(f"  {inv['lien']}")


@app.command("compte-reset-lien")
def compte_reset_lien_cmd(email: str) -> None:
    """Génère et AFFICHE le lien de réinitialisation (1 h) — à transmettre à la main."""
    from .comptes import demander_reset

    with session_scope() as s:
        r = demander_reset(s, email)
    if not r:
        typer.echo("email inconnu ou compte non actif", err=True); raise typer.Exit(1)
    typer.echo("LIEN DE RESET (1 h, à envoyer à la main) :")
    typer.echo(f"  {r['lien']}")


@app.command("compte-admin")
def compte_admin_cmd(email: str) -> None:
    """Crée LE compte admin (Vic) — mot de passe demandé au clavier, jamais en argv/historique."""
    import getpass

    from .comptes import creer_admin

    pw = getpass.getpass("Mot de passe admin (≥ 10 caractères) : ")
    if len(pw) < 10:
        typer.echo("trop court", err=True); raise typer.Exit(1)
    if getpass.getpass("Confirmez : ") != pw:
        typer.echo("les deux saisies diffèrent", err=True); raise typer.Exit(1)
    with session_scope() as s:
        uid = creer_admin(s, email, pw)
    typer.echo(f"admin créé (utilisateur #{uid}) — testez le login sur /login AVANT toute bascule")


@app.command("admin-list")
def admin_list_cmd() -> None:
    """SUITE-1 · S8 — liste les comptes admin (email · utilisateur#id · compte#id · statut · créé le).
    Lecture seule, pour l'exploitation en production (déploiement)."""
    from .comptes import lister_admins

    with session_scope() as s:
        admins = lister_admins(s)
    if not admins:
        typer.echo("aucun compte admin.")
        return
    typer.echo(f"{len(admins)} compte(s) admin :")
    for a in admins:
        cree = (a["created_at"] or "")[:10]
        typer.echo(f"  {a['email']:<40} utilisateur#{a['utilisateur_id']} · compte#{a['compte_id']} "
                   f"· {a['statut']:<9} · créé le {cree}")


@app.command("admin-set")
def admin_set_cmd(
    email: str,
    on: bool = typer.Option(False, "--on", help="Promeut l'utilisateur au rôle admin"),
    off: bool = typer.Option(False, "--off", help="Rétrograde l'utilisateur (rôle titulaire)"),
    oui: bool = typer.Option(False, "--oui", help="Ne pas demander de confirmation interactive"),
) -> None:
    """SUITE-1 · S8 — promeut (--on) ou rétrograde (--off) un utilisateur EXISTANT, journalisé.
    Confirmation demandée (sauf --oui). Idempotent : si le rôle est déjà celui demandé, ne fait rien."""
    from .comptes import definir_role_admin

    if on == off:
        typer.echo("choisir exactement --on OU --off", err=True); raise typer.Exit(2)
    action = "PROMOUVOIR admin" if on else "RÉTROGRADER (titulaire)"
    if not oui:
        rep = input(f"{action} « {email} » ? [oui/non] ").strip().lower()
        if rep not in ("oui", "o", "yes", "y"):
            typer.echo("annulé."); raise typer.Exit(1)
    with session_scope() as s:
        try:
            r = definir_role_admin(s, email, admin=on)
        except ValueError as exc:
            typer.echo(str(exc), err=True); raise typer.Exit(1)
    if not r["change"]:
        typer.echo(f"aucun changement — « {r['email']} » est déjà au rôle « {r['role']} ».")
    else:
        typer.echo(f"« {r['email']} » → rôle « {r['role']} » (utilisateur#{r['utilisateur_id']}, journalisé).")


@app.command("creer-admin")
def creer_admin_cmd(
    email: str,
    nom: str = typer.Option(None, help="Nom du compte interne (défaut : dérivé de l'email)"),
) -> None:
    """VPS · AC-020 — admin NOMINATIF : crée (ou promeut) un utilisateur rôle admin sur un
    compte interne actif, et AFFICHE le lien d'invitation pour poser le mot de passe (jamais
    de mot de passe en argv/historique). Idempotent — relancer ne casse rien. Au premier
    login, la 2FA TOTP s'enrôle (AC-025)."""
    from .comptes import creer_admin_invitation

    with session_scope() as s:
        r = creer_admin_invitation(s, email, nom=nom)
    if r["promu"]:
        typer.echo(f"utilisateur #{r['utilisateur_id']} PROMU admin (compte #{r['compte_id']})")
    else:
        typer.echo(f"admin — utilisateur #{r['utilisateur_id']} · compte #{r['compte_id']} · {r['email']}")
    if r["lien"]:
        typer.echo(f"LIEN D'INVITATION (pose le mot de passe ; expire {r['expire_at'][:10]}) :")
        typer.echo(f"  {r['lien']}")
        typer.echo("  → l'écran d'activation admin (sans paiement) demande un mot de passe ;")
        typer.echo("    la double authentification (2FA) s'enrôle à la première connexion sur /login.")
    else:
        # E2 — cas « déjà promu, mot de passe posé » (Vic ce soir) : rien à (re)poser, la porte
        # est /login et la 2FA s'enrôle au premier passage admin. Le reset reste un filet.
        typer.echo("mot de passe déjà posé — ce compte est prêt.")
        typer.echo("  → connectez-vous sur /login : la double authentification (2FA) s'enrôle")
        typer.echo("    automatiquement au premier passage administrateur (QR + codes de secours).")
        typer.echo("  (mot de passe oublié ? `labuse compte-reset-lien " + email + "`)")


@app.command("compte-suspend")
def compte_suspend_cmd(compte_id: int, motif: str = typer.Option("manuel")) -> None:
    """Suspend un compte (sessions révoquées ≤ 60 s) — l'app affiche « paiement requis »/« suspendu »."""
    from .comptes import suspendre_compte

    with session_scope() as s:
        suspendre_compte(s, compte_id, motif)
    typer.echo(f"compte #{compte_id} suspendu ({motif})")


@app.command("compte-reactive")
def compte_reactive_cmd(compte_id: int, motif: str = typer.Option("manuel")) -> None:
    """Réactive un compte suspendu."""
    from .comptes import reactiver_compte

    with session_scope() as s:
        reactiver_compte(s, compte_id, motif)
    typer.echo(f"compte #{compte_id} réactivé")


@app.command("compte-supprime")
def compte_supprime_cmd(email: str, oui: bool = typer.Option(False, "--oui", help="confirmation")) -> None:
    """EFFACEMENT RGPD : purge l'utilisateur (sessions comprises), anonymise l'audit."""
    if not oui:
        typer.echo("ajoutez --oui pour confirmer l'effacement définitif", err=True); raise typer.Exit(1)
    from .comptes import effacer_compte_rgpd

    with session_scope() as s:
        ok = effacer_compte_rgpd(s, email)
    typer.echo("effacé (RGPD : compte + projets + CRM + veilles)" if ok else "email inconnu")


@app.command("cgv-preuve")
def cgv_preuve_cmd(email: str = typer.Option(None, help="un email, ou tous si omis")) -> None:
    """LEX-D — preuve de consentement CGV EXPORTABLE : qui a accepté quelle version, quand."""
    from sqlalchemy import text as _t

    with session_scope() as s:
        rows = s.execute(_t(
            "SELECT email, cgv_version, cgv_acceptees_at FROM utilisateurs"
            " WHERE cgv_acceptees_at IS NOT NULL"
            + (" AND email = :e" if email else "") + " ORDER BY cgv_acceptees_at"),
            ({"e": email.strip().lower()} if email else {})).mappings().all()
    if not rows:
        typer.echo("aucun consentement enregistré"); return
    for r in rows:
        typer.echo(f"{r['cgv_acceptees_at'].isoformat()} · {r['email']} · CGV {r['cgv_version']}")


@app.command("radar-sources")
def radar_sources_cmd() -> None:
    """BLOC B (B3) — le radar des sources : sonde HEAD/métadonnées sur chaque source
    (zéro téléchargement), écrit `source_radar`, affiche les publications détectées.
    Le radar SIGNALE, l'humain DÉCIDE — jamais d'auto-ingestion (cascade gelée)."""
    from .radar import run_radar

    with session_scope() as s:
        r = run_radar(s)
    # M124 P0 — clé alignée sur run_radar M123 (`manuelles` a remplacé `non_sondables`) :
    # le cron hebdo crashait sur KeyError APRÈS l'écriture (affichage seul, données intactes).
    typer.echo(f"radar : {r['sondees']} sondées · {len(r['changements'])} publication(s) détectée(s)"
               f" · {r['manuelles']} suivies à la main · {r['erreurs']} erreurs")
    for c in r["changements"]:
        typer.echo(f"  ↗ {c['source']} : {c['avant']} → {c['apres']}")


@app.command("fraicheur-derives")
def fraicheur_derives_cmd(
    hebdo: bool = typer.Option(False, help="Inclure les dérivés lourds (m10 délais/vélocité, re-fetch réseau)."),
) -> None:
    """J+2 — chaîne post-ingestion : rebuild des dérivés LÉGERS (caducs, defisc, surface_d, compteur
    réveil DPE). NE TOUCHE JAMAIS les tables de run — le rang servi reste gelé (grande passe Mac)."""
    from .ingestion import fraicheur

    with session_scope() as s:
        r = fraicheur.run_derives(s, hebdo=hebdo, log_fn=typer.echo)
        typer.echo(f"✓ dérivés : {list(r)} · réveil DPE {r['dpe_reveil']['n']}/{r['dpe_reveil']['seuil']}")


@app.command("deposants-actifs")
def deposants_actifs_cmd(
    mois: int = typer.Option(24, help="Fenêtre de dépôt (mois)."),
    out: str = typer.Option("exports/deposants_actifs.csv", help="CSV de sortie (exports/ = gitignoré)."),
) -> None:
    """EXTRACT-DÉPOSANTS-ACTIFS : CSV de prospection des PM déposant des PC/PA (read-only).
    Dirigeants RNE actifs+diffusibles uniquement ; données nominatives jamais en git (exports/)."""
    from .ingestion import deposants_actifs

    with session_scope() as s:
        rows = deposants_actifs.extract_deposants(s, mois=mois)
    p = deposants_actifs.write_csv(rows, out)
    typer.echo(f"✓ {len(rows)} déposants actifs ({mois} mois) → {p} (gitignoré, ne pas committer)")


@app.command("prospection-notion")
def prospection_notion_cmd(
    mois: int = typer.Option(24, help="Fenêtre de dépôt (mois)."),
    out: str = typer.Option("exports/prospection_notion.csv", help="CSV d'import Notion (exports/ = gitignoré)."),
    enrich: bool = typer.Option(True, help="Enrichir adresse/ville du siège via l'API publique recherche-entreprises."),
) -> None:
    """PROSPECTION-NOTION : LE CSV d'import Notion « Prospection LABUSE », prêt sans retouche (read-only).
    En-têtes exacts de la base + tag « Entité publique » + « Segment » heuristique + adresse siège
    (open data INSEE/INPI). Séparateur virgule, UTF-8 avec BOM. Données nominatives jamais en git (exports/)."""
    from .ingestion import prospection_notion

    with session_scope() as s:
        stats = prospection_notion.generate(s, out=out, mois=mois, enrich=enrich, log_fn=typer.echo)
    typer.echo(
        f"✓ {stats['n_lignes']} lignes → {stats['path']} (gitignoré, ne pas committer) · "
        f"{stats['n_publiques']} entités publiques taguées · "
        f"adresse siège : {stats['n_adresse']}/{stats['n_lignes']} ({stats['taux_adresse']} %)"
    )


@app.command("division-or")
def division_or_cmd(
    communes: str = typer.Option(None, help="Communes (virgules) — NOM « Saint-Paul » OU code INSEE "
                                            "« 97415 » ; les deux acceptés (M50-SUITE). Ignoré si --all."),
    all_communes: bool = typer.Option(False, "--all", help="Toute l'île (24 communes, réf "
                                      "commune_conso_enaf) — un rebuild qui n'en oublie aucune (M50-SUITE-2)."),
) -> None:
    """O12 — Division en or (MASQUÉ) : détecte les parcelles à lot détachable constructible.
    `--communes` accepte le NOM ou le code INSEE ; `--all` = les 24 communes de l'île. Rebuild par
    commune : la commune est PURGÉE avant réécriture (un rebuild à 0 laisse la commune VIDE, pas
    périmée ; tracés revus préservés) et COMMITÉE par commune (durable/reprenable, M50-SUITE-2).
    Table division_or_candidates (flag EXPOSE=False). Exposition = APRÈS validation du dossier 20 cartes par Vic."""
    from .ingestion import division_or

    with session_scope() as s:
        if all_communes:
            cibles = division_or.all_communes(s)
            if not cibles:
                raise typer.BadParameter("réf commune_conso_enaf absente — --all indisponible")
        elif communes:
            cibles = [c.strip() for c in communes.split(",") if c.strip()]
        else:
            raise typer.BadParameter("préciser --communes <NOM|INSEE,...> ou --all")
        r = division_or.build_divisions(s, cibles, log=typer.echo)
        # M129-C : la famille DÉCOUPE (O12-PARTIEL, bande de façade) rejoint le GESTE UNIQUE —
        # elle n'avait JAMAIS été câblée au CLI (build_divisions_partiel orpheline, mesuré).
        rp = division_or.build_divisions_partiel(s, cibles, log=typer.echo)
        fails = (r.get("failures") or []) + (rp.get("failures") or [])
        if fails:
            typer.echo(f"⚠ {len(fails)} commune(s)/famille(s) en échec (île poursuivie, non "
                       f"écrites) : {', '.join(fails)} — voir les lignes ÉCHEC ci-dessus.")
        typer.echo(f"✓ division_or_candidates : {r['total']} résiduelle + {rp.get('total', 0)} découpe")


@app.command("division-or-review")
def division_or_review_cmd(
    out: str = typer.Option("division_or_revue.pdf", help="Chemin du PDF de revue."),
    limit: int = typer.Option(20, help="Nombre de cartes (candidats les plus clairs)."),
    communes: str = typer.Option(None, help="Échantillonnage équilibré sur ces communes (séparées par des virgules)."),
    type_division: str = typer.Option(None, "--type", help="Restreindre à un type : libre | demolition."),
    exhaustif: bool = typer.Option(False, "--all", help="TOUT le pool (découpes par commune puis résiduels) — revue 2."),
) -> None:
    """O12 — génère le DOSSIER DE REVUE pour validation visuelle de Vic (--all = pool complet)."""
    from .ingestion import division_or
    from .api import division_review

    with session_scope() as s:
        if exhaustif:
            cands = division_or.all_candidates_for_review(s)
        else:
            cands = division_or.top_candidates(
                s, limit=limit,
                communes=[c.strip() for c in communes.split(",") if c.strip()] if communes else None,
                type_division=type_division)
        if not cands:
            typer.echo("Aucun candidat — lancer d'abord `division-or --communes …`.")
            raise typer.Exit(1)
        pdf = division_review.build_review_dossier(s, cands)
    with open(out, "wb") as f:
        f.write(pdf)
    typer.echo(f"✓ dossier de revue : {out} ({len(cands)} cartes) — à valider par Vic")


@app.command("surface-d")
def surface_d_cmd() -> None:
    """O10 — Surface D (MOTEUR) : (re)construit surface_d_events (bascules datées par parcelle).
    Sources branchées : défisc, PC caducs, DPE passoire F/G, permis rattachés. Notification = post-M7."""
    from .ingestion import surface_d

    with session_scope() as s:
        r = surface_d.build_events(s, log=typer.echo)
        typer.echo(f"✓ surface_d_events : {r['total']} événements — {r['par_type']}")


@app.command("surface-d-events")
def surface_d_events_cmd(
    type_filtre: str = typer.Option(None, "--type", help="Filtrer par type d'événement."),
    limit: int = typer.Option(20, help="Nombre d'événements récents à afficher."),
) -> None:
    """O10 — test/diagnostic du moteur : affiche les bascules datées les plus récentes."""
    from .ingestion import surface_d

    with session_scope() as s:
        for e in surface_d.recent_events(s, limit=limit, type_filtre=type_filtre):
            typer.echo(f"{e['date_evenement']}  {e['type']:<22} {e['idu']}  {e['detail'][:60]}")


@app.command("prix-neuf")
def prix_neuf_cmd() -> None:
    """O0 — Prix de sortie NEUF par secteur (ventes ≤ 3 ans après achèvement PC), repli commune.
    Table additive dvf_prix_sortie_neuf. Lecture seule des sources ; prérequis du Score É V2."""
    from .ingestion import dvf_prix_neuf

    with session_scope() as s:
        r = dvf_prix_neuf.build_prix_neuf(s, log=typer.echo)
        typer.echo(f"✓ dvf_prix_sortie_neuf : {r['secteurs']} secteurs + {r['communes']} communes")


@app.command("rnu-pau")
def rnu_pau_cmd() -> None:
    """MANDAT RNU : matérialise les PAU (parties actuellement urbanisées ESTIMÉES) des
    communes sans document local (config/rnu_communes.yaml — méthode et paramètres VALIDÉS,
    en config jamais en dur). Tables additives commune_pau/parcel_pau ; le plancher C les
    lit au prochain `labuse score-v2` — jamais rétroactivement. La PAU est une ESTIMATION :
    la délimitation relève de l'appréciation du service instructeur."""
    from . import rnu

    with session_scope() as s:
        r = rnu.build_pau(s, log=typer.echo)
        typer.echo(f"✓ rnu-pau : {len(r['communes'])} commune(s) traitée(s) · params {r['params']}")


@app.command("renouv")
def renouv_cmd(
    run: str = typer.Option(None, help="Run servi dont lire l'étage 0 (défaut : Q_A_RUN_LABEL)."),
    top_n: int = typer.Option(20, help="Taille du top affiché."),
    commune: str = typer.Option(None, help="Limiter le top à une commune (code INSEE)."),
) -> None:
    """SEGMENT RENOUVELLEMENT (M-RENOUV) : parcelles écartées « déjà bâties » à l'étage 0 mais en
    zone U/AU avec capacité réelle → potentiel de renouvellement urbain (JAMAIS « opportunité »).
    Table additive parcel_renouvellement ; heuristique déterministe (config/renouvellement.yaml) ;
    lecture seule des sources — ne touche jamais la cascade ni les tiers servis."""
    from . import renouvellement

    with session_scope() as s:
        r = renouvellement.build(s, run_label=run, log=typer.echo)
        typer.echo(f"✓ segment Renouvellement : {r['n']} parcelles (run {r['run_label']}, "
                   f"as-of {r['annee']})")
        typer.echo("Entonnoir :")
        libelles = {
            "1_bati_fait": "bâti franc (fait M129 — codes francs)",
            "2_zone_u_au": "∩ zone U/AU",
            "3_capacite": (f"∩ capacité (SDP > {r['seuils']['sdp_min_m2']} m² "
                           f"ou surface ≥ {r['seuils']['surface_min_m2']} m²)"),
            "4_hors_copro": "− copropriétés",
            "5_hors_foncier_public_final": "− foncier public (SEGMENT FINAL)",
        }
        for k, lib in libelles.items():
            typer.echo(f"  {r['funnel'][k]:>7}  {lib}")
        rows = renouvellement.top(s, n=top_n, commune=commune)
        titre = f"commune {commune}" if commune else "île"
        typer.echo(f"\nTop {len(rows)} ({titre}) — score /100 (pot+ass+mar) :")
        for t in rows:
            typer.echo(
                f"  #{t['rang_segment']:<5} {t['idu']}  {t['renouv_score']:>3} "
                f"({t['comp_potentiel']}+{t['comp_assiette']}+{t['comp_marche']})  "
                f"{t['zone_plu']:<3} sdp={t['sdp_residuelle_m2'] or 0:>5} surf={t['surface_m2']:>6}  "
                f"{t['code_bati_origine']}")


@app.command("score-e")
def score_e_cmd(
    run: str = typer.Option(None, help="Run servi dont scorer les parcelles non-écartées (défaut : run servi Q_A_RUN_LABEL)."),
    prix_neuf: bool = typer.Option(True, help="Reconstruire d'abord dvf_prix_sortie_neuf (O0)."),
) -> None:
    """SCORE É V2 (O0) : marge estimée (€) = charge foncière supportable (prix de sortie NEUF) − prix probable.
    Table additive score_e (Estimé partout). Lecture seule des sources ; ne touche jamais les runs servis."""
    from . import runs
    from .ingestion import score_e, dvf_prix_neuf  # M44 Lot 0 : point de vérité (plus de q_v7 en dur)

    with session_scope() as s:
        if prix_neuf:
            dvf_prix_neuf.build_prix_neuf(s, log=typer.echo)
        r = score_e.build_score_e(s, run=run or runs.current(), log=typer.echo)
        typer.echo(f"✓ score_e : {r['total']} non-écartées, {r['estimables']} marge estimable")


@app.command("pc-caducs")
def pc_caducs_cmd(
    ref_year: int = typer.Option(2026, help="Année de référence (caduc probable pour Y ≤ ref_year-4)."),
) -> None:
    """Phase A cycle 2 — badge « PC caducs » : table additive pc_caducs (PC octroyé jamais achevé,
    état Sitadel). Signal parcellaire horodaté ; lecture seule des sources ; ne touche jamais les runs
    servis. Autorisation Sourcé (Sitadel), caducité Estimé (inférée) ; jamais un jugement du propriétaire."""
    from .ingestion import pc_caducs

    with session_scope() as s:
        r = pc_caducs.build_pc_caducs(s, ref_year=ref_year, log=typer.echo)
        typer.echo(f"✓ pc_caducs : {r['total']} parcelles caduc probable")


@app.command("defisc-fenetres")
def defisc_fenetres_cmd(
    ref_year: int = typer.Option(2026, help="Année de prospection de référence (fenêtres actives ref..ref+2)."),
) -> None:
    """Phase A-1 volet 2 — badge « fenêtre de sortie de défiscalisation » : table additive
    defisc_fenetres (maisons/monopropriété), fenêtre de sortie d'engagement +6/+11 ans dérivée
    de DVF (VEFA) + permis. Lecture seule des sources ; ne touche jamais le run servi (M80 : nom de
    run figé « q_v6_m8 » retiré de la docstring — le servi se lit dans config/served_run.txt)."""
    from .ingestion import defisc_fenetres

    with session_scope() as s:
        r = defisc_fenetres.build_defisc_fenetres(s, ref_year=ref_year, log=typer.echo)
        typer.echo(f"✓ defisc_fenetres : {r['total']} parcelles mono neuf, {r['active']} fenêtre active")


@app.command("anc")
def anc_cmd(
    etape: str = typer.Option("tout", help="insee | iris | zonages | proba | signal | tout"),
    fichier: str = typer.Option(None, help="Zip RP local déjà téléchargé (sinon download INSEE)."),
) -> None:
    """Lot A (wave ANC & Végétation) : couche probabiliste ANC (INSEE EGOUL RP2022 à
    l'IRIS), zonages officiels d'assainissement (GPU typeinf 19), proba par parcelle
    bâtie (modulation zone U), signal anc_mutation (fenêtre DVF 12 mois)."""
    from .ingestion import anc

    with session_scope() as s:
        if etape in ("insee", "tout"):
            typer.echo(f"✓ INSEE EGOUL : {anc.ingest_insee_egoul(s, fichier=fichier, log=typer.echo)}")
        if etape in ("iris", "tout"):
            typer.echo(f"✓ contours IRIS : {anc.ingest_iris_contours(s, log=typer.echo)}")
        if etape in ("zonages", "tout"):
            typer.echo(f"✓ zonages officiels GPU : {anc.ingest_zonages_gpu(s, log=typer.echo)}")
        if etape in ("proba", "tout"):
            typer.echo(f"✓ proba_anc : {anc.compute_proba(s, log=typer.echo)}")
            # M95 — communes classées INTÉGRALEMENT en ANC (Office de l'eau) → table servie par anc_service.
            typer.echo(f"✓ communes 100 % ANC (Office de l'eau) : {anc.load_office_eau_communes(s)}")
            typer.echo(f"✓ calage Office de l'eau : {anc.calage_office_eau(s)}")
        if etape in ("signal", "tout"):
            typer.echo(f"✓ signal anc_mutation : {anc.signal_mutation(s)}")


@app.command("vegetation-irc")
def vegetation_irc_cmd(
    limit: int = typer.Option(None, help="Nb max de tuiles (tests)."),
) -> None:
    """Lot B1 (wave ANC & Végétation) : acquisition BD ORTHO IRC sur la grille ortho
    existante (5 041 tuiles, cache séparé, checkpoint irc_acquise_at). Relançable."""
    from .ingestion import vegetation

    with session_scope() as s:
        res = vegetation.acquire_irc(s, limit=limit, log=typer.echo)
    typer.echo(f"✓ acquisition IRC : {res}")


@app.command("vegetation")
def vegetation_cmd(
    etape: str = typer.Option("tout", help="tuiles | finalize | signal | tout"),
    limit: int = typer.Option(None, help="Nb max de tuiles (tests)."),
) -> None:
    """Lot B2-B3 (wave ANC & Végétation) : NDVI (IRC) × MNH LiDAR HD streamé par tuile,
    agrégats canopée par parcelle (parcelle / bande limite 3 m / buffer bâti 8 m),
    signal vegetation_haute_limite. Relançable. (flag solaire : parti au spin-off vues+solaire.)"""
    from .ingestion import vegetation

    with session_scope() as s:
        if etape in ("tuiles", "tout"):
            typer.echo(f"✓ tuiles : {vegetation.process_tiles(s, limit=limit, log=typer.echo)}")
        if etape in ("finalize", "tout"):
            typer.echo(f"✓ agrégats : {vegetation.finalize(s, log=typer.echo)}")
            sanity = vegetation.sanity_est_ouest(s)
            typer.echo(f"  sanity Est > Ouest : {sanity}")
            if not sanity["ok"]:
                typer.echo("✗ SANITY : NDVI Est ≤ Ouest — inversion de canaux probable, INVESTIGUER.")
                raise typer.Exit(1)
        if etape in ("signal", "tout"):
            typer.echo(f"✓ signal vegetation_haute_limite : {vegetation.signal_vegetation(s)}")


@app.command("vegetation-validation")
def vegetation_validation_cmd() -> None:
    """Session de validation Vic : 20 vignettes « végétation haute en limite » dans
    l'outil ortho (quota CÔTÉ SERVEUR, anti-rafale) — re-télécharge les seules tuiles
    RVB nécessaires aux vignettes (cache purgé)."""
    from .ingestion import vegetation

    with session_scope() as s:
        res = vegetation.preparer_validation(s, log=typer.echo)
    typer.echo(f"✓ session prête : {res['vignettes']} vignettes — `labuse api` puis {res['url']}")


@app.command("purge-sessions")
def purge_sessions_cmd() -> None:
    """REVUE · R9 (RV-003) — supprime les sessions_auth EXPIRÉES (expire_at < now). Aucune session
    valide touchée. Cronable (quotidien) : évite l'accumulation de lignes mortes (dette AC-011)."""
    from sqlalchemy import text as _t

    from .db import engine
    with engine().begin() as c:
        n = c.execute(_t("DELETE FROM sessions_auth WHERE expire_at < now()")).rowcount
    typer.echo(f"✓ Purge : {n} session(s) expirée(s) supprimée(s).")


# ═══════════════════════════ CRON-1 — labuse jobs (exploitation planifiée) ═══════════════════════════
jobs_app = typer.Typer(add_completion=False, help="Exploitation planifiée : lister, lancer, consulter les jobs.")
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def jobs_list_cmd() -> None:
    """Les jobs, leur planification (heure Réunion) et leur dernier statut."""
    from .jobs import liste
    typer.echo(f"{'JOB':26s} {'CADENCE':14s} {'HEURE RÉUNION':18s} DERNIER")
    for j in liste():
        d = j["dernier"]
        typer.echo(f"{j['nom']:26s} {j['cadence']:14s} {j['heure_reunion']:18s} "
                   f"{d.get('statut') or '—'} {d.get('fin') or ''}")


@jobs_app.command("run")
def jobs_run_cmd(nom: str = typer.Argument(..., help="Nom du job (cf. jobs list)")) -> None:
    """Lance un job via le WRAPPER (même verrou flock que le cron). C'est ce que lance le crontab."""
    import os
    import subprocess as _sp
    import sys as _sys
    from pathlib import Path as _P
    script = _P(__file__).resolve().parents[2] / "scripts" / "jobs" / "run-job.sh"
    env = dict(os.environ)
    # binaire labuse installé (sibling du python courant) — l'entrée console charge TOUT le module,
    # contrairement à `python -m labuse.cli` (garde __main__ en milieu de fichier → commandes tardives
    # invisibles). Fallback : `labuse` sur le PATH.
    _cand = _P(_sys.executable).parent / "labuse"
    env.setdefault("LABUSE_BIN", str(_cand) if _cand.exists() else "labuse")
    r = _sp.run(["sh", str(script), nom], env=env)
    raise typer.Exit(r.returncode)


@jobs_app.command("exec")
def jobs_exec_cmd(nom: str = typer.Argument(...)) -> None:
    """INTERNE — exécute le job (appelé par le wrapper ; ne pose PAS le verrou)."""
    from .jobs import exec_one
    raise typer.Exit(exec_one(nom))


@jobs_app.command("status")
def jobs_status_cmd() -> None:
    """Tableau des états (dernier passage de chaque job)."""
    from .jobs import liste
    typer.echo(f"{'JOB':26s} {'STATUT':10s} {'DRY':4s} {'DURÉE':9s} DERNIER")
    for j in liste():
        d = j["dernier"]
        typer.echo(f"{j['nom']:26s} {(d.get('statut') or '—'):10s} "
                   f"{('oui' if d.get('dry_run') else 'non'):4s} "
                   f"{str(d.get('duree_s') or '—'):9s} {d.get('fin') or 'jamais'}")


# ═══════════════════════ CIRCUIT-1 (lot 1.5) — registre : le miroir en base ═══════════════════════
registre_app = typer.Typer(add_completion=False,
                           help="Registre des chiffres/robinets (CIRCUIT-1) : le code est la vérité.")
app.add_typer(registre_app, name="registre")


@registre_app.command("sync")
def registre_sync_cmd() -> None:
    """Écrit le miroir `registre_chiffres` / `registre_robinets` / `registre_aretes` DEPUIS le code
    (idempotent : truncate + insert). La page Circuit et la sonde lisent le miroir, jamais le code."""
    from .registre import sync as registre_sync_mod
    from .registre import verifier
    pb = verifier()
    if pb:
        typer.echo(f"✗ registre incohérent ({len(pb)}) :")
        for p in pb[:20]:
            typer.echo(f"  · {p}")
        raise typer.Exit(1)
    with session_scope() as s:
        n = registre_sync_mod.sync(s)
        s.commit()
    typer.echo(f"✓ miroir écrit : {n['chiffres']} chiffres · {n['robinets']} robinets · {n['aretes']} arêtes")


@registre_app.command("fiche")
def registre_fiche_cmd(cible: str = typer.Argument(..., help="parcelle | autres")) -> None:
    """CIRCUIT-2 lot 2 — génère le document « la fiche, donnée par donnée » DEPUIS le registre
    (docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md ou FICHES-DONNEES.md). Relu à la main avant commit."""
    from pathlib import Path

    from .registre import fiche_doc
    racine = Path(__file__).resolve().parents[2] / "docs" / "CIRCUIT"
    with session_scope() as s:
        if cible == "parcelle":
            chemin = racine / "FICHE-PARCELLE-DONNEES.md"
            chemin.write_text(fiche_doc.doc_fiche_parcelle(s))
        elif cible == "autres":
            chemin = racine / "FICHES-DONNEES.md"
            chemin.write_text(fiche_doc.doc_autres_fiches(s))
        else:
            typer.echo("cible inconnue : parcelle | autres")
            raise typer.Exit(1)
    typer.echo(f"✓ écrit : {chemin}")


# ═══════════════════ CIRCUIT-1 (lot 3.3) — la POMPE : Calculer un candidat COMPLET ═══════════════════
pompe_app = typer.Typer(add_completion=False,
                        help="La pompe (CIRCUIT-1) : Calculer un candidat complet — jamais servi tout seul.")
app.add_typer(pompe_app, name="pompe")


@pompe_app.command("calculer")
def pompe_calculer_cmd(
    label: str = typer.Option(..., help="Label du run candidat (ex. q_v13_20260906)."),
    recette: str = typer.Option("m36", help="Recette scoring : m36 (servie) ou q_v12."),
    par: str = typer.Option("cli", help="Qui lance (email admin) — entre au journal."),
    sans_division: bool = typer.Option(False, help="Sauter division-or (déjà calculé pour ce label)."),
) -> None:
    """CALCULER (lot 3.3) — le candidat COMPLET sous un label : cascade+scoring (flux-run),
    score É sur le neuf LIVE, division d'or POUR CE LABEL, note de version (registre), rapport
    candidat. Jamais servi : Basculer reste un geste. Le résiduel n'est recalculé que si ses
    entrées ont changé (sinon le manifeste candidat REPORTE le résiduel servi — lot 3.2)."""
    import os
    import subprocess
    import sys

    from . import bascule_flux, circuit_journal, filtres

    with session_scope() as s:
        blocages = filtres.garde_pompe(s)
        if blocages:
            for b in blocages:
                typer.echo(f"⛔ source `run` en quarantaine : {b['source']} [{b['version']}] — "
                           f"contrôles bloquants KO : {', '.join(b['controles'])}")
            circuit_journal.journaliser(s, "calculer", label, par, "refuse",
                                        {"garde_pompe": blocages})
            s.commit()
            typer.echo("✗ Calculer refusé : une source à portée `run` a une version servie en "
                       "quarantaine. Corrige la source (ou « servir quand même » sur la page Circuit).")
            raise typer.Exit(1)
        circuit_journal.journaliser(s, "calculer", label, par, "lance", {"recette": recette})
        s.commit()
    # 1) cascade + scoring — la brique existante, en process (progression run_progress incluse).
    flux_run_cmd(label=label, resume=True, recette=recette)
    # 2) score É pour CE label (neuf LIVE — lot 2.2).
    from .ingestion.score_e import build_score_e
    with session_scope() as s:
        build_score_e(s, run=label)
        s.commit()
    # 3) division d'or POUR CE LABEL (lot 2.3) : le builder tamponne runs.current() → on le lance
    #    détaché-en-avant avec l'override d'env (le même mécanisme que les tests), jamais le servi.
    if not sans_division:
        env = {**os.environ, "LABUSE_SERVED_RUN": label}
        subprocess.run([sys.executable, "-m", "labuse.cli", "division-or", "--all"],
                       env=env, check=True)
    # 4) résiduel : candidat SEULEMENT si ses entrées ont bougé (sinon reporté à la bascule).
    with session_scope() as s:
        dit = bascule_flux.residuel_entrees_changees(s)
        if dit["changees"]:
            typer.echo(f"⚠ résiduel : entrées plus récentes que le run servi ({dit['detail']}) — "
                       f"calcule un candidat résiduel (chaîne residuel_runs) avant de basculer.")
        else:
            typer.echo("✓ résiduel : entrées inchangées — le manifeste candidat reportera le servi.")
    # 5) note de version (registre) + rapport candidat (mail existant).
    with session_scope() as s:
        note = bascule_flux.note_version(s, label)
        typer.echo("── NOTE DE VERSION ──")
        typer.echo(f"réservoirs utilisés : {len(note['reservoirs'])} (millésimes portés)")
        typer.echo(f"chiffres recalculés (portée run) : {', '.join(note['chiffres_recalcules'][:12])}"
                   + (" …" if len(note["chiffres_recalcules"]) > 12 else ""))
        if note.get("ecart_classement"):
            typer.echo(f"écart de classement vs servi : {note['ecart_classement']}")
        circuit_journal.journaliser(s, "calculer", label, par, "ok", {"note": note})
        s.commit()
    from . import golden_ops
    golden_ops.rapport_candidat(dry_run=False)
    typer.echo(f"✓ candidat « {label} » complet — Basculer reste un geste (page Circuit / labuse golden promote).")


# ═══════════════════════════ CRON-1 (K5) — golden : candidat auto, bascule MANUELLE ═══════════════════════════
golden_app = typer.Typer(add_completion=False, help="Golden : run candidat (jamais servi) + bascule manuelle (Vic).")
app.add_typer(golden_app, name="golden")


@golden_app.command("promote")
def golden_promote_cmd(run: str = typer.Argument(..., help="Label du run candidat à servir")) -> None:
    """LA BASCULE — un geste de Vic. Fait du run candidat le run SERVI aux clients. Aucune bascule
    automatique n'existe : le classement ne change que par cette commande (ou le bouton admin équivalent)."""
    from . import circuit_journal, filtres
    from .golden_ops import promote
    with session_scope() as s:
        blocages = filtres.garde_pompe(s)
        if blocages:
            for b in blocages:
                typer.echo(f"⛔ source `run` en quarantaine : {b['source']} [{b['version']}] — "
                           f"contrôles bloquants KO : {', '.join(b['controles'])}")
            circuit_journal.journaliser(s, "basculer", run, "cli", "refuse", {"garde_pompe": blocages})
            s.commit()
            typer.echo("✗ Bascule refusée : une source à portée `run` a une version servie en "
                       "quarantaine (corrige la source ou « servir quand même » sur la page Circuit).")
            raise typer.Exit(1)
    r = promote(run)
    if r.get("ok"):
        typer.echo(f"✓ Run servi = {run} (ancien : {r.get('ancien')}). Golden re-gravé sur le servi.")
    else:
        typer.echo(f"✗ Bascule refusée : {r.get('motif')}")
        raise typer.Exit(1)


@golden_app.command("candidat")
def golden_candidat_cmd() -> None:
    """Calcule/compare un run CANDIDAT au run servi (promues, tiers, dérive %) et rend le rapport. Jamais
    servi : sortie informative seule (la bascule reste `golden promote`)."""
    from .golden_ops import candidat
    typer.echo(candidat())


# ═══════════════════ CIRCUIT-3 — LE FILTRE : la qualité à l'intérieur de chaque source ═══════════════════
filtre_app = typer.Typer(add_completion=False,
                         help="Le filtre (CIRCUIT-3) : jouer les contrôles qualité d'une source sur sa version.")
app.add_typer(filtre_app, name="filtre")


@filtre_app.command("jouer")
def filtre_jouer_cmd(
    source: str = typer.Argument(..., help="Clé de la source (label de la vanne). 'toutes' = toutes les sources à job."),
    version: str = typer.Option(None, "--version", help="Version explicite (défaut : la version servie)."),
    par: str = typer.Option("cli", help="Qui joue le filtre — entre au journal."),
) -> None:
    """JOUER (lot 1.1) — les contrôles d'un filtre sur UNE version : écrit filtre_resultats +
    filtre_versions, rend le verdict (ok / avertissements / QUARANTAINE si un bloquant KO)."""
    from . import circuit_journal, filtres
    cibles = filtres.sources() if source == "toutes" else [source]
    if source != "toutes" and filtres.get_filtre(source) is None:
        typer.echo(f"✗ source inconnue : {source} (voir `labuse filtre lister`).")
        raise typer.Exit(1)
    with session_scope() as s:
        for cle in cibles:
            f = filtres.get_filtre(cle)
            if f is None:
                continue
            v = filtres.jouer(s, f, version=version)
            s.commit()
            circuit_journal.journaliser(s, "filtre", cle, par,
                                        "refuse" if v.verdict == "quarantaine" else "ok",
                                        {"version": v.version, "verdict": v.verdict,
                                         "bloquants_ko": v.bloquants_ko,
                                         "avertissants_ko": v.avertissants_ko})
            s.commit()
            marque = {"ok": "✓", "avertissements": "⚠", "quarantaine": "⛔"}[v.verdict]
            typer.echo(f"{marque} {cle} [{v.version}] : {v.verdict} — "
                       f"{v.bloquants_ko} bloquant(s) KO, {v.avertissants_ko} avertissant(s) KO "
                       f"({len(v.resultats)} contrôles)")
            for r in v.resultats:
                if r["verdict"] == "ko":
                    typer.echo(f"    KO {r['severite']:<11} {r['controle']:<22} "
                               f"valeur={r['valeur']}  seuil={r['seuil']}")


@filtre_app.command("lister")
def filtre_lister_cmd() -> None:
    """Liste les sources et leur dernier verdict connu (run/live, propres/universels seuls)."""
    from . import filtres
    with session_scope() as s:
        for cle in filtres.sources():
            f = filtres.get_filtre(cle)
            v = filtres.dernier_verdict(s, cle)
            portee = ",".join([p for p, on in (("run", f.portee_run), ("live", f.live)) if on]) or "—"
            propres = len(f.propres)
            etat = f"{v['verdict']} [{v['version']}]" if v else "jamais joué"
            typer.echo(f"{cle:<26} portée={portee:<8} propres={propres:<2} {etat}")


@filtre_app.command("garde")
def filtre_garde_cmd() -> None:
    """Montre ce que la garde de la pompe (1.4) verrait : sources à portée `run` en quarantaine."""
    from . import filtres
    with session_scope() as s:
        blocages = filtres.garde_pompe(s)
    if not blocages:
        typer.echo("✓ garde pompe : aucune source `run` en quarantaine.")
        return
    for b in blocages:
        typer.echo(f"⛔ {b['source']} [{b['version']}] — contrôles bloquants KO : {', '.join(b['controles'])}")


# ═══════════════════ CIRCUIT-1 (lot 6) — les AGENTS de source, à la demande ═══════════════════
agent_app = typer.Typer(add_completion=False,
                        help="Agents de veille amont (CIRCUIT-1) : constatent, ne téléchargent jamais.")
app.add_typer(agent_app, name="agent")


@agent_app.command("source")
def agent_source_cmd(
    source_id: int = typer.Argument(None, help="id data_sources d'UN réservoir."),
    ids: str = typer.Option(None, "--ids", help="plusieurs ids, séparés par des virgules."),
    tous: bool = typer.Option(False, "--tous", help="tous les réservoirs affichés non en_direct."),
    par: str = typer.Option("cli", help="qui lance (email admin) — entre au journal."),
) -> None:
    """UN appel Claude par réservoir (surface agent_source, web_search natif, JSON strict) :
    verdict a_jour|nouvelle|introuvable|vide AVEC preuve datée (sinon forcé introuvable — 6.2).
    5 agents en parallèle au plus ; coût au ledger ia_log ; rapport en source_agent_rapports."""
    from .agent_source import lancer_agents
    from .db import session_scope

    if tous:
        with session_scope() as s:
            from .sources_catalog import WHERE_AFFICHEES, masquees_param
            cibles = [i for (i,) in s.execute(text(
                f"SELECT id FROM data_sources WHERE {WHERE_AFFICHEES}"
                " AND COALESCE(mode_remplissage,'') NOT IN ('en_direct','absente') ORDER BY id"),
                {"masquees": masquees_param()}).all()]
    elif ids:
        cibles = [int(x) for x in ids.split(",") if x.strip()]
    elif source_id is not None:
        cibles = [source_id]
    else:
        typer.echo("✗ donner un id, --ids a,b,c ou --tous")
        raise typer.Exit(1)
    typer.echo(f"→ {len(cibles)} agent(s), 5 en parallèle au plus…")
    rapports = lancer_agents(session_scope, cibles, par=par)
    for r in rapports:
        if not r.get("ok"):
            typer.echo(f"  ✗ {r.get('motif')}")
            continue
        ligne = f"  {r['verdict']:12} {r['source']}"
        if r.get("version_trouvee"):
            ligne += f" → {r['version_trouvee']}"
        if r.get("raison_forcage"):
            ligne += f"  ({r['raison_forcage']})"
        typer.echo(ligne)
    n_nouv = sum(1 for r in rapports if r.get("verdict") == "nouvelle")
    typer.echo(f"✓ terminé — {n_nouv} nouvelle(s) version(s) (la vanne apparaît sur la page Circuit).")
