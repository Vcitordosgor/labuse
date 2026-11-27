"""PPR zoné + aléas DEAL Réunion — mapping subtype/niveau, fallback PM1, lecture casse réelle,
construction requête fetch_layer (P1/P2). Mock WFS/HTTP, ZÉRO réseau/base."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from labuse.ingestion import layers_ingest
from labuse.ingestion.layers_ingest import _normalise_alea, _prop

_GEOM = {"type": "MultiPolygon", "coordinates": [[[[55.4, -20.9], [55.5, -20.9], [55.5, -21.0], [55.4, -20.9]]]]}


def _install(monkeypatch, by_typename):
    """Mocke WfsConnector (réseau) + _insert_layer (base). Renvoie (inserted, calls)."""
    inserted: list[dict] = []
    calls: list[dict] = []

    class FakeWfs:
        def __init__(self, *a, **k):
            pass

        def fetch_layer(self, endpoint_key, typename, bbox=None, max_features=1000,
                        start_index=0, sort_by=None, exp_filter=None):
            calls.append({"typename": typename, "exp_filter": exp_filter})
            return {"features": by_typename.get(typename, [])}

    monkeypatch.setattr(layers_ingest, "WfsConnector", FakeWfs)
    monkeypatch.setattr(layers_ingest, "_insert_layer",
                        lambda session, kind, subtype, name, geom, src, commune, run_id, attrs:
                        inserted.append({"kind": kind, "subtype": subtype, "name": name, "attrs": attrs}))
    return inserted, calls


def _ppr(degre, code_degre):
    # casse RÉELLE (test à blanc) : DEGRE/CODE_DEGRE/CODE_INSEE/RISQUE/DOCUMENT/APPROBATIO (MAJUSCULES).
    return {"geometry": _GEOM, "properties": {
        "DEGRE": degre, "CODE_DEGRE": code_degre, "RISQUE": "INONDATION_MOUVEMENT_DE_TERRAIN",
        "CODE_INSEE": "97411", "DOCUMENT": "PPR", "APPROBATIO": "2012-10-17"}}


def _alea(degre, code_degre):
    # casse RÉELLE (test à blanc) : Degre/Code_degre/Risque/Theme (mixte), CODE_INSEE (MAJUSCULES).
    return {"geometry": _GEOM, "properties": {
        "Degre": degre, "Code_degre": code_degre, "Risque": "INONDATION",
        "Theme": "ALEA", "CODE_INSEE": "97411"}}


# ── PPR zoné : subtype = DEGRE (rouge/bleu) ───────────────────────────────────
def test_ppr_zone_subtype_degre(monkeypatch):
    feats = [_ppr("INTERDICTION", "R1"), _ppr("INTERDICTION", "R2"),
             _ppr("PRESCRIPTION", "B2"), _ppr("PRESCRIPTION", "rB2")]
    session = MagicMock()
    session.execute.return_value.scalar.return_value = False
    monkeypatch.setattr(layers_ingest, "_rafraichir_derives_risque", lambda *args: None)
    inserted, calls = _install(monkeypatch, {"PPR_APPROUVE": feats})
    n = layers_ingest.ingest_ppr_zone(session, (0, 0, 1, 1), "Saint-Denis", 1, {layers_ingest.KIND_SOURCE["ppr"]: 1}, "97411")
    assert n == 4
    assert all(i["kind"] == "ppr" for i in inserted)
    subtypes = [i["subtype"] for i in inserted]
    assert subtypes.count("INTERDICTION") == 2 and subtypes.count("PRESCRIPTION") == 2
    assert inserted[0]["attrs"]["code_degre"] == "R1"
    assert inserted[0]["attrs"]["code_insee"] == "97411"     # lu via _prop (CODE_INSEE MAJ)
    assert inserted[0]["attrs"]["statut"] == "zonage_reglementaire"
    assert calls[0]["exp_filter"] == "CODE_INSEE = '97411'"   # filtre WFS bien passé


@pytest.mark.parametrize("geom,degre", [(None, "INTERDICTION"), (_GEOM, "")])
def test_zonage_incomplet_preserve_la_couche(monkeypatch, geom, degre):
    feat = {"geometry": geom, "properties": {"CODE_INSEE": "97411", "DEGRE": degre}}
    inserted, _ = _install(monkeypatch, {"PPR_APPROUVE": [feat]})
    session = MagicMock()
    with pytest.raises(ValueError, match="géométrie ou degré absent"):
        layers_ingest.ingest_ppr_zone(session, None, "Saint-Denis", 1, {}, "97411")
    session.execute.assert_not_called()
    assert not inserted


def test_zonage_vide_preserve_la_couche(monkeypatch):
    inserted, _ = _install(monkeypatch, {"PPR_APPROUVE": []})
    session = MagicMock()
    with pytest.raises(ValueError, match="Zonage PPR DEAL vide"):
        layers_ingest.ingest_ppr_zone(session, None, "Cilaos", 1, {}, "97414")
    session.execute.assert_not_called()
    assert not inserted


# ── Aléas : normalisation niveau + résiduel + lecture casse mixte ─────────────
def test_normalise_alea_mapping():
    assert _normalise_alea("FAIBLE") == ("faible", False)
    assert _normalise_alea("MOYEN") == ("moyen", False)
    assert _normalise_alea("FORT") == ("fort", False)
    assert _normalise_alea("RESIDUEL_MOYEN") == ("moyen", True)
    assert _normalise_alea("RESIDUEL_FORT") == ("fort", True)
    assert _normalise_alea("RESIDUEL_FORT_AGGRAVE") == ("fort", True)
    assert _normalise_alea(None) == ("moyen", False)              # défaut prudent


def test_georisque_alea_insert(monkeypatch):
    inond = [_alea("FAIBLE", "1"), _alea("FORT", "3"), _alea("RESIDUEL_FORT", "rD3")]
    inserted, calls = _install(monkeypatch, {"ALEA_INONDATION": inond, "ALEA_MOUVEMENT_TERRAIN": [_alea("FORT", "3")]})
    session = MagicMock()
    session.execute.return_value.scalar.return_value = False
    monkeypatch.setattr(layers_ingest, "_rafraichir_derives_risque", lambda *args: None)
    n = layers_ingest.ingest_georisque_alea(session, None, "Saint-Denis", 1,
                                           {layers_ingest.KIND_SOURCE["georisque_alea"]: 1}, "97411")
    assert n == 4 and inserted[-1]["subtype"] == "mouvement_terrain"
    inserted = inserted[:3]
    assert all(i["kind"] == "georisque_alea" and i["subtype"] == "inondation" for i in inserted)
    assert [(i["attrs"]["niveau"], i["attrs"]["residuel"]) for i in inserted] == \
           [("faible", False), ("fort", False), ("fort", True)]
    # P3 : malgré la casse mixte (Degre/Code_degre/CODE_INSEE), _prop lit bien les champs.
    assert inserted[0]["attrs"]["degre"] == "FAIBLE"
    assert inserted[0]["attrs"]["code_degre"] == "1"
    assert inserted[0]["attrs"]["code_insee"] == "97411"
    # SOURCES-2 lot 3 — + les deux couches submersion marine (PPRL vecteur, même WFS Lizmap).
    assert [c["typename"] for c in calls] == [
        "ALEA_INONDATION", "ALEA_MOUVEMENT_TERRAIN",
        "Alea_submersion_marine", "Alea_submersion_marine__changement_climatique"]
    assert "97400" in calls[0]["exp_filter"]
    assert all(c["exp_filter"] == "code_insee = '97411'" for c in calls[1:])


# ── P3 : _prop insensible à la casse (PPR MAJ vs ALEA mixte) ──────────────────
def test_prop_case_insensitive():
    ppr = {"DEGRE": "INTERDICTION", "CODE_INSEE": "97411"}                 # casse PPR
    alea = {"Degre": "FORT", "Code_degre": "3", "CODE_INSEE": "97411"}     # casse ALEA
    assert _prop(ppr, "degre") == "INTERDICTION" and _prop(ppr, "code_insee") == "97411"
    assert _prop(alea, "degre") == "FORT" and _prop(alea, "code_degre") == "3"
    assert _prop(alea, "code_insee") == "97411"
    assert _prop({}, "degre") is None


# ── P1+P2 : construction réelle de la requête fetch_layer (mock client, zéro réseau) ──
def _capture_fetch(monkeypatch, endpoint_key, typename, **kw):
    from labuse.connectors import wfs as wfsmod
    cap: dict = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"features": []}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            cap["url"], cap["params"] = url, params
            return _Resp()

    conn = wfsmod.WfsConnector(endpoint_key)
    monkeypatch.setattr(conn, "_client", lambda: _Client())
    conn.fetch_layer(endpoint_key, typename, **kw)
    return cap["url"], cap["params"]


def test_fetch_layer_geoplateforme_2_0_0_retrocompat(monkeypatch):
    # endpoint SANS query string → version 2.0.0, typeNames + count (comportement BD TOPO inchangé).
    url, p = _capture_fetch(monkeypatch, "geoplateforme_wfs", "BDTOPO_V3:batiment",
                            max_features=5000, start_index=10000, sort_by="cleabs")
    assert url == "https://data.geopf.fr/wfs/ows"
    assert p["version"] == "2.0.0" and p["typeNames"] == "BDTOPO_V3:batiment" and p["count"] == 5000
    assert "typeName" not in p and "maxFeatures" not in p
    assert p["startIndex"] == 10000 and p["sortBy"] == "cleabs"
    assert p["outputFormat"] == "application/json"


def test_fetch_layer_deal_1_1_0_preserve_query(monkeypatch):
    # P1 : repository/project réinjectés ; P2 : version 1.1.0 → typeName + maxFeatures.
    url, p = _capture_fetch(monkeypatch, "deal_reunion", "PPR_APPROUVE",
                            exp_filter="CODE_INSEE = '97411'")
    assert "?" not in url                                       # query déplacée dans params
    assert p["repository"] == "02sprinr" and p["project"] == "01risque"
    assert p["version"] == "1.1.0" and p["typeName"] == "PPR_APPROUVE" and p["maxFeatures"] == 1000
    assert "typeNames" not in p and "count" not in p
    assert p["EXP_FILTER"] == "CODE_INSEE = '97411'" and p["outputFormat"] == "GeoJSON"
