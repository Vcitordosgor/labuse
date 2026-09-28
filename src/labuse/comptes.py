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
from datetime import date, datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings

log = logging.getLogger("labuse.comptes")
_ph = PasswordHasher()  # argon2id par défaut (time_cost=3, memory=64 MiB, parallelism=4)

# Refonte commerciale (Vic 22/07 ; parcours d'entrée E1, 27/08) : UN SEUL plan commercial —
# INTÉGRAL, source de vérité `offres.py` (prix en config). 1 licence = 1 accès (plus d'Indé/Pro,
# plus de sièges multiples, plus de founding, PLUS d'« Illimité 499 € » : offre fantôme retirée).
# Le one-shot FLASH (offres.offre_flash()) vit dans facturation.py — pas un compte.
# `interne` = comptes HORS facturation (admin nominatif, système) : aucun prix, aucune offre
# affichée, quota d'exports non borné (quota.py). Jamais présenté comme une offre au client.
PLAN_INTERNE = "interne"


def _plan_integral() -> dict:
    from .offres import offre_integral
    o = offre_integral()
    return {"label": o["label"], "sieges": 1, "eur_mois": o["eur_mois"]}


class _Plans(dict):
    """PLANS lu à la volée depuis offres.py (le prix suit la config, jamais figé à l'import)."""

    def __getitem__(self, key):
        if key == "integral":
            return _plan_integral()
        if key == PLAN_INTERNE:
            return {"label": "Interne", "sieges": 99, "eur_mois": None}
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


PLANS = _Plans()


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
    # DASHBOARD-V1 · D9 — compte d'ESSAI 48 h : une date d'échéance (NULL = compte normal).
    # À l'échéance : bascule automatique sur le mécanisme de suspension (session_utilisateur).
    db.execute(text("ALTER TABLE comptes ADD COLUMN IF NOT EXISTS essai_expire_at timestamptz"))
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
    # AUDIT COMPTES · A5 — empreinte HACHÉE de la session (jamais l'IP/UA en clair : RGPD) pour
    # OBSERVER le partage de compte (plusieurs postes simultanés). Signal seulement, aucun blocage.
    db.execute(text("ALTER TABLE sessions_auth ADD COLUMN IF NOT EXISTS ip_hash text"))
    db.execute(text("ALTER TABLE sessions_auth ADD COLUMN IF NOT EXISTS ua_hash text"))
    # audit MINIMAL (jamais de secret, jamais de données de carte — il n'y en a nulle part)
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS evenements_compte (
            id serial PRIMARY KEY,
            type text NOT NULL,
            compte_id int, utilisateur_id int,
            detail text,
            at timestamptz NOT NULL DEFAULT now()
        )"""))
    # VPS · AC-025 — 2FA TOTP des ADMINS. `secret` reste en clair (il FAUT le relire pour
    # vérifier chaque code — un hash le rendrait inutilisable) : la protection est celle de la
    # base, comme pour tout secret symétrique. `dernier_pas` = anti-rejeu : un code TOTP
    # accepté consomme son pas de temps, le même code rejoué est refusé.
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS totp_2fa (
            utilisateur_id int PRIMARY KEY REFERENCES utilisateurs(id) ON DELETE CASCADE,
            secret text NOT NULL,
            confirme_at timestamptz,
            dernier_pas bigint,
            created_at timestamptz NOT NULL DEFAULT now()
        )"""))
    # Codes de SECOURS (téléphone perdu) : 8 à l'enrôlement, usage unique, montrés UNE fois
    # — en base : le SHA-256 seulement (contrairement au secret TOTP, on n'a jamais besoin
    # de les relire en clair).
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS totp_secours (
            id serial PRIMARY KEY,
            utilisateur_id int NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            code_hash text NOT NULL,
            utilise_at timestamptz
        )"""))
    # COMPTE-2 (Lot 6) — MÉMOIRE DU COMPTE : préférences de carte (fond + couches actives) REMONTÉES
    # en base pour SURVIVRE au changement de poste (avant : localStorage seulement → perdues). Une ligne
    # par compte, JSON pour les couches (souple). Cascade avec le compte (effacement RGPD).
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS prefs_carte (
            compte_id int PRIMARY KEY REFERENCES comptes(id) ON DELETE CASCADE,
            basemap text,
            couches jsonb,
            updated_at timestamptz NOT NULL DEFAULT now()
        )"""))
    db.commit()


