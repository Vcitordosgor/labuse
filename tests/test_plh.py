"""Orientations PLH (LOT 4.1) — données extraites du 3e PLH du TCO, jamais inventées."""
from __future__ import annotations

from labuse import plh


def test_orientations_saint_paul():
    o = plh.orientations("Saint-Paul", logements_estimes=88)
    assert o is not None
    assert o["cible_repartition"] == {"libre_pct": 40, "aide_pct": 60}
    assert o["typologies_aidees"]["locatif_social"] == ["LLTS", "LLS", "PLS"]
    assert o["source"]["provenance"] == "sourcee"
    assert o["source"]["millesime"] == "2019"
    assert o["bilan"]["logements_sociaux_realise_pct"] == 82


def test_alignement_factuel():
    """L'alignement applique la cible PLH (60 % aidé) à la capacité estimée — factuel, pas inventé."""
    o = plh.orientations("Saint-Paul", logements_estimes=88)
    al = o["alignement"]
    assert al["aides_cibles"] == round(88 * 60 / 100)      # 53
    assert al["libres_cibles"] == 88 - al["aides_cibles"]   # 35
    assert "facilite l'instruction" in al["message"]


def test_sans_capacite_pas_d_alignement():
    o = plh.orientations("Saint-Paul", logements_estimes=None)
    assert "alignement" not in o


def test_commune_hors_tco_renvoie_none():
    """Hors TCO → aucune orientation fabriquée."""
    assert plh.orientations("Saint-Denis", 50) is None
    assert plh.orientations("Le Tampon") is None
