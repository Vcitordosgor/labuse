"""Fiche de règle — timeline propriétaire PM (versionné ∪ servi) + acquisitions. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("proprietaire_timeline_liste", "acquisitions_pm_n"),
    formule_codee=(
        "Timeline = union des millésimes versionnés (pm_proprietaires_millesimes, 2019→2024) et du "
        "servi (parcelle_personne_morale 2025), anti-doublon NOT EXISTS, le servi jamais écrasé. "
        "acquisitions_pm_n = diff CONSTAT entre deux millésimes consécutifs (parcelles présentes au "
        "millésime N absentes au millésime N−1), agrégé à la maille commune — un constat de "
        "fichier, jamais une interprétation juridique (hors scoring)."),
    entrees=("pm_proprietaires_millesimes (2019→2024)", "parcelle_personne_morale (2025)"),
    classe="choix_labuse",
    fonction="src/labuse/proprietaire_historique.py:timeline",
    verdict="choix_assume",
    choix=("« Acquisition » = apparition dans le fichier PM entre deux millésimes — un CONSTAT de "
           "diff, pas un acte daté (DVF seul date une vente). Doctrine posée au mandat "
           "rattrapage-KF-2 (septembre 2026)."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_diff_constat_pm",
    verifie_le="2026-09-06",
))
