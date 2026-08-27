"""VPS · AC-025 + AC-020 — 2FA TOTP des admins, admin nominatif, mort du pilote partagé.

La primitive TOTP (labuse.totp) se prouve sur les VECTEURS RFC 6238 (annexe B, SHA-1) ;
le flux web se prouve en conditions réelles (TestClient + DB de test, comme test_auth.py) :
un admin ne reçoit JAMAIS de session sur le seul mot de passe.
"""
from __future__ import annotations

import base64
import re
import time
import uuid
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes, totp
from labuse.db import session_scope

pytestmark = pytest.mark.db

# secret des vecteurs RFC 6238 : ASCII "12345678901234567890"
SECRET_RFC = base64.b32encode(b"12345678901234567890").decode("ascii")
MDP = "mot-de-passe-2fa-974"


# ───────────────────────── unitaire : la primitive TOTP ─────────────────────────

def test_vecteurs_rfc6238():
    assert SECRET_RFC == "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert totp.code_totp(SECRET_RFC, t=59) == "287082"
    assert totp.code_totp(SECRET_RFC, t=1111111109) == "081804"


def test_verifier_code_fenetre_et_pas():
    # le pas accepté est RENVOYÉ (c'est lui qui porte l'anti-rejeu côté comptes)
    assert totp.verifier_code(SECRET_RFC, "287082", t=59) == 59 // 30
    # tolérance d'horloge ±1 pas : le code de t=59 vaut encore à t=59+30, plus à t=59+61
    assert totp.verifier_code(SECRET_RFC, "287082", t=59 + 30) == 1
    assert totp.verifier_code(SECRET_RFC, "287082", t=59 + 61) is None
    # code faux / malformé → None, jamais une exception
    assert totp.verifier_code(SECRET_RFC, "000000", t=59) is None
    assert totp.verifier_code(SECRET_RFC, "28708", t=59) is None
    assert totp.verifier_code(SECRET_RFC, "pas-un-code", t=59) is None


def test_uri_otpauth():
    uri = totp.uri_otpauth(SECRET_RFC, "vic@labuse.immo")
    assert uri.startswith("otpauth://totp/LABUSE:vic%40labuse.immo?")
    assert f"secret={SECRET_RFC}" in uri and "issuer=LABUSE" in uri


def test_anti_rejeu_en_base(engine):
    """comptes.totp_verifier : le MÊME code bon ne passe qu'une fois (dernier_pas)."""
    _, uid = _utilisateur(role="admin")
    with session_scope() as db:
        secret = comptes.totp_preparer(db, uid)
        assert comptes.totp_preparer(db, uid) == secret     # recharger ≠ nouveau secret
        code = totp.code_totp(secret)
        assert comptes.totp_verifier(db, uid, code) is True
        assert comptes.totp_verifier(db, uid, code) is False  # rejoué → refusé


# ───────────────────────── fixtures web (pattern test_auth.py) ─────────────────────────

@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def pilot(monkeypatch):
    from labuse import config
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "mot-de-passe-pilote")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "clef-de-test-stable")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def _utilisateur(role: str) -> tuple[str, int]:
    """Utilisateur ACTIF (mot de passe posé, compte actif) du rôle voulu — via le cycle
    d'invitation réel, comme en production."""
    email = f"test-2fa-{uuid.uuid4().hex[:10]}@exemple.test"
    with session_scope() as db:
        comptes.ensure_tables(db)
        inv = comptes.creer_invitation(db, email)
        tok = inv["lien"].split("token=")[1]
        comptes.activer_par_invitation(db, tok, MDP, "2026-07-22")
        db.execute(text("UPDATE comptes SET statut = 'actif' WHERE id = :c"),
                   {"c": inv["compte_id"]})
        db.execute(text("UPDATE utilisateurs SET role = :r WHERE id = :i"),
                   {"r": role, "i": inv["utilisateur_id"]})
        db.commit()
    return email, int(inv["utilisateur_id"])


def _login(client, email, password=MDP):
    return client.post("/login", content=urlencode({"identifiant": email, "password": password}),
                       headers={"content-type": "application/x-www-form-urlencoded"},
                       follow_redirects=False)


def _poster_code(client, code):
    return client.post("/login/2fa", content=urlencode({"code": code}),
                       headers={"content-type": "application/x-www-form-urlencoded"},
                       follow_redirects=False)


def _secret_de_la_page(html: str) -> str:
    m = re.search(r'id="totp-secret"[^>]*>([^<]+)<', html)
    assert m, "le secret doit être affiché en toutes lettres sur la page d'enrôlement"
    return m.group(1).replace(" ", "").strip()


def _enroler(client, email) -> tuple[str, list[str]]:
    """Login admin + enrôlement complet → (secret, codes de secours en clair)."""
    r = _login(client, email)
    assert r.status_code == 303 and r.headers["location"] == "/login/2fa"
    page = client.get("/login/2fa")
    secret = _secret_de_la_page(page.text)
    r = _poster_code(client, totp.code_totp(secret))
    assert r.status_code == 200 and "codes de secours" in r.text
    codes = ["".join(m) for m in re.findall(r"(\d{5})-(\d{5})", r.text)]
    assert len(codes) == 8
    return secret, codes


# ───────────────────────── flux admin : défi → enrôlement → session ─────────────────────────

def test_admin_redirige_vers_2fa_sans_session(client, pilot):
    email, _ = _utilisateur(role="admin")
    r = _login(client, email)
    assert r.status_code == 303 and r.headers["location"] == "/login/2fa"
    sc = r.headers.get("set-cookie", "")
    assert "labuse_2fa=" in sc                        # le DÉFI est posé…
    assert "labuse_session=" not in sc                # …JAMAIS la session sur le seul mot de passe
    assert client.get("/pipeline/meta").status_code == 401


