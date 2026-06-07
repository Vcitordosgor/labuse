"""Tests de l'API (TestClient) sur le jeu de démo Saint-Paul (PostGIS réel)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

pytestmark = pytest.mark.db


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


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_sources_page(client):
    srcs = client.get("/sources").json()
    assert len(srcs) >= 24
    assert all("status" in s and "reliability_level" in s for s in srcs)
    assert any(s["testable"] for s in srcs)  # au moins un connecteur live


def test_source_test_sans_connecteur(client):
    """Une source sans connecteur live répond proprement (sans réseau)."""
    srcs = client.get("/sources").json()
    ff = next(s for s in srcs if s["name"] == "Fichiers fonciers (Cerema)")
    res = client.post(f"/sources/{ff['id']}/test").json()
    assert res["ok"] is False and "connecteur" in res["message"].lower()


def test_fiche_double_score_et_cascade(client):
    f = client.get("/parcels/97415000AB0001").json()
    assert f["verdict"]["status"] == "opportunite"
    # Règle d'or : les DEUX scores présents
    assert f["verdict"]["opportunity_score"] is not None
    assert f["verdict"]["completeness_score"] is not None
    assert len(f["cascade"]) > 10
    assert f["sources_responded"] and f["ai"]["recommended_status"] == "opportunite"
    assert "jamais garanties" in f["disclaimer"]


def test_fiche_404(client):
    assert client.get("/parcels/00000000000000").status_code == 404


def test_export_markdown_et_html(client):
    md = client.get("/parcels/97415000AB0001/export", params={"format": "md"})
    assert md.status_code == 200 and "# LA BUSE" in md.text and "Cascade" in md.text
    htmlr = client.get("/parcels/97415000AB0001/export", params={"format": "html"})
    assert htmlr.status_code == 200 and "<table" in htmlr.text


def test_discover_classe_les_survivantes(client):
    disc = client.get("/discover").json()
    idus = [d["idu"] for d in disc]
    assert "97415000AB0001" in idus  # opportunité présente
    # aucune exclue/faux positif dans la découverte
    assert all(d["status"] in ("opportunite", "a_creuser") for d in disc)
    # classées par opportunité décroissante
    scores = [d["opportunity_score"] for d in disc]
    assert scores == sorted(scores, reverse=True)


def test_feedback(client):
    r = client.post("/feedback", json={"idu": "97415000AB0001", "verdict": "good_lead"})
    assert r.json()["ok"] is True


def test_stats_endpoint(client):
    s = client.get("/stats", params={"commune": "Saint-Paul"}).json()
    assert s["total"] >= 8
    assert s["opportunite"] + s["a_creuser"] + s["exclue"] <= s["total"]


def test_map_geojson(client):
    fc = client.get("/map/parcels.geojson", params={"commune": "Saint-Paul"}).json()
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) >= 8
    props = fc["features"][0]["properties"]
    assert props["idu"] and "status" in props and "opportunity_score" in props
    assert fc["features"][0]["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_front_served(client):
    assert client.get("/", follow_redirects=False).status_code in (302, 307)
    idx = client.get("/app/")
    assert idx.status_code == 200 and "LA" in idx.text


def test_feedback_reinjecte_dans_le_scoring(client):
    # Retour « faux positif » sur une opportunité → rétrogradée à la ré-évaluation (§10).
    idu = "97415000AB0001"
    client.post("/feedback", json={"idu": idu, "verdict": "false_positive"})
    r = client.post(f"/parcels/{idu}/evaluate").json()
    assert r["status"] == "faux_positif_probable"


def test_veille_signaux_idempotente(client):
    from labuse.db import session_scope
    from labuse.ingestion import signals

    with session_scope() as s:
        c1 = signals.generate_signals(s, "Saint-Paul")
    with session_scope() as s:
        c2 = signals.generate_signals(s, "Saint-Paul")
    assert set(c1) == {"mutation_dvf", "new_permit_nearby", "zonage_change"}
    assert c1 == c2  # purge avant regénération → idempotent
    assert isinstance(client.get("/signals", params={"commune": "Saint-Paul"}).json(), list)
