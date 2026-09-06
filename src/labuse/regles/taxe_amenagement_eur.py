"""Fiche de règle — calculette de taxe d'aménagement. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("taxe_amenagement_eur",),
    formule_codee=(
        "Assiette = surface_taxable × valeur forfaitaire de l'année (892 €/m² hors IdF, millésime "
        "2026 du YAML daté) + forfaits d'installations (piscine 251 €/m², PV au sol 10 €/m², "
        "stationnement extérieur, éolienne 3 000 €/mât) ; abattement 50 % sur les 100 premiers m² "
        "d'une résidence principale et sur les logements aidés ; exonération de plein droit des "
        "surfaces < 5 m². Taxe = assiette × (taux communal + taux départemental) — le taux "
        "communal est SAISI (ou lu de taxe_amenagement_taux si une délibération publique est en "
        "base), JAMAIS un défaut : sans taux, pas de total. Taux départemental plafond légal "
        "2,5 %, étiqueté « à confirmer ». Détail ligne par ligne, vérifiable."),
    entrees=("config/taxe_amenagement.yaml (millésime 2026, source service-public A15416, relevé "
             "2026-08-28)", "taxe_amenagement_taux (délibérations publiques)", "saisies client"),
    classe="regle_externe",
    fonction="src/labuse/taxe_amenagement.py:calculer",
    verdict="reference_introuvable",
    choix=("Doctrine « aucun taux inventé » : le taux communal vient d'une délibération ou du "
           "client, jamais d'un défaut. NOTE MANDAT : le mandat cite « art. L331-10 s. » (code de "
           "l'urbanisme) — ABROGÉ depuis l'ordonnance 2022-883 ; la base légale en vigueur est le "
           "CGI art. 1635 quater A à V, déjà celle du YAML (RV2-V2, 28/08/2026)."),
    exemple_temoin="tests/regles/test_taxe_amenagement.py::test_calcul_ligne_a_ligne_independant",
    verifie_le="2026-09-06",
))
