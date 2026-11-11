#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-2 (fix/estimer-2, D-6) — BANC PERMANENT de précision de l'outil « Estimer un bien ».

Point UNIQUE : rejoue, SANS FUITE, la chaîne RÉELLEMENT SERVIE sur des ventes DVF récentes, mesure
l'écart |prix estimé − prix réel| et en tire, PAR COMMUNE et PAR TYPE (maison / terrain / appartement) :

  · l'écart médian, les quartiles Q1/Q3 de l'écart, la part à ±20 %, la part SANS PRIX ;
  · la TABLE DE CALIBRATION servie par l'outil (D-5) : la fourchette d'incertitude n'est plus un
    ±30 % fixe mais les quartiles MESURÉS ici, et la fiabilité (haute/moyenne/faible) découle de
    l'écart médian mesuré + du nombre de ventes.

NO-LEAK : pour chaque vente jugée, les comparables sont strictement `date < date de la vente` ET la
mutation jugée est exclue ; l'outil ne s'estime jamais lui-même. Fenêtre « récente » ancrée sur 2026
comme le code servi. Échantillon par défaut : 200 maisons + 200 terrains + 200 appartements (graine fixe).

Ce module est appelé :
  · par le JOB de nuit `estimer-banc-precision` (jobs_impl) → persiste la calibration + alerte si la
    précision se dégrade (COMPTE-RENDU) ;
  · par l'outil, qui LIT la calibration persistée (`pige.calibration`) pour servir la marge mesurée ;
  · par le test `tests/test_estimer2_banc.py`.

Rejeu manuel :
  LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \\
    <venv>/python -m labuse.pige.banc_estimer            # (PYTHONPATH=src)
"""
from __future__ import annotations

import os
import random
import statistics
from collections import defaultdict

import numpy as np
import sqlalchemy as sa

ANNEE_REF = 2026
PERIODE_RECENTE_ANS = 5
AN_RECENTE = ANNEE_REF - PERIODE_RECENTE_ANS + 1     # 2022
RAYONS = (500.0, 1000.0, 1500.0)
MIN_N = 8
TRIM = 0.05
BORNES_BATI = (1000.0, 12000.0)
BORNES_TERR = (50.0, 20000.0)
GARDE_BATI = (1000.0, 12000.0)
GARDE_TERR = (50.0, 4000.0)
RATIO_ASSISE_MIN = 20
MULT_NIVEAUX_1 = 0.974                               # = pige.api._MULT_NIVEAUX_1 (mesuré ici à l'origine)
MULT_NIVEAUX_SUP = 1.170                             # = pige.api._MULT_NIVEAUX_SUP
ETAGE_REF_M = 3.0
N_SAMPLE = 200
SEED = 20261111
ANNEE_VENTES = 2025                                  # millésime des ventes jugées


def _trim_5pct(prices):
    xs = sorted(prices)
    k = int(len(xs) * (TRIM / 2))
    return xs[k:len(xs) - k] if k else xs


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Chargement (une passe)
# ════════════════════════════════════════════════════════════════════════════════════════════════
_UNIVERS_SQL = """
  WITH base AS (
    SELECT id_mutation, id_parcelle, type_local,
           COALESCE(surface_reelle_bati,0) AS bati, COALESCE(surface_terrain,0) AS terr,
           nature_mutation, valeur_fonciere, date_mutation
    FROM dvf_mutations_parcelle
    WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')
      AND extract(year FROM date_mutation) = :an),
  lig AS (SELECT DISTINCT id_mutation,id_parcelle,type_local,bati FROM base),
  terr_p AS (SELECT id_mutation,id_parcelle, max(terr) AS terr FROM base GROUP BY 1,2),
  mut AS (SELECT id_mutation, count(DISTINCT id_parcelle) AS np, sum(bati) AS bati_m2,
                 bool_or(type_local='Maison') AS am, bool_or(type_local='Appartement') AS aa
          FROM lig GROUP BY id_mutation),
  terrm AS (SELECT id_mutation, sum(terr) AS terrain_m2 FROM terr_p GROUP BY id_mutation),
  vtbm AS (SELECT id_mutation, max(valeur_fonciere) AS valeur, min(date_mutation) AS dmin,
                  min(id_parcelle) AS idu FROM base GROUP BY id_mutation)
  SELECT v.idu, v.id_mutation AS mid, v.valeur, v.dmin::date AS d, left(v.idu,5) AS insee,
         m.bati_m2, t.terrain_m2, m.am, m.aa
  FROM mut m JOIN terrm t USING(id_mutation) JOIN vtbm v USING(id_mutation)
  WHERE m.np = 1 AND v.valeur > 1000
