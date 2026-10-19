"""COMPTE-2 · Lot 2 — la FILE D'ATTENTE des mails (`mail_queue`) et le point d'envoi unique.

C'est le lot qui rend l'envoi VISIBLE. Avant, un mail partait (ou ne partait pas) sans que rien ne le
raconte. Désormais TOUT envoi de template passe par cette file, y compris les envois immédiats :

    en attente ──(revendication)──► parti (= envoi EN COURS) ──(2xx Brevo)──► reçu par Brevo
        │                                   │
        └────────(3 échecs)────────────────┴──► échec  (rejouable d'un clic)

ORF-08 (FIX-ORFEVRE-1) — l'état `parti` est la REVENDICATION transactionnelle posée AVANT l'appel
réseau : deux consommateurs concurrents (worker ↔ bouton « rejouer ») ne peuvent jamais envoyer le
même mail deux fois (le second trouve l'entrée déjà revendiquée). Un `parti` trop vieux (processus
tué pendant l'envoi) est repris par le worker (→ `a_rejouer`).

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
import os
import time
from datetime import datetime, timezone

from sqlalchemy import text

from . import brevo

log = logging.getLogger("labuse.mailfile")

TENTATIVES_MAX = 3
#: BUDGET DE TEMPS du worker (`consommer`). Le job `mail-queue-consommer` a un timeout de 300 s imposé
#: par `signal.alarm` (jobs.py) : si l'alarme frappe PENDANT une requête psycopg, la connexion reste
#: « command in progress » et le rollback lève « another command is already in progress » (incident du
#: 14/10, 09:40). On s'arrête donc BIEN avant (240 s) : la boucle ne lance plus de nouveau mail une fois
#: le budget écoulé — le dernier envoi en cours (SMTP timeout 15 s) + l'écriture finissent sous 300 s, et
#: le reliquat part au passage suivant (toutes les 5 min). Plus jamais d'alarme en pleine requête.
BUDGET_CONSOMMER_S = 240.0
#: fenêtre anti-doublon par défaut (double-clic) : deux enfilages identiques sous ce délai = un seul.
FENETRE_DOUBLON_S = 30
#: ORF-07 (FIX-ORFEVRE-1) — FRAÎCHEUR maximale d'un mail encore « dû » : au-delà, le worker l'ANNULE
#: (motif lisible) au lieu de l'envoyer. Garde contre les résidus de recette : 12 mails de test du
#: 16/10 restaient éligibles À JAMAIS — le premier passage avec un transport réel les aurait envoyés
#: (dont 3 vers un compte supprimé). Surchargable par env (jamais < 1 jour).
FRAICHEUR_MAX_JOURS = max(1, int(os.environ.get("LABUSE_MAIL_FRAICHEUR_MAX_JOURS", "7")))
#: ORF-08 — un `parti` (envoi revendiqué) plus vieux que ce délai = processus tué pendant l'envoi ;
#: le worker le repasse `a_rejouer` (at-least-once assumé : on ne sait pas si Brevo a reçu).
PARTI_REPRISE_MIN = 15

# VEILLE-FIX-2 (Lot D) — REJEU espacé : après un échec Brevo, l'entrée passe `a_rejouer` avec une date de
# prochaine tentative (5 min, puis 1 h, puis 24 h). Le worker `mail-queue-consommer` (cron 5 min) la
# reprend quand l'heure est venue. Au-delà des 3 rejeux → `echec` définitif (ligne rouge, rejeu manuel).
from datetime import timedelta as _td
DELAIS_REJEU = (_td(minutes=5), _td(hours=1), _td(hours=24))

# vocabulaire d'état UNIQUE (mandat). `annule` = un programmé décommandé avant départ (jamais supprimé)
# OU une ligne refusée par les gardes du worker (compte supprimé, dû trop vieux — ORF-07, motif dans
# `erreur`). `a_rejouer` (VEILLE-FIX-2) = échec transitoire Brevo, nouvelle tentative programmée
# (prevu_at). `parti` (ORF-08) = envoi EN COURS, revendiqué transactionnellement avant l'appel réseau.
ETATS = ("en_attente", "a_rejouer", "parti", "recu", "echec", "annule")
LIBELLES_ETAT = {
    "en_attente": "En attente", "a_rejouer": "À rejouer", "parti": "Envoi en cours",
    "recu": "Reçu par Brevo", "echec": "Échec", "annule": "Annulé",
}


def _schema_conforme(c) -> bool:
    """ORF-01 (FIX-ORFEVRE-1) — LE SCHÉMA EST-IL DÉJÀ EN PLACE ? Lecture seule des catalogues
    (to_regclass/pg_indexes/pg_constraint) : AUCUN verrou, jouable même pendant le pg_dump quotidien.
    C'est la garde qui évite de rejouer les DDL à chaque run du worker (toutes les 5 min) : l'ALTER
    CONSTRAINT prenait un verrou ACCESS EXCLUSIVE, bloqué par le backup 13:30-13:48 → timeout 300 s
    → échec quotidien du job mail-queue-consommer (journaux prod 14-18/10)."""
    if c.execute(text("SELECT to_regclass('mail_queue')")).scalar() is None:
        return False
    if not c.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'mail_queue' AND column_name = 'avert'")).first():
        return False
    idx = {r[0] for r in c.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'mail_queue'"))}
    if not {"ix_mail_queue_etat_cree", "ix_mail_queue_compte", "ix_mail_queue_dedup"} <= idx:
        return False
    # la contrainte CHECK doit connaître TOUS les états (dont `a_rejouer`, VEILLE-FIX-2).
    cdef = c.execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'mail_queue_etat_check' AND conrelid = 'mail_queue'::regclass")).scalar()
    return bool(cdef) and all(f"'{e}'" in cdef for e in ETATS)


def ensure_tables(engine) -> None:
    """Idempotent (pattern maison CREATE IF NOT EXISTS), appelable au boot.

    ORF-01 — en RÉGIME ÉTABLI (schéma conforme), cette fonction ne tente plus AUCUNE DDL : une
    vérification lecture seule suffit. Les DDL ne sont rejouées que si un morceau manque vraiment
    (première installation, migration) — le cas « déploiement », pas le cas « worker toutes les 5 min »."""
    with engine.begin() as c:
        if _schema_conforme(c):
            return
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
                             CHECK (etat IN ('en_attente','a_rejouer','parti','recu','echec','annule')),
                demandeur    varchar(64) NOT NULL DEFAULT 'systeme',  -- QUI : vic / job:<nom> / client
                dedup        varchar(96),            -- anti-doublon (compte:key), fenêtre courte
                tentatives   integer NOT NULL DEFAULT 0,
                message_id   text,                   -- messageId Brevo (preuve du départ)
                erreur       text,                   -- raison lisible en français (échec)
                prevu_at     timestamptz,            -- date PRÉVUE d'un programmé (NULL = immédiat)
                cree_at      timestamptz NOT NULL DEFAULT now(),
                parti_at     timestamptz             -- date de DÉPART réel (2xx)
            )"""))
        # COMPTE-3 (Lot 2) — avertissement figé à l'enfilage si l'URL de base des liens n'est pas
        # cliquable par un client distant (localhost). Colonne ajoutée en place (table existante).
        # RETOUCHES-1 (lot A) — GARDE d'existence AVANT l'ALTER : `ADD COLUMN IF NOT EXISTS` prend un
        # verrou ACCESS EXCLUSIVE sur mail_queue MÊME en no-op (colonne déjà là) ; sur une connexion
        # séparée (ensure_tables reçoit l'engine, pas la session), il s'interbloque contre une session
        # qui tient des écritures mail_queue non committées (2ᵉ appel envoyer_digests). On ne verrouille
        # donc que si la colonne manque VRAIMENT — idempotent et sans verrou en régime établi.
        _has_avert = c.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'mail_queue' AND column_name = 'avert'")).first()
        if not _has_avert:
            c.execute(text("ALTER TABLE mail_queue ADD COLUMN avert text"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_mail_queue_etat_cree ON mail_queue(etat, cree_at DESC)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_mail_queue_compte ON mail_queue(compte_id, cree_at DESC)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_mail_queue_dedup ON mail_queue(dedup, cree_at DESC)"))
        # VEILLE-FIX-2 (Lot D) — la contrainte CHECK d'une table EXISTANTE ne connaît pas `a_rejouer` :
        # on la remplace. ORF-01 : SEULEMENT si elle est vraiment périmée (le DROP/ADD systématique
        # prenait un verrou ACCESS EXCLUSIVE à chaque run — cf. _schema_conforme).
        cdef = c.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'mail_queue_etat_check' AND conrelid = 'mail_queue'::regclass")).scalar()
        if not cdef or not all(f"'{e}'" in cdef for e in ETATS):
            c.execute(text("ALTER TABLE mail_queue DROP CONSTRAINT IF EXISTS mail_queue_etat_check"))
            c.execute(text("ALTER TABLE mail_queue ADD CONSTRAINT mail_queue_etat_check "
                           "CHECK (etat IN ('en_attente','a_rejouer','parti','recu','echec','annule'))"))


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
    défaut, compte:key:hash(params)) a déjà une entrée NON-échec dans la fenêtre, on renvoie celle-là.

    VEILLE-FIX-1 (lot 5) — mail BRUT (digest de veille) : une `key` HORS registre Brevo est acceptée
    SI `params['__raw']` porte le mail construit côté code (`sujet`, `texte`, `html`, `nom`) ; le départ
    part alors par `mail.send_email` (SMTP), pas par un template Brevo. `template_id` reste NULL — c'est
    le marqueur « brut » lu par `_tenter_depart`. Ainsi les mails de veille passent par mail_queue comme
    les autres (même table, mêmes états, même trace)."""
    params = params or {}
    t = brevo.template(key)
    raw = params.get("__raw") if isinstance(params, dict) else None
    if not t and not raw:
        raise ValueError(f"template inconnu « {key} » (ni template Brevo, ni mail brut `__raw`)")
    tnom = (t.nom if t else (raw.get("nom") if isinstance(raw, dict) else None) or key)[:48]
    dd = dedup or f"{compte_id}:{key}:{_params_hash(params)}"
    # COMPTE-3 (Lot 2) — on FIGE ici l'état de l'URL de base : si les liens ne sont pas cliquables par
    # un destinataire distant (localhost / URL absente), l'entrée porte l'avertissement — visible dans
    # l'onglet Mails. L'envoi n'est jamais bloqué (Vic teste en local), mais la file ne peut pas le cacher.
    from . import config as _config
    avert = _config.base_url_probleme()
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
            " params, demandeur, dedup, prevu_at, avert) VALUES"
            " (:cid, :key, :tid, :tn, :to, CAST(:p AS jsonb), :who, :dd, :prevu, :avert) RETURNING *"),
            {"cid": compte_id, "key": key, "tid": (brevo.template_id(key) if t else None),
             "tn": tnom, "to": to,
             "p": json.dumps(params, ensure_ascii=False), "who": demandeur[:64], "dd": dd,
             "prevu": prevu_at, "avert": avert}).mappings().first()
    _journal(engine, row["id"], "en_attente", demandeur, compte_id,
             detail=f"{key} → {to}" + (f" (prévu {prevu_at.isoformat()})" if prevu_at else ""))
    return {**_ligne(row), "doublon": False}


def _tenter_depart(engine, mail_id: int) -> dict:
    """Tente le DÉPART d'une entrée : appelle le transport Brevo, écrit l'état RÉEL. Idempotent sur
    `recu`/`annule` (ne renvoie pas un mail déjà parti). Retourne la ligne à jour.

    ORF-08 (FIX-ORFEVRE-1) — REVENDICATION transactionnelle : avant l'appel réseau, l'entrée passe
    `parti` (= envoi en cours) DANS la transaction qui tient le FOR UPDATE. L'ancien code relâchait le
    verrou (commit) AVANT l'appel Brevo : worker ↔ « rejouer » admin pouvaient tous deux lire un état
    envoyable → le client recevait le mail DEUX fois. Désormais le second lecteur trouve `parti` et
    repart sans envoyer. Un `parti` orphelin (processus tué en plein envoi) est repris par `consommer`
    après PARTI_REPRISE_MIN minutes."""
    with engine.begin() as c:
        row = c.execute(text("SELECT * FROM mail_queue WHERE id = :i FOR UPDATE"),
                        {"i": mail_id}).mappings().first()
        if not row:
            raise ValueError(f"mail {mail_id} introuvable")
        if row["etat"] not in ("en_attente", "a_rejouer"):
            # recu/annule : idempotent ; echec : seul `rejouer` (qui remet en_attente) le relance ;
            # parti : un AUTRE consommateur l'envoie en ce moment même — on ne double jamais.
            return _ligne(row)
        # la revendication : visible de tout autre consommateur dès le commit, AVANT l'I/O réseau.
        c.execute(text("UPDATE mail_queue SET etat = 'parti', parti_at = :now WHERE id = :i"),
                  {"now": _now(), "i": mail_id})
        key, to, params = row["mail_key"], row["destinataire"], row["params"] or {}
        demandeur, compte_id, template_id = row["demandeur"], row["compte_id"], row["template_id"]
    raw = params.get("__raw") if isinstance(params, dict) else None
    if template_id is None and isinstance(raw, dict):
        # VEILLE-FIX-1 (lot 5) — mail BRUT : départ par SMTP (send_email), construit côté code.
        from . import mail
        r = mail.send_email(to, raw.get("sujet") or "", raw.get("texte") or "",
                            body_html=raw.get("html"), headers=raw.get("headers"))
        res = {"envoye": bool(r.ok), "raison": None if r.ok else (r.detail or "SMTP non configuré")}
    else:
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
    # VEILLE-FIX-2 (Lot D) — échec Brevo : REJEU ESPACÉ. On incrémente le compteur ; tant qu'il reste des
    # délais (5 min, 1 h, 24 h), l'entrée passe `a_rejouer` avec la date de la prochaine tentative (le
    # worker la reprendra). Au-delà → `echec` définitif (ligne rouge, rejeu manuel). Jamais d'envoi en
    # double : la REVENDICATION `parti` (ORF-08) posée transactionnellement ci-dessus sérialise les
    # consommateurs — l'ancien commentaire « le FOR UPDATE sérialise » était FAUX entre processus (le
    # verrou était relâché avant l'appel réseau). `parti_at` est remis à NULL : rien n'est parti (RV-013).
    raison = res.get("raison") or "échec inconnu"
    with engine.begin() as c:
        cur = c.execute(text("SELECT tentatives FROM mail_queue WHERE id = :i FOR UPDATE"),
                        {"i": mail_id}).scalar() or 0
        nouv = cur + 1
        if nouv <= len(DELAIS_REJEU):
            prochain = _now() + DELAIS_REJEU[nouv - 1]
            row = c.execute(text(
                "UPDATE mail_queue SET tentatives = :n, erreur = :err, etat = 'a_rejouer', prevu_at = :p,"
                " parti_at = NULL WHERE id = :i RETURNING *"),
                {"n": nouv, "err": raison, "p": prochain, "i": mail_id}).mappings().first()
        else:
            row = c.execute(text(
                "UPDATE mail_queue SET tentatives = :n, erreur = :err, etat = 'echec', parti_at = NULL"
                " WHERE id = :i RETURNING *"),
                {"n": nouv, "err": raison, "i": mail_id}).mappings().first()
    suite = (f" — rejeu prévu {row['prevu_at'].astimezone().isoformat(timespec='minutes')}"
             if row["etat"] == "a_rejouer" and row["prevu_at"] else " — ÉCHEC définitif (rejeu manuel)")
    _journal(engine, mail_id, row["etat"], demandeur, compte_id,
             detail=f"{key} → {to} — tentative {row['tentatives']} : {raison}{suite}")
    return _ligne(row)


def envoyer_mail(engine, *, key: str, to: str, params: dict | None = None,
                 compte_id: int | None = None, demandeur: str = "systeme",
                 prevu_at: datetime | None = None, dedup: str | None = None,
                 fenetre_doublon_s: int = FENETRE_DOUBLON_S, dry_run: bool = False,
                 differe: bool = False) -> dict:
    """POINT D'ENVOI UNIQUE (façade `mail.envoyer_mail`) : enfile, puis — si l'envoi est immédiat
    (`prevu_at` absent ou déjà passé) — déclenche le départ tout de suite. Un programmé (J+3, J+10)
    reste `en_attente` avec sa date prévue ; le worker `mail-queue-consommer` le fera partir. Renvoie la
    ligne. `fenetre_doublon_s` : fenêtre anti-doublon (ex. relance carte = plusieurs jours, Stripe rejoue).

    VEILLE-FIX-1 (lot 5) — `dry_run` : on ÉCRIT la ligne (trace) mais on NE DÉCLENCHE PAS le départ.
    VEILLE-FIX-2 (Lot D) — `differe` : on enfile `en_attente` SANS déclencher le départ synchrone (le
    worker s'en charge dans les 5 min) → le mail bénéficie du REJEU. Le digest passe par ce chemin."""
    ligne = enfiler(engine, key=key, to=to, params=params, compte_id=compte_id,
                    demandeur=demandeur, prevu_at=prevu_at, dedup=dedup,
                    fenetre_doublon_s=fenetre_doublon_s)
    if ligne.get("doublon") or dry_run or differe:
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


def consommer(engine, demandeur: str = "job:mail-queue-consommer", limite: int = 200,
              budget_s: float | None = BUDGET_CONSOMMER_S) -> dict:
    """VEILLE-FIX-2 (Lot D) — LE WORKER DE LA FILE (cron 5 min). Fait partir tout ce qui est DÛ :
      · `en_attente` sans `prevu_at` (immédiats différés, ex. digest) OU `prevu_at ≤ now` (programmés
        J+3 / J+10) ;
      · `a_rejouer` dont l'heure de rejeu est venue (`prevu_at ≤ now`).
    Idempotent, jamais d'envoi en double (`_tenter_depart` REVENDIQUE l'entrée — état `parti` — dans
    la transaction qui tient le FOR UPDATE, ORF-08). S'ARRÊTE après `budget_s` (ne lance plus de
    nouveau mail) pour ne JAMAIS se faire couper par le timeout du job en pleine requête (cf.
    BUDGET_CONSOMMER_S) ; le reliquat part au passage suivant.

    ORF-07 (FIX-ORFEVRE-1) — DEUX GARDES avant tout envoi (annulation motivée, jamais silencieuse) :
      · compte supprimé : une ligne dont le `compte_id` n'existe plus ne part JAMAIS ;
      · fraîcheur : une ligne due depuis plus de FRAICHEUR_MAX_JOURS (résidu de recette, file gelée
        en dry-run) ne part JAMAIS — un mail transactionnel vieux d'une semaine est un mail faux.
    ORF-08 — REPRISE des `parti` orphelins (> PARTI_REPRISE_MIN min : processus tué pendant l'envoi)
    → `a_rejouer` immédiat (at-least-once assumé, dit dans `erreur`).

    Retourne {traites, envoyes, a_rejouer, echecs, annules, repris, restants} — `restants` > 0 =
    budget atteint."""
    with engine.begin() as c:
        # ORF-08 — reprise des envois revendiqués puis abandonnés (kill -9 / coupure en plein appel).
        repris = c.execute(text(
            "UPDATE mail_queue SET etat = 'a_rejouer', prevu_at = now(), parti_at = NULL,"
            " erreur = 'départ interrompu (processus arrêté pendant l''envoi) — repris par le worker'"
            " WHERE etat = 'parti' AND parti_at < now() - make_interval(mins => :m)"),
            {"m": PARTI_REPRISE_MIN}).rowcount
        # ORF-07 garde 1 — compte supprimé → annulé (motif lisible, la ligne reste : l'historique EST
        # la preuve). Gardée par l'existence de la table (base de test minimale sans `comptes`).
        annules = 0
        if c.execute(text("SELECT to_regclass('comptes')")).scalar() is not None:
            annules += c.execute(text(
                "UPDATE mail_queue SET etat = 'annule',"
                " erreur = 'compte supprimé — envoi annulé par la garde du worker'"
                " WHERE etat IN ('en_attente','a_rejouer') AND (prevu_at IS NULL OR prevu_at <= now())"
                " AND compte_id IS NOT NULL"
                " AND NOT EXISTS (SELECT 1 FROM comptes k WHERE k.id = mail_queue.compte_id)")).rowcount
        # ORF-07 garde 2 — dû depuis trop longtemps → annulé (il ne « rattrapera » jamais son retard).
        annules += c.execute(text(
            "UPDATE mail_queue SET etat = 'annule',"
            " erreur = 'dû depuis plus de ' || :j || ' jours — envoi annulé par la garde du worker'"
            " WHERE etat IN ('en_attente','a_rejouer')"
            " AND coalesce(prevu_at, cree_at) < now() - make_interval(days => :j)"),
            {"j": FRAICHEUR_MAX_JOURS}).rowcount
        if repris or annules:
            log.warning("mail-queue : %d envoi(s) interrompu(s) repris, %d ligne(s) annulée(s) "
                        "(compte supprimé / dû > %d j)", repris, annules, FRAICHEUR_MAX_JOURS)
        ids = [r[0] for r in c.execute(text(
            "SELECT id FROM mail_queue WHERE etat IN ('en_attente','a_rejouer') "
            "AND (prevu_at IS NULL OR prevu_at <= now()) "
            "ORDER BY prevu_at NULLS FIRST, id LIMIT :l"), {"l": int(limite)}).all()]
    envoyes = rejeu = echecs = traites = 0
    debut = time.monotonic()
    for mid in ids:
        if budget_s is not None and (time.monotonic() - debut) >= budget_s:
            break  # budget écoulé : on ne lance PAS de nouvel envoi → jamais d'alarme en pleine requête
        r = _tenter_depart(engine, mid)
        traites += 1
        if r["etat"] == "recu":
            envoyes += 1
        elif r["etat"] == "a_rejouer":
            rejeu += 1
        elif r["etat"] == "echec":
            echecs += 1
    restants = len(ids) - traites
    if restants:
        log.info("mail-queue : budget %.0fs atteint — %d traité(s), %d reliquat(s) au prochain passage",
                 budget_s or 0, traites, restants)
    return {"traites": traites, "envoyes": envoyes, "a_rejouer": rejeu, "echecs": echecs,
            "annules": annules, "repris": repris, "restants": restants}


def depart_des_programmes(engine, demandeur: str = "job:mail-queue") -> int:
    """Compat — délègue au worker unifié `consommer` (retourne le nombre d'entrées traitées)."""
    return consommer(engine, demandeur=demandeur)["traites"]


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


def echecs_par_compte(engine) -> dict:
    """VEILLE-FIX-2 (Lot D) — {compte_id: nb de mails en ÉCHEC définitif}. Alimente la LIGNE ROUGE du
    dashboard Comptes : un compte dont un mail a épuisé ses rejeux est signalé."""
    with engine.begin() as c:
        rows = c.execute(text("SELECT compte_id, count(*) FROM mail_queue "
                              "WHERE etat = 'echec' AND compte_id IS NOT NULL GROUP BY compte_id")).all()
    return {int(r[0]): int(r[1]) for r in rows}


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
