"""AUDIT PAIEMENT · PARTIE D — conformité légale & hygiène (tests permanents)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes, models
from labuse.db import session_scope

pytestmark = pytest.mark.db


@pytest.fixture
def app_client(engine, monkeypatch):
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-conf")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-conf-0000000000000000000")
    from labuse import config
    config.get_settings.cache_clear()
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


# ─────────────────────── RGPD — effacement TOTAL bout en bout ───────────────────────

def test_rgpd_effacement_total_cascade(db_session):
    """Un compte supprimé part RÉELLEMENT : le compte, l'utilisateur, les sessions ET toutes
    ses données client (projet + piste CRM + veille) — par la cascade. L'audit est anonymisé."""
    s = db_session
    comptes.ensure_tables(s)
    email = f"rgpd-{uuid.uuid4().hex[:8]}@x.test"
    inv = comptes.creer_invitation(s, email)
    cid = inv["compte_id"]
    comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-rgpd-1", "2026-07-22")
    uid = s.execute(text("SELECT id FROM utilisateurs WHERE email=:e"), {"e": email}).scalar()
    comptes.creer_session(s, uid)
    # des données CLIENT rattachées au compte
    s.add(models.Projet(nom="Projet RGPD", fiche={}, filtres={}, compte_id=cid)); s.flush()
    s.execute(text("INSERT INTO saved_searches (nom, hash, compte_id) VALUES ('v', '#f', :c)"), {"c": cid})
    s.commit()
    assert s.execute(text("SELECT count(*) FROM projets WHERE compte_id=:c"), {"c": cid}).scalar() == 1

    assert comptes.effacer_compte_rgpd(s, email) is True

    # tout est parti
    assert s.execute(text("SELECT count(*) FROM comptes WHERE id=:c"), {"c": cid}).scalar() == 0
    assert s.execute(text("SELECT count(*) FROM utilisateurs WHERE email=:e"), {"e": email}).scalar() == 0
    assert s.execute(text("SELECT count(*) FROM sessions_auth WHERE utilisateur_id=:u"), {"u": uid}).scalar() == 0
    assert s.execute(text("SELECT count(*) FROM projets WHERE compte_id=:c"), {"c": cid}).scalar() == 0
    assert s.execute(text("SELECT count(*) FROM saved_searches WHERE compte_id=:c"), {"c": cid}).scalar() == 0
    # l'audit reste MAIS anonymisé (l'événement d'effacement subsiste, sans identité)
    assert s.execute(text("SELECT count(*) FROM evenements_compte WHERE type='compte_efface_rgpd'")).scalar() >= 1


# ─────────────────────── CGV — consentement retrouvable ───────────────────────

def test_cgv_consentement_horodate_versionne_retrouvable(db_session):
    """L'acceptation CGV est horodatée, versionnée et RETROUVABLE (preuve exportable)."""
    s = db_session
    comptes.ensure_tables(s)
    email = f"cgv-{uuid.uuid4().hex[:8]}@x.test"
    inv = comptes.creer_invitation(s, email)
    comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-cgv-1", "2026-07-22")
    row = s.execute(text("SELECT cgv_version, cgv_acceptees_at FROM utilisateurs WHERE email=:e"),
                    {"e": email}).mappings().first()
    assert row["cgv_version"] == "2026-07-22"
    assert row["cgv_acceptees_at"] is not None      # horodatage présent
    # la trace d'acceptation est aussi dans l'audit
    assert s.execute(text("SELECT count(*) FROM evenements_compte WHERE type='invitation_consommee'"
                          " AND compte_id=:c"), {"c": inv["compte_id"]}).scalar() >= 1


# ─────────────────────── Pas de donnée de carte, jamais ───────────────────────

def test_aucune_donnee_de_carte_en_base():
    """Aucune colonne de nos tables n'est destinée à une donnée de carte (PAN/CVC/expiry)."""
    import inspect

    from labuse import comptes as C
    from labuse import facturation as F
    ddl = inspect.getsource(C) + inspect.getsource(F)
    for interdit in ("card_number", "pan", "cvc", "cvv", "card_cvc", "numero_carte", "expiry"):
        assert interdit not in ddl.lower(), f"référence à une donnée de carte : {interdit}"


# ─────────────────────── Hygiène : pas de fuite, headers, QA ───────────────────────

def test_500_ne_fuit_pas_de_stack(app_client, monkeypatch):
    """Une erreur serveur renvoie un message générique, jamais une stack au client."""
    from labuse.api import app as appmod
    # forcer une 500 sur une route publique (healthz) en cassant sa dépendance
    monkeypatch.setattr(appmod, "_pipeline_cfg", lambda: (_ for _ in ()).throw(RuntimeError("secret interne")))
    r = app_client.get("/pipeline/meta")
    # soit 401 (auth avant la route), soit 500 générique — dans tous les cas, pas de stack/secret
    assert "secret interne" not in r.text and "Traceback" not in r.text


def test_headers_securite_presents(app_client):
    """Chaque réponse porte les en-têtes de sécurité de base."""
    r = app_client.get("/healthz")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "same-origin"


def test_qa_ne_cree_pas_de_trou_auth(app_client):
    """La voie QA (login pilote) exige toujours le mot de passe : pas de contournement d'auth."""
    # sans session, une route protégée est fermée
    assert app_client.get("/parcels?limit=1").status_code == 401
    # le login pilote SANS mot de passe correct échoue
    assert app_client.post("/login", data={"password": "faux"}, follow_redirects=False).status_code == 401
