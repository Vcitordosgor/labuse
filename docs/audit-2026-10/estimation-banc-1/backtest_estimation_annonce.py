#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMATION-BANC-1 — banc de précision de l'estimateur « Analyser une annonce » (entrée adresse).

Mesure, à la façon de Repère Immo, l'écart entre le prix au m² ESTIMÉ par l'outil et le prix au m²
RÉELLEMENT PAYÉ, sur TOUTES les ventes DVF 2025 des 24 communes de La Réunion.

────────────────────────────────────────────────────────────────────────────────────────────────
AUCUNE FUITE DE DONNÉES — le point le plus important.
────────────────────────────────────────────────────────────────────────────────────────────────
Pour chaque vente jugée, l'estimation est RECONSTRUITE avec, et seulement avec, les ventes DONT LA
DATE EST STRICTEMENT ANTÉRIEURE à la date de la vente jugée, ET en excluant explicitement la mutation
jugée (par son `id_mutation`). Concrètement :

  • On ne lit JAMAIS la table pré-agrégée servie `dvf_secteur_medianes` : elle est calculée sur toute
    la fenêtre 2021-2025 (donc inclut des ventes POSTÉRIEURES à la vente jugée). L'estimateur en
    production la lit pour le « terrain nu » ; ici on RECALCULE la médiane terrain à partir des
    mutations brutes avec le filtre de date, à l'identique de `ingestion/dvf_marche.compute_medianes_secteur`.
  • Pour le bâti, on reproduit `faisabilite/bilan.sector_price` (le `prix_ancien` de la fiche, cf.
    `marche_service.marche_dvf(profil=DVF_BANQUIER_ADAPTATIF)`), mais sur un échantillon filtré
    `date_mutation < date_vente` et privé de la mutation jugée.
  • Garde-fou automatique : pour chaque estimation on vérifie que la date de comparable la plus
    récente utilisée est < date de la vente jugée (colonne `fuite_ok`, agrégée en fin de run). Un
    seul False ferait échouer le banc.

On reproduit la LOGIQUE EXACTE de l'estimateur de production (choix de la nature depuis la parcelle,
plans appartement-d'abord puis mixte appart+maison, rayons 500/1000/1500 m puis commune, trim
[1000;12000] €/m² + 5 % extrêmes, seuil n≥8, badge de fiabilité). On ne l'APPELLE pas (il lirait les
agrégats servis, donc du futur) : on le RÉ-IMPLÉMENTE à l'identique avec la coupe temporelle.

Lecture seule, aucune écriture en base. Sorties : PAR-VENTE.csv, METRIQUES.json, tableaux imprimés.
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

# ── Constantes reprises VERBATIM de la production ────────────────────────────────────────────────
MIN_N = 8                       # bilan.MIN_N_SECTEUR / mon_secteur.SEUIL_N (config dvf_profils.yaml)
RAYONS = (500.0, 1000.0, 1500.0)   # bilan.RAYONS_SECTEUR_M
PERIODE_ANS = 5                 # bilan.PERIODE_SECTEUR_ANS
BORNE_BATI = (1000.0, 12000.0)  # filtre_ventes bornes €/m² bâti
TRIM_FRAC = 0.05                # bilan.TRIM_EXTREMES_FRAC (2,5 % par queue)
# garde-fous de VRAISEMBLANCE du prix RÉEL (vérité terrain) — mêmes bornes que verite_terrain_predictions
GARDE_BATI = (100.0, 20000.0)
GARDE_TERRAIN = (1.0, 10000.0)


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Réplicas fidèles des helpers de production
# ══════════════════════════════════════════════════════════════════════════════════════════════
def trim_extremes_5pct(prices: list[float]) -> list[float]:
    """bilan.trim_extremes_5pct : retire 2,5 % de chaque queue ; sous ~20 ventes (k=0) ne retire rien."""
    xs = sorted(prices)
    n = len(xs)
    k = int(n * (TRIM_FRAC / 2))
    if k == 0:
        return xs
    return xs[k:n - k]


