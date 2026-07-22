"""AUDIT PAIEMENT · PARTIE B — cycle de vie Stripe (argent ↔ état jamais divergents).
Webhook signé, rejeu idempotent, ordre/course, FLASH récupérable et cloisonné. Signature
calculée sans compte Stripe (le secret webhook suffit)."""
import hashlib
import hmac
import json
import time
import uuid

import pytest
from sqlalchemy import text

from labuse import comptes
from labuse.config import get_settings
from labuse.db import session_scope
from labuse.facturation import ensure_flash_table, flash_pdf_par_token, flash_statut, traiter_webhook

pytestmark = pytest.mark.db
SECRET = "whsec_audit_stripe"


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", SECRET)
    with session_scope() as s:
        comptes.ensure_tables(s)
        yield s


@pytest.fixture
def parcelle():
    """Parcelle DÉDIÉE (créée puis supprimée) pour tester la génération Flash sans dépendre
    des données de la base de test ni la polluer."""
    idu = f"974990FL{uuid.uuid4().hex[:6].upper()}"
    wkt = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
            " centroid, bbox) VALUES (:i,'X','ZZ','1', ST_GeomFromText(:w,4326),"
            " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
            " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "w": wkt}); s.commit()
    yield idu
    with session_scope() as s:
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu}); s.commit()


def _signe(payload: dict):
    body = json.dumps(payload).encode()
    t = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={t},v1={sig}"


def _evt(type_, obj, eid=None):
    return {"id": eid or f"evt_{uuid.uuid4().hex[:12]}", "object": "event",
            "type": type_, "data": {"object": obj}}


def _statut(db, cid):
    return db.execute(text("SELECT statut FROM comptes WHERE id=:c"), {"c": cid}).scalar()


# ─────────────── Webhook : rejeu idempotent (Stripe réessaie en vrai) ───────────────

