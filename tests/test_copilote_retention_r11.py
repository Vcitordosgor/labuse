"""RETOURS-8 (R11) → COPILOTE-4 — rétention 30 jours des conversations Copilote + mesure de leur poids.

  · défaut de rétention = 30 jours (COPILOTE-4 : était 7 ; réglage admin surchargeable à chaud) ;
  · le job `copilote-purge` supprime les conversations au-delà (messages par CASCADE) ;
  · `mesure()` chiffre ce que pèsent les conversations stockées (nb, Mo, croissance/jour) — R11.2 ;
  · COPILOTE-4 : `supprimer()` retire une conversation à la demande, cloisonnée (jamais celle d'un autre).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import reglages
from labuse.copilote_v2 import historique

pytestmark = pytest.mark.db


def test_retention_defaut_30_jours_et_reglable(engine):
    reglages._cache.clear()
    with engine.begin() as c:
        c.execute(text("DELETE FROM app_reglages WHERE cle = :k"), {"k": reglages.CLE_COPILOTE_RETENTION})
    assert reglages.copilote_retention_jours() == 30         # défaut config (COPILOTE-4 : était 7)
    reglages.set_int(reglages.CLE_COPILOTE_RETENTION, 14)     # réglage admin surchargeable à chaud
    assert reglages.copilote_retention_jours() == 14
    with engine.begin() as c:                                 # remise à plat
        c.execute(text("DELETE FROM app_reglages WHERE cle = :k"), {"k": reglages.CLE_COPILOTE_RETENTION})
    reglages._cache.clear()


def test_supprimer_retire_une_conversation_et_cloisonne(db_session, engine):
    """COPILOTE-4 — `supprimer()` retire la conversation du compte (messages par CASCADE), et NE
    touche JAMAIS celle d'un autre compte (cloison lot 6)."""
    historique.ensure_tables(engine)
    db = db_session
    a = db.execute(text("INSERT INTO copilote_conversations (compte_id, titre) "
                        "VALUES (101, 'à moi') RETURNING id")).scalar()
    b = db.execute(text("INSERT INTO copilote_conversations (compte_id, titre) "
                        "VALUES (202, 'à un autre') RETURNING id")).scalar()
    for cid in (a, b):
        db.execute(text("INSERT INTO copilote_messages (conversation_id, role, texte) "
                        "VALUES (:i, 'client', 'x')"), {"i": cid})
    db.commit()
    # cloison : le compte 101 ne supprime PAS la conversation du compte 202.
    assert historique.supprimer(db, compte_id=101, conversation_id=b) is False
    assert db.execute(text("SELECT count(*) FROM copilote_conversations WHERE id = :i"), {"i": b}).scalar() == 1
    # le compte 101 supprime la SIENNE → True, et ses messages tombent par CASCADE.
    assert historique.supprimer(db, compte_id=101, conversation_id=a) is True
    assert db.execute(text("SELECT count(*) FROM copilote_conversations WHERE id = :i"), {"i": a}).scalar() == 0
    assert db.execute(text("SELECT count(*) FROM copilote_messages WHERE conversation_id = :i"), {"i": a}).scalar() == 0
    db.execute(text("DELETE FROM copilote_conversations WHERE id = :i"), {"i": b}); db.commit()


def test_purge_supprime_les_vieilles_conversations(db_session, engine):
    historique.ensure_tables(engine)
    db = db_session
    # une vieille conversation (30 j) + une récente ; chacune avec un message.
    vieille = db.execute(text(
        "INSERT INTO copilote_conversations (compte_id, titre, updated_at) "
        "VALUES (NULL, 'vieille', now() - interval '30 days') RETURNING id")).scalar()
    recente = db.execute(text(
        "INSERT INTO copilote_conversations (compte_id, titre, updated_at) "
        "VALUES (NULL, 'recente', now()) RETURNING id")).scalar()
    for cid in (vieille, recente):
        db.execute(text("INSERT INTO copilote_messages (conversation_id, role, texte) "
                        "VALUES (:i, 'client', 'x')"), {"i": cid})

    n = historique.purger(db, 7)
    assert n >= 1
    reste = {r[0] for r in db.execute(text(
        "SELECT id FROM copilote_conversations WHERE id IN (:a,:b)"), {"a": vieille, "b": recente})}
    assert recente in reste and vieille not in reste          # la vieille purgée, la récente gardée
    # CASCADE : les messages de la vieille sont partis avec elle.
    assert db.execute(text("SELECT count(*) FROM copilote_messages WHERE conversation_id = :i"),
                      {"i": vieille}).scalar() == 0


def test_mesure_chiffre_le_poids(db_session, engine):
    historique.ensure_tables(engine)
    m = historique.mesure(db_session)
    for k in ("conversations", "messages", "octets", "mo", "messages_7j", "croissance_jour"):
        assert k in m
    assert isinstance(m["conversations"], int) and m["octets"] >= 0
