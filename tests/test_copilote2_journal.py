"""COPILOTE-2 lot 7 — LE JOURNAL D'INSTRUCTION lisible. Une ligne humaine par tour dit ce que le
Copilote a FAIT (« J'ai lu la fiche… », « J'ai ouvert Faisabilité… », « J'ai cherché sur le web :
N sources »), au lieu du #seq/kind/payload d'avant. Le payload brut reste en admin (télémétrie)."""
from __future__ import annotations

from labuse.copilote_v2.answering import journal_ligne


def test_journal_fiche():
    rep = {"tool": "fiche_parcelle", "voie": {"cible": "fiche", "idu": "97410000AN0347"}}
    assert journal_ligne(rep) == "J'ai lu la fiche de la parcelle 97410000AN0347."


def test_journal_fiche_resume():
    rep = {"tool": "fiche_parcelle", "resume_fiche": {"idu": "97410000AN0347"}}
    assert "fiche de la parcelle 97410000AN0347" in journal_ligne(rep)


def test_journal_commune():
    rep = {"tool": "stats_commune", "resume_commune": {"commune": "Saint-Benoît"}, "porte": "communes"}
    assert journal_ligne(rep) == "J'ai lu la fiche de la commune Saint-Benoît."


def test_journal_outil():
    rep = {"porte": "programme"}
    assert journal_ligne(rep) == "J'ai ouvert Faisabilité."
    # ETUDIER-BIEN-2 Lot C — « Étudier un bien » supprimé ; l'évaluation ouvre la Calculette foncière.
    rep2 = {"porte": "calculette-fonciere", "prefill_idu": "97415000AC0016"}
    assert journal_ligne(rep2) == "J'ai ouvert la Calculette foncière pour la parcelle 97415000AC0016."


def test_journal_web():
    rep = {"web": True, "sources": ["service-public.fr", "bofip.impots.gouv.fr"]}
    assert journal_ligne(rep) == "J'ai cherché sur le web : 2 sources."
    rep1 = {"web": True, "sources": ["reunion.fr"]}
    assert journal_ligne(rep1) == "J'ai cherché sur le web : 1 source."


def test_journal_web_rien_trouve():
    rep = {"refus": "web_rien_trouve", "general": True, "sources": []}
    assert journal_ligne(rep) == "J'ai cherché sur le web."


def test_journal_carte():
    rep = {"carte_filtre": {"commune": "Saint-Leu", "filtres": {}, "libelle": "les parcelles"}}
    assert journal_ligne(rep) == "J'ai filtré la carte sur vos critères."


def test_journal_rien_pour_clarification():
    assert journal_ligne({"clarification": True, "text": "Quelle commune ?"}) is None
    assert journal_ligne({"refus": "hors_sujet", "text": "…"}) is None
