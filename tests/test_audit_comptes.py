"""AUDIT COMPTES & CLOISONNEMENT (27/08/2026) — tests de RÉGRESSION des routes d'objet que
l'audit à deux comptes a couvertes et que test_audit_secu ne testait pas encore : Copilote v2
(veilles + conversations/missions) et colonnes CRM par id. Tous SAINS au moment de l'audit —
ces tests gèlent la preuve pour qu'une régression tombe. DB réelle, auth active, 2 comptes.
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
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-audit-comptes")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-audit-comptes-0000000000000000")
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
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-audit-1", "2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client, email):
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


def test_idor_copilote_v2_veilles_cloison(app_client):
    """Copilote v2 — une veille de A n'est ni listée, ni supprimable par B (cloison SQL :
    le DELETE renvoie {ok:false} sans rien toucher, la veille de A survit)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    cid_a = _compte_actif(ea)
    _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        # A crée une veille évaluable (via le module — pas d'endpoint POST direct)
        from labuse.copilote_v2 import veilles
        with session_scope() as s:
            vid = veilles.creer(s, compte_id=cid_a, type_="permis", commune="Saint-Denis")["id"]
            s.commit()
        # A la voit ; B ne la voit pas
        assert any(v["id"] == vid for v in ca.get("/api/copilote-v2/veilles").json()["veilles"])
        assert all(v["id"] != vid for v in cb.get("/api/copilote-v2/veilles").json()["veilles"])
        # B tente de la supprimer par id → {ok:false}, la veille de A SURVIT
        rb = cb.delete(f"/api/copilote-v2/veilles/{vid}")
        assert rb.status_code == 200 and rb.json()["ok"] is False
        with session_scope() as s:
            assert s.execute(text("SELECT actif FROM veilles WHERE id=:i"), {"i": vid}).scalar() is True
        # A la supprime bien
        assert ca.delete(f"/api/copilote-v2/veilles/{vid}").json()["ok"] is True
    finally:
        _purge(ea, eb)


def test_idor_copilote_v2_conversation_cloison(app_client):
    """Copilote v2 — une conversation de A n'est ni listée, ni ouverte par B (missions/{id} → 404)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        r = ca.post("/api/copilote-v2/ask", json={"message": "Bonjour, ici A."})
        assert r.status_code == 200, r.text
        conv = r.json().get("conversation_id")
        assert conv is not None, "la conversation doit être persistée (conversation_id)"
        # A ouvre SA conversation ; B ne le peut pas
        assert ca.get(f"/api/copilote-v2/missions/{conv}").status_code == 200
        assert cb.get(f"/api/copilote-v2/missions/{conv}").status_code == 404
    finally:
        _purge(ea, eb)


def test_idor_crm_columns_cloison(app_client):
    """CRM — une colonne custom de A n'est ni modifiable ni supprimable par B (404 IDOR)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        r = ca.post("/pipeline/columns", json={"label": "Colonne de A"})
        assert r.status_code == 200, r.text
        col = r.json()
        col_id = col.get("id") or (col.get("column") or {}).get("id")
        if col_id is None:   # certaines formes renvoient la liste complète
            cols = ca.get("/pipeline/columns").json()
            cols = cols if isinstance(cols, list) else cols.get("columns", [])
            col_id = next(c["id"] for c in cols if c.get("label") == "Colonne de A")
        # B ne peut ni renommer ni supprimer la colonne de A
        assert cb.patch(f"/pipeline/columns/{col_id}", json={"label": "VOL"}).status_code == 404
        assert cb.request("DELETE", f"/pipeline/columns/{col_id}", json={}).status_code == 404
    finally:
        _purge(ea, eb)


def test_idor_courrier_demande_cloison_et_admin_403(app_client):
    """Courrier — la demande de A n'est pas dans la timeline de B ; la route admin de
    changement de statut refuse un client (403) et ne touche pas la demande de A."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        r = ca.post("/courrier/demande", json={"parcelles": ["974AUDCOUR001"],
                                               "communes": "Saint-Denis", "modele": "standard",
                                               "corps": "Demande de A."})
        assert r.status_code == 200, r.text
        did = r.json()["id"]
        # A la voit dans SA timeline ; B ne la voit pas
        assert any(d["id"] == did for d in ca.get("/courrier/demandes").json()["demandes"])
        assert all(d["id"] != did for d in cb.get("/courrier/demandes").json()["demandes"])
        # B (client) ne peut pas faire avancer le statut (route admin) → 403, demande intacte
        assert cb.post(f"/courrier/admin/demandes/{did}/statut", json={"statut": "imprime"}).status_code == 403
        with session_scope() as s:
            assert s.execute(text("SELECT statut FROM courrier_demandes WHERE id=:i"), {"i": did}).scalar() == "demande"
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM courrier_demandes WHERE parcelles::text LIKE '%974AUDCOUR001%'")); s.commit()
