"""Fiche de règle — RPG et zone agricole (canne, friche possible). SOURCES-1 lot 2."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("rpg_couche",),
    formule_codee=(
        "Parcelle ∩ kind='safer' (déclarations RPG, attrs.code_cultu) croisée avec la zone "
        "PLU : en zone A (préfixe A strict, AU exclu, part ≥ 50 %), Σ couverture des "
        "déclarations CSA ≥ canne_hard_pct (50 %) → RÉDHIBITOIRE « sole cannière "
        "exploitée » ; zone A SANS déclaration RPG → VIGILANCE moyenne « friche agricole "
        "possible » (signal, pas une preuve) ; sinon flag moyen inchangé, culture déclarée "
        "citée."),
    entrees=("spatial_layers (kind=safer : attrs->code_cultu, coverage)",
             "spatial_layers (kind=plu_gpu_zone : name)",
             "config/cascade_rules.yaml (safer : canne_codes, canne_hard_pct, zone_a_prefixes)"),
    classe="choix_labuse",
    fonction="src/labuse/cascade/layers/phase1.py:SaferLayer ; ingestion/layers_ingest.py:ingest_rpg_agricole",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 lot 2 : « zone A cultivée en canne → RÉDHIBITOIRE, zone A absente "
        "du RPG → VIGILANCE friche possible ». Choix LABUSE : canne = code RPG CSA (12 464 "
        "déclarations 974, dominant vérifié en base) ; seuil 50 % de couverture parcelle, non "
        "calibré par une mesure (une parcelle majoritairement en sole cannière déclarée n'a "
        "pas de perspective de mutation — la défiscalisation sucrière et le fermage verrouillent). "
        "Variable candidate scoring (part RPG canne / friche possible) NOTÉE pour le banc K0, "
        "jamais branchée sans banc."),
    exemple_temoin="tests/test_sources1_lot2.py::test_rpg_canne_zone_a",
    verifie_le="2026-09-07",
))
