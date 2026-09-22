"""VEILLE-2 · Lot 3 — La cloche du haut : LISTE FERMÉE de quatre catégories.

Affichés (et seulement eux) : parcelle suivie (→ fiche), Radar (→ annonce), marché (→ fiche),
nouveauté de l'app (→ page Sources). Tout autre kind d'event_log n'apparaît PAS côté client.
Non-lus en tête ; un compte neuf ouvre à 0.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope


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


_TAG = uuid.uuid4().hex[:4].upper()   # court : idu = varchar(14)


def test_cloche_liste_fermee_un_de_chaque_type(app_client):
    """Un événement de CHAQUE catégorie + un intrus hors-liste → la cloche montre les quatre, jamais
    l'intrus ; chaque catégorie porte le bon clic (idu→fiche, url→annonce, /sources→Sources)."""
    email = f"clo-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    idus = {"suivi": f"974{_TAG}SUIV01", "marche": f"974{_TAG}MARC01"}
    try:
        c = TestClient(app_client.app, base_url="https://testserver"); _login(c, email)
        with session_scope() as s:
            s.execute(text("DELETE FROM event_log WHERE idu LIKE :p"), {"p": f"974{_TAG}%"})
            # 1) parcelle suivie (perso, → fiche via idu)
            s.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id, lien) VALUES "
                           "('parcelle_suivie', :i, 'Vente sur votre parcelle', :c, '/socle/#parcelle=x')"),
                      {"i": idus["suivi"], "c": cid})
            # 2) Radar (perso, → annonce via lien http, idu NULL)
            s.execute(text("INSERT INTO event_log (kind, titre, compte_id, lien, source) VALUES "
                           "('radar', 'Nouvelle annonce pour votre veille', :c, "
                           "'https://www.leboncoin.fr/ad/ventes_immobilieres/999', 'Radar')"),
                      {"c": cid})
            # 3) marché (broadcast NULL, → fiche via idu)
            s.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id) VALUES "
                           "('bascule', :i, '▲ bascule marché', NULL)"), {"i": idus["marche"]})
            # 4) nouveauté de l'app (broadcast NULL, → /sources)
            s.execute(text("INSERT INTO event_log (kind, titre, compte_id, lien, source) VALUES "
                           "('nouveaute', 'Nouvelle source dans LABUSE', NULL, '/sources', 'LABUSE')"))
            # INTRUS hors liste fermée : une veille de secteur/recherche + un event système → invisibles
            s.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id) VALUES "
                           "('veille', :i, 'veille secteur (hors cloche)', :c)"),
                      {"i": f"974{_TAG}VEIL01", "c": cid})
            s.execute(text("INSERT INTO event_log (kind, titre, compte_id, source) VALUES "
                           "('systeme', 'source en retard (pilote)', NULL, 'Ingestion')"))
            s.commit()

        items = c.get("/events").json()["items"]
        kinds = {e["kind"] for e in items if (e["titre"] or "").endswith(("suivie parcelle", "parcelle")) or
                 e["kind"] in {"parcelle_suivie", "radar", "bascule", "nouveaute", "veille", "systeme"}}
        # les quatre catégories présentes
        assert {"parcelle_suivie", "radar", "bascule", "nouveaute"} <= kinds
        # les intrus ABSENTS de la cloche du client
        assert "veille" not in kinds and "systeme" not in kinds
        # chaque catégorie porte son clic : Radar = lien annonce http ; nouveauté = /sources ; suivi/marché = idu
        by_kind = {e["kind"]: e for e in items if e["kind"] in {"parcelle_suivie", "radar", "bascule", "nouveaute"}}
        assert by_kind["radar"]["lien"].startswith("http") and by_kind["radar"]["idu"] is None
        assert by_kind["nouveaute"]["lien"] == "/sources"
        assert by_kind["parcelle_suivie"]["idu"] and by_kind["bascule"]["idu"]
    finally:
        with session_scope() as s:
            comptes.supprimer_utilisateur(s, email)
            s.execute(text("DELETE FROM event_log WHERE idu LIKE :p OR kind IN ('radar','nouveaute')"),
                      {"p": f"974{_TAG}%"})
            s.execute(text("DELETE FROM event_log WHERE titre IN ('source en retard (pilote)',"
                           "'Nouvelle source dans LABUSE','Nouvelle annonce pour votre veille')"))
            s.commit()


def test_compte_neuf_ouvre_a_zero(app_client):
    """Un compte NEUF n'hérite ni du marché ni des nouveautés diffusés AVANT sa création → cloche à 0.
    Un broadcast POSTÉRIEUR, lui, compte."""
    email = f"neuf-{uuid.uuid4().hex[:8]}@x.test"
    try:
        with session_scope() as s:   # broadcast ANTÉRIEUR à toute création de compte
            s.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id, ts) VALUES "
                           "('bascule', :i, 'marché ancien', NULL, now()-interval '30 days'),"
                           "('nouveaute', NULL, 'nouveauté ancienne', NULL, now()-interval '30 days')"),
                      {"i": f"974{_TAG}OLD01"})
            s.commit()
        cid = _compte_actif(email)
        c = TestClient(app_client.app, base_url="https://testserver"); _login(c, email)
        assert c.get("/events/count").json()["unread"] == 0        # compte neuf → 0
        with session_scope() as s:   # broadcast POSTÉRIEUR à la création
            s.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id) VALUES "
                           "('bascule', :i, 'marché récent', NULL)"), {"i": f"974{_TAG}NEW01"})
            s.commit()
        assert c.get("/events/count").json()["unread"] == 1        # le postérieur compte
    finally:
        with session_scope() as s:
            comptes.supprimer_utilisateur(s, email)
            s.execute(text("DELETE FROM event_log WHERE idu LIKE :p OR titre='nouveauté ancienne'"),
                      {"p": f"974{_TAG}%"})
            s.commit()
