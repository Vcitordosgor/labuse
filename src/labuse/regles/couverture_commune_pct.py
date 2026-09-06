"""Fiche de règle — chiffres de couverture de la plateforme. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("couverture_commune_pct",),
    formule_codee=(
        "Compteurs de couverture lus des données réelles : parcelles = count(parcels) ; communes = "
        "count(DISTINCT commune) ; dvf = count(dvf_mutations) ; radar = count(pige_biens) ; run "
        "servi + date. Chaque valeur est gardée : table absente → null, jamais un chiffre inventé. "
        "communes_total = 24 (référentiel de La Réunion, constante)."),
    entrees=("parcels", "dvf_mutations", "pige_biens", "p_score_v2_runs"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:couverture_sources",
    verdict="choix_assume",
    choix=("Périmètre d'affichage marketing honnête : les comptes de la base SERVIE, datés du run — "
           "pas des chiffres de communication figés."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_couverture_nulls_gardes",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.couverture_sources",),
))
