"""SCORING-2 · K5 — le challenger gradient boosting, jugé en arène.

HistGradientBoostingClassifier (sklearn, natif dans le venv ML — l'« équivalent
LightGBM » du mandat : mêmes arbres à histogrammes, mêmes contraintes de
monotonie via `monotonic_cst`, catégorielles natives). UN modèle par segment,
zone A hors apprentissage, calibration isotonique 2024, test 2025 — le MÊME
protocole et le MÊME banc K0 que le champion. RIEN n'est promu ici.

Règle de promotion (ÉCRITE, jamais appliquée — mandat K5.3) : le challenger ne
peut être promu que s'il gagne sur 2025 (année vierge) À LA FOIS
  (a) la précision en haut de liste : préc@100/commune médiane ET précision
      réelle de Priorité ≥ champion,
  (b) l'AUC global,
  (c) et tient ECE ≤ 0,01 sur CHAQUE segment.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocole  # noqa: E402
from _common import engine  # noqa: E402
from protocole import (  # noqa: E402
    CAL_YEAR, OUT, SCORE_YEAR, SEGMENTS, TEST_YEAR, TRAIN_MAX, TRAIN_MIN)

SEED = 974

#: contraintes de monotonie MÉTIER (+1 = plus la valeur monte, plus le hasard
#: de vente monte). Catégorielles et features au signe débattable : libres (0).
MONOTONIE_METIER = {
    "rot_nu": +1, "rot_bati": +1,             # rotation du secteur (spec servie : +1)
    # (détention = catégorielle tenure_bin_v2 → pas de contrainte possible ici)
    "sdp_residuelle_v2_m2": +1,               # droits non consommés
    "ventes_150m_12m": +1, "ventes_150m_24m": +1,
    "ventes_400m_12m": +1, "ventes_400m_24m": +1,   # une vente se propage
    "permis_100m_24m": +1, "operations_pa_400m_24m": +1,
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class ChallengerSegments:
    """4 HistGB + isotonique par segment. Interface alignée sur ModeleSegments."""

    def __init__(self, names: list[str], specs):
        self.names = names
        self.kinds = {s.name: s.kind for s in specs}
        self.cat_cols = [n for n in names if self.kinds[n] in ("cat", "bool")]
        self.d_features = [s.name for s in specs if s.bloc == "D"]
        self.modeles: dict[str, HistGradientBoostingClassifier] = {}
        self.isos: dict[str, IsotonicRegression] = {}
        self.categories: dict[str, list] = {}
        self.median_d: pd.Series | None = None

    # ---- encodage : num tels quels (NaN natif), cat/bool → codes entiers ----
    def _X(self, df: pd.DataFrame) -> pd.DataFrame:
        X = pd.DataFrame(index=df.index)
        for n in self.names:
            col = df[n]
            if n in self.cat_cols:
                cats = self.categories.setdefault(
                    n, sorted(col.astype(str).fillna("nan").unique().tolist()))
                mapping = {c: i for i, c in enumerate(cats)}
                X[n] = col.astype(str).fillna("nan").map(mapping).fillna(-1).astype(float)
            else:
                X[n] = pd.to_numeric(col, errors="coerce").astype(float)
        return X

    def fit(self, df: pd.DataFrame, seg: pd.Series, label_col: str = "label") -> "ChallengerSegments":
        hors_a = (df["zone_plu"].fillna("inconnu") != "A").to_numpy()
        train_m = ((df.annee >= TRAIN_MIN) & (df.annee <= TRAIN_MAX)).to_numpy() & hors_a
        cal_m = (df.annee == CAL_YEAR).to_numpy()
        mono = [MONOTONIE_METIER.get(n, 0) if n not in self.cat_cols else 0
                for n in self.names]
        cat_mask = [n in self.cat_cols for n in self.names]
        # figer les catégories sur TOUT le jeu (mêmes codes train/cal/test)
        self._X(df)
        self.median_d = self._X(df[train_m])[
            [c for c in self.d_features if c not in self.cat_cols]].median()
        for s in SEGMENTS:
            m_tr = train_m & (seg == s).to_numpy()
            m_ca = cal_m & (seg == s).to_numpy()
            sub, y = self._X(df[m_tr]), df.loc[m_tr, label_col].astype(int)
            log(f"  challenger segment {s} : {len(sub)} lignes train")
            gbm = HistGradientBoostingClassifier(
                random_state=SEED, max_iter=400, learning_rate=0.06,
                max_leaf_nodes=31, min_samples_leaf=100,
                early_stopping=True, validation_fraction=0.15,
                monotonic_cst=mono, categorical_features=cat_mask)
            gbm.fit(sub.to_numpy(), y.to_numpy())
            z = gbm.decision_function(self._X(df[m_ca]).to_numpy())
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            iso.fit(z, df.loc[m_ca, label_col].astype(int).to_numpy())
            self.modeles[s], self.isos[s] = gbm, iso
        return self

    def predict_proba(self, df: pd.DataFrame, seg: pd.Series) -> np.ndarray:
        p = np.full(len(df), np.nan)
        segv = seg.to_numpy()
        X = self._X(df)
        for s, gbm in self.modeles.items():
            mask = segv == s
            if mask.any():
                z = gbm.decision_function(X[mask].to_numpy())
                p[mask] = np.clip(self.isos[s].predict(z), 1e-7, 1 - 1e-7)
        assert not np.isnan(p).any()
        return p

    def contrib_d(self, df: pd.DataFrame, seg: pd.Series) -> np.ndarray:
        """Pseudo-contribution D (gate brûlante) : log-hasard complet MOINS
        log-hasard avec le bloc D neutralisé (numériques D → médiane train,
        catégorielles D → laissées : proxy documenté, seuil calibré ensuite)."""
        segv = seg.to_numpy()
        X = self._X(df)
        Xn = X.copy()
        for c in self.median_d.index:
            Xn[c] = float(self.median_d[c])
        out = np.full(len(df), np.nan)
        for s, gbm in self.modeles.items():
            mask = segv == s
            if mask.any():
                out[mask] = (gbm.decision_function(X[mask].to_numpy())
                             - gbm.decision_function(Xn[mask].to_numpy()))
        return out


REGLE_PROMOTION = {
    "precision_tete": "prec@100_commune_mediane ≥ champion ET prec_priorite ≥ champion",
    "auc": "auc_global > champion",
    "calibration": "ece ≤ 0,01 sur chacun des 4 segments",
    "decision": "les trois conditions À LA FOIS, sur 2025 (année vierge) — sinon le champion reste",
    "appliquee_dans_ce_mandat": False,
}


def verdict_arene(champion: dict, challenger: dict) -> dict:
    """Applique la règle SUR LE PAPIER (aucune promotion ici)."""
    tete = (challenger["prec@100_commune_mediane"] >= champion["prec@100_commune_mediane"]
            and challenger["prec_priorite"] >= champion["prec_priorite"])
    auc = challenger["auc_global"] > champion["auc_global"]
    ece_ok = all(challenger[f"ece_{s}"] <= 0.01 for s in SEGMENTS)
    return {"gagne_precision_tete": bool(tete), "gagne_auc": bool(auc),
            "ece_tenue_par_segment": bool(ece_ok),
            "promotion_satisfaite": bool(tete and auc and ece_ok),
            "promotion_appliquee": False}


def k5() -> None:
    """K5 — le challenger au banc K0, côte à côte avec le champion K4 bis."""
    import joblib
    import measure
    import candidats
    eng = engine()
    names, specs, _ = candidats.features_k4bis()
    log("[K5] chargement…")
    df = protocole.load_range(eng, candidats.YEARS)
    df = candidats._enrichir_k4bis(eng, df)
    copro = measure.copro_mask(eng, df)
    seg = protocole.segmenter(df, copro)
    log("[K5] fit challenger (4 segments, monotonie métier)…")
    ch = ChallengerSegments(names, specs).fit(df, seg)
    ctx = protocole.Contexte(eng, df[df.annee == TEST_YEAR],
                             df[df.annee == SCORE_YEAR])
    seg_test = seg[(df.annee == TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg[(df.annee == SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = ch.predict_proba(ctx.test, seg_test)
    cd = ch.contrib_d(ctx.test, seg_test)
    p26 = ch.predict_proba(ctx.score26, seg_26)
    row = protocole.metriques(ctx, "K5_challenger_gbm", p, cd, p26)
    table = protocole.enregistrer(row)
    # champion = la variante GLOBALE de K4 bis (verdicts K4/K4bis mesurés : la
    # segmentée perd la tête de liste — priorité déclarée du mandat)
    champion = table[table.candidat == "K4bis_voisinage_global"].iloc[0].to_dict()
    verdict = verdict_arene(champion, row)
    arene = pd.DataFrame([champion, row]).set_index("candidat").T
    arene.to_csv(OUT / "k5_arene.csv")
    with open(OUT / "k5_verdict.json", "w", encoding="utf-8") as f:
        json.dump({"regle": REGLE_PROMOTION, "verdict": verdict}, f,
                  ensure_ascii=False, indent=2)
    joblib.dump(ch, OUT / "cache/challenger_k5.joblib")
    print(arene.to_string())
    print(json.dumps(verdict, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    k5()
