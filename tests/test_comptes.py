"""PREMIER EURO · E5 — le cycle de vie COMPLET du compte :
invitation → activation (CGV horodatées) → login/verrou → session → reset → paiement_requis
→ suspendu → réactivé → effacement RGPD. DB réelle (comme le reste de la suite)."""
import uuid

import pytest
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope


@pytest.fixture()
def db():
    with session_scope() as s:
        comptes.ensure_tables(s)
        yield s


def _mail():
    return f"test-{uuid.uuid4().hex[:10]}@exemple.test"


def _purge(db, email):
    db.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})
    db.commit()


def test_cycle_complet(db):
    email = _mail()
    # 1. invitation — le token clair n'est PAS en base (hash seulement)
    inv = comptes.creer_invitation(db, email)
    tok = inv["lien"].split("token=")[1]
    row = db.execute(text("SELECT invite_token_hash, statut FROM utilisateurs WHERE email = :e"),
                     {"e": email}).mappings().first()
    assert row["statut"] == "invite" and row["invite_token_hash"] != tok

    # 2. activation : mot de passe court refusé, puis OK — CGV horodatées + version
    with pytest.raises(ValueError):
        comptes.activer_par_invitation(db, tok, "court", "2026-07-22")
    assert comptes.activer_par_invitation(db, tok, "correct-horse-974", "2026-07-22")
    assert comptes.valider_invitation(db, tok) is None          # token consommé
    row = db.execute(text("SELECT cgv_acceptees_at, cgv_version, hash FROM utilisateurs"
                          " WHERE email = :e"), {"e": email}).mappings().first()
    assert row["cgv_acceptees_at"] is not None and row["cgv_version"] == "2026-07-22"
    assert row["hash"].startswith("$argon2id$")                  # jamais un hash faible

    # 3. login : ok / mauvais mdp / verrou après N échecs
    u = comptes.verifier_login(db, email, "correct-horse-974")
    assert u and u["statut_compte"] == "invite"                  # le compte attend Stripe
    for _ in range(5):
        assert comptes.verifier_login(db, email, "faux") is None
    assert comptes.verifier_login(db, email, "correct-horse-974") is None   # verrouillé
    db.execute(text("UPDATE utilisateurs SET verrouille_jusqu_a = NULL, echecs_login = 0"
                    " WHERE email = :e"), {"e": email}); db.commit()

    # 4. session : un compte NON PAYÉ (invite) ne donne AUCUN accès (durci test Vic) ;
    #    on active le compte (comme le ferait le webhook Stripe) puis la session vaut.
    tok_s = comptes.creer_session(db, u["utilisateur_id"])
    assert comptes.session_utilisateur(db, tok_s) is None        # invite = porte fermée
    db.execute(text("UPDATE comptes SET statut = 'actif' WHERE id = :c"),
               {"c": u["compte_id"]}); db.commit()
    assert comptes.session_utilisateur(db, tok_s)
    comptes.detruire_session(db, tok_s)
    assert comptes.session_utilisateur(db, tok_s) is None

    # 5. reset : email inconnu → None (anti-énumération) ; connu → lien ; sessions révoquées
    assert comptes.demander_reset(db, "inconnu@exemple.test") is None
    tok_s2 = comptes.creer_session(db, u["utilisateur_id"])
    r = comptes.demander_reset(db, email)
    tok_r = r["lien"].split("token=")[1]
    assert comptes.appliquer_reset(db, tok_r, "nouveau-mdp-secure-1")
    assert comptes.session_utilisateur(db, tok_s2) is None       # reset = sessions tombées
    assert comptes.verifier_login(db, email, "nouveau-mdp-secure-1")

    # 6. suspension → sessions mortes, login refusé compte suspendu ? (statut compte)
    comptes.suspendre_compte(db, u["compte_id"], "impaye_test")
    tok_s3_before = comptes.creer_session(db, u["utilisateur_id"])   # session créée avant…
    comptes.suspendre_compte(db, u["compte_id"], "impaye_test")      # …révoquée par la suspension
    assert comptes.session_utilisateur(db, tok_s3_before) is None
    comptes.reactiver_compte(db, u["compte_id"])
    assert comptes.verifier_login(db, email, "nouveau-mdp-secure-1")

    # 7. effacement RGPD : utilisateur purgé, audit anonymisé, compte résilié (dernier siège)
    assert comptes.supprimer_utilisateur(db, email)
    assert db.execute(text("SELECT count(*) FROM utilisateurs WHERE email = :e"),
                      {"e": email}).scalar() == 0
    assert db.execute(text("SELECT count(*) FROM evenements_compte WHERE detail = '[efface RGPD]'"
                           )).scalar() >= 1
    assert db.execute(text("SELECT statut FROM comptes WHERE id = :c"),
                      {"c": u["compte_id"]}).scalar() == "resilie"


def test_licence_unique(db):
    # refonte 22/07 : 1 licence = 1 accès — un email actif ne peut pas être ré-invité
    email = _mail()
    inv = comptes.creer_invitation(db, email)
    tok = inv["lien"].split("token=")[1]
    comptes.activer_par_invitation(db, tok, "licence-unique-974", "2026-07-22")
    with pytest.raises(ValueError):
        comptes.creer_invitation(db, email)
    _purge(db, email)


def test_double_invitation_meme_email(db):
    email = _mail()
    comptes.creer_invitation(db, email)
    comptes.creer_invitation(db, email)     # re-invitation : nouveau token, pas un doublon
    assert db.execute(text("SELECT count(*) FROM utilisateurs WHERE email = :e"),
                      {"e": email}).scalar() == 1
    _purge(db, email)