"""


def charger(engine):
    out = {}
    with engine.connect() as c:
        out["univers"] = [dict(r) for r in c.execute(sa.text(_UNIVERS_SQL),
                                                      {"an": ANNEE_VENTES}).mappings().all()]
        # pool bâti (maison + appartement, de gré à gré, géo-DVF)
        out["bati"] = [dict(r) for r in c.execute(sa.text("""
            SELECT d.commune, d.mutation_id AS mid,
                   d.valeur_fonciere / d.surface_reelle_bati AS prix,
                   lower(d.type_local) AS tl,
                   extract(year FROM d.date_mutation)::int AS annee, d.date_mutation::date AS dt,
                   ST_X(ST_Transform(d.geom,2975)) AS x, ST_Y(ST_Transform(d.geom,2975)) AS y
            FROM dvf_mutations d
            WHERE d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 0
              AND d.nature_mutation = 'Vente' AND d.geom IS NOT NULL
              AND d.type_local ILIKE ANY(ARRAY['%MAISON%','%APPARTEMENT%'])""")).mappings().all()]
        # pool TERRAIN NU géo-DVF, par parcelle (centroïde 2975), dédoublonné terrain par mutation
        out["terr"] = [dict(r) for r in c.execute(sa.text("""
          WITH parc AS (
            SELECT DISTINCT dm.id_mutation, dm.id_parcelle, dm.valeur_fonciere AS vf,
                   dm.date_mutation::date AS d, left(dm.id_parcelle,5) AS insee,
                   max(COALESCE(dm.surface_terrain,0)) OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS terr_p,
                   ST_X(ST_Transform(pp.centroid,2975)) AS x, ST_Y(ST_Transform(pp.centroid,2975)) AS y
            FROM dvf_mutations_parcelle dm JOIN parcels pp ON pp.idu = dm.id_parcelle
            WHERE dm.nature_mutation IN ('Vente','Vente terrain à bâtir')
              AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain > 0
              AND dm.date_mutation IS NOT NULL),
          t AS (SELECT id_mutation, insee, min(d) AS d, sum(terr_p) AS surf, max(vf) AS vf,
                       avg(x) AS x, avg(y) AS y
                FROM parc GROUP BY id_mutation, insee)
          SELECT id_mutation AS mid, insee, d, (vf / NULLIF(surf,0)) AS prix_m2, x, y
          FROM t WHERE vf / NULLIF(surf,0) BETWEEN :lo AND :hi""",
            ).bindparams(lo=BORNES_TERR[0], hi=BORNES_TERR[1])).mappings().all()]
        # sujets : centroïde 2975, commune, surface parcelle
        idus = sorted({r["idu"] for r in out["univers"]})
        parc, emprise, niveaux, hist = {}, {}, {}, defaultdict(list)
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
            for r in c.execute(sa.text("""
                SELECT p.idu, p.commune,
                       ST_X(ST_Transform(p.centroid,2975)) AS x, ST_Y(ST_Transform(p.centroid,2975)) AS y,
                       COALESCE(p.contenance_m2, ST_Area(p.geom_2975)) AS surf_parc
                FROM parcels p WHERE p.idu = ANY(:lot)"""), {"lot": lot}).mappings():
                parc[r["idu"]] = dict(r)
            for r in c.execute(sa.text(
                "SELECT idu, emprise_bati_m2 AS e FROM p_model_bati "
                "WHERE idu = ANY(:lot) AND emprise_bati_m2 > 0"), {"lot": lot}).mappings():
                emprise[r["idu"]] = float(r["e"])
            for r in c.execute(sa.text(
                "SELECT idu, max(labuse_hauteur_lidar_m(egout_m)) AS eg FROM batiment_hauteur_lidar "
                "WHERE idu = ANY(:lot) GROUP BY idu"), {"lot": lot}).mappings():
                if r["eg"] and float(r["eg"]) > 0:
                    niveaux[r["idu"]] = max(1, round(float(r["eg"]) / ETAGE_REF_M))
            for r in c.execute(sa.text(
                "SELECT id_parcelle AS idu, id_mutation AS mid, date_mutation::date AS d, "
                "  COALESCE(sum(surface_reelle_bati) FILTER "
                "    (WHERE type_local IN ('Maison','Appartement')),0) AS bati "
                "FROM dvf_mutations_parcelle "
                "WHERE id_parcelle = ANY(:lot) AND date_mutation IS NOT NULL "
                "  AND nature_mutation IN ('Vente','Vente terrain à bâtir') "
                "GROUP BY id_parcelle, id_mutation, date_mutation"), {"lot": lot}).mappings():
                hist[r["idu"]].append({"mid": r["mid"], "d": r["d"], "bati": float(r["bati"] or 0)})
        # ratio surface/emprise par commune (médiane, assise ≥ RATIO_ASSISE_MIN)
        ratio = {}
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
        out.update(parc=parc, emprise=emprise, niveaux=niveaux, hist=dict(hist), ratio=ratio)
    return out


def _index_bati(bati):
    par = defaultdict(list)
    for r in bati:
        tl = r["tl"] or ""
        par[r["commune"]].append((float(r["prix"]), "maison" in tl, "appart" in tl,
                                  int(r["annee"]), r["dt"], float(r["x"]), float(r["y"]), r["mid"]))
    out = {}
    for com, lst in par.items():
        out[com] = {"prix": np.array([e[0] for e in lst]),
                    "maison": np.array([e[1] for e in lst], dtype=bool),
                    "appart": np.array([e[2] for e in lst], dtype=bool),
                    "annee": np.array([e[3] for e in lst]), "d": np.array([e[4] for e in lst]),
                    "x": np.array([e[5] for e in lst]), "y": np.array([e[6] for e in lst]),
                    "mid": np.array([e[7] for e in lst], dtype=object)}
    return out


def _index_terr(terr):
    par = defaultdict(list)
    for r in terr:
        par[r["insee"]].append((float(r["prix_m2"]), r["d"], float(r["x"]), float(r["y"]), r["mid"]))
    out = {}
    for insee, lst in par.items():
        out[insee] = {"prix": np.array([e[0] for e in lst]), "d": np.array([e[1] for e in lst]),
                      "x": np.array([e[2] for e in lst]), "y": np.array([e[3] for e in lst]),
                      "mid": np.array([e[4] for e in lst], dtype=object)}
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  €/m² SERVI, no-leak (reproduit la chaîne de pige.api / faisabilite.bilan)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def eur_m2_bati(subj, pool, d_vente, mid, type_bien):
    """Médiane SIMPLE €/m² du secteur, MÊME type, rayon adaptatif + période récente→élargie + trim 5 %,
    repli commune (reproduit reference_locale / comparateur_bien)."""
    if pool is None:
        return None, 0, None, False
    typ_mask = pool["maison"] if type_bien == "maison" else pool["appart"]
    avant = (pool["d"] < d_vente) & (pool["mid"] != mid) & typ_mask
    if not avant.any():
        return None, 0, None, False
    dx, dy = pool["x"] - subj["x"], pool["y"] - subj["y"]
    dist = np.sqrt(dx * dx + dy * dy)
    prix = pool["prix"]
    dom = avant & (prix >= BORNES_BATI[0]) & (prix <= BORNES_BATI[1])
    for an_min in (AN_RECENTE, 0):
        per = dom & (pool["annee"] >= an_min)
        for r in RAYONS:
            m = per & (dist <= r)
            vals = _trim_5pct([float(x) for x in prix[m]])
            if len(vals) >= MIN_N:
                return statistics.median(vals), len(vals), int(r), False
    vals_all = _trim_5pct([float(x) for x in prix[dom]])
    if vals_all:
        return statistics.median(vals_all), len(vals_all), None, True
    return None, 0, None, False


def eur_m2_terrain(subj, pool, insee, d_vente, mid):
    """ESTIMER-2 (D-3) — repère €/m² terrain à RAYON ADAPTATIF 500→1500 m puis repli COMMUNE, no-leak."""
    p = pool.get(insee)
    if p is None:
        return None, 0, None, False
    avant = (p["d"] < d_vente) & (p["mid"] != mid) & (p["prix"] >= BORNES_TERR[0]) & (p["prix"] <= BORNES_TERR[1])
    if not avant.any():
        return None, 0, None, False
    dx, dy = p["x"] - subj["x"], p["y"] - subj["y"]
    dist = np.sqrt(dx * dx + dy * dy)
    for r in RAYONS:
        m = avant & (dist <= r)
        vals = _trim_5pct([float(x) for x in p["prix"][m]])
        if len(vals) >= MIN_N:
            return statistics.median(vals), len(vals), int(r), False
    vals_all = _trim_5pct([float(x) for x in p["prix"][avant]])
    if vals_all:
        return statistics.median(vals_all), len(vals_all), None, True
    return None, 0, None, False


def surface_auto(idu, d_vente, mid, D):
    """Surface SERVE-TIME par défaut, no-leak : dernière vente DVF antérieure, sinon emprise × ratio ×
    multiplicateur de NIVEAUX mesuré (hauteur LiDAR) — D-4."""
    prior = [h for h in D["hist"].get(idu, []) if h["d"] < d_vente and h["mid"] != mid]
    if prior:
        b = max(prior, key=lambda h: h["d"])["bati"]
        if b > 0:
            return b, "dvf_vente"
    emp = D["emprise"].get(idu)
    rat = D["ratio"].get(idu[:5])
    if emp and rat:
        niv = D["niveaux"].get(idu)
        if niv:
            mult = MULT_NIVEAUX_1 if niv <= 1 else MULT_NIVEAUX_SUP
            return emp * rat * mult, "emprise_niveaux_lidar"
        return emp * rat, "emprise_ratio"
    return None, None


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Métriques
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _quart(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return {"n": 0, "mediane": None, "q1": None, "q3": None, "pct_20": None, "pct_10": None}
    if len(xs) >= 4:
        q1, _m, q3 = statistics.quantiles(xs, n=4, method="inclusive")
    else:
        q1, q3 = xs[0], xs[-1]
    return {"n": len(xs), "mediane": round(statistics.median(xs), 1),
            "q1": round(q1, 1), "q3": round(q3, 1),
            "pct_20": round(100 * sum(1 for x in xs if x <= 20) / len(xs), 1),
            "pct_10": round(100 * sum(1 for x in xs if x <= 10) / len(xs), 1)}


def calcule(engine, n_sample: int = N_SAMPLE, seed: int = SEED) -> dict:
    """Rejoue le banc no-leak et renvoie {global, par_type, par_commune, sans_prix, calibration, meta}.
    `calibration` : liste de dicts {type_bien, insee, n, ecart_median, ecart_q1, ecart_q3, pct_20,
    pct_sans_prix} — la table servie par l'outil (D-5)."""
    D = charger(engine)
    IDXB = _index_bati(D["bati"])
    IDXT = _index_terr(D["terr"])
    rng = random.Random(seed)

    maisons, terrains, apparts = [], [], []
    for row in D["univers"]:
        p = D["parc"].get(row["idu"])
        if p is None:
            continue
        bati = float(row["bati_m2"] or 0)
        terr = float(row["terrain_m2"] or 0)
        val = float(row["valeur"])
        if row["am"] and not row["aa"] and bati >= 20:
            reel = val / bati
            if GARDE_BATI[0] <= reel <= GARDE_BATI[1]:
                maisons.append({**row, "p": p, "reel_m2": reel, "reel_total": val, "bati": bati})
        elif row["aa"] and not row["am"] and bati >= 20:
            reel = val / bati
            if GARDE_BATI[0] <= reel <= GARDE_BATI[1]:
                apparts.append({**row, "p": p, "reel_m2": reel, "reel_total": val, "bati": bati})
        elif (not row["am"]) and (not row["aa"]) and bati == 0 and terr > 0:
            reel = val / terr
            if GARDE_TERR[0] <= reel <= GARDE_TERR[1]:
                terrains.append({**row, "p": p, "reel_m2": reel, "reel_total": val, "terr": terr})
    for lst in (maisons, terrains, apparts):
        rng.shuffle(lst)
    maisons, terrains, apparts = maisons[:n_sample], terrains[:n_sample], apparts[:n_sample]

    # erreurs globales + par commune + part sans prix, par type
    err = {"maison": [], "terrain": [], "appartement": []}
    sans_prix = {"maison": 0, "terrain": 0, "appartement": 0}
    par_com = {t: defaultdict(list) for t in err}
    tries = {"maison": len(maisons), "terrain": len(terrains), "appartement": len(apparts)}

    for k in maisons:
        subj = {"x": k["p"]["x"], "y": k["p"]["y"]}
        med, _n, _r, _cf = eur_m2_bati(subj, IDXB.get(k["p"]["commune"]), k["d"], k["mid"], "maison")
        sauto, _src = surface_auto(k["idu"], k["d"], k["mid"], D)
        if med and sauto:
            e = abs(sauto * med / k["reel_total"] - 1.0) * 100
            err["maison"].append(e)
            par_com["maison"][k["insee"]].append(e)
        else:
            sans_prix["maison"] += 1

    for k in apparts:
        subj = {"x": k["p"]["x"], "y": k["p"]["y"]}
        med, _n, _r, _cf = eur_m2_bati(subj, IDXB.get(k["p"]["commune"]), k["d"], k["mid"], "appartement")
        if med:
            # surface d'un appartement : la surface Carrez/bâti de la vente (saisie par l'annonceur).
            e = abs(k["bati"] * med / k["reel_total"] - 1.0) * 100
            err["appartement"].append(e)
            par_com["appartement"][k["insee"]].append(e)
        else:
            sans_prix["appartement"] += 1

    for k in terrains:
        subj = {"x": k["p"]["x"], "y": k["p"]["y"]}
        med, _n, _r, _cf = eur_m2_terrain(subj, IDXT, k["insee"], k["d"], k["mid"])
        surf_parc = float(k["p"]["surf_parc"] or 0)
        if med and surf_parc > 0:
            e = abs(surf_parc * med / k["reel_total"] - 1.0) * 100
            err["terrain"].append(e)
            par_com["terrain"][k["insee"]].append(e)
        else:
            sans_prix["terrain"] += 1

    par_type = {t: _quart(err[t]) for t in err}
    for t in err:
        par_type[t]["pct_sans_prix"] = round(100 * sans_prix[t] / max(1, tries[t]), 1)
    glob = _quart([e for t in err for e in err[t]])

    # table de calibration (servie) : par (type, commune), quartiles de l'écart + part sans prix
    calibration = []
    par_commune_rapport = {}
    for t in err:
        par_commune_rapport[t] = {}
        for insee, es in sorted(par_com[t].items()):
            q = _quart(es)
            if q["n"] < 8:
                continue
            par_commune_rapport[t][insee] = q
            calibration.append({"type_bien": t, "insee": insee, "n": q["n"],
                                "ecart_median": q["mediane"], "ecart_q1": q["q1"], "ecart_q3": q["q3"],
                                "pct_20": q["pct_20"], "pct_sans_prix": par_type[t]["pct_sans_prix"]})

    return {"meta": {"n_sample": n_sample, "seed": seed, "annee_ventes": ANNEE_VENTES,
                     "tires": tries, "sans_prix": sans_prix},
            "global": glob, "par_type": par_type, "par_commune": par_commune_rapport,
            "calibration": calibration}


