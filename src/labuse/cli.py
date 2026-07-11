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

    nom = _resolve_commune(commune)
    t0 = time.time()
    with session_scope() as s:
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
    label: str = typer.Option("q_v2", help="run_label à simuler."),
    candidates: str = typer.Option(
        "", help="Candidats « q:a » ou « q:a:acompl » séparés par des virgules "
                 "(défaut : balayage q∈{60..80} × a∈{55..70} autour de la convention courante)."),
) -> None:
    """SIMULATION À BLANC de conventions de matrice (aucune écriture persistante — table
    temporaire de session). Sortie : tableau console + grille HTML docs/tops_ile/
    matrice_sensibilite.html. La bascule événementielle n'est JAMAIS balayée (doctrine)."""
    from pathlib import Path

    from .config import load_yaml_config
    from .scoring.dryrun import simulate_matrice

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
           "h1{font-size:18px;color:#5CE6A1}h2{font-size:14px;color:#8FA69A;margin-top:28px}"
           "table{border-collapse:collapse;margin-top:10px}th{font:600 10px monospace;color:#8FA69A;"
           "padding:5px 8px;border-bottom:1px solid #2a352f;text-align:right}td{padding:5px 8px;"
           "border-bottom:1px solid #1a221e;text-align:right;font-family:monospace;font-size:12px}"
           "tr.cur{background:#0F1A14}tr.cur td{color:#5CE6A1;font-weight:600}"
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
            f"<h1>Grille de sensibilité — convention de matrice <span class='muted'>(run q_v2, simulation à blanc)</span></h1>"
            f"<p class='muted'>Ligne verte = convention COURANTE (Q≥{cur['q_chaude']} · A≥{cur['a_chaude']} · compl≥{cur['a_completude_min']}). "
            f"Les chaudes « + N évén. » = bascule BODACC, doctrinale, insensible aux seuils. "
            f"Dossiers = propriétaires uniques (SIREN) parmi les chaudes ; « sans id. » = parcelles chaudes sans identité connue.</p>"
            f"<table><tr><th style='text-align:left'>CANDIDAT</th><th>CHAUDES</th><th>DONT (matrice+évén.)</th>"
            f"<th>Δ</th><th>DOSSIERS</th><th>SANS ID.</th><th>SURVEILLER</th><th>CREUSER</th><th>ÉCARTÉES</th></tr>{main}</table>"
            f"<h2>Chaudes par commune</h2><table><tr><th style='text-align:left'>CANDIDAT</th>"
            + "".join(f"<th>{c[:12]}</th>" for c in communes) + f"</tr>{det}</table>")


@app.command("matrice-apply")
def matrice_apply_cmd(
    label: str = typer.Option("q_v2", help="run_label sur lequel appliquer la convention."),
) -> None:
    """Applique la CONVENTION VERSIONNÉE (config/scoring_matrice.yaml) : matrice ×24 + tuiles
    MVT + tops HTML — idempotent, minutes. Le canari 97415000AC0253 (chaude PAR événement)
    stoppe tout s'il tombe."""
    import json as _json
    import subprocess
    import sys as _sys

    from .scoring.dryrun import apply_convention

    with session_scope() as s:
        out = apply_convention(s, label)
    typer.echo(_json.dumps(out, ensure_ascii=False, indent=1))
    r = subprocess.run([_sys.executable, "scripts/gen_tops_ile.py"], capture_output=True, text=True)
    typer.echo(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else f"✗ tops : {r.stderr[-300:]}")
    typer.echo("✓ convention appliquée (matrice ×24 + MVT + tops).")


@app.command("build-mvt")
def build_mvt_cmd(
    label: str = typer.Option("q_v2", help="run_label dont matérialiser les tuiles."),
) -> None:
    """(Re)construit la table `mvt_parcels` servie en tuiles vectorielles (carte île entière).
    À relancer après CHAQUE run de scoring — les tuiles lisent cette matérialisation, pas le run."""
    from .api.tiles import build_mvt_table, build_overlay_mvt

    with session_scope() as s:
        n = build_mvt_table(s, label)
        n_ov = build_overlay_mvt(s)
    typer.echo(f"✓ mvt_parcels reconstruite : {n} parcelles (label {label}) · mvt_overlays : {n_ov} géométries.")


