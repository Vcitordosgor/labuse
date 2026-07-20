#!/usr/bin/env python
"""PHASE A cycle 2 — Backtest « PC caducs » (LECTURE SEULE).

Signal RÉTROSPECTIF : un PC octroyé jamais réalisé porte (1) une constructibilité prouvée et (2) une
intention manifestée puis abandonnée → propension de revente élevée. Contrairement au défisc (forward),
le label courant VOIT les mutations que ce signal prédit → l'arène sera juge de plein droit (étape 2).

Données (cf. A1_PC_CADUCS_CADRAGE.md §3.1) :
- p_model_permits (idu, type=PC, date_autorisation) ⋈ sitadel_permits (raw.etat) ⋈ m10_permit_delais (DAACT).
- États Sitadel : 6=achevé, 4=accordé(non achevé), 5=rejeté, 2=en instruction.
- DOC (ouverture chantier) N'EXISTE PAS ; DAACT rempli à 41 % (mais 83 % parmi les OCTROYÉS).

Définition parcelle :
- realized  = ≥1 PC achevé (etat=6 ou DAACT présent).
- caduc     = octroyé (etat∈{4,6}) MAIS aucun réalisé → accordé jamais achevé, Y+4 dépassé.
- (rejeté seul / en-instruction seul : exclus — pas de constructibilité prouvée.)
Cohorte Y = plus ancienne année d'autorisation octroyée de la parcelle.

Backtest : P(mutation parcelle dans [Y+3, Y+6]) —
  (a) caduc vs RÉALISÉS même cohorte (intention prouvée, seul le destin diffère) — CRITÈRE PRINCIPAL ;
  (b) caduc vs univers apparié SANS PC (même commune × tranche de surface × zonage) — contexte.
OR + IC95 bootstrap (cluster/parcelle, seed 974). Variante robustesse : caduc ∩ parcelle « nue »
(emprise_bati_m2 basse) — contre-vérif bâti (faible : emprise = parcelle entière, non datée).

Cohortes observables : Y tel que [Y+3,Y+6] ⊆ DVF (2014-2025) → Y ∈ [2014, 2019] (borne haute 2019 → 2025).

Usage: python scripts/pc_caducs_backtest.py  → reports/pc-caducs/backtest.json + tables
"""
from __future__ import annotations
import json, os, sys
from collections import defaultdict
import numpy as np
import psycopg

SEED = 974
COHORTS = list(range(2014, 2020))          # [Y+3,Y+6] observable jusqu'à 2025
BARE_M2 = 15.0                             # seuil « nue » (contre-vérif bâti, robustesse)
OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "pc-caducs")

PC_SQL = """
WITH pc AS (
  SELECT pmp.idu, EXTRACT(YEAR FROM pmp.date_autorisation)::int AS y,
         (sp.raw->>'etat') AS etat, (md.date_achevement IS NOT NULL) AS daact
  FROM p_model_permits pmp
  JOIN sitadel_permits sp ON sp.permit_id = pmp.permit_id
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type = 'PC' AND pmp.date_autorisation IS NOT NULL)
SELECT p.idu,
       min(p.y) AS y,
       bool_or(p.daact OR p.etat = '6') AS realized,
       bool_or(p.etat IN ('4','6'))     AS granted
FROM pc p GROUP BY p.idu;
"""

META_SQL = """
SELECT p.idu, p.commune, p.surface_m2,
       COALESCE(b.emprise_bati_m2, 0) AS emprise,
       z.zone_fam
FROM parcels p
LEFT JOIN p_model_bati b ON b.idu = p.idu
LEFT JOIN parcel_zone_plu z ON z.idu = p.idu;
"""

MUT_SQL = """
SELECT id_parcelle AS idu, EXTRACT(YEAR FROM date_mutation)::int AS my
FROM dvf_mutations_histo WHERE nature_mutation LIKE 'Vente%'
UNION ALL
SELECT id_parcelle, EXTRACT(YEAR FROM date_mutation)::int
FROM dvf_mutations_parcelle WHERE nature_mutation LIKE 'Vente%';
"""


def load():
    conn = psycopg.connect("dbname=labuse user=openclaw")
    cur = conn.cursor()
    cur.execute(PC_SQL)
    pc = {r[0]: {"y": r[1], "realized": r[2], "granted": r[3]} for r in cur.fetchall()}
    cur.execute(MUT_SQL)
    mut = defaultdict(set)
    for idu, my in cur.fetchall():
        mut[idu].add(my)
    cur.execute(META_SQL)
    meta = {}
    for idu, commune, surf, emprise, zone in cur.fetchall():
        meta[idu] = {"commune": commune, "surf": surf or 0, "emprise": emprise or 0, "zone": zone or "NA"}
    conn.close()
    return pc, mut, meta


def mutated(mut, idu, y):
    return int(any(y + 3 <= my <= y + 6 for my in mut.get(idu, ())))


def surf_bin(s):
    for i, b in enumerate((150, 300, 500, 1000, 2500)):
        if s < b:
            return i
    return 5


