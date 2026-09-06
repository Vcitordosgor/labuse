"""Fiche de règle — compteurs de projet. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("projet_cadrage_n", "projet_retenues_n"),
    formule_codee="Délégation : api/projets.py:_counts_by_projet — parcelles du projet / retenues, par projet.",
    entrees=("projets, projet_parcelles",),
    classe="choix_labuse",
    fonction="src/labuse/api/projets.py:_counts_by_projet (délégation plateforme_compteurs)",
    verdict="choix_assume",
    choix="Comptes bruts par appartenance au projet (statut retenu = décision client).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_compteurs_delegues_existent",
    verifie_le="2026-09-06",
))
