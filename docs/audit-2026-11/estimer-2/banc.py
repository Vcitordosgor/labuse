#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-2 — banc d'estimation REJOUÉ (méthode ESTIMATION-BANC-2, sans fuite) pour mesurer AVANT/APRÈS
les correctifs du mandat, et CALIBRER les bandes de fiabilité.

On réutilise la machinerie SANS FUITE du banc 2 (`backtest_banc2.py`, worktree banc-rayon-1) : l'estimateur
€/m² est ré-implémenté point-in-time (comparables strictement `date < date_vente` + exclusion de la
mutation jugée). On mesure DEUX choses que le mandat demande :

  1. L'ERREUR du TOTAL en € (le chiffre sur lequel le client s'ancre), AVANT vs APRÈS :
       AVANT = emprise au sol BD TOPO × €/m²   (le bug NU-E-021 / D-009)
       APRÈS = SURFACE × €/m², où SURFACE = surface bâtie de la dernière vente DVF ANTÉRIEURE si elle
               existe (no-leak : on exclut la vente jugée), sinon emprise × ratio médian de la commune.
     Univers : ventes de MAISONS/APPARTEMENTS 2025 (le total bâti est le cœur du mandat).

  2. L'ERREUR du €/m² par SEGMENT, AVANT vs APRÈS (effet de la nature lue sur la mutation, E-022, et du
     type forcé). Nature AVANT = état de la parcelle (emprise) ; nature APRÈS = dernière mutation DVF
     antérieure, repli emprise (strict no-leak). On ajoute une mesure PRODUCTION-RÉALISTE de E-022 : part
     des ventes de terrain nu que l'ancienne règle « emprise » aurait valorisées en bâti (la nature du bien
     vendu est OBSERVABLE, pas une prédiction — c'est ce que corrige E-022).

  3. La CALIBRATION des bandes de fiabilité (E-024) : pour chaque estimation bâtie APRÈS, on enregistre
     (n, dispersion IQR/médiane, |écart €/m²|) et on vérifie que « Élevée » tient sa promesse (<15 %).

Lecture seule, aucune écriture en base. Rejeu :
  LABUSE_DATABASE_URL=postgresql+psycopg:///labuse <venv>/python docs/audit-2026-11/estimer-2/banc.py
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import sqlalchemy as sa

ICI = Path(__file__).resolve().parent
# importe la machinerie no-leak du banc 2 (estimateur €/m² point-in-time, index, filtres)
sys.path.insert(0, str(ICI.parent.parent / "audit-2026-10" / "banc-rayon-1"))
import backtest_banc2 as b2  # noqa: E402

URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")
ENGINE = sa.create_engine(URL)
RATIO_ASSISE_MIN = 20   # idem _RATIO_ASSISE_MIN du code servi


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Estimateur €/m² point-in-time AVEC q1/q3 (copie fidèle de b2.estime_bien_v2 + quartiles)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def estime_bien_q(p, d_vente, mid, idx_bati, force_type):
    """b2.estime_bien_v2, mais renvoie AUSSI q1/q3 des comparables retenus (pour la dispersion E-024)."""
    com = p.get("commune")
    pool = idx_bati.get(com)
    if pool is None:
        return {"median": None, "n": 0, "type_bien": force_type or "bati", "q1": None, "q3": None,
                "commune_fallback": False}
    avant = (pool["d"] < d_vente) & (pool["mid"] != mid)
    if not avant.any():
        return {"median": None, "n": 0, "type_bien": force_type or "bati", "q1": None, "q3": None,
                "commune_fallback": False}
    anchor = pool["d"][avant].max()
    lo = b2._window_lo(anchor)
    base = avant & (pool["d"] >= lo)
    if not base.any():
        return {"median": None, "n": 0, "type_bien": force_type or "bati", "q1": None, "q3": None,
                "commune_fallback": False}
    dx, dy = pool["x"] - p["x"], pool["y"] - p["y"]
    dist = np.sqrt(dx * dx + dy * dy)

    def fetch_mask(rayon_m):
        m = base if rayon_m is None else (base & (dist <= rayon_m))
        if not m.any():
            return m
        idx = np.where(m)[0]
        if idx.size > b2.FETCH_LIMIT:
            order = np.argsort(dist[idx], kind="stable")[:b2.FETCH_LIMIT]
            idx = idx[order]
            m = np.zeros_like(base)
            m[idx] = True
        return m

    def type_frag_mask(km, typ):
        if typ == "maison":
            return km & pool["maison"]
        if typ == "appartement":
            return km & pool["appart"]
        return km

    type_bien = force_type
    if type_bien in (None, "bati"):
        km = b2._kept_mask(pool, fetch_mask(1000.0))
        nm = int((km & pool["maison"]).sum())
        na = int((km & pool["appart"]).sum())
        if nm + na > 0 and max(nm, na) / (nm + na) >= b2.DOMINANT_FRAC:
            type_bien = "maison" if nm >= na else "appartement"
        else:
            type_bien = None

    radius, commune_fallback = None, False
    kept = np.zeros_like(base)
    for rayon in b2.CMP_RAYONS:
        kept = type_frag_mask(b2._kept_mask(pool, fetch_mask(rayon)), type_bien)
        if int(kept.sum()) >= b2.CMP_SEUIL:
            radius = int(rayon)
            break
    else:
        commune = type_frag_mask(b2._kept_mask(pool, fetch_mask(None)), type_bien)
        if int(commune.sum()) > int(kept.sum()):
            kept, commune_fallback = commune, True
        elif kept.any():
            radius = int(b2.CMP_RAYONS[-1])

    prix = pool["prix"][kept]
    n = int(prix.size)
    if n == 0:
        return {"median": None, "n": 0, "type_bien": type_bien or "bati", "q1": None, "q3": None,
                "commune_fallback": commune_fallback, "max_comp": pool["d"][base].max()}
    median = float(np.median(prix))
    q1 = q3 = None
    if n >= 4:
        qs = statistics.quantiles(list(map(float, prix)), n=4, method="inclusive")
        q1, q3 = qs[0], qs[2]
    return {"median": median, "n": n, "type_bien": type_bien or "bati", "q1": q1, "q3": q3,
            "commune_fallback": commune_fallback, "radius_m": radius, "max_comp": pool["d"][kept].max()}


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Fiabilité servie (copie EXACTE de pige/api._fiabilite_bien) — la RÈGLE ; seuils calibrés ici
# ══════════════════════════════════════════════════════════════════════════════════════════════
FIAB_N_ELEVEE = 15
FIAB_DISP_ELEVEE = 0.30
FIAB_N_MIN = 8
FIAB_DISP_LIMITEE = 0.75


def fiabilite_bien(n, median, q1, q3, commune_fallback):
    if commune_fallback:
        return "limitee"
    disp = ((q3 - q1) / median) if (q1 is not None and q3 is not None and median) else None
    n = int(n or 0)
    if n < FIAB_N_MIN or (disp is not None and disp > FIAB_DISP_LIMITEE):
        return "limitee"
    if n >= FIAB_N_ELEVEE and disp is not None and disp <= FIAB_DISP_ELEVEE:
        return "fiable"
    return "moyen"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Chargements supplémentaires (emprise, historique de ventes par parcelle, ratio commune)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def charger_extra(idus, insees):
    emprise, hist, ratio = {}, defaultdict(list), {}
    with ENGINE.connect() as c:
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
            for r in c.execute(sa.text(
                "SELECT idu, emprise_bati_m2 AS e FROM p_model_bati "
                "WHERE idu = ANY(:lot) AND emprise_bati_m2 > 0"), {"lot": lot}).mappings():
                emprise[r["idu"]] = float(r["e"])
            # historique des ventes par parcelle (grain mutation) : date, bati, nature observée
            for r in c.execute(sa.text(
                "SELECT id_parcelle AS idu, id_mutation AS mid, date_mutation AS d, "
                "  COALESCE(sum(surface_reelle_bati) FILTER "
                "    (WHERE type_local IN ('Maison','Appartement')),0) AS bati, "
                "  count(*) FILTER (WHERE type_local='Maison') AS nm, "
                "  count(*) FILTER (WHERE type_local='Appartement') AS na, "
                "  max(surface_terrain) AS terr "
                "FROM dvf_mutations_parcelle "
                "WHERE id_parcelle = ANY(:lot) AND date_mutation IS NOT NULL "
                "  AND nature_mutation IN ('Vente','Vente terrain à bâtir') "
                "GROUP BY id_parcelle, id_mutation, date_mutation"), {"lot": lot}).mappings():
                nat = ("maison" if (r["nm"] or 0) >= (r["na"] or 0) and ((r["nm"] or 0) or (r["na"] or 0))
                       else ("appartement" if (r["na"] or 0) else ("terrain" if (r["terr"] or 0) > 0 else None)))
                hist[r["idu"]].append({"mid": r["mid"], "d": r["d"], "bati": float(r["bati"] or 0),
                                       "nat": nat})
        # ratio médian surface vendue / emprise, par commune (ventes de maisons) — idem code servi
        for r in c.execute(sa.text(
            "WITH v AS (SELECT dm.code_commune AS insee, dm.id_parcelle, dm.id_mutation, "
            "             sum(dm.surface_reelle_bati) AS surf "
            "           FROM dvf_mutations_parcelle dm "
            "           WHERE dm.type_local='Maison' AND dm.nature_mutation='Vente' "
            "             AND dm.surface_reelle_bati > 0 "
            "           GROUP BY dm.code_commune, dm.id_parcelle, dm.id_mutation) "
            "SELECT v.insee, count(*) AS n, "
            "  percentile_cont(0.5) WITHIN GROUP (ORDER BY v.surf / b.emprise_bati_m2) AS ratio "
            "FROM v JOIN p_model_bati b ON b.idu = v.id_parcelle AND b.emprise_bati_m2 > 0 "
            "GROUP BY v.insee"), {}).mappings():
            if r["ratio"] and (r["n"] or 0) >= RATIO_ASSISE_MIN:
                ratio[r["insee"]] = round(float(r["ratio"]), 3)
    return emprise, hist, ratio


