"""RADAR P1 · V3 — endpoints admin de la page Radar (dépôt, files, validation, check).

L'appel vision est mocké ; la garde admin est monkeypatchée pour éprouver la LOGIQUE des endpoints,
et une assertion séparée prouve que la route est bien RÉSERVÉE (non ouverte sans admin).
"""
from __future__ import annotations

import base64
import json
import struct
import zlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.ai.core import IAResult
from labuse.db import session_scope

pytestmark = pytest.mark.db


def _png() -> bytes:
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b""))


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


def test_route_radar_reservee(client, monkeypatch):
    """Les routes Radar passent bien par la garde admin `exiger_admin` (même barrière que tout /admin/*) :
    si la garde refuse, la route refuse. Prouve le câblage de la réserve admin sans monter une session."""
    from fastapi import HTTPException

    def _refuse(request):
        raise HTTPException(status_code=403, detail="admin requis")
    monkeypatch.setattr("labuse.api.auth.exiger_admin", _refuse)
    assert client.get("/admin/radar/check").status_code == 403
    assert client.get("/admin/radar/extraction").status_code == 403
    assert client.post("/admin/radar/valider", json={"bien_id": 1}).status_code == 403


def test_flux_admin_radar(client, monkeypatch, tmp_path):
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(tmp_path / "cap"))
    monkeypatch.setattr("labuse.api.auth.exiger_admin", lambda request: None)   # garde levée pour le flux
    monkeypatch.setattr("labuse.ai.core.complete", lambda *a, **k: IAResult(
        text=json.dumps({"prix": {"valeur": 260000, "confiance": 0.9},
                         "type": {"valeur": "maison", "confiance": 0.9},
                         "surface_hab": {"valeur": 90, "confiance": 0.9},
                         "commune": {"valeur": "Saint-Pierre", "confiance": 0.9}}), model="vision"))
    b64 = base64.b64encode(_png()).decode()
    lien = "https://www.leboncoin.fr/radar-api-1"

    # dépôt → brouillon
    dep = client.post("/admin/radar/deposer",
                      json={"lien": lien, "image_b64": b64, "media_type": "image/png"}).json()
    assert dep["statut"] == "a_valider"
    bid = dep["bien_id"]

    # file d'extraction contient le brouillon
    ext = client.get("/admin/radar/extraction").json()
    assert any(r["bien_id"] == bid for r in ext["file"])

    # validation → active
    v = client.post("/admin/radar/valider", json={"bien_id": bid, "faits": {}}).json()
    assert v["valide"] is True

    # re-vérif contient le bien validé actif
    rev = client.get("/admin/radar/reverif").json()
    assert any(r["bien_id"] == bid for r in rev["file"])

    # passage attentif : baisse de prix
    client.post("/admin/radar/prix", json={"bien_id": bid, "prix": 249000})
    with session_scope() as db:
        assert db.execute(text("SELECT count(*) FROM pige_prix_historique WHERE bien_id=:b"),
                          {"b": bid}).scalar() == 1

    # retirée (clic humain) → statut retiree
    client.post("/admin/radar/retiree", json={"bien_id": bid})
    with session_scope() as db:
        assert db.execute(text("SELECT statut FROM pige_biens WHERE bien_id=:b"), {"b": bid}).scalar() == "retiree"

    # check quotidien : file vidée, compteurs cohérents, plus « vide 48 h » (on vient de saisir)
    chk = client.get("/admin/radar/check").json()
    assert chk["cible_minutes"] == 15 and chk["intake_vide_48h"] is False

    # nettoyage [RADAR-TEST]
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id=:b"), {"b": bid})
        db.execute(text("DELETE FROM event_log WHERE kind LIKE 'pige.%'"))
        db.commit()
