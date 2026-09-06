"""Fiche de règle — compte de parcelles du Copilote (facette canonique). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("copilote_compte_parcelles",),
    formule_codee=("count sur la MÊME facette canonique que le filtre écran (mêmes WHERE : tiers, "
                   "zones, communes, run servi) — égalité verrouillée par test : le Copilote ne "
                   "peut pas dire un autre nombre que l'écran."),
    entrees=("parcels", "parcel_p_score_v2 (run servi)", "parcel_zone_plu"),
    classe="choix_labuse",
    fonction="src/labuse/copilote_v2/outils.py:compter_parcelles",
    verdict="choix_assume",
    choix="Une seule facette pour l'écran et le Copilote (jamais deux vérités).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_copilote_meme_facette",
    verifie_le="2026-09-06",
))
