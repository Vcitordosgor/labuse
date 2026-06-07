"""Tests des connecteurs — parsing contre fixtures (sans réseau).

Le réseau étant bloqué ici, on valide la LOGIQUE de parsing sur des réponses
au format documenté API Carto. `test_connection()` live n'est pas testé ici.
"""
from __future__ import annotations

from labuse.connectors import get_connector
from labuse.connectors.cadastre import _build_idu, parse_parcelles
from labuse.connectors.gpu import parse_zones

# Extrait représentatif d'une réponse API Carto cadastre/parcelle.
CADASTRE_FC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[55.27, -21.01], [55.271, -21.01], [55.271, -21.009], [55.27, -21.009], [55.27, -21.01]]]},
            "properties": {"idu": "97411000AB0001", "numero": "0001", "section": "AB",
                            "code_insee": "97411", "nom_com": "Saint-Paul", "contenance": 2000},
        },
        {  # sans idu explicite → reconstruit
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[55.28, -21.02], [55.281, -21.02], [55.281, -21.019], [55.28, -21.019], [55.28, -21.02]]]},
            "properties": {"numero": "42", "section": "AC", "code_insee": "97411", "com_abs": "000", "nom_com": "Saint-Paul"},
        },
        {"type": "Feature", "geometry": None, "properties": {"idu": "x"}},  # ignorée (pas de géométrie)
    ],
}


def test_parse_parcelles():
    parcels = parse_parcelles(CADASTRE_FC)
    assert len(parcels) == 2
    assert parcels[0]["idu"] == "97411000AB0001"
    assert parcels[0]["section"] == "AB" and parcels[0]["numero"] == "0001"
    assert parcels[0]["geometry"]["type"] == "Polygon"


def test_build_idu_reconstruit():
    # idu présent → utilisé tel quel
    assert _build_idu({"idu": "97411000AB0001"}) == "97411000AB0001"
    # reconstruction 14 car. : insee(5)+com_abs(3)+section(2)+numero(4)
    idu = _build_idu({"code_insee": "97411", "com_abs": "000", "section": "AC", "numero": "42"})
    assert idu == "97411000AC0042" and len(idu) == 14
    assert _build_idu({"section": "AC"}) is None  # infos insuffisantes


def test_parse_zones_gpu():
    fc = {"features": [
        {"properties": {"libelle": "U", "typezone": "U", "libelong": "Zone urbaine"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"properties": {"libelle": "A", "typezone": "A"}, "geometry": None},
    ]}
    zones = parse_zones(fc)
    assert zones[0]["typezone"] == "U" and zones[1]["libelle"] == "A"


def test_registry():
    c = get_connector("Cadastre (API Carto PCI)")
    assert c is not None and c.name == "Cadastre (API Carto PCI)"
    assert get_connector("inconnue") is None
