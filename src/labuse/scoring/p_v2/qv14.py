"""SCORING-4 · recette q_v14 — les deux améliorations combinées, jamais réunies.

q_v14 porte EN MÊME TEMPS :
  - les gains de MODÈLE de q_v12 (jamais servis) : K1c censoring + K2 mortes
    retirées + K3 résiduel 100 % + K4 bis voisinage GLOBAL + isotonique PAR
    SEGMENT (2024). Toute la recette q_v12 est reprise telle quelle (module
    `qv12`, SOURCE unique — features, enrichissement, fit, ModeleQv12) ;
  - les gains de DONNÉES prouvés par SCORING-DONNÉES-1, chacun as-of :
      · nu_constructible_asof  (remplace nu_constructible_v3)      — bâti/nu
        reconstruit à la date de la ligne (Sitadel + DVF) ;
      · pct_bati_secteur_asof  (remplace pct_bati_secteur)         — part bâtie
        du secteur, reconstruite à la date ;
      · pc_pm_sur_parcelle_pp_36m (ajout)                          — permis
        déposé par un professionnel (SIREN) sur une parcelle détenue par un
        particulier ;
      · anciennete_plu_annees  (ajout)                             — ancienneté
        du PLU de la commune ;
      · ventes_pm_secteur_36m  (ajout CONDITIONNEL)                — part des
        ventes du secteur parties à des sociétés ; ne rentre QUE si l'ECE du
        segment PM ne se dégrade pas de plus de 0,01 (garde-fou du mandat —
        SCORING-DONNÉES-1 Lot D : meilleur lift mais ECE PM fragile).

Les DONNÉES DU JOUR et la cascade de q_v13_sources1 (dont les 4 378 exclusions
neuves) entrent au RUN, pas dans le modèle : la cascade est ORTHOGONALE aux
features (SOURCES-1 ne change QUE la cascade, pas le modèle P — cf.
docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md §363-364). Le run q_v14 réutilise cet
étage 0 via `LABUSE_ETAGE0_RUN=q_v13_sources1` (pipeline M8a), sans rejeu.

Ce module est LA source unique de la recette q_v14 : l'arène
(`scripts/audit/scoring/q_v14_arene.py`) fit/mesure/gèle avec CE code ; le
pipeline réel (`p_v2.pipeline`, recette="q_v14") score avec CE code et
l'artefact GELÉ ici (sha256 au manifeste, refus si mismatch — doctrine m36/q_v12).

Doctrine : le run candidat est CALCULÉ, jamais basculé — `q_v11_m137` reste
servi ; la bascule est un geste de Vic (`golden promote`).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..p_model.features import FeatureSpec
from . import qv12

ROOT = Path(__file__).resolve().parents[4]

QV14_VERSION = "q_v14"
QV14_DIR = ROOT / "reports/q-v14"
QV14_ARTIFACT_12M = QV14_DIR / "artifacts-q_v14-12m.joblib"
QV14_ARTIFACT_24M = QV14_DIR / "artifacts-q_v14-24m.joblib"
QV14_FREEZE = QV14_DIR / "FREEZE-q_v14.json"

# protocole identique à q_v12 (banc K0 gravé)
TRAIN_MIN, TRAIN_MAX, CAL_YEAR = qv12.TRAIN_MIN, qv12.TRAIN_MAX, qv12.CAL_YEAR
TRAIN_MAX_24M, CAL_YEAR_24M = qv12.TRAIN_MAX_24M, qv12.CAL_YEAR_24M
SEGMENTS = qv12.SEGMENTS
MILL_MIN, MILL_MAX = 2019, 2024  # pm_proprietaires_millesimes

_SRC = ("recette q_v14 (SCORING-4) — q_v12 + variables as-of prouvées "
        "SCORING-DONNÉES-1 ; calculée par le pipeline réel, jamais basculée sans geste Vic")

#: les variables de DONNÉES qui remplacent une feature q_v12 (état 2026 → as-of).
REMPLACEES_QV14 = {"nu_constructible_v3": "nu_constructible_asof",
                   "pct_bati_secteur": "pct_bati_secteur_asof"}

# ─────────────────────────── specs des variables neuves ───────────────────────────
# Reprises À L'IDENTIQUE des specs mesurées au banc K0 par SCORING-DONNÉES-1
# (donnees1_a/c/d/e) — mêmes preuves, mêmes fenêtres as-of.

SPEC_NU_ASOF = FeatureSpec(
    "nu_constructible_asof", "D", "cat", 0,
    "bâti/nu RECONSTRUIT à l'état physique du 01/01/Y : Sitadel (1er PC autorisé, "
    "achèvement) + DVF (mutations nues/bâties datées) ; catégories bati / nu_droits "
    "(zone U-AU) / nu_sans_droits (A-N) / nu_non_calcule — remplace nu_constructible_v3",
    "as-of 01/01/Y (reconstruction)", _SRC,
    "la zone reste le zonage servi ; le flip ne porte que sur l'état bâti/nu")
SPEC_PCT_BATI_ASOF = FeatureSpec(
    "pct_bati_secteur_asof", "Z", "num", 0,
    "part de parcelles bâties du secteur, RECONSTRUITE au 01/01/Y (mêmes preuves "
    "que nu_constructible_asof) — remplace pct_bati_secteur (état 2026)",
    "as-of 01/01/Y (reconstruction)", _SRC)
SPEC_PC_PM = FeatureSpec(
    "pc_pm_sur_parcelle_pp_36m", "D", "bool", 0,
    "PC autorisé dans les 36 mois avant asof dont le demandeur porte un SIREN "
    "(personne morale), sur une parcelle dont le propriétaire est un particulier "
    "(owner_type='pp') — le promoteur sous compromis",
    "as-of 01/01/Y (demandeur) × statique (propriétaire)", _SRC)
SPEC_ANC_PLU = FeatureSpec(
    "anciennete_plu_annees", "Z", "num", 0,
    "années écoulées au 01/01/Y depuis l'approbation du PLU de la commune "
    "(sudocuh_procedures.approbation_opp) ; PLU approuvé APRÈS asof → manquant "
    "explicite", "as-of 01/01/Y", _SRC,
    "un PLU jeune ouvre des zones : signal d'offre nouvelle")
SPEC_VENTES_PM = FeatureSpec(
    "ventes_pm_secteur_36m", "Z", "num", 0,
    "part des ventes L2-F du secteur, 36 mois avant asof, parties vers un "
    "acquéreur PM (mutation suivie d'une entrée au millésime PM suivant)",
    "as-of 01/01/Y", _SRC,
    "CONDITIONNELLE : gardée seulement si l'ECE du segment PM ne se dégrade pas > 0,01")

SPECS_QV14 = [SPEC_NU_ASOF, SPEC_PCT_BATI_ASOF, SPEC_PC_PM, SPEC_ANC_PLU, SPEC_VENTES_PM]

#: libellés français des variables neuves (top-5 lisible de la fiche « Analyse LABUSE »).
LIBELLES_QV14 = {
    **qv12.LIBELLES_QV12,
    "nu_constructible_asof": "terrain nu constructible",
    "pct_bati_secteur_asof": "secteur peu bâti",
    "pc_pm_sur_parcelle_pp_36m": "un professionnel a déposé un permis sur cette "
                                 "parcelle détenue par un particulier",
    "anciennete_plu_annees": "ancienneté du PLU de la commune",
    "ventes_pm_secteur_36m": "part des ventes du secteur parties à des sociétés",
}


def features_qv14(avec_ventes_pm: bool = True
                  ) -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    """Features de q_v14 = chaîne q_v12, deux remplacements as-of + trois ajouts.

    `avec_ventes_pm` : ventes_pm_secteur_36m n'entre que si le garde-fou ECE PM
    l'autorise (décidé à l'arène ; le nom des features de l'artefact gelé fait foi
    au run — le pipeline lit m.base.feature_names)."""
    names, specs, inter = qv12.features_qv12()
    by = {s.name: s for s in specs}
    by.update({s.name: s for s in SPECS_QV14})

    # deux remplacements : nu_constructible_v3 → asof, pct_bati_secteur → asof
    names = [REMPLACEES_QV14.get(n, n) for n in names]
    inter = [(REMPLACEES_QV14.get(a, a), REMPLACEES_QV14.get(b, b)) for a, b in inter]

    # trois ajouts (le 3e conditionnel)
    ajouts = ["pc_pm_sur_parcelle_pp_36m", "anciennete_plu_annees"]
    if avec_ventes_pm:
        ajouts.append("ventes_pm_secteur_36m")
    for n in ajouts:
        if n not in names:
            names.append(n)

    specs_out = [by[n] for n in names]
    inter = [(a, b) for a, b in inter if a in names and b in names]
    return names, specs_out, inter


# ─────────────────────────── constructeurs de colonnes as-of ───────────────────────────
# Portés À L'IDENTIQUE de scripts/audit/scoring/donnees1_a/c/d/e (mêmes requêtes,
# mêmes règles de reconstruction), paramétrés par années pour la production.

_SQL_EVIDENCE_A = """
SELECT st.idu, (st.emprise_bati_m2 > 20) AS batie_2026,
       prem.prem_pc_auto, mb.prem_mut_batie
