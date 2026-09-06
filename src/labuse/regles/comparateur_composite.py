"""Fiche de règle — score composite du comparateur. CIRCUIT-4 (lot 3 : méthode citée)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("comparateur_composite",),
    formule_codee=(
        "Normalisation min-max de chaque indicateur présent sur [0;100] selon sa direction "
        "(direction −1 → 1−frac), avec frac = (v − min) ÷ (max − min) sur les 24 communes ; borne "
        "dégénérée (max = min) → 50 neutre. Composite = Σ(poids_k × norm_k) ÷ Σ(poids des axes "
        "PRÉSENTS) — renormalisation pour ne pas pénaliser une donnée manquante — arrondi 0,1 ; "
        "rang = tri décroissant."),
    entrees=("indicateurs_communes (stock, velocite, permis, deficit_sru, pression_zan, prix_neuf)",
             "poids (réglables, défauts INDICATEURS)"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/commune.py:composite_communes",
    verdict="conforme",
    reference=Reference(
        titre="Normalisation min-max (feature scaling) — scikit-learn, MinMaxScaler",
        article="sklearn.preprocessing.MinMaxScaler (formule de transformation)",
        url="https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.MinMaxScaler.html",
        version="documentation stable (consultée 2026-09-06)",
        extrait=("« X_std = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0)) ; "
                 "X_scaled = X_std * (max - min) + min » — la même transformation min-max, ici "
                 "portée sur [0;100] avec inversion pour les axes « plus bas = mieux »."),
        lu_le="2026-09-06"),
    choix=("Poids par défaut (0,30 stock · 0,15 vélocité · 0,15 permis · 0,15 SRU · 0,10 ZAN · "
           "0,15 prix neuf), inversion de direction et renormalisation des poids présents : "
           "conventions LABUSE du comparateur, réglables à l'écran."),
    exemple_temoin="tests/regles/test_comparateur_composite.py::test_composite_temoin",
    valide_par="cc",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.composite_communes",),
))
