#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-PRECISION-1 — banc d'estimation À RÉGLAGE/ANNONCE SÉPARÉS (2024 règle, 2025 annonce).

Règle de mesure du mandat, non négociable : TOUT réglage (poids, bandes passantes, seuils) se décide sur
les ventes 2024 ; le résultat s'ANNONCE sur les ventes 2025, jamais vues pendant le réglage. Aucune vente
ne s'estime elle-même (comparables strictement `date < date_vente` + exclusion de la mutation jugée).

Ce que le banc mesure, AVANT (médiane simple du secteur, l'estimateur servi aujourd'hui) vs APRÈS
(médiane PONDÉRÉE par la ressemblance) :

  · erreur du €/m²  — c'est là que mordent les poids (distance, écart de surface, écart de terrain pour
    les maisons, écart de distance au trait de côte = substitut Hauts/littoral, ancienneté + remise au
    présent par un indice local de dérive) ;
  · erreur du TOTAL en € — surface × €/m² — dans DEUX scénarios :
       (a) surface CONNUE (saisie) : surface = surface bâtie réelle de la vente jugée (un INTRANT
           observable fourni par l'utilisateur, jamais la cible) → l'erreur du total == l'erreur du €/m² ;
       (b) surface ESTIMÉE : dernière vente DVF ANTÉRIEURE (no-leak), sinon emprise × ratio communal.

L'ALTITUDE du mandat (« les Hauts et le littoral n'ont pas le même marché ») est servie par la DISTANCE
AU TRAIT DE CÔTE : sur une île volcanique l'altitude croît avec l'éloignement de la mer. Le MNT RGE ALTI
n'est PAS chargé sur cette base (2 dalles de 2 km² qui ne couvrent aucune des 24 communes) — c'est dit
franchement ; le trait de côte (`spatial_layers kind='trait_de_cote'`, 24 168 segments) couvre toute l'île.

Réglage (2024) : recherche de grille des bandes passantes, séparément maison / appartement, minimisant la
médiane |écart €/m²|. Les meilleurs paramètres sont FIGÉS puis rejoués tels quels sur 2025.

Lecture seule (une table TEMP de session pour le trait de côte, détruite à la fermeture). Rejeu :
  LABUSE_DATABASE_URL=postgresql+psycopg:///labuse <venv>/python docs/audit-2026-11/estimer-precision-1/banc.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import sqlalchemy as sa

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent.parent / "audit-2026-10" / "banc-rayon-1"))
import backtest_banc2 as b2  # noqa: E402  (loaders/typologie/garde-fous point-in-time déjà prouvés no-leak)

URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")
ENGINE = sa.create_engine(URL)
RATIO_ASSISE_MIN = 20

# bornes de dérive de l'indice local (geometric, par an) — garde-fou contre les communes à faible assise
DRIFT_MIN, DRIFT_MAX = -0.04, 0.12
DRIFT_ANS = (2019, 2024)   # l'indice est estimé sur ≤2024 et FIGÉ (no-leak pour l'annonce 2025)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Chargement (une seule connexion : table TEMP trait de côte + tout le reste)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def decimal_year(d: date) -> float:
    start = date(d.year, 1, 1).toordinal()
    end = date(d.year + 1, 1, 1).toordinal()
    return d.year + (d.toordinal() - start) / (end - start)