def test_2fa_sans_defi_retourne_au_login(client, pilot):
    r = client.get("/login/2fa", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"


def test_enrolement_complet_ouvre_la_session(client, pilot):
    email, _ = _utilisateur(role="admin")
    _enroler(client, email)
    assert client.get("/pipeline/meta").status_code == 200      # session posée avec les codes
    # l'enrôlement est confirmé : un retour à la porte demande le CODE, plus le QR
    client.get("/logout", follow_redirects=False)
    _login(client, email)
    page = client.get("/login/2fa")
    assert "totp-secret" not in page.text and "application" in page.text


def test_mauvais_code_pas_de_session(client, pilot):
    email, _ = _utilisateur(role="admin")
    _login(client, email)
    page = client.get("/login/2fa")
    secret = _secret_de_la_page(page.text)
    faux = "000000" if totp.code_totp(secret) != "000000" else "000001"
    r = _poster_code(client, faux)
    assert r.status_code == 401 and "incorrect" in r.text
    assert client.get("/pipeline/meta").status_code == 401


def test_cinq_echecs_invalident_le_defi(client, pilot):
    email, _ = _utilisateur(role="admin")
    _login(client, email)
    page = client.get("/login/2fa")
    faux = "000000" if totp.code_totp(_secret_de_la_page(page.text)) != "000000" else "000001"
    for _ in range(4):
        assert _poster_code(client, faux).status_code == 401
    r = _poster_code(client, faux)                    # 5ᵉ tentative → défi mort, retour porte
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert client.get("/pipeline/meta").status_code == 401


def test_totp_rejoue_refuse_apres_enrolement(client, pilot):
    """Le code qui a servi à l'enrôlement (pas de temps consommé) ne rouvre PAS la porte ;
    le code du pas SUIVANT (fenêtre ±1) passe."""
    email, _ = _utilisateur(role="admin")
    secret, _codes = _enroler(client, email)
    client.get("/logout", follow_redirects=False)
    _login(client, email)
    assert _poster_code(client, totp.code_totp(secret)).status_code == 401   # même pas → rejeu
    r = _poster_code(client, totp.code_totp(secret, t=time.time() + 30))     # pas suivant
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert client.get("/pipeline/meta").status_code == 200


def test_code_secours_usage_unique(client, pilot):
    email, _ = _utilisateur(role="admin")
    _, codes = _enroler(client, email)
    client.get("/logout", follow_redirects=False)
    _login(client, email)
    r = _poster_code(client, codes[0])
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert client.get("/pipeline/meta").status_code == 200
    client.get("/logout", follow_redirects=False)
    _login(client, email)
    assert _poster_code(client, codes[0]).status_code == 401    # déjà consommé → refusé
    assert client.get("/pipeline/meta").status_code == 401


# ───────────────────────── non-admin et pilote : rien ne change / tout se ferme ─────────────────────────

def test_non_admin_flux_inchange(client, pilot):
    email, _ = _utilisateur(role="titulaire")
    r = _login(client, email)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert "labuse_session=u." in r.headers.get("set-cookie", "")
    assert client.get("/pipeline/meta").status_code == 200


def test_login_pilote_desactive(client, pilot, monkeypatch):
    from labuse import config
    monkeypatch.setenv("LABUSE_LOGIN_PILOTE_ACTIF", "0")
    config.get_settings.cache_clear()
    r = client.post("/login", content="password=mot-de-passe-pilote",
                    headers={"content-type": "application/x-www-form-urlencoded"},
                    follow_redirects=False)
    assert r.status_code == 401                       # échec NEUTRE, même bon mot de passe
    assert "labuse_session" not in r.headers.get("set-cookie", "")
    # le login UTILISATEUR, lui, vit toujours
    email, _ = _utilisateur(role="titulaire")
    assert _login(client, email).status_code == 303


# ───────────────────────── AC-020 : admin nominatif idempotent ─────────────────────────

def test_creer_admin_invitation_idempotent(engine):
    email = f"test-adm-{uuid.uuid4().hex[:10]}@exemple.test"
    with session_scope() as db:
        r1 = comptes.creer_admin_invitation(db, email)
        assert r1["lien"] and "token=" in r1["lien"] and not r1["promu"]
        r2 = comptes.creer_admin_invitation(db, email)          # relance → même utilisateur
        assert r2["utilisateur_id"] == r1["utilisateur_id"] and r2["lien"]
        # le lien pose le mot de passe par le mécanisme d'invitation STANDARD
        tok = r2["lien"].split("token=")[1]
        assert comptes.activer_par_invitation(db, tok, MDP, "2026-07-22")
        role, statut = db.execute(text(
            "SELECT u.role, c.statut FROM utilisateurs u JOIN comptes c ON c.id = u.compte_id"
            " WHERE u.id = :i"), {"i": r1["utilisateur_id"]}).first()
        assert role == "admin" and statut == "actif"            # la porte ouvre (pas de Stripe)
        r3 = comptes.creer_admin_invitation(db, email)          # mot de passe posé → plus de lien
        assert r3["lien"] is None and not r3["promu"]


def test_promotion_utilisateur_existant(engine):
    email, uid = _utilisateur(role="titulaire")
    with session_scope() as db:
        r = comptes.creer_admin_invitation(db, email)
        assert r["promu"] and r["utilisateur_id"] == uid and r["lien"] is None
        assert db.execute(text("SELECT role FROM utilisateurs WHERE id = :i"),
                          {"i": uid}).scalar() == "admin"
