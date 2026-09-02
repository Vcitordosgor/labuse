"""SUITE-1 S9 — NON-RÉGRESSION : un seul Copilote, le v2. Les missions lourdes RECHERCHE et
VERIFICATION s'exécutent DANS le chat v2, par le MÊME moteur run-scopé (copilote/moteurs) et le MÊME
quota unifié que `/ask`. Tests DÉTERMINISTES (monkeypatch classify) au SEAM v2 :

 - RECHERCHE → récap-péage puis run lourd : le `brief_effectif` porte les critères compris (commune
   héritée comprise) → le run part des bons critères ;
 - VERIFICATION → récap-péage puis (confirme) AVIS instruit via `missions_lourdes.verification`, qui
   lit la FICHE (même source/tier que l'écran).

La preuve que tier/parcelles/sources = la fiche (run servi `Q_A_RUN_LABEL`, jamais un pipeline
parallèle ni la table LIVE) vit au niveau moteur dans `test_copilote_v1_run_scope.py` (inchangé — les
3 parcelles témoins de CONNEXIONS-3). Le quota unifié (kind 'copilote' = celui de `/ask`) est prouvé
dans `test_copilote_api.py`.
"""
from __future__ import annotations

import pytest

from labuse.copilote_v2 import answering, missions_lourdes
from labuse.copilote_v2.router import Route


@pytest.fixture(autouse=True)
def _no_telemetrie(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)


def _force(monkeypatch, intent, **params):
    monkeypatch.setattr(answering, "classify", lambda *a, **k: Route(intent, params=params))


# ── RECHERCHE : mission lourde, brief effectif fidèle aux critères compris ──

def test_recherche_recap_puis_run_avec_brief_fidele(monkeypatch):
    _force(monkeypatch, "RECHERCHE", commune="Saint-Leu", programme_logements=15, budget_eur=500000)
    r = answering.answer(None, "trouve des terrains")
    assert r.get("refus") is None and r.get("intent") == "RECHERCHE"
    assert r.get("needs_confirmation") is True
    be = r.get("brief_effectif") or ""
    # le run (mission 'instruire') réinterprétera CE brief → il doit porter les critères annoncés.
    assert "Saint-Leu" in be and "15 logements" in be and "500000" in be


# ── VERIFICATION : confirme → avis instruit par le moteur missions_lourdes (source = fiche) ──

def test_verification_confirme_passe_par_missions_lourdes_et_la_fiche(monkeypatch):
    vus = {}

    def _fake_verification(db, params):
        vus["params"] = dict(params)
        return {"text": "Avis instruit face au prix.", "intent": "VERIFICATION", "tool": "verification",
                "idu": params.get("idu"),
                "sources": ["Fiche parcelle (run servi)", "DVF (prix terrain nu par zone)"],
                "actions": ["ouvrir_fiche", "exporter_dossier"]}

    monkeypatch.setattr(missions_lourdes, "verification", _fake_verification)
    _force(monkeypatch, "VERIFICATION", idu="97415000AC0016", prix_eur=320000)
    r = answering.answer(None, "vérifie 97415000AC0016 à 320000 €", confirme=True)

    assert r.get("refus") is None                                   # plus un refus-voie fiche
    assert r.get("text") == "Avis instruit face au prix."
    assert vus["params"].get("idu") == "97415000AC0016" and vus["params"].get("prix_eur") == 320000
    # source = la FICHE (le même point de calcul que l'écran), jamais un pipeline parallèle.
    assert "Fiche parcelle (run servi)" in (r.get("sources") or [])


def test_verification_sans_confirme_reste_un_recap(monkeypatch):
    # sans confirmation, on N'exécute PAS l'avis (péage M78-bis) — on annonce ce qu'on a compris.
    appels = {"n": 0}

    def _fake_verification(db, params):
        appels["n"] += 1
        return {"text": "ne doit pas être appelé", "intent": "VERIFICATION"}

    monkeypatch.setattr(missions_lourdes, "verification", _fake_verification)
    _force(monkeypatch, "VERIFICATION", idu="97415000AC0016", prix_eur=320000)
    r = answering.answer(None, "vérifie 97415000AC0016 à 320000 €")   # confirme=False (défaut)
    assert appels["n"] == 0                                           # l'avis n'est PAS produit
    assert r.get("needs_confirmation") is True and r.get("refus") is None