#: table de calibration servie (D-5) — une ligne par (type, commune) + une ligne « * » par type (repli).
_DDL_CALIB = """
CREATE TABLE IF NOT EXISTS estimer_precision_calibration (
  type_bien      varchar(16) NOT NULL,
  insee          varchar(8)  NOT NULL,          -- '*' = repli global du type
  n_ventes       integer     NOT NULL,
  ecart_median   real        NOT NULL,          -- écart |estimé−réel| médian MESURÉ (%)
  ecart_q1       real,
  ecart_q3       real,                           -- borne haute de la fourchette servie (%)
  pct_20         real,
  pct_sans_prix  real,
  maj            timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (type_bien, insee)
)
"""


def persiste(engine, rapport: dict) -> int:
    """Écrit la table de calibration servie (`estimer_precision_calibration`) : une ligne par
    (type, commune) calibrée + une ligne de repli « * » par type (quartiles globaux du type). Remplace
    le contenu à chaque run (la table EST la photo du dernier banc). Renvoie le nombre de lignes écrites."""
    rows = list(rapport["calibration"])
    for t, q in rapport["par_type"].items():
        if q.get("mediane") is not None:
            rows.append({"type_bien": t, "insee": "*", "n": q["n"], "ecart_median": q["mediane"],
                         "ecart_q1": q["q1"], "ecart_q3": q["q3"], "pct_20": q["pct_20"],
                         "pct_sans_prix": q.get("pct_sans_prix")})
    with engine.begin() as c:
        c.execute(sa.text(_DDL_CALIB))
        c.execute(sa.text("DELETE FROM estimer_precision_calibration"))
        for r in rows:
            c.execute(sa.text(
                "INSERT INTO estimer_precision_calibration "
                "(type_bien,insee,n_ventes,ecart_median,ecart_q1,ecart_q3,pct_20,pct_sans_prix,maj) "
                "VALUES (:t,:i,:n,:em,:q1,:q3,:p20,:psp, now())"),
                {"t": r["type_bien"], "i": r["insee"], "n": r["n"], "em": r["ecart_median"],
                 "q1": r["ecart_q1"], "q3": r["ecart_q3"], "p20": r["pct_20"],
                 "psp": r.get("pct_sans_prix")})
    return len(rows)


