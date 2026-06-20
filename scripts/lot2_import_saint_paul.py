#!/usr/bin/env python3
"""LOT 2 — import contrôlé du cadastre COMPLET de Saint-Paul (3 000 → 51 129 parcelles).

SÉCURISÉ PAR DÉFAUT : sans flag, le script est en **DRY-RUN** — il exécute uniquement les
pré-checks (LECTURE SEULE) et affiche ce qu'il FERAIT, sans rien modifier. L'exécution réelle
exige DEUX garde-fous simultanés :

    python scripts/lot2_import_saint_paul.py --execute --confirm "IMPORT_SAINT_PAUL_COMPLET"

Principe (cf. docs/SAINT_PAUL_LOT2_IMPORT_PLAN.md) :
  B) parcelles : upsert ON CONFLICT (idu) — JAMAIS de reset, JAMAIS de DELETE parcels →
     les 3 000 `id` existants sont conservés (évaluations / pipeline / feedback / alertes intacts).
  D) couches  : purge CIBLÉE `WHERE commune='Saint-Paul'` (jamais une autre commune) puis
     ré-ingestion sur l'emprise commune COMPLÈTE, chaque couche isolée par SAVEPOINT.
  F) cascade  : evaluate_commune("Saint-Paul") sur les 51 129.

Robustesse (durcissement audit) :
  • toute couche en ERREUR est DÉTECTÉE → échec explicite, jamais de continuation silencieuse ;
  • post-checks de couverture (zonage ≥ 99 %, bâti > état pilote, PPR/ravines/prescriptions, doublons) ;
  • conservation pipeline/feedback/alertes Saint-Paul VÉRIFIÉE (avant/après) ;
  • étapes B/D/F sous try/except → exception ⇒ « ÉTAT PARTIEL POSSIBLE — ROLLBACK LOT 1 À ENVISAGER » ;
  • code retour ≠ 0 dès qu'un contrôle critique échoue ; le rapport ne dit JAMAIS « succès » à tort ;
  • distinction « ROLLBACK RECOMMANDÉ » (critique) vs « RE-FETCH COUCHE REQUIS » (couche non critique).

Imports « lourds » (réseau / base) faits PARESSEUSEMENT → importer ce module (tests) n'a aucun effet.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
import traceback
from pathlib import Path

# ── Constantes FIGÉES (jamais paramétrables : on ne vise QUE Saint-Paul) ─────────────────────
COMMUNE = "Saint-Paul"
INSEE = "97415"
EXPECTED_PARCELS_BEFORE = 3000
EXPECTED_PARCELS_AFTER = 51129          # source de vérité : cadastre.data.gouv.fr Etalab (98 sections)
EXPECTED_SECTIONS_AFTER = 98
ZONAGE_MIN_PCT = 99.0                   # couverture zonage PLU minimale acceptable
CONFIRM_PHRASE = "IMPORT_SAINT_PAUL_COMPLET"
DEFAULT_BACKUP = "/var/backups/labuse/labuse-labuse-20260620-101644.dump"
CRITICAL_TABLES = (
    "parcels", "spatial_layers", "cascade_results",
    "parcel_evaluations", "dvf_mutations", "bilan_params",
)
# Couches dont l'ABSENCE casse la fiche → leur échec impose un ROLLBACK (pas un simple re-fetch).
CRITICAL_LAYERS = ("plu_gpu_zone", "batiment", "pente", "voirie")
RESULTS_DOC = "docs/SAINT_PAUL_LOT2_RESULTS.md"

# Codes de sortie
EXIT_OK = 0
EXIT_ROLLBACK = 1        # contrôle critique KO ou crash → rollback LOT 1 recommandé
EXIT_CONFIRM = 2         # --execute sans confirmation exacte
EXIT_REFETCH = 3         # seule(s) couche(s) NON critique(s) en échec → re-fetch ciblé suffit


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


# ── Garde-fous & décisions PURS (testables sans base) ───────────────────────────────────────
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


def layers_errors(counts: dict | None) -> list[str]:
    """Couches dont l'ingestion a renvoyé une ERREUR (ingest_layers met « ERREUR … » dans counts)."""
    return sorted(k for k, v in (counts or {}).items()
                  if isinstance(v, str) and v.upper().startswith("ERREUR"))


