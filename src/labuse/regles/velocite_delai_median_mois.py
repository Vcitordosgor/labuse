"""Fiche de règle — vélocité administrative (délai médian). CIRCUIT-4 (lot 2/3)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("velocite_delai_median_mois",),
    formule_codee=(
        "Médiane (percentile_cont(0.5), interpolation linéaire) de delai_mois sur m10_permit_delais "
        "WHERE valide AND famille = 'logements' AND delai_mois >= 0, par commune. La même requête "
        "(_SQL_INDICATEURS) porte aussi le déficit SRU = max(objectif_pct − taux_lls, 0) — "
        "l'objectif étant celui de la loi SRU (25 %/20 % des résidences principales, données DHUP) "
        "— et la pression ZAN = conso_2021_2024_m2 ÷ 10 000 (ha, Cerema ENAF)."),
    entrees=("m10_permit_delais.delai_mois (valide, famille=logements)",
             "commune_contexte_sru.objectif_pct/taux_lls (DHUP)", "commune_conso_enaf (Cerema)"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/commune.py:indicateurs_communes",
    verdict="conforme",
    reference=Reference(
        titre="PostgreSQL — fonctions d'agrégat à ensemble ordonné (percentile_cont) ; "
              "CCH art. L302-5 (SRU) pour la colonne déficit",
        article="documentation PostgreSQL, Ordered-Set Aggregate Functions ; L302-5",
        url="https://www.postgresql.org/docs/current/functions-aggregate.html",
        version="PostgreSQL docs current (consultée 2026-09-06) ; L302-5 version en vigueur 2022",
        extrait=("percentile_cont : « Computes the continuous percentile, a value corresponding to "
                 "the specified fraction within the ordered set of aggregated argument values. "
                 "This will interpolate between adjacent input items if needed. » L302-5 (CCH) : "
                 "obligation d'au moins 25 % de logements locatifs sociaux parmi les résidences "
                 "principales (20 % dans les territoires où la pression sur le logement social est "
                 "sous un seuil fixé par décret)."),
        lu_le="2026-09-06"),
    exemple_temoin="tests/regles/test_velocite_delai_median.py::test_mediane_temoin",
    valide_par="cc",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.indicateurs_communes",),
))