def charge_calibration(db, type_bien: str | None, insee: str | None) -> dict | None:
    """LECTEUR SERVI (D-5) de la marge MESURÉE : la calibration de ce (type, commune), sinon le repli
    global du type (`insee='*'`). Renvoie {ecart_median, ecart_q1, ecart_q3, pct_20, n, perimetre}
    ou None (table absente / jamais calculée → l'appelant garde la bande historique). `perimetre` =
    'commune' si la ligne commune existe, 'ile' si on a replié sur le global du type."""
    t = type_bien if type_bien in ("maison", "appartement", "terrain") else "maison"
    try:
        for ins, peri in ((insee, "commune"), ("*", "ile")):
            if ins is None:
                continue
            r = db.execute(sa.text(
                "SELECT n_ventes, ecart_median, ecart_q1, ecart_q3, pct_20 "
                "FROM estimer_precision_calibration WHERE type_bien = :t AND insee = :i"),
                {"t": t, "i": ins}).mappings().first()
            if r:
                return {"n": int(r["n_ventes"]), "ecart_median": float(r["ecart_median"]),
                        "ecart_q1": (float(r["ecart_q1"]) if r["ecart_q1"] is not None else None),
                        "ecart_q3": (float(r["ecart_q3"]) if r["ecart_q3"] is not None else None),
                        "pct_20": (float(r["pct_20"]) if r["pct_20"] is not None else None),
                        "perimetre": peri}
    except Exception:  # noqa: BLE001 — table absente (banc jamais passé) → repli bande historique
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
    return None


