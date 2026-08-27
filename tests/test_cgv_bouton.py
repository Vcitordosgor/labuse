"""E3 (parcours d'entrée) — la case CGV débloque bien la continuation, SOUS CSP.

Racine du bug prod : la CSP `script-src 'self'` bloque tout script inline ET tout gestionnaire
`onchange=`/`oninput=`. Le toggle CGV inline ne s'exécutait jamais → bouton figé même case cochée.
Correction : JS servi en fichier same-origin (/parcours.js), bouton toujours cliquable (jamais de
cul-de-sac), validation native + garde serveur. Ce test gèle la propriété : aucun JS inline.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db

_INLINE_HANDLER = re.compile(r'\son(change|input|click|submit|load)=', re.I)
_INLINE_SCRIPT = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>', re.I)  # <script> SANS src


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def _token_client() -> str:
    email = f"cli-{uuid.uuid4().hex[:10]}@exemple.test"
    with session_scope() as db:
        inv = comptes.creer_invitation(db, email)
    return inv["lien"].split("token=")[1]


def _token_admin() -> str:
    email = f"adm-{uuid.uuid4().hex[:10]}@labuse.local"
    with session_scope() as db:
        r = comptes.creer_admin_invitation(db, email)
    return r["lien"].split("token=")[1]


@pytest.mark.parametrize("page", ["client", "admin", "reset", "flash_retour"])
def test_pages_parcours_sans_js_inline(client, page):
    """Aucune page du parcours ne porte de script inline ni de gestionnaire on*= (CSP-safe)."""
    if page == "client":
        html = client.get(f"/invitation?token={_token_client()}").text
    elif page == "admin":
        html = client.get(f"/invitation?token={_token_admin()}").text
    elif page == "reset":
        html = client.get("/reset?token=peu-importe").text
    else:
        html = client.get("/flash/retour?session_id=cs_test_123").text
    assert not _INLINE_HANDLER.search(html), f"gestionnaire on*= inline (bloqué par CSP) dans {page}"
    assert not _INLINE_SCRIPT.search(html), f"<script> inline (bloqué par CSP) dans {page}"


def test_bouton_cgv_toujours_cliquable(client):
    """Le bouton n'est plus 'disabled' (plus de cul-de-sac si le JS ne charge pas) ; la case CGV
    existe et est 'required' (validation native), le JS externe est référencé."""
    html = client.get(f"/invitation?token={_token_client()}").text
    bouton = re.search(r'<button[^>]*id="cta"[^>]*>', html).group(0)
    assert "disabled" not in bouton
    assert 'id="cgv"' in html and "required" in html
    assert 'src="/parcours.js"' in html


def test_parcours_js_servi_et_gere_la_case(client):
    r = client.get("/parcours.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    js = r.text
    assert "addEventListener" in js and "getElementById('cgv')" in js and "strength" in js.lower()
    # zéro gestionnaire inline dans le JS lui-même (tout est addEventListener)
    assert "onchange=" not in js and "oninput=" not in js


def test_flash_retour_js_servi(client):
    r = client.get("/flash-retour.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert "addEventListener" in r.text and "/flash/statut" in r.text
