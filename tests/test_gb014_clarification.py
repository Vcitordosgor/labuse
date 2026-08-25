"""GB-014 — le dernier finding du Grand Balayage, soldé en DÉTERMINISTE.

Trois leviers, chacun testé sans appel modèle (classify/core.complete mockés au besoin) :
- (Q24/Q25) déictique vague SANS antécédent → clarification courte, jamais un hors-sujet au hasard ;
- (Q29) multi-intentions → on NOMME ce qu'on laisse, plus jamais de largage silencieux ;
- (Q30) créole réunionnais on-topic → voie b, jamais « hors-domaine ».
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from labuse.copilote_v2 import answering
from labuse.copilote_v2.router import Route


@pytest.fixture(autouse=True)
def _no_telemetrie(monkeypatch):
    monkeypatch.setattr(answering.telemetrie, "refus", lambda *a, **k: None)


# ───────────────────────── (Q24/Q25) déictique vague sans antécédent ─────────────────────────
def test_q24_cher_labas_sans_antecedent_clarifie():
    """« c'est cher là-bas ? » (nouveau fil) → clarification qui demande le LIEU, jamais le hors-sujet."""
    r = answering.answer(None, "c'est cher là-bas ?")
    assert r.get("clarification") is True
    assert "commune" in r["text"].lower()
    assert answering.HORS_SUJET not in r["text"]


def test_q25_compare_les_deux_clarifie():
    """« compare les deux » (nouveau fil) → clarification « comparer quoi ? », pas une redirection fiche."""
    r = answering.answer(None, "compare les deux")
    assert r.get("clarification") is True
    assert "comparer" in r["text"].lower()


def test_deictique_avec_antecedent_herite_pas_de_clarification(monkeypatch):
    """« c'est cher là-bas ? » APRÈS une commune (prior_params) → le fil la résout : on N'INTERROMPT PAS,
    on laisse classify router (pas de clarification déterministe)."""
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: Route("QUESTION", params={"commune": "Saint-Leu"}, nouveau_sujet=False))
    monkeypatch.setattr(answering, "_answer_with_route",
                        lambda *a, **k: {"text": "Le prix médian…", "intent": "QUESTION"})
    r = answering.answer(None, "c'est cher là-bas ?", prior_params={"commune": "Saint-Leu"})
    assert not r.get("clarification")


def test_clarif_anaphore_unitaire():
    assert answering._clarif_anaphore("c'est cher là-bas ?", None, None)
    assert answering._clarif_anaphore("compare les deux", None, None)
    # antécédent → None (héritage) ; message qui nomme son lieu → None (rien à clarifier)
    assert answering._clarif_anaphore("c'est cher là-bas ?", {"commune": "Cilaos"}, None) is None
    assert answering._clarif_anaphore("c'est cher à Saint-Denis ?", None, None) is None
    # parcelle embarquée = antécédent
    assert answering._clarif_anaphore("compare les deux", None, {"idu": "97411000AB0001"}) is None


# ───────────────────────── (Q30) créole réunionnais on-topic ─────────────────────────
def test_est_creole_foncier():
    assert answering._est_creole_foncier("kosa i lé in kaz an tol ?")
    assert not answering._est_creole_foncier("combien de piscines à Saint-Paul ?")


def test_q30_creole_bascule_en_voie_b(monkeypatch):
    """Créole du bâti classé HORS_SUJET par le routeur → l'override le renvoie en voie b (general=True),
    jamais le message hors-sujet."""
    monkeypatch.setattr(answering, "classify", lambda *a, **k: Route("HORS_SUJET", nouveau_sujet=True))
    monkeypatch.setattr(answering.core, "complete",
                        lambda *a, **k: SimpleNamespace(
                            text="In kaz an tol lé in kaz konstrwi an tôl — abitasion tradisionèl.",
                            degraded=False, reason=None))
    r = answering.answer(None, "kosa i lé in kaz an tol ?")
    assert r.get("general") is True
    assert r.get("refus") != "hors_sujet"


# ───────────────────────── (Q29) multi-intentions : nommer ce qu'on laisse ─────────────────────────
Q29 = ("Bonjour, j'ai plusieurs questions. D'abord je voudrais savoir combien de parcelles brûlantes il "
       "y a à Saint-Pierre et aussi quel est le délai moyen d'instruction des permis là-bas. Ensuite, "
       "pour un terrain, je pense faire deux immeubles R+2 avec huit logements, est-ce que c'est faisable "
       "et quelle serait la surface de plancher. Et enfin, le dispositif Pinel outre-mer est-il toujours "
       "en vigueur ?")


def test_segments_demande_q29():
    segs = answering._segments_demande(Q29)
    assert len(segs) >= 3


def test_multi_reste_ne_renomme_pas_le_segment_traite():
    """Le programme (immeubles/plancher) étant traité (prefill), le reste NOMMÉ = brûlantes/délai + Pinel."""
    reste = answering._multi_demandes_reste(Q29, {"prefill_programme": {"niveaux": 2}, "porte": "programme"})
    joined = answering._fold_py(" ".join(reste).lower())
    assert "pinel" in joined
    assert ("brulante" in joined) or ("delai" in joined)
    assert "plancher" not in joined            # le segment traité n'est pas re-listé


def test_q29_integration_nomme_les_restes(monkeypatch):
    """Bout-en-bout : le programme est pré-rempli ET les autres demandes sont nommées (multi_intent)."""
    monkeypatch.setattr(answering, "classify", lambda *a, **k: Route("OUTIL", nouveau_sujet=True))
    r = answering.answer(None, Q29)
    assert r.get("multi_intent") is True
    assert "séparément" in r["text"]
    assert "Pinel" in r["text"]                 # la demande larguée est nommée, plus de silence


def test_mono_demande_ne_declenche_pas_multi(monkeypatch):
    """Une question composée courte (une commune, deux métriques) ne se fait PAS sur-découper."""
    monkeypatch.setattr(answering, "classify",
                        lambda *a, **k: Route("QUESTION", params={"commune": "Saint-Paul"}, nouveau_sujet=True))
    monkeypatch.setattr(answering, "_answer_with_route",
                        lambda *a, **k: {"text": "385 piscines détectées.", "intent": "QUESTION"})
    r = answering.answer(None, "combien de piscines à Saint-Paul ?")
    assert not r.get("multi_intent")


def test_clarification_ne_declenche_pas_multi():
    """Une clarification (déictique) ne doit jamais porter le bloc multi-intentions."""
    r = answering.answer(None, "compare les deux")
    assert not r.get("multi_intent")
