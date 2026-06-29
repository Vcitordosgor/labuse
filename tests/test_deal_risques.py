"""PPR zoné + aléas DEAL Réunion — mapping subtype/niveau, fallback PM1. Mock WFS, ZÉRO réseau/base."""
from __future__ import annotations

from labuse.ingestion import layers_ingest
from labuse.ingestion.layers_ingest import _normalise_alea

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
    return {"geometry": _GEOM, "properties": {
        "DEGRE": degre, "CODE_DEGRE": code_degre, "RISQUE": "INONDATION_MOUVEMENT_DE_TERRAIN",
        "CODE_INSEE": "97411", "DOCUMENT": "PPR SD", "APPROBATIO": "2021-01-01"}}


def _alea(degre, code_degre):
    return {"geometry": _GEOM, "properties": {
        "degre": degre, "code_degre": code_degre, "risque": "inondation", "code_insee": "97411"}}


# ── PPR zoné : subtype = DEGRE (rouge/bleu) ───────────────────────────────────
def test_ppr_zone_subtype_degre(monkeypatch):
    feats = [_ppr("INTERDICTION", "R1"), _ppr("INTERDICTION", "R2"),
             _ppr("PRESCRIPTION", "B2"), _ppr("PRESCRIPTION", "rB2")]
    inserted, calls = _install(monkeypatch, {"PPR_APPROUVE": feats})
    n = layers_ingest.ingest_ppr_zone(None, (0, 0, 1, 1), "Saint-Denis", 1, {}, "97411")
    assert n == 4
    assert all(i["kind"] == "ppr" for i in inserted)
    subtypes = [i["subtype"] for i in inserted]
    assert subtypes.count("INTERDICTION") == 2 and subtypes.count("PRESCRIPTION") == 2
    assert inserted[0]["attrs"]["code_degre"] == "R1"
    assert inserted[0]["attrs"]["statut"] == "zonage_reglementaire"
    assert calls[0]["exp_filter"] == "CODE_INSEE = '97411'"        # filtre WFS bien passé


def test_ppr_zone_ignore_sans_degre_ou_geom(monkeypatch):
    feats = [_ppr("INTERDICTION", "R1"),
             {"geometry": _GEOM, "properties": {"DEGRE": ""}},                 # pas de degré
             {"geometry": None, "properties": {"DEGRE": "PRESCRIPTION"}}]      # pas de géométrie
    inserted, _ = _install(monkeypatch, {"PPR_APPROUVE": feats})
    n = layers_ingest.ingest_ppr_zone(None, (0, 0, 1, 1), "Saint-Denis", 1, {}, "97411")
    assert n == 1


def test_ppr_zone_fallback_pm1_si_zero_deal(monkeypatch):
    inserted, _ = _install(monkeypatch, {"PPR_APPROUVE": []})                  # DEAL ne renvoie rien
    monkeypatch.setattr(layers_ingest, "ingest_ppr_sup",
                        lambda session, bbox, commune, run_id, sids: 7)
    n = layers_ingest.ingest_ppr_zone(None, (0, 0, 1, 1), "Cilaos", 1, {}, "97414")
    assert n == 7 and inserted == []          # repli PM1 appelé, aucune insertion DEAL


# ── Aléas : normalisation niveau + résiduel ───────────────────────────────────
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
    inserted, calls = _install(monkeypatch, {"ALEA_INONDATION": inond, "ALEA_MOUVEMENT_TERRAIN": []})
    n = layers_ingest.ingest_georisque_alea(None, (0, 0, 1, 1), "Saint-Denis", 1, {}, "97411")
    assert n == 3
    assert all(i["kind"] == "georisque_alea" and i["subtype"] == "inondation" for i in inserted)
    assert [(i["attrs"]["niveau"], i["attrs"]["residuel"]) for i in inserted] == \
           [("faible", False), ("fort", False), ("fort", True)]
    assert [c["typename"] for c in calls] == ["ALEA_INONDATION", "ALEA_MOUVEMENT_TERRAIN"]
    assert all(c["exp_filter"] == "code_insee = '97411'" for c in calls)
