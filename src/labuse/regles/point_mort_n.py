"""Fiche de règle — « point mort » (permis autorisés jamais concrétisés). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("point_mort_n",),
    formule_codee=(
        "count(DISTINCT permis PC) de la commune tels que : date < aujourd'hui − N mois, "
        "raw->>'daact' IS NULL (aucune déclaration d'achèvement), ET la parcelle du permis est "
        "toujours NON bâtie au run servi (aucun HARD_EXCLUDE de la couche 'bati' dans "
        "dryrun_cascade_results du run). Jointure permis→parcelles par idu_codes."),
    entrees=("sitadel_permits (type PC, date, raw->daact, idu_codes)",
             "dryrun_cascade_results (couche bati, run servi)", "dryrun_parcel_evaluations"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:permis_point_mort",
    verdict="choix_assume",
    choix=(
        "« Point mort » n'est PAS une définition SDES : c'est une définition LABUSE explicite "
        "(mandat CIRCUIT-4, attendu Sitadel) — permis autorisé + pas de DAACT + parcelle toujours "
        "nue au run servi. Le mot est à nous ; Sitadel définit « autorisé/commencé/terminé », pas "
        "« mort ». Fenêtre paramétrée par l'appelant."),
    exemple_temoin="tests/regles/test_point_mort.py::test_point_mort_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.permis_point_mort",),
))
