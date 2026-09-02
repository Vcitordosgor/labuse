"""RETOURS-8 (R12) — sur une parcelle, répondre comme la fiche (les deux voies ensemble).

  · une intention COUVERTE par un outil (pièges/risques, taxe, faisabilité) OUVRE l'outil prérempli
    avec l'IDU — le message « Je n'ai pas de mesure LABUSE dédiée » ne peut plus apparaître (R12.2/3) ;
  · une question de RÉSUMÉ sur une parcelle RÉPOND avec la vraie donnée (fond de la fiche) + la voie
    fiche, jamais un mur (R12.1).
"""
from __future__ import annotations

from labuse.copilote_v2 import answering


IDU = "97409000AB0570"


def test_pieges_ouvre_l_outil_risques_prerempli():
    r = answering._sans_outil(None, "quels sont les pièges de cette parcelle ?", {"idu": IDU}, "QUESTION")
    assert r.get("porte") == "risques"              # l'outil Pièges et risques
    assert r.get("prefill_idu") == IDU              # prérempli avec l'IDU
    assert "pas de mesure" not in (r.get("text") or "").lower()   # plus jamais le mur


def test_taxe_ouvre_l_outil_taxe_amenagement():
    r = answering._sans_outil(None, "combien de taxe d'aménagement sur cette parcelle ?", {"idu": IDU}, "QUESTION")
    assert r.get("porte") == "taxe-amenagement" and r.get("prefill_idu") == IDU


def test_faisabilite_ouvre_l_outil_programme():
    r = answering._sans_outil(None, "quelle est la constructibilité ici ?", {"idu": IDU}, "OUTIL")
    assert r.get("porte") == "programme"


def test_resume_parcelle_repond_avec_la_donnee(monkeypatch):
    """« résume-moi cette parcelle » → pas un refus : la vraie donnée (fond fiche) + la voie fiche."""
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)
    monkeypatch.setattr(answering, "_substance",
                        lambda db, idu: "612 m² · zone U · à Saint-Denis · verdict LABUSE : à creuser")
    r = answering._sans_outil(None, "résume-moi cette parcelle", {"idu": IDU}, "QUESTION")
    txt = (r.get("text") or "").lower()
    assert "pas de mesure" not in txt                # plus de mur
    assert "612 m²" in r["text"] and "verdict labuse" in txt   # la vraie donnée, comme la fiche
    assert r.get("voie", {}).get("cible") == "fiche" and r["voie"]["idu"] == IDU   # + la voie fiche
