"""RADAR P1 · V2 — extraction + intake (contrôle commune, dédoublonnage, dépôt, validation).

L'appel vision est mocké (pas de clé en test) : on éprouve l'ANTI-INVENTION (null non deviné, confiance
basse surlignée), le contrôle commune ∈ 24, le dédoublonnage V0 §3, le brouillon (rien de validé avant
le clic) et la promotion + événements. [RADAR-TEST] auto-nettoyés.
"""
from __future__ import annotations

import json
import struct
import zlib

import pytest
from sqlalchemy import text

from labuse.ai.core import IAResult
from labuse.db import session_scope
from labuse.pige import extraction, intake

pytestmark = pytest.mark.db


def _png() -> bytes:
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b""))


def _mock_ia(monkeypatch, payload: dict | str):
    txt = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr("labuse.ai.core.complete",
                        lambda *a, **k: IAResult(text=txt, model="vision"))


@pytest.fixture(autouse=True)
def _captures_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(tmp_path / "captures"))


def _cell(v, c):
    return {"valeur": v, "confiance": c}


def test_extraction_anti_invention(monkeypatch):
    # prix lisible (haute confiance), surface_hab illisible (null), pièces vue mais floue (basse conf)
    _mock_ia(monkeypatch, {"prix": _cell(245000, 0.95), "type": _cell("maison", 0.9),
                           "pieces": _cell(4, 0.4), "surface_hab": _cell(None, 0.0),
                           "commune": _cell("Saint-Paul", 0.9),
                           "inventé_hors_schema": _cell(999, 0.9)})
    r = extraction.extraire(None, _png(), "image/png", "https://www.leboncoin.fr/x")
    assert r["ok"]
    assert r["faits"]["prix"] == 245000 and r["faits"]["surface_hab"] is None
    assert "inventé_hors_schema" not in r["faits"]        # clé hors schéma JETÉE
    assert r["confiances"]["surface_hab"] == 0.0          # null → confiance 0
    assert "pieces" in r["champs_a_verifier"]             # sous le seuil → à vérifier
    assert r["portail"] == "leboncoin" and r["portail_inconnu"] is False


def test_extraction_non_json_ne_hallucine_pas(monkeypatch):
    _mock_ia(monkeypatch, "désolé, image floue, je ne peux pas lire")
    r = extraction.extraire(None, _png(), "image/png", "https://x.example/a")
    assert r["ok"] is False and "non-JSON" in r["motif"]
    assert r["portail"] == "autre" and r["portail_inconnu"] is True   # lien inconnu signalé


def test_resoudre_commune_perimetre():
    assert intake.resoudre_commune("saint-paul")[0] == "Saint-Paul"   # casse/accents tolérés
    assert intake.resoudre_commune("SAINT-DENIS")[1] == "97411"
    assert intake.resoudre_commune("Paris") is None                  # hors 24 → None


def test_deposer_rejette_commune_hors_perimetre(monkeypatch):
    _mock_ia(monkeypatch, {"prix": _cell(200000, 0.9), "type": _cell("maison", 0.9),
                           "commune": _cell("Marseille", 0.9)})
    with session_scope() as db:
        r = intake.deposer(db, _png(), "image/png", "https://www.pap.fr/hors")
        assert r["statut"] == "rejet_commune" and "hors des 24" in r["motif"]
        # RIEN en base
        assert db.execute(text("SELECT count(*) FROM pige_annonces WHERE url_sortante = :u"),
                          {"u": "https://www.pap.fr/hors"}).scalar() == 0


def test_deposer_valider_dedup_et_evenements(monkeypatch):
    lien = "https://www.leboncoin.fr/radar-test-1"
    _mock_ia(monkeypatch, {"prix": _cell(300000, 0.9), "type": _cell("terrain", 0.9),
                           "surface_terrain": _cell(1200, 0.9), "commune": _cell("Saint-Paul", 0.9)})
    with session_scope() as db:
        # 1) dépôt → brouillon (rien de validé avant le clic)
        prop = intake.deposer(db, _png(), "image/png", lien)
        assert prop["statut"] == "a_valider"
        bid = prop["bien_id"]
        assert db.execute(text("SELECT valide_at FROM pige_faits WHERE bien_id=:b"), {"b": bid}).scalar() is None
        assert db.execute(text("SELECT count(*) FROM pige_captures WHERE bien_id=:b"), {"b": bid}).scalar() == 1

        # 2) même URL → doublon_url (maj prix proposée, pas de création)
        again = intake.deposer(db, _png(), "image/png", lien)
        assert again["statut"] == "doublon_url" and again["bien_id"] == bid

        # 3) doublon INTER-PORTAIL (autre URL, prix ±2%, surface ±5%) → fusion proposée
        _mock_ia(monkeypatch, {"prix": _cell(303000, 0.9), "type": _cell("terrain", 0.9),
                               "surface_terrain": _cell(1210, 0.9), "commune": _cell("Saint-Paul", 0.9)})
        inter = intake.deposer(db, _png(), "image/png", "https://www.seloger.com/radar-test-2")
        assert inter["statut"] == "a_valider" and inter["fusion_proposee"] == bid

        # 4) validation → promu + événement pige.nouvelle ; baisse de prix → pige.baisse_prix
        intake.valider(db, bid, {"prix": 285000}, valide_par=1)
        f = db.execute(text("SELECT valide_at, prix FROM pige_faits WHERE bien_id=:b"), {"b": bid}).mappings().first()
        assert f["valide_at"] is not None and f["prix"] == 285000
        assert db.execute(text("SELECT statut FROM pige_biens WHERE bien_id=:b"), {"b": bid}).scalar() == "active"
        assert db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.nouvelle'")).scalar() >= 1
        assert db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.baisse_prix'")).scalar() >= 1

        # nettoyage [RADAR-TEST]
        ids = [r[0] for r in db.execute(text(
            "SELECT bien_id FROM pige_biens WHERE commune='Saint-Paul' AND bien_id IN (:a,:b)"),
            {"a": bid, "b": inter["bien_id"]}).all()]
        for x in ids:
            db.execute(text("DELETE FROM pige_biens WHERE bien_id=:b"), {"b": x})
        db.execute(text("DELETE FROM event_log WHERE kind IN ('pige.nouvelle','pige.baisse_prix')"))
        db.commit()
