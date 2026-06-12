"""Audit pull (Lot A) — orchestration des 3 chemins, réseau MOCKÉ.

Vérifie : garde-fou commune (jamais d'évaluation hors pilote), ingestion avec origine='audit',
réutilisation du cache (aucun réseau au 2e appel), et le passage par LE pipeline existant
(une parcelle auditée est évaluée comme les autres). Le parsing API Carto et la cascade ont
déjà leurs propres tests ; ici on teste le câblage.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import audit

pytestmark = pytest.mark.db

# Parcelle Saint-Paul fictive (4326, près du centre) au format FeatureCollection API Carto.
_GEOM = {"type": "Polygon", "coordinates": [[
    [55.2700, -21.0100], [55.2705, -21.0100], [55.2705, -21.0095], [55.2700, -21.0095], [55.2700, -21.0100]]]}


def _fc(idu="97415000ZZ0001", insee="97415", section="ZZ", numero="0001"):
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature", "geometry": _GEOM,
        "properties": {"idu": idu, "code_insee": insee, "nom_com": "Saint-Paul",
                       "section": section, "numero": numero, "contenance": 1200}}]}


def test_reference_commune_gate_sans_reseau(db_session, monkeypatch):
    """Hors commune pilote → message propre, AUCUN appel réseau, AUCUNE évaluation."""
    def _boom(*a, **k):
        raise AssertionError("le réseau ne doit pas être appelé hors commune")
    monkeypatch.setattr("labuse.connectors.cadastre.CadastreConnector.fetch_by_section", _boom)
    r = audit.audit_by_reference(db_session, "AB", "1", code_insee="97411")
    assert r["ok"] is False and r["error"] == "commune_non_couverte"
    assert "Saint-Paul" in r["message"]


def test_reference_ingests_with_origine_audit_and_evaluates(db_session, monkeypatch):
    monkeypatch.setattr("labuse.connectors.cadastre.CadastreConnector.fetch_by_section",
                        lambda self, insee, section, numero=None: _fc())
    r = audit.audit_by_reference(db_session, "ZZ", "0001")
    assert r["ok"] and r["origine"] == "audit" and r["cached"] is False
    assert r["idu"] == "97415000ZZ0001" and r["status"] in (
        "opportunite", "a_creuser", "faux_positif_probable", "exclue")
    row = db_session.execute(text(
        """SELECT p.origine, p.commune, (SELECT count(*) FROM parcel_evaluations e WHERE e.parcel_id=p.id) n
           FROM parcels p WHERE p.idu='97415000ZZ0001'""")).one()
    assert row.origine == "audit" and row.commune == "Saint-Paul" and row.n == 1


def test_reference_second_call_is_cached_no_network(db_session, monkeypatch):
    monkeypatch.setattr("labuse.connectors.cadastre.CadastreConnector.fetch_by_section",
                        lambda self, insee, section, numero=None: _fc())
    audit.audit_by_reference(db_session, "ZZ", "0001")          # 1er : ingère
    def _boom(*a, **k):
        raise AssertionError("le 2e appel doit être servi par le cache")
    monkeypatch.setattr("labuse.connectors.cadastre.CadastreConnector.fetch_by_section", _boom)
    r = audit.audit_by_reference(db_session, "ZZ", "0001")      # 2e : cache
    assert r["ok"] and r["cached"] is True and r["idu"] == "97415000ZZ0001"


def test_reference_introuvable_au_cadastre(db_session, monkeypatch):
    monkeypatch.setattr("labuse.connectors.cadastre.CadastreConnector.fetch_by_section",
                        lambda self, insee, section, numero=None: {"type": "FeatureCollection", "features": []})
    r = audit.audit_by_reference(db_session, "ZZ", "9999")
    assert r["ok"] is False and r["error"] == "introuvable"


def test_address_out_of_commune(db_session, monkeypatch):
    """BAN renvoie une commune hors pilote → commune_non_couverte (pas de fetch cadastre)."""
    class _Resp:
        def raise_for_status(self): pass
        def json(self):
            return {"features": [{"geometry": {"type": "Point", "coordinates": [55.45, -20.88]},
                                  "properties": {"citycode": "97411", "city": "Saint-Denis",
                                                 "label": "Rue X Saint-Denis"}}]}
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k): return _Resp()
    monkeypatch.setattr("labuse.audit.httpx.Client", _Client)
    r = audit.audit_by_address(db_session, "Rue X Saint-Denis")
    assert r["ok"] is False and r["error"] == "commune_non_couverte" and "Saint-Denis" in r["message"]


def test_polygon_out_of_commune(db_session, monkeypatch):
    monkeypatch.setattr("labuse.connectors.cadastre.CadastreConnector.fetch_by_geom",
                        lambda self, geom: _fc(idu="97411000AB0001", insee="97411", section="AB"))
    poly = {"type": "Polygon", "coordinates": [[[55.45, -20.88], [55.46, -20.88],
                                                [55.46, -20.87], [55.45, -20.87], [55.45, -20.88]]]}
    r = audit.audit_by_polygon(db_session, poly)
    assert r["ok"] is False and r["error"] == "commune_non_couverte"
