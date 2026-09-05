#!/usr/bin/env python
"""EXPORTS-1 lot 2 (2.2) — ré-étiquetage one-shot des agrégats multi-lots DÉJÀ en base.

L'ingestion géo-DVF sommait les lots d'une mutation et gardait le type du premier local :
une vente d'immeuble entier sortait « Appartement 750 m² » (audit A2, mutation
2025-1268771). L'ingestion étiquette désormais 'Immeuble' à la source (layers_ingest,
n_lots > 1) ; le stock existant ne porte pas le compte de lots → ré-étiquetage par
HEURISTIQUE DE VRAISEMBLANCE (le même seuil que le filtre d'affichage 2.3 : un
appartement > 200 m² est un agrégat multi-lots probable). Chaque ligne touchée garde la
trace du ré-étiquetage dans `raw`. Rejouable (idempotent) ; le prochain re-run DVF
réécrit tout proprement depuis la source.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/retiquette_immeubles_dvf.py [--dry-run]
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import session_scope

SEUIL_APPARTEMENT_M2 = 200   # = filtre_comparables.seuil_type_m2.appartement (dvf_profils.yaml)


def main() -> int:
    dry = "--dry-run" in sys.argv
    with session_scope() as s:
        n = s.execute(text(
            "SELECT count(*) FROM dvf_mutations "
            "WHERE type_local = 'Appartement' AND surface_reelle_bati > :s"),
            {"s": SEUIL_APPARTEMENT_M2}).scalar()
        print(f"{n} mutation(s) « Appartement > {SEUIL_APPARTEMENT_M2} m² » à ré-étiqueter 'Immeuble'")
        temoin = s.execute(text(
            "SELECT mutation_id, type_local, surface_reelle_bati FROM dvf_mutations "
            "WHERE mutation_id = '2025-1268771'")).mappings().first()
        print(f"cas de test 2025-1268771 avant : {dict(temoin) if temoin else 'absent'}")
        if dry:
            print("--dry-run : aucune écriture")
            return 0
        s.execute(text(
            "UPDATE dvf_mutations SET type_local = 'Immeuble', "
            " raw = COALESCE(raw, '{}'::jsonb) || jsonb_build_object("
            "   'retiquetage', 'exports-1 2.2 — agrégat multi-lots probable "
            "(Appartement > 200 m², heuristique de vraisemblance)', "
            "   'type_local_origine', type_local) "
            "WHERE type_local = 'Appartement' AND surface_reelle_bati > :s"),
            {"s": SEUIL_APPARTEMENT_M2})
        temoin = s.execute(text(
            "SELECT mutation_id, type_local, surface_reelle_bati FROM dvf_mutations "
            "WHERE mutation_id = '2025-1268771'")).mappings().first()
        print(f"cas de test 2025-1268771 après : {dict(temoin) if temoin else 'absent'}")
        s.commit()
        print("ré-étiquetage committé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
