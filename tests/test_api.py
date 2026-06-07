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


def test_coverage_banner(client):
    cov = client.get("/coverage").json()
    assert {"critical_layers", "missing", "complete", "reliable_ready"} <= set(cov)
    kinds = {x["kind"] for x in cov["critical_layers"]}
    assert kinds == {"sar", "risques", "foret_publique", "ens", "safer", "trait_de_cote"}
    assert isinstance(cov["reliable_ready"], bool)


def test_limit_negatif_rejete_en_422(client):
    # M3 : un limit négatif doit renvoyer un 422 propre (pas un 500 Postgres).
    assert client.get("/map/parcels.geojson", params={"limit": -5}).status_code == 422
    assert client.get("/signals", params={"limit": -5}).status_code == 422
    assert client.get("/discover", params={"limit": -5}).status_code == 422


def test_feedback_terrain_decote_le_score(client):
    # Retour « faux positif » sur une zone → décote le score d'opportunité (§10, zone).
    idu = "97415000AB0001"
    before = client.get(f"/parcels/{idu}").json()["verdict"]["opportunity_score"]
    client.post("/feedback", json={"idu": idu, "verdict": "false_positive", "comment": "déjà bâti (visite)"})
    after = client.post(f"/parcels/{idu}/evaluate").json()["opportunity_score"]
    assert after < before  # la zone faux-positif décote le score d'opportunité


def test_permit_idu_reconstruction():
    from labuse.ingestion.permits import _idu
    assert _idu("97415", "CV", "984") == "97415000CV0984"
    assert _idu("97415", "AH", "1017") == "97415000AH1017"
    assert _idu("97415", None, "1") is None


def test_watch_snapshot_delta_zonage(client):
    from sqlalchemy import text

    from labuse.db import session_scope
    from labuse.ingestion import signals

    with session_scope() as s:
        r1 = signals.run_watch(s, "Saint-Paul")
    assert r1["baseline"] is True and r1["signals_total"] == 0  # 1er run = photo de référence

    with session_scope() as s:  # simule une révision de zonage PLU (N → U)
        s.execute(text("UPDATE spatial_layers SET subtype='U' WHERE kind='plu_gpu_zone' AND subtype='N'"))

    with session_scope() as s:
        r2 = signals.run_watch(s, "Saint-Paul")
    assert r2["baseline"] is False
    assert r2["zonage_change"] >= 1 and r2["reevaluated"] >= 1  # delta détecté + ré-évaluation

    sig = client.get("/signals", params={"commune": "Saint-Paul", "signal_type": "zonage_change"}).json()
    assert sig and sig[0]["signal_type"] == "zonage_change" and sig[0]["payload"]["to"] == "U"
