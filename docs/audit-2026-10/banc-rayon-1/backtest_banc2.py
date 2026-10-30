#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMATION-BANC-2 (Lot A du mandat BANC-RAYON-1) — on REJOUE le banc ESTIMATION-BANC-1 sur
l'estimateur ACTUEL (« Analyser une annonce »), qui a changé depuis le banc 1 :

  · il compare désormais les MAISONS aux MAISONS (comparateur_bien déduit le type DOMINANT du secteur,
    au lieu du « plans appartement-d'abord » de sector_price qui pricait les maisons sur des apparts) ;
  · il traite une COPROPRIÉTÉ comme un APPARTEMENT (branche copro → comparateur appartements) ;
  · il lit la NATURE de la parcelle (inchangé : parcel_residuel.taux_emprise_pct ; nue→terrain).

Même univers (toutes les ventes DVF 2025 des 24 communes), même règle SANS FUITE que le banc 1
(estimation reconstruite avec `date_mutation < date_vente` + exclusion de la mutation jugée). On calcule
les DEUX estimateurs dans le MÊME passage (banc1 = sector_price replica ; banc2 = comparateur_bien
replica) → comparaison strictement apples-to-apples (même univers, même coupe de date, même garde-fou).

SANS FUITE : on n'appelle jamais l'estimateur servi (il lit des agrégats de TOUTE la fenêtre = du
futur) ; on ré-implémente sa logique point-in-time. Garde-fou par vente : date du comparable le plus
récent < date de la vente. Lecture seule, aucune écriture en base.
"""
from __future__ import annotations

import csv
import json
import os
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import sqlalchemy as sa

ICI = Path(__file__).resolve().parent
URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")
ENGINE = sa.create_engine(URL)
RUN_V2 = os.environ.get("LABUSE_SCORE_RUN", "q_v20")   # run servi (p_score_v2_runs) pour le flag copro

# ── Constantes BANC 1 (sector_price / bilan), reprises VERBATIM du banc 1 ─────────────────────────
MIN_N = 8
RAYONS = (500.0, 1000.0, 1500.0)
PERIODE_ANS = 5
BORNE_BATI = (1000.0, 12000.0)
TRIM_FRAC = 0.05
# ── Constantes BANC 2 (comparateur_bien + filtre_ventes), reprises de marche_service / config ─────
CMP_RAYONS = (500.0, 1000.0, 1500.0)
CMP_FENETRE_ANS = 5                      # comparateur_bien(fenetre_ans=5)
CMP_SEUIL = 8                            # seuil_effectif_local("comparables_annonce", 8)
Z_MAD = 3.5                              # filtre_comparables.z_mad_max
SEUIL_TYPE_M2 = {"appartement": 200.0}   # filtre_comparables.seuil_type_m2
DOMINANT_FRAC = 0.55                     # comparateur_bien : type dominant si max(nm,na)/(nm+na) ≥ 0.55
FETCH_LIMIT = 600                        # comparateur_bien _fetch LIMIT 600 (ordonné par distance)
# garde-fous de VRAISEMBLANCE du prix RÉEL (artefacts DVF) — identiques au banc 1
GARDE_BATI = (100.0, 20000.0)
GARDE_TERRAIN = (1.0, 10000.0)


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  BANC 1 — réplicas fidèles de sector_price / bilan (copiés verbatim du banc 1)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def trim_extremes_5pct(prices: list[float]) -> list[float]:
    xs = sorted(prices)
    n = len(xs)
    k = int(n * (TRIM_FRAC / 2))
    if k == 0:
        return xs
    return xs[k:n - k]


def filtre_bati_v1(prix: list[float]) -> list[float]:
    gard = [p for p in prix if BORNE_BATI[0] <= p <= BORNE_BATI[1]]
    if len(gard) >= 4:
        gard = trim_extremes_5pct(gard)
    return gard


def quartiles(xs: list[float]) -> tuple[float, float, float]:
    xs = sorted(xs)
    if len(xs) >= 4:
        q1, _m, q3 = statistics.quantiles(xs, n=4)
        return q1, statistics.median(xs), q3
    m = statistics.median(xs)
    return m, m, m


def fiabilite_bati_v1(prix_kept, annee_max, ref_year, type_label, commune_fallback) -> str:
    n = len(prix_kept)
    if n < MIN_N:
        return "insuffisant"
    q1, _m, q3 = quartiles(prix_kept)
    niveau = "fiable"
    if (ref_year - annee_max) > 3:
        niveau = "fragile"
    disp = (q3 / q1) if q1 else 99.0
    if disp > 2.0:
        niveau = "fragile"
    if "mixte" in type_label:
        niveau = "fragile"
    if commune_fallback:
        niveau = "fragile"
    return niveau


def badge_v1(fiabilite: str, commune_fallback: bool) -> str:
    if commune_fallback:
        return "Limitée"
    if fiabilite == "fiable":
        return "Élevée"
    return "Moyenne"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  BANC 2 — réplica fidèle du filtre_ventes (bornes + seuil_type + z-MAD) de marche_service
# ══════════════════════════════════════════════════════════════════════════════════════════════
def filtre_ventes_v2(prix: np.ndarray, surf: np.ndarray, est_appart: np.ndarray) -> np.ndarray:
    """marche_service.filtre_ventes(bornes, z_mad, seuil_type_m2) — renvoie un MASQUE booléen des
    ventes GARDÉES. Ordre identique à la prod : (1) bornes €/m² ; (2) seuil_type (un « appartement »
    de surface > 200 m² = agrégat multi-lots, écarté) ; (3) z-score médiane/MAD > 3,5 sur les gardées."""
    keep = (prix >= BORNE_BATI[0]) & (prix <= BORNE_BATI[1])
    seuil_app = SEUIL_TYPE_M2.get("appartement")
    if seuil_app is not None:
        keep = keep & ~(est_appart & (surf > seuil_app))
    if keep.sum() >= 4:
        p = prix[keep]
        med = float(np.median(p))
        mad = float(np.median(np.abs(p - med))) or 1e-9
        z = np.abs(0.6745 * (prix - med) / mad)
        keep = keep & (z <= Z_MAD)
    return keep


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Chargement des données (une fois)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def charger():
    with ENGINE.connect() as c:
        # 1) UNIVERS DES VENTES JUGÉES — identique au banc 1 (mutations 2025 mono-parcelle, grain mutation)
        univers = c.execute(sa.text("""
            WITH base AS (
              SELECT id_mutation, id_parcelle, type_local,
                     COALESCE(surface_reelle_bati,0) AS bati, COALESCE(surface_terrain,0) AS terr,
                     nature_mutation, valeur_fonciere, date_mutation
              FROM dvf_mutations_parcelle
              WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')
            ),
            lig AS (SELECT DISTINCT id_mutation,id_parcelle,type_local,bati FROM base),
            terr_p AS (SELECT id_mutation,id_parcelle, max(terr) AS terr FROM base GROUP BY 1,2),
            mut AS (
              SELECT id_mutation,
                     count(DISTINCT id_parcelle) AS np,
                     sum(bati) AS bati_m2,
                     bool_or(type_local='Maison') AS am,
                     bool_or(type_local='Appartement') AS aa
              FROM lig GROUP BY id_mutation
            ),
            terrm AS (SELECT id_mutation, sum(terr) AS terrain_m2 FROM terr_p GROUP BY id_mutation),
            vtbm AS (SELECT id_mutation, bool_or(nature_mutation='Vente terrain à bâtir') AS vtb,
                            max(valeur_fonciere) AS valeur, min(date_mutation) AS dmin,
                            min(id_parcelle) AS idu
                     FROM base GROUP BY id_mutation)
            SELECT v.idu, v.id_mutation, v.valeur, v.dmin AS d, left(v.idu,5) AS insee,
                   m.bati_m2, t.terrain_m2, m.am, m.aa, v.vtb
            FROM mut m JOIN terrm t USING(id_mutation) JOIN vtbm v USING(id_mutation)
            WHERE m.np = 1 AND extract(year FROM v.dmin) = 2025 AND v.valeur > 1000
        """)).mappings().all()

        communes = {r["insee"]: r["nom"] for r in c.execute(sa.text(
            "SELECT DISTINCT left(idu,5) AS insee, commune AS nom FROM parcels WHERE commune IS NOT NULL"
        )).mappings()}

        # 2) NATURE + CENTROÏDE 2975 + COPRO (run servi) des parcelles jugées
        idus = sorted({r["idu"] for r in univers})
        parc = {}
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
            for r in c.execute(sa.text("""
                SELECT p.idu, rb.taux_emprise_pct AS t, rb.sdp_residuelle_m2 AS s,
                       ST_X(ST_Transform(p.centroid,2975)) AS x, ST_Y(ST_Transform(p.centroid,2975)) AS y,
                       p.commune,
                       COALESCE(s2.copro, false) AS copro
                FROM parcels p
                LEFT JOIN parcel_residuel rb ON rb.parcel_id = p.id
                LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :run
                WHERE p.idu = ANY(:lot)
            """), {"lot": lot, "run": RUN_V2}).mappings():
                parc[r["idu"]] = dict(r)

        # 3) ÉCHANTILLON BÂTI (dvf_mutations) — SURENSEMBLE strict de ce que lisent les DEUX estimateurs
        #    (valeur>0, surface≥20, vente, géométrie). On NE restreint PAS le type_local ici : banc 2
        #    (comparateur_bien) fait tourner son filtre z-MAD sur TOUS les locaux de vente avant de ne
        #    garder que maison/appart ; banc 1 (sector_price) ne lit QUE maison/appart. D'où deux index
        #    construits à partir de ces lignes (idx_bati_ma pour banc 1, idx_bati_all pour banc 2).
        bati_rows = c.execute(sa.text("""
            SELECT d.commune, d.mutation_id AS mid,
                   d.valeur_fonciere / d.surface_reelle_bati AS prix,
                   d.surface_reelle_bati AS surface,
                   lower(d.type_local) AS tl,
                   extract(year FROM d.date_mutation)::int AS annee, d.date_mutation::date AS d,
                   ST_X(ST_Transform(d.geom,2975)) AS x, ST_Y(ST_Transform(d.geom,2975)) AS y
            FROM dvf_mutations d
            WHERE d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 0
              AND d.nature_mutation ILIKE '%vente%'
              AND d.geom IS NOT NULL
        """)).mappings().all()

        # 4) ÉCHANTILLON TERRAIN NU — identique au banc 1 (terrain inchangé entre les deux estimateurs)
        terr_rows = c.execute(sa.text("""
            WITH mutations AS (
              SELECT id_mutation,
                     max(valeur_fonciere) AS valeur,
                     sum(COALESCE(surface_reelle_bati,0)) AS bati_m2,
                     sum(terrain_par_parcelle) AS terrain_m2,
                     bool_or(type_local='Maison') AS am, bool_or(type_local='Appartement') AS aa,
                     bool_or(nature_mutation='Vente terrain à bâtir') AS vtb,
                     min(date_mutation) AS d
              FROM (SELECT id_mutation, valeur_fonciere, surface_reelle_bati, type_local,
                           nature_mutation, date_mutation,
                           max(COALESCE(surface_terrain,0)) OVER (PARTITION BY id_mutation,id_parcelle)
                             / greatest(count(*) OVER (PARTITION BY id_mutation,id_parcelle),1)
                             AS terrain_par_parcelle
                    FROM dvf_mutations_parcelle
                    WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')) x
              GROUP BY id_mutation
            ),
            terrains AS (
              SELECT id_mutation, valeur/terrain_m2 AS prix_m2, d
              FROM mutations
              WHERE valeur > 1000 AND am IS NOT TRUE AND aa IS NOT TRUE
                AND bati_m2 = 0 AND terrain_m2 > 0 AND (vtb IS NOT TRUE OR bati_m2 = 0)
            )
            SELECT DISTINCT substring(d2.id_parcelle FROM 1 FOR 10) AS secteur,
                   t.id_mutation, t.prix_m2, t.d
            FROM terrains t JOIN dvf_mutations_parcelle d2 ON d2.id_mutation = t.id_mutation
        """)).mappings().all()

    return univers, communes, parc, bati_rows, terr_rows


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Indexation en mémoire (numpy)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def index_bati(bati_rows, ma_only: bool):
    """Par commune → arrays numpy. dvf_mutations = 1 ligne/mutation (0 doublon mesuré) → pas de dédup.
    `ma_only` : True → ne garder que maison/appartement (population de sector_price, banc 1) ; False →
    tous les locaux de vente (population du filtre z-MAD de comparateur_bien, banc 2)."""
    par_com = defaultdict(list)
    for r in bati_rows:
        est_a = "appart" in (r["tl"] or "")
        est_m = "maison" in (r["tl"] or "")
        if ma_only and not (est_a or est_m):
            continue
        par_com[r["commune"]].append((
            float(r["prix"]), float(r["surface"]), est_a, est_m,
            int(r["annee"]), r["d"], float(r["x"]), float(r["y"]), r["mid"]))
    out = {}
    for com, lst in par_com.items():
        out[com] = {
            "prix": np.array([e[0] for e in lst]),
            "surface": np.array([e[1] for e in lst]),
            "appart": np.array([e[2] for e in lst], dtype=bool),
            "maison": np.array([e[3] for e in lst], dtype=bool),
            "annee": np.array([e[4] for e in lst]),
            "d": np.array([e[5] for e in lst]),
            "x": np.array([e[6] for e in lst]),
            "y": np.array([e[7] for e in lst]),
            "mid": np.array([e[8] for e in lst], dtype=object),
        }
    return out


def index_terrain(terr_rows):
    par_sect = defaultdict(list)
    for r in terr_rows:
        par_sect[r["secteur"]].append((float(r["prix_m2"]), r["d"], r["id_mutation"]))
    out = {}
    for s, lst in par_sect.items():
        out[s] = {
            "prix": np.array([e[0] for e in lst]),
            "d": np.array([e[1] for e in lst]),
            "mid": np.array([e[2] for e in lst], dtype=object),
        }
    return out


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Nature & terrain (PARTAGÉS entre les deux bancs — inchangés)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def nature_parcelle(p: dict) -> str:
    if p is None or p.get("t") is None:
        return "non_mesure"
    if p["t"] < 5:
        return "nu"
    return "bati_encore" if (p.get("s") or 0) > 0 else "bati_max"


def estime_terrain_nu(idu: str, d_vente: date, mid: str, idx_terr) -> dict:
    sect = idu[:10]
    pool = idx_terr.get(sect)
    if pool is None:
        return {"median": None, "n": 0, "max_comp": None}
    m = (pool["d"] < d_vente) & (pool["mid"] != mid)
    prix = pool["prix"][m]
    n = int(prix.size)
    max_comp = pool["d"][m].max() if n else None
    if n < MIN_N:
        return {"median": None, "n": n, "max_comp": max_comp}
    band = prix[(prix >= 50) & (prix <= 20000)]
    if band.size == 0:
        return {"median": None, "n": n, "max_comp": max_comp}
    return {"median": float(np.median(band)), "n": n,
            "max_comp": max_comp, "fiabilite": "fiable", "commune_fallback": False}


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  BANC 1 — estime_bati (sector_price replica), copié verbatim du banc 1
# ══════════════════════════════════════════════════════════════════════════════════════════════
def estime_bati_v1(p: dict, d_vente: date, mid: str, idx_bati) -> dict:
    com = p.get("commune")
    pool = idx_bati.get(com)
    if pool is None:
        return {"median": None, "n": 0, "max_comp": None}
    base = (pool["d"] < d_vente) & (pool["mid"] != mid)
    if not base.any():
        return {"median": None, "n": 0, "max_comp": None}
    dx = pool["x"] - p["x"]
    dy = pool["y"] - p["y"]
    dist = np.sqrt(dx * dx + dy * dy)
    ref_year = d_vente.year
    an_recent = ref_year - PERIODE_ANS + 1
    plans = ([("appartement", True, r, False) for r in RAYONS]
             + [("mixte (appart+maison)", None, r, False) for r in RAYONS]
             + [("appartement", True, 1500.0, True),
                ("mixte (appart+maison)", None, 1500.0, True)])
    chosen = None
    for periode, an_min in (("récente", an_recent), ("élargie", 0)):
        for label, appart_only, r, commune_wide in plans:
            m = base & (pool["annee"] >= an_min)
            if appart_only:
                m = m & pool["appart"]
            if not commune_wide:
                m = m & (dist <= r)
            prix = pool["prix"][m]
            if prix.size == 0:
                continue
            kept = filtre_bati_v1(list(prix))
            if len(kept) >= MIN_N:
                annees = pool["annee"][m]
                chosen = (label, kept, commune_wide, int(annees.max()), pool["d"][m].max())
                break
        if chosen:
            break
    if chosen is None:
        m = base
        prix = pool["prix"][m]
        kept = filtre_bati_v1(list(prix))
        if not kept:
            return {"median": None, "n": 0, "max_comp": pool["d"][m].max()}
        annees = pool["annee"][m]
        chosen = ("mixte (appart+maison)", kept, True, int(annees.max()), pool["d"][m].max())
    label, kept, commune_fallback, annee_max, max_comp = chosen
    fia = fiabilite_bati_v1(kept, annee_max, ref_year, label, commune_fallback)
    return {"median": float(statistics.median(kept)), "n": len(kept),
            "type_prix": label, "fiabilite": fia, "commune_fallback": commune_fallback,
            "max_comp": max_comp}


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  BANC 2 — comparateur_bien replica (type dominant OU forcé), point-in-time
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _window_lo(anchor: date) -> date:
    """make_interval(years => 5) : fenêtre de 5 ans en arrière de l'ancre (la dernière vente connue)."""
    try:
        return anchor.replace(year=anchor.year - CMP_FENETRE_ANS)
    except ValueError:        # 29/02 → 28/02
        return anchor.replace(year=anchor.year - CMP_FENETRE_ANS, day=28)


def _kept_mask(pool, sel: np.ndarray) -> np.ndarray:
    """Applique le filtre_ventes v2 (bornes+seuil_type+z-MAD) à un sous-ensemble `sel` (masque)."""
    if not sel.any():
        return sel
    idx = np.where(sel)[0]
    keep_sub = filtre_ventes_v2(pool["prix"][idx], pool["surface"][idx], pool["appart"][idx])
    out = np.zeros_like(sel)
    out[idx[keep_sub]] = True
    return out


def estime_bien_v2(p: dict, d_vente: date, mid: str, idx_bati, force_type: str | None,
                   anchor_force: date | None = None) -> dict:
    """comparateur_bien(db, idu, type_bien=force_type) recalculé point-in-time. force_type :
    'appartement' pour une copropriété ; None → type DOMINANT du secteur déduit sur 1 000 m.
    `anchor_force` : ancre de fenêtre imposée (fidelite_v2 → max global DVF, pour reproduire la prod
    fenêtre pleine) ; None → ancre point-in-time (dernière vente connue avant la vente jugée)."""
    com = p.get("commune")
    pool = idx_bati.get(com)
    if pool is None:
        return {"median": None, "n": 0, "max_comp": None, "type_bien": force_type or "bati"}
    # fenêtre point-in-time : ancre = dernière vente connue AVANT la vente jugée (global commune≈global),
    # fenêtre 5 ans en arrière. Coupe de fuite + exclusion de la mutation jugée.
    avant = (pool["d"] < d_vente) & (pool["mid"] != mid)
    if not avant.any():
        return {"median": None, "n": 0, "max_comp": None, "type_bien": force_type or "bati"}
    anchor = anchor_force if anchor_force is not None else pool["d"][avant].max()
    lo = _window_lo(anchor)
    base = avant & (pool["d"] >= lo)
    if not base.any():
        return {"median": None, "n": 0, "max_comp": None, "type_bien": force_type or "bati"}
    dx = pool["x"] - p["x"]
    dy = pool["y"] - p["y"]
    dist = np.sqrt(dx * dx + dy * dy)

    def fetch_mask(rayon_m):
        """_fetch(rayon) : ventes dans le rayon (ou commune si None), ORDER BY distance LIMIT 600."""
        m = base if rayon_m is None else (base & (dist <= rayon_m))
        if not m.any():
            return m
        idx = np.where(m)[0]
        if idx.size > FETCH_LIMIT:
            order = np.argsort(dist[idx], kind="stable")[:FETCH_LIMIT]
            idx = idx[order]
            m = np.zeros_like(base)
            m[idx] = True
        return m

    def type_frag_mask(kept_mask, typ):
        if typ == "maison":
            return kept_mask & pool["maison"]
        if typ == "appartement":
            return kept_mask & pool["appart"]
        return kept_mask

    # 1) type dominant (sur 1 000 m) si non forcé
    type_bien = force_type
    if type_bien in (None, "bati"):
        km = _kept_mask(pool, fetch_mask(1000.0))
        nm = int((km & pool["maison"]).sum())
        na = int((km & pool["appart"]).sum())
        if nm + na > 0 and max(nm, na) / (nm + na) >= DOMINANT_FRAC:
            type_bien = "maison" if nm >= na else "appartement"
        else:
            type_bien = None

    # 2) rayon adaptatif 500→1000→1500 jusqu'au seuil, puis repli commune
    radius = None
    commune_fallback = False
    kept = np.zeros_like(base)
    for rayon in CMP_RAYONS:
        kept = type_frag_mask(_kept_mask(pool, fetch_mask(rayon)), type_bien)
        if int(kept.sum()) >= CMP_SEUIL:
            radius = int(rayon)
            break
    else:
        commune = type_frag_mask(_kept_mask(pool, fetch_mask(None)), type_bien)
        if int(commune.sum()) > int(kept.sum()):
            kept, commune_fallback = commune, True
        elif kept.any():
            radius = int(CMP_RAYONS[-1])

    prix = pool["prix"][kept]
    annees = pool["annee"][kept]
    n = int(prix.size)
    if n == 0:
        return {"median": None, "n": 0, "max_comp": pool["d"][base].max(),
                "type_bien": type_bien or "bati"}
    median = float(np.median(prix))
    max_comp = pool["d"][kept].max()
    return {"median": median, "n": n, "type_bien": type_bien or "bati",
            "commune_fallback": commune_fallback, "radius_m": radius,
            "annee_max": int(annees.max()) if annees.size else None, "max_comp": max_comp}


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Précision servie par segment (banc 2) + badge — réplique pige/api._ECART_SEGMENT / _fiabilite_*
#  Les valeurs sont RECALIBRÉES en fin de run ; ici on code la RÈGLE (seuils <15 / <25).
# ══════════════════════════════════════════════════════════════════════════════════════════════
def badge_v2(ecart_pct: float, commune_fallback: bool) -> str:
    if commune_fallback:
        return "Limitée"
    if ecart_pct < 15:
        return "Élevée"
    if ecart_pct < 25:
        return "Moyenne"
    return "Limitée"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Backtest
# ══════════════════════════════════════════════════════════════════════════════════════════════
def typologie(row) -> str:
    if row["am"]:
        return "maison"
    if row["aa"]:
        return "appartement"
    if (row["bati_m2"] or 0) == 0 and (row["terrain_m2"] or 0) > 0:
        return "terrain nu"
    return "autre"


def prix_reel(row, typ):
    if typ in ("maison", "appartement"):
        b = row["bati_m2"] or 0
        return (float(row["valeur"]) / b) if b > 0 else None, "bati"
    if typ == "terrain nu":
        t = row["terrain_m2"] or 0
        return (float(row["valeur"]) / t) if t > 0 else None, "terrain"
    return None, None


def run():
    print("Chargement…")
    univers, communes, parc, bati_rows, terr_rows = charger()
    print(f"  univers brut : {len(univers)} mutations 2025 mono-parcelle")
    idx_bati_ma = index_bati(bati_rows, ma_only=True)     # banc 1 (sector_price) : maison/appart seuls
    idx_bati_all = index_bati(bati_rows, ma_only=False)   # banc 2 (comparateur_bien) : tous locaux vente
    idx_terr = index_terrain(terr_rows)
    n_copro = sum(1 for p in parc.values() if p.get("copro"))
    print(f"  bâti maison/appart (banc1) : {sum(len(v['prix']) for v in idx_bati_ma.values())} / "
          f"tous locaux (banc2) : {sum(len(v['prix']) for v in idx_bati_all.values())}")
    print(f"  terrain : {sum(len(v['prix']) for v in idx_terr.values())} comparables / {len(idx_terr)} secteurs")
    print(f"  parcelles jugées en copropriété (run {RUN_V2}) : {n_copro}")

    lignes = []
    for row in univers:
        typ = typologie(row)
        if typ == "autre":
            continue
        reel, base_reel = prix_reel(row, typ)
        if reel is None:
            continue
        g = GARDE_BATI if base_reel == "bati" else GARDE_TERRAIN
        if not (g[0] <= reel <= g[1]):
            continue

        idu = row["idu"]
        p = parc.get(idu)
        nat = nature_parcelle(p)
        copro = bool(p.get("copro")) if p else False
        d_vente = row["d"]
        mid = row["id_mutation"]

        # ── BANC 1 (sector_price, pas de branche copro) ──────────────────────────────────────────
        if nat == "nu":
            e1 = estime_terrain_nu(idu, d_vente, mid, idx_terr)
            base1 = "terrain"
        elif p is None:
            e1 = {"median": None, "n": 0, "max_comp": None}
            base1 = "bati"
        else:
            e1 = estime_bati_v1(p, d_vente, mid, idx_bati_ma)
            base1 = "bati"

        # ── BANC 2 (comparateur_bien dominant-type + branche copro) ──────────────────────────────
        if nat == "nu":
            e2 = estime_terrain_nu(idu, d_vente, mid, idx_terr)
            base2 = "terrain"
            type2 = "terrain"
        elif p is None:
            e2 = {"median": None, "n": 0, "max_comp": None, "type_bien": "bati"}
            base2 = "bati"
            type2 = "bati"
        elif copro:
            e2 = estime_bien_v2(p, d_vente, mid, idx_bati_all, force_type="appartement")
            base2 = "bati"
            type2 = "appartement"
        else:
            e2 = estime_bien_v2(p, d_vente, mid, idx_bati_all, force_type=None)
            base2 = "bati"
            type2 = e2.get("type_bien")

        def err(est, base_est):
            # fuite_ok : calculé depuis le comparable le plus récent, QUE l'estimation aboutisse ou non
            # (une estimation sans médiane a quand même utilisé — ou non — des comparables datés).
            fuite_ok = True if est.get("max_comp") is None else (est["max_comp"] < d_vente)
            m = est.get("median")
            if m is None:
                return None, None, fuite_ok, None
            e = m / reel - 1.0
            return e, (base_est != base_reel), fuite_ok, m

        err1, mm1, fuite1, med1 = err(e1, base1)
        err2, mm2, fuite2, med2 = err(e2, base2)

        lignes.append({
            "idu": idu, "insee": row["insee"],
            "commune": communes.get(row["insee"], p.get("commune") if p else None),
            "id_mutation": mid, "date": d_vente.isoformat(), "type_vente": typ,
            "nature_parcelle": nat, "copro": copro,
            "prix_reel_m2": round(reel, 1), "base_reelle": base_reel,
            # banc 1
            "b1_base": base1, "b1_median": (round(med1, 1) if med1 is not None else None),
            "b1_estimable": err1 is not None, "b1_mismatch": mm1,
            "b1_err_pct": (round(100 * err1, 2) if err1 is not None else None),
            "b1_abs_pct": (round(100 * abs(err1), 2) if err1 is not None else None),
            "b1_10": (abs(err1) <= 0.10) if err1 is not None else None,
            "b1_20": (abs(err1) <= 0.20) if err1 is not None else None,
            "b1_fuite_ok": fuite1,
            # banc 2
            "b2_base": base2, "b2_type": type2, "b2_median": (round(med2, 1) if med2 is not None else None),
            "b2_estimable": err2 is not None, "b2_mismatch": mm2,
            "b2_err_pct": (round(100 * err2, 2) if err2 is not None else None),
            "b2_abs_pct": (round(100 * abs(err2), 2) if err2 is not None else None),
            "b2_10": (abs(err2) <= 0.10) if err2 is not None else None,
            "b2_20": (abs(err2) <= 0.20) if err2 is not None else None,
            "b2_commune_fallback": bool(e2.get("commune_fallback")),
            "b2_fuite_ok": fuite2,
        })

    return lignes


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Agrégation & métriques
# ══════════════════════════════════════════════════════════════════════════════════════════════
def metriques(sous, pfx):
    n = len(sous)
    est = [l for l in sous if l[f"{pfx}_estimable"]]
    ne = n - len(est)
    errs = [l[f"{pfx}_abs_pct"] for l in est]
    signed = [l[f"{pfx}_err_pct"] for l in est]
    return {
        "n_ventes": n, "n_estimable": len(est),
        "pct_non_estimable": round(100 * ne / n, 1) if n else None,
        "ecart_median_abs_pct": round(statistics.median(errs), 1) if errs else None,
        "ecart_median_signe_pct": round(statistics.median(signed), 1) if signed else None,
        "biais_moyen_signe_pct": round(statistics.mean(signed), 1) if signed else None,
        "pct_dans_10": round(100 * sum(1 for l in est if l[f"{pfx}_10"]) / len(est), 1) if est else None,
        "pct_dans_20": round(100 * sum(1 for l in est if l[f"{pfx}_20"]) / len(est), 1) if est else None,
    }


def segment(lignes, nom, predicat):
    sous = [l for l in lignes if predicat(l)]
    return {"segment": nom, "banc1": metriques(sous, "b1"), "banc2": metriques(sous, "b2")}


def principal():
    lignes = run()
    cols = list(lignes[0].keys())
    with open(ICI / "PAR-VENTE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(lignes)

    segs = [
        segment(lignes, "Toutes ventes", lambda l: True),
        segment(lignes, "Appartement", lambda l: l["type_vente"] == "appartement"),
        segment(lignes, "Maison", lambda l: l["type_vente"] == "maison"),
        segment(lignes, "Terrain nu", lambda l: l["type_vente"] == "terrain nu"),
        segment(lignes, "Copropriété (parcelle)", lambda l: l["copro"] and l["base_reelle"] == "bati"),
    ]
    # segments auxiliaires : base alignée (hors mismatch de nature), type v2 servi
    aux = {
        "maison_base_alignee_b2": metriques(
            [l for l in lignes if l["type_vente"] == "maison" and not l["b2_mismatch"]], "b2"),
        "maison_b2_type_maison": metriques(
            [l for l in lignes if l["type_vente"] == "maison" and l["b2_type"] == "maison"], "b2"),
        "maison_b2_type_appartement": metriques(
            [l for l in lignes if l["type_vente"] == "maison" and l["b2_type"] == "appartement"], "b2"),
        "maison_b2_type_bati_combine": metriques(
            [l for l in lignes if l["type_vente"] == "maison" and l["b2_type"] == "bati"], "b2"),
    }
    # badge banc 2 : distribution par type v2 servi
    par_badge_b2 = {}
    for b in ("Élevée", "Moyenne", "Limitée"):
        # badge dépend de la précision recalibrée ; on le recalcule une fois les écarts connus (cf. rapport).
        pass

    res = {
        "run_v2_copro": RUN_V2,
        "segments": segs,
        "aux": aux,
        "fuite": {
            "banc1_ok": all(l["b1_fuite_ok"] for l in lignes),
            "banc2_ok": all(l["b2_fuite_ok"] for l in lignes),
            "banc1_violations": sum(1 for l in lignes if not l["b1_fuite_ok"]),
            "banc2_violations": sum(1 for l in lignes if not l["b2_fuite_ok"]),
        },
        "n_total": len(lignes),
    }
    with open(ICI / "METRIQUES.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    def ligne(nom, m):
        return (f"  {nom:<22} n={m['n_ventes']:>5} non-est={str(m['pct_non_estimable'])+'%':>7} "
                f"médian|écart|={str(m['ecart_median_abs_pct'])+'%':>8} "
                f"±10%={str(m['pct_dans_10'])+'%':>7} ±20%={str(m['pct_dans_20'])+'%':>7} "
                f"biais méd={str(m['ecart_median_signe_pct'])+'%':>8}")

    print("\n================  COMPARAISON BANC 1 vs BANC 2  ================")
    for s in segs:
        print(f"\n【 {s['segment']} 】")
        print(ligne("banc 1 (sector_price)", s["banc1"]))
        print(ligne("banc 2 (comparat.bien)", s["banc2"]))
    print("\n================  MAISON banc 2 — détail du type servi  ================")
    for k, m in aux.items():
        print(ligne(k, m))
    print("\n================  CONTRÔLE DE FUITE  ================")
    print(json.dumps(res["fuite"], ensure_ascii=False, indent=2))
    print(f"\nécrit : {ICI/'PAR-VENTE.csv'}  et  {ICI/'METRIQUES.json'}")


if __name__ == "__main__":
    principal()
