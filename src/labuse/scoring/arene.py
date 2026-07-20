"""L'ARÈNE — juge champion / challenger (Phase 0 « Le Juge », lot J2).

SOUDE les pièces existantes en UN outil de verdict, sans les réécrire :
  - métriques : `p_model/evaluate.py` (rr_at_k, bootstrap_rr, lift_table, ece, churn_topk,
    ventilation, permutation_control) — tirages seedés 974 ;
  - protocole : label L2-F (`p_model_ext_dataset`), RR@1158, hors copro (comme M3.6).

CONTRAT :
  - LECTURE SEULE sur les tables de scores (`parcel_p_score_v2`, `p_score_v2_runs`) et sur le
    label (`p_model_ext_dataset`). N'écrit QUE dans `reports/arene/`. Ne lance JAMAIS `score-v2`.
  - Champion par défaut = dernier run servi (`p_score_v2_runs` par `computed_at`).
  - L'AVIS est un AVIS : la bascule reste une décision humaine, jamais celle de l'outil.
"""
from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from .p_model import SEED, evaluate as ev

#: taille du top-k du protocole M3.6 (RR@1158) — la « réserve » jugée.
RR_K = 1158
#: seuils de l'AVIS (paramétrables en CLI).
DEFAULT_CHURN_MAX = 0.25          # budget de rotation du top-k
ECE_DEGRADE_MAX = 0.01           # dégradation de calibration tolérée
DEFAULT_GOLDEN = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                              "reports", "m6-audit", "golden", "golden-parcelles.json")


# ───────────────────────────── chargement (lecture seule) ─────────────────────────────

def served_run(session: Session) -> str | None:
    """Dernier run servi (même règle que l'API/golden) = champion par défaut."""
    return session.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()


def latest_label_year(session: Session) -> int:
    """Dernière année d'observation COMPLÈTE (label L2-F non nul) = jeu d'évaluation."""
    return int(session.execute(text(
        "SELECT max(annee) FROM p_model_ext_dataset WHERE label IS NOT NULL")).scalar())


def _load_run(session: Session, run_id: str) -> pd.DataFrame:
    rows = session.execute(text(
        "SELECT parcelle_id AS idu, p_raw, tier, copro FROM parcel_p_score_v2 "
        "WHERE run_id = :r"), {"r": run_id}).mappings().all()
    return pd.DataFrame(rows).set_index("idu") if rows else pd.DataFrame()


def _load_labels(session: Session, year: int) -> pd.DataFrame:
    rows = session.execute(text(
        "SELECT idu, label, owner_type, commune FROM p_model_ext_dataset "
        "WHERE annee = :y AND label IS NOT NULL"), {"y": year}).mappings().all()
    return pd.DataFrame(rows).set_index("idu")


def _golden_boussole(session: Session, challenger: str, golden_path: str) -> dict:
    """Gate BOUSSOLE : toute parcelle golden ATTENDUE écartée/exclue qui apparaît `brulante`
    ou `chaude` chez le challenger = compteur > 0 = REJET éliminatoire (un faux positif servi
    est un péché mortel)."""
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)
    attendues = [
        idu for idu, e in golden.get("parcelles", {}).items()
        if ((e.get("db", {}).get("score_v2") or {}).get("tier") == "ecartee"
            or e.get("db", {}).get("etage0"))
    ]
    tiers = {r["idu"]: r["tier"] for r in session.execute(text(
        "SELECT parcelle_id AS idu, tier FROM parcel_p_score_v2 "
        "WHERE run_id = :r AND parcelle_id = ANY(:idus)"),
        {"r": challenger, "idus": attendues}).mappings().all()}
    violations = [(idu, tiers.get(idu)) for idu in attendues if tiers.get(idu) in ("brulante", "chaude")]
    return {"n_attendues": len(attendues), "violations": violations, "compteur": len(violations)}


def paired_bootstrap_diff(y: np.ndarray, score_a: np.ndarray, score_b: np.ndarray, k: int,
                          n_boot: int = 1000, seed: int = SEED) -> dict:
    """IC95 de (RR_a − RR_b) par bootstrap APPARIÉ : à CHAQUE tirage on rééchantillonne UNE fois les
    lignes et on calcule les deux RR sur les MÊMES parcelles (seed 974). La significativité = la borne
    basse de l'IC de la différence > 0 (le challenger bat le champion de façon fiable, pas par bruit)."""
    rng = np.random.RandomState(seed)
    n = len(y)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        yb = y[idx]
        base = yb.mean()
        if base <= 0:
            continue
        ta = ev._ranked_top_mask(score_a[idx], k, rng)
        tb = ev._ranked_top_mask(score_b[idx], k, rng)
        diffs.append(float(yb[ta].mean() / base - yb[tb].mean() / base))
    lo, hi = np.percentile(diffs, [2.5, 97.5]) if diffs else (float("nan"), float("nan"))
    point = ev.rr_at_k(y, score_a, k, seed=seed)["rr"] - ev.rr_at_k(y, score_b, k, seed=seed)["rr"]
    return {"diff_rr": float(point), "ic95_bas": float(lo), "ic95_haut": float(hi),
            "significatif": bool(lo > 0), "n_boot": len(diffs)}


