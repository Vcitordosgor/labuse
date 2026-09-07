"""COMPTE-2 · Lot 2 — la FILE D'ATTENTE des mails (`mail_queue`) et le point d'envoi unique.

C'est le lot qui rend l'envoi VISIBLE. Avant, un mail partait (ou ne partait pas) sans que rien ne le
raconte. Désormais TOUT envoi de template passe par cette file, y compris les envois immédiats :

    en attente ──(départ)──► parti ──(2xx Brevo)──► reçu par Brevo
        │                                   │
        └────────(3 échecs)────────────────┴──► échec  (rejouable d'un clic)

Règles dures (mandat) :
- **Rien n'affiche « envoyé » si rien n'est parti** (RV-013) : l'état d'une entrée est le RÉEL renvoyé
  par le transport, jamais l'optimisme de l'appelant.
- Trois tentatives espacées, puis « échec » définitif avec la raison lisible en français.
- **Rien n'est supprimé** de la file : l'historique EST la preuve. « annuler » ne vaut que pour un
  mail encore en attente (programmé) ; il devient `annule`, il ne disparaît pas.
- Chaque entrée porte QUI l'a demandé (Vic, un job, le client).
- Anti-doublon : un double-clic (même compte, même template, fenêtre courte) = une seule entrée.

Le TRANSPORT bas niveau reste `brevo.envoyer_template` (templatisé, suivi de clic OFF). `mail.envoyer_mail`
est la façade applicative : elle enfile ici puis (envoi immédiat) déclenche le départ.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from . import brevo

log = logging.getLogger("labuse.mailfile")

TENTATIVES_MAX = 3
#: fenêtre anti-doublon par défaut (double-clic) : deux enfilages identiques sous ce délai = un seul.
FENETRE_DOUBLON_S = 30

# vocabulaire d'état UNIQUE (mandat). `annule` = un programmé décommandé avant départ (jamais supprimé).
ETATS = ("en_attente", "parti", "recu", "echec", "annule")
LIBELLES_ETAT = {
    "en_attente": "En attente", "parti": "Parti", "recu": "Reçu par Brevo",
    "echec": "Échec", "annule": "Annulé",
}


def ensure_tables(engine) -> None:
    """Idempotent (pattern maison CREATE IF NOT EXISTS), appelable au boot."""
    with engine.begin() as c:
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS mail_queue (
                id           bigserial PRIMARY KEY,
                compte_id    integer,
                mail_key     varchar(24) NOT NULL,   -- clé registre (brevo.REGISTRE)
                template_id  integer,                -- ID Brevo résolu à l'enfilage (trace)
                template_nom varchar(48),            -- nom Brevo (trace lisible)
                destinataire text NOT NULL,
                params       jsonb NOT NULL DEFAULT '{}'::jsonb,
                etat         varchar(12) NOT NULL DEFAULT 'en_attente'
                             CHECK (etat IN ('en_attente','parti','recu','echec','annule')),
                demandeur    varchar(64) NOT NULL DEFAULT 'systeme',  -- QUI : vic / job:<nom> / client
                dedup        varchar(96),            -- anti-doublon (compte:key), fenêtre courte
                tentatives   integer NOT NULL DEFAULT 0,
                message_id   text,                   -- messageId Brevo (preuve du départ)
                erreur       text,                   -- raison lisible en français (échec)
                prevu_at     timestamptz,            -- date PRÉVUE d'un programmé (NULL = immédiat)
                cree_at      timestamptz NOT NULL DEFAULT now(),
                parti_at     timestamptz             -- date de DÉPART réel (2xx)
            )"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_mail_queue_etat_cree ON mail_queue(etat, cree_at DESC)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_mail_queue_compte ON mail_queue(compte_id, cree_at DESC)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_mail_queue_dedup ON mail_queue(dedup, cree_at DESC)"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _params_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params or {}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _ligne(row) -> dict:
    """Sérialise une ligne de file pour les écrans (jamais de secret : params applicatifs seulement)."""
    d = dict(row)
    for k in ("cree_at", "parti_at", "prevu_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    d["etat_libelle"] = LIBELLES_ETAT.get(d.get("etat"), d.get("etat"))
    return d


# ───────────────────────── enfilage + envoi ─────────────────────────

def enfiler(engine, *, key: str, to: str, params: dict | None = None,
            compte_id: int | None = None, demandeur: str = "systeme",
            prevu_at: datetime | None = None, dedup: str | None = None,
            fenetre_doublon_s: int = FENETRE_DOUBLON_S) -> dict:
    """Pose une entrée `en_attente` dans la file (sans l'envoyer). Anti-doublon : si `dedup` (ou, à
    défaut, compte:key:hash(params)) a déjà une entrée NON-échec dans la fenêtre, on renvoie celle-là."""
    t = brevo.template(key)
    if not t:
        raise ValueError(f"template inconnu « {key} »")
    params = params or {}
    dd = dedup or f"{compte_id}:{key}:{_params_hash(params)}"
    with engine.begin() as c:
        # anti-doublon : même dedup, état non-échec, créé dans la fenêtre → on rend l'existant.
        recent = c.execute(text(
            "SELECT * FROM mail_queue WHERE dedup = :dd AND etat <> 'echec'"
            " AND cree_at > now() - make_interval(secs => :w) ORDER BY id DESC LIMIT 1"),
            {"dd": dd, "w": fenetre_doublon_s}).mappings().first()
        if recent:
            return {**_ligne(recent), "doublon": True}
        row = c.execute(text(
            "INSERT INTO mail_queue (compte_id, mail_key, template_id, template_nom, destinataire,"
            " params, demandeur, dedup, prevu_at) VALUES"
            " (:cid, :key, :tid, :tn, :to, CAST(:p AS jsonb), :who, :dd, :prevu) RETURNING *"),
            {"cid": compte_id, "key": key, "tid": brevo.template_id(key), "tn": t.nom, "to": to,
             "p": json.dumps(params, ensure_ascii=False), "who": demandeur[:64], "dd": dd,
             "prevu": prevu_at}).mappings().first()
    _journal(engine, row["id"], "en_attente", demandeur, compte_id,
             detail=f"{key} → {to}" + (f" (prévu {prevu_at.isoformat()})" if prevu_at else ""))
    return {**_ligne(row), "doublon": False}


def _tenter_depart(engine, mail_id: int) -> dict:
    """Tente le DÉPART d'une entrée : appelle le transport Brevo, écrit l'état RÉEL. Idempotent sur
    `recu`/`annule` (ne renvoie pas un mail déjà parti). Retourne la ligne à jour."""
    with engine.begin() as c:
        row = c.execute(text("SELECT * FROM mail_queue WHERE id = :i FOR UPDATE"),
                        {"i": mail_id}).mappings().first()
        if not row:
            raise ValueError(f"mail {mail_id} introuvable")
        if row["etat"] in ("recu", "annule"):
            return _ligne(row)
        key, to, params = row["mail_key"], row["destinataire"], row["params"] or {}
        demandeur, compte_id = row["demandeur"], row["compte_id"]
    # GARDE fail-closed (mandat Lot 2) : une variable attendue et non fournie sortirait en
    # « {{ params.X }} » brut chez le client (🔴). On REFUSE de partir : tentative ratée, raison
    # lisible, l'entrée reste visible dans la file (rejouable une fois le param fourni).
    manquants = [p for p in brevo.params_attendus(key) if p not in params]
    if manquants:
        res = {"envoye": False, "raison": "paramètres manquants : " + ", ".join(manquants)}
    else:
        # appel transport HORS transaction (I/O réseau), PAR LA FAÇADE `mail` (transport unique :
        # brevo.envoyer_template n'est appelé QUE depuis mail.py — garde test_transport_mail_unique).
        from . import mail
        res = mail.envoyer_template(to, key, params)
    now = _now()
    if res.get("envoye"):
        with engine.begin() as c:
            row = c.execute(text(
                "UPDATE mail_queue SET etat = 'recu', tentatives = tentatives + 1,"
                " message_id = :mid, erreur = NULL, parti_at = :now WHERE id = :i RETURNING *"),
                {"mid": res.get("message_id"), "now": now, "i": mail_id}).mappings().first()
        _journal(engine, mail_id, "recu", demandeur, compte_id,
                 detail=f"{key} → {to} (message-id {res.get('message_id') or '?'})")
        return _ligne(row)
    # échec : incrémente, bascule en 'echec' au bout de TENTATIVES_MAX, sinon reste 'en_attente'
    raison = res.get("raison") or "échec inconnu"
    with engine.begin() as c:
        row = c.execute(text(
            "UPDATE mail_queue SET tentatives = tentatives + 1, erreur = :err,"
            " etat = CASE WHEN tentatives + 1 >= :max THEN 'echec' ELSE 'en_attente' END"
            " WHERE id = :i RETURNING *"),
            {"err": raison, "max": TENTATIVES_MAX, "i": mail_id}).mappings().first()
    _journal(engine, mail_id, row["etat"], demandeur, compte_id,
             detail=f"{key} → {to} — tentative {row['tentatives']}/{TENTATIVES_MAX} : {raison}")
    return _ligne(row)


def envoyer_mail(engine, *, key: str, to: str, params: dict | None = None,
                 compte_id: int | None = None, demandeur: str = "systeme",
                 prevu_at: datetime | None = None, dedup: str | None = None) -> dict:
    """POINT D'ENVOI UNIQUE (façade `mail.envoyer_mail`) : enfile, puis — si l'envoi est immédiat
    (`prevu_at` absent ou déjà passé) — déclenche le départ tout de suite. Un programmé (J+3, J+10,
    digest) reste `en_attente` avec sa date prévue ; un worker/clic le fera partir. Renvoie la ligne."""
    ligne = enfiler(engine, key=key, to=to, params=params, compte_id=compte_id,
                    demandeur=demandeur, prevu_at=prevu_at, dedup=dedup)
    if ligne.get("doublon"):
        return ligne
    immediate = prevu_at is None or prevu_at <= _now()
    if immediate and ligne["etat"] == "en_attente":
        return {**_tenter_depart(engine, ligne["id"]), "doublon": False}
    return ligne


def rejouer(engine, mail_id: int, demandeur: str = "systeme") -> dict:
    """Rejoue un mail en ÉCHEC (ou un programmé en attente) : remet à zéro le compteur de tentatives
    et retente le départ. L'historique reste (aucune ligne supprimée)."""
    with engine.begin() as c:
        row = c.execute(text("SELECT etat FROM mail_queue WHERE id = :i"), {"i": mail_id}).mappings().first()
        if not row:
            raise ValueError(f"mail {mail_id} introuvable")
        if row["etat"] not in ("echec", "en_attente"):
            return _ligne(c.execute(text("SELECT * FROM mail_queue WHERE id = :i"),
                                    {"i": mail_id}).mappings().first())
        c.execute(text("UPDATE mail_queue SET etat = 'en_attente', tentatives = 0, erreur = NULL"
                       " WHERE id = :i"), {"i": mail_id})
    _journal(engine, mail_id, "rejoue", demandeur, None, detail="rejeu manuel")
    return _tenter_depart(engine, mail_id)


