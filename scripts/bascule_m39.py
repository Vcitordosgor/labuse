"""BASCULE M39 — déclassement des fausses chaudes à piscine (solde dette #13, geste GARDÉ).

⚠ NON EXÉCUTÉ dans le mandat M39. DRY-RUN par défaut : calcule le plan, le vérifie, n'écrit RIEN.
Le geste réel n'agit QUE si LABUSE_M39_EXECUTE=1 (jamais posé par M39) — décision de Vic sur la
mesure à blanc (qa/m39/mesure_a_blanc_p2.csv). Modèle : scripts/bascule_m32.py (6 gardes +
check_fraicheur + golden_regen dans le geste).

Règle (config/calibrage/piscine_signal.yaml, arbitrages A1/B/C1) : une parcelle servie brûlante/
chaude portant une piscine MATÉRIALISÉE (couche 90,7 %) en bande [15;60] m² → a_creuser (fausse
chaude : usage investi). Le V0 colorimétrique seul est EXCLU (C3 enterré). Les seeds AK1442/AL1154
restent au REGISTRE à l'identique (C1) — le geste PRÉSERVE le registre existant (motif +
motif_client) et n'y ajoute QUE les déclassements de la règle, motif_client famille M35. Zéro
double comptage (règle ∩ registre = ∅, vérifié P0 §4).

Ce que le geste réel ferait (modèle M32) :
  0. persist_millesime(ortho) — dater la couche dans le même geste.
  1. gardes démarrage : check_disque, check_peremption, ensure_backups.
  2. archive par RENAME : q_v8_calibre → q_v8_calibre_pre_m39 (registre existant suit l'archive).
  3. check_run_absent(q_v8_calibre) puis re-score run_score_v2 (reproduit les tiers naturels).
  4. CONFORME STRICT : 0 écart re-score vs archive HORS registre (le scoring n'a pas changé).
  5. RE-APPLIQUE le registre existant (5 entrées M28/M32) à l'identique.
  6. APPLIQUE la règle : les N déclassements piscine (hot → a_creuser), motif_client famille.
  7. verify_completude + check_fraicheur.
  8. golden_regen DANS LE GESTE (6e garde check_golden_regenere).

Usage (dry-run) : PYTHONPATH=src python scripts/bascule_m39.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import engine, session_scope  # noqa: E402
from labuse.faisabilite.piscine_signal import regle  # noqa: E402

LABEL, ARCHIVE = "q_v8_calibre", "q_v8_calibre_pre_m39"
EXECUTE = os.environ.get("LABUSE_M39_EXECUTE") == "1"


def plan_declassements(run_id: str = LABEL) -> list[dict]:
    """Les déclassements de la règle sur le run servi : hot ∩ piscine matérialisée ∩ bande [min;max].
    EXCLUT les parcelles déjà au registre (zéro double comptage). Lecture seule."""
    r = regle()
    with engine().connect() as c:
        rows = c.execute(text("""
            SELECT s.parcelle_id AS idu, s.tier AS tier_origine,
                   round(pe.piscine_surface_m2::numeric,1) AS surface_m2,
                   round(pe.piscine_confiance::numeric,3) AS confiance
            FROM parcel_p_score_v2 s
            JOIN parcel_equipements pe ON pe.idu = s.parcelle_id AND pe.piscine
            WHERE s.run_id = :run
              AND s.tier = ANY(:tiers)
              AND pe.piscine_surface_m2 BETWEEN :lo AND :hi
              AND s.parcelle_id NOT IN (SELECT idu FROM served_run_exceptions WHERE run_id = :run)
            ORDER BY substring(s.parcelle_id,1,5), s.tier, pe.piscine_surface_m2 DESC
        """), {"run": run_id, "tiers": list(r["tiers_source"]),
               "lo": r["surface_min_m2"], "hi": r["surface_max_m2"]}).mappings().all()
    return [dict(x) for x in rows]


def _dry_run() -> None:
    r = regle()
    plan = plan_declassements()
    print(f"— BASCULE M39 DRY-RUN (aucune écriture) — règle [{r['surface_min_m2']:.0f};"
          f"{r['surface_max_m2']:.0f}] m², tiers {r['tiers_source']} → {r['tier_cible']} —")
    par_commune: dict[str, int] = {}
    for d in plan:
        par_commune[d["idu"][:5]] = par_commune.get(d["idu"][:5], 0) + 1
    n_brul = sum(1 for d in plan if d["tier_origine"] == "brulante")
    n_chaud = sum(1 for d in plan if d["tier_origine"] == "chaude")
    print(f"  DÉCLASSEMENTS RÈGLE : {len(plan)} ({n_brul} brûlante + {n_chaud} chaude), "
          f"{len(par_commune)} communes.")
    for insee, n in sorted(par_commune.items(), key=lambda kv: -kv[1]):
        print(f"    {insee} : {n}")
    with engine().connect() as c:
        reg = c.execute(text("SELECT count(*) FROM served_run_exceptions WHERE run_id=:l"),
                        {"l": LABEL}).scalar()
        double = c.execute(text("""SELECT count(*) FROM parcel_p_score_v2 s
            JOIN parcel_equipements pe ON pe.idu=s.parcelle_id AND pe.piscine
            WHERE s.run_id=:l AND s.tier=ANY(:t) AND pe.piscine_surface_m2 BETWEEN :lo AND :hi
              AND s.parcelle_id IN (SELECT idu FROM served_run_exceptions WHERE run_id=:l)"""),
            {"l": LABEL, "t": list(r["tiers_source"]),
             "lo": r["surface_min_m2"], "hi": r["surface_max_m2"]}).scalar()
    print(f"  Registre existant PRÉSERVÉ : {reg} entrées (dont seeds AK1442/AL1154). "
          f"Chevauchement règle∩registre : {double} (attendu 0 — zéro double comptage).")
    print(f"  motif_client servi (famille M35) : « {r['motif_client']} »")
    print("✓ DRY-RUN OK — geste NON exécuté (LABUSE_M39_EXECUTE≠1). Décision Vic sur mesure à blanc.")


def _execute() -> None:
    from labuse.bascule_gardes import (check_disque, check_fraicheur, check_golden_regenere,
                                       check_peremption, check_run_absent, ensure_backups,
                                       verify_completude, _ts)
    from labuse.ingestion.fraicheur import persist_millesime
    from labuse.scoring.p_v2.pipeline import run_score_v2
    r = regle()
    t0 = time.time()
    # 0. dater la couche piscine dans le même geste
    with session_scope() as s:
        persist_millesime(s, only="ortho_piscine")
    with engine().connect() as c:
        n_parcels = c.execute(text("SELECT count(*) FROM parcels")).scalar()
        if c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:a"), {"a": ARCHIVE}).scalar():
            raise SystemExit(f"{ARCHIVE} existe déjà — reprise non gérée ici (voir bascule_m32).")
    print(f"{_ts()} BASCULE M39 ({n_parcels} parcelles). Archive : {ARCHIVE}.", flush=True)
    # 1. gardes de démarrage
    check_disque(LABEL); check_peremption(None); ensure_backups()
    # 2. archive par rename (registre existant suit l'archive)
    with engine().begin() as c:
        for tbl, col in [("parcel_p_score_v2", "run_id"), ("p_score_v2_runs", "run_id"),
                         ("score_snapshots", "run_label"), ("served_run_exceptions", "run_id")]:
            c.execute(text(f"UPDATE {tbl} SET {col}=:a WHERE {col}=:l"), {"a": ARCHIVE, "l": LABEL})
    check_run_absent(LABEL)
    # 3. re-score (reproduit les tiers naturels)
    os.environ["LABUSE_ETAGE0_RUN"] = LABEL
    with session_scope() as s:
        res = run_score_v2(s, run_id=LABEL, rebuild=False, snapshot=True)
    print(f"  [3] scoring servi : {res['n']} parcelles", flush=True)
    # 4. CONFORME STRICT hors registre : re-score == archive sauf parcelles du registre
    with engine().connect() as c:
        diffs = c.execute(text("""SELECT s.parcelle_id FROM parcel_p_score_v2 s
            JOIN parcel_p_score_v2 a ON a.parcelle_id=s.parcelle_id AND a.run_id=:a
            WHERE s.run_id=:l AND s.tier IS DISTINCT FROM a.tier
              AND s.parcelle_id NOT IN (SELECT idu FROM served_run_exceptions WHERE run_id=:a)"""),
            {"l": LABEL, "a": ARCHIVE}).all()
    if diffs:
        raise SystemExit(f"NON-CONFORME (hors registre) : {len(diffs)} écarts {[d[0] for d in diffs[:8]]} — ROLLBACK.")
    print("  [4] CONFORME STRICT à l'archive (0 écart hors registre)", flush=True)
    # 5. re-applique le registre existant à l'identique (motif + motif_client)
    with engine().begin() as c:
        reg = c.execute(text("SELECT idu, tier_origine, tier_servi, motif, motif_client "
                             "FROM served_run_exceptions WHERE run_id=:a"), {"a": ARCHIVE}).mappings().all()
        for e in reg:
            if e["tier_servi"] and e["tier_servi"] != e["tier_origine"]:
                c.execute(text("UPDATE parcel_p_score_v2 SET tier=:t WHERE run_id=:l AND parcelle_id=:i"),
                          {"t": e["tier_servi"], "l": LABEL, "i": e["idu"]})
            c.execute(text("INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif, motif_client) "
                           "VALUES (:l,:i,:o,:s,:m,:mc)"),
                      {"l": LABEL, "i": e["idu"], "o": e["tier_origine"], "s": e["tier_servi"],
                       "m": e["motif"], "mc": e["motif_client"]})
    print(f"  [5] registre existant ré-appliqué : {len(reg)} entrées (seeds inclus, à l'identique)", flush=True)
    # 6. applique la RÈGLE (les déclassements piscine, hors registre)
    plan = plan_declassements(LABEL)
    with engine().begin() as c:
        for d in plan:
            c.execute(text("UPDATE parcel_p_score_v2 SET tier=:t WHERE run_id=:l AND parcelle_id=:i"),
                      {"t": r["tier_cible"], "l": LABEL, "i": d["idu"]})
            motif = (f"M39 (règle piscine) : piscine matérialisée {d['surface_m2']} m² "
                     f"(conf {d['confiance']}, bande [{r['surface_min_m2']:.0f};{r['surface_max_m2']:.0f}], "
                     f"ortho {r['millesime']} {r['precision_pct']:.1f} %) — fausse chaude, {r['tier_cible']}, dette #13")
            c.execute(text("INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif, motif_client) "
                           "VALUES (:l,:i,:o,:s,:m,:mc)"),
                      {"l": LABEL, "i": d["idu"], "o": d["tier_origine"], "s": r["tier_cible"],
                       "m": motif, "mc": r["motif_client"]})
    print(f"  [6] règle appliquée : {len(plan)} déclassements piscine (hot → {r['tier_cible']})", flush=True)
    # 7. complétude + fraîcheur
    counts = verify_completude(LABEL, n_expected_cascade=n_parcels, n_expected_scores=n_parcels)
    print(f"  [7] complétude : {counts}", flush=True)
    check_fraicheur()
    # 8. golden_regen DANS LE GESTE (6e garde) — régénérer AVANT de vérifier
    import subprocess
    here = os.path.dirname(__file__)
    subprocess.run([sys.executable, os.path.join(here, "..", "qa", "golden_regen.py")], check=True)
    check_golden_regenere(LABEL)
    print(f"\n✓ BASCULE M39 en {time.time()-t0:.0f}s. golden régénéré, 6e garde OK.", flush=True)


if __name__ == "__main__":
    if EXECUTE:
        _execute()
    else:
        _dry_run()