def lire_prefs_carte(db: Session, compte_id: int | None) -> dict | None:
    """COMPTE-2 (Lot 6) — préférences de carte du compte ({basemap, couches}) ou None (jamais posées /
    pilote). Lues à l'ouverture de l'app pour rouvrir la carte comme le client l'avait laissée."""
    if compte_id is None:
        return None
    r = db.execute(text("SELECT basemap, couches FROM prefs_carte WHERE compte_id = :c"),
                   {"c": compte_id}).mappings().first()
    return {"basemap": r["basemap"], "couches": r["couches"]} if r else None


def ecrire_prefs_carte(db: Session, compte_id: int, basemap: str | None, couches: dict | None) -> None:
    """COMPTE-2 (Lot 6) — enregistre (upsert) le fond de carte et les couches actives du compte."""
    import json
    db.execute(text(
        "INSERT INTO prefs_carte (compte_id, basemap, couches) VALUES (:c, :b, CAST(:j AS jsonb))"
        " ON CONFLICT (compte_id) DO UPDATE SET basemap = :b, couches = CAST(:j AS jsonb),"
        " updated_at = now()"),
        {"c": compte_id, "b": basemap, "j": json.dumps(couches) if couches is not None else None})
    db.commit()


def _norm_email(email: str) -> str:
    return email.strip().lower()


# ── COMPTE-2 (Lot 3) — comptes de TEST & compteur UNIQUE de licences actives ──
#: convention de recette (mandat) : nom préfixé « [CT-TEST] » et/ou e-mail « @labuse.test ».
PREFIXE_TEST = "[CT-TEST]"
DOMAINE_TEST = "@labuse.test"
#: DASHBOARD-2 Lot 2 (recette) — filtre ÉLARGI : les comptes de recette/démo utilisent aussi ces
#: domaines (mandat §14 + placeholders), l'alias Gmail « +test@ », et des noms « … Test »/« Recette ».
DOMAINES_TEST = ("labuse.test", "labuse.local", "exemple.test", "ex.test",
                 "example.com", "example.org", "example.net", "test.com")
_DOMS_IN = "(" + ", ".join(f"'{d}'" for d in DOMAINES_TEST) + ")"
#: un compte a-t-il un e-mail RÉEL (ni domaine de test, ni alias +test) ? Les motifs de NOM (« test »,
#: « recette ») ne masquent QUE les comptes SANS e-mail réel — un vrai client au nom malheureux
#: (ex. nom « ton-email@test.com » avec un Gmail réel) reste compté.
_A_UN_EMAIL_REEL = (
    "EXISTS (SELECT 1 FROM utilisateurs u WHERE u.compte_id = c.id AND u.email IS NOT NULL"
    f" AND split_part(lower(u.email), '@', 2) NOT IN {_DOMS_IN}"
    " AND lower(u.email) NOT LIKE '%+test@%')")

#: prédicat SQL « compte de test/interne à MASQUER des chiffres client » — source UNIQUE, réutilisée
#: par le compteur, la liste et le Pilotage (alias de table `c` pour comptes).
_MASQUE_SQL = (
    "(c.plan = 'interne'"
    f" OR c.nom ILIKE '{PREFIXE_TEST}%'"
    " OR EXISTS (SELECT 1 FROM utilisateurs u WHERE u.compte_id = c.id"
    f"            AND (split_part(lower(u.email), '@', 2) IN {_DOMS_IN}"
    "                 OR lower(u.email) LIKE '%+test@%'))"
    f" OR ((c.nom ILIKE '%test%' OR c.nom ILIKE '%recette%') AND NOT {_A_UN_EMAIL_REEL}))")