def charger():
    import time
    t0 = [time.time()]

    def tic(msg):
        print(f"  [{time.time() - t0[0]:6.1f}s] {msg}", flush=True)
        t0[0] = time.time()

    out = {}
    with ENGINE.connect() as c:
        c.execute(sa.text("CREATE TEMP TABLE coast_seg AS "
                          "SELECT geom_2975 g FROM spatial_layers WHERE kind='trait_de_cote'"))
        c.execute(sa.text("CREATE INDEX ON coast_seg USING gist(g)"))
        c.execute(sa.text("ANALYZE coast_seg"))
        tic("coast_seg prêt")

        # 1) COMPARABLES BÂTI — surensemble (tous locaux de vente), + terrain + distance côte (KNN).
        bati = c.execute(sa.text("""
            WITH d AS (
              SELECT d.commune, d.mutation_id AS mid,
                     d.valeur_fonciere / d.surface_reelle_bati AS prix,
                     d.surface_reelle_bati AS surface, COALESCE(d.surface_terrain,0) AS terrain,
                     lower(d.type_local) AS tl,
                     extract(year FROM d.date_mutation)::int AS annee, d.date_mutation::date AS dt,
                     ST_Transform(d.geom,2975) AS g
              FROM dvf_mutations d
              WHERE d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 0
                AND d.nature_mutation ILIKE '%vente%' AND d.geom IS NOT NULL)
            SELECT d.commune, d.mid, d.prix, d.surface, d.terrain, d.tl, d.annee, d.dt,
                   ST_X(d.g) AS x, ST_Y(d.g) AS y,
                   (SELECT ST_Distance(d.g, cs.g) FROM coast_seg cs ORDER BY d.g <-> cs.g LIMIT 1) AS coast
            FROM d
        """)).mappings().all()
        out["bati"] = [dict(r) for r in bati]
        tic(f"bati {len(out['bati'])} chargés (coast KNN)")

        # 2) COMPARABLES TERRAIN NU — repris verbatim de b2 (terrain inchangé).
        out["terr"] = [dict(r) for r in c.execute(sa.text(_TERR_SQL)).mappings().all()]
        tic(f"terrain {len(out['terr'])} chargés")

        # 3) UNIVERS 2024 & 2025 (mutations mono-parcelle, grain mutation).
        for an in (2024, 2025):
            out[f"univers_{an}"] = [dict(r) for r in c.execute(
                sa.text(_UNIVERS_SQL), {"an": an}).mappings().all()]
            tic(f"univers {an} : {len(out[f'univers_{an}'])}")

        # 4) SUJETS (nature, centroïde 2975, copro, distance côte) pour tous les idus jugés.
        idus = sorted({r["idu"] for an in (2024, 2025) for r in out[f"univers_{an}"]})
        parc = {}
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
            for r in c.execute(sa.text("""
                WITH pp AS (SELECT p.idu, p.commune, rb.taux_emprise_pct AS t, rb.sdp_residuelle_m2 AS s,
                                   ST_Transform(p.centroid,2975) AS g,
                                   COALESCE(s2.copro,false) AS copro
                            FROM parcels p
                            LEFT JOIN parcel_residuel rb ON rb.parcel_id = p.id
                            LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :run
                            WHERE p.idu = ANY(:lot))
                SELECT pp.idu, pp.commune, pp.t, pp.s, pp.copro,
                       ST_X(pp.g) AS x, ST_Y(pp.g) AS y,
                       (SELECT ST_Distance(pp.g, cs.g) FROM coast_seg cs ORDER BY pp.g <-> cs.g LIMIT 1) AS coast
                FROM pp
            """), {"lot": lot, "run": b2.RUN_V2}).mappings():
                parc[r["idu"]] = dict(r)
        out["parc"] = parc
        tic(f"sujets {len(parc)} (coast KNN)")

        # 5) EMPRISE BD TOPO + historique ventes par parcelle + ratio surface/emprise communal.
        emprise, hist, ratio = {}, defaultdict(list), {}
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
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
            "GROUP BY v.insee"), {}).mappings():
            if r["ratio"] and (r["n"] or 0) >= RATIO_ASSISE_MIN:
                ratio[r["insee"]] = round(float(r["ratio"]), 3)
        out["emprise"], out["hist"], out["ratio"] = emprise, dict(hist), ratio
        tic(f"emprise {len(emprise)} · hist {len(hist)} · ratio {len(ratio)}")

        # 6) INDICE LOCAL DE DÉRIVE (par commune) — médiane €/m² bâti par an, FIGÉE sur ≤2024.
        drift_rows = c.execute(sa.text("""
            SELECT d.commune, extract(year FROM d.date_mutation)::int AS annee,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY d.valeur_fonciere/d.surface_reelle_bati) AS med,
                   count(*) AS n
            FROM dvf_mutations d
            WHERE d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 0
              AND d.nature_mutation = 'Vente'
              AND d.valeur_fonciere/d.surface_reelle_bati BETWEEN 1000 AND 12000
              AND extract(year FROM d.date_mutation) BETWEEN :a AND :b
            GROUP BY d.commune, annee
        """), {"a": DRIFT_ANS[0], "b": DRIFT_ANS[1]}).mappings().all()
        out["drift"] = _calc_drift([dict(r) for r in drift_rows])
        tic("drift calculé")
    return out


def _calc_drift(rows) -> dict:
    """Dérive géométrique annuelle par commune, estimée sur 2019-2024 (figée). Repli île si assise mince."""
    par_com = defaultdict(dict)
    for r in rows:
        if (r["n"] or 0) >= 8 and r["med"]:
            par_com[r["commune"]][int(r["annee"])] = float(r["med"])
    # dérive île (médiane des ratios année→année+1, toutes communes)
    ratios_ile = []
    drift = {}
    for com, serie in par_com.items():
        ans = sorted(serie)
        if len(ans) >= 4 and serie.get(ans[0]) and serie.get(ans[-1]):
            d = (serie[ans[-1]] / serie[ans[0]]) ** (1.0 / (ans[-1] - ans[0])) - 1.0
            d = max(DRIFT_MIN, min(DRIFT_MAX, d))
            drift[com] = d
            ratios_ile.append(d)
    drift["__ile__"] = statistics.median(ratios_ile) if ratios_ile else 0.0
    return drift


