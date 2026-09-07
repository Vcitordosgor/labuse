"""Fiche de règle — secteurs d'information sur les sols et CASIAS. SOURCES-1 lot 3."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("sols_parcelle", "sis_classe", "casias_statut"),
    formule_codee=(
        "SIS : parcelle ∩ spatial_layers (kind=sol_pollue, subtype=sis, périmètres "
        "réglementaires MultiPolygon) → classe « dans » (part = aire(∩)/aire(parcelle)) ; "
        "cascade VIGILANCE FORTE, motifs citant L556-2 (étude de sols au changement d'usage) "
        "et L125-7 (information écrite de l'acheteur/locataire). CASIAS/instruction : site le "
        "plus proche à ≤ 100 m (ST_DWithin, même rayon que la cascade sol_pollue) → "
        "sur_place (< 0,5 m) / proche_100m / hors ; VIGILANCE faible, motif « inventaire "
        "historique, pas une pollution avérée »."),
    entrees=("spatial_layers (kind=sol_pollue : subtype sis/casias/instruction, "
             "attrs->identifiant_ssp/statut/fiche_risque, geom_2975)",
             "config/cascade_rules.yaml (sol_pollue : severity_sis, proximite_m)"),
    classe="regle_externe",
    fonction=("src/labuse/api/app.py:_sols_block ; "
              "src/labuse/cascade/layers/etage1.py:SolPollueLayer"),
    verdict="conforme",
    reference=Reference(
        titre="Code de l'environnement", article="art. L125-7",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043978143",
        version="en vigueur depuis le 25/08/2021",
        extrait=("« Sans préjudice de l'article L. 514-20 et de l'article L. 125-5, lorsqu'un "
                 "terrain situé en secteur d'information sur les sols mentionné à l'article "
                 "L. 125-6 fait l'objet d'un contrat de vente ou de location, le vendeur ou "
                 "le bailleur du terrain est tenu d'en informer par écrit l'acquéreur ou le "
                 "locataire. »"),
        lu_le="2026-09-07"),
    exemple_temoin="tests/test_sources1_lot3.py::test_sis_vigilance_forte_et_obligations_dites",
    verifie_le="2026-09-07",
))
