"""Registre des features du modèle P — source UNIQUE du dictionnaire obligatoire.

Chaque feature déclare : bloc (Z/D), type, contrainte de monotonie (le signe est
LIBRE partout où Phase 0 l'exige), source, fenêtre temporelle et date de
disponibilité. `generate_dictionary()` produit reports/m3-p-model/dictionnaire-features.md.

Colonnes MÉTA (jamais encodées) : idu, annee, label, commune, secteur, owner_type,
n_mut_nu_36m, n_mut_bati_36m, stock_secteur (bruts servant au shrinkage).
Interdits absents par construction : statut matrice, computed_at, score V.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    bloc: str           # 'Z' | 'D'
    kind: str           # 'num' | 'cat' | 'bool'
    monotone: int       # +1 / -1 = contraint, 0 = signe libre
    source: str
    fenetre: str
    disponibilite: str
    note: str = ""


#: τ (m) de la pondération exponentielle des distances aux équipements.
EQUIP_TAU_M = 800.0

_STATIQUE = "millésime unique en base (ingestion 2026) — fuite faible, consignée"

FEATURES: list[FeatureSpec] = [
    # ============================== BLOC Z ==============================
    FeatureSpec("rot_nu", "Z", "num", +1,
                "DVF L2 dédupliqué (p_model_mut_l2) + stock parcelles",
                "36 mois glissants finissant au 31/12/Y-1 (clampés à 2021), annualisés",
                "acte publié DVF, ~6 mois de latence DGFiP",
                "rotation nu du secteur, shrinkage empirique vers le taux commune"),
    FeatureSpec("rot_bati", "Z", "num", +1,
                "DVF L2 dédupliqué + stock parcelles",
                "36 mois glissants finissant au 31/12/Y-1, annualisés",
                "acte publié DVF, ~6 mois de latence DGFiP",
                "rotation bâti du secteur, même shrinkage"),
    FeatureSpec("med_pm2_terrain_36m", "Z", "num", 0,
                "DVF L2 mutations nues (valeur / surface terrain de la mutation)",
                "36 mois finissant au 31/12/Y-1", "idem DVF"),
    FeatureSpec("med_pm2_bati_36m", "Z", "num", 0,
                "DVF L2 mutations bâties (valeur / surface bâtie de la mutation)",
                "36 mois finissant au 31/12/Y-1", "idem DVF"),
    FeatureSpec("tendance_pm2_bati", "Z", "num", 0,
                "DVF L2 : médiane €/m² bâti 12 derniers mois vs début de fenêtre",
                "[Y-1] vs [Y-3, Y-1]", "idem DVF"),
    FeatureSpec("permis_24m_norm", "Z", "num", 0,
                "Sitadel PC+PA autorisés (DATE_REELLE_AUTORISATION), rattachés au "
                "secteur via idu_codes, normalisés par le stock de parcelles",
                "24 mois finissant au 31/12/Y-1",
                "date d'autorisation connue immédiatement ; publication Dido "
                "mensuelle, latence 1-3 mois consignée"),
    FeatureSpec("dens_bati_secteur", "Z", "num", 0,
                "BD TOPO bâtiments × parcelles (emprise / surface du secteur)",
                "statique", _STATIQUE),
    FeatureSpec("pct_bati_secteur", "Z", "num", 0,
                "BD TOPO : part de parcelles bâties du secteur", "statique", _STATIQUE),
    FeatureSpec("filo_snv_pp", "Z", "num", 0,
                "Filosofi INSEE carreau 200 m : niveau de vie / individu",
                "statique (millésime Filosofi 2019)", _STATIQUE),
    FeatureSpec("filo_pct_pauv", "Z", "num", 0,
                "Filosofi 200 m : part ménages pauvres", "statique", _STATIQUE),
    FeatureSpec("filo_pct_prop", "Z", "num", 0,
                "Filosofi 200 m : part ménages propriétaires", "statique", _STATIQUE),
    FeatureSpec("filo_dens_pop", "Z", "num", 0,
                "Filosofi 200 m : individus / km²", "statique", _STATIQUE),
    FeatureSpec("qpv", "Z", "bool", 0,
                "périmètres QPV (spatial_layers kind=qpv), centroïde dans le polygone",
                "statique", _STATIQUE),
    FeatureSpec("pente_moy_deg", "Z", "num", 0,
                "RGE ALTI 5 m (parcel_terrain.pente_moy_deg)", "statique", _STATIQUE),
    FeatureSpec("acces_equipements", "Z", "num", 0,
                "OSM (parcel_amenites) : Σ exp(-dist/800 m) sur école, santé, "
                "commerce, TCSP — distance absente = contribution nulle",
                "statique", _STATIQUE),
    FeatureSpec("zone_plu", "Z", "cat", 0,
                "GPU zonage agrégé U / AU (AUc,AUs) / A / N, centroïde dans la zone ; "
                "'inconnu' explicite hors couverture",
                "statique (PLU en vigueur à l'ingestion)",
                _STATIQUE + " ; un reclassement PLU postérieur à Y peut refléter la "
                "dynamique — risque consigné, pas de zonage historisé disponible"),
    FeatureSpec("window_coverage", "Z", "num", 0,
                "mois DVF réellement disponibles dans la fenêtre 36 mois / 36",
                "par année d'observation", "déterministe",
                "dégradation des fenêtres 2022 (burn-in court) — lot 1.4"),
    # ============================== BLOC D ==============================
    FeatureSpec("nu_constructible", "D", "bool", 0,
                "BD TOPO (emprise ≤ 20 m²) × zone PLU U/AU", "statique", _STATIQUE),
    FeatureSpec("surface_m2", "D", "num", 0,
                "référentiel parcellaire (mvt_parcels/parcels)", "statique", _STATIQUE),
    FeatureSpec("dormance_droits", "D", "num", +1,
                "parcel_residuel.pct_potentiel : part du potentiel de droits PLU "
                "non consommée (BD TOPO vs droits calibrés)", "statique",
                _STATIQUE + " ; NULL = hors périmètre de calcul → bin 'manquant'"),
    FeatureSpec("sous_densite", "D", "bool", 0,
                "parcel_residuel.sous_densite", "statique", _STATIQUE),
    FeatureSpec("sdp_residuelle_m2", "D", "num", 0,
                "parcel_residuel.sdp_residuelle_m2", "statique", _STATIQUE),
    FeatureSpec("tenure_bin", "D", "cat", 0,
                "DVF toutes natures : dernière mutation avant le 01/01/Y → bins "
                "{<1, 1-2, 2-3, 3+, inconnu} — troncature 2021 assumée, le bin "
                "'inconnu' (rien depuis 2021) est explicite et sa portée varie "
                "avec Y (consigné)",
                "as-of 01/01/Y", "idem DVF"),
    FeatureSpec("permis_bin", "D", "cat", 0,
                "Sitadel 2013+ : ancienneté du dernier permis SUR la parcelle "
                "(tous types) → bins {<2a, 2-5a, 5-10a, 10a+, jamais} ; "
                "« permis < 24 mois » attendu NÉGATIF (projet en cours) — signe libre",
                "as-of 01/01/Y", "date d'autorisation, latence 1-3 mois"),
    FeatureSpec("canopee_pct", "D", "num", 0,
                "LiDAR/ortho (parcel_vegetation.canopee_pct)", "statique", _STATIQUE),
    FeatureSpec("ndvi_moyen", "D", "num", 0,
                "parcel_vegetation.ndvi_moyen", "statique", _STATIQUE),
    FeatureSpec("friche", "D", "bool", 0,
                "Cartofriches (spatial_layers kind=friche)", "statique", _STATIQUE),
    FeatureSpec("piscine", "D", "bool", 0,
                "détection ortho validée ou non-infirmée (type=piscine, hors "
                "faux_positif) — signe libre", "statique", _STATIQUE),
    FeatureSpec("pv_candidat", "D", "bool", 0,
                "candidats photovoltaïque (ortho_detections type=pv)", "statique",
                _STATIQUE),
]

FEATURE_NAMES = [f.name for f in FEATURES]
META_COLS = ["idu", "annee", "label", "commune", "secteur", "owner_type"]


def load_dataset(engine, years: tuple[int, ...]) -> pd.DataFrame:
    """Charge p_model_dataset pour les années demandées et dérive les features
    Python (shrinkage, composite équipements, renommages)."""
    yrs = ", ".join(str(int(y)) for y in years)
    df = pd.read_sql(f"SELECT * FROM p_model_dataset WHERE annee IN ({yrs})", engine)
    return derive(df)


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Features dérivées — déterministe, seed {SEED} sans objet ici (aucun aléa)."""
    df = df.copy()
    # rotations : shrinkage empirique vers le taux commune, par année et nu/bâti
    for kind in ("nu", "bati"):
        df[f"rot_{kind}"] = np.nan
        for annee, grp in df.groupby("annee"):
            df.loc[grp.index, f"rot_{kind}"] = _shrink_rotation(grp, kind)
    # composite équipements : distance absente → contribution nulle (parcelle isolée)
    acc = np.zeros(len(df))
    for col in ("dist_ecole_m", "dist_sante_m", "dist_commerce_m", "dist_tcsp_m"):
        d = pd.to_numeric(df[col], errors="coerce")
        acc = acc + np.where(d.notna(), np.exp(-d.fillna(np.inf) / EQUIP_TAU_M), 0.0)
    df["acces_equipements"] = acc
    df["dormance_droits"] = pd.to_numeric(df["pct_potentiel"], errors="coerce")
    return df


