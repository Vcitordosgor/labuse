"""SCORING-DONNEES-1 · Lot G — le tableau unique, la recette q_v13, le top-50.

  verdicts — applique LA règle de verdict (écrite ici, une fois) à chaque ligne
             de k0_donnees1.csv → g1_verdicts.csv ;
  recette  — fit du candidat recommandé q_v13 = q_v12 + toutes les variables à
             gain prouvé, mesure K0 (ligne q_v13_candidat), puis les 50 premières
             du classement 2026 face au servi q_v11_m137 avec 3 contributions en
             français → g2_top50.csv ;
  manifeste — protocole, couvertures, variantes, verdicts → g3_manifeste.json.

Règle de verdict (chiffrée, la même pour tous) :
  GAIN   si  Δprec@100 > 0  OU  Δlift ≥ +0,02  OU  ΔAUC ≥ +0,002
             OU  Δprec_priorite ≥ +16 pts (2× le bruit ±8 du mandat — un écart
             qui ne peut PAS être du bruit ne peut pas être ignoré)
         ET  Δprec@100 ≥ 0  ET  ECE ≤ base + 5e-4 ;
  pour le Lot D (segment PM) : mêmes seuils lus sur auc/ece_personne_morale ;
  la précision Priorité (~90 parcelles, bruit ±8 pts) ne décide jamais seule
  DANS le bruit — au-delà de 2× le bruit, elle décide, et c'est écrit ici.

Usage : .venv/bin/python scripts/audit/scoring/donnees1_g.py verdicts|recette|manifeste
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donnees1_commun as dc  # noqa: E402
import donnees1_a as la  # noqa: E402
import donnees1_c as lc  # noqa: E402
import donnees1_d as ld  # noqa: E402
import donnees1_e as le  # noqa: E402
import protocole  # noqa: E402
from donnees1_commun import OUT, log  # noqa: E402
from _common import engine, SERVED_RUN, ROOT  # noqa: E402
from labuse.scoring.p_v2 import qv12  # noqa: E402

BASE_TAG = "q_v12_base"
SEUIL_LIFT, SEUIL_AUC, SEUIL_ECE = 0.02, 0.002, 5e-4
SEUIL_PRIORITE = 0.16  # 2 × le bruit ±8 pts du mandat

#: candidat → (specs, remplacees, segment) — comment le reconstruire pour q_v13
CONSTRUCTEURS = {
    "A_nu_asof": ([la.SPECS_A[0]], {"nu_constructible_v3": "nu_constructible_asof"}, None),
    "A_pct_bati_secteur_asof": ([la.SPECS_A[1]], {"pct_bati_secteur": "pct_bati_secteur_asof"}, None),
    "C_dp_parcelle_36m": ([lc.SPECS_C[0]], None, None),
    "C_pc_caduc_asof": ([lc.SPECS_C[1]], None, None),
    "C_pc_pm_sur_parcelle_pp_36m": ([lc.SPECS_C[2]], None, None),
    "E_anciennete_plu_annees": (le.SPECS_E, None, None),
    **{f"D_{s.name}": ([s], None, "personne_morale") for s in ld.SPECS_D},
}

#: phrases françaises des variables candidates (top-50)
PHRASES = {
    "nu_constructible_asof": "état bâti/nu reconstruit à la date (Sitadel + DVF)",
    "pct_bati_secteur_asof": "part de parcelles bâties du secteur, à la date",
    "dp_parcelle_36m": "déclaration préalable sur la parcelle dans les 3 ans",
    "pc_caduc_asof": "permis de construire jamais commencé, devenu caduc",
    "pc_pm_sur_parcelle_pp_36m": "permis déposé par un professionnel (SIREN) sur "
                                 "une parcelle détenue par un particulier",
    "anciennete_plu_annees": "ancienneté du PLU de la commune",
    "dirigeant_age_max_asof": "âge du dirigeant de la société propriétaire",
    "sci_agee_asof": "SCI propriétaire ancienne (20 ans et plus)",
    "bodacc_36m": "événement BODACC récent chez le propriétaire",
    "pm_entree_recente": "société propriétaire depuis moins de 2 ans",
    "ventes_pm_secteur_36m": "part des ventes du secteur parties à des sociétés",
}


def _table() -> tuple[pd.DataFrame, pd.Series]:
    t = pd.read_csv(OUT / "k0_donnees1.csv")
    base = t[t.candidat == BASE_TAG].iloc[0]
    return t, base


def _verdict_ligne(r: pd.Series, base: pd.Series) -> tuple[str, str]:
    seg = isinstance(r.get("segment_verdict"), str) and r["segment_verdict"] == "personne_morale"
    if seg:
        d_auc = r["auc_personne_morale"] - base["auc_personne_morale"]
        ece_ok = r["ece_personne_morale"] <= base["ece_personne_morale"] + SEUIL_ECE
        gagne = d_auc >= SEUIL_AUC
        chiffre = (f"AUC PM {base['auc_personne_morale']:.4f}→{r['auc_personne_morale']:.4f}, "
                   f"ECE PM {r['ece_personne_morale']:.4f}")
    else:
        d_prec = r["prec@100_commune_mediane"] - base["prec@100_commune_mediane"]
        d_lift = r["lift_decile_sup"] - base["lift_decile_sup"]
        d_auc = r["auc_global"] - base["auc_global"]
        ece_ok = r["ece_global"] <= base["ece_global"] + SEUIL_ECE
        d_prio = r["prec_priorite"] - base["prec_priorite"]
        gagne = ((d_prec > 0) or (d_lift >= SEUIL_LIFT) or (d_auc >= SEUIL_AUC)
                 or (d_prio >= SEUIL_PRIORITE))
        gagne = gagne and d_prec >= 0
        chiffre = (f"préc@100 {base['prec@100_commune_mediane']:.3f}→"
                   f"{r['prec@100_commune_mediane']:.3f}, lift "
                   f"{base['lift_decile_sup']:.3f}→{r['lift_decile_sup']:.3f}, "
                   f"AUC {base['auc_global']:.4f}→{r['auc_global']:.4f}, "
                   f"ECE {r['ece_global']:.4f}")
    if r.get("couverture_pct", 100) < dc.COUVERTURE_MIN_PCT:
        return "écartée (couverture < 5 %)", chiffre
    if not ece_ok:
        return "neutre (ECE dégradé)", chiffre
    return ("gain" if gagne else "neutre"), chiffre


def verdicts() -> pd.DataFrame:
    t, base = _table()
    rows = []
    for _, r in t.iterrows():
        if r["candidat"] in (BASE_TAG, "q_v13_candidat") or r["candidat"].endswith("combine"):
            continue
        v, chiffre = _verdict_ligne(r, base)
        rows.append({"candidat": r["candidat"], "verdict": v, "chiffres": chiffre,
                     "prec_priorite": round(r["prec_priorite"], 3),
                     "n_priorite": int(r["n_priorite"])})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "g1_verdicts.csv", index=False)
    print(out.to_string(index=False))
    return out


def _gains() -> list[str]:
    v = pd.read_csv(OUT / "g1_verdicts.csv")
    return [c for c in v[v.verdict == "gain"]["candidat"] if c in CONSTRUCTEURS]


def recette() -> None:
    eng = engine()
    gains = _gains()
    log(f"[G2] recette q_v13 = q_v12 + {gains}")
    specs, remplacees = [], {}
    for g in gains:
        s, r, _ = CONSTRUCTEURS[g]
        specs += s
        remplacees.update(r or {})

    log("[G2] colonnes candidates (toutes)…")
    dfb, seg = dc.base_enrichie(eng)
    cols = None
    besoins = {sp.name for sp in specs}
    if besoins & {"nu_constructible_asof", "pct_bati_secteur_asof"}:
        cols = la._colonnes_a(eng)
    if besoins & {s.name for s in lc.SPECS_C}:
        c = lc._colonnes_c(eng)
        pp = dfb[["idu", "annee"]].assign(_pp=(dfb["owner_type"].fillna("pp") == "pp"))
        c = c.merge(pp, on=["idu", "annee"], how="left")
        c["pc_pm_sur_parcelle_pp_36m"] = c["pc_pm_36m_brut"] & c["_pp"].fillna(True)
        c = c.drop(columns=["pc_pm_36m_brut", "_pp"])
        cols = c if cols is None else cols.merge(c, on=["idu", "annee"], how="outer")
    if besoins & {s.name for s in ld.SPECS_D}:
        d = ld._colonnes_d(eng)
        sec = ld._ventes_pm_secteur(eng)
        dsec = dfb[["idu", "annee"]].copy()
        dsec["secteur"] = dfb["secteur"].to_numpy()
        dsec = dsec.merge(sec, on=["secteur", "annee"], how="left")
        d = d.merge(dsec[["idu", "annee", "ventes_pm_secteur_36m"]],
                    on=["idu", "annee"], how="outer")
        cols = d if cols is None else cols.merge(d, on=["idu", "annee"], how="outer")
    if "anciennete_plu_annees" in besoins:
        sud = pd.read_sql(
            "SELECT insee, approbation_opp FROM sudocuh_procedures "
            "WHERE approbation_opp IS NOT NULL", eng)
        e = dfb[["idu", "annee"]].copy()
        e["insee"] = e["idu"].str.slice(0, 5)
        e = e.merge(sud, on="insee", how="left")
        asof = pd.to_datetime(e["annee"].astype(str) + "-01-01")
        anc = (asof - pd.to_datetime(e["approbation_opp"])).dt.days / 365.25
        e["anciennete_plu_annees"] = anc.where(anc >= 0)
        e = e[["idu", "annee", "anciennete_plu_annees"]]
        cols = e if cols is None else cols.merge(e, on=["idu", "annee"], how="outer")
    cols = cols[["idu", "annee"] + [sp.name for sp in specs if sp.name in cols.columns]]
    bools = [sp.name for sp in specs if sp.kind == "bool" and sp.name in cols.columns
             and sp.name != "pm_entree_recente"]

    row = dc.mesurer("q_v13_candidat", specs, colonnes=cols,
                     remplacees=remplacees, fill_false=bools)

    log("[G2] top-50 du classement 2026 face au servi…")
    df = dc._ETAT["df_mesure"]
    m = dc._ETAT["modele"]
    mask26 = (df.annee == protocole.SCORE_YEAR).to_numpy()
    d26 = df[mask26].reset_index(drop=True)
    s26 = seg[mask26].reset_index(drop=True)
    p26 = m.predict_proba(d26, s26)
    hc = ~qv12.copro_de(eng, d26)
    ordre = np.argsort(-p26)
    top = [i for i in ordre if hc[i]][:50]

    servi = pd.read_sql(
        f"SELECT parcelle_id AS idu, rang AS rang_servi, tier AS tier_servi "
        f"FROM parcel_p_score_v2 WHERE run_id = '{SERVED_RUN}'", eng).set_index("idu")
    contrib = m.contributions(d26.iloc[top])
    rows = []
    for rg, i in enumerate(top, 1):
        idu = d26["idu"].iloc[i]
        cr = contrib.iloc[rg - 1].drop(
            [c for c in contrib.columns
             if c.startswith(("annee_", "contrib_", "intercept"))],
            errors="ignore")
        phrases, vus = [], set()
        for f, v in cr.sort_values(ascending=False).items():
            if v <= 0 or len(phrases) >= 3:
                break
            if "*" in f:  # croisement : nommer les deux jambes
                a, b = f.split("*", 1)
                lib = (f"croisement {PHRASES.get(a) or _libelle_prod(a)} × "
                       f"{PHRASES.get(b) or _libelle_prod(b)}")
            else:
                lib = PHRASES.get(f) or _libelle_prod(f)
            if lib in vus:
                continue
            vus.add(lib)
            phrases.append(f"{lib} (+{v:.2f})")
        while len(phrases) < 3:
            phrases.append("—")
        srow = servi.loc[idu] if idu in servi.index else None
        rows.append({
            "rang_q_v13": rg, "idu": idu, "p_q_v13": round(float(p26[i]), 5),
            "rang_servi_q_v11_m137": int(srow["rang_servi"]) if srow is not None else None,
            "tier_servi": srow["tier_servi"] if srow is not None else "absent",
            "contribution_1": phrases[0], "contribution_2": phrases[1],
            "contribution_3": phrases[2],
        })
    t50 = pd.DataFrame(rows)
    t50.to_csv(OUT / "g2_top50.csv", index=False)
    print(t50.head(15).to_string(index=False))


def _libelle_prod(feature: str) -> str:
    from labuse.scoring.p_model.features import FEATURES
    des = {f.name: f for f in FEATURES}
    fixes = {
        "tenure_bin_v2": "ancienneté de détention",
        "nu_constructible_v3": "terrain nu avec droits à bâtir",
        "sdp_residuelle_v2_m2": "surface encore constructible",
        "sous_densite_v2": "parcelle sous-densifiée",
        "residuel_famille": "nature du potentiel résiduel",
        "ventes_150m_12m": "ventes à moins de 150 m (12 mois)",
        "ventes_150m_24m": "ventes à moins de 150 m (24 mois)",
        "ventes_400m_12m": "ventes à moins de 400 m (12 mois)",
        "ventes_400m_24m": "ventes à moins de 400 m (24 mois)",
        "ventes_400m_delta": "accélération des ventes autour",
        "permis_100m_24m": "permis à moins de 100 m",
        "operations_pa_400m_24m": "opération d'aménageur à proximité",
        "volume_commune_a1": "volume de ventes de la commune",
        "med_pm2_commune_a1": "prix médian de la commune",
        "tendance_volume_3ans": "tendance du volume de ventes",
        "pm_vendeur_actif": "propriétaire société déjà vendeur",
        "rot_nu": "rotation des terrains nus du secteur",
        "rot_bati": "rotation du bâti du secteur",
        "med_pm2_terrain_36m": "prix médian du terrain (secteur)",
        "med_pm2_bati_36m": "prix médian du bâti (secteur)",
        "tendance_pm2_bati": "tendance des prix du bâti",
        "dens_bati_secteur": "densité bâtie du secteur",
        "pct_bati_secteur": "part de parcelles bâties du secteur",
        "filo_snv_pp": "niveau de vie du carreau",
        "filo_pct_pauv": "part de ménages pauvres du carreau",
        "filo_pct_prop": "part de propriétaires du carreau",
        "pente_moy_deg": "pente du terrain",
        "zone_plu": "zone du PLU",
        "surface_m2": "surface de la parcelle",
        "permis_bin": "ancienneté du dernier permis",
        "piscine": "piscine détectée",
        "pv_candidat": "toiture candidate au photovoltaïque",
    }
    if feature in fixes:
        return fixes[feature]
    if feature in des:
        return des[feature].desc.split(" (")[0][:60] if hasattr(des[feature], "desc") else feature
    return feature


def manifeste() -> None:
    t, base = _table()
    v = pd.read_csv(OUT / "g1_verdicts.csv")
    fuite = {}
    p = ROOT / "reports/q-v12/q_v12_test_fuite.csv"
    if p.exists():
        fuite = pd.read_csv(p).iloc[0].to_dict()
    man = {
        "mandat": "SCORING-DONNEES-1",
        "gel": time.strftime("%Y-%m-%d %H:%M:%S"),
        "protocole": {
            "banc": "K0 (protocole.py SCORING-2) : train 2017-2023, calibration "
                    "2024, test 2025 (année vierge)",
            "point_de_depart": "recette q_v12 (qv12.fit_qv12 : K1c censoring + K2 "
                               "mortes retirées + K3 résiduel 100 % + K4bis "
                               "voisinage global + isotonique par segment 2024)",
            "regle_mesure": "chaque variable mesurée SEULE ajoutée au candidat ; "
                            "as-of obligatoire sinon documentée non mesurée ; "
                            "couverture < 5 % → notée non candidate",
            "regle_verdict": f"gain si Δpréc@100 > 0 OU Δlift ≥ {SEUIL_LIFT} OU "
                             f"ΔAUC ≥ {SEUIL_AUC} OU ΔPriorité ≥ {SEUIL_PRIORITE} "
                             f"(2× le bruit ±8 pts), avec Δpréc@100 ≥ 0 et "
                             f"ECE ≤ base + {SEUIL_ECE} ; segment PM pour le Lot D",
            "hygiene_cible": dc._ETAT.get("ctx").hygiene_cr if dc._ETAT.get("ctx") else
                             "cf. reports/score-v2-arene/k0_hygiene.csv",
            "test_fuite_k4bis": fuite,
        },
        "reproduction_baseline": {
            "q_v12_base_vs_q_v12": "AUC et lift identiques à 1e-6 "
                                   "(k0_donnees1.csv vs k0_table.csv)"},
        "variantes_mesurees": json.loads(
            t.drop(columns=["coefs_candidates"], errors="ignore")
            .to_json(orient="records")),
        "verdicts": json.loads(v.to_json(orient="records")),
        "non_mesures_asof_impossible": [
            "zone PLU as-of (aucune archive GPU par parcelle)",
            "division cadastrale (aucune date de création de parcelle)",
            "emplacements réservés / prescriptions GPU (un seul millésime)",
            "commune en procédure (procédures closes sans historique)",
            "veille succession telle quelle (computed_at 2026 — recalculée as-of)",
            "permis refusés (Sitadel ne publie que les autorisés)",
        ],
        "notes_non_candidates": [
            "DPE frais : 17 lignes en base (couverture ~0,004 %)",
            "Radar agrégé : série de 2 jours, infaisable",
            "BDNB : 974 absent de l'export 2026-02.a (sonde S3)",
        ],
        "servi_intact": f"{SERVED_RUN} reste le run servi ; aucun run lancé, "
                        "aucune table servie écrite",
    }
    (OUT / "g3_manifeste.json").write_text(
        json.dumps(man, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log("manifeste écrit")


if __name__ == "__main__":
    {"verdicts": verdicts, "recette": recette, "manifeste": manifeste}[
        sys.argv[1] if len(sys.argv) > 1 else "verdicts"]()