def annuler(engine, mail_id: int, demandeur: str = "systeme") -> dict:
    """Décommande un mail ENCORE EN ATTENTE (programmé) : il devient `annule`, il n'est PAS supprimé.
    Un mail déjà parti/reçu ne s'annule pas (retour tel quel)."""
    with engine.begin() as c:
        row = c.execute(text("SELECT * FROM mail_queue WHERE id = :i FOR UPDATE"),
                        {"i": mail_id}).mappings().first()
        if not row:
            raise ValueError(f"mail {mail_id} introuvable")
        if row["etat"] != "en_attente":
            return _ligne(row)
        row = c.execute(text("UPDATE mail_queue SET etat = 'annule' WHERE id = :i RETURNING *"),
                        {"i": mail_id}).mappings().first()
    _journal(engine, mail_id, "annule", demandeur, row["compte_id"], detail="programmé annulé")
    return _ligne(row)


def depart_des_programmes(engine, demandeur: str = "job:mail-queue") -> int:
    """Worker : fait partir les programmés dont l'heure est venue (prevu_at ≤ now, encore en attente)."""
    with engine.begin() as c:
        ids = [r[0] for r in c.execute(text(
            "SELECT id FROM mail_queue WHERE etat = 'en_attente' AND prevu_at IS NOT NULL"
            " AND prevu_at <= now() ORDER BY prevu_at")).all()]
    for mid in ids:
        _tenter_depart(engine, mid)
    return len(ids)


