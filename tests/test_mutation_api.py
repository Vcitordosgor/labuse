"""API Radar Mutation (lecture seule) — endpoints `/mutation/{idu}` et `/mutation`.

Vérifie le câblage, la structure JSON explicable, le 404, le tri/limite de la liste et
l'absence d'écriture DB. La correction de la FORMULE est couverte par test_mutation.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

pytestmark = pytest.mark.db

NIVEAUX = {"prioritaire", "forte", "surveiller", "faible"}


@pytest.fixture(scope="module")
def client(engine):
    from labuse import models
    from labuse.ai import StubProvider
    from labuse.api.app import app
    from labuse.cascade import evaluate_parcels
    from labuse.db import session_scope
    from labuse.ingestion import demo_saint_paul, seed_sources

    with session_scope() as s:
        seed_sources.seed(s)
        demo_saint_paul.seed_demo(s)
        ids = [r[0] for r in s.execute(select(models.Parcel.id)).all()]
        evaluate_parcels(ids, s, persist=True, ai_provider=StubProvider())
    try:
        yield TestClient(app)
    finally:
        with session_scope() as s:
            demo_saint_paul.reset_demo(s)


def _valid_mutation(m: dict) -> None:
    assert set(m) >= {"score_mutation", "niveau", "confiance", "badges", "raisons", "limites"}
    assert 0 <= m["score_mutation"] <= 100
    assert m["niveau"] in NIVEAUX
    assert isinstance(m["badges"], list) and isinstance(m["raisons"], list)
    assert any("garanties" in x for x in m["limites"])   # wording prudent toujours présent


def test_mutation_parcel_structure(client):
    r = client.get("/mutation/97415000AB0001")
    assert r.status_code == 200
    body = r.json()
    assert body["idu"] == "97415000AB0001" and body["commune"]
    _valid_mutation(body["mutation"])


def test_mutation_parcel_404(client):
    assert client.get("/mutation/00000000000000").status_code == 404


def test_mutation_top_limite_et_tri(client):
    r = client.get("/mutation", params={"commune": "Saint-Paul", "limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["commune"] == "Saint-Paul"
    assert body["count"] <= 3 and len(body["parcels"]) == body["count"]
    scores = [p["score_mutation"] for p in body["parcels"]]
    assert scores == sorted(scores, reverse=True)        # trié décroissant
    for p in body["parcels"]:
        assert "idu" in p
        _valid_mutation(p)


def test_mutation_top_filtre_niveau(client):
    r = client.get("/mutation", params={"commune": "Saint-Paul", "niveau": "faible", "limit": 10})
    assert r.status_code == 200
    assert all(p["niveau"] == "faible" for p in r.json()["parcels"])


def test_mutation_aucune_ecriture_db(client):
    from labuse.db import session_scope

    with session_scope() as s:
        before = s.execute(text("SELECT count(*) FROM parcel_evaluations")).scalar()
    client.get("/mutation/97415000AB0001")
    client.get("/mutation", params={"commune": "Saint-Paul", "limit": 5})
    with session_scope() as s:
        after = s.execute(text("SELECT count(*) FROM parcel_evaluations")).scalar()
    assert before == after   # endpoints lecture seule : aucune écriture
