#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-4 — pour une MAISON dont le TERRAIN est CONNU, comment traiter les comparables SANS terrain
renseigné (terrain = 0 dans DVF) ? On mesure NO-LEAK trois variantes, sur les ventes 2025 de maisons de
terrain connu, surface connue (niveau « surface » du servi) :

  A. PLEIN POIDS (actuel)   — la pondération ESTIMER-3 saute le facteur « écart de terrain » quand le
                              comparable n'a pas de terrain → il garde tout son poids (distance/surface/âge).
  B. PÉNALISÉ               — on applique le facteur terrain en traitant le comparable comme terrain = 0
                              (écart = terrain du sujet) → il est d'autant plus pénalisé que le sujet a du terrain.
  C. ÉCARTÉ si ≥ 8 restent  — on retire les comparables sans terrain quand il reste ≥ 8 comparables AVEC
                              terrain dans la sélection ; sinon on les garde (repli).

Pour chaque variante : écart MÉDIAN |estimé−réel| et BIAIS SIGNÉ médian (estimé/réel − 1 ; négatif =
sous-estimation, positif = surestimation), GLOBAL et PAR COMMUNE, sur les sujets « concernés » (dont la
sélection contient au moins un comparable sans terrain — les seuls où la variante change l'estimation).

Réutilise STRICTEMENT la chaîne no-leak servie (`banc_estimer.charger3` + `estimer3._selection_rayon` +
la pondération de `estimer3.eur_m2_semblable`). Seul le traitement du terrain manquant varie.

    PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
      ~/Desktop/labuse/.venv/bin/python docs/audit-2026-11/estimer-4/mesure_terrain.py [N]
"""
from __future__ import annotations

import math
import os
import random
import statistics
import sys
from collections import defaultdict

import sqlalchemy as sa

from labuse.pige import banc_estimer as B
from labuse.pige import estimer3 as E3

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100000     # plafond de sujets (défaut : tous)
MIN_AVEC_TERRAIN = 8                                       # variante C : seuil de comparables avec terrain
MIN_CELL = 20                                             # commune servie dans le rapport si ≥ ce nb de sujets


def eur_m2_variant(comps, subj, mode: str):
    """Médiane €/m² pondérée par la ressemblance (maison), AVEC un traitement du terrain manquant selon
    `mode` ∈ {full, penalize, exclude}. Copie fidèle de `estimer3.eur_m2_semblable` (maison, sans pièces) ;
    seule la branche « comparable sans terrain » change."""
    par = E3.POIDS["maison"]
    st = subj.get("terrain")
    ss = subj.get("surf_poids")
    work = comps
    if mode == "exclude":
        avec = [c for c in comps if (c.get("terrain_m2") or 0) > 0]
        if len(avec) >= MIN_AVEC_TERRAIN:
            work = avec
    ref_dec = max((c["ydec"] for c in work if c.get("ydec")), default=0.0)
    vw = []
    for c in work:
        w = 1.0
        if c.get("distance_m") is not None:
            w *= math.exp(-((float(c["distance_m"]) / par["h_dist"]) ** 2))
        if ss and ss > 0 and c.get("surface_m2"):
            w *= math.exp(-abs(float(c["surface_m2"]) - float(ss)) / par["h_surf"])
        ht = par.get("h_terr")
        ct = float(c.get("terrain_m2") or 0)
        if ht and st and st > 0:
            if ct > 0:
                w *= math.exp(-abs(ct - float(st)) / ht)
            elif mode == "penalize":
                # terrain NON renseigné → traité comme 0 : écart = terrain du sujet (pénalité proportionnelle).
                w *= math.exp(-abs(0.0 - float(st)) / ht)
            # mode == "full" : on saute le facteur (comportement actuel).
        if par.get("halflife") and c.get("ydec"):
            w *= 0.5 ** (max(0.0, ref_dec - c["ydec"]) / par["halflife"])
        if not (w > 0) or not math.isfinite(w):
            w = 1e-12
        vw.append((float(c["prix_m2_f"]), w))
    _q1, med, _q3 = E3._wquantiles(vw)
    return med


def _med(xs):
    return round(statistics.median(xs), 1) if xs else None


def main():
    url = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    engine = sa.create_engine(url, future=True)
    D = B.charger3(engine)
    rng = random.Random(B.SEED)

    # sujets : maisons vendues en 2025, TERRAIN CONNU, surface connue, €/m² dans la garde.
    sujets = []
    for r in D["pool"]:
        if r["type_local"] != "Maison" or r["d"].year != B.ANNEE_VENTES:
            continue
        if not (B.GARDE_BATI[0] <= float(r["eurm2"]) <= B.GARDE_BATI[1]):
            continue
        if float(r["terr"] or 0) <= 0:
            continue
        sujets.append(r)
    rng.shuffle(sujets)
    sujets = sujets[:N]

    MODES = ("full", "penalize", "exclude")
    # erreurs signées + absolues, sur les sujets CONCERNÉS (sélection contenant ≥1 comparable sans terrain).
    g_abs = {m: [] for m in MODES}
    g_sig = {m: [] for m in MODES}
    com_abs = {m: defaultdict(list) for m in MODES}
    com_sig = {m: defaultdict(list) for m in MODES}
    n_sujets = n_concernes = 0

    for k in sujets:
        sx, sy = float(k["x"]), float(k["y"])
        dv = k["ydec"]
        surf = float(k["bati"])
        val = float(k["val"])
        comps = []
        for c in D["by_com"].get(k["insee"], ()):
            if c["mid"] == k["mid"] or c["ydec"] >= dv:
                continue
            comps.append({**c, "distance_m": math.hypot(float(c["x"]) - sx, float(c["y"]) - sy),
                          "prix_m2_f": float(c["eurm2"]), "surface_m2": float(c["bati"]),
                          "terrain_m2": float(c["terr"] or 0), "annee": c["d"].year})
        sel, _radius, _cf = E3._selection_rayon(comps, "maison")
        if len(sel) < E3.SEUIL:
            continue
        n_sujets += 1
        sans_terrain = sum(1 for c in sel if (c.get("terrain_m2") or 0) <= 0)
        if sans_terrain == 0:
            continue    # aucune variante ne change l'estimation → sujet non concerné
        n_concernes += 1
        subj = {"surf_poids": surf, "terrain": float(k["terr"])}
        for m in MODES:
            med = eur_m2_variant(sel, subj, m)
            if not med:
                continue
            signed = (surf * med / val - 1.0) * 100.0
            g_abs[m].append(abs(signed))
            g_sig[m].append(signed)
            com_abs[m][k["insee"]].append(abs(signed))
            com_sig[m][k["insee"]].append(signed)

    print(f"Sujets maisons terrain-connu / surface-connue évalués : {n_sujets}")
    print(f"Dont CONCERNÉS (≥1 comparable sans terrain dans la sélection) : {n_concernes} "
          f"({round(100 * n_concernes / max(1, n_sujets), 1)} %)\n")

    print("GLOBAL (sujets concernés) — écart médian | biais signé médian :")
    for m in MODES:
        print(f"  {m:9s} : écart {_med(g_abs[m])} %   biais {_med(g_sig[m]):+} %   (n={len(g_abs[m])})")

    print("\nPAR COMMUNE (sujets concernés, communes ≥ "
          f"{MIN_CELL}) — écart médian / biais signé médian, par variante :")
    communes = sorted({i for i in com_abs["full"] if len(com_abs["full"][i]) >= MIN_CELL},
                      key=lambda i: -len(com_abs["full"][i]))
    print(f"  {'insee':7s} {'n':>4s}  " + "  ".join(f"{m:^19s}" for m in MODES))
    print(f"  {'':7s} {'':>4s}  " + "  ".join(f"{'écart   biais':^19s}" for _ in MODES))
    for ins in communes:
        n = len(com_abs["full"][ins])
        cells = []
        for m in MODES:
            cells.append(f"{_med(com_abs[m][ins]):>5} {_med(com_sig[m][ins]):>+6}")
        print(f"  {ins:7s} {n:>4d}  " + "  ".join(f"{c:^19s}" for c in cells))

    # ── verdict : une variante réduit-elle l'écart OU le |biais| SANS dégrader l'autre ? (précision fine,
    #    car l'écart se joue au centième — la mesure est déterministe sur toute la cohorte 2025). ──
    def mm(xs):
        return statistics.median(xs) if xs else float("nan")
    def me(xs):
        return statistics.mean(xs) if xs else float("nan")
    print("\nVERDICT (écart médian | biais médian signé | biais MOYEN signé, au centième) :")
    base_e, base_bm, base_bmoy = mm(g_abs["full"]), mm(g_sig["full"]), me(g_sig["full"])
    print(f"  full      : écart {base_e:.3f}   biais méd {base_bm:+.3f}   biais moyen {base_bmoy:+.2f}")
    for m in ("penalize", "exclude"):
        e, bm, bmoy = mm(g_abs[m]), mm(g_sig[m]), me(g_sig[m])
        # « améliore » = réduit STRICTEMENT l'écart OU le |biais médian|, SANS dégrader l'autre
        #   (ni le |biais médian|, ni l'écart, ni le |biais moyen|).
        reduit = (e < base_e - 1e-6) or (abs(bm) < abs(base_bm) - 1e-6)
        degrade = (e > base_e + 1e-6) or (abs(bm) > abs(base_bm) + 1e-6) or (abs(bmoy) > abs(base_bmoy) + 1e-6)
        verdict = "AMÉLIORE sans dégrader" if (reduit and not degrade) else "NE QUALIFIE PAS (améliore l’un, dégrade l’autre)"
        print(f"  {m:9s} : écart {e:.3f} ({e - base_e:+.3f})   biais méd {bm:+.3f} ({abs(bm) - abs(base_bm):+.3f} en |·|)   "
              f"biais moyen {bmoy:+.2f} ({abs(bmoy) - abs(base_bmoy):+.2f} en |·|)   → {verdict}")


if __name__ == "__main__":
    main()
