"""QV21-PROMO-1 — RECOMPOSITION DES STATUTS (paliers) d'un run DÉJÀ calculé, SANS relancer la cascade
ni le scoring de l'île.

Le palier (`parcel_p_score_v2.tier`) est une fonction PURE de la probabilité `p_raw`, de la
copropriété, de l'étage 0 (écartée dure) et — QV21-PROMO-1 — de l'exclusion « entièrement en zone
rouge ». Cette fonction (`statuts.assign_paliers`) est le SEUL point qui décide d'un palier ; ici on
la rejoue sur les colonnes DÉJÀ en base (p_raw, copro) + l'étage 0 et les zones rouges lus dans la
CASCADE DU RUN (résolue comme à la bascule : run propre ou étage 0 emprunté). Aucune réécriture de
p_raw, rang, contributions : SEUL `tier` change.

Pourquoi c'était nécessaire pour q_v21 : il a été scoré avec `LABUSE_ETAGE0_RUN=q_v20`, un label
SANS cascade en base (la cascade de q_v20 vit sous `q_v19_sources`) → l'étage 0 est revenu VIDE →
0 « Écartée » et 153 k exclusions dures retombées en « Sans signal » (d'où l'écart de paliers de
35,5 %). On rejoue les statuts sur la cascade PROPRE de q_v21 (`resoudre_cascade_run`).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from .statuts import assign_paliers, charger_paliers_config


def _etage0_idus(session, cascade_run: str) -> set[str]:
    rows = session.execute(text(
        "SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id "
        "WHERE d.run_label = :r AND d.status IN ('exclue', 'faux_positif_probable')"),
        {"r": cascade_run}).all()
    return {r[0] for r in rows}


def _rouge_total_idus(session, cascade_run: str) -> set[str]:
    """Parcelles ENTIÈREMENT en zone rouge (fraction PPR rouge = 100 %) — MÊME source et MÊME motif
    que le gate `jobs_impl.rouge_actionnables` et `renouvellement.ppr_x`."""
    rows = session.execute(text(
        "SELECT p.idu FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id "
        "WHERE cr.run_label = :r AND cr.layer_name = 'risques' AND cr.result = 'HARD_EXCLUDE' "
        "  AND cr.detail LIKE '%%PPR zone rouge%%' "
        "GROUP BY p.idu "
        "HAVING max((regexp_match(cr.detail, '([0-9]+) %% de la surface'))[1]::int) >= 100"),
        {"r": cascade_run}).all()
    return {r[0] for r in rows}


def recompute_paliers(session, run: str, cascade_run: str) -> dict:
    """Recompose `parcel_p_score_v2.tier` pour `run` via `assign_paliers`, en lisant l'étage 0 et les
    zones rouges dans `cascade_run`. Renvoie {n, change, avant, apres, cascade_run}. N'ÉCRIT que la
    colonne `tier`, et seulement là où elle change (UPDATE ... FROM temp). Commit laissé à l'appelant."""
    df = pd.read_sql(text(
        "SELECT parcelle_id AS idu, p_raw AS p, copro, tier AS tier_avant "
        "FROM parcel_p_score_v2 WHERE run_id = :r"),
        session.connection(), params={"r": run})
    if not len(df):
        raise ValueError(f"run « {run} » absent de parcel_p_score_v2 — rien à recomposer.")

    e0 = _etage0_idus(session, cascade_run)
    rouge = _rouge_total_idus(session, cascade_run)
    df["ecartee_etage0"] = df["idu"].isin(e0)
    df["risque_exclut"] = df["idu"].isin(rouge)
    # entrée STRICTE (prev_palier=None), comme le scoring (pipeline : assign_paliers(work, None, None)).
    df["tier"] = assign_paliers(df, charger_paliers_config(), None)

    avant = df["tier_avant"].value_counts().to_dict()
    apres = df["tier"].value_counts().to_dict()
    change = int((df["tier"] != df["tier_avant"]).sum())

    # UPDATE efficace : table temporaire (idu, tier) puis un seul UPDATE ... FROM là où ça change.
    maj = df[df["tier"] != df["tier_avant"]][["idu", "tier"]]
    session.execute(text("CREATE TEMP TABLE _recompute_tiers (idu text PRIMARY KEY, tier text) "
                         "ON COMMIT DROP"))
    if len(maj):
        maj.to_sql("_recompute_tiers", session.connection(), if_exists="append", index=False,
                   method="multi", chunksize=10000)
        session.execute(text(
            "UPDATE parcel_p_score_v2 s SET tier = t.tier FROM _recompute_tiers t "
            "WHERE s.run_id = :r AND s.parcelle_id = t.idu"), {"r": run})
    return {"n": int(len(df)), "change": change, "avant": avant, "apres": apres,
            "e0": len(e0), "rouge_total": len(rouge), "cascade_run": cascade_run}


def ecrire_manifeste_candidat(session, run: str, cascade_run: str, par: str,
                              now_iso: str | None = None) -> dict:
    """Écrit le MANIFESTE DU CANDIDAT (`config/candidat_manifest.json`) pour `run` depuis son état réel
    en base (modèle gelé, comptes, tiers). Attestation lue par `controler_run` (manifeste_present)."""
    from ... import manifeste as _manifeste

    meta = session.execute(text(
        "SELECT model_version, model_sha256, n_parcelles FROM p_score_v2_runs WHERE run_id = :r"),
        {"r": run}).first()
    if meta is None:
        raise ValueError(f"run « {run} » absent de p_score_v2_runs — pas de manifeste candidat.")
    tiers = {t: n for t, n in session.execute(text(
        "SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id = :r GROUP BY tier"),
        {"r": run}).all()}
    man = {
        "scoring_run": run,
        "cascade_run": cascade_run,
        "model_version": meta[0],
        "model_sha256": meta[1],
        "n_parcelles": int(meta[2]) if meta[2] is not None else None,
        "tiers": tiers,
        "generated_at": now_iso or datetime.now(timezone.utc).isoformat(),
        "par": par,
    }
    _manifeste.ecrire_candidat(man)
    return man
