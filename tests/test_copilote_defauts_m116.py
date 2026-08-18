"""M116 — corrections des défauts M115 (D1-D4 + D11). Tests DÉTERMINISTES (monkeypatch, aucun modèle
sauf le comptage réel qui est du SQL déterministe simulé)."""
from __future__ import annotations

from labuse.copilote_v2 import answering, outils
from labuse.copilote_v2.outils import ToolResult
from labuse.copilote_v2.router import Route


# ───────────────────────── D1 — la source est celle du critère ─────────────────────────
def _patch_filtre(monkeypatch, compte=42):
    import labuse.api.app as app
    monkeypatch.setattr(app, "filtre", lambda **k: {"compte": compte})
    monkeypatch.setattr(outils, "resoudre_commune", lambda c: c)


def test_d1_procedure_credite_bodacc_pas_cadastre(monkeypatch):
    _patch_filtre(monkeypatch)
    r = outils.compter_parcelles(None, commune="Saint-Denis", signaux="procedure")
    assert r.source == "BODACC"            # jamais « cadastre » pour un signal BODACC
    assert r.millesime is None             # pas de faux millésime cadastre


def test_d1_base_reste_cadastre_avec_millesime(monkeypatch):
    _patch_filtre(monkeypatch)
    r = outils.compter_parcelles(None, commune="Cilaos")
    assert r.source == "cadastre" and r.millesime


def test_d1_signal_derive_dit_analyse_labuse(monkeypatch):
    _patch_filtre(monkeypatch)
    r = outils.compter_parcelles(None, commune="Saint-Paul", signaux="friche")
    assert "LABUSE" in r.source            # source non établissable → dite, pas un défaut cadastre


def test_d1_plusieurs_sources_toutes_nommees(monkeypatch):
    _patch_filtre(monkeypatch)
    r = outils.compter_parcelles(None, commune="Saint-Paul", surface_min=1000, signaux="procedure")
    assert "BODACC" in r.source and "cadastre" in r.source


def test_d1_criteres_variés(monkeypatch):
    _patch_filtre(monkeypatch)
    assert outils.compter_parcelles(None, commune="X", copro="avec").source == "RNIC (copropriétés)"
    assert outils.compter_parcelles(None, commune="X", zonage="U").source == "PLU (GPU)"
    assert outils.compter_parcelles(None, commune="X", adresse_absente=True).source.startswith("Base Adresse")
    assert outils.compter_parcelles(None, commune="X", personne_morale=True).source.startswith("DGFiP")


# ───────────────────────── D11 — l'aveu d'abord, jamais le total non filtré ─────────────
def test_d11_aveu_seul_sans_chiffre_quand_aucun_filtre_applicable():
    res = ToolResult("compter_parcelles", valeur=51129,
                     data={"compte": 51129, "criteres": {"commune": "Saint-Paul"}, "criteres_labels": []},
                     source="cadastre", criteres_non_appliques=["charge foncière supérieure à 300 000 €"])
    rep = answering._reply_compte(None, "combien de parcelles avec charge > 300000 à Saint-Paul", res, None, "QUESTION")
    assert rep["refus"] == "critere_non_applicable"
    assert "51129" not in rep["text"]                       # jamais le total non filtré
    assert "charge" in rep["text"].lower()
    assert "pas encore interrogeable" in rep["text"].lower()
    assert not rep.get("carte_filtre")                      # pas de carte non filtrée trompeuse


def test_d11_aveu_puis_souscompte_quand_un_filtre_a_agi():
    res = ToolResult("compter_parcelles", valeur=1970,
                     data={"compte": 1970, "criteres": {"commune": "Saint-Denis"}, "criteres_labels": ["zone U"]},
                     source="PLU (GPU)", criteres_non_appliques=["charge foncière > 200 €/m²"])
    rep = answering._reply_compte(None, "...", res, None, "QUESTION")
    assert rep.get("refus") != "critere_non_applicable"
    t = rep["text"]
    assert "1970" in t                                       # le sous-compte filtré est servi
    assert t.lower().find("interrogeable") < t.find("1970")  # l'AVEU vient AVANT le chiffre


def test_d11_scopé_compter_parcelles_seulement():
    # un autre outil (délai) avec une réserve NON applicable garde son chemin (chiffre + réserve, M109)
    res = ToolResult("delai_instruction", valeur=9.0, data={"delai": 9.0},
                     source="Sitadel", criteres_non_appliques=["par type de dossier"])
    # _reply_compte ne doit PAS transformer en aveu-seul → il passe à _formuler (ici on vérifie juste
    # qu'il ne court-circuite pas en refus critere_non_applicable).
    import labuse.copilote_v2.answering as a
    calls = {}
    a2 = a
    orig = a._formuler
    a._formuler = lambda *args, **k: (calls.__setitem__("f", True), "9 jours (Sitadel).")[1]
    try:
        rep = a._reply_compte(None, "...", res, None, "QUESTION")
    finally:
        a._formuler = orig
    assert calls.get("f") and rep.get("refus") != "critere_non_applicable"


# ───────────────────────── D3 — PROJET texte libre ouvre le formulaire ─────────────────
def test_d3_projet_texte_libre_ouvre_le_formulaire(monkeypatch):
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: Route("PROJET", params={"commune": "Saint-Leu"},
                                              clarification="Précisez le programme ?"))
    r = answering.answer(None, "je veux monter une opération immobilière à Saint-Leu")
    assert r.get("projet_form") is not None                 # le formulaire s'ouvre malgré la clarification
    assert r["projet_form"]["prefill"].get("commune") == "Saint-Leu"
    assert not r.get("clarification")                       # plus l'ancienne question-texte


# ───────────────────────── D4 — outil vague propose la liste ─────────────────────────
def test_d4_outil_vague_propose_la_liste(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)
    r = answering._outil(None, "ouvre un outil", {})
    assert r.get("outils_liste") is True and r.get("refus") is None


def test_d4_division_garde_le_reglement(monkeypatch):
    monkeypatch.setattr(answering, "_sans_outil", lambda *a, **k: {"text": "règlement de zone", "refus": "aucun_outil"})
    r = answering._outil(None, "je veux diviser cette parcelle en lots", {})
    assert r.get("outils_liste") is None and r.get("refus") == "aucun_outil"