def filtre_bati(prix: list[float]) -> list[float]:
    """marche_service.filtre_ventes(bornes=BORNE_BATI, trim_pct=0.05) pour le bâti : bornes puis trim."""
    gard = [p for p in prix if BORNE_BATI[0] <= p <= BORNE_BATI[1]]
    if len(gard) >= 4:
        gard = trim_extremes_5pct(gard)
    return gard


def quartiles(xs: list[float]) -> tuple[float, float, float]:
    """bilan._quartiles."""
    xs = sorted(xs)
    if len(xs) >= 4:
        q1, _m, q3 = statistics.quantiles(xs, n=4)
        return q1, statistics.median(xs), q3
    m = statistics.median(xs)
    return m, m, m


def fiabilite_bati(prix_kept: list[float], annee_max: int, ref_year: int,
                   type_label: str, commune_fallback: bool) -> str:
    """bilan._fiabilite : fiable | fragile | insuffisant (point-in-time : ref_year = année de la vente)."""
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


def badge(fiabilite: str, commune_fallback: bool) -> str:
    """AnalyserAnnonce.tsx _badge : commune_fallback→Limitée ; fiable→Élevée ; sinon→Moyenne."""
    if commune_fallback:
        return "Limitée"
    if fiabilite == "fiable":
        return "Élevée"
    return "Moyenne"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Chargement des données (une fois)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def charger():
    with ENGINE.connect() as c:
        # 1) UNIVERS DES VENTES JUGÉES — mutations 2025, UNE SEULE parcelle (valeur attribuable),
        #    agrégées au grain mutation (répétitions nature_culture ôtées), avec prix RÉEL au m²
        #    sur la base PROPRE à la vente (bâti pour maison/appart, terrain pour terrain nu).
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

        # commune (nom) par insee, pour relier à dvf_mutations.commune / parcels.commune
        communes = {r["insee"]: r["nom"] for r in c.execute(sa.text(
            "SELECT DISTINCT left(idu,5) AS insee, commune AS nom FROM parcels WHERE commune IS NOT NULL"
        )).mappings()}

        # 2) NATURE + CENTROÏDE 2975 des parcelles jugées (pour _nature_parcelle + distances sector_price)
        idus = sorted({r["idu"] for r in univers})
        parc = {}
        CH = 5000
        for i in range(0, len(idus), CH):
            lot = idus[i:i + CH]
            for r in c.execute(sa.text("""
                SELECT p.idu, rb.taux_emprise_pct AS t, rb.sdp_residuelle_m2 AS s,
                       ST_X(ST_Transform(p.centroid,2975)) AS x, ST_Y(ST_Transform(p.centroid,2975)) AS y,
                       p.commune
                FROM parcels p LEFT JOIN parcel_residuel rb ON rb.parcel_id = p.id
                WHERE p.idu = ANY(:lot)
            """), {"lot": lot}).mappings():
                parc[r["idu"]] = dict(r)

        # 3) ÉCHANTILLON BÂTI (dvf_mutations) — réplique EXACTE de bilan._ventes_bati_dedup,
        #    avec date + coordonnées 2975 pour reproduire ST_Distance et la coupe temporelle.
        bati_rows = c.execute(sa.text("""
            SELECT d.commune, d.mutation_id AS mid,
                   d.valeur_fonciere / d.surface_reelle_bati AS prix,
                   CASE WHEN d.type_local ILIKE '%APPARTEMENT%' THEN 1 ELSE 0 END AS appart,
                   extract(year FROM d.date_mutation)::int AS annee, d.date_mutation::date AS d,
                   ST_X(ST_Transform(d.geom,2975)) AS x, ST_Y(ST_Transform(d.geom,2975)) AS y
            FROM dvf_mutations d
            WHERE d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 20000
              AND d.nature_mutation ILIKE '%vente%'
              AND d.type_local ILIKE ANY(ARRAY['%APPARTEMENT%','%MAISON%'])
              AND d.geom IS NOT NULL
        """)).mappings().all()

        # 4) ÉCHANTILLON TERRAIN NU au grain mutation (réplique compute_medianes_secteur, type 'terrain'),
        #    éclaté par SECTEUR cadastral (left(idu,10)), avec date + id_mutation pour la coupe.
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
              -- classification TERRAIN à l'identique de compute_medianes_secteur (CASE NULL-safe :
              -- une mutation de terrain nu a type_local NULL partout → am/aa valent NULL, d'où
              -- `IS NOT TRUE` et non `NOT am`, qui écarterait tous ces actes). On NE filtre PAS la
              -- bande €/m² ici : production compte n_ventes sur TOUT le terrain du secteur et ne
              -- borne la bande [50;20000] que dans le calcul de la médiane (repris côté Python).
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
#  Indexation en mémoire (numpy) pour un backtest rapide
# ══════════════════════════════════════════════════════════════════════════════════════════════
def index_bati(bati_rows):
    """Par commune (nom) → arrays numpy, DÉDOUBLONNÉS par mutation_id (bilan._ventes_bati_dedup)."""
    par_com = defaultdict(list)
    seen = defaultdict(set)
    for r in bati_rows:
        com = r["commune"]
        if r["mid"] in seen[com]:
            continue
        seen[com].add(r["mid"])
        par_com[com].append((float(r["prix"]), int(r["appart"]), int(r["annee"]),
                             r["d"], float(r["x"]), float(r["y"]), r["mid"]))
    out = {}
    for com, lst in par_com.items():
        out[com] = {
            "prix": np.array([e[0] for e in lst]),
            "appart": np.array([e[1] for e in lst], dtype=bool),
            "annee": np.array([e[2] for e in lst]),
            "d": np.array([e[3] for e in lst]),           # datetime.date
            "x": np.array([e[4] for e in lst]),
            "y": np.array([e[5] for e in lst]),
            "mid": np.array([e[6] for e in lst], dtype=object),
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
#  L'ESTIMATEUR reconstruit, SANS fuite (réplique estimation_annonce)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def nature_parcelle(p: dict) -> str:
    """pige/api._nature_parcelle : NULL→non_mesure ; <5 %→nu ; sinon bâti."""
    if p is None or p.get("t") is None:
        return "non_mesure"
    if p["t"] < 5:
        return "nu"
    return "bati_encore" if (p.get("s") or 0) > 0 else "bati_max"


def estime_terrain_nu(idu: str, d_vente: date, mid: str, idx_terr) -> dict:
    """mon_secteur._terrain_section recalculé point-in-time (au lieu de lire dvf_secteur_medianes)."""
    sect = idu[:10]
    pool = idx_terr.get(sect)
    if pool is None:
        return {"median": None, "n": 0, "max_comp": None}
    m = (pool["d"] < d_vente) & (pool["mid"] != mid)
    prix = pool["prix"][m]
    n = int(prix.size)                      # n_ventes = compte NON borné (seuil n≥8, comme en prod)
    max_comp = pool["d"][m].max() if n else None
    if n < MIN_N:
        return {"median": None, "n": n, "max_comp": max_comp}
    band = prix[(prix >= 50) & (prix <= 20000)]   # médiane bornée [50;20000] €/m² (compute_medianes_secteur)
    if band.size == 0:
        return {"median": None, "n": n, "max_comp": max_comp}
    return {"median": float(np.median(band)), "n": n,
            "max_comp": max_comp, "fiabilite": "fiable", "commune_fallback": False}


def estime_bati(p: dict, d_vente: date, mid: str, idx_bati) -> dict:
    """bilan.sector_price recalculé point-in-time : plans appart-d'abord→mixte, rayons→commune,
    période récente (5 ans, ref = année de la vente) puis élargie ; trim ; n≥8."""
    com = p.get("commune")
    pool = idx_bati.get(com)
    if pool is None:
        return {"median": None, "n": 0, "max_comp": None}
    # coupe de fuite : strictement avant la vente + exclusion de la mutation jugée
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
            kept = filtre_bati(list(prix))
            if len(kept) >= MIN_N:
                annees = pool["annee"][m]
                chosen = (label, kept, commune_wide, int(annees.max()), pool["d"][m].max())
                break
        if chosen:
            break
    if chosen is None:
        # repli sector_price : mixte commune, toutes périodes, quel que soit n (fiabilité insuffisant)
        m = base
        prix = pool["prix"][m]
        kept = filtre_bati(list(prix))
        if not kept:
            return {"median": None, "n": 0, "max_comp": pool["d"][m].max()}
        annees = pool["annee"][m]
        chosen = ("mixte (appart+maison)", kept, True, int(annees.max()), pool["d"][m].max())
    label, kept, commune_fallback, annee_max, max_comp = chosen
    fia = fiabilite_bati(kept, annee_max, ref_year, label, commune_fallback)
    return {"median": float(statistics.median(kept)), "n": len(kept),
            "type_prix": label, "fiabilite": fia, "commune_fallback": commune_fallback,
            "max_comp": max_comp}


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
    """€/m² réellement payé, sur la base propre à la vente."""
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
    idx_bati = index_bati(bati_rows)
    idx_terr = index_terrain(terr_rows)
    print(f"  bâti : {sum(len(v['prix']) for v in idx_bati.values())} comparables dédoublonnés "
          f"/ {len(idx_bati)} communes")
    print(f"  terrain : {sum(len(v['prix']) for v in idx_terr.values())} comparables "
          f"/ {len(idx_terr)} secteurs")

    lignes = []
    for row in univers:
        typ = typologie(row)
        if typ == "autre":
            continue
        reel, base_reel = prix_reel(row, typ)
        if reel is None:
            continue
        # garde-fou de vraisemblance du prix RÉEL (artefacts DVF)
        g = GARDE_BATI if base_reel == "bati" else GARDE_TERRAIN
        if not (g[0] <= reel <= g[1]):
            continue

        idu = row["idu"]
        p = parc.get(idu)
        nat = nature_parcelle(p)
        d_vente = row["d"]
        mid = row["id_mutation"]

        if nat == "nu":
            est = estime_terrain_nu(idu, d_vente, mid, idx_terr)
            base_est = "terrain"
            type_prix = "terrain nu · secteur"
        else:  # bâti ou non mesuré → comparateur bâti (comme estimation_annonce)
            if p is None:   # parcelle absente de `parcels` : l'outil ne saurait pas l'estimer
                est = {"median": None, "n": 0, "max_comp": None}
            else:
                est = estime_bati(p, d_vente, mid, idx_bati)
            base_est = "bati"
            type_prix = est.get("type_prix")

        est_med = est.get("median")
        estimable = est_med is not None
        # fuite : la date du comparable le plus récent doit être < date de la vente jugée
        fuite_ok = True if est.get("max_comp") is None else (est["max_comp"] < d_vente)

        if estimable:
            fia = est.get("fiabilite", "fiable")
            cf = bool(est.get("commune_fallback"))
            bdg = badge(fia, cf)
            err = est_med / reel - 1.0
        else:
            fia = None
            cf = None
            bdg = None
            err = None

        nature_mismatch = (base_est != base_reel)

        lignes.append({
            "idu": idu, "insee": row["insee"], "commune": communes.get(row["insee"], p.get("commune") if p else None),
            "id_mutation": mid, "date": d_vente.isoformat(), "type_vente": typ,
            "nature_parcelle": nat, "base_estimation": base_est, "base_reelle": base_reel,
            "prix_reel_m2": round(reel, 1), "prix_estime_m2": (round(est_med, 1) if estimable else None),
            "type_prix": type_prix, "n_comparables": est.get("n", 0),
            "fiabilite": fia, "badge": bdg, "commune_fallback": cf,
            "estimable": estimable, "nature_mismatch": nature_mismatch,
            "erreur_pct": (round(100 * err, 2) if err is not None else None),
            "abs_erreur_pct": (round(100 * abs(err), 2) if err is not None else None),
            "dans_10pct": (abs(err) <= 0.10) if err is not None else None,
            "dans_20pct": (abs(err) <= 0.20) if err is not None else None,
            "date_comparable_max": (est["max_comp"].isoformat() if est.get("max_comp") else None),
            "fuite_ok": fuite_ok,
        })

    return lignes


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  Agrégation & métriques
# ══════════════════════════════════════════════════════════════════════════════════════════════
def metriques(sous: list[dict]) -> dict:
    n = len(sous)
    est = [l for l in sous if l["estimable"]]
    ne = n - len(est)
    errs = [l["abs_erreur_pct"] for l in est]
    signed = [l["erreur_pct"] for l in est]
    m = {
        "n_ventes": n,
        "n_estimable": len(est),
        "pct_non_estimable": round(100 * ne / n, 1) if n else None,
        "ecart_median_abs_pct": round(statistics.median(errs), 1) if errs else None,
        "ecart_median_signe_pct": round(statistics.median(signed), 1) if signed else None,
        "biais_moyen_signe_pct": round(statistics.mean(signed), 1) if signed else None,
        "pct_dans_10": round(100 * sum(1 for l in est if l["dans_10pct"]) / len(est), 1) if est else None,
        "pct_dans_20": round(100 * sum(1 for l in est if l["dans_20pct"]) / len(est), 1) if est else None,
    }
    return m


def ventile(lignes, cle):
    groupes = defaultdict(list)
    for l in lignes:
        groupes[l[cle]].append(l)
    return {k: metriques(v) for k, v in sorted(groupes.items(), key=lambda kv: -len(kv[1]))}


def _maison_apt(lignes):
    """Mécanisme « maison estimée au prix d'un appartement » : parmi les ventes de MAISON estimées
    (base alignée = parcelle bâtie → comparateur bâti), part dont le plan retenu est APPARTEMENT PUR,
    et son écart médian signé (positif = surestimation, l'appartement valant plus cher au m²)."""
    mz = [l for l in lignes if l["type_vente"] == "maison" and l["estimable"] and not l["nature_mismatch"]]
    apt = [l for l in mz if (l["type_prix"] or "").startswith("appartement")]
    mix = [l for l in mz if (l["type_prix"] or "").startswith("mixte")]
    def bloc(x):
        return {"n": len(x),
                "ecart_median_abs_pct": round(statistics.median([l["abs_erreur_pct"] for l in x]), 1) if x else None,
                "ecart_median_signe_pct": round(statistics.median([l["erreur_pct"] for l in x]), 1) if x else None,
                "pct_dans_20": round(100 * sum(1 for l in x if l["dans_20pct"]) / len(x), 1) if x else None}
    return {"maisons_estimees": len(mz), "plan_appartement_pur": bloc(apt),
            "plan_mixte_appart_maison": bloc(mix)}


def principal():
    lignes = run()
    # export par-vente
    cols = list(lignes[0].keys())
    with open(ICI / "PAR-VENTE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(lignes)

    aligne = [l for l in lignes if not l["nature_mismatch"]]
    terr = [l for l in lignes if l["type_vente"] == "terrain nu"]
    badge_seg = lambda src: {b: metriques([l for l in src if l["estimable"] and l["badge"] == b])
                             for b in ("Élevée", "Moyenne", "Limitée")}
    res = {
        "global": metriques(lignes),
        "global_base_alignee": metriques(aligne),   # hors nature-mismatch (estimateur sur la bonne base)
        "par_type": ventile(lignes, "type_vente"),
        "par_type_base_alignee": ventile(aligne, "type_vente"),
        "terrain_detail": {
            "parcelle_nue_alignee": metriques([l for l in terr if l["nature_parcelle"] == "nu"]),
            "parcelle_batie_mismatch": metriques([l for l in terr if l["nature_parcelle"] != "nu"]),
        },
        "par_commune": ventile(lignes, "commune"),
        # badge SUR CASES ALIGNÉS : juge le pouvoir discriminant RÉEL du badge, hors mismatch
        "par_badge": badge_seg(lignes),
        "par_badge_base_alignee": badge_seg(aligne),
        "maison_prix_appartement": _maison_apt(lignes),
        "nature_mismatch": {
            "n": sum(1 for l in lignes if l["nature_mismatch"]),
            "pct": round(100 * sum(1 for l in lignes if l["nature_mismatch"]) / len(lignes), 1),
            "detail": {
                "terrain_vendu_parcelle_batie": sum(1 for l in lignes
                    if l["base_reelle"] == "terrain" and l["base_estimation"] == "bati"),
                "bati_vendu_parcelle_nue": sum(1 for l in lignes
                    if l["base_reelle"] == "bati" and l["base_estimation"] == "terrain"),
            },
        },
        "fuite": {
            "toutes_ok": all(l["fuite_ok"] for l in lignes),
            "n_violations": sum(1 for l in lignes if not l["fuite_ok"]),
        },
    }
    with open(ICI / "METRIQUES.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    # ── impression lisible ────────────────────────────────────────────────────────────────────
    def ligne_tab(nom, m):
        return (f"{nom:<26} n={m['n_ventes']:>5}  non-est={str(m['pct_non_estimable'])+'%':>7}  "
                f"médian|écart|={str(m['ecart_median_abs_pct'])+'%':>8}  "
                f"±10%={str(m['pct_dans_10'])+'%':>7}  ±20%={str(m['pct_dans_20'])+'%':>7}  "
                f"médian signé={str(m['ecart_median_signe_pct'])+'%':>8}")

    print("\n================  GLOBAL  ================")
    print(ligne_tab("Toutes ventes", res["global"]))
    print(ligne_tab("Base alignée (hors mismatch)", res["global_base_alignee"]))
    print("\n================  PAR TYPE (toutes)  ================")
    for k, m in res["par_type"].items():
        print(ligne_tab(k, m))
    print("\n================  PAR TYPE (base alignée)  ================")
    for k, m in res["par_type_base_alignee"].items():
        print(ligne_tab(k, m))
    print("\n================  TERRAIN : détail nature parcelle  ================")
    print(ligne_tab("parcelle NUE (alignée)", res["terrain_detail"]["parcelle_nue_alignee"]))
    print(ligne_tab("parcelle BÂTIE (mismatch)", res["terrain_detail"]["parcelle_batie_mismatch"]))
    print("\n================  PAR BADGE (toutes)  ================")
    for k, m in res["par_badge"].items():
        print(ligne_tab(k, m))
    print("\n================  PAR BADGE (base alignée)  ================")
    for k, m in res["par_badge_base_alignee"].items():
        print(ligne_tab(k, m))
    print("\n================  MAISON estimée au prix d'un APPARTEMENT  ================")
    print(json.dumps(res["maison_prix_appartement"], ensure_ascii=False, indent=2))
    print("\n================  PAR COMMUNE  ================")
    for k, m in res["par_commune"].items():
        print(ligne_tab(str(k), m))
    print("\n================  NATURE MISMATCH  ================")
    print(json.dumps(res["nature_mismatch"], ensure_ascii=False, indent=2))
    print("\n================  CONTRÔLE DE FUITE  ================")
    print(json.dumps(res["fuite"], ensure_ascii=False, indent=2))
    print(f"\nécrit : {ICI/'PAR-VENTE.csv'}  et  {ICI/'METRIQUES.json'}")


if __name__ == "__main__":
    principal()
