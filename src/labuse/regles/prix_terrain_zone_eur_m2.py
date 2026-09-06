"""Fiche de règle — prix du terrain nu par famille de zone. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prix_terrain_zone_eur_m2",),
    formule_codee=("Médiane des €/m² DVF terrain nu de la commune par famille de zone (U/AU/A/N), "
                   "seuil 10 ventes par cellule sinon rien."),
    entrees=("dvf_mutations_parcelle (terrains)", "parcel_zone_plu.zone_fam"),
    classe="methode_standard",
    fonction="src/labuse/marche_service.py (prix_terrain_zone)",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_terrain_par_zone_seuil",
    verifie_le="2026-09-06",
))
