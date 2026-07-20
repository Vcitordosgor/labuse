#!/usr/bin/env python
"""PHASE A-1 — Backtest « fenêtre de sortie de défiscalisation » (LECTURE SEULE).

Teste l'empreinte agrégée : des bosses de REVENTE à +6/+9 ans après une acquisition
dans le NEUF, que la strate ANCIEN n'a pas. Aucune écriture DB, aucune identité de
personne physique — on travaille sur un timing par parcelle.

Sources (schémas identiques, union directe) :
  - dvf_mutations_histo      : 2014-2020, id_parcelle direct
  - dvf_mutations_parcelle   : 2021-2025, id_parcelle direct (DVF récent résolu parcelle)
Enrichissement :
  - VEFA  = nature_mutation 'Vente en l'état futur d'achèvement' (label direct « achat neuf »)
  - permis: p_model_permits (PC) JOIN m10_permit_delais.date_achevement (proxy achèvement, 41%)
  - copro : p_model_ext_copro (mono = copro_rnic=false ET copro_dvf=false)

Usage: python scripts/a1_defisc_backtest.py   (écrit reports/a1-defisc/backtest.json + tables)
"""
from __future__ import annotations
import json, os, sys
from collections import defaultdict
from datetime import date
import numpy as np
import psycopg

OBS_END = date(2025, 12, 31)          # fin de fenêtre d'observation (max DVF récent)
GRACE = 2.0                           # ans : neutralise l'acte de livraison VEFA (signature en
                                      # l'état futur → acte définitif ~1 an après, même prix ≈ pas
                                      # une revente). Appliqué symétriquement aux deux strates
                                      # (retire aussi les flips rapides de l'ancien). Diagnostic :
                                      # 821/1063 VEFA mono ont un « événement » < 6 mois, ratio prix 1,00.
SEED = 974
VEFA = "Vente en l'état futur d'achèvement"
OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "a1-defisc")

PULL = """
WITH muts AS (
  SELECT id_parcelle AS idu, date_mutation::date AS dt, id_mutation AS mid,
         nature_mutation AS nat, type_local AS tl, surface_reelle_bati AS surf
  FROM dvf_mutations_histo
  WHERE nature_mutation IN ('Vente', %(vefa)s)
  UNION ALL
  SELECT id_parcelle, date_mutation::date, id_mutation,
         nature_mutation, type_local, surface_reelle_bati
  FROM dvf_mutations_parcelle
  WHERE nature_mutation IN ('Vente', %(vefa)s)
),
ach AS (
  SELECT pmp.idu, min(md.date_achevement) AS ach
  FROM p_model_permits pmp
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type = 'PC' AND md.date_achevement IS NOT NULL
  GROUP BY pmp.idu
)
SELECT m.idu, m.dt, m.nat, m.tl, m.surf,
       (COALESCE(c.copro_rnic,false) OR COALESCE(c.copro_dvf,false)) AS copro,
       a.ach
FROM muts m
LEFT JOIN p_model_ext_copro c ON c.idu = m.idu
LEFT JOIN ach a ON a.idu = m.idu
ORDER BY m.idu, m.dt;
"""

DWELLING = {"Maison", "Appartement"}


def load():
    conn = psycopg.connect("dbname=labuse user=openclaw")
    with conn.cursor() as cur:
        cur.execute(PULL, {"vefa": VEFA})
        rows = cur.fetchall()
    conn.close()
    # regrouper par parcelle -> événements (une date = un événement, plusieurs type_local possibles)
    by_idu = defaultdict(lambda: {"copro": False, "ach": None, "events": defaultdict(lambda: {"vefa": False, "types": set(), "surf": []})})
    for idu, dt, nat, tl, surf, copro, ach in rows:
        p = by_idu[idu]
        p["copro"] = bool(copro)
        p["ach"] = ach
        ev = p["events"][dt]
        if nat == VEFA:
            ev["vefa"] = True
        if tl:
            ev["types"].add(tl)
        if tl == "Appartement" and surf:
            ev["surf"].append(surf)
    return by_idu


