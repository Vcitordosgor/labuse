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
# Taux d'« opportunité » au-delà duquel le résultat est jugé QA-suspect (signe d'une cascade SANS bâti :
# Saint-Paul gold ≈ 1 %, les communes non fiables montaient à 5–11 %). Heuristique, severité « qa ».
OPP_RATE_MAX_PCT = 5.0
# Index GIST attendus (globaux, idempotents) — leur absence rend la cascade lente / les calculs faux.
EXPECTED_INDEXES = ("idx_parcels_geom_2975", "idx_spatial_layers_geom_2975",
                    "idx_spatial_layers_voirie_geom2975")

# Détection de doublons EXACTS de couche : un même objet réglementaire ré-ingéré 2× (overlap de pages WFS,
# cf. Saint-Denis/Saint-Joseph). La clé inclut la géométrie ET les attributs réglementaires
# (kind, géom, subtype, name, attrs) — sinon deux objets DIFFÉRENTS superposés sur la même surface
# (ex. Le Port : OAP sectorielle + règle de mixité logement = 2 prescriptions GPU distinctes) seraient
# comptés à tort comme doublon. Un vrai doublon exact (tout identique) reste détecté.
DUP_GROUPS_SQL = (
    "SELECT count(*) FROM ("
    " SELECT kind, md5(ST_AsBinary(geom_2975)) AS h, subtype, name, md5(attrs::text) AS ah"
    " FROM spatial_layers WHERE commune = :c"
    " GROUP BY 1, 2, 3, 4, 5 HAVING count(*) > 1"
    ") t"
)

EXIT_OK = 0
EXIT_ROLLBACK = 1        # contrôle critique KO ou crash → rollback recommandé
EXIT_CONFIRM = 2         # --execute sans confirmation exacte / cible invalide
EXIT_REFETCH = 3         # seule(s) couche(s) NON critique(s) en échec → re-fetch ciblé suffit
EXIT_NOGO_QA = 4         # import OK techniquement mais résultat QA-suspect → ne PAS marquer gold, investiguer


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
    """Décide le code de sortie. Précédence : ROLLBACK(1) > NO-GO QA(4) > RE-FETCH(3) > SUCCÈS(0).

    `checks` = liste (nom, ok, severite, détail) avec severite ∈ {'critique','qa','info'}.
    """
    if crashed:
        return EXIT_ROLLBACK, "ÉTAT PARTIEL POSSIBLE — ROLLBACK À ENVISAGER"
    crit_failed = [n for (n, ok, sev, _) in checks if sev == "critique" and not ok]
    qa_failed = [n for (n, ok, sev, _) in checks if sev == "qa" and not ok]
    if crit_layer_fail or crit_failed:
        why = []
        if crit_layer_fail:
            why.append(f"couches critiques échouées {crit_layer_fail}")
        if crit_failed:
            why.append(f"contrôles critiques KO {crit_failed}")
        return EXIT_ROLLBACK, "ROLLBACK RECOMMANDÉ — " + " ; ".join(why)
    if qa_failed:
        return EXIT_NOGO_QA, f"NO-GO QA — résultat suspect, ne PAS marquer gold (investiguer) : {qa_failed}"
    if noncrit_layer_fail:
        return EXIT_REFETCH, f"RE-FETCH COUCHE REQUIS — non critique(s) : {noncrit_layer_fail}"
    return EXIT_OK, "SUCCÈS — commune prête au standard Saint-Paul"


# ── Post-checks [G] (PURS — logique testable sur un dict de métriques) ────────
def _layer_status_label(count: int | None, errored: bool) -> str:
    if errored:
        return "BLOQUÉ"
    return "complet" if (count or 0) > 0 else "absent/partiel"


