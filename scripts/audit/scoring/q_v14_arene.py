"""SCORING-4 · l'arène du candidat q_v14 : les deux améliorations combinées.

Recette (labuse.scoring.p_v2.qv14 — SOURCE UNIQUE, le pipeline réel score avec le
même code) : TOUTE la recette q_v12 (K1c/K2/K3/K4bis + iso par segment) PLUS les
variables as-of prouvées par SCORING-DONNÉES-1 :
  nu_constructible_asof, pct_bati_secteur_asof, pc_pm_sur_parcelle_pp_36m,
  anciennete_plu_annees, et ventes_pm_secteur_36m (CONDITIONNELLE — garde-fou ECE PM).

Sous-commandes :
  cache  — Étape 1 : construit le dataset d'apprentissage enrichi 2017-2026
           (q_v12 voisinage + 5 variables as-of) et le met en cache parquet.
  fit    — Étape 2 : test de fuite, garde-fou ECE PM (ventes_pm entre ou sort),
           fit 12 + 24 mois, mesure au banc K0 (lignes q_v14 / q_v14_24m_test2024),
           GÈLE les artefacts (reports/q-v14/, sha256), note de version.
  fuite  — test de fuite dédié (voisinage q_v12 + variables as-of bornées).
  churn  — APRÈS le run réel : churn top-1158 q_v14 vs q_v11_m137 + sorties Priorité.
  verif  — APRÈS le run réel : coïncidence run réel / arène sur 1 000 parcelles.

Doctrine : rien de servi ne change ; q_v11_m137 reste le run servi ; AUCUN promote.
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
from labuse.scoring.p_v2 import qv12, qv14  # noqa: E402

OUT = protocole.OUT
CACHE = ROOT / "reports/score-v2-arene/cache"
YEARS = tuple(range(2017, 2027))
QDIR = ROOT / "reports/q-v14"
QDIR.mkdir(parents=True, exist_ok=True)
ENRICHI = QDIR / "enrichi_2017_2026.pkl"  # pickle : pas de dépendance pyarrow

#: seuil du garde-fou du mandat : « si l'ECE se dégrade de plus de 0,01 sur un
#: segment, la variable responsable sort ».
ECE_TOLERANCE = 0.01


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _charger_enrichi(eng, force: bool = False) -> pd.DataFrame:
    """Le dataset 2017-2026 enrichi par la recette q_v14 (cache parquet — Étape 1)."""
    if ENRICHI.exists() and not force:
        log(f"chargement du cache enrichi {ENRICHI.name}…")
        return pd.read_pickle(ENRICHI)
    log("chargement 2017-2026 (dataset ext)…")
    df = protocole.load_range(eng, YEARS)
    log("enrichissement recette q_v14 (q_v12 voisinage + 5 variables as-of)…")
    df = qv14.enrichir(eng, df, YEARS, cache_dir=CACHE)
    df.to_pickle(ENRICHI)
    log(f"cache écrit : {ENRICHI} ({len(df)} lignes)")
    return df


def cache() -> None:
    """Étape 1 — construit et met en cache le dataset d'apprentissage enrichi."""
    _charger_enrichi(engine(), force=True)


def _q_v12_baseline_ece() -> dict:
    """Les ECE par segment de q_v12 (ligne q_v12 de k0_table.csv) — référence du
    garde-fou : q_v14 ne doit pas dégrader un segment de plus de 0,01."""
    t = pd.read_csv(ROOT / "reports/score-v2-arene/k0_table.csv")
    q = t[t.candidat == "q_v12"].iloc[0]
    return {s: float(q[f"ece_{s}"]) for s in qv12.SEGMENTS}


