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


# ───────── CONNEXIONS-2 Lot 3 (KO-4) — SIGNALEMENTS (file unique, traitée au dashboard) ─────────
# Le « Signaler » de la fiche (type='fiche') ET celui du Radar (type='annonce') écrivent dans la
# MÊME table `signalements`. L'admin les VOIT et les TRAITE ici (plus de revue CLI-only).

@router.get("/admin/signalements")
def admin_signalements(request: Request, statut: str | None = None) -> dict:
    """Liste TOUS les signalements (tous comptes), fiche + annonce, du plus récent au plus ancien.
    `statut` filtre (défaut : tous). Chaque ligne : type, IDU/bien, motif, auteur, date, statut."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    where = " WHERE s.statut = :s" if statut else ""
    with engine().connect() as c:
        rows = [dict(r) for r in c.execute(text(
            "SELECT s.id, s.type, s.parcelle_id, s.bien_id, s.type_erreur, s.champ, s.commentaire,"
            "       s.utilisateur, s.statut, s.created_at, s.traite_at, s.compte_id,"
            "       k.nom AS compte_nom"
            "  FROM signalements s LEFT JOIN comptes k ON k.id = s.compte_id"
            f"{where} ORDER BY s.created_at DESC LIMIT 500"), {"s": statut}).mappings()]
        n_ouverts = int(c.execute(text(
            "SELECT count(*) FROM signalements WHERE statut = 'nouveau'")).scalar() or 0)
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
        r["traite_at"] = r["traite_at"].isoformat() if r["traite_at"] else None
    return {"signalements": rows, "n_ouverts": n_ouverts}


class SignalementStatutIn(BaseModel):
    statut: str = Field(pattern="^(nouveau|traite)$")


@router.post("/admin/signalements/{sid}/statut")
def admin_signalement_statut(sid: int, body: SignalementStatutIn, request: Request) -> dict:
    """Traite (ou rouvre) un signalement : statut nouveau ↔ traite. `traite_at` horodaté au passage."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE signalements SET statut = (:st)::varchar,"
            "       traite_at = CASE WHEN (:st)::varchar = 'traite' THEN now() ELSE NULL END"
            " WHERE id = :i"), {"st": body.statut, "i": sid}).rowcount
    if not n:
        raise HTTPException(404, "Signalement introuvable.")
    return {"ok": True, "id": sid, "statut": body.statut}


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
        # CONNEXIONS-2 Lot 4 — KPI « courriers à déposer » : agrégat des demandes par bucket, vocabulaire
        # unique (courrier.STATUT_BUCKET). « à déposer » = ce que LABUSE doit encore déposer (statut demande).
        from .. import courrier as _courrier
        courrier_kpi = {"a_deposer": 0, "en_cours": 0, "clos": 0}
        if c.execute(text("SELECT to_regclass('courrier_demandes')")).scalar():
            rows_k = c.execute(text(
                "SELECT statut, count(*) AS n FROM courrier_demandes WHERE corps IS NOT NULL GROUP BY statut"
            )).mappings().all()
            for rk in rows_k:
                courrier_kpi[_courrier.STATUT_BUCKET.get(
                    _courrier.normaliser_statut(rk["statut"]), "en_cours")] += int(rk["n"])
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
    # CONNEXIONS-2 Lot 7.2 (N3) — sonde RUNTIME des endpoints métier (avec DB) : capte le cas
    # « /accueil/chiffres vivant mais écran vide » que le heal boot ne voit pas.
    from ..db import session_scope as _ss
    from . import sante as _sante
    try:
        with _ss() as _s:
            _sonde = _sante.sonde_metier(_s)
        sante["endpoints_ok"] = _sonde["ok"]
        sante["endpoints"] = _sonde["endpoints"]
    except Exception:  # noqa: BLE001 — la sonde ne casse jamais la page Pilotage
        sante["endpoints_ok"] = None
        sante["endpoints"] = []

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
        "courrier": courrier_kpi,   # CONNEXIONS-2 Lot 4 — {a_deposer, en_cours, clos}
        "run": {"label": run_label, "carte_le": carte_le.isoformat() if carte_le else None},
        "fil": fil,
        "gels": gels,
    }


