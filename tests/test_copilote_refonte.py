"""COPILOTE-REFONTE — la politique de conversation Phase B, en tests DÉTERMINISTES (aucun appel
modèle réel : `classify` et `core.complete` sont mockés). Verrous du repro Girardin (voie b + continuité),
de la tenue de position, du hors-domaine, de la clarification et de la disparition du mur."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from labuse.copilote_v2 import answering
from labuse.copilote_v2.router import Route


@pytest.fixture(autouse=True)
def _no_telemetrie(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)


def _force_route(monkeypatch, intent, *, nouveau_sujet=True, **params):
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: Route(intent, params=params, nouveau_sujet=nouveau_sujet))


def _mock_general(monkeypatch, text="Le dispositif X est un mécanisme fiscal outre-mer."):
    """core.complete renvoie `text` (une seule réponse suffit pour la voie b déterministe)."""
    monkeypatch.setattr(answering.core, "complete",
                        lambda *a, **k: SimpleNamespace(text=text, degraded=False, reason=None))


# ───────────────────────── LE REPRO GIRARDIN (voie b + continuité) ─────────────────────────
def test_q1_notion_part_en_voie_b_badgee(monkeypatch):
    """Q1 « qu'est-ce que la loi Girardin » → EXPLIQUER → voie b : general=True, badgée, non refusée,
    et le _route porte voie='generale' (le mode voyage vers le tour suivant)."""
    _force_route(monkeypatch, "EXPLIQUER")
    _mock_general(monkeypatch, "La loi Girardin est un dispositif de défiscalisation outre-mer.")
    r = answering.answer(None, "qu'est-ce que la loi girardin ?")
    assert r.get("general") is True and not r.get("refus")
    assert (r.get("_route") or {}).get("voie") == "generale"
    assert "Girardin" in r["text"]


def test_q2_suivi_actualite_reste_en_voie_b(monkeypatch):
    """LE CŒUR DU REPRO — Q2 « elle est toujours en place ? » APRÈS Girardin (fil en voie b, continuation
    sans signal de donnée) RESTE en voie b : jamais un refus, jamais le web bancal. Continuité de voie."""
    _force_route(monkeypatch, "QUESTION", nouveau_sujet=False)   # le routeur peut hésiter → la continuité tranche
    _mock_general(monkeypatch, "Le principe existe toujours, mais les modalités ont évolué ; vérifiez au BOFiP.")
    hist = [{"role": "user", "content": "qu'est-ce que la loi girardin ?"},
            {"role": "assistant", "content": "La loi Girardin est un dispositif…"}]
    r = answering.answer(None, "elle est toujours en place à la Réunion ?",
                         history=hist, prior_voie="generale")
    assert r.get("general") is True                     # resté en voie b
    assert not r.get("refus")                            # JAMAIS refusé (l'ancien mur / web bancal)
    assert "BOFiP" in r["text"] or "évolué" in r["text"]


def test_signal_donnee_sort_de_la_voie_b(monkeypatch):
    """Un suivi qui porte une COMMUNE (signal de donnée) sort de la voie b même après un fil général :
    il doit pouvoir appeler la voie a (ici on vérifie qu'il n'est PAS capté par la continuité générale)."""
    _force_route(monkeypatch, "QUESTION", nouveau_sujet=False, commune="Saint-Paul")
    # on mocke le chemin QUESTION pour rester déterministe (pas de vraie sélection d'outil)
    monkeypatch.setattr(answering, "_answer_with_route",
                        lambda *a, **k: {"text": "42 (cadastre).", "intent": "QUESTION", "sources": ["cadastre"]})
    r = answering.answer(None, "et à Saint-Paul ?", prior_voie="generale")
    assert not r.get("general")                          # PAS capté par la voie b
    assert "42" in r["text"]


# ───────────────────────── TENUE DE POSITION ─────────────────────────
def test_tenue_position_recite_le_fait_source(monkeypatch):
    """« t'es sûr ? » après un fait sourcé → on MAINTIENT et on cite la source, sans re-router (0 modèle)."""
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: pytest.fail("classify ne doit PAS être appelé sur une mise en doute"))
    faits = [{"cle": "valeur", "valeur": 66.0, "outil": "compter_parcelles",
              "source": "cadastre", "millesime": "2026"}]
    r = answering.answer(None, "t'es sûr ?", faits_fil=faits)
    assert r.get("tenue") is True and "66" in r["text"] and "cadastre" in r["text"]


