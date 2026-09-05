"""RETOURS-14 lot outils — S11 : la nature du toit n'est servie qu'au-dessus du seuil de
confiance (0 faux à l'œil sur 20 bâtiments, confirmé sur 50) ; « non déterminée (LiDAR) » sinon.
"""
from __future__ import annotations

import numpy as np

from labuse.solaire_toiture import SEUIL_CONFIANCE, _classify, _payload


def test_s11_double_pente_nette_servie():
    # deux plans opposés propres → confiance pleine, verdict servi
    mnh = np.zeros((40, 40))
    for i in range(40):
        mnh[:, i] = 6 + (i if i < 20 else 39 - i) * 0.2
    verdict, meta = _classify(mnh, np.ones((40, 40), bool))
    assert verdict == "double_pente"
    assert meta["confiance"] >= SEUIL_CONFIANCE
    p = _payload(verdict, meta["pente_mediane"], meta["pics_deg"], meta["part_pentue"], meta["confiance"])
    assert p["verdict"] == "double_pente" and p["libelle_court"] == "double pente"


def test_s11_sous_le_seuil_jamais_servi():
    # le verdict brut reste en cache mais n'est JAMAIS servi sous le seuil — les deux faux de
    # l'échantillon (croupe et bâtiment en L lus « double pente ») tombaient à 0,672 et 0,698
    p = _payload("double_pente", 15.0, [90, 270], 0.6, 0.698)
    assert p["verdict"] == "non_determine"
    assert p["libelle"] == "non déterminée (LiDAR)"
    assert p["pans_orientation_deg"] == []          # les pans incertains ne sortent pas
    assert p["pente_mediane_deg"] == 15.0           # la mesure directe, elle, reste servie
    assert p["seuil"] == SEUIL_CONFIANCE == 0.70


def test_s11_plat_confiance_directe():
    # toit plat : 85 %+ de pixels non pentus, la confiance porte cette part (pas les pans)
    verdict, meta = _classify(np.full((40, 40), 6.0), np.ones((40, 40), bool))
    assert verdict == "plat"
    assert meta["confiance"] >= SEUIL_CONFIANCE
