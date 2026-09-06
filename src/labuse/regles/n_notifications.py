"""Fiche de règle — notifications non lues. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_notifications",),
    formule_codee=("n = count(event_log e WHERE _visible(e) AND NOT _seen(e)) du compte — les "
                   "fragments de visibilité/lecture (_visible/_seen) restent chez api/events.py "
                   "(une sémantique, deux lecteurs : liste et compteur, même requête)."),
    entrees=("event_log", "event_seen (lectures par compte)"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:notifications_non_lues",
    verdict="choix_assume",
    choix="Visibilité = sémantique applicative events.py (kinds marché, cloison par compte).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_notifications_meme_semantique",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.notifications_non_lues",),
))
