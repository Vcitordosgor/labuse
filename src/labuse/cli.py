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
from .config import get_settings
from .db import engine, ensure_postgis, session_scope

app = typer.Typer(add_completion=False, help="LA BUSE — radar foncier intelligent de La Réunion.")


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


@app.command("seed-sources")
def seed_sources_cmd() -> None:
    from .ingestion import seed_sources

    with session_scope() as s:
        n = seed_sources.seed(s)
    typer.echo(f"✓ Catalogue de sources : {n} sources.")


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
    from .connectors.cadastre import ingest_parcels
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


@app.command("ingest-permits")
def ingest_permits_cmd(
    commune: str = typer.Option(None, help="INSEE de la commune (défaut = pilote)."),
    cap: int = typer.Option(10000, help="Plafond de permis récupérés (pagination ODS)."),
) -> None:
    """Ingère les autorisations d'urbanisme (SITADEL — API Région Réunion ODS) pour la commune,
    géolocalisées par IDU cadastral. Lancer ensuite `geocode-permits` pour les non géolocalisés."""
    from .ingestion.permits import ingest_permits

    insee = commune if (commune and commune.isdigit()) else get_settings().pilot_commune_insee
    nom = _commune_nom(insee)
    if nom is None:
        typer.echo(f"✗ INSEE {insee} inconnu au référentiel des 24 communes de La Réunion.")
        raise typer.Exit(1)
    with session_scope() as s:
        n = ingest_permits(s, insee, nom, cap=cap)
    typer.echo(f"✓ {n} permis (SITADEL) chargés pour {nom} (INSEE {insee}). "
               f"Géolocalisez les manquants : geocode-permits --commune {insee}")


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

    from .connectors.inpi_rne import InpiRneConnector
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
        for k in range(0, len(todo), chunk):
            part = todo[k:k + chunk]
            res = ingest_inpi_rne(s, part, connector=conn)
            s.commit()   # lot committé → reprise possible ; conso mémoire plate
            tot_d += res["dirigeants"]
            tot_h += res["sirens_with_dirigeant"]
            typer.echo(f"  … {min(k + chunk, len(todo))}/{len(todo)} — +{res['dirigeants']} dirigeants "
                       f"(cumul {tot_d}, sirens_hit {tot_h}, {time.time() - t0:.0f}s)", nl=True)
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

    from .connectors.inpi_rne import InpiRneConnector
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
        tot_d = tot_r = 0
        for k in range(0, len(cibles), chunk):
            sub = {c: all_targets[c] for c in cibles[k:k + chunk]}
            res = resolve_gigogne(s, connector=conn, targets=sub, throttle_s=throttle,
                                  gerant_cache=gerant_cache)
            s.commit()
            tot_d += res["dirigeants_gigogne"]
            tot_r += res["cibles_resolues"]
            typer.echo(f"  … {min(k + chunk, len(cibles))}/{len(cibles)} — +{res['dirigeants_gigogne']} "
                       f"physiques (cibles résolues {tot_r}, {time.time() - t0:.0f}s)")
    typer.echo(f"✓ INPI gigogne : {tot_r} cibles résolues, {tot_d} dirigeants physiques rattachés.")


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
    from .ingestion import georisques_layers, layers_ingest
    from .ingestion.run_all import REUNION_COMMUNES, _commune_bbox

    conn = GeorisquesConnector(throttle_s=throttle)
    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    api_kinds = list(georisques_layers.KIND_SOURCE)
    t0 = time.time()
    tot: dict[str, int] = {k: 0 for k in api_kinds}
    tot["georisque_alea"] = 0
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


@app.command("warm-vue-mer")
def warm_vue_mer_cmd(
    commune: str = typer.Option(None, help="INSEE de la commune (défaut = pilote)."),
    max_dist: int = typer.Option(2000, help="Rayon côtier (m) : parcelles à ≤ max_dist du trait de côte."),
    batch: int = typer.Option(200, help="Commit + log de progression tous les N parcelles."),
) -> None:
    """Pré-chauffe le cache VUE MER (parcel_vue_mer) sur les parcelles littorales de la commune.
    Réutilise api.enrichment.vue_mer (profil RGE ALTI). Idempotent (saute les parcelles déjà
    en cache), throttlé à la cadence RGE ALTI (~5 req/s, comme _alti_query)."""
    import time
    from collections import Counter
    from .api.enrichment import _live_enabled, vue_mer

    insee = commune if (commune and commune.isdigit()) else get_settings().pilot_commune_insee
    nom = _commune_nom(insee)
    if nom is None:
        typer.echo(f"✗ INSEE {insee} inconnu au référentiel des 24 communes de La Réunion.")
        raise typer.Exit(1)
    if not _live_enabled():
        typer.echo("✗ Mode live RGE ALTI désactivé (LABUSE_ENRICH_LIVE=0) — aucun calcul possible.")
        raise typer.Exit(1)

    with session_scope() as s:
        ids = [r[0] for r in s.execute(text(
            """SELECT p.id FROM parcels p
               WHERE p.commune = :c
                 AND EXISTS (SELECT 1 FROM spatial_layers l WHERE l.kind = 'trait_de_cote'
                             AND ST_DWithin(p.geom_2975, l.geom_2975, :d))
                 AND NOT EXISTS (SELECT 1 FROM parcel_vue_mer v WHERE v.parcel_id = p.id)
               ORDER BY p.id"""), {"c": nom, "d": float(max_dist)}).all()]
        total = len(ids)
        typer.echo(f"Pré-chauffe vue mer — {nom} : {total} parcelles littorales (≤ {max_dist} m) à calculer.")
        if not total:
            typer.echo("✓ Rien à faire (déjà en cache ou aucune parcelle côtière).")
            return
        tally: Counter = Counter()
        for i, pid in enumerate(ids, 1):
            try:
                res = vue_mer(s, pid)
                tally[res.get("vue") if res.get("available") else "indispo"] += 1
            except Exception:  # noqa: BLE001 - une parcelle ne casse pas le lot
                tally["erreur"] += 1
            time.sleep(0.21)   # throttle RGE ALTI ~5 req/s (même cadence que _alti_query)
            if i % batch == 0 or i == total:
                s.commit()
                typer.echo(f"    {i}/{total} · oui={tally['oui']} partielle={tally['partielle']} "
                           f"non={tally['non']} indispo={tally['indispo']} err={tally['erreur']}")
    typer.echo(f"✓ Vue mer pré-chauffée : {total} parcelles ({nom}). "
               f"oui={tally['oui']} · partielle={tally['partielle']} · non={tally['non']}")


