"""JOHN-TAYLOR-2 — la page conversationnelle de John : historique (liste / reprise / suppression),
accueil qui parle, sources & boutons tirés des LECTURES réelles, et « plus jamais d'erreur brute ».

Aucun réseau : le modèle est un faux `appel` injecté (même patron que test_john_1).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from labuse.john import accueil, carnet, chat

pytestmark = pytest.mark.db


# ════════════════════════════════ Stubs modèle ════════════════════════════════
def _usage():
    return SimpleNamespace(input_tokens=10, output_tokens=5)


def _txt(t):
    return SimpleNamespace(type="text", text=t)


def _tool(name, inp=None, tid="t1"):
    return SimpleNamespace(type="tool_use", name=name, input=inp or {}, id=tid)


def _msg(blocs):
    return SimpleNamespace(content=blocs, usage=_usage())


def _auto_appel(tool_name):
    """1er tour → lit `tool_name` ; 2e tour → une phrase sans chiffre (anti-invention trivialement vrai)."""
    def _appel(**kw):
        dernier = kw["messages"][-1]
        contenu = dernier.get("content")
        a_resultat = isinstance(contenu, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in contenu)
        if not a_resultat:
            return _msg([_tool(tool_name)])
        return _msg([_txt("Voici ma lecture : rien d'anormal ne ressort.")])
    return _appel


def _appel_qui_plante(**kw):
    raise RuntimeError("boom (simulé)")


# ════════════════════════════════ Historique ════════════════════════════════
def test_conversations_listees_rouvertes_supprimees(db_session):
    # deux conversations de DEUX comptes différents.
    a = chat.repondre(db_session, "Les jobs tournent ?", compte_id=1, appel=_auto_appel("lire_jobs"))
    b = chat.repondre(db_session, "Et les sources ?", compte_id=1, appel=_auto_appel("lire_sources"))
    autre = chat.repondre(db_session, "Question d'un autre compte", compte_id=2, appel=_auto_appel("lire_jobs"))

    # la liste du compte 1 : ses deux conversations seulement, la plus récente en tête.
    liste = chat.lister_conversations(db_session, 1)
    ids = [c["id"] for c in liste]
    assert a["conversation_id"] in ids and b["conversation_id"] in ids
    assert autre["conversation_id"] not in ids                 # cloison : jamais celle d'un autre
    assert liste[0]["id"] == b["conversation_id"]              # plus récemment utilisée en tête
    assert liste[0]["titre"].startswith("Et les sources")      # titre = première question

    # reprise d'un clic : le fil complet, cloisonné.
    fil = chat.charger_conversation(db_session, a["conversation_id"], 1)
    assert fil and fil["messages"][0]["role"] == "user"
    assert chat.charger_conversation(db_session, a["conversation_id"], 2) is None  # pas au compte 2

    # suppression cloisonnée + CASCADE des messages.
    assert chat.supprimer_conversation(db_session, a["conversation_id"], 2) is False  # pas le bon compte
    assert chat.supprimer_conversation(db_session, a["conversation_id"], 1) is True
    assert chat.charger_conversation(db_session, a["conversation_id"], 1) is None
    reste = db_session.execute(text("SELECT count(*) FROM john_messages WHERE conv_id = :i"),
                               {"i": a["conversation_id"]}).scalar()
    assert reste == 0


# ════════════════════════════════ Accueil ════════════════════════════════
def test_accueil_rien_puis_une_chose(db_session):
    chat.ensure(db_session)
    # un état propre : aucune proposition de carnet, pas d'incident posé par le test.
    db_session.execute(text("DELETE FROM john_carnet WHERE statut = 'propose'"))
    e0 = accueil.etat(db_session)
    assert e0["suggestions"] == ["Tout est à jour ?", "Qu'est-ce qui a changé depuis hier ?",
                                 "Où en est q_v21 ?"]
    base = e0["attentes"]
    if base == 0:
        assert "rien n'attend ta décision" in e0["phrase"]

    # une proposition de carnet = une chose de plus qui attend Vic.
    carnet.proposer(db_session, type="doctrine", titre="Test accueil", corps="x", par="john")
    e1 = accueil.etat(db_session)
    assert e1["attentes"] == base + 1
    assert "t'attend" in e1["phrase"]              # la phrase bascule sur « … t'attend(ent) »


# ════════════════════════════════ Sources & boutons (lectures réelles) ════════════════════════════════
def test_chat_rend_sources_et_boutons_depuis_lectures(db_session):
    out = chat.repondre(db_session, "Les jobs tournent-ils ?", compte_id=1, appel=_auto_appel("lire_jobs"))
    labels = [s["label"] for s in out["sources"]]
    assert "Jobs" in labels
    assert all("heure" in s for s in out["sources"])           # chaque puce porte sa date/heure
    assert any(b["ecran"] == "cron" for b in out["boutons"])   # bouton vers l'écran concerné

    # la méta est rangée avec le message → la reprise la rejoue.
    fil = chat.charger_conversation(db_session, out["conversation_id"], 1)
    dernier = fil["messages"][-1]
    assert dernier["role"] == "assistant"
    assert any(s["label"] == "Jobs" for s in (dernier["meta"].get("lectures") or []))


# ════════════════════════════════ Plus jamais d'erreur brute ════════════════════════════════
def test_erreur_outil_rendue_en_phrase(db_session):
    out = chat.repondre(db_session, "Un truc qui va casser", compte_id=1, appel=_appel_qui_plante)
    assert out.get("erreur") is True
    assert "boom" not in out["texte"] and "RuntimeError" not in out["texte"]   # jamais la trace brute
    assert out["texte"].startswith("Je n'ai pas pu aboutir")
    assert "journal" in out["texte"]                                           # dit où est parti le détail
    # la phrase est bien rangée dans le fil (pas de 500, pas de blanc).
    fil = chat.charger_conversation(db_session, out["conversation_id"], 1)
    assert fil["messages"][-1]["texte"].startswith("Je n'ai pas pu aboutir")
