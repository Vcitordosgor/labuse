"""TOUR DE CONTRÔLE (dashboard admin) — capteurs + endpoints /admin/* (mandat DASHBOARD-V1).

D1 — CAPTEURS. L'app s'instrumente, léger et RGPD-sobre : des COMPTEURS, jamais du contenu.
  · usage_events : ouverture d'outil + heartbeat de session (temps d'usage estimé par pas de
    5 min côté client). Fire-and-forget : l'endpoint ne lève JAMAIS (un capteur qui casse une
    requête client serait pire que pas de capteur).
  · retours : bouton « Signaler » de l'app cliente (bug/idée/question + message) → table
    `retours`, statut nouveau/traité/répondu. Notif cloche admin best-effort.
  · ia_budget : la conso IA est attribuée PAR COMPTE dans ia_log (colonne compte_id, posée par
    la garde d'auth via ai.core.poser_compte — réimplémentation propre du WIP fix/ia-modele-budget,
    branche NON mergée : divergée des fichiers remaniés).
  · quota Copilote PAR LICENCE : comptes.copilote_quota_jour (NULL = défaut config 80/jour) —
    lu par la porte NL de /ia (cf. ia.quota_nl_du_compte).
  · actifs/jour : rien à écrire ici — utilisateurs.dernier_login_at (existant) + usage_events.

Tout endpoint /admin/* passe par auth.exiger_admin (403 client, 401 sans session) — le
cloisonnement EXISTANT, réutilisé, jamais un nouveau mécanisme.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

log = logging.getLogger("labuse.dashboard")

router = APIRouter(tags=["dashboard"])

#: types de retours clients (bouton « Signaler ») — libellés courts, jamais de texte libre ici.
RETOUR_TYPES = ("bug", "idee", "question")
RETOUR_STATUTS = ("nouveau", "traite", "repondu")
#: outils/vues comptés — borne de longueur, pas de liste fermée (le front envoie sa clé d'outil ;
#: une clé inconnue reste un compteur honnête, jamais une erreur).
USAGE_KINDS = ("outil", "heartbeat")


def ensure_tables(engine) -> None:
    """Idempotent, appelé au boot (heal résilient FIX-GB-011)."""
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS usage_events ("
            " id bigserial PRIMARY KEY, ts timestamptz DEFAULT now(),"
            " compte_id integer, kind varchar(16) NOT NULL, outil varchar(48))"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_events_ts ON usage_events(ts)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_events_compte_ts ON usage_events(compte_id, ts)"))
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS retours ("
            " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), compte_id integer,"
            " type varchar(12) NOT NULL, message text NOT NULL,"
            " statut varchar(12) NOT NULL DEFAULT 'nouveau', updated_at timestamptz DEFAULT now())"))
        # ia_budget (D1) — attribution du coût IA au compte : colonne sur le ledger EXISTANT ia_log
        # (créé par ai.core._log_cost) ; ALTER d'abord au cas où la table précède cette colonne.
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS ia_log ("
            " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), kind varchar(24), model varchar(64),"
            " stub boolean, tokens_in integer, tokens_out integer, cout_eur numeric(8,5))"))
        c.execute(text("ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS compte_id integer"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_log_compte_ts ON ia_log(compte_id, ts)"))
        # quota Copilote PAR LICENCE (NULL = défaut config copilote_questions_jour_defaut)
        c.execute(text("ALTER TABLE comptes ADD COLUMN IF NOT EXISTS copilote_quota_jour integer"))
        # D4 — séquence d'onboarding : statut + date d'envoi STOCKÉS par (compte, mail)
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS licence_mails ("
            " compte_id integer NOT NULL, mail_key varchar(24) NOT NULL,"
            " statut varchar(12) NOT NULL DEFAULT 'envoye', sent_at timestamptz DEFAULT now(),"
            " PRIMARY KEY (compte_id, mail_key))"))


# ───────────────────────── capteurs côté CLIENT ─────────────────────────
class UsageIn(BaseModel):
    kind: str = Field(pattern="^(outil|heartbeat)$")
    outil: str | None = Field(default=None, max_length=48)


@router.post("/usage/event")
def usage_event(body: UsageIn, request: Request) -> dict:
    """Capteur d'usage — fire-and-forget : TOUJOURS {ok}, une panne de capteur ne casse jamais
    l'app cliente. RGPD-sobre : (compte, outil, ts), aucun contenu."""
    try:
        from ..db import engine
        cid = getattr(request.state, "compte_id", None)
        with engine().begin() as c:
            c.execute(text("INSERT INTO usage_events (compte_id, kind, outil) VALUES (:c, :k, :o)"),
                      {"c": cid, "k": body.kind, "o": (body.outil or None)})
    except Exception as exc:  # noqa: BLE001 — capteur best-effort, jamais bloquant
        log.debug("usage_event avalé : %s", exc)
    return {"ok": True}


