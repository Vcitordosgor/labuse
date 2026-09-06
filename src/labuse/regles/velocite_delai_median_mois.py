"""Fiche de règle — vélocité administrative (délai médian dépôt→autorisation). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("velocite_delai_median_mois",),
    formule_codee=(
        "Médiane (percentile_cont(0.5), interpolation linéaire PostgreSQL) de delai_mois sur "
        "m10_permit_delais WHERE valide AND famille = 'logements' AND delai_mois >= 0, par commune. "
        "La même requête (_SQL_INDICATEURS) porte aussi le déficit SRU = max(objectif_pct − taux_lls, 0) "
        "et la pression ZAN = conso_2021_2024_m2 ÷ 10 000 (ha)."),
    entrees=("m10_permit_delais.delai_mois (valide, famille=logements)",
             "commune_contexte_sru.objectif_pct/taux_lls", "commune_conso_enaf.conso_2021_2024_m2"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/commune.py:indicateurs_communes",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_velocite_delai_median.py::test_mediane_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.indicateurs_communes",),
))