def compte_est_test(nom: str | None, email: str | None) -> bool:
    """Un compte de recette / interne (masqué des chiffres client). DASHBOARD-2 Lot 2 : domaines de
    test élargis (mandat §14) + alias Gmail « +test » + noms « …Test »/« Recette » — ces derniers
    UNIQUEMENT quand le compte n'a pas d'e-mail réel (un vrai client au nom malheureux reste compté)."""
    n = (nom or "").strip()
    e = (email or "").strip().lower()
    if n.startswith(PREFIXE_TEST):
        return True
    dom = e.rsplit("@", 1)[-1] if "@" in e else ""
    if dom in DOMAINES_TEST or "+test@" in e:
        return True
    email_reel = bool(e) and dom not in DOMAINES_TEST and "+test@" not in e
    return (not email_reel) and ("test" in n.lower() or "recette" in n.lower())


def licences_actives(conn) -> int:
    """COMPTE-2 (Lot 3) — LE compteur unique de « licences actives » (payantes), lu par le rail, le
    Pilotage et la page Comptes (fin du 12 vs 9). Une licence active = compte au statut 'actif', qui
    n'est PAS un essai en cours (essai_expire_at NULL), ni un compte interne/de test. Un seul endroit.
    Accepte une Session OU une Connection (les tables existent déjà à ces points d'appel)."""
    return int(conn.execute(text(
        "SELECT COUNT(*) FROM comptes c WHERE c.statut = 'actif'"
        " AND c.essai_expire_at IS NULL AND NOT " + _MASQUE_SQL)).scalar() or 0)


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
    """Token d'invitation → utilisateur (ou None : inconnu/expiré/déjà consommé).

    ONBOARDING-1 (O2) — le token est TRIMMÉ : un lien collé depuis un e-mail arrive souvent avec un
    espace ou un retour-ligne collé en fin d'URL (le client mail coupe/enveloppe la ligne). Sans ce
    strip, `%20`/`%0A` en queue → hash différent → « Invitation introuvable » AU PREMIER CLIC (le
    « tunnel bugué » signalé). On ne touche jamais au token lui-même (token_urlsafe = sans espace)."""
    token = (token or "").strip()
    if not token:
        return None
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
    Renvoie {utilisateur_id, compte_id, statut_compte, role} ou None."""
    s = get_settings()
    email = _norm_email(email)
    u = db.execute(text(
        "SELECT u.id, u.hash, u.statut, u.echecs_login, u.verrouille_jusqu_a, u.compte_id,"
        "       u.role, c.statut AS statut_compte, c.essai_expire_at"
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
    # D9 — essai échu constaté AU LOGIN : bascule immédiate → l'appelant (/login) montre
    # l'écran « abonnement à régulariser » (même mécanisme que la suspension manuelle).
    statut_compte = u["statut_compte"]
    if _essai_echu(u):
        basculer_essai_expire(db, u["compte_id"])
        statut_compte = "suspendu"
    return {"utilisateur_id": int(u["id"]), "compte_id": int(u["compte_id"]),
            "statut_compte": statut_compte, "role": u["role"]}


# ── sessions (cookie httpOnly ; en base : le hash du token) ──

def creer_session(db: Session, utilisateur_id: int, heures: float | None = None,
                  ip_hash: str | None = None, ua_hash: str | None = None) -> str:
    """A5 : `ip_hash`/`ua_hash` (empreinte HACHÉE, jamais en clair) sont OPTIONNELS — posés par
    /login pour observer le partage de compte. Absents (repli/test) : session normale."""
    tok = _token()
    exp = datetime.now(timezone.utc) + timedelta(hours=heures or get_settings().session_hours)
    db.execute(text("INSERT INTO sessions_auth (token_hash, utilisateur_id, expire_at, ip_hash, ua_hash)"
                    " VALUES (:h, :u, :x, :ip, :ua)"),
               {"h": _sha(tok), "u": utilisateur_id, "x": exp, "ip": ip_hash, "ua": ua_hash})
    db.commit()
    return tok


def sessions_actives_par_compte(db: Session, seuil: int | None = None) -> list[dict]:
    """A5 — partage de compte OBSERVÉ (jamais bloqué) : par compte, le nombre de sessions
    actives (non expirées) et surtout le nombre d'EMPREINTES IP DISTINCTES simultanées. Plusieurs
    IP actives sur la fenêtre de session (12 h) = plusieurs postes = partage probable et DURABLE
    (par construction : une session dure 12 h, ce n'est pas un pic). Le seuil (config
    `sessions_signal_seuil`) borne le signal servi au dashboard. RGPD : on ne lit que des hash."""
    s = seuil if seuil is not None else int(get_settings().sessions_signal_seuil)
    rows = db.execute(text(
        "SELECT u.compte_id,"
        "       COUNT(*) AS sessions,"
        "       COUNT(DISTINCT s.ip_hash) FILTER (WHERE s.ip_hash IS NOT NULL) AS ips,"
        "       COUNT(DISTINCT s.ua_hash) FILTER (WHERE s.ua_hash IS NOT NULL) AS uas,"
        "       MIN(s.created_at) AS depuis"
        " FROM sessions_auth s JOIN utilisateurs u ON u.id = s.utilisateur_id"
        " WHERE s.expire_at > now() AND u.compte_id IS NOT NULL"
        " GROUP BY u.compte_id"), {}).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        # signal = IP distinctes ≥ seuil (repli sur le nb de sessions si l'empreinte manque encore)
        d["partage_probable"] = (int(d["ips"] or 0) >= s) or (int(d["ips"] or 0) == 0 and int(d["sessions"]) >= s)
        d["depuis"] = d["depuis"].isoformat() if d["depuis"] else None
        out.append(d)
    return out


def basculer_essai_expire(db: Session, compte_id: int) -> None:
    """DASHBOARD-V1 · D9 — l'essai 48 h a expiré : bascule AUTOMATIQUE sur le mécanisme de
    suspension EXISTANT (mandat : seul le déclencheur change — une date au lieu du bouton).
    Données conservées, réversible ; le client voit « abonnement à régulariser » au login."""
    suspendre_compte(db, compte_id, motif="essai_expire")


def _essai_echu(r) -> bool:
    """Compte ACTIF porteur d'une échéance d'essai passée (colonne essai_expire_at, D9)."""
    return (r["statut_compte"] == "actif" and r.get("essai_expire_at") is not None
            and r["essai_expire_at"] <= datetime.now(timezone.utc))


def session_utilisateur(db: Session, token: str) -> dict | None:
    """Session valide → {utilisateur_id, compte_id, role, statut_compte} (sinon None)."""
    r = db.execute(text(
        "SELECT s.utilisateur_id, u.compte_id, u.role, u.statut, c.statut AS statut_compte,"
        "       c.essai_expire_at"
        " FROM sessions_auth s JOIN utilisateurs u ON u.id = s.utilisateur_id"
        " JOIN comptes c ON c.id = u.compte_id"
        " WHERE s.token_hash = :h AND s.expire_at > now()"), {"h": _sha(token)}).mappings().first()
    if not r or r["statut"] in ("supprime", "suspendu"):
        return None
    # D9 — essai échu : la bascule se fait ICI, à la requête (aucun cron à attendre) ; la
    # session meurt comme pour toute suspension — la sécurité durcie ne change pas.
    if _essai_echu(r):
        basculer_essai_expire(db, r["compte_id"])
        return None
    # défense en profondeur (durcie aux tests Vic) : le statut du COMPTE se vérifie à
    # chaque requête — suspendu/résilié = coupé ; `invite` (jamais payé) = pas d'accès
    # non plus : l'app ne s'ouvre qu'à un abonnement réellement activé par Stripe.
    if r["statut_compte"] in ("suspendu", "resilie", "invite"):
        return None
    return {k: v for k, v in dict(r).items() if k != "essai_expire_at"}


def detruire_session(db: Session, token: str) -> None:
    db.execute(text("DELETE FROM sessions_auth WHERE token_hash = :h"), {"h": _sha(token)})
    db.commit()


# ── VPS · AC-025 — 2FA TOTP des admins (primitive pure : labuse.totp ; ici : l'état en base) ──

def totp_etat(db: Session, utilisateur_id: int) -> dict | None:
    """Enrôlement TOTP de l'utilisateur → {secret, confirme, dernier_pas} ou None (jamais enrôlé)."""
    r = db.execute(text("SELECT secret, confirme_at, dernier_pas FROM totp_2fa"
                        " WHERE utilisateur_id = :u"), {"u": utilisateur_id}).mappings().first()
    if not r:
        return None
    return {"secret": r["secret"], "confirme": r["confirme_at"] is not None,
            "dernier_pas": r["dernier_pas"]}


