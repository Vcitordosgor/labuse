"""ONBOARDING-1 (O3) — recette DE BOUT EN BOUT du tunnel d'invitation, au niveau HTTP (les routes que
le client traverse vraiment). Échoue si N'IMPORTE QUELLE étape recasse.

Couvre en particulier la CAUSE PROFONDE trouvée (O1/O2) : un lien collé depuis un e-mail avec un espace
ou un retour-ligne en queue d'URL DOIT quand même ouvrir le formulaire (avant le correctif : « Invitation
introuvable » au premier clic) ; et un lien invalide n'est JAMAIS un cul-de-sac (il offre /login).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.config import get_settings
from labuse.db import engine as _engine
from labuse.db import session_scope

pytestmark = pytest.mark.db
TAG = "onbtun-"


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


@pytest.fixture(autouse=True)
def _purge():
    yield
    with session_scope() as s:
        s.execute(text("DELETE FROM utilisateurs WHERE email LIKE :t"), {"t": f"{TAG}%"})
        s.execute(text("DELETE FROM comptes WHERE nom LIKE :t"), {"t": f"%{TAG}%"})
        s.commit()


def _invite(essai: bool = False) -> tuple[int, str, str]:
    email = f"{TAG}{uuid.uuid4().hex[:8]}@exemple.test"
    with session_scope() as s:
        inv = comptes.creer_invitation(s, email, nom=f"{TAG}client")
    if essai:
        with _engine().begin() as c:
            c.execute(text("UPDATE comptes SET statut='actif', essai_expire_at=now()+interval '48 hours'"
                           " WHERE id=:c"), {"c": inv["compte_id"]})
    return inv["compte_id"], email, inv["lien"].split("token=")[1]


def test_tunnel_http_de_bout_en_bout(client):
    """GET /invitation (formulaire) → POST /invitation (mot de passe + CGV) → login réel possible."""
    cid, email, tok = _invite()
    g = client.get("/invitation", params={"token": tok})
    assert g.status_code == 200 and "Créer votre accès" in g.text and 'name="password"' in g.text
    p = client.post("/invitation", data={"token": tok, "password": "MotDePasse123!", "cgv": "oui"},
                    follow_redirects=False)
    assert p.status_code in (303, 200)                      # → bascule paiement (intégral) ou écran d'accès
    with session_scope() as db:
        u = comptes.verifier_login(db, email, "MotDePasse123!")
    assert u is not None                                    # le mot de passe a bien été posé → login OK


def test_lien_mail_avec_espace_en_queue_fonctionne(client):
    """CAUSE PROFONDE (O2) — un lien collé depuis un e-mail (espace / retour-ligne en queue) DOIT ouvrir
    le formulaire, jamais « Invitation introuvable ». Garde de régression du correctif de trim."""
    _cid, _email, tok = _invite()
    with session_scope() as db:
        assert comptes.valider_invitation(db, tok + " ") is not None      # espace
        assert comptes.valider_invitation(db, tok + "\n") is not None     # retour-ligne
        assert comptes.valider_invitation(db, "  " + tok + "  ") is not None
    # au niveau HTTP aussi (le client mail a ajouté %20)
    g = client.get("/invitation", params={"token": tok + " "})
    assert g.status_code == 200 and "Créer votre accès" in g.text


def test_lien_invalide_offre_login_jamais_un_cul_de_sac(client):
    """O2/O4 — un lien expiré/déjà utilisé/inconnu rend un REFUS PROPRE avec un chemin de sortie
    (/login), jamais une impasse."""
    g = client.get("/invitation", params={"token": "token-inexistant"})
    assert g.status_code == 404
    assert '/login' in g.text and "Se connecter" in g.text


def test_lien_reutilise_apres_activation_refus_propre(client):
    """Un lien REUTILISÉ après activation (token consommé) → refus propre + /login (l'utilisateur a déjà
    son accès)."""
    _cid, _email, tok = _invite()
    client.post("/invitation", data={"token": tok, "password": "MotDePasse123!", "cgv": "oui"},
                follow_redirects=False)
    g = client.get("/invitation", params={"token": tok})      # re-clic du même lien
    assert g.status_code == 404 and "/login" in g.text


def test_essai_48h_meme_tunnel_puis_login(client):
    """L'essai 48 h emprunte le MÊME tunnel : invitation → mot de passe → « accès d'essai ouvert » →
    login (compte déjà actif, sans paiement)."""
    cid, email, tok = _invite(essai=True)
    p = client.post("/invitation", data={"token": tok, "password": "MotDePasse123!", "cgv": "oui"},
                    follow_redirects=False)
    assert p.status_code == 200 and "essai" in p.text.lower()
    with session_scope() as db:
        u = comptes.verifier_login(db, email, "MotDePasse123!")
    assert u is not None and u["statut_compte"] == "actif"    # essai = accès immédiat, pas de paiement


def test_mot_de_passe_trop_court_refuse_proprement(client):
    """Un mot de passe < 10 caractères → refus explicite, jamais un 500 ni un compte à demi créé."""
    _cid, _email, tok = _invite()
    p = client.post("/invitation", data={"token": tok, "password": "court", "cgv": "oui"},
                    follow_redirects=False)
    assert p.status_code == 400 and "passe" in p.text.lower()
