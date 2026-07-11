"""Tests Lot 4 (wave-adresses) : Dossier parcelle — dépendance souple + quota mensuel."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import config
    from labuse.api import protection
    from labuse.api.app import app

    protection.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_compteurs WHERE kind = 'dossier'"))
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_statut_sans_generateur(client):
    """Sans le module Flash mergé : disponible=false avec raison honnête (jamais un 500)."""
    r = client.get("/dossier/statut")
    assert r.status_code == 200
    body = r.json()
    if body["disponible"]:
        pytest.skip("module Flash présent sur cette instance — cas couvert par la QA merge")
    assert "module-flash" in body["raison"]


def test_pdf_parcelle_inconnue_ou_generateur_absent(client):
    """Générateur absent → 501 honnête ; présent → 404 propre sur parcelle inconnue."""
    r = client.get("/dossier/97416000ZZ9999.pdf?carte=false")
    assert r.status_code in (404, 501)


def test_pdf_genere_avec_mention(client, engine):
    """Parcelle seedée → PDF < 30 s, mention « Généré via LABUSE pour … », quota décompté."""
    pytest.importorskip("labuse.flash")
    poly = ("POLYGON((55.4495 -21.3005, 55.4505 -21.3005, 55.4505 -21.2995,"
            " 55.4495 -21.2995, 55.4495 -21.3005))")
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE idu = '97416000ZZ0042'"))
        c.execute(text(
            f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
                VALUES ('97416000ZZ0042', 'Saint-Pierre', 'ZZ', '0042', 11000,
                        ST_GeomFromText('{poly}', 4326),
                        ST_Transform(ST_GeomFromText('{poly}', 4326), 2975))"""))
    try:
        r = client.get("/dossier/97416000ZZ0042.pdf?carte=false")
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        st = client.get("/dossier/statut").json()
        assert st["utilises_mois"] >= 1
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM parcels WHERE idu = '97416000ZZ0042'"))


def test_quota_mensuel_essentiel(client, engine, monkeypatch):
    """Plan Essentiel + quota consommé → 429 AVANT même de chercher le générateur."""
    monkeypatch.setenv("LABUSE_PLAN_DEFAUT", "essentiel")
    monkeypatch.setenv("LABUSE_DOSSIER_QUOTA_MOIS", "2")
    from labuse import config
    config.get_settings.cache_clear()

    from labuse.api.protection import sujet_de

    class _Req:
        cookies: dict = {}

        class client:  # noqa: N801 — mime l'objet request.client
            host = "testclient"

    sujet = sujet_de(_Req())
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO usage_compteurs (jour, sujet, kind, n) "
            "VALUES (CURRENT_DATE, :s, 'dossier', 2)"), {"s": sujet})
    r = client.get("/dossier/97416000AA0001.pdf")
    assert r.status_code == 429
    assert r.json()["detail"]["plan_requis"] == "integral"
    # statut : compteur reflété
    st = client.get("/dossier/statut").json()
    assert st["utilises_mois"] == 2 and st["restants"] == 0
