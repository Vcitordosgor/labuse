"""Fiche de règle — SAR : indication régionale, jamais une règle. SOURCES-1 lot 4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("sar_divergence",),
    formule_codee=(
        "Divergence = parcelle en zone PLU U/AU (kind plu_gpu_zone, préfixes positive_prefixes) "
        "∩ vocation « naturel/agricole/continuité/coupure » du PROXY de vocations (kind sar, "
        "divergent_subtypes). Verdict : PASS avec warning « ⚠ divergence » (mention renforcée "
        "sur zone AU, remontée en VIGILANCE — RETOURS-11F) ; JAMAIS d'exclusion ni de malus "
        "(doctrine D2). Vocations info_subtypes (mixte, rurale) : information simple."),
    entrees=("spatial_layers (kind=sar : subtype=vocation — PROXY Potentiel foncier Région)",
             "spatial_layers (kind=plu_gpu_zone)",
             "config/cascade_rules.yaml (sar : divergent_subtypes, info_subtypes)"),
    classe="choix_labuse",
    fonction="src/labuse/cascade/layers/phase1.py:SarLayer",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 lot 4 + règle 5 : le SAR est une INDICATION, « jamais présentée comme "
        "une règle, jamais rédhibitoire seule » — le SAR n'est pas opposable aux tiers ni aux "
        "autorisations (décret du 22/11/2011, portée limitée à la compatibilité des PLU, hors "
        "dispositions valant SMVM). État réel 07/09/2026 : la couche SIG officielle du SAR "
        "(ENR littoral, coupures d'urbanisation, continuités, zones préférentielles, espaces "
        "agricoles) n'est diffusée NULLE PART en vecteur (Carmen 29 : 187 couches, 0 SAR ; "
        "Lizmap DEAL : 0 ; Sextant : WMS image seule ; ODS Région : 283 jeux, 0) — seule vit le "
        "PROXY de vocations du Potentiel foncier Région (doctrine D2 : zéro pouvoir d'exclusion, "
        "warning de divergence, AU remonté en vigilance). Choix LABUSE : le proxy n'est PAS "
        "affiché comme couche « SAR » sur la carte (ce serait un mensonge d'étiquette) ; à la "
        "livraison de la couche officielle (demande Région, lot 7 ; rappel sentinelle 180 j avec "
        "suivi SAR 2050), les zonages réels entreront en VIGILANCE SEULEMENT (jamais "
        "rédhibitoires seuls) avec la mention « schéma régional, indication non opposable »."),
    exemple_temoin="tests/test_sources1_lot4.py::test_sar_proxy_jamais_excluant",
    verifie_le="2026-09-07",
))