@app.command("dryrun-matrice")
def dryrun_matrice_cmd(
    label: str = typer.Option("etape2", help="run_label sur lequel appliquer la matrice Q×A."),
    commune: str = typer.Option("97415", help="Commune (défaut = 97415)."),
) -> None:
    """Post-pass MATRICE Q×A (étape 3) sur un run dry-run existant : calcule Q/A/statut et livre la
    répartition + top chaudes/à surveiller. Seuils dans config/scoring_matrice.yaml (tunable)."""
    import json

    from .scoring.dryrun import compute_matrice, matrice_report

    nom = _resolve_commune(commune)
    with session_scope() as s:
        compute_matrice(s, label, nom)
        s.commit()
        rep = matrice_report(s, label, nom)
    typer.echo(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


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
    from .ingestion import dpe
    from .ingestion.run_all import REUNION_COMMUNES

    conn = DpeConnector(throttle_s=throttle)
    targets = [(i, n) for i, n in REUNION_COMMUNES if not (commune and commune.isdigit()) or i == commune]
    t0 = time.time()
    tot = {"dpe": 0, "geocodes": 0, "rattaches_parcelle": 0}
    for insee, nom in targets:
        with session_scope() as s:
            has = s.execute(text("SELECT count(*) FROM dpe_records WHERE code_insee=:c"), {"c": insee}).scalar()
            if has and not force:
                typer.echo(f"  ⏭ {nom} : DPE déjà là ({has}), sauté.")
                continue
            res = dpe.ingest_commune(s, insee, nom, connector=conn)
            s.commit()
            for k in tot:
                tot[k] += res[k]
            typer.echo(f"  ✓ {nom} : {res}")
    if not commune:
        with session_scope() as s:
            res = dpe.ingest_orphelins(s, connector=conn)
            s.commit()
            tot["dpe"] += res["dpe"]
            tot["rattaches_parcelle"] += res["rattaches_parcelle"]
            typer.echo(f"  ✓ orphelins (CP brut 974xx sans code_insee_ban) : {res}")
    typer.echo(f"✓ DPE île : {tot} ({time.time() - t0:.0f}s)")


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


@app.command("detect-events")
def detect_events_cmd(run_from: str = "q_v2", run_to: str = "q_v2_demo") -> None:
    """Diffe deux runs de scoring → événements (bascules, BODACC, permis proches). Cronable."""
    from sqlalchemy.orm import Session

    from .api.events import detect_events, ensure_tables
    from .db import engine

    ensure_tables(engine())
    with Session(engine()) as s:
        out = detect_events(s, run_from, run_to, demo=run_to.endswith("_demo"))
        s.commit()
    typer.echo(f"Événements émis {run_from} → {run_to} : {out}")


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


# ───────────────────── Moteur de segments Habitat (mandat segments) ─────────────────────

@app.command("segments-seed")
def segments_seed_cmd() -> None:
    """Tables du moteur de segments + seed des presets métiers manquants (Lot 1/4)."""
    from .api.segments import ensure_tables as seg_ensure
    from .segments import presets as presets_mod

    seg_ensure(engine())
    with session_scope() as s:
        res = presets_mod.seed_presets(s)
    typer.echo(f"✓ Presets : {len(res['inseres'])} inséré(s), {len(res['ignores'])} déjà en base.")
    for slug, errs in (res["erreurs"] or {}).items():
        typer.echo(f"  ⚠ {slug} : {' ; '.join(errs)}")


@app.command("segments-counts")
def segments_counts_cmd(
    force: bool = typer.Option(False, "--force", help="Recalcule tout (ignore le cache 24 h)."),
) -> None:
    """Compteurs live de parcelles par preset (cache 24 h — galerie Segments)."""
    from .segments import presets as presets_mod

    with session_scope() as s:
        done = presets_mod.refresh_counts(s, only_stale_hours=None if force else 24.0)
    for slug, n in sorted(done.items()):
        typer.echo(f"  {slug:32} {n:>8}")
    typer.echo(f"✓ {len(done)} compteur(s) recalculé(s).")


@app.command("segments-residuel")
def segments_residuel_cmd(
    commune: str = typer.Option(None, help="Nom ou INSEE ; défaut = les 24 communes."),
) -> None:
    """Lot 2 : droits résiduels sur parcelles bâties → parcel_residuel_bati
    (emprise max/résiduelle selon règles PLU calibrées, surélévation, confiance)."""
    from .ingestion.run_all import REUNION_COMMUNES
    from .segments import residuel_bati

    residuel_bati.ensure_tables(engine())
    # PAS de repli pilote ici : sans --commune, on traite LES 24 (parc bâti de l'île).
    noms = [_resolve_commune(commune)] if commune else [nom for _, nom in REUNION_COMMUNES]
    for nom in noms:
        with session_scope() as s:
            res = residuel_bati.compute_commune(s, nom)
        typer.echo(f"  {nom:24} {res['baties']:>7} bâties · {res['avec_regle']:>7} avec règle")
    typer.echo("✓ Droits résiduels sur bâti à jour.")


@app.command("ingest-catnat")
def ingest_catnat_cmd() -> None:
    """Lot 3 : arrêtés CATNAT GASPAR (Géorisques) des 24 communes → catnat_arretes.
    Refresh mensuel : deploy/cron.d/catnat."""
    from .segments import catnat as catnat_mod

    catnat_mod.ensure_tables(engine())
    with session_scope() as s:
        res = catnat_mod.ingest_catnat(s)
    typer.echo(f"✓ CATNAT : {res['arretes']} arrêté(s) sur {res['communes_ok']} commune(s).")
    for insee, err in (res["erreurs"] or {}).items():
        typer.echo(f"  ⚠ {insee} : {err}")


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


@app.command("nl-eval")
def nl_eval_cmd(
    fichier: str = typer.Option("tests/nl_queries.txt", help="Jeu de questions annotées."),
) -> None:
    """Lot 6 (wave-adresses) : évalue la recherche NL sur le jeu de test (acceptation
    ≥ 16/20, 0 champ hors registry exécuté). Appelle l'API Anthropic (clé .env)."""
    import json as _json
    from pathlib import Path

    from .ai.nl_segments import traduire
    from .api.ia import MODEL_NL

    lignes = [ln for ln in Path(fichier).read_text(encoding="utf-8").splitlines()
              if ln.strip() and not ln.startswith("#")]
    ok, echecs, hors_registry = 0, [], 0
    with session_scope() as s:
        for ln in lignes:
            question, _, attendu_raw = ln.partition("||")
            question, attendu = question.strip(), _json.loads(attendu_raw)
            res = traduire(s, question, model=MODEL_NL)
            if res.get("stub"):
                typer.echo("⚠ repli stub (clé/API indisponible) — évaluation non probante")
            if attendu.get("out_of_scope"):
                reussi = "out_of_scope" in res
                obtenu = res.get("out_of_scope", [f["cle"] for f in res.get("filtres", [])])
            else:
                cles = {f["cle"] for f in res.get("filtres", [])}
                reussi = "out_of_scope" not in res and set(attendu["cles"]) <= cles
                obtenu = sorted(cles) if "out_of_scope" not in res else res["out_of_scope"]
            hors_registry += len(res.get("rejetes", []))
            if reussi:
                ok += 1
            else:
                echecs.append((question, attendu, obtenu))
            typer.echo(f"  {'✓' if reussi else '✗'} {question[:70]}")
    typer.echo(f"\nScore : {ok}/{len(lignes)} (acceptation ≥ 16) · "
               f"champs hors registry REJETÉS par le garde-fou : {hors_registry} "
               f"(0 exécuté, par construction)")
    for q, att, obt in echecs:
        typer.echo(f"  ✗ {q}\n    attendu {att} · obtenu {obt}")
    if ok < 16:
        raise typer.Exit(1)


# ───────────────────────────── Mandat Habitat Solaire ─────────────────────────────

@app.command("solaire-pvgis")
def solaire_pvgis_cmd(
    rebuild: bool = typer.Option(False, "--rebuild", help="Reconstruit la grille (repart de zéro)."),
    rps: float = typer.Option(None, help="Requêtes/s vers PVGIS (défaut settings, 10)."),
    limit: int = typer.Option(None, help="Nb max de points à récupérer (tests)."),
) -> None:
    """Lot 1 (habitat-solaire) : baseline PVGIS — grille ~400 m, E_y par point (SARAH3,
    horizon topo intégré), interpolation IDW → parcel_solar + score percentile île.
    One-shot LONG (~17 000 appels à 10 req/s ≈ 30 min), relançable sans perte."""
    from .ingestion import solaire_pvgis

    with session_scope() as s:
        res = solaire_pvgis.run(s, rebuild=rebuild, rps=rps, limit=limit, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() "
                       "WHERE name = 'PVGIS (Commission européenne)'"))
    typer.echo(f"✓ PVGIS : {res}")
    sanity = res.get("sanity")
    if sanity and not sanity["ouest_sup_est"]:
        typer.echo("⚠ Sanity Ouest>Est non vérifié — LIMITE DOCUMENTÉE de la source SARAH3 "
                   "(nuance côtière Ouest/Est non captée ; ingestion vérifiée fidèle, gradient "
                   "d'altitude OK). Détail : RAPPORT_HABITAT_SOLAIRE.md.")


