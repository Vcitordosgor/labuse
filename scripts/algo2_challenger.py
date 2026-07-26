#!/usr/bin/env python
"""ALGO-2 B+D — features propriétaire AS-OF + challenger walk-forward + ablations.

RÈGLE ABSOLUE (mandat) : le champion servi (q_v7_defisc, artifact gelé) est INTOUCHÉ —
ce script n'écrit QUE la table préfixée `algo2_prop_features` et des fichiers sous
reports/algo2/. AUCUNE ligne dans parcel_p_score_v2 (sur main, /v2 et le golden lisent
« le dernier run » : y insérer un candidat FUIRAIT dans le produit — le run-candidat
formel se fera à la bascule, après décision Vic, via LABUSE_ETAGE0_RUN).

Features (inventaire A validé, résolution C ≥ 95 % prouvée 32/32) :
  B1 prop_type       : catégoriel DGFiP par millésime as-of (pm_privee/public/hlm/sem/
                       copro/autre) ; « non_pm » = pas de ligne PM (≈ personne physique) ;
                       « inconnu » = ANNÉES SANS PANEL (2017-2019) — deux absences
                       distinctes, deux catégories distinctes (précision Vic n°3 :
                       'inconnu' est une VRAIE catégorie, testée avec WoE propre).
  B2 tenure_mois     : CONTINUE, mois depuis la dernière mutation toutes natures
                       (< 01/01/Y, DVF ext 2014+) — 100 % du frame (précision Vic n°2 :
                       ablation SÉPARÉE du bloc PM).
  B3 prop_nb_commune / prop_nb_ile : portefeuille de l'entité RÉSOLUE (règle C :
                       SIREN strict + dénomination ≥ 12c unique — jamais deviné).
  B4 prop_anciennete : années depuis l'immatriculation (owner_enrichment, as-of).
  B6 prop_bodacc36   : annonce BODACC du propriétaire dans les 36 mois avant 01/01/Y
                       (datée → as-of parfait) — pré-compté ≥ 200 obs (précision n°4).
Boussole : AUCUNE identité de personne physique — tout est PM/flags/durées.

Protocole D = CELUI DU CHAMPION : folds 2020-2025, train ≤ F-2 (dummies d'année),
calibration isotonique sur F-1, test F ; C=5.0 ; les 5 interactions GELÉES du manifeste ;
seed 974 ; RR@1158 hors copro + IC95 bootstrap ; ECE ; signes ; permutation ;
RR PAR COMMUNE (fold 2025) ; ablations fold 2025 (BASE / +B2 / +PM / FULL, bootstrap
APPARIÉ) ; gate boussole golden (négatives factuelles ∉ top-1158 challenger).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from labuse.scoring.p_model import SEED, evaluate as ev
from labuse.scoring.p_model.features import FEATURES, FeatureSpec, derive
from labuse.scoring.p_model.model import PModel
from labuse.scoring.p_model.woe import WoeEncoder

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "algo2")
GOLDEN = os.path.join(os.path.dirname(__file__), "..", "reports", "m6-audit", "golden",
                      "golden-parcelles.json")
K = 1158
C_REG = 5.0
INTERACTIONS = [("tenure_bin", "permis_bin"), ("tenure_bin", "surface_m2"),
                ("ndvi_moyen", "zone_plu"), ("tenure_bin", "rot_nu"),
                ("surface_m2", "permis_bin")]          # manifeste FREEZE-scoring2026 (gelées)
FOLDS = (2020, 2021, 2022, 2023, 2024, 2025)

#: specs des features candidates (bloc 'P' = propriétaire ; B2 à part — précision Vic n°2)
SPECS_B2 = [FeatureSpec("tenure_mois", "D", "num", 0, "DVF ext toutes natures", "as-of", "as-of")]
SPECS_PM = [
    FeatureSpec("prop_type", "P", "cat", 0, "DGFiP panel millésimes", "as-of 01/01/Y", "panel 2019-2024"),
    FeatureSpec("prop_nb_commune", "P", "num", 0, "panel + résolution C", "as-of", "panel"),
    FeatureSpec("prop_nb_ile", "P", "num", 0, "panel + résolution C", "as-of", "panel"),
    FeatureSpec("prop_anciennete", "P", "num", 0, "INPI date_creation", "as-of", "historique"),
    FeatureSpec("prop_bodacc36", "P", "bool", 0, "BODACC daté", "36 mois avant 01/01/Y", "daté"),
]

BUILD_SQL = """
DROP TABLE IF EXISTS algo2_prop_features;
CREATE TABLE algo2_prop_features AS
WITH years(annee) AS (VALUES (2017),(2018),(2019),(2020),(2021),(2022),(2023),(2024),(2025)),
pm AS (  -- panel nettoyé + résolution C (SIREN strict, puis dénomination ≥12c unique/millésime)
  SELECT idu, millesime::int AS m, groupe,
         CASE WHEN length(regexp_replace(coalesce(siren,''),'[^0-9]','','g')) = 9
              THEN regexp_replace(siren,'[^0-9]','','g') END AS siren9,
         upper(regexp_replace(coalesce(denomination,''), '[^A-Za-z0-9]', '', 'g')) AS dn
  FROM pm_proprietaires_millesimes),
