"""SCORING-DONNEES-1 · Lot D — bloc propriétaire personne morale (segment PM).

Ce qui existe dans le Score V et la veille succession, jamais entré dans le
modèle P — chaque variable construite AS-OF puis mesurée au banc K0, le verdict
se lit sur le SEGMENT PM (auc/ece_personne_morale) :

  - dirigeant_age_max_asof   : âge du plus vieux dirigeant PP (RNE, date de
                               naissance) au 01/01/Y ;
  - sci_agee_asof            : SCI (nature 6540 / forme DGFiP) créée ≥ 20 ans
                               avant asof (la « dormance RNE » n'est PAS as-of :
                               date_mise_a_jour_rne est un état 2026) ;
  - bodacc_36m               : événement BODACC (pcl / radiation / cession) sur
                               le SIREN propriétaire dans les 36 mois avant asof ;
  - pm_entree_recente        : la PM est propriétaire depuis < 2 ans au 01/01/Y
                               (pm_proprietaires_millesimes 2019-2024 ; hors
                               fenêtre → manquant explicite) ;
  - ventes_pm_secteur_36m    : part des ventes du secteur (36 mois avant asof)
                               parties vers un acquéreur PM (mutation suivie
                               d'une entrée au millésime PM suivant).

parcel_veille_succession (7 129 lignes) est un état CALCULÉ 2026 (computed_at) :
documenté, pas mesuré tel quel — son contenu (âge, SCI dormante) est recalculé
as-of ci-dessus.

Usage : .venv/bin/python scripts/audit/scoring/donnees1_d.py inventaire|k0
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donnees1_commun as dc  # noqa: E402
from donnees1_commun import OUT, YEARS, _ARENE, log  # noqa: E402
from _common import engine  # noqa: E402
from labuse.scoring.p_model.features import FeatureSpec  # noqa: E402

MILL_MIN, MILL_MAX = 2019, 2024  # pm_proprietaires_millesimes (situation au 01/01)


def inventaire() -> None:
    eng = engine()
    inv = pd.read_sql("""
        SELECT 'pm_proprietaires_millesimes' AS source,
               count(*)::text || ' liens, millésimes ' || min(millesime) || '-' || max(millesime) AS contenu,
               'idu × millesime × siren' AS cle, 'OUI (01/01 de chaque année)' AS asof
        FROM pm_proprietaires_millesimes
        UNION ALL
        SELECT 'pm_dirigeants (RNE)',
               count(*)::text || ' dirigeants, ' || count(date_naissance)::text || ' avec date de naissance',
               'siren', 'OUI (âge recalculable à toute date)'
        FROM pm_dirigeants
        UNION ALL
        SELECT 'bodacc_annonces_owner',
               count(*)::text || ' annonces ' || min(date_annonce) || ' → ' || max(date_annonce) ||
               ' (pcl/radiation/vente_cession)',
               'siren × date_annonce', 'OUI (annonces datées)'
        FROM bodacc_annonces_owner
        UNION ALL
        SELECT 'owner_enrichment (recherche-entreprises)',
               count(*)::text || ' SIREN, ' || count(payload->>'date_creation')::text || ' avec date de création',
               'siren', 'PARTIEL : date_creation OUI ; date_mise_a_jour_rne = état 2026 (NON)'
        FROM owner_enrichment
        UNION ALL
        SELECT 'parcel_veille_succession',
               count(*)::text || ' parcelles (dirigeant_age, sci_dormante), computed_at 2026',
               'parcelle_id', 'NON (état calculé 2026) — contenu recalculé as-of ici'
        FROM parcel_veille_succession""", eng)
    inv.to_csv(OUT / "d1_inventaire_pm.csv", index=False)
    print(inv.to_string(index=False))


SPECS_D = [
    FeatureSpec("dirigeant_age_max_asof", "D", "num", 0,
                "âge du plus vieux dirigeant personne physique du SIREN "
                "propriétaire au 01/01/Y (pm_dirigeants.date_naissance, RNE) ; "
                "non-PM ou dirigeant inconnu → manquant explicite",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("sci_agee_asof", "D", "bool", 0,
                "propriétaire SCI (nature juridique 6540 ou forme DGFiP SCI) "
                "créée ≥ 20 ans avant asof (owner_enrichment.date_creation) ; "
                "non-PM/non-SCI → False", "as-of 01/01/Y", _ARENE),
    FeatureSpec("bodacc_36m", "D", "bool", 0,
                "événement BODACC (procédure collective, radiation, cession) sur "
                "le SIREN propriétaire dans les 36 mois avant asof ; non-PM → False",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("pm_entree_recente", "D", "bool", 0,
                "le SIREN propriétaire est entré au millésime PM depuis < 2 ans "
                "au 01/01/Y (absent du millésime Y-2) ; hors fenêtre 2021-2024 → "
                "manquant explicite", "as-of 01/01/Y", _ARENE),
    FeatureSpec("ventes_pm_secteur_36m", "Z", "num", 0,
                "part des ventes L2-F du secteur, 36 mois avant asof, parties "
                "vers un acquéreur PM (mutation suivie d'une entrée au millésime "
                "PM suivant — déterminable pour les ventes ≤ 2023)",
                "as-of 01/01/Y", _ARENE),
]


def _proprietaire_asof(eng) -> pd.DataFrame:
    """(idu, annee, siren) : le propriétaire PM au 01/01/Y — millésime Y borné
    à [2019, 2024] ; l'écart est signalé dans `mill_exact`."""
    pm = pd.read_sql(
        "SELECT idu, millesime, siren FROM pm_proprietaires_millesimes "
        "WHERE siren IS NOT NULL", eng)
    frames = []
    for y in YEARS:
        m = int(np.clip(y, MILL_MIN, MILL_MAX))
        sub = pm[pm.millesime == m][["idu", "siren"]].drop_duplicates("idu")
        sub = sub.assign(annee=y, mill_exact=(m == y))
        frames.append(sub)
    return pd.concat(frames, ignore_index=True)