def yrs(d0, d1):
    return (d1 - d0).days / 365.25


def build_acquisitions(by_idu):
    """Retourne une liste d'acquisitions : (strate, copro, cohorte, resale_t|None, censor_t)."""
    acqs = []
    for idu, p in by_idu.items():
        ach = p["ach"]
        dates = sorted(p["events"])
        for i, A in enumerate(dates):
            ev = p["events"][A]
            # l'acquisition doit concerner un logement (pas une vente de dépendance seule)
            if not (ev["types"] & DWELLING) and not ev["vefa"]:
                continue
            # strate d'acquisition
            if ev["vefa"]:
                strate = "neuf_vefa"
            elif ach is not None and 0 <= (A - ach).days <= 3 * 365:
                strate = "neuf_permis"
            elif ach is None or (A - ach).days > 5 * 365:
                strate = "ancien"
            else:
                continue  # zone grise 3-5 ans après achèvement : exclue pour ne pas polluer
            # prochain événement = revente (logement) au-delà de la période de grâce
            # (< GRACE = acte de livraison VEFA / flip immédiat = même transaction, pas une revente)
            resale_t = None
            for B in dates[i + 1:]:
                t = yrs(A, B)
                if t <= GRACE:
                    continue
                evb = p["events"][B]
                if evb["types"] & DWELLING or evb["vefa"]:
                    resale_t = t
                    break
            censor_t = yrs(A, OBS_END)
            if censor_t <= 0:
                continue
            acqs.append({
                "idu": idu, "strate": strate, "copro": p["copro"],
                "cohorte": A.year, "resale_t": resale_t, "censor_t": censor_t,
            })
    return acqs


def life_table(acqs, kmax=12):
    """Hazard discret annuel avec censure (table de mortalité)."""
    n = len(acqs)
    resale = np.array([a["resale_t"] if a["resale_t"] is not None else np.inf for a in acqs])
    censor = np.array([a["censor_t"] for a in acqs])
    obs = np.minimum(resale, censor)
    event = resale <= censor
    rows = []
    for k in range(1, kmax + 1):
        at_risk = int(np.sum(obs >= (k - 1)))                 # entrent dans l'intervalle [k-1,k)
        d = int(np.sum(event & (resale > k - 1) & (resale <= k)))
        c = int(np.sum(~event & (censor > k - 1) & (censor <= k)))
        h = d / at_risk if at_risk else float("nan")
        rows.append({"k": k, "at_risk": at_risk, "events": d, "censored": c, "hazard": h})
    return {"n": n, "table": rows}


def window_rate(acqs, lo, hi, cohorts):
    """P(revente dans [A+lo, A+hi]) — inconditionnel, cohortes dont la fenêtre est observable."""
    sel = [a for a in acqs if a["cohorte"] in cohorts]
    if not sel:
        return None
    y = np.array([1 if (a["resale_t"] is not None and lo <= a["resale_t"] <= hi) else 0 for a in sel])
    # exiger que la fenêtre soit observable : censor_t >= hi
    obsv = np.array([a["censor_t"] >= hi for a in sel])
    y = y[obsv]
    return {"n": int(y.size), "hits": int(y.sum()), "rate": float(y.mean()) if y.size else float("nan")}


