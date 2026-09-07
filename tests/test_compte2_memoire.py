"""COMPTE-2 · Lot 6 — la mémoire du compte : les préférences de carte (fond + couches) VIVENT en base,
donc survivent au changement de poste (avant : localStorage seulement → perdues). Le reste des objets
client (veilles, projets, CRM, Copilote) est déjà cloisonné par compte_id (cf. test_audit_secu) et
survit de la même façon ; ce qui vit en localStorage (repli de légende…) est perdu au changement de
poste — c'est documenté au compte-rendu.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse import comptes

pytestmark = pytest.mark.db


@pytest.fixture()
def compte(engine):
    from labuse.db import session_scope
    with session_scope() as db:
        comptes.ensure_tables(db)
        cid = db.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                              " ('Mémoire test', 'integral', 'actif') RETURNING id")).scalar()
        db.commit()
    yield cid
    with session_scope() as db:
        db.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid}); db.commit()


def test_prefs_carte_absentes_par_defaut(compte):
    from labuse.db import session_scope
    with session_scope() as db:
        assert comptes.lire_prefs_carte(db, compte) is None
        assert comptes.lire_prefs_carte(db, None) is None      # pilote/anonyme


def test_prefs_carte_survivent_a_la_session(compte):
    """Écrites dans une « session », relues dans une AUTRE (autre connexion db = autre navigateur) :
    le fond de carte et les couches reviennent — clés par compte_id, jamais par session."""
    from labuse.db import session_scope
    couches = {"zonage": True, "parcelles": True, "ppr": False}
    with session_scope() as db:
        comptes.ecrire_prefs_carte(db, compte, "ortho", couches)
    with session_scope() as db2:                               # « autre navigateur »
        p = comptes.lire_prefs_carte(db2, compte)
    assert p and p["basemap"] == "ortho" and p["couches"]["zonage"] is True
    assert p["couches"]["parcelles"] is True and p["couches"]["ppr"] is False


def test_prefs_carte_upsert(compte):
    from labuse.db import session_scope
    with session_scope() as db:
        comptes.ecrire_prefs_carte(db, compte, "dark", {"zonage": False})
        comptes.ecrire_prefs_carte(db, compte, "clair", {"zonage": True, "znieff": True})
        p = comptes.lire_prefs_carte(db, compte)
        n = db.execute(text("SELECT count(*) FROM prefs_carte WHERE compte_id = :c"), {"c": compte}).scalar()
    assert n == 1 and p["basemap"] == "clair" and p["couches"]["znieff"] is True


def test_prefs_carte_cascade_a_l_effacement(compte):
    """RGPD : effacer le compte efface ses préférences (FK ON DELETE CASCADE)."""
    from labuse.db import session_scope
    with session_scope() as db:
        comptes.ecrire_prefs_carte(db, compte, "plan", {"parcelles": True})
    with session_scope() as db:
        db.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": compte}); db.commit()
    with session_scope() as db:
        assert db.execute(text("SELECT count(*) FROM prefs_carte WHERE compte_id = :c"),
                          {"c": compte}).scalar() == 0
