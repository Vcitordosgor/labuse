"""Fiche de règle — compteurs de sources de la plateforme. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_sources", "n_sources_surveillees"),
    formule_codee=("n_sources = count(data_sources) sous le prédicat canonique WHERE_AFFICHEES "
                   "(statut connecte/manuel, non doublon/retirée/dormante/masquée/désactivée) — "
                   "sources_catalog, LA définition partagée par la page et l'accueil ; "
                   "n_sources_surveillees = count(source_veille actives à vraie sonde "
                   "api/page/entete/temoin)."),
    entrees=("data_sources", "source_veille"),
    classe="choix_labuse",
    fonction="src/labuse/flux.py:construire_flux (périmètre sources_catalog.WHERE_AFFICHEES)",
    verdict="choix_assume",
    choix="Le périmètre « affichées » est le prédicat canonique unique (FIX-SOURCES S1).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_n_sources_perimetre",
    verifie_le="2026-09-06",
))