def _print(rapport):
    def ligne(nom, q):
        print(f"  {nom:<30} n={q['n']:>3}  médiane {str(q['mediane'])+'%':>8}  "
              f"Q1 {str(q['q1'])+'%':>7}  Q3 {str(q['q3'])+'%':>8}  ±20% {str(q['pct_20'])+'%':>7}  "
              f"sans prix {q.get('pct_sans_prix','?')}%")
    print("\n════════  BANC ESTIMER (no-leak, ventes 2025)  ════════")
    print(f"  tirés : {rapport['meta']['tires']}")
    for t in ("maison", "appartement", "terrain"):
        ligne(t.upper(), rapport["par_type"][t])
    ligne("GLOBAL (3 types)", rapport["global"])


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  ESTIMER-3 — banc permanent ÉTENDU aux NIVEAUX D'INFORMATION (comparables semblables)
#  ════════════════════════════════════════════════════════════════════════════════════════════════
#  Mesure, PAR TYPE et PAR COMMUNE, l'écart de l'estimation « comparables semblables » (le MÊME calcul
#  que `pige.estimer3.eur_m2_semblable` / `_selection_rayon` — banc == servi) à TROIS niveaux
#  d'information : surface ESTIMÉE (emprise×ratio×niveaux) / surface CONNUE / surface + pièces connues.
#  Écrit `estimer3_precision` (type, insee, niveau) : la précision servie à chaque temps de l'outil.
#  No-leak : comparables strictement antérieurs, mutation jugée exclue (comme le banc estimer-2).
_POOL3_SQL = """
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
       dd.nombre_pieces pieces
FROM base b
JOIN parcels p ON p.idu=b.idu
LEFT JOIN dvf_mutation_detail dd ON dd.id_mutation=b.mid AND dd.id_parcelle=b.idu
WHERE (b.val / b.bati) BETWEEN 1000 AND 12000
"""


