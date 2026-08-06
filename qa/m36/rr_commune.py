"""M36 Lot E — RR par commune : REPRODUCTION de la mesure ALGO-1 §1 + IC95 bootstrap.

Méthodologie (IDENTIQUE au protocole gelé, harnais réutilisé, rien recodé) :
- scores : `reports/m36-foncier/scores-2025-fold-final.csv` — sortie OUT-OF-SAMPLE du
  walk-forward (fold 2025) du modèle P (label L2-F) ; artefact FIGÉ, aucun re-scoring ;
- labels : `p_model_dataset` annee=2025, label L2-F (mutation L2 observée en 2025) ;
- population : hors copropriétés (flag `parcel_p_score_v2.copro`, run servi) — n = 428 239 ;
- RR@k : `p_model.evaluate.rr_at_k` (ties départagés par tirage seedé 974, comme le gel) ;
- contrôle : RR@1158 île — référence gelée ALGO-1 = 6,73. CONSTAT M36 : le label 2025 a
  BOUGÉ depuis le gel (rebuild du dataset + fenêtre DVF vivante : +39 positifs nouveaux,
  ~10 positifs du top retirés, net 6 466 → 6 495) → contrôle vivant = 6,15. L'écart est
  DOCUMENTÉ (pas masqué) ; les RR par commune sont mesurés sur les labels d'AUJOURD'HUI,
  cohérents avec le contrôle vivant ;
- k_c par commune ∝ 1158 (part de la commune dans la population) ;
- IC95 : `bootstrap_rr` (500 rééchantillonnages seedés) ; ⚠ si < 5 positifs dans le top-k_c
  (aucune conclusion) ;
- lecture « top île » : présence de la commune dans le top-1158 île + RR dans ce top.

MESURE SEULE : aucune écriture, rien servi côté client.
Usage : PYTHONPATH=src python qa/m36/rr_commune.py
"""
from __future__ import annotations

import csv
import sys

import numpy as np
import pandas as pd
from sqlalchemy import text

from labuse.db import session_factory
from labuse.scoring.p_model.evaluate import _ranked_top_mask, bootstrap_rr, rr_at_k


def rr_sensibilite(y, sc, k, seeds=range(1, 21)):
    """RR@k sur N tirages d'ex æquo — médiane et bornes (la coupure top-k tombe dans des
    paliers de scores identiques : UN tirage seul serait une fausse précision)."""
    vals = [rr_at_k(y, sc, k, seed=s)["rr"] for s in seeds]
    return float(np.median(vals)), float(min(vals)), float(max(vals))


K_ILE = 1158
CONTROLE_ILE = 6.73

db = session_factory()()
rows = db.execute(text(
    "SELECT d.idu, d.label, p.commune, s.copro "
    "FROM p_model_dataset d "
    "JOIN parcels p ON p.idu = d.idu "
    "JOIN parcel_p_score_v2 s ON s.parcelle_id = d.idu AND s.run_id = 'q_v8_calibre' "
    "WHERE d.annee = 2025")).all()
db.close()
base = pd.DataFrame(rows, columns=["idu", "label", "commune", "copro"])
scores = pd.read_csv("reports/m36-foncier/scores-2025-fold-final.csv")
df = base.merge(scores, on="idu", how="inner")
# Ordre CANONIQUE (idu) : le départage des ex æquo dépend de l'ordre des lignes — sans
# ordre fixé, le RR@1158 varie (~6,1-6,6) car la coupure tombe en plein PALIER de scores
# identiques (cf. AUDIT1 train 5). On fige l'ordre ET on mesure la sensibilité aux tirages.
df = df[~df["copro"]].sort_values("idu").reset_index(drop=True)
n_ile = len(df)
y = df["label"].to_numpy(dtype=float)
sc = df["p_l2f"].to_numpy(dtype=float)
taux_ile = 100 * y.mean()
rr_med, rr_min, rr_max = rr_sensibilite(y, sc, K_ILE)
print(f"population hors copro : {n_ile} · taux de base île {taux_ile:.2f} % · "
      f"RR@{K_ILE} île = {rr_med:.2f} médian [{rr_min:.2f}-{rr_max:.2f} sur 20 tirages "
      f"d'ex æquo] (contrôle gelé ALGO-1 : {CONTROLE_ILE})")
print("⚠ Le contrôle gelé 6,73 n'est reproductible qu'à l'ordre de lignes près : la coupure "
      "top-1158 tombe dans un PALIER d'ex æquo (AUDIT1) et le label 2025 a bougé depuis le "
      "gel (fenêtre DVF vivante, 6 466 → 6 495 positifs). Chiffres ci-dessous = labels "
      "d'aujourd'hui, médiane sur 20 tirages.")

# top île (masque seedé identique au harnais) pour la lecture « dans le top servi »
top_ile = _ranked_top_mask(sc, K_ILE, np.random.RandomState(974))

out = []
for com, g in df.groupby("commune"):
    idx = g.index.to_numpy()
    yc, sc_c = y[idx], sc[idx]
    n_c = len(idx)
    taux_c = 100 * yc.mean()
    k_c = max(1, round(K_ILE * n_c / n_ile))
    med, mn, mx = rr_sensibilite(yc, sc_c, k_c)
    r = rr_at_k(yc, sc_c, k_c)
    boot = bootstrap_rr(yc, sc_c, k_c, n_boot=500)
    pos_topk = r["positifs_topk"]
    in_top = top_ile[idx]
    n_top = int(in_top.sum())
    rr_top = (100 * y[idx][in_top].mean() / taux_c) if (n_top and taux_c) else None
    out.append({
        "commune": com, "n_hors_copro": n_c, "taux_base_pct": round(taux_c, 2),
        "k_c": k_c, "positifs_topk": pos_topk, "rr_intra": round(med, 1),
        "rr_min_tirages": round(mn, 1), "rr_max_tirages": round(mx, 1),
        "ic95_bas": round(boot["ic95_bas"], 1), "ic95_haut": round(boot["ic95_haut"], 1),
        "avertissement": "⚠ <5 positifs top-k — aucune conclusion" if pos_topk < 5 else "",
        "n_top1158_ile": n_top,
        "rr_dans_top_ile": round(rr_top, 1) if rr_top is not None else None,
    })
out.sort(key=lambda x: -x["rr_intra"])
with open("qa/m36/rr_commune.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print(f"{len(out)} communes → qa/m36/rr_commune.csv")
for r in out:
    print(f"{r['commune']:<24} n={r['n_hors_copro']:>6} k={r['k_c']:>3} "
          f"RR={r['rr_intra']:>5} [{r['rr_min_tirages']}-{r['rr_max_tirages']}] "
          f"IC95=[{r['ic95_bas']},{r['ic95_haut']}] {r['avertissement']}")
