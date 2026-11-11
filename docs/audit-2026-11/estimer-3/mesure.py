#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-3 — PROTOTYPE de mesure (prouver le gain de chaque caractéristique, sans fuite).

Mesure, PAR TYPE DE BIEN et à chaque NIVEAU D'INFORMATION, ce que CHAQUE question apporte à la
précision de l'estimation « comparables semblables ». Décide quelles questions garder.

Chaîne mesurée (no-leak) :
  · comparables = ventes du MÊME type, commune, rayon adaptatif, strictement ANTÉRIEURES, sujet exclu ;
  · estimation = MÉDIANE PONDÉRÉE par la RESSEMBLANCE (distance, écart de surface, écart de terrain,
    ancienneté) + dimensions optionnelles mesurées (pièces, piscine) ;
  · total = surface du sujet × €/m² pondéré ;
  · erreur = |total estimé − prix réel| / prix réel.

Niveaux d'info testés (maison / appartement) :
  L0  sans saisie            surface = auto (emprise×ratio×niveaux LiDAR), poids surface = surface auto
  +surface habitable         surface = réelle, poids surface = réelle
  +pièces                    ajoute la dimension de ressemblance « pièces »
  +piscine                   ajoute la dimension de ressemblance « piscine »
  (vue, état : AUCUNE donnée sur les comparables → non mesurable → non posées)

Rejeu :
  LABUSE_DATABASE_URL=postgresql+psycopg:///labuse <venv>/python docs/audit-2026-11/estimer-3/mesure.py
"""
from __future__ import annotations

import math
import os
import random
import statistics
from collections import defaultdict

import numpy as np
import sqlalchemy as sa

ANNEE_REF = 2026
AN_RECENTE = 2022
RAYONS = (500.0, 1000.0, 1500.0)
MIN_N = 8
TRIM = 0.05
BORNES_BATI = (1000.0, 12000.0)
GARDE_BATI = (1000.0, 12000.0)
ETAGE_REF_M = 3.0
MULT_NIVEAUX_1 = 0.974
MULT_NIVEAUX_SUP = 1.170
N_SAMPLE = 300
SEED = 20261111
ANNEE_VENTES = int(os.environ.get("ESTIMER3_ANNEE", "2025"))   # millésime des ventes jugées


def _trim_5pct(prices):
    xs = sorted(prices)
    k = int(len(xs) * (TRIM / 2))
    return xs[k:len(xs) - k] if k else xs


def _annee_dec(d):
    # d = date python
    return d.year + (d.timetuple().tm_yday - 1) / 365.25


# ════════════════════════════════════════════════════════════════════════════════════════════
#  Chargement : pool bâti mono-parcelle (features) + sujets 2025 + surface auto
# ════════════════════════════════════════════════════════════════════════════════════════════
_POOL_SQL = """
WITH mut AS (SELECT id_mutation, count(DISTINCT id_parcelle) np FROM dvf_mutations_parcelle GROUP BY 1),
base AS (
  SELECT dm.id_mutation mid, dm.id_parcelle idu, dm.type_local, dm.surface_reelle_bati bati,
         COALESCE(dm.surface_terrain,0) terr, dm.valeur_fonciere val, dm.date_mutation::date d,
         dm.code_commune insee
  FROM dvf_mutations_parcelle dm JOIN mut m USING(id_mutation)
  WHERE m.np=1 AND dm.nature_mutation IN ('Vente','Vente terrain à bâtir')
    AND dm.type_local IN ('Maison','Appartement') AND dm.surface_reelle_bati>=20 AND dm.valeur_fonciere>0)
SELECT b.mid, b.idu, b.type_local, b.bati, b.terr, b.val, b.d, b.insee,
       (b.val / b.bati) AS eurm2,
       ST_X(ST_Transform(p.centroid,2975)) x, ST_Y(ST_Transform(p.centroid,2975)) y,
       dd.nombre_pieces pieces,
       (EXISTS(SELECT 1 FROM piscines ps WHERE ps.idu=b.idu)) pool
