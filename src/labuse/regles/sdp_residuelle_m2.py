"""Fiche de règle — SDP résiduelle. CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

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
    verdict="partiel",
    reference=Reference(
        titre="Code de l'urbanisme — définition de la surface de plancher",
        article="art. R111-22",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031721274/",
        version="en vigueur au 01/01/2016 (décret n° 2015-1783 du 28/12/2015)",
        extrait=("« La surface de plancher de la construction est égale à la somme des surfaces de "
                 "plancher de chaque niveau clos et couvert, calculée à partir du nu intérieur des "
                 "façades après déduction : […] 3° Des surfaces de plancher d'une hauteur sous "
                 "plafond inférieure ou égale à 1,80 mètre ; 4° Des surfaces […] de stationnement "
                 "[…] ; 8° D'une surface égale à 10 % des surfaces de plancher affectées à "
                 "l'habitation […] »"),
        lu_le="2026-09-06"),
    ecart=("Même approximation que surface_plancher_m2 : SDP existante et SDP max sont des "
           "ENVELOPPES (emprise × niveaux) sans les huit déductions de R111-22 — dit à l'écran "
           "(« estimé ») ; proposition au REGLES-ECARTS (libellé « SDP estimée »)."),
    choix=("Seuil de sous-densité 40 % du taux d'emprise et niveaux par défaut 1,0 : conventions "
           "LABUSE prudentes, affichées."),
    exemple_temoin="tests/regles/test_sdp_residuelle.py::test_residuel_formule_independante",
    verifie_le="2026-09-06",
))
