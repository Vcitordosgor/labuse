"""M118 + SUITE-1 S9 — le Copilote resserré. Tests DÉTERMINISTES (monkeypatch classify).

S9 : RECHERCHE et VERIFICATION sont RAPATRIÉES dans le chat (missions lourdes du v2) — elles ne
partent plus en refus-voie mais produisent un RÉCAP-PÉAGE (needs_confirmation), puis le front lance le
run / renvoie confirme. Restent en refus-voie : PROJET (→ Projets), VEILLE (→ Surveillance), OUTIL
(→ Outils/CRM)."""
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
    ("PROJET", "projets"), ("VEILLE", "surveillance"),
])
def test_intent_hors_mission_donne_sa_voie(monkeypatch, intent, cible):
    _force(monkeypatch, intent)
    r = answering.answer(None, "peu importe le texte")
    assert r.get("refus") == "hors_mission"
    assert (r.get("voie") or {}).get("cible") == cible


def test_recherche_est_une_mission_lourde_pas_un_refus(monkeypatch):
    # S9 — RECHERCHE (avec commune) → récap-péage dans le chat, jamais un refus-voie.
    _force(monkeypatch, "RECHERCHE", commune="Saint-Leu", programme_logements=15)
    r = answering.answer(None, "trouve des terrains à Saint-Leu pour 15 logements")
    assert r.get("refus") is None
    assert r.get("intent") == "RECHERCHE" and r.get("needs_confirmation") is True
    assert r.get("brief_effectif")                      # le run partira de ce brief


def test_recherche_sans_commune_demande_la_commune(monkeypatch):
    _force(monkeypatch, "RECHERCHE")
    r = answering.answer(None, "trouve des terrains")
    assert r.get("refus") is None and r.get("needs_confirmation") is True
    assert (r.get("clarification_recap") or {}).get("champ") == "commune"


def test_verification_est_une_mission_lourde_avec_idu(monkeypatch):
    # S9 — VERIFICATION → récap-péage (puis confirme → avis), plus un refus-voie fiche.
    _force(monkeypatch, "VERIFICATION", idu="97415000AC0016")
    r = answering.answer(None, "cette parcelle vaut-elle 320000 € ?")
    assert r.get("refus") is None
    assert r.get("intent") == "VERIFICATION" and r.get("needs_confirmation") is True
    assert "97415000AC0016" in (r.get("brief_effectif") or "")


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
