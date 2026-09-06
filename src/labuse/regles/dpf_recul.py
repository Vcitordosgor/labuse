"""Fiche de règle — servitude de marchepied du domaine public fluvial. SOURCES-1 lot 2."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("dpf_couche",),
    formule_codee=(
        "Distance min (m, EPSG:2975) de la parcelle aux entités kind='dpf' (Cours_d_eau_DPF "
        "275 tronçons + Plan_d_eau_DPF 6, DEAL Carmen) ; d ≤ marchepied_m (3,25) → "
        "RÉDHIBITOIRE (bande grevée d'un passage public, lit domanial inaliénable). La bande "
        "de 10 m (code forestier R.174-2, ravines pente > 27°) est portée par la couche "
        "`ravine` (BD TOPO, toutes les ravines) — anti-double-compte."),
    entrees=("spatial_layers (kind=dpf : subtype cours_eau/plan_eau, attrs toponyme/classe)",
             "config/cascade_rules.yaml (dpf : marchepied_m, search_cap_m)"),
    classe="regle_externe",
    fonction="src/labuse/cascade/layers/phase1.py:DpfLayer ; ingestion/deal_carmen.py",
    verdict="conforme",
    reference=Reference(
        titre="Code général de la propriété des personnes publiques", article="art. L2131-2",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031065981",
        version="en vigueur depuis le 19/08/2015",
        extrait=("« Les propriétaires riverains d'un cours d'eau ou d'un lac domanial ne "
                 "peuvent planter d'arbres ni se clore par haies ou autrement qu'à une "
                 "distance de 3,25 mètres. Leurs propriétés sont grevées sur chaque rive de "
                 "cette dernière servitude de 3,25 mètres, dite servitude de marchepied. »"),
        lu_le="2026-09-07"),
    exemple_temoin="tests/test_sources1_lot2.py::test_dpf_marchepied",
    verifie_le="2026-09-07",
))
