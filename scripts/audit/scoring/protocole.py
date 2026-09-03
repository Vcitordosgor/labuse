"""SCORING-2 · K0 — LE banc de mesure, figé avant tout changement de candidat.

Protocole unique (mandat K0.1, plan §3.3) : entraîner ≤ 2023 · calibrer 2024 ·
tester 2025 (année vierge — jamais touchée par binning, fit ni calibration).
Chaque lot K passe par CE module ; aucun second harnais.

Réutilise le harnais SCORING-1 validé contre la prod (_common, measure) :
  - _common.load_year / engine (chargement + derive)
  - measure.copro_mask / measure._attach_gates (univers produit + gates statiques servis)
  - p_model.evaluate (rr_at_k, ece, churn_topk — tirages seedés 974)
  - p_v2.statuts (reconstruction des paliers, mêmes calibrages que la prod)

Doctrine : RIEN de servi ne change. Lecture seule sur la base ; n'écrit QUE dans
reports/score-v2-arene/. q_v11_m137 reste servi.

Hygiène de la cible (K0.3) :
  - une mutation multi-parcelles compte déjà UNE fois par parcelle (label EXISTS) ;
    l'indicateur « vente groupée » est porté par parcelle-test (flag, jamais une exclusion) ;
  - les ventes 2025 à un client LABUSE (courrier réellement parti ou piste CRM
    ANTÉRIEURS à la vente) sont EXCLUES de l'évaluation et comptées à part.

Univers de mesure (constant pour tous les candidats) :
  - métriques de rang (précision@100, paliers, lift décile, churn) : HORS COPRO
    (l'univers produit — les copros écraseraient tout, taux 29 %) ;
  - AUC / ECE par segment : chaque segment séparément, copro incluse comme segment.

Sous-commande : `python protocole.py baseline` — hygiène + ligne de base fold2025
(l'artefact du walk-forward est déjà EXACTEMENT ce protocole : train ≤2023, iso 2024).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import engine, ROOT, SERVED_RUN  # noqa: E402
import measure  # noqa: E402  — copro_mask, _attach_gates (réutilisés, pas réécrits)
from labuse.scoring.p_model import evaluate as ev  # noqa: E402
from labuse.scoring.p_model.features import FEATURES, derive  # noqa: E402
from labuse.scoring.p_model.model import PModel  # noqa: E402
from labuse.scoring.p_v2.statuts import (  # noqa: E402
    TierParams, assign_tiers, calibre_brulante, calibre_n_entree, plancher_c)
from labuse.scoring.tiers_client import court  # noqa: E402

OUT = ROOT / "reports/score-v2-arene"
OUT.mkdir(parents=True, exist_ok=True)

TRAIN_MIN, TRAIN_MAX = 2017, 2023
CAL_YEAR, TEST_YEAR, SCORE_YEAR = 2024, 2025, 2026
FOLD2025 = ROOT / "reports/m36-foncier/artifacts-m36-fold2025.joblib"

#: colonnes chargées (mêmes que le walk-forward M36 + celles des gates/paliers)
_META = ["idu", "annee", "label", "label_l2", "commune", "secteur", "owner_type",
         "n_mut_nu_36m", "n_mut_bati_36m", "stock_secteur", "window_coverage"]
_RAW = [f.name for f in FEATURES if f.name not in
        ("rot_nu", "rot_bati", "acces_equipements", "dormance_droits")]
_EXTRA = ["pct_potentiel", "dist_ecole_m", "dist_sante_m", "dist_commerce_m",
          "dist_tcsp_m", "nu", "emprise_bati_m2"]
SQL_COLS = list(dict.fromkeys(_META + _RAW + _EXTRA))

PALIERS_TETE = ("Priorité", "À suivre")
SEGMENTS = ("bati_individuel", "terrain_nu", "personne_morale", "copropriete")


def load_range(eng, years: tuple[int, ...]) -> pd.DataFrame:
    """Toutes les années demandées en un SELECT (colonnes du walk-forward), dérivées."""
    cols = ", ".join(SQL_COLS)
    yrs = ", ".join(str(int(y)) for y in years)
    df = pd.read_sql(
        f"SELECT {cols} FROM p_model_ext_dataset WHERE annee IN ({yrs})", eng)
    return derive(df).reset_index(drop=True)


def segmenter(df: pd.DataFrame, copro: np.ndarray) -> pd.Series:
    """Les quatre segments K4 — l'affectation est UNIQUE et prioritaire :
    copro > personne morale (pm/bailleur/public) > terrain nu > bâti individuel."""
    seg = np.where(copro, "copropriete",
          np.where(df["owner_type"].isin(["pm", "bailleur", "public"]),
                   "personne_morale",
          np.where(df["nu"].fillna(False).astype(bool), "terrain_nu",
                   "bati_individuel")))
    return pd.Series(seg, index=df.index)


# ─────────────────────────────── hygiène de la cible (K0.3) ───────────────────────────────

def hygiene(eng, annee: int = TEST_YEAR, horizon_mois: int = 12) -> tuple[pd.DataFrame, dict]:
    """Flags par parcelle vendue dans [01/01/annee, +horizon) : vente groupée +
    vente à un client LABUSE.

    Retourne (flags indexés idu, compte-rendu). `exclue_client` = courrier réellement
    parti OU piste CRM créée AVANT la date de la vente (les courriers `simule` ne sont
    jamais partis : comptés à part, jamais une exclusion).
    """
    fin = f"'{annee}-01-01'::date + interval '{int(horizon_mois)} months'"
    ventes = pd.read_sql(f"""
        SELECT m.idu, min(m.date_mutation) AS date_vente,
               bool_or(g.n_parc > 1)       AS vente_groupee
        FROM p_model_ext_mut_l2 m
        JOIN (SELECT id_mutation, count(DISTINCT idu) AS n_parc
              FROM p_model_ext_mut_l2 WHERE NOT exclue_l2f GROUP BY 1) g USING (id_mutation)
        WHERE NOT m.exclue_l2f
          AND m.date_mutation >= '{annee}-01-01'
          AND m.date_mutation <  {fin}
        GROUP BY 1""", eng).set_index("idu")

    courrier = pd.read_sql(
        "SELECT idu, min(ts) AS premier_envoi, count(*) FILTER (WHERE statut = 'simule') AS n_simule "
        "FROM courrier_envois GROUP BY 1", eng).set_index("idu")
    crm = pd.read_sql(
        "SELECT p.idu, min(pe.created_at) AS premiere_piste "
        "FROM pipeline_entries pe JOIN parcels p ON p.id = pe.parcel_id GROUP BY 1",
        eng).set_index("idu")

    flags = ventes.join(courrier, how="left").join(crm, how="left")
    dv = pd.to_datetime(flags["date_vente"], utc=True)
    envoi_reel = pd.to_datetime(flags["premier_envoi"], utc=True)
    envoi_reel = envoi_reel.where(flags["n_simule"].fillna(0) == 0)  # simulé ≠ parti
    piste = pd.to_datetime(flags["premiere_piste"], utc=True)
    flags["exclue_client"] = ((envoi_reel.notna() & (envoi_reel < dv))
                              | (piste.notna() & (piste < dv)))

    cr = {
        "annee_test": annee, "horizon_mois": horizon_mois,
        "parcelles_vendues": int(len(flags)),
        "parcelles_vente_groupee": int(flags["vente_groupee"].fillna(False).sum()),
        "parcelles_exclues_client_labuse": int(flags["exclue_client"].sum()),
        "courriers_simules_touchant_ventes": int(flags["n_simule"].fillna(0).gt(0).sum()),
        "pistes_crm_posterieures_vente": int((piste.notna() & (piste >= dv)).sum()),
    }
    suffixe = "" if (annee, horizon_mois) == (TEST_YEAR, 12) else f"_{annee}_{horizon_mois}m"
    flags.to_csv(OUT / f"k0_hygiene_flags{suffixe}.csv")
    pd.DataFrame([cr]).to_csv(OUT / f"k0_hygiene{suffixe}.csv", index=False)
    return flags, cr


# ───────────────────────────── contexte d'évaluation partagé ─────────────────────────────

class Contexte:
    """Tout ce qui ne change JAMAIS d'un candidat à l'autre : le jeu de test 2025
    (label + segments + gates statiques servis + exclusions d'hygiène) et les
    scores servis 2026 (churn). Construit UNE fois, réutilisé par tous les lots."""

    def __init__(self, eng, test: pd.DataFrame, score26: pd.DataFrame | None = None,
                 label_col: str = "label", annee_test: int = TEST_YEAR,
                 horizon_mois: int = 12):
        self.eng = eng
        self.test = test.reset_index(drop=True)
        self.copro = measure.copro_mask(eng, self.test)
        self.seg = segmenter(self.test, self.copro)
        self.y = self.test[label_col].astype(int).to_numpy()
        flags, self.hygiene_cr = hygiene(eng, annee_test, horizon_mois)
        self.exclues = set(flags.index[flags["exclue_client"]])
        self.eval_mask = ~self.test["idu"].isin(self.exclues).to_numpy()
        # gates statiques servis (mêmes lectures que le pipeline) — attachés une fois
        self.test["copro"] = self.copro
        measure._attach_gates(eng, self.test)
        # scores servis 2026 hors copro (churn top-1158)
        self.p_servi_26 = pd.read_sql(
            f"SELECT parcelle_id AS idu, p_raw FROM parcel_p_score_v2 "
            f"WHERE run_id = '{SERVED_RUN}' AND NOT copro", eng).set_index("idu")["p_raw"]
        self.score26 = score26.reset_index(drop=True) if score26 is not None else None

    # ---- paliers reconstruits (même mécanique que measure.paliers / la prod) ----
    def paliers(self, p: np.ndarray, contrib_d: np.ndarray) -> pd.Series:
        work = self.test.copy()
        hors = ~work["copro"].to_numpy()
        rang = np.full(len(work), np.nan)
        order = np.argsort(-p[hors])
        rh = np.empty(hors.sum()); rh[order] = np.arange(1, hors.sum() + 1)
        rang[hors] = rh
        work = work.assign(rang=rang, p=p, contrib_d=contrib_d, event_age_mois=np.nan)
        base_params = TierParams(n_entree=1, n_sortie=1)
        elig = work[~work["copro"] & ~work["ecartee_etage0"]
                    & plancher_c(work, base_params)]
        n_e = calibre_n_entree(elig["rang"], cible=1150)
        params = TierParams(n_entree=n_e, n_sortie=int(round(1.4 * n_e)))
        tier = assign_tiers(work, params, None)
        chaudes = work[tier.isin(["chaude", "brulante"])]
        params = calibre_brulante(chaudes, params)
        tier = assign_tiers(work, params, None)
        return tier.map(lambda t: court(t) or t)


def contexte(eng) -> Contexte:
    test = load_range(eng, (TEST_YEAR,))
    score26 = load_range(eng, (SCORE_YEAR,))
    return Contexte(eng, test, score26)


# ─────────────────────────────── la batterie de métriques K0 ───────────────────────────────

def metriques(ctx: Contexte, tag: str, p: np.ndarray,
              contrib_d: np.ndarray | None = None,
              p26: np.ndarray | None = None) -> dict:
    """Toutes les métriques du mandat, sur 2025, précision en haut de liste EN TÊTE.

    p / contrib_d : sur ctx.test (2025). p26 : sur ctx.score26 (2026, churn vs servi).
    contrib_d None → paliers non reconstruits (précisions palier = NaN).
    """
    m = ctx.eval_mask
    y, seg = ctx.y[m], ctx.seg[m].reset_index(drop=True)
    pm_ = p[m]
    hors = ~ctx.copro[m]
    row: dict = {"candidat": tag,
                 "n_eval": int(m.sum()), "n_exclues_client": int((~m).sum())}

    # 1. précision@100 par commune (médiane sur les 24), hors copro
    dcom = pd.DataFrame({"commune": ctx.test["commune"].to_numpy()[m][hors],
                         "p": pm_[hors], "y": y[hors]})
    precs = []
    for com, g in dcom.groupby("commune"):
        k = min(100, len(g))
        top = g.nlargest(k, "p")
        precs.append(top["y"].mean())
    row["prec@100_commune_mediane"] = float(np.median(precs))
    row["n_communes"] = len(precs)

    # 2. précision réelle des paliers de tête reconstruits + effectifs
    if contrib_d is not None:
        palier = ctx.paliers(p, contrib_d)[m].reset_index(drop=True)
        for nom, cle in (("priorite", "Priorité"), ("a_suivre", "À suivre")):
            mask = (palier == cle).to_numpy()
            row[f"n_{nom}"] = int(mask.sum())
            row[f"prec_{nom}"] = float(y[mask].mean()) if mask.any() else float("nan")
    else:
        row.update({"n_priorite": None, "prec_priorite": None,
                    "n_a_suivre": None, "prec_a_suivre": None})

    # 3. lift du décile supérieur, hors copro (tirage seedé 974 pour les égalités)
    k10 = max(1, int(round(hors.sum() * 0.10)))
    row["lift_decile_sup"] = float(ev.rr_at_k(y[hors], pm_[hors], k10)["rr"])

    # 4. AUC global (hors copro, comparable SCORING-1) + par segment
    row["auc_global"] = float(roc_auc_score(y[hors], pm_[hors]))
    for s in SEGMENTS:
        ms = (seg == s).to_numpy()
        row[f"auc_{s}"] = (float(roc_auc_score(y[ms], pm_[ms]))
                           if ms.any() and len(np.unique(y[ms])) > 1 else float("nan"))

    # 5. ECE global (hors copro) + par segment
    row["ece_global"] = float(ev.ece(y[hors], pm_[hors])[0])
    for s in SEGMENTS:
        ms = (seg == s).to_numpy()
        row[f"ece_{s}"] = float(ev.ece(y[ms], pm_[ms])[0]) if ms.any() else float("nan")

    # 6. churn vs le run SERVI q_v11_m137 (top-1158 hors copro, sur 2026)
    if p26 is not None and ctx.score26 is not None:
        hc26 = ~ctx.score26["idu"].isin(
            ctx.test["idu"][ctx.copro]).to_numpy()  # même flag copro (statique)
        cand = pd.Series(p26[hc26], index=ctx.score26["idu"][hc26])
        ch = ev.churn_topk(ctx.p_servi_26, cand, 1158)
        row["churn_top1158_vs_servi"] = float(1.0 - ch["overlap_pct"])
    else:
        row["churn_top1158_vs_servi"] = float("nan")
    return row


def enregistrer(row: dict) -> pd.DataFrame:
    """Ajoute/remplace la ligne du candidat dans LA table unique K0 (upsert par tag)."""
    path = OUT / "k0_table.csv"
    table = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(table):
        table = table[table["candidat"] != row["candidat"]]
    table = pd.concat([table, pd.DataFrame([row])], ignore_index=True)
    table.to_csv(path, index=False)
    return table


# ───────────────────────── entraînement selon LE protocole (les lots) ─────────────────────────

def fit_protocole(df_all: pd.DataFrame, feature_names: list[str],
                  specs=None, interactions: list[tuple[str, str]] | None = None,
                  label_col: str = "label", train_max: int = TRAIN_MAX,
                  cal_year: int = CAL_YEAR, C: float = 5.0,
                  min_count: int = 200, df_encodeur: pd.DataFrame | None = None) -> PModel:
    """Un PModel candidat : binning+fit ≤ train_max, isotonique sur cal_year.

    specs : FeatureSpec des features candidates (celles hors registre servi) —
    l'encodeur est pré-ajusté ici, features.py n'est JAMAIS modifié.
    df_encodeur : lignes sur lesquelles ajuster le DICTIONNAIRE WoE si elles
    diffèrent des lignes de fit (K4 : l'encodeur du segment voit toutes les
    zones, les coefficients restent ajustés hors zone A — sinon la catégorie
    « A » est inconnue au dictionnaire et son WoE vaut 0, neutre, ce qui fait
    remonter artificiellement la zone A au classement).
    """
    train = df_all[(df_all.annee >= TRAIN_MIN) & (df_all.annee <= train_max)
                   & df_all[label_col].notna()].reset_index(drop=True)
    cal = df_all[df_all.annee == cal_year].reset_index(drop=True)
    y_tr = train[label_col].astype(int)

    m = PModel(feature_names=feature_names)
    m.year_dummies = sorted(train.annee.unique())[:-1]
    m.interactions = [(a, b) for a, b in (interactions or [])
                      if a in feature_names and b in feature_names]
    if specs is not None:
        from labuse.scoring.p_model.woe import WoeEncoder
        enc_df = train if df_encodeur is None else df_encodeur[
            (df_encodeur.annee >= TRAIN_MIN) & (df_encodeur.annee <= train_max)
            & df_encodeur[label_col].notna()].reset_index(drop=True)
        m.encoder = WoeEncoder(min_count=min_count).fit(
            enc_df, enc_df[label_col].astype(int), specs)
    m.fit(train, y_tr, C=C, min_count=min_count)
    m.calibrate(cal, cal[label_col].astype(int))
    return m


def contrib_d_de(model: PModel, df: pd.DataFrame,
                 d_features: list[str]) -> np.ndarray:
    """Contribution du bloc D (coef × WoE, comme la prod) — pour le seuil brûlante."""
    contrib = model.contributions(df)
    cols = [c for c in d_features if c in contrib.columns]
    return contrib[cols].sum(axis=1).to_numpy()


# ─────────────────────────────────── ligne de base (K0.4) ───────────────────────────────────

def baseline() -> None:
    """Le modèle actuel mesuré par CE protocole : artefact fold2025 du walk-forward
    (entraîné 2017-2023, isotonique 2024 — exactement K0.1), prédit 2025 et 2026."""
    import joblib
    eng = engine()
    ctx = contexte(eng)
    fold: PModel = joblib.load(FOLD2025)
    assert max(fold.year_dummies) <= TRAIN_MAX, "fold2025 n'est pas le protocole"

    p = fold.predict_proba(ctx.test)
    d_feats = [f.name for f in FEATURES if f.bloc == "D"]
    cd = contrib_d_de(fold, ctx.test, d_feats)
    p26 = fold.predict_proba(ctx.score26)
    row = metriques(ctx, "ligne_de_base", p, cd, p26)
    table = enregistrer(row)
    print(json.dumps(ctx.hygiene_cr, indent=2, ensure_ascii=False))
    print(table.to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    {"baseline": baseline}[cmd]()