denom_map AS (  -- dénomination normalisée ≥12c → SIREN UNIQUE (par millésime)
  SELECT m, dn, min(siren9) AS siren9
  FROM pm WHERE siren9 IS NOT NULL AND length(dn) >= 12
  GROUP BY m, dn HAVING count(DISTINCT siren9) = 1),
res AS (  -- entité résolue par (idu, millésime)
  SELECT p.idu, p.m, p.groupe, coalesce(p.siren9, d.siren9) AS ent
  FROM pm p LEFT JOIN denom_map d ON d.m = p.m AND d.dn = p.dn AND p.siren9 IS NULL
                                  AND length(p.dn) >= 12),
portf AS (  -- portefeuille de l'entité résolue, par millésime (île et commune)
  SELECT m, ent, count(*) AS nb_ile FROM res WHERE ent IS NOT NULL GROUP BY m, ent),
portc AS (
  SELECT m, ent, left(idu,5) AS insee, count(*) AS nb_com
  FROM res WHERE ent IS NOT NULL GROUP BY m, ent, left(idu,5)),
immat AS (
  SELECT siren, substring(payload->>'date_creation' from 1 for 4)::int AS an_immat
  FROM owner_enrichment
  WHERE NOT coalesce((payload->>'not_found')::bool, false)
    AND payload->>'date_creation' ~ '^[0-9]{4}'),
bod AS (SELECT siren, date_annonce FROM bodacc_annonces_owner),
tenure AS (  -- B2 : dernière mutation toutes natures < 01/01/Y (100 % frame potentiel)
  SELECT ma.idu, y.annee,
         (make_date(y.annee,1,1) - max(ma.date_mutation)::date) / 30.44 AS tenure_mois
  FROM p_model_ext_mut_all ma CROSS JOIN years y
  WHERE ma.date_mutation < make_date(y.annee,1,1)
  GROUP BY ma.idu, y.annee)
SELECT f.idu, y.annee,
  CASE WHEN y.annee - 1 < 2019 THEN 'inconnu'         -- pas de panel avant 2019 (VRAIE catégorie)
       WHEN r.idu IS NULL      THEN 'non_pm'          -- millésime présent, pas de ligne PM
       WHEN r.groupe = 0 THEN 'pm_privee'
       WHEN r.groupe IN (1,3,4,9) THEN 'public'
       WHEN r.groupe = 5 THEN 'hlm'
       WHEN r.groupe = 6 THEN 'sem'
       ELSE 'autre' END                                            AS prop_type,
  t.tenure_mois,
  CASE WHEN y.annee - 1 >= 2019 THEN pc.nb_com END                 AS prop_nb_commune,
  CASE WHEN y.annee - 1 >= 2019 THEN pi.nb_ile END                 AS prop_nb_ile,
  CASE WHEN y.annee - 1 >= 2019 AND im.an_immat < y.annee
       THEN y.annee - im.an_immat END                              AS prop_anciennete,
  CASE WHEN y.annee - 1 < 2019 THEN NULL
       ELSE EXISTS (SELECT 1 FROM bod b WHERE b.siren = r.ent
                    AND b.date_annonce >= make_date(y.annee - 3, 1, 1)
                    AND b.date_annonce <  make_date(y.annee, 1, 1)) END AS prop_bodacc36