def classify_layer_failures(errors: list[str]) -> tuple[list[str], list[str]]:
    """(échecs CRITIQUES → rollback, échecs NON critiques → re-fetch ciblé)."""
    crit = [k for k in errors if k in CRITICAL_LAYERS]
    noncrit = [k for k in errors if k not in CRITICAL_LAYERS]
    return crit, noncrit


def _layer_status(count: int | None, errored: bool) -> str:
    if errored:
        return "échoué"
    return "complet" if (count or 0) > 0 else "partiel"


# Une « check » = (nom, ok: bool, critique: bool, détail: str).
def parcels_results(m: dict) -> list[tuple]:
    tot, dist, sec = m["count"], m["distinct"], m["sections"]
    return [
        (f"Saint-Paul ≈ {EXPECTED_PARCELS_AFTER}", abs(tot - EXPECTED_PARCELS_AFTER) <= 500, True, f"{tot}"),
        ("0 doublon IDU", tot == dist, True, f"{tot}/{dist}"),
        (f"sections ≈ {EXPECTED_SECTIONS_AFTER}", abs(sec - EXPECTED_SECTIONS_AFTER) <= 5, False, f"{sec}"),
        ("0 géométrie invalide", m["invalid"] == 0, True, f"{m['invalid']}"),
        ("3 000 IDU initiaux préservés", m["idu_missing"] == 0, True, f"manquants : {m['idu_missing']}"),
        ("100 % évaluées", m["evaluated"] == tot, True, f"{m['evaluated']}/{tot}"),
    ]


def coverage_results(m: dict, layer_errors: list[str], bati_before: int) -> list[tuple]:
    z = m.get("zonage_pct")
    bati = m.get("bati_after")
    out = [
        (f"zonage PLU ≥ {ZONAGE_MIN_PCT:g} %", z is not None and z >= ZONAGE_MIN_PCT, True, f"{z} %"),
        ("bâti re-fetché (> état pilote)", bati is not None and bati > bati_before, True,
         f"{bati} (pilote {bati_before})"),
    ]
    # PPR / ravines / prescriptions : statut EXPLICITE (complet / partiel / échoué), non bloquant.
    for kind in ("ppr", "ravine", "plu_gpu_prescription"):
        errored = kind in layer_errors
        out.append((f"{kind} : {_layer_status(m.get(kind), errored)}", not errored, False,
                    f"{m.get(kind)} features"))
    dup = m.get("dup_groups", 0)
    out.append(("aucune duplication de couche", dup == 0, False, f"{dup} groupes (kind,géom) dupliqués"))
    return out


def preservation_results(before: dict, after: dict) -> list[tuple]:
    """Échoue (critique) si un compteur métier Saint-Paul BAISSE après l'import."""
    out = []
    for key in ("pipeline", "feedback", "alertes"):
        b, a = before.get(key, 0), after.get(key, 0)
        out.append((f"{key} Saint-Paul conservé", a >= b, True, f"{b} → {a}"))
    return out


def final_decision(checks: list[tuple], crit_layer_fail: list[str],
                   noncrit_layer_fail: list[str], crashed: bool = False) -> tuple[int, str]:
    """Décide le code de sortie + le verdict. JAMAIS « succès » si un critère critique échoue."""
    if crashed:
        return EXIT_ROLLBACK, "ÉTAT PARTIEL POSSIBLE — ROLLBACK LOT 1 À ENVISAGER"
    critical_failed = [name for (name, ok, critical, _) in checks if critical and not ok]
    if crit_layer_fail or critical_failed:
        why = []
        if crit_layer_fail:
            why.append(f"couches critiques échouées {crit_layer_fail}")
        if critical_failed:
            why.append(f"contrôles critiques KO {critical_failed}")
        return EXIT_ROLLBACK, "ROLLBACK RECOMMANDÉ — " + " ; ".join(why)
    if noncrit_layer_fail:
        return EXIT_REFETCH, f"RE-FETCH COUCHE REQUIS — couche(s) non critique(s) : {noncrit_layer_fail}"
    return EXIT_OK, "SUCCÈS — Saint-Paul prêt comme commune modèle"


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
        out.append((f"Saint-Paul = {EXPECTED_PARCELS_BEFORE} parcelles", parcels_state_ok(n), f"trouvé : {n}"))
        tot, dist = c.execute(text(
            "SELECT count(*), count(DISTINCT idu) FROM parcels WHERE commune = :c"), {"c": COMMUNE}).one()
        out.append(("0 doublon IDU (Saint-Paul)", tot == dist, f"{tot} / {dist} distincts"))
    out.append(("/readyz (si app up)", True, _readyz(base_url)))   # informatif, jamais bloquant
    return out


