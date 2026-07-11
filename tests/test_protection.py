"""Tests Lot 3 (wave-adresses) : quotas fiches, rate limiting, watermark, abuse-scan."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine, monkeypatch):
    from labuse import config
    from labuse.api import protection
    from labuse.api.app import app

    protection.ensure_tables(engine)
    with engine.begin() as c:
        for t in ("usage_compteurs", "consultation_log", "acces_gels", "admin_alertes",
                  "abuse_scores", "export_fingerprints"):
            c.execute(text(f"DELETE FROM {t}"))
    protection.reset_etat_memoire()
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    protection.reset_etat_memoire()
    config.get_settings.cache_clear()


def test_quota_fiches_gel_jusqua_minuit(client, engine, monkeypatch):
    """301e fiche distincte du jour → 429 (critère d'acceptation, ici quota réduit à 3)."""
    monkeypatch.setenv("LABUSE_QUOTA_FICHES_JOUR", "3")
    from labuse import config
    config.get_settings.cache_clear()

    for i in range(3):
        client.get(f"/parcels/97416000AA000{i}")          # 404 métier : compte quand même
    r = client.get("/parcels/97416000AA0009")
    assert r.status_code == 429
    assert "minuit" in r.json()["detail"]
    # une fiche DÉJÀ VUE aujourd'hui reste consultable (dédup par idu)
    r2 = client.get("/parcels/97416000AA0001")
    assert r2.status_code != 429
    with engine.connect() as c:
        n = c.execute(text("SELECT n FROM usage_compteurs WHERE kind = 'fiche'")).scalar()
    assert n == 3


def test_rate_limit_defi_puis_gel(client, monkeypatch, engine):
    """Burst → 429 + défi arithmétique ; bonne réponse → répit ; récidive → gel + alerte."""
    monkeypatch.setenv("LABUSE_RATE_LIMIT_RPM", "5")
    monkeypatch.setenv("LABUSE_RATE_BURST_GEL", "2")
    from labuse import config
    config.get_settings.cache_clear()

    for _ in range(5):
        client.get("/discover")
    r = client.get("/discover")
    assert r.status_code == 429 and "defi" in r.json()
    # les dépassements suivants restent le MÊME épisode (pas de sur-comptage)
    assert client.get("/discover").status_code == 429
    a, _, b = r.json()["defi"].partition(" + ")
    ok = client.post("/protection/defi", json={"reponse": int(a) + int(b)})
    assert ok.status_code == 200

    # défi résolu → fenêtre purgée, la limite normale reprend ; nouveau burst =
    # 2e ÉPISODE du jour → gel + alerte admin (seuil réglé à 2)
    for _ in range(6):
        client.get("/discover")
    r2 = client.get("/discover")
    assert r2.status_code == 429
    with engine.connect() as c:
        gels = c.execute(text("SELECT count(*) FROM acces_gels WHERE actif")).scalar()
        alertes = c.execute(text("SELECT count(*) FROM admin_alertes")).scalar()
    assert gels == 1 and alertes >= 1
    # sujet gelé → toute requête métier répond 429 gel
    r3 = client.get("/discover")
    assert r3.status_code == 429 and r3.json().get("gel") is True


def test_filigrane_export(db_session, engine):
    """Colonne ref + 2-3 canaris (micro-variations de voie) + export_fingerprints."""
    from labuse.api import protection

    protection.ensure_tables(engine)
    headers = ["Parcelle (IDU)", "Voie (BAN)", "Ville"]
    rows = [[f"97416000AA{i:04d}", "Rue des Tests", "Saint-Pierre"] for i in range(10)]
    ref = protection.filigrane_export(db_session, "s:test", headers, rows,
                                      slug="test-preset")
    assert headers[-1] == "ref" and all(r[-1] == ref for r in rows)
    fp = db_session.execute(text(
        "SELECT ref, n_lignes, canaris FROM export_fingerprints WHERE sujet = 's:test'"
    )).mappings().first()
    assert fp["ref"] == ref and fp["n_lignes"] == 10
    canaris = fp["canaris"] if isinstance(fp["canaris"], list) else json.loads(fp["canaris"])
    assert 1 <= len(canaris) <= 3
    variees = [r for r in rows if r[1] != "Rue des Tests"]
    assert len(variees) == len(canaris)       # variations réellement appliquées


def test_abuse_scan_sequences_regulieres(db_session, engine):
    """Séquence d'IDU consécutifs + cadence machinale + nocturne → score élevé + alerte."""
    from labuse.api import protection

    protection.ensure_tables(engine)
    hier = date.today() - timedelta(days=1)
    t0 = datetime.combine(hier, datetime.min.time(), tzinfo=timezone.utc)  # 04h Réunion
    for i in range(60):
        db_session.execute(text(
            "INSERT INTO consultation_log (ts, sujet, chemin, idu) "
            "VALUES (:ts, 's:robot', 'fiche', :idu)"),
            {"ts": t0 + timedelta(seconds=2 * i), "idu": f"97416000AA{i:04d}"})
    res = protection.scan_abus(db_session, hier)
    sc = res["scores"]["s:robot"]
    assert sc["seq_idu_max"] >= 10 and sc["score"] >= 60
    assert res["alertes"] >= 1
