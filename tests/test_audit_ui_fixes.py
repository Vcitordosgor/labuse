"""Régressions audit UI 12/07 — mention fiabilité piscines (exports) + double-tir ortho.

1. Option B wave-ortho : exports piscine rouverts AVEC la mention de précision mesurée
   (90,7 %, échantillon interne). La mention suit le preset (galerie/builder) ET voyage
   en pied d'export CSV.
2. Un verdict de validation ortho ne s'écrase JAMAIS silencieusement — avec OU sans
   `profil` (le garde était limité aux sessions profilées : un POST nu écrasait).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.api.segments import MENTIONS_LEGALES

pytestmark = pytest.mark.db


def test_mention_piscine_presente_et_sourcee():
    for slug in ("piscinistes-construction", "parc-piscines-entretien"):
        m = MENTIONS_LEGALES.get(slug)
        assert m, f"mention absente pour {slug}"
        assert "90,7" in m["texte"] and "échantillon interne" in m["texte"]
        assert "non contractuelle" in m["texte"]      # jamais une promesse


@pytest.fixture
def client(engine, monkeypatch):
    from labuse import config
    from labuse.api import protection
    from labuse.api.app import app

    protection.ensure_tables(engine)
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_export_csv_porte_la_mention_en_pied(client, monkeypatch):
    from labuse.api import segments as segapi

    monkeypatch.setattr(segapi, "_resolve_body", lambda db, body: ([], None, []))
    monkeypatch.setattr(segapi.seg, "build", lambda *a, **k: None)
    monkeypatch.setattr(segapi, "_rows_export",
                        lambda db, q: (["Parcelle (IDU)", "Voie (BAN)"],
                                       [["97415000AB0001", "Rue des Tests"]]))
    r = client.post("/segments/export", json={"slug": "piscinistes-construction"})
    assert r.status_code == 200
    assert "Mention :" in r.text and "90,7" in r.text     # pied d'export
    r2 = client.post("/segments/export", json={"slug": "pergolas-terrasses"})
    assert r2.status_code == 200 and "Mention :" not in r2.text   # pas de bruit ailleurs


def _detection(db, det_id, validation=None):
    db.execute(text(
        "INSERT INTO ortho_detections (id, type, validation) VALUES (:i, 'piscine', :v) "
        "ON CONFLICT (id) DO UPDATE SET validation = :v"), {"i": det_id, "v": validation})


def test_double_tir_refuse_meme_sans_profil(client, engine, db_session):
    from labuse.ingestion.ortho_piscines import DDL as ORTHO_DDL
    with engine.begin() as c:
        for stmt in ORTHO_DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))
        c.execute(text("ALTER TABLE ortho_detections ADD COLUMN IF NOT EXISTS valide_profil varchar(16)"))
        c.execute(text("DELETE FROM ortho_detections WHERE id IN (990001, 990002)"))
        c.execute(text(
            "INSERT INTO ortho_detections (id, type, validation, geom) VALUES "
            "(990001, 'piscine', NULL, ST_SetSRID(ST_GeomFromText("
            " 'POLYGON((55.29 -21.01, 55.291 -21.01, 55.291 -21.009, 55.29 -21.009, 55.29 -21.01))'),4326)), "
            "(990002, 'piscine', 'ok', ST_SetSRID(ST_GeomFromText("
            " 'POLYGON((55.30 -21.02, 55.301 -21.02, 55.301 -21.019, 55.30 -21.019, 55.30 -21.02))'),4326))"))
    try:
        # détection vierge : 1er verdict passe, 2e (double envoi, SANS profil) → 409
        r1 = client.post("/ortho/validation/api/990001", json={"verdict": "ok"})
        assert r1.status_code == 200
        r2 = client.post("/ortho/validation/api/990001", json={"verdict": "faux_positif"})
        assert r2.status_code == 409
        # détection DÉJÀ validée : jamais écrasée silencieusement
        r3 = client.post("/ortho/validation/api/990002", json={"verdict": "faux_positif"})
        assert r3.status_code == 409
        with engine.connect() as c:
            v = c.execute(text("SELECT validation FROM ortho_detections WHERE id = 990002")).scalar()
        assert v == "ok"          # le verdict d'origine est intact
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM ortho_detections WHERE id IN (990001, 990002)"))
