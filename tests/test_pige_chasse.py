"""RADAR — CHASSE AUX BUGS : verrous de non-régression des findings RD-501→506.

Chaque test grave une attaque qui CASSAIT le Radar avant correction. [CHASSE-TEST] auto-nettoyés.
"""
from __future__ import annotations

import json
import struct
import uuid
import zlib

import pytest
from sqlalchemy import text

from labuse.ai.core import IAResult
from labuse.db import session_scope
from labuse.pige import digests, intake

pytestmark = pytest.mark.db


def _png() -> bytes:
    def ch(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + ch(b"IEND", b""))


def _mock(monkeypatch, extra=None):
    payload = {"prix": {"valeur": 250000, "confiance": 0.9}, "type": {"valeur": "maison", "confiance": 0.9},
               "commune": {"valeur": "Saint-Paul", "confiance": 0.9}, **(extra or {})}
    monkeypatch.setattr("labuse.ai.core.complete", lambda *a, **k: IAResult(text=json.dumps(payload), model="v"))


@pytest.fixture(autouse=True)
def _captures_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(tmp_path / "cap"))


def test_rd502_valider_refuse_les_corrections_hostiles():
    """RD-502 — prix/type/pieces/dpe/pp hors bornes ou type → ValueError, jamais écrit faux ni 500."""
    from labuse.pige.intake import valider_corrections
    for corr in ({"prix": -5}, {"prix": 0}, {"prix": "cher"}, {"pieces": -3}, {"type": "chateau"},
                 {"particulier_pro": "🏠"}, {"dpe_classe": "ZZZ"}, {"surface_hab": -50}):
        with pytest.raises(ValueError):
            valider_corrections(corr)
    # valeurs saines : passent (dpe minuscule normalisé)
    assert valider_corrections({"prix": 260000, "dpe_classe": "d", "type": "terrain"}) == {
        "prix": 260000, "dpe_classe": "D", "type": "terrain"}


def test_rd504_lien_invalide_refuse(monkeypatch):
    """RD-504 — lien vide / javascript: / data: / malformé → rejet_lien (jamais un url_sortante XSS servi)."""
    _mock(monkeypatch)
    for lien in ("", "   ", "javascript:alert(1)", "data:text/html,x", "pas une url"):
        with session_scope() as db:
            r = intake.deposer(db, _png(), "image/png", lien)
        assert r["statut"] == "rejet_lien"


def test_rd506_date_future_remise_a_null(monkeypatch):
    _mock(monkeypatch, {"date_publication": {"valeur": "2099-12-31", "confiance": 0.9}})
    tag = uuid.uuid4().hex[:6]
    with session_scope() as db:
        r = intake.deposer(db, _png(), "image/png", f"https://www.leboncoin.fr/ch-{tag}")
        dp = db.execute(text("SELECT date_publication FROM pige_biens WHERE bien_id=:b"), {"b": r["bien_id"]}).scalar()
        db.execute(text("DELETE FROM pige_biens WHERE bien_id=:b"), {"b": r["bien_id"]})
        db.commit()
    assert dp is None   # date impossible → null, jamais écrite fausse


def test_rd501_capture_non_stockable_ne_laisse_rien(monkeypatch):
    """RD-501 — répertoire captures inaccessible → echec_stockage, AUCUN bien partiel committé."""
    _mock(monkeypatch)
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", "/srv/interdit-chasse/xyz")
    tag = uuid.uuid4().hex[:6]
    with session_scope() as db:
        avant = db.execute(text("SELECT count(*) FROM pige_biens")).scalar()
        r = intake.deposer(db, _png(), "image/png", f"https://www.leboncoin.fr/nostore-{tag}")
        apres = db.execute(text("SELECT count(*) FROM pige_biens")).scalar()
    assert r["statut"] == "echec_stockage" and apres == avant


def test_rd503_digests_tourne_contre_le_schema_reel():
    """RD-503 — _clients_actifs ne référence QUE des colonnes réelles (pas `prenoms`) → pas de 500."""
    with session_scope() as db:
        r = digests.envoyer(db, dry_run=True)   # ne doit pas lever
    assert "envoyes" in r and "n_biens_du_jour" in r
    # garde-fou anti-régression : la requête ne SÉLECTIONNE plus la colonne inexistante c.prenoms
    import inspect
    from labuse.pige import digests as d
    src = inspect.getsource(d._clients_actifs)
    assert "c.prenoms" not in src and "c.nom AS prenom" in src
