"""Fiche de règle — score composite du comparateur des 24 communes. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("comparateur_composite",),
    formule_codee=(
        "Normalisation min-max de chaque indicateur présent sur [0;100] selon sa direction "
        "(direction −1 → 1−frac), avec frac = (v − min) ÷ (max − min) sur les 24 communes ; borne "
        "dégénérée (max = min) → 50 neutre. Composite = Σ(poids_k × norm_k) ÷ Σ(poids des axes "
        "PRÉSENTS) — renormalisation pour ne pas pénaliser une donnée manquante — arrondi 0,1 ; "
        "rang = tri décroissant."),
    entrees=("indicateurs_communes (stock, velocite, permis, deficit_sru, pression_zan, prix_neuf)",
             "poids (réglables, défauts INDICATEURS)"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/commune.py:composite_communes",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_comparateur_composite.py::test_composite_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.composite_communes",),
))
