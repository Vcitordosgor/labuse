"""Fiche de règle — enveloppe ZAN restante estimée. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("zan_reste_ha",),
    formule_codee=(
        "Délégation : le calcul vit dans api/rarete.py:compute_rarete (une seule vérité). Enveloppe "
        "restante estimée depuis la consommation ENAF observée (commune_conso_enaf, Cerema "
        "2021-2024) rapportée à la trajectoire de réduction ZAN. La pression ZAN du comparateur = "
        "conso_2021_2024_m2 ÷ 10 000 (ha)."),
    entrees=("commune_conso_enaf.conso_2021_2024_m2 (Cerema, portail artificialisation)",),
    classe="regle_externe",
    fonction="src/labuse/api/rarete.py:compute_rarete (délégation commune_compteurs)",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_pression_zan_conversion_ha",
    verifie_le="2026-09-06",
))