_UNIVERS_SQL = """
  WITH base AS (
    SELECT id_mutation, id_parcelle, type_local,
           COALESCE(surface_reelle_bati,0) AS bati, COALESCE(surface_terrain,0) AS terr,
           nature_mutation, valeur_fonciere, date_mutation
    FROM dvf_mutations_parcelle
    WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')
      AND extract(year FROM date_mutation) = :an),   -- 0 mutation ne chevauche 2 années (vérifié)
  lig AS (SELECT DISTINCT id_mutation,id_parcelle,type_local,bati FROM base),
  terr_p AS (SELECT id_mutation,id_parcelle, max(terr) AS terr FROM base GROUP BY 1,2),
  mut AS (SELECT id_mutation, count(DISTINCT id_parcelle) AS np, sum(bati) AS bati_m2,
                 bool_or(type_local='Maison') AS am, bool_or(type_local='Appartement') AS aa
          FROM lig GROUP BY id_mutation),
  terrm AS (SELECT id_mutation, sum(terr) AS terrain_m2 FROM terr_p GROUP BY id_mutation),
  vtbm AS (SELECT id_mutation, bool_or(nature_mutation='Vente terrain à bâtir') AS vtb,
                  max(valeur_fonciere) AS valeur, min(date_mutation) AS dmin, min(id_parcelle) AS idu
           FROM base GROUP BY id_mutation)
  SELECT v.idu, v.id_mutation, v.valeur, v.dmin::date AS d, left(v.idu,5) AS insee,
         m.bati_m2, t.terrain_m2, m.am, m.aa, v.vtb
  FROM mut m JOIN terrm t USING(id_mutation) JOIN vtbm v USING(id_mutation)
  WHERE m.np = 1 AND extract(year FROM v.dmin) = :an AND v.valeur > 1000
"""

_TERR_SQL = """
  WITH mutations AS (
    SELECT id_mutation, max(valeur_fonciere) AS valeur,
           sum(COALESCE(surface_reelle_bati,0)) AS bati_m2, sum(terrain_par_parcelle) AS terrain_m2,
           bool_or(type_local='Maison') AS am, bool_or(type_local='Appartement') AS aa,
           bool_or(nature_mutation='Vente terrain à bâtir') AS vtb, min(date_mutation) AS d
    FROM (SELECT id_mutation, valeur_fonciere, surface_reelle_bati, type_local, nature_mutation, date_mutation,
                 max(COALESCE(surface_terrain,0)) OVER (PARTITION BY id_mutation,id_parcelle)
                   / greatest(count(*) OVER (PARTITION BY id_mutation,id_parcelle),1) AS terrain_par_parcelle
          FROM dvf_mutations_parcelle
          WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')) x
    GROUP BY id_mutation),
  terrains AS (SELECT id_mutation, valeur/terrain_m2 AS prix_m2, d FROM mutations
               WHERE valeur > 1000 AND am IS NOT TRUE AND aa IS NOT TRUE
                 AND bati_m2 = 0 AND terrain_m2 > 0 AND (vtb IS NOT TRUE OR bati_m2 = 0))
  SELECT DISTINCT substring(d2.id_parcelle FROM 1 FOR 10) AS secteur, t.id_mutation, t.prix_m2, t.d::date AS d
  FROM terrains t JOIN dvf_mutations_parcelle d2 ON d2.id_mutation = t.id_mutation
"""


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Index mémoire des comparables bâti (par commune) — arrays numpy, + coast + terrain
# ════════════════════════════════════════════════════════════════════════════════════════════════
def index_bati(bati):
    par = defaultdict(list)
    for r in bati:
        tl = r["tl"] or ""
        par[r["commune"]].append((
            float(r["prix"]), float(r["surface"]), float(r["terrain"] or 0),
            "appart" in tl, "maison" in tl, int(r["annee"]), r["dt"],
            float(r["x"]), float(r["y"]), float(r["coast"] or 0), r["mid"]))
    out = {}
    for com, lst in par.items():
        out[com] = {
            "prix": np.array([e[0] for e in lst]), "surface": np.array([e[1] for e in lst]),
            "terrain": np.array([e[2] for e in lst]),
            "appart": np.array([e[3] for e in lst], dtype=bool),
            "maison": np.array([e[4] for e in lst], dtype=bool),
            "annee": np.array([e[5] for e in lst]), "d": np.array([e[6] for e in lst]),
            "x": np.array([e[7] for e in lst]), "y": np.array([e[8] for e in lst]),
            "coast": np.array([e[9] for e in lst]), "mid": np.array([e[10] for e in lst], dtype=object),
        }
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Sélection des candidats (POINT-IN-TIME, no-leak) — MÊME logique que l'estimateur servi
# ════════════════════════════════════════════════════════════════════════════════════════════════
def selection(p, d_vente, mid, idx, force_type):
    """Renvoie (features des candidats retenus, type_bien, commune_fallback, radius). Identique à
    comparateur_bien : fenêtre 5 ans ancrée sur la dernière vente connue < d_vente, filtre z-MAD,
    type dominant (ou forcé), rayon adaptatif 500→1000→1500 puis repli commune. Exclut la mutation jugée."""
    com = p.get("commune")
    pool = idx.get(com)
    none = (None, force_type or "bati", False, None)
    if pool is None:
        return none
    avant = (pool["d"] < d_vente) & (pool["mid"] != mid)
    if not avant.any():
        return none
    anchor = pool["d"][avant].max()
    lo = b2._window_lo(anchor)
    base = avant & (pool["d"] >= lo)
    if not base.any():
        return none
    dx, dy = pool["x"] - p["x"], pool["y"] - p["y"]
    dist = np.sqrt(dx * dx + dy * dy)

    def fetch(r):
        m = base if r is None else (base & (dist <= r))
        if not m.any():
            return m
        ix = np.where(m)[0]
        if ix.size > b2.FETCH_LIMIT:
            order = np.argsort(dist[ix], kind="stable")[:b2.FETCH_LIMIT]
            ix = ix[order]
            m = np.zeros_like(base)
            m[ix] = True
        return m

    def tfrag(km, typ):
        if typ == "maison":
            return km & pool["maison"]
        if typ == "appartement":
            return km & pool["appart"]
        return km

    type_bien = force_type
    if type_bien in (None, "bati"):
        km = b2._kept_mask(pool, fetch(1000.0))
        nm = int((km & pool["maison"]).sum())
        na = int((km & pool["appart"]).sum())
        type_bien = ("maison" if nm >= na else "appartement") if (
            nm + na > 0 and max(nm, na) / (nm + na) >= b2.DOMINANT_FRAC) else None

    radius, cf, kept = None, False, np.zeros_like(base)
    for rayon in b2.CMP_RAYONS:
        kept = tfrag(b2._kept_mask(pool, fetch(rayon)), type_bien)
        if int(kept.sum()) >= b2.CMP_SEUIL:
            radius = int(rayon)
            break
    else:
        commune = tfrag(b2._kept_mask(pool, fetch(None)), type_bien)
        if int(commune.sum()) > int(kept.sum()):
            kept, cf = commune, True
        elif kept.any():
            radius = int(b2.CMP_RAYONS[-1])

    if not kept.any():
        return (None, type_bien or "bati", cf, radius)
    feats = {
        "prix": pool["prix"][kept], "surface": pool["surface"][kept], "terrain": pool["terrain"][kept],
        "dist": dist[kept], "coast": pool["coast"][kept],
        "yc": np.array([decimal_year(x) for x in pool["d"][kept]]),
    }
    return (feats, type_bien or "bati", cf, radius)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Médiane PONDÉRÉE par la ressemblance (le cœur APRÈS)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def weighted_median(values, weights):
    order = np.argsort(values, kind="stable")
    v, w = values[order], weights[order]
    cw = np.cumsum(w)
    if cw[-1] <= 0:
        return float(np.median(values))
    cut = cw[-1] / 2.0
    k = int(np.searchsorted(cw, cut))
    k = min(k, len(v) - 1)
    return float(v[k])