def _shrink_rotation(grp: pd.DataFrame, kind: str) -> pd.Series:
    """Shrinkage gamma-Poisson vers le taux commune.

    Exposition = stock_secteur × années couvertes ; taux secteur = n/expo.
    Force du prior m (en parcelle-années) estimée par méthode des moments sur la
    surdispersion inter-secteurs ; bornée [50, 5000] pour rester raisonnable sur
    les petits parcs. r̂ = (n + m·r_commune) / (expo + m).
    """
    sect = grp.drop_duplicates("secteur").set_index("secteur")
    n = sect[f"n_mut_{kind}_36m"].astype(float)
    yrs = (sect["window_coverage"].astype(float) * 3.0).clip(lower=1e-9)
    expo = sect["stock_secteur"].astype(float) * yrs
    commune = sect.index.str.slice(0, 5)
    r_com = (n.groupby(commune).transform("sum") / expo.groupby(commune).transform("sum"))
    # méthode des moments : var(taux vrai) ≈ var(taux observé) - E[taux/expo]
    r_obs = n / expo
    var_true = max(float(r_obs.var(ddof=1) - (r_obs / expo).mean()), 1e-12)
    m = float(np.clip(r_obs.mean() / var_true, 50.0, 5000.0))
    r_shrunk = (n + m * r_com) / (expo + m)
    return grp["secteur"].map(r_shrunk)


