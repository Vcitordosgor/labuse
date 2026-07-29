"""BASCULE v7 → v8 — le calibrage de 21 communes atteint le scoring servi (REFONTE 30/07).

Matérialise un NOUVEAU run servi COMPLET `q_v8_calibre` = scores P + cascade + matrice + snapshot,
tous cohérents sur les features calibrées. Le run précédent `q_v7_defisc` est INTÉGRALEMENT
conservé (hystérésis / rollback).

Séquence (chaque étape idempotente, transactionnelle) :
  1. MIGRATION  parcel_residuel ← parcel_residuel_rerun (SDP calibrée) — la prod.
  2. REBUILD    p_model_static (features résiduel) depuis le nouveau parcel_residuel.
  3. RE-PASSE CASCADE ÎLE ENTIÈRE (24 communes) dans dryrun_* sous run_label=q_v8_calibre :
       evaluate_parcels (cascade) + compute_matrice, par commune, chunké/RÉSUMABLE.
       JAMAIS une copie de q_v7 — la cascade dépend de resolve_zone (YAML calibrés) ET de
       parcel_residuel (migré), qui changent les tables (prémisse « copie » prouvée FAUSSE :
       50/50 parcelles divergeaient — 6e principe).
  4. RE-SCORE   run_score_v2(run_id=q_v8_calibre) avec LABUSE_ETAGE0_RUN=q_v8_calibre (le scoring
       lit SA PROPRE cascade pour l'étage 0), champion INCHANGÉ (sha gelé), snapshot inclus.
  5. AUTO-VÉRIFICATION DE COMPLÉTUDE — chaque table comptée vs attendu (île entière). Si UNE seule
       manque → échec BRUYANT (RunIncompletError), le run n'est PAS déclaré servable (7e principe :
       un run incomplet est plus dangereux qu'un run qui échoue).

Sauvegardes préalables (créées si absentes) : parcel_residuel_pre_v8, p_model_static_pre_v8.
Bascule des SURFACES (hors DB, opérateur) : export LABUSE_SERVED_RUN=q_v8_calibre ;
  (front) VITE_RUN_LABEL=q_v8_calibre npm run build ; labuse build-mvt --label q_v8_calibre.
Rollback : python scripts/rollback_v8_calibre.py.

Usage :
  PYTHONPATH=src python scripts/bascule_v8_calibre.py               # bascule prod (île entière)
  PYTHONPATH=src python scripts/bascule_v8_calibre.py --resume      # reprend la cascade interrompue
"""
from __future__ import annotations
import argparse, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine, session_scope

TARGET = "q_v8_calibre"


class RunIncompletError(RuntimeError):
    """Levée par verify_completude quand une table attendue manque — échec BRUYANT."""


# ─────────────────────────────── étapes (idempotentes) ───────────────────────────────

def ensure_backups() -> None:
    """Sauvegardes features pré-bascule (créées une seule fois ; jamais écrasées)."""
    with engine().begin() as c:
        for src, bak in [("parcel_residuel", "parcel_residuel_pre_v8"),
                         ("p_model_static", "p_model_static_pre_v8")]:
            if not c.execute(text("SELECT to_regclass(:b)"), {"b": bak}).scalar():
                c.execute(text(f"CREATE TABLE {bak} AS SELECT * FROM {src}"))
                print(f"  backup créé : {bak}", flush=True)


def migrate_residuel() -> int:
    """1) parcel_residuel ← parcel_residuel_rerun (constructibles seulement, sémantique prod).
    Transactionnel (TRUNCATE + INSERT dans une seule transaction) et idempotent (relance = même état)."""
    with engine().begin() as c:
        c.execute(text("TRUNCATE parcel_residuel"))
        c.execute(text(
            "INSERT INTO parcel_residuel (parcel_id, taux_emprise_pct, pct_potentiel, sous_densite,"
            " sdp_residuelle_m2, capacite_estimee, computed_at) "
            "SELECT parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2,"
            " false, now() FROM parcel_residuel_rerun WHERE dispo_rerun"))
        n = c.execute(text("SELECT count(*) FROM parcel_residuel")).scalar()
    print(f"  [1] parcel_residuel migré : {n} lignes (SDP calibrée)", flush=True)
    return n


