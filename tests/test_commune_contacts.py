"""ADMIN-1 (AD10) — carnet des contacts nommés de communes : CRUD + idempotence DDL."""
from __future__ import annotations

import pytest

from labuse import commune_contacts as cc
from labuse.db import session_scope

pytestmark = pytest.mark.db


def test_ensure_table_idempotent(engine):
    # deux appels d'affilée ne lèvent pas (CREATE IF NOT EXISTS)
    cc.ensure_table(engine)
    cc.ensure_table(engine)


def test_crud_contact_cycle(engine):
    cc.ensure_table(engine)
    with session_scope() as db:
        # nettoyage préalable (insee de test)
        db.execute(__import__("sqlalchemy").text("DELETE FROM commune_contacts WHERE insee = '97999'"))
        db.commit()
        c = cc.creer(db, insee="97999", commune_nom="Testville", nom="Mme Serveau",
                     role="resp. PLU", telephone="0692", email="s@x.re", note="matin")
        db.commit()
        assert c["id"] and c["nom"] == "Mme Serveau" and c["role"] == "resp. PLU"
        lst = cc.lister(db, "97999")
        assert len(lst) == 1 and lst[0]["email"] == "s@x.re"
        # présent dans le groupé
        tous = {g["insee"]: g for g in cc.lister_tous(db)}
        assert "97999" in tous and tous["97999"]["contacts"]
        # modification partielle
        maj = cc.modifier(db, c["id"], role="resp. urbanisme", telephone="0693")
        db.commit()
        assert maj["role"] == "resp. urbanisme" and maj["telephone"] == "0693" and maj["nom"] == "Mme Serveau"
        # suppression
        assert cc.supprimer(db, c["id"]) is True
        db.commit()
        assert cc.lister(db, "97999") == []
        assert cc.supprimer(db, c["id"]) is False   # déjà supprimé
