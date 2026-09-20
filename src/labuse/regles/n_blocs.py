"""Fiche de règle — outil « Blocs fonciers » (M29). CIRCUIT-4 / OUTILS-FIX-5 L6."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_blocs_pm", "n_parcelles_bloc"),
    formule_codee=("Assiettes contiguës d'un MÊME propriétaire personne morale (SIREN) : arêtes "
                   "ST_DWithin(geom_2975, 0,5 m) BORNÉES au même SIREN, composantes par union-find, "
                   "bloc = ≥ 2 parcelles (tables parcel_blocs / parcel_bloc_membres, batch blocs-build). "
                   "n_blocs_pm = count des blocs (île ou commune) ; n_parcelles_bloc = membres d'un "
                   "bloc ; résiduel agrégé = somme parcel_residuel de la vue servie, épinglée au bloc."),
    entrees=("parcel_blocs", "parcel_bloc_membres", "parcelle_personne_morale",
             "parcel_residuel (vue servie)"),
    classe="choix_labuse",
    fonction="src/labuse/blocs.py:build_blocs ; src/labuse/api/modules.py:blocs_liste",
    verdict="choix_assume",
    choix=("« Bloc foncier » = définition LABUSE d'une assiette d'un même propriétaire PM (0,5 m de "
           "contiguïté, ≥ 2 parcelles) — ce qu'un promoteur ne voit pas parcelle par parcelle. "
           "Personnes morales SEULEMENT (les particuliers n'ont pas d'identité stable d'une parcelle "
           "à l'autre) ; publics écartés par défaut (OUTILS-MUSCLER-3)."),
    exemple_temoin="tests/regles/test_outils_fix5_temoins.py::test_n_blocs_pm",
    valide_par="en_attente",
    verifie_le="2026-09-20",
))