FROM p_model_frame f
CROSS JOIN years y
LEFT JOIN res r  ON r.idu = f.idu AND r.m = least(y.annee - 1, 2024) AND y.annee - 1 >= 2019
LEFT JOIN portf pi ON pi.m = r.m AND pi.ent = r.ent
LEFT JOIN portc pc ON pc.m = r.m AND pc.ent = r.ent AND pc.insee = left(f.idu, 5)
LEFT JOIN immat im ON im.siren = r.ent
LEFT JOIN tenure t ON t.idu = f.idu AND t.annee = y.annee;
CREATE UNIQUE INDEX ON algo2_prop_features (idu, annee);
"""


def fit_variant(df_tr, y_tr, df_cal, y_cal, extra_specs) -> PModel:
    specs = list(FEATURES) + list(extra_specs)
    names = [s.name for s in specs]
    enc = WoeEncoder(min_count=200).fit(df_tr, y_tr, specs)
    m = PModel(feature_names=names)
    m.encoder = enc
    m.interactions = list(INTERACTIONS)
    m.year_dummies = sorted(df_tr["annee"].unique())[:-1]  # même convention champion
    m.fit(df_tr, y_tr, C=C_REG)
    m.calibrate(df_cal, y_cal.astype(int))
    return m


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    eng = create_engine(DB)

    print("── B · matérialisation algo2_prop_features (as-of) ──", flush=True)
    with eng.begin() as cx:
        for stmt in BUILD_SQL.split(";"):
            if stmt.strip():
                cx.execute(text(stmt))
    with eng.connect() as cx:
        chk = cx.execute(text("""
            SELECT annee, count(*) FILTER (WHERE prop_type='inconnu') AS inconnu,
                   count(*) FILTER (WHERE prop_type='non_pm') AS non_pm,
                   count(*) FILTER (WHERE prop_type NOT IN ('inconnu','non_pm')) AS pm,
                   count(*) FILTER (WHERE prop_bodacc36) AS bodacc36,
                   count(tenure_mois) AS tenure_ok
            FROM algo2_prop_features GROUP BY annee ORDER BY annee""")).all()
        for r in chk:
            print("  ", dict(r._mapping), flush=True)

    print("── chargement dataset (2017-2025, labels) ──", flush=True)
    base = pd.read_sql(text("SELECT * FROM p_model_ext_dataset WHERE annee BETWEEN 2017 AND 2025"
                            " AND label IS NOT NULL"), eng)
    prop = pd.read_sql(text("SELECT * FROM algo2_prop_features WHERE annee BETWEEN 2017 AND 2025"), eng)
    cop = pd.read_sql(text("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro"), eng)
    df = derive(base).merge(prop, on=["idu", "annee"], how="left")
    df = df.merge(cop, on="idu", how="left")
    df["copro"] = df["copro"].fillna(False).astype(bool)
    df["prop_type"] = df["prop_type"].fillna("inconnu")
    df["prop_bodacc36"] = df["prop_bodacc36"].astype("boolean")
    y_all = df["label"].astype(int)

    VARIANTS = {"BASE": [], "B2": SPECS_B2, "PM": SPECS_PM, "FULL": SPECS_B2 + SPECS_PM}
    res_folds, signes = [], {}
    for F in FOLDS:
        tr = df[df["annee"] <= F - 2]
        cal = df[df["annee"] == F - 1]
        te = df[(df["annee"] == F) & (~df["copro"])].reset_index(drop=True)
        m = fit_variant(tr, y_all.loc[tr.index], cal, y_all.loc[cal.index], VARIANTS["FULL"])
        p = m.predict_proba(te)
        rr = ev.bootstrap_rr(te["label"].astype(int).to_numpy(), p, K, n_boot=1000, seed=SEED)
        e, _ = ev.ece(te["label"].astype(int).to_numpy(), p)
        res_folds.append({"fold": F, "n_train": len(tr), "rr": rr["rr"], "lo": rr["ic95_bas"],
                          "hi": rr["ic95_haut"], "ece": e, "pos_topk": rr["positifs_topk"]})
        for k, v in m.coefs.items():
            signes.setdefault(k, []).append(np.sign(v) if abs(v) > 1e-6 else 0.0)
        print(f"  FULL fold {F}: RR@{K}={rr['rr']:.2f} [{rr['ic95_bas']:.2f};{rr['ic95_haut']:.2f}] "
              f"ECE={e:.4f}", flush=True)
        if F == 2025:
            te25, m_full, p_full = te, m, p
            # bin 'inconnu' = VRAIE catégorie (précision Vic n°3) — preuve chiffrée
            bf = m.encoder.binned["prop_type"]
            idx = bf.categories.get("inconnu")
            print(f"  [bin inconnu] catégorie={idx is not None} effectif="
                  f"{bf.counts[idx] if idx is not None else 0} woe="
                  f"{bf.woe[idx] if idx is not None else None}", flush=True)

    print("── ablations fold 2025 (bootstrap APPARIÉ vs BASE) ──", flush=True)
    tr = df[df["annee"] <= 2023]; cal = df[df["annee"] == 2024]
    scores = {"FULL": p_full}
    for name in ("BASE", "B2", "PM"):
        mv = fit_variant(tr, y_all.loc[tr.index], cal, y_all.loc[cal.index], VARIANTS[name])
        scores[name] = mv.predict_proba(te25)
        print(f"  {name}: fit ok", flush=True)
    y25 = te25["label"].astype(int).to_numpy()
    abl = []
    from labuse.scoring.arene import paired_bootstrap_diff
    for name in ("BASE", "B2", "PM", "FULL"):
        rr = ev.bootstrap_rr(y25, scores[name], K, n_boot=1000, seed=SEED)
        d = (paired_bootstrap_diff(y25, scores[name], scores["BASE"], K, n_boot=1000, seed=SEED)
             if name != "BASE" else {"diff_rr": 0.0, "ic95_bas": 0.0, "ic95_haut": 0.0})
        abl.append({"variante": name, "rr": rr["rr"], "lo": rr["ic95_bas"], "hi": rr["ic95_haut"],
                    "d_vs_base": d["diff_rr"], "d_lo": d["ic95_bas"], "d_hi": d["ic95_haut"]})
        print(f"  {name}: RR={rr['rr']:.2f} Δbase={d['diff_rr']:+.2f} [{d['ic95_bas']:+.2f};{d['ic95_haut']:+.2f}]",
              flush=True)

    # champion fold 2025 (out-of-sample, CSV gelé) — Δ FULL vs CHAMPION apparié
    ch = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "reports", "m36-foncier",
                                  "scores-2025-fold-final.csv"))
    te_ch = te25.merge(ch, on="idu", how="left")
    d_ch = paired_bootstrap_diff(y25, scores["FULL"], te_ch["p_l2f"].to_numpy(float), K,
                                 n_boot=1000, seed=SEED)
    churn = ev.churn_topk(pd.Series(te_ch["p_l2f"].to_numpy(float), index=te25["idu"]),
                          pd.Series(scores["FULL"], index=te25["idu"]), K, seed=SEED)
    perm = ev.permutation_control(y25, scores["FULL"], np.full(len(te25), 2025), K, seed=SEED)

    # RR PAR COMMUNE fold 2025 — FULL vs champion (les 4 cibles + toutes)
    rows_c = []
    for com, g in te25.assign(p_full=scores["FULL"], p_ch=te_ch["p_l2f"].to_numpy(float)).groupby("commune"):
        yc = g["label"].astype(int).to_numpy()
        k_c = max(5, int(round(K * len(g) / len(te25))))
        rows_c.append({"commune": com, "n": len(g), "k_c": k_c,
                       "rr_full": ev.rr_at_k(yc, g["p_full"].to_numpy(), k_c, seed=SEED)["rr"],
                       "rr_champion": ev.rr_at_k(yc, g["p_ch"].to_numpy(), k_c, seed=SEED)["rr"]})

    # gate boussole : négatives factuelles golden ∉ top-1158 FULL
    gold = json.load(open(GOLDEN, encoding="utf-8"))
    negs = [i for i, e in gold["parcelles"].items()
            if (e.get("anchor") and e.get("validation") == "factuelle")
            or (not e.get("anchor") and ((e.get("db", {}).get("score_v2") or {}).get("tier") == "ecartee"
                                         or e.get("db", {}).get("etage0")))]
    rng = np.random.RandomState(SEED)
    top_mask = ev._ranked_top_mask(scores["FULL"], K, rng)
    top_idus = set(te25.loc[top_mask, "idu"])
    violations = sorted(set(negs) & top_idus)

    pd.DataFrame(res_folds).to_csv(f"{OUT}/walk-forward-challenger.csv", index=False)
    pd.DataFrame(abl).to_csv(f"{OUT}/ablations-2025.csv", index=False)
    pd.DataFrame(rows_c).sort_values("rr_full", ascending=False).to_csv(f"{OUT}/rr-commune-2025.csv", index=False)
    stab = {k: (abs(sum(v)) == len(v)) for k, v in signes.items()}
    json.dump({"delta_vs_champion_2025": d_ch, "churn_top1158": churn, "permutation": perm,
               "boussole_violations": violations, "signes_stables": sum(stab.values()),
               "signes_total": len(stab),
               "signes_instables": [k for k, ok in stab.items() if not ok]},
              open(f"{OUT}/synthese.json", "w"), indent=1)
    print("── SYNTHÈSE ──", flush=True)
    print(f"Δ FULL−CHAMPION fold 2025 (apparié): {d_ch['diff_rr']:+.2f} "
          f"[{d_ch['ic95_bas']:+.2f};{d_ch['ic95_haut']:+.2f}] significatif={d_ch['significatif']}")
    print(f"churn top-1158 vs champion: {1 - churn['overlap_pct']:.0%} · permutation RR={perm['rr']:.2f}")
    print(f"boussole: {len(violations)} violation(s) {violations[:5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
