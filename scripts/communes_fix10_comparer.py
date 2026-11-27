#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-10 LOT 4 — PREUVE : sous le seuil, Comparer MASQUE le prix du terrain MAIS SERT
l'effectif des ventes utilisées (comme la fiche et le Carnet). Avant, `_compare_row` filtrait les
sections sur `mediane_prix_m2` (déjà None sous le seuil) → la section était écartée → effectif vide.

Exemple du rapport : 97415000CD0003 (Saint-Paul), section 97415000CD, terrain = 1 vente.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix10_comparer.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from labuse.dvf_secteur import prix_sections


def _terrain_servi_comparer(secteur: list[dict]) -> tuple[object, object]:
    """Reproduit l'extraction CORRIGÉE de `app._compare_row` : sélection par TYPE + ventes (jamais en
    exigeant le prix, déjà masqué sous le seuil), prix masqué, EFFECTIF servi."""
    terr = [s for s in secteur if (s.get("type_bien") or "").lower() in ("terrain", "terrain à bâtir")
            and (s.get("n_ventes") or 0) > 0]
    sel = max(terr, key=lambda s: s.get("n_ventes") or 0) if terr else None
    return (sel or {}).get("mediane_prix_m2"), (sel or {}).get("n_ventes")


def main() -> int:
    url = os.environ.get("LABUSE_TEST_DATABASE_URL")
    if not url:
        print("LABUSE_TEST_DATABASE_URL manquant", file=sys.stderr)
        return 2
    with Session(create_engine(url)) as s:
        secteur = [{"type_bien": p["type_bien"], "n_ventes": p["n_ventes"],
                    "mediane_prix_m2": p["mediane_prix_m2"]} for p in prix_sections(s, "97415000CD")]
        print("section 97415000CD (prix_sections, seuil 8) :", secteur)
        prix, n = _terrain_servi_comparer(secteur)
        print(f"Comparer → terrain_zone_eur_m2={prix} (prix MASQUÉ sous le seuil) · prix_terrain_n={n} (effectif SERVI)")
        ok = prix is None and n == 1
        print("SUCCÈS : effectif 1 servi, prix masqué." if ok
              else f"ÉCHEC : prix={prix} n={n}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
