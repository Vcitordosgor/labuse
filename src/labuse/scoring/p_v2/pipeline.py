"""Pipeline de scoring production v2 (M5 lot 1) — `labuse score-v2`.

Étapes : vérif sha256 de l'artifact gelé (REFUS si mismatch) → rebuild des
features as-of (builder ext M3.6, réutilisé en import) → recalage d'intercept →
scoring → rangs/percentiles hors copro → tiers v2 (hystérésis vs run précédent)
→ écriture versionnée (parcel_p_score_v2) → gel snapshot (mécanisme M1).

POLITIQUE DE RECALIBRATION (mandat 1.3, gravée ici) :
  - à CHAQUE run : recalage de l'INTERCEPT seul sur la dernière année labellisée
    (décalage additif du log-hazard, coefficients et binning INTACTS) — corrige
    la dérive de niveau du marché sans toucher au classement appris ;
  - re-train complet (binning + coefficients + calibration) : DÉCISION HUMAINE
    ANNUELLE, jamais automatique — passe par un mandat, un nouveau walk-forward
    et un nouveau manifeste de gel.

Convention as-of : le modèle est au grain annuel (features au 01/01 de l'année
courante, fenêtres finissant au 31/12 précédent). Un run mensuel rafraîchit les
DONNÉES sous-jacentes (DVF/Sitadel arrivent avec retard — cf. protocole B0),
pas la convention temporelle.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import score_v  # mécanisme snapshot M1 (lecture seule, réutilisé)
from ..score_v_constants import Q_A_RUN_LABEL  # source unique du run SERVI (bascule centralisée)
from ..p_model import ext_sql
from ..p_model.features import derive
from ..p_model.model import PModel
from . import MODEL_ARTIFACT, MODEL_FREEZE, MODEL_VERSION, SEED
from .statuts import TierParams, assign_tiers, calibre_brulante, calibre_n_entree

#: Libellés français des features (contributions lisibles, mandat 1.1/4.1).
LIBELLES = {
    "rot_nu": "rotation foncier nu du secteur",
    "rot_bati": "rotation bâti du secteur",
    "med_pm2_terrain_36m": "prix médian du terrain (36 mois)",
    "med_pm2_bati_36m": "prix médian du bâti (36 mois)",
    "tendance_pm2_bati": "tendance des prix du bâti",
    "permis_24m_norm": "permis dans le secteur (24 mois)",
    "dens_bati_secteur": "densité bâtie du secteur",
    "pct_bati_secteur": "part de parcelles bâties du secteur",
    "filo_snv_pp": "niveau de vie du carreau",
    "filo_pct_pauv": "part de ménages pauvres",
    "filo_pct_prop": "part de propriétaires",
    "filo_dens_pop": "densité de population",
    "qpv": "quartier prioritaire",
    "pente_moy_deg": "pente moyenne",
    "acces_equipements": "accès aux équipements",
    "zone_plu": "zone PLU",
    "window_coverage": "couverture de la fenêtre DVF",
    "nu_constructible": "nu constructible",
    "surface_m2": "surface de la parcelle",
    "dormance_droits": "droits à bâtir dormants",
    "sous_densite": "sous-densité",
    "sdp_residuelle_m2": "SDP résiduelle",
    "tenure_bin": "ancienneté de la dernière mutation",
    "permis_bin": "ancienneté du dernier permis",
    "canopee_pct": "canopée",
    "ndvi_moyen": "végétation (NDVI)",
    "friche": "friche répertoriée",
    "piscine": "piscine détectée",
    "pv_candidat": "candidat photovoltaïque",
}

#: Codes de signaux v1.3 DATÉS qui comptent comme « événement » (bypass, brûlante).
EVENT_CODES = {"BODACC_LJ", "BODACC_RJ", "BODACC_SAUVEGARDE", "BODACC_CESSION_FONDS"}


def verify_artifact() -> tuple[PModel, str]:
    """Charge l'artifact gelé et REFUSE tout mismatch sha256 (mandat 1.2)."""
    import joblib

    freeze = json.loads(Path(MODEL_FREEZE).read_text())
    sha = hashlib.sha256(Path(MODEL_ARTIFACT).read_bytes()).hexdigest()
    if sha != freeze["sha256"]:
        raise RuntimeError(
            f"REFUS : sha256 de l'artifact ({sha[:16]}…) ≠ manifeste de gel "
            f"({freeze['sha256'][:16]}…) — l'artifact M3.6 seul fait foi.")
    return joblib.load(MODEL_ARTIFACT), sha


