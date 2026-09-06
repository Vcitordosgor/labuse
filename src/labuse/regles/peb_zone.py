"""Fiche de règle — zones du plan d'exposition au bruit (PEB). SOURCES-1 lot 1."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("peb_zone",),
    formule_codee=(
        "Zone PEB de la parcelle = subtype (a/b/c/d) des entités kind='peb' intersectant la "
        "parcelle (part = aire(∩)/aire(parcelle)) ; « hors » sinon. Cascade : zone ∈ hard_zones "
        "(A, B) et part ≥ hard_min_pct (2 %) → RÉDHIBITOIRE ; zone C → VIGILANCE moyenne "
        "(isolement acoustique renforcé) ; zone D → VIGILANCE faible (information). La zone est "
        "SERVIE telle que publiée au GPU (txt de l'information typeinf 27), jamais recalculée."),
    entrees=("spatial_layers (kind=peb : subtype=zone, attrs->libelle/idurba, geom_2975)",
             "config/cascade_rules.yaml (peb : hard_zones, flag_zones, hard_min_pct)"),
    classe="regle_externe",
    fonction="src/labuse/cascade/layers/phase1.py:PebLayer ; ingestion/gpu_infos.py:ingest_gpu_infos",
    verdict="conforme",
    reference=Reference(
        titre="Code de l'urbanisme", article="art. L112-10",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031210273",
        version="en vigueur depuis le 01/01/2016",
        extrait=("« Dans les zones définies par le plan d'exposition au bruit, l'extension de "
                 "l'urbanisation et la création ou l'extension d'équipements publics sont "
                 "interdites lorsqu'elles conduisent à exposer immédiatement ou à terme de "
                 "nouvelles populations aux nuisances de bruit. » Les constructions à usage "
                 "d'habitation y sont interdites, sauf exceptions énumérées (activité "
                 "aéronautique ; logements de fonction en B et C ; en C, constructions "
                 "individuelles en secteur déjà urbanisé sous conditions)."),
        lu_le="2026-09-07"),
    ecart=None,
    exemple_temoin="tests/test_sources1_lot1.py::test_peb_zones_cascade",
    verifie_le="2026-09-07",
))
