"""RETOURS-8 (R13) — traiter en masse les signalements venus d'un compte interne/test.

La file contenait des signalements de test (compte NULL = interne, ou comptes.plan='interne') qui
gonflaient le compteur Pilotage. L'action admin les marque `traite` (rien n'est supprimé) : le compteur
retombe au nombre RÉEL de signalements clients. Réversible à l'unité (rouvrir).
"""
from __future__ import annotations

import types

import pytest
from sqlalchemy import text

from labuse.api import auth, dashboard

pytestmark = pytest.mark.db


def _req():
    return types.SimpleNamespace(state=types.SimpleNamespace(compte_id=None))


def test_traiter_internes_fait_retomber_le_compteur(db_session, engine, monkeypatch):
    from labuse.comptes import ensure_tables as comptes_ens
    from labuse.db import session_scope
    with session_scope() as s:
        comptes_ens(s)
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS signalements ("
                       " id bigserial PRIMARY KEY, type varchar(16), type_erreur text,"
                       " commentaire text, statut varchar(16) DEFAULT 'nouveau', compte_id integer,"
                       " created_at timestamptz DEFAULT now(), traite_at timestamptz)"))
        client = c.execute(text(
            "INSERT INTO comptes (nom, plan, statut) VALUES ('Client réel', 'integral', 'actif') RETURNING id")).scalar()
        interne = c.execute(text(
            "INSERT INTO comptes (nom, plan, statut) VALUES ('Interne', 'interne', 'actif') RETURNING id")).scalar()
        # 1 signalement client réel + 2 « de test » (un interne nommé, un sans compte).
        id_client = c.execute(text(
            "INSERT INTO signalements (type, type_erreur, commentaire, statut, compte_id) "
            "VALUES ('fiche', 'autre', 'vrai retour client', 'nouveau', :cl) RETURNING id"), {"cl": client}).scalar()
        id_interne = c.execute(text(
            "INSERT INTO signalements (type, type_erreur, commentaire, statut, compte_id) "
            "VALUES ('fiche', 'autre', 'E2E M9 — signalement via UI', 'nouveau', :it) RETURNING id"), {"it": interne}).scalar()
        id_null = c.execute(text(
            "INSERT INTO signalements (type, type_erreur, commentaire, statut, compte_id) "
            "VALUES ('annonce', 'autre', 'AAAA', 'nouveau', NULL) RETURNING id")).scalar()

    def _statut(sid):
        with engine.begin() as c:
            return c.execute(text("SELECT statut FROM signalements WHERE id=:i"), {"i": sid}).scalar()

    monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
    out = dashboard.admin_signalements_traiter_internes(_req())
    assert out["ok"] and out["traites"] >= 2             # au moins mes 2 internes/test
    # scoped à MES lignes : le client réel reste ouvert, les 2 de test passent traités (rien supprimé).
    assert _statut(id_client) == "nouveau"
    assert _statut(id_interne) == "traite" and _statut(id_null) == "traite"
    with engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM signalements WHERE id IN (:a,:b,:c)"),
                         {"a": id_client, "b": id_interne, "c": id_null}).scalar() == 3   # rien supprimé
        c.execute(text("DELETE FROM signalements WHERE id IN (:a,:b,:c)"),
                  {"a": id_client, "b": id_interne, "c": id_null})
        c.execute(text("DELETE FROM comptes WHERE nom IN ('Client réel', 'Interne')"))
