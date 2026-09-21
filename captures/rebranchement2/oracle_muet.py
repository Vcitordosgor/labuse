#!/usr/bin/env python
"""DONNEES-4 — SCAN « extracteur muet » par l'oracle indépendant.

Pour chaque ligne du Dossier (extracteur de robinet_fiche.py), on lit la valeur DEUX fois :
· l'EXTRACTEUR (le chemin du Dossier) ;
· l'ORACLE (le chemin où la fiche RÉACT lit la valeur — src/labuse/exports/oracle_dossier.py).
Si l'oracle a une valeur et que l'extracteur renvoie None → « extracteur muet » (l'écart que
`preuve_ecran_pdf.py` ne pouvait pas voir, puisqu'il compare l'extracteur au PDF rendu du même
extracteur). Les lignes rendues par une AUTRE requête que /parcels/{idu} sont hors oracle (déclarées
dans oracle_dossier.HORS_PAYLOAD). Construit le payload en direct (aucun JSON pré-enregistré requis).

Usage : python captures/rebranchement2/oracle_muet.py            (les 4 témoins)
        python captures/rebranchement2/oracle_muet.py <IDU> ...   (parcelles au choix)
"""
import sys

from labuse.db import session_scope
from labuse.api.app import _q_v2_fiche
from labuse.exports import oracle_dossier as O
from labuse.exports.robinet_fiche import EXTRACTEURS, collecte

TEMOINS = ["97410000AN0347", "97422000BO0765", "97415000BO0852", "97411000AB0346"]
PARCELS = sys.argv[1:] or TEMOINS

ids = [c for c in list(O.ORACLE) + list(O.ORACLE_FN) if c in EXTRACTEURS]
muet: dict[str, list[str]] = {}
for idu in PARCELS:
    with session_scope() as db:
        f = _q_v2_fiche(db, idu)
        vals = collecte(db, idu, ids, fiche=f)
    for cid in ids:
        ov = O.valeur_oracle(f, cid)
        if O.present(ov) and vals.get(cid) is None:
            muet.setdefault(cid, []).append(f"{idu[-6:]}={ov!r:.30}")

print(f"Oracle indépendant · {len(ids)} lignes contrôlées · {len(O.HORS_PAYLOAD)} hors-payload déclarées")
print(f"Parcelles : {', '.join(PARCELS)}\n")
if not muet:
    print("EXTRACTEURS MUETS : 0 — aucune ligne où le payload a une valeur et l'extracteur renvoie None.")
    sys.exit(0)
print("EXTRACTEURS MUETS (l'oracle a une valeur, l'extracteur renvoie None) :")
for cid, occ in sorted(muet.items()):
    print(f"  {cid:32s} {occ}")
print(f"\nTOTAL : {len(muet)} extracteur(s) muet(s).")
sys.exit(1)
