#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-9 LOT C (3) — PREUVE : le Bilan mode B
  · RÉSERVE « ventes » aux effectifs d'ACTES (niveau secteur) et « sections » au repli communal
    (le champ `effectif` ne se lit plus « N ventes » quand ce sont des sections — défaut ASTRA-6 §3) ;
  · EXPLIQUE le seuil (phrase `note_seuil`) : pourquoi un prix apparaît au Bilan quand Comparer le
    masque (médiane de section dès 3 ventes au Bilan, publication publique à partir de 8).

Comme AUCUNE parcelle du run servi q_v20 n'est éligible au mode B (tier ∈ MODE_B_TIERS = 0 — vérifié
ci-dessous, conforme au rapport), on ne peut pas rendre un Bilan de bout en bout sur cette base : on
exerce donc les fonctions SERVIES (`_prix_bati_local`/`_prix_terrain_local`, construction du dict comme
`compute_mode_b`, rendu `rehab_bloc`) sur les exemples du rapport.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix9_bilan_unite.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse import runs
from labuse.api.blocs_documents import rehab_bloc
from labuse.dvf_secteur import seuil_section
from labuse.faisabilite.bilan import (
    MODE_B_TIERS, _eur, _prix_bati_local, _prix_terrain_local,
)
from labuse.estimation_prix import fourchette as _fourchette


def _note_seuil(px_terrain, px):
    seuil = seuil_section()
    ns = [p["n"] for p in (px_terrain, px)
          if p and p.get("niveau") == "secteur" and p.get("n") is not None and p["n"] < seuil]
    return (f"Hypothèse de Bilan fondée sur {min(ns)} ventes. "
            f"Un prix de marché est publié à partir de {seuil} ventes." if ns else None)


def _terrain_nu(px_terrain):
    surface = 500.0
    valeur = round(px_terrain["prix_m2"] * surface)
    fr = _fourchette(valeur)
    return {
        "valeur_eur": valeur, "valeur_libelle": _eur(valeur),
        "valeur_fourchette_libelle": f"{_eur(fr['bas'])} – {_eur(fr['haut'])}", "incertitude": fr["mention"],
        "prix_m2": round(px_terrain["prix_m2"]), "surface_m2": round(surface),
        "niveau": px_terrain["niveau"], "libelle": px_terrain["libelle"],
        "effectif": px_terrain.get("n"),
        "effectif_unite": "ventes" if px_terrain["niveau"] == "secteur" else "sections",
        "etiquette": "Estimé",
    }


def main() -> int:
    eng = create_engine(os.environ["LABUSE_TEST_DATABASE_URL"])
    with Session(eng) as s:
        run = runs.current()
        ph = "(" + ",".join(f"'{t}'" for t in MODE_B_TIERS) + ")"
        n_elig = s.execute(text(
            f"SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier IN {ph}"), {"r": run}).scalar()
        print(f"{'='*80}\n[ACCÈS MODE B] run servi={run} · parcelles éligibles (tier ∈ {MODE_B_TIERS}) = {n_elig}")
        print("  → 0 attendu : AUCUNE parcelle q_v20 ne donne accès au mode B sur cette base (bilan.py:1219)")
        print("     cause : le run q_v20 n'émet que sans_signal/ecartee/a_suivre/priorite — pas les deux")
        print("     tiers « déclassé pour cause de bâti ». Impossible donc de rendre un Bilan LIVE ici.")

        # (A) TERRAIN secteur à 7 ventes — unité « ventes » + note_seuil (97406000AR, exemple rapport)
        print(f"\n{'='*80}\n[A] secteur 7 ventes — unité « ventes » + explication du seuil")
        px_t = _prix_terrain_local(s, "97406000AR0001")
        px_b = _prix_bati_local(s, "97406000AR0001")
        tn = _terrain_nu(px_t)
        note = _note_seuil(px_t, px_b)
        print(f"  _prix_terrain_local : {px_t}")
        print(f"  terrain_nu.effectif={tn['effectif']} effectif_unite={tn['effectif_unite']!r}")
        print(f"  note_seuil = {note!r}")
        bloc = rehab_bloc({"disponible": True, "achat_max_libelle": "180 000 €",
                           "surface_parcelle_m2": 500, "terrain_nu": tn, "note_seuil": note})
        for role, t in bloc["lignes"]:
            if "Terrain nu" in t or "Hypothèse de Bilan" in t:
                print(f"    [{role}] {t}")
        ok_a = (tn["effectif_unite"] == "ventes" and "7 ventes" in next(t for _, t in bloc["lignes"] if "Terrain nu" in t)
                and note and "7 ventes" in note and "8 ventes" in note)

        # (B) COMMUNE repli — unité « sections », JAMAIS « ventes » (CD0003 terrain : 291 €/m², 56 sections,
        # l'exemple EXACT du rapport §3). Le dict terrain_nu et le rendu rehab_bloc disent « sections ».
        print(f"\n{'='*80}\n[B] repli communal — unité « sections » (97415000CD0003 terrain, exemple rapport §3)")
        px_cd = _prix_terrain_local(s, "97415000CD0003")
        print(f"  _prix_terrain_local(CD0003) : {px_cd}")
        tn_cd = _terrain_nu(px_cd)
        print(f"  niveau={px_cd['niveau']} → effectif_unite={tn_cd['effectif_unite']!r} · libellé={px_cd['libelle']!r}")
        bloc_cd = rehab_bloc({"disponible": True, "achat_max_libelle": "180 000 €",
                              "surface_parcelle_m2": 500, "terrain_nu": tn_cd})
        ligne_cd = next(t for _, t in bloc_cd["lignes"] if "Terrain nu" in t)
        print(f"    [rendu] {ligne_cd}")
        ok_b = (px_cd["niveau"] == "commune" and tn_cd["effectif_unite"] == "sections"
                and "56 sections" in ligne_cd and "vente" not in ligne_cd)

        print(f"\n{'='*80}")
        if ok_a and ok_b and n_elig == 0:
            print("SUCCÈS : « ventes » (secteur) vs « sections » (repli) distingués ; note_seuil servie ;")
            print("         accès mode B q_v20 = 0 (Bilan live impossible sur cette base, dit en clair).")
            return 0
        print(f"ÉCHEC : ok_a={ok_a} ok_b={ok_b} n_elig={n_elig}")
        return 1


if __name__ == "__main__":
    if not os.environ.get("LABUSE_TEST_DATABASE_URL"):
        print("LABUSE_TEST_DATABASE_URL manquant", file=sys.stderr); raise SystemExit(2)
    raise SystemExit(main())