@app.command("solaire-flags")
def solaire_flags_cmd() -> None:
    """Lot 5 (habitat-solaire) : flags de qualification — amiante (DPE pré-1997),
    ABF (cascade), azimut du bâti (BD TOPO), proba propriétaire-occupant
    (Filosofi 200 m + bonus mutation DVF). Zéro ingestion, pures dérivations."""
    from .ingestion import solaire_flags

    with session_scope() as s:
        res = solaire_flags.run(s, log=typer.echo)
    typer.echo(f"✓ Flags solaire : {res}")


@app.command("solaire-conso")
def solaire_conso_cmd() -> None:
    """Lot 2 (habitat-solaire) : baseline EDF SEI (conso résidentielle par commune,
    dernier millésime) puis facture ESTIMÉE par parcelle bâtie résidentielle —
    estimation statistique, coefficients en config/habitat_solaire.yaml."""
    from .ingestion import solaire_conso

    with session_scope() as s:
        res = solaire_conso.run(s, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() "
                       "WHERE name = 'EDF SEI Réunion — open data'"))
    typer.echo(f"✓ Conso/facture estimées : {res}")
    if not res.get("plausible", True):
        raise typer.Exit(1)


@app.command("solaire-tertiaire")
def solaire_tertiaire_cmd(
    export: str = typer.Option(None, help="Chemin d'export CSV (optionnel)."),
) -> None:
    """Lot 6 (habitat-solaire) : vue matérialisée toitures tertiaires > 500 m²
    × propriétaire PM × bilan INPI × gisement PVGIS × poste source. Zéro ingestion."""
    from pathlib import Path

    from .ingestion import solaire_tertiaire

    with session_scope() as s:
        res = solaire_tertiaire.refresh(s)
        typer.echo(f"✓ mv_toitures_tertiaires : {res}")
        if export:
            Path(export).parent.mkdir(parents=True, exist_ok=True)
            Path(export).write_text(solaire_tertiaire.export_csv(s), encoding="utf-8-sig")
            typer.echo(f"✓ export : {export}")