class RetourIn(BaseModel):
    type: str = Field(pattern="^(bug|idee|question)$")
    message: str = Field(min_length=3, max_length=2000)


@router.post("/retours")
def creer_retour(body: RetourIn, request: Request) -> dict:
    """Bouton « Signaler » (app cliente, en haut à droite) : bug/idée/question + message."""
    from ..db import engine
    cid = getattr(request.state, "compte_id", None)
    with engine().begin() as c:
        rid = c.execute(text(
            "INSERT INTO retours (compte_id, type, message) VALUES (:c, :t, :m) RETURNING id"),
            {"c": cid, "t": body.type, "m": body.message.strip()}).scalar_one()
    # cloche admin best-effort (patron courrier_demande) — l'échec de la notif ne perd jamais le retour
    try:
        from ..db import session_scope
        from .events import creer_notification
        with session_scope() as s:
            creer_notification(s, kind="systeme", compte_id=None, source="Retour",
                               titre=f"Nouveau retour client ({body.type})",
                               detail=body.message[:280], lien="/admin",
                               dedup=f"retour:{rid}", permanent=True)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": rid}


# ───────────────────────── D2 — STRIPE (lecture seule) ─────────────────────────
@router.get("/admin/stripe")
def admin_stripe(request: Request, force: bool = False) -> dict:
    """Vue Stripe du dashboard (MRR, abonnements, statuts, CA/mois, rapprochement) — clé
    RESTREINTE lecture, cache 5 min, mode « non configuré » propre. Admin seulement (403 client)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..stripe_lecture import apercu
    return apercu(force=force)


# ───────────────────────── D3 — PILOTAGE ─────────────────────────
def _age_backup() -> dict:
    """Âge du dernier dump (GB-054) : mtime du .dump le plus récent de backup_dir.
    ambre ≥ 2 j · rouge ≥ 7 j · « absent » honnête si le répertoire est vide/inaccessible."""
    import glob
    import os
    import time as _t
    from .. import config
    rep = config.get_settings().backup_dir
    try:
        dumps = glob.glob(os.path.join(rep, "*.dump"))
        if not dumps:
            return {"etat": "absent", "chemin": rep, "age_jours": None}
        mtime = max(os.path.getmtime(p) for p in dumps)
        age_j = (_t.time() - mtime) / 86400
        etat = "rouge" if age_j >= 7 else "ambre" if age_j >= 2 else "ok"
        return {"etat": etat, "chemin": rep, "age_jours": round(age_j, 1),
                "mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()}
    except Exception:  # noqa: BLE001 — la tuile dit « absent », jamais un 500
        return {"etat": "absent", "chemin": rep, "age_jours": None}


@router.get("/admin/pilotage")
def admin_pilotage(request: Request) -> dict:
    """L'état de LABUSE en cinq secondes (héros + tuiles + LED du rail). AUCUN chiffre métier
    recalculé : tout est LU (Stripe lecture, ledgers, event_log, /readyz du process)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    from ..stripe_lecture import apercu
    stripe = apercu()

    with engine().begin() as c:
        licences_actives = c.execute(text(
            "SELECT COUNT(*) FROM comptes WHERE statut = 'actif'")).scalar() or 0
        # actifs 24 h = un login OU un capteur d'usage dans les dernières 24 h (par compte)
        actifs_24h = c.execute(text(
            "SELECT COUNT(*) FROM ("
            " SELECT DISTINCT compte_id FROM usage_events"
            "  WHERE ts > now() - interval '24 hours' AND compte_id IS NOT NULL"
            " UNION"
            " SELECT DISTINCT compte_id FROM utilisateurs"
            "  WHERE dernier_login_at > now() - interval '24 hours' AND compte_id IS NOT NULL) t"
        )).scalar() or 0
        ia = c.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) AS cout, COUNT(*) AS appels FROM ia_log"
            " WHERE ts >= date_trunc('month', now())")).mappings().one()
        # fil admin : les événements SYSTÈME (compte NULL = feed pilote/admin, patron existant)
        fil = [dict(r) for r in c.execute(text(
            "SELECT id, ts, kind, source, titre, detail, lien FROM event_log"
            " WHERE compte_id IS NULL AND kind = 'systeme'"
            " ORDER BY ts DESC LIMIT 30")).mappings()]
        gels = [dict(r) for r in c.execute(text(
            "SELECT sujet, motif, ts FROM acces_gels WHERE actif ORDER BY ts DESC LIMIT 20")).mappings()]
        # LED rail : run servi + date de la carte (même vérité que /map/tiles/meta)
        run_label = carte_le = None
        if c.execute(text("SELECT to_regclass('mvt_meta')")).scalar():
            row = c.execute(text(
                "SELECT value, updated_at FROM mvt_meta WHERE key = 'run_label'")).mappings().first()
            if row:
                run_label, carte_le = row["value"], row["updated_at"]

    from .app import app as _app
    heal = getattr(_app.state, "schema_heal", None) or {}
    # ok None = heal jamais passé (boot sans lifespan, ex. tests) → la tuile dit « inconnu »,
    # jamais un faux rouge ni un faux vert.
    sante = {"ok": heal.get("ok"), "total": heal.get("total"),
             "en_echec": [f.get("module") for f in heal.get("failures", [])]}

    for r in fil:
        r["ts"] = r["ts"].isoformat() if r["ts"] else None
    for g in gels:
        g["ts"] = g["ts"].isoformat() if g["ts"] else None
    return {
        "stripe": stripe,
        "licences_actives": licences_actives,
        "actifs_24h": actifs_24h,
        "ia_mois": {"cout_eur": float(ia["cout"]), "appels": int(ia["appels"])},
        "backup": _age_backup(),
        "sante": sante,
        "run": {"label": run_label, "carte_le": carte_le.isoformat() if carte_le else None},
        "fil": fil,
        "gels": gels,
    }


