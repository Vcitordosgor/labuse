"""SCORING-3 · L1 — la recette q_v12 : les gains sûrs de SCORING-2, rien d'autre.

Recette EXACTEMENT ce que l'arène a validé (COMPTE-RENDU-SCORING-2) :
  - censoring K1 (variante c) : `tenure_bin_v2` catégorielle censurée fine
    ({<1,1-2,2-3,3-5,5-8,8+,censure}) — couverture 100 % par construction ;
  - K2 : 4 variables mortes (ndvi, canopée, accès équipements, friche)
    + 5 `retired` M35 hors du fit — le vrai gain (AUC 0,613 → 0,626) ;
  - K3 : `parcel_residuel` lu EN ENTIER (0 = réponse du moteur, cause explicite ;
    `hors_plu` seul réellement inconnaissable → manquant WoE) ;
  - K4 bis variante GLOBALE : voisinage et marché as-of (fuite zéro, testée) —
    la meilleure tête du tableau (préc@100 0,075, lift 2,11) ;
  - calibration : isotonique PAR SEGMENT sur 2024 (le seul apport de K4 retenu —
    le fit reste GLOBAL, les fits segmentés perdent la discrimination) ;
  - horizon : 12 mois servi (p_raw), 24 mois calculé et stocké (p_24m).

Ce module est LA source unique de la recette : l'arène
(`scripts/audit/scoring/q_v12_arene.py`) fit et mesure au banc K0 avec CE code ;
le pipeline réel (`p_v2.pipeline`, recette="q_v12") score avec CE code et
l'artefact GELÉ ici (sha256 au manifeste, refus si mismatch — même doctrine que
m36). La coïncidence run réel / arène est vérifiée sur 1 000 parcelles (L1.2).

Doctrine : le run candidat est CALCULÉ, jamais basculé — `q_v11_m137` reste
servi ; la bascule est un geste de Vic (Données › Circuit › Basculer).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from ..p_model.features import FEATURES, FeatureSpec
from ..p_model.model import PModel
from ..p_model.woe import WoeEncoder

ROOT = Path(__file__).resolve().parents[4]

QV12_VERSION = "q_v12"
QV12_DIR = ROOT / "reports/q-v12"
QV12_ARTIFACT_12M = QV12_DIR / "artifacts-q_v12-12m.joblib"
QV12_ARTIFACT_24M = QV12_DIR / "artifacts-q_v12-24m.joblib"
QV12_FREEZE = QV12_DIR / "FREEZE-q_v12.json"

FOLD2025 = ROOT / "reports/m36-foncier/artifacts-m36-fold2025.joblib"

#: protocole du banc K0 (SCORING-2), gravé — l'artefact 12 mois EST ce protocole.
TRAIN_MIN, TRAIN_MAX, CAL_YEAR = 2017, 2023, 2024
#: protocole 24 mois (K1 bis) : seule fenêtre complète, DVF s'arrêtant au 31/12/2025.
TRAIN_MAX_24M, CAL_YEAR_24M = 2022, 2023

SEGMENTS = ("bati_individuel", "terrain_nu", "personne_morale", "copropriete")

_ARENE = "recette q_v12 (SCORING-3 L1) — calculée par le pipeline réel, jamais basculée sans geste Vic"

# ───────────────── chaîne des retraits/remplacements (verdicts SCORING-2) ─────────────────

#: K1 (variante c retenue) — bins servis remplacés par leur version censurée.
REMPLACEES_K1 = {"tenure_bin": "tenure_bin_v2", "nu_constructible": "nu_constructible_v2"}
#: K2 — mortes au mandat (Δauc ≤ 0 mesuré SCORING-1 B.2) + doctrine M35.
MORTES_K2 = ("ndvi_moyen", "canopee_pct", "acces_equipements", "friche")
RETIREES_M35 = tuple(f.name for f in FEATURES if f.retired)
#: K3 — remplacées par la lecture 100 % du résiduel.
REMPLACEES_K3 = ("sdp_residuelle_m2", "sous_densite", "nu_constructible_v2")
REMAP_K3 = {"sdp_residuelle_m2": "sdp_residuelle_v2_m2",
            "sous_densite": "sous_densite_v2",
            "nu_constructible_v2": "nu_constructible_v3"}

SPECS_CENSORING = [
    FeatureSpec("tenure_bin_v2", "D", "cat", 0,
                "détention CATÉGORIELLE enrichie (K1 variante c retenue) : "
                "{<1, 1-2, 2-3, 3-5, 5-8, 8+} sur les mutations connues (DVF 2014+) "
                "+ « censure » explicite = aucune mutation depuis le début de "
                "l'historique de la commune (≥ N ans)", "as-of 01/01/Y", _ARENE,
                "couverture 100 % (valeur ou censure, jamais un inconnu muet)"),
    FeatureSpec("nu_constructible_v2", "D", "cat", 0,
                "BD TOPO × zone PLU, désambiguïsé : nu_constructible (U/AU) / "
                "nu_zone_fermee (A/N) / nu_zone_inconnue (non calculé) / bati — "
                "remplacé par nu_constructible_v3 dès K3", "statique", _ARENE),
]

SPECS_RESIDUEL = [
    FeatureSpec("sdp_residuelle_v2_m2", "D", "num", 0,
                "parcel_residuel M125 lu EN ENTIER : cause NULL → valeur calculée ; "
                "zone_non_constructible / terrain_exigu / zone_non_resolue / "
                "habitat_interdit / redhibitoire → 0 (la réponse du moteur, pas un "
                "doute) ; hors_plu → manquant EXPLICITE (réellement inconnaissable)",
                "statique", _ARENE, "couverture ~99 % (K3)"),
    FeatureSpec("sous_densite_v2", "D", "bool", 0,
                "parcel_residuel.sous_densite ; parcelles à 0 droit → False (pas de "
                "potentiel, donc pas « sous-dense »)", "statique", _ARENE),
    FeatureSpec("residuel_famille", "D", "cat", 0,
                "famille de cause du résiduel (calculee / zone_non_constructible / "
                "terrain_exigu / zone_non_resolue / habitat_interdit / redhibitoire "
                "/ hors_plu)", "statique", _ARENE),
    FeatureSpec("nu_constructible_v3", "D", "cat", 0,
                "désambiguïsé PAR le résiduel : bati / nu_droits (SDP v2 > 0) / "
                "nu_sans_droits (SDP v2 = 0) / nu_non_calcule (hors_plu)",
                "statique", _ARENE),
]

SPECS_VOISINAGE = [
    FeatureSpec("ventes_150m_12m", "Z", "num", +1,
                "DVF L2-F dans 150 m (bord à bord), 12 mois avant asof",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("ventes_150m_24m", "Z", "num", +1,
                "DVF L2-F dans 150 m, 24 mois", "as-of 01/01/Y", _ARENE),
    FeatureSpec("ventes_400m_12m", "Z", "num", +1,
                "DVF L2-F dans 400 m, 12 mois", "as-of 01/01/Y", _ARENE),
    FeatureSpec("ventes_400m_24m", "Z", "num", +1,
                "DVF L2-F dans 400 m, 24 mois", "as-of 01/01/Y", _ARENE),
    FeatureSpec("ventes_400m_delta", "Z", "num", 0,
                "accélération : n_12m − (n_24m − n_12m) dans 400 m",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("permis_100m_24m", "Z", "num", 0,
                "permis Sitadel dans 100 m, 24 mois", "as-of 01/01/Y", _ARENE),
    FeatureSpec("operations_pa_400m_24m", "Z", "num", 0,
                "opérations d'aménageur : permis PA dans 400 m, 24 mois",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("volume_commune_a1", "Z", "num", 0,
                "volume de mutations L2-F de la commune, année Y-1",
                "année civile Y-1", _ARENE),
    FeatureSpec("med_pm2_commune_a1", "Z", "num", 0,
                "médiane €/m² bâti de la commune, année Y-1", "année Y-1", _ARENE),
    FeatureSpec("tendance_volume_3ans", "Z", "num", 0,
                "volume Y-1 / moyenne des volumes Y-3..Y-1 (commune)",
                "années Y-3..Y-1", _ARENE),
    FeatureSpec("pm_vendeur_actif", "D", "bool", 0,
                "personne morale : le propriétaire (SIREN, millésime ≤ Y-1) a vendu "
                "une AUTRE parcelle dans les 24 mois ; non-PM → False ; avant 2021 "
                "(millésimes indisponibles) → manquant explicite",
                "as-of 01/01/Y", _ARENE),
]

#: libellés français des features candidates (top 5 contributions lisibles).
LIBELLES_QV12 = {
    "tenure_bin_v2": "ancienneté de la dernière mutation (censure explicite)",
    "nu_constructible_v2": "nu constructible (zone PLU)",
    "nu_constructible_v3": "nu constructible (résiduel)",
    "sdp_residuelle_v2_m2": "SDP résiduelle (lecture complète)",
    "sous_densite_v2": "sous-densité",
    "residuel_famille": "cause du résiduel",
    "ventes_150m_12m": "ventes à 150 m (12 mois)",
    "ventes_150m_24m": "ventes à 150 m (24 mois)",
    "ventes_400m_12m": "ventes à 400 m (12 mois)",
    "ventes_400m_24m": "ventes à 400 m (24 mois)",
    "ventes_400m_delta": "accélération des ventes à 400 m",
    "permis_100m_24m": "permis à 100 m (24 mois)",
    "operations_pa_400m_24m": "opérations d'aménageur à 400 m",
    "volume_commune_a1": "volume de ventes de la commune (Y-1)",
    "med_pm2_commune_a1": "prix médian €/m² bâti de la commune (Y-1)",
    "tendance_volume_3ans": "tendance du volume communal (3 ans)",
    "pm_vendeur_actif": "personne morale vendeuse récente",
}


def features_qv12() -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    """La liste de features du candidat q_v12 — chaîne K1c → K2 → K3 → K4 bis,
    reproduite depuis les verdicts SCORING-2 (candidats.features_k4bis)."""
    # K1 : bins censurés remplacent tenure_bin / nu_constructible
    names = [f.name for f in FEATURES if f.name not in REMPLACEES_K1]
    names += ["tenure_bin_v2", "nu_constructible_v2"]
    # K2 : mortes + retired hors du fit
    hors = set(MORTES_K2) | set(RETIREES_M35)
    names = [n for n in names if n not in hors]
    # K3 : lecture 100 % du résiduel
    names = [n for n in names if n not in REMPLACEES_K3]
    names += [s.name for s in SPECS_RESIDUEL]
    # K4 bis : voisinage et marché
    names += [s.name for s in SPECS_VOISINAGE]

    by = {f.name: f for f in FEATURES}
    by.update({s.name: s for s in SPECS_CENSORING + SPECS_RESIDUEL + SPECS_VOISINAGE})
    specs = [by[n] for n in names]

    # interactions : les 5 croisements minés du walk-forward M36, reportés sur les
    # features candidates de même sémantique (le minage n'est pas refait), pairs
    # touchant une feature retirée exclues.
    import joblib
    fold = joblib.load(FOLD2025)
    inter = [(REMPLACEES_K1.get(a, a), REMPLACEES_K1.get(b, b))
             for a, b in fold.interactions]
    inter = [(a, b) for a, b in inter if a not in hors and b not in hors]
    inter = [(REMAP_K3.get(a, a), REMAP_K3.get(b, b)) for a, b in inter]
    inter = [(a, b) for a, b in inter if a in names and b in names]
    return names, specs, inter


# ─────────────────────────── enrichissement (features candidates) ───────────────────────────
# Code REPRIS de l'arène SCORING-2 (scripts/audit/scoring/{candidats,voisinage}.py),
# paramétré par années — sémantique inchangée, vérifiée par la coïncidence L1.2.

def charger_censoring(eng, years: tuple[int, ...]) -> pd.DataFrame:
    """Dernière mutation / dernier permis par (idu, annee), as-of 01/01/annee."""
    yrs = f"generate_series({min(years)}, {max(years)})"
    t = pd.read_sql(f"""
        WITH win AS (SELECT annee, make_date(annee,1,1) AS asof FROM {yrs} AS g(annee))
        SELECT ma.idu, w.annee, max(ma.date_mutation) AS derniere_mutation
        FROM p_model_ext_mut_all ma JOIN win w ON ma.date_mutation < w.asof
        GROUP BY 1, 2""", eng)
    p = pd.read_sql(f"""
        WITH win AS (SELECT annee, make_date(annee,1,1) AS asof FROM {yrs} AS g(annee))
        SELECT pp.idu, w.annee, max(pp.date_autorisation) AS dernier_permis
        FROM p_model_permits pp JOIN win w ON pp.date_autorisation < w.asof
        GROUP BY 1, 2""", eng)
    hist = pd.read_sql(
        "SELECT left(idu, 5) AS commune, min(date_mutation) AS debut_histo "
        "FROM p_model_ext_mut_all GROUP BY 1", eng)
    out = t.merge(p, on=["idu", "annee"], how="outer")
    out["commune"] = out["idu"].str.slice(0, 5)
    out = out.merge(hist, on="commune", how="left")
    return out.drop(columns=["commune"])


def appliquer_censoring(df: pd.DataFrame, cens: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(cens, on=["idu", "annee"], how="left")
    asof = pd.to_datetime(df["annee"].astype(str) + "-01-01")
    derniere = pd.to_datetime(df["derniere_mutation"])
    tenure = (asof - derniere).dt.days / 365.25
    df["tenure_censuree"] = derniere.isna()
    df["tenure_annees"] = tenure
    bins = pd.cut(tenure, [-0.001, 1, 2, 3, 5, 8, np.inf],
                  labels=["<1", "1-2", "2-3", "3-5", "5-8", "8+"])
    df["tenure_bin_v2"] = pd.Series(bins.astype(str), index=df.index).where(
        derniere.notna(), "censure")
    dernier_p = pd.to_datetime(df["dernier_permis"])
    df["permis_jamais"] = dernier_p.isna()
    df["permis_anciennete_annees"] = (asof - dernier_p).dt.days / 365.25
    nu = df["nu"].fillna(False).astype(bool)
    zone = df["zone_plu"].fillna("inconnu")
    df["nu_constructible_v2"] = np.select(
        [~nu, zone.isin(["U", "AU"]), zone == "inconnu"],
        ["bati", "nu_constructible", "nu_zone_inconnue"], default="nu_zone_fermee")
    return df


def charger_residuel(eng) -> pd.DataFrame:
    """Le résiduel lu en entier (statique — même valeur pour toutes les années)."""
    return pd.read_sql("""
        SELECT p.idu, r.sdp_residuelle_m2 AS sdp_v2, r.sous_densite AS sous_densite_r,
               coalesce(split_part(r.cause, ':', 1), 'calculee') AS residuel_famille
        FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id""", eng)


def appliquer_residuel(df: pd.DataFrame, res: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(res, on="idu", how="left")
    df["residuel_famille"] = df["residuel_famille"].fillna("absent_du_cache")
    df["sdp_residuelle_v2_m2"] = pd.to_numeric(df["sdp_v2"], errors="coerce")
    df["sous_densite_v2"] = df["sous_densite_r"].fillna(False).astype(bool)
    nu = df["nu"].fillna(False).astype(bool)
    sdp = df["sdp_residuelle_v2_m2"]
    df["nu_constructible_v3"] = np.select(
        [~nu, sdp > 0, sdp == 0], ["bati", "nu_droits", "nu_sans_droits"],
        default="nu_non_calcule")
    return df.drop(columns=["sdp_v2", "sous_densite_r"])


def _ventes_annee(eng, annee: int, date_max: str | None = None) -> pd.DataFrame:
    """Ventes L2-F voisines pour une année d'observation. `date_max` (test de
    fuite) restreint la SOURCE en amont — le résultat doit être identique."""
    borne = f"AND m.date_mutation < '{date_max}'" if date_max else ""
    return pd.read_sql(f"""
        WITH asof AS (SELECT make_date({annee},1,1) AS d),
        mut AS (
            SELECT DISTINCT m.idu, m.id_mutation, m.date_mutation
            FROM p_model_ext_mut_l2 m, asof
            WHERE NOT m.exclue_l2f
              AND m.date_mutation >= (asof.d - interval '24 months')
              AND m.date_mutation <  asof.d {borne}
        ),
        mutg AS (
            SELECT mut.id_mutation, mut.date_mutation, p.geom_2975
            FROM mut JOIN parcels p ON p.idu = mut.idu
        )
        SELECT t.idu,
               count(DISTINCT mg.id_mutation) FILTER (
                   WHERE ST_DWithin(t.geom_2975, mg.geom_2975, 150)
                     AND mg.date_mutation >= (SELECT d - interval '12 months' FROM asof))
                   AS ventes_150m_12m,
               count(DISTINCT mg.id_mutation) FILTER (
                   WHERE ST_DWithin(t.geom_2975, mg.geom_2975, 150))
                   AS ventes_150m_24m,
               count(DISTINCT mg.id_mutation) FILTER (
                   WHERE mg.date_mutation >= (SELECT d - interval '12 months' FROM asof))
                   AS ventes_400m_12m,
               count(DISTINCT mg.id_mutation) AS ventes_400m_24m
        FROM parcels t
        JOIN mutg mg ON ST_DWithin(t.geom_2975, mg.geom_2975, 400)
        GROUP BY t.idu""", eng)


def _permis_annee(eng, annee: int, date_max: str | None = None) -> pd.DataFrame:
    borne = f"AND pp.date_autorisation < '{date_max}'" if date_max else ""
    return pd.read_sql(f"""
        WITH asof AS (SELECT make_date({annee},1,1) AS d),
        perm AS (
            SELECT pp.permit_id, pp.type, pp.date_autorisation, p.geom_2975
            FROM p_model_permits pp
            JOIN parcels p ON p.idu = pp.idu, asof
            WHERE pp.date_autorisation >= (asof.d - interval '24 months')
              AND pp.date_autorisation <  asof.d {borne}
        )
        SELECT t.idu,
               count(DISTINCT pe.permit_id) FILTER (
                   WHERE ST_DWithin(t.geom_2975, pe.geom_2975, 100))
                   AS permis_100m_24m,
               count(DISTINCT pe.permit_id) FILTER (WHERE pe.type = 'PA')
                   AS operations_pa_400m_24m
        FROM parcels t
        JOIN perm pe ON ST_DWithin(t.geom_2975, pe.geom_2975, 400)
        GROUP BY t.idu""", eng)


def charger_spatial(eng, years: tuple[int, ...],
                    cache: Path | None = None) -> pd.DataFrame:
    """Ventes + permis voisins par année (cache optionnel : fichier de l'arène)."""
    if cache is not None and Path(cache).exists():
        out = pd.read_csv(cache)
        return out[out["annee"].isin(years)].reset_index(drop=True)
    frames = []
    for y in years:
        v = _ventes_annee(eng, y)
        p = _permis_annee(eng, y)
        f = v.merge(p, on="idu", how="outer")
        f["annee"] = y
        frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    if cache is not None:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(cache, index=False)
    return out


def charger_marche(eng, years: tuple[int, ...]) -> pd.DataFrame:
    """Par (commune, annee) : volume Y-1, médiane €/m² bâti Y-1, tendance 3 ans."""
    an = pd.read_sql("""
        SELECT left(m.idu, 5) AS commune,
               extract(year FROM m.date_mutation)::int AS an,
               count(DISTINCT m.id_mutation) AS volume,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY m.pm2_bati)
                   FILTER (WHERE m.pm2_bati IS NOT NULL) AS med_pm2_bati
        FROM p_model_ext_mut_l2 m WHERE NOT m.exclue_l2f
        GROUP BY 1, 2""", eng)
    rows = []
    for y in years:
        a1 = an[an["an"] == y - 1].set_index("commune")
        a3 = (an[(an["an"] >= y - 3) & (an["an"] <= y - 1)]
              .groupby("commune")["volume"].mean())
        f = pd.DataFrame({
            "commune": a1.index,
            "volume_commune_a1": a1["volume"].to_numpy(),
            "med_pm2_commune_a1": a1["med_pm2_bati"].to_numpy(),
        })
        f["tendance_volume_3ans"] = (
            a1["volume"] / a3.reindex(a1.index)).to_numpy()
        f["annee"] = y
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


def charger_vendeur_actif(eng, years: tuple[int, ...],
                          cache: Path | None = None) -> pd.DataFrame:
    """Par (idu, annee) : le propriétaire PM (SIREN au dernier millésime ≤ Y-1)
    a vendu une AUTRE parcelle dans [asof-24 mois, asof). Renseigné pour Y ≥ 2021
    (millésimes SIREN 2019-2024), manquant explicite avant."""
    if cache is not None and Path(cache).exists():
        out = pd.read_csv(cache)
        return out[out["annee"].isin(years)].reset_index(drop=True)
    mil = pd.read_sql("SELECT idu, millesime, siren FROM pm_proprietaires_millesimes "
                      "WHERE siren IS NOT NULL", eng)
    v = pd.read_sql("SELECT DISTINCT idu, date_mutation FROM p_model_ext_mut_l2 "
                    "WHERE NOT exclue_l2f", eng)
    v["date_mutation"] = pd.to_datetime(v["date_mutation"])
    v["an"] = v["date_mutation"].dt.year
    ventes_pm = v.merge(mil, on="idu")
    ventes_pm = ventes_pm[ventes_pm["millesime"] == ventes_pm["an"] - 1]
    rows = []
    for annee in [y for y in years if y >= 2021]:
        asof = pd.Timestamp(annee, 1, 1)
        own = (mil[mil["millesime"] <= annee - 1]
               .sort_values("millesime").groupby("idu")["siren"].last())
        w = ventes_pm[(ventes_pm["date_mutation"] >= asof - pd.DateOffset(months=24))
                      & (ventes_pm["date_mutation"] < asof)]
        vendus = w.groupby("siren")["idu"].agg(set)
        s = own.map(vendus)
        flag = np.array([isinstance(x, set) and bool(x - {i})
                         for i, x in zip(own.index, s)])
        rows.append(pd.DataFrame({"idu": own.index[flag], "annee": annee,
                                  "pm_vendeur_actif": True}))
    out = (pd.concat(rows, ignore_index=True) if rows
           else pd.DataFrame(columns=["idu", "annee", "pm_vendeur_actif"]))
    if cache is not None:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(cache, index=False)
    return out


def appliquer_voisinage(df: pd.DataFrame, spatial: pd.DataFrame,
                        marche: pd.DataFrame, vendeur: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(spatial, on=["idu", "annee"], how="left")
    for c in ("ventes_150m_12m", "ventes_150m_24m", "ventes_400m_12m",
              "ventes_400m_24m", "permis_100m_24m", "operations_pa_400m_24m"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)
    df["ventes_400m_delta"] = df["ventes_400m_12m"] - (df["ventes_400m_24m"]
                                                       - df["ventes_400m_12m"])
    df = df.merge(marche, on=["commune", "annee"], how="left")
    df = df.merge(vendeur, on=["idu", "annee"], how="left")
    # PM sans info SIREN ou millésime : manquant explicite ; non-PM : False
    est_pm = df["owner_type"].isin(["pm", "bailleur", "public"])
    df["pm_vendeur_actif"] = np.where(
        ~est_pm, False,
        np.where(df["annee"] >= 2021, df["pm_vendeur_actif"].fillna(False), None))
    return df


def enrichir(eng, df: pd.DataFrame, years: tuple[int, ...],
             cache_dir: Path | None = None) -> pd.DataFrame:
    """Toutes les features candidates de la recette (censoring + résiduel +
    voisinage), pour les années demandées. `cache_dir` : caches de l'arène
    (calcul spatial long) — None en production (une seule année, calcul direct)."""
    df = appliquer_censoring(df, charger_censoring(eng, years))
    df = appliquer_residuel(df, charger_residuel(eng))
    spatial = charger_spatial(
        eng, years, cache_dir / "voisinage_spatial.csv.gz" if cache_dir else None)
    marche = charger_marche(eng, years)
    vendeur = charger_vendeur_actif(
        eng, years, cache_dir / "vendeur_actif.csv.gz" if cache_dir else None)
    return appliquer_voisinage(df, spatial, marche, vendeur)


# ─────────────────────────── segments + modèle q_v12 ───────────────────────────

def segmenter(df: pd.DataFrame, copro: np.ndarray) -> pd.Series:
    """Les quatre segments (K4) — affectation UNIQUE et prioritaire :
    copro > personne morale (pm/bailleur/public) > terrain nu > bâti individuel."""
    seg = np.where(copro, "copropriete",
          np.where(df["owner_type"].isin(["pm", "bailleur", "public"]),
                   "personne_morale",
          np.where(df["nu"].fillna(False).astype(bool), "terrain_nu",
                   "bati_individuel")))
    return pd.Series(seg, index=df.index)


def copro_de(eng, df: pd.DataFrame) -> np.ndarray:
    """Flag copro par idu (p_model_ext_copro, même lecture que le pipeline)."""
    cop = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro "
                      "FROM p_model_ext_copro", eng)
    m = df[["idu"]].merge(cop, on="idu", how="left")
    return m["copro"].fillna(False).astype(bool).to_numpy()


@dataclass
class ModeleQv12:
    """Le modèle de la recette : fit GLOBAL (PModel, iso=None) + calibration
    isotonique PAR SEGMENT (2024). Les contributions par bloc sont recomposées
    depuis les specs CANDIDATES (le registre servi ne les connaît pas)."""

    base: PModel
    iso_par_segment: dict[str, IsotonicRegression]
    blocs: dict[str, str]                     # feature → 'Z' | 'D'
    meta: dict = field(default_factory=dict)

    def margin(self, df: pd.DataFrame) -> np.ndarray:
        return self.base.margin(df)

    def predict_proba(self, df: pd.DataFrame, seg: pd.Series) -> np.ndarray:
        z = self.margin(df)
        p = np.full(len(df), np.nan)
        segv = seg.to_numpy()
        for s, iso in self.iso_par_segment.items():
            m = segv == s
            if m.any():
                p[m] = iso.predict(z[m])
        assert not np.isnan(p).any(), "segment sans calibration isotonique"
        return np.clip(p, 1e-7, 1 - 1e-7)

    def contributions(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self.base.contributions(df)
        # les agrégats de PModel lisent le registre servi ; on les recompose
        # depuis les blocs de la recette (features candidates incluses).
        z_cols = [c for c in out.columns if self.blocs.get(c) == "Z"]
        d_cols = [c for c in out.columns if self.blocs.get(c) == "D"]
        out["contrib_Z"] = out[z_cols].sum(axis=1)
        out["contrib_D"] = out[d_cols].sum(axis=1)
        return out


def fit_qv12(df_all: pd.DataFrame, seg_all: pd.Series,
             names: list[str], specs: list[FeatureSpec],
             inter: list[tuple[str, str]], *, label_col: str = "label",
             train_min: int = TRAIN_MIN, train_max: int = TRAIN_MAX,
             cal_year: int = CAL_YEAR, C: float = 5.0,
             min_count: int = 200) -> ModeleQv12:
    """Fit GLOBAL au protocole K0 (binning+fit ≤ train_max), puis isotonique
    PAR SEGMENT sur cal_year — exactement la recette validée en arène."""
    train = df_all[(df_all.annee >= train_min) & (df_all.annee <= train_max)
                   & df_all[label_col].notna()].reset_index(drop=True)
    cal_mask = (df_all.annee == cal_year).to_numpy()
    cal = df_all[cal_mask].reset_index(drop=True)
    seg_cal = seg_all[cal_mask].reset_index(drop=True)
    y_tr = train[label_col].astype(int)

    m = PModel(feature_names=list(names))
    m.year_dummies = sorted(train.annee.unique())[:-1]
    m.interactions = [(a, b) for a, b in inter if a in names and b in names]
    m.encoder = WoeEncoder(min_count=min_count).fit(train, y_tr, list(specs))
    m.fit(train, y_tr, C=C, min_count=min_count)

    z_cal = m.margin(cal)
    y_cal = cal[label_col].astype(int).to_numpy()
    iso_par_segment: dict[str, IsotonicRegression] = {}
    for s in SEGMENTS:
        ms = (seg_cal == s).to_numpy()
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(z_cal[ms], y_cal[ms])
        iso_par_segment[s] = iso
    blocs = {sp.name: sp.bloc for sp in specs}
    return ModeleQv12(base=m, iso_par_segment=iso_par_segment, blocs=blocs,
                      meta={"label_col": label_col, "train_max": train_max,
                            "cal_year": cal_year, "C": C, "n_train": int(len(train))})


# ─────────────────────────── artefacts gelés (doctrine m36) ───────────────────────────

def verify_artifacts() -> tuple[ModeleQv12, ModeleQv12, dict]:
    """Charge les DEUX artefacts gelés (12 et 24 mois) et REFUSE tout mismatch
    sha256 avec le manifeste FREEZE-q_v12.json — même doctrine que m36."""
    import joblib
    freeze = json.loads(QV12_FREEZE.read_text())
    for path, cle in ((QV12_ARTIFACT_12M, "sha256_12m"),
                      (QV12_ARTIFACT_24M, "sha256_24m")):
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if sha != freeze[cle]:
            raise RuntimeError(
                f"REFUS : sha256 de {Path(path).name} ({sha[:16]}…) ≠ manifeste "
                f"({freeze[cle][:16]}…) — l'artefact gelé q_v12 seul fait foi.")
    return (joblib.load(QV12_ARTIFACT_12M), joblib.load(QV12_ARTIFACT_24M), freeze)


def geler_artifacts(m12: ModeleQv12, m24: ModeleQv12, manifeste: dict) -> dict:
    """Écrit les artefacts + le manifeste de gel (sha256). Utilisé par l'arène
    (q_v12_arene.py) — jamais par le pipeline, qui ne fait que LIRE."""
    import joblib
    QV12_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(m12, QV12_ARTIFACT_12M)
    joblib.dump(m24, QV12_ARTIFACT_24M)
    manifeste = dict(manifeste)
    manifeste["sha256_12m"] = hashlib.sha256(QV12_ARTIFACT_12M.read_bytes()).hexdigest()
    manifeste["sha256_24m"] = hashlib.sha256(QV12_ARTIFACT_24M.read_bytes()).hexdigest()
    QV12_FREEZE.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2,
                                      default=str), encoding="utf-8")
    return manifeste
