#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-11 — NON-RÉGRESSION (routes/fonctions réelles) sur ce que le rapport ASTRA-8
déclare CLOS. FIX-11 ne touche que l'en-tête Marché (front) + la chronologie PLU de La Plaine : ces
témoins ne doivent pas bouger.

Témoins (rapport §« Ça pourrait être mieux ») :
  · Saint-Paul CD terrain : prix absent, 1 vente.
  · Saint-Denis IZ terrain : 284 €/m² sur 14 ventes.
  · Les Avirons AT : maisons masquées (7), appartements (1), terrains (2).
  · La Possession AB : maisons masquées (7), terrain publié 313 €/m² sur 28 ventes.
  · Les Trois-Bassins : date PLU connue au MOIS (2025-05).
  · 212 sections de terrain entre 3 et 7 ventes.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix11_non_regression.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.dvf_secteur import prix_section


def main() -> int:
    url = os.environ.get("LABUSE_TEST_DATABASE_URL")
    if not url:
        print("LABUSE_TEST_DATABASE_URL manquant", file=sys.stderr)
        return 2
    ok = True

    def chk(label, cond, got):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'OK ' if cond else 'KO '}] {label} — {got}")

    with Session(create_engine(url)) as s:
        print("Prix de section (fonction servie prix_section, seuil 8) :")
        cd = prix_section(s, "97415000CD", "terrain")
        chk("Saint-Paul CD terrain : prix masqué, 1 vente", cd["prix_m2"] is None and cd["n"] == 1,
            f"prix={cd['prix_m2']} n={cd['n']}")
        iz = prix_section(s, "97411000IZ", "terrain")
        chk("Saint-Denis IZ terrain : 284 €/m², 14 ventes", iz["prix_m2"] == 284 and iz["n"] == 14,
            f"prix={iz['prix_m2']} n={iz['n']}")
        at_m = prix_section(s, "97401000AT", "maison")
        at_t = prix_section(s, "97401000AT", "terrain")
        chk("Les Avirons AT : maison masquée (7), terrain masqué (2)",
            at_m["prix_m2"] is None and at_m["n"] == 7 and at_t["prix_m2"] is None and at_t["n"] == 2,
            f"maison prix={at_m['prix_m2']} n={at_m['n']} · terrain prix={at_t['prix_m2']} n={at_t['n']}")
        ab_m = prix_section(s, "97408000AB", "maison")
        ab_t = prix_section(s, "97408000AB", "terrain")
        chk("La Possession AB : maison masquée (7), terrain 313 €/m² sur 28 ventes",
            ab_m["prix_m2"] is None and ab_m["n"] == 7 and ab_t["prix_m2"] == 313 and ab_t["n"] == 28,
            f"maison prix={ab_m['prix_m2']} n={ab_m['n']} · terrain prix={ab_t['prix_m2']} n={ab_t['n']}")

        print("Date PLU au mois + décompte sections :")
        from labuse import veille_plu as V
        tb = V.entry("97423") or {}
        # FIX-12 : la valeur de référence corrigée est 2025-09-04 (le débat PADD du 04/09/2025 que FIX-11
        # LOT 2 a lui-même établi comme dernière pièce de la révision) — pas l'ancien mois 2025-05
        # d'ASTRA-8. Le débat est AUSSI consigné en fait daté (debat_padd_tenu) sans armer le sursis.
        chk("Les Trois-Bassins : dernière pièce 2025-09-04 (débat PADD, jour)", tb.get("etat_source_date") == "2025-09-04",
            f"etat_source_date={tb.get('etat_source_date')!r}")
        chk("Les Trois-Bassins : débat PADD consigné en fait daté, sursis NON armé",
            tb.get("debat_padd_tenu") == "2025-09-04" and tb.get("debat_padd") in ("ABSENT", None),
            f"debat_padd_tenu={tb.get('debat_padd_tenu')!r} debat_padd={tb.get('debat_padd')!r}")
        n212 = s.execute(text("SELECT count(*) FROM dvf_secteur_medianes WHERE type_bien='terrain' "
                              "AND n_ventes BETWEEN 3 AND 7")).scalar()
        chk("212 sections de terrain entre 3 et 7 ventes", n212 == 212, f"n={n212}")

    print()
    if ok:
        print("SUCCÈS : aucune régression sur les témoins clos.")
        return 0
    print("ÉCHEC : au moins un témoin a bougé.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
