"""Fiche de règle — liens officiels adresse ↔ bâtiment (BAN PLUS, IGN).
TESTS-1 lot 1 (dette SOURCES-2 lot 3 : donnée servie sans fiche)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("ban_plus_adresses_bati",),
    formule_codee=(
        "Sur ban_plus_liens restreint à l'idu de la parcelle : liens = count(*), "
        "adresses = count(DISTINCT id_adr), batiments = count(DISTINCT id_bat). "
        "0 lien → None (le tiroir ne montre rien plutôt qu'un zéro ambigu) ; table absente "
        "→ None, jamais un tiroir cassé (bati.py:le_bien_block)."),
    entrees=("ban_plus_liens (BAN PLUS IGN — id_adr, id_bat, idu)",),
    classe="methode_standard",
    fonction="src/labuse/bati.py:le_bien_block (adresses_bati)",
    verdict="choix_assume",
    choix=(
        "Comptage BRUT des liens publiés par l'IGN (aucun filtre de qualité LABUSE) : la donnée "
        "sert de CLÉ de rapprochement adresse BAN ↔ bâtiment BD TOPO ↔ ID-RNB, pas d'indicateur "
        "métier. Un zéro est rendu None : « aucun lien publié » et « parcelle sans adresse » ne "
        "sont pas distinguables dans la source."),
    exemple_temoin="tests/test_regles_temoins_ocsge_rnb.py::test_ban_plus_comptes_a_la_main",
    verifie_le="2026-09-14",
))