def postcheck_results(m: dict, before: dict, expected_min: int,
                      layer_errors: list[str]) -> list[tuple]:
    """Tous les contrôles post-traitement. Renvoie [(nom, ok, severite, détail)].

    `m` (métriques mesurées) : parcels, distinct, sections, geom_invalid, geom2975_null, evaluated,
    layers{kind:count}, zonage_pct, dup_groups, verdicts{...}, opp_rate_pct, micro_opp, indexes[],
    alertes/pipeline/feedback. `before` : compteurs métier avant. `expected_min` : plancher de parcelles.
    """
    lay = m.get("layers", {})
    v = m.get("verdicts", {})
    out: list[tuple] = [
        (f"parcelles ≥ attendu ({expected_min})", m["parcels"] >= expected_min - TOLERANCE_PARCELS,
         "critique", f"{m['parcels']} (min {expected_min})"),
        ("sections présentes", (m.get("sections") or 0) >= 1, "info", f"{m.get('sections')}"),
        ("0 doublon IDU", m["parcels"] == m["distinct"], "critique", f"{m['parcels']}/{m['distinct']}"),
        ("0 géométrie invalide", m.get("geom_invalid", 0) == 0, "critique", f"{m.get('geom_invalid')}"),
        ("100 % geom_2975", m.get("geom2975_null", 0) == 0, "critique", f"nuls : {m.get('geom2975_null')}"),
        ("100 % évaluées", m.get("evaluated") == m["parcels"], "critique",
         f"{m.get('evaluated')}/{m['parcels']}"),
        ("bâti présent (> 0)", (lay.get("batiment") or 0) > 0, "critique", f"{lay.get('batiment')}"),
        ("zonage PLU présent", (lay.get("plu_gpu_zone") or 0) > 0, "critique", f"{lay.get('plu_gpu_zone')}"),
        ("pente présente", (lay.get("pente") or 0) > 0, "critique", f"{lay.get('pente')}"),
        ("voirie présente", (lay.get("voirie") or 0) > 0, "critique", f"{lay.get('voirie')}"),
        (f"couverture zonage ≥ {ZONAGE_MIN_PCT:g} %", (m.get("zonage_pct") or 0) >= ZONAGE_MIN_PCT,
         "critique", f"{m.get('zonage_pct')} %"),
        ("aucune duplication de couche", m.get("dup_groups", 0) == 0, "critique",
         f"{m.get('dup_groups')} groupes (kind,géom) dupliqués"),
    ]
    # PPR / SAR / ravines / prescriptions : statut EXPLICITE (complet / absent / BLOQUÉ), non bloquant.
    for kind in ("ppr", "sar", "ravine", "plu_gpu_prescription"):
        errored = kind in layer_errors
        out.append((f"{kind} : {_layer_status_label(lay.get(kind), errored)}", not errored, "info",
                    f"{lay.get(kind)} features"))
    # Index GIST.
    idx = set(m.get("indexes", []))
    missing_idx = [i for i in EXPECTED_INDEXES if i not in idx]
    out.append(("index GIST présents", not missing_idx, "critique",
                "tous" if not missing_idx else f"MANQUANTS : {missing_idx}"))
    # Cohérence des verdicts : la somme des 4 statuts = nombre d'évaluées.
    vsum = sum(v.get(k, 0) for k in ("opportunite", "a_creuser", "exclue", "faux_positif_probable"))
    out.append(("verdicts cohérents (Σ = évaluées)", vsum == (m.get("evaluated") or 0), "critique",
                f"{vsum}/{m.get('evaluated')}"))
    # Taux d'opportunités NON explosif (QA — signe d'une cascade sans bâti).
    rate = m.get("opp_rate_pct")
    out.append((f"taux d'opportunité non explosif (≤ {OPP_RATE_MAX_PCT:g} %)",
                rate is not None and rate <= OPP_RATE_MAX_PCT, "qa",
                f"{rate} % ({v.get('opportunite')} opp)"))
    # Conservation des données métier (si elles existaient avant) — jamais de baisse.
    for key in ("pipeline", "feedback", "alertes"):
        b, a = before.get(key, 0), m.get(key, 0)
        out.append((f"{key} conservé (≥ avant)", a >= b, "critique", f"{b} → {a}"))
    return out


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