FROM p_model_static st
LEFT JOIN (
  SELECT pp.idu, min(pp.date_autorisation) AS prem_pc_auto
  FROM p_model_permits pp WHERE pp.type = 'PC' GROUP BY 1) prem ON prem.idu = st.idu
LEFT JOIN (SELECT idu, min(date_mutation) AS prem_mut_batie
           FROM p_model_ext_mut_l2 WHERE bati GROUP BY 1) mb ON mb.idu = st.idu
"""


def _nu_asof_grille(conn, years) -> pd.DataFrame:
    """(idu, annee, nu_asof) — état PHYSIQUE bâti/nu au 01/01/Y reconstruit
    depuis des événements datés antérieurs (règles conservatrices, cf. Lot A3)."""
    ev = pd.read_sql(_SQL_EVIDENCE_A, conn)
    for c in ("prem_pc_auto", "prem_mut_batie"):
        ev[c] = pd.to_datetime(ev[c])
    batie26 = ev["batie_2026"].fillna(False).to_numpy()
    frames = []
    for y in years:
        asof = pd.Timestamp(f"{y}-01-01")
        flip_vers_nu = (batie26
                        & ev["prem_pc_auto"].notna().to_numpy()
                        & (ev["prem_pc_auto"] >= asof).to_numpy()
                        & ~(ev["prem_mut_batie"] < asof).to_numpy())
        flip_vers_bati = (~batie26 & (ev["prem_mut_batie"] >= asof).to_numpy())
        nu_asof = np.where(flip_vers_nu, True,
                  np.where(flip_vers_bati, False, ~batie26))
        frames.append(pd.DataFrame({"idu": ev["idu"], "annee": y, "nu_asof": nu_asof}))
    return pd.concat(frames, ignore_index=True)


def _colonnes_a(conn, years) -> pd.DataFrame:
    """nu_constructible_asof (cat) + pct_bati_secteur_asof (agrégat secteur)."""
    g = _nu_asof_grille(conn, years)
    zone = pd.read_sql(
        "SELECT idu, st.zone_plu, f.secteur FROM p_model_static st "
        "JOIN p_model_frame f USING (idu)", conn)
    g = g.merge(zone, on="idu", how="left")
    z = g["zone_plu"].fillna("inconnu")
    g["nu_constructible_asof"] = np.select(
        [~g["nu_asof"], z.isin(["U", "AU"]), z == "inconnu"],
        ["bati", "nu_droits", "nu_non_calcule"], default="nu_sans_droits")
    sect = (g.groupby(["secteur", "annee"])["nu_asof"]
            .agg(lambda s: 1.0 - s.mean()).rename("pct_bati_secteur_asof")
            .reset_index())
    g = g.merge(sect, on=["secteur", "annee"], how="left")
    return g[["idu", "annee", "nu_constructible_asof", "pct_bati_secteur_asof"]]


def _colonnes_pc_pm(conn, years) -> pd.DataFrame:
    """(idu, annee, pc_pm_36m_brut) — PC à demandeur SIREN dans les 36 mois."""
    pcpm = pd.read_sql("""
        SELECT pp.idu, pp.date_autorisation
        FROM p_model_permits pp
        JOIN sitadel_permits s ON s.permit_id = pp.permit_id
        WHERE pp.type = 'PC' AND coalesce(s.raw->>'petitioner_siren','') <> ''""", conn)
    pcpm["date_autorisation"] = pd.to_datetime(pcpm["date_autorisation"])
    frames = []
    for y in years:
        asof = pd.Timestamp(f"{y}-01-01")
        deb = asof - pd.DateOffset(months=36)
        w_pm = pcpm[(pcpm.date_autorisation >= deb)
                    & (pcpm.date_autorisation < asof)]["idu"].unique()
        frames.append(pd.DataFrame({"idu": pd.Index(w_pm, name="idu"), "annee": y,
                                    "pc_pm_36m_brut": True}))
    if not frames:
        return pd.DataFrame(columns=["idu", "annee", "pc_pm_36m_brut"])
    return pd.concat(frames, ignore_index=True)


def _colonnes_anc_plu(conn, df) -> pd.DataFrame:
    """(idu, annee, anciennete_plu_annees) — années depuis l'approbation du PLU."""
    sud = pd.read_sql(
        "SELECT insee, approbation_opp FROM sudocuh_procedures "
        "WHERE approbation_opp IS NOT NULL", conn)
    cols = df[["idu", "annee"]].copy()
    cols["insee"] = cols["idu"].str.slice(0, 5)
    cols = cols.merge(sud, on="insee", how="left")
    asof = pd.to_datetime(cols["annee"].astype(str) + "-01-01")
    anc = (asof - pd.to_datetime(cols["approbation_opp"])).dt.days / 365.25
    cols["anciennete_plu_annees"] = anc.where(anc >= 0)
    return cols[["idu", "annee", "anciennete_plu_annees"]]