class DegelerIn(BaseModel):
    sujet: str = Field(min_length=1, max_length=128)


@router.post("/admin/degeler")
def admin_degeler(body: DegelerIn, request: Request) -> dict:
    """Dégel d'un sujet (gel anti-burst) depuis le fil Pilotage — même geste que la CLI
    `labuse ungel`, journalisé."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine, session_scope
    with engine().begin() as c:
        n = c.execute(text("UPDATE acces_gels SET actif = false WHERE sujet = :s AND actif"),
                      {"s": body.sujet}).rowcount
    if n:
        try:
            from .events import creer_notification
            with session_scope() as s:
                creer_notification(s, kind="systeme", compte_id=None, source="Sécurité",
                                   titre=f"Gel anti-burst levé sur {body.sujet[:64]}",
                                   detail="Dégel manuel depuis la Tour de contrôle.",
                                   dedup=f"degel:{body.sujet[:64]}")
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "degele": bool(n)}


# ───────────────────────── D4 — LICENCES ─────────────────────────
def _rappels_onboarding(created_at, mails: dict) -> list[str]:
    """L'app RAPPELLE, Vic déclenche (mandat MAILS) : Mail 2 à J+3, Mail 3 à J+10 — en ambre
    sur la fiche tant que non envoyés. Jamais d'envoi automatique."""
    if created_at is None:
        return []
    age_j = (datetime.now(tz=timezone.utc) - created_at).total_seconds() / 86400
    rappels = []
    if age_j >= 3 and "onboarding2" not in mails:
        rappels.append("Mail 2 à envoyer (J+3 atteint)")
    if age_j >= 10 and "onboarding3" not in mails:
        rappels.append("Mail 3 à envoyer (J+10 atteint)")
    return rappels


