"""PREMIER EURO · E1 — l'IDENTITÉ : comptes, utilisateurs, sessions, invitations, reset.

Doctrine :
- hachage **argon2id** (argon2-cffi, paramètres par défaut de la lib — recommandation OWASP) ;
- les tokens (invitation, reset, session) ne sont JAMAIS stockés en clair : SHA-256 en base,
  le porteur du lien détient le seul exemplaire ;
- création de compte par INVITATION uniquement (lien signé envoyé après la vente) ;
- effacement RGPD réel (`compte-supprime` : lignes utilisateur purgées, audit anonymisé) ;
- rate-limit login : N échecs → verrou temporaire ; jamais un message qui révèle si l'email
  existe (« Identifiants invalides », toujours).
Tables ADDITIVES (CREATE IF NOT EXISTS — pattern maison), aucune table existante touchée.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings

log = logging.getLogger("labuse.comptes")
_ph = PasswordHasher()  # argon2id par défaut (time_cost=3, memory=64 MiB, parallelism=4)

# Refonte commerciale (Vic 22/07) : UN modèle d'abonnement — INTÉGRAL, 349 €/mois par
# licence, 1 licence = 1 accès (plus d'Indé/Pro, plus de sièges multiples, plus de founding).
# Le one-shot FLASH (79 €/rapport) vit dans facturation.py — pas un compte.
PLANS = {"integral": {"label": "Intégral", "sieges": 1, "eur_mois": 349}}


def ensure_tables(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS comptes (
            id serial PRIMARY KEY,
            nom text NOT NULL,
            plan text NOT NULL,
            founding boolean NOT NULL DEFAULT false,  -- hérité, plus jamais posé (refonte 22/07)
            statut text NOT NULL DEFAULT 'invite'
                CHECK (statut IN ('invite', 'actif', 'paiement_requis', 'suspendu', 'resilie')),
            sieges int NOT NULL DEFAULT 1,
            stripe_customer_id text,
            stripe_subscription_id text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )"""))
    # refonte 22/07 : le CHECK historique (inde/pro) tombe — plan libre ('integral')
    db.execute(text("ALTER TABLE comptes DROP CONSTRAINT IF EXISTS comptes_plan_check"))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id serial PRIMARY KEY,
            compte_id int NOT NULL REFERENCES comptes(id) ON DELETE CASCADE,
            email text NOT NULL UNIQUE,
            hash text,
            role text NOT NULL DEFAULT 'titulaire' CHECK (role IN ('admin', 'titulaire', 'membre', 'qa')),
            statut text NOT NULL DEFAULT 'invite'
                CHECK (statut IN ('invite', 'actif', 'verrouille', 'suspendu', 'supprime')),
            invite_token_hash text, invite_expire_at timestamptz,
            reset_token_hash text, reset_expire_at timestamptz,
            cgv_acceptees_at timestamptz, cgv_version text,
            echecs_login int NOT NULL DEFAULT 0,
            verrouille_jusqu_a timestamptz,
            dernier_login_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )"""))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sessions_auth (
            token_hash text PRIMARY KEY,
            utilisateur_id int NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now(),
            expire_at timestamptz NOT NULL
        )"""))
    # audit MINIMAL (jamais de secret, jamais de données de carte — il n'y en a nulle part)
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS evenements_compte (
            id serial PRIMARY KEY,
            type text NOT NULL,
            compte_id int, utilisateur_id int,
            detail text,
            at timestamptz NOT NULL DEFAULT now()
        )"""))
    db.commit()


def _norm_email(email: str) -> str:
    return email.strip().lower()


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _token() -> str:
    return secrets.token_urlsafe(32)


def audit(db: Session, type_: str, compte_id: int | None = None,
          utilisateur_id: int | None = None, detail: str | None = None) -> None:
    db.execute(text("INSERT INTO evenements_compte (type, compte_id, utilisateur_id, detail)"
                    " VALUES (:t, :c, :u, :d)"),
               {"t": type_, "c": compte_id, "u": utilisateur_id, "d": detail})


# ───────────────────────── cycle de vie ─────────────────────────

def creer_invitation(db: Session, email: str, nom: str | None = None,
                     jours: int = 7) -> dict:
    """Crée compte INTÉGRAL + utilisateur en statut `invite` et renvoie le TOKEN CLAIR
    (seul exemplaire — en base : le hash). Le lien s'envoie À LA MAIN (décision Vic :
    aucun email automatique)."""
    ensure_tables(db)
    email = _norm_email(email)
    plan, role = "integral", "titulaire"
    exist = db.execute(text("SELECT id, statut FROM utilisateurs WHERE email = :e"),
                       {"e": email}).mappings().first()
    if exist and exist["statut"] != "invite":
        raise ValueError(f"{email} existe déjà (statut {exist['statut']})")
    if exist:
        compte_id = db.execute(text("SELECT compte_id FROM utilisateurs WHERE id = :i"),
                               {"i": exist["id"]}).scalar()
    else:
        compte_id = db.execute(text(
            "INSERT INTO comptes (nom, plan, sieges) VALUES (:n, :p, 1) RETURNING id"),
            {"n": nom or email, "p": plan}).scalar()
    tok = _token()
    exp = datetime.now(timezone.utc) + timedelta(days=jours)
    if exist:
        db.execute(text("UPDATE utilisateurs SET invite_token_hash = :h, invite_expire_at = :x,"
                        " updated_at = now() WHERE id = :i"),
                   {"h": _sha(tok), "x": exp, "i": exist["id"]})
        uid = exist["id"]
    else:
        uid = db.execute(text(
            "INSERT INTO utilisateurs (compte_id, email, role, statut, invite_token_hash, invite_expire_at)"
            " VALUES (:c, :e, :r, 'invite', :h, :x) RETURNING id"),
            {"c": compte_id, "e": email, "r": role, "h": _sha(tok), "x": exp}).scalar()
    audit(db, "invitation_creee", compte_id, uid, f"plan={plan} role={role}")
    db.commit()
    lien = f"{get_settings().public_base_url}/invitation?token={tok}"
    return {"utilisateur_id": int(uid), "compte_id": int(compte_id), "email": email, "lien": lien,
            "expire_at": exp.isoformat()}


def valider_invitation(db: Session, token: str) -> dict | None:
    """Token d'invitation → utilisateur (ou None : inconnu/expiré/déjà consommé)."""
    r = db.execute(text(
        "SELECT u.id, u.email, u.compte_id, c.plan FROM utilisateurs u"
        " JOIN comptes c ON c.id = u.compte_id"
        " WHERE u.invite_token_hash = :h AND u.statut = 'invite' AND u.invite_expire_at > now()"),
        {"h": _sha(token)}).mappings().first()
    return dict(r) if r else None


