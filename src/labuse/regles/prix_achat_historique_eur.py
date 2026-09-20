"""Fiche de règle — prix d'achat historique de la parcelle (fait foncier D-a). CIRCUIT-4 · EXPORTS-2 lot 2."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prix_achat_historique_eur",),
    formule_codee=(
        "Passe-plat de la DERNIÈRE mutation DVF rattachée à l'IDU de la parcelle (montant + date), "
        "tel quel — jamais un prix estimé ni une médiane de secteur. « Non disponible » si aucune "
        "mutation DVF n'est rattachée à la parcelle (cas fréquent : parcelle jamais mutée seule)."),
    entrees=("dvf_parcelle.derniere_mutation (montant, date)",),
    classe="choix_labuse",
    fonction="src/labuse/exports/robinet_fiche.py:_c_prix_achat",
    verdict="choix_assume",
    choix=("Le fait affiché est la dernière mutation DVF SUR la parcelle elle-même (pas le secteur) "
           "— un fait public sourcé et daté, jamais complété par une estimation quand il manque."),
    exemple_temoin="tests/regles/test_prix_achat_historique.py::test_passe_plat_dvf_de_la_parcelle",
    verifie_le="2026-09-08",
))
