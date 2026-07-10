"""Tests Lot 2B (wave-adresses) : courrier — stub, responsabilité, plafond, tarif."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import config, courrier
    from labuse.api.app import app
    courrier.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM courrier_envois"))
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_statut_stub_sans_compte(client):
    """Sans compte prestataire : disponible=false — le front N'AFFICHE PAS le bouton."""
    r = client.get("/courrier/statut").json()
    assert r["disponible"] is False and r["provider"] == "stub"
    assert "Merci Facteur" in r["raison"]
    # tarif = coût prestataire × marge (défauts : 2,69 × 1,5)
    assert r["tarif"]["prix_client_eur"] == round(2.69 * 1.5, 2)


def test_envoi_exige_responsabilite(client):
    r = client.post("/courrier/envois", json={
        "destinataires": [{"idu": "97416000AA0001", "adresse": "12 Rue X, 97410 Saint-Pierre"}],
        "assume_contenu": False})
    assert r.status_code == 422 and "responsabilité" in r.json()["detail"]


def test_envoi_stub_et_plafond(client, monkeypatch, engine):
    monkeypatch.setenv("LABUSE_COURRIER_MAX_JOUR", "2")
    from labuse import config
    config.get_settings.cache_clear()

    r = client.post("/courrier/envois", json={
        "destinataires": [
            {"idu": "97416000AA0001", "adresse": "12 Rue X, 97410 Saint-Pierre"},
            {"idu": "97416000AA0002", "adresse": "14 Rue X, 97410 Saint-Pierre"}],
        "modele": "renovation", "assume_contenu": True})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "stub"
    assert all(e["statut"] == "simule" for e in body["envois"])   # RIEN ne part en stub
    assert body["total_eur"] == round(2 * body["prix_unitaire_eur"], 2)

    # plafond/jour atteint → refus
    r2 = client.post("/courrier/envois", json={
        "destinataires": [{"idu": "97416000AA0003", "adresse": "16 Rue X, 97410 Saint-Pierre"}],
        "assume_contenu": True})
    assert r2.status_code == 422 and "Plafond" in r2.json()["detail"]

    # suivi
    suivi = client.get("/courrier/envois").json()
    assert suivi["n"] == 2 and suivi["envois"][0]["modele"] == "renovation"