def _ventes_pm_secteur(conn, years) -> pd.DataFrame:
    """(secteur, annee, ventes_pm_secteur_36m) — part des ventes vers un
    acquéreur PM (entrée au millésime PM suivant la vente)."""
    mut = pd.read_sql("""
        SELECT m.idu, m.date_mutation, f.secteur
        FROM p_model_ext_mut_l2 m JOIN p_model_frame f ON f.idu = m.idu
        WHERE NOT m.exclue_l2f""", conn)
    mut["date_mutation"] = pd.to_datetime(mut["date_mutation"])
    mut["annee_mut"] = mut["date_mutation"].dt.year
    pm = pd.read_sql(
        "SELECT idu, millesime, siren FROM pm_proprietaires_millesimes "
        "WHERE siren IS NOT NULL", conn)
    sirens_par_mill = {m: dict(g[["idu", "siren"]].values)
                       for m, g in pm.groupby("millesime")}

    def vers_pm(idu: str, annee_mut: int) -> float:
        ap = annee_mut + 1
        if ap < MILL_MIN + 1 or ap > MILL_MAX:
            return np.nan
        s_apres = sirens_par_mill.get(ap, {}).get(idu)
        if s_apres is None:
            return 0.0
        s_avant = sirens_par_mill.get(min(max(annee_mut, MILL_MIN), MILL_MAX), {}).get(idu)
        return 1.0 if s_apres != s_avant else 0.0

    mut["vers_pm"] = [vers_pm(i, a) for i, a in zip(mut["idu"], mut["annee_mut"])]
    frames = []
    for y in years:
        a = pd.Timestamp(f"{y}-01-01")
        w = mut[(mut.date_mutation >= a - pd.DateOffset(months=36))
                & (mut.date_mutation < a)]
        agg = (w.groupby("secteur")["vers_pm"].mean()
               .rename("ventes_pm_secteur_36m").reset_index().assign(annee=y))
        frames.append(agg)
    return pd.concat(frames, ignore_index=True)