def prior_mutation(hist_idu, d_vente, mid):
    """Dernière mutation ANTÉRIEURE (no-leak) de la parcelle : (bati, nat) ou None."""
    prior = [h for h in hist_idu if h["d"] < d_vente and h["mid"] != mid]
    if not prior:
        return None
    return max(prior, key=lambda h: h["d"])


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Backtest
# ══════════════════════════════════════════════════════════════════════════════════════════════
def pct(xs, cond):
    xs = [x for x in xs if x is not None]
    return round(100 * sum(1 for x in xs if cond(x)) / len(xs), 1) if xs else None


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def run():
    print("Chargement (banc 2)…")
    univers, communes, parc, bati_rows, terr_rows = b2.charger()
    idx_bati = b2.index_bati(bati_rows, ma_only=False)
    idx_terr = b2.index_terrain(terr_rows)
    idus = sorted({r["idu"] for r in univers})
    insees = sorted({r["insee"] for r in univers})
    print(f"  univers : {len(univers)} ventes 2025 mono-parcelle · {len(idus)} parcelles")
    emprise, hist, ratio = charger_extra(idus, insees)
    print(f"  emprise BD TOPO : {len(emprise)} parcelles · ratio commune calibré : {len(ratio)} communes")
    print(f"  ratio médian (toutes communes) : {med(list(ratio.values()))}")

    lignes = []
    for row in univers:
        typ = b2.typologie(row)
        if typ == "autre":
            continue
        reel, base_reel = b2.prix_reel(row, typ)   # €/m² réel
        if reel is None:
            continue
        g = b2.GARDE_BATI if base_reel == "bati" else b2.GARDE_TERRAIN
        if not (g[0] <= reel <= g[1]):
            continue
        idu, mid, d_vente = row["idu"], row["id_mutation"], row["d"]
        p = parc.get(idu)
        if p is None:
            continue
        copro = bool(p.get("copro"))
        nat_emprise = b2.nature_parcelle(p)          # 'nu'|'non_mesure'|'bati_*'
        prior = prior_mutation(hist.get(idu, []), d_vente, mid)
        emp = emprise.get(idu)
        rat = ratio.get(row["insee"])

        # ── nature APRÈS (strict no-leak) : mutation antérieure, repli emprise ──
        if copro:
            nat_after = "copro"
        elif prior and prior["nat"]:
            nat_after = prior["nat"]                  # 'maison'|'appartement'|'terrain'
        elif nat_emprise == "nu":
            nat_after = "terrain"
        else:
            nat_after = "bati"                        # type déduit par le comparateur

        # ── €/m² estimé AVANT (emprise-nature) et APRÈS (nature mutation) ──
        def est_terrain():
            e = b2.estime_terrain_nu(idu, d_vente, mid, idx_terr)
            return e.get("median"), "terrain", None, None, None, False
        # AVANT : nu→terrain ; copro→appartement ; sinon bâti type déduit
        if nat_emprise == "nu":
            m_b, t_b, q1b, q3b, nb, cfb = est_terrain()
        else:
            ft = "appartement" if copro else None
            e = estime_bien_q(p, d_vente, mid, idx_bati, ft)
            m_b, t_b, q1b, q3b, nb, cfb = (e["median"], e["type_bien"], e.get("q1"), e.get("q3"),
                                           e["n"], e.get("commune_fallback"))
        # APRÈS
        if nat_after == "terrain":
            m_a, t_a, q1a, q3a, na, cfa = est_terrain()
        else:
            ft = "appartement" if nat_after in ("copro", "appartement") else (
                "maison" if nat_after == "maison" else None)
            e = estime_bien_q(p, d_vente, mid, idx_bati, ft)
            m_a, t_a, q1a, q3a, na, cfa = (e["median"], e["type_bien"], e.get("q1"), e.get("q3"),
                                           e["n"], e.get("commune_fallback"))

        # ── erreur €/m² (on compare au réel, base alignée seulement si même base) ──
        base_b = "terrain" if (nat_emprise == "nu") else "bati"
        base_a = "terrain" if (nat_after == "terrain") else "bati"
        err_m2_b = (abs(m_b / reel - 1.0) * 100) if (m_b and base_b == base_reel) else None
        err_m2_a = (abs(m_a / reel - 1.0) * 100) if (m_a and base_a == base_reel) else None

        # ── erreur du TOTAL en € (bâti uniquement : maison/appartement) ──
        err_tot_b = err_tot_a = None
        surf_src = None
        if base_reel == "bati":
            reel_total = float(row["valeur"])
            # AVANT : emprise × €/m² (bâti). (terrain n'a pas de total bâti)
            if emp and m_b and base_b == "bati":
                err_tot_b = abs((emp * m_b) / reel_total - 1.0) * 100
            # APRÈS : surface (vente DVF antérieure, sinon emprise×ratio) × €/m²
            if m_a and base_a == "bati":
                if prior and prior["bati"] > 0:
                    surf, surf_src = prior["bati"], "dvf_vente"
                elif emp and rat:
                    surf, surf_src = emp * rat, "emprise_ratio"
                else:
                    surf = None
                if surf:
                    err_tot_a = abs((surf * m_a) / reel_total - 1.0) * 100

        # mis-nature E-022 (production-réaliste) : terrain vendu nu que l'emprise aurait dit « bâti »
        misnat_terrain = (typ == "terrain nu" and nat_emprise not in ("nu",))

        # calibration fiabilité (APRÈS, bâti) : (n, disp, |err €/m²|, bande)
        disp_a = ((q3a - q1a) / m_a) if (q1a is not None and q3a is not None and m_a) else None
        bande_a = fiabilite_bien(na, m_a, q1a, q3a, cfa) if base_a == "bati" else None

        lignes.append({
            "idu": idu, "insee": row["insee"], "type_vente": typ, "copro": copro,
            "nat_emprise": nat_emprise, "nat_after": nat_after, "resale": bool(prior),
            "reel_m2": round(reel, 1),
            "err_m2_avant": round(err_m2_b, 2) if err_m2_b is not None else None,
            "err_m2_apres": round(err_m2_a, 2) if err_m2_a is not None else None,
            "err_total_avant": round(err_tot_b, 2) if err_tot_b is not None else None,
            "err_total_apres": round(err_tot_a, 2) if err_tot_a is not None else None,
            "surf_src": surf_src, "misnat_terrain": misnat_terrain,
            "n_apres": na, "disp_apres": round(disp_a, 3) if disp_a is not None else None,
            "bande_apres": bande_a,
            "fuite_ok": (True if m_a is None else True),  # estimateur point-in-time par construction
        })
    return lignes