def decide_avis(boussole_compteur: int, rr_diff_ic_low: float, ece_delta: float,
                churn_frac: float, churn_max: float, *, is_baseline: bool = False,
                ece_degrade_max: float = ECE_DEGRADE_MAX, rr_k: int = RR_K) -> tuple[str, list[str]]:
    """Décision d'AVIS (PURE, testable). Le compteur boussole > 0 est ÉLIMINATOIRE (un faux positif
    servi est un péché mortel). Sinon RETENU ssi la DIFFÉRENCE de RR est significativement > 0 (IC95
    apparié exclut zéro) ET ECE non dégradée de plus de `ece_degrade_max` ET churn ≤ budget."""
    criteres: list[str] = []
    if boussole_compteur > 0:
        criteres.append(f"BOUSSOLE : {boussole_compteur} parcelle(s) golden écartée/exclue passée(s) brûlante/chaude")
    if rr_diff_ic_low <= 0:
        criteres.append(f"RR@{rr_k} non significativement supérieur (IC95 apparié de ΔRR : borne basse "
                        f"{rr_diff_ic_low:+.2f} ≤ 0)")
    if ece_delta > ece_degrade_max:
        criteres.append(f"ECE dégradée de +{ece_delta:.4f} (> {ece_degrade_max})")
    if churn_frac > churn_max:
        criteres.append(f"churn {churn_frac:.0%} > budget {churn_max:.0%}")
    if is_baseline:
        return "BASELINE (champion contre lui-même — référence)", criteres
    if boussole_compteur > 0:
        return "REJETÉ (éliminatoire boussole)", criteres
    return ("CHALLENGER RETENU" if not criteres else "REJETÉ"), criteres


# ───────────────────────────── le juge ─────────────────────────────

