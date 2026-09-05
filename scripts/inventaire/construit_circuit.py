#!/usr/bin/env python3
"""CIRCUIT-0 Lot 6 — construit docs/CIRCUIT/inventaire/circuit.json À PARTIR des CSV des
lots 1, 2, 4, 5 (jamais à la main). Les chiffres dont la matière est une table interne
LABUSE (event_log, projets, comptes, veilles, pipeline, ia_log, config) sont raccordés au
pseudo-réservoir `labuse_interne` (déclaré, famille `interne`) pour que la règle « chaque
chiffre a ≥ 1 réservoir » reste vérifiable sans mentir sur l'amont.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

INV = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire"
OUT = INV / "circuit.json"


def lire(nom: str) -> list[dict]:
    with (INV / nom).open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main() -> None:
    reservoirs = lire("reservoirs.csv")
    moteurs = lire("moteurs.csv")
    robinets = lire("robinets.csv")
    chiffres = lire("chiffres.csv")

    res_ids = {r["id"] for r in reservoirs}
    j_res = [{"id": r["id"], "nom": r["nom_affiche"], "famille": r["famille"],
              "mode_remplissage": r["mode_remplissage"], "millesime_servi": r["millesime_servi"],
              "sentinelle": r["sentinelle"] == "oui"} for r in reservoirs]
    j_res.append({"id": "labuse_interne", "nom": "Tables internes LABUSE (event_log, comptes, projets…)",
                  "famille": "interne", "mode_remplissage": "derivee", "millesime_servi": "",
                  "sentinelle": False})
    res_ids.add("labuse_interne")

    j_mot = [{"id": m["id"], "nom": m["nom"], "fichier": m["fichier"]} for m in moteurs]
    mot_ids = {m["id"] for m in j_mot}
    j_rob = [{"id": r["id"], "nom": r["nom_affiche"], "categorie": r["categorie"],
              "parent": r["parent"] or None} for r in robinets]
    rob_ids = {r["id"] for r in j_rob}

    # chiffres : un nœud par chiffre_id (libellé de la 1re occurrence), moteur si calcul=moteur:x
    par_chiffre: dict[str, dict] = {}
    r2c: set[tuple[str, str]] = set()      # reservoir → chiffre
    c2r: set[tuple[str, str]] = set()      # chiffre → robinet
    for row in chiffres:
        cid = row["chiffre_id"]
        if cid not in par_chiffre:
            m = re.match(r"moteur:(\S+)", row["calcul"])
            par_chiffre[cid] = {"id": cid, "libelle": row["libelle_affiche"], "unite": row["unite"],
                                "niveau": row["niveau"], "moteur": m.group(1) if m else None}
        c2r.add((cid, row["robinet_id"]))
        matiere = row["reservoirs_lus"].strip()
        trouve = False
        for tok in re.split(r"[,;]\s*", matiere):
            tok = tok.strip()
            if tok in res_ids:
                r2c.add((tok, cid))
                trouve = True
        if not trouve:
            r2c.add(("labuse_interne", cid))    # matière interne ou pseudo (parenthésée)

    fuites = [
        ["gpu_plu_api_carto", "fiche_commune_zonage", "part_zone_A_pct", "src/labuse/api/app.py:2436"],
        ["gpu_plu_api_carto", "fiche_commune_zonage", "part_zone_N_pct", "src/labuse/api/app.py:2436"],
        ["labuse_interne", "admin_flux_circuit", "n_sources", "src/labuse/flux.py:198"],
        ["dvf", "fiche_parcelle_marche", "prix_neuf_vefa_eur_m2", "src/labuse/ingestion/score_e.py:59"],
    ]

    circuit = {
        "run_servi": "q_v11_m137",
        "reservoirs": j_res,
        "moteurs": j_mot,
        "chiffres": sorted(par_chiffre.values(), key=lambda c: c["id"]),
        "robinets": j_rob,
        "aretes": {
            "reservoir_vers_chiffre": sorted([list(x) for x in r2c]),
            "chiffre_vers_robinet": sorted([list(x) for x in c2r]),
            "fuites": fuites,
        },
    }
    OUT.write_text(json.dumps(circuit, ensure_ascii=False, indent=1), encoding="utf-8")

    # Q6.1 — table d'impact par réservoir (imprimée pour le rapport).
    imp_c: dict[str, set] = defaultdict(set)
    imp_r: dict[str, set] = defaultdict(set)
    rob_par_chiffre: dict[str, set] = defaultdict(set)
    for cid, rob in c2r:
        rob_par_chiffre[cid].add(rob)
    for res, cid in r2c:
        imp_c[res].add(cid)
        imp_r[res] |= rob_par_chiffre[cid]
    print(f"circuit.json : {len(j_res)} réservoirs, {len(j_mot)} moteurs, "
          f"{len(par_chiffre)} chiffres, {len(j_rob)} robinets, "
          f"{len(r2c)}+{len(c2r)} arêtes, {len(fuites)} fuites")
    print("\nIMPACT PAR RÉSERVOIR (chiffres | robinets touchés) — trié par impact :")
    for res in sorted(imp_c, key=lambda k: -len(imp_r[k])):
        if res == "labuse_interne":
            continue
        print(f"  {res}: {len(imp_c[res])} chiffres | {len(imp_r[res])} robinets → "
              f"{', '.join(sorted(imp_r[res])[:8])}{'…' if len(imp_r[res]) > 8 else ''}")


if __name__ == "__main__":
    main()