def rebuild_static() -> None:
    """2) p_model_static reconstruit depuis le nouveau parcel_residuel (features résiduel calibrées)."""
    from labuse.scoring.p_model import sql as p_sql
    with session_scope() as s:
        p_sql.build_static(s)
        s.commit()
    print("  [2] p_model_static reconstruit", flush=True)


def repass_cascade(communes: list[str], target: str = TARGET, chunk: int = 2000,
                   resume: bool = True) -> int:
    """3) RE-PASSE la cascade (evaluate_parcels + compute_matrice) par commune sous run_label=target.
    Idempotent : evaluate_parcels purge (run_label, parcel_id) avant réinsertion ; `resume` saute les
    parcelles déjà évaluées → une relance après interruption ne duplique ni ne recommence tout."""
    from labuse.cascade import evaluate_parcels
    from labuse.scoring.dryrun import compute_matrice
    from labuse.cli import _parcel_ids

    t0 = time.time(); total = 0
    for ci, commune in enumerate(communes, 1):
        with session_scope() as s:
            ids = _parcel_ids(s, commune)
            done = set()
            if resume:
                done = {r[0] for r in s.execute(text(
                    "SELECT parcel_id FROM dryrun_parcel_evaluations WHERE run_label=:r AND parcel_id = ANY(:ids)"),
                    {"r": target, "ids": ids}).all()}
            todo = [i for i in ids if i not in done]
        for k in range(0, len(todo), chunk):
            part = todo[k:k + chunk]
            with session_scope() as s:
                evaluate_parcels(part, s, persist=True, dryrun_label=target)
                s.commit()
            total += len(part)
        with session_scope() as s:                       # matrice = post-pass sur la commune entière
            compute_matrice(s, target, commune)
            s.commit()
        print(f"  [3] cascade {ci}/{len(communes)} {commune:22s} : {len(ids)} parcelles "
              f"({len(ids)-len(todo)} reprises)  [{time.time()-t0:.0f}s]", flush=True)
    print(f"  [3] cascade RE-PASSÉE : {total} évaluées sur {len(communes)} communes", flush=True)
    return total


def score(target: str = TARGET) -> dict:
    """4) run_score_v2 sur la cascade du target (LABUSE_ETAGE0_RUN=target → étage 0 lu sur SA cascade,
    pas celle du servi). Champion chargé depuis l'artifact (sha gelé), snapshot inclus."""
    from labuse.scoring.p_v2.pipeline import run_score_v2
    os.environ["LABUSE_ETAGE0_RUN"] = target       # M8a : scorer le candidat sur SA propre cascade
    with session_scope() as s:
        res = run_score_v2(s, run_id=target, rebuild=True, snapshot=True)
    print(f"  [4] run {target} : {res['n']} parcelles scorées, snapshot {res.get('snapshot')}", flush=True)
    return res


