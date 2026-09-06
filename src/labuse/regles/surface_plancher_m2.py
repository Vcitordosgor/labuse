"""Fiche de règle — capacité constructible « table rase » (moteur commun). CIRCUIT-4."""
from . import FicheRegle, declarer

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
    verdict="reference_introuvable",
    choix=("Les coefficients 0,45 (occupation du gabarit), 3,0 m/étage, 0,80 (SDP→SHAB), 65-80 "
           "m²/logement et 30 logts/ha/niveau sont des HYPOTHÈSES LABUSE de modélisation, "
           "affichées avec le résultat — pas des règles de PLU."),
    exemple_temoin="tests/regles/test_surface_plancher.py::test_enveloppe_ordre_du_reglement",
    verifie_le="2026-09-06",
))