@app.command("compute-residuel")
def compute_residuel_cmd(
    commune: str = typer.Option(None, help="Commune (nom ou INSEE ; défaut = pilote)."),
    chunk: int = typer.Option(500, help="Taille des lots (commit par lot)."),
) -> None:
    """Calcule et cache le POTENTIEL RÉSIDUEL (Lot B) — alimente le filtre « sous-densité »."""
    from .faisabilite.residuel import compute_residuel_batch

    commune = _resolve_commune(commune)
    models.ensure_residuel_cache(engine())   # idempotent : crée/migre la colonne capacite_estimee
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
    if not ids:
        typer.echo("Aucune parcelle ingérée.")
        raise typer.Exit(1)
    total = 0
    for k in range(0, len(ids), chunk):
        with session_scope() as s:
            total += compute_residuel_batch(s, ids[k:k + chunk])
        typer.echo(f"    {min(k + chunk, len(ids))}/{len(ids)} parcelles…")
    typer.echo(f"✓ Potentiel résiduel caché pour {total} parcelles constructibles ({commune}).")


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

    if as_json:
        typer.echo(_json.dumps({"db_reachable": True, "schema": sch, "data": data, **st},
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


@app.command("backup-db")
def backup_db_cmd(
    dir: str = typer.Option("backups", help="Dossier des sauvegardes (créé si absent)."),
) -> None:
    """Sauvegarde COMPLÈTE de la base (pg_dump format custom compressé) — données,
    évaluations, pipeline, cache enrichment, état démo. Nommage horodaté."""
    import subprocess
    import time
    from pathlib import Path
    from shutil import which

    if not which("pg_dump"):
        typer.echo("✗ pg_dump introuvable — installer postgresql-client.")
        raise typer.Exit(2)
    env, dbname = _pg_env_and_db(get_settings().database_url)
    out_dir = Path(dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"labuse-{dbname}-{time.strftime('%Y%m%d-%H%M%S')}.dump"
    typer.echo(f"▶ pg_dump {dbname} → {out}")
    res = subprocess.run(["pg_dump", "-Fc", "--no-owner", "-d", dbname, "-f", str(out)],
                         env=env, capture_output=True, text=True)
    if res.returncode != 0:
        typer.echo(f"✗ pg_dump a échoué :\n{res.stderr.strip()}")
        raise typer.Exit(1)
    size_mb = out.stat().st_size / 1e6
    typer.echo(f"✓ Sauvegarde : {out} ({size_mb:.1f} Mo)")
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
    from shutil import which

    if not which("pg_restore"):
        typer.echo("✗ pg_restore introuvable — installer postgresql-client.")
        raise typer.Exit(2)
    src = Path(file)
    if not src.is_file():
        typer.echo(f"✗ Fichier introuvable : {src}")
        raise typer.Exit(1)
    probe = subprocess.run(["pg_restore", "--list", str(src)], capture_output=True, text=True)
    if probe.returncode != 0:
        typer.echo(f"✗ Fichier invalide (pas une archive pg_dump) : {src}\n{probe.stderr.strip()}")
        raise typer.Exit(1)

    env, dbname = _pg_env_and_db(target_url or get_settings().database_url)
    if not yes and not typer.confirm(f"⚠ Restaurer {src.name} dans « {dbname} » ? Les données actuelles seront ÉCRASÉES."):
        typer.echo("Abandon.")
        raise typer.Exit(1)
    typer.echo(f"▶ pg_restore → {dbname}…")
    res = subprocess.run(
        ["pg_restore", "--clean", "--if-exists", "--no-owner", "-d", dbname, str(src)],
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


if __name__ == "__main__":
    app()