@router.get("/admin/sante-endpoints")
def admin_sante_endpoints(request: Request) -> dict:
    """CONNEXIONS-2 Lot 7.2 (N3) — sonde des endpoints MÉTIER (avec DB), à la demande. La tuile
    « Santé » du dashboard poll ceci : dernier passage + endpoints en échec (forme et non-vacuité)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import session_scope
    from . import sante
    with session_scope() as s:
        return sante.sonde_metier(s)


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
            "       k.stripe_customer_id, k.copilote_quota_jour, k.essai_expire_at,"
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
    # A5 — signal de partage de compte (sessions actives + IP distinctes), par compte
    from ..comptes import sessions_actives_par_compte
    from ..db import session_scope
    with session_scope() as _s:
        partage = {p["compte_id"]: p for p in sessions_actives_par_compte(_s)}
    out = []
    for k in comptes:
        mails = mails_par_compte.get(k["id"], {})
        pg = partage.get(k["id"])
        out.append({
            "id": k["id"], "nom": k["nom"], "email": k["email"], "plan": k["plan"],
            "statut": k["statut"], "created_at": k["created_at"].isoformat() if k["created_at"] else None,
            "essai_expire_at": k["essai_expire_at"].isoformat() if k["essai_expire_at"] else None,
            "stripe": abos_par_cust.get(k["stripe_customer_id"]),
            "mails": mails,
            "rappels": _rappels_onboarding(k["created_at"], mails),
            # A5 — sessions simultanées : purement informatif (jamais de blocage/déconnexion)
            "partage": {"sessions": int(pg["sessions"]), "ips": int(pg["ips"] or 0),
                        "probable": bool(pg["partage_probable"])} if pg else None,
            "kpi": {
                # heartbeat = 1 balise / 5 min onglet visible → temps d'usage ESTIMÉ (dit au front)
                "usage_7j_min": hb.get(k["id"], 0) * 5,
                "derniere_connexion": k["derniere_connexion"].isoformat() if k["derniere_connexion"] else None,
                "copilote_jour": nl.get(f"c:{k['id']}", 0),
                "copilote_quota": k["copilote_quota_jour"] or defaut_quota,
            },
        })
    return {"licences": out, "stripe_configure": bool(stripe.get("configure")),
            "rapprochement": stripe.get("rapprochement"), "brevo": etat_configuration(),
            "partage_seuil": int(config.get_settings().sessions_signal_seuil)}


@router.get("/admin/partage")
def admin_partage(request: Request) -> dict:
    """A5 — partage de compte OBSERVÉ : par compte, sessions actives + IP distinctes simultanées,
    et le drapeau `partage_probable` (≥ seuil). Purement informatif : Vic décide, l'app informe —
    AUCUNE déconnexion, AUCUN blocage. RGPD : n'expose que des comptes et des NOMBRES (les
    empreintes sont hachées en base, jamais servies)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import config
    from ..comptes import sessions_actives_par_compte
    from ..db import engine, session_scope
    with session_scope() as s:
        lignes = sessions_actives_par_compte(s)
    noms = {}
    if lignes:
        with engine().begin() as c:
            noms = {r["id"]: r["nom"] for r in c.execute(text(
                "SELECT id, nom FROM comptes WHERE id = ANY(:ids)"),
                {"ids": [x["compte_id"] for x in lignes]}).mappings()}
    for x in lignes:
        x["nom"] = noms.get(x["compte_id"])
    signales = [x for x in lignes if x["partage_probable"]]
    return {"seuil": int(config.get_settings().sessions_signal_seuil),
            "comptes": sorted(lignes, key=lambda x: (-int(x["ips"] or 0), -int(x["sessions"]))),
            "n_signales": len(signales)}


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


class EssaiIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    nom: str | None = Field(default=None, max_length=120)
    heures: int | None = Field(default=None, ge=1, le=24 * 30)


