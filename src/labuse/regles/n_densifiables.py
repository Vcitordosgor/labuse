"""Fiche de règle — segment « renouvellement urbain ». CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_densifiables", "densifier_couche"),
    formule_codee=("Parcelles BÂTIES à capacité résiduelle (agrégation des verdicts cascade + "
                   "résiduel du run servi → parcel_renouvellement, reconstruit à la bascule) ; "
                   "n = count au run servi, la couche peint le segment."),
    entrees=("dryrun_cascade_results", "parcel_residuel", "parcel_renouvellement (run servi)"),
    classe="choix_labuse",
    fonction="src/labuse/renouvellement.py",
    verdict="choix_assume",
    choix=("« Densifiable » = définition LABUSE de segment (bâti + résiduel positif + non exclu "
           "cascade) — un angle de lecture du stock, pas une qualification réglementaire."),
    exemple_temoin="tests/regles/test_cascade_compteurs.py::test_segment_renouvellement",
    verifie_le="2026-09-06",
))
