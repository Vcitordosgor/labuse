"""Fiche de règle — état du corpus PLU (servable / RNU / révision / non ingéré). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_extraits_plu", "n_communes_rnu", "n_procedures_plu"),
    formule_codee=(
        "Par commune du référentiel : statut = servable (extraits ingérés, idurba réconcilié) · rnu "
        "(registre config/rnu_communes.yaml) · revision (opposabilité en attente GPU) · non_ingere. "
        "Compteurs CALCULÉS par somme des statuts (jamais par soustraction) ; invariant : servables "
        "+ n_revision + n_rnu + n_non_ingere = n_communes. Les procédures ACTIVES viennent du "
        "registre veille_plu (source unique, RETOURS-12 O4) : n_procedures = count(communes à "
        "procédure active), ventilé par type."),
    entrees=("corpus PLU ingéré (plu_ingest.corpus_status)", "config/rnu_communes.yaml",
             "veille_plu (radar Sudocuh)"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:etat_corpus_plu",
    verdict="choix_assume",
    choix=("Le RNU (absence de PLU) n'est jamais compté « en révision » ; on ne sert pas un "
           "règlement non réconcilié (garde idurba+sha). Ce sont des règles d'inventaire LABUSE, "
           "pas une définition externe."),
    exemple_temoin="tests/regles/test_corpus_plu.py::test_invariant_somme_statuts",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.etat_corpus_plu",),
))
