"""Fiche de règle — usage par outil. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("usage_outil_n",),
    formule_codee=("n = count(usage_events WHERE kind='outil' AND outil IS NOT NULL AND ts > now() − "
                   "fenêtre) GROUP BY outil, tri décroissant ; fenêtre ∈ {7, 30, 90} jours."),
    entrees=("usage_events (kind, outil, ts)",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:usage_par_outil",
    verdict="choix_assume",
    choix="Un « usage » = un événement d'ouverture d'outil émis par le front (capteur usage_events).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_usage_par_outil",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.usage_par_outil",),
))