def activer_par_invitation(db: Session, token: str, password: str,
                           cgv_version: str) -> dict | None:
    """Pose le mot de passe (argon2id), horodate l'acceptation CGV, consomme le token.
    Le compte ne devient `actif` qu'au paiement (webhook Stripe) — ici : utilisateur actif,
    compte reste `invite` jusqu'à checkout.session.completed."""
    inv = valider_invitation(db, token)
    if not inv:
        return None
    if len(password) < 10:
        raise ValueError("mot de passe trop court (10 caractères minimum)")
    db.execute(text(
        "UPDATE utilisateurs SET hash = :h, statut = 'actif', invite_token_hash = NULL,"
        " invite_expire_at = NULL, cgv_acceptees_at = now(), cgv_version = :v, updated_at = now()"
        " WHERE id = :i"),
        {"h": _ph.hash(password), "v": cgv_version, "i": inv["id"]})
    audit(db, "invitation_consommee", inv["compte_id"], inv["id"], f"cgv={cgv_version}")
    db.commit()
    return inv


def verifier_login(db: Session, email: str, password: str) -> dict | None:
    """Login utilisateur — verrou après N échecs, message JAMAIS différencié.
    Renvoie {utilisateur_id, compte_id, statut_compte} ou None."""
    s = get_settings()
    email = _norm_email(email)
    u = db.execute(text(
        "SELECT u.id, u.hash, u.statut, u.echecs_login, u.verrouille_jusqu_a, u.compte_id,"
        "       c.statut AS statut_compte"
        " FROM utilisateurs u JOIN comptes c ON c.id = u.compte_id WHERE u.email = :e"),
        {"e": email}).mappings().first()
    if not u or not u["hash"] or u["statut"] in ("supprime", "suspendu", "invite"):
        return None
    if u["verrouille_jusqu_a"] and u["verrouille_jusqu_a"] > datetime.now(timezone.utc):
        audit(db, "login_verrouille", u["compte_id"], u["id"]); db.commit()
        return None
    try:
        _ph.verify(u["hash"], password)
    except VerifyMismatchError:
        n = int(u["echecs_login"]) + 1
        verrou = (datetime.now(timezone.utc) + timedelta(minutes=s.login_verrou_minutes)
                  if n >= s.login_echecs_max else None)
        db.execute(text("UPDATE utilisateurs SET echecs_login = :n, verrouille_jusqu_a = :v,"
                        " updated_at = now() WHERE id = :i"), {"n": n, "v": verrou, "i": u["id"]})
        audit(db, "login_echec", u["compte_id"], u["id"], f"echecs={n}" + (" verrou" if verrou else ""))
        db.commit()
        return None
    if _ph.check_needs_rehash(u["hash"]):
        db.execute(text("UPDATE utilisateurs SET hash = :h WHERE id = :i"),
                   {"h": _ph.hash(password), "i": u["id"]})
    db.execute(text("UPDATE utilisateurs SET echecs_login = 0, verrouille_jusqu_a = NULL,"
                    " dernier_login_at = now(), updated_at = now() WHERE id = :i"), {"i": u["id"]})
    audit(db, "login_ok", u["compte_id"], u["id"]); db.commit()
    return {"utilisateur_id": int(u["id"]), "compte_id": int(u["compte_id"]),
            "statut_compte": u["statut_compte"]}