# ───────────────────────── lecture (écrans) ─────────────────────────

def lister(engine, *, filtre: str = "tous", compte_id: int | None = None, limite: int = 200) -> list[dict]:
    """File servie aux écrans. `filtre` : en_attente | partis | echecs | tous.
    `compte_id` : restreint à un compte (fiche → onglet Activité)."""
    where, p = [], {"lim": min(int(limite), 500)}
    if filtre == "en_attente":
        where.append("etat = 'en_attente'")
    elif filtre == "partis":
        where.append("etat IN ('parti','recu')")
    elif filtre == "echecs":
        where.append("etat = 'echec'")
    if compte_id is not None:
        where.append("compte_id = :cid")
        p["cid"] = compte_id
    sql = "SELECT * FROM mail_queue"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT :lim"
    with engine.begin() as c:
        rows = c.execute(text(sql), p).mappings().all()
    return [_ligne(r) for r in rows]


def compteurs(engine) -> dict:
    """Compteurs par état (bandeau de la page Courrier → Mails) + échecs du jour (jauge Pilotage)."""
    with engine.begin() as c:
        par_etat = {r[0]: r[1] for r in c.execute(text(
            "SELECT etat, count(*) FROM mail_queue GROUP BY etat")).all()}
        echecs_jour = c.execute(text(
            "SELECT count(*) FROM mail_queue WHERE etat = 'echec' AND cree_at::date = (now() AT TIME ZONE"
            " 'Indian/Reunion')::date")).scalar() or 0
    return {"par_etat": par_etat, "echecs_jour": int(echecs_jour),
            "en_attente": int(par_etat.get("en_attente", 0)),
            "partis": int(par_etat.get("recu", 0) + par_etat.get("parti", 0)),
            "echecs": int(par_etat.get("echec", 0))}


def echecs_du_jour(engine) -> int:
    return compteurs(engine)["echecs_jour"]


# ───────────────────────── journal (« qui ») ─────────────────────────

def _journal(engine, mail_id: int, etat: str, demandeur: str, compte_id: int | None,
             detail: str = "") -> None:
    """Trace chaque transition dans evenements_compte (audit compte : QUI a fait QUOI, QUAND).
    Best-effort : une trace qui échoue ne masque jamais l'action (déjà écrite dans mail_queue)."""
    try:
        with engine.begin() as c:
            c.execute(text(
                "INSERT INTO evenements_compte (type, compte_id, detail)"
                " VALUES (:t, :c, :d)"),
                {"t": f"mail_{etat}", "c": compte_id,
                 "d": f"[{demandeur}] file#{mail_id} — {detail}"})
    except Exception:  # noqa: BLE001 — le journal est une preuve secondaire ; mail_queue reste la vérité
        log.debug("journal mail #%s (%s) non écrit", mail_id, etat)