def generate_dictionary() -> str:
    """dictionnaire-features.md — obligatoire au mandat."""
    lines = [
        "# Dictionnaire de features — modèle P (M3, blocs Z + D)",
        "",
        "Convention as-of : pour l'année d'observation Y, toute feature n'utilise que",
        "des événements **strictement antérieurs au 01/01/Y** ; le label n'utilise que",
        "les mutations L2 de [01/01/Y, 31/12/Y]. Fenêtres clampées au 01/01/2021",
        "(millésimes DVF antérieurs retirés par la DGFiP) — la couverture réelle est",
        "portée par `window_coverage`.",
        "",
        "Interdits (absents par construction) : statut matrice, computed_at, score V",
        "(baseline lot 5 uniquement), tout calcul daté de 2026 hors couches statiques",
        "consignées ci-dessous. `owner_type` est une méta de ventilation d'évaluation,",
        "jamais une feature.",
        "",
        "| Feature | Bloc | Type | Monotonie | Source | Fenêtre | Disponibilité | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    mono = {1: "↑ contrainte", -1: "↓ contrainte", 0: "libre"}
    for f in FEATURES:
        lines.append(
            f"| `{f.name}` | {f.bloc} | {f.kind} | {mono[f.monotone]} | {f.source} "
            f"| {f.fenetre} | {f.disponibilite} | {f.note} |")
    return "\n".join(lines) + "\n"
