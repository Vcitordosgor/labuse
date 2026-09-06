"""Fiche de règle — événements propriétaire (score V). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("evenements_proprietaire_liste",),
    formule_codee=("Signaux DATÉS assemblés des sources publiques : procédures collectives BODACC, "
                   "radiations/cessations SIRENE, mutations DVF — chaque événement porte sa source "
                   "et sa date (faits publics, jamais une interprétation) ; consommés ensuite par "
                   "le scoring (famille V)."),
    entrees=("bodacc_*", "sirene_etablissements", "dvf_mutations"),
    classe="choix_labuse",
    fonction="src/labuse/ingestion/score_v_fetch.py",
    verdict="choix_assume",
    choix=("La SÉLECTION des types d'événements retenus (procédures, radiations, ventes) est un "
           "choix LABUSE ; chaque fait affiché reste un passe-plat sourcé de sa source."),
    exemple_temoin=None,
    verifie_le="2026-09-06",
))