def rebuild_features(session: Session) -> None:
    """Re-matérialise l'union DVF + le dataset ext (builder M3.6, importé)."""
    ext_sql.build_ext_union(session)
    ext_sql.build_ext_mutations(session)
    ext_sql.build_ext_dataset(session)
    from ..p_model import sql as p_sql  # copro dépend de p_model_frame
    ext_sql.build_copro_flags(session)
    _ = p_sql  # import documentaire : le frame M3 est réutilisé tel quel


def load_events(session: Session) -> pd.DataFrame:
    """Dernier événement DATÉ v1.3 par parcelle (signals JSONB de parcel_v_score)."""
    rows = session.execute(text("""
        SELECT v.parcelle_id, max((s ->> 'date_evenement')::date) AS event_date
        FROM parcel_v_score v, jsonb_array_elements(coalesce(v.signals, '[]')) s
        WHERE s ->> 'code' = ANY(:codes) AND s ->> 'date_evenement' IS NOT NULL
        GROUP BY v.parcelle_id
    """), {"codes": list(EVENT_CODES)}).all()
    return pd.DataFrame(rows, columns=["idu", "event_date"])


def top5_lisibles(model: PModel, contrib: pd.DataFrame, df: pd.DataFrame) -> list:
    """Top 5 contributions par ligne : [{feature, bin, signe, libelle, valeur}]."""
    feat_cols = [c for c in contrib.columns if not c.startswith("contrib_")]
    vals = contrib[feat_cols].to_numpy()
    order = np.argsort(-np.abs(vals), axis=1)[:, :5]
    bin_cache: dict[str, np.ndarray] = {}
    labels: dict[str, list[str]] = {}
    for name in feat_cols:
        base = name.split("*")[0] if "*" in name else name
        bf = model.encoder.binned.get(base)
        if bf is not None and "*" not in name:
            idx = bf.bin_index(df[name])
            bin_cache[name] = idx
            labels[name] = [bf.bin_label(i) for i in
                            range(-1, len(bf.woe))]  # -1 → position 0
    rows = []
    for i in range(len(df)):
        entries = []
        for j in order[i]:
            name = feat_cols[j]
            v = float(vals[i, j])
            if abs(v) < 1e-9:
                continue
            base = name.split("*")[0] if "*" in name else name
            lib = LIBELLES.get(base, base)
            if "*" in name:
                autre = name.split("*")[1]
                lib = f"croisement {lib} × {LIBELLES.get(autre, autre)}"
                bin_lab = ""
            else:
                bin_lab = labels[name][int(bin_cache[name][i]) + 1]
            entries.append({"feature": name, "bin": bin_lab,
                            "signe": "+" if v > 0 else "-",
                            "libelle": lib, "log_hazard": round(v, 4)})
        rows.append(entries)
    return rows


def previous_run(session: Session) -> tuple[str | None, pd.Series | None]:
    run = session.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
    if not run:
        return None, None
    prev = pd.read_sql(text(
        "SELECT parcelle_id, tier FROM parcel_p_score_v2 WHERE run_id = :r"),
        session.connection(), params={"r": run})
    return run, prev.set_index("parcelle_id")["tier"]