@router.get("/admin/licences")
def admin_licences(request: Request) -> dict:
    """Une fiche par client : statut app + Stripe, onboarding (mails stockés + rappels),
    KPI (usage 7 j via heartbeats, dernière connexion, Copilote jour/quota)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import config
    from ..brevo import etat_configuration
    from ..db import engine
    from ..stripe_lecture import apercu
    stripe = apercu()
    abos_par_cust = {a["customer_id"]: a for a in (stripe.get("abonnements") or [])}
    defaut_quota = int(config.get_settings().copilote_questions_jour_defaut)
    with engine().begin() as c:
        comptes = [dict(r) for r in c.execute(text(
            "SELECT k.id, k.nom, k.plan, k.statut, k.sieges, k.created_at, k.updated_at,"
            "       k.stripe_customer_id, k.copilote_quota_jour,"
            "       (SELECT u.email FROM utilisateurs u WHERE u.compte_id = k.id"
            "         ORDER BY u.id LIMIT 1) AS email,"
            "       (SELECT MAX(u.dernier_login_at) FROM utilisateurs u WHERE u.compte_id = k.id)"
            "         AS derniere_connexion"
            " FROM comptes k WHERE k.statut != 'resilie' ORDER BY k.created_at DESC")).mappings()]
        mails_rows = c.execute(text(
            "SELECT compte_id, mail_key, statut, sent_at FROM licence_mails")).mappings().all()
        usage_rows = c.execute(text(
            "SELECT compte_id, COUNT(*) AS hb FROM usage_events"
            " WHERE kind = 'heartbeat' AND ts > now() - interval '7 days'"
            "   AND compte_id IS NOT NULL GROUP BY compte_id")).mappings().all()
        nl_rows = c.execute(text(
            "SELECT sujet, n FROM usage_compteurs WHERE jour = CURRENT_DATE AND kind = 'nl'"
        )).mappings().all()
    mails_par_compte: dict[int, dict] = {}
    for m in mails_rows:
        mails_par_compte.setdefault(m["compte_id"], {})[m["mail_key"]] = {
            "statut": m["statut"], "sent_at": m["sent_at"].isoformat() if m["sent_at"] else None}
    hb = {u["compte_id"]: int(u["hb"]) for u in usage_rows}
    nl = {s["sujet"]: int(s["n"]) for s in nl_rows}
    out = []
    for k in comptes:
        mails = mails_par_compte.get(k["id"], {})
        out.append({
            "id": k["id"], "nom": k["nom"], "email": k["email"], "plan": k["plan"],
            "statut": k["statut"], "created_at": k["created_at"].isoformat() if k["created_at"] else None,
            "stripe": abos_par_cust.get(k["stripe_customer_id"]),
            "mails": mails,
            "rappels": _rappels_onboarding(k["created_at"], mails),
            "kpi": {
                # heartbeat = 1 balise / 5 min onglet visible → temps d'usage ESTIMÉ (dit au front)
                "usage_7j_min": hb.get(k["id"], 0) * 5,
                "derniere_connexion": k["derniere_connexion"].isoformat() if k["derniere_connexion"] else None,
                "copilote_jour": nl.get(f"c:{k['id']}", 0),
                "copilote_quota": k["copilote_quota_jour"] or defaut_quota,
            },
        })
    return {"licences": out, "stripe_configure": bool(stripe.get("configure")),
            "rapprochement": stripe.get("rapprochement"), "brevo": etat_configuration()}


class NouveauClientIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    nom: str | None = Field(default=None, max_length=120)


@router.post("/admin/licences/creer")
def admin_licence_creer(body: NouveauClientIn, request: Request) -> dict:
    """Parcours « nouveau client » étape 1 — le MÉCANISME OFFICIEL existant (creer_invitation :
    compte + utilisateur `invite`, token 7 j). Renvoie le lien d'invitation (envoi à la main,
    décision Vic historique conservée)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..comptes import creer_invitation
    from ..db import session_scope
    try:
        with session_scope() as s:
            inv = creer_invitation(s, body.email.strip(), nom=(body.nom or "").strip() or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, **inv}


