"""Fiche de règle — parcelles de l'île (run servi). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_parcelles_ile",),
    formule_codee=(
        "n = p_score_v2_runs.n_parcelles du run servi (registre du run, lecture par clé primaire) ; "
        "repli count(parcel_p_score_v2 du run) si le registre ne connaît pas le run ; indisponible "
        "→ null (jamais une invention, jamais un chiffre en dur)."),
    entrees=("p_score_v2_runs.n_parcelles", "parcel_p_score_v2 (repli)"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:compte_parcelles_ile",
    verdict="choix_assume",
    choix=("Le chiffre affiché est celui du RUN SERVI (mesuré à la bascule), pas un count vif : "
           "l'accueil ne bouge pas entre deux bascules (RETOURS-10 T2)."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_n_parcelles_ile_registre",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.compte_parcelles_ile",),
))
