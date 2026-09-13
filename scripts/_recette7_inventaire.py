#!/usr/bin/env python
"""RECETTE-7 lot 0 (Z2/Z5 discovery) — inventaire des nombres imprimés sur les 4 témoins.
Usage: PYTHONPATH=src python scripts/_recette7_inventaire.py [--fuites]"""
from __future__ import annotations
import sys
from collections import Counter

from fastapi.testclient import TestClient
from labuse.api.app import app
from labuse.db import session_scope
from labuse.exports import builder, provenance

TEMOINS = ["97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110"]
DOCS = ["dossier", "flash", "financier", "apporteur"]


def main() -> int:
    c = TestClient(app)
    total_fuites = 0
    par_id: Counter = Counter()
    for idu in TEMOINS:
        fiche = c.get(f"/parcels/{idu}").json()
        for doc in DOCS:
            try:
                with session_scope() as s:
                    res = builder.construire(s, idu, doc, fiche=fiche)
            except builder.DocumentNonEtablissable as e:
                print(f"[{idu}/{doc}] NON ÉTABLISSABLE : {[m['libelle'] for m in e.manques]}")
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"[{idu}/{doc}] ERREUR : {exc!r}")
                continue
            inv = provenance.inventaire(doc, res.valeurs, res.html, res.contexte)
            for l in inv:
                par_id[l["etat"] if l["etat"] != "rattaché" else l["chiffre_id"]] += 1
            fu = [l for l in inv if l["etat"] == "FUITE"]
            total_fuites += len(fu)
            if "--fuites" in sys.argv and fu:
                print(f"\n== {idu}/{doc} — {len(fu)} fuite(s) sur {len(inv)} nombres")
                for l in fu:
                    print(f"   {l['nombre']:>12g}  « {l['contexte']} »")
    print("\n=== RÉCAP par rattachement ===")
    for k, n in par_id.most_common():
        print(f"  {n:>4}  {k}")
    print(f"\nTOTAL FUITES = {total_fuites}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