class SuspendreIn(BaseModel):
    motif: str = Field(default="manuel", max_length=120)


@router.post("/admin/licences/{compte_id}/suspendre")
def admin_licence_suspendre(compte_id: int, body: SuspendreIn, request: Request) -> dict:
    """Suspension MANUELLE (mandat : jamais automatique sur un échec de carte) — flag en base,
    sessions coupées, données INTACTES, réversible. Le client voit « abonnement à régulariser »
    + lien de paiement à son prochain login (cf. branche /login)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..comptes import suspendre_compte
    from ..db import session_scope
    with session_scope() as s:
        suspendre_compte(s, compte_id, motif=f"dashboard:{body.motif}")
    return {"ok": True, "statut": "suspendu"}


@router.post("/admin/licences/{compte_id}/retablir")
def admin_licence_retablir(compte_id: int, request: Request) -> dict:
    from .auth import exiger_admin
    exiger_admin(request)
    from ..comptes import reactiver_compte
    from ..db import session_scope
    with session_scope() as s:
        reactiver_compte(s, compte_id, motif="dashboard:retabli")
    return {"ok": True, "statut": "actif"}


class MailIn(BaseModel):
    key: str = Field(min_length=2, max_length=24)


@router.post("/admin/licences/{compte_id}/mail")
def admin_licence_mail(compte_id: int, body: MailIn, request: Request) -> dict:
    """Envoi MANUEL d'un template Brevo au titulaire (onboarding 1/2/3, souscription, relance…).
    Non configuré → {envoye:false, raison} — le bouton du dashboard l'affiche, rien de silencieux.
    Statut + date STOCKÉS (licence_mails) quand l'envoi part."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..brevo import LIBELLES, envoyer_template
    from ..db import engine
    if body.key not in LIBELLES:
        raise HTTPException(422, f"Template inconnu « {body.key} ».")
    with engine().begin() as c:
        row = c.execute(text(
            "SELECT k.nom, (SELECT u.email FROM utilisateurs u WHERE u.compte_id = k.id"
            " ORDER BY u.id LIMIT 1) AS email FROM comptes k WHERE k.id = :c"),
            {"c": compte_id}).mappings().first()
    if not row or not row["email"]:
        raise HTTPException(404, "Compte introuvable ou sans utilisateur.")
    res = envoyer_template(row["email"], body.key, params={"nom": row["nom"]})
    if res.get("envoye"):
        with engine().begin() as c:
            c.execute(text(
                "INSERT INTO licence_mails (compte_id, mail_key, statut) VALUES (:c, :k, 'envoye')"
                " ON CONFLICT (compte_id, mail_key)"
                " DO UPDATE SET statut = 'envoye', sent_at = now()"),
                {"c": compte_id, "k": body.key})
    return {"ok": True, **res}


