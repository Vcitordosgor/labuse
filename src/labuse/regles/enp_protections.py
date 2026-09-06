"""Fiche de règle — protections des espaces naturels (ENP). SOURCES-1 lot 2."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("enp_couche",),
    formule_codee=(
        "Parcelle ∩ kind='ens' → verdict par subtype : réserve_naturelle_nationale / "
        "reserve_naturelle (Carmen : RNN zonée + réserve marine) / réserve_biologique / apb "
        "→ RÉDHIBITOIRE ; conservatoire_du_littoral → VIGILANCE moyenne ; ramsar → faible "
        "(indication internationale) ; site_classe / site_inscrit → info ×0 "
        "(anti-double-compte : la servitude AC2 les porte en fort, lot 1). Le cœur de parc "
        "national reste RÉDHIBITOIRE via la couche parc_national (inchangé)."),
    entrees=("spatial_layers (kind=ens : subtype, name, coverage)",
             "config/cascade_rules.yaml (ens : hard_subtypes, severites)"),
    classe="choix_labuse",
    fonction="src/labuse/cascade/layers/phase1.py:EnsLayer ; ingestion/deal_carmen.py",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 lot 2 : « RÉDHIBITOIRE en cœur de parc, réserves, APB ; VIGILANCE "
        "ailleurs ». Les réserves biologiques (ONF) sont traitées comme réserves (protection "
        "forte). Sites classés/inscrits : le mandat lot 1 les porte déjà en VIGILANCE FORTE "
        "par la SUP AC2 — les compter aussi ici serait un double malus, la couche ENP les "
        "AFFICHE (info ×0). Chevauchement DIT : la RNN de l'Étang Saint-Paul existe côté INPN "
        "(1 entité) et côté Carmen (zones A/B) — deux entrées, même verdict rédhibitoire."),
    exemple_temoin="tests/test_sources1_lot2.py::test_enp_hard_reserves_apb",
    verifie_le="2026-09-07",
))