def verify_completude(target: str, n_expected_cascade: int, n_expected_scores: int) -> dict:
    """5) AUTO-VÉRIFICATION. Compte chaque table clé-run vs attendu. Lève RunIncompletError (échec
    BRUYANT) au premier manque — le run n'est PAS déclaré servable tant que les 4 tables ne sont pas
    complètes : scores P, cascade (evaluations + résultats), snapshot."""
    with engine().connect() as c:
        counts = {
            "parcel_p_score_v2":         c.execute(text("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": target}).scalar(),
            "dryrun_parcel_evaluations": c.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:r"), {"r": target}).scalar(),
            "dryrun_cascade_results":    c.execute(text("SELECT count(*) FROM dryrun_cascade_results WHERE run_label=:r"), {"r": target}).scalar(),
            "matrice_statut_non_null":   c.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:r AND matrice_statut IS NOT NULL"), {"r": target}).scalar(),
            "p_score_v2_runs":           c.execute(text("SELECT count(*) FROM p_score_v2_runs WHERE run_id=:r"), {"r": target}).scalar(),
            "snapshot_parcelles":        c.execute(text("SELECT count(*) FROM score_snapshot_parcelles sp JOIN score_snapshots ss ON ss.id=sp.snapshot_id WHERE ss.run_label=:r"), {"r": target}).scalar(),
        }
    problems = []
    if counts["parcel_p_score_v2"] != n_expected_scores:
        problems.append(f"scores P {counts['parcel_p_score_v2']} ≠ {n_expected_scores}")
    if counts["dryrun_parcel_evaluations"] != n_expected_cascade:
        problems.append(f"cascade evaluations {counts['dryrun_parcel_evaluations']} ≠ {n_expected_cascade}")
    if counts["matrice_statut_non_null"] != n_expected_cascade:
        problems.append(f"matrice_statut renseigné {counts['matrice_statut_non_null']} ≠ {n_expected_cascade}")
    if counts["dryrun_cascade_results"] <= 0:
        problems.append("dryrun_cascade_results VIDE (cascade non produite)")
    if counts["p_score_v2_runs"] != 1:
        problems.append(f"header p_score_v2_runs {counts['p_score_v2_runs']} ≠ 1")
    if counts["snapshot_parcelles"] != n_expected_scores:
        problems.append(f"snapshot {counts['snapshot_parcelles']} ≠ {n_expected_scores}")
    if problems:
        raise RunIncompletError(f"RUN {target} INCOMPLET — NE PAS SERVIR :\n    - " + "\n    - ".join(problems)
                                + f"\n  détail: {counts}")
    return counts


# ─────────────────────────────────── orchestration ───────────────────────────────────

def all_communes() -> list[str]:
    from labuse import communes as _c
    return list(_c.load_communes().keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true", help="reprend la cascade interrompue (ne recommence pas).")
    args = ap.parse_args()

    with engine().connect() as c:
        if c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:t"), {"t": TARGET}).scalar():
            raise SystemExit(f"{TARGET} existe déjà — rollback d'abord (python scripts/rollback_v8_calibre.py).")
        n_parcels = c.execute(text("SELECT count(*) FROM parcels")).scalar()

    t0 = time.time()
    communes = all_communes()
    print(f"BASCULE → {TARGET} : {n_parcels} parcelles, {len(communes)} communes. q_v7_defisc conservé.", flush=True)
    ensure_backups()
    migrate_residuel()
    rebuild_static()
    # cache pré-subdivisé (×64 sur l'intersection de prime) — construit avant la re-passe cascade.
    from labuse import models as _m
    npieces = _m.ensure_spatial_layers_sub(engine())
    print(f"  [2b] spatial_layers_sub : {npieces} pièces (cache pré-subdivisé, prime ~×64)", flush=True)
    repass_cascade(communes, resume=args.resume)
    score()
    counts = verify_completude(TARGET, n_expected_cascade=n_parcels, n_expected_scores=n_parcels)

    with engine().connect() as c:
        dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:t GROUP BY tier ORDER BY count(*)"), {"t": TARGET}).all()
    print(f"\n✓ BASCULE COMPLÈTE ET VÉRIFIÉE en {(time.time()-t0)/60:.0f} min. Tables : {counts}")
    print("Tiers du nouveau run servi :")
    for tier, n in dist:
        print(f"  {tier:28s} {n:>8}")
    print(f"\n  SURFACES : export LABUSE_SERVED_RUN={TARGET} ; (front) VITE_RUN_LABEL={TARGET} npm run build ; labuse build-mvt --label {TARGET}")
    print(f"  GOLDEN   : LABUSE_DEV_MODE=1 sur l'API, puis LABUSE_GOLDEN_RUN_LABEL={TARGET} python qa/golden_check.py")
    print(f"  ROLLBACK : python scripts/rollback_v8_calibre.py")


if __name__ == "__main__":
    main()
