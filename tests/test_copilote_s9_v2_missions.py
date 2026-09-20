"""COPILOTE-2 lot 4 — un seul Copilote (v2), SANS le moteur run-scopé v1 (retiré). Les missions
lourdes RECHERCHE et VERIFICATION deviennent des PASSERELLES vers les outils (chemin OUTIL, lot 2) :
le Copilote extrait les critères/l'IDU, ouvre l'outil, et le DIT — il ne produit ni shortlist ni avis
lui-même. Tests DÉTERMINISTES (monkeypatch classify)."""
from __future__ import annotations

import pytest

from labuse.copilote_v2 import answering
from labuse.copilote_v2.router import Route


@pytest.fixture(autouse=True)
def _no_telemetrie(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)


def _force(monkeypatch, intent, **params):
    monkeypatch.setattr(answering, "classify", lambda *a, **k: Route(intent, params=params))


# ── RECHERCHE : passerelle vers la carte filtrée sur les critères (facette), pas un run ──
def test_recherche_ouvre_la_carte_filtree(monkeypatch):
    _force(monkeypatch, "RECHERCHE", commune="Saint-Leu", programme_logements=15, budget_eur=500000)
    r = answering.answer(None, "trouve des terrains")
    assert r.get("refus") is None
    assert not r.get("needs_confirmation")            # plus de run à confirmer
    cf = r.get("carte_filtre")
    assert cf and cf["commune"] == "Saint-Leu"        # la facette liste les parcelles, pas le Copilote
    assert "je ne produis pas la sélection" in r["text"].lower()


# ── VERIFICATION : passerelle vers « Étudier un bien » préremplie de l'IDU, jamais un avis calculé ──
def test_verification_ouvre_etudier_un_bien(monkeypatch):
    _force(monkeypatch, "VERIFICATION", idu="97415000AC0016", prix_eur=320000)
    r = answering.answer(None, "vérifie 97415000AC0016 à 320000 €", confirme=True)
    assert r.get("refus") is None
    assert r.get("porte") == "scoreur-adresse"
    assert r.get("prefill_idu") == "97415000AC0016"
    assert "je ne le calcule pas" in r["text"].lower()
    assert not r.get("sources")                        # aucune donnée servie : c'est une porte


def test_verification_sans_idu_demande_precision(monkeypatch):
    _force(monkeypatch, "VERIFICATION", prix_eur=320000)
    r = answering.answer(None, "cette parcelle vaut-elle 320000 € ?")
    assert r.get("clarification") is True
    assert "idu" in r["text"].lower()
