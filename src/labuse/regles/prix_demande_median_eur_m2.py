"""Fiche de règle — statistiques du marché Radar (annonces). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prix_demande_median_eur_m2", "delai_vente_median_j", "annonces_actives_n",
             "n_biens_du_jour", "n_biens_veille"),
    formule_codee=(
        "Sur pige_biens × pige_faits validés (valide_at NOT NULL) et NON à-qualifier : médiane "
        "percentile_cont(0.5) des prix affichés €/m² (terrain : prix ÷ surface_terrain ; bâti "
        "maison/appartement/immeuble : prix ÷ surface_hab) ; délai médian = médiane de (retrait ou "
        "vente − publication) en jours. TOUTE mesure avec n < 5 (SEUIL_N) est MASQUÉE "
        "(valeur=null, insuffisant=true) ; les COMPTES (actives, nouvelles/30 j, du jour, par "
        "veille) restent des faits bruts toujours servis."),
    entrees=("pige_biens (statut, type_bien, dates)", "pige_faits (prix, surfaces, valide_at)"),
    classe="methode_standard",
    fonction="src/labuse/pige/marche.py:stats",
    verdict="reference_introuvable",
    choix=("Seuil 5 : honnêteté statistique gravée (jamais une médiane sur trois valeurs) ; les "
           "annonces à-qualifier n'entrent JAMAIS dans une statistique (RADAR-HTML)."),
    exemple_temoin="tests/regles/test_marche_pige.py::test_seuil5_et_medianes",
    verifie_le="2026-09-06",
))
