"""Fiche de règle — écart demandé (Radar) vs acté (DVF). CIRCUIT-4."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("ecart_demande_acte_pct",),
    formule_codee=(
        "ecart = 100 × (médiane_demandé − médiane_acté) ÷ médiane_acté, servi seulement si les "
        "DEUX côtés tiennent n ≥ 5 (SEUIL_N), avec les deux n et les deux millésimes. Référence du "
        "MÊME TYPE de bien dès n ≥ 30 (SEUIL_REF_TYPE — mesuré : la référence mixte sur-évalue les "
        "maisons de +34,8 % vs +5,4 % en médiane maisons seules) ; repli mixte au périmètre DIT. "
        "Par annonce : référence LOCALE du même type autour de la parcelle rattachée (n ≥ 8, "
        "délégué au moteur de secteur unique), repli commune dit ; badge « sous le marché » à "
        "−15 % (SEUIL_SOUS_MARCHE_PCT, justifié : le demandé dépasse presque toujours l'acté) ; "
        "aucun verdict si la part foncière > 0,5 du prix (SEUIL_PART_FONCIERE — le €/m² habitable "
        "n'est plus comparable). Par type vendu : médiane de (acté − demandé) ÷ demandé sur les "
        "paires rattachées Sourcé."),
    entrees=("pige_biens/pige_faits (prix affichés, types, paires vendues)",
             "DVF acté via marche_service (référence locale/commune)"),
    classe="methode_standard",
    fonction="src/labuse/pige/signaux.py (_ecart, ecart_demande_acte) + pige/releves.py:ecart_par_type",
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
    choix=("Seuils 5 (service), 30 (référence du même type), 8 (référence locale), −15 % (badge), "
           "0,5 (part foncière) : conventions LABUSE MESURÉES sur corpus (RADAR-VEILLE-1, "
           "RADAR-DEPOT-2 D4) — chaque seuil est justifié dans le code, l'écart exact reste "
           "affiché quel que soit le seuil."),
    exemple_temoin="tests/regles/test_ecart_demande_acte.py::test_ecart_formule_et_seuils",
    valide_par="cc",
    verifie_le="2026-09-06",
))
