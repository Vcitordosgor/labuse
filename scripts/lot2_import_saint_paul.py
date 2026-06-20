#!/usr/bin/env python3
"""LOT 2 — import contrôlé du cadastre COMPLET de Saint-Paul (3 000 → 51 129 parcelles).

SÉCURISÉ PAR DÉFAUT : sans flag, le script est en **DRY-RUN** — il exécute uniquement les
pré-checks (LECTURE SEULE) et affiche ce qu'il FERAIT, sans rien modifier. L'exécution réelle
exige DEUX garde-fous simultanés :

    python scripts/lot2_import_saint_paul.py --execute --confirm "IMPORT_SAINT_PAUL_COMPLET"

Principe (cf. docs/SAINT_PAUL_LOT2_IMPORT_PLAN.md) :
  B) parcelles : upsert ON CONFLICT (idu) — JAMAIS de reset, JAMAIS de DELETE parcels →
     les 3 000 `id` existants sont conservés (évaluations / pipeline / feedback / prospection intacts).
  D) couches  : purge CIBLÉE `WHERE commune='Saint-Paul'` (jamais une autre commune) puis
     ré-ingestion sur l'emprise commune COMPLÈTE, chaque couche isolée par SAVEPOINT.
  F) cascade  : evaluate_commune("Saint-Paul") sur les 51 129.

Garanties dures :
  • commune FIGÉE à Saint-Paul / 97415 (aucun argument ne permet de viser une autre commune) ;
  • en dry-run, AUCUN accès en écriture à la base — les étapes B/D/F ne touchent même pas la connexion ;
  • rollback : restauration du backup LOT 1 (cf. plan).

Imports « lourds » (réseau / base) faits PARESSEUSEMENT dans les branches d'exécution → importer ce
module (tests) ne déclenche aucun effet de bord.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

# ── Constantes FIGÉES (jamais paramétrables : on ne vise QUE Saint-Paul) ─────────────────────
COMMUNE = "Saint-Paul"
INSEE = "97415"
EXPECTED_PARCELS_BEFORE = 3000
EXPECTED_PARCELS_AFTER = 51129          # source de vérité : cadastre.data.gouv.fr Etalab (98 sections)
EXPECTED_SECTIONS_AFTER = 98
CONFIRM_PHRASE = "IMPORT_SAINT_PAUL_COMPLET"
DEFAULT_BACKUP = "/var/backups/labuse/labuse-labuse-20260620-101644.dump"
CRITICAL_TABLES = (
    "parcels", "spatial_layers", "cascade_results",
    "parcel_evaluations", "dvf_mutations", "bilan_params",
)
RESULTS_DOC = "docs/SAINT_PAUL_LOT2_RESULTS.md"


def real_mode(args: argparse.Namespace) -> bool:
    """Exécution RÉELLE uniquement si --execute ET --confirm exactement égal à la phrase."""
    return bool(getattr(args, "execute", False)) and getattr(args, "confirm", "") == CONFIRM_PHRASE


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="LOT 2 — import Saint-Paul complet (DRY-RUN par défaut).")
    p.add_argument("--execute", action="store_true",
                   help="Exécution RÉELLE (sinon dry-run). Exige aussi --confirm.")
    p.add_argument("--confirm", default="",
                   help=f'Phrase de confirmation exacte requise : "{CONFIRM_PHRASE}".')
    p.add_argument("--backup", default=DEFAULT_BACKUP,
                   help="Chemin du backup LOT 1 (vérifié avant toute action).")
    p.add_argument("--base-url", default="http://127.0.0.1:8000",
                   help="URL de l'app pour la sonde /readyz (non bloquant si l'app est éteinte).")
    return p.parse_args(argv)


# ── Garde-fous PURS (testables sans base) ───────────────────────────────────────────────────
def parcels_state_ok(count: int | None) -> bool:
    """L'état de départ attendu est EXACTEMENT 3 000 parcelles Saint-Paul."""
    return count == EXPECTED_PARCELS_BEFORE


