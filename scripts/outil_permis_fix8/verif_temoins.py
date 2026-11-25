#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-8 — vérification des TÉMOINS sur la base LOCALE `labuse` (lecture seule).

Rejoue, par les VRAIES fonctions du produit, les surfaces du contre-audit ASTRA-4 :
  LOT 1 — 97441626E0304 : dépôt absent en fiche, en historique de 97416000IE1348, en frise, et dans la
          ligne du Dossier (chaîne historique_site → _r_permis_liste). Aucune autorisation sous « déposé ».
  LOT 2 — 97440226G0018 : les deux dates restent servies, AUCUNE durée d'instruction.
  LOT 4 — ligne « permis à proximité » du Dossier (chaîne nearby_permits → _c_permis → _r_permis_proximite)
          pour Petite-Île (2 annulés), Saint-Denis BZ1065, Cilaos AB0001, Saint-Paul CV1498.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/outil_permis_fix8/verif_temoins.py
"""
from __future__ import annotations

import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse.api import modules, moteurs, site_voisinage  # noqa: E402
from labuse.db import session_scope  # noqa: E402
from labuse.exports import miroir  # noqa: E402
from labuse.exports.robinet_fiche import _c_permis  # noqa: E402


def _print(titre):
    print("\n" + "=" * 92 + f"\n{titre}\n" + "=" * 92)


with session_scope() as s:
    _print("LOT 1 — 97441626E0304 (DP ; AN_DEPOT=2026 ; DR_DEPOT=01/06/2020 ; autorisé 03/08/2026)")
    f = modules.permis_fiche("97441626E0304", s)
    print(f"  fiche          : date_depot={f['date_depot']!r}  date_autorisation={f['date_autorisation']!r}  "
          f"delai_instruction={f.get('delai_instruction')!r}")
    h = site_voisinage.historique_permis(s, "97416000IE1348")
    pm = next(p for p in h["permis"] if p["permit_id"] == "97441626E0304")
    print(f"  historique     : date_depot={pm['date_depot']!r}  date_autorisation={pm['date_autorisation']!r}")
    # frise (api/moteurs.histoire_parcelle) : les libellés datés du permis
    faits = moteurs.histoire_parcelle("97416000IE1348", s)
    labels = [x["libelle"] for x in faits["faits"] if x.get("permit_id") == "97441626E0304"]
    print(f"  frise libellés : {labels}  (aucun « déposé » attendu)")
    # Dossier : la MÊME liste que l'écran passe au renderer _r_permis_liste
    dossier_ligne = miroir._r_permis_liste(h["permis"])
    print(f"  Dossier (rendu): {dossier_ligne}")
    print(f"  → '2020' dans le Dossier ? {'2020' in dossier_ligne}   'déposé 03/08/2026' ? "
          f"{'déposé 03/08/2026' in dossier_ligne}")

    _print("LOT 2 — 97440226G0018 (DP ; dépôt 15/02/2026 → autorisation 13/03/2026 ; 26 jours réels)")
    g = modules.permis_fiche("97440226G0018", s)
    print(f"  fiche          : date_depot={g['date_depot']!r}  date_autorisation={g['date_autorisation']!r}  "
          f"delai_instruction={g.get('delai_instruction')!r}")

    _print("LOT 4 — Dossier « permis à proximité » (nearby_permits → _c_permis → _r_permis_proximite)")
    for idu, lib in [("97405000BE1692", "Petite-Île (2 annulés)"),
                     ("97411000BZ1065", "Saint-Denis"),
                     ("97424000AB0001", "Cilaos"),
                     ("97415000CV1498", "Saint-Paul")]:
        v = _c_permis(s, idu, {})
        rendu = miroir._r_permis_proximite(v) if v is not None else "(parcelle absente)"
        brut = "" if v is None else (f"n={v['n']} logts={v['logements']} sans={v['sans_logements']} "
                                     f"annulés={v['annules']}")
        print(f"  {idu} · {lib}\n      brut   : {brut}\n      Dossier: {rendu}")