def run_score_v2(session: Session, *, run_id: str | None = None,
                 rebuild: bool = True, annee: int | None = None,
                 snapshot: bool = True) -> dict:
    """Exécute le scoring v2 complet. Idempotent : run_id identique → REFUS
    explicite (versionné par run, jamais d'écrasement silencieux)."""
    t0 = time.time()
    model, sha = verify_artifact()
    annee = annee or date.today().year
    run_id = run_id or f"{MODEL_VERSION}-{date.today().isoformat()}"

    if session.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id = :r"),
                       {"r": run_id}).scalar():
        raise RuntimeError(f"run_id '{run_id}' existe déjà — relance avec un "
                           "run_id explicite différent (aucun écrasement silencieux).")

    if rebuild:
        rebuild_features(session)

    df = pd.read_sql(text("SELECT * FROM p_model_ext_dataset WHERE annee = :a"),
                     session.connection(), params={"a": annee})
    df = derive(df).reset_index(drop=True)

    # recalage d'intercept sur la dernière année labellisée (politique 1.3)
    last_labeled = int(pd.read_sql(text(
        "SELECT max(annee) FROM p_model_ext_dataset WHERE label IS NOT NULL"),
        session.connection()).iloc[0, 0])
    dcal = pd.read_sql(text("SELECT * FROM p_model_ext_dataset WHERE annee = :a"),
                       session.connection(), params={"a": last_labeled})
    dcal = derive(dcal).reset_index(drop=True)
    model = copy.deepcopy(model)
    model.recale_intercept(dcal, dcal["label"].astype(int))

    p = model.predict_proba(df)
    contrib = model.contributions(df)

    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro "
                        "FROM p_model_ext_copro", session.connection())
    df = df.merge(copro, on="idu", how="left")
    df["copro"] = df["copro"].fillna(False).astype(bool)

    # rangs et percentiles HORS copro, ties départagés seedés 974
    rng = np.random.RandomState(SEED)
    tie = rng.random(len(df))
    hors = ~df["copro"].to_numpy()
    rang = np.full(len(df), np.nan)
    order = np.lexsort((tie[hors], -p[hors]))
    rang_h = np.empty(hors.sum())
    rang_h[order] = np.arange(1, hors.sum() + 1)
    rang[hors] = rang_h
    pct = np.full(len(df), np.nan)
    pct[hors] = 100.0 * (1 - (rang_h - 1) / hors.sum())
    taux_base = float(p[hors].mean())

    # étage 0 + événements datés — l'étage 0 est lu sur le run SERVI (Q_A_RUN_LABEL,
    # source unique / bascule centralisée), PAS un run gelé en dur (ANO-1 : « q_v2 »
    # codé en dur = dette, le servi ré-appliquait déjà q_v5_m6b → on aligne le calcul interne).
    # M8a — override NON DESTRUCTIF pour scorer un run CANDIDAT sur SA propre cascade sans
    # toucher la constante servie : `LABUSE_ETAGE0_RUN` (défaut = Q_A_RUN_LABEL, comportement
    # inchangé pour l'app et les tests). Utilisé uniquement en batch candidat, jamais en prod.
    etage0_run = os.environ.get("LABUSE_ETAGE0_RUN", Q_A_RUN_LABEL)
    etage0 = pd.read_sql(text("""
        SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
        WHERE d.run_label = :run AND d.status IN ('exclue', 'faux_positif_probable')
    """), session.connection(), params={"run": etage0_run})
    df["ecartee_etage0"] = df["idu"].isin(set(etage0["idu"]))
    events = load_events(session)
    df = df.merge(events, on="idu", how="left")
    asof = pd.Timestamp(date(annee, 1, 1))
    now = pd.Timestamp.today()
    df["event_age_mois"] = (now - pd.to_datetime(df["event_date"])).dt.days / 30.44
    _ = asof  # l'âge des événements est relatif à AUJOURD'HUI (fraîcheur produit)

    # tiers : calibrage N_e (effectif chaude ~1 150) puis hystérésis vs run précédent
    work = df.assign(rang=rang, p=p, contrib_d=contrib["contrib_D"].to_numpy())
    from .statuts import plancher_c
    base_params = TierParams(n_entree=1, n_sortie=1)
    eligibles = work[~work["copro"] & ~work["ecartee_etage0"]
                     & plancher_c(work, base_params)]
    n_e = calibre_n_entree(eligibles["rang"], cible=1150)
    params = TierParams(n_entree=n_e, n_sortie=int(round(1.4 * n_e)))
    prev_run, prev_tiers = previous_run(session)
    prev_aligned = (df["idu"].map(prev_tiers) if prev_tiers is not None else None)
    tier = assign_tiers(work, params, prev_aligned)
    # brûlante : calibrage mécanique sur les chaudes du run (garde-fou 30-120)
    # (au 1er passage les seuils brûlante sont à 0 → chaude ∪ brulante = les chaudes)
    chaudes = work[tier.isin(["chaude", "brulante"])]
    params = calibre_brulante(chaudes, params)
    tier = assign_tiers(work, params, prev_aligned)

    top5 = top5_lisibles(model, contrib, df)

    event_dates = pd.to_datetime(df["event_date"], errors="coerce")
    rows = pd.DataFrame({
        "run_id": run_id, "parcelle_id": df["idu"],
        "p_raw": np.round(p, 6),
        "mult_base": np.round(p / taux_base, 2),
        # colonnes nullables en objets Python purs (None, jamais pd.NA/NaT :
        # psycopg ne sait pas les adapter en insertion multi)
        "percentile": [None if np.isnan(v) else round(float(v), 2) for v in pct],
        "rang": [None if np.isnan(r) else int(r) for r in rang],
        "contrib_z": np.round(contrib["contrib_Z"], 4),
        "contrib_d": np.round(contrib["contrib_D"], 4),
        "top5_contributions": top5,
        "copro": df["copro"], "tier": tier,
        "event_date": [d.date() if pd.notna(d) else None for d in event_dates],
        "model_version": MODEL_VERSION,
    })
    assert len(rows) == len(df) and rows["p_raw"].notna().all(), "NA interdit"

    from sqlalchemy.dialects.postgresql import JSONB
    rows.to_sql("parcel_p_score_v2", session.connection(), if_exists="append",
                index=False, method="multi", chunksize=5000,
                dtype={"top5_contributions": JSONB})

    snapshot_label = None
    if snapshot:
        snapshot_label = f"m5-{date.today().isoformat()}"
        _snapshot_v2(session, snapshot_label, run_id, rows)

    session.execute(text("""
        INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params,
                                     n_parcelles, duration_s, snapshot_label)
        VALUES (:r, :v, :s, :p, :n, :d, :l)"""), {
        "r": run_id, "v": MODEL_VERSION, "s": sha,
        "p": json.dumps({"n_entree": params.n_entree, "n_sortie": params.n_sortie,
                         "c_surface_min_m2": params.c_surface_min_m2,
                         "brulante_seuil_d": params.brulante_seuil_d,
                         "brulante_top_decile_d": params.brulante_top_decile_d,
                         "annee_features": annee, "recale_intercept_sur": last_labeled,
                         "taux_base": taux_base, "prev_run": prev_run}),
        "n": len(rows), "d": int(time.time() - t0), "l": snapshot_label})

    # M9 lot 1 — Indice de confiance données (ICD) : backfill LECTURE depuis le dataset
    # qui vient d'être matérialisé pour CE run. Colonnes annexes icd/icd_detail,
    # CLOISONNÉES du score P (n'altèrent ni tier, ni rang, ni p_raw). Best-effort :
    # une absence de dataset (ex. run sans rebuild) ne doit pas faire échouer le scoring.
    try:
        from ..icd import backfill_run as _icd_backfill
        n_icd = _icd_backfill(session, run_id, annee=annee)
    except Exception as _e:  # noqa: BLE001
        n_icd = 0

    tiers_counts = tier.value_counts().to_dict()
    return {"run_id": run_id, "n": len(rows), "duree_s": int(time.time() - t0),
            "params": params, "tiers": tiers_counts, "taux_base": taux_base,
            "snapshot": snapshot_label, "sha256": sha[:16], "icd_backfill": n_icd}