def test_tenue_position_voie_b_renvoie_conseil(monkeypatch):
    """« vraiment ? » après une réponse GÉNÉRALE → on maintient mais on assume le « hors LABUSE »."""
    monkeypatch.setattr(answering, "classify", lambda *a, **k: pytest.fail("pas de classify"))
    r = answering.answer(None, "vraiment ?", prior_voie="generale")
    assert r.get("tenue") is True and r.get("general") is True
    assert "BOFiP" in r["text"] or "notaire" in r["text"] or "conseil" in r["text"]


def test_mise_en_doute_detection():
    assert answering._est_mise_en_doute("t'es sûr ?")
    assert answering._est_mise_en_doute("vraiment ?")
    assert answering._est_mise_en_doute("es-tu certain ?")
    assert not answering._est_mise_en_doute("combien de parcelles sûres à Saint-Paul avec un bon potentiel ?")


# ───────────────────────── HORS-DOMAINE (1 phrase) ─────────────────────────
def test_hors_domaine_une_phrase(monkeypatch):
    """Le modèle répond « HORS_DOMAINE » (cuisine) → refus d'UNE phrase, jamais badgé general."""
    _mock_general(monkeypatch, "HORS_DOMAINE")
    r = answering._general(None, "fais-moi une recette de rougail saucisse")
    assert r.get("refus") == "hors_sujet" and not r.get("general")
    assert r["text"].count(".") <= 2                     # une phrase


# ───────────────────────── LE MUR DISPARAÎT ─────────────────────────
def test_sans_outil_sans_parcelle_bascule_voie_b(monkeypatch):
    """Aucun outil + aucune parcelle citée → CONNAISSANCE GÉNÉRALE (voie b), plus le mur « PAS D'OUTIL »."""
    _mock_general(monkeypatch, "En général, ce point relève du règlement d'urbanisme local.")
    r = answering._sans_outil(None, "c'est quoi le coefficient de biotope ?", {}, "QUESTION")
    assert r.get("general") is True and r.get("refus") != "aucun_outil"


def test_sans_outil_avec_parcelle_donne_une_voie(monkeypatch):
    """Aucun outil MAIS une parcelle citée → ce que LABUSE en sait + voie fiche (jamais un mur sec)."""
    monkeypatch.setattr(answering, "_substance", lambda db, idu: "800 m² · zone U · à Saint-Denis")
    r = answering._sans_outil(None, "quelque chose de spécial ?", {"idu": "97411000BZ1065"}, "QUESTION")
    assert (r.get("voie") or {}).get("cible") == "fiche"
    assert "800 m²" in r["text"]


def test_a_signal_data():
    assert answering._a_signal_data({"commune": "Saint-Paul"})
    assert answering._a_signal_data({"idu": "97411000BZ1065"})
    assert not answering._a_signal_data({"sujet": "girardin"})
    assert not answering._a_signal_data({})


# ───────────────────────── Q3 — « montre-les sur la carte » (demande visuelle anaphorique) ──────────
def test_montre_les_devient_recherche_visuelle(monkeypatch):
    """« montre-les sur la carte » après un compte (commune héritée) est ramené sur la voie a visuelle
    (RECHERCHE → compte + porte carte), plus un refus « ouvrir un outil »."""
    _force_route(monkeypatch, "OUTIL", commune="Saint-Paul")
    captured = {}
    monkeypatch.setattr(answering, "_answer_with_route",
                        lambda db, msg, route, **k: (captured.update(intent=route.intent),
                                                     {"text": "ok", "intent": route.intent})[1])
    answering.answer(None, "montre-les sur la carte")
    assert captured.get("intent") == "RECHERCHE"


# ───────────────────────── Q19 — résumé déterministe du fil ─────────────────────────
def test_resume_fil_liste_questions_et_faits():
    hist = [{"role": "user", "content": "combien de brûlantes à Saint-Paul"},
            {"role": "assistant", "content": "18"}, {"role": "user", "content": "délai à Saint-Denis"}]
    faits = [{"cle": "valeur", "valeur": 9.0, "source": "Sitadel"}]
    r = answering._resume_fil(hist, faits)
    assert r.get("resume") is True and "brûlantes" in r["text"] and "9 (Sitadel)" in r["text"]