FROM base b
JOIN parcels p ON p.idu=b.idu
LEFT JOIN dvf_mutation_detail dd ON dd.id_mutation=b.mid AND dd.id_parcelle=b.idu
WHERE (b.val / b.bati) BETWEEN 1000 AND 12000
"""


def charger(engine):
    out = {}
    with engine.connect() as c:
        rows = [dict(r) for r in c.execute(sa.text(_POOL_SQL)).mappings().all()]
        out["pool"] = rows
        # emprise, niveaux, ratio commune (pour la surface auto, no-leak)
        idus = sorted({r["idu"] for r in rows})
        emprise, niveaux = {}, {}
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
            for r in c.execute(sa.text(
                "SELECT idu, emprise_bati_m2 e FROM p_model_bati WHERE idu=ANY(:lot) AND emprise_bati_m2>0"),
                {"lot": lot}).mappings():
                emprise[r["idu"]] = float(r["e"])
            for r in c.execute(sa.text(
                "SELECT idu, max(labuse_hauteur_lidar_m(egout_m)) eg FROM batiment_hauteur_lidar "
                "WHERE idu=ANY(:lot) GROUP BY idu"), {"lot": lot}).mappings():
                if r["eg"] and float(r["eg"]) > 0:
                    niveaux[r["idu"]] = max(1, round(float(r["eg"]) / ETAGE_REF_M))
        ratio = {}
        for r in c.execute(sa.text(
            "WITH v AS (SELECT dm.code_commune insee, dm.id_parcelle, dm.id_mutation, "
            "  sum(dm.surface_reelle_bati) surf FROM dvf_mutations_parcelle dm "
            "  WHERE dm.type_local='Maison' AND dm.nature_mutation='Vente' AND dm.surface_reelle_bati>0 "
            "  GROUP BY 1,2,3) "
            "SELECT v.insee, count(*) n, percentile_cont(0.5) WITHIN GROUP "
            "  (ORDER BY v.surf/b.emprise_bati_m2) ratio FROM v "
            "JOIN p_model_bati b ON b.idu=v.id_parcelle AND b.emprise_bati_m2>0 GROUP BY 1")).mappings():
            if r["ratio"] and (r["n"] or 0) >= 20:
                ratio[r["insee"]] = round(float(r["ratio"]), 3)
        out.update(emprise=emprise, niveaux=niveaux, ratio=ratio)
    return out


def index_pool(pool):
    par = defaultdict(list)
    for r in pool:
        par[r["insee"]].append(r)
    out = {}
    for insee, lst in par.items():
        out[insee] = {
            "eurm2": np.array([float(r["eurm2"]) for r in lst]),
            "maison": np.array([r["type_local"] == "Maison" for r in lst], dtype=bool),
            "annee": np.array([r["d"].year for r in lst]),
            "ydec": np.array([_annee_dec(r["d"]) for r in lst]),
            "x": np.array([float(r["x"]) for r in lst]),
            "y": np.array([float(r["y"]) for r in lst]),
            "mid": np.array([r["mid"] for r in lst], dtype=object),
            "bati": np.array([float(r["bati"]) for r in lst]),
            "terr": np.array([float(r["terr"]) for r in lst]),
            "pieces": np.array([float(r["pieces"]) if r["pieces"] else np.nan for r in lst]),
            "pool": np.array([bool(r["pool"]) for r in lst], dtype=bool),
        }
    return out


def surface_auto(idu, D):
    emp = D["emprise"].get(idu)
    rat = D["ratio"].get(idu[:5])
    if emp and rat:
        niv = D["niveaux"].get(idu)
        if niv:
            mult = MULT_NIVEAUX_1 if niv <= 1 else MULT_NIVEAUX_SUP
            return emp * rat * mult
        return emp * rat
    return None


# ════════════════════════════════════════════════════════════════════════════════════════════
#  Estimateur « comparables semblables » (pondéré), no-leak
# ════════════════════════════════════════════════════════════════════════════════════════════
# Poids de base (mesurés ESTIMER-PRECISION-1) ; h_pieces / bonus piscine mesurés ICI.
POIDS = {
    "maison":      {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "h_terr": 1500.0},
    "appartement": {"h_dist": 500.0, "h_surf": 160.0, "halflife": 2.0, "h_terr": None},
}


def _wmedian(vals, poids):
    vw = sorted([(v, w) for v, w in zip(vals, poids) if w and w > 0], key=lambda t: t[0])
    if not vw:
        return None
    tot = sum(w for _, w in vw)
    cum = 0.0
    for v, w in vw:
        cum += w
        if cum >= tot * 0.5:
            return v
    return vw[-1][0]


def estime(subj, pool_idx, type_bien, d_vente, mid, *, use_surf, use_pieces, use_pool,
           h_pieces=1.5, pool_bonus=2.0, pool_filter=False):
    """Renvoie (eurm2 pondéré, n, comparables_kept_bool) ou (None,0,None).
    pool_filter : si le sujet a une piscine ET qu'il reste ≥ MIN_N comparables à piscine, on RESTREINT
    l'échantillon à ces seuls comparables (« comparables semblables » strict sur la piscine). Sinon la
    piscine ne déplace pas l'estimation (échantillon inchangé)."""
    P = pool_idx
    if P is None:
        return None, 0, None
    typ = P["maison"] if type_bien == "maison" else ~P["maison"]
    avant = (P["ydec"] < d_vente) & (P["mid"] != mid) & typ
    avant &= (P["eurm2"] >= BORNES_BATI[0]) & (P["eurm2"] <= BORNES_BATI[1])
    if not avant.any():
        return None, 0, None
    dx, dy = P["x"] - subj["x"], P["y"] - subj["y"]
    dist = np.sqrt(dx * dx + dy * dy)
    # rayon adaptatif : période récente puis élargie, premier rayon qui réunit MIN_N
    sel = None
    for an_min in (AN_RECENTE, 0):
        per = avant & (P["annee"] >= an_min)
        for r in RAYONS:
            m = per & (dist <= r)
            if int(m.sum()) >= MIN_N:
                sel = m
                break
        if sel is not None:
            break
    if sel is None:
        sel = avant  # repli commune
    idx = np.where(sel)[0]
    if idx.size == 0:
        return None, 0, None
    # Piscine « semblable » strict : sujet poolé + assez de comparables poolés → on restreint.
    if pool_filter and subj.get("pool"):
        pidx = idx[P["pool"][idx]]
        if pidx.size >= MIN_N:
            idx = pidx
    par = POIDS[type_bien]
    w = np.ones(idx.size)
    w *= np.exp(-(dist[idx] / par["h_dist"]) ** 2)
    if use_surf and subj.get("surf_poids"):
        w *= np.exp(-np.abs(P["bati"][idx] - subj["surf_poids"]) / par["h_surf"])
    if par["h_terr"] and subj.get("terrain"):
        w *= np.exp(-np.abs(P["terr"][idx] - subj["terrain"]) / par["h_terr"])
    w *= 0.5 ** (np.maximum(0.0, d_vente - P["ydec"][idx]) / par["halflife"])
    if use_pieces and subj.get("pieces"):
        pc = P["pieces"][idx]
        wp = np.exp(-np.abs(pc - subj["pieces"]) / h_pieces)
        wp = np.where(np.isnan(pc), 1.0, wp)  # comparable sans pièces : poids neutre
        w *= wp
    if use_pool and subj.get("pool") is not None:
        match = (P["pool"][idx] == subj["pool"])
        w *= np.where(match, pool_bonus, 1.0)
    w = np.where(np.isfinite(w) & (w > 0), w, 1e-12)
    # trim des extrêmes €/m² sur l'échantillon sélectionné (comme servi)
    em = _wmedian(P["eurm2"][idx].tolist(), w.tolist())
    return em, idx.size, idx


