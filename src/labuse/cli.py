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


@app.command("api")
def api_cmd(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Lance l'API FastAPI (uvicorn)."""
    import uvicorn

    uvicorn.run("labuse.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