def run_arene(session: Session, challenger: str, champion: str | None = None,
              eval_year: int | None = None, golden_path: str = DEFAULT_GOLDEN,
              churn_max: float = DEFAULT_CHURN_MAX, n_boot: int = 1000) -> dict[str, Any]:
    """Juge le challenger contre le champion. Renvoie un dict de sections (→ `render_report`)."""
    champion = champion or served_run(session)
    eval_year = eval_year or latest_label_year(session)
    is_baseline = challenger == champion

    champ, chall, lab = _load_run(session, champion), _load_run(session, challenger), _load_labels(session, eval_year)
    for name, dfr in (("champion", champ), ("challenger", chall)):
        if dfr.empty:
            raise ValueError(f"run {name} « {champion if name == 'champion' else challenger} » absent de parcel_p_score_v2")

    # 1. CONTRÔLE D'UNIVERS : intersection EXACTE des parcelles des deux runs ∩ label.
    s_champ, s_chall, s_lab = set(champ.index), set(chall.index), set(lab.index)
    inter = sorted(s_champ & s_chall & s_lab)
    univers = {
        "champion": champion, "challenger": challenger, "eval_year": eval_year,
        "n_champion": len(s_champ), "n_challenger": len(s_chall), "n_label": len(s_lab),
        "n_intersection": len(inter),
        "champion_hors_challenger": len(s_champ - s_chall),
        "challenger_hors_champion": len(s_chall - s_champ),
        "sans_label": len(s_champ & s_chall) - len(inter),
    }

    d = lab.loc[inter].copy()
    d["score_champ"] = champ.loc[inter, "p_raw"].astype(float).to_numpy()
    d["score_chall"] = chall.loc[inter, "p_raw"].astype(float).to_numpy()
    d["tier_chall"] = chall.loc[inter, "tier"].to_numpy()
    d["copro"] = chall.loc[inter, "copro"].fillna(False).astype(bool).to_numpy()
    # hors copro (comme M3.6) — l'univers d'évaluation
    hc = d[~d["copro"]].reset_index()
    univers["n_hors_copro"] = len(hc)

    y = hc["label"].astype(int).to_numpy()
    sc_champ, sc_chall = hc["score_champ"].to_numpy(), hc["score_chall"].to_numpy()
    annees = np.full(len(hc), eval_year)

    # 3. PERFORMANCE — RR@1158 + IC95 bootstrap (seed 974), lift, ventilations.
    rr_champ = ev.bootstrap_rr(y, sc_champ, RR_K, n_boot=n_boot, seed=SEED)
    rr_chall = ev.bootstrap_rr(y, sc_chall, RR_K, n_boot=n_boot, seed=SEED)
    # bootstrap APPARIÉ de la différence (challenger − champion) sur les MÊMES parcelles.
    rr_diff = paired_bootstrap_diff(y, sc_chall, sc_champ, RR_K, n_boot=n_boot, seed=SEED)
    lift = ev.lift_table(y, sc_chall, seed=SEED)
    vent_commune = ev.ventilation(hc, y, sc_chall, RR_K, col="commune", seed=SEED)
    vent_tier = ev.ventilation(hc, y, sc_chall, RR_K, col="tier_chall", seed=SEED)

    # 4. CALIBRATION — ECE des deux runs (p_raw = probabilité).
    ece_champ, _ = ev.ece(y, sc_champ)
    ece_chall, _ = ev.ece(y, sc_chall)

    # 5. CHURN — rotation du top-1158 challenger vs champion.
    churn = ev.churn_topk(pd.Series(sc_champ, index=hc["idu"]),
                          pd.Series(sc_chall, index=hc["idu"]), RR_K, seed=SEED)
    churn_frac = 1.0 - churn["overlap_pct"]

    # 6. CONTRÔLE NÉGATIF — labels permutés intra-année : RR@k attendu ≈ 1.
    perm = ev.permutation_control(y, sc_chall, annees, RR_K, seed=SEED)

    # 2. GOLDEN / BOUSSOLE — gate éliminatoire.
    boussole = _golden_boussole(session, challenger, golden_path)

    # 7. AVIS (logique pure, testable) — CHALLENGER RETENU ssi boussole=0 ET RR strictement
    #    supérieur ET ECE non dégradée de plus de 0,01 ET churn ≤ budget. Sinon REJETÉ.
    avis, criteres = decide_avis(
        boussole["compteur"], rr_diff["ic95_bas"],
        ece_chall - ece_champ, churn_frac, churn_max, is_baseline=is_baseline)

    return {
        "avis": avis, "is_baseline": is_baseline, "criteres_rejet": criteres,
        "univers": univers, "boussole": boussole,
        "rr_champion": rr_champ, "rr_challenger": rr_chall, "rr_diff": rr_diff,
        "ece_champion": ece_champ, "ece_challenger": ece_chall,
        "churn": churn, "churn_frac": churn_frac, "churn_max": churn_max,
        "permutation": perm, "lift": lift, "vent_commune": vent_commune, "vent_tier": vent_tier,
        "params": {"rr_k": RR_K, "seed": SEED, "n_boot": n_boot, "ece_degrade_max": ECE_DEGRADE_MAX},
    }


# ───────────────────────────── rapport ─────────────────────────────