def snapshot_before(eng, commune: str) -> dict:
    """Compteurs métier AVANT traitement (conservation) — LECTURE SEULE."""
    from sqlalchemy import text
    with eng.connect() as c:
        def q(sql):
            return c.execute(text(sql), {"c": commune}).scalar() or 0
        return {
            "pipeline": q("SELECT count(*) FROM pipeline_entries pe JOIN parcels p ON p.id=pe.parcel_id WHERE p.commune=:c"),
            "feedback": q("SELECT count(*) FROM parcel_feedback f JOIN parcels p ON p.id=f.parcel_id WHERE p.commune=:c"),
            "alertes": q("SELECT count(*) FROM alertes a JOIN parcels p ON p.id=a.parcel_id WHERE p.commune=:c"),
            "bati": q("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind='batiment'"),
            "parcels": q("SELECT count(*) FROM parcels WHERE commune=:c"),
        }


def read_postcheck_metrics(eng, commune: str) -> dict:
    """Toutes les métriques post-traitement [G] — LECTURE SEULE (exécuté APRÈS les étapes mutantes)."""
    from sqlalchemy import text
    with eng.connect() as c:
        def q(sql):
            return c.execute(text(sql), {"c": commune}).scalar()
        tot, dist, sec = c.execute(text(
            "SELECT count(*), count(DISTINCT idu), count(DISTINCT section) FROM parcels WHERE commune=:c"),
            {"c": commune}).one()
        geom_invalid = q("SELECT count(*) FROM parcels WHERE commune=:c AND (geom IS NULL OR NOT ST_IsValid(geom))")
        geom2975_null = q("SELECT count(*) FROM parcels WHERE commune=:c AND geom_2975 IS NULL")
        evaluated = q("SELECT count(*) FROM parcels p WHERE p.commune=:c AND EXISTS "
                      "(SELECT 1 FROM parcel_evaluations e WHERE e.parcel_id=p.id)")
        layers = {k: n for k, n in c.execute(text(
            "SELECT kind, count(*) FROM spatial_layers WHERE commune=:c GROUP BY kind"), {"c": commune}).all()}
        zoned = q("SELECT count(*) FROM parcels p WHERE p.commune=:c AND EXISTS "
                  "(SELECT 1 FROM spatial_layers s WHERE s.kind='plu_gpu_zone' "
                  "AND ST_Intersects(p.geom_2975,s.geom_2975))")
        dup = q(DUP_GROUPS_SQL)
        # Verdicts = DERNIÈRE évaluation par parcelle (DISTINCT ON), scopé commune.
        vrows = c.execute(text(
            "WITH latest AS (SELECT DISTINCT ON (p.id) e.status FROM parcels p "
            "JOIN parcel_evaluations e ON e.parcel_id=p.id WHERE p.commune=:c "
            "ORDER BY p.id, e.evaluated_at DESC) SELECT status, count(*) FROM latest GROUP BY status"),
            {"c": commune}).all()
        verdicts = {s: n for s, n in vrows}
        micro = q("WITH latest AS (SELECT DISTINCT ON (p.id) p.surface_m2, e.status FROM parcels p "
                  "JOIN parcel_evaluations e ON e.parcel_id=p.id WHERE p.commune=:c "
                  "ORDER BY p.id, e.evaluated_at DESC) SELECT count(*) FROM latest "
                  "WHERE status='opportunite' AND surface_m2>250 AND surface_m2<=500")
        indexes = [r[0] for r in c.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname = ANY(:names)"),
            {"names": list(EXPECTED_INDEXES)}).all()]
        before_after = snapshot_before(eng, commune)   # ré-utilise pour pipeline/feedback/alertes APRÈS
    opp = verdicts.get("opportunite", 0)
    opp_rate = round(100.0 * opp / tot, 1) if tot else 0.0
    return {"parcels": tot, "distinct": dist, "sections": sec, "geom_invalid": geom_invalid,
            "geom2975_null": geom2975_null, "evaluated": evaluated, "layers": layers,
            "zonage_pct": round(100.0 * (zoned or 0) / tot, 1) if tot else 0.0,
            "dup_groups": dup, "verdicts": verdicts, "opp_rate_pct": opp_rate,
            "micro_opp": micro, "indexes": indexes,
            "pipeline": before_after["pipeline"], "feedback": before_after["feedback"],
            "alertes": before_after["alertes"]}


