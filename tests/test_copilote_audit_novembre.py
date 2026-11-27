"""Régressions de l'audit COPILOTE du 26 novembre."""
from types import SimpleNamespace

import pytest

from labuse.api import recherche
from labuse.copilote_v2 import historique, resolveur, resume_fiche
from labuse.copilote_v2.answering import answer

IDU = "97415000CV1186"


@pytest.mark.parametrize(("adresse", "suggestion", "attendu"), [
    ("12 rue des Lilas à Saint-Paul", "14 rue des Lilas", "introuvable"),
    ("12bis rue des Lilas à Saint-Paul", "12 rue des Lilas", "introuvable"),
    ("12bis rue des Lilas à Saint-Paul", "12bis rue des Lilas", "idu"),
    ("12 bis rue des Lilas à Saint-Paul", "12 rue des Lilas", "introuvable"),
    ("12 rue des Lilas à Saint-Paul", "12 ter rue des Lilas", "introuvable"),
    ("12 rue des Lilas 97460 Saint-Denis", "12 rue des Lilas", "introuvable"),
    ("12 rue des Lilas 97400 Saint-Paul", "12 rue des Lilas", "introuvable"),
    ("12 bis rue des Lilas 97460 Saint-Paul", "12 bis rue des Lilas", "idu"),
])
def test_adresse_exacte(monkeypatch, adresse, suggestion, attendu):
    monkeypatch.setattr(recherche, "_sugg_adresse", lambda *_: [
        {"idu": IDU, "label": suggestion, "sub": "97460 Saint-Paul"}])
    res = resolveur.resoudre(None, adresse)
    assert res.kind == attendu
    if attendu == "introuvable":
        assert not res.idu and res.candidats


@pytest.mark.parametrize(("question", "champ", "valeur", "attendus"), [
    ("Quel emplacement réservé ?", "er_emplacement_reserve", [{"libelle": "Passage", "part_pct": 25}], ["Passage", "25"]),
    ("Quel est son DPE ?", "dpe_connu", {"etiquette": "E", "date": "2024-06-30", "type_batiment": "maison"}, ["classe E", "2024-06-30", "maison"]),
    ("Quel est le prix du terrain ?", "prix_terrain_secteur_eur_m2", {"insuffisant": True, "n": 1}, ["1", "insuffisant"]),
    ("La fibre ?", "fibre_parcelle", {"etat": "servi", "ftth": True, "distance_m": 95}, ["Immeuble", "95 m", "raccordable"]),
    ("La fibre ?", "fibre_parcelle", {"etat": "servi", "ftth": False, "distance_m": 30}, ["30 m", "non raccordable"]),
    ("La fibre ?", "fibre_parcelle", {"etat": "aucun_immeuble"}, ["Aucun immeuble"]),
    ("Quel potentiel constructible ?", "potentiel_verdict", {"libelle": "Configuration défavorable", "calcul": None}, ["Configuration défavorable"]),
])
def test_reponses_de_la_fiche(monkeypatch, question, champ, valeur, attendus):
    monkeypatch.setattr(resume_fiche, "_fiche", lambda *_: {})
    monkeypatch.setattr(resume_fiche, "_valeurs", lambda *_: {champ: SimpleNamespace(valeur=valeur)})
    reponse = answer(None, f"{question} {IDU}")
    assert reponse.get("champ_id") == champ
    assert all(mot in reponse["text"] for mot in attendus)
    assert "None" not in reponse["text"]


@pytest.mark.parametrize(("question", "fiche", "attendu"), [
    ("Quel droit de préemption ?", {"dispositifs": {"dpu": {"etat": "hors"}, "sup": [{"categorie": "PM1"}]}}, "hors du périmètre"),
    ("Sa dernière vente ?", {"dvf_parcelle": {"derniere_mutation": {"date_mutation": "2021-02-03"}}}, "2021-02-03"),
    ("Sa dernière vente ?", {}, "inconnue"),
])
def test_champ_de_la_parcelle(monkeypatch, question, fiche, attendu):
    monkeypatch.setattr(resume_fiche, "_fiche", lambda *_: fiche)
    assert attendu in answer(None, f"{question} {IDU}")["text"]


@pytest.mark.db
def test_historique_fidele_et_ecriture_reservee_au_proprietaire(db_session):
    question = "Q" * 2200
    reponse = {"text": "R" * 4300, "intent": "QUESTION", "sources": ["cadastre"], "porte": "communes"}
    cid = historique.enregistrer(db_session, compte_id=None, sujet="session-A", conversation_id=None,
                                message=question, reponse=reponse)
    assert cid is not None
    with pytest.raises(historique.ConversationIntrouvable):
        historique.enregistrer(db_session, compte_id=None, sujet="session-B", conversation_id=cid,
                               message="autre message", reponse=reponse)
    messages = historique.charger(db_session, None, cid, sujet="session-A")["messages"]
    assert [m["texte"] for m in messages] == [question, reponse["text"]]
    assert messages[1]["reponse"] == {"sources": ["cadastre"], "porte": "communes"}
