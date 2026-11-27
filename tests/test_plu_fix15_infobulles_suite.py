import pytest
from test_plu_fix15_stationnement import conditions


@pytest.mark.parametrize("zone", ["Ua", "Ub", "Uc"])
def test_bras_panon_foyers(zone):
    t = conditions("Bras-Panon", zone).lower()
    assert "au maximum pour 3 logements ou 3 chambres" in t


@pytest.mark.parametrize("zone", ["Ua", "Ub"])
def test_entre_deux_visiteurs(zone):
    t = conditions("Entre-Deux", zone).lower()
    assert "1 place visiteur par tranche de 10 logements" in t
    assert "1 place visiteur par tranche de 5 logements ou 5 lots" in t


@pytest.mark.parametrize("zone", ["UA", "UB"])
def test_sainte_marie_desserte(zone):
    t = conditions("Sainte-Marie", zone).lower()
    assert "0,5 place par logement" in t
    assert "moins de 500 m" in t and "qualité de la desserte" in t
