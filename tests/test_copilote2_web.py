"""COPILOTE-2 lot 3 — LE CHEMIN WEB. Une question de connaissance passe par une recherche web
OBLIGATOIRE (jamais la mémoire) ; chaque affirmation porte sa source ; sans source → refus honnête ;
le contexte DOM (Pinel outre-mer, TVA 8,5 %, ZFANG) est injecté. Tests déterministes (web mocké)."""
from __future__ import annotations

from datetime import date

import pytest

from labuse.copilote_v2 import answering
from labuse.copilote_v2.outils import ToolResult


@pytest.fixture(autouse=True)
def _no_telemetrie(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)
    monkeypatch.setattr(answering.telemetrie, "web", lambda *a, **k: None)


def _mock_web(monkeypatch, *, ok=True, reponse="La loi Girardin est une défiscalisation outre-mer.",
              domaines=("service-public.fr", "bofip.impots.gouv.fr"), mode_vu=None):
    def _fake(db, *, question, history=None, mode="fait"):
        if mode_vu is not None:
            mode_vu.append(mode)
        if not ok:
            return ToolResult("recherche_web", ok=False, refus="rien trouvé sur le web")
        return ToolResult("recherche_web", ok=True, web=True,
                          data={"reponse": reponse, "domaines": list(domaines), "date": date.today().isoformat()},
                          source="web")
    monkeypatch.setitem(answering.OUTILS, "recherche_web", _fake)


def test_connaissance_passe_par_le_web(monkeypatch):
    """La voie b appelle recherche_web en mode « connaissance » et rend une réponse SOURCÉE (web=True)."""
    modes = []
    _mock_web(monkeypatch, mode_vu=modes)
    r = answering._general(None, "qu'est-ce que la loi girardin ?")
    assert modes == ["connaissance"]                  # web OBLIGATOIRE, mode notion
    assert r.get("web") is True and r.get("general") is True
    assert "Source : web" in r["text"] and "service-public.fr" in r["text"]
    assert not r.get("refus")


def test_sans_source_refus_jamais_memoire(monkeypatch):
    """Sans source fiable → « je n'ai pas trouvé de source fiable », JAMAIS une réponse de mémoire."""
    _mock_web(monkeypatch, ok=False)
    r = answering._general(None, "un dispositif obscur introuvable ?")
    assert r.get("refus") == "web_rien_trouve"
    assert "source fiable" in r["text"]
    assert not r.get("web")


def test_contexte_dom_injecte():
    """Le contexte DOM (Pinel outre-mer, TVA 8,5 %, ZFANG) est injecté dans le prompt web connaissance."""
    from labuse.copilote_v2 import outils
    sys = outils.WEB_CONNAISSANCE_SYSTEM
    assert "OUTRE-MER" in sys and "8,5 %" in sys and "ZFANG" in sys
    assert "Pinel OUTRE-MER" in sys
    # le prompt FAIT (élus/actualité) porte aussi le contexte DOM
    assert "OUTRE-MER" in outils.WEB_SYSTEM


def test_mode_connaissance_plus_long(monkeypatch):
    """Le mode connaissance autorise 2-4 phrases (une notion se définit) vs 1-2 pour un fait."""
    from labuse.copilote_v2 import outils
    quatre = "Phrase une. Phrase deux. Phrase trois. Phrase quatre. Phrase cinq."
    assert outils._deux_phrases(quatre, max_car=600, max_phrases=4).count(".") >= 3
    assert outils._deux_phrases(quatre).count(".") <= 2