def _annee_dec3(d):
    return d.year + (d.timetuple().tm_yday - 1) / 365.25


def charger3(engine):
    """Charge le pool bâti mono-parcelle (features : surface, terrain, pièces, x/y, date) + de quoi
    estimer la surface AUTO (emprise, niveaux LiDAR, ratio communal) — comme `pige.estimer3` sert."""
    from collections import defaultdict as _dd
    out = {}
    with engine.connect() as c:
        rows = [dict(r) for r in c.execute(sa.text(_POOL3_SQL)).mappings().all()]
        for r in rows:
            r["ydec"] = _annee_dec3(r["d"])
        out["pool"] = rows
        idus = sorted({r["idu"] for r in rows})
        emprise, niveaux = {}, {}
        for i in range(0, len(idus), 5000):
            lot = idus[i:i + 5000]
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
            if r["ratio"] and (r["n"] or 0) >= RATIO_ASSISE_MIN:
                ratio[r["insee"]] = round(float(r["ratio"]), 3)
        by_com = _dd(list)
        for r in rows:
            by_com[r["insee"]].append(r)
        out.update(emprise=emprise, niveaux=niveaux, ratio=ratio, by_com=dict(by_com))
    return out


def _surface_auto3(idu, D):
    emp = D["emprise"].get(idu)
    rat = D["ratio"].get(idu[:5])
    if emp and rat:
        niv = D["niveaux"].get(idu)
        if niv:
            return emp * rat * (MULT_NIVEAUX_1 if niv <= 1 else MULT_NIVEAUX_SUP)
        return emp * rat
    return None


#: ESTIMER-3 — échantillon du banc des NIVEAUX plus LARGE que le banc estimer-2 (200) : la précision est
#: servie PAR COMMUNE, il faut assez de ventes par commune pour un Q3 stable (sinon repli île). ~1 500
#: couvre l'essentiel des ~2 300 ventes bâties 2025 ; les grosses communes dépassent le seuil, les
#: petites replient sur l'île. Seuil de cellule commune = ventes minimales pour SERVIR le commune-spécifique.
N_SAMPLE3 = 1500
MIN_CELL3 = 25