# ── sessions (cookie httpOnly ; en base : le hash du token) ──

def creer_session(db: Session, utilisateur_id: int, heures: float | None = None) -> str:
    tok = _token()
    exp = datetime.now(timezone.utc) + timedelta(hours=heures or get_settings().session_hours)
    db.execute(text("INSERT INTO sessions_auth (token_hash, utilisateur_id, expire_at)"
                    " VALUES (:h, :u, :x)"), {"h": _sha(tok), "u": utilisateur_id, "x": exp})
    db.commit()
    return tok


def session_utilisateur(db: Session, token: str) -> dict | None:
    """Session valide → {utilisateur_id, compte_id, role, statut_compte} (sinon None)."""
    r = db.execute(text(
        "SELECT s.utilisateur_id, u.compte_id, u.role, u.statut, c.statut AS statut_compte"
        " FROM sessions_auth s JOIN utilisateurs u ON u.id = s.utilisateur_id"
        " JOIN comptes c ON c.id = u.compte_id"
        " WHERE s.token_hash = :h AND s.expire_at > now()"), {"h": _sha(token)}).mappings().first()
    if not r or r["statut"] in ("supprime", "suspendu"):
        return None
    return dict(r)


def detruire_session(db: Session, token: str) -> None:
    db.execute(text("DELETE FROM sessions_auth WHERE token_hash = :h"), {"h": _sha(token)})
    db.commit()


# ── reset mot de passe ──

def demander_reset(db: Session, email: str, minutes: int = 60) -> dict | None:
    """Token de reset (lien signé, expirant). None si l'email n'existe pas — l'APPELANT ne
    doit JAMAIS différencier sa réponse (anti-énumération)."""
    email = _norm_email(email)
    u = db.execute(text("SELECT id, compte_id FROM utilisateurs WHERE email = :e"
                        " AND statut = 'actif'"), {"e": email}).mappings().first()
    if not u:
        return None
    tok = _token()
    db.execute(text("UPDATE utilisateurs SET reset_token_hash = :h, reset_expire_at = :x,"
                    " updated_at = now() WHERE id = :i"),
               {"h": _sha(tok), "x": datetime.now(timezone.utc) + timedelta(minutes=minutes),
                "i": u["id"]})
    audit(db, "reset_demande", u["compte_id"], u["id"]); db.commit()
    return {"email": email, "lien": f"{get_settings().public_base_url}/reset?token={tok}"}