def expected_min_parcels(cfg: dict, imported_count: int | None) -> int:
    """Plancher de parcelles attendu (jamais inventé) :
    - commune présente : au moins le compte mesuré en base (config.parcelles_en_base) ;
    - commune absente : le compte RÉEL importé depuis Etalab (imported_count), pas une constante.
    'attendu' confirmé (Saint-Paul) est aussi pris en compte. 'a_verifier' n'invente rien.
    """
    base = int(cfg.get("parcelles_en_base") or 0)
    att = cfg.get("attendu")
    confirmed = int(att) if isinstance(att, int) else 0
    imported = int(imported_count or 0)
    return max(base, confirmed, imported)


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


# ── Rapport [H] (PUR — assemble le markdown ; write_report l'écrit) ───────────
def report_path(commune: str) -> str:
    return f"docs/communes/{slug(commune).lower()}_RESULTS.md"


_VERDICT_LABEL = {"opportunite": "Opportunité", "a_creuser": "À creuser",
                  "exclue": "Écartée", "faux_positif_probable": "Faux positif probable"}


def build_report(commune: str, insee: str, strategie: str, verdict: str, exit_code: int,
                 before: dict, m: dict, checks: list[tuple], layer_errors: list[str],
                 seconds: dict | None = None) -> list[str]:
    """Lignes markdown du rapport commune (testable sans base ni écriture)."""
    seconds = seconds or {}
    v = m.get("verdicts", {})
    lay = m.get("layers", {})
    blocked = [k for k in ("ppr", "sar", "ravine", "plu_gpu_prescription", "batiment", "voirie", "pente")
               if k in layer_errors]
    lines = [
        f"# {commune} — résultats import gold standard ({time.strftime('%Y-%m-%dT%H:%M:%S')})", "",
        f"- **Commune / INSEE** : {commune} / {insee}",
        f"- **Stratégie appliquée** : {strategie}",
        f"- **Verdict** : {verdict} (code de sortie {exit_code})", "",
        "## État avant → après", "",
        f"- Parcelles : {before.get('parcels')} → **{m.get('parcels')}**",
        f"- Sections : **{m.get('sections')}**",
        f"- Bâti (couche) : {before.get('bati')} → **{lay.get('batiment')}**",
        f"- Évaluées : **{m.get('evaluated')} / {m.get('parcels')}** "
        f"({'100 %' if m.get('evaluated') == m.get('parcels') else 'INCOMPLET'})", "",
        "## Couches", "",
    ]
    for k in ("batiment", "voirie", "pente", "plu_gpu_zone", "ppr", "sar", "ravine",
              "plu_gpu_prescription", "osm_faux_positif", "abf"):
        st = "BLOQUÉ" if k in layer_errors else (lay.get(k) if lay.get(k) is not None else "absent")
        lines.append(f"- {k} : {st}")
    lines += ["", f"- Couverture zonage PLU : **{m.get('zonage_pct')} %**",
              f"- Duplication de couches : {m.get('dup_groups')} groupe(s)",
              f"- Index GIST présents : {len(m.get('indexes', []))}/{len(EXPECTED_INDEXES)}", ""]
    if blocked:
        lines += [f"> ⚠ Couches BLOQUÉES (à re-fetch) : {blocked}", ""]
    lines += ["## Verdicts & opportunités", ""]
    for st in ("opportunite", "a_creuser", "exclue", "faux_positif_probable"):
        lines.append(f"- {_VERDICT_LABEL[st]} : **{v.get(st, 0)}**")
    lines += [f"- Taux d'opportunité : **{m.get('opp_rate_pct')} %** "
              f"(repère Saint-Paul ≈ 1 % ; seuil QA ≤ {OPP_RATE_MAX_PCT:g} %)",
              f"- Micro-opportunités (251–500 m²) : {m.get('micro_opp')}", ""]
    if seconds:
        lines += ["## Temps d'exécution", "",
                  *(f"- {k} : {sv:.0f}s" for k, sv in seconds.items()), ""]
    lines += ["## Contrôles", ""]
    sev_lbl = {"critique": "[critique]", "qa": "[QA]", "info": ""}
    for (name, ok, sev, detail) in checks:
        lines.append(f"- {'✓ OK ' if ok else '✗ ÉCHEC'} {sev_lbl.get(sev, '')} {name} — {detail}")
    concl = {EXIT_OK: "SUCCÈS — commune prête au standard (peut être marquée gold)",
             EXIT_ROLLBACK: "ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune",
             EXIT_REFETCH: "RE-FETCH NÉCESSAIRE — relancer la/les couche(s) non critique(s)",
             EXIT_NOGO_QA: "NO-GO QA — ne PAS marquer gold, investiguer le résultat",
             EXIT_CONFIRM: "NO-GO — confirmation absente/incorrecte"}.get(exit_code, verdict)
    lines += ["", f"## Conclusion : {concl}", ""]
    return lines


