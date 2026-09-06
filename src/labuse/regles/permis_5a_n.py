"""Fiche de règle — comptes de permis Sitadel par commune (fenêtres 5 ans / 12 mois). CIRCUIT-4."""
from . import FicheRegle, declarer

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
    verdict="reference_introuvable",
    choix=("Fenêtre 12 mois ancrée sur la fin des données (pas calendaire) : choix LABUSE d'honnêteté "
           "sur une source publiée avec retard — la fenêtre calendaire sous-compterait."),
    exemple_temoin="tests/regles/test_permis_fenetres.py::test_compte_fenetre_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.compte_permis_commune",),
))