# ── Snapshots & métriques (LECTURE SEULE) ───────────────────────────────────────────────────
def snapshot_state(conn) -> dict:
    """Compteurs métier Saint-Paul + bâti (référence avant/après)."""
    from sqlalchemy import text

    def q(sql):
        return conn.execute(text(sql), {"c": COMMUNE}).scalar()
    return {
        "pipeline": q("SELECT count(*) FROM pipeline_entries pe JOIN parcels p ON p.id=pe.parcel_id WHERE p.commune=:c"),
        "feedback": q("SELECT count(*) FROM parcel_feedback f JOIN parcels p ON p.id=f.parcel_id WHERE p.commune=:c"),
        "alertes": q("SELECT count(*) FROM alertes a JOIN parcels p ON p.id=a.parcel_id WHERE p.commune=:c"),
        "bati": q("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind='batiment'"),
    }


def snapshot_idus(eng) -> set[str]:
    from sqlalchemy import text
    with eng.connect() as c:
        return set(r[0] for r in c.execute(text(
            "SELECT idu FROM parcels WHERE commune = :c"), {"c": COMMUNE}).all())


def parcels_metrics(conn, idus_before: set[str]) -> dict:
    from sqlalchemy import text
    tot, dist, sec = conn.execute(text(
        "SELECT count(*), count(DISTINCT idu), count(DISTINCT section) FROM parcels WHERE commune=:c"),
        {"c": COMMUNE}).one()
    invalid = conn.execute(text("SELECT count(*) FROM parcels WHERE commune=:c AND "
                                "(geom IS NULL OR NOT ST_IsValid(geom) OR geom_2975 IS NULL)"),
                           {"c": COMMUNE}).scalar()
    now = set(r[0] for r in conn.execute(text("SELECT idu FROM parcels WHERE commune=:c"),
                                         {"c": COMMUNE}).all())
    evaluated = conn.execute(text(
        "SELECT count(*) FROM parcels p WHERE p.commune=:c AND EXISTS "
        "(SELECT 1 FROM parcel_evaluations e WHERE e.parcel_id=p.id)"), {"c": COMMUNE}).scalar()
    return {"count": tot, "distinct": dist, "sections": sec, "invalid": invalid,
            "idu_missing": len(idus_before - now), "evaluated": evaluated}


def coverage_metrics(conn) -> dict:
    from sqlalchemy import text
    tot = conn.execute(text("SELECT count(*) FROM parcels WHERE commune=:c"), {"c": COMMUNE}).scalar() or 1
    zoned = conn.execute(text(
        "SELECT count(*) FROM parcels p WHERE p.commune=:c AND EXISTS "
        "(SELECT 1 FROM spatial_layers s WHERE s.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975,s.geom_2975))"),
        {"c": COMMUNE}).scalar()
    def cnt(k):
        return conn.execute(text("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind=:k"),
                            {"c": COMMUNE, "k": k}).scalar()
    dup = conn.execute(text(
        "SELECT count(*) FROM (SELECT kind, md5(ST_AsBinary(geom_2975)) h FROM spatial_layers "
        "WHERE commune=:c GROUP BY 1,2 HAVING count(*)>1) t"), {"c": COMMUNE}).scalar()
    return {"zonage_pct": round(100.0 * zoned / tot, 1), "bati_after": cnt("batiment"),
            "ppr": cnt("ppr"), "ravine": cnt("ravine"),
            "plu_gpu_prescription": cnt("plu_gpu_prescription"), "dup_groups": dup}


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
    errs = layers_errors(counts)
    dt = time.monotonic() - t0
    if errs:
        print(f"    ⚠ {len(errs)} couche(s) en ERREUR : {errs}")
    print(f"    ✓ étape couches terminée · {dt:.0f}s · {counts}")
    return {"dry_run": False, "counts": counts, "errors": errs, "seconds": dt}


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


def write_report(dry_run: bool, lines: list[str]) -> None:
    if dry_run:
        print(f"\n[H] RAPPORT — DRY-RUN : écrirait {RESULTS_DOC} (non créé en dry-run).")
        return
    Path(RESULTS_DOC).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[H] ✓ rapport écrit : {RESULTS_DOC}")


