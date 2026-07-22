"""Tests authentification PILOTE : sessions, cookies, fail-closed, readyz réduit.

La config est rechargée par fixture (env vars) — l'app lit les settings À CHAQUE requête
dans le middleware, donc le basculement local/pilot est testable sans redémarrer l'app.
"""
from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db   # readyz touche la DB ; le reste s'en passe mais partage la fixture


@pytest.fixture
def client(engine):
    from labuse.api.app import app

    # base_url https : en pilote le cookie est Secure → le jar httpx ne l'enverrait pas
    # sur http (comportement navigateur fidèle ; en réel : reverse proxy HTTPS, documenté).
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def pilot(monkeypatch):
    """Active le mode pilote : auth obligatoire, cookie Secure, docs protégés."""
    from labuse import config

    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "mot-de-passe-pilote")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "clef-de-test-stable")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def _login(client, password="mot-de-passe-pilote"):
    return client.post("/login", content=f"password={password}",
                       headers={"content-type": "application/x-www-form-urlencoded"},
                       follow_redirects=False)


# ───────────────────────── Local (défaut) : auth désactivée ─────────────────────────

def test_local_par_defaut_tout_ouvert(client):
    # Rétro-compatibilité : sans LABUSE_AUTH_PASSWORD ni env pilote, rien ne change.
    assert client.get("/pipeline/meta").status_code == 200
    assert client.get("/login", follow_redirects=False).status_code == 302  # rien à demander


# ───────────────────────── Pilote : protection effective ─────────────────────────

def test_sans_session_api_401_et_pages_redirigees(client, pilot):
    assert client.get("/pipeline/meta").status_code == 401          # API → 401 JSON
    assert client.get("/stats").status_code == 401
    r = client.get("/", follow_redirects=False)                     # navigation → /login
    assert r.status_code == 302 and r.headers["location"] == "/login"
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert client.get("/demo-status").status_code == 401
    assert client.get("/docs").status_code in (302, 401)            # docs protégés hors local


def test_healthz_reste_public(client, pilot):
    assert client.get("/healthz").status_code == 200
    assert client.get("/health").status_code == 200


def test_mauvais_mot_de_passe_refus_neutre(client, pilot):
    r = _login(client, password="totalement-faux")
    assert r.status_code == 401
    assert "Identifiants invalides" in r.text                       # message NEUTRE
    assert "labuse_session" not in r.headers.get("set-cookie", "")


def test_login_ok_cookie_securise_puis_acces(client, pilot):
    r = _login(client)
    assert r.status_code == 303 and r.headers["location"] == "/"
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=lax" in sc and "secure" in sc   # pilote = Secure
    assert client.get("/pipeline/meta").status_code == 200          # cookie conservé par TestClient
    assert client.get("/stats").status_code == 200


def test_logout_ferme_la_session(client, pilot):
    _login(client)
    assert client.get("/pipeline/meta").status_code == 200
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert client.get("/pipeline/meta").status_code == 401


def test_session_falsifiee_refusee(client, pilot):
    client.cookies.set("labuse_session", "v1.9999999999.deadbeef")  # signature invalide
    assert client.get("/pipeline/meta").status_code == 401


def test_readyz_public_mais_reduit_sans_session(client, pilot):
    r = client.get("/readyz")
    assert r.status_code in (200, 503)                              # public (monitoring)
    js = r.json()
    assert set(js) == {"ready", "checked_at"}                       # AUCUN détail sensible
    _login(client)
    full = client.get("/readyz").json()
    assert {"schema", "data", "actions"} <= set(full)               # détails avec session


def test_fail_closed_pilote_sans_mot_de_passe(client, monkeypatch):
    from labuse import config

    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.delenv("LABUSE_AUTH_PASSWORD", raising=False)
    config.get_settings.cache_clear()
    try:
        r = client.get("/pipeline/meta")
        assert r.status_code == 503                                 # fermé, jamais ouvert par accident
        assert "non configurée" in r.json()["detail"]
        assert client.get("/healthz").status_code == 200            # le monitoring vit toujours
    finally:
        config.get_settings.cache_clear()


def test_mot_de_passe_hash_sha256_supporte(client, monkeypatch):
    from labuse import config

    digest = hashlib.sha256(b"secret-hashe").hexdigest()
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", f"sha256:{digest}")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "clef-de-test-stable")
    config.get_settings.cache_clear()
    try:
        assert _login(client, "mauvais").status_code == 401
        assert _login(client, "secret-hashe").status_code == 303    # le hash matche le mot de passe
    finally:
        config.get_settings.cache_clear()
