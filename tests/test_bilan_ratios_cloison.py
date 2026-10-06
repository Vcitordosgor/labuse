"""BILAN-1 Lot 4 — isolation des ratios maison (IDOR).

Même épreuve à deux comptes que CLOISONNEMENT-1, sur la table bilan_ratios :
le compte A mémorise un ratio, le compte B ne le voit pas (liste), ne peut pas le
modifier ni le supprimer par id, et en base le ratio de A ne porte que compte_id = A.
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
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-bilan-ratios")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-bilan-ratios-000000000000000000")
    monkeypatch.setenv("LABUSE_SMTP_HOST", "")
    monkeypatch.setenv("BREVO_API_KEY", "")
    from labuse import config

    config.get_settings.cache_clear()
    from labuse.api.app import app

    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def _compte_actif(email: str) -> int:
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:
            pass
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(
            s, inv["lien"].split("token=")[1], "motdepasse-bilan-ratios", "2026-09-28"
        )
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client, email):
    r = client.post(
        "/login",
        data={"identifiant": email, "password": "motdepasse-bilan-ratios"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    return client


@pytest.fixture
def deux_comptes(app_client):
    ea, eb = f"bra-{uuid.uuid4().hex[:8]}@x.test", f"brb-{uuid.uuid4().hex[:8]}@x.test"
    cid_a = _compte_actif(ea)
    cid_b = _compte_actif(eb)
    ca = TestClient(app_client.app, base_url="https://testserver")
    _login(ca, ea)
    cb = TestClient(app_client.app, base_url="https://testserver")
    _login(cb, eb)
    try:
        yield ca, cb, cid_a, cid_b
    finally:
        with session_scope() as s:
            for e in (ea, eb):
                try:
                    comptes.supprimer_utilisateur(s, e)
                except Exception:
                    pass
            s.commit()


def test_ratios_maison_cloison(deux_comptes):
    ca, cb, cid_a, cid_b = deux_comptes

    # A mémorise un ratio « notaire 1,5 % »
    r = ca.put("/bilan-ratios/notT", json={"valeur": 1.5})
    assert r.status_code == 200, r.text

    # A le voit ; B ne voit RIEN
    assert ca.get("/bilan-ratios").json().get("notT", {}).get("valeur") == 1.5
    assert cb.get("/bilan-ratios").json() == {}

    # en base : le ratio ne porte que compte_id = A
    with session_scope() as s:
        assert s.execute(
            text("SELECT count(*) FROM bilan_ratios WHERE poste_id='notT' AND compte_id=:c"),
            {"c": cid_a},
        ).scalar() == 1
        assert s.execute(
            text("SELECT count(*) FROM bilan_ratios WHERE poste_id='notT' AND compte_id=:c"),
            {"c": cid_b},
        ).scalar() == 0

    # B « supprime » le même poste : aucun effet sur le ratio de A (cloison)
    assert cb.delete("/bilan-ratios/notT").status_code == 200
    with session_scope() as s:
        assert s.execute(
            text("SELECT count(*) FROM bilan_ratios WHERE poste_id='notT' AND compte_id=:c"),
            {"c": cid_a},
        ).scalar() == 1

    # B mémorise SON propre notT avec une autre valeur : les deux coexistent, isolés
    assert cb.put("/bilan-ratios/notT", json={"valeur": 2.0}).status_code == 200
    assert ca.get("/bilan-ratios").json()["notT"]["valeur"] == 1.5
    assert cb.get("/bilan-ratios").json()["notT"]["valeur"] == 2.0


def test_poste_inconnu_rejete(deux_comptes):
    ca, _cb, _a, _b = deux_comptes
    assert ca.put("/bilan-ratios/nexiste_pas", json={"valeur": 1.0}).status_code == 404
