#!/usr/bin/env python3
"""LOT 6 — import « gold standard » d'UNE commune (générique, DRY-RUN par défaut).

Conçu pour remplacer progressivement `scripts/lot2_import_saint_paul.py` (figé sur Saint-Paul) par un
process paramétré commune par commune. Mêmes garde-fous, mais :
  - commune + INSEE en ARGUMENTS (validés contre le référentiel officiel `REUNION_COMMUNES`) ;
  - métadonnées lues dans `config/communes_gold_standard.yaml` (état, stratégie, vague…) ;
  - détecte l'état réel : ABSENTE / PARTIELLE / GOLD, et adapte le PLAN ;
  - phrase de confirmation **spécifique à la commune** (impossible de relancer la mauvaise) ;
  - refuse de toucher une commune déjà GOLD (protège Saint-Paul) sauf --allow-regold.

SÉCURISÉ PAR DÉFAUT : sans flag, **DRY-RUN** — pré-checks LECTURE SEULE + plan affiché, AUCUNE écriture.
L'exécution réelle exige DEUX garde-fous simultanés :

    python scripts/import_commune_gold_standard.py --commune "La Possession" --insee 97408 \
        --execute --confirm "IMPORT_LA_POSSESSION_COMPLET"

Invariants : DELETE TOUJOURS scopés `WHERE commune=:c` (jamais une autre commune, jamais les parcelles —
upsert id-préservant) ; backup pré-commune vérifié avant toute écriture ; couche critique en échec →
ROLLBACK ; couche non critique → RE-FETCH ; chaque couche isolée par SAVEPOINT. Imports lourds paresseux.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
import traceback
import unicodedata
from pathlib import Path

# Couches dont l'ABSENCE casse la fiche → leur échec impose un ROLLBACK (pas un simple re-fetch).
CRITICAL_LAYERS = ("plu_gpu_zone", "batiment", "pente", "voirie")
# Couches « gold » (présentes pour Saint-Paul seul au 2026-06-20) à garantir au standard.
GOLD_LAYERS = ("batiment", "ppr", "sar", "ravine", "osm_faux_positif", "plu_gpu_prescription", "abf")
CRITICAL_TABLES = ("parcels", "spatial_layers", "cascade_results",
                   "parcel_evaluations", "dvf_mutations", "bilan_params")
ZONAGE_MIN_PCT = 99.0
TOLERANCE_PARCELS = 500

EXIT_OK = 0
EXIT_ROLLBACK = 1        # contrôle critique KO ou crash → rollback recommandé
EXIT_CONFIRM = 2         # --execute sans confirmation exacte / cible invalide
EXIT_REFETCH = 3         # seule(s) couche(s) NON critique(s) en échec → re-fetch suffit


# ── Identité & confirmation (PURS) ────────────────────────────────────────────
def slug(commune: str) -> str:
    """« La Possession » → « LA_POSSESSION » ; « L'Étang-Salé » → « L_ETANG_SALE »."""
    s = unicodedata.normalize("NFKD", commune).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()


def confirm_phrase(commune: str) -> str:
    """Phrase EXACTE requise pour exécuter réellement — nomme la commune (anti-erreur de commune)."""
    return f"IMPORT_{slug(commune)}_COMPLET"


def real_mode(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "execute", False)) and \
        getattr(args, "confirm", "") == confirm_phrase(args.commune)


def validate_target(insee: str, commune: str) -> tuple[bool, str]:
    """INSEE et nom doivent CORRESPONDRE dans le référentiel officiel (24 communes La Réunion)."""
    from labuse.communes import commune_known
    if not commune_known(insee=insee, nom=commune):
        return False, (f"cible INVALIDE : ({insee}, « {commune} ») absente/incohérente dans le "
                       "référentiel officiel REUNION_COMMUNES")
    return True, f"cible valide : {insee} = « {commune} »"


# ── Backup (PUR) ──────────────────────────────────────────────────────────────
def verify_backup(path: str | None) -> tuple[bool, str]:
    if not path:
        return False, "aucun backup pré-commune fourni (--backup requis en mode réel)"
    f = Path(path)
    if not f.is_file():
        return False, f"backup ABSENT : {path}"
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