def estime(feats, subj, drift, params, force_type, type_bien):
    """€/m² estimé. `params` : bandes passantes + bascules. AVANT = params None (médiane simple)."""
    prix = feats["prix"].astype(float)
    if params is None:
        return float(np.median(prix)), int(prix.size)
    ys = subj["ys"]
    d = drift.get(subj["commune"], drift.get("__ile__", 0.0)) if params.get("drift") else 0.0
    prix_adj = prix * (1.0 + d) ** (ys - feats["yc"]) if d else prix
    w = np.ones_like(prix_adj)
    hd = params.get("h_dist")
    if hd:
        w = w * np.exp(-(feats["dist"] / hd) ** 2)
    hs = params.get("h_surf")
    if hs and subj.get("ssurf"):
        w = w * np.exp(-np.abs(feats["surface"] - subj["ssurf"]) / hs)
    ht = params.get("h_terr")
    if ht and type_bien == "maison" and subj.get("sterr"):
        dterr = np.abs(feats["terrain"] - subj["sterr"])
        tw = np.where(feats["terrain"] > 0, np.exp(-dterr / ht), 1.0)
        w = w * tw
    hc = params.get("h_coast")
    if hc and subj.get("coast") is not None:
        w = w * np.exp(-np.abs(feats["coast"] - subj["coast"]) / hc)
    hl = params.get("halflife")
    if hl:
        w = w * 0.5 ** (np.maximum(0.0, ys - feats["yc"]) / hl)
    w = np.where(np.isfinite(w) & (w > 0), w, 1e-12)
    return weighted_median(prix_adj, w), int(prix.size)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Préparation des cas (candidats mis en cache UNE fois ; le réglage ne refait que les poids)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def surface_estimee(idu, d_vente, mid, D):
    """Surface SERVE-TIME (no-leak) : dernière vente DVF ANTÉRIEURE, sinon emprise × ratio communal."""
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


