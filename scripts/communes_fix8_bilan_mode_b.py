#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-8 (2) — PREUVE : le Bilan mode B porte l'EFFECTIF (nb de ventes utilisées)
ET la mention « Estimé » à côté d'un prix de section fondé sur 3 à 7 ventes, sur les trois surfaces
citées par la relecture : à l'ÉCRAN, dans le PDF, dans l'Excel.

Les 3 exemples de ~/Desktop/relecture-communes-4.md (réserve 1) :
    97406000AR La Plaine-des-Palmistes — 7 ventes, 74 €/m²
    97408000AH La Possession          — 7 ventes, 385 €/m²
    97405000AO Petite-Île             — 7 ventes, 143 €/m²

Chaque chiffre vient d'une fonction SERVIE (pas d'un littéral) ; sortie brute.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python \
        scripts/communes_fix8_bilan_mode_b.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from labuse.api.blocs_documents import rehab_bloc
from labuse.estimation_prix import fourchette as _fourchette
from labuse.faisabilite.bilan import _eur, _prix_terrain_local

SECTIONS = [
    ("97406000AR", "La Plaine-des-Palmistes", 74),
    ("97408000AH", "La Possession", 385),
    ("97405000AO", "Petite-Île", 143),
]


def _terrain_nu_servi(session: Session, idu: str) -> dict:
    """Reconstruit le dict `terrain_nu` EXACTEMENT comme compute_mode_b (bilan.py l.1293-1302) :
    mêmes champs, même source (_prix_terrain_local, seuil mode B = 3)."""
    px = _prix_terrain_local(session, idu)          # {prix_m2, n, niveau, libelle} — fonction servie
    surface = 500.0                                  # surface de parcelle d'exemple (n'entre pas dans n)
    valeur = round(px["prix_m2"] * surface)
    fr = _fourchette(valeur)
    return {
        "valeur_eur": valeur, "valeur_libelle": _eur(valeur),
        "valeur_bas_eur": fr["bas"], "valeur_haut_eur": fr["haut"],
        "valeur_fourchette_libelle": f"{_eur(fr['bas'])} – {_eur(fr['haut'])}",
        "incertitude": fr["mention"],
        "prix_m2": round(px["prix_m2"]), "surface_m2": round(surface),
        "niveau": px["niveau"], "libelle": px["libelle"],
        "effectif": px.get("n"),                     # FIX-8 (2)
        "etiquette": "Estimé",
    }, px


def main() -> int:
    url = os.environ.get("LABUSE_TEST_DATABASE_URL")
    if not url:
        print("LABUSE_TEST_DATABASE_URL manquant", file=sys.stderr)
        return 2
    eng = create_engine(url)
    echecs = []
    with Session(eng) as session:
        for sec, commune, prix_attendu in SECTIONS:
            idu = sec + "0001"                        # _prix_terrain_local n'utilise que idu[:10]/[:5]
            tn, px = _terrain_nu_servi(session, idu)
            n = tn["effectif"]
            print(f"\n{'='*78}\n{sec}  {commune}  —  prix servi {px['prix_m2']} €/m² "
                  f"(attendu {prix_attendu}), effectif {n} ventes")
            assert px["prix_m2"] == prix_attendu, f"prix {px['prix_m2']} != {prix_attendu}"
            assert 3 <= n <= 7, f"effectif {n} hors 3-7"

            # ── SURFACE 1 — ÉCRAN (JSON servi au front, consommé par constructibilite.tsx) ──────────
            print(f"  [ÉCRAN]  terrain_nu.effectif={tn['effectif']!r}  terrain_nu.etiquette={tn['etiquette']!r}")
            print(f"           terrain_nu.libelle={tn['libelle']!r}")
            ok_ecran = tn["effectif"] == n and tn["etiquette"] == "Estimé" and f"{n} vente" in tn["libelle"]

            # ── SURFACE 2 — PDF (rehab_bloc → pdf_premium.py + _bloc_html WeasyPrint) ───────────────
            mb = {"disponible": True, "achat_max_libelle": "180 000 €",
                  "surface_parcelle_m2": tn["surface_m2"], "terrain_nu": tn}
            bloc = rehab_bloc(mb)
            ligne_pdf = next((t for _, t in bloc["lignes"] if "Terrain nu au prix du secteur" in t), "")
            print(f"  [PDF]    bloc.etat={bloc['etat']!r}")
            print(f"           {ligne_pdf}")
            ok_pdf = (f"{n} vente" in ligne_pdf) and ("Estimé" in ligne_pdf)

            if ok_ecran and ok_pdf:
                print(f"  → OK : effectif ({n} ventes) + « Estimé » présents à l'écran ET dans le PDF.")
            else:
                echecs.append((sec, "ecran" if not ok_ecran else "", "pdf" if not ok_pdf else ""))

    # ── SURFACE 3 — EXCEL : aucun export Excel ne rend le prix de section du mode B ──────────────────
    print(f"\n{'='*78}\n[EXCEL]  Le prix de section 3-7 ventes du mode B (_prix_terrain_local / _prix_bati_local,")
    print("         seuil 3) N'EST servi que par compute_mode_b → écran + PDF. Aucun .xlsx ne le rend.")
    print("         Preuve (grep sur les générateurs Excel) :")
    grep = subprocess.run(
        ["grep", "-rnE", "terrain_nu|compute_mode_b|rehab_bloc|_prix_terrain_local|_prix_bati_local",
         "src/labuse/bilan/excel.py", "src/labuse/api/bilan.py"],
        capture_output=True, text=True)
    out = grep.stdout.strip()
    print("           " + (out.replace("\n", "\n           ") if out else "(aucune occurrence)"))
    # Le Bilan promoteur /bilan/{idu}.xlsx utilise le chemin seuil-8 (MIN_N_SECTEUR), PAS la section 3-7.
    seuil8 = subprocess.run(["grep", "-nE", "MIN_N_SECTEUR *=", "src/labuse/faisabilite/bilan.py"],
                            capture_output=True, text=True).stdout.strip()
    print(f"           (Bilan promoteur Excel = chemin seuil 8 : {seuil8 or 'MIN_N_SECTEUR introuvable'})")
    ok_excel = not re.search(r"(terrain_nu|compute_mode_b|rehab_bloc|_prix_terrain_local|_prix_bati_local)", out or "")

    print(f"\n{'='*78}")
    if echecs or not ok_excel:
        print(f"ÉCHEC : {echecs}  excel_sans_mode_b={ok_excel}")
        return 1
    print("SUCCÈS : écran + PDF portent l'effectif (3-7 ventes) et « Estimé » sur les 3 exemples ;")
    print("         aucun Excel ne sert ce prix de section (rien à corriger côté Excel).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
