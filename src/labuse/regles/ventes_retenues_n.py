"""Fiche de règle — comparables DVF : filtre + profils. CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("ventes_retenues_n", "ventes_ecartees_n", "dvf_parcelle_liste", "voisinage_100m_liste",
             "ventes_100m_n"),
    formule_codee=(
        "filtre_ventes (marche_service) : chaque vente DVF est RETENUE ou ÉCARTÉE AVEC MOTIF "
        "(nature de mutation hors vente, prix nul, surface nulle, hors bornes de bon sens, doublon "
        "multi-parcelles) — la couverture est VISIBLE (n retenues + n écartées + motifs, EXPORTS-1 "
        "lot 2). Profils déclarés (config/dvf_profils.yaml) : voisinage_100m = ventes + permis 36 "
        "mois dans un buffer de 100 m, site exclu (doctrine M38) ; dvf_parcelle_liste = dernière "
        "mutation de la parcelle + médianes du secteur cadastral (indicateur secondaire étiqueté)."),
    entrees=("dvf_mutations_parcelle (nature, prix, surfaces, geom)", "config/dvf_profils.yaml"),
    classe="regle_externe",
    fonction="src/labuse/marche_service.py:filtre_ventes (+ profils)",
    verdict="conforme",
    reference=Reference(
        titre="DGFiP — jeu de données « Demandes de valeurs foncières » (DVF)",
        article="description officielle du jeu (data.gouv.fr) et décret fondateur",
        url="https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres",
        version="décret n° 2018-1350 du 28/12/2018 ; dernière mise à jour du jeu : 07/04/2026",
        extrait=("« Le présent jeu de données “Demandes de valeurs foncières”, publié et produit "
                 "par la direction générale des finances publiques, permet de connaître les "
                 "transactions immobilières intervenues au cours des cinq dernières années sur le "
                 "territoire métropolitain et les DOM-TOM, à l'exception de l'Alsace, de la "
                 "Moselle et de Mayotte » — « Conformément au décret n° 2018-1350 du 28 décembre "
                 "2018 relatif à la publication sous forme électronique des informations portant "
                 "sur les valeurs foncières déclarées à l'occasion des mutations immobilières »."),
        lu_le="2026-09-06"),
    choix=("Bornes de bon sens et rayons de profils = conventions LABUSE déclarées (YAML) ; les "
           "champs lus (nature de mutation, valeur foncière, dispositions) sont ceux du fichier "
           "DGFiP — La Réunion est couverte (DOM, hors exclusions Alsace-Moselle-Mayotte)."),
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_filtre_motifs_visibles",
    valide_par="cc",
    verifie_le="2026-09-06",
))