def appliquer_reset(db: Session, token: str, password: str) -> bool:
    u = db.execute(text("SELECT id, compte_id FROM utilisateurs WHERE reset_token_hash = :h"
                        " AND reset_expire_at > now() AND statut = 'actif'"),
                   {"h": _sha(token)}).mappings().first()
    if not u:
        return False
    if len(password) < 10:
        raise ValueError("mot de passe trop court (10 caractères minimum)")
    db.execute(text("UPDATE utilisateurs SET hash = :h, reset_token_hash = NULL,"
                    " reset_expire_at = NULL, echecs_login = 0, verrouille_jusqu_a = NULL,"
                    " updated_at = now() WHERE id = :i"),
               {"h": _ph.hash(password), "i": u["id"]})
    # toutes les sessions tombent (le reset invalide un éventuel voleur de session)
    db.execute(text("DELETE FROM sessions_auth WHERE utilisateur_id = :i"), {"i": u["id"]})
    audit(db, "reset_applique", u["compte_id"], u["id"]); db.commit()
    return True


# ── administration (CLI Vic) ──

def creer_admin(db: Session, email: str, password: str) -> int:
    """Le compte ADMIN de Vic — hors plans, jamais suspendu par Stripe."""
    ensure_tables(db)
    email = _norm_email(email)
    cid = db.execute(text("INSERT INTO comptes (nom, plan, statut, sieges)"
                          " VALUES ('LABUSE (admin)', 'pro', 'actif', 99) RETURNING id")).scalar()
    uid = db.execute(text(
        "INSERT INTO utilisateurs (compte_id, email, hash, role, statut, cgv_acceptees_at, cgv_version)"
        " VALUES (:c, :e, :h, 'admin', 'actif', now(), :v) RETURNING id"),
        {"c": cid, "e": email, "h": _ph.hash(password), "v": get_settings().cgv_version}).scalar()
    audit(db, "admin_cree", cid, uid); db.commit()
    return int(uid)


def suspendre_compte(db: Session, compte_id: int, motif: str = "manuel") -> None:
    db.execute(text("UPDATE comptes SET statut = 'suspendu', updated_at = now() WHERE id = :c"),
               {"c": compte_id})
    db.execute(text("DELETE FROM sessions_auth WHERE utilisateur_id IN"
                    " (SELECT id FROM utilisateurs WHERE compte_id = :c)"), {"c": compte_id})
    audit(db, "compte_suspendu", compte_id, None, motif); db.commit()


def reactiver_compte(db: Session, compte_id: int, motif: str = "manuel") -> None:
    db.execute(text("UPDATE comptes SET statut = 'actif', updated_at = now() WHERE id = :c"),
               {"c": compte_id})
    audit(db, "compte_reactive", compte_id, None, motif); db.commit()


def supprimer_utilisateur(db: Session, email: str) -> bool:
    """EFFACEMENT RGPD : lignes utilisateur purgées (sessions cascade), audit ANONYMISÉ
    (l'événement reste, l'identité part). Le compte reste s'il a d'autres sièges."""
    email = _norm_email(email)
    u = db.execute(text("SELECT id, compte_id FROM utilisateurs WHERE email = :e"),
                   {"e": email}).mappings().first()
    if not u:
        return False
    db.execute(text("UPDATE evenements_compte SET utilisateur_id = NULL,"
                    " detail = '[efface RGPD]' WHERE utilisateur_id = :i"), {"i": u["id"]})
    db.execute(text("DELETE FROM utilisateurs WHERE id = :i"), {"i": u["id"]})
    reste = db.execute(text("SELECT count(*) FROM utilisateurs WHERE compte_id = :c"),
                       {"c": u["compte_id"]}).scalar()
    if not reste:
        db.execute(text("UPDATE comptes SET statut = 'resilie', updated_at = now()"
                        " WHERE id = :c"), {"c": u["compte_id"]})
    audit(db, "utilisateur_efface_rgpd", u["compte_id"], None)
    db.commit()
    return True
