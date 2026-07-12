"""Monitoring forward 2026 (M5 lot 5) — `labuse monitor-forward`, mensuel, manuel.

Suit le TOP GELÉ (snapshot m5-*) contre les événements arrivés depuis le gel :
  - hits : mutations L2-F et permis autorisés post-gel sur les parcelles du top ;
  - sonde faux négatifs : parcelles écartées ou P bas (percentile < 50) qui ont
    pourtant muté ou obtenu un permis post-gel ;
  - churn observé : overlap chaude/brûlante entre les deux derniers runs.

Protocole B0 (censure DVF 974) : le CLASSEMENT se suit en continu, les NIVEAUX
ne se jugent qu'à l'édition N+2 — tout taux affiché ici est PROVISOIRE.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

REPORTS = Path("reports/monitoring")


def run_monitor(session: Session, snapshot_label: str | None = None) -> dict:
    REPORTS.mkdir(parents=True, exist_ok=True)
    if snapshot_label:
        snap = session.execute(text(
            "SELECT id, label, created_at FROM score_snapshots WHERE label = :l"),
            {"l": snapshot_label}).one_or_none()
    else:
        snap = session.execute(text(
            "SELECT id, label, created_at FROM score_snapshots "
            "WHERE label LIKE 'm5-%' ORDER BY created_at DESC LIMIT 1")).one_or_none()
    if snap is None:
        raise RuntimeError("aucun snapshot m5-* — lancer `labuse score-v2` d'abord.")
    sid, label, gel = snap

    top = pd.read_sql(text("""
        SELECT parcelle_id, statut FROM score_snapshot_parcelles
        WHERE snapshot_id = :s AND statut IN ('chaude', 'brulante')"""),
        session.connection(), params={"s": sid})

    # événements post-gel (mutations L2-F re-matérialisées au dernier score-v2)
    muts = pd.read_sql(text("""
        SELECT DISTINCT idu, max(date_mutation) AS date_mutation
        FROM p_model_ext_mut_l2 WHERE NOT exclue_l2f AND date_mutation >= :g
        GROUP BY idu"""), session.connection(), params={"g": gel.date()})
    permis = pd.read_sql(text("""
        SELECT DISTINCT idu, max(date_autorisation) AS date_permis
        FROM p_model_permits WHERE date_autorisation >= :g GROUP BY idu"""),
        session.connection(), params={"g": gel.date()})

    top_set = set(top["parcelle_id"])
    hits_mut = muts[muts["idu"].isin(top_set)]
    hits_perm = permis[permis["idu"].isin(top_set)]

    # sonde faux négatifs : P bas ou écartée AVEC événement post-gel
    latest_run = session.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
    scores = pd.read_sql(text("""
        SELECT parcelle_id, percentile, tier FROM parcel_p_score_v2
        WHERE run_id = :r"""), session.connection(), params={"r": latest_run})
    evented = set(muts["idu"]) | set(permis["idu"])
    fn = scores[scores["parcelle_id"].isin(evented)
                & ((scores["tier"] == "ecartee") | (scores["percentile"] < 50))]
    fn = fn.merge(muts, left_on="parcelle_id", right_on="idu", how="left") \
           .merge(permis, left_on="parcelle_id", right_on="idu", how="left")

    # churn observé entre les deux derniers runs
    runs = [r[0] for r in session.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 2")).all()]
    churn = None
    if len(runs) == 2:
        cur = set(pd.read_sql(text(
            "SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id = :r "
            "AND tier IN ('chaude','brulante')"), session.connection(),
            params={"r": runs[0]})["parcelle_id"])
        prv = set(pd.read_sql(text(
            "SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id = :r "
            "AND tier IN ('chaude','brulante')"), session.connection(),
            params={"r": runs[1]})["parcelle_id"])
        churn = {"sortants": len(prv - cur), "entrants": len(cur - prv),
                 "churn_pct": round(len(prv - cur) / max(len(prv), 1) * 100, 1)}

    mois = time.strftime("%Y-%m")
    csv_path = REPORTS / f"{mois}-faux-negatifs.csv"
    fn.to_csv(csv_path, index=False)
    md = REPORTS / f"{mois}.md"
    md.write_text(f"""# Monitoring forward — {mois}

Snapshot suivi : **{label}** (gelé le {gel:%Y-%m-%d}), top gelé = {len(top)} parcelles
(chaude + brûlante). Classement suivi en continu ; **niveaux provisoires**
(censure DVF 974, protocole B0 : jugement de niveau à l'édition N+2).

## Hits du top gelé depuis le gel
- mutations L2-F : **{len(hits_mut)}** parcelles du top ont muté
- permis autorisés : **{len(hits_perm)}** parcelles du top ont un permis

## Sonde faux négatifs
{len(fn)} parcelles écartées ou P bas (percentile < 50) avec mutation ou permis
post-gel → `{csv_path.name}`.

## Churn observé
{churn if churn else "un seul run v2 — churn observable au prochain run."}
""")
    return {"rapport": str(md), "hits": int(len(hits_mut) + len(hits_perm)),
            "faux_negatifs": int(len(fn)), "churn": churn}
