"""Fiche de règle — prix du terrain nu par famille de zone. CIRCUIT-4."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("prix_terrain_zone_eur_m2",),
    formule_codee=("Médiane des €/m² DVF terrain nu de la commune par famille de zone (U/AU/A/N), "
                   "seuil 10 ventes par cellule sinon rien."),
    entrees=("dvf_mutations_parcelle (terrains)", "parcel_zone_plu.zone_fam"),
    classe="methode_standard",
    fonction="src/labuse/marche_service.py (prix_terrain_zone)",
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
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_terrain_par_zone_seuil",
    valide_par="cc",
    verifie_le="2026-09-06",
))