def OR_ci(y_a, y_b, n_boot=2000):
    """OR P(a)/P(b) + IC95 bootstrap indépendant (tableaux binaires triés → reproductible)."""
    a, b = np.sort(np.array(y_a)), np.sort(np.array(y_b))
    if a.size < 20 or b.size < 20:
        return {"n_a": int(a.size), "n_b": int(b.size), "insufficient": True}

    def OR(x, z):
        px, pz = x.mean(), z.mean()
        px = min(max(px, 1e-9), 1 - 1e-9); pz = min(max(pz, 1e-9), 1 - 1e-9)
        return (px / (1 - px)) / (pz / (1 - pz))
    rng = np.random.RandomState(SEED)
    boots = [OR(a[rng.randint(0, a.size, a.size)], b[rng.randint(0, b.size, b.size)]) for _ in range(n_boot)]
    return {"n_a": int(a.size), "n_b": int(b.size), "p_a": float(a.mean()), "p_b": float(b.mean()),
            "odds_ratio": float(OR(a, b)), "ic95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}


def main():
    print("chargement PC/mutations/meta ...", file=sys.stderr)
    pc, mut, meta = load()

    # classification parcelle-level, cohortes observables
    caduc, realise = [], []
    for idu, d in pc.items():
        if d["y"] not in COHORTS:
            continue
        rec = (idu, d["y"], mutated(mut, idu, d["y"]))
        if d["realized"]:
            realise.append(rec)
        elif d["granted"]:
            caduc.append(rec)
    res = {"n_caduc": len(caduc), "n_realise": len(realise), "cohorts": COHORTS}

    # ── (a) caduc vs réalisés — CRITÈRE PRINCIPAL ──
    ya = [m for _, _, m in caduc]
    yb = [m for _, _, m in realise]
    res["comparateur_a_realises"] = OR_ci(ya, yb)

    # par cohorte
    res["par_cohorte"] = {}
    for Y in COHORTS:
        ca = [m for _, y, m in caduc if y == Y]
        ra = [m for _, y, m in realise if y == Y]
        res["par_cohorte"][Y] = {
            "n_caduc": len(ca), "p_caduc": (float(np.mean(ca)) if ca else None),
            "n_realise": len(ra), "p_realise": (float(np.mean(ra)) if ra else None)}

    # ── variante robustesse : caduc ∩ « nue » (emprise < seuil) ──
    caduc_nue = [(i, y, m) for i, y, m in caduc if meta.get(i, {}).get("emprise", 0) < BARE_M2]
    res["caduc_nue"] = {"n": len(caduc_nue),
                        "vs_realises": OR_ci([m for _, _, m in caduc_nue], yb)}

    # ── (b) caduc vs SANS-PC apparié (commune × surface × zonage) ──
    # index des parcelles sans PC par strate
    pc_idus = set(pc)
    strata = defaultdict(list)
    for idu, mt in meta.items():
        if idu in pc_idus:
            continue
        strata[(mt["commune"], surf_bin(mt["surf"]), mt["zone"])].append(idu)
    rng = np.random.RandomState(SEED)
    ctrl = []
    for idu, y, _ in caduc:
        mt = meta.get(idu)
        if not mt:
            continue
        pool = strata.get((mt["commune"], surf_bin(mt["surf"]), mt["zone"]), [])
        if not pool:
            continue
        for j in rng.choice(len(pool), min(len(pool), 20), replace=False):
            ctrl.append(mutated(mut, pool[j], y))          # même fenêtre calendaire que le caduc
    res["comparateur_b_sans_pc"] = OR_ci(ya, ctrl)

    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "backtest.json"), "w"), indent=2, default=str)

    def line(tag, d):
        if d.get("insufficient"):
            print(f"  {tag}: insuffisant (a={d['n_a']}, b={d['n_b']})")
        else:
            print(f"  {tag}: OR={d['odds_ratio']:.2f} IC95[{d['ic95'][0]:.2f},{d['ic95'][1]:.2f}] "
                  f"p_caduc={d['p_a']:.4f}(n={d['n_a']}) p_ref={d['p_b']:.4f}(n={d['n_b']})")
    print(f"\n=== PC CADUCS — cohortes {COHORTS[0]}-{COHORTS[-1]} ===")
    print(f"  caduc={res['n_caduc']}  realise={res['n_realise']}")
    print("\n=== OR (mutation [Y+3,Y+6]) ===")
    line("(a) vs réalisés   ", res["comparateur_a_realises"])
    line("(b) vs sans-PC    ", res["comparateur_b_sans_pc"])
    line("(a') caduc nue    ", res["caduc_nue"]["vs_realises"])
    print("\n=== par cohorte (p_caduc vs p_realise) ===")
    for Y in COHORTS:
        c = res["par_cohorte"][Y]
        pc_ = f"{c['p_caduc']:.4f}" if c["p_caduc"] is not None else "  —  "
        pr_ = f"{c['p_realise']:.4f}" if c["p_realise"] is not None else "  —  "
        print(f"  {Y}: caduc {pc_} (n={c['n_caduc']:>4}) · realise {pr_} (n={c['n_realise']:>5})")
    print(f"\nJSON -> {os.path.join(OUT, 'backtest.json')}")


if __name__ == "__main__":
    main()
