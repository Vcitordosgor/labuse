"""Fiche de règle — permis Sitadel : profils de proximité. CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

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
    verdict="partiel",
    reference=Reference(
        titre="SDES — la base de données Sitadel : méthodologie",
        article="définitions (autorisation, DOC, date réelle)",
        url="https://www.statistiques.developpement-durable.gouv.fr/la-base-de-donnees-sitadel-methodologie",
        version="méthodologie SDES en ligne (consultée 2026-09-06)",
        extrait=("« Suite à son autorisation, le pétitionnaire pourra soit démarrer les travaux et "
                 "déclarer l'ouverture de son chantier (DOC) » — les états servis (déposé, "
                 "autorisé, DOC, DAACT) sont ceux du formulaire Sitadel."),
        lu_le="2026-09-06"),
    ecart=("Même question d'ingestion que permis_5a_n (date réelle vs prise en compte, non tracée "
           "en base) ; les fenêtres/rayons sont des conventions LABUSE déclarées."),
    choix=("Rayon 500 m / fenêtres 24 et 36 mois : conventions LABUSE de profil (déclarées, "
           "transmises au front)."),
    exemple_temoin="tests/regles/test_permis_fenetres.py::test_rayon_et_fenetre_profil",
    verifie_le="2026-09-06",
))
