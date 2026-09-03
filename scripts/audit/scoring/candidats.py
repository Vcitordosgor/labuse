"""SCORING-2 · K1 → K4 bis — features candidates et lots mesurés au banc K0.

Chaque lot construit un CANDIDAT (jamais servi) : un jeu de features, un PModel
ajusté par LE protocole (protocole.fit_protocole), une ligne dans LA table unique
(reports/score-v2-arene/k0_table.csv). features.py (registre servi) n'est JAMAIS
modifié : les specs candidates vivent ici, l'encodeur est pré-ajusté à part.

Usage : .venv/bin/python scripts/audit/scoring/candidats.py k1 | k1bis | k2 | ...
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocole  # noqa: E402
from protocole import (  # noqa: E402
    CAL_YEAR, FOLD2025, OUT, SCORE_YEAR, TEST_YEAR, TRAIN_MAX, Contexte,
    enregistrer, fit_protocole, load_range, metriques)
from _common import engine  # noqa: E402
from labuse.scoring.p_model.features import FEATURES, FeatureSpec  # noqa: E402

_ARENE = "candidat SCORING-2 — arène seulement, jamais servi"
YEARS = tuple(range(2017, 2027))

#: bins actuels remplacés par leur version censurée (K1, variante c RETENUE).
#: `permis_bin` servi n'est PAS remplacé : il code déjà « jamais » explicite +
#: l'ancienneté du dernier permis (K1.2 déjà satisfait par la prod — mesuré :
#: le remplacer par un numérique 8,8 % dégradait, cf. k1_variantes.csv).
REMPLACEES_K1 = {"tenure_bin": "tenure_bin_v2",
                 "nu_constructible": "nu_constructible_v2"}
#: variante b (mesurée puis écartée) — remplacements numériques intégraux
REMPLACEES_K1B = {"tenure_bin": "tenure_annees",
                  "permis_bin": "permis_anciennete_annees",
                  "nu_constructible": "nu_constructible_v2"}

SPECS_CENSORING = [
    FeatureSpec("tenure_annees", "D", "num", 0,
                "DVF union 2014+ (p_model_ext_mut_all) : années depuis la dernière "
                "mutation as-of 01/01/Y ; AUCUNE mutation connue → bin « manquant » "
                "EXPLICITE = censuré « ≥ N ans » (N = ancienneté historique commune)",
                "as-of 01/01/Y", _ARENE, "couverture 100 % par construction (K1.1) : "
                "valeur OU bin censuré explicite, jamais un NA silencieux"),
    FeatureSpec("tenure_censuree", "D", "bool", 0,
                "indicateur : la détention est un plancher (pas de mutation depuis "
                "le début de l'historique DVF de la commune)", "as-of 01/01/Y", _ARENE),
    FeatureSpec("permis_anciennete_annees", "D", "num", 0,
                "Sitadel 2013+ : années depuis le dernier permis SUR la parcelle "
                "as-of 01/01/Y ; jamais de permis → bin « manquant » explicite",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("permis_jamais", "D", "bool", 0,
                "absence de permis = 0 explicite (jamais un inconnu) — couverture "
                "100 % (K1.2)", "as-of 01/01/Y", _ARENE),
    FeatureSpec("nu_constructible_v2", "D", "cat", 0,
                "BD TOPO × zone PLU, désambiguïsé : nu_constructible (U/AU) / "
                "nu_zone_fermee (A/N) / nu_zone_inconnue (non calculé) / bati — "
                "provisoire en attendant K3 (K1.3)", "statique", _ARENE),
    FeatureSpec("tenure_bin_v2", "D", "cat", 0,
                "détention CATÉGORIELLE enrichie (variante c retenue) : "
                "{<1, 1-2, 2-3, 3-5, 5-8, 8+} sur les mutations connues (DVF 2014+) "
                "+ « censure » explicite = aucune mutation depuis le début de "
                "l'historique de la commune (≥ N ans)", "as-of 01/01/Y", _ARENE,
                "couverture 100 % (valeur ou censure, jamais un inconnu muet)"),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def specs_pour(names: list[str], extra: list[FeatureSpec]) -> list[FeatureSpec]:
    by = {f.name: f for f in FEATURES}
    by.update({s.name: s for s in extra})
    return [by[n] for n in names]


def interactions_remappees(remap: dict[str, str]) -> list[tuple[str, str]]:
    """Les 5 croisements minés du walk-forward M36, reportés sur les features
    candidates de même sémantique (le minage n'est pas refait : même architecture)."""
    import joblib
    fold = joblib.load(FOLD2025)
    return [(remap.get(a, a), remap.get(b, b)) for a, b in fold.interactions]


# ─────────────────────────────── censoring (K1) ───────────────────────────────

def charger_censoring(eng, years: tuple[int, ...] = YEARS) -> pd.DataFrame:
    """Colonnes candidates K1 par (idu, annee) — grille complète en pandas,
    dernières mutations/permis en SQL (mêmes sources que ext_sql, lecture seule)."""
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
    """Merge + dérivation des 5 features candidates K1 sur le dataset chargé."""
    df = df.merge(cens, on=["idu", "annee"], how="left")
    asof = pd.to_datetime(df["annee"].astype(str) + "-01-01")
    derniere = pd.to_datetime(df["derniere_mutation"])
    debut = pd.to_datetime(df["debut_histo"]).fillna(pd.Timestamp("2014-01-01"))
    n_commune = (asof - debut).dt.days / 365.25
    tenure = (asof - derniere).dt.days / 365.25
    df["tenure_censuree"] = derniere.isna()
    # Codage retenu (variante b) : censuré → bin « manquant » EXPLICITE du WoE
    # (sémantique « ≥ N ans, N = ancienneté de l'historique commune ») + indicateur.
    # La variante a (plancher numérique = N) a été MESURÉE et rejetée : N varie avec
    # l'année d'entraînement (3 ans en 2017 → 12 en 2026), les censurées des années
    # anciennes polluaient les bins des vraies détentions courtes (AUC 0,609 < base
    # 0,613, churn 70 % — reports/score-v2-arene/k1_variantes.csv).
    df["tenure_annees"] = tenure
    df["tenure_plancher_annees"] = n_commune  # documentaire (constant par commune-année)
    # Variante c (RETENUE après mesure des trois) : catégorielle enrichie — bins fins
    # de détention CONNUE + catégorie « censure » explicite (≥ N ans d'historique).
    # Garde la stabilité du catégoriel (l'AUC de la variante b numérique perdait ~0,008)
    # tout en ouvrant la granularité 3→8+ ans que tenure_bin écrasait en « 3+ ».
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


def features_k1() -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    """Variante c retenue : tenure_bin_v2 (cat censurée fine) + nu_constructible_v2.
    tenure_censuree/tenure_annees/permis_* numériques restent des COLONNES
    (raisons K6, challenger K5) mais pas des features du candidat logistique."""
    names = [f.name for f in FEATURES if f.name not in REMPLACEES_K1]
    names += ["tenure_bin_v2", "nu_constructible_v2"]
    return (names, specs_pour(names, SPECS_CENSORING),
            interactions_remappees(REMPLACEES_K1))


def features_k1b() -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    """Variante b (numérique intégral) — gardée mesurable, écartée."""
    names = [f.name for f in FEATURES if f.name not in REMPLACEES_K1B]
    names += [s.name for s in SPECS_CENSORING if s.name != "nu_constructible_v3"]
    names = [n for n in names if n != "tenure_bin_v2"]
    return (names, specs_pour(names, SPECS_CENSORING),
            interactions_remappees(REMPLACEES_K1B))


# ─────────────────────────────── horizons (K1 bis) ───────────────────────────────

def charger_label24(eng) -> pd.DataFrame:
    """label_24m par (idu, annee) — mutation L2-F dans [asof, asof+24 mois).
    DVF s'arrête au 31/12/2025 → complet pour annee ≤ 2024 SEULEMENT."""
    pos = pd.read_sql("""
        WITH win AS (SELECT annee, make_date(annee,1,1) AS asof
                     FROM generate_series(2017, 2024) AS g(annee))
        SELECT DISTINCT m.idu, w.annee, 1 AS label_24m
        FROM p_model_ext_mut_l2 m
        JOIN win w ON NOT m.exclue_l2f
         AND m.date_mutation >= w.asof
         AND m.date_mutation <  w.asof + interval '24 months'""", eng)
    return pos


def appliquer_label24(df: pd.DataFrame, pos: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(pos, on=["idu", "annee"], how="left")
    complet = df["annee"] <= 2024
    df["label_24m"] = df["label_24m"].where(~complet, df["label_24m"].fillna(0))
    return df


# ─────────────────────────── variables mortes (K2) ───────────────────────────

#: K2 — mortes au mandat (Δauc ≤ 0 mesuré SCORING-1 B.2)
MORTES_K2 = ("ndvi_moyen", "canopee_pct", "acces_equipements", "friche")
#: doctrine M35 (features.py) : les `retired` sont exclues de tout NOUVEL entraînement
RETIREES_M35 = tuple(f.name for f in FEATURES if f.retired)


def features_k2() -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    names, specs, inter = features_k1()
    hors = set(MORTES_K2) | set(RETIREES_M35)
    names = [n for n in names if n not in hors]
    specs = [s for s in specs if s.name not in hors]
    inter = [(a, b) for a, b in inter if a not in hors and b not in hors]
    return names, specs, inter


# ─────────────────────────── résiduel à 100 % (K3) ───────────────────────────

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

REMPLACEES_K3 = ("sdp_residuelle_m2", "sous_densite", "nu_constructible_v2")


def charger_residuel(eng) -> pd.DataFrame:
    """Le résiduel lu en entier (statique — même valeur pour toutes les années)."""
    r = pd.read_sql("""
        SELECT p.idu, r.sdp_residuelle_m2 AS sdp_v2, r.sous_densite AS sous_densite_r,
               coalesce(split_part(r.cause, ':', 1), 'calculee') AS residuel_famille
        FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id""", eng)
    return r


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


def features_k3() -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    names, specs, inter = features_k2()
    names = [n for n in names if n not in REMPLACEES_K3]
    names += [s.name for s in SPECS_RESIDUEL]
    specs = specs_pour(names, SPECS_CENSORING + SPECS_RESIDUEL)
    remap = {"sdp_residuelle_m2": "sdp_residuelle_v2_m2",
             "sous_densite": "sous_densite_v2",
             "nu_constructible_v2": "nu_constructible_v3"}
    inter = [(remap.get(a, a), remap.get(b, b)) for a, b in inter]
    return names, specs, inter


# ─────────────────── voisinage et marché, as-of (K4 bis) ───────────────────

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


def _enrichir_k4bis(eng, df):
    import voisinage
    df = _enrichir_k3(eng, df)
    log("  voisinage : spatial (cache)…")
    spatial = voisinage.charger_spatial(eng)
    log("  voisinage : marché communal…")
    marche = voisinage.charger_marche(eng)
    log("  voisinage : PM vendeur actif…")
    vendeur = voisinage.charger_vendeur_actif(eng)
    return voisinage.appliquer_voisinage(df, spatial, marche, vendeur)


def features_k4bis() -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    names, _, inter = features_k3()
    names = names + [s.name for s in SPECS_VOISINAGE]
    specs = specs_pour(names, SPECS_CENSORING + SPECS_RESIDUEL + SPECS_VOISINAGE)
    return names, specs, inter


def k4bis() -> None:
    """K4 bis — segments K4 + voisinage/marché. Sauve le CHAMPION (K5/K6/K7)."""
    import joblib
    import voisinage
    eng = engine()
    log("[K4bis] test de fuite dédié (2025)…")
    fuite = voisinage.test_fuite(eng)
    print(fuite)
    assert not fuite["fuite_detectee"], "FUITE dans les features de voisinage"
    names, specs, inter = features_k4bis()
    log("[K4bis] chargement…")
    df = load_range(eng, YEARS)
    df = _enrichir_k4bis(eng, df)
    log("[K4bis] fit des 4 segments…")
    ms, seg_all = fit_segments(df, names, specs, inter, eng)
    ctx = Contexte(eng, df[df.annee == TEST_YEAR], df[df.annee == SCORE_YEAR])
    seg_test = seg_all[(df.annee == TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = ms.predict_proba(ctx.test, seg_test)
    cd = ms.contrib_d(ctx.test, seg_test)
    p26 = ms.predict_proba(ctx.score26, seg_26)
    table = enregistrer(metriques(ctx, "K4bis_voisinage", p, cd, p26))
    joblib.dump({"modeles": ms.modeles, "d_features": ms.d_features,
                 "names": names, "inter": inter},
                protocole.OUT / "cache/champion_k4bis.joblib")
    print(table.to_string(index=False))


# ─────────────────────── quatre segments, pas un (K4) ───────────────────────

class ModeleSegments:
    """Un PModel PAR segment (bâti individuel / terrain nu / personne morale /
    copropriété), calibration isotonique par segment. Zone A HORS apprentissage
    (écartée par la cascade — AUC 0,51 mesurée SCORING-1 C.3) ; les parcelles A
    restent scorées par le modèle de leur segment (extrapolation, jamais servies
    en tête par le produit)."""

    def __init__(self, modeles: dict, d_features: list[str]):
        self.modeles = modeles
        self.d_features = d_features

    def predict_proba(self, df: pd.DataFrame, seg: pd.Series) -> np.ndarray:
        p = np.full(len(df), np.nan)
        segv = seg.to_numpy()
        for s, m in self.modeles.items():
            mask = segv == s
            if mask.any():
                p[mask] = m.predict_proba(df[mask])
        assert not np.isnan(p).any(), "segment sans modèle"
        return p

    def contrib_d(self, df: pd.DataFrame, seg: pd.Series) -> np.ndarray:
        out = np.full(len(df), np.nan)
        segv = seg.to_numpy()
        for s, m in self.modeles.items():
            mask = segv == s
            if mask.any():
                out[mask] = protocole.contrib_d_de(m, df[mask], self.d_features)
        return out


def fit_segments(df: pd.DataFrame, names, specs, inter, eng,
                 label_col: str = "label", train_max: int = TRAIN_MAX,
                 cal_year: int = CAL_YEAR) -> tuple[ModeleSegments, pd.Series]:
    """Ajuste les 4 modèles segmentés au protocole. Renvoie (modèle, seg du df)."""
    import measure
    copro = measure.copro_mask(eng, df)
    seg = protocole.segmenter(df, copro)
    hors_a = df["zone_plu"].fillna("inconnu") != "A"
    modeles = {}
    for s in protocole.SEGMENTS:
        sub = df[(seg == s).to_numpy() & hors_a.to_numpy()].reset_index(drop=True)
        log(f"  segment {s} : {len(sub)} lignes (zone A exclue de l'apprentissage)")
        modeles[s] = fit_protocole(sub, names, specs=specs, interactions=inter,
                                   label_col=label_col, train_max=train_max,
                                   cal_year=cal_year)
    d_feats = [sp.name for sp in specs if sp.bloc == "D"]
    return ModeleSegments(modeles, d_feats), seg


def k4() -> None:
    names, specs, inter = features_k3()
    eng = engine()
    log("[K4] chargement…")
    df = load_range(eng, YEARS)
    df = _enrichir_k3(eng, df)
    log("[K4] fit des 4 segments…")
    ms, seg_all = fit_segments(df, names, specs, inter, eng)
    ctx = Contexte(eng, df[df.annee == TEST_YEAR], df[df.annee == SCORE_YEAR])
    seg_test = seg_all[(df.annee == TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = ms.predict_proba(ctx.test, seg_test)
    cd = ms.contrib_d(ctx.test, seg_test)
    p26 = ms.predict_proba(ctx.score26, seg_26)
    table = enregistrer(metriques(ctx, "K4_segments", p, cd, p26))
    print(table.to_string(index=False))


# ─────────────────────────────── le runner de lot ───────────────────────────────

def run_lot(tag: str, names: list[str], specs: list[FeatureSpec],
            inter: list[tuple[str, str]],
            enrichir=None, label_col: str = "label") -> dict:
    """Charge 2017-2026, enrichit (features candidates), ajuste au protocole,
    mesure au banc K0, enregistre la ligne dans la table unique."""
    eng = engine()
    log(f"[{tag}] chargement {YEARS[0]}-{YEARS[-1]}…")
    df = load_range(eng, YEARS)
    if enrichir is not None:
        log(f"[{tag}] features candidates…")
        df = enrichir(eng, df)
    log(f"[{tag}] fit protocole (≤{TRAIN_MAX}, cal {CAL_YEAR})…")
    m = fit_protocole(df, names, specs=specs, interactions=inter, label_col=label_col)
    log(f"[{tag}] contexte de mesure…")
    ctx = Contexte(eng, df[df.annee == TEST_YEAR], df[df.annee == SCORE_YEAR])
    log(f"[{tag}] prédictions + métriques…")
    p = m.predict_proba(ctx.test)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    cd = protocole.contrib_d_de(m, ctx.test, d_feats)
    p26 = m.predict_proba(ctx.score26)
    row = metriques(ctx, tag, p, cd, p26)
    table = enregistrer(row)
    log(f"[{tag}] terminé.")
    print(table.to_string(index=False))
    return {"model": m, "row": row, "ctx": ctx, "df": df}


def k1() -> None:
    names, specs, inter = features_k1()
    couv = None

    def enrichir(eng, df):
        nonlocal couv
        cens = charger_censoring(eng)
        df = appliquer_censoring(df, cens)
        y26 = df[df.annee == SCORE_YEAR]
        couv = {
            "tenure_bin_v2": y26["tenure_bin_v2"].value_counts().to_dict(),
            "tenure_censuree_pct": float(100 * y26["tenure_censuree"].mean()),
            "permis_jamais_pct": float(100 * y26["permis_jamais"].mean()),
            "nu_constructible_v2": y26["nu_constructible_v2"].value_counts().to_dict(),
        }
        return df

    run_lot("K1_censoring", names, specs, inter, enrichir=enrichir)
    pd.DataFrame([couv]).to_csv(OUT / "k1_couverture.csv", index=False)
    print(couv)


def _enrichir_censoring(eng, df):
    return appliquer_censoring(df, charger_censoring(eng))


def _enrichir_k3(eng, df):
    df = appliquer_censoring(df, charger_censoring(eng))
    return appliquer_residuel(df, charger_residuel(eng))


def k1bis() -> None:
    """K1 bis — 12 vs 24 mois, à protocole égal (train ≤2022, cal 2023, test 2024 :
    la SEULE année de test à fenêtre 24 mois complète, DVF s'arrêtant au 31/12/2025)."""
    names, specs, inter = features_k1()
    eng = engine()
    log("[K1bis] chargement…")
    df = load_range(eng, YEARS)
    df = _enrichir_censoring(eng, df)
    df = appliquer_label24(df, charger_label24(eng))
    for tag, label_col, hz in (("K1bis_12m_test2024", "label", 12),
                               ("K1bis_24m_test2024", "label_24m", 24)):
        log(f"[{tag}] fit (≤2022, cal 2023)…")
        m = fit_protocole(df, names, specs=specs, interactions=inter,
                          label_col=label_col, train_max=2022, cal_year=2023)
        ctx = Contexte(eng, df[df.annee == 2024], df[df.annee == SCORE_YEAR],
                       label_col=label_col, annee_test=2024, horizon_mois=hz)
        p = m.predict_proba(ctx.test)
        cd = protocole.contrib_d_de(m, ctx.test, [s.name for s in specs if s.bloc == "D"])
        p26 = m.predict_proba(ctx.score26)
        table = enregistrer(metriques(ctx, tag, p, cd, p26))
    print(table.to_string(index=False))


def _stabilite(df, names, specs, inter, tag, n_tirages: int = 3,
               frac: float = 0.6) -> dict:
    """K2 — stabilité bootstrap : refits sur sous-échantillons seedés du train,
    écart-type de l'AUC test + concordance des signes de coefficients."""
    from sklearn.metrics import roc_auc_score
    train = df[(df.annee >= 2017) & (df.annee <= TRAIN_MAX)].reset_index(drop=True)
    cal = df[df.annee == CAL_YEAR].reset_index(drop=True)
    test = df[df.annee == TEST_YEAR].reset_index(drop=True)
    y_te = test["label"].astype(int).to_numpy()
    aucs, signes = [], []
    for seed in range(n_tirages):
        sub = train.sample(frac=frac, random_state=974 + seed).reset_index(drop=True)
        from labuse.scoring.p_model.model import PModel
        from labuse.scoring.p_model.woe import WoeEncoder
        m = PModel(feature_names=names)
        m.year_dummies = sorted(sub.annee.unique())[:-1]
        m.interactions = [(a, b) for a, b in inter if a in names and b in names]
        m.encoder = WoeEncoder(min_count=200).fit(sub, sub["label"].astype(int), specs)
        m.fit(sub, sub["label"].astype(int), C=5.0)
        m.calibrate(cal, cal["label"].astype(int))
        aucs.append(roc_auc_score(y_te, m.predict_proba(test)))
        signes.append({f: float(np.sign(m.coefs.get(f, 0.0))) for f in names})
    sg = pd.DataFrame(signes)
    concord = float((sg.nunique() == 1).mean())  # part de features au signe constant
    return {"jeu": tag, "n_tirages": n_tirages, "frac_train": frac,
            "auc_test_moy": float(np.mean(aucs)), "auc_test_std": float(np.std(aucs)),
            "signes_constants_pct": 100 * concord, "n_features": len(names)}


def k2() -> None:
    """K2 — variables mortes retirées + doctrine M35 (retired hors de tout nouveau fit).
    L'AUC ne doit pas baisser ; la stabilité bootstrap doit s'améliorer."""
    n2, s2, i2 = features_k2()
    res = run_lot("K2_mortes", n2, s2, i2, enrichir=_enrichir_censoring)
    n1, s1, i1 = features_k1()
    log("[K2] stabilité bootstrap K1 vs K2…")
    stab = pd.DataFrame([_stabilite(res["df"], n1, s1, i1, "K1 (avant retrait)"),
                         _stabilite(res["df"], n2, s2, i2, "K2 (après retrait)")])
    stab.to_csv(OUT / "k2_stabilite.csv", index=False)
    print(stab.to_string(index=False))


def k3() -> None:
    """K3 — le résiduel lu à 100 % (zéros M125 + cause explicite) + ventilation."""
    eng = engine()
    vent = pd.read_sql("""
        SELECT coalesce(split_part(r.cause, ':', 1), 'calculee') AS famille,
               count(*) AS n,
               count(*) FILTER (WHERE r.sdp_residuelle_m2 IS NULL) AS sdp_null,
               count(*) FILTER (WHERE r.sdp_residuelle_m2 = 0)     AS sdp_zero,
               count(*) FILTER (WHERE r.sdp_residuelle_m2 > 0)     AS sdp_pos,
               count(*) FILTER (WHERE st.sdp_residuelle_m2 IS NULL) AS perdu_feature_store
        FROM parcel_residuel r
        JOIN parcels p ON p.id = r.parcel_id
        LEFT JOIN p_model_static st ON st.idu = p.idu
        GROUP BY 1 ORDER BY n DESC""", eng)
    vent.to_csv(OUT / "k3_ventilation.csv", index=False)
    print(vent.to_string(index=False))
    names, specs, inter = features_k3()
    run_lot("K3_residuel", names, specs, inter, enrichir=_enrichir_k3)


if __name__ == "__main__":
    {"k1": k1, "k1bis": k1bis, "k2": k2, "k3": k3, "k4": k4, "k4bis": k4bis}[
        sys.argv[1] if len(sys.argv) > 1 else "k1"]()
