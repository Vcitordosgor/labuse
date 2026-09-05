#!/usr/bin/env python3
"""CIRCUIT-0 Lot 6 — VALIDE circuit.json (lecture seule). Vérifie :
  1. tous les ids référencés par les arêtes existent (réservoirs, chiffres, robinets) ;
  2. chaque chiffre a ≥ 1 réservoir (ou labuse_interne) et ≥ 1 robinet ;
  3. les moteurs référencés par les chiffres existent ;
  4. les tailles des listes égalent les compteurs des CSV sources (règle 2 du mandat).
Sort avec un code ≠ 0 au premier écart. Aucune écriture.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire"

erreurs: list[str] = []


def err(msg: str) -> None:
    erreurs.append(msg)


def n_csv(nom: str) -> int:
    with (INV / nom).open(encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f, delimiter=";"))


def main() -> int:
    c = json.loads((INV / "circuit.json").read_text(encoding="utf-8"))
    res = {r["id"] for r in c["reservoirs"]}
    mot = {m["id"] for m in c["moteurs"]}
    chi = {x["id"] for x in c["chiffres"]}
    rob = {r["id"] for r in c["robinets"]}

    for rid, cid in c["aretes"]["reservoir_vers_chiffre"]:
        if rid not in res:
            err(f"arête réservoir→chiffre : réservoir inconnu {rid}")
        if cid not in chi:
            err(f"arête réservoir→chiffre : chiffre inconnu {cid}")
    for cid, rid in c["aretes"]["chiffre_vers_robinet"]:
        if cid not in chi:
            err(f"arête chiffre→robinet : chiffre inconnu {cid}")
        if rid not in rob:
            err(f"arête chiffre→robinet : robinet inconnu {rid}")
    for f in c["aretes"]["fuites"]:
        rid, robid, cid = f[0], f[1], f[2]
        if rid not in res:
            err(f"fuite : réservoir inconnu {rid}")
        if robid not in rob:
            err(f"fuite : robinet inconnu {robid}")
        if cid not in chi:
            err(f"fuite : chiffre inconnu {cid}")

    avec_res = {cid for _, cid in c["aretes"]["reservoir_vers_chiffre"]}
    avec_rob = {cid for cid, _ in c["aretes"]["chiffre_vers_robinet"]}
    for cid in sorted(chi - avec_res):
        err(f"chiffre sans réservoir : {cid}")
    for cid in sorted(chi - avec_rob):
        err(f"chiffre sans robinet : {cid}")
    for x in c["chiffres"]:
        if x["moteur"] and x["moteur"] not in mot:
            err(f"chiffre {x['id']} : moteur inconnu {x['moteur']}")

    # compteurs = tailles des listes = lignes des CSV sources
    attendus = {
        "reservoirs": (len(c["reservoirs"]), n_csv("reservoirs.csv") + 1),   # +1 labuse_interne
        "moteurs": (len(c["moteurs"]), n_csv("moteurs.csv")),
        "robinets": (len(c["robinets"]), n_csv("robinets.csv")),
    }
    for nom, (taille, csv_n) in attendus.items():
        if taille != csv_n:
            err(f"compteur {nom} : liste={taille} ≠ csv={csv_n}")
    cids_csv = set()
    with (INV / "chiffres.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            cids_csv.add(row["chiffre_id"])
    if len(chi) != len(cids_csv):
        err(f"compteur chiffres : graphe={len(chi)} ≠ ids distincts csv={len(cids_csv)}")

    if erreurs:
        print(f"ÉCHEC — {len(erreurs)} problème(s) :")
        for e in erreurs:
            print(" ·", e)
        return 1
    print(f"OK — {len(res)} réservoirs, {len(mot)} moteurs, {len(chi)} chiffres, {len(rob)} robinets ; "
          f"{len(c['aretes']['reservoir_vers_chiffre'])} + {len(c['aretes']['chiffre_vers_robinet'])} arêtes, "
          f"{len(c['aretes']['fuites'])} fuites ; compteurs = tailles des CSV.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
