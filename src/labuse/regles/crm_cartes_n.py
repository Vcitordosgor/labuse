"""Fiche de règle — cartes du pipeline (CRM) par colonne. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("crm_cartes_n", "pipeline_entrees_n"),
    formule_codee=("n(statut) = count(pipeline_entries WHERE compte_id IS NOT DISTINCT FROM :cid) "
                   "GROUP BY status — périmètre du compte (NULL = pilote)."),
    entrees=("pipeline_entries (status, compte_id)",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:cartes_par_colonne",
    verdict="choix_assume",
    choix="Périmètre strict du compte (IS NOT DISTINCT FROM : le pilote voit les siennes, NULL).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_cartes_par_colonne",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.cartes_par_colonne",),
))