# ───────────────────────── D5 — IA (section mauve) ─────────────────────────
@router.get("/admin/ia")
def admin_ia(request: Request) -> dict:
    """Conso IA lue du ledger ia_log (D1) : mois courant, coût moyen/question, 30 jours de
    barres, ventilation par licence, projection fin de mois AU RYTHME DES 7 DERNIERS JOURS.
    Le solde Anthropic n'est PAS exposé par l'API : conso trackée localement (note honnête)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import config
    from ..db import engine
    with engine().begin() as c:
        mois = c.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) AS cout, COUNT(*) AS appels FROM ia_log"
            " WHERE ts >= date_trunc('month', now())")).mappings().one()
        jours = [dict(r) for r in c.execute(text(
            "SELECT date_trunc('day', ts)::date AS jour, ROUND(SUM(cout_eur), 4) AS cout,"
            "       COUNT(*) AS appels"
            " FROM ia_log WHERE ts > now() - interval '30 days'"
            " GROUP BY 1 ORDER BY 1")).mappings()]
        par_licence = [dict(r) for r in c.execute(text(
            "SELECT l.compte_id, COALESCE(k.nom, 'Vous (admin/pilote)') AS nom,"
            "       ROUND(SUM(l.cout_eur), 4) AS cout, COUNT(*) AS appels"
            " FROM ia_log l LEFT JOIN comptes k ON k.id = l.compte_id"
            " WHERE l.ts > now() - interval '30 days'"
            " GROUP BY l.compte_id, k.nom ORDER BY SUM(l.cout_eur) DESC")).mappings()]
        cout_7j = float(c.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) FROM ia_log"
            " WHERE ts > now() - interval '7 days'")).scalar() or 0)
        quotas = [dict(r) for r in c.execute(text(
            "SELECT id, nom, copilote_quota_jour FROM comptes"
            " WHERE statut NOT IN ('resilie') ORDER BY created_at DESC")).mappings()]
    from datetime import date
    import calendar
    today = date.today()
    jours_restants = calendar.monthrange(today.year, today.month)[1] - today.day
    projection = float(mois["cout"]) + (cout_7j / 7.0) * jours_restants
    appels = int(mois["appels"])
    for r in jours:
        r["jour"] = r["jour"].isoformat()
        r["cout"] = float(r["cout"])
    for r in par_licence:
        r["cout"] = float(r["cout"])
    return {
        "mois": {"cout_eur": float(mois["cout"]), "appels": appels,
                 "cout_moyen_question": (float(mois["cout"]) / appels) if appels else None},
        "projection_fin_mois_eur": round(projection, 2),
        "jours": jours,
        "par_licence": par_licence,
        "quota_defaut": int(config.get_settings().copilote_questions_jour_defaut),
        "quotas": quotas,
        "note": "Solde Anthropic non exposé par l'API — consommation trackée localement (ledger ia_log).",
    }


class QuotaIn(BaseModel):
    quota: int | None = Field(default=None, ge=1, le=10_000)


@router.post("/admin/licences/{compte_id}/quota")
def admin_licence_quota(compte_id: int, body: QuotaIn, request: Request) -> dict:
    """Quota Copilote/jour de LA licence (éditable au dashboard, mandat D5) — null = retour
    au défaut config. Le /ask le lit à la prochaine question (quota_nl_du_compte)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE comptes SET copilote_quota_jour = :q, updated_at = now() WHERE id = :c"),
            {"q": body.quota, "c": compte_id}).rowcount
    if not n:
        raise HTTPException(404, "Compte introuvable.")
    return {"ok": True, "quota": body.quota}


# ───────────────────────── D6 — SOURCES ─────────────────────────
#: cadence normalisée → délai (jours, marge comprise) au-delà duquel « À mettre à jour ».
#: None = pas d'échéance calculable (pluriannuelle : le millésime amont bouge rarement).
CADENCES: dict[str, int | None] = {
    "hebdomadaire": 10, "mensuelle": 40, "trimestrielle": 100,
    "semestrielle": 200, "annuelle": 400, "pluriannuelle": None, "continue": 10,
}


