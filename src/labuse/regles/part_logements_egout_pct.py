"""Fiche de règle — part des logements au tout-à-l'égout (INSEE EGOUL). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("part_logements_egout_pct",),
    formule_codee=("pct = 100 × logements raccordés au tout-à-l'égout ÷ logements total, à la "
                   "maille IRIS de la parcelle, REPLI commune si l'IRIS manque — le TAUX est servi "
                   "avec sa maille, jamais une conclusion parcellaire (la parcelle elle-même n'est "
                   "pas dans la source)."),
    entrees=("insee_rp2022_egoul (fichier détail Logements EGOUL, RP 2022, maille IRIS)",),
    classe="regle_externe",
    fonction="src/labuse/anc_service.py:statut_anc",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_zone_insee.py::test_part_egout_maille",
    verifie_le="2026-09-06",
))
