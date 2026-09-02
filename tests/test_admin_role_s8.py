"""SUITE-1 · S8 — exploitation admin : lister / promouvoir / rétrograder (comptes.py).

Les commandes CLI `admin-list` / `admin-set` s'appuient sur `lister_admins` et
`definir_role_admin` : promotion/rétrogradation journalisée, idempotente, refus si email inconnu.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db


def _creer_utilisateur(db, role: str = "titulaire") -> str:
    email = f"s8-{uuid.uuid4().hex[:10]}@labuse.local"
    cid = db.execute(text("INSERT INTO comptes (nom, plan, statut, sieges)"
                          " VALUES ('S8', 'integral', 'actif', 1) RETURNING id")).scalar()
    db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut)"
                    " VALUES (:c, :e, :r, 'actif')"), {"c": cid, "e": email, "r": role})
    db.commit()
    return email


def test_promotion_puis_retrogradation_journalisee():
    with session_scope() as db:
        email = _creer_utilisateur(db)
        # promotion
        r = comptes.definir_role_admin(db, email, admin=True)
        assert r["change"] and r["role"] == "admin"
        assert any(a["email"] == email for a in comptes.lister_admins(db))
        # journalisée
        n = db.execute(text("SELECT count(*) FROM evenements_compte WHERE utilisateur_id = :u"
                            " AND type = 'admin_promu'"), {"u": r["utilisateur_id"]}).scalar()
        assert n >= 1
        # rétrogradation
        r2 = comptes.definir_role_admin(db, email, admin=False)
        assert r2["change"] and r2["role"] == "titulaire"
        assert not any(a["email"] == email for a in comptes.lister_admins(db))


def test_idempotence_aucun_changement():
    with session_scope() as db:
        email = _creer_utilisateur(db, role="titulaire")
        r = comptes.definir_role_admin(db, email, admin=False)  # déjà titulaire
        assert r["change"] is False


def test_email_inconnu_leve():
    with session_scope() as db:
        with pytest.raises(ValueError):
            comptes.definir_role_admin(db, "inconnu-s8@nulle-part.test", admin=True)
