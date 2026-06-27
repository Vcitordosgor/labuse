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


# ── Phase 2D : durcissement des paramètres ────────────────────────────────────────────────

def test_mutation_niveau_invalide_422(client):
    r = client.get("/mutation", params={"commune": "Saint-Paul", "niveau": "bidon"})
    assert r.status_code == 422                     # avant 2D : 200 + liste vide silencieuse
    assert "niveau" in r.json()["detail"].lower()


def test_mutation_niveaux_valides_ok(client):
    from labuse.mutation import NIVEAUX

    for niv in NIVEAUX:
        assert client.get("/mutation", params={"commune": "Saint-Paul", "niveau": niv}).status_code == 200


def test_mutation_commune_inconnue_404(client):
    r = client.get("/mutation", params={"commune": "Atlantis-sur-Mer"})
    assert r.status_code == 404
    assert "commune" in r.json()["detail"].lower()


def test_mutation_limit_min_score_bornes(client):
    assert client.get("/mutation", params={"commune": "Saint-Paul", "limit": 999}).status_code == 422
    assert client.get("/mutation", params={"commune": "Saint-Paul", "limit": 0}).status_code == 422
    assert client.get("/mutation", params={"commune": "Saint-Paul", "min_score": 250}).status_code == 422


# ── Phase 2D : cache mémoire TTL (lecture seule, résultat identique) ───────────────────────

def test_mutation_top_cache_coherent(client):
    from labuse import mutation as mut

    mut.clear_top_cache()
    p = {"commune": "Saint-Paul", "niveau": "faible", "limit": 5}
    a = client.get("/mutation", params=p).json()
    assert len(mut._TOP_CACHE) >= 1                 # le calcul a bien été mémorisé
    b = client.get("/mutation", params=p).json()    # 2ᵉ appel : servi par le cache
    assert a == b                                   # résultat strictement identique (même top, mêmes scores)
    mut.clear_top_cache()
    assert len(mut._TOP_CACHE) == 0                 # invalidation manuelle fonctionnelle


# ── Phase 2D : calque carte Radar (GeoJSON lecture seule, fondation Phase 2E) ──────────────

def test_mutation_geojson_structure(client):
    r = client.get("/map/mutation.geojson", params={"commune": "Saint-Paul", "niveau": "faible", "limit": 20})
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection" and isinstance(fc["features"], list)
    for ft in fc["features"]:
        assert ft["type"] == "Feature" and ft["geometry"] and "coordinates" in ft["geometry"]
        pr = ft["properties"]
        assert "idu" in pr and pr["niveau"] in NIVEAUX and 0 <= pr["score_mutation"] <= 100


def test_mutation_geojson_durci(client):
    assert client.get("/map/mutation.geojson", params={"niveau": "bidon"}).status_code == 422
    assert client.get("/map/mutation.geojson", params={"commune": "Atlantis-sur-Mer"}).status_code == 404
    assert client.get("/map/mutation.geojson", params={"limit": 9999}).status_code == 422