def odds_ratio_boot(acqs_neuf, acqs_anc, lo, hi, cohorts, n_boot=2000):
    """Odds ratio P(revente[lo,hi]) neuf vs ancien + IC95 bootstrap (seed 974)."""
    def prep(acqs):
        sel = [a for a in acqs if a["cohorte"] in cohorts and a["censor_t"] >= hi]
        return np.array([1 if (a["resale_t"] is not None and lo <= a["resale_t"] <= hi) else 0 for a in sel])
    yn, ya = prep(acqs_neuf), prep(acqs_anc)
    if yn.size < 20 or ya.size < 20:
        return {"n_neuf": int(yn.size), "n_anc": int(ya.size), "insufficient": True}
    # tri des tableaux binaires : rend le bootstrap reproductible indépendamment de l'ordre
    # de lignes renvoyé par le SGBD (le rééchantillonnage ne dépend que du multiset, sans biais).
    yn, ya = np.sort(yn), np.sort(ya)

    def OR(a, b):
        pa, pb = a.mean(), b.mean()
        pa = min(max(pa, 1e-6), 1 - 1e-6); pb = min(max(pb, 1e-6), 1 - 1e-6)
        return (pa / (1 - pa)) / (pb / (1 - pb))
    rng = np.random.RandomState(SEED)
    boots = []
    for _ in range(n_boot):
        boots.append(OR(yn[rng.randint(0, yn.size, yn.size)], ya[rng.randint(0, ya.size, ya.size)]))
    boots = np.array(boots)
    return {
        "n_neuf": int(yn.size), "n_anc": int(ya.size),
        "p_neuf": float(yn.mean()), "p_anc": float(ya.mean()),
        "odds_ratio": float(OR(yn, ya)),
        "ic95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
    }


def apartment_lot_analysis(by_idu, n_boot=2000):
    """Mécanisme PROPRE au niveau du LOT appartement (copro) : on suit un appartement précis
    via (parcelle + type Appartement + surface ±15 %) plutôt que la parcelle entière, pour
    retirer la contamination « un autre lot se vend ». VEFA-appart vs ancien-appart."""
    acqs = []  # (strate, resale_t|None, censor_t, cohorte)
    for idu, p in by_idu.items():
        if not p["copro"]:
            continue
        dates = sorted(p["events"])
        # index des ventes d'appartement avec surface
        appt = [(d, s) for d in dates for s in p["events"][d]["surf"]]
        for i, A in enumerate(dates):
            ev = p["events"][A]
            if "Appartement" not in ev["types"]:
                continue
            surfs = ev["surf"] or [None]
            strate = "neuf_vefa" if ev["vefa"] else ("ancien" if p["ach"] is None else None)
            if strate is None:
                continue
            for sA in surfs:
                # revente = appartement de surface comparable, > GRACE, plus tard
                resale_t = None
                for (B, sB) in appt:
                    t = yrs(A, B)
                    if t <= GRACE:
                        continue
                    if sA and sB and abs(sB - sA) <= 0.15 * sA:
                        resale_t = t
                        break
                censor_t = yrs(A, OBS_END)
                if censor_t > 0 and sA:
                    acqs.append({"strate": strate, "resale_t": resale_t, "censor_t": censor_t, "cohorte": A.year})
    neuf = [a for a in acqs if a["strate"] == "neuf_vefa"]
    anc = [a for a in acqs if a["strate"] == "ancien"]
    return {
        "n_neuf": len(neuf), "n_anc": len(anc),
        "hazard_neuf": life_table(neuf), "hazard_anc": life_table(anc),
        "w68": odds_ratio_boot(neuf, anc, 6, 8, set(range(2014, 2018)), n_boot),
        "w911": odds_ratio_boot(neuf, anc, 9, 11, set(range(2014, 2017)), n_boot),
    }


