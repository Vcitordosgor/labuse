"""Tests authentification : garde globale, sessions, cookies, fail-closed, readyz réduit.

POST-DEPLOY-1 (décision Vic) — le compte « pilote » PARTAGÉ est SUPPRIMÉ : plus de login par mot
de passe partagé, plus de TOTP partagé. Seuls les comptes NOMINATIFS (email + argon2id + 2FA par
compte) se connectent. `LABUSE_AUTH_PASSWORD` ne sert plus qu'à ACTIVER l'authentification.

La config est rechargée par fixture (env vars) — l'app lit les settings À CHAQUE requête
dans le middleware, donc le basculement local/pilot est testable sans redémarrer l'app.
"""
from __future__ import annotations

import re
import uuid
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes, totp
from labuse.db import session_scope

pytestmark = pytest.mark.db   # readyz + login nominatif touchent la DB


@pytest.fixture
def client(engine):
    from labuse.api.app import app

    # base_url https : hors local le cookie est Secure → le jar httpx ne l'enverrait pas
    # sur http (comportement navigateur fidèle ; en réel : reverse proxy HTTPS, documenté).
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def auth_actif(monkeypatch):
    """Active l'authentification (env ≠ local + mot de passe d'activation + clé de signature).
    POST-DEPLOY-1 : AUCUN secret TOTP « pilote » — les comptes nominatifs portent chacun leur 2FA."""
    from labuse import config

    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "interrupteur-auth-actif")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "clef-de-test-stable")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


MDP = "mot-de-passe-nominatif-974"


def _utilisateur(role: str) -> tuple[str, int]:
    """Utilisateur ACTIF du rôle voulu, via le cycle d'invitation réel (comme en production)."""
    email = f"test-auth-{uuid.uuid4().hex[:10]}@exemple.test"
    with session_scope() as db:
        comptes.ensure_tables(db)
        inv = comptes.creer_invitation(db, email)
        tok = inv["lien"].split("token=")[1]
        comptes.activer_par_invitation(db, tok, MDP, "2026-07-22")
        db.execute(text("UPDATE comptes SET statut = 'actif' WHERE id = :c"), {"c": inv["compte_id"]})
        db.execute(text("UPDATE utilisateurs SET role = :r WHERE id = :i"),
                   {"r": role, "i": inv["utilisateur_id"]})
        db.commit()
    return email, int(inv["utilisateur_id"])


def _login(client, email, password=MDP):
    return client.post("/login", content=urlencode({"identifiant": email, "password": password}),
                       headers={"content-type": "application/x-www-form-urlencoded"},
                       follow_redirects=False)


def _ouvrir_session_admin(client) -> str:
    """Crée un admin nominatif, l'enrôle en 2FA et ouvre sa session (le jar du client la porte)."""
    email, _ = _utilisateur(role="admin")
    r = _login(client, email)
    assert r.status_code == 303 and r.headers["location"] == "/login/2fa"
    page = client.get("/login/2fa")
    m = re.search(r'id="totp-secret"[^>]*>([^<]+)<', page.text)
    assert m, "secret affiché à l'enrôlement"
    secret = m.group(1).replace(" ", "").strip()
    r = client.post("/login/2fa", content=urlencode({"code": totp.code_totp(secret)}),
                    headers={"content-type": "application/x-www-form-urlencoded"}, follow_redirects=False)
    assert r.status_code == 200 and "codes de secours" in r.text   # session posée sur cette réponse
    return email


# ───────────────────────── Local (défaut) : auth désactivée ─────────────────────────

def test_local_par_defaut_tout_ouvert(client):
    # Rétro-compatibilité : sans LABUSE_AUTH_PASSWORD ni env pilote, rien ne change.
    assert client.get("/pipeline/meta").status_code == 200
    assert client.get("/login", follow_redirects=False).status_code == 302  # rien à demander


# ───────────────────────── Auth active : protection effective ─────────────────────────

def test_sans_session_api_401_et_pages_redirigees(client, auth_actif):
    assert client.get("/pipeline/meta").status_code == 401          # API → 401 JSON
    assert client.get("/stats").status_code == 401
    r = client.get("/", follow_redirects=False)                     # navigation → /login
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert client.get("/demo-status").status_code == 401
    assert client.get("/docs").status_code in (302, 401)            # docs protégés hors local


def test_healthz_reste_public(client, auth_actif):
    assert client.get("/healthz").status_code == 200
    assert client.get("/health").status_code == 200


# ───────────────────────── POST-DEPLOY-1 : le login pilote partagé est MORT ─────────────────────────

