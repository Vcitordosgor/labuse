"""Fiche de règle — prix du neuf (VEFA / observé) et tranches. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prix_neuf_observe_eur_m2", "prix_neuf_vefa_acte_eur_m2", "tranche_prix_vefa", "vefa_couche"),
    formule_codee=(
        "prix_neuf_vefa_acte = médiane des VEFA déclarées à l'acte (neuf_vefa_commune, fenêtre 36 "
        "mois glissants, ≥ 10 ventes avec prix sinon rien). prix_neuf_observe = ventes ≤ 3 ans "
        "après achèvement, cascade de résolution : bassin sourcé > secteur > commune > repli île "
        "(resolve_prix_neuf_marche, chaque niveau dit sa source). tranche_prix_vefa = la médiane "
        "rangée dans les tranches TRANCHE_LIBELLE (moins_4000 … 5500_plus ; sous_seuil si < 10 "
        "ventes) ; la couche peint la commune de sa tranche (hachure sous seuil)."),
    entrees=("dvf (VEFA, dates d'achèvement Sitadel)", "neuf_vefa_commune (live, 36 mois)"),
    classe="methode_standard",
    fonction="src/labuse/ingestion/vefa_neuf.py + src/labuse/marche_service.py (neuf_vefa_seuil)",
    verdict="reference_introuvable",
    choix=("Fenêtre 36 mois, seuil 10 ventes, bornes de tranches : conventions LABUSE d'affichage "
           "(l'hachure dit le sous-seuil, jamais une médiane fragile)."),
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_tranche_vefa_seuil10",
    verifie_le="2026-09-06",
))