def calcule_niveaux(engine, n_sample: int = N_SAMPLE3, seed: int = SEED) -> dict:
    """Rejoue le banc « comparables semblables » no-leak aux trois niveaux d'information et renvoie
    {par_type_niveau, calibration3}. `calibration3` : lignes {type_bien, insee, niveau, n, ecart_median,
    ecart_q3, pct_20} + repli « * » par (type, niveau). Réutilise le point de calcul SERVI (`estimer3`)."""
    import math as _math
    from collections import defaultdict as _dd
    from . import estimer3 as E3
    D = charger3(engine)
    rng = random.Random(seed)
    # sujets 2025 par type
    maisons, apparts = [], []
    for r in D["pool"]:
        if r["d"].year != ANNEE_VENTES:
            continue
        reel = float(r["eurm2"])
        if not (GARDE_BATI[0] <= reel <= GARDE_BATI[1]):
            continue
        (maisons if r["type_local"] == "Maison" else apparts).append(r)
    rng.shuffle(maisons); rng.shuffle(apparts)
    maisons, apparts = maisons[:n_sample], apparts[:n_sample]

    NIV = ("sans_saisie", "surface", "surface_pieces")
    # On mesure DEUX méthodes sur le MÊME échantillon : « secteur » (médiane SIMPLE du secteur = le prix
    # d'ESTIMER-2) et « semblable » (médiane pondérée par la ressemblance = ESTIMER-3). Par cellule, on
    # SERT la meilleure des deux (mandat) → une caractéristique/méthode ne dégrade jamais le servi.
    err = _dd(lambda: _dd(lambda: {"semblable": [], "secteur": []}))     # [(type)][(insee,niveau)]
    err_t = _dd(lambda: _dd(lambda: {"semblable": [], "secteur": []}))   # [(type)][niveau] (repli île)

    def _un(k, type_bien):
        sx, sy = float(k["x"]), float(k["y"])
        dv = k["ydec"]
        surf_vraie = float(k["bati"])
        surf_auto = _surface_auto3(k["idu"], D)
        # comparables de la commune, no-leak (antérieurs, sujet exclu), avec distance au sujet
        comps = []
        for c in D["by_com"].get(k["insee"], ()):
            if c["mid"] == k["mid"] or c["ydec"] >= dv:
                continue
            comps.append({**c, "distance_m": _math.hypot(float(c["x"]) - sx, float(c["y"]) - sy),
                          "prix_m2_f": float(c["eurm2"]), "surface_m2": float(c["bati"]),
                          "terrain_m2": float(c["terr"]), "annee": c["d"].year})
        sel, _radius, _cf = E3._selection_rayon(comps, type_bien)
        for niveau in NIV:
            vraie_surf = (niveau != "sans_saisie")
            use_pieces = (niveau == "surface_pieces")
            # Un appartement n'a pas de surface MESURABLE sans saisie (emprise×ratio = formule maison) :
            # le niveau « sans saisie » n'existe pas pour lui (pas de total servi sans surface connue).
            if type_bien == "appartement" and not vraie_surf:
                continue
            # pondération surface SEULEMENT si la surface est CONNUE (comme le servi) ; la surface du
            # TOTAL reste l'estimée au niveau sans saisie.
            surf_poids = surf_vraie if vraie_surf else None
            surf_tot = surf_vraie if vraie_surf else surf_auto
            if not surf_tot or len(sel) < E3.SEUIL:
                continue
            subj = {"surf_poids": surf_poids, "terrain": float(k["terr"]) or None,
                    "pieces": (float(k["pieces"]) if (use_pieces and k["pieces"]) else None)}
            _q1, med, _q3 = E3.eur_m2_semblable([dict(c) for c in sel], subj, type_bien,
                                                use_pieces=use_pieces)
            # « secteur » (ESTIMER-2) = médiane SIMPLE non pondérée du MÊME échantillon sélectionné.
            med_sec = statistics.median([float(c["eurm2"]) for c in sel])
            val = float(k["val"])
            if med:
                e = abs(surf_tot * med / val - 1.0) * 100
                err[type_bien][(k["insee"], niveau)]["semblable"].append(e)
                err_t[type_bien][niveau]["semblable"].append(e)
            if med_sec:
                es = abs(surf_tot * med_sec / val - 1.0) * 100
                err[type_bien][(k["insee"], niveau)]["secteur"].append(es)
                err_t[type_bien][niveau]["secteur"].append(es)

    for k in maisons:
        _un(k, "maison")
    for k in apparts:
        _un(k, "appartement")

    def _meilleure(d: dict) -> dict:
        """Choisit la MEILLEURE méthode (écart médian le plus bas) entre secteur et semblable, et renvoie
        {methode, n, ecart_median, ecart_q3, pct_20, secteur, semblable} (les deux mesures pour le rapport)."""
        qs = {m: _quart(d[m]) for m in ("secteur", "semblable")}
        cand = {m: q for m, q in qs.items() if q["mediane"] is not None}
        if not cand:
            return {"methode": None, "n": 0, "ecart_median": None, "ecart_q3": None, "pct_20": None,
                    "secteur": qs["secteur"], "semblable": qs["semblable"]}
        best = min(cand, key=lambda m: cand[m]["mediane"])
        q = cand[best]
        return {"methode": best, "n": q["n"], "ecart_median": q["mediane"], "ecart_q3": q["q3"],
                "pct_20": q["pct_20"], "secteur": qs["secteur"], "semblable": qs["semblable"]}

    calibration3 = []
    par_type_niveau = {}
    for t in ("maison", "appartement"):
        par_type_niveau[t] = {niv: _meilleure(err_t[t][niv]) for niv in NIV}
        for niv in NIV:
            b = par_type_niveau[t][niv]
            if b["methode"] is not None:
                calibration3.append({"type_bien": t, "insee": "*", "niveau": niv, "n": b["n"],
                                     "methode": b["methode"], "ecart_median": b["ecart_median"],
                                     "ecart_q3": b["ecart_q3"], "pct_20": b["pct_20"]})
        for (insee, niv), d in err[t].items():
            b = _meilleure(d)
            if b["methode"] is not None and b["n"] >= MIN_CELL3:
                calibration3.append({"type_bien": t, "insee": insee, "niveau": niv, "n": b["n"],
                                     "methode": b["methode"], "ecart_median": b["ecart_median"],
                                     "ecart_q3": b["ecart_q3"], "pct_20": b["pct_20"]})
    return {"par_type_niveau": par_type_niveau, "calibration3": calibration3,
            "meta": {"n_sample": n_sample, "tires": {"maison": len(maisons), "appartement": len(apparts)}}}