def test_webhook_rejeu_meme_event_id_ignore(db):
    """Le MÊME event id rejoué → ignoré : pas de double activation, pas de re-suspension."""
    email = f"rejeu-{uuid.uuid4().hex[:8]}@x.test"
    inv = comptes.creer_invitation(db, email)
    cid, cus = inv["compte_id"], f"cus_{uuid.uuid4().hex[:8]}"
    fixe = f"evt_rejeu_{uuid.uuid4().hex[:12]}"   # unique par run, réutilisé pour les 2 appels
    ev = _evt("checkout.session.completed",
              {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_x"},
              eid=fixe)
    body, sig = _signe(ev)
    assert traiter_webhook(db, body, sig)["action"] == "activation"
    assert _statut(db, cid) == "actif"
    # une suspension manuelle puis REJEU du checkout.completed (même id) ne doit PAS ré-activer
    comptes.suspendre_compte(db, cid, "test")
    assert traiter_webhook(db, body, sig)["action"] == "rejeu_ignore"
    assert _statut(db, cid) == "suspendu"       # le rejeu n'a rien fait
    db.execute(text("DELETE FROM utilisateurs WHERE email=:e"), {"e": email}); db.commit()


def test_webhook_ordre_inverse_ne_perd_pas_l_actif(db):
    """Course : invoice.paid AVANT que le compte soit connu (customer non lié) → no-op, puis
    checkout.completed le lie et l'active. État final = actif (jamais perdu)."""
    email = f"ordre-{uuid.uuid4().hex[:8]}@x.test"
    inv = comptes.creer_invitation(db, email)
    cid, cus = inv["compte_id"], f"cus_{uuid.uuid4().hex[:8]}"
    # invoice.paid arrive en premier, customer pas encore lié → ignoré proprement
    b1, s1 = _signe(_evt("invoice.paid", {"customer": cus}))
    traiter_webhook(db, b1, s1)               # no crash, no-op
    assert _statut(db, cid) == "invite"
    # puis checkout.completed → lie + active
    b2, s2 = _signe(_evt("checkout.session.completed",
                         {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_y"}))
    assert traiter_webhook(db, b2, s2)["action"] == "activation"
    assert _statut(db, cid) == "actif"
    db.execute(text("DELETE FROM utilisateurs WHERE email=:e"), {"e": email}); db.commit()


# ─────────────── FLASH : récupérable, cloisonné à l'IDU, expirable ───────────────

def _flash_paye(db, idu="97499000ZZ0001"):
    ensure_flash_table(db)
    sid = f"cs_test_{uuid.uuid4().hex[:12]}"
    db.execute(text("INSERT INTO flash_commandes (stripe_session_id, idu) VALUES (:s, :i)"),
               {"s": sid, "i": idu})
    db.commit()
    body, sig = _signe(_evt("checkout.session.completed",
                            {"id": sid, "mode": "payment", "customer_details": {"email": "f@x.test"}}))
    assert traiter_webhook(db, body, sig)["action"] == "flash_genere"
    return sid


def test_flash_recuperable_apres_onglet_ferme(db, parcelle):
    """Payer puis FERMER avant de récupérer le lien : le rapport est généré quand même (webhook),
    et le lien se RÉCUPÈRE en ré-appelant flash_statut (session_id) — DB-backed, pas de mémoire."""
    sid = _flash_paye(db, parcelle)
    # 1er appel (comme si l'onglet se rouvrait plus tard) → lien frais
    st = flash_statut(db, sid)
    assert st["statut"] == "generee" and st.get("lien"), st
    tok1 = st["lien"].split("token=")[1]
    # 2e appel → NOUVEAU lien valide (récupérable autant de fois qu'on veut)
    tok2 = flash_statut(db, sid)["lien"].split("token=")[1]
    assert tok2 != tok1
    assert flash_pdf_par_token(db, tok2) is not None      # le dernier lien marche
    db.execute(text("DELETE FROM flash_commandes WHERE stripe_session_id=:s"), {"s": sid}); db.commit()


def test_flash_token_ne_donne_que_son_pdf(db, parcelle):
    """Le token de téléchargement mappe UNE commande → UN pdf (l'IDU payé). On ne peut pas
    récupérer un autre rapport en changeant l'URL (le token EST le droit, pas l'IDU)."""
    sid = _flash_paye(db, parcelle)
    lien = flash_statut(db, sid)["lien"]
    tok = lien.split("token=")[1]
    assert flash_pdf_par_token(db, tok) is not None   # le pdf de CETTE commande
    # un token bidon → rien
    assert flash_pdf_par_token(db, "z" * 43) is None
    db.execute(text("DELETE FROM flash_commandes WHERE stripe_session_id=:s"), {"s": sid}); db.commit()


def test_flash_lien_expire_apres_30j(db, parcelle):
    """Lien rejoué après expiration (30 j) → refusé (téléchargement 404), statut 'expire'."""
    sid = _flash_paye(db, parcelle)
    tok = flash_statut(db, sid)["lien"].split("token=")[1]
    assert flash_pdf_par_token(db, tok) is not None
    # on fait EXPIRER la commande
    db.execute(text("UPDATE flash_commandes SET expire_at = now() - interval '1 day'"
                    " WHERE stripe_session_id=:s"), {"s": sid}); db.commit()
    assert flash_pdf_par_token(db, tok) is None            # téléchargement refusé
    assert flash_statut(db, sid).get("expire") is True     # le statut le dit
    db.execute(text("DELETE FROM flash_commandes WHERE stripe_session_id=:s"), {"s": sid}); db.commit()


# ─────────────── Partie C — concurrence & reprise ───────────────

def test_concurrence_double_checkout_une_seule_souscription(db):
    """Double-clic / deux onglets → deux Checkout → deux checkout.completed. Le compte garde
    UNE souscription (la première) ; le doublon ne l'écrase pas (DB), et serait annulé chez
    Stripe (path testé séparément avec un stripe mocké)."""
    email = f"conc-{uuid.uuid4().hex[:8]}@x.test"
    inv = comptes.creer_invitation(db, email)
    cid, cus = inv["compte_id"], f"cus_{uuid.uuid4().hex[:8]}"
    b1, s1 = _signe(_evt("checkout.session.completed",
                         {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_PREMIERE"}))
    assert traiter_webhook(db, b1, s1)["action"] == "activation"
    # 2e checkout (autre souscription) — sans clé Stripe l'annulation échoue proprement, mais
    # la souscription enregistrée reste la PREMIÈRE (COALESCE ne l'écrase pas)
    b2, s2 = _signe(_evt("checkout.session.completed",
                         {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_DOUBLON"}))
    traiter_webhook(db, b2, s2)
    sub = db.execute(text("SELECT stripe_subscription_id FROM comptes WHERE id=:c"), {"c": cid}).scalar()
    assert sub == "sub_PREMIERE", f"le doublon a écrasé la souscription : {sub}"
    db.execute(text("DELETE FROM utilisateurs WHERE email=:e"), {"e": email}); db.commit()


def test_concurrence_doublon_annule_chez_stripe(db, monkeypatch):
    """Avec Stripe joignable, le doublon entrant est ANNULÉ (une seule souscription active)."""
    annulees = []
    class _FakeSub:
        @staticmethod
        def cancel(sid): annulees.append(sid)
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "sk_test_fake")
    import labuse.facturation as F
    monkeypatch.setattr(F, "_stripe", lambda: type("S", (), {"Subscription": _FakeSub}))
    email = f"conc2-{uuid.uuid4().hex[:8]}@x.test"
    inv = comptes.creer_invitation(db, email)
    cid, cus = inv["compte_id"], f"cus_{uuid.uuid4().hex[:8]}"
    b1, s1 = _signe(_evt("checkout.session.completed",
                         {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_A"}))
    traiter_webhook(db, b1, s1)
    b2, s2 = _signe(_evt("checkout.session.completed",
                         {"client_reference_id": str(cid), "customer": cus, "subscription": "sub_B"}))
    assert traiter_webhook(db, b2, s2)["action"] == "doublon_annule"
    assert annulees == ["sub_B"]          # le doublon entrant annulé, sub_A gardée
    db.execute(text("DELETE FROM utilisateurs WHERE email=:e"), {"e": email}); db.commit()


def test_reprise_flash_apres_interruption(db, parcelle):
    """Serveur redémarré en pleine génération : la commande reste 'payee'. Le prochain
    flash_statut la RATTRAPE (reprise idempotente) et livre le lien."""
    ensure_flash_table(db)
    sid = f"cs_test_{uuid.uuid4().hex[:12]}"
    db.execute(text("INSERT INTO flash_commandes (stripe_session_id, idu, statut)"
                    " VALUES (:s, :i, 'payee')"), {"s": sid, "i": parcelle})   # bloquée à 'payee'
    db.commit()
    st = flash_statut(db, sid)            # rattrape et génère
    assert st["statut"] == "generee" and st.get("lien")
    db.execute(text("DELETE FROM flash_commandes WHERE stripe_session_id=:s"), {"s": sid}); db.commit()
