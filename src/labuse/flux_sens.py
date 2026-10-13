"""Flux de données — SENS et FOI (décision 13/10).

Règle d'exploitation UNIQUE, pour ne plus jamais mélanger les sens :

- FLUX QUOTIDIENS (BODACC, Sitadel, DPE, SIRENE, DVF) : ingérés EN PROD la nuit par les crons du
  registre (les producteurs publient en continu ; la prod est en ligne 24/7). La **PROD FAIT FOI**
  pour ces tables. Le Mac les **RÉCUPÈRE** de la prod (sens prod→Mac) quand il recalcule.

- SOURCES DE FOND (cadastre, PLU, risques, BAN, couches) : construites/ingérées SUR LE MAC (lourd,
  outillage de calcul), puis **POUSSÉES** en prod (sources-maj-1 / sync-run). Le **MAC FAIT FOI**
  (sens Mac→prod).

Les tables CALCULÉES (scoring p_score_v2/score_labuse, résiduel, cascade, dérivés) restent
Mac→prod via `deploy/scripts/sync-run.sh` : le Mac calcule, le VPS sert.

Exposé par `labuse parite`. Récupération prod→Mac : docs/EXPLOITATION.md §11.
"""
from __future__ import annotations

# flux quotidien → tables brutes écrites par l'ingestion. PROD fait foi. Sens : prod → Mac.
FLUX_QUOTIDIEN_PROD: dict[str, list[str]] = {
    "bodacc": ["bodacc_procedures", "bodacc_depots", "bodacc_sondages"],
    "sitadel": ["sitadel_permits"],
    "dpe": ["dpe_records"],
    "sirene": ["sirene_etablissements"],
    "dvf": ["dvf_mutations"],
}

# source de fond → tables. MAC fait foi. Sens : Mac → prod (sources-maj-1 / sync-run).
SOURCES_FOND_MAC: dict[str, list[str]] = {
    "cadastre": ["parcels", "parcel_cadastre_remplacement"],
    "ban": ["adresses", "adresse_parcelles"],
    "plu": ["parcel_zone_plu"],
    "couches": ["spatial_layers", "parcel_couche_intersection"],
}


def tables_quotidiennes() -> list[str]:
    """Liste à plat des tables des flux quotidiens (prod fait foi)."""
    return [t for tables in FLUX_QUOTIDIEN_PROD.values() for t in tables]


def tables_fond() -> list[str]:
    """Liste à plat des tables de fond (Mac fait foi)."""
    return [t for tables in SOURCES_FOND_MAC.values() for t in tables]