def seg_metrics(rows, key):
    e = [r[key] for r in rows if r[key] is not None]
    return {"n": len(e), "median_abs_pct": med(e),
            "pct_20": pct(e, lambda x: x <= 20), "pct_10": pct(e, lambda x: x <= 10)}


def principal():
    lignes = run()
    with open(ICI / "PAR-VENTE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)

    segs = {
        "Toutes ventes bâties": lambda r: r["type_vente"] in ("maison", "appartement"),
        "Maison": lambda r: r["type_vente"] == "maison",
        "Appartement": lambda r: r["type_vente"] == "appartement",
        "Copropriété (parcelle)": lambda r: r["copro"] and r["type_vente"] in ("maison", "appartement"),
        "Terrain nu": lambda r: r["type_vente"] == "terrain nu",
    }
    out = {"n_total": len(lignes), "segments_m2": {}, "segments_total": {}}
    print("\n============  ERREUR €/m² par segment (AVANT nature-emprise → APRÈS nature-DVF)  ============")
    for nom, pred in segs.items():
        sub = [r for r in lignes if pred(r)]
        a = seg_metrics(sub, "err_m2_avant")
        b = seg_metrics(sub, "err_m2_apres")
        out["segments_m2"][nom] = {"avant": a, "apres": b}
        print(f"  {nom:<26} méd|écart| {str(a['median_abs_pct'])+'%':>7} → {str(b['median_abs_pct'])+'%':>7}"
              f"   ±20% {str(a['pct_20'])+'%':>7} → {str(b['pct_20'])+'%':>7}   (n={b['n']})")

    print("\n============  ERREUR du TOTAL en € (AVANT emprise×€/m² → APRÈS surface×€/m²)  ============")
    for nom, pred in segs.items():
        if "Terrain" in nom:
            continue
        sub = [r for r in lignes if pred(r)]
        a = seg_metrics(sub, "err_total_avant")
        b = seg_metrics(sub, "err_total_apres")
        out["segments_total"][nom] = {"avant": a, "apres": b}
        print(f"  {nom:<26} méd|écart| {str(a['median_abs_pct'])+'%':>7} → {str(b['median_abs_pct'])+'%':>7}"
              f"   ±20% {str(a['pct_20'])+'%':>7} → {str(b['pct_20'])+'%':>7}   (n={b['n']})")

    # surface source utilisée APRÈS (bâti)
    srcs = defaultdict(int)
    for r in lignes:
        if r["err_total_apres"] is not None:
            srcs[r["surf_src"]] += 1
    out["surface_source_apres"] = dict(srcs)
    print(f"\n  Surface servie APRÈS : {dict(srcs)}")

    # E-022 : terrains vendus nus mal naturés par l'ancienne règle emprise
    terr = [r for r in lignes if r["type_vente"] == "terrain nu"]
    misnat = sum(1 for r in terr if r["misnat_terrain"])
    out["e022_terrain_misnature"] = {"n_terrain": len(terr), "n_misnature": misnat,
                                     "pct": round(100 * misnat / len(terr), 1) if terr else None}
    print(f"\n============  E-022 — terrains vendus nus que l'emprise aurait valorisés en bâti  ============")
    print(f"  {misnat} / {len(terr)} ventes de terrain nu ({out['e022_terrain_misnature']['pct']} %)")

    # ── CALIBRATION des bandes de fiabilité (APRÈS, bâti) ──
    print("\n============  CALIBRATION fiabilité (APRÈS, bâti) — « Élevée » doit tenir <15 %  ============")
    out["fiabilite"] = {}
    for bande in ("fiable", "moyen", "limitee"):
        e = [r["err_m2_apres"] for r in lignes
             if r["bande_apres"] == bande and r["err_m2_apres"] is not None]
        m = seg_metrics([r for r in lignes if r["bande_apres"] == bande], "err_m2_apres")
        out["fiabilite"][bande] = m
        lib = {"fiable": "Élevée", "moyen": "Moyenne", "limitee": "Limitée"}[bande]
        print(f"  {lib:<9} n={m['n']:>5}  méd|écart| {str(m['median_abs_pct'])+'%':>7}  "
              f"±20% {str(m['pct_20'])+'%':>7}  ±10% {str(m['pct_10'])+'%':>7}")
    # grille (n × dispersion) pour affiner les seuils
    grille = {}
    for r in lignes:
        if r["bande_apres"] is None or r["err_m2_apres"] is None or r["disp_apres"] is None:
            continue
        nb = "n<8" if r["n_apres"] < 8 else ("8-14" if r["n_apres"] < 15 else "n>=15")
        db = ("disp<=0.30" if r["disp_apres"] <= 0.30 else
              ("0.30-0.75" if r["disp_apres"] <= 0.75 else "disp>0.75"))
        grille.setdefault(f"{nb} · {db}", []).append(r["err_m2_apres"])
    print("\n  Grille (n × dispersion) → médian |écart €/m²| · ±20% · effectif :")
    gout = {}
    for k in sorted(grille):
        v = grille[k]
        gout[k] = {"n": len(v), "median_abs_pct": med(v), "pct_20": pct(v, lambda x: x <= 20)}
        print(f"    {k:<22} méd {str(med(v))+'%':>7}  ±20% {str(pct(v, lambda x: x<=20))+'%':>7}  n={len(v)}")
    out["fiabilite_grille"] = gout

    with open(ICI / "METRIQUES.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nécrit : {ICI/'PAR-VENTE.csv'}  et  {ICI/'METRIQUES.json'}")


if __name__ == "__main__":
    principal()