# ── Classification d'état (PURE) ──────────────────────────────────────────────
def classify_state(parcels: int, bati: int, eval_pct: float) -> str:
    """ABSENTE (0 parcelle) · GOLD (cadastre + bâti + 100 % évalué) · PARTIELLE (sinon)."""
    if parcels <= 0:
        return "absent"
    if bati > 0 and eval_pct >= 100.0:
        return "gold"
    return "partiel"


def missing_gold_layers(layer_counts: dict[str, int]) -> list[str]:
    """Couches « gold » absentes (compte 0) → à (re)charger."""
    return [k for k in GOLD_LAYERS if (layer_counts.get(k) or 0) <= 0]


def plan_for_state(state: str, commune: str, missing: list[str]) -> list[str]:
    """Le PLAN d'actions selon l'état (texte affiché ; aucune action réelle ici)."""
    common_tail = [
        "[E] index : globaux & idempotents (vérifiés) — idx_spatial_layers_voirie_geom2975 requis",
        f"[F] cascade : evaluate_commune('{commune}') — ÉCRASE les verdicts existants (non fiables)",
        "[G] post-checks : compte≈Etalab · sections · géom valide · bâti>0 · top-N sans bâti · 100 % évalué · conservation",
        f"[H] rapport : docs/communes/{slug(commune).lower()}_RESULTS.md",
        "[I] backup POST-vague (horodaté + sha256)",
        "ROLLBACK : restore-db <backup_pré> si contrôle critique KO ou crash",
    ]
    pre = "[0] backup PRÉ-commune (labuse backup-db) — point de retour vérifié"
    couches = (f"[D] couches : DELETE scopé commune='{commune}' puis ré-ingestion CIBLÉE "
               f"(SAVEPOINT/couche) · à (re)charger : {missing or 'toutes les gold'}")
    if state == "absent":
        return [pre,
                "[B] cadastre : IMPORT complet (Etalab INSEE) — upsert id-préservant, compare au compte Etalab",
                couches, *common_tail]
    if state == "gold":
        return ["(déjà GOLD — aucune action sans --allow-regold)"]
    # partiel
    return [pre,
            "[B] cadastre : PRÉSENT — upsert id-préservant (PAS de reset) + compare au compte Etalab",
            couches, *common_tail]


# ── Décision finale (PURE, reprise LOT 2) ─────────────────────────────────────
def layers_errors(counts: dict | None) -> list[str]:
    return sorted(k for k, v in (counts or {}).items()
                  if isinstance(v, str) and v.upper().startswith("ERREUR"))


def classify_layer_failures(errors: list[str]) -> tuple[list[str], list[str]]:
    crit = [k for k in errors if k in CRITICAL_LAYERS]
    noncrit = [k for k in errors if k not in CRITICAL_LAYERS]
    return crit, noncrit


def final_decision(checks: list[tuple], crit_layer_fail: list[str],
                   noncrit_layer_fail: list[str], crashed: bool = False) -> tuple[int, str]:
    if crashed:
        return EXIT_ROLLBACK, "ÉTAT PARTIEL POSSIBLE — ROLLBACK À ENVISAGER"
    critical_failed = [name for (name, ok, critical, _) in checks if critical and not ok]
    if crit_layer_fail or critical_failed:
        why = []
        if crit_layer_fail:
            why.append(f"couches critiques échouées {crit_layer_fail}")
        if critical_failed:
            why.append(f"contrôles critiques KO {critical_failed}")
        return EXIT_ROLLBACK, "ROLLBACK RECOMMANDÉ — " + " ; ".join(why)
    if noncrit_layer_fail:
        return EXIT_REFETCH, f"RE-FETCH COUCHE REQUIS — non critique(s) : {noncrit_layer_fail}"
    return EXIT_OK, "SUCCÈS — commune prête au standard Saint-Paul"


# ── Connexion & lecture d'état (LECTURE SEULE) ────────────────────────────────
def _engine():
    from labuse.db import engine
    return engine()


def _readyz(base_url: str) -> str:
    import urllib.request
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/readyz", timeout=8) as r:
            return f"HTTP {r.status}"
    except Exception as exc:  # noqa: BLE001
        return f"indisponible ({type(exc).__name__})"


