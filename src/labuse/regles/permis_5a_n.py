"""Fiche de règle — comptes de permis Sitadel. CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("permis_5a_n", "permis_12m_n"),
    formule_codee=(
        "permis_5a_n = count(sitadel_permits) de la commune avec date ≥ aujourd'hui − 5 ans "
        "(fenêtre calendaire). permis_12m_n = count(sitadel_permits) de la commune (et du type "
        "s'il est demandé) avec date ≥ dmax − N mois, où dmax = FIN DES DONNÉES (fournie par "
        "l'appelant, pas la date du jour — Sitadel est publié avec retard) ; + sous-compte géocodé "
        "(geom IS NOT NULL)."),
    entrees=("sitadel_permits.date/commune/type/geom",),
    classe="regle_externe",
    fonction="src/labuse/registre/moteurs/commune.py:compte_permis_commune (+ indicateurs_communes pour 5 ans)",
    verdict="partiel",
    reference=Reference(
        titre="SDES — la base de données Sitadel : méthodologie",
        article="définitions (autorisation, mise en chantier/DOC, date réelle)",
        url="https://www.statistiques.developpement-durable.gouv.fr/la-base-de-donnees-sitadel-methodologie",
        version="méthodologie SDES en ligne (consultée 2026-09-06 ; séries « date réelle » DR++)",
        extrait=("« Suite à son autorisation, le pétitionnaire pourra soit démarrer les travaux et "
                 "déclarer l'ouverture de son chantier (DOC) » ; « Les séries estimées en date "
                 "réelle visent à retracer dès le mois suivant les autorisations et les mises en "
                 "chantier à la date réelle de l'événement »."),
        lu_le="2026-09-06"),
    ecart=("QUESTION D'INGESTION, DITE : la colonne locale sitadel_permits.date n'est pas tracée "
           "« date réelle » vs « date de prise en compte » (les deux existent chez le SDES) — à "
           "confirmer à l'ingestion et à documenter au réservoir. Les COMPTES eux-mêmes sont de "
           "simples fenêtres sur cette date."),
    choix=("Fenêtre 12 mois ancrée sur la fin des données (pas calendaire) : choix LABUSE "
           "d'honnêteté sur une source publiée avec retard."),
    exemple_temoin="tests/regles/test_permis_fenetres.py::test_compte_fenetre_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.compte_permis_commune",),
))