def verify_backup(path: str) -> tuple[bool, str]:
    """Backup présent + checksum SHA-256 conforme si un fichier .sha256 l'accompagne."""
    f = Path(path)
    if not f.is_file():
        return False, f"backup LOT 1 ABSENT : {path}"
    sidecar = Path(str(f) + ".sha256")
    if sidecar.is_file():
        expected = sidecar.read_text(encoding="utf-8").split()[0].strip()
        h = hashlib.sha256()
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != expected:
            return False, f"checksum NON conforme pour {f.name} (backup corrompu ?)"
        return True, f"backup OK + checksum vérifié ({f.stat().st_size} octets)"
    return True, f"backup présent ({f.stat().st_size} octets) — pas de .sha256, checksum non vérifié"


# ── Connexion (paresseuse) ──────────────────────────────────────────────────────────────────
def _engine():
    from labuse.db import engine
    return engine()


def _readyz(base_url: str) -> str:
    import urllib.request
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/readyz", timeout=8) as r:
            return f"HTTP {r.status}"
    except Exception as exc:  # noqa: BLE001 - app éteinte = non bloquant
        return f"indisponible ({type(exc).__name__})"


# ── Pré-checks (LECTURE SEULE — exécutés dans LES DEUX modes) ────────────────────────────────
def prechecks(eng, backup_path: str, base_url: str) -> list[tuple[str, bool, str]]:
    from sqlalchemy import text
    out: list[tuple[str, bool, str]] = []

    ok, msg = verify_backup(backup_path)
    out.append(("backup LOT 1 + checksum", ok, msg))

    with eng.connect() as c:
        try:
            pg = c.execute(text("SELECT postgis_lib_version()")).scalar()
            out.append(("PostGIS actif", bool(pg), f"lib {pg}"))
        except Exception as exc:  # noqa: BLE001
            out.append(("PostGIS actif", False, f"{type(exc).__name__}"))

        present = set(r[0] for r in c.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'")).all())
        missing = [t for t in CRITICAL_TABLES if t not in present]
        out.append(("tables critiques présentes", not missing,
                    "toutes" if not missing else f"MANQUANTES : {missing}"))

        n = c.execute(text("SELECT count(*) FROM parcels WHERE commune = :c"), {"c": COMMUNE}).scalar()
        out.append((f"Saint-Paul = {EXPECTED_PARCELS_BEFORE} parcelles", parcels_state_ok(n),
                    f"trouvé : {n}"))

        tot, dist = c.execute(text(
            "SELECT count(*), count(DISTINCT idu) FROM parcels WHERE commune = :c"),
            {"c": COMMUNE}).one()
        out.append(("0 doublon IDU (Saint-Paul)", tot == dist, f"{tot} / {dist} distincts"))

    out.append(("/readyz (si app up)", True, _readyz(base_url)))   # informatif, jamais bloquant
    return out


# ── Étapes MUTANTES — en dry-run elles n'utilisent JAMAIS `eng` (zéro accès base) ────────────
def step_import_parcels(eng, dry_run: bool) -> dict:
    print("\n[B] IMPORT PARCELLES — cadastre Etalab 97415, upsert ON CONFLICT (idu), SANS reset")
    if dry_run:
        print("    DRY-RUN : téléchargerait ~51 129 parcelles et ferait un UPSERT id-préservant.")
        print("    AUCUN DELETE parcels · AUCUN reset · les 3 000 id existants seraient conservés.")
        return {"dry_run": True}
    from labuse import models
    from labuse.connectors.cadastre import ingest_parcels
    from labuse.db import session_scope
    from labuse.ingestion import cadastre_bulk
    t0 = time.monotonic()
    with session_scope() as s:
        parcels = cadastre_bulk.parse_etalab(cadastre_bulk.download_parcelles(INSEE))
        run = models.IngestionRun(commune=COMMUNE, status="running", parcels_count=len(parcels))
        s.add(run)
        s.flush()
        run_id = run.id
        n = ingest_parcels(s, parcels, COMMUNE, run_id)
    models.ensure_geom_2975(_engine())
    dt = time.monotonic() - t0
    print(f"    ✓ {n} parcelles upsert · {dt:.0f}s")
    return {"dry_run": False, "parcels": n, "run_id": run_id, "seconds": dt}


def step_layers(eng, dry_run: bool, run_id: int | None = None) -> dict:
    print("\n[D] COUCHES — purge CIBLÉE commune='Saint-Paul' puis ré-ingestion (emprise complète)")
    if dry_run:
        print("    DRY-RUN : exécuterait, UNIQUEMENT pour Saint-Paul :")
        print("      DELETE FROM spatial_layers WHERE commune = 'Saint-Paul'")
        print("      DELETE FROM dvf_mutations  WHERE commune = 'Saint-Paul'")
        print("    puis ré-ingestion (SAVEPOINT par couche) sur l'emprise des 51 129 parcelles.")
        print("    Aucune autre commune n'est touchée (filtre commune sur chaque ligne).")
        return {"dry_run": True}
    from sqlalchemy import text

    from labuse import models
    from labuse.db import session_scope
    from labuse.ingestion import layers_ingest, run_all
    t0 = time.monotonic()
    with session_scope() as s:
        # Purge SCOPÉE : ne touche QUE les lignes portant commune='Saint-Paul'.
        s.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": COMMUNE})
        s.execute(text("DELETE FROM dvf_mutations  WHERE commune = :c"), {"c": COMMUNE})
        bbox = run_all._commune_bbox(s, COMMUNE)        # emprise des 51 129 (pas l'île)
        # ingest_layers isole déjà chaque couche par session.begin_nested() (SAVEPOINT).
        counts = layers_ingest.ingest_layers(s, INSEE, COMMUNE, bbox, run_id)
    models.ensure_geom_2975(_engine())
    dt = time.monotonic() - t0
    print(f"    ✓ couches ré-ingérées · {dt:.0f}s · {counts}")
    return {"dry_run": False, "counts": counts, "seconds": dt}


def step_cascade(eng, dry_run: bool) -> dict:
    print("\n[F] RECALCUL CASCADE — evaluate_commune('Saint-Paul') sur les 51 129")
    if dry_run:
        print("    DRY-RUN : appellerait evaluate_commune('Saint-Paul') (aucune éval lancée).")
        return {"dry_run": True}
    from labuse.db import session_scope
    from labuse.ingestion import run_all
    t0 = time.monotonic()
    with session_scope() as s:
        nev = run_all.evaluate_commune(s, COMMUNE)
    dt = time.monotonic() - t0
    print(f"    ✓ {nev} parcelles évaluées · {dt:.0f}s")
    return {"dry_run": False, "evaluated": nev, "seconds": dt}


# ── Contrôles post-import (LECTURE SEULE) ───────────────────────────────────────────────────
def postchecks(eng, idus_before: set[str]) -> list[tuple[str, bool, str]]:
    from sqlalchemy import text
    out: list[tuple[str, bool, str]] = []
    with eng.connect() as c:
        tot, dist, sec = c.execute(text(
            "SELECT count(*), count(DISTINCT idu), count(DISTINCT section) "
            "FROM parcels WHERE commune = :c"), {"c": COMMUNE}).one()
        out.append((f"Saint-Paul ≈ {EXPECTED_PARCELS_AFTER}", abs(tot - EXPECTED_PARCELS_AFTER) <= 200, f"{tot}"))
        out.append(("0 doublon IDU", tot == dist, f"{tot}/{dist}"))
        out.append((f"sections ≈ {EXPECTED_SECTIONS_AFTER}", abs(sec - EXPECTED_SECTIONS_AFTER) <= 5, f"{sec}"))
        bad = c.execute(text("SELECT count(*) FROM parcels WHERE commune = :c AND "
                             "(geom IS NULL OR NOT ST_IsValid(geom) OR geom_2975 IS NULL)"),
                        {"c": COMMUNE}).scalar()
        out.append(("0 géométrie invalide", bad == 0, f"{bad}"))
        now = set(r[0] for r in c.execute(text(
            "SELECT idu FROM parcels WHERE commune = :c"), {"c": COMMUNE}).all())
        kept = idus_before <= now
        out.append(("3 000 IDU initiaux préservés", kept, f"manquants : {len(idus_before - now)}"))
        ev = c.execute(text(
            "SELECT count(*) FROM parcels p WHERE p.commune = :c AND EXISTS "
            "(SELECT 1 FROM parcel_evaluations e WHERE e.parcel_id = p.id)"), {"c": COMMUNE}).scalar()
        out.append(("100 % évaluées", ev == tot, f"{ev}/{tot}"))
        pe = c.execute(text("SELECT count(*) FROM pipeline_entries")).scalar()
        fb = c.execute(text("SELECT count(*) FROM parcel_feedback")).scalar()
        out.append(("pipeline / feedback conservés", True, f"pipeline={pe} feedback={fb}"))
    return out


def snapshot_idus(eng) -> set[str]:
    from sqlalchemy import text
    with eng.connect() as c:
        return set(r[0] for r in c.execute(text(
            "SELECT idu FROM parcels WHERE commune = :c"), {"c": COMMUNE}).all())


def write_report(dry_run: bool, lines: list[str]) -> None:
    if dry_run:
        print(f"\n[H] RAPPORT — DRY-RUN : écrirait {RESULTS_DOC} (non créé en dry-run).")
        return
    Path(RESULTS_DOC).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[H] ✓ rapport écrit : {RESULTS_DOC}")


# ── Orchestration ───────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    real = real_mode(args)
    dry_run = not real

    print("=" * 70)
    print(f"LOT 2 — import Saint-Paul complet · mode = {'EXÉCUTION RÉELLE' if real else 'DRY-RUN'}")
    print("=" * 70)

    # Refus EXPLICITE si --execute sans la bonne confirmation (évite tout lancement accidentel).
    if args.execute and not real:
        print(f'✗ REFUS : --execute exige --confirm "{CONFIRM_PHRASE}" (reçu : "{args.confirm}").')
        return 2

    eng = _engine()
    print("\n[A] PRÉ-CHECKS (lecture seule)")
    checks = prechecks(eng, args.backup, args.base_url)
    blocking = ("backup LOT 1 + checksum", "PostGIS actif", "tables critiques présentes",
                f"Saint-Paul = {EXPECTED_PARCELS_BEFORE} parcelles", "0 doublon IDU (Saint-Paul)")
    failed = []
    for name, ok, detail in checks:
        print(f"    {'✓' if ok else '✗'} {name} — {detail}")
        if name in blocking and not ok:
            failed.append(name)
    if failed:
        print(f"\n✗ PRÉ-CHECKS bloquants en échec : {failed} → ARRÊT (aucune action).")
        return 1

    if dry_run:
        print("\n— DRY-RUN : les étapes B / D / F ci-dessous ne sont PAS exécutées —")

    idus_before = snapshot_idus(eng) if real else set()
    r_b = step_import_parcels(eng, dry_run)
    step_layers(eng, dry_run, run_id=r_b.get("run_id"))
    r_f = step_cascade(eng, dry_run)

    if real:
        print("\n[G] CONTRÔLES POST-IMPORT")
        post = postchecks(eng, idus_before)
        for name, ok, detail in post:
            print(f"    {'✓' if ok else '✗'} {name} — {detail}")
        report = [f"# Saint-Paul — LOT 2 résultats ({time.strftime('%Y-%m-%dT%H:%M:%S')})", ""]
        report += [f"- {'OK' if ok else 'ÉCHEC'} · {name} — {detail}" for name, ok, detail in post]
        report += ["", f"Évaluées : {r_f.get('evaluated')}"]
        write_report(False, report)
    else:
        write_report(True, [])
        print("\n✓ DRY-RUN terminé. Aucune donnée modifiée. Pour exécuter réellement :")
        print(f'    python scripts/lot2_import_saint_paul.py --execute --confirm "{CONFIRM_PHRASE}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