def read_state(eng, commune: str) -> dict:
    """Métriques d'état LECTURE SEULE : parcelles, sections, éval %, comptes de couches."""
    from sqlalchemy import text
    with eng.connect() as c:
        tot, dist, sec = c.execute(text(
            "SELECT count(*), count(DISTINCT idu), count(DISTINCT section) FROM parcels WHERE commune=:c"),
            {"c": commune}).one()
        evaluated = c.execute(text(
            "SELECT count(*) FROM parcels p WHERE p.commune=:c AND EXISTS "
            "(SELECT 1 FROM parcel_evaluations e WHERE e.parcel_id=p.id)"), {"c": commune}).scalar()
        rows = c.execute(text(
            "SELECT kind, count(*) FROM spatial_layers WHERE commune=:c GROUP BY kind"), {"c": commune}).all()
        layer_counts = {k: n for k, n in rows}
    eval_pct = round(100.0 * (evaluated or 0) / tot, 1) if tot else 0.0
    return {"parcels": tot, "distinct": dist, "sections": sec,
            "evaluated": evaluated, "eval_pct": eval_pct, "layers": layer_counts}


def prechecks(eng, commune: str, insee: str, backup_path: str | None, base_url: str,
              real: bool) -> tuple[list[tuple[str, bool, str]], dict | None]:
    from sqlalchemy import text
    out: list[tuple[str, bool, str]] = []
    ok, msg = validate_target(insee, commune)
    out.append(("cible dans le référentiel officiel", ok, msg))
    # Backup : bloquant en mode réel seulement.
    bok, bmsg = verify_backup(backup_path)
    out.append(("backup pré-commune + checksum", bok or not real, bmsg if real else "(créé en mode réel)"))
    state = None
    try:
        with eng.connect() as c:
            pg = c.execute(text("SELECT postgis_lib_version()")).scalar()
            out.append(("PostGIS actif", bool(pg), f"lib {pg}"))
            present = set(r[0] for r in c.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'")).all())
            missing = [t for t in CRITICAL_TABLES if t not in present]
            out.append(("tables critiques présentes", not missing,
                        "toutes" if not missing else f"MANQUANTES : {missing}"))
        state = read_state(eng, commune)
        det = classify_state(state["parcels"], state["layers"].get("batiment", 0), state["eval_pct"])
        out.append((f"état mesuré : {det.upper()}",
                    state["parcels"] == state["distinct"],
                    f"{state['parcels']} parcelles · {state['sections']} sections · "
                    f"{state['eval_pct']} % évaluées · bâti={state['layers'].get('batiment', 0)}"))
    except Exception as exc:  # noqa: BLE001 — base injoignable = non bloquant en dry-run
        out.append(("lecture d'état base", False, f"indisponible ({type(exc).__name__})"))
    out.append(("/readyz (si app up)", True, _readyz(base_url)))
    return out, state


# ── Étapes MUTANTES — en DRY-RUN elles n'utilisent JAMAIS `eng` (zéro accès base) ─────────────
def step_import_parcels(commune: str, insee: str, present_count: int, dry_run: bool) -> dict:
    action = "présent — upsert id-préservant" if present_count > 0 else "IMPORT complet (absente)"
    print(f"\n[B] PARCELLES — {action}, cadastre Etalab {insee}, ON CONFLICT (idu), SANS reset")
    if dry_run:
        print("    DRY-RUN : upsert id-préservant + comparaison au compte Etalab. AUCUN DELETE parcels.")
        return {"dry_run": True}
    from labuse import models
    from labuse.connectors.cadastre import ingest_parcels
    from labuse.db import session_scope
    from labuse.ingestion import cadastre_bulk
    t0 = time.monotonic()
    with session_scope() as s:
        parcels = cadastre_bulk.parse_etalab(cadastre_bulk.download_parcelles(insee))
        run = models.IngestionRun(commune=commune, status="running", parcels_count=len(parcels))
        s.add(run)
        s.flush()
        run_id = run.id
        n = ingest_parcels(s, parcels, commune, run_id)
    models.ensure_geom_2975(_engine(), commune=commune)
    dt = time.monotonic() - t0
    print(f"    ✓ {n} parcelles upsert · {dt:.0f}s")
    return {"dry_run": False, "parcels": n, "run_id": run_id, "seconds": dt}


def step_layers(commune: str, insee: str, dry_run: bool, run_id: int | None = None) -> dict:
    print(f"\n[D] COUCHES — purge CIBLÉE commune='{commune}' puis ré-ingestion (emprise commune)")
    if dry_run:
        print(f"    DRY-RUN : exécuterait, UNIQUEMENT pour {commune} :")
        print(f"      DELETE FROM spatial_layers WHERE commune = '{commune}'")
        print(f"      DELETE FROM dvf_mutations  WHERE commune = '{commune}'")
        print("    puis ré-ingestion (SAVEPOINT/couche). Aucune autre commune touchée.")
        return {"dry_run": True}
    from sqlalchemy import text

    from labuse import models
    from labuse.db import session_scope
    from labuse.ingestion import layers_ingest, run_all
    t0 = time.monotonic()
    with session_scope() as s:
        s.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": commune})
        s.execute(text("DELETE FROM dvf_mutations  WHERE commune = :c"), {"c": commune})
        bbox = run_all._commune_bbox(s, commune)
        counts = layers_ingest.ingest_layers(s, insee, commune, bbox, run_id)
    models.ensure_geom_2975(_engine(), commune=commune)
    errs = layers_errors(counts)
    dt = time.monotonic() - t0
    if errs:
        print(f"    ⚠ {len(errs)} couche(s) en ERREUR : {errs}")
    print(f"    ✓ étape couches terminée · {dt:.0f}s")
    return {"dry_run": False, "counts": counts, "errors": errs, "seconds": dt}


def step_cascade(commune: str, dry_run: bool) -> dict:
    print(f"\n[F] CASCADE — evaluate_commune('{commune}') (écrase les verdicts non fiables)")
    if dry_run:
        print("    DRY-RUN : appellerait evaluate_commune (aucune éval lancée).")
        return {"dry_run": True}
    from labuse.db import session_scope
    from labuse.ingestion import run_all
    t0 = time.monotonic()
    with session_scope() as s:
        nev = run_all.evaluate_commune(s, commune)
    dt = time.monotonic() - t0
    print(f"    ✓ {nev} parcelles évaluées · {dt:.0f}s")
    return {"dry_run": False, "evaluated": nev, "seconds": dt}


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LOT 6 — import gold standard d'une commune (DRY-RUN par défaut).")
    p.add_argument("--commune", required=True, help="Nom EXACT de la commune (réf. REUNION_COMMUNES).")
    p.add_argument("--insee", required=True, help="Code INSEE de la commune (doit correspondre au nom).")
    p.add_argument("--execute", action="store_true", help="Exécution RÉELLE (sinon dry-run). Exige --confirm.")
    p.add_argument("--confirm", default="", help='Phrase exacte : "IMPORT_<COMMUNE>_COMPLET".')
    p.add_argument("--backup", default=None, help="Chemin du backup pré-commune (vérifié en mode réel).")
    p.add_argument("--allow-regold", action="store_true",
                   help="Autorise de retraiter une commune DÉJÀ gold (protège Saint-Paul par défaut).")
    p.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL app pour /readyz (non bloquant).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from labuse import communes
    args = parse_args(argv)
    real = real_mode(args)
    dry_run = not real
    phrase = confirm_phrase(args.commune)

    print("=" * 74)
    print(f"IMPORT COMMUNE GOLD STANDARD — {args.commune} ({args.insee}) · "
          f"mode = {'EXÉCUTION RÉELLE' if real else 'DRY-RUN'}")
    print("=" * 74)

    # Validation de cible AVANT tout (anti-erreur de commune).
    tgt_ok, tgt_msg = validate_target(args.insee, args.commune)
    if not tgt_ok:
        print(f"✗ REFUS : {tgt_msg}")
        return EXIT_CONFIRM
    if args.execute and not real:
        print(f'✗ REFUS : --execute exige --confirm "{phrase}" (reçu : "{args.confirm}").')
        return EXIT_CONFIRM

    cfg = communes.get(args.commune) or {}
    print(f"\n[CONFIG] {args.commune} ({args.insee})")
    print(f"    config : état={cfg.get('etat', '?')} · stratégie={cfg.get('strategie', '?')} · "
          f"vague {cfg.get('vague', '?')} · risque {cfg.get('risque', '?')}")
    att = cfg.get("attendu")
    att_txt = "à vérifier (confirmé au compte Etalab à l'import)" if att in (None, "a_verifier") else str(att)
    print(f"    parcelles attendues (Etalab) : {att_txt}")

    # Garde : commune déjà GOLD → refus (protège Saint-Paul).
    if cfg.get("etat") == "gold" and not args.allow_regold:
        print(f"\n✓ {args.commune} est déjà GOLD (validée au standard). "
              "Aucune action — utilisez --allow-regold pour forcer un retraitement.")
        return EXIT_OK

    eng = _engine()
    print("\n[A] PRÉ-CHECKS (lecture seule)")
    checks, state = prechecks(eng, args.commune, args.insee, args.backup, args.base_url, real)
    for name, ok, detail in checks:
        print(f"    {'✓' if ok else '✗'} {name} — {detail}")

    # État détecté + couches gold manquantes.
    if state is not None:
        det = classify_state(state["parcels"], state["layers"].get("batiment", 0), state["eval_pct"])
        missing = missing_gold_layers(state["layers"])
        print(f"\n    → ÉTAT DÉTECTÉ : {det.upper()}"
              + (f" · couches gold manquantes : {missing}" if missing else " · couches gold complètes"))
        if det != "gold" and state["eval_pct"] >= 100.0:
            print("    ⚠ verdicts actuels NON fiables (évalués sans toutes les couches critiques).")
    else:
        det = cfg.get("etat", "partiel").split("_")[0]
        missing = list(GOLD_LAYERS)
        print(f"\n    → base injoignable : état présumé d'après la config = {det.upper()}")

    print(f"\n[PLAN] stratégie = {cfg.get('strategie', 're_couches_re_cascade')}")
    for line in plan_for_state("absent" if det == "absent" else det, args.commune, missing):
        print(f"    {line}")

    # Bloquants mode réel.
    blocking = ("cible dans le référentiel officiel", "backup pré-commune + checksum",
                "PostGIS actif", "tables critiques présentes")
    pre_failed = [n for (n, ok, _) in checks if n in blocking and not ok]

    if dry_run:
        print("\n✓ DRY-RUN terminé. AUCUNE donnée modifiée. Pour exécuter réellement :")
        print(f'    python scripts/import_commune_gold_standard.py --commune "{args.commune}" '
              f'--insee {args.insee} \\')
        print(f'        --execute --confirm "{phrase}" --backup <dump_pré_commune>')
        return EXIT_OK

    if pre_failed:
        print(f"\n✗ PRÉ-CHECKS bloquants en échec : {pre_failed} → ARRÊT (aucune action).")
        return EXIT_ROLLBACK

    # ── EXÉCUTION RÉELLE (gated) ────────────────────────────────────────────────
    present = state["parcels"] if state else 0
    try:
        r_b = step_import_parcels(args.commune, args.insee, present, False)
        r_d = step_layers(args.commune, args.insee, False, run_id=r_b.get("run_id"))
        step_cascade(args.commune, False)
    except Exception as exc:  # noqa: BLE001
        print(f"\n✗ EXCEPTION pendant une étape mutante : {type(exc).__name__}: {exc}")
        print(traceback.format_exc())
        code, verdict = final_decision([], [], [], crashed=True)
        print(f"\n⛔ {verdict}")
        return code
    crit_lf, noncrit_lf = classify_layer_failures(r_d.get("errors", []))
    code, verdict = final_decision([], crit_lf, noncrit_lf, crashed=False)
    print(f"\n{'✓' if code == EXIT_OK else '⛔'} {verdict}")
    print("    (post-checks détaillés & rapport : à brancher comme dans lot2_import_saint_paul.py)")
    return code


if __name__ == "__main__":
    sys.exit(main())
