"""SCORING-3 · L5 — retour terrain : étiquette d'un clic, CLOISONNÉE et testée.

Le test du mandat (L5.2) : une étiquette posée par un compte n'apparaît JAMAIS
chez un autre — ni en lecture, ni en écriture. Tests ADVERSARIAUX permanents
(même harnais que test_audit_secu : DB réelle labuse_test, auth active,
deux comptes réels). + validation des 8 états, réversibilité, journal (compteur
Pilotage) — et AUCUN agrégat inter-comptes produit.
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
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-audit")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-audit-000000000000000000")
    from labuse import config
    config.get_settings.cache_clear()
    from labuse.api.app import app
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def _compte_actif(email: str) -> int:
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:  # noqa: BLE001
            pass
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1],
                                       "motdepasse-audit-1", "2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"),
                  {"c": inv["compte_id"]})
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
            except Exception:  # noqa: BLE001
                pass
        s.commit()


def _parcelle(idu: str) -> None:
    _wkt = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
            " centroid, bbox) VALUES (:i,'X','ZZ','1', ST_GeomFromText(:w,4326),"
            " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
            " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "w": _wkt})
        s.commit()


def test_etiquette_cloisonnee_entre_comptes(app_client):
    """L5.2 — LE test du mandat : l'étiquette d'un compte n'apparaît jamais chez
    un autre. B suit la MÊME parcelle : sa carte reste vierge ; B ne peut pas
    poser d'étiquette sur l'entrée de A (404, pas 403 — l'existence même est tue)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    idu = f"974991TER{uuid.uuid4().hex[:5].upper()}"
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        _parcelle(idu)
        eid_a = ca.post("/pipeline", json={"idu": idu}).json()["entry"]["id"]
        eid_b = cb.post("/pipeline", json={"idu": idu}).json()["entry"]["id"]

        # A pose « refus ferme » — horodaté
        r = ca.patch(f"/pipeline/{eid_a}", json={"contact_etiquette": "refus_ferme"})
        assert r.status_code == 200, r.text
        assert r.json()["entry"]["contact_etiquette"] == "refus_ferme"
        assert r.json()["entry"]["contact_etiquette_at"] is not None
        assert r.json()["entry"]["contact_etiquette_label"] == "Refus ferme"

        # B, sur LA MÊME parcelle : rien ne transpire — sa carte est vierge
        eb_entry = cb.get(f"/pipeline/parcel/{idu}").json()["entry"]
        assert eb_entry["id"] == eid_b
        assert eb_entry["contact_etiquette"] is None, \
            "FUITE : l'étiquette de A visible chez B"
        assert all(e.get("contact_etiquette") is None for e in cb.get("/pipeline").json())

        # B ne peut pas étiqueter l'entrée de A (l'existence même est tue : 404)
        assert cb.patch(f"/pipeline/{eid_a}",
                        json={"contact_etiquette": "vendu_a_nous"}).status_code == 404
        # et l'étiquette de A n'a pas bougé
        assert ca.get(f"/pipeline/parcel/{idu}").json()["entry"]["contact_etiquette"] == "refus_ferme"
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu}); s.commit()


def test_etiquette_validee_reversible_et_journalisee(app_client):
    """Les 8 états seuls sont acceptés ; "" efface (réversible) ; chaque geste est
    JOURNALISÉ avec le compte (compteur Pilotage) — et le journal n'expose aucun
    agrégat inter-comptes (c'est un compte global, pas une vue par parcelle)."""
    ea = f"a-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(ea)
    idu = f"974992TER{uuid.uuid4().hex[:5].upper()}"
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        _parcelle(idu)
        eid = ca.post("/pipeline", json={"idu": idu}).json()["entry"]["id"]

        # état inconnu → 422 (validation stricte, jamais un état inventé)
        assert ca.patch(f"/pipeline/{eid}",
                        json={"contact_etiquette": "peut_etre"}).status_code == 422

        # pose → correction → effacement : réversible, trois lignes au journal
        for et in ("contacte", "en_negociation", ""):
            r = ca.patch(f"/pipeline/{eid}", json={"contact_etiquette": et})
            assert r.status_code == 200, r.text
        entry = ca.get(f"/pipeline/parcel/{idu}").json()["entry"]
        assert entry["contact_etiquette"] is None          # effacée
        assert entry["contact_etiquette_at"] is None
        with session_scope() as s:
            lignes = s.execute(text(
                "SELECT etiquette FROM contact_etiquette_log "
                "WHERE compte_id = :c AND entry_id = :e ORDER BY id"),
                {"c": cid, "e": eid}).scalars().all()
        assert lignes == ["contacte", "en_negociation", None]
    finally:
        _purge(ea)
        with session_scope() as s:
            s.execute(text("DELETE FROM contact_etiquette_log WHERE compte_id = :c"), {"c": cid})
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu}); s.commit()


def test_vue_contact_compte_cloisonnee(db_session):
    """L4.4 — la vue « déjà contacté » porte compte_id dans sa clé : une piste
    d'un compte n'apparaît que sous SON compte_id (jamais un agrégat anonyme)."""
    from labuse.scoring.p_v2.potentiel import ensure_vue_contact
    ensure_vue_contact(db_session)
    idu = f"974993TER{uuid.uuid4().hex[:5].upper()}"
    pid = db_session.execute(text(
        "INSERT INTO parcels (idu, commune, geom, created_at, updated_at) "
        "VALUES (:i, 'X', ST_GeomFromText('POINT(55.5 -21.1)', 4326), now(), now()) "
        "RETURNING id"), {"i": idu}).scalar()
    cid_a, cid_b = [db_session.execute(text(
        "INSERT INTO comptes (nom, plan, founding, statut, sieges, created_at, updated_at) "
        "VALUES (:n, 'licence', false, 'actif', 1, now(), now()) RETURNING id"),
        {"n": f"terrain-{n}-{uuid.uuid4().hex[:6]}"}).scalar() for n in ("a", "b")]
    db_session.execute(text(
        "INSERT INTO pipeline_entries (compte_id, parcel_id, status, priority, notes, "
        " prospection, created_at, updated_at) "
        "VALUES (:c, :p, 'a_qualifier', 'normale', '', '{}', now(), now())"),
        {"c": cid_a, "p": pid})
    rows = db_session.execute(text(
        "SELECT compte_id, contact_via FROM v_parcelle_contact_compte "
        "WHERE parcelle_idu = :i"), {"i": idu}).all()
    assert rows == [(cid_a, "piste_crm")]
    # un AUTRE compte ne voit rien pour cette parcelle (filtre compte obligatoire)
    autres = db_session.execute(text(
        "SELECT count(*) FROM v_parcelle_contact_compte "
        "WHERE parcelle_idu = :i AND compte_id = :b"), {"i": idu, "b": cid_b}).scalar()
    assert autres == 0
