"""Fiche de règle — Gabarit réglementaire (zone d'implantation, plafond d'emprise, hauteur,
couverture, motif de blocage, plan 2D). GABARIT-1→5 / CIRCUIT-4.

Un seul CALCUL (le pipeline gabarit : raccordement réel → moteur pur → plan) produit les six
données ; une seule fiche les couvre (comme emprise_batie_m2 couvre emprise + compte)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("gabarit_implantation_m2", "gabarit_emprise_plafond_m2", "gabarit_hauteur_m",
             "gabarit_couverture_verdict", "gabarit_motif_blocage", "gabarit_plan_2d"),
    formule_codee=(
        "Moteur géospatial PUR et déterministe (aucun estimatif — liste noire testée). Par parcelle, "
        "après validation stricte (sinon « Calcul incomplet » + motif) :\n"
        "• zone d'implantation = parcelle − reculs − exclusions : chaque limite classée (voie / "
        "séparative / voie privée) est bufferisée de son recul PLU, l'union est retranchée de la "
        "parcelle, puis les exclusions (PPR zone rouge) sont soustraites ; surface = ST_Area de la "
        "part surfacique (Polygon/MultiPolygon), en EPSG:2975.\n"
        "• plafond d'emprise = surface_parcelle × CES / 100, calculé À PART (JAMAIS min(zone, "
        "plafond)) ; None (« Non réglementé ») quand le règlement ne fixe pas de CES — silence prouvé "
        "(MaxFootprint.status='absent'), sourcé, jamais un zéro ni un 100 %.\n"
        "• hauteur = valeur PLU du §4 Urbanisme, CITÉE (jamais redéclarée) ; « Non chiffrée » quand la "
        "règle est en prospect (L ≥ H : forme validée non numérique, status='not_integrated', 2D "
        "servie / 3D indisponible, aucun calcul de H depuis L).\n"
        "• couverture = nombre de familles réglementaires vérifiées parmi {reculs, hauteur, emprise, "
        "risques} (≤ 4 ; l'emprise absente compte « vérifiée — sans plafond ») + la liste des règles "
        "connues mais non intégrées (hauteur prospect, stationnement, espaces libres).\n"
        "• motif de blocage = la cause métier quand une donnée réglementaire nécessaire manque "
        "(limite non qualifiée ; voie privée sans recul réglé ; zone hors calibrage ; ≥ 2 zones "
        "constructibles ; recul non validé…) — servi seul, sans chiffre.\n"
        "• plan 2D = SVG des géométries servies (contour cadastral, zone d'implantation, bandes de "
        "retrait, exclusions), miroir exact du mini-plan de la fiche (schéma, pas un plan de masse).\n"
        "Les limites sont classées par adjacence cadastre + BD TOPO (route d'abord ; voie privée = "
        "parcelle sans bâti, allongée L/l≥5 et étroite ≤6 m, raccordée au réseau sans le traverser), "
        "mesurée 0 faux (docs/GABARIT/A0-5-MESURE.md : 143/170 servies, 0 faux)."),
    entrees=(
        "parcels (cadastre — geom_2975, surface, commune)",
        "config/plu_destinations/*.yaml (PLU calibré : CES, hauteur, reculs voie/séparatif, "
        "citations retraits.voie — lues via faisabilite/zonage.py:resolve_zone et plu/destinations)",
        "spatial_layers (kind=voirie/batiment/plu_gpu_zone/ppr, geom_2975)",
        "cascade_results (layer_name='risques' — PPR zone rouge, HARD_EXCLUDE)",
    ),
    classe="choix_labuse",
    fonction="src/labuse/gabarit/engine.py:compute_gabarit",
    verdict="choix_assume",
    choix=(
        "Choix LABUSE (GABARIT-1→5) : le gabarit est une ENVELOPPE réglementaire géométrique — "
        "l'espace où une construction peut s'implanter selon les SEULES règles intégrées (reculs, "
        "CES, hauteur, exclusions PPR), jamais un plan de masse ni un projet chiffré. Deux principes "
        "gravés : (1) le plafond d'emprise est un fait DISTINCT de la zone d'implantation, calculé à "
        "part, jamais min() ; (2) un silence prouvé du règlement (CES ou hauteur non fixés) est une "
        "donnée sourcée servie « Non réglementé » / « Non chiffrée », jamais un zéro ni un blocage "
        "trompeur (CDC §3, « silence prouvé = donnée sourcée »). Zéro estimatif : aucun logement, SDP, "
        "coût ou potentiel. Servi sur fixtures dès GABARIT-1, réel per-parcelle depuis GABARIT-2 "
        "(classification des limites) ; voies privées par citation PLU depuis GABARIT-5."),
    exemple_temoin="tests/gabarit/test_engine.py::test_02_distinction_zone_vs_plafond",
    valide_par="cc",
    verifie_le="2026-09-22",
    moteur_fonctions=(),
))