def test_resume_detection():
    assert answering._est_resume("résume-moi ce qu'on s'est dit")
    assert answering._est_resume("récapitule")
    assert not answering._est_resume("combien de parcelles à Saint-Paul")


# ───────────────────────── Q14 — l'outil piscines existe dans la voie a ─────────────────────────
def test_piscines_dans_la_voie_a():
    from labuse.copilote_v2 import outils
    assert "compter_piscines" in outils.OUTILS
    assert any(t["nom"] == "compter_piscines" for t in answering.CATALOGUE)
    assert "compter_piscines" in answering._ARG_SPEC


# ═════════════ FIX-COPILOTE-BATTERIE — les 5 KO soldés ═════════════
def test_q7_compter_permis_distinct_du_delai():
    """Q7 — un outil DISTINCT pour le COMPTE de permis (valeur=compte, jamais le délai)."""
    from labuse.copilote_v2 import outils
    assert "compter_permis" in outils.OUTILS and "compter_permis" in answering._ARG_SPEC
    assert any(t["nom"] == "compter_permis" for t in answering.CATALOGUE)
    # delais_instruction reste le DÉLAI ; compter_permis le COMPTE — deux outils, deux valeurs menées.
    assert "compter_permis" in answering._ARG_SPEC and "mois" in answering._ARG_SPEC["compter_permis"]


def test_q11_extract_programme():
    """Q11 — extraction déterministe du programme de construction."""
    assert answering._extract_programme("un terrain pour 3 immeubles R+3 de 8 logements") == {
        "batiments": 3, "niveaux": 3, "logements_par_batiment": 8}
    assert answering._extract_programme("R+2 de 12 logements") == {"niveaux": 2, "logements_par_batiment": 12}
    # une QUESTION de donnée (pas de bâtiment ni R+N) n'est PAS un programme
    assert answering._extract_programme("combien de logements à Saint-Paul") is None


def test_q11_programme_ouvre_la_faisabilite(monkeypatch):
    """Q11 — un programme → porte 'programme' (Faisabilité) + prefill, la promesse d'écran tenue."""
    _force_route(monkeypatch, "RECHERCHE", programme_logements=8)
    r = answering.answer(None, "un terrain pour 3 immeubles R+3 de 8 logements")
    assert r.get("porte") == "programme"
    assert r.get("prefill_programme") == {"batiments": 3, "niveaux": 3, "logements_par_batiment": 8}


def test_q13_verification_sert_le_verdict_inline(monkeypatch):
    """Q13 — « BZ1065 vaut quoi » sert le verdict INLINE (voie a) + la voie fiche, plus muette."""
    from labuse.copilote_v2 import outils
    from labuse.copilote_v2.outils import ToolResult
    monkeypatch.setattr(outils, "fiche_parcelle", lambda db, idu: ToolResult(
        "fiche_parcelle", valeur=1625, data={"idu": idu, "commune": "Saint-Denis", "surface_m2": 1625,
                                             "zone": "Uh", "verdict": "a_creuser"}, source="cadastre"))
    from labuse.copilote_v2.router import Route
    r = answering._answer_with_route(None, "97411000BZ1065 elle vaut quoi",
                                     Route("VERIFICATION", params={"idu": "97411000BZ1065"}))
    assert r.get("tool") == "fiche_parcelle" and "a_creuser" in r["text"] and "1625" in r["text"]
    assert (r.get("voie") or {}).get("cible") == "fiche"


def test_q5_marche_valeur_primaire():
    """Q5 — le nombre principal d'une ligne de marché est extrait du dict `valeurs` imbriqué."""
    from labuse.copilote_v2.outils import _marche_valeur_primaire
    assert _marche_valeur_primaire({"median_eur_m2": 2327, "n": 44}) == 2327
    assert _marche_valeur_primaire({"prix_eur_m2": 4275}) == 4275
    assert _marche_valeur_primaire({"par_zone": {"U": {"median_eur_m2": 485}}}) is None  # pas de scalaire top
    assert _marche_valeur_primaire(None) is None
