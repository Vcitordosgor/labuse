"""Fiche de règle — marge de surélévation sous la règle de hauteur. CIRCUIT-4 (lot 2)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("marge_surelevation_m",),
    formule_codee=(
        "marge = hauteur_règle − hauteur_bâti, avec hauteur_règle = hé (hauteur à l'ÉGOUT du "
        "règlement de zone, YAML calibré) en priorité, repli hf (faîtage) SEULEMENT si l'égout est "
        "absent, avec avertissement. possible = marge ≥ 2,8 m (un niveau habitable) ; None (jamais "
        "un faux « non ») quand une des deux hauteurs manque."),
    entrees=("config/plu_<commune>.yaml (he_m, hf_m, hauteur_src)", "hauteur_bati_m (BD TOPO)"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/potentiel.py:surelevation",
    verdict="partiel",
    reference=Reference(
        titre="Règlements de PLU communaux (corpus calibré LABUSE) — hauteurs Art. 10",
        article="hauteur d'égout/faîtage par zone, article et page cités dans le YAML",
        url="config/plu_<commune>.yaml (hauteur_src par zone)",
        version="calibration 2026 (millésimes GPU par commune)",
        extrait=("Saint-Paul, zone U1a : « he_m: 12, hf_m: 16 — Bande 15 m depuis voie : hé 9 / "
                 "hf 13 ; au-delà (ou si jouxte bâti >3 niveaux) : hé 12 / hf 16. » "
                 "(hauteur_src : « Zone U1a, Art. 10.2, p.20-21 »)."),
        lu_le="2026-09-06"),
    ecart=("PARTIE NON IMPLÉMENTÉE, DITE : les hauteurs par BANDE (ex. U1a : 9 m sur les 15 "
           "premiers mètres depuis la voie, 12 m au-delà) sont calibrées en une seule valeur "
           "retenue (la note le dit) ; le moteur ne modélise pas la bande — prudence à la valeur "
           "haute ou basse selon la calibration, écrite zone par zone."),
    choix=("Seuil 2,8 m = un niveau habitable (convention LABUSE, affichée avec le verdict)."),
    exemple_temoin="tests/regles/test_surelevation.py::test_marge_egout_prioritaire",
    verifie_le="2026-09-06",
))
