"""RADAR P1 · V1 — le cœur IA apprend à voir. Extension vision de `ai.core.complete`.

Aucune régression sur le chemin texte (les tests Copilote restent verts sans modif). Ici on éprouve :
le bloc image base64 (format/taille validés, jamais d'envoi douteux), le chemin complet vision (client
mocké — pas de clé réelle en test), et le coût logué au ledger avec son kind propre.

Image RÉELLE fabriquée en mémoire (PNG 1×1 valide) — aucun fichier externe.
"""
from __future__ import annotations

import base64
import struct
import zlib

import pytest

from labuse.ai import core
from labuse.ai.core import ImagePart

pytestmark = pytest.mark.db


def _png(w: int = 1, h: int = 1, rgb: tuple[int, int, int] = (200, 40, 40)) -> bytes:
    """PNG truecolor minimal VALIDE (signature + IHDR + IDAT + IEND), en pur stdlib."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)   # 8-bit, truecolor
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def test_bloc_image_valide():
    png = _png()
    b = core._bloc_image(ImagePart(png, "image/png"))
    assert b["type"] == "image" and b["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(b["source"]["data"]) == png   # round-trip exact


def test_bloc_image_rejette_format_taille_vide():
    with pytest.raises(ValueError, match="non supporté"):
        core._bloc_image(ImagePart(_png(), "image/tiff"))
    with pytest.raises(ValueError, match="vide"):
        core._bloc_image(ImagePart(b"", "image/png"))
    with pytest.raises(ValueError, match="trop lourde"):
        core._bloc_image(ImagePart(b"x" * (core.MAX_IMAGE_BYTES + 1), "image/png"))


def test_image_invalide_ne_consomme_rien(monkeypatch):
    """Une image non supportée → degraded honnête AVANT tout appel réseau (pas de coût, pas d'invention)."""
    monkeypatch.setattr(core, "has_key", lambda: True)
    # si un appel réseau partait, ce fake le prouverait en levant ; il ne doit PAS être atteint.
    monkeypatch.setattr("anthropic.Anthropic", lambda **k: (_ for _ in ()).throw(AssertionError("appelé")))
    r = core.complete(None, kind="vision_pige", system="s", context={"x": 1},
                      images=[ImagePart(_png(), "image/bmp")], model=core.MODEL_VISION)
    assert r.degraded and r.reason.startswith("image:")


class _FakeMsg:
    def __init__(self):
        self.content = [type("B", (), {"text": '{"prix": 245000}'})()]
        self.usage = type("U", (), {"input_tokens": 1200, "output_tokens": 30})()


def test_chemin_vision_complet_mocke_et_cout_logue(monkeypatch, db_session):
    """has_key + client mockés : l'image est jointe, la prose revient, le coût est logué kind=vision_pige."""
    captured = {}

    class _FakeClient:
        def __init__(self, **k):
            self.messages = self
        def create(self, **kw):
            captured.update(kw)
            return _FakeMsg()

    monkeypatch.setattr(core, "has_key", lambda: True)
    monkeypatch.setattr("anthropic.Anthropic", _FakeClient)
    r = core.complete(db_session, kind="vision_pige", system="Tu lis une capture.",
                      context={"lien": "https://exemple"}, images=[ImagePart(_png(), "image/png")],
                      model=core.MODEL_VISION, max_tokens=300)
    assert not r.degraded and '"prix": 245000' in r.text
    # le message utilisateur porte bien un bloc image PUIS le texte
    contenu = captured["messages"][-1]["content"]
    assert isinstance(contenu, list) and contenu[0]["type"] == "image" and contenu[-1]["type"] == "text"
    # coût logué au ledger avec le kind propre + le modèle vision
    from sqlalchemy import text
    row = db_session.execute(text(
        "SELECT kind, model FROM ia_log WHERE kind='vision_pige' ORDER BY id DESC LIMIT 1")).mappings().first()
    assert row and row["model"] == core.MODEL_VISION


def test_chemin_texte_inchange(monkeypatch):
    """Sans images, le contenu utilisateur reste une CHAÎNE (aucun appel existant impacté)."""
    captured = {}

    class _FakeClient:
        def __init__(self, **k):
            self.messages = self
        def create(self, **kw):
            captured.update(kw)
            return _FakeMsg()

    monkeypatch.setattr(core, "has_key", lambda: True)
    monkeypatch.setattr("anthropic.Anthropic", _FakeClient)
    core.complete(None, kind="test_txt", system="s", context={"a": 1})
    assert isinstance(captured["messages"][-1]["content"], str)