def totp_preparer(db: Session, utilisateur_id: int) -> str:
    """Secret d'ENRÔLEMENT : en crée un si absent, sinon rend l'existant NON confirmé
    (recharger la page d'enrôlement ne doit pas changer le QR — sinon l'app du téléphone
    et la base divergent). Un secret déjà confirmé n'est JAMAIS régénéré ici."""
    from . import totp as _totp
    etat = totp_etat(db, utilisateur_id)
    if etat:
        return etat["secret"]
    secret = _totp.generer_secret()
    db.execute(text("INSERT INTO totp_2fa (utilisateur_id, secret) VALUES (:u, :s)"),
               {"u": utilisateur_id, "s": secret})
    db.commit()
    return secret


def totp_verifier(db: Session, utilisateur_id: int, code: str) -> bool:
    """Vérifie un code TOTP AVEC anti-rejeu : fenêtre ±1 pas (tolérance d'horloge), et un
    pas ≤ dernier_pas consommé est REFUSÉ même si le code est mathématiquement bon — un
    code intercepté (épaule, phishing) ne resservira jamais."""
    from . import totp as _totp
    etat = totp_etat(db, utilisateur_id)
    if not etat:
        return False
    pas = _totp.verifier_code(etat["secret"], code, fenetre=1)
    if pas is None or (etat["dernier_pas"] is not None and pas <= etat["dernier_pas"]):
        return False
    db.execute(text("UPDATE totp_2fa SET dernier_pas = :p WHERE utilisateur_id = :u"),
               {"p": pas, "u": utilisateur_id})
    db.commit()
    return True


