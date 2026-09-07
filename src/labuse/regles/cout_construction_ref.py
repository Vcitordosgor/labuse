"""Fiche de règle — coût de construction de référence. SOURCES-1 lot 5."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("cout_construction_ref_eur_m2",),
    formule_codee=(
        "Hypotheses.charger lit la ligne SERVIE de cout_construction_ref (labuse_promotion : "
        "bas/haut €/m² SDP), REPLI sur les constantes du dataclass si la table est absente/"
        "vide ; un YAML de commune qui calibre ces coûts garde la main (appliqué après). "
        "Valeurs servies 2 300-2 800 €/m² SDP = les anciennes constantes, INCHANGÉES "
        "(écart bilan témoins = 0, mesuré)."),
    entrees=("cout_construction_ref (ligne servie labuse_promotion + contexte eptb_2024_maison)",),
    classe="choix_labuse",
    fonction=("src/labuse/faisabilite/engine.py:_couts_construction_reference / "
              "Hypotheses.charger"),
    verdict="choix_assume",
    reference=Reference(
        titre="EPTB (SDES) — Les prix du terrain et du bâti, La Réunion, 2024",
        article="chapitre 3 — caractéristiques des maisons construites",
        url=("https://dreal.statistiques.developpement-durable.gouv.fr/eptb/2024/"
             "la_reunion/caracteristiques_maisons_contruites.html"),
        version="EPTB 2024 (publication 2026)",
        extrait=("« à La Réunion, son coût moyen est de 145 500 € en 2024. Il diminue de "
                 "4 % sur un an » — surface moyenne 96 m², soit ≈ 1 516 €/m² habitable "
                 "(calcul LABUSE dit)."),
        lu_le="2026-09-07"),
    choix=(
        "Mandat SOURCES-1 lot 5 : « la constante d'engine.py disparaît ». État réel : l'EPTB "
        "2024 Réunion (lu, cité) mesure le segment MAISON INDIVIDUELLE (≈ 1 516 €/m² "
        "habitable) — pas le coût de revient d'une PROMOTION collective en SDP ; le « jeu "
        "CDC » du mandat est introuvable (aucun jeu identifiable, dit au compte-rendu). "
        "Choix LABUSE : la fourchette promotion 2 300-2 800 €/m² SDP (audit O2 : contexte "
        "insulaire, normes para-cycloniques) sort du code vers la table SOURCÉE "
        "cout_construction_ref (ligne servie), l'EPTB 2024 entre en ligne de CONTEXTE "
        "(jamais servie au bilan — segments incomparables, dérivation documentée en table). "
        "Valeurs inchangées : aucun bilan ne bouge."),
    exemple_temoin="tests/test_sources1_lot5.py::test_cout_construction_reference",
    verifie_le="2026-09-07",
))
