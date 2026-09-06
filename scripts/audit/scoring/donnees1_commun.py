"""SCORING-DONNEES-1 — socle commun des lots A→G (audit, lecture seule).

Banc K0 (protocole.py, inchangé) ; point de départ mandaté = la recette q_v12
(labuse.scoring.p_v2.qv12 : K1c censoring + K2 mortes retirées + K3 résiduel
100 % + K4 bis voisinage GLOBAL + isotonique PAR SEGMENT 2024). Chaque variable
candidate est mesurée SEULE, ajoutée à ce candidat (mandat, règles de mesure).

Doctrine : rien de servi ne change. Lecture seule sur la base ; n'écrit QUE dans
reports/score-v2-arene/donnees1/. q_v11_m137 reste le run servi.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocole  # noqa: E402
from _common import engine, ROOT, SERVED_RUN  # noqa: E402
from labuse.scoring.p_model.features import FeatureSpec  # noqa: E402
from labuse.scoring.p_v2 import qv12  # noqa: E402

OUT = ROOT / "reports/score-v2-arene/donnees1"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / "reports/score-v2-arene/cache"
YEARS = tuple(range(2017, 2027))
_ARENE = "candidat SCORING-DONNEES-1 — arène seulement, jamais servi"

#: seuil de couverture du mandat : « une variable couverte à < 5 % n'est pas
#: candidate (elle peut être notée) »
COUVERTURE_MIN_PCT = 5.0


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ─────────────────────── chargement enrichi q_v12 (cache process) ───────────────────────

_ETAT: dict = {}


def base_enrichie(eng) -> tuple[pd.DataFrame, pd.Series]:
    """Le dataset 2017-2026 enrichi par LA recette q_v12 (caches d'arène
    réutilisés) + la segmentation. Chargé UNE fois par process."""
    if "df" not in _ETAT:
        log("chargement 2017-2026 (p_model_ext_dataset)…")
        df = protocole.load_range(eng, YEARS)
        log("enrichissement recette q_v12 (censoring + résiduel + voisinage)…")
        df = qv12.enrichir(eng, df, YEARS, cache_dir=CACHE)
        copro = qv12.copro_de(eng, df)
        seg = qv12.segmenter(df, copro)
        _ETAT["df"], _ETAT["seg"] = df, seg
    return _ETAT["df"], _ETAT["seg"]


def contexte_partage(eng, df: pd.DataFrame) -> protocole.Contexte:
    """Le Contexte K0 (test 2025 + score 2026), construit UNE fois par process —
    l'hygiène de la cible et les gates statiques ne changent pas d'un candidat
    à l'autre."""
    if "ctx" not in _ETAT:
        _ETAT["ctx"] = protocole.Contexte(
            eng, df[df.annee == protocole.TEST_YEAR],
            df[df.annee == protocole.SCORE_YEAR])
    return _ETAT["ctx"]


# ───────────────────────────── la mesure d'UNE variable ─────────────────────────────

def enregistrer_d1(row: dict) -> pd.DataFrame:
    """Table K0 du mandat DONNEES-1 (upsert par tag) — même format que k0_table."""
    path = OUT / "k0_donnees1.csv"
    table = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(table):
        table = table[table["candidat"] != row["candidat"]]
    table = pd.concat([table, pd.DataFrame([row])], ignore_index=True)
    table.to_csv(path, index=False)
    return table


