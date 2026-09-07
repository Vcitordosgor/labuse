"""Fiche de règle — loyer médian servi (bascule OLL/DHUP). SOURCES-1 lot 5 (CIRCUIT-4)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("loyer_median_eur_m2",),
    formule_codee=(
        "Bascule CANONIQUE/REPLI (ligne9_loyer) : si la commune tient dans UNE zone OLL "
        "(oll_zonage, 16/24 mesuré), loyer servi = médiane 'toutes catégories' de SA zone "
        "(oll_loyers, loyers OBSERVÉS 2024, €/m² hors charges) ; sinon repli DHUP (carte des "
        "loyers, loyer d'ANNONCE charges comprises, extrait embarqué 2025) avec le motif dit. "
        "Aucune moyenne inter-zones n'est fabriquée (maille dite) ; le détail OLL par zone "
        "reste disponible à la parcelle (oll_parcelle, IRIS→zone)."),
    entrees=("oll_loyers (annee, zone, loyer_median — agrégats ouverts du réseau OLL)",
             "oll_zonage (insee, iris, zone — L9740Zonage2024.csv)",
             "data/carte_loyers_reunion_2025.json (repli DHUP)"),
    classe="choix_labuse",
    fonction="src/labuse/faisabilite/marche_commune.py:ligne9_loyer",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 lot 5 : « loyer_median_eur_m2 prend l'OLL comme source canonique "
        "quand elle couvre le secteur, DHUP en repli ». Choix LABUSE d'application : le "
        "« secteur » est la ZONE OLL (la maille publiée) ; une commune multi-zones (8/24 : "
        "Saint-Denis 6 zones, Saint-Pierre/Sainte-Marie 5, La Possession/Saint-Leu/"
        "Saint-Paul/Le Tampon 4, Sainte-Suzanne 3) n'a PAS de valeur communale publiée par "
        "l'OLL → repli DHUP à la maille commune, motif dit, plutôt qu'une moyenne de zones "
        "inventée. Contrôle de cohérence : médiane agglomération 10,9 €/m² = plaquette "
        "AGORAH (fiche 15 : 10,90 — vérifié au filtre, bloquant). OLL = loyers OBSERVÉS "
        "hors charges ; DHUP = loyers d'ANNONCE charges comprises — l'étiquette de source "
        "porte la distinction."),
    exemple_temoin="tests/test_sources1_lot5.py::test_loyer_bascule_oll_dhup",
    verifie_le="2026-09-07",
))