def prospective_coverage():
    """Parcelles de l'univers scoré (431k) portant une fenêtre de sortie ACTIVE 2026-2028.
    Fenêtre = [acq+6, acq+8] ou [acq+9, acq+11] chevauchant 2026-2028.
    Acquisition neuf = dernière VEFA (ou Vente ≤3 ans après achèvement PC). Par commune + copro."""
    conn = psycopg.connect("dbname=labuse user=openclaw")
    sql = """
    WITH ach AS (
      SELECT pmp.idu, min(md.date_achevement) ach FROM p_model_permits pmp
      JOIN m10_permit_delais md ON md.permit_id=pmp.permit_id
      WHERE pmp.type='PC' AND md.date_achevement IS NOT NULL GROUP BY pmp.idu),
    acq AS (  -- dernière acquisition NEUF par parcelle (VEFA, ou Vente <=3 ans apres achevement)
      SELECT m.idu, max(m.dt) AS acq_dt FROM (
        SELECT id_parcelle idu, date_mutation::date dt, nature_mutation nat, type_local tl
        FROM dvf_mutations_histo WHERE nature_mutation IN ('Vente', %(v)s)
        UNION ALL
        SELECT id_parcelle, date_mutation::date, nature_mutation, type_local
        FROM dvf_mutations_parcelle WHERE nature_mutation IN ('Vente', %(v)s)) m
      LEFT JOIN ach a ON a.idu=m.idu
      WHERE (m.nat=%(v)s)
         OR (a.ach IS NOT NULL AND m.dt>=a.ach AND m.dt < a.ach + INTERVAL '3 years' AND m.tl IN ('Maison','Appartement'))
      GROUP BY m.idu)
    SELECT p.commune,
           CASE WHEN (COALESCE(c.copro_rnic,false) OR COALESCE(c.copro_dvf,false)) THEN 'copro' ELSE 'mono' END AS classe,
           count(*) AS parcelles,
           count(*) FILTER (WHERE EXTRACT(YEAR FROM acq_dt) BETWEEN 2015 AND 2020) AS fen_active_2026_2028
    FROM acq
    JOIN parcels p ON p.idu=acq.idu
    LEFT JOIN p_model_ext_copro c ON c.idu=acq.idu
    GROUP BY 1,2 ORDER BY 4 DESC;
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"v": VEFA})
        rows = cur.fetchall()
    conn.close()
    tot = defaultdict(lambda: {"parcelles": 0, "fenetre_active": 0})
    par_commune = []
    for commune, classe, parcelles, active in rows:
        tot[classe]["parcelles"] += parcelles
        tot[classe]["fenetre_active"] += int(active)
        par_commune.append({"commune": commune, "classe": classe, "parcelles": parcelles, "fenetre_active": int(active)})
    return {"total": dict(tot), "par_commune": par_commune}


def main():
    print("chargement timeline 2014-2025 ...", file=sys.stderr)
    by_idu = load()
    acqs = build_acquisitions(by_idu)
    print(f"{len(by_idu)} parcelles, {len(acqs)} acquisitions", file=sys.stderr)

    result = {"obs_end": OBS_END.isoformat(), "n_parcelles": len(by_idu), "n_acquisitions": len(acqs)}

    # ── ventilations ──
    def subset(copro, strates):
        return [a for a in acqs if a["copro"] == copro and a["strate"] in strates]

    result["effectifs"] = {}
    for cl, copro in (("mono", False), ("copro", True)):
        for st in ("neuf_vefa", "neuf_permis", "ancien"):
            s = subset(copro, {st})
            result["effectifs"][f"{cl}/{st}"] = {
                "n": len(s),
                "par_cohorte": {y: sum(1 for a in s if a["cohorte"] == y) for y in range(2014, 2026)},
            }

    # ── tables de mortalité : mono et copro, neuf (vefa+permis) vs ancien ──
    result["hazard"] = {}
    for cl, copro in (("mono", False), ("copro", True)):
        result["hazard"][cl] = {
            "neuf": life_table(subset(copro, {"neuf_vefa", "neuf_permis"})),
            "neuf_vefa": life_table(subset(copro, {"neuf_vefa"})),
            "ancien": life_table(subset(copro, {"ancien"})),
        }

    # ── lifts [6,8] et [9,11] ──
    result["lifts"] = {}
    for cl, copro in (("mono", False), ("copro", True)):
        neuf = subset(copro, {"neuf_vefa", "neuf_permis"})
        anc = subset(copro, {"ancien"})
        result["lifts"][cl] = {
            "w68_c2014_2017": odds_ratio_boot(neuf, anc, 6, 8, set(range(2014, 2018))),
            "w911_c2014_2016": odds_ratio_boot(neuf, anc, 9, 11, set(range(2014, 2017))),
            "w611_c2014_2016": odds_ratio_boot(neuf, anc, 6, 11, set(range(2014, 2017))),
            "rate_neuf_68": window_rate(neuf, 6, 8, set(range(2014, 2018))),
            "rate_anc_68": window_rate(anc, 6, 8, set(range(2014, 2018))),
        }

    # ── mécanisme propre : appartement lot-level (surface-matché) ──
    result["appartement_lot"] = apartment_lot_analysis(by_idu)

    # ── couverture prospective 2026-2028 ──
    result["couverture"] = prospective_coverage()

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "backtest.json"), "w") as f:
        json.dump(result, f, indent=2, default=str)

    # ── impression lisible ──
    print("\n=== EFFECTIFS (acquisitions par classe/strate) ===")
    for k, v in result["effectifs"].items():
        print(f"  {k:22s} n={v['n']}")
    for cl in ("mono", "copro"):
        print(f"\n=== HAZARD {cl.upper()} (revente | ancienneté) ===")
        print(f"  {'k':>3} | {'neuf h':>9} (risq) | {'vefa h':>9} | {'ancien h':>9} (risq)")
        H = result["hazard"][cl]
        for i in range(12):
            n, vf, a = H["neuf"]["table"][i], H["neuf_vefa"]["table"][i], H["ancien"]["table"][i]
            print(f"  {i+1:>3} | {n['hazard']:>9.4f} ({n['at_risk']:>4}) | {vf['hazard']:>9.4f} | {a['hazard']:>9.4f} ({a['at_risk']:>4})")
    print("\n=== LIFTS ===")
    for cl in ("mono", "copro"):
        L = result["lifts"][cl]
        for w in ("w68_c2014_2017", "w911_c2014_2016", "w611_c2014_2016"):
            d = L[w]
            if d.get("insufficient"):
                print(f"  {cl}/{w}: effectif insuffisant (neuf={d['n_neuf']}, ancien={d['n_anc']})")
            else:
                print(f"  {cl}/{w}: OR={d['odds_ratio']:.2f} IC95[{d['ic95'][0]:.2f},{d['ic95'][1]:.2f}] "
                      f"p_neuf={d['p_neuf']:.3f}(n={d['n_neuf']}) p_anc={d['p_anc']:.3f}(n={d['n_anc']})")
    print("\n=== APPARTEMENT LOT-LEVEL (surface-matché, mécanisme propre) ===")
    AL = result["appartement_lot"]
    print(f"  n_neuf(vefa appart)={AL['n_neuf']}  n_anc(appart ancien)={AL['n_anc']}")
    print(f"  {'k':>3} | {'neuf h':>9} (risq) | {'ancien h':>9} (risq)")
    for i in range(12):
        n, a = AL["hazard_neuf"]["table"][i], AL["hazard_anc"]["table"][i]
        print(f"  {i+1:>3} | {n['hazard']:>9.4f} ({n['at_risk']:>5}) | {a['hazard']:>9.4f} ({a['at_risk']:>5})")
    for w in ("w68", "w911"):
        d = AL[w]
        if d.get("insufficient"):
            print(f"  {w}: insuffisant (neuf={d['n_neuf']}, anc={d['n_anc']})")
        else:
            print(f"  {w}: OR={d['odds_ratio']:.2f} IC95[{d['ic95'][0]:.2f},{d['ic95'][1]:.2f}] "
                  f"p_neuf={d['p_neuf']:.3f}(n={d['n_neuf']}) p_anc={d['p_anc']:.3f}(n={d['n_anc']})")

    print("\n=== COUVERTURE PROSPECTIVE (fenêtre active 2026-2028) ===")
    C = result["couverture"]
    for cl, v in C["total"].items():
        print(f"  {cl}: {v['parcelles']} parcelles neuf identifiées, {v['fenetre_active']} avec fenêtre active 2026-2028")
    print("  top communes (fenêtre active) :")
    for r in sorted(C["par_commune"], key=lambda x: -x["fenetre_active"])[:12]:
        print(f"    {r['commune']:22s} {r['classe']:5s} active={r['fenetre_active']:4d} (total neuf {r['parcelles']})")
    print(f"\nJSON -> {os.path.join(OUT, 'backtest.json')}")


if __name__ == "__main__":
    main()