def enrichir(eng, df: pd.DataFrame, years, cache_dir: Path | None = None) -> pd.DataFrame:
    """Toutes les features de q_v14 : d'abord la recette q_v12 (censoring +
    résiduel + voisinage), puis les 5 variables as-of de SCORING-DONNÉES-1.
    `cache_dir` : caches d'arène (calcul spatial long) — None en production."""
    df = qv12.enrichir(eng, df, years, cache_dir=cache_dir)

    a = _colonnes_a(eng, years)
    df = df.drop(columns=[c for c in ("nu_constructible_asof", "pct_bati_secteur_asof")
                          if c in df.columns])
    df = df.merge(a, on=["idu", "annee"], how="left")

    pcpm = _colonnes_pc_pm(eng, years)
    df = df.merge(pcpm, on=["idu", "annee"], how="left")
    est_pp = df["owner_type"].fillna("pp") == "pp"
    df["pc_pm_sur_parcelle_pp_36m"] = (df["pc_pm_36m_brut"].fillna(False).astype(bool)
                                       & est_pp)
    df = df.drop(columns=["pc_pm_36m_brut"])

    anc = _colonnes_anc_plu(eng, df)
    df = df.drop(columns=[c for c in ["anciennete_plu_annees"] if c in df.columns])
    df = df.merge(anc, on=["idu", "annee"], how="left")

    sec = _ventes_pm_secteur(eng, years)
    frame = pd.read_sql("SELECT idu, secteur FROM p_model_frame", eng)
    vpm = df[["idu", "annee"]].merge(frame, on="idu", how="left").merge(
        sec, on=["secteur", "annee"], how="left")
    df = df.drop(columns=[c for c in ["ventes_pm_secteur_36m"] if c in df.columns])
    df = df.merge(vpm[["idu", "annee", "ventes_pm_secteur_36m"]],
                  on=["idu", "annee"], how="left")
    return df


