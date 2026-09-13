"""Fiche de règle — artificialisation communale 2017→2022 (OCS GE, pression ZAN).
TESTS-1 lot 1 (dette REPARATIONS-1 lot 5 : donnée et fonction moteur sans fiche)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("zan_evolution_commune",),
    formule_codee=(
        "Par commune, sur l'assiette cadastrale (parcel_ocsge × parcels.commune) : "
        "artif_ha = Σ evol_artif_m2 ÷ 10 000 et renat_ha = Σ evol_renat_m2 ÷ 10 000 (m² passés "
        "artificialisés / renaturés entre les millésimes OCS GE 2017 et 2022, flags du produit "
        "DIFFÉRENTIEL OFFICIEL IGN — portail de l'artificialisation, jamais un diff recalculé "
        "par LABUSE) ; part_artif_pct = 100 × Σ artif_m2 ÷ Σ ST_Area(geom parcelles). "
        "Arrondis 0,1."),
    entrees=("parcel_ocsge (evol_artif_m2, evol_renat_m2, artif_m2 — précalcul ingestion/ocsge.py)",
             "parcels (commune, geom_2975)"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/commune.py:zan_ocsge_commune",
    moteur_fonctions=("commune.zan_ocsge_commune",),
    verdict="choix_assume",
    choix=(
        "L'agrégat porte sur l'ASSIETTE CADASTRALE : les emprises hors parcelle (voirie "
        "notamment) ne sont pas comptées, et l'écran le dit. Le chiffre d'artificialisation "
        "est le produit différentiel officiel (flags IGN), pas une soustraction de millésimes "
        "faite maison."),
    exemple_temoin=None,
    verifie_le="2026-09-14",
))