def mesurer(tag: str, extra_specs: list[FeatureSpec],
            colonnes: pd.DataFrame | None = None,
            remplacees: dict[str, str] | None = None,
            segment_seul: str | None = None,
            fill_false: list[str] | None = None) -> dict:
    """LA mesure du mandat : le candidat q_v12 + les variables d'`extra_specs`,
    ajustées par fit_qv12 (global ≤2023, iso par segment 2024), banc K0 2025.

    colonnes : DataFrame (idu, annee, <variables…>) mergé sur le dataset enrichi
    (les colonnes déjà présentes dans le df de base ne sont pas re-mergées).
    remplacees : {feature_qv12 → candidate} si la variable REMPLACE une feature
    de la recette au lieu de s'y ajouter (les interactions sont remappées).
    segment_seul : si donné (Lot D : 'personne_morale'), les métriques AUC/ECE
    de ce segment font le verdict — le fit reste global (recette q_v12).
    """
    eng = engine()
    df, seg = base_enrichie(eng)
    if colonnes is not None:
        nouvelles = [c for c in colonnes.columns if c not in ("idu", "annee")]
        df = df.drop(columns=[c for c in nouvelles if c in df.columns])
        on = ["idu", "annee"] if "annee" in colonnes.columns else ["idu"]
        df = df.merge(colonnes, on=on, how="left")
        _verifier_alignement(df)
        for c in (fill_false or []):
            df[c] = df[c].fillna(False).astype(bool)
    names, specs, inter = qv12.features_qv12()
    remplacees = remplacees or {}
    names = [remplacees.get(n, n) for n in names]
    names = [n for n in names if n not in {s.name for s in extra_specs}]
    names += [s.name for s in extra_specs]
    by = {s.name: s for s in specs}
    by.update({s.name: s for s in extra_specs})
    specs2 = [by[n] for n in names]
    inter = [(remplacees.get(a, a), remplacees.get(b, b)) for a, b in inter]

    couv = _couverture(df, [s.name for s in extra_specs])
    ctx = contexte_partage(eng, df if colonnes is None else _ETAT["df"])
    # le contexte porte le df de BASE ; les colonnes candidates du test/score26
    # sont reprises du df enrichi (mêmes lignes, merge par idu+annee)
    test, s_test = _sous_ensemble(df, seg, protocole.TEST_YEAR)
    score26, s_26 = _sous_ensemble(df, seg, protocole.SCORE_YEAR)

    log(f"[{tag}] fit qv12 + {[s.name for s in extra_specs]}…")
    m = qv12.fit_qv12(df, seg, names, specs2, inter)
    p = m.predict_proba(test, s_test)
    d_feats = [s.name for s in specs2 if s.bloc == "D"]
    cd = m.contributions(test)[
        [c for c in d_feats if c in m.base.coefs]].sum(axis=1).to_numpy()
    p26 = m.predict_proba(score26, s_26)
    row = protocole.metriques(ctx, tag, p, cd, p26)
    row["couverture_pct"] = couv
    if segment_seul:
        row["segment_verdict"] = segment_seul
    coefs = {s.name: float(m.base.coefs.get(s.name, float("nan")))
             for s in extra_specs}
    row["coefs_candidates"] = json.dumps(coefs, ensure_ascii=False)
    _ETAT["modele"], _ETAT["df_mesure"] = m, df  # pour le top-50 (Lot G)
    table = enregistrer_d1(row)
    log(f"[{tag}] terminé — AUC {row['auc_global']:.4f}, "
        f"préc@100 {row['prec@100_commune_mediane']:.3f}, "
        f"lift {row['lift_decile_sup']:.2f}")
    print(table[["candidat", "prec@100_commune_mediane", "lift_decile_sup",
                 "auc_global", "auc_personne_morale", "ece_global"]]
          .to_string(index=False))
    return row


def _sous_ensemble(df: pd.DataFrame, seg: pd.Series, annee: int):
    mask = (df.annee == annee).to_numpy()
    return (df[mask].reset_index(drop=True),
            seg[mask].reset_index(drop=True))


def _verifier_alignement(df: pd.DataFrame) -> None:
    assert len(df) == len(_ETAT["df"]), \
        f"merge candidate a changé le nombre de lignes ({len(df)} vs {len(_ETAT['df'])})"


def _couverture(df: pd.DataFrame, noms: list[str]) -> float:
    """% non-nul des candidates sur l'année scorée (2026) — règle des 5 %."""
    y26 = df[df.annee == 2026]
    couv = [100 * y26[n].notna().mean() for n in noms if n in y26.columns]
    if not len(y26) or not couv:
        return 100.0
    return float(min(couv))


def baseline() -> None:
    """La colonne de base du tableau unique : q_v12 refit ICI (mêmes chiffres
    attendus que la ligne q_v12 de k0_table.csv — contrôle de reproduction)."""
    row = mesurer("q_v12_base", [])
    ref = pd.read_csv(ROOT / "reports/score-v2-arene/k0_table.csv")
    ref = ref[ref.candidat == "q_v12"].iloc[0]
    ecart = abs(row["auc_global"] - float(ref["auc_global"]))
    print(f"reproduction vs k0_table q_v12 : ΔAUC = {ecart:.5f}")


if __name__ == "__main__":
    baseline()
