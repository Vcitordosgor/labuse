"""Fiche de règle — vigilance zones humides (inventaires DEAL). SOURCES-1 lot 2."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("zone_humide_couche",),
    formule_codee=(
        "Parcelle ∩ kind='zone_humide' (5 inventaires DEAL : habitats 2011, inventaire 2009 "
        "+ espaces fonctionnels, 2003, basse altitude 2019) → VIGILANCE FORTE, l'inventaire "
        "touché et la part de parcelle dits ; jamais une exclusion seule. Hors inventaire → "
        "PASS avec la réserve « par secteurs, l'absence n'est pas une preuve »."),
    entrees=("spatial_layers (kind=zone_humide : subtype=inventaire, name, coverage)",),
    classe="choix_labuse",
    fonction="src/labuse/cascade/layers/phase1.py:ZoneHumideLayer ; ingestion/deal_carmen.py",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 lot 2 : « VIGILANCE forte ; couverture par secteurs dite ». Pas de "
        "RÉDHIBITOIRE automatique : les inventaires DEAL sont PARTIELS (secteurs 2003→2019) et "
        "une « cartographie d'habitats de zones humides » n'est pas la délimitation "
        "réglementaire (L211-1 code de l'environnement) — mais la séquence "
        "éviter-réduire-compenser de la loi sur l'eau rend la contrainte souvent rédhibitoire "
        "à l'instruction : le motif le dit et impose l'étude zone humide."),
    exemple_temoin="tests/test_sources1_lot2.py::test_zone_humide_vigilance",
    verifie_le="2026-09-07",
))