def _cadence_normalisee(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip().lower()
    for k in CADENCES:
        if v.startswith(k[:6]):     # 'mensuel'/'mensuelle', 'semestriel(le)'… → clé canonique
            return k
    return None


def _commandes_ingestion() -> list[dict]:
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "config" / "sources_ingestion.yaml"
    try:
        return (yaml.safe_load(p.read_text()) or {}).get("commandes", [])
    except Exception:  # noqa: BLE001 — pas de mapping → pas de bouton, jamais un 500
        return []


def _relance_pour(nom: str) -> dict | None:
    import fnmatch
    for cmd in _commandes_ingestion():
        if fnmatch.fnmatch(nom.lower(), cmd["motif"].lower().replace("%", "*")):
            return cmd
    return None


@router.get("/admin/sources")
def admin_sources(request: Request) -> dict:
    """Les 59 : millésime amont, ingéré le, cadence ATTENDUE (configurable ici), badge
    « À mettre à jour » = cadence dépassée (calcul auto sur last_sync_at), bouton Relancer
    quand une commande existe (config/sources_ingestion.yaml). + dernières exécutions
    d'ingestion (ingestion_runs — les crons ne journalisent pas event_log, la table est
    leur vraie trace ; le verdict des crons vit sur /healthz/crons, l'écran l'affiche)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    from ..sources_catalog import est_affichee
    now = datetime.now(tz=timezone.utc)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            "SELECT id, name, category, provider, status, technical_notes, last_sync_at,"
            "       source_millesime, source_horizon_at, source_cadence"
            " FROM data_sources ORDER BY name")).mappings()]
        runs = [dict(r) for r in c.execute(text(
            "SELECT r.started_at, r.finished_at, r.status, r.parcels_count, d.name"
            " FROM ingestion_runs r LEFT JOIN data_sources d ON d.id = r.data_source_id"
            " ORDER BY r.started_at DESC NULLS LAST LIMIT 10")).mappings()]
    sources = []
    for r in rows:
        if not est_affichee(r["name"], r.get("technical_notes"), r["status"]):
            continue
        cad = _cadence_normalisee(r["source_cadence"])
        delai = CADENCES.get(cad) if cad else None
        a_jour = None
        if delai is not None and r["last_sync_at"] is not None:
            a_jour = (now - r["last_sync_at"]).days <= delai
        relance = _relance_pour(r["name"])
        sources.append({
            "id": r["id"], "name": r["name"], "category": r["category"],
            "millesime": r["source_millesime"],
            "horizon": r["source_horizon_at"].isoformat() if r["source_horizon_at"] else None,
            "ingere_le": r["last_sync_at"].isoformat() if r["last_sync_at"] else None,
            "cadence": cad,
            # a_jour : true OK · false à mettre à jour · null = pas d'échéance calculable
            "a_jour": a_jour,
            "relance": relance["label"] if relance else None,
        })
    # « à mettre à jour » d'abord (mandat), puis nom
    sources.sort(key=lambda s: (s["a_jour"] is not False, s["name"].lower()))
    for r in runs:
        r["started_at"] = r["started_at"].isoformat() if r["started_at"] else None
        r["finished_at"] = r["finished_at"].isoformat() if r["finished_at"] else None
    return {"sources": sources,
            "synthese": {"a_mettre_a_jour": sum(1 for s in sources if s["a_jour"] is False),
                         "ok": sum(1 for s in sources if s["a_jour"] is True),
                         "sans_echeance": sum(1 for s in sources if s["a_jour"] is None)},
            "cadences": list(CADENCES.keys()),
            "runs": runs}


class CadenceIn(BaseModel):
    cadence: str | None = None


@router.post("/admin/sources/{source_id}/cadence")
def admin_source_cadence(source_id: int, body: CadenceIn, request: Request) -> dict:
    """La cadence attendue de chaque source se règle SUR CETTE PAGE (mandat D6)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    cad = _cadence_normalisee(body.cadence) if body.cadence else None
    if body.cadence and cad is None:
        raise HTTPException(422, f"Cadence inconnue « {body.cadence} » (attendues : {', '.join(CADENCES)}).")
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text("UPDATE data_sources SET source_cadence = :v WHERE id = :i"),
                      {"v": cad, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Source introuvable.")
    return {"ok": True, "cadence": cad}


@router.post("/admin/sources/{source_id}/relancer")
def admin_source_relancer(source_id: int, request: Request) -> dict:
    """Relance l'ingestion d'une source dont la commande est CONNUE (même geste que le cron,
    détaché) — journalisée. Sans mapping : 404, le front n'affiche pas le bouton."""
    import subprocess
    import sys
    from pathlib import Path
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine, session_scope
    with engine().begin() as c:
        nom = c.execute(text("SELECT name FROM data_sources WHERE id = :i"), {"i": source_id}).scalar()
    if not nom:
        raise HTTPException(404, "Source introuvable.")
    cmd = _relance_pour(nom)
    if not cmd:
        raise HTTPException(404, "Aucune commande d'ingestion connue pour cette source.")
    argv = list(cmd["argv"])
    if argv and argv[0] == "python":
        argv[0] = sys.executable          # le python du process (venv), jamais un python du PATH
    racine = Path(__file__).resolve().parents[3]
    log_path = f"/tmp/labuse-relance-{cmd['label']}.log"
    try:
        with open(log_path, "ab") as fh:
            subprocess.Popen(argv, cwd=str(racine), stdout=fh, stderr=fh,
                             start_new_session=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Lancement impossible ({type(exc).__name__}).") from exc
    try:
        from .events import creer_notification
        with session_scope() as s:
            creer_notification(s, kind="systeme", compte_id=None, source="Sources",
                               titre=f"Ingestion relancée à la main : {cmd['label']}",
                               detail=f"{nom} — commande du cron, détachée (log {log_path}).",
                               dedup=f"relance:{cmd['label']}:{datetime.now(tz=timezone.utc):%Y%m%d%H%M}")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "label": cmd["label"], "log": log_path}


# ───────────────────────── D7 — PRODUIT ─────────────────────────
@router.get("/admin/produit")
def admin_produit(request: Request) -> dict:
    """Usage par outil 30 j (capteurs D1 — « Par client » = V2, hors mandat) + retours clients
    (bouton « Signaler », statuts éditables ici)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        usage = [dict(r) for r in c.execute(text(
            "SELECT outil, COUNT(*) AS n FROM usage_events"
            " WHERE kind = 'outil' AND outil IS NOT NULL AND ts > now() - interval '30 days'"
            " GROUP BY outil ORDER BY COUNT(*) DESC")).mappings()]
        retours = [dict(r) for r in c.execute(text(
            "SELECT r.id, r.ts, r.type, r.message, r.statut, k.nom AS compte"
            " FROM retours r LEFT JOIN comptes k ON k.id = r.compte_id"
            " ORDER BY r.ts DESC LIMIT 200")).mappings()]
    for r in retours:
        r["ts"] = r["ts"].isoformat() if r["ts"] else None
    return {"usage": usage, "retours": retours}


class RetourStatutIn(BaseModel):
    statut: str = Field(pattern="^(nouveau|traite|repondu)$")


@router.post("/admin/retours/{retour_id}/statut")
def admin_retour_statut(retour_id: int, body: RetourStatutIn, request: Request) -> dict:
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE retours SET statut = :s, updated_at = now() WHERE id = :i"),
            {"s": body.statut, "i": retour_id}).rowcount
    if not n:
        raise HTTPException(404, "Retour introuvable.")
    return {"ok": True, "statut": body.statut}


# ───────────────────────── quota Copilote PAR LICENCE ─────────────────────────
def quota_nl_du_compte(compte_id: int | None) -> int | None:
    """Quota de questions Copilote/jour pour CE compte : l'override de la licence
    (comptes.copilote_quota_jour), sinon le défaut config (80/jour). None si pas de compte
    (pilote/anonyme → l'appelant garde son quota historique nl_quota_jour)."""
    if compte_id is None:
        return None
    from .. import config
    defaut = int(config.get_settings().copilote_questions_jour_defaut)
    try:
        from ..db import engine
        with engine().begin() as c:
            v = c.execute(text("SELECT copilote_quota_jour FROM comptes WHERE id = :c"),
                          {"c": compte_id}).scalar()
        return int(v) if v is not None else defaut
    except Exception:  # noqa: BLE001 — lecture best-effort : jamais bloquer une question sur une panne
        return defaut
