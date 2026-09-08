"""PALIERS-1 — gardes de la politique v2 (statuts.assign_paliers + motifs + réserve).

Fonctions PURES : pas de DB. On grave la règle (seuils, anti-churn, domaine) pour que
la moindre dérive de seuil ou de vocabulaire casse un test.
"""
import numpy as np
import pandas as pd

from labuse.scoring.p_v2 import statuts as S


def _cfg():
    return S.charger_paliers_config()


def test_config_seuils_depuis_yaml():
    c = _cfg()
    assert (c.entree_priorite, c.entree_a_suivre) == (0.20, 0.10)
    assert (c.sortie_priorite, c.sortie_a_suivre) == (0.18, 0.09)
    assert c.reserve_quantile == 0.90


def test_domaine_quatre_valeurs_uniquement():
    assert S.PALIERS == ("priorite", "a_suivre", "sans_signal", "ecartee")


def test_entree_stricte():
    df = pd.DataFrame({"p": [0.20, 0.1999, 0.10, 0.0999, 0.0, 0.5],
                       "ecartee_etage0": [False, False, False, False, False, True]})
    got = list(S.assign_paliers(df, _cfg()).values)
    assert got == ["priorite", "a_suivre", "a_suivre", "sans_signal", "sans_signal", "ecartee"]


def test_ecartee_prime_sur_tout():
    df = pd.DataFrame({"p": [0.99], "ecartee_etage0": [True]})
    assert S.assign_paliers(df, _cfg()).iloc[0] == "ecartee"


def test_anti_churn_priorite_reste_jusqu_a_sortie():
    prev = pd.Series(["priorite"] * 4)
    df = pd.DataFrame({"p": [0.185, 0.18, 0.179, 0.05], "ecartee_etage0": [False] * 4})
    got = list(S.assign_paliers(df, _cfg(), prev).values)
    # ≥0,18 reste Priorité ; sous 0,18 descend d'un cran (À suivre si ≥0,09) ; crash → Sans signal
    assert got == ["priorite", "priorite", "a_suivre", "sans_signal"]


def test_anti_churn_a_suivre_reste_jusqu_a_sortie():
    prev = pd.Series(["a_suivre"] * 3)
    df = pd.DataFrame({"p": [0.09, 0.089, 0.25], "ecartee_etage0": [False] * 3})
    got = list(S.assign_paliers(df, _cfg(), prev).values)
    # ≥0,09 reste À suivre ; sous 0,09 → Sans signal ; ≥0,20 promotion IMMÉDIATE
    assert got == ["a_suivre", "sans_signal", "priorite"]


def test_promotion_immediate_sans_hysterese():
    prev = pd.Series(["sans_signal", "sans_signal"])
    df = pd.DataFrame({"p": [0.20, 0.10], "ecartee_etage0": [False, False]})
    assert list(S.assign_paliers(df, _cfg(), prev).values) == ["priorite", "a_suivre"]


def test_motifs_copropriete_hors_palier_puis_declassements():
    df = pd.DataFrame({
        "copro": [True, False, False, False],
        "declasse_cause": [None, "declasse_non_constructible", None, None],
        "au_statut": [None, None, "declasse_au_fermee", None],
        "bati_sature": [False, False, False, True]})
    got = list(S.motifs_parcelle(df).values)
    assert got == [["copropriete"], ["declasse_non_constructible"],
                   ["declasse_au_fermee"], ["declasse_bati_sature"]]


def test_motif_le_plus_specifique_prime():
    # zone fermée (spécifique) prime sur bâti saturé (général)
    df = pd.DataFrame({"declasse_cause": ["declasse_zone_fermee"], "bati_sature": [True]})
    assert S.motifs_parcelle(df).iloc[0] == ["declasse_zone_fermee"]


def test_reserve_fonciere_decile_superieur():
    df = pd.DataFrame({"sdp_residuelle_m2": [0, 10, 100, 100, 100, 100, 100, 100, 100, 5000]})
    flag = S.reserve_fonciere(df, _cfg())
    assert bool(flag.iloc[-1]) is True and bool(flag.iloc[0]) is False


def test_declassement_garde_son_palier():
    """Une bâtie saturée à p ≥ 0,20 est Priorité (le déclassement est un motif, pas un palier)."""
    df = pd.DataFrame({"p": [0.30], "ecartee_etage0": [False], "bati_sature": [True]})
    assert S.assign_paliers(df, _cfg()).iloc[0] == "priorite"
    assert S.motifs_parcelle(df).iloc[0] == ["declasse_bati_sature"]