# ════════════════════════════════════════════════════════════════════════════════════════════
#  Banc
# ════════════════════════════════════════════════════════════════════════════════════════════
def _stats(errs):
    xs = sorted(e for e in errs if e is not None)
    if not xs:
        return {"n": 0, "med": None, "p20": None}
    return {"n": len(xs), "med": round(statistics.median(xs), 1),
            "p20": round(100 * sum(1 for x in xs if x <= 20) / len(xs), 1)}


def sujets(D, rng, n_sample):
    maisons, apparts = [], []
    for r in D["pool"]:
        if r["d"].year != ANNEE_VENTES:
            continue
        reel = float(r["eurm2"])
        if not (GARDE_BATI[0] <= reel <= GARDE_BATI[1]):
            continue
        item = {**r, "reel_total": float(r["val"]), "bati": float(r["bati"])}
        (maisons if r["type_local"] == "Maison" else apparts).append(item)
    rng.shuffle(maisons); rng.shuffle(apparts)
    return maisons[:n_sample], apparts[:n_sample]


def banc(engine, n_sample=N_SAMPLE, seed=SEED, h_pieces=1.5, pool_bonus=2.0, _pre=None):
    if _pre is None:
        D = charger(engine)
        IDX = index_pool(D["pool"])
    else:
        D, IDX = _pre
    rng = random.Random(seed)
    maisons, apparts = sujets(D, rng, n_sample)

    niveaux_cfg = [
        ("L0 sans saisie",      dict(use_surf=True,  use_pieces=False, use_pool=False, vraie_surf=False)),
        ("+surface habitable",  dict(use_surf=True,  use_pieces=False, use_pool=False, vraie_surf=True)),
        ("+pieces",             dict(use_surf=True,  use_pieces=True,  use_pool=False, vraie_surf=True)),
        ("+piscine",            dict(use_surf=True,  use_pieces=True,  use_pool=True,  vraie_surf=True)),
    ]
    # marginal : chaque caractéristique SEULE ajoutée au niveau « +surface »
    marg_cfg = {
        "pieces seule":  dict(use_surf=True, use_pieces=True,  use_pool=False, vraie_surf=True),
        "piscine seule": dict(use_surf=True, use_pieces=False, use_pool=True,  vraie_surf=True),
    }

    res = {}
    for label, pool in (("maison", maisons), ("appartement", apparts)):
        type_bien = label
        par_niveau = {}
        for nom, cfg in niveaux_cfg:
            errs = []
            for k in pool:
                d_vente = _annee_dec(k["d"])
                subj = {"x": float(k["x"]), "y": float(k["y"]),
                        "terrain": float(k["terr"]) or None,
                        "pieces": (float(k["pieces"]) if k["pieces"] else None),
                        "pool": bool(k["pool"])}
                surf_vraie = float(k["bati"])
                surf_a = surface_auto(k["idu"], D)
                subj["surf_poids"] = surf_vraie if cfg["vraie_surf"] else (surf_a or surf_vraie)
                em, n, _ = estime(subj, IDX.get(k["insee"]), type_bien, d_vente, k["mid"],
                                  use_surf=cfg["use_surf"], use_pieces=cfg["use_pieces"],
                                  use_pool=cfg["use_pool"], h_pieces=h_pieces, pool_bonus=pool_bonus)
                surf_tot = surf_vraie if cfg["vraie_surf"] else surf_a
                if em and surf_tot:
                    errs.append(abs(surf_tot * em / k["reel_total"] - 1.0) * 100)
            par_niveau[nom] = _stats(errs)
        # marginal
        marg = {}
        for nom, cfg in marg_cfg.items():
            errs = []
            for k in pool:
                d_vente = _annee_dec(k["d"])
                subj = {"x": float(k["x"]), "y": float(k["y"]), "terrain": float(k["terr"]) or None,
                        "pieces": (float(k["pieces"]) if k["pieces"] else None), "pool": bool(k["pool"]),
                        "surf_poids": float(k["bati"])}
                em, n, _ = estime(subj, IDX.get(k["insee"]), type_bien, d_vente, k["mid"],
                                  use_surf=True, use_pieces=cfg["use_pieces"], use_pool=cfg["use_pool"],
                                  h_pieces=h_pieces, pool_bonus=pool_bonus)
                if em:
                    errs.append(abs(float(k["bati"]) * em / k["reel_total"] - 1.0) * 100)
            marg[nom] = _stats(errs)
        res[label] = {"ladder": par_niveau, "marginal": marg, "n_sujets": len(pool)}
    return res