def test_login_pilote_partage_supprime(client, auth_actif):
    """Un POST /login SANS identifiant (ancienne voie « mot de passe partagé »), même avec l'ancien
    mot de passe d'activation, → 401 NEUTRE et AUCUNE session. La voie pilote n'existe plus."""
    r = client.post("/login", content="password=interrupteur-auth-actif",
                    headers={"content-type": "application/x-www-form-urlencoded"}, follow_redirects=False)
    assert r.status_code == 401
    assert "E-mail ou mot de passe incorrect" in r.text             # message NEUTRE, identique
    assert "labuse_session" not in r.headers.get("set-cookie", "")
    # et le login UTILISATEUR nominatif, lui, vit toujours
    email, _ = _utilisateur(role="titulaire")
    assert _login(client, email).status_code == 303


def test_mauvais_mot_de_passe_refus_neutre(client, auth_actif):
    email, _ = _utilisateur(role="titulaire")
    r = _login(client, email, password="totalement-faux")
    assert r.status_code == 401
    assert "E-mail ou mot de passe incorrect" in r.text             # message NEUTRE (O1)
    assert "labuse_session" not in r.headers.get("set-cookie", "")


# ───────────────────────── Session nominative : cookie, accès, logout ─────────────────────────

def test_session_cookie_securise_puis_acces(client, auth_actif):
    _ouvrir_session_admin(client)
    assert client.get("/pipeline/meta").status_code == 200          # cookie conservé par TestClient
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    assert client.get("/stats", params={"source": Q_A_RUN_LABEL}).status_code == 200  # M45 : source requise


def test_logout_ferme_la_session(client, auth_actif):
    _ouvrir_session_admin(client)
    assert client.get("/pipeline/meta").status_code == 200
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert client.get("/pipeline/meta").status_code == 401


def test_session_falsifiee_refusee(client, auth_actif):
    client.cookies.set("labuse_session", "v1.9999999999.deadbeef")  # signature invalide
    assert client.get("/pipeline/meta").status_code == 401


def test_readyz_public_mais_reduit_sans_session(client, auth_actif):
    r = client.get("/readyz")
    assert r.status_code in (200, 503)                              # public (monitoring)
    js = r.json()
    # COMPTE-3 (Lot 2) — mode réduit : état des liens de mails mais NOM D'HÔTE SEUL (jamais l'URL
    # complète, ni schema/data/couches). Rien de sensible ne fuit à une sonde anonyme.
    assert set(js) == {"ready", "checked_at", "mail_liens"}
    assert set(js["mail_liens"]) == {"host", "ok"}                  # host + verdict, pas l'URL complète
    assert "base_url" not in js["mail_liens"] and "avert" not in js["mail_liens"]
    _ouvrir_session_admin(client)
    full = client.get("/readyz").json()
    assert {"schema", "data", "actions"} <= set(full)               # détails avec session
    assert full["mail_liens"].get("base_url") is not None           # URL complète avec session


def test_fail_closed_sans_mot_de_passe(client, monkeypatch):
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


# ───────────── RADAR-FIX-2 (serveur, Option 2) : jeton X-Radar-Token au garde ─────────────

_RADAR_TOKEN_TEST = "jeton-radar-RADARFIX2-test-constant-48c-xxxxxxxxxxxx"


def test_radar_token_passe_le_garde_mais_rien_d_autre(client, auth_actif, engine, monkeypatch):
    """Le garde _auth_guard laisse passer les 3 endpoints de l'extension SI X-Radar-Token est valide
    (comparaison à temps constant) ; sans jeton / faux jeton → 401 ; et le jeton n'ouvre AUCUNE autre
    route /admin/*. _exiger_radar reste dans la route (enforcement final, fail-closed)."""
    from labuse import config
    from labuse.pige.tables import ensure_tables

    ensure_tables(engine)   # /admin/radar/etat lit pige_passes : garantir le schéma pour le 200
    monkeypatch.setenv("LABUSE_RADAR_TOKEN", _RADAR_TOKEN_TEST)
    config.get_settings.cache_clear()
    try:
        bon = {"X-Radar-Token": _RADAR_TOKEN_TEST}
        faux = {"X-Radar-Token": "jeton-faux"}
        assert client.get("/admin/radar/etat").status_code == 401                 # sans jeton → 401
        assert client.get("/admin/radar/etat", headers=faux).status_code == 401   # faux jeton → 401
        assert client.get("/admin/radar/etat", headers=bon).status_code == 200    # bon jeton → 200
        # capture (POST) passe aussi le garde avec le bon jeton : corps vide → 422 métier, JAMAIS 401
        assert client.post("/admin/radar/capture", headers=bon, json={}).status_code != 401
        # une AUTRE route /admin/* avec le jeton radar → toujours 401 (jeton scopé aux 3 endpoints)
        assert client.get("/admin/radar/extraction", headers=bon).status_code == 401
    finally:
        config.get_settings.cache_clear()
