"""Fiche de règle — statut du document d'urbanisme d'une commune. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("statut_plu",),
    formule_codee=("Préséance : RNU (registre config/rnu_communes.yaml — Saint-Philippe) l'emporte ; "
                   "sinon statut du registre veille_plu (radar Sudocuh : PLU opposable, révision, "
                   "élaboration). Une lecture d'inventaire, pas un calcul."),
    entrees=("config/rnu_communes.yaml", "veille_plu (Sudocuh)"),
    classe="choix_labuse",
    fonction="src/labuse/veille_plu.py (+ registre RNU)",
    verdict="choix_assume",
    choix=("La préséance RNU-d'abord est une règle d'affichage LABUSE : l'ABSENCE de PLU prime tout "
           "statut de procédure (une élaboration en cours ne rend pas un règlement opposable)."),
    exemple_temoin="tests/regles/test_corpus_plu.py::test_rnu_prime",
    verifie_le="2026-09-06",
))