def totp_confirmer(db: Session, utilisateur_id: int) -> list[str]:
    """Premier code accepté (vérifié par l'appelant via totp_verifier) → l'enrôlement est
    CONFIRMÉ et les 8 codes de secours naissent. Renvoie les codes EN CLAIR — seul moment
    où ils existent hors de la tête de l'admin (en base : le hash)."""
    codes = [f"{secrets.randbelow(10**10):010d}" for _ in range(8)]
    db.execute(text("UPDATE totp_2fa SET confirme_at = now() WHERE utilisateur_id = :u"),
               {"u": utilisateur_id})
    # ré-enrôlement (secret régénéré à la main en base) → les anciens codes tombent
    db.execute(text("DELETE FROM totp_secours WHERE utilisateur_id = :u"), {"u": utilisateur_id})
    for c in codes:
        db.execute(text("INSERT INTO totp_secours (utilisateur_id, code_hash) VALUES (:u, :h)"),
                   {"u": utilisateur_id, "h": _sha(c)})
    db.commit()
    return codes


def totp_secours_consommer(db: Session, utilisateur_id: int, code: str) -> bool:
    """Code de secours : valable UNE fois (utilise_at posé atomiquement par le même UPDATE
    qui le trouve — pas de fenêtre de double emploi)."""
    code = (code or "").strip().replace(" ", "").replace("-", "")
    if not code:
        return False
    n = db.execute(text("UPDATE totp_secours SET utilise_at = now()"
                        " WHERE utilisateur_id = :u AND code_hash = :h AND utilise_at IS NULL"),
                   {"u": utilisateur_id, "h": _sha(code)}).rowcount
    db.commit()
    return bool(n)


# ── reset mot de passe ──

