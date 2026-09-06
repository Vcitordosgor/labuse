"""Fiche de règle — prix de l'ancien par commune. CIRCUIT-4 (lot 3 : méthode citée)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("prix_ancien_median_eur_m2",),
    formule_codee=("Médiane des €/m² DVF « ventes strictes » de la commune (filtre de retenue du "
                   "baromètre : natures de mutation de vente, surfaces > 0, bornes de bon sens) — "
                   "moteur prix_ancien_communes, MÊME fonction pour le tableau Communes et le PDF."),
    entrees=("dvf_mutations (nature, prix, surface, commune)",),
    classe="methode_standard",
    fonction="src/labuse/marche_service.py (prix_ancien_communes)",
    verdict="conforme",
    reference=Reference(
        titre="Médiane — PostgreSQL percentile_cont (interpolation linéaire)",
        article="Ordered-Set Aggregate Functions",
        url="https://www.postgresql.org/docs/current/functions-aggregate.html",
        version="documentation current (consultée 2026-09-06)",
        extrait=("« Computes the continuous percentile, a value corresponding to the specified "
                 "fraction within the ordered set of aggregated argument values. This will "
                 "interpolate between adjacent input items if needed. »"),
        lu_le="2026-09-06"),
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_mediane_commune_independante",
    valide_par="cc",
    verifie_le="2026-09-06",
))