def _snapshot_v2(session: Session, label: str, run_id: str, rows: pd.DataFrame) -> None:
    """Gel v2 dans les tables snapshots M1 (protocole : un label ne s'écrase
    JAMAIS — même refus que score_v.snapshot_scores)."""
    if session.execute(text("SELECT 1 FROM score_snapshots WHERE label = :l"),
                       {"l": label}).scalar():
        raise RuntimeError(f"snapshot '{label}' existe déjà — protocole M1 : "
                           "un label ne s'écrase jamais.")
    sid = session.execute(text("""
        INSERT INTO score_snapshots (label, run_label, brulante_threshold, notes)
        VALUES (:l, :r, 0, :n) RETURNING id"""), {
        "l": label, "r": run_id,
        "n": f"scoring v2 (M5) — modèle {MODEL_VERSION}, tiers v2 ; "
             "brulante_threshold=0 (sans objet, seuils v2 dans p_score_v2_runs.params)",
    }).scalar()
    # v_score / v_band omis : NULL par défaut (sans objet pour un snapshot v2)
    snap = pd.DataFrame({
        "snapshot_id": sid, "parcelle_id": rows["parcelle_id"],
        "statut": rows["tier"],
        "brulante": rows["tier"] == "brulante",
        "veille_succession": False,
    })
    snap.to_sql("score_snapshot_parcelles", session.connection(),
                if_exists="append", index=False, method="multi", chunksize=5000)
    _ = score_v  # référence documentaire au mécanisme M1 réutilisé