@router.post("/admin/licences/creer-essai")
def admin_licence_creer_essai(body: EssaiIn, request: Request) -> dict:
    """D9 — compte d'ESSAI : même mécanisme officiel que le nouveau client (invitation), mais
    le compte est ACTIF tout de suite avec une date d'échéance (défaut 48 h, paramétrable).
    À l'échéance : bascule automatique sur la suspension (accès coupé, données conservées,
    écran « abonnement à régulariser »). Le lien d'invitation s'envoie à la main."""
    from fastapi import HTTPException
    from .. import config
    from ..comptes import creer_invitation
    from ..db import engine, session_scope
    from .auth import exiger_admin
    exiger_admin(request)
    heures = body.heures or int(config.get_settings().essai_duree_heures)
    try:
        with session_scope() as s:
            inv = creer_invitation(s, body.email.strip(), nom=(body.nom or "").strip() or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with engine().begin() as c:
        expire = c.execute(text(
            "UPDATE comptes SET statut = 'actif', essai_expire_at = now() + (:h || ' hours')::interval,"
            " updated_at = now() WHERE id = :c RETURNING essai_expire_at"),
            {"h": heures, "c": inv["compte_id"]}).scalar_one()
    return {"ok": True, **inv, "essai": True, "heures": heures, "essai_expire_at": expire.isoformat()}


@router.post("/admin/licences/{compte_id}/convertir")
def admin_licence_convertir(compte_id: int, request: Request) -> dict:
    """D9 — « Convertir en abonnement » : l'échéance d'essai tombe, le compte repasse `invite`
    (jamais payé) → le mécanisme OFFICIEL de reprise de paiement prend le relais au login
    (Checkout). Données conservées."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE comptes SET essai_expire_at = NULL,"
            " statut = CASE WHEN stripe_subscription_id IS NULL THEN 'invite' ELSE statut END,"
            " updated_at = now() WHERE id = :c"), {"c": compte_id}).rowcount
    if not n:
        raise HTTPException(404, "Compte introuvable.")
    return {"ok": True, "detail": "Essai levé — le compte paiera via le parcours officiel (login → Checkout)."}


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
    from ..brevo import LIBELLES              # LIBELLES = données d'affichage (pas un transport)
    from ..mail import envoyer_template       # CONNEXIONS-2 Lot 9.1 (KO-12) — envoi via la façade unique
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
    # CONNEXIONS-2 Lot 2 — consommé AUJOURD'HUI / plafond effectif par compte (même compteur que la
    # garde /ia + /ask). `plafond_effectif` = override licence, sinon défaut config.
    _defaut_q = int(config.get_settings().copilote_questions_jour_defaut)
    for q in quotas:
        q["plafond_effectif"] = int(q["copilote_quota_jour"]) if q["copilote_quota_jour"] is not None else _defaut_q
        q["consomme_aujourdhui"] = consomme_copilote_aujourdhui(int(q["id"]))
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
    au défaut config. CONNEXIONS-2 Lot 2 (KO-3) : /ia ET /api/copilote-v2/ask le lisent tous deux
    à la requête suivante (fonction unique `quota_du_compte`) — l'édition agit sur les deux surfaces."""
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
            "SELECT d.id, d.name, d.category, d.provider, d.status, d.technical_notes, d.last_sync_at,"
            "       d.source_millesime, d.source_horizon_at, d.source_cadence,"
            "       COALESCE(d.affichage_desactive, false) AS affichage_desactive,"
            # SENTINELLE-1 (W4) — état de veille amont (LEFT JOIN : une source non surveillée = état normal).
            "       v.actif AS veille_actif, v.methode AS veille_methode, v.dernier_statut AS veille_statut,"
            "       v.dernier_vu AS veille_vu, v.dernier_passage_at AS veille_passage, v.dernier_message AS veille_message"
            " FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id ORDER BY d.name")).mappings()]
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
            # CONNEXIONS-2 Lot 6.3 — état du flag pour le toggle admin (désactivée ⇒ hors vitrine).
            "affichage_desactive": bool(r.get("affichage_desactive")),
            # SENTINELLE-1 (W4) — bloc veille amont. `surveillee` = une ligne source_veille existe.
            # `nouvelle_version` = la sonde a constaté un millésime amont postérieur au servi (statut ambre).
            "veille": {
                "surveillee": r.get("veille_actif") is not None,
                "actif": bool(r.get("veille_actif")) if r.get("veille_actif") is not None else None,
                "methode": r.get("veille_methode"),
                "statut": r.get("veille_statut"),
                "millesime_amont": r.get("veille_vu"),
                "nouvelle_version": r.get("veille_statut") == "nouvelle_version",
                "passage_at": r["veille_passage"].isoformat() if r.get("veille_passage") else None,
                "message": r.get("veille_message"),
            },
        })
    # « à mettre à jour » d'abord (mandat), puis nom
    sources.sort(key=lambda s: (s["a_jour"] is not False, s["name"].lower()))
    for r in runs:
        r["started_at"] = r["started_at"].isoformat() if r["started_at"] else None
        r["finished_at"] = r["finished_at"].isoformat() if r["finished_at"] else None
    return {"sources": sources,
            "synthese": {"a_mettre_a_jour": sum(1 for s in sources if s["a_jour"] is False),
                         "ok": sum(1 for s in sources if s["a_jour"] is True),
                         "sans_echeance": sum(1 for s in sources if s["a_jour"] is None),
                         # SENTINELLE-1 (W4.2) — nombre de sources avec une nouvelle version disponible.
                         "nouvelle_version": sum(1 for s in sources if s["veille"]["nouvelle_version"]),
                         "surveillees": sum(1 for s in sources if s["veille"]["surveillee"])},
            "cadences": list(CADENCES.keys()),
            "runs": runs}


