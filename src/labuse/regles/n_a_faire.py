"""Fiche de règle — gestes attendus (sources). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_a_faire",),
    formule_codee=("Délégation : etats_sources.compteurs sur lister_etats — n = nouvelles versions à "
                   "injecter + sources à rafraîchir (arbitre d'état unique des sources)."),
    entrees=("data_sources", "source_veille"),
    classe="choix_labuse",
    fonction="src/labuse/etats_sources.py:compteurs (délégation plateforme_compteurs)",
    verdict="choix_assume",
    choix="Un « geste attendu » = un état de source qui appelle un clic (arbitre unique RETOURS-8 R1).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_n_a_faire_arbitre",
    verifie_le="2026-09-06",
))