# le modèle q_v14 EST le modèle q_v12 (fit global + isotonique par segment) —
# seule change la liste de features. On réutilise la mécanique telle quelle.
ModeleQv14 = qv12.ModeleQv12
segmenter = qv12.segmenter
copro_de = qv12.copro_de


def fit_qv14(df_all, seg_all, names, specs, inter, **kw):
    """Alias de qv12.fit_qv12 (ModeleQv12 : fit GLOBAL ≤ train_max + isotonique
    PAR SEGMENT sur cal_year) — la recette q_v14 ne change QUE les features."""
    return qv12.fit_qv12(df_all, seg_all, names, specs, inter, **kw)


# ─────────────────────────── artefacts gelés (doctrine m36/q_v12) ───────────────────────────

def verify_artifacts():
    """Charge les DEUX artefacts gelés (12 et 24 mois) et REFUSE tout mismatch
    sha256 avec FREEZE-q_v14.json — même doctrine que m36/q_v12."""
    import joblib
    freeze = json.loads(QV14_FREEZE.read_text())
    for path, cle in ((QV14_ARTIFACT_12M, "sha256_12m"),
                      (QV14_ARTIFACT_24M, "sha256_24m")):
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if sha != freeze[cle]:
            raise RuntimeError(
                f"REFUS : sha256 de {Path(path).name} ({sha[:16]}…) ≠ manifeste "
                f"({freeze[cle][:16]}…) — l'artefact gelé q_v14 seul fait foi.")
    return (joblib.load(QV14_ARTIFACT_12M), joblib.load(QV14_ARTIFACT_24M), freeze)


def geler_artifacts(m12, m24, manifeste: dict) -> dict:
    """Écrit les artefacts + le manifeste de gel (sha256). Utilisé par l'arène —
    jamais par le pipeline, qui ne fait que LIRE."""
    import joblib
    QV14_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(m12, QV14_ARTIFACT_12M)
    joblib.dump(m24, QV14_ARTIFACT_24M)
    manifeste = dict(manifeste)
    manifeste["sha256_12m"] = hashlib.sha256(QV14_ARTIFACT_12M.read_bytes()).hexdigest()
    manifeste["sha256_24m"] = hashlib.sha256(QV14_ARTIFACT_24M.read_bytes()).hexdigest()
    QV14_FREEZE.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2,
                                      default=str), encoding="utf-8")
    return manifeste