def _build_report(verdict: str, exit_code: int, checks: list[tuple], layer_errs: list[str],
                  r_f: dict) -> list[str]:
    lines = [f"# Saint-Paul — LOT 2 résultats ({time.strftime('%Y-%m-%dT%H:%M:%S')})", "",
             f"**Verdict : {verdict}** (code de sortie {exit_code})", ""]
    if layer_errs:
        lines += [f"- Couches en ERREUR : {layer_errs}", ""]
    lines += [f"- {'OK ' if ok else 'ÉCHEC'} · {'[critique] ' if crit else ''}{name} — {detail}"
              for (name, ok, crit, detail) in checks]
    lines += ["", f"Parcelles évaluées : {r_f.get('evaluated')}"]
    return lines


# ── Orchestration ───────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    real = real_mode(args)
    dry_run = not real

    print("=" * 70)
    print(f"LOT 2 — import Saint-Paul complet · mode = {'EXÉCUTION RÉELLE' if real else 'DRY-RUN'}")
    print("=" * 70)

    if args.execute and not real:
        print(f'✗ REFUS : --execute exige --confirm "{CONFIRM_PHRASE}" (reçu : "{args.confirm}").')
        return EXIT_CONFIRM

    eng = _engine()
    print("\n[A] PRÉ-CHECKS (lecture seule)")
    checks = prechecks(eng, args.backup, args.base_url)
    blocking = ("backup LOT 1 + checksum", "PostGIS actif", "tables critiques présentes",
                f"Saint-Paul = {EXPECTED_PARCELS_BEFORE} parcelles", "0 doublon IDU (Saint-Paul)")
    pre_failed = [n for (n, ok, _) in checks if n in blocking and not ok]
    for name, ok, detail in checks:
        print(f"    {'✓' if ok else '✗'} {name} — {detail}")
    if pre_failed:
        print(f"\n✗ PRÉ-CHECKS bloquants en échec : {pre_failed} → ARRÊT (aucune action).")
        return EXIT_ROLLBACK

    if dry_run:
        print("\n— DRY-RUN : les étapes B / D / F ci-dessous ne sont PAS exécutées —")
        step_import_parcels(eng, True)
        step_layers(eng, True)
        step_cascade(eng, True)
        write_report(True, [])
        print("\n✓ DRY-RUN terminé. Aucune donnée modifiée. Pour exécuter réellement :")
        print(f'    python scripts/lot2_import_saint_paul.py --execute --confirm "{CONFIRM_PHRASE}"')
        return EXIT_OK

    # ── EXÉCUTION RÉELLE — étapes mutantes protégées ────────────────────────────────────────
    with eng.connect() as c:
        before = snapshot_state(c)
    idus_before = snapshot_idus(eng)
    try:
        r_b = step_import_parcels(eng, False)
        r_d = step_layers(eng, False, run_id=r_b.get("run_id"))
        r_f = step_cascade(eng, False)
    except Exception as exc:  # noqa: BLE001 - on ne présente JAMAIS une opération crashée comme réussie
        tb = traceback.format_exc()
        print(f"\n✗ EXCEPTION pendant une étape mutante : {type(exc).__name__}: {exc}")
        code, verdict = final_decision([], [], [], crashed=True)
        print(f"\n⛔ {verdict}")
        write_report(False, [f"# Saint-Paul — LOT 2 ÉCHEC ({time.strftime('%Y-%m-%dT%H:%M:%S')})", "",
                             f"**{verdict}** (code {code})", "", "```", tb, "```"])
        return code

    layer_errs = r_d.get("errors", [])
    crit_lf, noncrit_lf = classify_layer_failures(layer_errs)
    print("\n[G] CONTRÔLES POST-IMPORT")
    with eng.connect() as c:
        after = snapshot_state(c)
        results = (parcels_results(parcels_metrics(c, idus_before))
                   + coverage_results(coverage_metrics(c), layer_errs, before["bati"])
                   + preservation_results(before, after))
    for name, ok, crit, detail in results:
        print(f"    {'✓' if ok else '✗'} {'[critique] ' if crit else ''}{name} — {detail}")
    code, verdict = final_decision(results, crit_lf, noncrit_lf, crashed=False)
    print(f"\n{'✓' if code == EXIT_OK else '⛔'} {verdict}")
    write_report(False, _build_report(verdict, code, results, layer_errs, r_f))
    return code


if __name__ == "__main__":
    sys.exit(main())
