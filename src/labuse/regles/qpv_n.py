"""Fiche de règle — QPV intersectant la commune. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("qpv_n",),
    formule_codee=("Liste (puis compte) des QPV de spatial_layers kind='qpv' rattachés à la commune "
                   "(colonne commune de la couche), nom + code_qp, tri par nom."),
    entrees=("spatial_layers (kind=qpv, name, attrs->code_qp, commune)",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:qpv_commune",
    verdict="choix_assume",
    choix=("Le périmètre QPV lui-même est réglementaire (décret QPV 2024, ANCT — passe-plat de la "
           "couche) ; le COMPTE par commune est un simple rattachement LABUSE via la colonne "
           "commune de l'ingestion."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_qpv_commune",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.qpv_commune",),
))
