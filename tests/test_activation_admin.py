"""E2 (parcours d'entrée) — activation ADMIN sans paiement.

Un compte créé par `labuse creer-admin` (plan 'interne') passe par un écran d'activation
DÉDIÉ : e-mail + mot de passe, aucune offre/prix/CGV commerciale/Stripe. Le client Intégral,
lui, garde son tunnel (offre + prix + CGV + paiement).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def _token_admin() -> str:
    email = f"adm-{uuid.uuid4().hex[:10]}@labuse.local"
    with session_scope() as db:
        r = comptes.creer_admin_invitation(db, email)
    return r["lien"].split("token=")[1]


def _token_client() -> str:
    email = f"cli-{uuid.uuid4().hex[:10]}@exemple.test"
    with session_scope() as db:
        inv = comptes.creer_invitation(db, email)
    return inv["lien"].split("token=")[1]


def test_ecran_admin_sans_offre_ni_paiement(client):
    html = client.get(f"/invitation?token={_token_admin()}").text
    assert "administrateur" in html.lower()
    assert "€" not in html                              # aucun prix
    assert "Continuer vers le paiement" not in html    # pas le CTA du tunnel client
    assert "/cgv" not in html                           # pas de lien CGV (ni corps ni footer)
    assert 'name="cgv"' not in html                     # pas de case CGV
    assert "double authentification" in html.lower()    # dit la prochaine étape (2FA)


def test_ecran_client_garde_son_tunnel(client):
    html = client.get(f"/invitation?token={_token_client()}").text
    assert "349 €/mois" in html and "sans engagement" in html
    assert 'name="cgv"' in html                          # la case CGV existe (client)
    assert "Continuer vers le paiement" in html


def test_activation_admin_sans_cgv_aboutit(client):
    """L'admin n'a pas de case CGV : le POST /invitation ne DOIT PAS exiger cgv=oui."""
    tok = _token_admin()
    r = client.post("/invitation", data={"token": tok, "password": "MotDePasseAdmin1!", "interne": "1"},
                    follow_redirects=False)
    assert r.status_code in (200, 303), r.text[:300]
    body = r.text
    assert "Conditions requises" not in body            # jamais le cul-de-sac CGV
    # compte activé (utilisateur actif) → l'écran « accès ouvert » ou une redirection /login
    if r.status_code == 200:
        assert "ouvert" in body.lower() or "login" in body.lower()


def test_client_sans_cgv_reste_bloque(client):
    """Le garde CGV du tunnel CLIENT n'est PAS affaibli par la dérogation admin."""
    tok = _token_client()
    r = client.post("/invitation", data={"token": tok, "password": "MotDePasseClient1!"},
                    follow_redirects=False)
    assert r.status_code == 400 and "Conditions requises" in r.text


def test_champ_interne_non_falsifiable(client):
    """Un CLIENT qui poste interne=1 n'échappe pas à la CGV (le serveur juge sur le PLAN)."""
    tok = _token_client()
    r = client.post("/invitation", data={"token": tok, "password": "MotDePasseX1!", "interne": "1"},
                    follow_redirects=False)
    assert r.status_code == 400 and "Conditions requises" in r.text
