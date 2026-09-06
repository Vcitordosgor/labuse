"""Fiche de règle — SDP résiduelle (potentiel restant d'une parcelle bâtie). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("sdp_residuelle_m2", "classe_residuel"),
    formule_codee=(
        "SDP_existante = emprise_bâtie × niveaux_existants, où emprise_bâtie = max(bati_ratio(BD "
        "TOPO) × surface, emprise_cosia_m2 révélée) et niveaux_existants = étages BD TOPO, sinon "
        "⌈hauteur ÷ 3⌉, sinon hypothèse 1,0 (le résultat est alors marqué « estimé »). "
        "SDP_résiduelle = max(0 ; SDP_max − SDP_existante), SDP_max venant du moteur commun (fiche "
        "surface_plancher_m2). taux_emprise = 100 × emprise_bâtie ÷ emprise_max (plafonné 999) ; "
        "sous_densite = taux_emprise < 40 % (seuil hypothèses). Non constructible → SDP écrite 0 "
        "avec cause structurée ; hors PLU → NULL (réellement inconnaissable)."),
    entrees=("spatial_layers kind=batiment (BD TOPO : etages, hauteur)", "parcel_bati_revele (CoSIA)",
             "parcel_faisabilite (capacité max)", "Hypotheses (niveaux défaut 1,0 ; seuil 40 %)"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/residuel.py:compute_residuel",
    verdict="reference_introuvable",
    choix=("Seuil de sous-densité 40 % du taux d'emprise : palier LABUSE (filtre « sous-densité »), "
           "pas une règle externe. Niveaux par défaut 1,0 : hypothèse prudente quand BD TOPO ne "
           "porte ni étages ni hauteur — le libellé le dit."),
    exemple_temoin="tests/regles/test_sdp_residuelle.py::test_residuel_formule_independante",
    verifie_le="2026-09-06",
))
