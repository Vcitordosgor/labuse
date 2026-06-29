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
    s = get_settings()
    if commune is None:
        return s.pilot_commune_name
    return s.pilot_commune_name if commune == s.pilot_commune_insee else commune


def _parcel_ids(session, commune: str | None) -> list[int]:
    stmt = select(models.Parcel.id).order_by(models.Parcel.idu)
    if commune:
        stmt = stmt.where(models.Parcel.commune == commune)
    return [r[0] for r in session.execute(stmt).all()]


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

    commune = _resolve_commune(commune)
    provider = get_provider() if ai else None
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
        if not ids:
            typer.echo("Aucune parcelle ingérée. Lancer `labuse seed-demo`.")
            raise typer.Exit(1)
        outcomes = evaluate_parcels(ids, session, persist=True, ai_provider=provider)

    from collections import Counter

    counts = Counter(o.status for o in outcomes)
    typer.echo(f"✓ {len(outcomes)} parcelles évaluées ({commune}).")
    for status, n in counts.most_common():
        typer.echo(f"    {status:24} : {n}")


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

    commune = _resolve_commune(commune)
    with session_scope() as session:
        ids = _parcel_ids(session, commune)
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