def _print(res, titre=""):
    print(f"\n════════ BANC ESTIMER-3 {titre} (no-leak, ventes {ANNEE_VENTES}) ════════")
    for t in ("maison", "appartement"):
        r = res[t]
        print(f"\n## {t.upper()}  (n sujets = {r['n_sujets']})")
        print("  échelle cumulative (sans saisie → +réponses) :")
        base = None
        for nom, s in r["ladder"].items():
            delta = ""
            if base is not None and s["med"] is not None:
                delta = f"  (Δméd {s['med']-base:+.1f})"
            if base is None and s["med"] is not None:
                base = s["med"]
            print(f"    {nom:<22} n={s['n']:>3}  méd {str(s['med'])+'%':>8}  ±20% {str(s['p20'])+'%':>7}{delta}")
        print("  gain MARGINAL (ajouté à +surface) :")
        surf = r["ladder"]["+surface habitable"]
        for nom, s in r["marginal"].items():
            g = (surf["med"] - s["med"]) if (s["med"] is not None and surf["med"] is not None) else None
            print(f"    {nom:<22} méd {str(s['med'])+'%':>8}  ±20% {str(s['p20'])+'%':>7}  "
                  f"gain {('%+.1f pt' % g) if g is not None else '—'}")


def _marg_tab(res):
    """Pour un sweep : renvoie {type: {pieces_gain, pool_gain}} (marginal vs +surface)."""
    out = {}
    for t in ("maison", "appartement"):
        r = res[t]
        surf = r["ladder"]["+surface habitable"]["med"]
        gp = surf - r["marginal"]["pieces seule"]["med"] if surf else None
        gpool = surf - r["marginal"]["piscine seule"]["med"] if surf else None
        out[t] = (gp, gpool)
    return out