@app.command("solaire-parkings")
def solaire_parkings_cmd() -> None:
    """Lot 3 (habitat-solaire) : parkings assujettis loi APER (OSM déjà en base,
    seuil Réunion 1 000 m² — décret 2025-802), rattachement parcelles + PM DGFiP,
    signal aper_deadline (échéance < 24 mois OU dépassée)."""
    from .ingestion import parkings_aper

    with session_scope() as s:
        res = parkings_aper.run(s, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() "
                       "WHERE name = 'Parkings OSM (loi APER)'"))
    typer.echo(f"✓ Parkings APER : {res}")


@app.command("solaire-pv-registry")
def solaire_pv_registry_cmd() -> None:
    """Lot 4 (habitat-solaire) : registre national des installations (extrait 974,
    EDF SEI/ODRÉ) → pv_registry, communes à forte densité de petites installations,
    vivier repowering 2006-2013 (contrats d'achat 20 ans en fin de vie)."""
    from .ingestion import solaire_pv_registry

    with session_scope() as s:
        res = solaire_pv_registry.run(s, log=typer.echo)
        s.execute(text("UPDATE data_sources SET last_sync_at = now() "
                       "WHERE name = 'Registre national des installations (ODRÉ)'"))
    typer.echo(f"✓ Registre PV : {res}")


@app.command("solaire-grid-capacity")
def solaire_grid_capacity_cmd() -> None:
    """Lot 7 (habitat-solaire, best effort) : capacités d'accueil réseau EDF SEI
    par poste source (S3REnR). Géométries des postes NON publiées (sécurité) —
    capacités seules, geom NULL."""
    from .ingestion import solaire_grid_capacity

    with session_scope() as s:
        res = solaire_grid_capacity.ingest(s)
    typer.echo(f"✓ Capacités réseau : {res}")


@app.command("solaire-cache-purge")
def solaire_cache_purge_cmd() -> None:
    """Lot 8 (habitat-solaire) : purge STRICTE du cache Google Solar API au-delà du
    TTL 30 jours (conformité ToS Google — pas de stockage permanent). Le refresh
    est LAZY : une entrée purgée n'est re-téléchargée que si elle est re-consultée."""
    ttl = get_settings().solar_api_cache_ttl_jours
    with session_scope() as s:
        n = s.execute(text(
            "DELETE FROM solar_api_cache WHERE fetched_at < now() - make_interval(days => :d)"),
            {"d": ttl}).rowcount
    typer.echo(f"✓ Cache Solar API : {n} entrée(s) purgée(s) (TTL {ttl} j)")


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
    etape: str = typer.Option("tout", help="tuiles | finalize | flags | signal | tout"),
    limit: int = typer.Option(None, help="Nb max de tuiles (tests)."),
) -> None:
    """Lot B2-B3 (wave ANC & Végétation) : NDVI (IRC) × MNH LiDAR HD streamé par tuile,
    agrégats canopée par parcelle (parcelle / bande limite 3 m / buffer bâti 8 m),
    flag_ombrage_vegetal (solaire) + signal vegetation_haute_limite. Relançable."""
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
        if etape in ("flags", "tout"):
            typer.echo(f"✓ flag_ombrage_vegetal : {vegetation.flag_solaire(s)}")
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
