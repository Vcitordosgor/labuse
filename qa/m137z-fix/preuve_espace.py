#!/usr/bin/env python
"""M137-Z-fix — PREUVE que restreindre le nettoyeur [.,;] → [.,] ne bouge QUE l'espace avant « ; ».

Le point-virgule français prend un espace AVANT (« 47 % ; »). L'ancien `nettoyer_libelle_client`
(export_commun.py) le retirait (« 47 %; »), fautif et divergent de la donnée cascade + de la référence
golden. Ce script compare, sur TOUTES les paires (layer, detail) distinctes du run servi, la sortie
ANCIENNE (fonction du commit parent `main`) à la sortie NOUVELLE (module courant), et vérifie que la
SEULE différence est la restauration d'un espace avant « ; » — zéro autre changement.

Usage :
    LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \\
        .venv/bin/python qa/m137z-fix/preuve_espace.py [--run q_v10_m129] [--base main]

Code retour : 0 si 0 violation (preuve établie), 1 sinon.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

import psycopg

from labuse.api.export_commun import nettoyer_libelle_client as clean_new


def _load_old(base: str):
    """Charge le `nettoyer_libelle_client` ANCIEN depuis le commit `base` (git show + exec isolé)."""
    src = subprocess.check_output(["git", "show", f"{base}:src/labuse/api/export_commun.py"], text=True)
    ns: dict = {}
    exec(compile(src, "export_commun@base", "exec"), ns)  # imports du fichier = stdlib/sqlalchemy (sûrs)
    return ns["nettoyer_libelle_client"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="q_v10_m129")
    ap.add_argument("--base", default="main", help="commit portant l'ANCIEN nettoyeur (défaut : main)")
    ap.add_argument("--dsn", default="postgresql://openclaw@localhost:5432/labuse")
    a = ap.parse_args()

    clean_old = _load_old(a.base)
    conn = psycopg.connect(a.dsn)
    rows = conn.execute(
        "SELECT DISTINCT layer_name, detail FROM dryrun_cascade_results "
        "WHERE run_label=%s AND detail IS NOT NULL", (a.run,)).fetchall()

    changed = 0
    violations = []
    for layer, detail in rows:
        o = clean_old(layer, detail)
        n = clean_new(layer, detail)
        if o == n:
            continue
        changed += 1
        # SEULE différence permise : NEW restaure un espace avant « ; » que OLD retirait.
        # Donc re-retirer cet espace de NEW (\s+; → ;) doit redonner EXACTEMENT OLD.
        if re.sub(r"\s+;", ";", n) != o:
            violations.append((layer, o, n))

    print(f"run                    : {a.run}")
    print(f"paires (layer,detail)  : {len(rows)}")
    print(f"paires changées OLD→NEW: {changed}")
    print(f"violations (≠ espace-;): {len(violations)}")
    for v in violations[:20]:
        print("  !!", v)
    ok = not violations
    print("\nPREUVE", "ÉTABLIE — rien d'autre que l'espace avant « ; » ne bouge." if ok else "ÉCHOUÉE.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
