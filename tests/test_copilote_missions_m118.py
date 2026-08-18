"""M118 — le Copilote resserré à 4 missions. Tests DÉTERMINISTES (monkeypatch classify) : les
intentions qui QUITTENT le chat (RECHERCHE/PROJET/VERIFICATION/VEILLE/OUTIL) reçoivent un refus +
une voie cliquable, et le registre ne sert plus que 4 chips."""
from __future__ import annotations

import pytest

from labuse.copilote_v2 import answering
from labuse.copilote_v2.router import Route


@pytest.fixture(autouse=True)
def _no_telemetrie(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)


def _force(monkeypatch, intent, **params):
    monkeypatch.setattr(answering, "classify", lambda *a, **k: Route(intent, params=params))


@pytest.mark.parametrize("intent, cible", [
    ("RECHERCHE", "projets"), ("PROJET", "projets"), ("VEILLE", "surveillance"),
])
def test_intent_hors_mission_donne_sa_voie(monkeypatch, intent, cible):
    _force(monkeypatch, intent)
    r = answering.answer(None, "peu importe le texte")
    assert r.get("refus") == "hors_mission"
    assert (r.get("voie") or {}).get("cible") == cible


def test_verification_voie_fiche_avec_idu(monkeypatch):
    _force(monkeypatch, "VERIFICATION", idu="97415000AC0016")
    r = answering.answer(None, "cette parcelle vaut-elle 320000 € ?")
    v = r.get("voie") or {}
    assert r.get("refus") == "hors_mission" and v.get("cible") == "fiche" and v.get("idu") == "97415000AC0016"


def test_outil_courrier_voie_courriers(monkeypatch):
    _force(monkeypatch, "OUTIL")
    r = answering.answer(None, "rédige un courrier au propriétaire")
    assert r.get("refus") == "hors_mission" and (r.get("voie") or {}).get("cible") == "courriers"


def test_outil_autre_voie_outils(monkeypatch):
    _force(monkeypatch, "OUTIL")
    r = answering.answer(None, "je veux assembler des parcelles")
    assert r.get("refus") == "hors_mission" and (r.get("voie") or {}).get("cible") == "outils"


def test_refus_voie_ne_sert_aucun_chiffre():
    # la voie est du texte + navigation, jamais un chiffre LABUSE (gate négative, côté unité).
    import re
    r = answering._refus_voie(None, "trouve un terrain", "RECHERCHE", "Trouver se fait dans Projets.",
                              "projets", "Ouvrir Projets")
    assert not re.search(r"\d{4,6}", r["text"])
