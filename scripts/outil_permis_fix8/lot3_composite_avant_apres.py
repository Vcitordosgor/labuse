#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-8 (LOT 3) — score composite du comparateur AVANT / APRÈS le retrait de l'axe délai.

« Avant » = les SIX axes, l'axe vélocité (délai médian dépôt→autorisation, lu de m10_permit_delais)
compris, poids 0,15 — l'état validé par FIX-5 (délai caché mais encore au classement).
« Après » = les CINQ axes restants, poids renormalisés (somme = 1) — l'état FIX-8.

Le composite est RECALCULÉ ICI, indépendamment de `composite_communes`, pour servir de contrôle :
min-max par axe selon sa direction, moyenne pondérée des axes présents ÷ somme des poids présents.
Les indicateurs bruts (stock/permis/SRU/ZAN/prix neuf) viennent de `comparateur._compute_raw` (la source
du produit) ; la vélocité vient de m10 (encore peuplée en base, bientôt dormante).

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/outil_permis_fix8/lot3_composite_avant_apres.py
"""
from __future__ import annotations

import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse import runs  # noqa: E402
from labuse.api import comparateur  # noqa: E402
from labuse.db import session_scope  # noqa: E402

DIRECTIONS = {"stock": +1, "velocite": -1, "permis": +1,
              "deficit_sru": +1, "pression_zan": -1, "prix_neuf": +1}
POIDS_AVANT = {"stock": 0.30, "velocite": 0.15, "permis": 0.15,
               "deficit_sru": 0.15, "pression_zan": 0.10, "prix_neuf": 0.15}
POIDS_APRES = {"stock": 0.30, "permis": 0.15, "deficit_sru": 0.15,
               "pression_zan": 0.10, "prix_neuf": 0.15}


def composite(rows, poids):
    """Min-max directionnel [0-100] + moyenne pondérée des axes présents ÷ Σ poids présents (renormalisé),
    rang = tri décroissant. Implémentation indépendante (contrôle de composite_communes)."""
    keys = list(poids)
    bornes = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        bornes[k] = (min(vals), max(vals)) if vals else (None, None)
    out = []
    for r in rows:
        wsum = wpres = 0.0
        for k in keys:
            lo, hi = bornes[k]
            v = r.get(k)
            if v is None or lo is None or hi == lo:
                n = None if v is None else 50.0
            else:
                frac = (v - lo) / (hi - lo)
                n = round((frac if DIRECTIONS[k] > 0 else 1 - frac) * 100, 1)
            if n is not None:
                wsum += poids[k] * n
                wpres += poids[k]
        score = round(wsum / wpres, 1) if wpres > 0 else None
        out.append({"commune": r["commune"], "score": score})
    out.sort(key=lambda r: (r["score"] is not None, r["score"] or 0), reverse=True)
    for i, r in enumerate(out, 1):
        r["rang"] = i
    return {r["commune"]: r for r in out}


with session_scope() as s:
    raw = comparateur._compute_raw(s)   # stock / permis / deficit_sru / pression_zan / prix_neuf (source produit)
    velo = {r[0]: r[1] for r in s.execute(text(
        "SELECT commune, percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois) "
        "FROM m10_permit_delais WHERE valide AND famille='logements' AND delai_mois>=0 GROUP BY commune"))}
    rows = []
    for commune, r in raw.items():
        rows.append({
            "commune": commune,
            "stock": r.get("stock"),
            "velocite": round(float(velo[commune]), 1) if velo.get(commune) is not None else None,
            "permis": r.get("permis"),
            "deficit_sru": round(float(r["deficit_sru"]), 1) if r.get("deficit_sru") is not None else None,
            "pression_zan": round(float(r["pression_zan"]), 1) if r.get("pression_zan") is not None else None,
            "prix_neuf": r.get("prix_neuf"),
        })
    avant = composite([dict(r) for r in rows], POIDS_AVANT)
    apres = composite([dict(r) for r in rows], POIDS_APRES)

    print(f"run servi : {runs.current()}   ·   {len(rows)} communes\n")
    print(f"{'Commune':<22}{'score av.':>10}{'rang av.':>9}{'score ap.':>11}{'rang ap.':>9}{'Δ rang':>8}")
    print("-" * 69)
    # trié par rang APRÈS (le classement servi désormais)
    for commune in sorted(apres, key=lambda c: apres[c]["rang"]):
        a, b = avant[commune], apres[commune]
        drang = a["rang"] - b["rang"]   # >0 : monte avec le retrait du délai
        fleche = "→" if drang == 0 else (f"↑{drang}" if drang > 0 else f"↓{-drang}")
        print(f"{commune:<22}{a['score']:>10}{a['rang']:>9}{b['score']:>11}{b['rang']:>9}{fleche:>8}")
    bouge = sum(1 for c in apres if avant[c]["rang"] != apres[c]["rang"])
    print(f"\ncommunes dont le RANG change : {bouge}/{len(rows)}")
    print("poids après (renormalisés, somme=1) :",
          {k: round(w / sum(POIDS_APRES.values()), 4) for k, w in POIDS_APRES.items()})
