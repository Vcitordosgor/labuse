"""Fiche de règle — permis Sitadel : profils de proximité et historique. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_permis_proximite", "depots_secteur_n", "historique_permis_liste"),
    formule_codee=(
        "n_permis_proximite = count(sitadel_permits) dans le rayon 500 m, fenêtre 24 mois (LE "
        "profil client, arbitrage Q7, paramètres TRANSMIS au front). depots_secteur_n = dépôts de "
        "la section cadastrale (préfixe IDU 10), fenêtre 36 mois (DEPOTS_FENETRE_MOIS). "
        "historique_permis_liste = permis déposés/autorisés SUR la parcelle + caducité, chaque "
        "ligne datée."),
    entrees=("sitadel_permits (date, type, geom, idu_codes)",),
    classe="regle_externe",
    fonction="src/labuse/marche_service.py:permits",
    verdict="reference_introuvable",
    choix=("Rayon 500 m / fenêtres 24 et 36 mois : conventions LABUSE de profil (déclarées, "
           "transmises au front) ; les ÉTATS des permis (autorisé, commencé, annulé) sont les "
           "définitions SDES/Sitadel (lot 2)."),
    exemple_temoin="tests/regles/test_permis_fenetres.py::test_rayon_et_fenetre_profil",
    verifie_le="2026-09-06",
))