def prepare(D, univers):
    """Pour chaque vente jugée bâtie : type, candidats (features), surfaces, réel. Terrain nu à part."""
    idx = D["_idx_bati"]
    cas = []
    for row in univers:
        typ = b2.typologie(row)
        if typ not in ("maison", "appartement"):
            continue
        reel, base = b2.prix_reel(row, typ)
        if reel is None or not (b2.GARDE_BATI[0] <= reel <= b2.GARDE_BATI[1]):
            continue
        idu, mid, d_vente = row["idu"], row["id_mutation"], row["d"]
        p = D["parc"].get(idu)
        if p is None:
            continue
        copro = bool(p.get("copro"))
        force = "appartement" if copro else typ   # type OBSERVABLE du bien vendu (E-022, non prédit)
        feats, type_bien, cf, radius = selection(p, d_vente, mid, idx, force)
        if feats is None:
            continue
        ssurf, ssrc = surface_estimee(idu, d_vente, mid, D)
        subj = {"commune": p.get("commune"), "ys": decimal_year(d_vente),
                "ssurf": ssurf, "sterr": float(row["terrain_m2"] or 0), "coast": p.get("coast")}
        cas.append({
            "idu": idu, "insee": row["insee"], "typ": typ, "copro": copro,
            "type_bien": type_bien, "cf": cf, "radius": radius, "n": int(feats["prix"].size),
            "feats": feats, "subj": subj, "reel_m2": reel, "reel_total": float(row["valeur"]),
            "vrai_bati": float(row["bati_m2"] or 0), "ssurf": ssurf, "ssrc": ssrc,
            "coast": p.get("coast"), "x": p.get("x"), "y": p.get("y"),
        })
    return cas


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Métriques
# ════════════════════════════════════════════════════════════════════════════════════════════════
def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def pctle(xs, c):
    xs = [x for x in xs if x is not None]
    return round(100 * sum(1 for x in xs if c(x)) / len(xs), 1) if xs else None


def err_m2(cas, params, D):
    out = []
    for k in cas:
        m, _ = estime(k["feats"], k["subj"], D["drift"], params, None, k["type_bien"])
        out.append(abs(m / k["reel_m2"] - 1.0) * 100 if m else None)
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Réglage sur 2024 (grille), FIGÉ, puis annonce sur 2025
# ════════════════════════════════════════════════════════════════════════════════════════════════
GRILLE = {
    "h_dist": [None, 500.0, 900.0, 1500.0],
    "h_surf": [None, 40.0, 80.0, 160.0],
    "h_coast": [None, 600.0, 1500.0, 4000.0],
    "halflife": [None, 2.0, 4.0],
    "drift": [False, True],
    "h_terr": [None, 500.0, 1500.0],   # maisons seulement
}


def regler(cas2024, D, typ):
    """Recherche par coordonnées (depuis la médiane simple) du jeu de poids qui minimise la médiane
    |écart €/m²| sur 2024, pour un type donné. Renvoie les meilleurs params."""
    sub = [k for k in cas2024 if k["typ"] == typ]
    base = {"h_dist": None, "h_surf": None, "h_coast": None, "halflife": None, "drift": False, "h_terr": None}
    best = dict(base)
    best_score = med(err_m2(sub, None, D))   # médiane simple = AVANT
    ordre = ["h_dist", "drift", "h_surf", "halflife", "h_coast"] + (["h_terr"] if typ == "maison" else [])
    improved = True
    passes = 0
    while improved and passes < 3:
        improved = False
        passes += 1
        for clef in ordre:
            for val in GRILLE[clef]:
                cand = dict(best)
                cand[clef] = val
                s = med(err_m2(sub, cand, D))
                if s is not None and (best_score is None or s < best_score - 1e-9):
                    best, best_score = cand, s
                    improved = True
    return best, best_score, len(sub)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Zones (Hauts / littoral) par distance au trait de côte
# ════════════════════════════════════════════════════════════════════════════════════════════════
LITTORAL_MAX = 1000.0   # ≤ 1 km du trait de côte = littoral
HAUTS_MIN = 4000.0      # ≥ 4 km = Hauts


def zone(coast):
    if coast is None:
        return None
    if coast <= LITTORAL_MAX:
        return "littoral"
    if coast >= HAUTS_MIN:
        return "hauts"
    return "medians"


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Rapport
# ════════════════════════════════════════════════════════════════════════════════════════════════
def bloc(errs):
    return {"n": len([e for e in errs if e is not None]), "median_abs_pct": med(errs),
            "pct_10": pctle(errs, lambda x: x <= 10), "pct_20": pctle(errs, lambda x: x <= 20)}


