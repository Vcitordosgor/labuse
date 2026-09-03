"""SCORING-3 · L1 — l'arène du candidat q_v12 : fit, mesure K0, gel, garde de churn.

La recette (labuse.scoring.p_v2.qv12 — SOURCE UNIQUE, le pipeline réel score avec
le même code) : K1c censoring + K2 mortes retirées + K3 résiduel 100 % + K4 bis
voisinage GLOBAL + isotonique PAR SEGMENT (2024). Horizon 12 mois (protocole K0)
+ modèle 24 mois (protocole K1 bis : train ≤2022, cal 2023, test 2024).

Sous-commandes :
  fit    — fit les deux modèles, mesure au banc K0 (lignes `q_v12` et
           `q_v12_24m_test2024` de k0_table.csv), GÈLE les artefacts
           (reports/q-v12/, sha256 au manifeste) + note de version composée.
  fuite  — test de fuite dédié (mêmes requêtes que le pipeline, code qv12).
  churn  — APRÈS le run réel : churn top-1158 q_v12 vs q_v11_m137 + les 50
           premières sorties de Priorité avec la raison (L1.4).
  verif  — APRÈS le run réel : coïncidence sur 1 000 parcelles tirées au hasard
           (seed 974) entre le p_raw stocké du run réel et la prédiction de
           l'artefact via le chemin d'arène (L1.2, écart médian < 1e-6).

Doctrine : rien de servi ne change ; q_v11_m137 reste le run servi.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidats  # noqa: E402 — charger_label24/appliquer_label24 (K1 bis)
import protocole  # noqa: E402
from _common import engine, ROOT, SERVED_RUN  # noqa: E402
from labuse.scoring.p_v2 import qv12  # noqa: E402

OUT = protocole.OUT
CACHE = ROOT / "reports/score-v2-arene/cache"
YEARS = tuple(range(2017, 2027))
QDIR = ROOT / "reports/q-v12"
QDIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _charger_enrichi(eng) -> pd.DataFrame:
    log("chargement 2017-2026 (dataset ext)…")
    df = protocole.load_range(eng, YEARS)
    log("enrichissement recette q_v12 (censoring + résiduel + voisinage, caches arène)…")
    return qv12.enrichir(eng, df, YEARS, cache_dir=CACHE)


def note_de_version(row_base: dict, row_q: dict, row_24: dict) -> str:
    """La note en français que Vic lira à la bascule — composée DEPUIS les
    chiffres mesurés au banc K0, jamais écrite à la main."""
    ratio = (row_q["n_priorite"] / row_base["n_priorite"]
             if row_base.get("n_priorite") else float("nan"))
    return "\n".join([
        f"Candidat q_v12 du {date.today().strftime('%d/%m/%Y')} — les gains sûrs "
        "de SCORING-2, produits par le pipeline réel.",
        "",
        "Ce qui change : 4 variables mortes + 5 retired retirées (K2) · résiduel "
        "lu à 100 % (zéros M125, hors_plu seul inconnu — K3) · voisinage et "
        "marché as-of, architecture globale (K4 bis, fuite testée) · calibration "
        "isotonique par segment sur 2024 (seul apport de K4 retenu) · censoring "
        "explicite (détention/permis couverts à 100 %). Horizon 12 mois servi ; "
        "24 mois calculé et stocké (p_24m), rien d'affiché.",
        "",
        "Les chiffres (banc K0, année vierge 2025 : train ≤2023, cal 2024) :",
        f"- précision@100 par commune (médiane) : {row_base['prec@100_commune_mediane']:.3f} "
        f"→ {row_q['prec@100_commune_mediane']:.3f} ;",
        f"- Priorité : {row_base['prec_priorite']:.1%} sur {row_base['n_priorite']:.0f} "
        f"parcelles → {row_q['prec_priorite']:.1%} sur {row_q['n_priorite']:.0f} "
        f"(effectif ×{ratio:.1f}) ;",
        f"- lift du décile supérieur : {row_base['lift_decile_sup']:.2f} → "
        f"{row_q['lift_decile_sup']:.2f} ;",
        f"- AUC global : {row_base['auc_global']:.3f} → {row_q['auc_global']:.3f} "
        f"(nu {row_q['auc_terrain_nu']:.3f}, PM {row_q['auc_personne_morale']:.3f}) ;",
        f"- ECE global : {row_q['ece_global']:.4f} "
        f"(par segment : bâti {row_q['ece_bati_individuel']:.4f}, "
        f"nu {row_q['ece_terrain_nu']:.4f}, PM {row_q['ece_personne_morale']:.4f}, "
        f"copro {row_q['ece_copropriete']:.4f}) ;",
        f"- churn top-1158 vs le run servi : {row_q['churn_top1158_vs_servi']:.1%} "
        "(la garde de churn liste les sorties de Priorité au compte-rendu) ;",
        f"- horizon 24 mois (test 2024) : AUC {row_24['auc_global']:.3f}, "
        f"préc@100 méd {row_24['prec@100_commune_mediane']:.3f} — colonne stockée.",
        "",
        f"Rien de servi ne change tant que la bascule n'est pas faite : "
        f"`{SERVED_RUN}` reste le run servi. La bascule est un geste manuel "
        "(Données › Circuit › Basculer), réversible (retour arrière tracé).",
    ])


def fit() -> None:
    eng = engine()
    log("[q_v12] test de fuite dédié (2025)…")
    fuite = test_fuite(eng)
    assert not fuite["fuite_detectee"], "FUITE dans les features de voisinage"

    df = _charger_enrichi(eng)
    names, specs, inter = qv12.features_qv12()
    log(f"[q_v12] {len(names)} features, {len(inter)} interactions")
    copro = qv12.copro_de(eng, df)
    seg_all = qv12.segmenter(df, copro)

    log("[q_v12] fit 12 mois (global ≤2023, iso par segment 2024)…")
    m12 = qv12.fit_qv12(df, seg_all, names, specs, inter)

    log("[q_v12] mesure K0 (test 2025)…")
    ctx = protocole.Contexte(eng, df[df.annee == protocole.TEST_YEAR],
                             df[df.annee == protocole.SCORE_YEAR])
    seg_test = seg_all[(df.annee == protocole.TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = m12.predict_proba(ctx.test, seg_test)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    cd = m12.contributions(ctx.test)[
        [c for c in d_feats if c in m12.base.coefs]].sum(axis=1).to_numpy()
    p26 = m12.predict_proba(ctx.score26, seg_26)
    row_q = protocole.metriques(ctx, "q_v12", p, cd, p26)
    protocole.enregistrer(row_q)

    log("[q_v12] fit 24 mois (≤2022, cal 2023, test 2024 — K1 bis)…")
    df = candidats.appliquer_label24(df, candidats.charger_label24(eng))
    m24 = qv12.fit_qv12(df, seg_all, names, specs, inter, label_col="label_24m",
                        train_max=qv12.TRAIN_MAX_24M, cal_year=qv12.CAL_YEAR_24M)
    ctx24 = protocole.Contexte(eng, df[df.annee == 2024],
                               df[df.annee == protocole.SCORE_YEAR],
                               label_col="label_24m", annee_test=2024,
                               horizon_mois=24)
    seg_24 = seg_all[(df.annee == 2024).to_numpy()].reset_index(drop=True)
    p_t24 = m24.predict_proba(ctx24.test, seg_24)
    cd24 = m24.contributions(ctx24.test)[
        [c for c in d_feats if c in m24.base.coefs]].sum(axis=1).to_numpy()
    p26_24 = m24.predict_proba(ctx24.score26, seg_26)
    row_24 = protocole.metriques(ctx24, "q_v12_24m_test2024", p_t24, cd24, p26_24)
    table = protocole.enregistrer(row_24)

    log("[q_v12] gel des artefacts + manifeste…")
    row_base = table[table.candidat == "ligne_de_base"].iloc[0].to_dict()
    note = note_de_version(row_base, row_q, row_24)
    df26 = df[df.annee == protocole.SCORE_YEAR]
    couv = [{"feature": n,
             "pct_non_null": round(100 * float(df26[n].notna().mean()), 2)
             if n in df26.columns else None} for n in names]
    millesimes = json.loads(pd.read_sql(
        "SELECT name, source_millesime, last_sync_at::date AS ingere_le "
        "FROM data_sources WHERE source_millesime IS NOT NULL ORDER BY name",
        eng).to_json(orient="records", date_format="iso"))
    manifeste = {
        "candidat": qv12.QV12_VERSION,
        "gel": time.strftime("%Y-%m-%d %H:%M:%S"),
        "doctrine": "calculé par le pipeline réel, jamais basculé — "
                    f"{SERVED_RUN} reste le run servi (bascule = geste Vic)",
        "recette": "K1c censoring + K2 mortes retirées + K3 résiduel 100 % + "
                   "K4bis voisinage GLOBAL + isotonique PAR SEGMENT (2024) ; "
                   "12 mois servi, 24 mois stocké (p_24m)",
        "protocole_12m": {"train": f"{qv12.TRAIN_MIN}-{qv12.TRAIN_MAX}",
                          "calibration": qv12.CAL_YEAR, "test": protocole.TEST_YEAR},
        "protocole_24m": {"train": f"{qv12.TRAIN_MIN}-{qv12.TRAIN_MAX_24M}",
                          "calibration": qv12.CAL_YEAR_24M, "test": 2024,
                          "motif": "seule année de test à fenêtre 24 mois complète "
                                   "(DVF s'arrête au 31/12/2025)"},
        "recale_intercept": "non — la calibration est l'isotonique par segment "
                            "(2024), exactement ce que l'arène a mesuré",
        "hygiene_cible": ctx.hygiene_cr,
        "segments": {s: int((seg_all == s).sum()) for s in qv12.SEGMENTS},
        "n_features": len(names), "interactions": inter,
        "features_couverture_2026": couv,
        "test_fuite": fuite,
        "metriques_k0_2025": {k: (None if isinstance(v, float) and np.isnan(v) else v)
                              for k, v in row_q.items()},
        "metriques_24m_test2024": {k: (None if isinstance(v, float) and np.isnan(v) else v)
                                   for k, v in row_24.items()},
        "millesimes_sources": millesimes,
        "note_de_version": note,
    }
    manifeste = qv12.geler_artifacts(m12, m24, manifeste)
    (QDIR / "NOTE-DE-VERSION-q_v12.md").write_text(note + "\n", encoding="utf-8")

    # round-trip : l'artefact rechargé doit prédire EXACTEMENT pareil (gel sain)
    m12b, _, _ = qv12.verify_artifacts()
    ech = ctx.test.sample(n=2000, random_state=974)
    seg_ech = seg_test.loc[ech.index]
    assert np.allclose(m12b.predict_proba(ech, seg_ech),
                       m12.predict_proba(ech, seg_ech)), "round-trip artefact KO"
    log(f"[q_v12] gelé : {manifeste['sha256_12m'][:16]}… / "
        f"{manifeste['sha256_24m'][:16]}…")
    print(table.to_string(index=False))
    print("\n" + note)


def test_fuite(eng, annee: int = 2025) -> dict:
    """Test de fuite sur le code qv12 (mêmes requêtes que le pipeline réel)."""
    asof = f"{annee}-01-01"
    livre_v = qv12._ventes_annee(eng, annee).set_index("idu").sort_index()
    tronque_v = qv12._ventes_annee(eng, annee, date_max=asof).set_index("idu").sort_index()
    livre_p = qv12._permis_annee(eng, annee).set_index("idu").sort_index()
    tronque_p = qv12._permis_annee(eng, annee, date_max=asof).set_index("idu").sort_index()
    verdict = {
        "annee_testee": annee,
        "ventes_voisines_egales_source_tronquee": bool(livre_v.equals(tronque_v)),
        "permis_voisins_egaux_source_tronquee": bool(livre_p.equals(tronque_p)),
        "asof": asof,
        "fuite_detectee": not (livre_v.equals(tronque_v) and livre_p.equals(tronque_p)),
    }
    pd.DataFrame([verdict]).to_csv(QDIR / "q_v12_test_fuite.csv", index=False)
    print(verdict)
    return verdict


# ─────────────────────────── après le run réel ───────────────────────────

PRIORITE_TIERS = ("chaude", "brulante")   # tiers servis « Priorité »


def churn() -> None:
    """L1.4 — la garde de churn : top-1158 q_v12 vs servi + les 50 premières
    sorties de Priorité avec la raison. Lit les DEUX runs stockés (le run réel)."""
    eng = engine()
    servi = pd.read_sql(
        f"SELECT parcelle_id AS idu, p_raw, rang, tier, top5_contributions "
        f"FROM parcel_p_score_v2 WHERE run_id = '{SERVED_RUN}' AND NOT copro", eng)
    cand = pd.read_sql(
        "SELECT parcelle_id AS idu, p_raw, rang, tier "
        "FROM parcel_p_score_v2 WHERE run_id = 'q_v12' AND NOT copro", eng)
    top_s = set(servi.nsmallest(1158, "rang")["idu"])
    top_c = set(cand.nsmallest(1158, "rang")["idu"])
    churn_1158 = 1.0 - len(top_s & top_c) / 1158

    prio_s = servi[servi["tier"].isin(PRIORITE_TIERS)]
    prio_c = set(cand[cand["tier"].isin(PRIORITE_TIERS)]["idu"])
    sorties = prio_s[~prio_s["idu"].isin(prio_c)].sort_values("rang")
    log(f"churn top-1158 : {churn_1158:.1%} ; Priorité servie {len(prio_s)}, "
        f"candidate {len(prio_c)}, sorties {len(sorties)}")

    # raisons : recette rejouée sur les parcelles sorties (features 2026 enrichies)
    sub_idus = list(sorties["idu"].head(50))
    df26 = protocole.load_range(eng, (protocole.SCORE_YEAR,))
    df26 = df26[df26["idu"].isin(sub_idus)].reset_index(drop=True)
    df26 = qv12.enrichir(eng, df26, (protocole.SCORE_YEAR,), cache_dir=CACHE)
    m12, _, _ = qv12.verify_artifacts()
    contrib = m12.contributions(df26)
    vois_z = [s.name for s in qv12.SPECS_VOISINAGE
              if s.bloc == "Z" and s.name in contrib.columns]
    retirees = set(qv12.MORTES_K2) | set(qv12.RETIREES_M35)

    top5_servi = {r["idu"]: (r["top5_contributions"] or [])
                  for _, r in servi[servi["idu"].isin(sub_idus)].iterrows()}
    rows = []
    for i, idu in enumerate(df26["idu"]):
        t5 = top5_servi.get(idu, [])
        contrib_retiree = sum(e.get("log_hazard", 0) for e in t5
                              if e.get("feature", "").split("*")[0] in retirees
                              and e.get("log_hazard", 0) > 0)
        fam = df26["residuel_famille"].iloc[i]
        sdp_v2 = df26["sdp_residuelle_v2_m2"].iloc[i]
        residuel_corrige = (fam != "calculee") or (
            pd.notna(sdp_v2) and sdp_v2 == 0
            and pd.isna(pd.to_numeric(df26["sdp_residuelle_m2"].iloc[i],
                                      errors="coerce")))
        vz = float(contrib[vois_z].iloc[i].sum()) if vois_z else 0.0
        if contrib_retiree > 0.05:
            raison = ("variable retirée : le score servi s'appuyait sur une "
                      "variable morte (K2) qui ne compte plus")
        elif residuel_corrige:
            raison = ("résiduel corrigé : la SDP résiduelle vaut 0 (lue) là où "
                      "le feature store servait « inconnue » (K3)")
        elif vz < -0.05:
            raison = ("voisinage défavorable : peu de ventes/permis autour de la "
                      "parcelle (K4 bis) — le voisinage redistribue la tête")
        else:
            raison = ("redistribution de la tête : recalibration par segment et "
                      "effectif Priorité élargi déplacent la frontière du palier")
        srow = sorties[sorties["idu"] == idu].iloc[0]
        rows.append({"idu": idu, "rang_servi": int(srow["rang"]),
                     "tier_servi": srow["tier"],
                     "contrib_vois_z": round(vz, 4),
                     "contrib_retiree_servie": round(contrib_retiree, 4),
                     "residuel_famille": fam, "raison": raison})
    out = pd.DataFrame(rows)
    out.to_csv(QDIR / "q_v12_sorties_priorite.csv", index=False)
    resume = {"churn_top1158_vs_servi": round(churn_1158, 4),
              "n_priorite_servi": int(len(prio_s)),
              "n_priorite_candidat": int(len(prio_c)),
              "n_sorties_priorite": int(len(sorties)),
              "raisons": out["raison"].str.split(" :").str[0].value_counts().to_dict()}
    pd.DataFrame([resume]).to_csv(QDIR / "q_v12_churn.csv", index=False)
    print(json.dumps(resume, indent=2, ensure_ascii=False))
    print(out.head(50).to_string(index=False))


def verif() -> None:
    """L1.2 — coïncidence run réel / arène : 1 000 parcelles tirées au hasard
    (seed 974), p_raw stocké vs artefact via le chemin d'arène. Attendu :
    écart médian < 1e-6 (p_raw stocké est arrondi à 1e-6). Les parcelles sous
    pondération AU (politique de RANG du pipeline, hors modèle) sont signalées."""
    eng = engine()
    stored = pd.read_sql(
        "SELECT parcelle_id AS idu, p_raw FROM parcel_p_score_v2 "
        "WHERE run_id = 'q_v12'", eng)
    ech = stored.sample(n=1000, random_state=974).reset_index(drop=True)
    df = protocole.load_range(eng, (protocole.SCORE_YEAR,))
    df = df[df["idu"].isin(set(ech["idu"]))].reset_index(drop=True)
    # enrichissement SANS cache : mêmes requêtes fraîches que le pipeline réel
    df = qv12.enrichir(eng, df, (protocole.SCORE_YEAR,))
    m12, _, _ = qv12.verify_artifacts()
    copro = qv12.copro_de(eng, df)
    seg = qv12.segmenter(df, copro)
    p = m12.predict_proba(df, seg)
    j = df[["idu"]].assign(p_arene=p).merge(ech, on="idu")
    # parcelles sous pondération AU (le pipeline multiplie p AVANT stockage)
    au = pd.read_sql(
        "SELECT a.idu FROM parcel_au_statut a "
        "JOIN parcels ap ON ap.id = a.parcel_id WHERE a.classe = 'au_sous_plancher'",
        eng) if pd.read_sql("SELECT to_regclass('parcel_au_statut') t", eng)["t"].iloc[0] \
        else pd.DataFrame(columns=["idu"])
    j["ponderee_au"] = j["idu"].isin(set(au["idu"]))
    j["ecart"] = (j["p_arene"] - j["p_raw"]).abs()
    hors_au = j[~j["ponderee_au"]]
    verdict = {
        "n": int(len(j)), "n_ponderees_au": int(j["ponderee_au"].sum()),
        "ecart_median": float(j["ecart"].median()),
        "ecart_max_hors_au": float(hors_au["ecart"].max()),
        "ecart_median_hors_au": float(hors_au["ecart"].median()),
        "n_ecart_gt_1e6_hors_au": int((hors_au["ecart"] > 1e-6).sum()),
        "explication_au": "les parcelles au_sous_plancher portent la pondération "
                          "de RANG du pipeline (option B, hors modèle) — écart attendu",
    }
    j.to_csv(QDIR / "q_v12_verif_1000.csv", index=False)
    pd.DataFrame([verdict]).to_csv(QDIR / "q_v12_verif.csv", index=False)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    assert verdict["ecart_median"] < 1e-6, "écart médian ≥ 1e-6 — à expliquer avant d'aller plus loin"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fit"
    if cmd == "fuite":
        test_fuite(engine())
    else:
        {"fit": fit, "churn": churn, "verif": verif}[cmd]()
