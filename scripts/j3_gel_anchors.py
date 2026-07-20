#!/usr/bin/env python
"""PHASE 0 J3 étape 2 — GEL : ajoute les 84 additions validées au golden, en ANCRES.

Chaque ancre gèle le COUPLE (statut cascade attendu, matrice, tier v2 attendu) + `validation` :
`factuelle` pour les négatives (écartées/exclues — base du gate boussole), `coherence` pour les
positives (ancres de non-régression). Les 32 d'origine sont INCHANGÉS. Lecture DB seule ; écrit
uniquement le golden JSON.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

RUN = "q_v6_m8"
DB = "postgresql://openclaw@localhost:5432/labuse"
GOLDEN = Path("reports/m6-audit/golden/golden-parcelles.json")
PROP = Path("docs/golden/PROPOSITION_GOLDEN_120.md")
MOTIF_LABEL = {"eau": "eau/hydrographie", "zonage_plu_gpu": "zone A/N inconstructible",
               "risques": "PPR/aléa fort", "pente": "pente forte", "surface": "micro-surface",
               "osm_faux_positif": "OSM faux positif", "foncier_public": "foncier public",
               "emprise_lineaire": "emprise linéaire (délaissé)", "emprise_routiere": "emprise routière",
               "prescription_plu": "prescription PLU (ER/EBC)"}
LABEL_MOTIF = {v: k for k, v in MOTIF_LABEL.items()}
NEG_CASCADE = {"exclue", "faux_positif_probable"}


def parse_prop():
    for ln in PROP.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", ln)
        if m:
            idu, commune, tier, motif_lbl, edge = (x.strip() for x in m.groups())
            yield {"idu": idu, "commune": commune, "motif": LABEL_MOTIF.get(motif_lbl),
                   "edge": None if edge == "—" else edge}


def main():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    parcelles = golden["parcelles"]
    conn = psycopg.connect(DB, row_factory=dict_row)
    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")

    n_new = n_fact = n_coh = 0
    for p in parse_prop():
        idu = p["idu"]
        if idu in parcelles:      # ne jamais toucher un existant (32 d'origine)
            continue
        cur.execute("""
            SELECT d.status cascade_status, d.matrice_statut,
                   (d.status IN ('exclue','faux_positif_probable')) etage0, s2.tier tier_v2
            FROM parcels p
            LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label=%(r)s
            LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id=p.idu AND s2.run_id=%(r)s
            WHERE p.idu=%(i)s""", {"r": RUN, "i": idu})
        r = cur.fetchone()
        if not r:
            print("!! absente:", idu)
            continue
        negative = (r["tier_v2"] == "ecartee") or (r["cascade_status"] in NEG_CASCADE)
        validation = "factuelle" if negative else "coherence"
        parcelles[idu] = {
            "anchor": True, "commune": p["commune"], "motif": p["motif"],
            "cascade_status": r["cascade_status"], "matrice_statut": r["matrice_statut"],
            "etage0": bool(r["etage0"]), "tier_v2": r["tier_v2"], "validation": validation,
        }
        n_new += 1
        n_fact += validation == "factuelle"
        n_coh += validation == "coherence"

    golden["meta"]["n_parcelles"] = len(parcelles)
    golden["meta"]["j3_ancres"] = {"ajoutees": n_new, "factuelle": n_fact, "coherence": n_coh,
                                   "format": "couple (cascade_status, matrice_statut, tier_v2) + validation"}
    GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"golden : +{n_new} ancres ({n_fact} factuelle / {n_coh} coherence) → total {len(parcelles)}")
    conn.close()


if __name__ == "__main__":
    main()
