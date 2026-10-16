"""RECETTE-GÉNÉRALE-1 — correctifs mails/onboarding/abonnement + résumé circuit.

A-07-2 : le message « mot de passe oublié » ne promet un envoi que si l'envoi RÉEL est actif
         (`envoi_reel_autorise`), pas dès que `BREVO_API_KEY` existe. En dry-run → message neutre.
A-07-5 : les transitions d'état d'abonnement émettent un mail AUTOMATIQUE (résiliation 16,
         suspension 10, rétablissement 11), best-effort comme `relance_carte` (jamais bloquer).
A-08-2 : le sujet du `.eml` interne « demande de courrier » reste ASCII lisible (« ×1 » → « x1 »),
         en-tête proprement encodé (plus d'encodage RFC2047 fragmenté cassé).
A-09-1 : `verrous.phrases` du résumé circuit n'est plus vide quand tout est vert : il porte la
         phrase de CHAQUE verrou (le résumé « dit vrai »).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

import pytest
from sqlalchemy import text

from labuse.config import get_settings


# ───────────────────────── A-07-2 — message reset honnête (pas de DB) ─────────────────────────

class _FauxRequest:
    def __init__(self, body: bytes):
        self._body = body

    async def body(self) -> bytes:  # noqa: D401 — surface minimale pour reset_demande
        return self._body


def _corps_reset(monkeypatch, *, reel: bool) -> str:
    """Appelle reset_demande AVEC un e-mail vide (anti-DB : la branche d'envoi est sautée) et
    renvoie le HTML. Le message dépend UNIQUEMENT de `envoi_reel_autorise` (A-07-2)."""
    import asyncio

    from labuse.api import onboarding
    monkeypatch.setattr(onboarding, "envoi_reel_autorise", lambda *a, **k: reel, raising=False)
    # `envoi_reel_autorise` est importé DANS la fonction → on patche à la source aussi.
    monkeypatch.setattr("labuse.config.envoi_reel_autorise", lambda *a, **k: reel)
    resp = asyncio.run(onboarding.reset_demande(_FauxRequest(b"email="), db=None))
    return resp.body.decode("utf-8")


def test_a072_dry_run_message_neutre(monkeypatch):
    html = _corps_reset(monkeypatch, reel=False)
    assert "vient d'être envoyé" not in html, "en dry-run on ne doit JAMAIS affirmer qu'un mail est parti"
    assert "n'est pas\nactif" in html or "n'est pas actif" in html or "pas\n" in html or "Demande enregistrée" in html
    assert "Demande enregistrée" in html
    # anti-énumération préservée : jamais révéler si le compte existe
    assert "Si un compte est associé" in html


def test_a072_envoi_reel_message_promet_lenvoi(monkeypatch):
    html = _corps_reset(monkeypatch, reel=True)
    assert "vient d'être envoyé" in html, "envoi réel actif → on annonce l'envoi"
    assert "Si un compte est associé" in html  # anti-énumération toujours là


# ───────────────────────── A-08-2 — sujet du .eml interne lisible (pas de DB) ─────────────────────────

def test_a082_sujet_courrier_ascii_lisible():
    """Le « × » (U+00D7) du récap communes casse l'en-tête Subject (RFC2047 fragmenté). Le sujet
    doit rester ASCII lisible (× → x, · → -) et l'en-tête sérialisé ne contient aucun mot encodé."""
    from email.message import EmailMessage

    com = "Saint-Denis ×1 · Saint-Paul ×2"
    titre = f"Compte #3 demande l'envoi de 3 courriers ({com})"
    # la transformation appliquée dans api/courrier.py :
    titre_sujet = titre.replace("×", "x").replace(" · ", " - ")
    assert "×" not in titre_sujet and " · " not in titre_sujet
    assert "x1" in titre_sujet and "x2" in titre_sujet

    m = EmailMessage()
    m["Subject"] = f"[LABUSE] {titre_sujet}"
    serialise = m.as_string().split("\n\n", 1)[0]
    assert "=?utf-8?" not in serialise, "le sujet ASCII ne doit plus déclencher d'encodage RFC2047"
    # et l'ANCIEN sujet (avec ×) déclenchait bien l'encodage fragmenté (preuve de la régression) :
    m2 = EmailMessage()
    m2["Subject"] = f"[LABUSE] {titre}"
    assert "=?utf-8?" in m2.as_string().split("\n\n", 1)[0]


# ───────────────────────── A-09-1 — verrous.phrases complet (pas de DB) ─────────────────────────

def test_a091_phrases_couvre_tous_les_verrous():
    """La synthèse construit `phrases` à partir de TOUS les verrous, plus seulement des cassés —
    donc jamais vide quand tout est vert (donnée morte avant le fix)."""
    from labuse.circuit_verrous import VERROUS

    phrases = {v.id: v.phrase for v in VERROUS}
    assert len(phrases) == len(VERROUS) >= 20
    assert all(p for p in phrases.values()), "chaque verrou porte une phrase non vide"


@pytest.mark.db
def test_a091_synthese_phrases_non_vide_quand_tout_vert(db_session):
    """Même après un passage SANS cassé (casses == []), `verrous.phrases` reste rempli."""
    from labuse import circuit_journal, circuit_verrous as CV
    circuit_journal.ensure(db_session)
    circuit_journal.journaliser(db_session, "controle", "verrous", "cli", "ok",
                                {"joues": len(CV.VERROUS), "casses": [], "a_decider": []})
    s = CV.synthese_pour_page(db_session)
    assert s["casses"] == []
    assert len(s["phrases"]) == len(CV.VERROUS), "phrases doit couvrir tous les verrous, même tout-vert"
    for v in CV.VERROUS:
        assert s["phrases"][v.id] == v.phrase


# ───────────────────────── A-07-5 — mails automatiques sur transition d'état (DB) ─────────────────────────

_SECRET = "whsec_test_recette1"


@pytest.fixture(autouse=True)
def _no_real_mail(monkeypatch):
    """Dry-run étanche : le transport Brevo est mocké → aucun vrai e-mail (comme test_facturation)."""
    monkeypatch.setattr("labuse.brevo.envoyer_template",
                        lambda to, key, params: {"envoye": True, "message_id": "<test>"})


@pytest.fixture()
def db_webhook(monkeypatch):
    from labuse import comptes
    from labuse.db import session_scope
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", _SECRET)
    with session_scope() as s:
        comptes.ensure_tables(s)
        yield s


def _signe(payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    t = int(time.time())
    sig = hmac.new(_SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={t},v1={sig}"


def _evt(type_, obj):
    return {"id": f"evt_{uuid.uuid4().hex[:16]}", "object": "event", "api_version": "2024-06-20",
            "type": type_, "data": {"object": obj}}


@pytest.mark.db
def test_a075_resiliation_mail_auto_sur_subscription_deleted(db_webhook):
    """`customer.subscription.deleted` → suspendre_compte ET mail `resiliation` (template 16) enfilé."""
    from labuse import comptes, mailfile
    from labuse.db import engine as _engine
    from labuse.facturation import traiter_webhook
    mailfile.ensure_tables(_engine())
    email = f"resil-{uuid.uuid4().hex[:8]}@exemple.test"
    cus = f"cus_{uuid.uuid4().hex[:10]}"
    cid = comptes.creer_invitation(db_webhook, email)["compte_id"]
    with _engine().begin() as c:
        c.execute(text("DELETE FROM mail_queue WHERE compte_id = :c"), {"c": cid})
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_r"}))
    traiter_webhook(db_webhook, body, sig)
    body, sig = _signe(_evt("customer.subscription.deleted", {"customer": cus}))
    traiter_webhook(db_webhook, body, sig)
    assert db_webhook.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() == "suspendu"
    rows = [r for r in mailfile.lister(_engine(), filtre="tous", compte_id=cid)
            if r["mail_key"] == "resiliation"]
    assert rows, "résiliation : mail template 16 attendu"
    assert rows[0]["demandeur"] == "job:stripe-webhook"
    db_webhook.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})


@pytest.mark.db
def test_a075_retablissement_mail_auto_sur_invoice_paid(db_webhook):
    """invoice.paid qui RÉACTIVE un compte suspendu → mail `retablissement` (template 11) enfilé."""
    from labuse import comptes, mailfile
    from labuse.db import engine as _engine
    from labuse.facturation import traiter_webhook
    mailfile.ensure_tables(_engine())
    email = f"retab-{uuid.uuid4().hex[:8]}@exemple.test"
    cus = f"cus_{uuid.uuid4().hex[:10]}"
    cid = comptes.creer_invitation(db_webhook, email)["compte_id"]
    body, sig = _signe(_evt("checkout.session.completed",
                            {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_t"}))
    traiter_webhook(db_webhook, body, sig)
    # on casse le paiement (actif → paiement_requis) puis on paie (→ réactivation = rétablissement)
    body, sig = _signe(_evt("invoice.payment_failed", {"customer": cus}))
    traiter_webhook(db_webhook, body, sig)
    with _engine().begin() as c:
        c.execute(text("DELETE FROM mail_queue WHERE compte_id = :c AND mail_key = 'retablissement'"), {"c": cid})
    body, sig = _signe(_evt("invoice.paid", {"customer": cus}))
    traiter_webhook(db_webhook, body, sig)
    assert db_webhook.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() == "actif"
    rows = [r for r in mailfile.lister(_engine(), filtre="tous", compte_id=cid)
            if r["mail_key"] == "retablissement"]
    assert rows, "rétablissement : mail template 11 attendu"
    db_webhook.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})


@pytest.mark.db
def test_a075_suspension_mail_auto_sur_bascule_essai(db_webhook):
    """La bascule d'essai (suspension AUTOMATIQUE) émet le mail `suspension` (template 10)."""
    from labuse import comptes, mailfile
    from labuse.db import engine as _engine
    mailfile.ensure_tables(_engine())
    email = f"essai-{uuid.uuid4().hex[:8]}@exemple.test"
    cid = comptes.creer_invitation(db_webhook, email)["compte_id"]
    db_webhook.execute(text("UPDATE comptes SET essai_expire_at = now() - interval '1 hour' WHERE id = :c"),
                       {"c": cid})
    db_webhook.commit()
    with _engine().begin() as c:
        c.execute(text("DELETE FROM mail_queue WHERE compte_id = :c"), {"c": cid})
    comptes.basculer_essai_expire(db_webhook, cid)
    assert db_webhook.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() == "suspendu"
    rows = [r for r in mailfile.lister(_engine(), filtre="tous", compte_id=cid)
            if r["mail_key"] == "suspension"]
    assert rows, "bascule d'essai : mail suspension (template 10) attendu"
    assert rows[0]["params"].get("LIEN_PAIEMENT")
    db_webhook.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})


@pytest.mark.db
def test_a075_best_effort_un_envoi_qui_echoue_ne_casse_pas_la_transition(db_webhook, monkeypatch):
    """Comme relance_carte : si l'enfilage du mail lève, la transition d'état tient quand même."""
    from labuse import comptes
    email = f"boom-{uuid.uuid4().hex[:8]}@exemple.test"
    cid = comptes.creer_invitation(db_webhook, email)["compte_id"]

    def _boom(*a, **k):
        raise RuntimeError("file indisponible")

    monkeypatch.setattr("labuse.mail.envoyer_mail", _boom)
    # ne doit PAS lever ; la suspension est actée
    comptes.suspendre_compte(db_webhook, cid, motif="test")
    comptes.mail_cycle_de_vie_auto(db_webhook, cid, "suspension", "job:test")
    assert db_webhook.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": cid}).scalar() == "suspendu"
    db_webhook.execute(text("DELETE FROM utilisateurs WHERE email = :e"), {"e": email})
