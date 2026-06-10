"""PPR (servitude PM1) — parsing du risque et normalisation commune (fonctions pures)."""
from labuse.ingestion.layers_ingest import _norm_commune, _ppr_risque


def test_risque_inondation_mvt():
    code, lib = _ppr_risque("PM1_PPR_i_mvt_SAINT_PAUL_20161026_act.pdf")
    assert code == "i_mvt" and "inondation" in lib and "mouvement" in lib


def test_risque_littoral():
    code, lib = _ppr_risque("PM1_PPR_l_SAINT_PAUL_20181219_act.pdf")
    assert code == "l" and "littoral" in lib.lower()


def test_risque_mvt_seul():
    code, lib = _ppr_risque("PM1_PPR_mvt_CILAOS_20110609_act.pdf")
    assert code == "mvt" and lib == "mouvement de terrain"


def test_norm_commune():
    assert _norm_commune("Saint-Paul") == "SAINT_PAUL"
    assert _norm_commune("L'Étang-Salé") == "L_ETANG_SALE"


def test_filtre_commune_via_fichier():
    # le filtre commune (utilisé à l'ingestion) doit garder Saint-Paul et écarter Le Port.
    want = _norm_commune("Saint-Paul")
    assert want in _norm_commune("PM1_PPR_i_mvt_SAINT_PAUL_20161026_act.pdf")
    assert want not in _norm_commune("PM1_PPR_i_mvt_alea_cotier_LE_PORT_20120326_act.pdf")