_DDL3 = """
CREATE TABLE IF NOT EXISTS estimer3_precision (
  type_bien    varchar(16) NOT NULL,
  insee        varchar(8)  NOT NULL,          -- '*' = repli île du type
  niveau       varchar(20) NOT NULL,          -- sans_saisie | surface | surface_pieces
  methode      varchar(12) NOT NULL DEFAULT 'semblable',  -- secteur (ESTIMER-2) | semblable (ESTIMER-3) : la MEILLEURE
  n_ventes     integer     NOT NULL,
  ecart_median real        NOT NULL,          -- écart |estimé−réel| médian MESURÉ (%) de la méthode servie
  ecart_q3     real,                          -- borne de la fourchette servie (%)
  pct_20       real,
  maj          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (type_bien, insee, niveau)
)
"""


def persiste3(engine, rapport: dict) -> int:
    """Écrit `estimer3_precision` (remplace le contenu) depuis `calibration3`. Renvoie le nombre de lignes."""
    rows = list(rapport["calibration3"])
    with engine.begin() as c:
        # La table EST la photo du dernier banc : on la recrée (le schéma peut évoluer — ajout `methode`).
        c.execute(sa.text("DROP TABLE IF EXISTS estimer3_precision"))
        c.execute(sa.text(_DDL3))
        for r in rows:
            c.execute(sa.text(
                "INSERT INTO estimer3_precision "
                "(type_bien,insee,niveau,methode,n_ventes,ecart_median,ecart_q3,pct_20,maj) "
                "VALUES (:t,:i,:nv,:me,:n,:em,:q3,:p20, now())"),
                {"t": r["type_bien"], "i": r["insee"], "nv": r["niveau"], "me": r.get("methode", "semblable"),
                 "n": r["n"], "em": r["ecart_median"], "q3": r["ecart_q3"], "p20": r["pct_20"]})
    return len(rows)


def _print3(rapport):
    print("\n════════  BANC ESTIMER-3 — niveaux d'information (no-leak, ventes 2025)  ════════")
    print(f"  tirés : {rapport['meta']['tires']}")
    for t in ("maison", "appartement"):
        print(f"  {t.upper()}  (secteur=ESTIMER-2 · semblable=ESTIMER-3 · SERVI=la meilleure)")
        for niv, q in rapport["par_type_niveau"][t].items():
            sec, sem = q["secteur"], q["semblable"]
            print(f"    {niv:<16} secteur méd {str(sec['mediane'])+'%':>7} ±20% {str(sec['pct_20'])+'%':>6}"
                  f"  | semblable méd {str(sem['mediane'])+'%':>7} ±20% {str(sem['pct_20'])+'%':>6}"
                  f"  → SERVI {q['methode']} méd {str(q['ecart_median'])+'%':>7} Q3 {str(q['ecart_q3'])+'%':>7}")


if __name__ == "__main__":
    url = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")
    eng = sa.create_engine(url)
    import sys
    if "--niveaux" in sys.argv:
        rep3 = calcule_niveaux(eng)
        _print3(rep3)
    else:
        rep = calcule(eng)
        _print(rep)
        rep3 = calcule_niveaux(eng)
        _print3(rep3)
