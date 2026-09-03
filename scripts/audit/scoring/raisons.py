"""SCORING-2 · K6 — trois raisons en français par parcelle (rien d'affiché).

Le champion est ADDITIF (logistique WoE) : contribution(feature) = coef × WoE(bin),
exacte par construction — c'est la décomposition de Shapley d'un modèle additif.
Ce module traduit les trois contributions dominantes en phrases courtes, sourcées,
datées, via UNE table de traduction variable → phrase (relue pour le français).

Conventions :
  - les contributions des croisements a*b sont réparties pour moitié sur chaque
    parent AVANT le top-3 (le client lit des faits, pas des produits de WoE) ;
  - une raison NÉGATIVE (frein) est préfixée « Frein — » ;
  - chaque phrase porte sa source et son millésime.

Sortie : reports/score-v2-arene/k6_raisons.csv (top-1158 hors copro du run
candidat 2026 + échantillon aléatoire seedé). Colonne produite, rien d'affiché.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import engine  # noqa: E402
import protocole  # noqa: E402

#: millésimes affichés (K7 les recopie du catalogue ; ici la date « arrêtée au »)
DATE_DVF = "DVF arrêté au 31/12/2025"
DATE_SITADEL = "Sitadel 2013→2025"
DATE_PLU = "PLU/GPU en vigueur à l'ingestion 2026"
DATE_RESIDUEL = "résiduel m135, PLU 2026"
DATE_BDTOPO = "BD TOPO 2026"
DATE_FILO = "Filosofi INSEE 2019"
DATE_FONCIER = "millésimes fonciers PM 2019-2024"


def _annees(v: float) -> str:
    return f"{v:.0f} an" + ("s" if v >= 2 else "")


TABLE_TRADUCTION: dict = {
    "tenure_annees": lambda r: (
        f"Aucune vente connue depuis au moins {_annees(r.get('tenure_plancher_annees', 11))} ({DATE_DVF}, historique 2014+)"
        if pd.isna(r.get("tenure_annees")) or r.get("tenure_censuree", False)
        else f"Détenue depuis {_annees(r['tenure_annees'])} — dernière mutation connue ({DATE_DVF})"),
    "tenure_censuree": lambda r: (
        f"Aucune vente connue depuis au moins {_annees(r.get('tenure_plancher_annees', 11))} ({DATE_DVF}, historique 2014+)"),
    "tenure_bin_v2": lambda r: (
        f"Aucune vente connue depuis au moins {_annees(r.get('tenure_plancher_annees', 11))} ({DATE_DVF}, historique 2014+)"
        if str(r.get("tenure_bin_v2")) == "censure"
        else "Détenue depuis " + {
            "<1": "moins d'un an", "1-2": "1 à 2 ans", "2-3": "2 à 3 ans",
            "3-5": "3 à 5 ans", "5-8": "5 à 8 ans", "8+": "plus de 8 ans",
        }.get(str(r.get("tenure_bin_v2")), str(r.get("tenure_bin_v2")))
        + f" — dernière mutation connue ({DATE_DVF})"),
    "permis_anciennete_annees": lambda r: (
        f"Jamais de permis connu sur la parcelle ({DATE_SITADEL})"
        if pd.isna(r.get("permis_anciennete_annees"))
        else f"Dernier permis sur la parcelle il y a {_annees(r['permis_anciennete_annees'])} ({DATE_SITADEL})"),
    "permis_jamais": lambda r: f"Jamais de permis connu sur la parcelle ({DATE_SITADEL})",
    "zone_plu": lambda r: f"Zone {r['zone_plu']} au PLU ({DATE_PLU})",
    "sdp_residuelle_v2_m2": lambda r: (
        f"{r['sdp_residuelle_v2_m2']:.0f} m² de SDP résiduelle ({DATE_RESIDUEL})"
        if pd.notna(r.get("sdp_residuelle_v2_m2")) and r["sdp_residuelle_v2_m2"] > 0
        else f"Aucun droit à bâtir résiduel ({DATE_RESIDUEL})"),
    "sdp_residuelle_m2": lambda r: (
        f"{r['sdp_residuelle_m2']:.0f} m² de SDP résiduelle ({DATE_RESIDUEL})"
        if pd.notna(r.get("sdp_residuelle_m2"))
        else f"SDP résiduelle non calculée ({DATE_RESIDUEL})"),
    "sous_densite_v2": lambda r: f"Parcelle sous-dense pour sa zone ({DATE_RESIDUEL})",
    "sous_densite": lambda r: f"Parcelle sous-dense pour sa zone ({DATE_RESIDUEL})",
    "residuel_famille": lambda r: {
        "calculee": f"Capacité résiduelle calculée ({DATE_RESIDUEL})",
        "zone_non_constructible": f"Zone sans droits à bâtir ({DATE_RESIDUEL})",
        "terrain_exigu": f"Terrain trop exigu pour bâtir ({DATE_RESIDUEL})",
        "zone_non_resolue": f"Zone non outillée au règlement ({DATE_RESIDUEL})",
        "habitat_interdit": f"Habitat interdit dans la zone ({DATE_RESIDUEL})",
        "redhibitoire": f"Contrainte rédhibitoire ({DATE_RESIDUEL})",
        "hors_plu": f"Hors PLU outillé — capacité inconnue ({DATE_RESIDUEL})",
    }.get(str(r.get("residuel_famille")), f"Résiduel : {r.get('residuel_famille')}"),
    "nu_constructible_v3": lambda r: {
        "nu_droits": f"Terrain nu avec droits à bâtir ({DATE_RESIDUEL})",
        "nu_sans_droits": f"Terrain nu sans droits à bâtir ({DATE_RESIDUEL})",
        "nu_non_calcule": f"Terrain nu, capacité non calculée ({DATE_RESIDUEL})",
        "bati": f"Parcelle bâtie ({DATE_BDTOPO})",
    }.get(str(r.get("nu_constructible_v3")), "Terrain nu"),
    "surface_m2": lambda r: f"Parcelle de {r['surface_m2']:.0f} m² (cadastre)",
    "rot_nu": lambda r: f"Secteur à rotation {'forte' if r['rot_nu'] > 0.02 else 'faible'} du foncier nu ({DATE_DVF}, 36 mois)",
    "rot_bati": lambda r: f"Secteur à rotation {'forte' if r['rot_bati'] > 0.02 else 'faible'} du bâti ({DATE_DVF}, 36 mois)",
    "med_pm2_terrain_36m": lambda r: f"Terrain du secteur à {r['med_pm2_terrain_36m']:.0f} €/m² ({DATE_DVF}, 36 mois)",
    "med_pm2_bati_36m": lambda r: f"Bâti du secteur à {r['med_pm2_bati_36m']:.0f} €/m² ({DATE_DVF}, 36 mois)",
    "tendance_pm2_bati": lambda r: f"Prix du bâti du secteur en {'hausse' if r['tendance_pm2_bati'] > 0 else 'baisse'} de {abs(r['tendance_pm2_bati']):.0%} ({DATE_DVF})",
    "dens_bati_secteur": lambda r: f"Secteur densément bâti ({DATE_BDTOPO})",
    "pct_bati_secteur": lambda r: f"{r['pct_bati_secteur']:.0%} de parcelles bâties dans le secteur ({DATE_BDTOPO})",
    "filo_snv_pp": lambda r: f"Niveau de vie du carreau : {r['filo_snv_pp']:.0f} €/pers. ({DATE_FILO})",
    "filo_pct_pauv": lambda r: f"{r['filo_pct_pauv']:.0%} de ménages pauvres dans le carreau ({DATE_FILO})",
    "filo_pct_prop": lambda r: f"{r['filo_pct_prop']:.0%} de propriétaires dans le carreau ({DATE_FILO})",
    "pente_moy_deg": lambda r: f"Pente moyenne de {r['pente_moy_deg']:.0f}° (RGE ALTI 5 m)",
    "piscine": lambda r: "Piscine détectée sur la parcelle (ortho 2026)",
    "pv_candidat": lambda r: "Candidat photovoltaïque (ortho 2026)",
    "ventes_150m_12m": lambda r: f"{r['ventes_150m_12m']:.0f} vente(s) à moins de 150 m en 12 mois ({DATE_DVF})",
    "ventes_150m_24m": lambda r: f"{r['ventes_150m_24m']:.0f} vente(s) à moins de 150 m en 24 mois ({DATE_DVF})",
    "ventes_400m_12m": lambda r: f"{r['ventes_400m_12m']:.0f} vente(s) à moins de 400 m en 12 mois ({DATE_DVF})",
    "ventes_400m_24m": lambda r: f"{r['ventes_400m_24m']:.0f} vente(s) à moins de 400 m en 24 mois ({DATE_DVF})",
    "ventes_400m_delta": lambda r: (
        f"Marché de voisinage en {'accélération' if r['ventes_400m_delta'] > 0 else 'ralentissement'} ({DATE_DVF})"),
    "permis_100m_24m": lambda r: f"{r['permis_100m_24m']:.0f} permis à moins de 100 m en 24 mois ({DATE_SITADEL})",
    "operations_pa_400m_24m": lambda r: f"Opération d'aménagement (permis PA) à moins de 400 m ({DATE_SITADEL})",
    "volume_commune_a1": lambda r: f"{r['volume_commune_a1']:.0f} ventes dans la commune l'an dernier ({DATE_DVF})",
    "med_pm2_commune_a1": lambda r: f"Marché communal à {r['med_pm2_commune_a1']:.0f} €/m² bâti ({DATE_DVF})",
    "tendance_volume_3ans": lambda r: (
        f"Volume communal en {'hausse' if r['tendance_volume_3ans'] > 1 else 'baisse'} sur 3 ans ({DATE_DVF})"),
    "pm_vendeur_actif": lambda r: f"Le propriétaire a vendu une autre parcelle depuis 24 mois ({DATE_FONCIER})",
    "acces_equipements": lambda r: "Équipements (école, commerce, santé) à proximité (OSM)",
    "canopee_pct": lambda r: f"Canopée {r['canopee_pct']:.0f} % (LiDAR/ortho)",
    "ndvi_moyen": lambda r: "Végétation de la parcelle (ortho)",
    "friche": lambda r: "Friche recensée (Cartofriches)",
}


def raisons_top3(model, df: pd.DataFrame, prefix_frein: str = "Frein — ") -> pd.DataFrame:
    """Trois raisons par ligne de df pour UN PModel (contributions additives).

    Croisements a*b : contribution répartie 1/2 sur chaque parent avant le top-3.
    Doublons de phrase (ex. tenure_annees + tenure_censuree) : dédupliqués, on
    descend au contributeur suivant.
    """
    contrib = model.contributions(df)
    feat_cols = [c for c in contrib.columns
                 if not c.startswith("contrib_") and "*" not in c]
    inter_cols = [c for c in contrib.columns if "*" in c]
    tot = contrib[feat_cols].copy()
    for ic in inter_cols:
        a, b = ic.split("*")
        for p_ in (a, b):
            if p_ in tot.columns:
                tot[p_] = tot[p_] + contrib[ic] / 2
    vals = tot.to_numpy()
    names = np.array(tot.columns)
    ordre = np.argsort(-np.abs(vals), axis=1)
    rows = []
    for i in range(len(df)):
        r = df.iloc[i]
        phrases, contribs = [], []
        for j in ordre[i]:
            f = names[j]
            v = float(vals[i, j])
            if abs(v) < 1e-9:
                break
            fn = TABLE_TRADUCTION.get(f)
            if fn is None:
                continue
            try:
                ph = fn(r)
            except (KeyError, TypeError, ValueError):
                continue
            if v < 0:
                ph = prefix_frein + ph
            if ph in phrases:
                continue
            phrases.append(ph)
            contribs.append(round(v, 4))
            if len(phrases) == 3:
                break
        while len(phrases) < 3:
            phrases.append("")
            contribs.append(np.nan)
        rows.append((r["idu"], *phrases, *contribs))
    return pd.DataFrame(rows, columns=[
        "idu", "raison_1", "raison_2", "raison_3",
        "contrib_1", "contrib_2", "contrib_3"])


def main() -> None:
    """Produit k6_raisons.csv : top-1158 hors copro 2026 du champion K4bis
    + 500 parcelles aléatoires seedées (relecture du français sur tout venant)."""
    import joblib
    import candidats
    eng = engine()
    art = joblib.load(protocole.OUT / "cache/champion_k4bis.joblib")
    modele_global = art.get("global")  # champion retenu (cf. verdicts K4/K4bis)
    print(f"[{time.strftime('%H:%M:%S')}] chargement 2026…", flush=True)
    df = protocole.load_range(eng, (protocole.SCORE_YEAR,))
    df = candidats._enrichir_k4bis(eng, df)
    import measure
    copro = measure.copro_mask(eng, df)
    p = modele_global.predict_proba(df)
    hors = ~copro
    ordre = np.argsort(-p[hors])
    idx_hors = df.index[hors].to_numpy()[ordre[:1158]]
    rng = np.random.RandomState(974)
    idx_alea = rng.choice(df.index.to_numpy(), 500, replace=False)
    idx = pd.Index(np.concatenate([idx_hors, idx_alea])).unique()
    sub = df.loc[idx].reset_index(drop=True)
    out = raisons_top3(modele_global, sub)
    out.insert(1, "p", np.round(p[df.index.get_indexer(idx)], 5))
    out.to_csv(protocole.OUT / "k6_raisons.csv", index=False)
    print(out.head(12).to_string(index=False))
    print(f"{len(out)} lignes → k6_raisons.csv")


if __name__ == "__main__":
    main()