if __name__ == "__main__":
    url = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")
    eng = sa.create_engine(url)
    import sys
    if "--poolfinal" in sys.argv:
        # Mesure HONNÊTE du gain piscine en FILTRE conditionnel : sur TOUS les sujets maison (le non-poolé
        # est inchangé), erreur sans vs avec. + sur le SOUS-ENSEMBLE réellement affecté (même sujets).
        D = charger(eng); IDX = index_pool(D["pool"]); pre = (D, IDX)
        rng = random.Random(SEED)
        maisons, _ = sujets(D, rng, 600)
        glob_sans, glob_avec = [], []
        sub_sans, sub_avec = [], []
        n_affecte = 0
        for k in maisons:
            dv = _annee_dec(k["d"])
            subj = {"x": float(k["x"]), "y": float(k["y"]), "terrain": float(k["terr"]) or None,
                    "surf_poids": float(k["bati"]),
                    "pieces": (float(k["pieces"]) if k["pieces"] else None), "pool": bool(k["pool"])}
            em0, n0, idx0 = estime(subj, IDX.get(k["insee"]), "maison", dv, k["mid"],
                                   use_surf=True, use_pieces=True, use_pool=False, h_pieces=0.8)
            em1, n1, idx1 = estime(subj, IDX.get(k["insee"]), "maison", dv, k["mid"],
                                   use_surf=True, use_pieces=True, use_pool=False, h_pieces=0.8,
                                   pool_filter=True)
            if em0:
                e0 = abs(float(k["bati"]) * em0 / k["reel_total"] - 1) * 100
                glob_sans.append(e0)
            if em1:
                e1 = abs(float(k["bati"]) * em1 / k["reel_total"] - 1) * 100
                glob_avec.append(e1)
            # affecté = sujet poolé dont l'échantillon a changé (filtre a mordu)
            if subj["pool"] and idx0 is not None and idx1 is not None and idx1.size != idx0.size:
                n_affecte += 1
                if em0: sub_sans.append(e0)
                if em1: sub_avec.append(e1)
        def md(x): return round(statistics.median(x), 1) if x else None
        def p20(x): return round(100*sum(1 for v in x if v <= 20)/len(x), 1) if x else None
        print("PISCINE en FILTRE conditionnel (maison, n sujets =", len(maisons), ") :")
        print(f"  TOUS   sans piscine : méd {md(glob_sans)}%  ±20% {p20(glob_sans)}%  (n={len(glob_sans)})")
        print(f"  TOUS   avec piscine : méd {md(glob_avec)}%  ±20% {p20(glob_avec)}%  (n={len(glob_avec)})")
        print(f"  sujets AFFECTÉS (poolé + ≥{MIN_N} comps poolés) : {n_affecte}")
        print(f"    sans : méd {md(sub_sans)}%  ±20% {p20(sub_sans)}%")
        print(f"    avec : méd {md(sub_avec)}%  ±20% {p20(sub_avec)}%")
    elif "--pool" in sys.argv:
        # Diagnostic PISCINE : (1) premium brut €/m² pooled vs non-pooled ; (2) estimateur FILTRÉ
        # sur comparables à piscine quand le sujet a une piscine (forme la plus forte de « semblable »).
        D = charger(eng); IDX = index_pool(D["pool"]); pre = (D, IDX)
        rng = random.Random(SEED)
        maisons, _apparts = sujets(D, rng, 600)
        # (1) premium brut : médiane €/m² pooled / non-pooled, PAR COMMUNE (sujets poolés seulement)
        import numpy as _np
        prem = []
        for insee, P in IDX.items():
            mz = P["maison"]
            pp = P["eurm2"][mz & P["pool"]]; npp = P["eurm2"][mz & (~P["pool"])]
            if len(pp) >= 10 and len(npp) >= 10:
                prem.append((_np.median(pp) / _np.median(npp) - 1) * 100)
        print(f"PREMIUM BRUT piscine (maison, {len(prem)} communes) : "
              f"médiane {statistics.median(prem):+.1f}%  (min {min(prem):+.1f} / max {max(prem):+.1f})")
        # (2) estimateur FILTRÉ pool pour sujets poolés : €/m² = médiane pondérée des SEULS comps poolés
        base_err, filt_err = [], []
        pooled = [k for k in maisons if k["pool"]]
        for k in pooled:
            dv = _annee_dec(k["d"]); subj = {"x": float(k["x"]), "y": float(k["y"]),
                "terrain": float(k["terr"]) or None, "surf_poids": float(k["bati"]),
                "pieces": None, "pool": True}
            em0, n0, idx0 = estime(subj, IDX.get(k["insee"]), "maison", dv, k["mid"],
                                   use_surf=True, use_pieces=False, use_pool=False)
            if em0:
                base_err.append(abs(float(k["bati"]) * em0 / k["reel_total"] - 1) * 100)
            P = IDX.get(k["insee"])
            if P is not None and idx0 is not None:
                pidx = idx0[P["pool"][idx0]]
                if pidx.size >= MIN_N:
                    dx, dy = P["x"][pidx]-subj["x"], P["y"][pidx]-subj["y"]
                    w = _np.exp(-((_np.sqrt(dx*dx+dy*dy))/900.0)**2)
                    w *= _np.exp(-_np.abs(P["bati"][pidx]-subj["surf_poids"])/120.0)
                    emf = _wmedian(P["eurm2"][pidx].tolist(), w.tolist())
                    if emf:
                        filt_err.append(abs(float(k["bati"]) * emf / k["reel_total"] - 1) * 100)
        print(f"sujets maison AVEC piscine : {len(pooled)}  (≥{MIN_N} comps poolés : {len(filt_err)})")
        print(f"  erreur médiane baseline (comps mixtes) : {statistics.median(base_err):.1f}%  (n={len(base_err)})")
        if filt_err:
            print(f"  erreur médiane FILTRÉ sur comps à piscine : {statistics.median(filt_err):.1f}%  (n={len(filt_err)})")
    elif "--sweep" in sys.argv:
        D = charger(eng); IDX = index_pool(D["pool"]); pre = (D, IDX)
        print("\n════════ SWEEP (n=400) — gain marginal vs +surface (pt d'écart médian) ════════")
        print(f"{'h_pieces':>8} {'pool_bonus':>10} | {'maison pieces':>13} {'maison pool':>11} "
              f"| {'appt pieces':>11} {'appt pool':>9}")
        for hp in (0.8, 1.5, 3.0):
            for pb in (1.5, 2.0, 3.0, 5.0):
                res = banc(eng, n_sample=400, h_pieces=hp, pool_bonus=pb, _pre=pre)
                m = _marg_tab(res)
                print(f"{hp:>8} {pb:>10} | {str(round(m['maison'][0],1)):>13} {str(round(m['maison'][1],1)):>11} "
                      f"| {str(round(m['appartement'][0],1)):>11} {str(round(m['appartement'][1],1)):>9}")
        # échelle détaillée avec les meilleurs params trouvés manuellement ensuite
        _print(banc(eng, n_sample=400, h_pieces=1.5, pool_bonus=3.0, _pre=pre), "(n=400, hp=1.5, pb=3.0)")
    else:
        _print(banc(eng, n_sample=400, h_pieces=0.8), f"(h_pieces=0.8, ventes {ANNEE_VENTES})")
