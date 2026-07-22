"""AUDIT PAIEMENT · PARTIE A — sécurité de l'accès (tests ADVERSARIAUX permanents).

Chaque test attaque une faille : s'il tombe, la cloison est ouverte. Ils RESTENT dans la
suite (régression). DB réelle (labuse_test), auth active, deux comptes réels.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db


@pytest.fixture
def app_client(engine, monkeypatch):
    """App en mode auth active (comme la prod) — cookie Secure → base https."""
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-audit")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-audit-000000000000000000")
    from labuse import config
    config.get_settings.cache_clear()
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def _compte_actif(email: str) -> int:
    """Crée + active un compte (paiement simulé : statut compte 'actif'), renvoie compte_id."""
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:
            pass
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-audit-1", "2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client: TestClient, email: str) -> TestClient:
    r = client.post("/login", data={"identifiant": email, "password": "motdepasse-audit-1"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    return client


def _purge(*emails):
    with session_scope() as s:
        for e in emails:
            try:
                comptes.supprimer_utilisateur(s, e)
            except Exception:
                pass


# ─────────────────────────── SEC-IDOR : cloison multi-tenant ───────────────────────────

def test_idor_projets_cloison_totale(app_client):
    """Compte A crée un projet ; compte B ne le voit, ni ne le lit, modifie, supprime,
    ou n'exporte via l'id d'URL — 404 partout, jamais une fuite."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver")
        cb = TestClient(app_client.app, base_url="https://testserver")
        _login(ca, ea); _login(cb, eb)

        # A crée un projet
        r = ca.post("/projets", json={"nom": "Secret de A", "fiche": {"type_programme": "logements"}})
        assert r.status_code == 200, r.text
        pid = r.json()["projet"]["id"]

        # A le voit dans SA liste
        assert any(p["id"] == pid for p in ca.get("/projets").json())
        # B ne le voit PAS
        assert all(p["id"] != pid for p in cb.get("/projets").json())
        # B ne peut ni lire, ni patcher, ni rejouer, ni supprimer, ni exporter (404)
        assert cb.get(f"/projets/{pid}").status_code == 404
        assert cb.patch(f"/projets/{pid}", json={"nom": "vol"}).status_code == 404
        assert cb.post(f"/projets/{pid}/rejouer").status_code == 404
        assert cb.get(f"/projets/{pid}/parcelles").status_code == 404
        assert cb.get(f"/projets/{pid}/export.pdf").status_code == 404
        assert cb.delete(f"/projets/{pid}").status_code == 404
        # A toujours intact après les tentatives de B
        assert ca.get(f"/projets/{pid}").status_code == 200
    finally:
        _purge(ea, eb)


def test_idor_pipeline_cloison_et_meme_parcelle(app_client):
    """Le CRM : B ne voit pas les pistes de A, ne peut pas les modifier/supprimer par id,
    et LES DEUX peuvent suivre la MÊME parcelle (la clé (compte, parcelle) le permet)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        idu = f"974990SEC{uuid.uuid4().hex[:5].upper()}"   # parcelle DÉDIÉE (nettoyée en finally)
        _wkt = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
        with session_scope() as s:
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
                " centroid, bbox) VALUES (:i,'X','ZZ','1', ST_GeomFromText(:w,4326),"
                " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
                " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                {"i": idu, "w": _wkt})
            s.commit()

        ra = ca.post("/pipeline", json={"idu": idu})
        assert ra.status_code == 200 and not ra.json()["already"], ra.text
        eid_a = ra.json()["entry"]["id"]
        # B suit LA MÊME parcelle → autorisé (plus de UNIQUE(parcel_id) global), entrée distincte
        rb = cb.post("/pipeline", json={"idu": idu})
        assert rb.status_code == 200 and not rb.json()["already"], rb.text
        assert rb.json()["entry"]["id"] != eid_a

        # B ne voit pas la piste de A ; ne peut pas la patcher/supprimer
        assert all(e["id"] != eid_a for e in cb.get("/pipeline").json())
        assert cb.patch(f"/pipeline/{eid_a}", json={"priority": "haute"}).status_code == 404
        assert cb.delete(f"/pipeline/{eid_a}").status_code == 404
        # la parcelle vue par A reste « in_pipeline » pour A, indépendamment de B
        assert ca.get(f"/pipeline/parcel/{idu}").json()["in_pipeline"] is True
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu}); s.commit()


def test_idor_veilles_cloison(app_client):
    """Veilles (recherches sauvegardées) : B ne voit pas celles de A, ni ne les supprime."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        assert ca.post("/events/searches", json={"nom": "veille A", "hash": "#f=1"}).status_code == 200
        mine = ca.get("/events/searches").json()
        assert len(mine) == 1 and mine[0]["nom"] == "veille A"
        sid = mine[0]["id"]
        # B ne voit rien, et un DELETE ciblé sur l'id de A ne détruit rien chez A
        assert cb.get("/events/searches").json() == []
        cb.delete(f"/events/searches/{sid}")
        assert len(ca.get("/events/searches").json()) == 1   # intacte
    finally:
        _purge(ea, eb)
