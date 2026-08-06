#!/usr/bin/env python
"""M39-BIS A0.2 — FUITE TEMPORELLE : test as-of sur TOUTES les features (lecture seule).

M43 a prouvé (test as-of) que « cessée »/« radiée » SUIVENT la vente. On applique le même
regard à chaque feature du modèle P : quelle part de ses valeurs est POSTÉRIEURE à l'événement
de mutation ? La réponse est DÉTERMINÉE par la discipline as-of de la source (dictionnaire de
features) — on la rend explicite, et on CHIFFRE la « fuite des couches statiques » (dette connue).

Principe (dictionnaire) : « feature as-of = événements strictement antérieurs au 01/01/Y ;
label = mutations de [01/01/Y, 31/12/Y] ». Donc :
  - DVF / Sitadel (fenêtres finissant 31/12/Y-1) + tenure/permis (as-of 01/01/Y) : 0 % postérieur.
  - Couches STATIQUES « millésime unique, ingestion 2026 » : 100 % postérieur au label 2025 —
    MAIS fuite RÉELLE seulement si l'attribut CHANGE avec la mutation (bâti/canopée/friche…),
    pas s'il est invariant (pente, surface, socio-démo, distance).
La fuite = IV cumulée des features {statique 2026 ∧ change-avec-mutation}. Borne SUPÉRIEURE
(l'IV est univariée ; la contribution marginale dans le modèle L2 est ≤). L'ablation propre
(re-scorer sans ces features) est le test définitif — signalée, non exécutée ici (retrain).

Sortie : qa/audit-rr/a0_2_anteriorite.csv. Aucune écriture DB.
"""
from __future__ import annotations

import os

import pandas as pd

IV = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "m3-p-model", "iv-features.csv")

# classification as-of, adossée au dictionnaire de features (source + fenêtre).
# classe : 'asof_dvf' / 'asof_sitadel' / 'asof_dvf_tenure' (0 % postérieur, propre) ;
#          'stat_invariant' (100 % postérieur mais n'évolue pas avec la mutation → pas de fuite) ;
#          'stat_fuite' (100 % postérieur ET change avec la mutation → FUITE) ; 'stat_zonage' (fuite partielle).
CLASSE = {
    "rot_nu": "asof_dvf", "rot_bati": "asof_dvf", "med_pm2_terrain_36m": "asof_dvf",
    "med_pm2_bati_36m": "asof_dvf", "tendance_pm2_bati": "asof_dvf", "permis_24m_norm": "asof_sitadel",
    "tenure_bin": "asof_dvf_tenure", "permis_bin": "asof_sitadel", "window_coverage": "asof_dvf",
    "filo_snv_pp": "stat_invariant", "filo_pct_pauv": "stat_invariant", "filo_pct_prop": "stat_invariant",
    "filo_dens_pop": "stat_invariant", "qpv": "stat_invariant", "pente_moy_deg": "stat_invariant",
    "acces_equipements": "stat_invariant", "surface_m2": "stat_invariant",
    "zone_plu": "stat_zonage",
    "dens_bati_secteur": "stat_fuite", "pct_bati_secteur": "stat_fuite", "nu_constructible": "stat_fuite",
    "dormance_droits": "stat_fuite", "sous_densite": "stat_fuite", "sdp_residuelle_m2": "stat_fuite",
    "canopee_pct": "stat_fuite", "ndvi_moyen": "stat_fuite", "friche": "stat_fuite",
    "piscine": "stat_fuite", "pv_candidat": "stat_fuite",
}
PCT_POST = {"asof_dvf": 0, "asof_sitadel": 0, "asof_dvf_tenure": 0,
            "stat_invariant": 100, "stat_zonage": 100, "stat_fuite": 100}
FUITE = {"asof_dvf": False, "asof_sitadel": False, "asof_dvf_tenure": False,
         "stat_invariant": False, "stat_zonage": True, "stat_fuite": True}


def main() -> None:
    iv = pd.read_csv(IV).set_index("feature")["iv"]
    rows = []
    for f, cls in CLASSE.items():
        rows.append({"feature": f, "classe_asof": cls, "pct_valeurs_posterieures": PCT_POST[cls],
                     "fuite_reelle": FUITE[cls], "iv": round(float(iv.get(f, 0.0)), 4)})
    df = pd.DataFrame(rows).sort_values("iv", ascending=False)
    iv_tot = df["iv"].sum()
    iv_fuite = df[df["fuite_reelle"]]["iv"].sum()
    iv_zonage = df[df["classe_asof"] == "stat_zonage"]["iv"].sum()
    iv_fuite_dure = df[df["classe_asof"] == "stat_fuite"]["iv"].sum()
    print("=== ANTÉRIORITÉ par feature (as-of) — top IV ===")
    for _, r in df.head(30).iterrows():
        flag = "  ⚠ FUITE" if r["fuite_reelle"] else ""
        print(f"  {r['feature']:20s} {r['classe_asof']:16s} post={r['pct_valeurs_posterieures']:>3}% "
              f"IV={r['iv']:.4f}{flag}")
    print(f"\nIV totale = {iv_tot:.4f}")
    print(f"IV fuite RÉELLE (statique 2026 ∧ change-mutation, hors zonage) = {iv_fuite_dure:.4f} "
          f"({100*iv_fuite_dure/iv_tot:.1f} % de l'IV)")
    print(f"IV zonage (fuite partielle, reclassement PLU) = {iv_zonage:.4f} ({100*iv_zonage/iv_tot:.1f} %)")
    print(f"IV fuite TOTALE (dure + zonage) = {iv_fuite:.4f} ({100*iv_fuite/iv_tot:.1f} % de l'IV) — BORNE SUP.")
    print("\n⚠ Ablation propre (re-score sans les features de fuite) = test DÉFINITIF, NON exécuté "
          "(retrain hors lecture-seule) → à faire pour trancher la contribution MARGINALE (≤ cette borne).")
    df.to_csv(os.path.join(os.path.dirname(__file__), "a0_2_anteriorite.csv"), index=False)


if __name__ == "__main__":
    main()