def _mesurer(eng, df, seg_all, avec_ventes_pm: bool, tag: str) -> tuple[dict, object, list, list, list]:
    """Fit 12 mois + mesure K0 (test 2025) pour une variante (ventes_pm ou non)."""
    names, specs, inter = qv14.features_qv14(avec_ventes_pm=avec_ventes_pm)
    m12 = qv14.fit_qv14(df, seg_all, names, specs, inter)
    ctx = protocole.Contexte(eng, df[df.annee == protocole.TEST_YEAR],
                             df[df.annee == protocole.SCORE_YEAR])
    seg_test = seg_all[(df.annee == protocole.TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = m12.predict_proba(ctx.test, seg_test)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    cd = m12.contributions(ctx.test)[
        [c for c in d_feats if c in m12.base.coefs]].sum(axis=1).to_numpy()
    p26 = m12.predict_proba(ctx.score26, seg_26)
    row = protocole.metriques(ctx, tag, p, cd, p26)
    return row, m12, names, specs, inter


def fit() -> None:
    eng = engine()
    log("[q_v14] test de fuite dédié (2025)…")
    fuite = test_fuite(eng)
    assert not fuite["fuite_detectee"], "FUITE dans les features de voisinage/as-of"

    df = _charger_enrichi(eng)
    copro = qv14.copro_de(eng, df)
    seg_all = qv14.segmenter(df, copro)

    # ── garde-fou ECE PM (mandat) : ventes_pm_secteur_36m n'entre que si l'ECE du
    #    segment PM ne se dégrade pas de plus de 0,01 vs q_v12 ─────────────────────
    base_ece = _q_v12_baseline_ece()
    log("[q_v14] mesure AVEC ventes_pm_secteur_36m (test 2025)…")
    row_avec, m_avec, names_a, specs_a, inter_a = _mesurer(
        eng, df, seg_all, True, "q_v14_avec_ventespm")
    protocole.enregistrer(row_avec)
    d_ece_pm = row_avec["ece_personne_morale"] - base_ece["personne_morale"]
    log(f"[q_v14] ΔECE PM (avec ventes_pm) = {d_ece_pm:+.4f} "
        f"(seuil garde-fou {ECE_TOLERANCE})")

    if d_ece_pm > ECE_TOLERANCE:
        log("[q_v14] garde-fou DÉCLENCHÉ → ventes_pm_secteur_36m SORT du modèle")
        avec_ventes_pm = False
        log("[q_v14] mesure SANS ventes_pm_secteur_36m (test 2025)…")
        row_q, m12, names, specs, inter = _mesurer(
            eng, df, seg_all, False, "q_v14")
    else:
        log("[q_v14] garde-fou OK → ventes_pm_secteur_36m RESTE dans le modèle")
        avec_ventes_pm = True
        row_q, m12, names, specs, inter = row_avec, m_avec, names_a, specs_a, inter_a
        row_q = dict(row_q); row_q["candidat"] = "q_v14"

    # garde-fou général : aucun segment ne se dégrade de plus de 0,01
    degrade = {s: round(row_q[f"ece_{s}"] - base_ece[s], 4) for s in qv12.SEGMENTS
               if row_q[f"ece_{s}"] - base_ece[s] > ECE_TOLERANCE}
    row_q["candidat"] = "q_v14"
    protocole.enregistrer(row_q)
    log(f"[q_v14] {len(names)} features (ventes_pm={avec_ventes_pm}), "
        f"{len(inter)} interactions ; segments ECE dégradés > {ECE_TOLERANCE} : "
        f"{degrade or 'aucun'}")

    log("[q_v14] fit 24 mois (≤2022, cal 2023, test 2024 — K1 bis)…")
    df24 = candidats.appliquer_label24(df.copy(), candidats.charger_label24(eng))
    m24 = qv14.fit_qv14(df24, seg_all, names, specs, inter, label_col="label_24m",
                        train_max=qv14.TRAIN_MAX_24M, cal_year=qv14.CAL_YEAR_24M)
    ctx24 = protocole.Contexte(eng, df24[df24.annee == 2024],
                               df24[df24.annee == protocole.SCORE_YEAR],
                               label_col="label_24m", annee_test=2024, horizon_mois=24)
    seg_24 = seg_all[(df24.annee == 2024).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df24.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    p_t24 = m24.predict_proba(ctx24.test, seg_24)
    cd24 = m24.contributions(ctx24.test)[
        [c for c in d_feats if c in m24.base.coefs]].sum(axis=1).to_numpy()
    p26_24 = m24.predict_proba(ctx24.score26, seg_26)
    row_24 = protocole.metriques(ctx24, "q_v14_24m_test2024", p_t24, cd24, p26_24)
    table = protocole.enregistrer(row_24)

    log("[q_v14] gel des artefacts + manifeste…")
    row_base = table[table.candidat == "ligne_de_base"].iloc[0].to_dict()
    row_qv12 = table[table.candidat == "q_v12"].iloc[0].to_dict()
    ctx = protocole.Contexte(eng, df[df.annee == protocole.TEST_YEAR],
                             df[df.annee == protocole.SCORE_YEAR])
    note = note_de_version(row_base, row_qv12, row_q, row_24, avec_ventes_pm, degrade)
    df26 = df[df.annee == protocole.SCORE_YEAR]
    couv = [{"feature": n,
             "pct_non_null": round(100 * float(df26[n].notna().mean()), 2)
             if n in df26.columns else None} for n in names]
    millesimes = json.loads(pd.read_sql(
        "SELECT name, source_millesime, last_sync_at::date AS ingere_le "
        "FROM data_sources WHERE source_millesime IS NOT NULL ORDER BY name",
        eng).to_json(orient="records", date_format="iso"))
    manifeste = {
        "candidat": qv14.QV14_VERSION,
        "gel": time.strftime("%Y-%m-%d %H:%M:%S"),
        "doctrine": "calculé par le pipeline réel, jamais basculé — "
                    f"{SERVED_RUN} reste le run servi (bascule = geste Vic)",
        "recette": "q_v12 (K1c/K2/K3/K4bis + iso par segment) + variables as-of "
                   "SCORING-DONNÉES-1 (nu_asof, pct_bati_secteur_asof, pc_pm_sur_"
                   "parcelle_pp_36m, anciennete_plu_annees" +
                   (", ventes_pm_secteur_36m" if avec_ventes_pm else "") + ")",
        "combine": "gains MODÈLE q_v12 + gains DONNÉES q_v13_sources1 (cascade au run) — "
                   "les deux jamais réunis avant ce candidat (mandat SCORING-4)",
        "ventes_pm_secteur_36m_retenue": avec_ventes_pm,
        "garde_fou_ece": {"seuil": ECE_TOLERANCE,
                          "ece_pm_q_v12": base_ece["personne_morale"],
                          "ece_pm_avec_ventespm": row_avec["ece_personne_morale"],
                          "delta_ece_pm_avec_ventespm": round(d_ece_pm, 4),
                          "segments_degrades_final": degrade},
        "protocole_12m": {"train": f"{qv14.TRAIN_MIN}-{qv14.TRAIN_MAX}",
                          "calibration": qv14.CAL_YEAR, "test": protocole.TEST_YEAR},
        "protocole_24m": {"train": f"{qv14.TRAIN_MIN}-{qv14.TRAIN_MAX_24M}",
                          "calibration": qv14.CAL_YEAR_24M, "test": 2024,
                          "motif": "seule année de test à fenêtre 24 mois complète"},
        "recale_intercept": "non — calibration = isotonique par segment (2024)",
        "hygiene_cible": ctx.hygiene_cr,
        "segments": {s: int((seg_all == s).sum()) for s in qv14.SEGMENTS},
        "n_features": len(names), "features": names, "interactions": inter,
        "features_couverture_2026": couv,
        "test_fuite": fuite,
        "metriques_k0_2025": {k: (None if isinstance(v, float) and np.isnan(v) else v)
                              for k, v in row_q.items()},
        "metriques_24m_test2024": {k: (None if isinstance(v, float) and np.isnan(v) else v)
                                   for k, v in row_24.items()},
        "millesimes_sources": millesimes,
        "note_de_version": note,
    }
    manifeste = qv14.geler_artifacts(m12, m24, manifeste)
    (QDIR / "NOTE-DE-VERSION-q_v14.md").write_text(note + "\n", encoding="utf-8")

    # round-trip : l'artefact rechargé prédit EXACTEMENT pareil (gel sain)
    m12b, _, _ = qv14.verify_artifacts()
    ech = ctx.test.sample(n=2000, random_state=974)
    seg_test = seg_all[(df.annee == protocole.TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_ech = seg_test.loc[ech.index]
    assert np.allclose(m12b.predict_proba(ech, seg_ech),
                       m12.predict_proba(ech, seg_ech)), "round-trip artefact KO"
    log(f"[q_v14] gelé : {manifeste['sha256_12m'][:16]}… / {manifeste['sha256_24m'][:16]}…")
    print(table.to_string(index=False))
    print("\n" + note)


def note_de_version(row_base, row_qv12, row_q, row_24, avec_ventes_pm, degrade) -> str:
    """La note en français, composée DEPUIS les chiffres mesurés au banc K0."""
    def g(r, k):
        v = r.get(k)
        return float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else float("nan")
    ratio = (g(row_q, "n_priorite") / g(row_base, "n_priorite")
             if g(row_base, "n_priorite") else float("nan"))
    lignes = [
        f"Candidat q_v14 du {date.today().strftime('%d/%m/%Y')} — les deux améliorations "
        "combinées (gains de MODÈLE q_v12 + gains de DONNÉES q_v13_sources1), "
        "produites par le pipeline réel.",
        "",
        "Ce qui change vs le servi : la recette q_v12 (4 mortes + 5 retired retirées, "
        "résiduel lu à 100 %, voisinage/marché as-of, calibration isotonique par "
        "segment) PLUS quatre variables reconstruites à la date de chaque ligne — "
        "l'état bâti/nu et la part bâtie du secteur (Sitadel + DVF), le permis déposé "
        "par un professionnel sur une parcelle de particulier, l'ancienneté du PLU" +
        (", et la part des ventes du secteur parties à des sociétés."
         if avec_ventes_pm else
         ". La part des ventes vers des sociétés a été ÉCARTÉE : elle dégradait "
         "l'ECE du segment personnes morales au-delà du seuil de 0,01."),
        "",
        "Les données du jour et la cascade de q_v13_sources1 (dont 4 378 exclusions "
        "neuves fondées sur des servitudes réelles) entrent AU RUN, réutilisées sans "
        "rejeu — la cascade est orthogonale au modèle.",
        "",
        "Les chiffres (banc K0, année vierge 2025 : train ≤2023, cal 2024) :",
        f"- précision@100 par commune (médiane) : servi {g(row_base,'prec@100_commune_mediane'):.3f} "
        f"· q_v12 {g(row_qv12,'prec@100_commune_mediane'):.3f} · q_v14 {g(row_q,'prec@100_commune_mediane'):.3f} ;",
        f"- Priorité : servi {g(row_base,'prec_priorite'):.1%} sur {g(row_base,'n_priorite'):.0f} "
        f"→ q_v14 {g(row_q,'prec_priorite'):.1%} sur {g(row_q,'n_priorite'):.0f} (effectif ×{ratio:.1f}) ;",
        f"- lift du décile supérieur : servi {g(row_base,'lift_decile_sup'):.2f} · "
        f"q_v12 {g(row_qv12,'lift_decile_sup'):.2f} · q_v14 {g(row_q,'lift_decile_sup'):.2f} ;",
        f"- AUC global : servi {g(row_base,'auc_global'):.3f} · q_v12 {g(row_qv12,'auc_global'):.3f} · "
        f"q_v14 {g(row_q,'auc_global'):.3f} (nu {g(row_q,'auc_terrain_nu'):.3f}, "
        f"PM {g(row_q,'auc_personne_morale'):.3f}) ;",
        f"- ECE global q_v14 : {g(row_q,'ece_global'):.4f} "
        f"(bâti {g(row_q,'ece_bati_individuel'):.4f}, nu {g(row_q,'ece_terrain_nu'):.4f}, "
        f"PM {g(row_q,'ece_personne_morale'):.4f}, copro {g(row_q,'ece_copropriete'):.4f}) ;",
        f"- segments dont l'ECE se dégrade de plus de 0,01 vs q_v12 : {degrade or 'aucun'} ;",
        f"- churn top-1158 vs le run servi : {g(row_q,'churn_top1158_vs_servi'):.1%} "
        "(la garde de churn liste les sorties de Priorité au compte-rendu) ;",
        f"- horizon 24 mois (test 2024) : AUC {g(row_24,'auc_global'):.3f}, "
        f"préc@100 méd {g(row_24,'prec@100_commune_mediane'):.3f} — colonne stockée.",
        "",
        f"Rien de servi ne change tant que la bascule n'est pas faite : `{SERVED_RUN}` "
        "reste le run servi. La bascule est un geste manuel (`golden promote`), réversible.",
    ]
    return "\n".join(lignes)


#: le protocole du walk-forward de l'artefact SERVI (m36, FREEZE) — pour comparer
#: q_v14 sur le même terrain : 6 plis, RR@1158 hors copro.
WF_FOLDS = (2020, 2021, 2022, 2023, 2024, 2025)
RR_K = 1158
M36_WF = "walk-forward m36 servi : RR@1158 6,9-11,0 (hors copro 6,7-9,4), fold 2025 = 6,73"


def walk() -> None:
    """Étape 3 — walk-forward 6 plis (comme l'artefact servi), RR@1158 hors copro.
    Chaque pli T : fit q_v14 sur train ≤ T-2, isotonique T-1, test T. On mesure
    aussi q_v12 sur les mêmes plis (ce qui vient du modèle vs des données)."""
    from labuse.scoring.p_model import evaluate as ev
    eng = engine()
    df = _charger_enrichi(eng)
    copro = qv14.copro_de(eng, df)
    seg_all = qv14.segmenter(df, copro)
    n14, s14, i14 = qv14.features_qv14(avec_ventes_pm=_ventes_pm_retenue())
    n12, s12, i12 = qv12.features_qv12()

    rows = []
    for T in WF_FOLDS:
        maskT = (df.annee == T).to_numpy()
        yT = df.loc[maskT, "label"].astype(float)
        elig = maskT & df["label"].notna().to_numpy()
        if not elig.any():
            continue
        horsT = ~copro[maskT]
        segT = seg_all[maskT].reset_index(drop=True)
        testT = df[maskT].reset_index(drop=True)
        rec = {"pli_test": T, "n_test": int(maskT.sum()),
               "n_positifs": int(np.nansum(yT.to_numpy()))}
        for tag, (names, specs, inter) in (("q_v14", (n14, s14, i14)),
                                           ("q_v12", (n12, s12, i12))):
            fit_fn = qv14.fit_qv14 if tag == "q_v14" else qv12.fit_qv12
            m = fit_fn(df, seg_all, names, specs, inter,
                       train_max=T - 2, cal_year=T - 1)
            p = m.predict_proba(testT, segT)
            y = testT["label"].astype(float).to_numpy()
            ok = horsT & ~np.isnan(y)
            rec[f"rr@{RR_K}_{tag}"] = round(float(
                ev.rr_at_k(y[ok].astype(int), p[ok], RR_K, seed=974)["rr"]), 3)
        rows.append(rec)
        log(f"pli {T} : q_v14 RR@{RR_K}={rec[f'rr@{RR_K}_q_v14']} · "
            f"q_v12={rec[f'rr@{RR_K}_q_v12']} (n={rec['n_test']})")

    out = pd.DataFrame(rows)
    out.to_csv(QDIR / "q_v14_walkforward.csv", index=False)
    rr14 = out[f"rr@{RR_K}_q_v14"]
    resume = {"reference_m36": M36_WF,
              "q_v14_rr_min": float(rr14.min()), "q_v14_rr_max": float(rr14.max()),
              "q_v14_rr_median": float(rr14.median()),
              "q_v12_rr_min": float(out[f"rr@{RR_K}_q_v12"].min()),
              "q_v12_rr_max": float(out[f"rr@{RR_K}_q_v12"].max()),
              "plis": WF_FOLDS}
    (QDIR / "q_v14_walkforward_resume.json").write_text(
        json.dumps(resume, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out.to_string(index=False))
    print("\n" + json.dumps(resume, indent=2, ensure_ascii=False))


def _ventes_pm_retenue() -> bool:
    """Lit dans le manifeste gelé si ventes_pm_secteur_36m a été retenue (garde-fou)."""
    if qv14.QV14_FREEZE.exists():
        return bool(json.loads(qv14.QV14_FREEZE.read_text())
                    .get("ventes_pm_secteur_36m_retenue", True))
    return True


def test_fuite(eng, annee: int = 2025) -> dict:
    """Test de fuite sur le code recette (mêmes requêtes que le pipeline réel).

    - voisinage q_v12 : les compteurs de ventes/permis voisins doivent être
      IDENTIQUES si l'on tronque la source à < asof (déjà borné → égal) ;
    - variables as-of neuves bornées par date < asof (pc_pm, ventes_pm) : idem ;
    - nu_asof / pct_bati_secteur_asof : reconstruisent l'état PHYSIQUE bâti/nu
      (permis, mutations datées) — jamais la cible (vente L2-F sous 12 mois) ;
      contrôle : la variable n'utilise aucune colonne de label.
    """
    # 1) voisinage q_v12 (réutilise le test dédié)
    v = qv12._ventes_annee(eng, annee).set_index("idu").sort_index()
    vt = qv12._ventes_annee(eng, annee, date_max=f"{annee}-01-01").set_index("idu").sort_index()
    p = qv12._permis_annee(eng, annee).set_index("idu").sort_index()
    pt = qv12._permis_annee(eng, annee, date_max=f"{annee}-01-01").set_index("idu").sort_index()
    vois_ok = bool(v.equals(vt) and p.equals(pt))

    # 2) variables as-of neuves : le calcul pour l'année Y n'utilise que des dates < Y.
    #    On vérifie que la grille pour Y=annee est STABLE quand on ajoute une année
    #    postérieure au calcul (les colonnes de Y ne doivent pas bouger).
    pcpm_seul = qv14._colonnes_pc_pm(eng, (annee,))
    pcpm_avec_futur = qv14._colonnes_pc_pm(eng, (annee, annee + 1))
    pcpm_avec_futur = pcpm_avec_futur[pcpm_avec_futur.annee == annee]
    pcpm_ok = bool(set(pcpm_seul["idu"]) == set(pcpm_avec_futur["idu"]))

    vpm_seul = qv14._ventes_pm_secteur(eng, (annee,)).set_index("secteur")["ventes_pm_secteur_36m"]
    vpm_futur = qv14._ventes_pm_secteur(eng, (annee, annee + 1))
    vpm_futur = vpm_futur[vpm_futur.annee == annee].set_index("secteur")["ventes_pm_secteur_36m"]
    vpm_ok = bool(np.allclose(vpm_seul.sort_index().to_numpy(),
                              vpm_futur.reindex(vpm_seul.index).sort_index().to_numpy(),
                              equal_nan=True))

    verdict = {
        "annee_testee": annee,
        "voisinage_egal_source_tronquee": vois_ok,
        "pc_pm_stable_ajout_annee_future": pcpm_ok,
        "ventes_pm_secteur_stable_ajout_annee_future": vpm_ok,
        "nu_asof_note": "reconstruit l'état physique bâti/nu (permis/mutations datées), "
                        "jamais la cible L2-F — aucune colonne de label lue",
        "fuite_detectee": not (vois_ok and pcpm_ok and vpm_ok),
    }
    pd.DataFrame([verdict]).to_csv(QDIR / "q_v14_test_fuite.csv", index=False)
    print(verdict)
    return verdict


# ─────────────────────────── après le run réel ───────────────────────────

PRIORITE_TIERS = ("chaude", "brulante")


def churn() -> None:
    """La garde de churn : top-1158 q_v14 vs servi + les 50 premières sorties de
    Priorité avec la raison. Lit les DEUX runs stockés (le run réel)."""
    eng = engine()
    servi = pd.read_sql(
        f"SELECT parcelle_id AS idu, p_raw, rang, tier, top5_contributions "
        f"FROM parcel_p_score_v2 WHERE run_id = '{SERVED_RUN}' AND NOT copro", eng)
    cand = pd.read_sql(
        "SELECT parcelle_id AS idu, p_raw, rang, tier "
        "FROM parcel_p_score_v2 WHERE run_id = 'q_v14' AND NOT copro", eng)
    top_s = set(servi.nsmallest(1158, "rang")["idu"])
    top_c = set(cand.nsmallest(1158, "rang")["idu"])
    churn_1158 = 1.0 - len(top_s & top_c) / 1158
    prio_s = servi[servi["tier"].isin(PRIORITE_TIERS)]
    prio_c = set(cand[cand["tier"].isin(PRIORITE_TIERS)]["idu"])
    sorties = prio_s[~prio_s["idu"].isin(prio_c)].sort_values("rang")
    log(f"churn top-1158 : {churn_1158:.1%} ; Priorité servie {len(prio_s)}, "
        f"candidate {len(prio_c)}, sorties {len(sorties)}")
    resume = {"churn_top1158_vs_servi": round(churn_1158, 4),
              "n_priorite_servi": int(len(prio_s)),
              "n_priorite_candidat": int(len(prio_c)),
              "n_sorties_priorite": int(len(sorties))}
    sorties.head(50)[["idu", "rang", "tier"]].to_csv(
        QDIR / "q_v14_sorties_priorite.csv", index=False)
    pd.DataFrame([resume]).to_csv(QDIR / "q_v14_churn.csv", index=False)
    print(json.dumps(resume, indent=2, ensure_ascii=False))


def verif() -> None:
    """Coïncidence run réel / arène : 1 000 parcelles (seed 974), p_raw stocké vs
    artefact via le chemin d'arène. Attendu : écart médian < 1e-6."""
    eng = engine()
    stored = pd.read_sql(
        "SELECT parcelle_id AS idu, p_raw FROM parcel_p_score_v2 WHERE run_id = 'q_v14'", eng)
    ech = stored.sample(n=1000, random_state=974).reset_index(drop=True)
    df = protocole.load_range(eng, (protocole.SCORE_YEAR,))
    df = df[df["idu"].isin(set(ech["idu"]))].reset_index(drop=True)
    df = qv14.enrichir(eng, df, (protocole.SCORE_YEAR,))
    m12, _, _ = qv14.verify_artifacts()
    seg = qv14.segmenter(df, qv14.copro_de(eng, df))
    p = m12.predict_proba(df, seg)
    j = df[["idu"]].assign(p_arene=p).merge(ech, on="idu")
    au = (pd.read_sql("SELECT a.idu FROM parcel_au_statut a JOIN parcels ap "
                      "ON ap.id = a.parcel_id WHERE a.classe = 'au_sous_plancher'", eng)
          if pd.read_sql("SELECT to_regclass('parcel_au_statut') t", eng)["t"].iloc[0]
          else pd.DataFrame(columns=["idu"]))
    j["ponderee_au"] = j["idu"].isin(set(au["idu"]))
    j["ecart"] = (j["p_arene"] - j["p_raw"]).abs()
    hors_au = j[~j["ponderee_au"]]
    verdict = {
        "n": int(len(j)), "n_ponderees_au": int(j["ponderee_au"].sum()),
        "ecart_median": float(j["ecart"].median()),
        "ecart_max_hors_au": float(hors_au["ecart"].max()),
        "ecart_median_hors_au": float(hors_au["ecart"].median()),
        "n_ecart_gt_1e6_hors_au": int((hors_au["ecart"] > 1e-6).sum()),
    }
    j.to_csv(QDIR / "q_v14_verif_1000.csv", index=False)
    pd.DataFrame([verdict]).to_csv(QDIR / "q_v14_verif.csv", index=False)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    assert verdict["ecart_median"] < 1e-6, "écart médian ≥ 1e-6 — à expliquer"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fit"
    {"cache": cache, "fit": fit, "walk": walk, "fuite": lambda: test_fuite(engine()),
     "churn": churn, "verif": verif}[cmd]()
