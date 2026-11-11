#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-AUDIT-1 — rétro-test INDÉPENDANT de l'outil « Estimer un bien » (lecture seule).

But : mesurer, sur des ventes RÉELLES de 2025, l'écart entre le prix que l'outil AFFICHE et le prix
réellement constaté (DVF). Médiane, quartiles, part à ±20 %, globalement / par type / par commune.

Ce banc reproduit la chaîne RÉELLEMENT SERVIE par le code (non la médiane pondérée interne) :

  · BÂTI (maison) — le €/m² servi au total est celui de `reference_locale` / `sector_price`
    (faisabilite/bilan.py) : échantillon COMMUNE dédoublonné par mutation, MÊME type, surf ≥ 20 m²,
    valeur > 20 000 €, vente de gré à gré (VEFA exclue du servi), domaine [1000 ; 12000] €/m²,
    exclusion des 5 % extrêmes, rayon adaptatif 500→1000→1500 m autour du centroïde, période RÉCENTE
    (5 ans, préférée) puis élargie, min 8 ventes — MÉDIANE SIMPLE. (La médiane pondérée de
    `comparateur_bien`/ESTIMER-PRECISION-1 ne sert qu'à choisir les 8 comparables AFFICHÉS : elle est
    ÉCRASÉE par `reference_locale` pour le chiffre de tête dès que le type est maison/appartement.)
    Surface du total : (connue) surface bâtie réelle de la vente — intrant observable ; (auto, défaut
    de l'outil) dernière vente DVF ANTÉRIEURE, sinon emprise BD TOPO × ratio médian surface/emprise
    de la commune.

  · TERRAIN NU — repère €/m² de la SECTION cadastrale (left(idu,10)) : ventes « Vente » + « Vente
    terrain à bâtir » SANS bâti, domaine [50 ; 20000] €/m², médiane simple, min 8 ventes (table
    `dvf_secteur_medianes`, reproduite ici point-in-time). Total = surface de la parcelle × repère.

NO-LEAK : pour chaque vente jugée, les comparables sont strictement `date_mutation < date de la vente`
ET la mutation jugée est exclue. L'année de référence de la fenêtre « récente » = 2026 (jour Réunion),
comme le code servi (`annee_ref`). Échantillon : 200 maisons + 200 terrains de 2025 (tirage aléatoire
graine fixe parmi les ventes mono-parcelle jugeables).

Rejeu : LABUSE_DATABASE_URL=postgresql+psycopg:///labuse <venv>/python docs/audit-2026-11/estimer-1/banc.py
"""
from __future__ import annotations

import csv
import json
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import sqlalchemy as sa

ICI = Path(__file__).resolve().parent
URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")
ENGINE = sa.create_engine(URL)

ANNEE_REF = 2026                 # = annee_ref() servi (jour Réunion, 2026-11)
PERIODE_RECENTE_ANS = 5          # PERIODE_SECTEUR_ANS
AN_RECENTE = ANNEE_REF - PERIODE_RECENTE_ANS + 1   # 2022
RAYONS = (500.0, 1000.0, 1500.0)
MIN_N = 8                        # MIN_N_SECTEUR
TRIM = 0.05                      # 5 % extrêmes (2,5 % chaque queue)
BORNES_BATI = (1000.0, 12000.0)
BORNES_TERR = (50.0, 20000.0)    # domaine de la table dvf_secteur_medianes
GARDE_BATI = (1000.0, 12000.0)   # une vente jugée hors de là = artefact DVF, non jugée
GARDE_TERR = (50.0, 4000.0)      # domaine du comparateur terrain de l'outil
RATIO_ASSISE_MIN = 20
N_SAMPLE = 200
SEED = 20261110


def trim_5pct(prices: list[float]) -> list[float]:
    """Exclut 2,5 % à chaque queue (floor) — sous ~20 ventes, k=0 → rien retiré. Comme trim_extremes_5pct."""
    xs = sorted(prices)
    n = len(xs)
    k = int(n * (TRIM / 2))
    if k == 0:
        return xs
    return xs[k:n - k]


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Chargement
# ════════════════════════════════════════════════════════════════════════════════════════════════
_UNIVERS_SQL = """
  WITH base AS (
    SELECT id_mutation, id_parcelle, type_local,
           COALESCE(surface_reelle_bati,0) AS bati, COALESCE(surface_terrain,0) AS terr,
           nature_mutation, valeur_fonciere, date_mutation
    FROM dvf_mutations_parcelle
    WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')
      AND extract(year FROM date_mutation) = 2025),
  lig AS (SELECT DISTINCT id_mutation,id_parcelle,type_local,bati FROM base),
  terr_p AS (SELECT id_mutation,id_parcelle, max(terr) AS terr FROM base GROUP BY 1,2),
  mut AS (SELECT id_mutation, count(DISTINCT id_parcelle) AS np, sum(bati) AS bati_m2,
                 bool_or(type_local='Maison') AS am, bool_or(type_local='Appartement') AS aa
          FROM lig GROUP BY id_mutation),
  terrm AS (SELECT id_mutation, sum(terr) AS terrain_m2 FROM terr_p GROUP BY id_mutation),
  vtbm AS (SELECT id_mutation, bool_or(nature_mutation='Vente terrain à bâtir') AS vtb,
                  max(valeur_fonciere) AS valeur, min(date_mutation) AS dmin, min(id_parcelle) AS idu
           FROM base GROUP BY id_mutation)
  SELECT v.idu, v.id_mutation AS mid, v.valeur, v.dmin::date AS d, left(v.idu,5) AS insee,
         m.bati_m2, t.terrain_m2, m.am, m.aa, v.vtb
  FROM mut m JOIN terrm t USING(id_mutation) JOIN vtbm v USING(id_mutation)
  WHERE m.np = 1 AND v.valeur > 1000
"""


def charger():
    import time
    t0 = [time.time()]

    def tic(msg):
        print(f"  [{time.time()-t0[0]:6.1f}s] {msg}", flush=True)
        t0[0] = time.time()

    out = {}
    with ENGINE.connect() as c:
        # 1) univers 2025 (mono-parcelle, grain mutation)
        out["univers"] = [dict(r) for r in c.execute(sa.text(_UNIVERS_SQL)).mappings().all()]
        tic(f"univers 2025 : {len(out['univers'])}")

        # 2) pool comparable BÂTI (tous locaux de vente géo-DVF, de gré à gré) + x/y 2975
        bati = c.execute(sa.text("""
            SELECT d.commune, d.mutation_id AS mid,
                   d.valeur_fonciere / d.surface_reelle_bati AS prix,
                   lower(d.type_local) AS tl,
                   extract(year FROM d.date_mutation)::int AS annee, d.date_mutation::date AS dt,
                   ST_X(ST_Transform(d.geom,2975)) AS x, ST_Y(ST_Transform(d.geom,2975)) AS y
            FROM dvf_mutations d
            WHERE d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 0
              AND d.nature_mutation = 'Vente' AND d.geom IS NOT NULL
              AND d.type_local ILIKE ANY(ARRAY['%MAISON%','%APPARTEMENT%'])
        """)).mappings().all()
        out["bati"] = [dict(r) for r in bati]
        tic(f"pool bâti : {len(out['bati'])}")

        # 3) pool comparable TERRAIN NU par section cadastrale (grain mutation, Vente + VTB sans bâti)
        terr = c.execute(sa.text("""
          WITH mutations AS (
            SELECT id_mutation, max(valeur_fonciere) AS valeur,
                   sum(COALESCE(surface_reelle_bati,0)) AS bati_m2, sum(terrain_par_parcelle) AS terrain_m2,
                   bool_or(type_local='Maison') AS am, bool_or(type_local='Appartement') AS aa,
                   bool_or(nature_mutation='Vente terrain à bâtir') AS vtb, min(date_mutation)::date AS d
            FROM (SELECT id_mutation, valeur_fonciere, surface_reelle_bati, type_local, nature_mutation, date_mutation,
                         max(COALESCE(surface_terrain,0)) OVER (PARTITION BY id_mutation,id_parcelle)
                           / greatest(count(*) OVER (PARTITION BY id_mutation,id_parcelle),1) AS terrain_par_parcelle
                  FROM dvf_mutations_parcelle
                  WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')) x
            GROUP BY id_mutation),
          terrains AS (SELECT id_mutation, valeur/terrain_m2 AS prix_m2, d FROM mutations
                       WHERE valeur > 1000 AND am IS NOT TRUE AND aa IS NOT TRUE
                         AND bati_m2 = 0 AND terrain_m2 > 0 AND (vtb IS NOT TRUE OR bati_m2 = 0))
          SELECT DISTINCT substring(d2.id_parcelle FROM 1 FOR 10) AS secteur,
                 t.id_mutation AS mid, t.prix_m2, t.d
          FROM terrains t JOIN dvf_mutations_parcelle d2 ON d2.id_mutation = t.id_mutation
        """)).mappings().all()
        out["terr"] = [dict(r) for r in terr]
        tic(f"pool terrain : {len(out['terr'])}")

        # 4) sujets : centroïde 2975, commune, surface parcelle (contenance → dessin)
        idus = sorted({r["idu"] for r in out["univers"]})
        parc = {}
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i+CH]
            for r in c.execute(sa.text("""
                SELECT p.idu, p.commune,
                       ST_X(ST_Transform(p.centroid,2975)) AS x, ST_Y(ST_Transform(p.centroid,2975)) AS y,
                       COALESCE(p.contenance_m2, ST_Area(p.geom_2975)) AS surf_parc
                FROM parcels p WHERE p.idu = ANY(:lot)
            """), {"lot": lot}).mappings():
                parc[r["idu"]] = dict(r)
        out["parc"] = parc
        tic(f"sujets : {len(parc)}")

        # 5) emprise BD TOPO + historique ventes bâti par parcelle + ratio surface/emprise communal
        emprise, hist, ratio = {}, defaultdict(list), {}
        for i in range(0, len(idus), CH):
            lot = idus[i:i+CH]
            for r in c.execute(sa.text(
                "SELECT idu, emprise_bati_m2 AS e FROM p_model_bati "
                "WHERE idu = ANY(:lot) AND emprise_bati_m2 > 0"), {"lot": lot}).mappings():
                emprise[r["idu"]] = float(r["e"])
            for r in c.execute(sa.text(
                "SELECT id_parcelle AS idu, id_mutation AS mid, date_mutation::date AS d, "
                "  COALESCE(sum(surface_reelle_bati) FILTER "
                "    (WHERE type_local IN ('Maison','Appartement')),0) AS bati "
                "FROM dvf_mutations_parcelle "
                "WHERE id_parcelle = ANY(:lot) AND date_mutation IS NOT NULL "
                "  AND nature_mutation IN ('Vente','Vente terrain à bâtir') "
                "GROUP BY id_parcelle, id_mutation, date_mutation"), {"lot": lot}).mappings():
                hist[r["idu"]].append({"mid": r["mid"], "d": r["d"], "bati": float(r["bati"] or 0)})
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
            "GROUP BY v.insee")).mappings():
            if r["ratio"] and (r["n"] or 0) >= RATIO_ASSISE_MIN:
                ratio[r["insee"]] = round(float(r["ratio"]), 3)
        out["emprise"], out["hist"], out["ratio"] = emprise, dict(hist), ratio
        tic(f"emprise {len(emprise)} · hist {len(hist)} · ratio {len(ratio)}")
    return out


def index_bati(bati):
    par = defaultdict(list)
    for r in bati:
        tl = r["tl"] or ""
        par[r["commune"]].append((float(r["prix"]), "maison" in tl, "appart" in tl,
                                  int(r["annee"]), r["dt"], float(r["x"]), float(r["y"]), r["mid"]))
    out = {}
    for com, lst in par.items():
        out[com] = {
            "prix": np.array([e[0] for e in lst]),
            "maison": np.array([e[1] for e in lst], dtype=bool),
            "appart": np.array([e[2] for e in lst], dtype=bool),
            "annee": np.array([e[3] for e in lst]),
            "d": np.array([e[4] for e in lst]),
            "x": np.array([e[5] for e in lst]), "y": np.array([e[6] for e in lst]),
            "mid": np.array([e[7] for e in lst], dtype=object),
        }
    return out


def index_terr(terr):
    par = defaultdict(list)
    for r in terr:
        par[r["secteur"]].append((float(r["prix_m2"]), r["d"], r["mid"]))
    out = {}
    for sec, lst in par.items():
        out[sec] = {"prix": np.array([e[0] for e in lst]),
                    "d": np.array([e[1] for e in lst]),
                    "mid": np.array([e[2] for e in lst], dtype=object)}
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  €/m² SERVI (reference_locale / sector_price) — point-in-time, no-leak
# ════════════════════════════════════════════════════════════════════════════════════════════════
def eur_m2_bati(subj, pool, d_vente, mid, type_bien):
    """Médiane SIMPLE €/m² du secteur, MÊME type, rayon adaptatif + période récente→élargie + trim 5 %.
    Renvoie (median, n, radius, commune_fallback) ou (None,0,None,False). Reproduit reference_locale ;
    repli commune reproduit le dernier ressort de comparateur_bien quand reference_locale est vide."""
    if pool is None:
        return None, 0, None, False
    typ_mask = pool["maison"] if type_bien == "maison" else pool["appart"]
    avant = (pool["d"] < d_vente) & (pool["mid"] != mid) & typ_mask
    if not avant.any():
        return None, 0, None, False
    dx, dy = pool["x"] - subj["x"], pool["y"] - subj["y"]
    dist = np.sqrt(dx*dx + dy*dy)
    prix = pool["prix"]
    dom = avant & (prix >= BORNES_BATI[0]) & (prix <= BORNES_BATI[1])
    # reference_locale : période récente préférée, puis élargie ; rayons croissants ; min_n après trim
    for an_min in (AN_RECENTE, 0):
        per = dom & (pool["annee"] >= an_min)
        for r in RAYONS:
            m = per & (dist <= r)
            vals = trim_5pct([float(x) for x in prix[m]])
            if len(vals) >= MIN_N:
                return statistics.median(vals), len(vals), int(r), False
    # repli commune entière (dernier ressort servi) : tout le type, toutes années, après trim
    vals_all = trim_5pct([float(x) for x in prix[dom]])
    if vals_all:
        return statistics.median(vals_all), len(vals_all), None, True
    return None, 0, None, False


def eur_m2_terrain(secteur, pool, d_vente, mid):
    """Repère €/m² terrain nu de la SECTION, médiane simple, domaine [50;20000], min 8 — point-in-time."""
    p = pool.get(secteur)
    if p is None:
        return None, 0
    m = (p["d"] < d_vente) & (p["mid"] != mid) & (p["prix"] >= BORNES_TERR[0]) & (p["prix"] <= BORNES_TERR[1])
    vals = [float(x) for x in p["prix"][m]]
    if len(vals) < MIN_N:
        return None, 0
    return statistics.median(vals), len(vals)


def surface_auto(idu, d_vente, mid, D):
    """Surface SERVE-TIME par défaut (no-leak) : dernière vente DVF antérieure, sinon emprise × ratio."""
    prior = [h for h in D["hist"].get(idu, []) if h["d"] < d_vente and h["mid"] != mid]
    if prior:
        b = max(prior, key=lambda h: h["d"])["bati"]
        if b > 0:
            return b, "dvf_vente"
    emp = D["emprise"].get(idu)
    rat = D["ratio"].get(idu[:5])
    if emp and rat:
        return emp * rat, "emprise_ratio"
    return None, None


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Métriques
# ════════════════════════════════════════════════════════════════════════════════════════════════
def quart(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return {"n": 0, "mediane": None, "q1": None, "q3": None, "pct_20": None, "pct_10": None}
    if len(xs) >= 4:
        q1, _m, q3 = statistics.quantiles(xs, n=4, method="inclusive")
    else:
        q1, q3 = xs[0], xs[-1]
    return {"n": len(xs), "mediane": round(statistics.median(xs), 1),
            "q1": round(q1, 1), "q3": round(q3, 1),
            "pct_20": round(100*sum(1 for x in xs if x <= 20)/len(xs), 1),
            "pct_10": round(100*sum(1 for x in xs if x <= 10)/len(xs), 1)}


def principal():
    print("Chargement…", flush=True)
    D = charger()
    IDXB = index_bati(D["bati"])
    IDXT = index_terr(D["terr"])
    rng = random.Random(SEED)

    # ── tirage des 200 maisons + 200 terrains jugeables ───────────────────────────────────────────
    maisons, terrains = [], []
    for row in D["univers"]:
        idu, insee = row["idu"], row["insee"]
        p = D["parc"].get(idu)
        if p is None:
            continue
        bati = float(row["bati_m2"] or 0)
        terr = float(row["terrain_m2"] or 0)
        val = float(row["valeur"])
        # MAISON : bâti maison, pas appartement, surface ≥ 20, €/m² dans le garde-fou
        if row["am"] and not row["aa"] and bati >= 20:
            reel = val / bati
            if GARDE_BATI[0] <= reel <= GARDE_BATI[1]:
                maisons.append({**row, **{"p": p, "reel_m2": reel, "reel_total": val, "bati": bati}})
        # TERRAIN NU : ni maison ni appartement, bâti nul, terrain > 0
        elif (not row["am"]) and (not row["aa"]) and bati == 0 and terr > 0:
            reel = val / terr
            if GARDE_TERR[0] <= reel <= GARDE_TERR[1]:
                terrains.append({**row, **{"p": p, "reel_m2": reel, "reel_total": val, "terr": terr}})
    rng.shuffle(maisons)
    rng.shuffle(terrains)
    maisons = maisons[:N_SAMPLE]
    terrains = terrains[:N_SAMPLE]
    print(f"  maisons jugeables tirées : {len(maisons)} · terrains : {len(terrains)}", flush=True)

    rows_csv = []
    # ── MAISONS ───────────────────────────────────────────────────────────────────────────────────
    err_m2_h, err_tot_connu, err_tot_auto = [], [], []
    par_com_h = defaultdict(lambda: {"connu": [], "auto": []})
    n_auto_dvf = n_auto_emprise = n_auto_absent = 0
    for k in maisons:
        subj = {"x": k["p"]["x"], "y": k["p"]["y"]}
        med, n, radius, cf = eur_m2_bati(subj, IDXB.get(k["p"]["commune"]), k["d"], k["mid"], "maison")
        e_m2 = e_connu = e_auto = None
        sauto, ssrc = surface_auto(k["idu"], k["d"], k["mid"], D)
        if ssrc == "dvf_vente":
            n_auto_dvf += 1
        elif ssrc == "emprise_ratio":
            n_auto_emprise += 1
        else:
            n_auto_absent += 1
        if med:
            e_m2 = abs(med / k["reel_m2"] - 1.0) * 100
            e_connu = abs(k["bati"] * med / k["reel_total"] - 1.0) * 100
            if sauto:
                e_auto = abs(sauto * med / k["reel_total"] - 1.0) * 100
        err_m2_h.append(e_m2)
        err_tot_connu.append(e_connu)
        err_tot_auto.append(e_auto)
        par_com_h[k["insee"]]["connu"].append(e_connu)
        par_com_h[k["insee"]]["auto"].append(e_auto)
        rows_csv.append(["maison", k["idu"], k["insee"], round(k["reel_m2"], 1),
                         round(med, 1) if med else "", n, radius or "", cf,
                         round(k["reel_total"]), round(k["bati"]),
                         round(sauto) if sauto else "", ssrc or "",
                         round(e_m2, 1) if e_m2 is not None else "",
                         round(e_connu, 1) if e_connu is not None else "",
                         round(e_auto, 1) if e_auto is not None else ""])

    # ── TERRAINS ──────────────────────────────────────────────────────────────────────────────────
    err_m2_t, err_tot_t = [], []
    par_com_t = defaultdict(list)
    for k in terrains:
        sec = k["idu"][:10]
        med, n = eur_m2_terrain(sec, IDXT, k["d"], k["mid"])
        e_m2 = e_tot = None
        surf_parc = float(k["p"]["surf_parc"] or 0)
        if med:
            e_m2 = abs(med / k["reel_m2"] - 1.0) * 100
            if surf_parc > 0:
                e_tot = abs(surf_parc * med / k["reel_total"] - 1.0) * 100
        err_m2_t.append(e_m2)
        err_tot_t.append(e_tot)
        par_com_t[k["insee"]].append(e_tot)
        rows_csv.append(["terrain", k["idu"], k["insee"], round(k["reel_m2"], 1),
                         round(med, 1) if med else "", n, "", "",
                         round(k["reel_total"]), "", round(surf_parc), "section",
                         round(e_m2, 1) if e_m2 is not None else "",
                         round(e_tot, 1) if e_tot is not None else "", ""])

    # ── Rapport ─────────────────────────────────────────────────────────────────────────────────
    rapport = {
        "echantillon": {"maisons_tirees": len(maisons), "terrains_tires": len(terrains),
                        "n_sample_vise": N_SAMPLE, "seed": SEED, "annee_ventes": 2025,
                        "annee_ref_fenetre": ANNEE_REF},
        "surface_auto_maison": {"via_vente_dvf_anterieure": n_auto_dvf,
                                "via_emprise_ratio": n_auto_emprise, "indisponible": n_auto_absent},
        "maison": {
            "eur_m2": quart(err_m2_h),
            "total_surface_connue": quart(err_tot_connu),
            "total_surface_auto": quart(err_tot_auto),
        },
        "terrain": {
            "eur_m2": quart(err_m2_t),
            "total": quart(err_tot_t),
        },
        "par_commune_maison_total_auto": {
            insee: quart(v["auto"]) for insee, v in sorted(par_com_h.items())
            if quart(v["auto"])["n"] >= 8
        },
        "par_commune_maison_total_connu": {
            insee: quart(v["connu"]) for insee, v in sorted(par_com_h.items())
            if quart(v["connu"])["n"] >= 8
        },
        "par_commune_terrain_total": {
            insee: quart(v) for insee, v in sorted(par_com_t.items()) if quart(v)["n"] >= 8
        },
    }

    def ligne(nom, q):
        print(f"  {nom:<34} n={q['n']:>3}  médiane {str(q['mediane'])+'%':>8}  "
              f"Q1 {str(q['q1'])+'%':>7}  Q3 {str(q['q3'])+'%':>8}  ±20% {str(q['pct_20'])+'%':>7}")

    print("\n════════  MAISON (200 ventes 2025)  ════════")
    ligne("€/m² seul", rapport["maison"]["eur_m2"])
    ligne("TOTAL (surface connue)", rapport["maison"]["total_surface_connue"])
    ligne("TOTAL (surface auto = défaut outil)", rapport["maison"]["total_surface_auto"])
    print(f"  surface auto : {n_auto_dvf} via vente DVF antérieure · {n_auto_emprise} via emprise×ratio · "
          f"{n_auto_absent} indisponible")
    print("\n════════  TERRAIN NU (200 ventes 2025)  ════════")
    ligne("€/m² seul", rapport["terrain"]["eur_m2"])
    ligne("TOTAL (surface parcelle)", rapport["terrain"]["total"])

    print("\n════════  PAR COMMUNE — maison, TOTAL surface auto (n≥8)  ════════")
    for insee, q in rapport["par_commune_maison_total_auto"].items():
        ligne(insee, q)
    print("\n════════  PAR COMMUNE — terrain, TOTAL (n≥8)  ════════")
    for insee, q in rapport["par_commune_terrain_total"].items():
        ligne(insee, q)

    with open(ICI / "METRIQUES.json", "w") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    with open(ICI / "PAR-VENTE.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["type", "idu", "insee", "reel_eur_m2", "est_eur_m2", "n_comparables", "radius_m",
                    "commune_fallback", "reel_total_eur", "bati_m2", "surface_estimee_m2", "src_surface",
                    "err_eur_m2_pct", "err_total_connu_pct", "err_total_auto_pct"])
        w.writerows(rows_csv)
    print(f"\nécrit : {ICI/'METRIQUES.json'} · {ICI/'PAR-VENTE.csv'}")


if __name__ == "__main__":
    principal()
