"""M113 · Phase 2/3 — les CHIPS de contexte, côté serveur. Tests DÉTERMINISTES (monkeypatch, aucun
modèle) : le registre servi, le court-circuit web, le parcours projet (jamais de création directe,
préremplissage), et le FORÇAGE du scénario (intent forcé, clarification d'intention retirée)."""
from __future__ import annotations

from labuse.copilote_v2 import answering
from labuse.copilote_v2.router import Route


# ───────────────────────── le registre servi ─────────────────────────
def test_scenarios_publies_six_chips():
    sc = answering.scenarios_publies()
    assert [s["cle"] for s in sc] == ["donnees", "parcelle", "projet", "web", "surveillance", "outil"]
    assert all(s["libelle"] and s["placeholder"] for s in sc)   # jamais un chip nu
    assert answering.SCENARIOS["web"]["intent"] == "QUESTION"
    assert answering.SCENARIOS["surveillance"]["intent"] == "VEILLE"


# ───────────────────────── web : court-circuit total ─────────────────────────
class _Res:
    def __init__(self, ok, data=None, refus=None):
        self.ok, self.data, self.refus = ok, data, refus


def test_web_court_circuite_classify(monkeypatch):
    appels = {"classify": 0}
    monkeypatch.setattr(answering, "classify", lambda *a, **k: (appels.__setitem__("classify", 1), Route("QUESTION"))[1])
    monkeypatch.setitem(answering.OUTILS, "recherche_web",
                        lambda db, question, history=None: _Res(True, {"reponse": "Le maire est X.", "domaines": ["reunion.fr"], "date": "2026-08-17"}))
    monkeypatch.setattr(answering.telemetrie, "web", lambda *a, **k: None)
    r = answering.answer(db=None, message="Qui est le maire ?", scenario="web")
    assert appels["classify"] == 0                 # classify JAMAIS appelé (court-circuit)
    assert r["web"] is True and r["scenario"] == "web"
    assert "Source : web" in r["text"]


# ───────────────────────── projet : jamais de création directe ─────────────────────────
def test_projet_form_prerempli_sans_classify():
    # params fournis → aucun appel modèle ; le formulaire s'ouvre prérempli (pas de création).
    r = answering._projet_form(db=None, message="15 logements à Saint-Paul",
                               params={"commune": "Saint-Paul", "programme_logements": 15, "budget_eur": 800000})
    assert r["intent"] == "PROJET" and r["scenario"] == "projet"
    assert r["projet_form"]["prefill"] == {"commune": "Saint-Paul", "programme_logements": 15, "budget_eur": 800000}
    assert "_action" not in r                       # RIEN qui déclenche une création serveur


def test_projet_intent_ouvre_le_formulaire(monkeypatch):
    # même en texte libre classé PROJET, on OUVRE le formulaire (jamais _executer_projet).
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: Route("PROJET", params={"commune": "Bras-Panon", "programme_logements": 12}))
    r = answering.answer(db=None, message="résidence 12 lots à Bras-Panon")
    assert r.get("projet_form") is not None
    assert r["projet_form"]["prefill"]["commune"] == "Bras-Panon"
    assert "_action" not in r


# ───────────────────────── forçage du scénario ─────────────────────────
def test_scenario_force_intent_et_retire_clarif_intention(monkeypatch):
    capté = {}

    def faux_route(db, message, route, **k):
        capté["intent"] = route.intent
        capté["clarification"] = route.clarification
        return {"text": "ok", "intent": route.intent}

    # le routeur aurait deviné QUESTION avec une clarification d'intention ; le chip « parcelle » force
    # RECHERCHE et retire la clarification d'intention (la clarif de paramètre reste produite en aval).
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: Route("QUESTION", params={"commune": "Saint-Leu"},
                                              clarification="Chercher ou vérifier ?"))
    monkeypatch.setattr(answering, "_answer_with_route", faux_route)
    answering.answer(db=None, message="des terrains à Saint-Leu", scenario="parcelle")
    assert capté["intent"] == "RECHERCHE"           # intent FORCÉ par le chip
    assert capté["clarification"] is None           # clarification d'INTENTION retirée
