"""Fiche de règle — portefeuille d'une personne morale (SIREN). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_parcelles_pm",),
    formule_codee=(
        "Délégation : api/modules.py:patrimoine — n_parcelles est le compte du portefeuille complet "
        "du SIREN (jointure parcelle_personne_morale × parcels, millésime servi 2025) ; même "
        "assiette que la liste et le CSV (jamais un count parallèle sur la table brute)."),
    entrees=("parcelle_personne_morale (DGFiP, millésime 2025)", "parcels"),
    classe="choix_labuse",
    fonction="src/labuse/api/modules.py:patrimoine (délégation registre/moteurs/proprietaire.py)",
    verdict="choix_assume",
    choix=("Assiette = parcelles du SIREN PRÉSENTES dans la base servie (jointure parcels) — pas le "
           "fichier DGFiP brut : un droit sur une parcelle hors périmètre ingéré ne compte pas."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_n_parcelles_pm_meme_assiette",
    verifie_le="2026-09-06",
    moteur_fonctions=("proprietaire.compte_parcelles_pm",),
))