def write_report(commune: str, dry_run: bool, lines: list[str]) -> str | None:
    path = report_path(commune)
    if dry_run:
        print(f"\n[H] RAPPORT — DRY-RUN : écrirait {path} (non créé en dry-run).")
        return None
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[H] ✓ rapport écrit : {path}")
    return path


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
    before = snapshot_before(eng, args.commune)
    present = before.get("parcels", 0)
    seconds: dict = {}
    try:
        r_b = step_import_parcels(args.commune, args.insee, present, False)
        r_d = step_layers(args.commune, args.insee, False, run_id=r_b.get("run_id"))
        r_f = step_cascade(args.commune, False)
        for r, name in ((r_b, "parcelles"), (r_d, "couches"), (r_f, "cascade")):
            if r.get("seconds") is not None:
                seconds[name] = r["seconds"]
    except Exception as exc:  # noqa: BLE001 — on ne présente JAMAIS une opération crashée comme réussie
        tb = traceback.format_exc()
        print(f"\n✗ EXCEPTION pendant une étape mutante : {type(exc).__name__}: {exc}")
        print(tb)
        code, verdict = final_decision([], [], [], crashed=True)
        print(f"\n⛔ {verdict}")
        write_report(args.commune, False,
                     [f"# {args.commune} — ÉCHEC ({time.strftime('%Y-%m-%dT%H:%M:%S')})", "",
                      f"**{verdict}** (code {code})", "", "```", tb, "```"])
        return code

    layer_errs = r_d.get("errors", [])
    crit_lf, noncrit_lf = classify_layer_failures(layer_errs)

    print("\n[G] POST-CHECKS")
    m = read_postcheck_metrics(eng, args.commune)
    expected_min = expected_min_parcels(cfg, r_b.get("parcels"))
    results = postcheck_results(m, before, expected_min, layer_errs)
    for name, ok, sev, detail in results:
        tag = {"critique": "[critique] ", "qa": "[QA] ", "info": ""}.get(sev, "")
        print(f"    {'✓' if ok else '✗'} {tag}{name} — {detail}")

    code, verdict = final_decision(results, crit_lf, noncrit_lf, crashed=False)
    print(f"\n{'✓' if code == EXIT_OK else '⛔'} {verdict}")
    lines = build_report(args.commune, args.insee, cfg.get("strategie", "?"), verdict, code,
                         before, m, results, layer_errs, seconds)
    write_report(args.commune, False, lines)
    return code


if __name__ == "__main__":
    sys.exit(main())
