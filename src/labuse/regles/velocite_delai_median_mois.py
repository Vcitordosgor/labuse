"""Fiche de règle — vélocité administrative (délai médian), RETIRÉE (OUTIL-PERMIS-FIX-8). CIRCUIT-4.

La fiche est conservée pour tracer la décision et COUVRIR `indicateurs_communes` (qui produit encore
le déficit SRU et la pression ZAN). Le délai lui-même n'est plus ni calculé ni servi."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("velocite_delai_median_mois",),
    formule_codee=(
        "RETIRÉ (OUTIL-PERMIS-FIX-8, LOT 3) — la vélocité (délai médian dépôt→autorisation) n'est PLUS "
        "ni calculée ni servie : le dépôt n'est connu qu'à l'année (AN_DEPOT → 1er janvier), le délai "
        "n'a jamais été mesuré, et l'axe sort du score composite ; la couche m10_permit_delais est "
        "décommissionnée. Règle historique (trace) : médiane percentile_cont(0.5) de delai_mois sur "
        "m10_permit_delais valide/logements. La requête `indicateurs_communes` (_SQL_INDICATEURS) porte "
        "ENCORE le déficit SRU = max(objectif_pct − taux_lls, 0) — objectif loi SRU (25 %/20 % des "
        "résidences principales, DHUP) — et la pression ZAN = conso_2021_2024_m2 ÷ 10 000 (ha, Cerema ENAF)."),
    entrees=("commune_contexte_sru.objectif_pct/taux_lls (DHUP)", "commune_conso_enaf (Cerema)",
             "— (ex-m10_permit_delais.delai_mois : retiré, couche décommissionnée)"),
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