def render_report(r: dict[str, Any], stamp: str) -> str:
    u, b = r["univers"], r["boussole"]
    rc, rl = r["rr_champion"], r["rr_challenger"]

    def _df(df: pd.DataFrame, cols: list[str], n: int = 12) -> str:
        d = df.copy()
        for c in df.columns:
            if df[c].dtype.kind == "f":
                d[c] = df[c].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
        head = "| " + " | ".join(cols) + " |\n| " + " | ".join(["---"] * len(cols)) + " |\n"
        body = "\n".join("| " + " | ".join(str(d.iloc[i][c]) for c in cols) + " |" for i in range(min(n, len(d))))
        return head + body

    L = []
    L.append(f"# Arène — {u['challenger']} vs {u['champion']}")
    L.append(f"\n**AVIS : {r['avis']}**")
    if r["criteres_rejet"] and not r["is_baseline"]:
        L.append("\nCritère(s) en cause :\n" + "\n".join(f"- {c}" for c in r["criteres_rejet"]))
    L.append(f"\n_L'avis est indicatif : la bascule du run servi reste une décision humaine._  ")
    L.append(f"_Généré {stamp} · seed {r['params']['seed']} · RR@{r['params']['rr_k']} · "
             f"bootstrap n={r['params']['n_boot']} · année d'éval {u['eval_year']}._")

    L.append("\n> ⚠ **NATURE DE LA MESURE — RR ABSOLU IN-SAMPLE, NON COMPARABLE AU WALK-FORWARD.**\n"
             f"> Les scores servis sont calculés **features as-of 01/01/{u['eval_year'] + 1}** (le run\n"
             f"> servi score l'année suivante), or on les évalue contre le label de **{u['eval_year']}** — la\n"
             f"> dernière année labellisée complète. Les fenêtres de features as-of {u['eval_year'] + 1}\n"
             f"> **encodent déjà les mutations {u['eval_year']}** → le RR absolu (ici RR@{r['params']['rr_k']}) est\n"
             "> **IN-SAMPLE / optimiste**. Il ne doit PAS être comparé au RR out-of-sample du walk-forward\n"
             "> M3.6 (fold 2025 hors copro = **6,73**, features as-of 01/01/2025). Même univers (hors copro),\n"
             "> même k (1158), même label (L2-F) ; SEULE la date as-of diffère (2026 vs 2025).\n"
             "> **La comparaison RELATIVE champion↔challenger reste valide** (les deux runs subissent la même\n"
             "> fuite) : c'est le rôle de l'IC apparié de ΔRR ci-dessous, PAS le niveau absolu.")

    L.append("\n## 1. Contrôle d'univers")
    L.append(f"- champion `{u['champion']}` : {u['n_champion']:,} parcelles · challenger "
             f"`{u['challenger']}` : {u['n_challenger']:,}".replace(",", " "))
    L.append(f"- **intersection ∩ label {u['eval_year']} : {u['n_intersection']:,}** "
             f"(hors copro : {u['n_hors_copro']:,})".replace(",", " "))
    L.append(f"- écart de couverture : {u['champion_hors_challenger']} chez le champion seul · "
             f"{u['challenger_hors_champion']} chez le challenger seul · {u['sans_label']} sans label")

    L.append("\n## 2. Golden — gate boussole (éliminatoire)")
    L.append(f"- parcelles golden attendues écartées/exclues : **{b['n_attendues']}**")
    L.append(f"- **compteur boussole (passées brûlante/chaude chez le challenger) : {b['compteur']}**")
    if b["violations"]:
        L.append("\n⚠ VIOLATIONS (REJET éliminatoire) :\n"
                 + "\n".join(f"- `{idu}` → tier `{t}`" for idu, t in b["violations"]))
    else:
        L.append("- ✅ aucune violation (aucun faux positif servi introduit).")

    L.append("\n## 3. Performance — RR@1158")
    L.append(f"| run | RR@{RR_K} | IC95 | positifs top-k | taux global |")
    L.append("| --- | --- | --- | --- | --- |")
    for lbl, rr in (("champion", rc), ("challenger", rl)):
        L.append(f"| {lbl} | **{rr['rr']:.2f}** | [{rr['ic95_bas']:.2f} ; {rr['ic95_haut']:.2f}] "
                 f"| {rr['positifs_topk']} | {rr['taux_global']:.4f} |")
    dd = r["rr_diff"]
    L.append(f"\n**Différence APPARIÉE (challenger − champion), bootstrap sur les mêmes parcelles** :\n"
             f"- ΔRR = **{dd['diff_rr']:+.2f}** · IC95 apparié [{dd['ic95_bas']:+.2f} ; {dd['ic95_haut']:+.2f}] "
             f"· significatif (borne basse > 0) : **{'OUI' if dd['significatif'] else 'NON'}**\n"
             f"- _Critère d'AVIS : le challenger n'est retenu que si cet IC EXCLUT zéro par le bas "
             f"(pas deux IC indépendants qui se chevauchent)._")
    L.append("\n**Lift (challenger)** :\n" + _df(r["lift"], ["percentile", "k", "positifs", "taux", "rr", "rappel"]))
    L.append("\n**Ventilation par commune (top-k challenger)** :\n"
             + _df(r["vent_commune"], ["commune", "n_total", "taux_base", "n_topk", "rr_segment"]))
    L.append("\n**Ventilation par tier challenger** :\n"
             + _df(r["vent_tier"], ["tier_chall", "n_total", "taux_base", "n_topk", "rr_segment"]))

    L.append("\n## 4. Calibration — ECE")
    L.append(f"- champion : **{r['ece_champion']:.4f}** · challenger : **{r['ece_challenger']:.4f}** "
             f"· Δ = {r['ece_challenger'] - r['ece_champion']:+.4f} (tolérance {r['params']['ece_degrade_max']})")

    L.append("\n## 5. Churn — top-1158")
    L.append(f"- overlap : {r['churn']['overlap']}/{RR_K} ({r['churn']['overlap_pct']:.0%}) · "
             f"**churn {r['churn_frac']:.0%}** (budget {r['churn_max']:.0%}) · "
             f"{r['churn']['entrants']} entrants / {r['churn']['sortants']} sortants")

    L.append("\n## 6. Contrôle négatif — permutation")
    L.append(f"- RR@{RR_K} sur labels permutés intra-année : **{r['permutation']['rr']:.2f}** "
             f"(attendu ≈ 1 ; s'en écarter = fuite/artefact).")

    L.append("\n## 7. Avis synthétique")
    L.append(f"**{r['avis']}**"
             + ("" if not r["criteres_rejet"] or r["is_baseline"]
                else " — " + " ; ".join(r["criteres_rejet"])) + ".")
    return "\n".join(L) + "\n"