def experience_gbm(cas24, cas25, D, params):
    """EXPÉRIENCE (hors servi) — plafond d'un modèle gradient boosting entraîné jusqu'à 2024 et testé sur
    2025, pour les MAISONS que la médiane pondérée ne ramène pas sous 20 %. Features OBSERVABLES en base :
    surface, terrain, distance côte, x, y, commune (catégorielle), médiane comparable du secteur. Cible :
    €/m². On mesure GBM seul ET un mélange GBM×comparable. sklearn est déjà déclaré ([ml]/[ci]) ; ce code
    ne tourne QU'au banc (jamais servi — la prod ne porte pas scikit-learn)."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except Exception as exc:  # noqa: BLE001
        print(f"\n[GBM] scikit-learn indisponible ({exc}) — expérience sautée.")
        return {}
    communes = sorted({k["insee"] for k in cas24 + cas25})
    cidx = {c: i for i, c in enumerate(communes)}

    def feat(k):
        m_cmp, _ = estime(k["feats"], k["subj"], D["drift"], None, None, k["type_bien"])
        return [k["vrai_bati"], k["subj"].get("sterr") or 0.0, k["coast"] or 0.0,
                k["x"] or 0.0, k["y"] or 0.0, float(cidx.get(k["insee"], -1)),
                m_cmp if m_cmp else float("nan")], m_cmp

    out = {}
    for typ in ("maison", "appartement"):
        tr = [k for k in cas24 if k["typ"] == typ and k["vrai_bati"] > 0]
        te = [k for k in cas25 if k["typ"] == typ and k["vrai_bati"] > 0]
        Xtr, ytr = [], []
        for k in tr:
            f, _ = feat(k)
            Xtr.append(f)
            ytr.append(math.log(k["reel_m2"]))
        Xte, cmp_te = [], []
        for k in te:
            f, mc = feat(k)
            Xte.append(f)
            cmp_te.append(mc)
        Xtr, ytr, Xte = np.array(Xtr), np.array(ytr), np.array(Xte)
        model = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.05, max_depth=3, min_samples_leaf=40,
            l2_regularization=1.0, categorical_features=[5], random_state=0)
        model.fit(Xtr, ytr)
        pred = np.exp(model.predict(Xte))
        egbm, eblend = [], []
        for i, k in enumerate(te):
            egbm.append(abs(pred[i] / k["reel_m2"] - 1.0) * 100)
            mc = cmp_te[i]
            blend = (pred[i] + mc) / 2.0 if mc else pred[i]
            eblend.append(abs(blend / k["reel_m2"] - 1.0) * 100)
        out[typ] = {"gbm_m2": bloc(egbm), "blend_m2": bloc(eblend), "n_train": len(tr)}
        print(f"\n[GBM {typ}] n_train(2024)={len(tr)} n_test(2025)={len(te)}")
        print(f"   €/m² (= total surface connue)  GBM {out[typ]['gbm_m2']['median_abs_pct']}%  "
              f"(±20% {out[typ]['gbm_m2']['pct_20']}%)   |   "
              f"mélange GBM×comparable {out[typ]['blend_m2']['median_abs_pct']}%  "
              f"(±20% {out[typ]['blend_m2']['pct_20']}%)")
    return out


def disp_case(k):
    """Dispersion IQR relative des comparables retenus (non pondérés) — comme _fiabilite_bien servi."""
    prix = k["feats"]["prix"].astype(float)
    if prix.size < 4:
        return None
    qs = statistics.quantiles(list(prix), n=4, method="inclusive")
    m = float(np.median(prix))
    return (qs[2] - qs[0]) / m if m else None


def ablation(cas, params, D, typ):
    """Contribution de chaque terme : on part des params réglés et on RETIRE un terme à la fois (2025)."""
    sub = [k for k in cas if k["typ"] == typ]
    base = med(err_m2(sub, params[typ], D))
    out = {"tous": base}
    for terme in ("h_dist", "h_surf", "h_coast", "halflife", "drift", "h_terr"):
        p = dict(params[typ])
        p[terme] = (False if terme == "drift" else None)
        out[f"sans_{terme}"] = med(err_m2(sub, p, D))
    return out


def calibration_grille(cas, params, D):
    """Grille (n × dispersion) par type sous la méthode pondérée : médian |€/m²| + ±20 % + effectif.
    Sert à poser des bandes de fiabilité qui TIENNENT sur 2025 (« Élevée » = ce que le banc confirme)."""
    out = {}
    for typ in ("maison", "appartement"):
        grille = defaultdict(list)
        for k in cas:
            if k["typ"] != typ:
                continue
            m, _ = estime(k["feats"], k["subj"], D["drift"], params[typ], None, k["type_bien"])
            if not m:
                continue
            e = abs(m / k["reel_m2"] - 1.0) * 100
            d = disp_case(k)
            nb = ("n<8" if k["n"] < 8 else "8-14" if k["n"] < 15 else
                  "15-39" if k["n"] < 40 else "n>=40")
            db = ("?" if d is None else "d<=0.25" if d <= 0.25 else
                  "0.25-0.40" if d <= 0.40 else "0.40-0.75" if d <= 0.75 else "d>0.75")
            grille[f"{nb} · {db}"].append(e)
        out[typ] = {k: {"n": len(v), "median": med(v), "pct_20": pctle(v, lambda x: x <= 20),
                        "pct_10": pctle(v, lambda x: x <= 10)}
                    for k, v in sorted(grille.items())}
    return out


def principal():
    print("Chargement…")
    D = charger()
    D["_idx_bati"] = index_bati(D["bati"])
    D["_idx_terr"] = b2.index_terrain([
        {"secteur": r["secteur"], "id_mutation": r["id_mutation"], "prix_m2": r["prix_m2"], "d": r["d"]}
        for r in D["terr"]])
    print(f"  comparables bâti : {len(D['bati'])} · terrain : {len(D['terr'])} · "
          f"communes drift : {len([k for k in D['drift'] if k != '__ile__'])} (île {D['drift']['__ile__']:.3f})")
    print("  préparation des candidats 2024 / 2025 (point-in-time, no-leak)…")
    cas24 = prepare(D, D["univers_2024"])
    cas25 = prepare(D, D["univers_2025"])
    print(f"  cas bâtis estimables : 2024 {len(cas24)} · 2025 {len(cas25)}")

    # ── RÉGLAGE sur 2024 (figé) ──
    params = {}
    reglage = {}
    for typ in ("maison", "appartement"):
        best, score, n = regler(cas24, D, typ)
        params[typ] = best
        reglage[typ] = {"params": best, "median_2024_apres": score, "n_2024": n,
                        "median_2024_avant": med(err_m2([k for k in cas24 if k["typ"] == typ], None, D))}
        print(f"  réglage {typ:<12} 2024 : AVANT {reglage[typ]['median_2024_avant']}%  →  "
              f"APRÈS {score}%   params={best}")

    # ── Paramètres EXACTEMENT SERVIS (marche_service._POIDS_SEGMENT) : coast retirée (0,1pt, pas d'index
    #    au serve-time) ; maison = pondération douce cohérente. On REMPLACE les params réglés par ceux-ci
    #    pour que le banc annonce ce que le code sert vraiment. ──
    SERVIS = {
        "appartement": {"h_dist": 500.0, "h_surf": 160.0, "h_coast": None, "halflife": 2.0,
                        "drift": True, "h_terr": None},
        "maison": {"h_dist": 900.0, "h_surf": 120.0, "h_coast": None, "halflife": 4.0,
                   "drift": True, "h_terr": 1500.0},
    }
    for typ in ("maison", "appartement"):
        srv = med(err_m2([k for k in cas25 if k["typ"] == typ], SERVIS[typ], D))
        reglage[typ]["median_2025_servi"] = srv
        print(f"  SERVI {typ:<12} 2025 (config code, sans coast) : {srv}%")
    params = SERVIS

    # ── ANNONCE sur 2025 (paramètres figés) ──
    def errs_scn(cas, scn, after):
        """scn : 'm2' | 'total_connu' | 'total_estime'. after : appliquer les poids réglés."""
        out = []
        for k in cas:
            pr = params[k["typ"]] if after else None
            m, _ = estime(k["feats"], k["subj"], D["drift"], pr, None, k["type_bien"])
            if m is None:
                out.append(None)
                continue
            if scn == "m2":
                out.append(abs(m / k["reel_m2"] - 1.0) * 100)
            elif scn == "total_connu":
                tot = k["vrai_bati"] * m
                out.append(abs(tot / k["reel_total"] - 1.0) * 100 if k["vrai_bati"] > 0 else None)
            else:  # total_estime
                if k["ssurf"]:
                    tot = k["ssurf"] * m
                    out.append(abs(tot / k["reel_total"] - 1.0) * 100)
                else:
                    out.append(None)
        return out

    segs = {"Maison": lambda k: k["typ"] == "maison",
            "Appartement": lambda k: k["typ"] == "appartement",
            "Copropriété": lambda k: k["copro"]}
    rapport = {"n_2024": len(cas24), "n_2025": len(cas25), "reglage": reglage,
               "litto_max_m": LITTORAL_MAX, "hauts_min_m": HAUTS_MIN, "segments": {}}

    print("\n========  ANNONCE 2025 — €/m² et TOTAL (AVANT médiane simple → APRÈS pondérée)  ========")
    for nom, pred in segs.items():
        sub = [k for k in cas25 if pred(k)]
        e = {}
        for scn in ("m2", "total_connu", "total_estime"):
            e[scn] = {"avant": bloc(errs_scn(sub, scn, False)), "apres": bloc(errs_scn(sub, scn, True))}
        rapport["segments"][nom] = e
        a, b = e["m2"]["avant"], e["m2"]["apres"]
        tc = e["total_connu"]["apres"]
        te = e["total_estime"]["apres"]
        print(f"\n【 {nom} 】 n={b['n']}")
        print(f"   €/m²          AVANT {a['median_abs_pct']}%  → APRÈS {b['median_abs_pct']}%   "
              f"(±20% {a['pct_20']}%→{b['pct_20']}%)")
        print(f"   TOTAL surface CONNUE  (saisie)   APRÈS {tc['median_abs_pct']}%  (±20% {tc['pct_20']}%)")
        print(f"   TOTAL surface ESTIMÉE (auto)     AVANT {e['total_estime']['avant']['median_abs_pct']}% "
              f"→ APRÈS {te['median_abs_pct']}%  (±20% {te['pct_20']}%)")

    # ── TERRAIN NU (méthode inchangée : repère de secteur ; le mandat pondère le BÂTI) ──
    terr_err = []
    for row in D["univers_2025"]:
        if b2.typologie(row) != "terrain nu":
            continue
        reel, base = b2.prix_reel(row, "terrain nu")
        if reel is None or not (b2.GARDE_TERRAIN[0] <= reel <= b2.GARDE_TERRAIN[1]):
            continue
        e = b2.estime_terrain_nu(row["idu"], row["d"], row["id_mutation"], D["_idx_terr"])
        if e.get("median"):
            terr_err.append(abs(e["median"] / reel - 1.0) * 100)
    rapport["segments"]["Terrain nu"] = {"m2": {"avant": bloc(terr_err), "apres": bloc(terr_err)}}
    tb = bloc(terr_err)
    print(f"\n【 Terrain nu 】 n={tb['n']}  €/m² médian {tb['median_abs_pct']}%  (±20% {tb['pct_20']}%) — "
          f"méthode inchangée (repère de secteur)")

    # ── ZONES Hauts / littoral (sur le TOTAL surface connue, APRÈS) ──
    print("\n========  ZONE (distance au trait de côte) — TOTAL surface connue, APRÈS  ========")
    rapport["zones"] = {}
    for zn in ("littoral", "medians", "hauts"):
        for typ in ("maison", "appartement"):
            sub = [k for k in cas25 if k["typ"] == typ and zone(k["coast"]) == zn]
            if len(sub) < 15:
                continue
            e = bloc(errs_scn(sub, "total_connu", True))
            rapport["zones"][f"{zn}·{typ}"] = e
            print(f"   {zn:<9} {typ:<12} n={e['n']:>4}  médian {e['median_abs_pct']}%  ±20% {e['pct_20']}%")

    # ── Commune la mieux / la moins bien servie (maison, total connu, APRÈS, n≥30) ──
    print("\n========  COMMUNE la mieux / la moins bien servie (maison, total connu, APRÈS)  ========")
    par_com = defaultdict(list)
    for k in cas25:
        if k["typ"] == "maison":
            par_com[k["insee"]].append(k)
    com_scores = []
    for insee, sub in par_com.items():
        if len(sub) < 30:
            continue
        e = bloc(errs_scn(sub, "total_connu", True))
        com_scores.append((insee, e["median_abs_pct"], e["n"]))
    com_scores.sort(key=lambda t: (t[1] if t[1] is not None else 999))
    rapport["communes"] = {"mieux": com_scores[:3], "moins": com_scores[-3:]}
    for insee, m, n in com_scores[:3]:
        print(f"   mieux  {insee}  médian {m}%  n={n}")
    for insee, m, n in com_scores[-3:]:
        print(f"   moins  {insee}  médian {m}%  n={n}")

    # ── CSV par-vente (2025) ──
    with open(ICI / "PAR-VENTE-2025.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "insee", "typ", "copro", "type_bien", "zone", "n", "radius", "cf",
                    "reel_m2", "est_m2_avant", "est_m2_apres", "reel_total", "vrai_bati", "ssurf", "ssrc",
                    "err_total_connu_apres", "err_total_estime_apres"])
        for k in cas25:
            ma, _ = estime(k["feats"], k["subj"], D["drift"], None, None, k["type_bien"])
            mb, _ = estime(k["feats"], k["subj"], D["drift"], params[k["typ"]], None, k["type_bien"])
            etc = abs(k["vrai_bati"] * mb / k["reel_total"] - 1) * 100 if (mb and k["vrai_bati"] > 0) else ""
            ete = abs(k["ssurf"] * mb / k["reel_total"] - 1) * 100 if (mb and k["ssurf"]) else ""
            w.writerow([k["idu"], k["insee"], k["typ"], k["copro"], k["type_bien"], zone(k["coast"]),
                        k["n"], k["radius"], k["cf"], round(k["reel_m2"], 1),
                        round(ma, 1) if ma else "", round(mb, 1) if mb else "",
                        round(k["reel_total"]), round(k["vrai_bati"]), round(k["ssurf"]) if k["ssurf"] else "",
                        k["ssrc"] or "", round(etc, 1) if etc != "" else "", round(ete, 1) if ete != "" else ""])

    # ── ABLATION des termes (appartement & maison) ──
    print("\n========  ABLATION des termes (2025, médian |€/m²|)  ========")
    rapport["ablation"] = {}
    for typ in ("appartement", "maison"):
        ab = ablation(cas25, params, D, typ)
        rapport["ablation"][typ] = ab
        print(f"  {typ:<12} tous={ab['tous']}%  " + "  ".join(
            f"{k}={v}%" for k, v in ab.items() if k != "tous"))

    # ── CALIBRATION des bandes (grille n × dispersion, méthode pondérée, 2025) ──
    print("\n========  CALIBRATION bandes (grille n × dispersion, 2025, méthode pondérée)  ========")
    rapport["grille"] = calibration_grille(cas25, params, D)
    for typ in ("maison", "appartement"):
        print(f"  — {typ} —")
        for cle, m in rapport["grille"][typ].items():
            print(f"     {cle:<22} médian {str(m['median'])+'%':>7}  ±20% {str(m['pct_20'])+'%':>7}  n={m['n']}")

    # ── EXPÉRIENCE GBM (plafond, hors servi) ──
    print("\n========  EXPÉRIENCE — plafond gradient boosting (2024→2025, hors servi)  ========")
    rapport["gbm"] = experience_gbm(cas24, cas25, D, params)

    with open(ICI / "METRIQUES.json", "w") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print(f"\nécrit : {ICI/'METRIQUES.json'} et {ICI/'PAR-VENTE-2025.csv'}")


if __name__ == "__main__":
    principal()
