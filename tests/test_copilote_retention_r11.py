"""RETOURS-8 (R11) — rétention 7 jours des conversations Copilote + mesure de leur poids.

  · défaut de rétention = 7 jours (réglage admin surchargeable à chaud via app_reglages) ;
  · le job `copilote-purge` supprime les conversations au-delà (messages par CASCADE) ;
  · `mesure()` chiffre ce que pèsent les conversations stockées (nb, Mo, croissance/jour) — R11.2.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import reglages
from labuse.copilote_v2 import historique

pytestmark = pytest.mark.db


def test_retention_defaut_7_jours_et_reglable(engine):
    reglages._cache.clear()
    with engine.begin() as c:
        c.execute(text("DELETE FROM app_reglages WHERE cle = :k"), {"k": reglages.CLE_COPILOTE_RETENTION})
    assert reglages.copilote_retention_jours() == 7          # défaut config (R11)
    reglages.set_int(reglages.CLE_COPILOTE_RETENTION, 14)     # réglage admin surchargeable à chaud
    assert reglages.copilote_retention_jours() == 14
    with engine.begin() as c:                                 # remise à plat
        c.execute(text("DELETE FROM app_reglages WHERE cle = :k"), {"k": reglages.CLE_COPILOTE_RETENTION})
    reglages._cache.clear()


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
