"""DOCS-1 (Lot B4) — la bibliothèque « Mes documents » respecte la cloison par compte (même IDOR que
Projets/CRM). Le compte A enregistre un document ; le compte B ne le voit pas (liste vide) et ne peut
ni le régénérer ni le supprimer par id (404). On vérifie aussi l'état « À jour » → « Sources modifiées
depuis » quand un millésime de source bouge, et le retour à « À jour » après régénération.

Harness autonome (on ne touche aucun test existant) : deux comptes actifs connectés sur DB réelle +
auth active, même patron que test_cloisonnement_1.py.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


@pytest.fixture
def app_client(engine, monkeypatch):
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-docs-1")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-docs-1-000000000000000000000000")
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
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-docs-1", "2026-09-28")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client, email):
    r = client.post("/login", data={"identifiant": email, "password": "motdepasse-docs-1"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    return client


def _seed_parcelle(idu: str) -> None:
    with session_scope() as s:
        if not s.execute(text("SELECT 1 FROM parcels WHERE idu=:i"), {"i": idu}).scalar():
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
                " VALUES (:i,'Saint-Denis','ZZ','1', ST_GeomFromText(:w,4326),"
                " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
                " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                {"i": idu, "w": _WKT})
        s.commit()


def _purge(*emails):
    with session_scope() as s:
        for e in emails:
            try:
                comptes.supprimer_utilisateur(s, e)
            except Exception:
                pass


@pytest.fixture
def deux_comptes(app_client):
    ea, eb = f"da-{uuid.uuid4().hex[:8]}@x.test", f"db-{uuid.uuid4().hex[:8]}@x.test"
    n = uuid.uuid4().int
    idu1 = f"97411000AA{n % 10000:04d}"
    cid_a, cid_b = _compte_actif(ea), _compte_actif(eb)
    _seed_parcelle(idu1)
    # au moins une source avec un millésime : garantit un instantané NON vide (état « À jour » calculable).
    from labuse import enums
    from labuse.models import DataSource
    with session_scope() as s:
        if not s.execute(text("SELECT 1 FROM data_sources WHERE name=:n"), {"n": "ZZ-DOCS1-TEST"}).scalar():
            s.add(DataSource(name="ZZ-DOCS1-TEST", source_millesime="2026_T1",
                             status=enums.DataSourceStatus.A_FAIRE))
        s.commit()
    ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
    cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
    try:
        yield ca, cb, cid_a, cid_b, idu1
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM data_sources WHERE name=:n"), {"n": "ZZ-DOCS1-TEST"})
            s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": idu1})
            s.commit()
        _purge(ea, eb)


def test_documents_generes_cloison(deux_comptes):
    """A enregistre un document ; B ne le voit pas et ne peut ni le régénérer ni le supprimer."""
    ca, cb, cid_a, cid_b, idu1 = deux_comptes
    r = ca.post("/documents", json={"doc_type": "dossier", "idus": [idu1]})
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]

    # A voit sa ligne, B ne voit rien.
    la = ca.get("/documents").json()
    assert any(d["id"] == doc_id for d in la["documents"]) and la["total"] >= 1
    lb = cb.get("/documents").json()
    assert all(d["id"] != doc_id for d in lb["documents"])

    # B ne peut ni régénérer ni supprimer la ligne de A (404, jamais 200).
    assert cb.post(f"/documents/{doc_id}/rafraichir").status_code == 404
    assert cb.delete(f"/documents/{doc_id}").status_code == 404

    # cloison au niveau base : la ligne porte bien le compte de A.
    with session_scope() as s:
        assert s.execute(text("SELECT compte_id FROM documents_generes WHERE id=:i"),
                         {"i": doc_id}).scalar() == cid_a

    # A peut, lui, supprimer sa ligne.
    assert ca.delete(f"/documents/{doc_id}").status_code == 200


def test_etat_a_jour_puis_sources_modifiees(deux_comptes):
    """État « À jour » à la génération ; « Sources modifiées depuis » quand un millésime bouge ;
    retour à « À jour » après régénération (l'instantané repasse à aujourd'hui)."""
    ca, _cb, _cid_a, _cid_b, idu1 = deux_comptes
    doc_id = ca.post("/documents", json={"doc_type": "dossier", "idus": [idu1]}).json()["id"]

    def etat():
        row = next(d for d in ca.get("/documents").json()["documents"] if d["id"] == doc_id)
        return row["etat"]

    assert etat() == "a_jour"

    # un millésime de source bouge → la ligne passe à « modifié ».
    with session_scope() as s:
        s.execute(text("UPDATE data_sources SET source_millesime='2026_T2' WHERE name='ZZ-DOCS1-TEST'"))
        s.commit()
    assert etat() == "modifie"

    # régénération : l'instantané repasse à aujourd'hui → de nouveau « À jour ».
    assert ca.post(f"/documents/{doc_id}/rafraichir").status_code == 200
    assert etat() == "a_jour"

    ca.delete(f"/documents/{doc_id}")
