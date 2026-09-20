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


def test_faits_ne_fuient_pas_entre_anonymes(db):
    from labuse.copilote_v2 import historique, registre_faits
    cid = _tour(db, "s:eeeeeeeeeeeeeeeeeeee", "avec un fait")
    registre_faits.enregistrer(db, cid, [{"outil": "marche", "cle": "prix", "valeur": "1360",
                                          "source": "DVF", "millesime": "2025"}])
    db.commit()
    assert registre_faits.du_fil(db, None, cid, 60, sujet="s:eeeeeeeeeeeeeeeeeeee")
    assert registre_faits.du_fil(db, None, cid, 60, sujet="s:ffffffffffffffffffff") == []


def test_un_seul_modele_haiku_par_chemin():
    """Lot 6 — un seul modèle, le moins cher (Haiku), sur les trois chemins ; WEB relevable par env."""
    from labuse import ai_models
    for kind in ("copilote-route", "copilote-select", "copilote-formule", "copilote-general",
                 "copilote-web", "copilote-prepare"):
        assert ai_models.model_for(kind) == ai_models.MODEL_FACTUAL, kind


def test_web_relevable_a_sonnet_par_env(monkeypatch):
    from labuse import ai_models
    monkeypatch.setenv("LABUSE_IA_MODELE_COPILOTE_WEB", ai_models.MODEL_REASONING)
    assert ai_models.model_for("copilote-web") == ai_models.MODEL_REASONING
