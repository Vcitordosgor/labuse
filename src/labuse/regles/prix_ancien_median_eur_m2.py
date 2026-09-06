"""Fiche de règle — prix de l'ancien par commune (baromètre). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prix_ancien_median_eur_m2",),
    formule_codee=("Médiane des €/m² DVF « ventes strictes » de la commune (filtre de retenue du "
                   "baromètre : natures de mutation de vente, surfaces > 0, bornes de bon sens) — "
                   "moteur prix_ancien_communes, MÊME fonction pour le tableau Communes et le PDF."),
    entrees=("dvf_mutations (nature, prix, surface, commune)",),
    classe="methode_standard",
    fonction="src/labuse/marche_service.py (prix_ancien_communes)",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_mediane_commune_independante",
    verifie_le="2026-09-06",
))