@router.post("/admin/sources/{source_id}/veille/verifier")
def admin_source_veille_verifier(source_id: int, request: Request) -> dict:
    """SENTINELLE-1 (W4.3) — « Vérifier maintenant » : lance la sonde sur CETTE source, en direct
    (forcer=True, hors cadence), et renvoie le verdict. N'écrit que dans source_veille, jamais dans
    data_sources. 404 si la source n'est pas surveillée (pas de ligne source_veille)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import session_scope
    from .. import sentinelle
    with session_scope() as s:
        existe = s.execute(text("SELECT 1 FROM source_veille WHERE source_id = :i"), {"i": source_id}).scalar()
        if not existe:
            raise HTTPException(404, "Cette source n'est pas surveillée (aucune ligne de veille).")
        recap = sentinelle.passer(s, source_ids=[source_id], forcer=True, notifier=True, delai_s=0)
        s.commit()
    detail = recap["details"][0] if recap["details"] else {}
    return {"ok": True, "statut": detail.get("statut"), "millesime_amont": detail.get("vu"),
            "servi": detail.get("servi"), "message": detail.get("message"), "notifs": recap["notifs"]}


class VeilleActiveIn(BaseModel):
    actif: bool


@router.post("/admin/sources/{source_id}/veille/active")
def admin_source_veille_active(source_id: int, body: VeilleActiveIn, request: Request) -> dict:
    """SENTINELLE-1 (W4.3) — active / désactive la SURVEILLANCE d'une source (flag source_veille.actif).
    Désactivée ⇒ le job quotidien la saute (état normal, pas une erreur). 404 si non surveillée."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text("UPDATE source_veille SET actif = :a, updated_at = now() WHERE source_id = :i"),
                      {"a": body.actif, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Cette source n'est pas surveillée (aucune ligne de veille).")
    return {"ok": True, "actif": body.actif}


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


class AffichageIn(BaseModel):
    actif: bool


@router.post("/admin/sources/{source_id}/affichage")
def admin_source_affichage(source_id: int, body: AffichageIn, request: Request) -> dict:
    """CONNEXIONS-2 Lot 6.3 (M2) — DÉSACTIVER / réactiver une source depuis le dashboard (admin seul).
    Écrit le flag `affichage_desactive` EN BASE (remplace `SOURCES_MASQUEES` en dur). Désactivée ⇒
    retirée de la vitrine (WHERE_AFFICHEES) ET les consommateurs (couches/outils) servent « source
    désactivée » via `sources_catalog.source_active`. Relu à la requête suivante (aucun cache)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        # ceinture : la colonne existe (heal boot) ; ADD IF NOT EXISTS pour une base jamais healée.
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS affichage_desactive "
                       "boolean NOT NULL DEFAULT false"))
        n = c.execute(text("UPDATE data_sources SET affichage_desactive = :d WHERE id = :i"),
                      {"d": not body.actif, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Source introuvable.")
    return {"ok": True, "actif": body.actif, "affichage_desactive": not body.actif}


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
#: CONNEXIONS-2 Lot 2 (KO-3) — kind UNIQUE du compteur de quota Copilote, partagé par /ia (recherche
#: NL) ET /api/copilote-v2/ask. Un seul compteur, un seul plafond (`quota_du_compte`), une seule
#: fonction : l'admin édite `copilote_quota_jour` au dashboard et les DEUX surfaces la respectent.
#: (Avant : /ia comptait 'nl' plafonné per-compte, /ask comptait 'copilote_v2_ask' plafonné GLOBAL
#: `copilote_v2_missions_jour` — l'override dashboard était ignoré par le Copilote réellement servi.)
QUOTA_COPILOTE_KIND = "copilote"


def quota_du_compte(compte_id: int | None) -> int | None:
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


#: alias rétro-compatible (l'ancien nom pointe sur la fonction unifiée — plus de divergence).
quota_nl_du_compte = quota_du_compte


def consomme_copilote_aujourdhui(compte_id: int) -> int:
    """Compteur Copilote consommé AUJOURD'HUI par ce compte (kind unique, scope `c:<id>`, jour
    Réunion) — la même mesure que la garde de quota. Pour la tuile dashboard « consommé / plafond »."""
    from ..tz import today_reunion
    from .protection import compteur
    from ..db import engine
    try:
        with engine().connect() as c:
            return compteur(c, f"c:{compte_id}", QUOTA_COPILOTE_KIND, today_reunion().isoformat())
    except Exception:  # noqa: BLE001 — best-effort, jamais un 500 sur le dashboard
        return 0
