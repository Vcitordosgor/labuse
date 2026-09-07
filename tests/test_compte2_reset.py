"""COMPTE-2 · Lot 4 — le reset branché sur les templates 14/15 + déconnexion à distance.

Le lien de réinitialisation part par le template 14 (`mdp_oublie`) via la FILE ; la confirmation
« mot de passe modifié » part par le 15 (`mdp_modifie`) APRÈS application. Le token reste haché,
usage unique, la lecture d'infos est NON consommante. La déconnexion à distance ferme les sessions.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import comptes, mailfile

pytestmark = pytest.mark.db


@pytest.fixture()
def compte_actif(engine):
    mailfile.ensure_tables(engine)
    from labuse.db import session_scope
    with session_scope() as db:
        comptes.ensure_tables(db)
        db.execute(text("DELETE FROM utilisateurs WHERE email = 'reset2@labuse.test'"))
        db.commit()
        inv = comptes.creer_invitation(db, "reset2@labuse.test", "Client Reset")
        comptes.activer_par_invitation(db, inv["lien"].split("token=")[1], "motdepasse-initial-1",
                                       cgv_version="t")
        cid = inv["compte_id"]
    with engine.begin() as c:
        c.execute(text("DELETE FROM mail_queue WHERE compte_id = :c"), {"c": cid})
    yield cid
    from labuse.db import session_scope as _ss
    with _ss() as db:
        db.execute(text("DELETE FROM utilisateurs WHERE email = 'reset2@labuse.test'"))
        db.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid}); db.commit()


def test_demander_reset_rend_compte_et_nom(compte_actif):
    from labuse.db import session_scope
    with session_scope() as db:
        r = comptes.demander_reset(db, "reset2@labuse.test")
    assert r and r["compte_id"] == compte_actif and r["nom"] == "Client Reset"
    assert "/reset?token=" in r["lien"]


def test_reset_email_enfile_template_14(compte_actif, engine, monkeypatch):
    monkeypatch.setattr("labuse.brevo.envoyer_template",
                        lambda to, key, params: {"envoye": True, "message_id": "<x>"})
    from labuse.api.onboarding import _envoyer_reset_email
    from labuse.db import session_scope
    with session_scope() as db:
        r = comptes.demander_reset(db, "reset2@labuse.test")
    _envoyer_reset_email(r["email"], r["lien"], compte_id=r["compte_id"], nom=r["nom"])
    rows = mailfile.lister(engine, filtre="tous", compte_id=compte_actif)
    m14 = [x for x in rows if x["mail_key"] == "mdp_oublie"]
    assert m14 and m14[0]["etat"] == "recu"
    assert m14[0]["params"].get("LIEN_RESET") and m14[0]["params"].get("VALIDITE") == "1 heure"


def test_compte_du_reset_token_non_consommant(compte_actif):
    from labuse.db import session_scope
    with session_scope() as db:
        r = comptes.demander_reset(db, "reset2@labuse.test")
        tok = r["lien"].split("token=")[1]
    with session_scope() as db:
        infos1 = comptes.compte_du_reset_token(db, tok)
        infos2 = comptes.compte_du_reset_token(db, tok)   # lu deux fois → toujours valide (non consommant)
    assert infos1 and infos1["email"] == "reset2@labuse.test" and infos1["compte_id"] == compte_actif
    assert infos2 is not None
    # après application, le token est consommé → plus d'infos
    with session_scope() as db:
        assert comptes.appliquer_reset(db, tok, "nouveau-mdp-solide-2") is True
    with session_scope() as db:
        assert comptes.compte_du_reset_token(db, tok) is None


def test_deconnexion_a_distance_ferme_les_sessions(compte_actif):
    from labuse.db import session_scope
    with session_scope() as db:
        uid = db.execute(text("SELECT id FROM utilisateurs WHERE compte_id = :c"),
                         {"c": compte_actif}).scalar()
        comptes.creer_session(db, uid)
        comptes.creer_session(db, uid)
        avant = db.execute(text("SELECT count(*) FROM sessions_auth WHERE utilisateur_id = :u"),
                           {"u": uid}).scalar()
        assert avant == 2
        n = comptes.deconnecter_compte(db, compte_actif)
        apres = db.execute(text("SELECT count(*) FROM sessions_auth WHERE utilisateur_id = :u"),
                           {"u": uid}).scalar()
    assert n == 2 and apres == 0
