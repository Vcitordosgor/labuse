"""MOTEUR-VERITE-FIX-1 — rejeu de la cohorte de permis (mêmes filtres que VT-2/VT-3) sur le
moteur CORRIGÉ, avec un cache par lot (cache-<tag>/). Réutilise le runner VT-3 (qui réutilise
lui-même le module VT-2) en détournant les chemins.

    PYTHONPATH=src:docs/audit-2026-11/verite-terrain-3/scripts \
      python docs/audit-2026-11/moteur-verite-fix-1/scripts/rejouer_fix.py <tag> [run|rapport]
"""
from __future__ import annotations

import sys
from pathlib import Path

tag = sys.argv[1] if len(sys.argv) > 1 else "lot1"
cmd = sys.argv[2] if len(sys.argv) > 2 else "run"

import rejouer_capacite_vt3 as r3   # noqa: E402 — fixe déjà run_seq servi + capacité enrichie
vt = r3.vt

RACINE = Path(__file__).resolve().parents[4]
SORTIE = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1"
vt.SORTIE = SORTIE
vt.CACHE = SORTIE / f"cache-{tag}"
vt.PERMIS_CSV = SORTIE / f"PERMIS-VS-CAPACITE-{tag.upper()}.csv"
vt.NOTES_MD = SORTIE / f"PERMIS-VS-CAPACITE-{tag.upper()}-NOTES.md"
vt.PARTIEL_CSV = SORTIE / f"_capacite_partiel_{tag}.csv"

if __name__ == "__main__":
    print(f"tag={tag} ; cache={vt.CACHE}", flush=True)
    if cmd == "run":
        vt._run(0, None)
    else:
        vt._finaliser()