def _colonnes_d(eng) -> pd.DataFrame:
    log("  propriétaire PM as-of (millésimes)…")
    prop = _proprietaire_asof(eng)

    log("  âge dirigeant as-of…")
    dirg = pd.read_sql(
        "SELECT siren, min(date_naissance) AS naissance_max_age "
        "FROM pm_dirigeants WHERE date_naissance IS NOT NULL "
        "AND type_personne <> 'morale' GROUP BY siren", eng)
    prop = prop.merge(dirg, on="siren", how="left")
    asof = pd.to_datetime(prop["annee"].astype(str) + "-01-01")
    naiss = pd.to_datetime(prop["naissance_max_age"], errors="coerce")
    prop["dirigeant_age_max_asof"] = ((asof - naiss).dt.days / 365.25).round(1)

    log("  SCI âgée as-of…")
    sci = pd.read_sql("""
        SELECT siren, payload->>'date_creation' AS date_creation,
               (payload->>'nature_juridique' = '6540') AS nature_sci
        FROM owner_enrichment""", eng)
    formes = pd.read_sql(
        "SELECT DISTINCT siren FROM pm_proprietaires_millesimes "
        "WHERE upper(coalesce(forme_juridique,'')) LIKE '%%SCI%%'", eng)
    sci["forme_sci"] = sci["siren"].isin(set(formes["siren"]))
    prop = prop.merge(sci, on="siren", how="left")
    crea = pd.to_datetime(prop["date_creation"], errors="coerce")
    est_sci = prop["nature_sci"].fillna(False) | prop["forme_sci"].fillna(False)
    prop["sci_agee_asof"] = (est_sci & crea.notna()
                             & ((asof - crea).dt.days / 365.25 >= 20))

    log("  BODACC 36 mois as-of…")
    bod = pd.read_sql(
        "SELECT siren, date_annonce FROM bodacc_annonces_owner", eng)
    bod["date_annonce"] = pd.to_datetime(bod["date_annonce"])
    hits = []
    for y in YEARS:
        a = pd.Timestamp(f"{y}-01-01")
        s = bod[(bod.date_annonce >= a - pd.DateOffset(months=36))
                & (bod.date_annonce < a)]["siren"].unique()
        hits.append(pd.DataFrame({"siren": s, "annee": y, "bodacc_36m": True}))
    prop = prop.merge(pd.concat(hits, ignore_index=True),
                      on=["siren", "annee"], how="left")
    prop["bodacc_36m"] = prop["bodacc_36m"].fillna(False)

    log("  entrée récente en PM…")
    pm = pd.read_sql(
        "SELECT idu, millesime, siren FROM pm_proprietaires_millesimes "
        "WHERE siren IS NOT NULL", eng)
    cles = set(zip(pm["idu"], pm["millesime"], pm["siren"]))
    m = prop["annee"].clip(MILL_MIN, MILL_MAX)
    mesurable = (m - 2 >= MILL_MIN) & prop["mill_exact"]
    present_avant = [
        (i, mm - 2, s) in cles
        for i, mm, s in zip(prop["idu"], m, prop["siren"])]
    prop["pm_entree_recente"] = np.where(
        mesurable, ~np.array(present_avant), np.nan)

    return prop[["idu", "annee", "dirigeant_age_max_asof", "sci_agee_asof",
                 "bodacc_36m", "pm_entree_recente"]]


