"""Fiche de règle — capacité constructible « table rase ». CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("surface_plancher_m2", "capacite_logements", "surface_vendable_m2", "potentiel_verdict"),
    formule_codee=(
        "Enveloppe gabaritaire posée DANS L'ORDRE DU RÈGLEMENT de la zone (YAML calibré par commune, "
        "sources citées article par article) : (1) emprise au sol = contour cadastral réel inseté du "
        "recul limites séparatives (Art. 7 ; repli modèle carré (√S−rv−rl)×(√S−2rl) avec défauts "
        "prudents rv=5 m, rl=3 m) ; (2) plafonnée par le % d'emprise réglementé s'il existe "
        "(Art. 9 : min(reculs, S×CES%)) ; (3) plafonnée par la pleine terre (Art. 13 : emprise ≤ "
        "S×(1−PT%)) ; (4) niveaux = ⌊hé ÷ 3,0 m⌋ (hauteur à l'ÉGOUT Art. 10 ; repli faîtage "
        "prudent ⌊(hf−3)÷3⌋, averti) ; (5) footprint = emprise × 0,45 (coef d'occupation du "
        "gabarit, HYPOTHÈSE de modélisation dite) ; (6) SDP = footprint × niveaux ; (7) SHAB "
        "vendable = SDP × 0,80 ; (8) logements = SHAB ÷ [65;80] m², plafonnés par la densité "
        "30 logts/ha/niveau et le stationnement (scénarios au sol / silo). Zone non constructible "
        "au règlement ou habitat interdit → 0 avec cause dite."),
    entrees=("parcels.geom_2975/surface_m2", "parcel_zone_plu (zone dominante)",
             "config/plu_<commune>.yaml (reculs, CES, pleine terre, hé/hf, sources d'articles)",
             "Hypotheses (étage 3,0 m ; occupation 0,45 ; rendement 0,80 ; 65-80 m²/logt ; "
             "densité 30 logts/ha/niveau)"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/engine.py:estimate_capacity (servi par faisabilite/potentiel.py:bloc_potentiel)",
    verdict="partiel",
    reference=Reference(
        titre="Code de l'urbanisme — définition de la surface de plancher",
        article="art. R111-22",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031721274/",
        version="en vigueur au 01/01/2016 (décret n° 2015-1783 du 28/12/2015)",
        extrait=("« La surface de plancher de la construction est égale à la somme des surfaces de "
                 "plancher de chaque niveau clos et couvert, calculée à partir du nu intérieur des "
                 "façades après déduction : 1° Des surfaces correspondant à l'épaisseur des murs "
                 "[…] ; 2° Des vides et des trémies […] ; 3° Des surfaces de plancher d'une hauteur "
                 "sous plafond inférieure ou égale à 1,80 mètre ; 4° Des surfaces de plancher "
                 "aménagées en vue du stationnement […] ; 5° Des surfaces de plancher des combles "
                 "non aménageables […] ; 6° Des locaux techniques […] ; 7° Des caves ou celliers "
                 "[…] ; 8° D'une surface égale à 10 % des surfaces de plancher affectées à "
                 "l'habitation […] »"),
        lu_le="2026-09-06"),
    ecart=("PARTIE NON IMPLÉMENTÉE, DITE : le moteur estime une ENVELOPPE gabaritaire (emprise "
           "modélisée × niveaux) et la nomme « surface de plancher » ; il n'applique AUCUNE des "
           "huit déductions de R111-22 (murs, trémies, h ≤ 1,80 m, stationnement, combles, locaux "
           "techniques, caves, 10 % habitation) — l'estimation majore donc la SDP réglementaire. "
           "Proposition (REGLES-ECARTS, décision Vic) : libeller « SDP estimée (enveloppe) » ou "
           "poser un coefficient de passage documenté."),
    choix=("Les coefficients 0,45 / 3,0 m / 0,80 / 65-80 m² / 30 logts/ha/niveau sont des "
           "HYPOTHÈSES LABUSE de modélisation, affichées avec le résultat."),
    exemple_temoin="tests/regles/test_surface_plancher.py::test_enveloppe_ordre_du_reglement",
    verifie_le="2026-09-06",
))