def demander_reset(db: Session, email: str, minutes: int = 60) -> dict | None:
    """Token de reset (lien signé, expirant). None si l'email n'existe pas — l'APPELANT ne
    doit JAMAIS différencier sa réponse (anti-énumération)."""
    email = _norm_email(email)
    u = db.execute(text(
        "SELECT u.id, u.compte_id, c.nom FROM utilisateurs u JOIN comptes c ON c.id = u.compte_id"
        " WHERE u.email = :e AND u.statut = 'actif'"), {"e": email}).mappings().first()
    if not u:
        return None
    tok = _token()
    db.execute(text("UPDATE utilisateurs SET reset_token_hash = :h, reset_expire_at = :x,"
                    " updated_at = now() WHERE id = :i"),
               {"h": _sha(tok), "x": datetime.now(timezone.utc) + timedelta(minutes=minutes),
                "i": u["id"]})
    audit(db, "reset_demande", u["compte_id"], u["id"]); db.commit()
    # COMPTE-2 (Lot 4) — compte_id + nom joints pour envoyer le template 14 par la file (PRENOM/LIEN/VALIDITE).
    return {"email": email, "lien": f"{get_settings().public_base_url}/reset?token={tok}",
            "compte_id": int(u["compte_id"]), "nom": u["nom"]}


def compte_du_reset_token(db: Session, token: str) -> dict | None:
    """COMPTE-2 (Lot 4) — lecture NON consommante des infos du porteur d'un token de reset VALIDE
    (email, compte_id, nom) pour envoyer le template 15 « mot de passe modifié » APRÈS application.
    Ne modifie rien (le token est consommé par `appliquer_reset`)."""
    token = (token or "").strip()
    if not token:
        return None
    r = db.execute(text(
        "SELECT u.compte_id, u.email, c.nom FROM utilisateurs u JOIN comptes c ON c.id = u.compte_id"
        " WHERE u.reset_token_hash = :h AND u.reset_expire_at > now() AND u.statut = 'actif'"),
        {"h": _sha(token)}).mappings().first()
    return dict(r) if r else None


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


# ── Loi Chatel / avis d'échéance : RETIRÉ le 27/08/2026 ──────────────────────────────────────
# Intégral est passé en abonnement mensuel SANS ENGAGEMENT (décision Vic) : la loi Chatel
# (art. L.215-1), qui encadre les contrats à DURÉE DÉTERMINÉE reconductibles, est SANS OBJET.
# Le déclencheur (`declencher_avis_echeance`), le calcul d'échéance annuelle (`avis_echeance_dus`),
# le point d'envoi (`_envoyer_avis_echeance`) et le texte e-mail (`emails.avis_echeance`) ont été
# supprimés. La commande CLI `avis-echeance` est neutralisée (no-op explicite), son cron retiré.


# ── administration (CLI Vic) ──

def creer_admin(db: Session, email: str, password: str) -> int:
    """Le compte ADMIN de Vic — hors plans, jamais suspendu par Stripe."""
    ensure_tables(db)
    email = _norm_email(email)
    # E1 : l'admin vit HORS facturation → plan 'interne' (aucune offre, aucun prix affiché,
    # quota non borné). N'affecte pas les gardes admin (rôle 'admin', jamais suspendu par Stripe).
    cid = db.execute(text("INSERT INTO comptes (nom, plan, statut, sieges)"
                          " VALUES ('LABUSE (admin)', :p, 'actif', 99) RETURNING id"),
                     {"p": PLAN_INTERNE}).scalar()
    uid = db.execute(text(
        "INSERT INTO utilisateurs (compte_id, email, hash, role, statut, cgv_acceptees_at, cgv_version)"
        " VALUES (:c, :e, :h, 'admin', 'actif', now(), :v) RETURNING id"),
        {"c": cid, "e": email, "h": _ph.hash(password), "v": get_settings().cgv_version}).scalar()
    audit(db, "admin_cree", cid, uid); db.commit()
    return int(uid)


