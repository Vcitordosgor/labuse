"""COPILOTE-2 lot 6 — mémoire cloisonnée et modèle par chemin.

Le bucket pilote NULL est FERMÉ : deux visiteurs anonymes de sessions différentes ne se lisent plus
(ni conversations, ni faits). Un compte connecté garde sa cloison par compte_id. Un seul modèle
(Haiku) sur les trois chemins.
"""
from __future__ import annotations

import pytest

from labuse.db import session_factory


@pytest.fixture
def db():
    s = session_factory()()
    from labuse.copilote_v2 import historique
    historique.ensure_tables(s.get_bind())
    try:
        yield s
    finally:
        s.close()


def _tour(db, sujet, msg, cid=None):
    from labuse.copilote_v2 import historique
    return historique.enregistrer(db, compte_id=None, conversation_id=cid, message=msg,
                                  reponse={"text": "ok", "intent": "QUESTION"}, sujet=sujet)


@pytest.mark.db  # CI-1 Lot 2 : mémoire Copilote stockée en base (fixture db)
def test_deux_anonymes_ne_se_lisent_pas(db):
    """Le cœur du lot : session A et session B (toutes deux anonymes, compte_id NULL) sont ISOLÉES."""
    cid_a = _tour(db, "s:aaaaaaaaaaaaaaaaaaaa", "conversation de A")
    cid_b = _tour(db, "s:bbbbbbbbbbbbbbbbbbbb", "conversation de B")
    db.commit()
    from labuse.copilote_v2 import historique
    # A ne voit QUE sa conversation
    ids_a = {m["id"] for m in historique.lister(db, None, sujet="s:aaaaaaaaaaaaaaaaaaaa")}
    ids_b = {m["id"] for m in historique.lister(db, None, sujet="s:bbbbbbbbbbbbbbbbbbbb")}
    assert cid_a in ids_a and cid_b not in ids_a
    assert cid_b in ids_b and cid_a not in ids_b
    # B ne peut PAS charger la conversation de A (id étranger → None → 404 côté endpoint)
    assert historique.charger(db, None, cid_a, sujet="s:bbbbbbbbbbbbbbbbbbbb") is None
    assert historique.charger(db, None, cid_a, sujet="s:aaaaaaaaaaaaaaaaaaaa") is not None


@pytest.mark.db  # CI-1 Lot 2 : mémoire Copilote stockée en base (fixture db)
def test_meme_anonyme_retrouve_son_fil(db):
    """Fermer le bucket ne casse pas la continuité : la MÊME session retrouve son fil."""
    cid = _tour(db, "s:cccccccccccccccccccc", "premier tour")
    _tour(db, "s:cccccccccccccccccccc", "deuxieme tour", cid=cid)
    db.commit()
    from labuse.copilote_v2 import historique
    hist, _ = historique.fil(db, None, cid, ttl_minutes=60, sujet="s:cccccccccccccccccccc")
    assert len(hist) >= 2
    # une autre session ne voit PAS ce fil
    hist_x, _ = historique.fil(db, None, cid, ttl_minutes=60, sujet="s:dddddddddddddddddddd")
    assert hist_x == []


@pytest.mark.db  # CI-1 Lot 2 : mémoire Copilote stockée en base (fixture db)
def test_faits_ne_fuient_pas_entre_anonymes(db):
    from labuse.copilote_v2 import historique, registre_faits
    cid = _tour(db, "s:eeeeeeeeeeeeeeeeeeee", "avec un fait")
    registre_faits.enregistrer(db, cid, [{"outil": "marche", "cle": "prix", "valeur": "1360",
                                          "source": "DVF", "millesime": "2025"}])
    db.commit()
    assert registre_faits.du_fil(db, None, cid, 60, sujet="s:eeeeeeeeeeeeeeeeeeee")
    assert registre_faits.du_fil(db, None, cid, 60, sujet="s:ffffffffffffffffffff") == []


def test_modeles_par_chemin():
    """Lot 6 (mis à jour COPILOTE-5) — l'EXTRACTION reste sur Haiku (route/sélection/web/général/
    préparer) mais le ROUTAGE prend la génération 5.5 (`claude-haiku-5-5`, repli 4.5) ; la FORMULATION
    (la phrase servie) passe à Opus (`claude-opus-5-5`, repli 4.x comme John). Le modèle ne calcule ni
    ne choisit aucun chiffre — verrou anti-invention inchangé. WEB relevable par env (test suivant)."""
    from labuse import ai_models
    from labuse.ai import core
    # Routage → Haiku 5.5 (repli 4.5, temperature omise).
    assert ai_models.model_for("copilote-route") == ai_models.MODEL_HAIKU
    assert ai_models.repli_pour(ai_models.MODEL_HAIKU) == ai_models.MODEL_HAIKU_REPLI
    assert ai_models.MODEL_HAIKU_REPLI == ai_models.MODEL_FACTUAL        # 4.5 = le filet
    assert ai_models.MODEL_HAIKU in core.NO_TEMPERATURE_MODELS
    # Sélection / web / préparer restent sur Haiku 4.5 (extraction pure, le moins cher).
    for kind in ("copilote-select", "copilote-general", "copilote-web", "copilote-prepare"):
        assert ai_models.model_for(kind) == ai_models.MODEL_FACTUAL, kind
    # Formulation → Opus, repli 4.x câblé (core.complete).
    assert ai_models.model_for("copilote-formule") == ai_models.MODEL_OPUS
    assert ai_models.repli_pour(ai_models.MODEL_OPUS) == ai_models.MODEL_OPUS_REPLI
    # Opus ET Haiku 5.5 REFUSENT `temperature` → omis par le socle (core.NO_TEMPERATURE_MODELS).
    assert ai_models.MODEL_OPUS in core.NO_TEMPERATURE_MODELS
    assert ai_models.MODEL_OPUS_REPLI in core.NO_TEMPERATURE_MODELS


def test_web_relevable_a_sonnet_par_env(monkeypatch):
    from labuse import ai_models
    monkeypatch.setenv("LABUSE_IA_MODELE_COPILOTE_WEB", ai_models.MODEL_REASONING)
    assert ai_models.model_for("copilote-web") == ai_models.MODEL_REASONING