def _ventes_pm_secteur(eng) -> pd.DataFrame:
    """(secteur, annee, ventes_pm_secteur_36m) — acquéreur PM détecté par
    l'entrée du bien au millésime PM suivant la vente (nouveau SIREN)."""
    log("  part des ventes vers un acquéreur PM (secteur, 36 mois)…")
    mut = pd.read_sql("""
        SELECT m.idu, m.date_mutation, f.secteur
        FROM p_model_ext_mut_l2 m JOIN p_model_frame f ON f.idu = m.idu
        WHERE NOT m.exclue_l2f""", eng)
    mut["date_mutation"] = pd.to_datetime(mut["date_mutation"])
    mut["annee_mut"] = mut["date_mutation"].dt.year
    pm = pd.read_sql(
        "SELECT idu, millesime, siren FROM pm_proprietaires_millesimes "
        "WHERE siren IS NOT NULL", eng)
    sirens_par_mill = {m: dict(g[["idu", "siren"]].values)
                       for m, g in pm.groupby("millesime")}

    def vers_pm(idu: str, annee_mut: int) -> float:
        ap = annee_mut + 1
        if ap < MILL_MIN + 1 or ap > MILL_MAX:
            return np.nan  # indéterminable (millésime suivant absent)
        s_apres = sirens_par_mill.get(ap, {}).get(idu)
        if s_apres is None:
            return 0.0
        s_avant = sirens_par_mill.get(min(max(annee_mut, MILL_MIN), MILL_MAX), {}).get(idu)
        return 1.0 if s_apres != s_avant else 0.0

    mut["vers_pm"] = [vers_pm(i, a) for i, a in zip(mut["idu"], mut["annee_mut"])]
    frames = []
    for y in YEARS:
        a = pd.Timestamp(f"{y}-01-01")
        w = mut[(mut.date_mutation >= a - pd.DateOffset(months=36))
                & (mut.date_mutation < a)]
        agg = (w.groupby("secteur")["vers_pm"].mean()
               .rename("ventes_pm_secteur_36m").reset_index().assign(annee=y))
        frames.append(agg)
    return pd.concat(frames, ignore_index=True)


def k0() -> None:
    eng = engine()
    log("[D2] colonnes candidates PM…")
    cols = _colonnes_d(eng)
    couv = cols.groupby("annee").agg(
        n_pm=("idu", "count"),
        age_connu=("dirigeant_age_max_asof", lambda s: int(s.notna().sum())),
        sci_agee=("sci_agee_asof", "sum"), bodacc=("bodacc_36m", "sum"),
        entree_recente=("pm_entree_recente", lambda s: int((s == 1).sum())))
    couv.to_csv(OUT / "d2_couverture_pm_par_annee.csv")
    print(couv.to_string())

    df, _ = dc.base_enrichie(eng)
    secteurs = _ventes_pm_secteur(eng)
    sec_cols = df[["idu", "annee"]].copy()
    sec_cols["secteur"] = df["secteur"].to_numpy()
    sec_cols = sec_cols.merge(secteurs, on=["secteur", "annee"], how="left")

    for spec in SPECS_D:
        if spec.name == "ventes_pm_secteur_36m":
            colonnes = sec_cols[["idu", "annee", spec.name]]
            ff = None
        else:
            colonnes = cols[["idu", "annee", spec.name]]
            ff = [spec.name] if spec.name in ("sci_agee_asof", "bodacc_36m") else None
        dc.mesurer(f"D_{spec.name}", [spec], colonnes=colonnes,
                   fill_false=ff, segment_seul="personne_morale")


if __name__ == "__main__":
    {"inventaire": inventaire, "k0": k0}[
        sys.argv[1] if len(sys.argv) > 1 else "inventaire"]()