def lister_admins(db: Session) -> list[dict]:
    """SUITE-1 · S8 — les comptes admin pour l'exploitation (déploiement). Lecture seule.
    Renvoie [{utilisateur_id, compte_id, email, statut, created_at}] triés par ancienneté."""
    ensure_tables(db)
    rows = db.execute(text(
        "SELECT u.id, u.compte_id, u.email, u.statut, u.created_at"
        " FROM utilisateurs u WHERE u.role = 'admin' ORDER BY u.created_at, u.id")).mappings().all()
    return [{"utilisateur_id": int(r["id"]), "compte_id": int(r["compte_id"]), "email": r["email"],
             "statut": r["statut"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None} for r in rows]


def definir_role_admin(db: Session, email: str, admin: bool) -> dict:
    """SUITE-1 · S8 — promeut (`admin=True`) ou rétrograde (`admin=False`) un utilisateur EXISTANT,
    journalisé (evenements_compte). Rétrograder rend le rôle 'titulaire' (défaut). Idempotent :
    si l'état demandé est déjà en place, `change=False` et rien n'est écrit. Lève ValueError si
    l'email est inconnu. La confirmation interactive est du ressort de l'appelant (CLI)."""
    ensure_tables(db)
    email = _norm_email(email)
    u = db.execute(text("SELECT id, compte_id, role FROM utilisateurs WHERE email = :e"),
                   {"e": email}).mappings().first()
    if not u:
        raise ValueError(f"aucun utilisateur avec l'email « {email} »")
    uid, cid = int(u["id"]), int(u["compte_id"])
    cible = "admin" if admin else "titulaire"
    deja = (u["role"] == "admin") if admin else (u["role"] != "admin")
    if deja:
        return {"utilisateur_id": uid, "compte_id": cid, "email": email,
                "role": u["role"], "change": False}
    db.execute(text("UPDATE utilisateurs SET role = :r, updated_at = now() WHERE id = :i"),
               {"r": cible, "i": uid})
    audit(db, "admin_promu" if admin else "admin_retrograde", cid, uid,
          f"role {u['role']} → {cible} (CLI admin-set)")
    db.commit()
    return {"utilisateur_id": uid, "compte_id": cid, "email": email, "role": cible, "change": True}


def creer_admin_invitation(db: Session, email: str, nom: str | None = None) -> dict:
    """VPS · AC-020 — admin NOMINATIF par invitation (le mot de passe se pose via le lien
    /invitation, jamais en argv ni au clavier de l'opérateur). Idempotent :
    - email inconnu → compte interne ACTIF (hors facturation, plan 'interne' comme
      `creer_admin`) + utilisateur rôle admin en statut 'invite' + lien d'invitation ;
    - email connu → PROMOTION au rôle admin ; si le mot de passe n'est pas encore posé,
      un lien d'invitation frais est (re)émis, sinon aucun lien (compte déjà opérationnel).
    Renvoie {utilisateur_id, compte_id, email, promu, lien|None, expire_at|None}."""
    ensure_tables(db)
    email = _norm_email(email)
    exist = db.execute(text("SELECT id, compte_id, role, hash, statut FROM utilisateurs"
                            " WHERE email = :e"), {"e": email}).mappings().first()
    if exist:
        uid, cid = int(exist["id"]), int(exist["compte_id"])
        promu = exist["role"] != "admin"
        if promu:
            db.execute(text("UPDATE utilisateurs SET role = 'admin', updated_at = now()"
                            " WHERE id = :i"), {"i": uid})
        # le compte porteur doit ouvrir la porte (session_utilisateur refuse invite/suspendu)
        db.execute(text("UPDATE comptes SET statut = 'actif', updated_at = now()"
                        " WHERE id = :c AND statut <> 'actif'"), {"c": cid})
        lien, exp = None, None
        if not exist["hash"]:                     # mot de passe jamais posé → lien frais
            tok = _token()
            exp = datetime.now(timezone.utc) + timedelta(days=7)
            db.execute(text("UPDATE utilisateurs SET statut = 'invite', invite_token_hash = :h,"
                            " invite_expire_at = :x, updated_at = now() WHERE id = :i"),
                       {"h": _sha(tok), "x": exp, "i": uid})
            lien = f"{get_settings().public_base_url}/invitation?token={tok}"
        audit(db, "admin_promu" if promu else "admin_reconfirme", cid, uid)
        db.commit()
        return {"utilisateur_id": uid, "compte_id": cid, "email": email, "promu": promu,
                "lien": lien, "expire_at": exp.isoformat() if exp else None}
    cid = db.execute(text("INSERT INTO comptes (nom, plan, statut, sieges)"
                          " VALUES (:n, :p, 'actif', 1) RETURNING id"),
                     {"n": nom or f"LABUSE (admin {email})", "p": PLAN_INTERNE}).scalar()
    tok = _token()
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    uid = db.execute(text(
        "INSERT INTO utilisateurs (compte_id, email, role, statut, invite_token_hash, invite_expire_at)"
        " VALUES (:c, :e, 'admin', 'invite', :h, :x) RETURNING id"),
        {"c": cid, "e": email, "h": _sha(tok), "x": exp}).scalar()
    audit(db, "admin_cree", cid, uid, "par invitation (AC-020)")
    db.commit()
    return {"utilisateur_id": int(uid), "compte_id": int(cid), "email": email, "promu": False,
            "lien": f"{get_settings().public_base_url}/invitation?token={tok}",
            "expire_at": exp.isoformat()}


def suspendre_compte(db: Session, compte_id: int, motif: str = "manuel") -> None:
    db.execute(text("UPDATE comptes SET statut = 'suspendu', updated_at = now() WHERE id = :c"),
               {"c": compte_id})
    db.execute(text("DELETE FROM sessions_auth WHERE utilisateur_id IN"
                    " (SELECT id FROM utilisateurs WHERE compte_id = :c)"), {"c": compte_id})
    audit(db, "compte_suspendu", compte_id, None, motif); db.commit()


def deconnecter_compte(db: Session, compte_id: int, motif: str = "admin") -> int:
    """COMPTE-2 (Lot 4) — DÉCONNEXION À DISTANCE : ferme TOUTES les sessions du compte (poste partagé,
    départ d'un client) SANS suspendre le compte (il pourra se reconnecter). Renvoie le nombre de
    sessions coupées. Geste réservé à l'admin (endpoint gardé)."""
    n = db.execute(text("DELETE FROM sessions_auth WHERE utilisateur_id IN"
                        " (SELECT id FROM utilisateurs WHERE compte_id = :c)"), {"c": compte_id}).rowcount
    audit(db, "compte_deconnecte_distance", compte_id, None, motif); db.commit()
    return int(n or 0)


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


def effacer_compte_rgpd(db: Session, email: str) -> bool:
    """AUDIT PAIEMENT · LEX-D — droit à l'effacement TOTAL : l'utilisateur, SON compte, et
    TOUTES ses données client (projets, pipeline CRM, veilles, filtres, signalements) partent
    réellement — par la cascade FK ON DELETE CASCADE de compte_id. L'audit est ANONYMISÉ
    (l'événement légal reste, l'identité disparaît). Renvoie True si un compte a été effacé."""
    email = _norm_email(email)
    u = db.execute(text("SELECT id, compte_id FROM utilisateurs WHERE email = :e"),
                   {"e": email}).mappings().first()
    if not u:
        return False
    cid = u["compte_id"]
    # anonymiser l'audit AVANT de perdre les id (on garde la trace de l'événement, pas l'identité)
    db.execute(text("UPDATE evenements_compte SET utilisateur_id = NULL, compte_id = NULL,"
                    " detail = '[efface RGPD]' WHERE compte_id = :c"), {"c": cid})
    # CLOISONNEMENT-1 (Lot C) — `mail_queue` et `contact_etiquette_log` portent `compte_id` mais SANS
    # FK cascade (le spool mail utilise `compte_id` comme TAG LIBRE — des inserts existent avec un
    # compte_id sans compte réel ; une FK stricte casserait ce contrat). La cascade du DELETE comptes
    # ne les emportait donc pas → la file de mails d'un compte effacé (destinataire + params) et le
    # journal de retours terrain SURVIVAIENT (orphelins RGPD). On les efface EXPLICITEMENT ici, avant
    # de perdre l'id. `contact_etiquette_log` n'était nettoyée ni par compte_id ni par son entry_id.
    for t in ("mail_queue", "contact_etiquette_log"):
        if db.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar():
            db.execute(text(f"DELETE FROM {t} WHERE compte_id = :c"), {"c": cid})
    # DELETE du compte → cascade : utilisateurs, sessions_auth, projets, pipeline_entries,
    # saved_searches, saved_filters, signalements (toutes portent compte_id ON DELETE CASCADE).
    db.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid})
    audit(db, "compte_efface_rgpd", None, None, "effacement total (compte + données client)")
    db.commit()
    log.info("RGPD : compte %s et toutes ses données client effacés", cid)
    return True
