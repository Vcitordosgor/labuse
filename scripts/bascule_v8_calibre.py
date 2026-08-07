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
from labuse.bascule_gardes import (   # 6 gardes + helper _ts : briques importables, AUCUNE logique recopiée
    TARGET, RunDejaExistantError, RunIncompletError, DisqueInsuffisantError, PeremptionError,
    GoldenPerimeError, check_run_absent, check_disque, check_peremption, ensure_backups,
    verify_completude, check_golden_regenere, _ts)


# ─────────────────────────────── étapes (idempotentes) ───────────────────────────────


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
        # une ligne par commune TERMINÉE : heure, commune, compte cumulé, ETA (Vic 30/07).
        eta = (len(communes) - ci) * (time.time() - t0) / ci
        print(f"  [3] {_ts()} commune {ci}/{len(communes)} {commune:22s} FINIE : "
              f"{len(ids)} parcelles ({len(ids)-len(todo)} reprises) · cumul {total} · "
              f"ETA ~{eta/60:.0f} min", flush=True)
    print(f"  [3] {_ts()} cascade RE-PASSÉE : {total} évaluées sur {len(communes)} communes", flush=True)
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



# ─────────────────────────────────── orchestration ───────────────────────────────────

def all_communes() -> list[str]:
    from labuse import communes as _c
    return list(_c.load_communes().keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true", help="reprend la cascade interrompue (ne recommence pas).")
    ap.add_argument("--skip-disk-check", action="store_true", help="passe la garde disque (réutilisation d'espace mort certaine).")
    ap.add_argument("--peremption-ack", metavar="MOTIF", default=None,
                    help="contourne la garde de péremption AU (>180 j) — motif OBLIGATOIRE, tracé (QUI/QUAND/COMBIEN).")
    args = ap.parse_args()

    try:                                    # garde ANTI-ÉCRASEMENT (1ʳᵉ garde, brique importable)
        n_parcels = check_run_absent(TARGET)
    except RunDejaExistantError as e:
        raise SystemExit(str(e))

    t0 = time.time()
    communes = all_communes()
    print(f"{_ts()} BASCULE → {TARGET} : {n_parcels} parcelles, {len(communes)} communes. q_v7_defisc conservé.", flush=True)
    if not args.skip_disk_check:            # garde DISQUE : refuse de démarrer si la marge manque
        check_disque(TARGET)
    check_peremption(args.peremption_ack)   # garde PÉREMPTION : refuse de servir des déclassées AU > 180 j
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

    # M48 : TUILES DANS LE GESTE — « un geste = tout ou rien ». Le build-mvt manuel post-bascule
    # (« SUITE » dans les scripts) laissait la carte périmée (constat M48 : M39 servi sans build-mvt).
    from labuse.api.tiles import rebuild_mvt_servies
    from labuse.bascule_gardes import check_peremption_tuiles
    with session_scope() as s:
        mvt = rebuild_mvt_servies(s, TARGET, log=lambda m: print(f"  [5] {m}", flush=True))
    print(f"  [5] tuiles reconstruites : {mvt['n']} parcelles "
          f"(flags {mvt['parcel_flags']}, renouv {mvt['renouvellement']})", flush=True)
    check_peremption_tuiles()

    with engine().connect() as c:
        dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:t GROUP BY tier ORDER BY count(*)"), {"t": TARGET}).all()
    print(f"\n✓ BASCULE COMPLÈTE ET VÉRIFIÉE en {(time.time()-t0)/60:.0f} min. Tables : {counts}")
    print("Tiers du nouveau run servi :")
    for tier, n in dist:
        print(f"  {tier:28s} {n:>8}")
    print(f"\n  SURFACES : export LABUSE_SERVED_RUN={TARGET} ; (front) VITE_RUN_LABEL={TARGET} npm run build ; labuse build-mvt --label {TARGET}")
    print(f"  GOLDEN   : LABUSE_DEV_MODE=1 sur l'API, puis LABUSE_GOLDEN_RUN_LABEL={TARGET} python qa/golden_check.py")
    # 6ᵉ garde (Vic 04/08) : la bascule N'EST PAS complète tant que le golden ne cite pas le
    # run servi — RÉGÉNÉRER dans le même geste (--dump --idu <IDs de la référence>, jamais nu).
    try:
        rep = check_golden_regenere(TARGET)
        print(f"  GOLDEN OK : référence sur {rep['run_v2_servi']} ({rep['n_parcelles']} parcelles)")
    except GoldenPerimeError as e:
        print(f"  ⚠ GARDE GOLDEN : {e}")
    print(f"  ROLLBACK : python scripts/rollback_v8_calibre.py")


if __name__ == "__main__":
    main()
