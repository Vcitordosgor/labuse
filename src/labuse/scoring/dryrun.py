"""Dry-run scoring (étages 1+2) — lecture des tables parallèles `dryrun_*`.

Le calcul à blanc est écrit par cascade.pipeline.evaluate_parcels(dryrun_label=…) ; ici on ne fait
que LIRE pour produire les livrables (distributions, top N, DIFF entre runs, contrôle de traçabilité).
Ne touche JAMAIS les évaluations live.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def report(session: Session, run_label: str, commune: str, top_n: int = 50) -> dict:
    """Livrable d'un run : couverture, histogramme d'opportunité, comptes par statut/verdict,
    parcelles UNKNOWN-ABF, top N opportunités motivées, et contrôle base+Σ=score."""
    base = {"run_label": run_label, "commune": commune}

    base["n_parcelles"] = int(session.execute(text(
        "SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c"), {"r": run_label, "c": commune}).scalar() or 0)

    base["par_statut"] = {r[0]: r[1] for r in session.execute(text(
        "SELECT d.status, count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c GROUP BY d.status ORDER BY 2 DESC"),
        {"r": run_label, "c": commune}).all()}

    # histogramme opportunité par tranches de 10
    base["histogramme_opportunite"] = {int(r[0]): r[1] for r in session.execute(text(
        "SELECT (opportunity_score/10)*10 AS tranche, count(*) "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c GROUP BY 1 ORDER BY 1"),
        {"r": run_label, "c": commune}).all()}

    base["opportunite_stats"] = dict(session.execute(text(
        "SELECT min(opportunity_score) AS min, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY opportunity_score)::int AS median, "
        "  max(opportunity_score) AS max, round(avg(opportunity_score))::int AS moyenne, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY completeness_score)::int AS median_completude "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c"), {"r": run_label, "c": commune}).mappings().first() or {})

    base["verdicts_par_couche"] = {f"{r[0]}:{r[1]}": r[2] for r in session.execute(text(
        "SELECT cr.layer_name, cr.result, count(*) "
        "FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id "
        "WHERE cr.run_label=:r AND p.commune=:c GROUP BY 1,2 ORDER BY 3 DESC LIMIT 25"),
        {"r": run_label, "c": commune}).all()}

    base["unknown_abf"] = int(session.execute(text(
        "SELECT count(*) FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id "
        "WHERE cr.run_label=:r AND p.commune=:c AND cr.layer_name='abf' AND cr.result='UNKNOWN'"),
        {"r": run_label, "c": commune}).scalar() or 0)

    # top N opportunités + motifs (lignes à points ≠ 0, tracées)
    top = []
    for row in session.execute(text(
        "SELECT p.idu, d.opportunity_score, d.completeness_score, d.status "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c "
        "ORDER BY d.opportunity_score DESC, d.completeness_score DESC LIMIT :n"),
        {"r": run_label, "c": commune, "n": top_n}).mappings().all():
        motifs = [f"{m[0]}({m[1]:+g}) {m[2]}" for m in session.execute(text(
            "SELECT layer_name, weight_applied, left(detail,60) FROM dryrun_cascade_results cr "
            "JOIN parcels p ON p.id=cr.parcel_id "
            "WHERE cr.run_label=:r AND p.idu=:idu AND cr.weight_applied IS NOT NULL "
            "ORDER BY abs(cr.weight_applied) DESC LIMIT 4"),
            {"r": run_label, "idu": row["idu"]}).all()]
        top.append({**dict(row), "motifs": motifs})
    base["top"] = top

    # contrôle de traçabilité : base + Σ(weight_applied) == opportunity_score (hors HARD_EXCLUDE/clamp)
    ok = session.execute(text(
        "SELECT count(*) FROM ("
        "  SELECT d.parcel_id, d.opportunity_base, d.opportunity_score, "
        "    COALESCE(sum(cr.weight_applied),0) AS somme "
        "  FROM dryrun_parcel_evaluations d "
        "  JOIN parcels p ON p.id=d.parcel_id "
        "  LEFT JOIN dryrun_cascade_results cr ON cr.run_label=d.run_label AND cr.parcel_id=d.parcel_id "
        "  WHERE d.run_label=:r AND p.commune=:c AND d.opportunity_score > 0 "
        "  GROUP BY d.parcel_id, d.opportunity_base, d.opportunity_score"
        ") t WHERE opportunity_base + somme = opportunity_score"), {"r": run_label, "c": commune}).scalar()
    total_non_excl = session.execute(text(
        "SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c AND d.opportunity_score > 0"),
        {"r": run_label, "c": commune}).scalar()
    base["tracabilite_base_plus_somme"] = f"{ok}/{total_non_excl} (hors clamp/hard-exclude)"
    return base
